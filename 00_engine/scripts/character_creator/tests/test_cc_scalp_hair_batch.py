import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_build_scalp_hair_compatibility_batch_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_scalp_hair_batch_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class ScalpHairBatchTests(unittest.TestCase):
    def test_builds_sixty_by_two_matrix_with_user_prior(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset_output = pathlib.Path(temporary) / "assets.json"
            batch_output = pathlib.Path(temporary) / "batch.json"
            result = SUBJECT.build(
                asset_catalog_output=str(asset_output),
                batch_output=str(batch_output),
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["asset_count"], 60)
            self.assertEqual(result["matrix_count"], 120)
            self.assertEqual(result["female_primary_prior_count"], 45)
            self.assertEqual(result["male_primary_prior_count"], 15)

            with asset_output.open("r", encoding="utf-8") as handle:
                catalog = json.load(handle)
            with batch_output.open("r", encoding="utf-8") as handle:
                batch = json.load(handle)

            assets = catalog["assets"]
            self.assertEqual(len(assets), 60)
            self.assertEqual(
                len(
                    {
                        item["selected_source"]["sha256"]
                        for item in assets
                    }
                ),
                60,
            )
            self.assertTrue(
                all(
                    item["slot"] == "scalp_hair"
                    and item["asset_form"] == "group"
                    and item["preferred_path"].endswith(
                        (".rlHair", ".rlhair")
                    )
                    for item in assets
                )
            )
            self.assertTrue(
                all(
                    any(
                        variant["path"] == item["preferred_path"]
                        for variant in item["variants"]
                    )
                    for item in assets
                )
            )
            migrated = [
                item for item in assets if item.get("path_migration")
            ]
            self.assertEqual(len(migrated), 20)
            self.assertTrue(
                all(
                    item["hair_builder_pack"]["pack_id"]
                    == "hair_builder_3_edgy"
                    and item["path_migration"][
                        "stable_asset_id_preserved"
                    ]
                    is True
                    for item in migrated
                )
            )

            samurai = next(
                item
                for item in assets
                if item["display_name"] == "Top knot samurai"
            )
            self.assertEqual(
                samurai["presentation_prior"]["label"],
                "male_primary",
            )
            egirl = [
                item
                for item in assets
                if item["hair_builder_pack"]["pack_id"]
                == "hair_builder_2_egirl"
            ]
            self.assertEqual(len(egirl), 20)
            self.assertTrue(
                all(
                    item["presentation_prior"]["label"]
                    == "female_primary"
                    for item in egirl
                )
            )

            presets = batch["presets"]
            self.assertEqual(len(presets), 120)
            matrix_keys = {
                (
                    item["appearance_asset_ids"][0],
                    item["sex"],
                )
                for item in presets
            }
            self.assertEqual(len(matrix_keys), 120)
            self.assertTrue(
                all(
                    item["appearance_validation_plan"][
                        "pose_profile"
                    ]
                    == SUBJECT.SCALP_HAIR_PROFILE
                    for item in presets
                )
            )
            self.assertTrue(
                all(
                    item["appearance_validation_plan"][
                        "subject_position_offset"
                    ]
                    == {"x": -25.0, "z": 6.0}
                    for item in presets
                )
            )


if __name__ == "__main__":
    unittest.main()
