#!/usr/bin/env python3
"""Build a restart-bounded correction plan for completed F01 outfit evidence."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class CorrectionPlanError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CorrectionPlanError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def verified_preset_ids(validation: dict[str, Any]) -> set[str]:
    verified: set[str] = set()
    for result in validation.get("results", []):
        if not isinstance(result, dict) or result.get("success") is not True:
            continue
        preset_id = result.get("preset_id")
        result_path = Path(str(result.get("result_path", "")))
        if not isinstance(preset_id, str) or not result_path.is_file():
            continue
        case = read_json(result_path)
        captures = case.get("captures", [])
        if case.get("success") is not True or len(captures) != 5:
            continue
        image_paths: list[Path] = []
        for capture in captures:
            image = capture.get("image", {}) if isinstance(capture, dict) else {}
            image_path = image.get("path") if isinstance(image, dict) else None
            if not image_path and isinstance(capture, dict):
                image_path = capture.get("path")
            image_paths.append(Path(str(image_path or "")))
        if all(path.is_file() for path in image_paths):
            verified.add(preset_id)
    return verified


def family_id_for(preset: dict[str, Any]) -> str:
    family_id = preset.get("family_id")
    if isinstance(family_id, str) and family_id:
        return family_id
    look_id = preset.get("look_id")
    if isinstance(look_id, str) and "::" in look_id:
        return look_id.split("::", 1)[0]
    raise CorrectionPlanError(f"Cannot resolve family for {preset.get('preset_id')}")


def build_subset_manifest(
    gate: dict[str, Any],
    presets: list[dict[str, Any]],
    manifest_id: str,
    status: str,
    output_dir: Path,
    phase: str,
) -> dict[str, Any]:
    subject_ids = {str(preset["subject_id"]) for preset in presets}
    family_ids = {family_id_for(preset) for preset in presets}
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
        raise CorrectionPlanError(f"Subject subset is incomplete for {manifest_id}")
    if len(families) != len(family_ids):
        raise CorrectionPlanError(f"Family subset is incomplete for {manifest_id}")

    manifest = copy.deepcopy(gate)
    manifest["library_id"] = f"{gate['library_id']}__{manifest_id}"
    manifest["status"] = status
    manifest["subjects"] = subjects
    manifest["families"] = families
    manifest["presets"] = copy.deepcopy(presets)
    execution_policy = manifest.setdefault("execution_policy", {})
    execution_policy["remove_source_accessories"] = True
    manifest["correction_run"] = {
        "phase": phase,
        "bodyfit_id": "F01_Lean",
        "cause": "detached source accessory geometry in right-profile evidence",
        "planned_output_root": str(output_dir),
        "requires_fresh_cc_process": True,
        "visual_gate": [
            "source accessories removed",
            "scalp hair remains intact",
            "detached black geometry absent in right_profile",
        ],
    }
    manifest["counts"] = {
        "subject_count": len(subjects),
        "family_count": len(families),
        "logical_group_count": len({preset.get("look_id") for preset in presets}),
        "test_case_count": len(presets),
        "views_per_case": 5,
        "expected_image_count": len(presets) * 5,
        "cases_by_sex": {
            sex: sum(1 for preset in presets if preset.get("sex") == sex)
            for sex in ("female", "male")
        },
    }
    return manifest


def command_for(manifest: Path, output_dir: Path, job_id: str) -> list[str]:
    return [
        "python",
        r"D:\UE\Lance_Work\00_engine\character_creator_bridge\cc_bridge_client.py",
        "validate-bodies",
        "--library-file",
        str(manifest),
        "--output-dir",
        str(output_dir),
        "--confirm-scene-replace",
        "--auto-dismiss-undo-warning",
        "--job-id",
        job_id,
        "--timeout",
        "21600",
    ]


def build_plan(
    gate_path: Path,
    validation_paths: list[Path],
    output_path: Path,
    manifests_dir: Path,
    run_root: Path,
    cases_per_chunk: int,
    job_prefix: str,
    smoke_preset_id: str | None = None,
) -> dict[str, Any]:
    if cases_per_chunk < 1:
        raise CorrectionPlanError("cases_per_chunk must be positive")
    if not validation_paths:
        raise CorrectionPlanError("At least one validation checkpoint is required")
    if not job_prefix or any(character.isspace() for character in job_prefix):
        raise CorrectionPlanError("job_prefix must be non-empty and contain no spaces")

    gate = read_json(gate_path)
    gate_presets = gate.get("presets", [])
    if not isinstance(gate_presets, list) or not gate_presets:
        raise CorrectionPlanError("Gate manifest has no presets")
    verified: set[str] = set()
    for validation_path in validation_paths:
        verified.update(verified_preset_ids(read_json(validation_path)))

    affected = [
        copy.deepcopy(preset)
        for preset in gate_presets
        if preset.get("bodyfit_id") == "F01_Lean"
        and preset.get("preset_id") in verified
    ]
    if not affected:
        raise CorrectionPlanError("No verified F01_Lean presets were found")
    affected.sort(key=lambda preset: str(preset.get("preset_id")))
    affected_ids = {str(preset["preset_id"]) for preset in affected}

    if smoke_preset_id is None:
        smoke = affected[0]
    else:
        if smoke_preset_id not in affected_ids:
            raise CorrectionPlanError(
                f"Smoke preset is not a verified F01 case: {smoke_preset_id}"
            )
        smoke = next(
            preset for preset in affected if preset["preset_id"] == smoke_preset_id
        )

    manifests_dir.mkdir(parents=True, exist_ok=True)
    smoke_manifest_path = manifests_dir / "smoke.json"
    smoke_output = run_root / "smoke"
    smoke_manifest = build_subset_manifest(
        gate,
        [smoke],
        "f01_accessory_cleanup_smoke",
        "planned_correction_smoke",
        smoke_output,
        "smoke",
    )
    write_json(smoke_manifest_path, smoke_manifest)

    chunks: list[dict[str, Any]] = []
    for start in range(0, len(affected), cases_per_chunk):
        items = affected[start : start + cases_per_chunk]
        chunk_id = f"chunk_{len(chunks) + 1:02d}"
        manifest_path = manifests_dir / f"{chunk_id}.json"
        output_dir = run_root / chunk_id
        manifest = build_subset_manifest(
            gate,
            items,
            f"f01_accessory_cleanup_{chunk_id}",
            "planned_correction_chunk",
            output_dir,
            "correction",
        )
        write_json(manifest_path, manifest)
        job_id = f"{job_prefix}_{chunk_id}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "status": "blocked_until_smoke_passes",
                "case_count": len(items),
                "expected_image_count": len(items) * 5,
                "preset_ids": [item["preset_id"] for item in items],
                "manifest_path": str(manifest_path),
                "output_dir": str(output_dir),
                "job_id": job_id,
                "requires_offline_cc_restart_before_run": True,
                "command": command_for(manifest_path, output_dir, job_id),
            }
        )

    expected = {smoke_manifest_path.resolve()} | {
        Path(chunk["manifest_path"]).resolve() for chunk in chunks
    }
    for stale in manifests_dir.glob("*.json"):
        if stale.resolve() not in expected:
            stale.unlink()

    smoke_job_id = f"{job_prefix}_smoke"
    plan = {
        "schema_version": 1,
        "plan_id": "cc_outfit_f01_accessory_correction_plan_20260815_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate_manifest": str(gate_path),
        "validation_checkpoints": [str(path) for path in validation_paths],
        "bodyfit_id": "F01_Lean",
        "cause": "detached Double Bubble Braids source accessory geometry",
        "affected_case_count": len(affected),
        "affected_preset_ids": [preset["preset_id"] for preset in affected],
        "safety_policy": {
            "smoke_must_pass_before_corrections": True,
            "restart_cc_offline_before_smoke": True,
            "restart_cc_offline_before_every_correction_chunk": True,
            "agent_must_not_restart_cc": True,
            "cases_per_chunk": cases_per_chunk,
            "existing_machine_passes_remain_historical_only": True,
        },
        "smoke": {
            "status": "pending",
            "preset_id": smoke["preset_id"],
            "manifest_path": str(smoke_manifest_path),
            "output_dir": str(smoke_output),
            "job_id": smoke_job_id,
            "expected_image_count": 5,
            "command": command_for(smoke_manifest_path, smoke_output, smoke_job_id),
        },
        "correction_chunks": chunks,
    }
    write_json(output_path, plan)
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build F01 source-accessory cleanup smoke and correction chunks."
    )
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument(
        "--validation", type=Path, action="append", required=True,
        help="Successful gate checkpoint; repeat for multiple checkpoints.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifests-dir", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--cases-per-chunk", type=int, default=5)
    parser.add_argument(
        "--job-prefix", default="outfit_gate_20260815_f01_fix_v1"
    )
    parser.add_argument("--smoke-preset-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(
        gate_path=args.gate,
        validation_paths=args.validation,
        output_path=args.output,
        manifests_dir=args.manifests_dir,
        run_root=args.run_root,
        cases_per_chunk=args.cases_per_chunk,
        job_prefix=args.job_prefix,
        smoke_preset_id=args.smoke_preset_id,
    )
    print(f"Wrote: {args.output}")
    print(f"affected_cases: {plan['affected_case_count']}")
    print(f"correction_chunks: {len(plan['correction_chunks'])}")
    print(f"smoke_preset: {plan['smoke']['preset_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
