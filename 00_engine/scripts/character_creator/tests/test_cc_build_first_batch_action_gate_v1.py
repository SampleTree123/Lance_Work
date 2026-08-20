import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "cc_build_first_batch_action_gate_v1.py"
SPEC = importlib.util.spec_from_file_location("first_batch_action_gate", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FirstBatchActionGateTests(unittest.TestCase):
    def make_fixture(self, root):
        source = root / "selected"
        source.mkdir()
        motions = []
        for index, spec in enumerate(SUBJECT.ACTION_SPECS, 1):
            path = source / spec["filename"]
            path.write_bytes(f"motion-{index}-{spec['action_id']}".encode("ascii"))
            motions.append(
                {
                    "motion_id": f"motion-{index:02d}",
                    "filename": spec["filename"],
                    "sex_hint": spec["sex"],
                    "production_status": "not_approved",
                    "package_name": "fixture",
                    "source_container_relative_path": "fixture.zip",
                    "member_path": f"fixture/{spec['filename']}",
                    "semantic_tags": [spec["semantic_family"]],
                    "dependency_class": "unknown",
                    "review_bucket": "contextual_standalone_review",
                }
            )
        inventory = root / "inventory.json"
        inventory.write_text(
            json.dumps({"inventory_id": "fixture-inventory", "motions": motions}),
            encoding="utf-8",
        )

        presets = []
        actors = []
        actor_source = root / "actor_source"
        actor_source.mkdir()
        actor_runtime = root / "actor_runtime"
        for actor_id, sex in (("F02_Average", "female"), ("M02_Average", "male")):
            project = actor_source / f"{actor_id}.ccProject"
            avatar = root / f"{actor_id}.ccAvatar"
            project.write_bytes(actor_id.encode("ascii"))
            avatar.write_bytes((actor_id + "-avatar").encode("ascii"))
            presets.append(
                {
                    "preset_id": actor_id,
                    "sex": sex,
                    "source_project": {
                        "path": str(project),
                        "bytes": project.stat().st_size,
                        "sha256": digest(project),
                    },
                    "base_avatar": {
                        "path": str(avatar),
                        "sha256": digest(avatar),
                    },
                }
            )
            actors.append(
                {
                    "bodyfit_id": actor_id,
                    "sex": sex,
                    "actor_binding_id": f"binding-{actor_id}",
                    "appearance_recipe_id": f"appearance-{actor_id}",
                    "source_project": {
                        "path": str(project),
                        "bytes": project.stat().st_size,
                        "sha256": digest(project),
                    },
                }
            )
        body = root / "body.json"
        body.write_text(
            json.dumps({"library_id": "fixture-body", "presets": presets}),
            encoding="utf-8",
        )
        work = root / "work.json"
        work.write_text(json.dumps({"actors": actors}), encoding="utf-8")
        camera = root / "camera.ccCam"
        lightroom = root / "light.ccLightroom"
        camera.write_bytes(b"camera")
        lightroom.write_bytes(b"lightroom")
        return {
            "source": source,
            "inventory": inventory,
            "body": body,
            "work": work,
            "runtime": root / "runtime",
            "actor_runtime": actor_runtime,
            "output": root / "output",
            "gate": root / "gate.json",
            "registry": root / "registry.json",
            "camera": camera,
            "lightroom": lightroom,
        }

    def build(self, fixture):
        return SUBJECT.build_first_batch_action_gate(
            fixture["source"],
            fixture["inventory"],
            fixture["body"],
            fixture["work"],
            fixture["runtime"],
            fixture["actor_runtime"],
            fixture["output"],
            fixture["gate"],
            fixture["registry"],
            fixture["camera"],
            fixture["lightroom"],
        )

    def test_builds_hash_locked_six_per_sex_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            result = self.build(fixture)
            gate = json.loads(fixture["gate"].read_text(encoding="utf-8"))
            registry = json.loads(
                fixture["registry"].read_text(encoding="utf-8")
            )
            self.assertEqual(12, gate["counts"]["motion_case_count"])
            self.assertEqual(60, gate["counts"]["expected_image_count"])
            self.assertTrue(gate["capture_policy"]["follow_root_for_capture"])
            self.assertEqual(6, registry["cardinality_contract"]["female_actions"])
            self.assertEqual(6, registry["cardinality_contract"]["male_actions"])
            self.assertEqual("not_approved", registry["production_status"])
            self.assertEqual(
                12,
                sum(
                    len(item["motion_cases"]) for item in gate["presets"]
                ),
            )
            self.assertTrue(
                Path(result["gate_config"]).samefile(fixture["gate"])
            )

    def test_rejects_unexpected_selected_motion(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            (fixture["source"] / "Unexpected.rlMotion").write_bytes(b"extra")
            with self.assertRaises(SUBJECT.FirstBatchActionBuildError):
                self.build(fixture)

    def test_rejects_inventory_sex_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            inventory = json.loads(fixture["inventory"].read_text(encoding="utf-8"))
            inventory["motions"][0]["sex_hint"] = "male"
            fixture["inventory"].write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            with self.assertRaises(SUBJECT.FirstBatchActionBuildError):
                self.build(fixture)

    def test_rejects_runtime_copy_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = self.make_fixture(Path(raw))
            self.build(fixture)
            staged = next((fixture["runtime"] / "motions").iterdir())
            staged.write_bytes(b"drift")
            with self.assertRaises(SUBJECT.FirstBatchActionBuildError):
                self.build(fixture)


if __name__ == "__main__":
    unittest.main()
