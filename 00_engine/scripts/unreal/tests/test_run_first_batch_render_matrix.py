from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "run_first_batch_render_matrix.py"
SPEC = importlib.util.spec_from_file_location("run_first_batch_render_matrix", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sequence_report(*, force_custom_mode: bool) -> dict:
    return {
        "force_custom_mode_required": force_custom_mode,
        "animation_binding_type": "native_actor_binding",
        "target_actor": "CC_FB_F_ID01_O01_Blueprint_LiveLink_C_1",
        "animation_sections": [
            {"force_custom_mode": force_custom_mode} for _ in range(4)
        ],
    }


class PoseDriverContractTests(unittest.TestCase):
    def test_accepts_explicit_custom_mode_on_all_sections(self) -> None:
        contract = MODULE.pose_driver_contract(
            sequence_report(force_custom_mode=True)
        )

        self.assertTrue(contract["passed"])
        self.assertTrue(all(contract["checks"].values()))

    def test_rejects_sequence_that_can_fall_back_to_t_pose(self) -> None:
        contract = MODULE.pose_driver_contract(
            sequence_report(force_custom_mode=False)
        )

        self.assertFalse(contract["passed"])
        self.assertFalse(contract["checks"]["force_custom_mode_required"])
        self.assertFalse(contract["checks"]["all_sections_force_custom_mode"])


class ResumeValidationTests(unittest.TestCase):
    ROW = {
        "sample_id": "FB32_001_F_ID01_O01",
        "look_id": "F_ID01_O01",
        "action_id": "ACT_F01_SEXY_DANCE",
        "start_frame_inclusive": 0,
        "end_frame_exclusive": 150,
    }

    def write_report(self, folder: Path, *, pose_passed: bool) -> None:
        video = folder / "sample.mp4"
        video.write_bytes(b"not-empty")
        report = {
            "status": "passed",
            "frame_count": 150,
            "resolution": [2560, 1440],
            "fps": 30,
            "start_frame_inclusive": 0,
            "end_frame_exclusive": 150,
            "video": str(video),
            "automation_contract": {
                "sample_id": self.ROW["sample_id"],
                "look_id": self.ROW["look_id"],
                "action_id": self.ROW["action_id"],
                "pose_driver_contract": {"passed": pose_passed},
                "temporal_motion_contract": {"passed": pose_passed},
            },
        }
        (folder / "render_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

    def test_resume_accepts_matching_pose_safe_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.write_report(folder, pose_passed=True)

            self.assertIsNotNone(MODULE.valid_render(folder, self.ROW))

    def test_resume_rejects_legacy_output_without_pose_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.write_report(folder, pose_passed=False)

            self.assertIsNone(MODULE.valid_render(folder, self.ROW))

    def test_resume_rejects_output_without_temporal_motion_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.write_report(folder, pose_passed=True)
            report_path = folder / "render_report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            del report["automation_contract"]["temporal_motion_contract"]
            report_path.write_text(json.dumps(report), encoding="utf-8")

            self.assertIsNone(MODULE.valid_render(folder, self.ROW))


class TemporalMotionContractTests(unittest.TestCase):
    def write_frames(self, folder: Path, *, moving: bool) -> None:
        for index in range(150):
            value = 255 if moving and index == 75 else 0
            Image.new("L", (16, 16), value).save(folder / f"frame_{index:04d}.png")

    def test_rejects_static_frame_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.write_frames(folder, moving=False)

            self.assertFalse(MODULE.temporal_motion_contract(folder)["passed"])

    def test_accepts_visible_temporal_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            self.write_frames(folder, moving=True)

            self.assertTrue(MODULE.temporal_motion_contract(folder)["passed"])


if __name__ == "__main__":
    unittest.main()
