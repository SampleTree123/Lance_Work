from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import build_outfit_motion_stress_run as motion_portal  # noqa: E402


class OutfitMotionStressRunTests(unittest.TestCase):
    def _write_image(self, path: Path, color: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (24, 24), color).save(path)

    def _fixture(self, root: Path) -> tuple[dict, list[Path]]:
        case_id = "female.demo::default::F04_Heavy::motion_stress_v1"
        profiles = []
        validations = []
        for profile_id, color in (
            ("locomotion_walk", "#cc4455"),
            ("full_body_calibration", "#4488cc"),
        ):
            samples = []
            for index, position in enumerate((0.0, 0.2, 0.4, 0.6, 0.8)):
                image = root / "images" / profile_id / f"{index}.png"
                self._write_image(image, color)
                samples.append({"frame": index * 10, "image": str(image)})
            profiles.append(
                {
                    "profile_id": profile_id,
                    "purpose": f"purpose-{profile_id}",
                    "sample_normalized_positions": [0.0, 0.2, 0.4, 0.6, 0.8],
                }
            )
            validations.append(
                {"profile_id": profile_id, "samples": samples}
            )
        reference = root / "images" / "reference.png"
        self._write_image(reference, "#44cc88")
        case_result = root / "chunk_01" / "cases" / "d001" / "result.json"
        case_result.parent.mkdir(parents=True)
        case_result.write_text(
            json.dumps(
                {
                    "success": True,
                    "case_id": case_id,
                    "preset_id": "demo-preset",
                    "look_id": "female.demo::default",
                    "subject_id": "OUTFIT_F04_HEAVY",
                    "sex": "female",
                    "bodyfit_id": "F04_Heavy",
                    "captures": [
                        {
                            "view_id": "front_three_quarter",
                            "image": {"path": str(reference)},
                        }
                    ],
                    "motion_stress_validations": validations,
                }
            ),
            encoding="utf-8",
        )
        checkpoint = root / "chunk_01" / "validation_result.json"
        checkpoint.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "case_id": case_id,
                            "success": True,
                            "result_path": str(case_result),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        gate = {
            "counts": {"test_case_count": 1},
            "representative_looks": [
                {
                    "look_id": "female.demo::default",
                    "family_display_name": "Demo",
                    "group_id": "default",
                }
            ],
            "presets": [
                {
                    "case_id": case_id,
                    "preset_id": "demo-preset",
                    "motion_stress_profiles": profiles,
                }
            ],
        }
        return gate, [checkpoint]

    def test_builds_complete_eleven_image_case(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[3]) as temp:
            root = Path(temp)
            gate, validations = self._fixture(root)
            review = root / "review"
            run, index = motion_portal.build_run(gate, validations, review)
            self.assertEqual(run["status"], "pending_review")
            self.assertEqual(index["motion_image_count"], 10)
            self.assertEqual(len(next(iter(run["groups"].values()))["cases"][0]["images"]), 11)
            self.assertEqual(len(list((review / "sheets").glob("*.png"))), 1)

    def test_applies_spot_check_decision_without_claiming_exhaustive_review(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[3]) as temp:
            root = Path(temp)
            gate, validations = self._fixture(root)
            review = root / "review"
            decision_path = root / "decision.json"
            decision = {
                "review_scope": {
                    "review_method": "user_spot_check",
                    "reviewed_look_count": None,
                },
                "user_visual_review": {
                    "overall_status": "motion_stress_accepted_by_spot_check"
                },
            }
            decision_path.write_text(json.dumps(decision), encoding="utf-8")

            run, index = motion_portal.build_run(
                gate,
                validations,
                review,
                decision,
                decision_path,
            )

            self.assertEqual(run["status"], "approved")
            self.assertEqual(index["status"], "approved")
            self.assertEqual(index["machine_status"], "pending_review")
            self.assertEqual(index["visual_review_method"], "user_spot_check")
            self.assertIn("spot-check", run["decision"]["label"])
            self.assertIn("not 53 individual", run["decision"]["summary"])
            self.assertEqual(
                run["artifacts"][-1]["label"], "User motion review decision"
            )

    def test_discovers_nested_checkpoints_in_timestamp_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "chunk_01" / "validation_result.json"
            second = root / "chunk_02" / "validation_result.json"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("{}", encoding="utf-8")
            second.write_text("{}", encoding="utf-8")
            discovered = motion_portal.discover_validations(root)
            self.assertEqual(set(discovered), {first.resolve(), second.resolve()})


if __name__ == "__main__":
    unittest.main()
