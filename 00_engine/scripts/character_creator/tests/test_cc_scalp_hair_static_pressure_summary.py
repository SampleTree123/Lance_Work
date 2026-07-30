import importlib.util
import json
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_summarize_scalp_hair_static_pressure_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_summarize_scalp_hair_static_pressure_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ScalpHairStaticPressureSummaryTests(unittest.TestCase):
    def test_structural_pass_is_summarized(self):
        with tempfile.TemporaryDirectory() as directory:
            batch_path = os.path.join(directory, "batch.json")
            artifact_root = os.path.join(directory, "artifacts")
            chunk_dir = os.path.join(artifact_root, "chunk_01")
            case_dir = os.path.join(chunk_dir, "HAIRPRESS_01_M_M01")
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
                        "appearance_asset_ids": ["HAIR_A"],
                        "appearance_recipe": {
                            "assets": [
                                {"display_name": "Mullet", "slot": "scalp_hair"}
                            ]
                        },
                        "preset_id": "HAIRPRESS_01_M_M01",
                        "scalp_hair_static_pressure": {
                            "face_index": 1,
                            "primary_seed_id": "M01",
                            "silhouette_family": "mullet",
                        },
                        "sex": "male",
                    }
                ]
            }
            validation = {
                "results": [
                    {
                        "appearance_morph_policy": {
                            "status": "accepted"
                        },
                        "artifacts": artifacts,
                        "preset_id": "HAIRPRESS_01_M_M01",
                        "reconstruction_matches_library": True,
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
