import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_sync_scalp_hair_catalog_paths_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_scalp_hair_catalog_sync_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class ScalpHairCatalogSyncTests(unittest.TestCase):
    def test_sync_preserves_ids_and_updates_selected_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            assets = []
            selected_assets = []
            for index in range(60):
                asset_id = "HAIR_{:02d}".format(index)
                current_path = root / "current" / (
                    "hair_{:02d}.rlHair".format(index)
                )
                current_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.write_bytes(b"hair")
                common = {
                    "asset_form": "group",
                    "asset_id": asset_id,
                    "asset_type": "hair",
                    "display_name": "Hair {:02d}".format(index),
                    "slot": "scalp_hair",
                }
                assets.append(
                    dict(
                        common,
                        preferred_path=str(
                            root / "old" / current_path.name
                        ),
                    )
                )
                selected_assets.append(
                    dict(
                        common,
                        hair_builder_pack={
                            "asset_index": index + 1,
                            "pack_code": "HBX",
                            "pack_id": "synthetic",
                        },
                        path_migration={
                            "stable_asset_id_preserved": True
                        },
                        preferred_origin="custom",
                        preferred_path=str(current_path),
                        presentation_prior={
                            "female_presentation_score": 0.5,
                            "label": "unisex",
                            "source": "test",
                        },
                        sex_hint="unknown",
                        variants=[
                            {
                                "asset_form": "group",
                                "extension": ".rlhair",
                                "origin": "custom",
                                "path": str(current_path),
                            }
                        ],
                    )
                )

            canonical_path = root / "canonical.json"
            selected_path = root / "selected.json"
            output_path = root / "output.json"
            canonical_path.write_text(
                json.dumps({"assets": assets}),
                encoding="utf-8",
            )
            selected_path.write_text(
                json.dumps(
                    {
                        "assets": selected_assets,
                        "catalog_id": "selected",
                    }
                ),
                encoding="utf-8",
            )

            result = SUBJECT.sync(
                str(canonical_path),
                str(selected_path),
                str(output_path),
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["asset_count"], 60)
            self.assertEqual(result["migration_count"], 60)
            output = json.loads(
                output_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                [item["asset_id"] for item in output["assets"]],
                [item["asset_id"] for item in assets],
            )
            self.assertTrue(
                all(
                    pathlib.Path(item["preferred_path"]).is_file()
                    for item in output["assets"]
                )
            )
            self.assertEqual(
                output["selected_pool_syncs"][0]["catalog_id"],
                "selected",
            )


if __name__ == "__main__":
    unittest.main()
