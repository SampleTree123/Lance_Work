"""Run with torchrun --standalone --nproc-per-node=2; real CPU/Gloo DDP check."""
import argparse
from contextlib import nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

from test_datamake_ddp_peft import create
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel
from train.train_utils import compute_training_loss


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--accumulation", type=int, default=8)
    parser.add_argument("--no-region-weighting", action="store_true")
    args = parser.parse_args()
    if args.accumulation < 1:
        raise ValueError("accumulation must be positive")
    torch.set_num_threads(1)
    dist.init_process_group("gloo")
    rank, world = dist.get_rank(), dist.get_world_size()
    model, opt, sched = create(True)
    reference = deepcopy(model)
    ref_opt = torch.optim.AdamW([p for p in reference.parameters() if p.requires_grad], lr=3e-4, weight_decay=0)
    from train.datamake_train_state import initialize_adam_state
    initialize_adam_state(ref_opt)
    ref_sched = torch.optim.lr_scheduler.LambdaLR(ref_opt, lambda step: min(step / 101, 1))
    ddp = DistributedDataParallel(model, find_unused_parameters=True, gradient_as_bucket_view=True)
    base = {n: p.detach().clone() for n, p in model.named_parameters() if not p.requires_grad}
    max_gradient_difference = 0.
    for step in range(3):
        opt.zero_grad(set_to_none=True);ref_opt.zero_grad(set_to_none=True)
        for micro in range(args.accumulation):
            inputs = [torch.randn(2, 4, generator=torch.Generator().manual_seed(1000*step+10*micro+r)) for r in range(world)]
            weights = [torch.tensor([1., 1.2 + .1*r, 2.]) for r in range(world)]
            if args.no_region_weighting:
                weights = [torch.ones(3) for _ in range(world)]
            with ddp.no_sync() if micro < args.accumulation - 1 else nullcontext():
                scalar = ddp(inputs[rank])
                loss, _, _, _ = compute_training_loss(
                    {"ce": None, "mse": scalar.expand(3, 1), "total_mse_tokens": 3, "frame_mse": None},
                    {}, None, SimpleNamespace(visual_gen=True, mse_weight=1.), "cpu", world,
                    None if args.no_region_weighting else weights[rank])
                (loss / args.accumulation).backward()
            ref_loss = sum(reference(x) * w.sum() for x, w in zip(inputs, weights)) / sum(w.sum() for w in weights)
            (ref_loss / args.accumulation).backward()
        ref_params = dict(reference.named_parameters())
        for name, p in model.named_parameters():
            q = ref_params[name]
            if p.grad is None:
                assert q.grad is None, name
            else:
                difference = (p.grad-q.grad).abs().max().item()
                max_gradient_difference = max(max_gradient_difference, difference)
                torch.testing.assert_close(p.grad, q.grad, atol=1e-6, rtol=1e-5)
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.)
        torch.nn.utils.clip_grad_norm_([p for p in reference.parameters() if p.requires_grad], 1.)
        opt.step();sched.step();ref_opt.step();ref_sched.step()
        for name, p in model.named_parameters():
            torch.testing.assert_close(p, ref_params[name], atol=1e-7, rtol=1e-5)
            if name in base: assert torch.equal(p, base[name]), name
    if rank == 0:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"status": "passed", "world_size": world, "backend": "gloo",
                                           "updates": 3, "accumulation": args.accumulation,
                                           "region_weighting": not args.no_region_weighting,
                                           "max_gradient_difference": max_gradient_difference,
                                           "scope": "real DDP + PEFT + project weighted loss vs explicit global reference; no GPU performance evidence"}, indent=2)+'\n')
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
