import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_build_facial_hair_compatibility_batch_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_facial_hair_batch_test_subject", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class FacialHairBatchTests(unittest.TestCase):
    def test_builds_five_by_nine_male_matrix(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset_output = pathlib.Path(temporary) / "assets.json"
            batch_output = pathlib.Path(temporary) / "batch.json"
            result = SUBJECT.build(
                asset_catalog_output=str(asset_output),
                batch_output=str(batch_output),
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["asset_count"], 5)
            self.assertEqual(result["matrix_count"], 45)
            self.assertEqual(len(result["pilot_preset_ids"]), 5)

            with asset_output.open("r", encoding="utf-8") as handle:
                catalog = json.load(handle)
            with batch_output.open("r", encoding="utf-8") as handle:
                batch = json.load(handle)

            self.assertEqual(
                catalog["catalog_id"], SUBJECT.ASSET_CATALOG_ID
            )
            self.assertEqual(len(catalog["assets"]), 5)
            self.assertTrue(
                all(
                    "Reallusion Templates" in item["preferred_path"]
                    and item["slot"] == "facial_hair"
                    and item["asset_form"] == "group"
                    for item in catalog["assets"]
                )
            )

            presets = batch["presets"]
            self.assertEqual(len(presets), 45)
            self.assertEqual(
                len(
                    {
                        (
                            item["face_generation"][
                                "primary_seed_id"
                            ],
                            item["appearance_asset_ids"][0],
                        )
                        for item in presets
                    }
                ),
                45,
            )
            self.assertTrue(
                all(
                    item["sex"] == "male"
                    and item["appearance_validation_plan"][
                        "pose_profile"
                    ]
                    == SUBJECT.FACIAL_HAIR_PROFILE
                    for item in presets
                )
            )


if __name__ == "__main__":
    unittest.main()
