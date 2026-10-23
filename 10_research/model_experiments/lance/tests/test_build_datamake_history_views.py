from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT = (
    Path(__file__).parents[1] / "scripts" / "build_datamake_history_views.py"
)
SPEC = importlib.util.spec_from_file_location("datamake_history_views", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HistoryViewTest(unittest.TestCase):
    def setUp(self):
        self.row = {
            "sample_id": "sample-r3",
            "chain_id": "chain-a",
            "target_round": 3,
            "context_length": 3,
            "prompt_view": "dialogue",
            "prompts": ["p1", "p2", "p3"],
            "video_paths": ["v0.mp4", "v1.mp4", "v2.mp4", "v3.mp4"],
            "output_video_path": "v3.mp4",
        }
        self.rollout = {
            ("chain-a", 1): "/rollout/r1.mp4",
            ("chain-a", 2): "/rollout/r2.mp4",
        }

    def test_teacher_forced_keeps_all_paths(self):
        row, count = MODULE.replace_conditions(self.row, "teacher_forced", {})
        self.assertEqual(row["video_paths"], self.row["video_paths"])
        self.assertEqual(count, 0)
        self.assertTrue(row["direct_source_is_ground_truth"])

    def test_rollout_vit_only_replaces_old_history_not_direct_source(self):
        row, count = MODULE.replace_conditions(
            self.row, "rollout_vit_only", self.rollout
        )
        self.assertEqual(
            row["video_paths"],
            ["v0.mp4", "/rollout/r1.mp4", "v2.mp4", "v3.mp4"],
        )
        self.assertEqual(count, 1)
        self.assertTrue(row["direct_source_is_ground_truth"])

    def test_rollout_full_replaces_all_generated_conditions_not_target(self):
        row, count = MODULE.replace_conditions(self.row, "rollout_full", self.rollout)
        self.assertEqual(
            row["video_paths"],
            ["v0.mp4", "/rollout/r1.mp4", "/rollout/r2.mp4", "v3.mp4"],
        )
        self.assertEqual(count, 2)
        self.assertFalse(row["direct_source_is_ground_truth"])
        self.assertEqual(row["video_paths"][-1], self.row["video_paths"][-1])

    def test_missing_rollout_fails_closed(self):
        with self.assertRaisesRegex(KeyError, "missing rollout"):
            MODULE.replace_conditions(
                self.row,
                "rollout_full",
                {("chain-a", 1): "/rollout/r1.mp4"},
            )


if __name__ == "__main__":
    unittest.main()

