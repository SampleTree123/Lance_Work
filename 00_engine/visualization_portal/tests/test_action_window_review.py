from __future__ import annotations

import json
import unittest
from pathlib import Path


LANCE_ROOT = Path(__file__).resolve().parents[3]
PORTAL_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_full_preview"
    / "review_20260820_v2_5s"
    / "action_window_manifest.json"
)
V3_REVIEW_ROOT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_full_preview"
    / "review_20260820_v3_5s"
)
V4_REVIEW_ROOT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_replacements"
    / "review_20260821_v4_5s_full"
)


class ActionWindowReviewTests(unittest.TestCase):
    def test_v2_manifest_has_twelve_fixed_five_second_actions(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cases = manifest["cases"]

        self.assertEqual(manifest["window_duration_seconds"], 5.0)
        self.assertEqual(len(cases), 12)
        self.assertEqual(sum(case["sex"] == "female" for case in cases), 6)
        self.assertEqual(sum(case["sex"] == "male" for case in cases), 6)
        self.assertEqual(len({case["action_id"] for case in cases}), 12)

        for case in cases:
            video_path = Path(case["video"]["path"])
            self.assertTrue(video_path.is_file(), case["action_id"])
            self.assertEqual(len(case["video"]["sha256"]), 64)
            self.assertGreater(case["source_window_duration_seconds"], 0)
            self.assertLessEqual(case["source_window_duration_seconds"], 5.0)
            self.assertGreaterEqual(case["recommended_start_seconds"], 0)
            self.assertLessEqual(
                case["recommended_start_seconds"]
                + case["source_window_duration_seconds"],
                case["video"]["duration_seconds"] + 0.001,
            )

    def test_selector_exposes_precise_persistent_export(self) -> None:
        html = (PORTAL_ROOT / "action-window-review.html").read_text(encoding="utf-8")
        source = (PORTAL_ROOT / "assets" / "action-window-review.js").read_text(
            encoding="utf-8"
        )

        for control_id in (
            "windowStart",
            "windowStartNumber",
            "previewWindow",
            "confirmWindow",
            "confirmAndNext",
            "exportJson",
        ):
            self.assertIn(f'id="{control_id}"', html)

        self.assertNotIn("3 秒", html)
        self.assertIn("localStorage", source)
        self.assertIn("source_video_sha256", source)
        self.assertIn("production_window_duration_seconds", source)
        self.assertIn("padding_required_seconds", source)
        self.assertIn('waitForVideoEvent("seeked")', source)
        self.assertIn('params.get("selection")', source)
        self.assertIn("source_video_sha256 !== item.video.sha256", source)
        self.assertIn("locked: true", source)

    def test_v3_review_reuses_ten_confirmed_windows_and_leaves_two_pending(self) -> None:
        manifest = json.loads(
            (V3_REVIEW_ROOT / "action_window_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        seed = json.loads(
            (V3_REVIEW_ROOT / "selection_seed_10_of_12.json").read_text(
                encoding="utf-8"
            )
        )
        cases = {item["action_id"]: item for item in manifest["cases"]}

        self.assertEqual(manifest["review_id"], "first_batch_action_windows_20260820_v3_5s")
        self.assertEqual(len(cases), 12)
        self.assertEqual(seed["confirmed_count"], 10)
        self.assertEqual(len(seed["selections"]), 10)
        self.assertEqual(
            set(manifest["reuse_provenance"]["newly_captured_action_ids"]),
            {"ACT_F02_CATCH_BREATH", "ACT_M04_LIVING_ROOM_SWING"},
        )
        for decision in seed["selections"]:
            case = cases[decision["action_id"]]
            self.assertTrue(decision["confirmed"])
            self.assertEqual(decision["case_id"], case["case_id"])
            self.assertEqual(decision["source_filename"], case["source_filename"])
            self.assertEqual(decision["source_video_sha256"], case["video"]["sha256"])

    def test_v4_review_reuses_nine_windows_and_leaves_three_replacements_pending(self) -> None:
        manifest = json.loads(
            (V4_REVIEW_ROOT / "action_window_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        seed = json.loads(
            (V4_REVIEW_ROOT / "action_window_seed_selection.json").read_text(
                encoding="utf-8"
            )
        )
        cases = {item["action_id"]: item for item in manifest["cases"]}

        self.assertEqual(
            manifest["review_id"],
            "first_batch_action_windows_20260821_v4_5s",
        )
        self.assertEqual(len(cases), 12)
        self.assertEqual(seed["confirmed_count"], 9)
        self.assertEqual(len(seed["selections"]), 9)
        self.assertEqual(
            set(manifest["reuse_provenance"]["newly_captured_action_ids"]),
            {
                "ACT_F01_SEXY_DANCE",
                "ACT_M01_BATTLE_DANCE",
                "ACT_M06_CHEER_HANDS_STEP_DANCE",
            },
        )
        for action_id, case in cases.items():
            self.assertTrue(Path(case["video"]["path"]).is_file(), action_id)
        for decision in seed["selections"]:
            case = cases[decision["action_id"]]
            self.assertTrue(decision["confirmed"])
            self.assertEqual(decision["case_id"], case["case_id"])
            self.assertEqual(decision["source_filename"], case["source_filename"])
            self.assertEqual(decision["source_video_sha256"], case["video"]["sha256"])


if __name__ == "__main__":
    unittest.main()
