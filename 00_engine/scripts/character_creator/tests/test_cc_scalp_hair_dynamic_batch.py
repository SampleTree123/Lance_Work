import importlib.util
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_scalp_hair_dynamic_batch_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_build_scalp_hair_dynamic_batch_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DynamicHairBatchTests(unittest.TestCase):
    def test_default_inputs_build_expected_dynamic_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "dynamic.json")
            document = MODULE.build(output_path=output)

        self.assertEqual(document["character_count"], 74)
        self.assertEqual(
            document["selection"]["base_case_count"],
            58,
        )
        self.assertEqual(
            document["selection"][
                "cross_presentation_case_count"
            ],
            16,
        )
        self.assertEqual(
            len({item["preset_id"] for item in document["presets"]}),
            74,
        )

        base = [
            item
            for item in document["presets"]
            if item["scalp_hair_dynamic_validation"]["case_phase"]
            == "base"
        ]
        cross = [
            item
            for item in document["presets"]
            if item["scalp_hair_dynamic_validation"]["case_phase"]
            == "cross_presentation"
        ]
        self.assertEqual(
            len(
                {
                    item["appearance_asset_ids"][0]
                    for item in base
                }
            ),
            58,
        )
        self.assertEqual(
            len(
                {
                    item["appearance_asset_ids"][0]
                    for item in cross
                }
            ),
            16,
        )
        self.assertEqual(
            {
                item["scalp_hair_dynamic_validation"]["motion_id"]
                for item in base
            },
            {"emote", "idle", "walk"},
        )
        self.assertEqual(
            {
                item["scalp_hair_dynamic_validation"]["motion_id"]
                for item in cross
            },
            {"walk"},
        )
        for item in base:
            metadata = item["scalp_hair_dynamic_validation"]
            score = metadata["female_presentation_score"]
            sex = item["sex"]
            if score < 0.5:
                self.assertEqual(sex, "male")
            elif score > 0.5:
                self.assertEqual(sex, "female")
            else:
                self.assertIn(sex, ("female", "male"))
            motion = item["appearance_validation_plan"][
                "hair_motion_validation"
            ]
            pacing = item["appearance_validation_plan"][
                "asset_load_pacing"
            ]["slots"]["scalp_hair"]
            self.assertEqual(pacing["before_seconds"], 8.0)
            self.assertEqual(pacing["after_seconds"], 12.0)
            self.assertTrue(os.path.isfile(motion["motion_path"]))
            self.assertTrue(os.path.isfile(motion["camera_path"]))


if __name__ == "__main__":
    unittest.main()
