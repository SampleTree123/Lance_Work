import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PILOT = load_module(
    "cc_build_p0_animation_pilot_v1",
    "cc_build_p0_animation_pilot_v1.py",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class P0AnimationPilotTests(unittest.TestCase):
    def make_fixture(self, root):
        source = root / "P0"
        source.mkdir()
        archive = source / "Everyday.zip"
        members = {
            "Walk/Walk_F.rlMotion": b"walk-current",
            "Idle/Idle_F.iMotion": b"idle-legacy",
            "Ignored/Phone.rlMotion": b"phone",
        }
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as output:
            for name, data in members.items():
                output.writestr(name, data)
        with zipfile.ZipFile(archive) as payload:
            infos = {item.filename: item for item in payload.infolist()}

        motions = []
        for index, (name, data) in enumerate(list(members.items())[:2], 1):
            info = infos[name]
            motions.append(
                {
                    "motion_id": f"motion-{index}",
                    "package_id": "package-1",
                    "package_name": "Everyday.zip",
                    "source_type": "archive_member",
                    "source_container_relative_path": "Everyday.zip",
                    "member_path": name,
                    "filename": pathlib.PurePosixPath(name).name,
                    "extension": pathlib.PurePosixPath(name).suffix.lower(),
                    "size": len(data),
                    "crc32": f"{info.CRC:08x}",
                    "sex_hint": "female",
                    "dependency_class": "standalone_candidate",
                    "dependency_hints": [],
                    "semantic_tags": ["locomotion" if index == 1 else "idle_pose"],
                    "review_bucket": "standalone_first",
                    "review_status": "not_reviewed",
                    "production_status": "not_approved",
                }
            )
        inventory = {
            "schema_version": 1,
            "inventory_id": "fixture-inventory",
            "source_root": str(source),
            "packages": [
                {
                    "package_id": "package-1",
                    "archives": [
                        {
                            "relative_path": "Everyday.zip",
                            "extension": ".zip",
                            "size": archive.stat().st_size,
                            "sha256": sha256(archive),
                            "status": "readable",
                        }
                    ],
                }
            ],
            "motions": motions,
        }
        spec = {
            "schema_version": 1,
            "pilot_id": "fixture-pilot",
            "source_inventory_id": "fixture-inventory",
            "selection_policy": {
                "minimum_case_count": 2,
                "maximum_case_count": 2,
                "required_review_bucket": "standalone_first",
                "require_unique_content": True,
            },
            "boundaries": [],
            "cases": [
                {
                    "case_id": "fixture_walk",
                    "motion_id": "motion-1",
                    "pilot_actor_preset_id": "F02_Average",
                    "review_family": "locomotion",
                    "loop_hint": "unknown",
                },
                {
                    "case_id": "fixture_idle",
                    "motion_id": "motion-2",
                    "pilot_actor_preset_id": "F02_Average",
                    "review_family": "idle",
                    "loop_hint": "candidate",
                },
            ],
        }
        inventory_path = root / "inventory.json"
        spec_path = root / "spec.json"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        return archive, inventory_path, spec_path

    def test_extracts_only_whitelisted_members_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive, inventory_path, spec_path = self.make_fixture(root)
            before = sha256(archive)
            output = root / "pilot"
            result = PILOT.build_pilot(inventory_path, spec_path, output)

            self.assertEqual(before, sha256(archive))
            self.assertEqual(2, result["counts"]["case_count"])
            self.assertEqual(0, result["counts"]["production_approved_count"])
            extracted = sorted((output / "motions").iterdir())
            self.assertEqual(2, len(extracted))
            self.assertEqual(
                {b"walk-current", b"idle-legacy"},
                {path.read_bytes() for path in extracted},
            )
            review = json.loads(
                (output / "dynamic_review.json").read_text(encoding="utf-8")
            )
            self.assertTrue(
                all(item["visual_decision"] == "pending" for item in review["cases"])
            )

    def test_rejects_non_standalone_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, inventory_path, spec_path = self.make_fixture(root)
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            inventory["motions"][0]["review_bucket"] = "dependency_review_later"
            inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
            with self.assertRaises(PILOT.PilotBuildError):
                PILOT.build_pilot(inventory_path, spec_path, root / "pilot")

    def test_rejects_byte_identical_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive, inventory_path, spec_path = self.make_fixture(root)
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as output:
                output.writestr("Walk/Walk_F.rlMotion", b"same")
                output.writestr("Idle/Idle_F.iMotion", b"same")
            with zipfile.ZipFile(archive) as payload:
                infos = {item.filename: item for item in payload.infolist()}
            inventory["packages"][0]["archives"][0].update(
                {
                    "size": archive.stat().st_size,
                    "sha256": sha256(archive),
                }
            )
            for motion in inventory["motions"]:
                info = infos[motion["member_path"]]
                motion["size"] = info.file_size
                motion["crc32"] = f"{info.CRC:08x}"
            inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
            with self.assertRaises(PILOT.PilotBuildError):
                PILOT.build_pilot(inventory_path, spec_path, root / "pilot")


if __name__ == "__main__":
    unittest.main()
