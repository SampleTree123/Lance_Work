import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_videos_framewise.py"
SPEC = importlib.util.spec_from_file_location("compare_videos_framewise", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CompareVideosFramewiseTest(unittest.TestCase):
    def test_identical_frames_have_zero_error(self):
        frame = np.full((32, 48, 3), 127, dtype=np.uint8)
        report = MODULE.compare_frames([frame, frame], [frame, frame, frame])
        self.assertEqual(report["mean_mse"], 0)
        self.assertEqual(report["mean_l1"], 0)
        self.assertEqual(report["mean_ssim_luma"], 1)

    def test_temporal_indexes_include_both_endpoints(self):
        self.assertEqual(MODULE.normalized_indexes(5, 3), [0, 2, 4])


if __name__ == "__main__":
    unittest.main()
