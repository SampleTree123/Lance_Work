from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "cc_merge_shared_shoe_assignments_into_outfit_rules_v1.py"
)
SPEC = importlib.util.spec_from_file_location("cc_shoe_rule_merge_test", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SharedShoeRuleMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = {
            "schema_version": 1,
            "confirmed_families": [
                {
                    "sex": "female",
                    "family": "Native",
                    "family_id": "female.native",
                    "assembly_mode": "slot_groups",
                    "groups": [
                        {
                            "group_id": "default",
                            "required_slots": ["shirts", "shoes"],
                            "optional_slots": [],
                            "slot_pools": {
                                "shirts": ["Shirts/Top.ccCloth"],
                                "shoes": ["Shoes/Flat.ccShoes"],
                            },
                        }
                    ],
                },
                {
                    "sex": "female",
                    "family": "Shared",
                    "family_id": "female.shared",
                    "assembly_mode": "slot_groups",
                    "groups": [
                        {
                            "group_id": "default",
                            "required_slots": ["full_body"],
                            "optional_slots": [],
                            "slot_pools": {
                                "full_body": ["Full-body/Dress.ccCloth"]
                            },
                        }
                    ],
                },
                {
                    "sex": "male",
                    "family": "Integrated",
                    "family_id": "male.integrated",
                    "assembly_mode": "slot_groups",
                    "groups": [
                        {
                            "group_id": "default",
                            "required_slots": ["full_body"],
                            "optional_slots": [],
                            "slot_pools": {
                                "full_body": ["Full-body/Gear.ccShoes"]
                            },
                        }
                    ],
                },
            ],
            "deferred_families": [],
        }
        self.assignments = {
            "families": [
                {
                    "family_id": "female.shared",
                    "sex": "female",
                    "shoe_resolution": "shared_pool",
                    "allowed_shared_shoe_ids": ["F001"],
                    "default_shared_shoe_id": None,
                    "allow_barefoot": True,
                    "look_overrides": [],
                },
                {
                    "family_id": "male.integrated",
                    "sex": "male",
                    "shoe_resolution": "integrated_footwear",
                    "allowed_shared_shoe_ids": [],
                    "default_shared_shoe_id": None,
                    "allow_barefoot": False,
                    "look_overrides": [],
                },
            ]
        }
        self.inventory = {
            "library_id": "cc_shared_shoes_v1",
            "revision_id": "test_revision",
            "assets": [
                {"shoe_id": "F001", "sex": "female"},
                {"shoe_id": "M001", "sex": "male"},
            ],
        }

    def test_merge_covers_native_shared_and_integrated_modes(self) -> None:
        merged, report = MODULE.merge(
            self.rules, self.assignments, self.inventory
        )
        policies = {
            rule["family_id"]: rule["footwear_policy"]
            for rule in merged["confirmed_families"]
        }

        self.assertEqual("native_pool", policies["female.native"]["mode"])
        self.assertEqual("shared_pool", policies["female.shared"]["mode"])
        self.assertTrue(policies["female.shared"]["allow_barefoot"])
        self.assertEqual(
            "integrated_footwear", policies["male.integrated"]["mode"]
        )
        self.assertEqual(
            {"integrated_footwear": 1, "native_pool": 1, "shared_pool": 1},
            report["counts_by_footwear_mode"],
        )

    def test_wrong_sex_shared_shoe_is_rejected(self) -> None:
        assignment = self.assignments["families"][0]
        assignment["allowed_shared_shoe_ids"] = ["M001"]

        with self.assertRaisesRegex(MODULE.ShoeMergeError, "wrong-sex"):
            MODULE.merge(self.rules, self.assignments, self.inventory)


if __name__ == "__main__":
    unittest.main()
