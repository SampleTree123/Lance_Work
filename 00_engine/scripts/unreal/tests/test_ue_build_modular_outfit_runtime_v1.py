from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1] / "ue_build_modular_outfit_runtime_v1.py"
)
sys.modules.setdefault("unreal", types.ModuleType("unreal"))
SPEC = importlib.util.spec_from_file_location(
    "ue_build_modular_outfit_runtime_v1_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def plan() -> dict:
    return {
        "schema_version": 1,
        "status": "classified_ready_for_blueprint_build",
        "bodyfits": [
            {
                "bodyfit_id": "M02_Average",
                "sex": "male",
                "component_count": 2,
                "component_names": ["Outfit_M_CASE_01", "Outfit_M_CASE_02"],
                "components": [
                    {
                        "component_name": "Outfit_M_CASE_01",
                        "mesh_path": "/Game/Test/M_Top",
                    },
                    {
                        "component_name": "Outfit_M_CASE_02",
                        "mesh_path": "/Game/Test/M_Pants",
                    },
                ],
                "runtime_variants": [
                    {
                        "variant_id": "base",
                        "qualified_variant_id": "M_BASE::base",
                        "enabled_component_count": 0,
                        "enabled_component_names": [],
                    },
                    {
                        "variant_id": "default",
                        "qualified_variant_id": "M_CASE::default",
                        "enabled_component_count": 2,
                        "enabled_component_names": [
                            "Outfit_M_CASE_01",
                            "Outfit_M_CASE_02",
                        ],
                    },
                ],
                "cases": [
                    {
                        "case_id": "M_CASE",
                        "runtime_variants": [
                            {
                                "variant_id": "default",
                                "qualified_variant_id": "M_CASE::default",
                                "enabled_component_count": 2,
                                "enabled_component_names": [
                                    "Outfit_M_CASE_01",
                                    "Outfit_M_CASE_02",
                                ],
                            }
                        ],
                    }
                ],
            },
            {
                "bodyfit_id": "F02_Average",
                "sex": "female",
                "component_count": 1,
                "component_names": ["Outfit_F_CASE_01"],
                "components": [
                    {
                        "component_name": "Outfit_F_CASE_01",
                        "mesh_path": "/Game/Test/F_Dress",
                    }
                ],
                "runtime_variants": [
                    {
                        "variant_id": "base",
                        "qualified_variant_id": "F_BASE::base",
                        "enabled_component_count": 0,
                        "enabled_component_names": [],
                    },
                    {
                        "variant_id": "default",
                        "qualified_variant_id": "F_CASE::default",
                        "enabled_component_count": 1,
                        "enabled_component_names": ["Outfit_F_CASE_01"],
                    },
                ],
                "cases": [
                    {
                        "case_id": "F_CASE",
                        "runtime_variants": [
                            {
                                "variant_id": "default",
                                "qualified_variant_id": "F_CASE::default",
                                "enabled_component_count": 1,
                                "enabled_component_names": [
                                    "Outfit_F_CASE_01"
                                ],
                            }
                        ],
                    }
                ],
            },
        ],
    }


class RuntimePlanContractTests(unittest.TestCase):
    def test_component_variable_names_have_compact_search_form(self) -> None:
        name = "Outfit_M_1920_LAYERED_01"
        compact = MODULE.re.sub(r"[^A-Za-z0-9]+", "", name)
        self.assertEqual(compact, "OutfitM1920LAYERED01")

    def test_accepts_two_bodyfits_and_unique_variants(self) -> None:
        result = MODULE.validate_runtime_plan(plan())
        self.assertEqual(result["bodyfit_count"], 2)
        self.assertEqual(result["variant_count"], 4)

    def test_rejects_variant_with_unknown_component(self) -> None:
        invalid = copy.deepcopy(plan())
        variant = invalid["bodyfits"][1]["runtime_variants"][1]
        variant["enabled_component_names"].append("Outfit_F_CASE_99")
        variant["enabled_component_count"] = 2
        with self.assertRaisesRegex(RuntimeError, "unknown components"):
            MODULE.validate_runtime_plan(invalid)

    def test_rejects_component_registry_order_mismatch(self) -> None:
        invalid = copy.deepcopy(plan())
        invalid["bodyfits"][0]["components"].reverse()
        with self.assertRaisesRegex(RuntimeError, "registry ordering"):
            MODULE.validate_runtime_plan(invalid)

    def test_bodyfit_and_variant_lookup_are_exact(self) -> None:
        runtime_plan = plan()
        bodyfit = MODULE.bodyfit_for_id(runtime_plan, "M02_Average")
        variant = MODULE.variant_for_id(bodyfit, "M_CASE::default")
        self.assertEqual(variant["enabled_component_count"], 2)
        with self.assertRaisesRegex(RuntimeError, "found 0"):
            MODULE.variant_for_id(bodyfit, "M_CASE::missing")


class VariantValidationTests(unittest.TestCase):
    def test_reports_structural_failures_without_visual_claims(self) -> None:
        record = {
            "body_identity_preserved": True,
            "body_propagates_curves": True,
            "actual_enabled_count": 1,
            "expected_enabled_count": 1,
            "actual_enabled_names": ["Outfit_M_CASE_01"],
            "expected_enabled_names": ["Outfit_M_CASE_01"],
            "components": [
                {
                    "component_name": "Outfit_M_CASE_01",
                    "leader_is_body": True,
                    "enabled": True,
                    "mesh": "/Game/Test/Top",
                    "collision": "CollisionEnabled.NO_COLLISION",
                }
            ],
        }
        self.assertEqual(MODULE.validate_variant_application(record), [])
        record["components"][0]["leader_is_body"] = False
        self.assertIn(
            "Outfit_M_CASE_01 has no Body leader",
            MODULE.validate_variant_application(record),
        )


if __name__ == "__main__":
    unittest.main()
