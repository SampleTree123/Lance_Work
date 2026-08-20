import importlib.util
import os
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_character_showcase_10_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_build_character_showcase_10_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CharacterShowcase10Tests(unittest.TestCase):
    def test_builds_one_unaged_high_resolution_character_per_bodyfit(self):
        document = MODULE.build(
            MODULE.DEFAULT_SOURCE_MANIFEST,
            MODULE.DEFAULT_BODY_LIBRARY,
            MODULE.DEFAULT_DECISIONS,
        )

        self.assertEqual(document["character_count"], 10)
        self.assertEqual(len(document["presets"]), 10)
        self.assertEqual(document["preview_capture_mode"], "render_image")
        self.assertEqual(document["preview_resolution"], [1024, 1024])
        self.assertTrue(document["save_character_projects"])
        self.assertEqual(
            {item["bodyfit_id"] for item in document["presets"]},
            {item[0] for item in MODULE.SHOWCASE_ROWS},
        )
        self.assertEqual(
            len({item["face_recipe_id"] for item in document["presets"]}),
            10,
        )
        self.assertTrue(
            all(item["age_label"] == "young" for item in document["presets"])
        )
        self.assertTrue(
            all(
                item["full_face_elder_weight"] == 0.0
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["showcase_provenance"]["unaged_showcase"]
                for item in document["presets"]
            )
        )
        by_bodyfit = {
            item["bodyfit_id"]: item for item in document["presets"]
        }
        self.assertTrue(
            by_bodyfit["M05_Short_Average"]["showcase_provenance"][
                "appearance_requires_visual_review"
            ]
        )
        self.assertTrue(
            by_bodyfit["F05_Short_Average"]["showcase_provenance"][
                "appearance_requires_visual_review"
            ]
        )

    def test_static_variant_avoids_pose_snapshot_reload(self):
        document = MODULE.build(
            MODULE.DEFAULT_SOURCE_MANIFEST,
            MODULE.DEFAULT_BODY_LIBRARY,
            MODULE.DEFAULT_DECISIONS,
            dynamic_poses=False,
        )

        self.assertEqual(
            document["library_id"],
            "cc_character_showcase_10_static_20260803_v1",
        )
        self.assertFalse(document["showcase_design"]["dynamic_pose_evidence"])
        self.assertTrue(
            all(
                item["appearance_validation_plan"]["pose_profile"] is None
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                "post_pose_eye_world_translation_tolerance_cm"
                not in item["appearance_validation_plan"]
                for item in document["presets"]
            )
        )


if __name__ == "__main__":
    unittest.main()
