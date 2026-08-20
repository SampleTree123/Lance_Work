import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cc_build_p0_animation_ue_pilot_work_order_v1.py"
SPEC = importlib.util.spec_from_file_location("p0_ue_pilot", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class P0AnimationUEPilotWorkOrderTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        actors = []
        presets = []
        summaries = []
        for sex, bodyfit, character_id, recipe in (
            ("female", "F02_Average", "F_CHAR", "F_CASUAL"),
            ("male", "M02_Average", "M_CHAR", "M_CASUAL"),
        ):
            project = root / f"{character_id}.ccProject"
            project.write_bytes(character_id.encode("ascii"))
            actors.append(
                {
                    "actor_binding_id": f"actor_{sex}",
                    "sex": sex,
                    "bodyfit_id": bodyfit,
                    "character_id": character_id,
                    "appearance_recipe_id": recipe,
                    "saved_project": {
                        "path": str(project),
                        "bytes": project.stat().st_size,
                        "sha256": digest(project),
                    },
                }
            )
            presets.append(
                {
                    "character_id": character_id,
                    "sex": sex,
                    "bodyfit_id": bodyfit,
                    "appearance_recipe_id": recipe,
                    "appearance_recipe": {
                        "assets": [
                            {"slot": "upper", "asset_id": "u", "display_name": "U"},
                            {"slot": "lower", "asset_id": "l", "display_name": "L"},
                            {
                                "slot": "footwear",
                                "asset_id": "f",
                                "display_name": "F",
                            },
                        ]
                    },
                }
            )
            summaries.append(
                {
                    "character_id": character_id,
                    "project": {
                        "review_path": str(project),
                        "sha256": digest(project),
                    },
                }
            )

        roles = [
            ("female_root_motion_walk", "walk_f", "actor_female", "one_shot", "preserve_source_root_motion"),
            ("male_root_motion_walk", "walk_m", "actor_male", "one_shot", "preserve_source_root_motion"),
            ("in_place_loop", "idle_f", "actor_female", "loop_candidate", "in_place"),
            ("one_shot_gesture", "gesture_m", "actor_male", "one_shot", "in_place"),
        ]
        candidates = []
        motion_specs = []
        for gate_role, case_id, actor_id, temporal, root_policy in roles:
            motion = root / f"{case_id}.rlMotion"
            motion.write_bytes(case_id.encode("ascii"))
            candidates.append(
                {
                    "case_id": case_id,
                    "source_motion": {
                        "path": str(motion),
                        "bytes": motion.stat().st_size,
                        "sha256": digest(motion),
                    },
                    "motion_role": gate_role,
                    "temporal_usage": temporal,
                    "root_motion": {"policy": root_policy},
                    "facial_channels": "none",
                    "facial_reuse_policy": "replaceable",
                    "production_status": "not_approved",
                }
            )
            motion_specs.append(
                {
                    "gate_role": gate_role,
                    "case_id": case_id,
                    "actor_binding_id": actor_id,
                }
            )

        registry = {
            "registry_id": "registry",
            "status": "registered_pending_ue_runtime_validation",
            "counts": {"production_approved_count": 0},
            "candidates": candidates,
        }
        spec = {
            "source_registry_id": "registry",
            "character_policy": {
                "generated_clothed_characters_required": True,
                "gray_body_templates_forbidden": True,
                "required_appearance_slots": ["upper", "lower", "footwear"],
            },
            "actors": actors,
            "motion_cases": motion_specs,
            "export_root": str(root / "exports"),
            "unreal_destination": {"vendor_root": "/Game/Vendor"},
        }
        showcase = {"presets": presets}
        summary = {"status": "passed", "characters": summaries}
        paths = []
        for name, value in (
            ("registry.json", registry),
            ("spec.json", spec),
            ("showcase.json", showcase),
            ("summary.json", summary),
        ):
            path = root / name
            path.write_text(json.dumps(value), encoding="utf-8")
            paths.append(path)
        return paths

    def test_builds_clothed_two_actor_four_motion_work_order(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            value = SUBJECT.build_work_order(*paths)
            self.assertEqual("ready_for_cc_export", value["status"])
            self.assertEqual(2, value["scope"]["actor_count"])
            self.assertEqual(4, value["scope"]["motion_count"])
            self.assertTrue(value["scope"]["generated_clothed_characters_required"])
            self.assertEqual(0, value["scope"]["production_approved_count"])

    def test_rejects_unclothed_actor(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            showcase = json.loads(paths[2].read_text(encoding="utf-8"))
            showcase["presets"][0]["appearance_recipe"]["assets"] = []
            paths[2].write_text(json.dumps(showcase), encoding="utf-8")
            with self.assertRaises(SUBJECT.UEPilotWorkOrderError):
                SUBJECT.build_work_order(*paths)

    def test_rejects_saved_project_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            spec = json.loads(paths[1].read_text(encoding="utf-8"))
            Path(spec["actors"][0]["saved_project"]["path"]).write_bytes(b"drift")
            with self.assertRaises(SUBJECT.UEPilotWorkOrderError):
                SUBJECT.build_work_order(*paths)

    def test_rejects_loop_role_bound_to_one_shot(self):
        with tempfile.TemporaryDirectory() as raw:
            paths = self.make_fixture(Path(raw))
            registry = json.loads(paths[0].read_text(encoding="utf-8"))
            next(
                item for item in registry["candidates"] if item["case_id"] == "idle_f"
            )["temporal_usage"] = "one_shot"
            paths[0].write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(SUBJECT.UEPilotWorkOrderError):
                SUBJECT.build_work_order(*paths)


if __name__ == "__main__":
    unittest.main()
