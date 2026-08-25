import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "build_first_batch_graph_source_v1.py"
SPEC = importlib.util.spec_from_file_location("first_batch_graph_source", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def fake_hash(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def source_file(bundle_id, relative_path):
    return {
        "local_path": rf"D:\fixture\{relative_path.replace('/', chr(92))}",
        "source_ref": f"bundle://{bundle_id}/{relative_path}",
        "bytes": 100,
        "sha256": fake_hash(relative_path),
    }


def make_inputs():
    bundle_id = "first_data_batch_fixture_v1"
    looks = []
    actions = []
    samples = []
    action_ids_by_sex = {}

    for sex, prefix in (("female", "F"), ("male", "M")):
        action_ids = [f"ACT_{prefix}{index:02d}" for index in range(1, 6)]
        action_ids_by_sex[sex] = action_ids
        for action_id in action_ids:
            action_path = f"motions/{sex}/{action_id}.fbx"
            actions.append(
                {
                    "action_id": action_id,
                    "sex": sex,
                    "actor_id": f"{prefix}02_Average",
                    "semantic_family": "fixture_motion",
                    "source_motion": source_file(
                        bundle_id, f"motion_sources/{sex}/{action_id}.rlMotion"
                    ),
                    "window": {
                        "start_seconds": 0.0,
                        "source_end_seconds": 5.0,
                        "source_duration_seconds": 5.0,
                        "production_duration_seconds": 5.0,
                        "padding_required_seconds": 0.0,
                        "padding_policy": "none",
                    },
                    "expected_export": source_file(bundle_id, action_path),
                    "root_motion_policy": "preserve_source_root_motion",
                    "root_motion_override_asset": None,
                    "face_policy": "replaceable",
                    "cc_export_status": "validated",
                }
            )

        look_index = 0
        for identity_index in range(1, 5):
            for outfit_index in range(1, 5):
                look_id = f"{prefix}_ID{identity_index:02d}_O{outfit_index:02d}"
                fbx = source_file(
                    bundle_id,
                    f"full_reference/{look_id}/CC_FB_{look_id}.fbx",
                )
                looks.append(
                    {
                        "look_id": look_id,
                        "sex": sex,
                        "bodyfit_id": f"{prefix}02_Average",
                        "identity_id": f"{prefix}_ID{identity_index:02d}",
                        "outfit_id": f"O{outfit_index:02d}",
                        "source_validated_look_id": f"fixture::{look_id}",
                        "fbx": fbx,
                        "cc_export_status": "validated",
                    }
                )
                action_id = action_ids[look_index % len(action_ids)]
                expression_name = ("Happy", "Angry", "Sad")[look_index % 3]
                samples.append(
                    {
                        "look_id": look_id,
                        "action_id": action_id,
                        "character_blueprint": f"/Game/Fixture/{look_id}/BP_{look_id}",
                        "character_blueprint_class": (
                            f"/Game/Fixture/{look_id}/BP_{look_id}.BP_{look_id}_C"
                        ),
                        "composite_animation": (
                            f"/Game/Fixture/{sex}/{action_id}_"
                            f"{expression_name}_Composite_v001"
                        ),
                    }
                )
                look_index += 1

    required = {
        "schema_version": "required_exports_v1",
        "batch_id": bundle_id,
        "full_reference_looks": looks,
        "actions": actions,
        "expressions": [
            {
                "expression_id": expression_id,
                "profile_sha256": fake_hash(expression_id),
                "asset_suffix": f"{expression_id.title()}_Dynamic_v001",
                "unreal_assets": {
                    "F02": f"/Game/Fixture/F02/{expression_id}",
                    "M02": f"/Game/Fixture/M02/{expression_id}",
                },
            }
            for expression_id in ("happy", "angry", "sad")
        ],
    }
    matrix = {
        "schema_version": "first_batch_local_render_matrix_v1",
        "unreal": {
            "source_map_package": "/Game/Fixture/Maps/Source",
            "staging_map_package": "/Game/Fixture/Maps/Staging",
            "source_sequence_package": "/Game/Fixture/Sequences/Source",
            "workspace_sequence_package": "/Game/Fixture/Sequences/Workspace",
            "render_preset": "/Game/Fixture/Render/MRQ_1440p30",
        },
        "render": {
            "resolution": [2560, 1440],
            "fps": 30,
            "duration_seconds": 5,
            "frame_count": 150,
            "image_sequence": "png",
            "video_codec": "h264",
        },
        "samples": samples,
    }
    return required, matrix


class FirstBatchGraphSourceTests(unittest.TestCase):
    def build(self, root, required=None, matrix=None):
        required, matrix = (
            (required, matrix) if required is not None else make_inputs()
        )
        root.mkdir(parents=True, exist_ok=True)
        required_path = root / "required.json"
        matrix_path = root / "matrix.json"
        required_path.write_text(json.dumps(required), encoding="utf-8")
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
        return SUBJECT.build_source_manifest(required_path, matrix_path)

    def test_builds_happy_only_frozen_source_contract(self):
        with tempfile.TemporaryDirectory() as raw:
            source = self.build(Path(raw))
            self.assertEqual("first_batch_source_manifest", source["manifest_type"])
            self.assertEqual(["happy"], source["expression_ids"])
            self.assertFalse(source["expression_policy"]["editable_feature"])
            self.assertEqual(32, len(source["looks"]))
            self.assertEqual(10, sum(map(len, source["actions_by_sex"].values())))
            self.assertEqual(37, len(source["assets"]))
            self.assertEqual(
                {"near", "far", "high", "side"},
                set(source["scene_binding"]["camera_ids"]),
            )
            self.assertEqual(150, source["render_profile"]["duration_frames"])
            self.assertEqual(
                {"width": 2560, "height": 1440},
                source["render_profile"]["resolution"],
            )
            self.assertTrue(
                all(
                    SUBJECT.is_portable_source_ref(asset["source_ref"])
                    for asset in source["assets"]
                )
            )

    def test_input_hashes_are_independent_of_json_line_endings(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            required, matrix = make_inputs()
            outputs = []
            for name, newline in (("lf", "\n"), ("crlf", "\r\n")):
                case = root / name
                case.mkdir()
                required_path = case / "required.json"
                matrix_path = case / "matrix.json"
                required_text = json.dumps(required, ensure_ascii=False, indent=2) + "\n"
                matrix_text = json.dumps(matrix, ensure_ascii=False, indent=2) + "\n"
                required_path.write_bytes(required_text.replace("\n", newline).encode("utf-8"))
                matrix_path.write_bytes(matrix_text.replace("\n", newline).encode("utf-8"))
                outputs.append(SUBJECT.build_source_manifest(required_path, matrix_path))

            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(
                "canonical_json_v1",
                outputs[0]["input_manifests"]["local_render_matrix"]["hash_mode"],
            )

    def test_rejects_windows_source_reference(self):
        with tempfile.TemporaryDirectory() as raw:
            required, matrix = make_inputs()
            required["full_reference_looks"][0]["fbx"]["source_ref"] = (
                r"D:\fixture\look.fbx"
            )
            with self.assertRaisesRegex(SUBJECT.GraphSourceError, "Unportable"):
                self.build(Path(raw), required, matrix)

    def test_normalizes_every_action_to_happy_composite(self):
        with tempfile.TemporaryDirectory() as raw:
            source = self.build(Path(raw))
            action_assets = [
                asset for asset in source["assets"] if asset["asset_type"] == "action"
            ]
            self.assertEqual(10, len(action_assets))
            for asset in action_assets:
                path = asset["constraints"]["happy_composite_animation"]
                self.assertIn("_Happy_Composite_", path)
                self.assertNotIn("_Angry_Composite_", path)
                self.assertNotIn("_Sad_Composite_", path)

    def test_same_inputs_produce_identical_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            required, matrix = make_inputs()
            first = self.build(root / "first", required, matrix)
            second = self.build(root / "second", required, matrix)
            self.assertEqual(first, second)

    def test_rejects_unvalidated_export_and_mismatched_looks(self):
        with tempfile.TemporaryDirectory() as raw:
            required, matrix = make_inputs()
            required["actions"][0]["cc_export_status"] = "pending"
            with self.assertRaises(SUBJECT.GraphSourceError):
                self.build(Path(raw) / "pending", required, matrix)

            required, matrix = make_inputs()
            matrix["samples"][0]["look_id"] = "UNKNOWN_LOOK"
            with self.assertRaises(SUBJECT.GraphSourceError):
                self.build(Path(raw) / "mismatch", required, matrix)


if __name__ == "__main__":
    unittest.main()
