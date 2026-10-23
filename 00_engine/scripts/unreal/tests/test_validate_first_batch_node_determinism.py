from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "validate_first_batch_node_determinism.py"
)
SPEC = importlib.util.spec_from_file_location(
    "validate_first_batch_node_determinism", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DifferenceMetricTests(unittest.TestCase):
    def test_frame_difference_reports_mad_changed_pixels_and_maximum(self) -> None:
        mad, changed, maximum = MODULE.frame_difference(
            bytes([0, 10, 20, 30]),
            bytes([0, 12, 30, 20]),
            pixel_delta=5,
        )

        self.assertEqual(mad, 5.5)
        self.assertEqual(changed, 2)
        self.assertEqual(maximum, 10)

    def test_percentile_uses_nearest_rank(self) -> None:
        values = [float(value) for value in range(1, 101)]

        self.assertEqual(MODULE.percentile(values, 0.95), 95.0)

    def test_empty_or_mismatched_frames_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "incompatible"):
            MODULE.frame_difference(b"", b"", pixel_delta=5)
        with self.assertRaisesRegex(RuntimeError, "incompatible"):
            MODULE.frame_difference(b"a", b"ab", pixel_delta=5)


if __name__ == "__main__":
    unittest.main()
