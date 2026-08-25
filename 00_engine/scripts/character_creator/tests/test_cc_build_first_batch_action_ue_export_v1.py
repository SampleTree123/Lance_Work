import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cc_build_first_batch_action_ue_export_v1.py"
SPEC = importlib.util.spec_from_file_location("first_batch_action_export", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)}


class FirstBatchActionExportBuilderTests(unittest.TestCase):
    def make_fixture(self, root):
        registry_actions = []
        review_cases = []
        for sex in ("female", "male"):
            for index in range(1, 7):
                action_id = f"ACT_{sex[0].upper()}{index:02d}_FIXTURE"
                motion = root / f"{action_id}.rlMotion"
                motion.write_bytes(action_id.encode("ascii"))
                registry_actions.append(
                    {
                        "action_id": action_id,
                        "sex": sex,
                        "semantic_family": "gesture",
                        "runtime_file": record(motion),
                    }
                )
                root_class = "moving_candidate" if index == 6 else "in_place_candidate"
                review_cases.append(
                    {
                        "case_id": action_id.lower(),
                        "load_status": "succeeded",
                        "facial_channel_class": "none_detected",
                        "hidden_dependencies": [],
                        "root_motion_class": root_class,
                        "automation_evidence": {
                            "root_motion_evidence": {
                                "first_to_last_horizontal_distance_cm": 20.0 if index == 6 else 1.0
                            }
                        },
                    }
                )
        registry = root / "registry.json"
        registry.write_text(
            json.dumps(
                {
                    "status": "frozen_pending_cc_and_ue_validation",
                    "actions": registry_actions,
                }
            ),
            encoding="utf-8",
        )
        review = root / "review.json"
        review.write_text(
            json.dumps(
                {
                    "status": "automation_complete_pending_visual_review",
                    "cases": review_cases,
                }
            ),
            encoding="utf-8",
        )
        windows = root / "windows.json"
        windows.write_text(
            json.dumps(
                {
                    "status": "frozen_ready_for_cc_export",
                    "actions": [
                        {
                            "action_id": action["action_id"],
                            "case_id": action["action_id"].lower(),
                            "source_motion": action["runtime_file"],
                            "window": {
                                "start_seconds": 0.0,
                                "source_end_seconds": 5.0,
                                "source_duration_seconds": 5.0,
                                "production_duration_seconds": 5.0,
                                "padding_required_seconds": 0.0,
                                "padding_policy": "none",
                            },
                        }
                        for action in registry_actions
                    ],
                }
            ),
            encoding="utf-8",
        )
        bridge = root / "bridge"
        bridge.mkdir()
        actors = []
        for sex, binding, character in (
            ("female", "p0_female_clothed", "F_CHAR"),
            ("male", "p0_male_clothed", "M_CHAR"),
        ):
            project = bridge / SUBJECT.BRIDGE_PROJECT_NAMES[sex]
            project.write_bytes(character.encode("ascii"))
            actors.append(
                {
                    "actor_binding_id": binding,
                    "character_id": character,
                    "sex": sex,
                    "bodyfit_id": "F02_Average" if sex == "female" else "M02_Average",
                    "appearance_recipe_id": f"{sex}_appearance",
                    "source_project": record(project),
                }
            )
        actor_work = root / "actors.json"
        actor_work.write_text(json.dumps({"actors": actors}), encoding="utf-8")
        return {
            "registry": registry,
            "review": review,
            "windows": windows,
            "actors": actor_work,
            "bridge": bridge,
            "work": root / "work_order.json",
            "config": root / "config.json",
            "staging": root / "staging",
            "final": root / "final",
        }

    def build(self, fixture):
        return SUBJECT.build_first_batch_action_export(
            fixture["registry"],
            fixture["review"],
            fixture["actors"],
            fixture["bridge"],
            fixture["work"],
            fixture["config"],
            fixture["staging"],
            fixture["final"],
            fixture["windows"],
        )

    def test_builds_two_actor_twelve_motion_export(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            result = self.build(fixture)
            work = json.loads(fixture["work"].read_text(encoding="utf-8"))
            config = json.loads(fixture["config"].read_text(encoding="utf-8"))
            self.assertEqual(12, result["motion_count"])
            self.assertEqual(12, work["scope"]["motion_count"])
            self.assertEqual(2, work["scope"]["root_motion_counts"]["moving_candidate"])
            self.assertEqual(12, len(config["animation_p0_ue_export"]["export_names"]["motions"]))
            self.assertEqual("not_approved", work["production_status"])
            self.assertEqual(
                "frozen_five_second_window", work["motions"][0]["temporal_usage"]
            )
            self.assertEqual(5.0, work["motions"][0]["window"]["production_duration_seconds"])

    def test_rejects_hidden_dependency(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            review = json.loads(fixture["review"].read_text(encoding="utf-8"))
            review["cases"][0]["hidden_dependencies"] = ["cup"]
            fixture["review"].write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaises(SUBJECT.FirstBatchActionExportBuildError):
                self.build(fixture)

    def test_rejects_action_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            registry = json.loads(fixture["registry"].read_text(encoding="utf-8"))
            Path(registry["actions"][0]["runtime_file"]["path"]).write_bytes(b"drift")
            with self.assertRaises(SUBJECT.FirstBatchActionExportBuildError):
                self.build(fixture)

    def test_merges_successful_delta_review(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            base = json.loads(fixture["review"].read_text(encoding="utf-8"))
            replaced = base["cases"][0]
            base["cases"][0] = {"case_id": replaced["case_id"], "load_status": "not_run"}
            fixture["review"].write_text(json.dumps(base), encoding="utf-8")
            delta = Path(raw) / "delta.json"
            delta.write_text(
                json.dumps(
                    {
                        "status": "automation_complete_pending_visual_review",
                        "cases": [replaced],
                    }
                ),
                encoding="utf-8",
            )
            result = SUBJECT.build_first_batch_action_export(
                fixture["registry"],
                [fixture["review"], delta],
                fixture["actors"],
                fixture["bridge"],
                fixture["work"],
                fixture["config"],
                fixture["staging"],
                fixture["final"],
                fixture["windows"],
            )
            self.assertEqual(12, result["motion_count"])

    def test_rejects_frozen_window_source_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            windows = json.loads(fixture["windows"].read_text(encoding="utf-8"))
            windows["actions"][0]["source_motion"]["sha256"] = "0" * 64
            fixture["windows"].write_text(json.dumps(windows), encoding="utf-8")
            with self.assertRaises(SUBJECT.FirstBatchActionExportBuildError):
                self.build(fixture)


if __name__ == "__main__":
    unittest.main()
