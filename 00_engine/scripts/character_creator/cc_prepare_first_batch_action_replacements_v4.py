"""Prepare the licensed-export-safe v4 action set for the first data batch."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v3.json"
DEFAULT_PREVIEW_TEMPLATE = (
    SCRIPT_ROOT / "cc_first_batch_action_full_preview_delta_20260820_v3.json"
)
DEFAULT_OUTPUT_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260821_v4.json"
DEFAULT_OUTPUT_PREVIEW = (
    SCRIPT_ROOT / "cc_first_batch_action_full_preview_delta_20260821_v4.json"
)
DEFAULT_RUNTIME_ROOT = (
    SCRIPT_ROOT / "runtime_assets" / "first_batch_actions_20260821_v4" / "motions"
)
DEFAULT_EXPORT_ROOT = Path(
    r"D:\UE\exports\character_creator\first_data_batch_20260820_v1\motions"
)
DEFAULT_SOURCE_ROOT = Path(
    r"D:\BaiduNetdiskDownload\iclone动作\P0_Core_Everyday\1"
)


REPLACEMENTS = {
    "ACT_F01_ARGUMENT_BOSSY": {
        "action_id": "ACT_F01_SEXY_DANCE",
        "case_id": "act_f01_sexy_dance",
        "filename": "Sexy Dance.rlMotion",
        "semantic_family": "dance_gesture",
        "runtime_filename": "01_act_f01_sexy_dance.rlMotion",
        "export_filename": "A_F01_SEXY_DANCE.fbx",
        "raw_export_filename": "1_Motion.Fbx",
    },
    "ACT_M01_ARGUMENT_SURRENDER": {
        "action_id": "ACT_M01_BATTLE_DANCE",
        "case_id": "act_m01_battle_dance",
        "filename": "Battle Dance.rlMotion",
        "semantic_family": "dance_gesture",
        "runtime_filename": "07_act_m01_battle_dance.rlMotion",
        "export_filename": "A_M01_BATTLE_DANCE.fbx",
        "raw_export_filename": "1_Battle_Dance_Motion.Fbx",
    },
    "ACT_M06_MOVING_ARGUMENT_DECLINE": {
        "action_id": "ACT_M06_CHEER_HANDS_STEP_DANCE",
        "case_id": "act_m06_cheer_hands_step_dance",
        "filename": "Cheer Hands & Step Dance.rlMotion",
        "semantic_family": "celebration_dance",
        "runtime_filename": "12_act_m06_cheer_hands_step_dance.rlMotion",
        "export_filename": "A_M06_CHEER_HANDS_STEP_DANCE.fbx",
        "raw_export_filename": "1_Cheer_Hands___Step_Dance_Motion.Fbx",
    },
}


UNCHANGED_EXPORTS = {
    "ACT_F02_CATCH_BREATH": (
        "1_02_act_f02_catch_breath_Motion.Fbx",
        "A_F02_CATCH_BREATH.fbx",
    ),
    "ACT_F03_AUDIENCE_01": (
        "1_03_act_f03_audience_01_Motion.Fbx",
        "A_F03_AUDIENCE_01.fbx",
    ),
    "ACT_F04_AUDIENCE_09": (
        "1_04_act_f04_audience_09_Motion.Fbx",
        "A_F04_AUDIENCE_09.fbx",
    ),
    "ACT_F05_TIE_SHOES": (
        "1_05_act_f05_tie_shoes_Motion.Fbx",
        "A_F05_TIE_SHOES.fbx",
    ),
    "ACT_F06_ELEVATOR_GREETING": (
        "1_06_act_f06_elevator_greeting_Motion.Fbx",
        "A_F06_ELEVATOR_GREETING.fbx",
    ),
    "ACT_M02_AUDIENCE_01": (
        "1_08_act_m02_audience_01_Motion.Fbx",
        "A_M02_AUDIENCE_01.fbx",
    ),
    "ACT_M03_AUDIENCE_12": (
        "1_09_act_m03_audience_12_Motion.Fbx",
        "A_M03_AUDIENCE_12.fbx",
    ),
    "ACT_M04_LIVING_ROOM_SWING": (
        "1_10_act_m04_living_room_swing_Motion.Fbx",
        "A_M04_LIVING_ROOM_SWING.fbx",
    ),
    "ACT_M05_ELEVATOR_GREETING": (
        "1_11_act_m05_elevator_greeting_Motion.Fbx",
        "A_M05_ELEVATOR_GREETING.fbx",
    ),
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
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


def file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return {
        "path": str(resolved),
        "size_bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def copy_locked(source: Path, destination: Path) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        if sha256_file(source) != sha256_file(destination):
            raise RuntimeError(f"Destination differs from source: {destination}")
    else:
        shutil.copy2(source, destination)
    return file_record(destination)


def normalize_export(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        if source.is_file() and sha256_file(source) != sha256_file(destination):
            raise RuntimeError(f"Conflicting manual exports: {source} and {destination}")
    elif source.is_file():
        source.replace(destination)
    else:
        raise FileNotFoundError(f"Neither raw nor canonical export exists: {source}")
    return file_record(destination)


def replacement_row(
    old_row: dict[str, Any],
    spec: dict[str, str],
    source_root: Path,
    runtime_root: Path,
) -> dict[str, Any]:
    source_path = source_root / spec["filename"]
    source = file_record(source_path)
    runtime = copy_locked(source_path, runtime_root / spec["runtime_filename"])
    motion_token = runtime["sha256"][:12]
    return {
        "action_id": spec["action_id"],
        "sex": old_row["sex"],
        "actor_id": old_row["actor_id"],
        "semantic_family": spec["semantic_family"],
        "motion_id": f"motion-p0-user-replacement-{motion_token}",
        "filename": spec["filename"],
        "source_inventory_review_bucket": "user_replacement",
        "source_package": "P0_Core_Everyday/1",
        "source_container_relative_path": "P0_Core_Everyday/1",
        "source_member_path": spec["filename"],
        "source_file": source,
        "runtime_file": runtime,
        "user_selection_status": "selected_no_required_prop_reported",
        "dynamic_review_status": "pending_replacement_review",
        "ue_validation_status": "pending",
        "production_status": "not_approved",
        "replaces_action_id": old_row["action_id"],
        "replacement_reason": "source motion could not pass CC external-export license gate",
    }


def unchanged_row(
    row: dict[str, Any],
    runtime_root: Path,
) -> dict[str, Any]:
    result = copy.deepcopy(row)
    source_runtime = Path(row["runtime_file"]["path"])
    runtime = copy_locked(source_runtime, runtime_root / source_runtime.name)
    result["runtime_file"] = runtime
    return result


def build_registry(
    source_registry: dict[str, Any],
    source_root: Path,
    runtime_root: Path,
    export_root: Path,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    replacement_history = []
    for row in source_registry.get("actions") or []:
        old_id = row["action_id"]
        spec = REPLACEMENTS.get(old_id)
        if spec:
            new_row = replacement_row(row, spec, source_root, runtime_root)
            replacement_history.append(
                {
                    "removed_action_id": old_id,
                    "replacement_action_id": spec["action_id"],
                    "reason": new_row["replacement_reason"],
                }
            )
        else:
            new_row = unchanged_row(row, runtime_root)
        sex_root = export_root / new_row["sex"]
        if spec:
            raw_name = spec["raw_export_filename"]
            export_name = spec["export_filename"]
        else:
            raw_name, export_name = UNCHANGED_EXPORTS[old_id]
        new_row["export_fbx"] = normalize_export(
            sex_root / raw_name,
            sex_root / export_name,
        )
        new_row["cc_export_status"] = "validated_file_present"
        actions.append(new_row)

    actions.sort(key=lambda item: item["action_id"])
    if len(actions) != 12:
        raise RuntimeError(f"Expected 12 actions, got {len(actions)}")
    sex_counts = {
        sex: sum(item["sex"] == sex for item in actions)
        for sex in ("female", "male")
    }
    if sex_counts != {"female": 6, "male": 6}:
        raise RuntimeError(f"Unexpected action sex counts: {sex_counts}")

    result = copy.deepcopy(source_registry)
    result["registry_id"] = "first_batch_action_registry_20260821_v4"
    result["generated_at"] = now()
    result["status"] = "frozen_pending_replacement_window_and_ue_validation"
    result["cardinality_contract"]["physical_action_assets"] = 12
    result["actions"] = actions
    result["replacement_history"] = replacement_history
    result["export_summary"] = {
        "status": "12_manual_fbx_files_present",
        "export_root": str(export_root.resolve()),
        "female_actions": 6,
        "male_actions": 6,
        "physical_action_assets": 12,
    }
    return result


def preview_case(row: dict[str, Any]) -> dict[str, Any]:
    case_id = row["action_id"].lower()
    return {
        "case_id": case_id,
        "motion_id": row["motion_id"],
        "filename": row["filename"],
        "source_format": ".rlmotion",
        "format_generation": "current",
        "review_family": row["semantic_family"],
        "loop_hint": "unknown",
        "semantic_tags": [row["semantic_family"]],
        "motion": row["runtime_file"],
        "review_status": "pending_cc_dynamic_review",
        "production_status": "not_approved",
        "action_id": row["action_id"],
        "source_review_bucket": "user_replacement",
        "user_selected": True,
        "required_prop_reported": False,
    }


def build_preview_support_documents(
    registry: dict[str, Any],
    runtime_root: Path,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    pilot_id = "cc_first_batch_action_replacements_20260821_v4"
    replacement_rows = sorted(
        (
            item
            for item in registry["actions"]
            if item.get("replaces_action_id")
        ),
        key=lambda item: item["action_id"],
    )
    cases = []
    review_cases = []
    for row in replacement_rows:
        case_id = row["action_id"].lower()
        cases.append(
            {
                "case_id": case_id,
                "motion_id": row["motion_id"],
                "filename": row["filename"],
                "source_format": ".rlmotion",
                "format_generation": "current",
                "package_name": row["source_package"],
                "source_container_relative_path": row[
                    "source_container_relative_path"
                ],
                "source_member_path": row["source_member_path"],
                "sex_hint": row["sex"],
                "semantic_tags": [row["semantic_family"]],
                "dependency_class": "standalone_candidate",
                "review_bucket": "user_replacement",
                "pilot_actor_preset_id": row["actor_id"],
                "review_family": row["semantic_family"],
                "loop_hint": "unknown",
                "extracted_file": row["runtime_file"],
                "selected_loose_file": row["source_file"],
                "review_status": "pending_cc_dynamic_review",
                "production_status": "not_approved",
            }
        )
        review_cases.append(
            {
                "case_id": case_id,
                "motion_id": row["motion_id"],
                "load_status": "not_run",
                "motion_length_frames": None,
                "fps": None,
                "loop_class": "pending",
                "root_motion_class": "pending",
                "facial_channel_class": "pending",
                "hidden_dependencies": [],
                "visual_decision": "pending",
                "notes": [],
            }
        )

    support_root = runtime_root.parent
    pilot_path = support_root / "pilot_manifest.json"
    review_path = support_root / "dynamic_review.json"
    write_json(
        pilot_path,
        {
            "schema_version": 1,
            "pilot_id": pilot_id,
            "generated_at": now(),
            "status": "staged_pending_cc_dynamic_review",
            "boundaries": [
                "User replacement selection is not production approval.",
                "All three motions still require CC playback and UE retarget gates.",
            ],
            "counts": {
                "case_count": len(cases),
                "by_pilot_actor": {"F02_Average": 1, "M02_Average": 2},
                "by_source_format": {".rlmotion": 3},
                "production_approved_count": 0,
            },
            "cases": cases,
        },
    )
    write_json(
        review_path,
        {
            "schema_version": 1,
            "pilot_id": pilot_id,
            "status": "not_started",
            "required_fields": [
                "load_status",
                "motion_length_frames",
                "loop_class",
                "root_motion_class",
                "facial_channel_class",
                "hidden_dependencies",
                "visual_decision",
            ],
            "cases": review_cases,
        },
    )
    pilot_record = file_record(pilot_path)
    pilot_record["pilot_id"] = pilot_id
    return pilot_id, pilot_record, file_record(review_path)


def build_preview(
    template: dict[str, Any],
    registry: dict[str, Any],
    registry_path: Path,
    runtime_root: Path,
) -> dict[str, Any]:
    result = copy.deepcopy(template)
    replacements = {
        item["action_id"]: item
        for item in registry["actions"]
        if item.get("replaces_action_id")
    }
    by_sex = {
        sex: [item for item in replacements.values() if item["sex"] == sex]
        for sex in ("female", "male")
    }
    template_presets = {item["sex"]: item for item in template["presets"]}
    presets = []
    for sex in ("female", "male"):
        preset = copy.deepcopy(template_presets[sex])
        preset["motion_cases"] = [preview_case(item) for item in sorted(
            by_sex[sex], key=lambda value: value["action_id"]
        )]
        presets.append(preset)

    result["library_id"] = "cc_first_batch_action_full_preview_20260821_v4_delta"
    result["generated_at"] = now()
    result["status"] = "replacement_full_preview_capture_planned"
    result["source_action_registry"] = file_record(registry_path)
    _, pilot_record, review_record = build_preview_support_documents(
        registry,
        runtime_root,
    )
    result["source_pilot_manifest"] = pilot_record
    result["source_dynamic_review_template"] = review_record
    result["presets"] = presets
    result["counts"] = {
        "actor_count": 2,
        "motion_case_count": 3,
        "sample_count_per_motion": None,
        "expected_image_count": None,
        "by_actor": {"F02_Average": 1, "M02_Average": 2},
        "by_source_format": {".rlmotion": 3},
        "production_approved_count": 0,
        "case_count": 3,
        "preview_fps": result["capture_policy"]["preview_fps"],
    }
    result["selection_override"] = {
        "authority": "user",
        "source_review_buckets": {"user_replacement": 3},
        "reported_required_prop_count": 0,
        "dynamic_gate_still_required": True,
        "production_approval_granted": False,
    }
    result["subset_case_ids"] = sorted(
        case["case_id"]
        for preset in presets
        for case in preset["motion_cases"]
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-registry", type=Path, default=DEFAULT_SOURCE_REGISTRY)
    parser.add_argument("--preview-template", type=Path, default=DEFAULT_PREVIEW_TEMPLATE)
    parser.add_argument("--output-registry", type=Path, default=DEFAULT_OUTPUT_REGISTRY)
    parser.add_argument("--output-preview", type=Path, default=DEFAULT_OUTPUT_PREVIEW)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_registry = read_json(args.source_registry)
    template = read_json(args.preview_template)
    registry = build_registry(
        source_registry,
        args.source_root,
        args.runtime_root,
        args.export_root,
    )
    write_json(args.output_registry, registry)
    preview = build_preview(
        template,
        registry,
        args.output_registry,
        args.runtime_root,
    )
    write_json(args.output_preview, preview)
    print(json.dumps({
        "registry": str(args.output_registry.resolve()),
        "preview": str(args.output_preview.resolve()),
        "export_summary": registry["export_summary"],
        "replacement_history": registry["replacement_history"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
