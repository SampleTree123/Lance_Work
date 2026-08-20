"""Build the remaining P0 animation review batches and CC gate configs.

This freezes the 69 standalone-first motions that are not part of the accepted
16-motion Pilot. The output is split into four independently resumable CC
batches and uses the already generated clothed F02/M02 showcase projects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from cc_build_p0_animation_dynamic_gate_v1 import (
    DEFAULT_CAMERA,
    DEFAULT_LIGHTROOM,
    build_gate,
)
from cc_build_p0_animation_pilot_v1 import build_pilot


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
ARTIFACT_ROOT = ENGINE_ROOT / "outputs" / "character_creator_bridge" / "artifacts"
DEFAULT_INVENTORY_ROOT = (
    ARTIFACT_ROOT / "animation_source_inventory" / "p0_20260817_v3"
)
DEFAULT_INVENTORY = DEFAULT_INVENTORY_ROOT / "inventory.json"
DEFAULT_QUEUE = DEFAULT_INVENTORY_ROOT / "review_queue.json"
DEFAULT_ACCEPTED_PILOT = (
    ARTIFACT_ROOT
    / "animation_p0_pilot"
    / "pilot_20260817_v1"
    / "pilot_manifest.json"
)
DEFAULT_BODY_LIBRARY = SCRIPT_ROOT / "cc_body_preset_library_v2.json"
DEFAULT_WORK_ORDER = (
    ARTIFACT_ROOT
    / "animation_p0_ue_runtime_pilot"
    / "work_order_20260818_v1"
    / "work_order.json"
)
DEFAULT_OUTPUT = (
    ARTIFACT_ROOT
    / "animation_p0_offline_review"
    / "source_batches_20260818_v1"
)
RUNTIME_INPUT_ROOT = SCRIPT_ROOT / "runtime_assets" / "p0_offline_review_20260818_v1"

BATCH_SIZES = (18, 17, 17, 17)
ACTOR_IDS = ("F02_Average", "M02_Average")
CASE_ID_PATTERN = re.compile(r"[^a-z0-9]+")


class OfflineReviewBuildError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OfflineReviewBuildError(f"Could not read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OfflineReviewBuildError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locked_file(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise OfflineReviewBuildError(f"Required file is missing: {path}")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def slug(value: str, fallback: str) -> str:
    normalized = CASE_ID_PATTERN.sub("-", value.lower()).strip("-")
    return (normalized or fallback)[:48]


def actor_for_motion(motion: dict[str, Any]) -> str:
    # Unknown motions are placed on the male review actor. This balances the
    # queue (37 female / 32 male-or-unknown) without asserting a hard sex lock.
    return "F02_Average" if motion.get("sex_hint") == "female" else "M02_Average"


def review_family(motion: dict[str, Any]) -> str:
    tags = [
        str(value).strip().lower()
        for value in motion.get("semantic_tags") or []
        if str(value).strip() and str(value).strip().lower() != "unclassified"
    ]
    return tags[0] if tags else "pending_user_semantic_review"


def interleave_actor_queues(motions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queues = {
        actor_id: [item for item in motions if actor_for_motion(item) == actor_id]
        for actor_id in ACTOR_IDS
    }
    ordered: list[dict[str, Any]] = []
    while any(queues.values()):
        for actor_id in ACTOR_IDS:
            if queues[actor_id]:
                ordered.append(queues[actor_id].pop(0))
    return ordered


def collect_remaining(
    inventory: dict[str, Any],
    queue: dict[str, Any],
    accepted_pilot: dict[str, Any],
) -> list[dict[str, Any]]:
    inventory_id = inventory.get("inventory_id")
    if queue.get("inventory_id") != inventory_id:
        raise OfflineReviewBuildError("Review queue and inventory IDs differ")
    pilot_inventory = (accepted_pilot.get("source_inventory") or {}).get(
        "inventory_id"
    )
    if pilot_inventory != inventory_id:
        raise OfflineReviewBuildError("Accepted Pilot and inventory IDs differ")

    motions = inventory.get("motions") or []
    by_id = {item.get("motion_id"): item for item in motions}
    if len(by_id) != len(motions):
        raise OfflineReviewBuildError("Inventory motion IDs are not unique")

    queue_ids = list((queue.get("buckets") or {}).get("standalone_first") or [])
    accepted_ids = {
        item.get("motion_id") for item in accepted_pilot.get("cases") or []
    }
    if len(queue_ids) != 85 or len(accepted_ids) != 16:
        raise OfflineReviewBuildError("Expected the frozen 85/16 P0 source sets")
    if not accepted_ids.issubset(set(queue_ids)):
        raise OfflineReviewBuildError("Accepted Pilot is outside standalone_first")

    remaining_ids = [item for item in queue_ids if item not in accepted_ids]
    if len(remaining_ids) != sum(BATCH_SIZES):
        raise OfflineReviewBuildError("Expected exactly 69 remaining P0 motions")
    unknown = sorted(set(remaining_ids) - set(by_id))
    if unknown:
        raise OfflineReviewBuildError(f"Queue references unknown motions: {unknown}")

    remaining = [by_id[motion_id] for motion_id in remaining_ids]
    for motion in remaining:
        if motion.get("review_bucket") != "standalone_first":
            raise OfflineReviewBuildError("A remaining motion changed review bucket")
        if Path(str(motion.get("source_container_relative_path", ""))).suffix.lower() != ".zip":
            raise OfflineReviewBuildError("Offline review currently requires ZIP sources")
        if motion.get("production_status") != "not_approved":
            raise OfflineReviewBuildError("Source motion unexpectedly gained approval")
    signatures = [
        (item.get("size"), item.get("crc32"), item.get("extension"))
        for item in remaining
    ]
    if len(signatures) != len(set(signatures)):
        raise OfflineReviewBuildError("Remaining P0 motions contain duplicate bytes")
    return interleave_actor_queues(remaining)


def clothed_actor_library(
    base_library: dict[str, Any], work_order: dict[str, Any]
) -> dict[str, Any]:
    presets = {
        item.get("preset_id"): dict(item)
        for item in base_library.get("presets") or []
        if item.get("preset_id") in ACTOR_IDS
    }
    if set(presets) != set(ACTOR_IDS):
        raise OfflineReviewBuildError("Base BodyFit library lacks F02/M02")

    actors = {
        item.get("bodyfit_id"): item for item in work_order.get("actors") or []
    }
    if set(ACTOR_IDS) - set(actors):
        raise OfflineReviewBuildError("Clothed work order lacks F02/M02")
    for preset_id in ACTOR_IDS:
        record = locked_file(Path((actors[preset_id].get("source_project") or {}).get("path", "")))
        presets[preset_id]["source_project"] = {
            **record,
            "size_bytes": record["bytes"],
        }
        presets[preset_id]["review_actor_binding_id"] = actors[preset_id].get(
            "actor_binding_id"
        )
        presets[preset_id]["appearance_recipe_id"] = actors[preset_id].get(
            "appearance_recipe_id"
        )
    return {
        "schema_version": 1,
        "library_id": "cc_p0_offline_review_clothed_actors_20260818_v1",
        "generated_at": now(),
        "status": "review_only",
        "production_status": "not_approved",
        "presets": [presets[preset_id] for preset_id in ACTOR_IDS],
    }


def mirror_actor_projects(work_order: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actors = {
        item.get("bodyfit_id"): item for item in work_order.get("actors") or []
    }
    if set(ACTOR_IDS) - set(actors):
        raise OfflineReviewBuildError("Clothed work order lacks F02/M02")
    RUNTIME_INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    mirrors: dict[str, dict[str, Any]] = {}
    for preset_id in ACTOR_IDS:
        source = Path(
            (actors[preset_id].get("source_project") or {}).get("path", "")
        ).resolve()
        source_record = locked_file(source)
        target = RUNTIME_INPUT_ROOT / f"{preset_id}_Clothed.ccProject"
        if target.is_file():
            if (
                target.stat().st_size != source_record["bytes"]
                or sha256_file(target) != source_record["sha256"]
            ):
                raise OfflineReviewBuildError(
                    f"Runtime actor mirror drifted: {target}"
                )
        else:
            shutil.copy2(source, target)
        mirrors[preset_id] = {
            **locked_file(target),
            "size_bytes": target.stat().st_size,
            "source_path": str(source),
        }
    return mirrors


def refresh_runtime_inputs(
    output_root: Path, work_order_path: Path
) -> dict[str, Any]:
    output_root = output_root.resolve()
    master_path = output_root / "offline_review_manifest.json"
    master = read_json(master_path)
    mirrors = mirror_actor_projects(read_json(work_order_path.resolve()))
    for batch in master.get("batches") or []:
        index = int(batch["batch_index"])
        canonical_gate_path = Path((batch.get("gate_config") or {}).get("path", ""))
        gate = read_json(canonical_gate_path)
        for preset in gate.get("presets") or []:
            preset_id = preset.get("preset_id")
            if preset_id not in mirrors:
                raise OfflineReviewBuildError(
                    f"Unexpected runtime gate actor: {preset_id}"
                )
            preset["source_project"] = {
                key: value
                for key, value in mirrors[preset_id].items()
                if key != "source_path"
            }
        runtime_gate_path = (
            SCRIPT_ROOT
            / f"cc_p0_offline_review_batch_{index:02d}_gate_20260818_v1.json"
        )
        write_json(runtime_gate_path, gate)
        batch["runtime_gate_config"] = locked_file(runtime_gate_path)
    master.setdefault("source", {})["runtime_actor_projects"] = {
        preset_id: record for preset_id, record in mirrors.items()
    }
    write_json(master_path, master)
    return master


def make_case(index: int, motion: dict[str, Any]) -> dict[str, Any]:
    stem = Path(str(motion.get("filename") or "motion")).stem
    suffix = str(motion["motion_id"])[-6:]
    return {
        "case_id": f"p0r_{index:03d}_{slug(stem, 'motion')}_{suffix}",
        "motion_id": motion["motion_id"],
        "pilot_actor_preset_id": actor_for_motion(motion),
        "review_family": review_family(motion),
        "loop_hint": "unknown",
    }


def build_offline_review(
    inventory_path: Path,
    queue_path: Path,
    accepted_pilot_path: Path,
    body_library_path: Path,
    work_order_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise OfflineReviewBuildError(f"Output already exists: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    inventory = read_json(inventory_path.resolve())
    queue = read_json(queue_path.resolve())
    accepted_pilot = read_json(accepted_pilot_path.resolve())
    remaining = collect_remaining(inventory, queue, accepted_pilot)
    all_cases = [make_case(index, motion) for index, motion in enumerate(remaining, 1)]

    actor_library = clothed_actor_library(
        read_json(body_library_path.resolve()), read_json(work_order_path.resolve())
    )
    actor_library_path = output_root / "config" / "clothed_actor_library.json"
    write_json(actor_library_path, actor_library)

    batches = []
    cursor = 0
    for batch_index, batch_size in enumerate(BATCH_SIZES, 1):
        cases = all_cases[cursor : cursor + batch_size]
        cursor += batch_size
        batch_id = f"cc_p0_offline_review_batch_{batch_index:02d}_20260818_v1"
        spec = {
            "schema_version": 1,
            "pilot_id": batch_id,
            "source_inventory_id": inventory["inventory_id"],
            "status": "selection_frozen_pending_extraction",
            "selection_policy": {
                "minimum_case_count": 10,
                "maximum_case_count": 20,
                "required_review_bucket": "standalone_first",
                "require_unique_content": True,
                "production_approval_from_selection": False,
            },
            "boundaries": [
                "This batch is for offline visual screening only.",
                "Actor assignment is a review presentation, not a permanent sex lock.",
                "User decisions do not grant production approval until imported and validated.",
            ],
            "cases": cases,
        }
        spec_path = output_root / "specs" / f"batch_{batch_index:02d}.json"
        write_json(spec_path, spec)

        batch_root = output_root / "batches" / f"batch_{batch_index:02d}"
        manifest = build_pilot(inventory_path, spec_path, batch_root)
        gate = build_gate(
            batch_root / "pilot_manifest.json",
            batch_root / "dynamic_review.json",
            actor_library_path,
            DEFAULT_CAMERA,
            DEFAULT_LIGHTROOM,
            library_id=batch_id,
            camera_mode="lightroom_current",
            auto_frame_full_body=False,
        )
        gate_path = output_root / "config" / f"batch_{batch_index:02d}_gate.json"
        write_json(gate_path, gate)
        batches.append(
            {
                "batch_index": batch_index,
                "batch_id": batch_id,
                "case_count": len(cases),
                "case_ids": [item["case_id"] for item in cases],
                "actor_counts": manifest["counts"]["by_pilot_actor"],
                "selection_spec": locked_file(spec_path),
                "pilot_manifest": locked_file(batch_root / "pilot_manifest.json"),
                "dynamic_review_template": locked_file(batch_root / "dynamic_review.json"),
                "gate_config": locked_file(gate_path),
                "cc_output_dir": str(
                    output_root.parent
                    / "dynamic_runs_20260818_v1"
                    / f"batch_{batch_index:02d}"
                ),
                "status": "ready_for_cc_capture",
            }
        )

    candidates = []
    motion_by_id = {item["motion_id"]: item for item in remaining}
    case_to_batch = {
        case_id: batch["batch_index"]
        for batch in batches
        for case_id in batch["case_ids"]
    }
    for case in all_cases:
        motion = motion_by_id[case["motion_id"]]
        candidates.append(
            {
                **case,
                "batch_index": case_to_batch[case["case_id"]],
                "filename": motion.get("filename"),
                "source_format": motion.get("extension"),
                "source_package": motion.get("package_name"),
                "source_member_path": motion.get("member_path"),
                "sex_hint": motion.get("sex_hint"),
                "semantic_tags": motion.get("semantic_tags") or [],
                "dependency_class": motion.get("dependency_class"),
                "review_status": "pending_cc_capture",
                "production_status": "not_approved",
            }
        )

    master = {
        "schema_version": 1,
        "review_set_id": "cc_p0_offline_review_remaining_69_20260818_v1",
        "generated_at": now(),
        "status": "ready_for_cc_capture",
        "production_status": "not_approved",
        "counts": {
            "standalone_first_total": 85,
            "previously_reviewed": 16,
            "candidate_count": len(candidates),
            "batch_count": len(batches),
            "expected_image_count": len(candidates) * 5,
            "by_actor": {
                actor_id: sum(
                    item["pilot_actor_preset_id"] == actor_id for item in candidates
                )
                for actor_id in ACTOR_IDS
            },
        },
        "source": {
            "inventory": locked_file(inventory_path),
            "review_queue": locked_file(queue_path),
            "accepted_pilot": locked_file(accepted_pilot_path),
            "clothed_actor_work_order": locked_file(work_order_path),
            "clothed_actor_library": locked_file(actor_library_path),
        },
        "batches": batches,
        "candidates": candidates,
        "review_contract": {
            "user_fields": [
                "decision",
                "naturalness",
                "semantic_class",
                "presentation",
                "prop_dependency",
                "notes",
            ],
            "decision_values": ["accepted", "rejected", "deferred", "unreviewed"],
            "local_autosave": True,
            "json_export_required": True,
        },
    }
    master_path = output_root / "offline_review_manifest.json"
    write_json(master_path, master)
    master = refresh_runtime_inputs(output_root, work_order_path)
    return {**master, "manifest_path": str(master_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--accepted-pilot", type=Path, default=DEFAULT_ACCEPTED_PILOT)
    parser.add_argument("--body-library", type=Path, default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--work-order", type=Path, default=DEFAULT_WORK_ORDER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--refresh-runtime-inputs",
        action="store_true",
        help="Refresh only the bridge-whitelisted actor and gate mirrors.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.refresh_runtime_inputs:
        result = refresh_runtime_inputs(args.output, args.work_order)
        print(
            json.dumps(
                {
                    "review_set_id": result["review_set_id"],
                    "status": result["status"],
                    "runtime_inputs_refreshed": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    result = build_offline_review(
        args.inventory,
        args.queue,
        args.accepted_pilot,
        args.body_library,
        args.work_order,
        args.output,
    )
    print(
        json.dumps(
            {
                "review_set_id": result["review_set_id"],
                "status": result["status"],
                "counts": result["counts"],
                "manifest_path": result["manifest_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
