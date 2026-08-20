import importlib.util
import pathlib
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_compile_character_manifest.py"
)
SPEC = importlib.util.spec_from_file_location(
    "cc_compile_character_manifest_under_test",
    MODULE_PATH,
)
SUBJECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUBJECT)


class CharacterManifestV3Tests(unittest.TestCase):
    def test_v3_character_contains_only_primary_and_local_face_fields(self):
        body = {
            "base_avatar": {"path": "base.ccAvatar"},
            "body_and_junction_fingerprint": "body-fingerprint",
            "body_class": "average",
            "preset_id": "M02_Average",
            "sex": "male",
            "source_project": {"path": "body.ccProject"},
            "target_body_morphs": [],
            "target_junction_morphs": [],
        }
        face = {
            "face_recipe_id": "MFACEV3_0001",
            "local_morph_fingerprint": "local-fingerprint",
            "local_morphs": [
                {
                    "baseline_weight": 0.0,
                    "id": "local_eye_width",
                    "weight": 0.2,
                }
            ],
            "pipeline": SUBJECT.COMPLETE_PRIMARY_FACE_PIPELINE,
            "primary_face_seed_id": "M01_Aaron",
            "sex": "male",
            "source_head_preset": {
                "path": "Aaron.ccAvatarPreset",
                "sha256": "a" * 64,
            },
            "source_facial_profile": {
                "application_mode": (
                    SUBJECT.FACIAL_PROFILE_APPLICATION_MODE
                ),
                "path": "Aaron.ccFacialProfile",
                "policy_binding": "seed_override",
                "sha256": "b" * 64,
            },
            "strength_tier": "normal",
        }
        appearance = {
            "appearance_asset_ids": [],
            "appearance_recipe_id": "none",
            "validation_preset_id": "none",
        }
        bodyfit_proportion_adjustment = {
            "application_order": ["head_scale", "neck_height"],
            "decision_set_id": "adult_head_bodyfit_scale_v1",
            "targets": [
                {
                    "id": "head_scale",
                    "role": "head_scale",
                    "target": 0.1,
                },
                {
                    "id": "neck_height",
                    "role": "neck_height",
                    "target": -0.2,
                },
            ],
        }

        result = SUBJECT.compiled_character(
            {"character_id": "CHAR_0001"},
            body,
            face,
            appearance,
            {},
            bodyfit_proportion_adjustment=(
                bodyfit_proportion_adjustment
            ),
        )

        self.assertEqual(
            result["face_generation"],
            {
                "pipeline": SUBJECT.COMPLETE_PRIMARY_FACE_PIPELINE,
                "primary_seed_id": "M01_Aaron",
                "strength_tier": "normal",
            },
        )
        self.assertEqual(
            result["local_face_morphs"], face["local_morphs"]
        )
        self.assertEqual(
            result["local_morph_fingerprint"], "local-fingerprint"
        )
        self.assertEqual(
            result["source_facial_profile"],
            face["source_facial_profile"],
        )
        self.assertNotIn("target_face_morphs", result)
        self.assertNotIn("target_face_fingerprint", result)
        self.assertEqual(
            result["bodyfit_proportion_adjustment"],
            bodyfit_proportion_adjustment,
        )
        self.assertIsNot(
            result["bodyfit_proportion_adjustment"],
            bodyfit_proportion_adjustment,
        )


if __name__ == "__main__":
    unittest.main()
