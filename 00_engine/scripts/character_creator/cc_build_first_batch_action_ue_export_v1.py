"""Build the 12-action first-batch CC-to-UE candidate export work order."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
ARTIFACT_ROOT = ENGINE_ROOT / "outputs" / "character_creator_bridge" / "artifacts"
DEFAULT_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v1.json"
DEFAULT_DYNAMIC_REVIEW = (
    ARTIFACT_ROOT
    / "first_batch_action_selection"
    / "dynamic_run_20260820_v1"
    / "dynamic_review_automation.json"
)
DEFAULT_ACTOR_WORK_ORDER = (
    ARTIFACT_ROOT
    / "animation_p0_ue_runtime_pilot"
    / "work_order_20260818_v1"
    / "work_order.json"
)
DEFAULT_BRIDGE_ACTORS = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_face_recipes"
    / "_bridge_inputs"
    / "p0_ue_runtime_pilot_20260818_v1"
)
DEFAULT_EXPORT_ARTIFACT_ROOT = ARTIFACT_ROOT / "first_batch_action_ue_export"
DEFAULT_WORK_ORDER = (
    DEFAULT_EXPORT_ARTIFACT_ROOT
    / "work_order_20260820_v1"
    / "work_order.json"
)
DEFAULT_STAGING_ROOT = DEFAULT_EXPORT_ARTIFACT_ROOT / "staging_20260820_v1"
DEFAULT_FINAL_ROOT = DEFAULT_EXPORT_ARTIFACT_ROOT / "bundle_20260820_v1"
DEFAULT_CONFIG = SCRIPT_ROOT / "cc_first_batch_action_ue_export_20260820_v1.json"

ACTOR_BINDINGS = {
    "female": "p0_female_clothed",
    "male": "p0_male_clothed",
}
BRIDGE_PROJECT_NAMES = {
    "female": "CCSHOW_F02_AVERAGE_001.ccProject",
    "male": "CCSHOW_M02_AVERAGE_001.ccProject",
}


class FirstBatchActionExportBuildError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FirstBatchActionExportBuildError(
            f"Could not read JSON: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise FirstBatchActionExportBuildError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locked_file(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise FirstBatchActionExportBuildError(f"Required file is missing: {path}")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def verified_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    actual = locked_file(Path(str(record.get("path", ""))))
    expected_bytes = record.get("bytes", record.get("size_bytes"))
    if expected_bytes is not None and actual["bytes"] != int(expected_bytes):
        raise FirstBatchActionExportBuildError(f"{label} size drifted")
    if record.get("sha256") != actual["sha256"]:
        raise FirstBatchActionExportBuildError(f"{label} hash drifted")
    return actual


def safe_export_basename(action_id: str) -> str:
    value = "A_" + action_id.removeprefix("ACT_")
    if len(value) > 64 or not value.replace("_", "").isalnum():
        raise FirstBatchActionExportBuildError(
            f"Invalid action export basename: {value}"
        )
    return value


def build_first_batch_action_export(
    registry_path: Path = DEFAULT_REGISTRY,
    dynamic_review_path: Path = DEFAULT_DYNAMIC_REVIEW,
    actor_work_order_path: Path = DEFAULT_ACTOR_WORK_ORDER,
    bridge_actor_root: Path = DEFAULT_BRIDGE_ACTORS,
    work_order_output: Path = DEFAULT_WORK_ORDER,
    config_output: Path = DEFAULT_CONFIG,
    staging_root: Path = DEFAULT_STAGING_ROOT,
    final_root: Path = DEFAULT_FINAL_ROOT,
) -> dict[str, Any]:
    registry_path = registry_path.resolve()
    dynamic_review_path = dynamic_review_path.resolve()
    actor_work_order_path = actor_work_order_path.resolve()
    registry = read_json(registry_path)
    review = read_json(dynamic_review_path)
    actor_work_order = read_json(actor_work_order_path)

    if registry.get("status") != "frozen_pending_cc_and_ue_validation":
        raise FirstBatchActionExportBuildError("Action registry is not frozen")
    actions = registry.get("actions") or []
    review_cases = {item.get("case_id"): item for item in review.get("cases") or []}
    if len(actions) != 12 or len(review_cases) != 12:
        raise FirstBatchActionExportBuildError("Expected exactly 12 actions")
    if review.get("status") != "automation_complete_pending_visual_review":
        raise FirstBatchActionExportBuildError("CC dynamic review is incomplete")

    source_actors = actor_work_order.get("actors") or []
    actor_by_sex = {item.get("sex"): item for item in source_actors}
    if set(actor_by_sex) != set(ACTOR_BINDINGS):
        raise FirstBatchActionExportBuildError("F02/M02 actor bindings are incomplete")
    actors = []
    actor_overrides = {}
    presets = []
    actor_export_names = {}
    for sex in ("female", "male"):
        actor = dict(actor_by_sex[sex])
        if actor.get("actor_binding_id") != ACTOR_BINDINGS[sex]:
            raise FirstBatchActionExportBuildError(
                f"Unexpected {sex} actor binding"
            )
        actor["source_project"] = verified_record(
            actor.get("source_project") or {}, f"{sex} actor source"
        )
        actor["character_export_status"] = "pending_cc_export"
        actor["unreal_import_status"] = "pending"
        actors.append(actor)

        bridge_project = verified_record(
            {
                **actor["source_project"],
                "path": str(bridge_actor_root.resolve() / BRIDGE_PROJECT_NAMES[sex]),
            },
            f"{sex} bridge actor",
        )
        if bridge_project["sha256"] != actor["source_project"]["sha256"]:
            raise FirstBatchActionExportBuildError(
                f"{sex} bridge actor differs from source"
            )
        actor_overrides[actor["actor_binding_id"]] = bridge_project
        presets.append(
            {
                "preset_id": actor["character_id"],
                "sex": sex,
                "base_avatar": {
                    "path": str(
                        Path(
                            r"D:\CharacterCreator_sucai\Reallusion Templates"
                            r"\Actor\Character\_Mixer Ready\Base"
                            + (r"\_HD Neutral F.ccAvatar" if sex == "female" else r"\_HD Neutral M.ccAvatar")
                        )
                    )
                },
                "source_project": bridge_project,
            }
        )
        actor_export_names[actor["actor_binding_id"]] = {
            "directory": "female" if sex == "female" else "male",
            "reference_basename": (
                "F02_FirstBatchReference"
                if sex == "female"
                else "M02_FirstBatchReference"
            ),
        }

    motions = []
    motion_export_names = {}
    root_counts: dict[str, int] = {}
    for action in actions:
        action_id = action.get("action_id")
        case_id = str(action_id).lower()
        evidence = review_cases.get(case_id)
        if evidence is None or evidence.get("load_status") != "succeeded":
            raise FirstBatchActionExportBuildError(
                f"Action lacks successful CC evidence: {action_id}"
            )
        if evidence.get("facial_channel_class") != "none_detected":
            raise FirstBatchActionExportBuildError(
                f"Action occupies facial channels: {action_id}"
            )
        if evidence.get("hidden_dependencies"):
            raise FirstBatchActionExportBuildError(
                f"Action has hidden dependencies: {action_id}"
            )
        sex = action.get("sex")
        actor_binding = ACTOR_BINDINGS.get(sex)
        if actor_binding is None:
            raise FirstBatchActionExportBuildError(
                f"Action has unsupported sex: {action_id}"
            )
        root_class = evidence.get("root_motion_class")
        if root_class not in {
            "in_place_candidate",
            "moving_candidate",
            "ambiguous",
        }:
            raise FirstBatchActionExportBuildError(
                f"Action has unsupported root evidence: {action_id}"
            )
        root_counts[root_class] = root_counts.get(root_class, 0) + 1
        source_motion = verified_record(
            action.get("runtime_file") or {}, f"action {action_id}"
        )
        root_evidence = (evidence.get("automation_evidence") or {}).get(
            "root_motion_evidence"
        ) or {}
        motions.append(
            {
                "gate_role": action_id,
                "case_id": case_id,
                "action_id": action_id,
                "actor_binding_id": actor_binding,
                "source_motion": source_motion,
                "motion_role": action.get("semantic_family"),
                "temporal_usage": "pending_visual_assignment",
                "root_motion": {
                    "classification": root_class,
                    "policy": (
                        "in_place"
                        if root_class == "in_place_candidate"
                        else "preserve_source_root_motion"
                    ),
                    "horizontal_displacement_cm": root_evidence.get(
                        "first_to_last_horizontal_distance_cm"
                    ),
                    "ue_validation_status": "pending",
                },
                "facial_channels": "none",
                "facial_reuse_policy": "replaceable",
                "cc_visual_status": "pending_user_review",
                "cc_export_status": "pending",
                "unreal_import_status": "pending",
                "unreal_runtime_status": "pending",
                "production_status": "not_approved",
            }
        )
        motion_export_names[case_id] = safe_export_basename(str(action_id))

    work_order = {
        "schema_version": 1,
        "work_order_id": "cc_first_batch_action_ue_export_20260820_v1",
        "generated_at": now(),
        "status": "ready_for_cc_export",
        "production_status": "not_approved",
        "visual_status": "pending_user_review",
        "provenance": {
            "action_registry": locked_file(registry_path),
            "cc_dynamic_review": locked_file(dynamic_review_path),
            "source_actor_work_order": locked_file(actor_work_order_path),
        },
        "scope": {
            "actor_count": 2,
            "motion_count": 12,
            "female_motion_count": 6,
            "male_motion_count": 6,
            "root_motion_counts": root_counts,
            "generated_clothed_characters_required": True,
            "production_approved_count": 0,
        },
        "actors": actors,
        "motions": motions,
        "export": {
            "root": str(final_root.resolve()),
            "character_mode": "clothed_reference_character_once_per_actor",
            "animation_mode": "motion_fbx_bound_to_matching_actor_skeleton",
            "auto_material_json_required": True,
            "morph_export_required": True,
            "facial_expression_export_required": True,
            "status": "pending_cc",
        },
        "unreal": {
            "vendor_root": "/Game/Vendor/Reallusion/CC5/FirstBatchActions",
            "datamake_root": "/Game/DataMake/Animations/CC5/FirstBatchActions",
            "required_runtime_checks": [
                "skeleton_binding",
                "root_motion_direction_and_distance",
                "clip_duration",
                "reusable_face_layer_composition",
                "clothing_deformation",
            ],
            "status": "pending_import",
        },
        "execution_order": [
            "cc_export_two_clothed_reference_characters",
            "cc_export_twelve_bound_motion_fbxs",
            "patch_auxiliary_bone_names",
            "import_motion_fbxs_under_vendor_root",
            "run_unreal_runtime_matrix",
            "record_user_visual_decision",
        ],
        "stop_conditions": [
            "unknown_modal_dialog",
            "source_hash_drift",
            "skeleton_mismatch",
            "unreal_editor_crash",
        ],
    }
    write_json(work_order_output.resolve(), work_order)

    config = {
        "schema_version": 1,
        "library_id": "cc_first_batch_action_ue_export_20260820_v1",
        "diagnostic_mode": "animation_p0_ue_runtime_export",
        "presets": presets,
        "animation_p0_ue_export": {
            "work_order_path": str(work_order_output.resolve()),
            "work_order_sha256": sha256_file(work_order_output.resolve()),
            "staging_output_root": str(staging_root.resolve()),
            "actor_project_overrides": actor_overrides,
            "expected_source_timeline": {
                actor_id: {"body_clip_count": 1, "face_clip_count": 1}
                for actor_id in ACTOR_BINDINGS.values()
            },
            "export_names": {
                "actors": actor_export_names,
                "motions": motion_export_names,
            },
            "export_timeout_seconds": 900.0,
        },
    }
    write_json(config_output.resolve(), config)
    return {
        "work_order": str(work_order_output.resolve()),
        "config": str(config_output.resolve()),
        "staging_root": str(staging_root.resolve()),
        "final_root": str(final_root.resolve()),
        "actor_count": 2,
        "motion_count": 12,
        "root_motion_counts": root_counts,
        "status": "ready_for_cc_export_pending_user_visual_review",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--dynamic-review", type=Path, default=DEFAULT_DYNAMIC_REVIEW)
    parser.add_argument("--actor-work-order", type=Path, default=DEFAULT_ACTOR_WORK_ORDER)
    parser.add_argument("--bridge-actor-root", type=Path, default=DEFAULT_BRIDGE_ACTORS)
    parser.add_argument("--work-order-output", type=Path, default=DEFAULT_WORK_ORDER)
    parser.add_argument("--config-output", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--staging-root", type=Path, default=DEFAULT_STAGING_ROOT)
    parser.add_argument("--final-root", type=Path, default=DEFAULT_FINAL_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_first_batch_action_export(
        args.registry,
        args.dynamic_review,
        args.actor_work_order,
        args.bridge_actor_root,
        args.work_order_output,
        args.config_output,
        args.staging_root,
        args.final_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
