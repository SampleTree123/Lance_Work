"""Freeze the revised first-batch action set and build its CC dynamic gate.

The user-selected files are loose ``.rlMotion`` and ``.iMotion`` assets. This
builder binds
them back to the hash-audited P0 inventory, stages immutable runtime copies
inside the CC Bridge input boundary, and emits a clothed F02/M02 review gate.
Selection is never treated as production approval; CC and UE validation still
own that decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from cc_build_p0_animation_dynamic_gate_v1 import (
    DEFAULT_CAMERA,
    DEFAULT_LIGHTROOM,
    build_gate,
)


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
ARTIFACT_ROOT = ENGINE_ROOT / "outputs" / "character_creator_bridge" / "artifacts"

DEFAULT_SOURCE = Path(r"D:\BaiduNetdiskDownload\iclone动作\P0_Core_Everyday\1")
DEFAULT_INVENTORY = (
    ARTIFACT_ROOT
    / "animation_source_inventory"
    / "p0_20260817_v3"
    / "inventory.json"
)
DEFAULT_BODY_LIBRARY = SCRIPT_ROOT / "cc_body_preset_library_v2.json"
DEFAULT_WORK_ORDER = (
    ARTIFACT_ROOT
    / "animation_p0_ue_runtime_pilot"
    / "work_order_20260818_v1"
    / "work_order.json"
)
DEFAULT_RUNTIME_ROOT = (
    SCRIPT_ROOT / "runtime_assets" / "first_batch_actions_20260820_v2"
)
DEFAULT_ACTOR_RUNTIME_ROOT = (
    SCRIPT_ROOT / "runtime_assets" / "p0_offline_review_20260818_v1"
)
DEFAULT_OUTPUT = (
    ARTIFACT_ROOT
    / "first_batch_action_selection"
    / "selection_20260820_v2"
)
DEFAULT_GATE_OUTPUT = SCRIPT_ROOT / "cc_first_batch_action_gate_20260820_v2.json"
DEFAULT_REGISTRY_OUTPUT = (
    SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v2.json"
)

PILOT_ID = "cc_first_batch_actions_12_20260820_v2"
ACTOR_IDS = ("F02_Average", "M02_Average")
ACTION_SPECS = (
    {
        "action_id": "ACT_F01_ARGUMENT_BOSSY",
        "filename": "Argument_Bossy_F.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "argument_gesture",
    },
    {
        "action_id": "ACT_F02_SENSUAL_DANCE_03",
        "filename": "Sensual_Dance_03.iMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "dance_gesture",
    },
    {
        "action_id": "ACT_F03_AUDIENCE_01",
        "filename": "Audience F 01.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_F04_AUDIENCE_09",
        "filename": "Audience F 09.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_F05_TIE_SHOES",
        "filename": "TieShoes.iMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "self_interaction",
    },
    {
        "action_id": "ACT_F06_ELEVATOR_GREETING",
        "filename": "Elevator_Greeting_F.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "greeting_gesture",
    },
    {
        "action_id": "ACT_M01_ARGUMENT_SURRENDER",
        "filename": "Argument_Surrender_M.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "argument_gesture",
    },
    {
        "action_id": "ACT_M02_AUDIENCE_01",
        "filename": "Audience M 01.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_M03_AUDIENCE_12",
        "filename": "Audience M 12.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_M04_WATCH_GAME_HAPPY_DANCING",
        "filename": "WatchGame_HappyDancing.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "celebration_gesture",
    },
    {
        "action_id": "ACT_M05_ELEVATOR_GREETING",
        "filename": "Elevator_Greeting_M.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "greeting_gesture",
    },
    {
        "action_id": "ACT_M06_MOVING_ARGUMENT_DECLINE",
        "filename": "MovingArgument_Decline_M.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "argument_gesture",
    },
)


class FirstBatchActionBuildError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FirstBatchActionBuildError(f"Could not read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FirstBatchActionBuildError(f"Expected a JSON object: {path}")
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
        raise FirstBatchActionBuildError(f"Required file is missing: {path}")
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def copy_locked(source: Path, target: Path) -> dict[str, Any]:
    source_record = locked_file(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        target_record = locked_file(target)
        if (
            target_record["size_bytes"] != source_record["size_bytes"]
            or target_record["sha256"] != source_record["sha256"]
        ):
            raise FirstBatchActionBuildError(
                f"Runtime copy drifted and will not be overwritten: {target}"
            )
    else:
        shutil.copy2(source, target)
    return locked_file(target)


def inventory_matches(
    inventory: dict[str, Any], filename: str
) -> list[dict[str, Any]]:
    return [
        item
        for item in inventory.get("motions") or []
        if str(item.get("filename", "")).casefold() == filename.casefold()
    ]


def validate_source_set(source_root: Path) -> dict[str, Path]:
    if not source_root.is_dir():
        raise FirstBatchActionBuildError(
            f"Selected action directory is missing: {source_root}"
        )
    expected = {item["filename"] for item in ACTION_SPECS}
    actual = {
        item.name
        for item in source_root.iterdir()
        if item.is_file()
        and item.suffix.casefold() in (".rlmotion", ".imotion")
    }
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise FirstBatchActionBuildError(
            f"Selected action set changed; missing={missing}, unexpected={unexpected}"
        )
    return {name: source_root / name for name in expected}


def build_actor_library(
    body_library: dict[str, Any],
    work_order: dict[str, Any],
    actor_runtime_root: Path,
) -> dict[str, Any]:
    presets = {
        item.get("preset_id"): dict(item)
        for item in body_library.get("presets") or []
        if item.get("preset_id") in ACTOR_IDS
    }
    actors = {
        item.get("bodyfit_id"): item for item in work_order.get("actors") or []
    }
    if set(presets) != set(ACTOR_IDS) or set(ACTOR_IDS) - set(actors):
        raise FirstBatchActionBuildError("F02/M02 clothed actor sources are incomplete")

    for actor_id in ACTOR_IDS:
        source_record = actors[actor_id].get("source_project") or {}
        source = Path(str(source_record.get("path", ""))).resolve()
        verified_source = locked_file(source)
        expected_size = source_record.get("bytes", source_record.get("size_bytes"))
        if expected_size is not None and verified_source["size_bytes"] != int(
            expected_size
        ):
            raise FirstBatchActionBuildError(f"Clothed actor size drifted: {actor_id}")
        if source_record.get("sha256") != verified_source["sha256"]:
            raise FirstBatchActionBuildError(f"Clothed actor hash drifted: {actor_id}")
        mirror = actor_runtime_root / f"{actor_id}_Clothed.ccProject"
        runtime_record = copy_locked(source, mirror)
        presets[actor_id]["source_project"] = runtime_record
        presets[actor_id]["review_actor_binding_id"] = actors[actor_id].get(
            "actor_binding_id"
        )
        presets[actor_id]["appearance_recipe_id"] = actors[actor_id].get(
            "appearance_recipe_id"
        )

    return {
        "schema_version": 1,
        "library_id": "cc_first_batch_clothed_review_actors_20260820_v2",
        "generated_at": now(),
        "status": "review_only",
        "production_status": "not_approved",
        "presets": [presets[actor_id] for actor_id in ACTOR_IDS],
    }


def build_first_batch_action_gate(
    source_root: Path,
    inventory_path: Path,
    body_library_path: Path,
    work_order_path: Path,
    runtime_root: Path,
    actor_runtime_root: Path,
    output_root: Path,
    gate_output: Path,
    registry_output: Path,
    camera_path: Path = DEFAULT_CAMERA,
    lightroom_path: Path = DEFAULT_LIGHTROOM,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    inventory_path = inventory_path.resolve()
    runtime_root = runtime_root.resolve()
    output_root = output_root.resolve()
    selected_files = validate_source_set(source_root)
    inventory = read_json(inventory_path)

    cases = []
    registry_actions = []
    seen_hashes: set[str] = set()
    for index, spec in enumerate(ACTION_SPECS, 1):
        matches = inventory_matches(inventory, spec["filename"])
        if len(matches) != 1:
            raise FirstBatchActionBuildError(
                f"Expected one inventory record for {spec['filename']}; got {len(matches)}"
            )
        inventory_motion = matches[0]
        if inventory_motion.get("sex_hint") not in (spec["sex"], "unknown"):
            raise FirstBatchActionBuildError(
                f"Inventory sex hint drifted for {spec['filename']}"
            )
        if inventory_motion.get("production_status") != "not_approved":
            raise FirstBatchActionBuildError(
                f"Unexpected inherited approval: {spec['filename']}"
            )

        source_record = locked_file(selected_files[spec["filename"]])
        if source_record["sha256"] in seen_hashes:
            raise FirstBatchActionBuildError("Selected actions contain duplicate bytes")
        seen_hashes.add(source_record["sha256"])
        source_suffix = selected_files[spec["filename"]].suffix
        target = runtime_root / "motions" / (
            f"{index:02d}_{spec['action_id'].lower()}{source_suffix}"
        )
        staged_record = copy_locked(selected_files[spec["filename"]], target)
        case_id = spec["action_id"].lower()
        case = {
            "case_id": case_id,
            "motion_id": inventory_motion["motion_id"],
            "filename": spec["filename"],
            "source_format": source_suffix.casefold(),
            "format_generation": (
                "legacy" if source_suffix.casefold() == ".imotion" else "current"
            ),
            "package_name": inventory_motion.get("package_name"),
            "source_container_relative_path": inventory_motion.get(
                "source_container_relative_path"
            ),
            "source_member_path": inventory_motion.get("member_path"),
            "sex_hint": spec["sex"],
            "semantic_tags": inventory_motion.get("semantic_tags") or [],
            "dependency_class": inventory_motion.get("dependency_class"),
            "review_bucket": inventory_motion.get("review_bucket"),
            "pilot_actor_preset_id": spec["actor_id"],
            "review_family": spec["semantic_family"],
            "loop_hint": "unknown",
            "extracted_file": staged_record,
            "selected_loose_file": source_record,
            "review_status": "pending_cc_dynamic_review",
            "production_status": "not_approved",
        }
        cases.append(case)
        registry_actions.append(
            {
                "action_id": spec["action_id"],
                "sex": spec["sex"],
                "actor_id": spec["actor_id"],
                "semantic_family": spec["semantic_family"],
                "motion_id": inventory_motion["motion_id"],
                "filename": spec["filename"],
                "source_inventory_review_bucket": inventory_motion.get(
                    "review_bucket"
                ),
                "source_package": inventory_motion.get("package_name"),
                "source_container_relative_path": inventory_motion.get(
                    "source_container_relative_path"
                ),
                "source_member_path": inventory_motion.get("member_path"),
                "source_file": source_record,
                "runtime_file": staged_record,
                "user_selection_status": "selected_no_required_prop_reported",
                "dynamic_review_status": "pending",
                "ue_validation_status": "pending",
                "production_status": "not_approved",
            }
        )

    sex_counts = Counter(item["sex_hint"] for item in cases)
    if sex_counts != {"female": 6, "male": 6}:
        raise FirstBatchActionBuildError(f"Expected 6 actions per sex: {sex_counts}")

    output_root.mkdir(parents=True, exist_ok=True)
    actor_library = build_actor_library(
        read_json(body_library_path.resolve()),
        read_json(work_order_path.resolve()),
        actor_runtime_root.resolve(),
    )
    actor_library_path = output_root / "clothed_actor_library.json"
    write_json(actor_library_path, actor_library)

    selection = {
        "schema_version": 1,
        "selection_id": PILOT_ID,
        "generated_at": now(),
        "status": "frozen_pending_cc_dynamic_review",
        "source_directory": str(source_root),
        "selection_authority": "user",
        "selection_statement": (
            "Six female and six male motions were explicitly selected for the "
            "first batch and reported not to require handheld props."
        ),
        "safety_boundary": (
            "This override changes review priority only. It does not bypass CC "
            "dynamic evidence, UE import validation, or visual approval."
        ),
        "counts": {"physical_assets": 12, "female": 6, "male": 6},
        "actions": registry_actions,
    }
    selection_path = output_root / "selection_manifest.json"
    write_json(selection_path, selection)

    manifest = {
        "schema_version": 1,
        "pilot_id": PILOT_ID,
        "generated_at": now(),
        "status": "extracted_pending_cc_dynamic_review",
        "source_inventory": {
            "inventory_id": inventory.get("inventory_id"),
            **locked_file(inventory_path),
        },
        "selection_spec": locked_file(selection_path),
        "source_root": str(source_root),
        "boundaries": [
            "User selection is not production approval.",
            "Actor assignment is a sex-compatible review presentation.",
            "Hidden props, partner dependence, root motion, and face channels remain gated.",
        ],
        "counts": {
            "case_count": 12,
            "by_pilot_actor": {"F02_Average": 6, "M02_Average": 6},
            "by_source_format": dict(
                sorted(Counter(item["source_format"] for item in cases).items())
            ),
            "by_review_family": dict(
                sorted(Counter(item["review_family"] for item in cases).items())
            ),
            "production_approved_count": 0,
        },
        "cases": cases,
        "validation": {
            "success": True,
            "source_directory_exact_match": True,
            "inventory_identity_resolved": True,
            "all_selected_from_required_bucket": False,
            "review_bucket_override_recorded": True,
            "all_extracted_files_unique": True,
            "duplicate_content_groups": [],
            "source_archives_unchanged": None,
        },
    }
    manifest_path = output_root / "pilot_manifest.json"
    write_json(manifest_path, manifest)
    review = {
        "schema_version": 1,
        "pilot_id": PILOT_ID,
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
        "cases": [
            {
                "case_id": item["case_id"],
                "motion_id": item["motion_id"],
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
            for item in cases
        ],
    }
    review_path = output_root / "dynamic_review.json"
    write_json(review_path, review)

    gate = build_gate(
        manifest_path,
        review_path,
        actor_library_path,
        camera_path,
        lightroom_path,
        library_id=PILOT_ID,
        camera_mode="lightroom_current",
        auto_frame_full_body=False,
    )
    gate["selection_override"] = {
        "authority": "user",
        "source_review_buckets": dict(
            sorted(Counter(item["review_bucket"] for item in cases).items())
        ),
        "reported_required_prop_count": 0,
        "dynamic_gate_still_required": True,
        "production_approval_granted": False,
    }
    gate["capture_policy"]["follow_root_for_capture"] = True
    case_by_id = {item["case_id"]: item for item in cases}
    for preset in gate["presets"]:
        for motion_case in preset["motion_cases"]:
            source_case = case_by_id[motion_case["case_id"]]
            motion_case["action_id"] = source_case["case_id"].upper()
            motion_case["source_review_bucket"] = source_case["review_bucket"]
            motion_case["user_selected"] = True
            motion_case["required_prop_reported"] = False
    write_json(gate_output.resolve(), gate)

    registry = {
        "schema_version": 1,
        "registry_id": "first_batch_action_registry_20260820_v2",
        "generated_at": now(),
        "status": "frozen_pending_cc_and_ue_validation",
        "production_status": "not_approved",
        "cardinality_contract": {
            "physical_action_assets": 12,
            "selectable_actions_per_compatible_look": 6,
            "female_actions": 6,
            "male_actions": 6,
            "node_budget_formula": "16 looks * 6 compatible actions * 4 states = 384",
        },
        "selection_manifest": locked_file(selection_path),
        "cc_gate_config": locked_file(gate_output.resolve()),
        "actions": registry_actions,
    }
    write_json(registry_output.resolve(), registry)
    write_json(output_root / "action_registry.json", registry)
    return {
        "pilot_id": PILOT_ID,
        "status": registry["status"],
        "counts": registry["cardinality_contract"],
        "selection_manifest": str(selection_path),
        "registry": str(registry_output.resolve()),
        "gate_config": str(gate_output.resolve()),
        "cc_output_dir": str(output_root.parent / "dynamic_run_20260820_v2"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--body-library", type=Path, default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--work-order", type=Path, default=DEFAULT_WORK_ORDER)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument(
        "--actor-runtime-root", type=Path, default=DEFAULT_ACTOR_RUNTIME_ROOT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gate-output", type=Path, default=DEFAULT_GATE_OUTPUT)
    parser.add_argument(
        "--registry-output", type=Path, default=DEFAULT_REGISTRY_OUTPUT
    )
    parser.add_argument("--camera", type=Path, default=DEFAULT_CAMERA)
    parser.add_argument("--lightroom", type=Path, default=DEFAULT_LIGHTROOM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_first_batch_action_gate(
        args.source,
        args.inventory,
        args.body_library,
        args.work_order,
        args.runtime_root,
        args.actor_runtime_root,
        args.output,
        args.gate_output,
        args.registry_output,
        args.camera,
        args.lightroom,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
