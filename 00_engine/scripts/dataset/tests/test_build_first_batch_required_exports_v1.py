import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "build_first_batch_required_exports_v1.py"
SPEC = importlib.util.spec_from_file_location("first_batch_required_exports", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_asset(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": str(path),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def make_fixture(root):
    look_rows = []
    audit_rows = []
    for sex, prefix in (("female", "F"), ("male", "M")):
        for index in range(1, 17):
            look_id = f"{prefix}_ID{index:02d}_O{index:02d}"
            look_rows.append(
                {
                    "look_id": look_id,
                    "sex": sex,
                    "bodyfit_id": f"{prefix}02_Average",
                    "identity_id": f"{prefix}_ID{index:02d}",
                    "outfit_id": f"O{index:02d}",
                    "source_validated_look_id": f"fixture.{look_id}",
                    "outfit_asset_override_id": None,
                }
            )
            project = write_asset(root / "projects" / f"{look_id}.ccProject", look_id.encode())
            fbx = write_asset(root / "full_reference" / look_id / f"{look_id}.fbx", b"fbx-" + look_id.encode())
            material_json = write_asset(
                root / "full_reference" / look_id / f"{look_id}.json",
                b"json-" + look_id.encode(),
            )
            texture = root / "full_reference" / look_id / f"{look_id}.fbm" / "texture.png"
            texture.parent.mkdir(parents=True, exist_ok=True)
            texture.write_bytes(b"texture")
            audit_rows.append(
                {
                    "look_id": look_id,
                    "passed": True,
                    "project": project,
                    "fbx": fbx,
                    "json": material_json,
                    "fbm_file_count": 1,
                    "fbm_total_bytes": len(b"texture"),
                }
            )

    look_config = root / "look_config.json"
    look_audit = root / "look_audit.json"
    write_json(look_config, {"look_rows": look_rows})
    write_json(
        look_audit,
        {
            "status": "passed",
            "summary": {
                "expected_look_count": 32,
                "passed_count": 32,
                "failed_count": 0,
            },
            "rows": audit_rows,
        },
    )

    registry_rows = []
    window_rows = []
    for sex, prefix in (("female", "F"), ("male", "M")):
        for index in range(1, 7):
            action_id = (
                "ACT_F02_CATCH_BREATH"
                if sex == "female" and index == 2
                else f"ACT_{prefix}{index:02d}_FIXTURE"
            )
            source = write_asset(
                root / "motions" / sex / f"{action_id}.rlMotion",
                action_id.encode(),
            )
            registry_rows.append(
                {
                    "action_id": action_id,
                    "sex": sex,
                    "actor_id": f"{prefix}02_Average",
                    "semantic_family": "fixture",
                    "runtime_file": {
                        "path": source["path"],
                        "size_bytes": source["bytes"],
                        "sha256": source["sha256"],
                    },
                }
            )
            window_rows.append(
                {
                    "action_id": action_id,
                    "source_motion": source,
                    "window": {
                        "start_seconds": 0.0,
                        "source_end_seconds": 5.0,
                        "source_duration_seconds": 5.0,
                        "production_duration_seconds": 5.0,
                        "padding_required_seconds": 0.0,
                        "padding_policy": "none",
                    },
                }
            )

    action_registry = root / "action_registry.json"
    action_pool = root / "action_pool.json"
    action_windows = root / "action_windows.json"
    write_json(
        action_registry,
        {
            "status": "frozen_pending_cc_and_ue_validation",
            "actions": registry_rows,
        },
    )
    write_json(
        action_windows,
        {"status": "frozen_ready_for_cc_export", "actions": window_rows},
    )
    write_json(
        action_pool,
        {
            "status": "frozen_for_first_batch_local_and_server_render",
            "active_actions": {
                "female": [
                    "ACT_F01_FIXTURE",
                    "ACT_F02_CATCH_BREATH",
                    "ACT_F03_FIXTURE",
                    "ACT_F04_FIXTURE",
                    "ACT_F05_FIXTURE",
                ],
                "male": [f"ACT_M{index:02d}_FIXTURE" for index in range(1, 6)],
            },
            "root_motion_policy": {
                "default": "preserve_source_root_motion",
                "overrides": {
                    "ACT_F02_CATCH_BREATH": {
                        "policy": "approved_in_place_override",
                        "ue_asset": "/Game/Fixture/F02_InPlace",
                    }
                },
            },
            "expression_policy": {
                "rendered_variation": True,
                "editable_feature": False,
                "edit_axis": None,
            },
        },
    )

    expression_profile = root / "expression_profile.json"
    write_json(
        expression_profile,
        {
            "profile_id": "fixture_expressions",
            "status": "frozen_for_ue_pilot",
            "duration_seconds": 3.0,
            "actors": [
                {"actor_id": "F02", "target_folder": "/Game/Fixture/F02"},
                {"actor_id": "M02", "target_folder": "/Game/Fixture/M02"},
            ],
            "expressions": [
                {"expression_id": "happy", "asset_suffix": "Happy"},
                {"expression_id": "angry", "asset_suffix": "Angry"},
                {"expression_id": "sad", "asset_suffix": "Sad"},
            ],
        },
    )
    return {
        "look_config": look_config,
        "look_audit": look_audit,
        "action_registry": action_registry,
        "action_pool": action_pool,
        "action_windows": action_windows,
        "expression_profile": expression_profile,
        "audit_rows": audit_rows,
    }


class FirstBatchRequiredExportsTests(unittest.TestCase):
    def build(self, root, fixture):
        output = root / "required_exports.json"
        manifest = SUBJECT.build_required_exports(
            fixture["look_config"],
            fixture["look_audit"],
            fixture["action_registry"],
            fixture["action_pool"],
            fixture["action_windows"],
            fixture["expression_profile"],
            output,
            root / "exports" / "motions",
        )
        return output, manifest

    def test_builds_locked_32_10_3_manifest(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output, manifest = self.build(root, make_fixture(root))
            self.assertTrue(output.is_file())
            self.assertEqual(
                {
                    "full_reference_looks": 32,
                    "action_assets": 10,
                    "female_actions": 5,
                    "male_actions": 5,
                    "expression_assets": 3,
                },
                manifest["counts"],
            )
            self.assertEqual(7, len(manifest["pending_runtime_bindings"]))
            self.assertTrue(
                manifest["full_reference_looks"][0]["fbx"]["source_ref"].startswith(
                    "bundle://first_data_batch_20260820_v1/"
                )
            )
            self.assertEqual("pending", manifest["actions"][0]["cc_export_status"])
            self.assertFalse(manifest["expression_policy"]["editable_feature"])

    def test_v4_registry_locks_all_exported_motion_fbxs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = make_fixture(root)
            registry = json.loads(
                fixture["action_registry"].read_text(encoding="utf-8")
            )
            registry["status"] = (
                "frozen_pending_replacement_window_and_ue_validation"
            )
            for action in registry["actions"]:
                basename = SUBJECT.export_basename(action["action_id"])
                action["export_fbx"] = write_asset(
                    root / "exports" / "motions" / action["sex"] / f"{basename}.fbx",
                    (action["action_id"] + "-fbx").encode(),
                )
            write_json(fixture["action_registry"], registry)

            _, manifest = self.build(root, fixture)

            self.assertEqual(
                "frozen_sources_ready_for_unreal_import",
                manifest["status"],
            )
            self.assertTrue(
                all(
                    action["cc_export_status"] == "validated"
                    for action in manifest["actions"]
                )
            )
            self.assertTrue(
                all("sha256" in action["expected_export"] for action in manifest["actions"])
            )

    def test_v4_registry_rejects_missing_export_lock(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = make_fixture(root)
            registry = json.loads(
                fixture["action_registry"].read_text(encoding="utf-8")
            )
            registry["status"] = (
                "frozen_pending_replacement_window_and_ue_validation"
            )
            write_json(fixture["action_registry"], registry)

            with self.assertRaisesRegex(SUBJECT.RequiredExportsError, "export FBX lock"):
                self.build(root, fixture)

    def test_rejects_audited_file_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = make_fixture(root)
            Path(fixture["audit_rows"][0]["project"]["path"]).write_bytes(b"changed")
            with self.assertRaisesRegex(SUBJECT.RequiredExportsError, "drifted"):
                self.build(root, fixture)

    def test_rejects_action_registry_window_id_mismatch(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = make_fixture(root)
            windows = json.loads(fixture["action_windows"].read_text(encoding="utf-8"))
            windows["actions"][0]["action_id"] = "ACT_F99_WRONG"
            write_json(fixture["action_windows"], windows)
            with self.assertRaisesRegex(
                SUBJECT.RequiredExportsError,
                "Active action is missing from windows",
            ):
                self.build(root, fixture)


if __name__ == "__main__":
    unittest.main()
