import json
import pathlib
import unittest


SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
BATCH_PATH = SCRIPT_DIR / "cc_face_quality_batch_v3_validation.json"


class FaceQualityBatchV3Tests(unittest.TestCase):
    def test_repository_matrix_has_explicit_profile_and_real_materials(self):
        with BATCH_PATH.open("r", encoding="utf-8") as handle:
            batch = json.load(handle)

        self.assertEqual(
            batch["library_id"],
            "adult_face_v3_dynamic_validation_v2",
        )
        self.assertEqual(batch["character_count"], 25)
        self.assertEqual(
            batch["selection"]["primary_baseline_count"], 17
        )
        self.assertEqual(
            batch["selection"]["random_bodyfit_count"], 8
        )
        for preset in batch["presets"]:
            self.assertEqual(
                preset["source_facial_profile"]["application_mode"],
                "selected_avatar_content_load",
            )
            self.assertIn(
                preset["source_facial_profile"]["policy_binding"],
                ("default_by_sex", "seed_override"),
            )
            self.assertTrue(
                preset["source_facial_profile"]["path"]
                .lower()
                .endswith(".ccfacialprofile")
            )
            self.assertTrue(preset["source_head_preset"]["path"])
            self.assertTrue(preset["skin_asset_id"])
            self.assertTrue(preset["eye_asset_id"])
            self.assertEqual(
                preset["facial_assembly"]["asset_ids"],
                [
                    preset["skin_asset_id"],
                    preset["eye_asset_id"],
                ],
            )
            self.assertEqual(
                preset["facial_assembly"]["application_order"],
                [
                    "skin",
                    "age_morph",
                    "dynamic_wrinkle_profile",
                    "teeth",
                    "eyebrows",
                    "eyelashes",
                    "eyes_material_only",
                    "facial_hair",
                    "scalp_hair",
                    "shared_hair_pigmentation",
                ],
            )
            self.assertEqual(
                preset["full_face_elder_weight"], 0.0
            )
            self.assertEqual(
                preset["appearance_validation_plan"][
                    "face_camera_reference_top_z"
                ],
                {
                    "female": 166.9602508544922,
                    "male": 175.70965576171875,
                }[preset["sex"]],
            )


if __name__ == "__main__":
    unittest.main()
