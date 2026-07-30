import importlib.util
import json
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_summarize_eyelash_v3_extreme_validation_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_summarize_eyelash_v3_extreme_validation_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EyelashV3ExtremeSummaryTests(unittest.TestCase):
    def test_structural_pass_is_summarized(self):
        with tempfile.TemporaryDirectory() as directory:
            batch_path = os.path.join(directory, "batch.json")
            artifact_root = os.path.join(directory, "artifacts")
            chunk_dir = os.path.join(artifact_root, "chunk_01")
            case_dir = os.path.join(chunk_dir, "EYLV3_01_M_M01")
            os.makedirs(case_dir)
            artifacts = {}
            for key in MODULE.REQUIRED_ARTIFACTS:
                path = os.path.join(case_dir, key + ".png")
                with open(path, "wb") as handle:
                    handle.write(b"image")
                artifacts[key] = path
            batch = {
                "presets": [
                    {
                        "appearance_asset_ids": ["EYELASH_A"],
                        "appearance_recipe": {
                            "assets": [
                                {"display_name": "Natural", "slot": "eyelashes"}
                            ]
                        },
                        "eyelash_v3_extreme": {
                            "face_index": 1,
                            "primary_seed_id": "M01",
                        },
                        "preset_id": "EYLV3_01_M_M01",
                        "sex": "male",
                    }
                ]
            }
            validation = {
                "results": [
                    {
                        "appearance_application": {
                            "steps": [
                                {
                                    "character_preset_verified": True,
                                    "eye_geometry_preserved": True,
                                    "eye_support_preserved": True,
                                    "slot": "eyelashes",
                                }
                            ]
                        },
                        "artifacts": artifacts,
                        "facial_pose_validation": {
                            "profile": "eyelash_visibility_v1"
                        },
                        "preset_id": "EYLV3_01_M_M01",
                        "success": True,
                    }
                ]
            }
            with open(batch_path, "w", encoding="utf-8") as handle:
                json.dump(batch, handle)
            with open(
                os.path.join(chunk_dir, "validation_result.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(validation, handle)

            summary = MODULE.build_summary(artifact_root, batch_path)

        self.assertEqual(summary["completed_case_count"], 1)
        self.assertEqual(summary["pending_case_count"], 0)
        self.assertEqual(
            summary["cases"][0]["automation_status"],
            "structural_pass_visual_pending",
        )
        self.assertTrue(summary["cases"][0]["structural_pass"])


if __name__ == "__main__":
    unittest.main()
