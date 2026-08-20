import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cc_build_p0_animation_candidate_registry_v1.py"
SPEC = importlib.util.spec_from_file_location("p0_candidate_registry", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class P0AnimationCandidateRegistryTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        cases = []
        evidence_cases = []
        policies = []
        accepted = []
        for index in range(16):
            case_id = f"fixture_case_{index:02d}"
            motion = root / f"{case_id}.rlMotion"
            motion.write_bytes(case_id.encode("ascii"))
            moving = index < 7
            cases.append(
                {
                    "case_id": case_id,
                    "motion_id": f"motion_{index:02d}",
                    "filename": motion.name,
                    "source_format": ".rlmotion",
                    "pilot_actor_preset_id": (
                        "F02_Average" if index < 8 else "M02_Average"
                    ),
                    "extracted_file": {
                        "path": str(motion),
                        "size_bytes": motion.stat().st_size,
                        "sha256": digest(motion),
                    },
                }
            )
            evidence_cases.append(
                {
                    "case_id": case_id,
                    "motion_length_frames": 120 + index,
                    "facial_channel_class": "none_detected",
                    "recomputed_root_evidence": {
                        "classification": (
                            "moving_candidate" if moving else "in_place_candidate"
                        ),
                        "first_to_last_horizontal_distance_cm": (
                            100.0 if moving else 0.0
                        ),
                    },
                }
            )
            loop = index in {7, 8, 9}
            policies.append(
                {
                    "case_id": case_id,
                    "motion_role": "fixture",
                    "sex_preference": "unisex",
                    "temporal_usage": "loop_candidate" if loop else "one_shot",
                    "root_motion_policy": (
                        "preserve_source_root_motion" if moving else "in_place"
                    ),
                    "facial_reuse_policy": "replaceable",
                    "known_limits": [],
                }
            )
            accepted.append(case_id)

        pilot = {
            "pilot_id": "cc_p0_animation_dynamic_pilot_20260817_v1",
            "cases": cases,
        }
        evidence = {
            "success": True,
            "failure_count": 0,
            "production_approved_count": 0,
            "visual_review_status": "accepted",
            "cases": evidence_cases,
        }
        gate = root / "gate.json"
        source_validation = root / "validation.json"
        gate.write_text("{}", encoding="utf-8")
        source_validation.write_text("{}", encoding="utf-8")
        decision = {
            "review_scope": {
                "gate_manifest": {"path": str(gate), "sha256": digest(gate)},
                "source_validations": [
                    {
                        "path": str(source_validation),
                        "sha256": digest(source_validation),
                    }
                ],
            },
            "user_visual_review": {
                "overall_status": "all_16_visual_quality_accepted",
                "accepted_case_ids": accepted,
            },
            "scope_boundary": {
                "allows_candidate_registry_work_to_start": True,
                "approves_motions_as_production_assets": False,
            },
        }
        policy = {
            "source_pilot_id": "cc_p0_animation_dynamic_pilot_20260817_v1",
            "cases": policies,
        }

        paths = []
        for name, value in (
            ("pilot.json", pilot),
            ("evidence.json", evidence),
            ("decision.json", decision),
            ("policy.json", policy),
        ):
            path = root / name
            path.write_text(json.dumps(value), encoding="utf-8")
            paths.append(path)
        return paths

    def test_builds_registered_candidate_set_without_production_approval(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            result = SUBJECT.build_registry(*paths)
            self.assertEqual(16, result["counts"]["candidate_count"])
            self.assertEqual(3, result["counts"]["loop_candidate_count"])
            self.assertEqual(16, result["counts"]["replaceable_face_count"])
            self.assertEqual(0, result["counts"]["production_approved_count"])
            self.assertTrue(
                all(
                    item["production_status"] == "not_approved"
                    for item in result["candidates"]
                )
            )

    def test_rejects_motion_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            pilot = json.loads(paths[0].read_text(encoding="utf-8"))
            Path(pilot["cases"][0]["extracted_file"]["path"]).write_bytes(b"drift")
            with self.assertRaises(SUBJECT.CandidateRegistryError):
                SUBJECT.build_registry(*paths)

    def test_rejects_root_policy_conflict(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            policy = json.loads(paths[3].read_text(encoding="utf-8"))
            policy["cases"][0]["root_motion_policy"] = "in_place"
            paths[3].write_text(json.dumps(policy), encoding="utf-8")
            with self.assertRaises(SUBJECT.CandidateRegistryError):
                SUBJECT.build_registry(*paths)

    def test_rejects_visual_decision_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            decision = json.loads(paths[2].read_text(encoding="utf-8"))
            Path(decision["review_scope"]["gate_manifest"]["path"]).write_text(
                "changed", encoding="utf-8"
            )
            with self.assertRaises(SUBJECT.CandidateRegistryError):
                SUBJECT.build_registry(*paths)


if __name__ == "__main__":
    unittest.main()
