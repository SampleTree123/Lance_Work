"""Build and register the remaining-69 P0 offline animation review run."""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from build_animation_p0_dynamic_gate_run import (
    build_sheet,
    collect_successes,
    read_json,
    safe_id,
    sha256_file,
    to_url,
    validate_case,
    write_json,
)
from build_outfit_compatibility_gate_run import OutfitPortalError
from portal_registry import register_run, validate_local_assets, validate_run


ENGINE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_offline_review"
    / "source_batches_20260818_v1"
)
DEFAULT_MANIFEST = DEFAULT_SOURCE_ROOT / "offline_review_manifest.json"
DEFAULT_RUNS_ROOT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_offline_review"
    / "dynamic_runs_20260818_v1"
)
DEFAULT_REVIEW_ROOT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_offline_review"
    / "offline_portal_20260818_v1"
)
DEFAULT_PORTAL = ENGINE_ROOT / "visualization_portal"
RUN_ID = "2026-08-18-cc-animation-p0-offline-review-v1"


def fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        path = path.resolve()
        digest.update(str(path).lower().encode("utf-8"))
        digest.update(sha256_file(path).encode("ascii"))
    return digest.hexdigest()


def batch_validation_paths(manifest: dict[str, Any], runs_root: Path) -> list[Path]:
    paths = []
    for batch in manifest.get("batches") or []:
        index = int(batch["batch_index"])
        path = runs_root.resolve() / f"batch_{index:02d}" / "validation_result.json"
        if not path.is_file():
            raise OutfitPortalError(f"Offline review batch is incomplete: {path}")
        paths.append(path)
    return paths


