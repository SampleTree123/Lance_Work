import importlib.util
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_scalp_hair_static_pressure_batch_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_build_scalp_hair_static_pressure_batch_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StaticPressureBatchTests(unittest.TestCase):
    def test_default_inputs_build_expected_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "pressure.json")
            document = MODULE.build(output_path=output)

        self.assertEqual(document["character_count"], 64)
        self.assertEqual(len(document["presets"]), 64)
        self.assertEqual(
            len(document["selection"]["asset_ids"]),
            16,
        )
        self.assertEqual(
            len(document["selection"]["primary_seed_ids"]),
            4,
        )
        self.assertEqual(
            len({item["preset_id"] for item in document["presets"]}),
            64,
        )

        combinations = {
            (
                item["appearance_asset_ids"][0],
                item["face_generation"]["primary_seed_id"],
            )
            for item in document["presets"]
        }
        self.assertEqual(len(combinations), 64)
        self.assertTrue(
            all(
                item["appearance_validation_plan"]["pose_profile"]
                == MODULE.SCALP_HAIR_PROFILE
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"][
                    "asset_load_pacing"
                ]["slots"]["scalp_hair"]
                == {
                    "after_seconds": 12.0,
                    "before_seconds": 8.0,
                }
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["scalp_hair_static_pressure"][
                    "presentation_mode"
                ]
                == "technical_cross_sex_allowed"
                for item in document["presets"]
            )
        )


if __name__ == "__main__":
    unittest.main()
