"""Unequal whole chains per CPU/Gloo rank vs explicit detached global reference."""
import argparse
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP


def targets(rank):
    # Rank0: a five-round chain with R5x3. Rank1: a real single-turn sample.
    return [1, 2, 3, 4, 5, 5, 5] if rank == 0 else [1]


def one_rank(model, rank, denominator, distributed):
    history, forwards, decodes = [], 0, 0
    for index, k in enumerate(targets(rank)):
        x = torch.ones(2 + rank, 2) * (k / 10)
        if k > 1:
            x = x + history[k-2]
        context = model.no_sync() if distributed and index < len(targets(rank))-1 else nullcontext()
        with context:
            prediction = model(x)
            numerator = prediction.square().mean(-1).sum()
            clean = prediction.detach().mean().reshape(1)
            loss = numerator * (dist.get_world_size() if distributed else 1) / denominator
            loss.backward()
        if rank == 0 and k < 5:
            assert clean.grad_fn is None and not clean.requires_grad
            history.append(clean)
            decodes += 1
        forwards += 1
    return forwards, decodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    dist.init_process_group("gloo")
    rank = dist.get_rank()
    assert dist.get_world_size() == 2
    model = torch.nn.Linear(2, 1)
    with torch.no_grad():
        model.weight.fill_(.2)
        model.bias.fill_(.1)
    reference = deepcopy(model)
    ddp = DDP(model, find_unused_parameters=True, broadcast_buffers=False, gradient_as_bucket_view=True)
    optimizer = torch.optim.SGD(model.parameters(), lr=.01)
    ref_optimizer = torch.optim.SGD(reference.parameters(), lr=.01)
    max_difference = 0.
    for step in range(3):
        count = torch.tensor((2 + rank) * len(targets(rank)))
        dist.all_reduce(count)
        denominator = int(count)
        forwards, decodes = one_rank(ddp, rank, denominator, True)
        for r in range(2):
            one_rank(reference, r, denominator, False)
        for actual, expected in zip(model.parameters(), reference.parameters()):
            torch.testing.assert_close(actual.grad, expected.grad, rtol=1e-6, atol=1e-7)
            max_difference = max(max_difference, float((actual.grad-expected.grad).abs().max()))
        optimizer.step(); ref_optimizer.step()
        optimizer.zero_grad(set_to_none=True); ref_optimizer.zero_grad(set_to_none=True)
    if rank == 0:
        args.output.write_text(json.dumps(dict(status="passed", world_size=2, backend="gloo", updates=3,
            local_forward_counts=[7,1], decode_counts=[4,0], gradient_reference="global_token_mean_detached_history",
            max_gradient_difference=max_difference), indent=2)+"\n")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
