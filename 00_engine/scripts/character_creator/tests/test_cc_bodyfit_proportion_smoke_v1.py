import importlib.util
import os
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_bodyfit_proportion_smoke_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_build_bodyfit_proportion_smoke_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BodyFitProportionSmokeTests(unittest.TestCase):
    def test_production_manifest_builds_six_lightweight_cases(self):
        source = MODULE.read_json(MODULE.DEFAULT_SOURCE)
        document = MODULE.build(source)

        self.assertEqual(len(document["presets"]), 6)
        self.assertEqual(
            document["diagnostic_mode"],
            "bodyfit_proportion_smoke_matrix",
        )
        by_bodyfit = {}
        for preset in document["presets"]:
            by_bodyfit.setdefault(preset["bodyfit_id"], []).append(preset)
            self.assertNotIn("facial_assembly", preset)
            self.assertNotIn("appearance_asset_ids", preset)
            self.assertEqual(
                preset["appearance_validation_plan"]["domain"],
                "bodyfit_proportion",
            )
            self.assertNotIn(
                "pose_profile",
                preset["appearance_validation_plan"],
            )
            self.assertIsInstance(
                preset["appearance_validation_plan"][
                    "face_camera_reference_top_z"
                ],
                float,
            )
            self.assertEqual(
                preset["bodyfit_proportion_adjustment"][
                    "application_order"
                ],
                ["head_scale", "neck_height"],
            )
        self.assertEqual(set(by_bodyfit), set(MODULE.TARGET_BODYFITS))
        for cases in by_bodyfit.values():
            self.assertEqual(len(cases), 2)
            self.assertEqual(
                len({item["face_recipe_id"] for item in cases}),
                2,
            )
            self.assertEqual(
                len(
                    {
                        item["face_generation"]["primary_seed_id"]
                        for item in cases
                    }
                ),
                2,
            )


if __name__ == "__main__":
    unittest.main()
