#!/usr/bin/env python3
"""Compile the v001 pilot inventory into the v002 fixed-slot runtime plan.

The v001 plan is the verified CC/UE mesh inventory.  This compiler keeps that
inventory as data, but replaces one-component-per-candidate with five semantic
slots and a bounded pool for inseparable bundle parts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
REPORT_ROOT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "modular_outfit_pilot_20260829_v1"
)
DEFAULT_SOURCE = REPORT_ROOT / "runtime_plan_v1.json"
DEFAULT_OUTPUT = REPORT_ROOT / "runtime_plan_v2.json"
RUNTIME_BLUEPRINT_ROOT = "/Game/DataMake/Characters/ModularOutfitPilot"
BUNDLE_CAPACITY = 10

FIXED_COMPONENTS = (
    {
        "component_name": "UpperInner",
        "component_kind": "fixed_semantic_slot",
        "accepted_slots": ["shirts"],
    },
    {
        "component_name": "UpperOuter",
        "component_kind": "fixed_semantic_slot",
        "accepted_slots": ["coats"],
    },
    {
        "component_name": "Bottom",
        "component_kind": "fixed_semantic_slot",
        "accepted_slots": ["pants", "skirts"],
    },
    {
        "component_name": "FullBody",
        "component_kind": "fixed_semantic_slot",
        "accepted_slots": ["full_body"],
    },
    {
        "component_name": "Footwear",
        "component_kind": "fixed_semantic_slot",
        "accepted_slots": ["shoes"],
    },
)
SLOT_TO_FIXED_COMPONENT = {
    slot: spec["component_name"]
    for spec in FIXED_COMPONENTS
    for slot in spec["accepted_slots"]
}
SUPPORTED_SLOTS = frozenset((*SLOT_TO_FIXED_COMPONENT, "family_accessory"))


class RuntimePlanV2Error(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimePlanV2Error(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def template_components() -> list[dict[str, Any]]:
    components = [dict(spec) for spec in FIXED_COMPONENTS]
    components.extend(
        {
            "component_name": f"BundlePart{index:02d}",
            "component_kind": "reusable_bundle_pool",
            "pool_index": index,
            "accepted_slots": sorted(SUPPORTED_SLOTS),
        }
        for index in range(1, BUNDLE_CAPACITY + 1)
    )
    return components


def _source_component_registry(bodyfit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    components = bodyfit.get("components")
    if not isinstance(components, list):
        raise RuntimePlanV2Error(
            f"Source component registry is missing: {bodyfit.get('bodyfit_id')}"
        )
    registry: dict[str, dict[str, Any]] = {}
    for component in components:
        if not isinstance(component, dict):
            raise RuntimePlanV2Error("Source component row is not an object")
        name = component.get("component_name")
        slot = component.get("slot")
        if not isinstance(name, str) or not name:
            raise RuntimePlanV2Error("Source component name is empty")
        if name in registry:
            raise RuntimePlanV2Error(f"Duplicate source component: {name}")
        if slot not in SUPPORTED_SLOTS:
            raise RuntimePlanV2Error(f"Unsupported source slot {slot!r}: {name}")
        if not component.get("mesh_path"):
            raise RuntimePlanV2Error(f"Source component has no mesh path: {name}")
        registry[name] = component
    return registry


def _validate_semantic_combination(
    qualified_variant_id: str, source_components: list[dict[str, Any]]
) -> None:
    slots = {component["slot"] for component in source_components}
    if "pants" in slots and "skirts" in slots:
        raise RuntimePlanV2Error(
            f"Variant mixes pants and skirts in Bottom: {qualified_variant_id}"
        )
    layered_slots = {"shirts", "coats", "pants", "skirts"}
    if "full_body" in slots and slots.intersection(layered_slots):
        raise RuntimePlanV2Error(
            f"Variant mixes FullBody with separates: {qualified_variant_id}"
        )


def compile_variant(
    variant: dict[str, Any], registry: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    qualified = variant.get("qualified_variant_id")
    if not isinstance(qualified, str) or "::" not in qualified:
        raise RuntimePlanV2Error(f"Invalid source variant ID: {qualified}")
    source_names = variant.get("enabled_component_names")
    if not isinstance(source_names, list):
        raise RuntimePlanV2Error(f"Variant has no source component list: {qualified}")
    if len(source_names) != len(set(source_names)):
        raise RuntimePlanV2Error(f"Variant repeats a source component: {qualified}")
    missing = [name for name in source_names if name not in registry]
    if missing:
        raise RuntimePlanV2Error(
            f"Variant references unknown source components: {qualified}: {missing}"
        )

    source_components = [registry[name] for name in source_names]
    _validate_semantic_combination(qualified, source_components)
    used_fixed: set[str] = set()
    bundle_count = 0
    assignments: list[dict[str, Any]] = []
    for source in source_components:
        slot = source["slot"]
        fixed_target = SLOT_TO_FIXED_COMPONENT.get(slot)
        if fixed_target and fixed_target not in used_fixed:
            target = fixed_target
            target_kind = "fixed_semantic_slot"
            used_fixed.add(target)
        else:
            bundle_count += 1
            if bundle_count > BUNDLE_CAPACITY:
                raise RuntimePlanV2Error(
                    f"Variant exceeds BundlePart capacity {BUNDLE_CAPACITY}: {qualified}"
                )
            target = f"BundlePart{bundle_count:02d}"
            target_kind = "reusable_bundle_pool"
        assignments.append(
            {
                "target_component": target,
                "target_kind": target_kind,
                "source_component_name": source["component_name"],
                "case_id": source.get("case_id"),
                "qualified_module_id": source.get("qualified_module_id"),
                "module_key": source.get("module_key"),
                "slot": slot,
                "mesh_name": source.get("mesh_name"),
                "mesh_path": source["mesh_path"],
            }
        )

    targets = [assignment["target_component"] for assignment in assignments]
    if len(targets) != len(set(targets)):
        raise RuntimePlanV2Error(f"Variant target collision: {qualified}")
    return {
        "case_id": variant.get("case_id"),
        "variant_id": variant.get("variant_id"),
        "qualified_variant_id": qualified,
        "purpose": variant.get("purpose"),
        "enabled_modules": list(variant.get("enabled_modules") or []),
        "disabled_modules": list(variant.get("disabled_modules") or []),
        "source_enabled_component_names": list(source_names),
        "assignments": assignments,
        "expected_target_component_names": targets,
        "assignment_count": len(assignments),
        "required_bundle_component_count": bundle_count,
    }


def compile_runtime_plan(source: dict[str, Any]) -> dict[str, Any]:
    if source.get("schema_version") != 1:
        raise RuntimePlanV2Error("v002 requires a schema-v1 classified source plan")
    if source.get("status") != "classified_ready_for_blueprint_build":
        raise RuntimePlanV2Error("Source runtime plan is not classified and ready")
    source_bodyfits = source.get("bodyfits")
    if not isinstance(source_bodyfits, list) or len(source_bodyfits) != 2:
        raise RuntimePlanV2Error("Source runtime plan must contain two bodyfits")

    templates = template_components()
    template_names = [component["component_name"] for component in templates]
    bodyfits: list[dict[str, Any]] = []
    total_candidates = 0
    total_variants = 0
    for source_bodyfit in source_bodyfits:
        bodyfit_id = source_bodyfit.get("bodyfit_id")
        if not isinstance(bodyfit_id, str) or not bodyfit_id:
            raise RuntimePlanV2Error("Source bodyfit ID is empty")
        registry = _source_component_registry(source_bodyfit)
        source_variants = source_bodyfit.get("runtime_variants")
        if not isinstance(source_variants, list) or not source_variants:
            raise RuntimePlanV2Error(f"Source variants are missing: {bodyfit_id}")
        variants = [compile_variant(variant, registry) for variant in source_variants]
        total_candidates += len(registry)
        total_variants += len(variants)
        bodyfits.append(
            {
                "sex": source_bodyfit.get("sex"),
                "bodyfit_id": bodyfit_id,
                "base_case_id": source_bodyfit.get("base_case_id"),
                "body_mesh_path": source_bodyfit.get("body_mesh_path"),
                "skeleton_path": source_bodyfit.get("skeleton_path"),
                "reference_report": source_bodyfit.get("reference_report"),
                "blueprint_path": (
                    f"{RUNTIME_BLUEPRINT_ROOT}/{bodyfit_id}/"
                    f"BP_DM_{bodyfit_id}_ModularOutfitPilot_v002"
                ),
                "template_component_count": len(templates),
                "template_component_names": list(template_names),
                "template_components": [dict(component) for component in templates],
                "candidate_mesh_count": len(registry),
                "candidate_mesh_registry": list(registry.values()),
                "runtime_variants": variants,
                "max_active_component_count": max(
                    variant["assignment_count"] for variant in variants
                ),
                "max_bundle_component_count": max(
                    variant["required_bundle_component_count"] for variant in variants
                ),
            }
        )

    qualified_ids = [
        variant["qualified_variant_id"]
        for bodyfit in bodyfits
        for variant in bodyfit["runtime_variants"]
    ]
    if len(qualified_ids) != len(set(qualified_ids)):
        raise RuntimePlanV2Error("Qualified variant IDs are not globally unique")
    return {
        "schema_version": 2,
        "plan_id": "modular_outfit_runtime_plan_20260902_v2",
        "pilot_id": source.get("pilot_id"),
        "created_at_utc": utc_now(),
        "status": "fixed_slot_ready_for_blueprint_build",
        "source_plan_id": source.get("plan_id"),
        "runtime_architecture": {
            "identity_and_animation": "one clothing-free FullReference Body per sex",
            "outfit_components": "five fixed semantic slots plus ten reusable empty BundlePart slots",
            "candidate_mesh_references": "JSON object paths loaded only when a variant is applied",
            "blueprint_candidate_hard_references": False,
            "switching": "validate complete target, clear all slots, then assign target meshes",
            "pose_sync": "SetLeaderPoseComponent on every reusable slot",
            "curve_policy": "Body propagates curves to followers",
            "collision_policy": "Body owns collision; outfit followers use no collision",
        },
        "slot_contract": {
            "fixed_components": [dict(component) for component in FIXED_COMPONENTS],
            "bundle_component_prefix": "BundlePart",
            "bundle_capacity": BUNDLE_CAPACITY,
            "supported_source_slots": sorted(SUPPORTED_SLOTS),
            "pants_and_skirts_share_bottom": True,
            "full_body_excludes_separates": True,
        },
        "bodyfit_count": len(bodyfits),
        "runtime_variant_count": total_variants,
        "candidate_mesh_count": total_candidates,
        "template_component_count_per_actor": len(templates),
        "bodyfits": bodyfits,
        "production_gaps": sorted(
            set(source.get("production_gaps") or [])
            | {
                "packaged_runtime_soft_reference_registry_not_implemented",
                "body_surface_hide_masks_not_implemented",
            }
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = args.source.resolve()
    plan = compile_runtime_plan(read_json(source_path))
    plan["source_plan_path"] = str(source_path)
    output = args.output.resolve()
    write_json(output, plan)
    print(
        json.dumps(
            {
                "success": True,
                "output": str(output),
                "bodyfit_count": plan["bodyfit_count"],
                "runtime_variant_count": plan["runtime_variant_count"],
                "candidate_mesh_count": plan["candidate_mesh_count"],
                "template_component_count_per_actor": plan[
                    "template_component_count_per_actor"
                ],
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
