from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = SCRIPT_ROOT / "cc_build_confirmed_outfit_family_json_v1.py"
VALIDATOR_PATH = SCRIPT_ROOT / "cc_validate_outfit_family_library_v1.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


BUILDER = load_module("cc_outfit_family_builder_test", BUILDER_PATH)
VALIDATOR = load_module("cc_outfit_family_validator_test", VALIDATOR_PATH)


class OutfitFamilyJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "female").mkdir()
        (self.root / "male").mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def barefoot_policy() -> dict[str, object]:
        return {
            "mode": "barefoot_only",
            "allowed_shared_shoe_ids": [],
            "default_shared_shoe_id": None,
            "allow_barefoot": True,
            "shared_inventory_ref": None,
        }

    @staticmethod
    def native_policy() -> dict[str, object]:
        return {
            "mode": "native_pool",
            "allowed_shared_shoe_ids": [],
            "default_shared_shoe_id": None,
            "allow_barefoot": False,
            "shared_inventory_ref": None,
        }

    @staticmethod
    def integrated_policy() -> dict[str, object]:
        return {
            "mode": "integrated_footwear",
            "allowed_shared_shoe_ids": [],
            "default_shared_shoe_id": None,
            "allow_barefoot": False,
            "shared_inventory_ref": None,
        }

    def write_shared_inventory(self) -> None:
        path = self.root / "both" / "shoes" / "shoe_inventory.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 3,
                    "library_id": "cc_shared_shoes_v1",
                    "revision_id": "test_revision",
                    "assets": [
                        {"shoe_id": "F001", "sex": "female"},
                        {"shoe_id": "M001", "sex": "male"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def write_config(
        self,
        confirmed: list[dict[str, object]],
        deferred: list[dict[str, str]] | None = None,
    ) -> Path:
        path = self.root / "rules.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "confirmed_families": confirmed,
                    "deferred_families": deferred or [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def test_confirmed_family_requires_exhaustive_asset_coverage(self) -> None:
        family = self.root / "female" / "Example"
        (family / "Shirts").mkdir(parents=True)
        (family / "Pants").mkdir()
        (family / "Shirts" / "Top.ccCloth").write_bytes(b"top")
        (family / "Pants" / "Pants.ccCloth").write_bytes(b"pants")
        rule = {
            "sex": "female",
            "family": "Example",
            "family_id": "female.example",
            "assembly_mode": "explicit_looks",
            "looks": [
                {"look_id": "default", "assets": ["Shirts/Top.ccCloth"]}
            ],
            "footwear_policy": self.barefoot_policy(),
        }

        with self.assertRaisesRegex(BUILDER.OutfitBuildError, "unreferenced"):
            BUILDER.build_document(rule, self.root, "2026-08-12T00:00:00+08:00")

    def test_full_body_ccshoes_is_preserved_with_semantic_override(self) -> None:
        family = self.root / "male" / "Rugged"
        (family / "Full-body").mkdir(parents=True)
        asset = family / "Full-body" / "Protective Gear.ccShoes"
        asset.write_bytes(b"full body payload")
        rule = {
            "sex": "male",
            "family": "Rugged",
            "family_id": "male.rugged",
            "assembly_mode": "explicit_looks",
            "looks": [
                {
                    "look_id": "default",
                    "assets": ["Full-body/Protective Gear.ccShoes"],
                }
            ],
            "footwear_policy": self.integrated_policy(),
        }

        document = BUILDER.build_document(
            rule, self.root, "2026-08-12T00:00:00+08:00"
        )

        self.assertEqual("full_body", document["assets"][0]["slot"])
        self.assertEqual(".ccShoes", document["assets"][0]["file_extension"])
        self.assertTrue(document["assets"][0]["semantic_slot_override"])

    def test_family_local_accessories_can_be_independently_optional(self) -> None:
        family = self.root / "female" / "Jumpsuit"
        (family / "Full-body").mkdir(parents=True)
        (family / "_Accessories-Pending").mkdir()
        (family / "Full-body" / "Jumpsuit.ccCloth").write_bytes(b"jumpsuit")
        (family / "_Accessories-Pending" / "Belt.ccCloth").write_bytes(b"belt")
        (family / "_Accessories-Pending" / "Necklace.ccCloth").write_bytes(
            b"necklace"
        )
        rule = {
            "sex": "female",
            "family": "Jumpsuit",
            "family_id": "female.jumpsuit",
            "assembly_mode": "explicit_looks",
            "looks": [
                {
                    "look_id": "default",
                    "assets": ["Full-body/Jumpsuit.ccCloth"],
                    "optional_assets": [
                        "_Accessories-Pending/Belt.ccCloth",
                        "_Accessories-Pending/Necklace.ccCloth",
                    ],
                }
            ],
            "footwear_policy": self.barefoot_policy(),
        }

        document = BUILDER.build_document(
            rule, self.root, "2026-08-12T00:00:00+08:00"
        )
        look = document["assembly"]["looks"][0]
        accessories = [
            asset for asset in document["assets"] if asset["slot"] == "family_accessory"
        ]

        self.assertEqual("independent_subset", look["optional_asset_policy"])
        self.assertEqual(2, len(look["optional_assets"]))
        self.assertEqual(2, len(accessories))
        self.assertTrue(
            all(asset["component_scope"] == "family_local" for asset in accessories)
        )
        self.assertFalse(document["constraints"]["family_accessories_cross_family"])

    def test_slot_groups_can_reuse_assets_across_mutually_exclusive_groups(self) -> None:
        family = self.root / "female" / "Streetwear"
        (family / "Coats").mkdir(parents=True)
        (family / "Shirts").mkdir()
        (family / "Pants").mkdir()
        (family / "Coats" / "Jacket.ccCloth").write_bytes(b"jacket")
        (family / "Shirts" / "Shirt.ccCloth").write_bytes(b"shirt")
        (family / "Pants" / "Pants.ccCloth").write_bytes(b"pants")
        rule = {
            "sex": "female",
            "family": "Streetwear",
            "family_id": "female.streetwear",
            "assembly_mode": "slot_groups",
            "groups": [
                {
                    "group_id": "shirt",
                    "required_slots": ["pants", "shirts"],
                    "optional_slots": [],
                    "slot_pools": {
                        "pants": ["Pants/Pants.ccCloth"],
                        "shirts": ["Shirts/Shirt.ccCloth"],
                    },
                },
                {
                    "group_id": "jacket",
                    "required_slots": ["pants", "coats"],
                    "optional_slots": [],
                    "slot_pools": {
                        "pants": ["Pants/Pants.ccCloth"],
                        "coats": ["Coats/Jacket.ccCloth"],
                    },
                },
            ],
            "footwear_policy": self.barefoot_policy(),
        }

        document = BUILDER.build_document(
            rule, self.root, "2026-08-13T00:00:00+08:00"
        )

        self.assertEqual(2, len(document["assembly"]["groups"]))
        self.assertEqual(3, len(document["assets"]))

    def test_slot_group_supports_fixed_family_local_accessories(self) -> None:
        family = self.root / "male" / "Formal"
        (family / "Shirts").mkdir(parents=True)
        (family / "_Accessories-Pending").mkdir()
        (family / "Shirts" / "Shirt.ccCloth").write_bytes(b"shirt")
        (family / "_Accessories-Pending" / "Waistcoat.ccCloth").write_bytes(
            b"waistcoat"
        )
        rule = {
            "sex": "male",
            "family": "Formal",
            "family_id": "male.formal",
            "assembly_mode": "slot_groups",
            "groups": [
                {
                    "group_id": "default",
                    "required_slots": ["shirts"],
                    "optional_slots": [],
                    "slot_pools": {"shirts": ["Shirts/Shirt.ccCloth"]},
                    "required_assets": [
                        "_Accessories-Pending/Waistcoat.ccCloth"
                    ],
                }
            ],
            "footwear_policy": self.barefoot_policy(),
        }

        document = BUILDER.build_document(
            rule, self.root, "2026-08-13T00:00:00+08:00"
        )
        group = document["assembly"]["groups"][0]

        self.assertEqual(1, len(group["required_assets"]))
        self.assertEqual([], group["optional_assets"])
        self.assertEqual("independent_subset", group["optional_asset_policy"])

    def test_write_and_independent_validation_keep_deferred_family_untouched(self) -> None:
        confirmed_family = self.root / "female" / "Confirmed"
        (confirmed_family / "Full-body").mkdir(parents=True)
        (confirmed_family / "Full-body" / "Dress.ccCloth").write_bytes(b"dress")
        deferred_family = self.root / "male" / "Deferred"
        (deferred_family / "Shirts").mkdir(parents=True)
        (deferred_family / "Shirts" / "Unknown.ccCloth").write_bytes(b"unknown")
        rule = {
            "sex": "female",
            "family": "Confirmed",
            "family_id": "female.confirmed",
            "assembly_mode": "explicit_looks",
            "looks": [
                {"look_id": "default", "assets": ["Full-body/Dress.ccCloth"]}
            ],
            "footwear_policy": self.barefoot_policy(),
        }
        rules_path = self.write_config(
            [rule],
            [
                {
                    "sex": "male",
                    "family": "Deferred",
                    "reason": "Compatibility is not confirmed.",
                }
            ],
        )
        BUILDER.validate_config_partition(self.root, BUILDER.read_json(rules_path))
        document = BUILDER.build_document(
            rule, self.root, "2026-08-12T00:00:00+08:00"
        )
        output = confirmed_family / "outfit_family.json"

        BUILDER.write_documents(self.root, [(output, document)], replace=False)
        result = VALIDATOR.validate(self.root, rules_path)

        self.assertTrue(result["success"], result["errors"])
        self.assertEqual(1, result["validated_family_count"])
        self.assertFalse((deferred_family / "outfit_family.json").exists())

    def test_native_shoe_pool_is_embedded_without_shared_inventory(self) -> None:
        family = self.root / "male" / "Casual"
        (family / "Shirts").mkdir(parents=True)
        (family / "Shoes").mkdir()
        (family / "Shirts" / "Top.ccCloth").write_bytes(b"top")
        (family / "Shoes" / "Shoe.ccShoes").write_bytes(b"shoe")
        rule = {
            "sex": "male",
            "family": "Casual",
            "family_id": "male.casual",
            "assembly_mode": "slot_groups",
            "groups": [
                {
                    "group_id": "default",
                    "required_slots": ["shirts", "shoes"],
                    "optional_slots": [],
                    "slot_pools": {
                        "shirts": ["Shirts/Top.ccCloth"],
                        "shoes": ["Shoes/Shoe.ccShoes"],
                    },
                }
            ],
            "footwear_policy": self.native_policy(),
        }

        document = BUILDER.build_document(
            rule, self.root, "2026-08-15T00:00:00+08:00"
        )

        self.assertEqual("native_pool", document["footwear_policy"]["mode"])
        self.assertEqual(1, len([asset for asset in document["assets"] if asset["slot"] == "shoes"]))

    def test_shared_shoe_pool_validates_inventory_identity_and_sex(self) -> None:
        self.write_shared_inventory()
        family = self.root / "female" / "Dress"
        (family / "Full-body").mkdir(parents=True)
        (family / "Full-body" / "Dress.ccCloth").write_bytes(b"dress")
        rule = {
            "sex": "female",
            "family": "Dress",
            "family_id": "female.dress",
            "assembly_mode": "slot_groups",
            "groups": [
                {
                    "group_id": "default",
                    "required_slots": ["full_body"],
                    "optional_slots": [],
                    "slot_pools": {"full_body": ["Full-body/Dress.ccCloth"]},
                }
            ],
            "footwear_policy": {
                "mode": "shared_pool",
                "allowed_shared_shoe_ids": ["F001"],
                "default_shared_shoe_id": "F001",
                "allow_barefoot": False,
                "shared_inventory_ref": {
                    "library_id": "cc_shared_shoes_v1",
                    "revision_id": "test_revision",
                },
            },
        }

        document = BUILDER.build_document(
            rule, self.root, "2026-08-15T00:00:00+08:00"
        )
        self.assertEqual(["F001"], document["footwear_policy"]["allowed_shared_shoe_ids"])

        rule["footwear_policy"]["allowed_shared_shoe_ids"] = ["M001"]
        rule["footwear_policy"]["default_shared_shoe_id"] = "M001"
        with self.assertRaisesRegex(BUILDER.OutfitBuildError, "Wrong-sex"):
            BUILDER.build_document(rule, self.root, "2026-08-15T00:00:00+08:00")

    def test_validator_rejects_json_in_deferred_family(self) -> None:
        deferred_family = self.root / "male" / "Deferred"
        deferred_family.mkdir(parents=True)
        (deferred_family / "outfit_family.json").write_text("{}", encoding="utf-8")
        rules_path = self.write_config(
            [],
            [
                {
                    "sex": "male",
                    "family": "Deferred",
                    "reason": "Compatibility is not confirmed.",
                }
            ],
        )

        result = VALIDATOR.validate(self.root, rules_path)

        self.assertFalse(result["success"])
        self.assertEqual(1, result["deferred_with_json_count"])
        self.assertTrue(
            any("deferred family unexpectedly has JSON" in error for error in result["errors"])
        )


if __name__ == "__main__":
    unittest.main()
