"""History-only control equivalence, graph boundary and seed contracts."""
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

ROOT = Path(__file__).parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "lance"), str(ROOT / "runtime/peft_0_15_2")]
import run_datamake_ddp_training as baseline
import run_datamake_pred_x0_ddp_training as launcher
from train import datamake_pred_x0_ddp_train as trainer
from train.datamake_pred_x0_prefix import make_history_row, history_seed, PredX0PrefixDataset
from train.datamake_stage2_lora_data import IndexedPrefixDataset

PROFILE = ROOT / "configs/datamake_coinve_mixed_ddp8_lora64_both_pred_x0_no_region_v1.json"


class PredX0Tests(unittest.TestCase):
    def test_only_history_semantics_change_and_control_hashes_remain_bound(self):
        control = baseline.load_profile(baseline.workspace_path(launcher.CONTROL_PROFILE))
        variant = launcher.load_profile(PROFILE)
        a, b = baseline.semantic_recipe(control), baseline.semantic_recipe(variant)
        self.assertEqual({k for k in a if a[k] != b[k]}, {"history"})
        before = baseline.make_contract(control)
        after = launcher.make_contract(variant)
        for path, digest in before["implementation_sha256"].items():
            self.assertEqual(digest, after["implementation_sha256"][path])
        self.assertTrue(any(name.endswith("train/datamake_flow_history.py")
                            for name in after["implementation_sha256"]))
        self.assertTrue(any(p.endswith("data/datamake_reference_image.py")
                            for p in after["implementation_sha256"]))
        self.assertEqual(variant["checkpoint"], control["checkpoint"])

    def test_reject_nonhistory_hyperparameter_change_even_when_recipe_matches(self):
        p = json.loads(PROFILE.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            recipe = deepcopy(p)
            recipe["run"]["run_name"] += "_recipe"
            recipe["wandb"]["run_id"] += "_recipe"
            p["optimization"]["learning_rate"] *= 2
            recipe["optimization"] = p["optimization"]
            ref = Path(tmp) / "recipe.json"
            ref.write_text(json.dumps(recipe))
            p["ddp"]["source_profile"] = str(ref)
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError, "Only history"):
                launcher.load_profile(path)

    def test_generated_history_replaces_all_previous_outputs_only(self):
        original = dict(sample_id="r5", chain_id="chain", target_round=5,
                        prompts=list("abcde"), video_paths=[f"v{i}" for i in range(6)])
        history = [torch.ones(3, 5, 2, 2) * i for i in range(4)]
        result = make_history_row(original, 5, history)
        self.assertEqual(result["video_inputs"][0], "v0")
        self.assertEqual(result["video_inputs"][-1], "v5")
        for i in range(4):
            self.assertIs(result["video_inputs"][i+1], history[i])
        self.assertEqual(result["video_paths"], original["video_paths"])
        with self.assertRaisesRegex(ValueError, "detached"):
            make_history_row(original, 2, [torch.ones(3, 5, 2, 2, requires_grad=True)])
        with self.assertRaises(ValueError):
            make_history_row(original, 5, history[:2])

    def test_r1_including_real_pairs_uses_exact_control_dataset(self):
        dataset = object.__new__(PredX0PrefixDataset)
        for origin in ("ue_synthetic", "coinve"):
            dataset.rows = [[dict(target_round=1, dataset_origin=origin)]]
            with patch.object(IndexedPrefixDataset, "__getitem__", return_value=object()) as original:
                self.assertIs(dataset[7], original.return_value)
                original.assert_called_once_with(7)

    def test_prefix_request_preserves_index_and_cycle_without_worker_gpu_work(self):
        dataset = object.__new__(PredX0PrefixDataset)
        dataset.rows = [[dict(target_round=3, video_paths=["a", "b", "c", "d"], sample_id="r3")]]
        dataset.seed = 2220
        dataset.source = SimpleNamespace(local_rank=7, _read_media_bytes=lambda path, cache: path.encode())
        request = dataset[2]["pred_x0_prefix_request"]
        self.assertEqual((request["microstep"], request["cycle"], request["row_index"]), (2, 2, 0))
        self.assertEqual(request["row"]["sample_id"], "r3")
        self.assertEqual(request, dataset[2]["pred_x0_prefix_request"])
        self.assertNotEqual(history_seed(request["seed"], 1), history_seed(request["seed"], 2))

    def test_official_flow_intermediates_decode_under_no_grad(self):
        parameter = torch.nn.Parameter(torch.tensor(2.0))
        seen = []

        def model(**kwargs):
            self.assertFalse(torch.is_grad_enabled())
            self.assertTrue(kwargs["return_flow_intermediates"])
            seen.append("model")
            return dict(flow_noisy_target=parameter * torch.ones(1, 3),
                        flow_pred_velocity=parameter * torch.ones(1, 3),
                        flow_timesteps=torch.tensor([.25]))

        def decode(latents):
            self.assertFalse(torch.is_grad_enabled())
            seen.append("vae")
            self.assertTrue(torch.equal(latents[0], torch.full((1, 1, 1, 3), 1.5)))
            return [latents[0].permute(3, 0, 1, 2) / 2]

        data = dict(patchified_vae_latent_shapes=[(1, 1, 1)], vae_data_mode="video", padded_videos=[])
        batch = SimpleNamespace(cuda=lambda device: SimpleNamespace(to_dict=lambda: data.copy()))
        with patch.object(trainer.control, "make_padded_latent", return_value=[]), patch("torch.autocast", return_value=nullcontext()):
            result = trainer.predict_history(batch, model, SimpleNamespace(vae_decode=decode), 0, False, "fixed")
        self.assertEqual(seen, ["model", "vae"])
        self.assertFalse(result.requires_grad)
        self.assertIsNone(result.grad_fn)
        self.assertIsNone(parameter.grad)
        self.assertEqual(result.dtype, torch.float16)
        self.assertTrue(torch.equal(result, torch.full((3, 1, 1, 1), .75)))


if __name__ == "__main__":
    unittest.main()
