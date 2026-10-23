import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "cc_finalize_modular_outfit_pilot_v1.py"
SPEC = importlib.util.spec_from_file_location("modular_outfit_finalizer", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class ModularOutfitFinalizerTests(unittest.TestCase):
    def test_attaches_export_and_scene_object_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime_path = root / "runtime.json"
            cc_path = root / "cc.json"
            summary_path = root / "validation_result.json"
            fbx = root / "case.fbx"
            auto_json = root / "case.json"
            project = root / "case.ccProject"
            fbx.write_bytes(b"fbx")
            auto_json.write_bytes(b"json")
            project.write_bytes(b"project")
            case_result_path = root / "cases" / "CASE" / "result.json"
            runtime = {
                "pilot_id": "pilot",
                "status": "source_export_pending",
                "cases": [
                    {
                        "case_id": "CASE",
                        "case_role": "outfit_modules",
                        "planned_export": {
                            "fbx": str(fbx),
                            "json": str(auto_json),
                            "project": str(project),
                        },
                        "modules": [{"asset_id": "shirt"}],
                    }
                ],
            }
            write_json(runtime_path, runtime)
            write_json(cc_path, {"pilot_id": "pilot"})
            export = {
                "fbx": self._file_record(fbx),
                "json": self._file_record(auto_json),
                "fbm": {"file_count": 1},
                "textures": {"file_count": 0},
            }
            write_json(
                case_result_path,
                {
                    "case_id": "CASE",
                    "success": True,
                    "asset_applications": [
                        {
                            "asset_id": "shirt",
                            "cloth_options_policy": "fit_body_shape",
                            "dialogs": {"observed_dialogs": []},
                            "inventory_changes": {
                                "added": [
                                    {
                                        "collection": "GetClothes",
                                        "name": "shirt_mesh",
                                        "python_type": "RICloth",
                                    }
                                ]
                            },
                        }
                    ],
                    "assembled_inventory": {
                        "object_count": 1,
                        "objects": [
                            {"collection": "GetClothes", "name": "shirt_mesh"}
                        ],
                    },
                    "production_export": export,
                    "production_project": self._file_record(project),
                },
            )
            write_json(
                summary_path,
                {
                    "success": True,
                    "success_count": 1,
                    "failure_count": 0,
                    "results": [
                        {
                            "case_id": "CASE",
                            "success": True,
                            "result_path": str(case_result_path),
                        }
                    ],
                },
            )
            finalized = SUBJECT.finalize_manifest(runtime_path, cc_path, summary_path)
            self.assertEqual("cc_export_passed", finalized["status"])
            case = finalized["cases"][0]
            self.assertEqual("cc_export_passed", case["validation_status"])
            self.assertEqual(
                "shirt_mesh", case["modules"][0]["cc_scene_objects"][0]["name"]
            )
            self.assertEqual(SUBJECT.sha256_file(fbx), case["export"]["fbx"]["sha256"])

    @staticmethod
    def _file_record(path):
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": SUBJECT.sha256_file(path),
        }


if __name__ == "__main__":
    unittest.main()
