import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "cc_build_first_batch_action_full_preview_v1.py"
SPEC = importlib.util.spec_from_file_location("full_preview_builder", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FullPreviewBuilderTests(unittest.TestCase):
    def test_replaces_sparse_sampling_without_mutating_source(self):
        source = {
            "diagnostic_mode": "animation_p0_dynamic_gate",
            "capture_policy": {"sample_normalized_positions": [0.0, 1.0]},
            "counts": {"sample_count_per_motion": 2, "expected_image_count": 2},
            "selection_override": {
                "dynamic_gate_still_required": True,
                "production_approval_granted": False,
            },
        }
        original = copy.deepcopy(source)
        result = MODULE.build(source, 6)
        self.assertEqual(source, original)
        self.assertEqual(result["capture_policy"]["sample_interval_frames"], 6)
        self.assertEqual(result["capture_policy"]["preview_fps"], 10.0)
        self.assertNotIn("sample_normalized_positions", result["capture_policy"])
        self.assertIsNone(result["counts"]["expected_image_count"])

    def test_rejects_invalid_interval(self):
        source = {
            "diagnostic_mode": "animation_p0_dynamic_gate",
            "capture_policy": {},
            "selection_override": {},
        }
        with self.assertRaises(ValueError):
            MODULE.build(source, 0)


if __name__ == "__main__":
    unittest.main()
