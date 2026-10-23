import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "cc_build_modular_outfit_pilot_v1.py"
SPEC = importlib.util.spec_from_file_location("modular_outfit_builder", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


class ModularOutfitBuilderTests(unittest.TestCase):
    def test_runtime_variant_can_disable_optional_coat(self):
        family = {
            "family_id": "male.demo",
            "assembly_mode": "slot_groups",
            "assets": [
                {"asset_id": "pants", "slot": "pants"},
                {"asset_id": "shirt", "slot": "shirts"},
                {"asset_id": "coat", "slot": "coats"},
                {"asset_id": "shoe", "slot": "shoes"},
            ],
            "assembly": {
                "groups": [
                    {
                        "group_id": "default",
                        "required_slots": ["pants", "shirts", "shoes"],
                        "optional_slots": ["coats"],
                        "slot_pools": {
                            "pants": ["pants"],
                            "shirts": ["shirt"],
                            "coats": ["coat"],
                            "shoes": ["shoe"],
                        },
                    }
                ]
            },
            "footwear_policy": {"mode": "native_pool"},
        }
        group = family["assembly"]["groups"][0]
        enabled = [
            {"asset_id": "pants", "source": "family"},
            {"asset_id": "shirt", "source": "family"},
            {"asset_id": "shoe", "source": "family"},
        ]
        SUBJECT.validate_runtime_variant(family, group, enabled)

    def test_barefoot_requires_family_permission(self):
        family = {
            "family_id": "female.demo",
            "assembly_mode": "slot_groups",
            "assets": [
                {"asset_id": "pants", "slot": "pants"},
                {"asset_id": "shirt", "slot": "shirts"},
            ],
            "assembly": {
                "groups": [
                    {
                        "group_id": "default",
                        "required_slots": ["pants", "shirts"],
                        "optional_slots": [],
                        "slot_pools": {
                            "pants": ["pants"],
                            "shirts": ["shirt"],
                        },
                    }
                ]
            },
            "footwear_policy": {
                "mode": "shared_pool",
                "allowed_shared_shoe_ids": ["F001"],
                "allow_barefoot": False,
            },
        }
        group = family["assembly"]["groups"][0]
        enabled = [
            {"asset_id": "pants", "source": "family"},
            {"asset_id": "shirt", "source": "family"},
        ]
        with self.assertRaises(SUBJECT.ModularPilotError):
            SUBJECT.validate_runtime_variant(family, group, enabled)
        family["footwear_policy"]["allow_barefoot"] = True
        SUBJECT.validate_runtime_variant(family, group, enabled)

    def test_production_source_compiles_all_frozen_cases(self):
        cc_manifest, ue_manifest = SUBJECT.compile_manifests(SUBJECT.DEFAULT_SOURCE)
        self.assertEqual(14, cc_manifest["counts"]["case_count"])
        self.assertEqual(2, cc_manifest["counts"]["base_case_count"])
        self.assertEqual(12, cc_manifest["counts"]["outfit_case_count"])
        self.assertEqual(14, len(cc_manifest["presets"]))
        self.assertEqual(14, len(ue_manifest["cases"]))
        self.assertEqual("render_image", cc_manifest["preview_capture_mode"])
        self.assertTrue(
            all(
                item["production_output"]["skip_preview_capture"]
                for item in cc_manifest["presets"]
            )
        )
        base_presets = [
            item for item in cc_manifest["presets"] if item["case_role"] == "base_body"
        ]
        self.assertEqual(2, len(base_presets))
        self.assertTrue(all(item["allow_empty_selected_assets"] for item in base_presets))
        self.assertTrue(all(not item["selected_assets"] for item in base_presets))
        self.assertIn("locked_bundle", cc_manifest["counts"]["coverage_tags"])
        self.assertIn("barefoot_toggle", cc_manifest["counts"]["coverage_tags"])
        red = next(
            item for item in cc_manifest["presets"] if item["case_id"] == "M_REDSOUL_LOCKED"
        )
        self.assertEqual(
            [
                "male.redsoul.asset.b7a4b22d397e",
                "male.redsoul.asset.31b40f2f6361",
                "male.redsoul.asset.9517e41aeeaa",
                "male.redsoul.asset.c255d8db850e",
                "male.redsoul.asset.b27df7cee669",
                "male.redsoul.asset.b37f9c3bd4cf",
            ],
            [asset["asset_id"] for asset in red["selected_assets"]],
        )


if __name__ == "__main__":
    unittest.main()
