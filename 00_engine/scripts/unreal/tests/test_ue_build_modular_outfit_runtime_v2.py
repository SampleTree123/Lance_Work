from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "ue_build_modular_outfit_runtime_v2.py"
sys.modules.setdefault("unreal", types.ModuleType("unreal"))
SPEC = importlib.util.spec_from_file_location(
    "ue_build_modular_outfit_runtime_v2_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def bodyfit(sex: str, bodyfit_id: str, prefix: str) -> dict:
    templates = [
        {
            "component_name": "UpperInner",
            "component_kind": "fixed_semantic_slot",
            "accepted_slots": ["shirts"],
        },
        {
            "component_name": "BundlePart01",
            "component_kind": "reusable_bundle_pool",
            "accepted_slots": ["family_accessory"],
        },
    ]
    candidates = [
        {
            "component_name": f"{prefix}_Top",
            "mesh_path": f"/Game/Test/{prefix}_Top",
        }
    ]
    assignments = [
        {
            "target_component": "UpperInner",
            "target_kind": "fixed_semantic_slot",
            "source_component_name": f"{prefix}_Top",
            "slot": "shirts",
            "mesh_path": f"/Game/Test/{prefix}_Top",
        }
    ]
    return {
        "bodyfit_id": bodyfit_id,
        "sex": sex,
        "template_component_count": len(templates),
        "template_component_names": [item["component_name"] for item in templates],
        "template_components": templates,
        "candidate_mesh_count": len(candidates),
        "candidate_mesh_registry": candidates,
        "runtime_variants": [
            {
                "variant_id": "base",
                "qualified_variant_id": f"{prefix}_BASE::base",
                "assignment_count": 0,
                "assignments": [],
                "expected_target_component_names": [],
                "source_enabled_component_names": [],
                "required_bundle_component_count": 0,
            },
            {
                "variant_id": "default",
                "qualified_variant_id": f"{prefix}_CASE::default",
                "assignment_count": 1,
                "assignments": assignments,
                "expected_target_component_names": ["UpperInner"],
                "source_enabled_component_names": [f"{prefix}_Top"],
                "required_bundle_component_count": 0,
            },
        ],
    }


def plan() -> dict:
    return {
        "schema_version": 2,
        "status": "fixed_slot_ready_for_blueprint_build",
        "runtime_architecture": {"blueprint_candidate_hard_references": False},
        "bodyfits": [
            bodyfit("male", "M02_Average", "M"),
            bodyfit("female", "F02_Average", "F"),
        ],
    }


class RuntimePlanContractV2Tests(unittest.TestCase):
    def test_accepts_fixed_slot_plan(self) -> None:
        result = MODULE.validate_runtime_plan(plan())
        self.assertEqual(result["bodyfit_count"], 2)
        self.assertEqual(result["variant_count"], 4)
        self.assertEqual(result["template_component_count_per_actor"], 2)

    def test_rejects_candidate_hard_reference_on_template(self) -> None:
        invalid = copy.deepcopy(plan())
        invalid["bodyfits"][0]["template_components"][0][
            "mesh_path"
        ] = "/Game/Test/Forbidden"
        with self.assertRaisesRegex(RuntimeError, "candidate mesh path"):
            MODULE.validate_runtime_plan(invalid)

    def test_rejects_unknown_target_slot(self) -> None:
        invalid = copy.deepcopy(plan())
        variant = invalid["bodyfits"][0]["runtime_variants"][1]
        variant["assignments"][0]["target_component"] = "UnknownSlot"
        variant["expected_target_component_names"] = ["UnknownSlot"]
        with self.assertRaisesRegex(RuntimeError, "unknown template"):
            MODULE.validate_runtime_plan(invalid)


class VariantValidationV2Tests(unittest.TestCase):
    def record(self) -> dict:
        return {
            "body_identity_preserved": True,
            "body_propagates_curves": True,
            "actual_enabled_count": 1,
            "expected_enabled_count": 1,
            "actual_enabled_names": ["UpperInner"],
            "expected_enabled_names": ["UpperInner"],
            "components": [
                {
                    "component_name": "UpperInner",
                    "leader_is_body": True,
                    "enabled": True,
                    "mesh": "/Game/Test/M_Top",
                    "expected_mesh": "/Game/Test/M_Top",
                    "collision": "CollisionEnabled.NO_COLLISION",
                },
                {
                    "component_name": "BundlePart01",
                    "leader_is_body": True,
                    "enabled": False,
                    "mesh": None,
                    "expected_mesh": None,
                    "collision": "CollisionEnabled.NO_COLLISION",
                },
            ],
        }

    def test_accepts_loaded_target_and_empty_unused_slots(self) -> None:
        self.assertEqual(MODULE.validate_variant_application(self.record()), [])

    def test_rejects_stale_mesh_in_disabled_slot(self) -> None:
        record = self.record()
        record["components"][1]["mesh"] = "/Game/Test/OldAccessory"
        self.assertIn(
            "BundlePart01 retained a stale candidate mesh",
            MODULE.validate_variant_application(record),
        )


if __name__ == "__main__":
    unittest.main()
