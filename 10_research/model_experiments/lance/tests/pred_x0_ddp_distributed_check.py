"""Two CPU/Gloo ranks: unequal history lengths, no_sync and detached gradients."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace

from test_datamake_pred_x0_ddp import trainer, PredX0PrefixDataset
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    dist.init_process_group("gloo")
    rank, world = dist.get_rank(), dist.get_world_size()
    model = torch.nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        model.weight.fill_(.5)
    ddp = DDP(model, broadcast_buffers=False, find_unused_parameters=True)
    observations = []
    reference_gradient = 0.

    def pack(request, turn, histories, seed):
        assert all(not h.requires_grad and h.grad_fn is None for h in histories)
        return torch.tensor([[float(turn)]])

    def predict(batch, bare, *args):
        assert not torch.is_grad_enabled()
        result = bare(batch)
        assert not result.requires_grad
        observations.append(float(result))
        return result.detach()

    def supervised(batch, wrapped, *args, **kwargs):
        assert torch.is_grad_enabled()
        loss = wrapped(batch).square().mean()
        return loss, {}, 1, [{"sample_id": "toy"}]

    PredX0PrefixDataset.active = SimpleNamespace(pack_turn=pack)
    trainer.generation_rng = lambda *args: nullcontext()
    trainer.predict_history = predict
    trainer.supervised_loss = supervised
    for micro in range(4):
        # One rank may do zero histories while the other does four; swap next microbatch.
        rounds = [1 + ((micro + r) % 2) * 4 for r in range(world)]
        k = rounds[rank]
        batch = (SimpleNamespace(pred_x0_prefix_request={"row": {"target_round": k}, "seed": micro})
                 if k > 1 else torch.tensor([[1.]]))
        with ddp.no_sync() if micro < 3 else nullcontext():
            loss, metrics, _, _ = trainer.microbatch_loss(batch, ddp, None, None, None, "cpu", world, [])
            assert set(metrics) == {"history_generated_rounds", "history_detached"}
            (loss / 4).backward()
        reference_gradient += sum(k*k for k in rounds) / world / 4  # d(.5*x)^2/dw = x^2
    torch.testing.assert_close(model.weight.grad, torch.tensor([[reference_gradient]]), rtol=0, atol=0)
    assert len(observations) == 8
    if rank == 0:
        args.output.write_text(json.dumps(dict(status="passed", backend="gloo", world_size=world,
            accumulation=4, gradient=float(model.weight.grad), reference_gradient=reference_gradient,
            generation_forwards_per_rank=len(observations), cross_history_gradient=False), indent=2)+"\n")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
