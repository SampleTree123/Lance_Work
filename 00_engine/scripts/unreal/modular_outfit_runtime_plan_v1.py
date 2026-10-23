#!/usr/bin/env python3
"""Classify CC split meshes and freeze the modular-outfit runtime plan.

This module is intentionally Unreal-free. It consumes the finalized CC/UE
manifest plus UE import reports and produces the exact follower components that the
runtime Blueprint builder is allowed to use.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
DEFAULT_MANIFEST = SCRIPT_ROOT / "ue_modular_outfit_pilot_manifest_20260829_v1.json"
DEFAULT_REPORT_ROOT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "modular_outfit_pilot_20260829_v1"
)
DEFAULT_OUTPUT = DEFAULT_REPORT_ROOT / "runtime_plan_v1.json"
RUNTIME_BLUEPRINT_ROOT = "/Game/DataMake/Characters/ModularOutfitPilot"
BASE_CASE_IDS = {"male": "M_BASE", "female": "F_BASE"}
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_]+$")
KNOWN_MESH_SUFFIXES = (
    "skeletalmesh",
    "skelmesh",
    "mesh",
    "lod0",
)


class RuntimePlanError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimePlanError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def normalize_object_name(value: object) -> str:
    """Normalize CC scene names and Unreal asset names for strict matching."""
    name = str(value or "").strip().casefold()
    if not name:
        return ""
    # Object paths and generated-class notation are irrelevant to mesh identity.
    name = name.rsplit("/", 1)[-1].split(".", 1)[0].replace("_gen_variable", "")
    normalized = re.sub(r"[^a-z0-9]+", "", name)
    changed = True
    while normalized and changed:
        changed = False
        for suffix in KNOWN_MESH_SUFFIXES:
            if normalized.endswith(suffix) and len(normalized) > len(suffix):
                normalized = normalized[: -len(suffix)]
                changed = True
                break
    return normalized


def _mesh_match_score(scene_name: str, mesh_name: str) -> int:
    scene = normalize_object_name(scene_name)
    mesh = normalize_object_name(mesh_name)
    if not scene or not mesh:
        return 0
    if scene == mesh:
        return 100
    # Interchange can prefix a source-file token or append a numeric asset token.
    if mesh.endswith(scene) or mesh.startswith(scene):
        return 80
    if len(scene) >= 5 and scene in mesh:
        return 60
    return 0


def _skeletal_mesh_records(report: dict[str, Any]) -> list[dict[str, Any]]:
    records = report.get("split_assets")
    if records is None:
        records = report.get("meshes")
    if not isinstance(records, list):
        raise RuntimePlanError("Split report has no mesh inventory")
    meshes = [
        record
        for record in records
        if isinstance(record, dict) and record.get("class") == "SkeletalMesh"
    ]
    if not meshes:
        raise RuntimePlanError("Split report has no SkeletalMesh records")
    for mesh in meshes:
        if not mesh.get("name") or not mesh.get("path"):
            raise RuntimePlanError("Split mesh record is missing name or path")
    return meshes


def classify_case_meshes(
    case: dict[str, Any], split_report: dict[str, Any]
) -> dict[str, Any]:
    """Map each manifest module to one or more independently imported meshes."""
    if split_report.get("success") is not True:
        raise RuntimePlanError(f"Split import did not pass: {case.get('case_id')}")
    meshes = _skeletal_mesh_records(split_report)
    modules = case.get("modules") or []
    if not modules:
        raise RuntimePlanError(
            f"Outfit case has no declared modules: {case.get('case_id')}"
        )

    scene_rows: list[dict[str, Any]] = []
    for module_index, module in enumerate(modules):
        module_key = module.get("module_key")
        scene_objects = module.get("cc_scene_objects")
        if not module_key or not isinstance(scene_objects, list) or not scene_objects:
            raise RuntimePlanError(
                f"Finalized CC scene evidence is missing for "
                f"{case.get('case_id')}/{module_key or module_index}"
            )
        seen_names: set[str] = set()
        for scene_index, scene_object in enumerate(scene_objects):
            if not isinstance(scene_object, dict) or not scene_object.get("name"):
                raise RuntimePlanError(
                    f"Invalid CC scene object for {case.get('case_id')}/{module_key}"
                )
            normalized = normalize_object_name(scene_object["name"])
            if not normalized:
                raise RuntimePlanError(
                    f"Empty normalized scene name for {case.get('case_id')}/{module_key}"
                )
            if normalized in seen_names:
                continue
            seen_names.add(normalized)
            scene_rows.append(
                {
                    "module_index": module_index,
                    "scene_index": scene_index,
                    "module_key": module_key,
                    "scene_object": scene_object,
                }
            )

    assignments: list[dict[str, Any]] = []
    used_mesh_paths: set[str] = set()
    for row in scene_rows:
        scored = [
            (_mesh_match_score(row["scene_object"]["name"], mesh["name"]), mesh)
            for mesh in meshes
            if mesh["path"] not in used_mesh_paths
        ]
        best_score = max((score for score, _mesh in scored), default=0)
        best = [mesh for score, mesh in scored if score == best_score and score > 0]
        if len(best) != 1:
            candidates = [mesh["path"] for mesh in best]
            raise RuntimePlanError(
                "Expected one split mesh for "
                f"{case.get('case_id')}/{row['module_key']}/"
                f"{row['scene_object']['name']!r}; score={best_score}; "
                f"candidates={candidates}"
            )
        mesh = best[0]
        used_mesh_paths.add(mesh["path"])
        assignments.append(
            {
                **row,
                "match_score": best_score,
                "mesh": mesh,
            }
        )

    by_module: list[dict[str, Any]] = []
    for module_index, module in enumerate(modules):
        matched = [
            item for item in assignments if item["module_index"] == module_index
        ]
        if not matched:
            raise RuntimePlanError(
                f"Module mapped to no split meshes: "
                f"{case.get('case_id')}/{module.get('module_key')}"
            )
        matched.sort(key=lambda item: item["scene_index"])
        by_module.append(
            {
                "module_key": module["module_key"],
                "asset_id": module.get("asset_id"),
                "display_name": module.get("display_name"),
                "slot": module.get("slot"),
                "source": module.get("source"),
                "source_path": module.get("source_path"),
                "cc_scene_objects": [item["scene_object"] for item in matched],
                "mesh_paths": [item["mesh"]["path"] for item in matched],
                "mesh_names": [item["mesh"]["name"] for item in matched],
                "match_scores": [item["match_score"] for item in matched],
            }
        )

    ignored_meshes = [mesh for mesh in meshes if mesh["path"] not in used_mesh_paths]
    return {
        "case_id": case["case_id"],
        "module_count": len(by_module),
        "classified_mesh_count": len(used_mesh_paths),
        "ignored_split_mesh_count": len(ignored_meshes),
        "modules": by_module,
        "ignored_split_meshes": ignored_meshes,
    }


def _require_passed_report(path: Path, mode: str, case_id: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimePlanError(f"Missing {mode} report for {case_id}: {path}")
    report = read_json(path)
    if report.get("mode") != mode or report.get("case_id") != case_id:
        raise RuntimePlanError(f"Unexpected report identity: {path}")
    if report.get("success") is not True:
        raise RuntimePlanError(f"Report did not pass: {path}")
    return report


def _base_runtime_record(
    manifest: dict[str, Any], report_root: Path, sex: str
) -> dict[str, Any]:
    base_case_id = BASE_CASE_IDS[sex]
    base_case = next(
        (
            case
            for case in manifest["cases"]
            if case.get("case_id") == base_case_id
            and case.get("case_role") == "base_body"
            and case.get("sex") == sex
        ),
        None,
    )
    if base_case is None:
        raise RuntimePlanError(f"Missing frozen base case: {base_case_id}")
    report_path = report_root / f"{base_case_id}_import_reference.json"
    report = _require_passed_report(report_path, "import_reference", base_case_id)
    if report.get("requires_auto_setup") is not False:
        raise RuntimePlanError(f"Auto Setup is incomplete for {base_case_id}")
    if report.get("material_quality_passed") is not True:
        raise RuntimePlanError(f"Material quality gate failed for {base_case_id}")
    if report.get("rig_assets_passed") is not True:
        raise RuntimePlanError(f"Rig asset gate failed for {base_case_id}")
    meshes = [
        item
        for item in report.get("assets") or []
        if isinstance(item, dict) and item.get("class") == "SkeletalMesh"
    ]
    if len(meshes) != 1:
        raise RuntimePlanError(
            f"Expected one clothing-free base SkeletalMesh for {base_case_id}, "
            f"found {len(meshes)}"
        )
    mesh = meshes[0]
    if not mesh.get("path") or not mesh.get("skeleton"):
        raise RuntimePlanError(f"Base mesh record is incomplete: {base_case_id}")
    return {
        "sex": sex,
        "bodyfit_id": base_case["bodyfit_id"],
        "base_case_id": base_case_id,
        "body_mesh_path": mesh["path"],
        "skeleton_path": mesh["skeleton"],
        "reference_report": str(report_path.resolve()),
    }


def _component_name(case_id: str, index: int) -> str:
    return f"Outfit_{case_id}_{index:02d}"


def build_runtime_plan(
    manifest: dict[str, Any], report_root: Path
) -> dict[str, Any]:
    if manifest.get("status") != "cc_export_passed":
        raise RuntimePlanError(
            "Runtime planning requires a fully successful finalized CC export"
        )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RuntimePlanError("Manifest has no cases")

    bodyfits: list[dict[str, Any]] = []
    total_classified_meshes = 0
    total_ignored_meshes = 0
    for sex in ("male", "female"):
        base = _base_runtime_record(manifest, report_root, sex)
        runtime_cases: list[dict[str, Any]] = []
        sex_cases = [
            case
            for case in cases
            if case.get("sex") == sex and case.get("case_role") == "outfit_modules"
        ]
        for case in sex_cases:
            case_id = case["case_id"]
            split_report_path = report_root / f"{case_id}_import_split.json"
            validate_report_path = report_root / f"{case_id}_validate_case.json"
            split_report = _require_passed_report(
                split_report_path, "import_split", case_id
            )
            _require_passed_report(validate_report_path, "validate_case", case_id)
            classified = classify_case_meshes(case, split_report)
            total_classified_meshes += classified["classified_mesh_count"]
            total_ignored_meshes += classified["ignored_split_mesh_count"]
            runtime_cases.append(
                {
                    "case_id": case_id,
                    "family": case.get("family"),
                    "coverage_tags": list(case.get("coverage_tags") or []),
                    "split_report": str(split_report_path.resolve()),
                    "validate_report": str(validate_report_path.resolve()),
                    "classification": classified,
                    "source_runtime_variants": list(case.get("runtime_variants") or []),
                }
            )

        if not runtime_cases:
            raise RuntimePlanError(f"No runtime outfit cases for {sex}")
        components: list[dict[str, Any]] = []
        component_by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
        for runtime_case in runtime_cases:
            case_id = runtime_case["case_id"]
            case_component_index = 0
            for module in runtime_case["classification"]["modules"]:
                module_components = []
                for mesh_path, mesh_name in zip(
                    module["mesh_paths"], module["mesh_names"], strict=True
                ):
                    case_component_index += 1
                    component = {
                        "component_name": _component_name(
                            case_id, case_component_index
                        ),
                        "case_id": case_id,
                        "qualified_module_id": f"{case_id}::{module['module_key']}",
                        "module_key": module["module_key"],
                        "slot": module.get("slot"),
                        "mesh_name": mesh_name,
                        "mesh_path": mesh_path,
                    }
                    identity = (case_id, module["module_key"], mesh_path)
                    if identity in component_by_identity:
                        raise RuntimePlanError(
                            f"Duplicate runtime component identity: {identity}"
                        )
                    if any(
                        item["component_name"] == component["component_name"]
                        for item in components
                    ):
                        raise RuntimePlanError(
                            "Duplicate generated runtime component name: "
                            + component["component_name"]
                        )
                    component_by_identity[identity] = component
                    components.append(component)
                    module_components.append(component)
                module["components"] = module_components

        runtime_variants: list[dict[str, Any]] = [
            {
                "case_id": base["base_case_id"],
                "variant_id": "base",
                "qualified_variant_id": f"{base['base_case_id']}::base",
                "purpose": "clothing-free identity and animation leader",
                "enabled_modules": [],
                "disabled_modules": [],
                "enabled_component_names": [],
                "enabled_component_count": 0,
            }
        ]
        for runtime_case in runtime_cases:
            case_id = runtime_case["case_id"]
            module_index = {
                module["module_key"]: module
                for module in runtime_case["classification"]["modules"]
            }
            case_variants = []
            for variant in runtime_case.pop("source_runtime_variants"):
                enabled = list(variant.get("enabled_modules") or [])
                unknown = [key for key in enabled if key not in module_index]
                if unknown:
                    raise RuntimePlanError(
                        f"Variant references unclassified modules: "
                        f"{case_id}/{variant.get('variant_id')}: {unknown}"
                    )
                enabled_components = [
                    component["component_name"]
                    for module_key in enabled
                    for component in module_index[module_key]["components"]
                ]
                if not enabled_components:
                    raise RuntimePlanError(
                        f"Outfit runtime variant is empty: "
                        f"{case_id}/{variant.get('variant_id')}"
                    )
                runtime_variant = {
                    "case_id": case_id,
                    "variant_id": variant["variant_id"],
                    "qualified_variant_id": f"{case_id}::{variant['variant_id']}",
                    "purpose": variant.get("purpose"),
                    "enabled_modules": enabled,
                    "disabled_modules": list(
                        variant.get("disabled_modules") or []
                    ),
                    "enabled_component_names": enabled_components,
                    "enabled_component_count": len(enabled_components),
                }
                case_variants.append(runtime_variant)
                runtime_variants.append(runtime_variant)
            if not case_variants:
                raise RuntimePlanError(f"Outfit case has no runtime variants: {case_id}")
            runtime_case["runtime_variants"] = case_variants

        bodyfit_id = base["bodyfit_id"]
        if not SAFE_SEGMENT.fullmatch(bodyfit_id):
            raise RuntimePlanError(f"Unsafe bodyfit ID: {bodyfit_id}")
        bodyfits.append(
            {
                **base,
                "blueprint_path": (
                    f"{RUNTIME_BLUEPRINT_ROOT}/{bodyfit_id}/"
                    f"BP_DM_{bodyfit_id}_ModularOutfitPilot_v001"
                ),
                "component_count": len(components),
                "component_names": [item["component_name"] for item in components],
                "components": components,
                "runtime_variants": runtime_variants,
                "cases": runtime_cases,
            }
        )

    variant_count = sum(len(bodyfit["runtime_variants"]) for bodyfit in bodyfits)
    return {
        "schema_version": 1,
        "plan_id": "modular_outfit_runtime_plan_20260829_v1",
        "pilot_id": manifest.get("pilot_id"),
        "created_at_utc": utc_now(),
        "status": "classified_ready_for_blueprint_build",
        "runtime_architecture": {
            "identity_and_animation": "one clothing-free FullReference Body per sex",
            "outfit_components": "one hidden hard-reference SkeletalMeshComponent per classified apparel mesh",
            "switching": "toggle registered components on the same actor",
            "pose_sync": "SetLeaderPoseComponent",
            "curve_policy": "Body propagates curves; explicit morph broadcast remains required where used",
            "collision_policy": "Body owns collision; outfit followers use no collision",
            "unclassified_split_meshes": "ignored body, hair, face, and rig duplicates",
        },
        "manifest_path": str(DEFAULT_MANIFEST.resolve()),
        "report_root": str(report_root.resolve()),
        "bodyfit_count": len(bodyfits),
        "runtime_variant_count": variant_count,
        "classified_mesh_count": total_classified_meshes,
        "ignored_split_mesh_count": total_ignored_meshes,
        "bodyfits": bodyfits,
        "production_gaps": [
            "body_surface_hide_masks_not_implemented",
            "cloth_physics_not_validated",
            "visual_clipping_requires_manual_review",
            "hair_outfit_compatibility_requires_manual_review",
            "lod_sync_not_validated",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = read_json(args.manifest.resolve())
    plan = build_runtime_plan(manifest, args.report_root.resolve())
    plan["manifest_path"] = str(args.manifest.resolve())
    write_json(args.output.resolve(), plan)
    print(
        json.dumps(
            {
                "success": True,
                "output": str(args.output.resolve()),
                "bodyfit_count": plan["bodyfit_count"],
                "runtime_variant_count": plan["runtime_variant_count"],
                "classified_mesh_count": plan["classified_mesh_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
