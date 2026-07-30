import importlib.util
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_dynamic_wrinkle_age_batch_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_build_dynamic_wrinkle_age_batch_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DynamicWrinkleAgeBatchTests(unittest.TestCase):
    def test_default_inputs_build_expected_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "wrinkles.json")
            document = MODULE.build(output_path=output)

        self.assertEqual(document["character_count"], 6)
        self.assertEqual(len(document["presets"]), 6)
        self.assertEqual(
            len({item["preset_id"] for item in document["presets"]}),
            6,
        )
        self.assertEqual(
            {
                (item["sex"], item["age_label"])
                for item in document["presets"]
            },
            {
                ("female", "young"),
                ("female", "middle"),
                ("female", "older"),
                ("male", "young"),
                ("male", "middle"),
                ("male", "older"),
            },
        )
        self.assertEqual(
            {
                item["full_face_elder_weight"]
                for item in document["presets"]
            },
            {0.0, 0.5, 1.0},
        )
        self.assertTrue(
            all(
                item["dynamic_wrinkle_strength"] == 1.0
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["facial_assembly"]["application_order"]
                == MODULE.FACIAL_ASSEMBLY_ORDER
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                "hair_color" not in item["facial_assembly"]
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"][
                    "dynamic_wrinkle_validation"
                ]["baseline_strength"]
                == 0.0
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"][
                    "dynamic_wrinkle_validation"
                ]["target_strength"]
                == 1.0
                for item in document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"][
                    "asset_load_pacing"
                ]["slots"]["skin"]
                == {
                    "after_seconds": 10.0,
                    "before_seconds": 4.0,
                }
                for item in document["presets"]
            )
        )


if __name__ == "__main__":
    unittest.main()
