import importlib.util
import json
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_summarize_scalp_hair_dynamic_validation_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_summarize_scalp_hair_dynamic_validation_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DynamicSummaryTests(unittest.TestCase):
    def test_motion_displacement_separates_active_parts(self):
        report = {
            "samples": [
                {
                    "hair_physics": {
                        "hair_parts": [
                            {
                                "bounds": {"center": [0.0, 0.0, 0.0]},
                                "id": "active",
                                "name": "Active",
                                "physics_active": True,
                            },
                            {
                                "bounds": {"center": [0.0, 0.0, 0.0]},
                                "id": "rigid",
                                "name": "Rigid",
                                "physics_active": False,
                            },
                        ]
                    }
                },
                {
                    "hair_physics": {
                        "hair_parts": [
                            {
                                "bounds": {"center": [0.0, 3.0, 4.0]},
                                "id": "active",
                                "name": "Active",
                                "physics_active": True,
                            },
                            {
                                "bounds": {"center": [1.0, 0.0, 0.0]},
                                "id": "rigid",
                                "name": "Rigid",
                                "physics_active": False,
                            },
                        ]
                    }
                },
            ]
        }
        result = MODULE.motion_displacement(report)
        self.assertEqual(
            result["active_part_max_center_displacement"],
            5.0,
        )
        self.assertEqual(
            result["all_part_max_center_displacement"],
            5.0,
        )

    def test_multiple_roots_reject_duplicate_results(self):
        with tempfile.TemporaryDirectory() as directory:
            batch_path = os.path.join(directory, "batch.json")
            roots = [
                os.path.join(directory, "first"),
                os.path.join(directory, "second"),
            ]
            preset = {
                "appearance_recipe": {"assets": []},
                "appearance_validation_plan": {},
                "preset_id": "DUPLICATE",
                "sex": "female",
            }
            with open(batch_path, "w", encoding="utf-8") as handle:
                json.dump({"presets": [preset]}, handle)
            for root in roots:
                os.makedirs(root)
                with open(
                    os.path.join(root, "validation_result.json"),
                    "w",
                    encoding="utf-8",
                ) as handle:
                    json.dump(
                        {
                            "results": [
                                {
                                    "preset_id": "DUPLICATE",
                                    "success": False,
                                }
                            ]
                        },
                        handle,
                    )
            with self.assertRaises(MODULE.SummaryError):
                MODULE.build_summary(roots, batch_path)


if __name__ == "__main__":
    unittest.main()
