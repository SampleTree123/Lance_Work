from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import torch
from torch import nn


LANCE_ROOT = Path(__file__).parents[1] / "lance"
import sys

sys.path.insert(0, str(LANCE_ROOT))

from train.datamake_generation_lora import GenerationLoRAConfig  # noqa: E402
from train.datamake_lora_checkpoint import (  # noqa: E402
    load_lora_checkpoint,
    save_lora_checkpoint,
    validate_lora_checkpoint,
)


class AdapterOnlyModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.frozen = nn.Parameter(torch.ones(4), requires_grad=False)
        self.lora_A = nn.Parameter(torch.arange(8, dtype=torch.float32).view(2, 4))
        self.lora_B = nn.Parameter(torch.zeros(4, 2))

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        update = value @ self.lora_A.t() @ self.lora_B.t()
        return (value * self.frozen + update).square().mean()


class Logger:
    def info(self, _message) -> None:
        pass


class AdapterCheckpointTest(unittest.TestCase):
    def test_single_process_optimizer_scheduler_and_rng_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            torch.manual_seed(17)
            model = AdapterOnlyModel()
            optimizer = torch.optim.AdamW(
                [model.lora_A, model.lora_B], lr=1e-3, weight_decay=0.0
            )
            scheduler = torch.optim.lr_scheduler.LambdaLR(
                optimizer, lambda step: 1.0 - 0.01 * step
            )
            value = torch.arange(4, dtype=torch.float32).view(1, 4)
            model(value).backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)

            config = GenerationLoRAConfig(
                rank=2,
                alpha=2.0,
                dropout=0.0,
                target_scope="generation_experts",
                expected_target_modules=1,
            )
            contract = {"schema": "unit-test", "seed": 17}
            checkpoint = save_lora_checkpoint(
                Path(temp_dir) / "checkpoints",
                completed_steps=1,
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                lora_config=config,
                training_contract=contract,
                trainer_state={"epoch": 0, "epoch_step": 1},
                keep_last=4,
                logger=Logger(),
            )
            marker = json.loads(
                (checkpoint / "checkpoint_complete.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(marker["adapter_only"])
            self.assertFalse(marker["base_weights_stored"])
            self.assertEqual(marker["checkpoint_format_version"], 5)

            restored_model = AdapterOnlyModel()
            with torch.no_grad():
                restored_model.lora_A.zero_()
                restored_model.lora_B.zero_()
            restored_optimizer = torch.optim.AdamW(
                [restored_model.lora_A, restored_model.lora_B],
                lr=1e-3,
                weight_decay=0.0,
            )
            restored_scheduler = torch.optim.lr_scheduler.LambdaLR(
                restored_optimizer, lambda step: 1.0 - 0.01 * step
            )
            state = load_lora_checkpoint(
                checkpoint,
                restored_model,
                restored_optimizer,
                restored_scheduler,
                config,
                contract,
            )

            self.assertEqual(state["next_step"], 1)
            self.assertEqual(scheduler.state_dict(), restored_scheduler.state_dict())
            self.assertTrue(torch.equal(model.lora_A, restored_model.lora_A))
            self.assertTrue(torch.equal(model.lora_B, restored_model.lora_B))
            original_state = optimizer.state_dict()["state"]
            restored_state = restored_optimizer.state_dict()["state"]
            self.assertEqual(set(original_state), set(restored_state))
            for key in original_state:
                for field in ("step", "exp_avg", "exp_avg_sq"):
                    self.assertTrue(
                        torch.equal(
                            original_state[key][field], restored_state[key][field]
                        )
                    )

            marker["checkpoint_format_version"] = 4
            (checkpoint / "checkpoint_complete.json").write_text(
                json.dumps(marker), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "format must be v5"):
                validate_lora_checkpoint(checkpoint, expected_world_size=1)


if __name__ == "__main__":
    unittest.main()
