#!/usr/bin/env python3
"""Build restart-bounded resume chunks for the CC outfit compatibility gate."""

from __future__ import annotations

import argparse
import copy
import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any


class ResumePlanError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ResumePlanError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def completed_preset_ids(validation: dict[str, Any]) -> set[str]:
    completed: set[str] = set()
    for result in validation.get("results", []):
        if not isinstance(result, dict) or result.get("success") is not True:
            continue
        preset_id = result.get("preset_id")
        result_path = Path(str(result.get("result_path", "")))
        if not isinstance(preset_id, str) or not result_path.is_file():
            continue
        case_result = read_json(result_path)
        captures = case_result.get("captures", [])
        if case_result.get("success") is not True or len(captures) != 5:
            continue
        capture_paths = []
        for item in captures:
            image = item.get("image", {}) if isinstance(item, dict) else {}
            value = image.get("path") if isinstance(image, dict) else None
            if not value and isinstance(item, dict):
                value = item.get("path")
            capture_paths.append(Path(str(value or "")))
        if not all(path.is_file() for path in capture_paths):
            continue
        completed.add(preset_id)
    return completed


def group_presets(presets: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for preset in presets:
        look_id = preset.get("look_id")
        preset_id = preset.get("preset_id")
        if not isinstance(look_id, str) or not isinstance(preset_id, str):
            raise ResumePlanError("Every gate preset must define look_id and preset_id")
        grouped.setdefault(look_id, []).append(preset)
    for look_id, items in grouped.items():
        if len(items) != 3:
            raise ResumePlanError(
                f"Expected exactly three extreme BodyFits for {look_id}, found {len(items)}"
            )
    return list(grouped.items())


def chunked(values: list[Any], size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def preset_family_id(preset: dict[str, Any]) -> str:
    family_id = preset.get("family_id")
    if isinstance(family_id, str) and family_id:
        return family_id
    look_id = preset.get("look_id")
    if isinstance(look_id, str) and "::" in look_id:
        return look_id.split("::", 1)[0]
    raise ResumePlanError(f"Cannot resolve family ID for {preset.get('preset_id')}")


def build_chunk_manifest(
    gate: dict[str, Any],
    chunk_id: str,
    look_groups: list[tuple[str, list[dict[str, Any]]]],
    output_dir: Path,
) -> dict[str, Any]:
    presets = [copy.deepcopy(preset) for _, items in look_groups for preset in items]
    subject_ids = {preset["subject_id"] for preset in presets}
    family_ids = {preset_family_id(preset) for preset in presets}
    subjects = [
        copy.deepcopy(subject)
        for subject in gate.get("subjects", [])
        if subject.get("subject_id") in subject_ids
    ]
    families = [
        copy.deepcopy(family)
        for family in gate.get("families", [])
        if family.get("family_id") in family_ids
    ]
    if len(subjects) != len(subject_ids):
        raise ResumePlanError(f"Subject subset is incomplete for {chunk_id}")
    if len(families) != len(family_ids):
        raise ResumePlanError(f"Family subset is incomplete for {chunk_id}")

    manifest = copy.deepcopy(gate)
    manifest["library_id"] = f"{gate['library_id']}__{chunk_id}"
    manifest["status"] = "planned_resume_chunk"
    manifest["subjects"] = subjects
    manifest["families"] = families
    manifest["presets"] = presets
    manifest["resume_chunk"] = {
        "chunk_id": chunk_id,
        "parent_library_id": gate["library_id"],
        "look_ids": [look_id for look_id, _ in look_groups],
        "planned_output_root": str(output_dir),
        "requires_fresh_cc_process": True,
    }
    manifest["counts"] = {
        "subject_count": len(subjects),
        "family_count": len(families),
        "logical_group_count": len(look_groups),
        "test_case_count": len(presets),
        "views_per_case": 5,
        "expected_image_count": len(presets) * 5,
        "cases_by_sex": {
            sex: sum(1 for preset in presets if preset.get("sex") == sex)
            for sex in ("female", "male")
        },
    }
    return manifest


def build_resume_plan(
    gate_path: Path,
    validation_path: Path | list[Path],
    output_path: Path,
    chunks_dir: Path,
    run_root: Path,
    looks_per_chunk: int,
    job_prefix: str = "outfit_gate_20260815",
) -> dict[str, Any]:
    if looks_per_chunk < 1:
        raise ResumePlanError("looks_per_chunk must be positive")
    if not job_prefix or any(character.isspace() for character in job_prefix):
        raise ResumePlanError("job_prefix must be non-empty and contain no spaces")
    gate = read_json(gate_path)
    validation_paths = (
        [validation_path]
        if isinstance(validation_path, Path)
        else list(validation_path)
    )
    if not validation_paths:
        raise ResumePlanError("At least one validation checkpoint is required")
    presets = gate.get("presets", [])
    if not isinstance(presets, list) or not presets:
        raise ResumePlanError("Gate manifest has no presets")
    checkpoint_completed: set[str] = set()
    for checkpoint_path in validation_paths:
        checkpoint_completed.update(
            completed_preset_ids(read_json(checkpoint_path))
        )
    gate_ids = {preset["preset_id"] for preset in presets}
    ignored_checkpoint_preset_ids = sorted(
        checkpoint_completed - gate_ids
    )
    completed = checkpoint_completed & gate_ids

    grouped = group_presets(presets)
    completed_look_ids: list[str] = []
    remaining_groups: list[tuple[str, list[dict[str, Any]]]] = []
    replay_preset_ids: list[str] = []
    for look_id, items in grouped:
        item_ids = {item["preset_id"] for item in items}
        finished = item_ids & completed
        if finished == item_ids:
            completed_look_ids.append(look_id)
            continue
        if finished:
            replay_preset_ids.extend(sorted(finished))
        remaining_groups.append((look_id, items))

    chunks: list[dict[str, Any]] = []
    for index, groups in enumerate(chunked(remaining_groups, looks_per_chunk), start=1):
        chunk_id = f"chunk_{index:02d}"
        manifest_path = chunks_dir / f"{chunk_id}.json"
        output_dir = run_root / chunk_id
        manifest = build_chunk_manifest(gate, chunk_id, groups, output_dir)
        write_json(manifest_path, manifest)
        chunks.append(
            {
                "chunk_id": chunk_id,
                "status": "pending",
                "look_ids": [look_id for look_id, _ in groups],
                "look_count": len(groups),
                "case_count": sum(len(items) for _, items in groups),
                "expected_image_count": sum(len(items) for _, items in groups) * 5,
                "manifest_path": str(manifest_path),
                "output_dir": str(output_dir),
                "job_id": f"{job_prefix}_{chunk_id}",
                "requires_offline_cc_restart_before_run": False,
                "restart_policy": "resource_gate_at_complete_look_boundary",
                "command": [
                    "python",
                    r"D:\UE\Lance_Work\00_engine\character_creator_bridge\cc_bridge_client.py",
                    "validate-bodies",
                    "--library-file",
                    str(manifest_path),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-scene-replace",
                    "--auto-dismiss-undo-warning",
                    "--job-id",
                    f"{job_prefix}_{chunk_id}",
                    "--timeout",
                    "21600",
                ],
            }
        )

    expected_manifests = {Path(chunk["manifest_path"]).resolve() for chunk in chunks}
    if chunks_dir.is_dir():
        for stale_path in chunks_dir.glob("chunk_*.json"):
            if stale_path.resolve() not in expected_manifests:
                stale_path.unlink()

    plan = {
        "schema_version": 1,
        "plan_id": "cc_outfit_compatibility_resume_plan_20260815_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate_manifest": str(gate_path),
        "checkpoint_validation": str(validation_paths[-1]),
        "checkpoint_validations": [str(path) for path in validation_paths],
        "job_prefix": job_prefix,
        "safety_policy": {
            "looks_per_chunk": looks_per_chunk,
            "cases_per_full_chunk": looks_per_chunk * 3,
            "restart_not_per_case": True,
            "target_cases_per_submitted_job": [3, 6],
            "target_cases_per_cc_process": [6, 12],
            "evaluation_boundary": "after_each_complete_look",
            "private_memory_soft_limit_gib": 24,
            "private_memory_hard_limit_gib": 30,
            "minimum_available_physical_memory_gib": 8,
            "commit_usage_soft_limit_percent": 75,
            "commit_usage_hard_limit_percent": 85,
            "gpu_free_memory_soft_limit_mib": 2048,
            "gpu_free_memory_hard_limit_mib": 1024,
            "resource_release_probe_manifest": (
                r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
                r"\cc_resource_release_probe_20260815_v1.json"
            ),
            "run_resource_release_probe_at_soft_limit": True,
            "continue_only_if_resources_recover_above_soft_limits": True,
            "restart_cc_offline_before_every_chunk": False,
            "restart_cc_offline_when_resource_gate_reached": True,
            "agent_must_not_restart_cc": True,
            "reason": (
                "Large historical runs reached 24-39 cases, but outfit-dependent "
                "native and GPU caches make those counts unsafe as a default. A "
                "combined 24-case process later fell to about 0.23 GiB free VRAM. "
                "Submit one or two complete three-case Looks per job and normally "
                "limit a CC process to 6-12 cases. Evaluate RAM, commit, and VRAM "
                "after each complete Look. At a soft limit, clear the disposable "
                "scene and Python/Qt caches once; continue only when every resource "
                "recovers above its soft boundary, otherwise let the user restart CC."
            ),
        },
        "counts": {
            "gate_cases": len(presets),
            "verified_completed_cases": len(completed),
            "incomplete_cases": len(presets) - len(completed),
            "scheduled_cases": sum(chunk["case_count"] for chunk in chunks),
            "completed_looks": len(completed_look_ids),
            "remaining_looks": len(remaining_groups),
            "chunk_count": len(chunks),
            "ignored_checkpoint_cases_outside_gate": len(
                ignored_checkpoint_preset_ids
            ),
            "replayed_cases_due_to_partial_look": len(replay_preset_ids),
        },
        "completed_look_ids": completed_look_ids,
        "ignored_checkpoint_preset_ids": ignored_checkpoint_preset_ids,
        "replayed_preset_ids": replay_preset_ids,
        "chunks": chunks,
    }
    write_json(output_path, plan)
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument(
        "--validation",
        type=Path,
        action="append",
        required=True,
        help="Repeat for every completed checkpoint that should be skipped",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunks-dir", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--looks-per-chunk", type=int, default=5)
    parser.add_argument("--job-prefix", default="outfit_gate_20260815")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_resume_plan(
        gate_path=args.gate.resolve(),
        validation_path=[path.resolve() for path in args.validation],
        output_path=args.output.resolve(),
        chunks_dir=args.chunks_dir.resolve(),
        run_root=args.run_root.resolve(),
        looks_per_chunk=args.looks_per_chunk,
        job_prefix=args.job_prefix,
    )
    print(json.dumps(plan["counts"], ensure_ascii=False))
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
