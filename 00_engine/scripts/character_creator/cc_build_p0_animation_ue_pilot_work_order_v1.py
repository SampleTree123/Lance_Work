"""Build a UE runtime Pilot work order using generated clothed CC characters."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_REGISTRY = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_candidate_registry"
    / "registry_20260818_v1"
    / "candidate_registry.json"
)
DEFAULT_SPEC = SCRIPT_ROOT / "cc_p0_animation_ue_pilot_spec_20260818_v1.json"
DEFAULT_SHOWCASE_MANIFEST = SCRIPT_ROOT / "cc_character_showcase_10_20260803_v1.json"
DEFAULT_SHOWCASE_SUMMARY = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "character_showcase_10_20260803_01"
    / "review_20260803_01"
    / "showcase_summary.json"
)
DEFAULT_OUTPUT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_ue_runtime_pilot"
    / "work_order_20260818_v1"
    / "work_order.json"
)
REQUIRED_GATE_ROLES = {
    "female_root_motion_walk",
    "male_root_motion_walk",
    "in_place_loop",
    "one_shot_gesture",
}


class UEPilotWorkOrderError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UEPilotWorkOrderError(f"Could not read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise UEPilotWorkOrderError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locked_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise UEPilotWorkOrderError(f"Required file is missing: {resolved}")
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def unique(items: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            raise UEPilotWorkOrderError(f"{label} has no {key}")
        if value in result:
            raise UEPilotWorkOrderError(f"{label} duplicates {key}: {value}")
        result[value] = item
    return result


def build_work_order(
    registry_path: Path = DEFAULT_REGISTRY,
    spec_path: Path = DEFAULT_SPEC,
    showcase_manifest_path: Path = DEFAULT_SHOWCASE_MANIFEST,
    showcase_summary_path: Path = DEFAULT_SHOWCASE_SUMMARY,
) -> dict[str, Any]:
    registry_path = registry_path.resolve()
    spec_path = spec_path.resolve()
    showcase_manifest_path = showcase_manifest_path.resolve()
    showcase_summary_path = showcase_summary_path.resolve()
    registry = read_json(registry_path)
    spec = read_json(spec_path)
    showcase = read_json(showcase_manifest_path)
    summary = read_json(showcase_summary_path)

    if registry.get("registry_id") != spec.get("source_registry_id"):
        raise UEPilotWorkOrderError("Pilot spec and candidate registry IDs differ")
    if registry.get("status") != "registered_pending_ue_runtime_validation":
        raise UEPilotWorkOrderError("Candidate registry is not ready for UE Pilot")
    if (registry.get("counts") or {}).get("production_approved_count") != 0:
        raise UEPilotWorkOrderError("Candidate registry leaks production approval")
    candidates = unique(registry.get("candidates") or [], "case_id", "Registry")

    policy = spec.get("character_policy") or {}
    if not policy.get("generated_clothed_characters_required"):
        raise UEPilotWorkOrderError("UE Pilot must require generated clothed characters")
    if not policy.get("gray_body_templates_forbidden"):
        raise UEPilotWorkOrderError("UE Pilot must forbid gray body templates")
    required_slots = set(policy.get("required_appearance_slots") or [])
    if required_slots != {"upper", "lower", "footwear"}:
        raise UEPilotWorkOrderError("Unexpected required clothing slots")

    showcase_presets = unique(showcase.get("presets") or [], "character_id", "Showcase")
    summary_characters = unique(summary.get("characters") or [], "character_id", "Summary")
    if summary.get("status") != "passed":
        raise UEPilotWorkOrderError("Character showcase summary did not pass")

    actors = unique(spec.get("actors") or [], "actor_binding_id", "Actor spec")
    if len(actors) != 2 or {item.get("sex") for item in actors.values()} != {
        "female",
        "male",
    }:
        raise UEPilotWorkOrderError("UE Pilot requires one female and one male actor")

    actor_records: list[dict[str, Any]] = []
    for binding_id, actor in actors.items():
        character_id = actor.get("character_id")
        preset = showcase_presets.get(character_id)
        summary_item = summary_characters.get(character_id)
        if preset is None or summary_item is None:
            raise UEPilotWorkOrderError(f"Unknown generated character: {character_id}")
        for field in ("sex", "bodyfit_id", "appearance_recipe_id"):
            if actor.get(field) != preset.get(field):
                raise UEPilotWorkOrderError(
                    f"Actor {binding_id} conflicts with showcase field {field}"
                )
        appearance_assets = (preset.get("appearance_recipe") or {}).get("assets") or []
        slots = {item.get("slot") for item in appearance_assets}
        if not required_slots.issubset(slots):
            raise UEPilotWorkOrderError(
                f"Generated character is not fully clothed: {character_id}"
            )

        expected_project = actor.get("saved_project") or {}
        project_path = Path(expected_project.get("path", ""))
        if not project_path.is_file():
            raise UEPilotWorkOrderError(f"Saved character project is missing: {character_id}")
        if project_path.stat().st_size != expected_project.get("bytes"):
            raise UEPilotWorkOrderError(f"Saved character project size drifted: {character_id}")
        project_hash = sha256_file(project_path)
        if project_hash != expected_project.get("sha256"):
            raise UEPilotWorkOrderError(f"Saved character project hash drifted: {character_id}")
        summary_project = summary_item.get("project") or {}
        if Path(summary_project.get("review_path", "")).resolve() != project_path.resolve():
            raise UEPilotWorkOrderError(f"Summary project path differs: {character_id}")
        if summary_project.get("sha256") != project_hash:
            raise UEPilotWorkOrderError(f"Summary project hash differs: {character_id}")

        actor_records.append(
            {
                "actor_binding_id": binding_id,
                "character_id": character_id,
                "sex": actor["sex"],
                "bodyfit_id": actor["bodyfit_id"],
                "appearance_recipe_id": actor["appearance_recipe_id"],
                "appearance_assets": [
                    {
                        "slot": item.get("slot"),
                        "asset_id": item.get("asset_id"),
                        "display_name": item.get("display_name"),
                    }
                    for item in appearance_assets
                    if item.get("slot") in required_slots
                ],
                "source_project": {
                    "path": str(project_path.resolve()),
                    "bytes": project_path.stat().st_size,
                    "sha256": project_hash,
                },
                "character_export_status": "pending_cc_export",
                "unreal_import_status": "pending",
            }
        )

    selected_specs = unique(spec.get("motion_cases") or [], "gate_role", "Motion spec")
    if set(selected_specs) != REQUIRED_GATE_ROLES:
        raise UEPilotWorkOrderError("UE Pilot representative role set is incomplete")
    selected_ids: set[str] = set()
    motion_records: list[dict[str, Any]] = []
    for gate_role, selected in selected_specs.items():
        case_id = selected.get("case_id")
        if case_id in selected_ids:
            raise UEPilotWorkOrderError(f"UE Pilot repeats a motion: {case_id}")
        selected_ids.add(case_id)
        candidate = candidates.get(case_id)
        if candidate is None:
            raise UEPilotWorkOrderError(f"UE Pilot references unknown motion: {case_id}")
        actor_binding_id = selected.get("actor_binding_id")
        actor = actors.get(actor_binding_id)
        if actor is None:
            raise UEPilotWorkOrderError(f"Unknown actor binding: {actor_binding_id}")
        if candidate.get("production_status") != "not_approved":
            raise UEPilotWorkOrderError("Representative motion must remain unapproved")
        if candidate.get("facial_reuse_policy") != "replaceable":
            raise UEPilotWorkOrderError("Representative motion must support face layering")
        if gate_role == "in_place_loop" and candidate.get("temporal_usage") != "loop_candidate":
            raise UEPilotWorkOrderError("Loop role does not reference a loop candidate")
        if gate_role == "one_shot_gesture" and candidate.get("temporal_usage") != "one_shot":
            raise UEPilotWorkOrderError("Gesture role does not reference a one-shot clip")
        if gate_role.endswith("root_motion_walk") and (
            (candidate.get("root_motion") or {}).get("policy")
            != "preserve_source_root_motion"
        ):
            raise UEPilotWorkOrderError("Walk role does not preserve source Root Motion")
        if gate_role.startswith("female_") and actor.get("sex") != "female":
            raise UEPilotWorkOrderError("Female role is bound to a non-female actor")
        if gate_role.startswith("male_") and actor.get("sex") != "male":
            raise UEPilotWorkOrderError("Male role is bound to a non-male actor")

        motion_records.append(
            {
                "gate_role": gate_role,
                "case_id": case_id,
                "actor_binding_id": actor_binding_id,
                "source_motion": candidate.get("source_motion"),
                "motion_role": candidate.get("motion_role"),
                "temporal_usage": candidate.get("temporal_usage"),
                "root_motion": candidate.get("root_motion"),
                "facial_channels": candidate.get("facial_channels"),
                "facial_reuse_policy": candidate.get("facial_reuse_policy"),
                "cc_export_status": "pending",
                "unreal_import_status": "pending",
                "unreal_runtime_status": "pending",
                "production_status": "not_approved",
            }
        )

    return {
        "schema_version": 1,
        "work_order_id": "cc_p0_animation_ue_runtime_pilot_20260818_v1",
        "generated_at": now(),
        "status": "ready_for_cc_export",
        "provenance": {
            "candidate_registry": locked_file(registry_path),
            "pilot_spec": locked_file(spec_path),
            "character_showcase_manifest": locked_file(showcase_manifest_path),
            "character_showcase_summary": locked_file(showcase_summary_path),
        },
        "scope": {
            "actor_count": len(actor_records),
            "motion_count": len(motion_records),
            "generated_clothed_characters_required": True,
            "gray_body_templates_forbidden": True,
            "production_approved_count": 0,
        },
        "actors": actor_records,
        "motions": motion_records,
        "export": {
            "root": spec.get("export_root"),
            "character_mode": "clothed_reference_character_once_per_actor",
            "animation_mode": "motion_fbx_bound_to_matching_actor_skeleton",
            "auto_material_json_required": True,
            "morph_export_required": True,
            "facial_expression_export_required": True,
            "status": "pending_cc",
        },
        "unreal": {
            **(spec.get("unreal_destination") or {}),
            "required_runtime_checks": [
                "skeleton_binding",
                "root_motion_direction_and_distance",
                "in_place_loop_seam",
                "one_shot_completion",
                "reusable_face_layer_composition",
                "clothing_deformation",
                "hair_and_clothing_collision_visual_check",
            ],
            "status": "pending_import",
        },
        "execution_order": [
            "cc_export_two_clothed_reference_characters",
            "cc_export_four_bound_motion_fbxs",
            "close_cc_and_open_unreal",
            "import_under_vendor_root",
            "create_datamake_runtime_wrappers",
            "run_four_role_runtime_matrix",
            "record_machine_and_visual_decisions",
        ],
        "stop_conditions": [
            "unknown_modal_dialog",
            "saved_character_project_hash_drift",
            "skeleton_mismatch",
            "missing_auto_setup_material_sidecar",
            "unreal_editor_crash",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--showcase-manifest", type=Path, default=DEFAULT_SHOWCASE_MANIFEST)
    parser.add_argument("--showcase-summary", type=Path, default=DEFAULT_SHOWCASE_SUMMARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    value = build_work_order(
        args.registry,
        args.spec,
        args.showcase_manifest,
        args.showcase_summary,
    )
    write_json(args.output.resolve(), value)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