def gate_cases(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for batch in manifest.get("batches") or []:
        gate_path = Path((batch.get("gate_config") or {}).get("path", ""))
        gate = read_json(gate_path)
        for preset in gate.get("presets") or []:
            for case in preset.get("motion_cases") or []:
                case_id = case.get("case_id")
                if case_id in result:
                    raise OutfitPortalError(f"Duplicate offline case: {case_id}")
                result[case_id] = {
                    **case,
                    "pilot_actor_preset_id": preset["preset_id"],
                }
    return result


def build_run(
    manifest_path: Path = DEFAULT_MANIFEST,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    review_root: Path = DEFAULT_REVIEW_ROOT,
    portal_root: Path = DEFAULT_PORTAL,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = read_json(manifest_path)
    candidates = manifest.get("candidates") or []
    if len(candidates) != 69:
        raise OutfitPortalError("Offline review manifest must contain 69 candidates")

    validation_paths = batch_validation_paths(manifest, runs_root)
    successes, source_runs = collect_successes(validation_paths)
    gates = gate_cases(manifest)
    expected_ids = [item["case_id"] for item in candidates]
    if set(successes) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(successes))
        extra = sorted(set(successes) - set(expected_ids))
        raise OutfitPortalError(
            f"Offline review evidence differs from manifest; missing={missing}, extra={extra}"
        )
    if set(gates) != set(expected_ids):
        raise OutfitPortalError("Offline review gate cases differ from manifest")

    review_root = review_root.resolve()
    sheets_root = review_root / "sheets"
    groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    consolidated_cases = []
    by_id = {item["case_id"]: item for item in candidates}
    for index, case_id in enumerate(expected_ids, 1):
        source = by_id[case_id]
        validated = validate_case(gates[case_id], successes[case_id])
        consolidated_cases.append(validated)
        sheet_path = sheets_root / f"g{index:03d}-{safe_id(case_id)}.png"
        build_sheet(validated, sheet_path, visual_accepted=False)
        root = validated["recomputed_root_evidence"]
        group_id = f"g{index:03d}-{safe_id(case_id)}"
        groups[group_id] = {
            "label": (
                f"{validated['pilot_actor_preset_id']} / "
                f"{validated['filename']}"
            ),
            "overview": to_url(sheet_path),
            "comparisons": {},
            "cases": [
                {
                    "id": case_id,
                    "label": validated["filename"],
                    "preset_id": validated["pilot_actor_preset_id"],
                    "parameters": {
                        "batch": f"{int(source['batch_index']):02d}/04",
                        "source_package": source.get("source_package"),
                        "source_format": validated["source_format"],
                        "motion_length_frames": validated["motion_length_frames"],
                        "root_motion_class": root["classification"],
                        "root_motion_landmark": root.get("landmark_bone"),
                        "facial_channel_class": validated[
                            "facial_channel_class"
                        ],
                        "review_family": validated["review_family"],
                        "hidden_dependency_count": len(
                            validated["hidden_dependencies"]
                        ),
                        "source_sex_hint": source.get("sex_hint"),
                    },
                    "images": validated["images"],
                }
            ],
        }

    roots = Counter(
        item["recomputed_root_evidence"]["classification"]
        for item in consolidated_cases
    )
    formats = Counter(item["source_format"] for item in consolidated_cases)
    hidden_count = sum(
        len(item["hidden_dependencies"]) for item in consolidated_cases
    )
    fingerprint_paths = [manifest_path, *validation_paths]
    source_fingerprint = fingerprint(fingerprint_paths)
    consolidated = {
        "schema_version": 1,
        "review_set_id": manifest["review_set_id"],
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "automation_complete_pending_user_review",
        "production_status": "not_approved",
        "source_fingerprint": source_fingerprint,
        "counts": {
            "candidate_count": len(consolidated_cases),
            "image_count": len(consolidated_cases) * 5,
            "hidden_dependency_count": hidden_count,
            "by_root_motion": dict(sorted(roots.items())),
            "by_source_format": dict(sorted(formats.items())),
        },
        "source_runs": source_runs,
        "cases": consolidated_cases,
    }
    consolidated_path = review_root / "consolidated_validation.json"
    write_json(consolidated_path, consolidated)

    artifacts = [
        {"label": "69-candidate frozen manifest", "url": to_url(manifest_path)},
        {"label": "Consolidated CC validation", "url": to_url(consolidated_path)},
    ]
    for index, path in enumerate(validation_paths, 1):
        artifacts.append(
            {"label": f"CC batch {index:02d} validation", "url": to_url(path)}
        )

    run = {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "P0 动画候选离线审查",
        "task": "Character Creator / 动画池筛选",
        "created_at": consolidated["generated_at"],
        "status": "pending_review",
        "summary": (
            "审查剩余 69 条 P0 独立动作。进度自动保存在本机浏览器；"
            "离线完成后请导出 JSON 决定文件。"
        ),
        "tags": ["CC5", "P0", "动画", "离线审查", "穿衣角色"],
        "thumbnail": next(iter(groups.values()))["overview"],
        "metrics": [
            {"label": "待审动作", "value": 69},
            {"label": "关键帧", "value": 345},
            {"label": "批次", "value": 4},
            {"label": "隐藏道具", "value": hidden_count},
        ],
        "groups": groups,
        "artifacts": artifacts,
        "review": {
            "schema_version": 1,
            "mode": "candidate_review",
            "review_id": "cc-p0-animation-offline-review-remaining-69-v1",
            "source_fingerprint": source_fingerprint,
            "export_filename": "cc_p0_animation_remaining_69_review_decisions.json",
        },
    }
    validate_run(run)
    missing_assets = validate_local_assets(run, ENGINE_ROOT.parent)
    if missing_assets:
        raise OutfitPortalError(f"Portal run has missing assets: {missing_assets}")

    source_run_path = review_root / "run.json"
    write_json(source_run_path, run)
    target, registry = register_run(source_run_path, portal_root, replace=True)
    return {
        "run": run,
        "source_run_path": str(source_run_path),
        "portal_run_path": str(target),
        "registry_path": str(registry),
        "consolidated_path": str(consolidated_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--portal", type=Path, default=DEFAULT_PORTAL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_run(args.manifest, args.runs_root, args.review_root, args.portal)
    print(result["portal_run_path"])
    print("69 candidates / 345 images registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
