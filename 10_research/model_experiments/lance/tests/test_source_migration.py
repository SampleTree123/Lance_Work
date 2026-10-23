"""Current source boundaries and helpers after the 2026-10-22 migration."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lance"), str(ROOT / "scripts"), str(ROOT / "runtime/peft_0_15_2")]


class SourceMigrationTests(unittest.TestCase):
    def test_official_loop_does_not_forward_datamake_metadata_to_model(self):
        # Execute the actual per-batch preprocessing before autocast. This
        # protects the boundary between our shared packer and official trainer.
        tree = ast.parse((ROOT / "lance/train/unified_train.py").read_text())
        loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For)
                    and isinstance(n.target, ast.Tuple)
                    and any(isinstance(x, ast.Name) and x.id == "curr_step" for x in n.target.elts))
        body = next(n.body for n in loop.body if isinstance(n, ast.Try))
        prefix = body[:next(i for i, n in enumerate(body) if isinstance(n, ast.With))]
        class Batch:
            def cuda(self, device):
                return self
            def to_dict(self):
                return {"sequence_length": 128, "vae_edit_roles": ["source", "target"],
                        "batch_data_indexes": ["sample"], "ce_loss_weights": None}
        scope = {"data": Batch(), "DEVICE": "cpu"}
        exec(compile(ast.Module(body=prefix, type_ignores=[]), "official_batch_boundary", "exec"), scope)
        self.assertEqual(scope["data"], {"sequence_length": 128})

    def test_current_training_does_not_import_retired_trainers_or_manual_lora(self):
        forbidden = {
            "run_datamake_formal_training", "train.datamake_stage2_lora_train",
            "train.datamake_online_rollout_lora_train", "train.datamake_lora_generation_train",
            "train.datamake_stage2_lora_checkpoint", "train.datamake_branch_lora",
            "train.datamake_generation_lora",
        }
        files = [ROOT / "lance/train" / name for name in (
            "datamake_ddp_train.py", "datamake_chain_pred_x0_ddp_train.py",
            "datamake_peft.py", "datamake_lora_config.py", "datamake_train_state.py",
            "datamake_flow_history.py", "datamake_ddp_checkpoint.py")]
        files += [ROOT / "scripts/datamake_runtime.py", ROOT / "scripts/run_datamake_ddp_training.py"]
        for path in files:
            tree = ast.parse(path.read_text())
            imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            imports.update(alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names)
            self.assertFalse(imports & forbidden, f"{path}: {imports & forbidden}")

    def test_pred_x0_is_detached_but_current_loss_keeps_gradients(self):
        import torch
        from train.datamake_flow_history import predict_clean_latent_patches
        velocity = torch.nn.Parameter(torch.tensor([[2., 4.], [6., 8.]]))
        noisy = torch.tensor([[1., 2.], [3., 4.]])
        history = predict_clean_latent_patches(dict(
            flow_noisy_target=noisy, flow_pred_velocity=velocity,
            flow_timesteps=torch.tensor([0.25, 0.5])))
        torch.testing.assert_close(history, torch.tensor([[0.5, 1.], [0., 0.]]))
        self.assertFalse(history.requires_grad)
        self.assertIsNone(history.grad_fn)
        velocity.square().sum().backward()
        torch.testing.assert_close(velocity.grad, 2 * velocity.detach())

    def test_current_contract_covers_extracted_training_helpers(self):
        import run_datamake_ddp_training as launcher
        for path in ("train/datamake_train_state.py", "train/datamake_lora_config.py",
                     "train/datamake_prefix_data.py"):
            self.assertIn(path, launcher.SOURCE_FILES)
            self.assertTrue((launcher.LANCE_ROOT / path).is_file())
        for name in ("train/datamake_lora_generation_train.py", "train/datamake_online_rollout_lora_train.py",
                     "train/datamake_stage2_lora_train.py"):
            self.assertFalse((launcher.LANCE_ROOT / name).exists())


if __name__ == "__main__":
    unittest.main()
