import importlib.util
import os
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR, "cc_build_first_batch_identity_library_v1.py"
)
SPEC = importlib.util.spec_from_file_location("first_batch_identity_builder", MODULE_PATH)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class FirstBatchIdentityLibraryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = builder.build(
            builder.DEFAULT_SOURCE_MANIFEST,
            builder.DEFAULT_BODY_LIBRARY,
            builder.DEFAULT_DECISIONS,
        )

    def test_frozen_identity_and_bodyfit_counts(self):
        presets = self.document["presets"]
        self.assertEqual(8, len(presets))
        self.assertEqual(4, sum(item["sex"] == "female" for item in presets))
        self.assertEqual(4, sum(item["sex"] == "male" for item in presets))
        self.assertEqual(
            {"F02_Average", "M02_Average"},
            {item["bodyfit_id"] for item in presets},
        )

    def test_identity_contract(self):
        presets = self.document["presets"]
        self.assertEqual(8, len({item["face_recipe_id"] for item in presets}))
        self.assertTrue(self.document["save_character_projects"])
        self.assertTrue(all(item["age_label"] == "young" for item in presets))
        self.assertTrue(
            all(item["full_face_elder_weight"] == 0.0 for item in presets)
        )
        self.assertEqual(
            [row[0] for row in builder.IDENTITY_ROWS],
            [item["preset_id"] for item in presets],
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"]["pose_profile"] is None
                for item in presets
            )
        )


if __name__ == "__main__":
    unittest.main()
