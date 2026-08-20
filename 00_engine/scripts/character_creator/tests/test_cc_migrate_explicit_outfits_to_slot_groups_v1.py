#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "cc_migrate_explicit_outfits_to_slot_groups_v1.py"
SPEC = importlib.util.spec_from_file_location("outfit_rule_migration", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ExplicitLookMigrationTests(unittest.TestCase):
    def test_numbered_pairs_become_free_slot_pools(self) -> None:
        source = {
            "family_id": "female.example",
            "assembly_mode": "explicit_looks",
            "looks": [
                {
                    "look_id": "a",
                    "assets": ["Shirts/A.ccCloth", "Pants/A.ccCloth"],
                },
                {
                    "look_id": "b",
                    "assets": ["Shirts/B.ccCloth", "Pants/B.ccCloth"],
                },
            ],
        }
        result = MODULE.convert_explicit_family(source)
        group = result["groups"][0]
        self.assertEqual("slot_groups", result["assembly_mode"])
        self.assertEqual(["shirts", "pants"], group["required_slots"])
        self.assertEqual(
            ["Shirts/A.ccCloth", "Shirts/B.ccCloth"],
            group["slot_pools"]["shirts"],
        )
        self.assertEqual(
            ["Pants/A.ccCloth", "Pants/B.ccCloth"],
            group["slot_pools"]["pants"],
        )

    def test_full_body_and_optional_accessories_are_preserved(self) -> None:
        source = {
            "family_id": "female.jumpsuit",
            "assembly_mode": "explicit_looks",
            "looks": [
                {
                    "look_id": "a",
                    "assets": ["Full-body/A.ccCloth"],
                    "optional_assets": ["_Accessories-Pending/Belt.ccCloth"],
                },
                {
                    "look_id": "b",
                    "assets": ["Full-body/B.ccCloth"],
                    "optional_assets": ["_Accessories-Pending/Belt.ccCloth"],
                },
            ],
        }
        group = MODULE.convert_explicit_family(source)["groups"][0]
        self.assertEqual(["full_body"], group["required_slots"])
        self.assertEqual(
            ["Full-body/A.ccCloth", "Full-body/B.ccCloth"],
            group["slot_pools"]["full_body"],
        )
        self.assertEqual(
            ["_Accessories-Pending/Belt.ccCloth"], group["optional_assets"]
        )

    def test_different_slot_shapes_are_rejected(self) -> None:
        source = {
            "family_id": "invalid.example",
            "assembly_mode": "explicit_looks",
            "looks": [
                {"look_id": "a", "assets": ["Full-body/A.ccCloth"]},
                {
                    "look_id": "b",
                    "assets": ["Shirts/B.ccCloth", "Pants/B.ccCloth"],
                },
            ],
        }
        with self.assertRaises(MODULE.OutfitRuleMigrationError):
            MODULE.convert_explicit_family(source)


if __name__ == "__main__":
    unittest.main()
