import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cc_build_p0_animation_dynamic_gate_v1.py"
SPEC = importlib.util.spec_from_file_location("p0_dynamic_gate", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class P0AnimationDynamicGateTests(unittest.TestCase):
    def make_fixture(self, root):
        camera = root / "camera.ccCam"
        lightroom = root / "light.ccLightroom"
        camera.write_bytes(b"camera")
        lightroom.write_bytes(b"lightroom")
        body_presets = []
        cases = []
        review_cases = []
        for actor_id, sex in (
            ("F02_Average", "female"),
            ("M02_Average", "male"),
        ):
            project = root / f"{actor_id}.ccProject"
            base = root / f"{actor_id}.ccAvatar"
            project.write_bytes(actor_id.encode("ascii"))
            base.write_bytes((actor_id + "base").encode("ascii"))
            body_presets.append(
                {
                    "preset_id": actor_id,
                    "sex": sex,
                    "source_project": {
                        "path": str(project),
                        "bytes": project.stat().st_size,
                        "sha256": digest(project),
                    },
                    "base_avatar": {
                        "path": str(base),
                        "sha256": digest(base),
                    },
                }
            )
            for index in range(5):
                case_id = f"case_{sex}_{index}"
                motion = root / f"{case_id}.rlMotion"
                motion.write_bytes(case_id.encode("ascii"))
                cases.append(
                    {
                        "case_id": case_id,
                        "motion_id": f"motion_{case_id}",
                        "filename": motion.name,
                        "source_format": ".rlmotion",
                        "format_generation": "current",
                        "pilot_actor_preset_id": actor_id,
                        "review_family": "fixture",
                        "loop_hint": "unknown",
                        "semantic_tags": [],
                        "extracted_file": {
                            "path": str(motion),
                            "size_bytes": motion.stat().st_size,
                            "sha256": digest(motion),
                        },
                        "production_status": "not_approved",
                    }
                )
                review_cases.append(
                    {
                        "case_id": case_id,
                        "visual_decision": "pending",
                    }
                )
        manifest = {
            "pilot_id": "fixture-pilot",
            "status": "extracted_pending_cc_dynamic_review",
            "validation": {
                "success": True,
                "all_extracted_files_unique": True,
            },
            "cases": cases,
        }
        review = {
            "pilot_id": "fixture-pilot",
            "status": "not_started",
            "cases": review_cases,
        }
        body = {"library_id": "body-fixture", "presets": body_presets}
        manifest_path = root / "manifest.json"
        review_path = root / "review.json"
        body_path = root / "body.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        review_path.write_text(json.dumps(review), encoding="utf-8")
        body_path.write_text(json.dumps(body), encoding="utf-8")
        return manifest_path, review_path, body_path, camera, lightroom

    def test_builds_two_actor_hash_locked_gate_without_approval(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            document = SUBJECT.build_gate(*fixture)
            self.assertEqual("animation_p0_dynamic_gate", document["diagnostic_mode"])
            self.assertEqual(10, document["counts"]["motion_case_count"])
            self.assertEqual(50, document["counts"]["expected_image_count"])
            self.assertEqual(0, document["counts"]["production_approved_count"])
            self.assertEqual(
                {"F02_Average", "M02_Average"},
                {item["preset_id"] for item in document["presets"]},
            )
            self.assertTrue(
                all(
                    case["production_status"] == "not_approved"
                    for preset in document["presets"]
                    for case in preset["motion_cases"]
                )
            )
            capture = document["capture_policy"]
            self.assertEqual("lightroom_current", capture["camera_mode"])
            self.assertIsNone(capture["yaw_degrees"])
            self.assertFalse(capture["auto_frame_full_body"])
            self.assertTrue(capture["align_motion_start_to_source"])

    def test_rejects_motion_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            manifest = json.loads(fixture[0].read_text(encoding="utf-8"))
            Path(manifest["cases"][0]["extracted_file"]["path"]).write_bytes(
                b"changed"
            )
            with self.assertRaises(SUBJECT.DynamicGateBuildError):
                SUBJECT.build_gate(*fixture)

    def test_builds_case_filtered_recovery_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            document = SUBJECT.build_gate(
                *fixture,
                selected_case_ids=["case_female_0", "case_male_0"],
                library_id="fixture-recovery",
            )
            self.assertEqual("fixture-recovery", document["library_id"])
            self.assertEqual(2, document["counts"]["motion_case_count"])
            self.assertEqual(10, document["counts"]["expected_image_count"])
            self.assertEqual(
                {"case_female_0", "case_male_0"},
                {
                    case["case_id"]
                    for preset in document["presets"]
                    for case in preset["motion_cases"]
                },
            )

    def test_builds_single_actor_recovery_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            document = SUBJECT.build_gate(
                *fixture,
                selected_case_ids=["case_male_0"],
                library_id="fixture-male-recovery",
            )
            self.assertEqual(1, document["counts"]["motion_case_count"])
            self.assertEqual(5, document["counts"]["expected_image_count"])
            self.assertEqual(
                ["M02_Average"],
                [preset["preset_id"] for preset in document["presets"]],
            )

    def test_records_explicit_capture_yaw(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            document = SUBJECT.build_gate(*fixture, yaw_degrees=90.0)
            self.assertEqual(90.0, document["capture_policy"]["yaw_degrees"])

    def test_records_lightroom_camera_with_preserved_source_transform(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            document = SUBJECT.build_gate(
                *fixture,
                yaw_degrees=None,
                camera_mode="lightroom_current",
                auto_frame_full_body=False,
            )
            capture = document["capture_policy"]
            self.assertEqual("lightroom_current", capture["camera_mode"])
            self.assertIsNone(capture["yaw_degrees"])
            self.assertFalse(capture["auto_frame_full_body"])
            self.assertEqual(
                "preserve_lightroom_camera_and_source_transform",
                capture["framing"],
            )

    def test_rejects_unknown_camera_mode(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            with self.assertRaises(SUBJECT.DynamicGateBuildError):
                SUBJECT.build_gate(*fixture, camera_mode="unknown")

    def test_rejects_non_finite_capture_yaw(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            with self.assertRaises(SUBJECT.DynamicGateBuildError):
                SUBJECT.build_gate(*fixture, yaw_degrees=float("nan"))

    def test_rejects_inherited_production_approval(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            manifest = json.loads(fixture[0].read_text(encoding="utf-8"))
            manifest["cases"][0]["production_status"] = "approved"
            fixture[0].write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(SUBJECT.DynamicGateBuildError):
                SUBJECT.build_gate(*fixture)


if __name__ == "__main__":
    unittest.main()
