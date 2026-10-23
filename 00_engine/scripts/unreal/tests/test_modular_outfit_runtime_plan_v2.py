from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "modular_outfit_runtime_plan_v2.py"
SPEC = importlib.util.spec_from_file_location(
    "modular_outfit_runtime_plan_v2_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def component(name: str, slot: str) -> dict:
    return {
        "component_name": name,
        "case_id": name.split("_")[0],
        "qualified_module_id": f"CASE::{name}",
        "module_key": f"{slot}/{name}.ccCloth",
        "slot": slot,
        "mesh_name": name,
        "mesh_path": f"/Game/Test/{name}",
    }


def source_plan() -> dict:
    bodyfits = []
    rows_by_sex = {
        "male": [
            component("M_Shirt", "shirts"),
            component("M_Pants", "pants"),
            component("M_Scarf", "family_accessory"),
        ],
        "female": [
            component("F_DressPart1", "full_body"),
            component("F_DressPart2", "full_body"),
            component("F_Shoes", "shoes"),
        ],
    }
    for sex, bodyfit_id, prefix in (
        ("male", "M02_Average", "M"),
        ("female", "F02_Average", "F"),
    ):
        rows = rows_by_sex[sex]
        bodyfits.append(
            {
                "sex": sex,
                "bodyfit_id": bodyfit_id,
                "base_case_id": f"{prefix}_BASE",
                "body_mesh_path": f"/Game/Test/{prefix}_Body",
                "skeleton_path": f"/Game/Test/{prefix}_Skeleton",
                "reference_report": f"{prefix}_BASE.json",
                "component_count": len(rows),
                "component_names": [row["component_name"] for row in rows],
                "components": rows,
                "runtime_variants": [
                    {
                        "case_id": f"{prefix}_BASE",
                        "variant_id": "base",
                        "qualified_variant_id": f"{prefix}_BASE::base",
                        "enabled_component_names": [],
                        "enabled_component_count": 0,
                    },
                    {
                        "case_id": f"{prefix}_CASE",
                        "variant_id": "default",
                        "qualified_variant_id": f"{prefix}_CASE::default",
                        "enabled_component_names": [
                            row["component_name"] for row in rows
                        ],
                        "enabled_component_count": len(rows),
                    },
                ],
            }
        )
    return {
        "schema_version": 1,
        "plan_id": "source_v1",
        "pilot_id": "pilot",
        "status": "classified_ready_for_blueprint_build",
        "bodyfits": bodyfits,
        "production_gaps": [],
    }


class RuntimePlanV2Tests(unittest.TestCase):
    def test_compiles_fixed_slots_and_reusable_bundle_parts(self) -> None:
        result = MODULE.compile_runtime_plan(source_plan())

        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["template_component_count_per_actor"], 15)
        self.assertFalse(
            result["runtime_architecture"]["blueprint_candidate_hard_references"]
        )
        male = result["bodyfits"][0]
        assignments = male["runtime_variants"][1]["assignments"]
        self.assertEqual(
            [item["target_component"] for item in assignments],
            ["UpperInner", "Bottom", "BundlePart01"],
        )
        female = result["bodyfits"][1]
        assignments = female["runtime_variants"][1]["assignments"]
        self.assertEqual(
            [item["target_component"] for item in assignments],
            ["FullBody", "BundlePart01", "Footwear"],
        )
        self.assertTrue(
            all(
                "mesh_path" not in component
                for component in male["template_components"]
            )
        )

    def test_rejects_full_body_mixed_with_separates(self) -> None:
        source = source_plan()
        male = source["bodyfits"][0]
        dress = component("M_Dress", "full_body")
        male["components"].append(dress)
        male["runtime_variants"][1]["enabled_component_names"].append("M_Dress")

        with self.assertRaisesRegex(MODULE.RuntimePlanV2Error, "FullBody"):
            MODULE.compile_runtime_plan(source)

    def test_rejects_bundle_pool_overflow(self) -> None:
        source = source_plan()
        male = source["bodyfits"][0]
        extras = [
            component(f"M_Extra_{index:02d}", "family_accessory")
            for index in range(MODULE.BUNDLE_CAPACITY + 1)
        ]
        male["components"] = extras
        male["runtime_variants"][1]["enabled_component_names"] = [
            item["component_name"] for item in extras
        ]

        with self.assertRaisesRegex(MODULE.RuntimePlanV2Error, "capacity"):
            MODULE.compile_runtime_plan(source)

    def test_rejects_unknown_source_component(self) -> None:
        source = copy.deepcopy(source_plan())
        source["bodyfits"][0]["runtime_variants"][1][
            "enabled_component_names"
        ].append("M_Missing")
        with self.assertRaisesRegex(MODULE.RuntimePlanV2Error, "unknown"):
            MODULE.compile_runtime_plan(source)


if __name__ == "__main__":
    unittest.main()
