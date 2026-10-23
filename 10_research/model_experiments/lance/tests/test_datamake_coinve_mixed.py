import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

ROOT = Path(__file__).parents[1]
sys.path[:0] = [str(ROOT / "lance"), str(ROOT / "scripts")]
from data.datasets_factory.dataset_datamake_mixed_v2v_local import (
    CROP_POLICY, DataMakeMixedV2VLocalIterableDataset, crop_frame_indices,
)
from build_datamake_coinve_mixed_data import fixed_crop_start
from test_datamake_multiturn_dataset import make_dataset, write_videos


class MixedDataTest(unittest.TestCase):
    def test_mismatched_full_lengths_use_same_window(self):
        # source 13.54s, target 8.38s: both must stay near [2,7), not
        # independently sample the full clips, which would end at 13.5/8.33s.
        source = crop_frame_indices(325, 24.0, 2.0)
        target = crop_frame_indices(201, 24.0, 2.0)
        self.assertEqual(source, target)
        self.assertEqual((len(source), source[0], source[-1]), (61, 48, 167))

    def test_native_fps_quantization_and_duration_boundary(self):
        a = np.array(crop_frame_indices(450, 30, 1.374)) / 30
        b = np.array(crop_frame_indices(201, 23.98, 1.374)) / 23.98
        self.assertLess(float(np.max(np.abs(a-b))), 2 / 23.98)
        self.assertEqual(len(crop_frame_indices(120, 24, 0)), 61)
        with self.assertRaises(ValueError):
            crop_frame_indices(120, 24, 0.01)

    def test_frozen_start_reproducible_and_in_common_range(self):
        a = fixed_crop_start("coinve-0", 8.38, 42)
        self.assertEqual(a, fixed_crop_start("coinve-0", 8.38, 42))
        self.assertGreaterEqual(a, 0)
        self.assertLessEqual(a + 5, 8.38)
        self.assertEqual(fixed_crop_start("coinve-0", 5, 42), 0)
        with self.assertRaises(ValueError):
            fixed_crop_start("short", 4.99, 42)

    def test_pair_roles_frames_and_no_state_leak_into_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_videos(root, 2)
            dataset = make_dataset(root)
            # Retain the real inherited row processor with tiny spatial transforms.
            del dataset.get_video_tensor
            dataset.__class__ = DataMakeMixedV2VLocalIterableDataset
            dataset.transform = lambda frames: torch.zeros(3, len(frames), 8, 8)
            dataset._read_decord = lambda reader, indices: list(indices)
            row = dict(sample_id="coinve-test", chain_id="coinve-test", target_round=1,
                prompts=["1. Add a hat. 2. Replace the background."],
                video_paths=["videos/0.mp4", "videos/1.mp4"], dataset_origin="coinve",
                crop_policy=CROP_POLICY, crop_start_seconds=2.0, crop_duration_seconds=5.0)
            class Reader:
                def __init__(self, path, **kwargs):
                    self.length = 325 if path.endswith("0.mp4") else 201
                def __len__(self): return self.length
                def get_avg_fps(self): return 24.0
            with patch("data.datasets_factory.dataset_datamake_mixed_v2v_local.decord.VideoReader", Reader):
                sample = dataset._process_row(row, 0, 0, 0, 0, "test")
            self.assertEqual([t.shape[1] for t in sample["video_tensor_list"]], [62, 61, 61])
            self.assertEqual([p.get("datamake_edit_role") for p in sample["sequence_plan"]
                              if p["type"] == "vae_video"], ["source", "target"])
            self.assertEqual(sum(p["loss"] for p in sample["sequence_plan"]), 1)
            self.assertFalse(hasattr(dataset, "_paired_window"))
            self.assertFalse(hasattr(dataset, "_paired_frames"))
            synthetic = {**row, "dataset_origin": "ue_synthetic", "crop_policy": None}
            from data.datasets_factory.dataset_datamake_multiturn_v2v_local import DataMakeMultiTurnV2VLocalIterableDataset
            with patch.object(DataMakeMultiTurnV2VLocalIterableDataset, "_process_row", return_value="legacy") as old:
                self.assertEqual(dataset._process_row(synthetic, 0, 0, 0, 0, "test"), "legacy")
                self.assertEqual(old.call_args.args[0], synthetic)


if __name__ == "__main__":
    unittest.main()
