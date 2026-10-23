#!/usr/bin/env python3
"""Run resumable runtime-build phases for the modular outfit pilot."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: run_modular_outfit_runtime_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
REMOTE_EXEC = SCRIPT_ROOT / "ue_remote_exec.py"
PLAN_BUILDER = SCRIPT_ROOT / "modular_outfit_runtime_plan_v1.py"
UE_WORKER = SCRIPT_ROOT / "ue_build_modular_outfit_runtime_v1.py"
MOTION_WORKER = SCRIPT_ROOT / "ue_modular_outfit_motion_validation_v1.py"
REVIEW_WORKER = SCRIPT_ROOT / "ue_build_modular_outfit_review_level_v1.py"
REPORT_ROOT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "modular_outfit_pilot_20260829_v1"
    / "runtime"
    / "runs"
)
BODYFIT_IDS = ("M02_Average", "F02_Average")
PHASE_TO_MODE = {
    "build": "build_bodyfit",
    "validate": "validate_switches",
    "stage": "stage_variant",
    "cleanup": "cleanup_stage",
}
MOTION_PHASE_TO_MODE = {
    "motion-import": "import_motion",
    "motion-validate": "validate_motion",
    "motion-stage": "stage_motion",
}
REVIEW_PHASE = "review-level"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def runtime_command(mode: str, bodyfit_id: str, variant_id: str | None) -> str:
    worker = str(UE_WORKER.resolve())
    assignments = [
        f"DM_MODULAR_RUNTIME_MODE={mode!r}",
        f"DM_MODULAR_BODYFIT_ID={bodyfit_id!r}",
        f"__file__={worker!r}",
    ]
    if variant_id is not None:
        assignments.append(f"DM_MODULAR_VARIANT_ID={variant_id!r}")
    assignments.append(
        "exec(compile(open(r%r, 'r', encoding='utf-8').read(), "
        "r%r, 'exec'), globals())" % (worker, worker)
    )
    return "; ".join(assignments)


def motion_command(mode: str, bodyfit_id: str, variant_id: str | None) -> str:
    worker = str(MOTION_WORKER.resolve())
    assignments = [
        f"DM_MODULAR_MOTION_MODE={mode!r}",
        f"DM_MODULAR_BODYFIT_ID={bodyfit_id!r}",
        f"__file__={worker!r}",
    ]
    if variant_id is not None:
        assignments.append(f"DM_MODULAR_VARIANT_ID={variant_id!r}")
    assignments.append(
        "exec(compile(open(r%r, 'r', encoding='utf-8').read(), "
        "r%r, 'exec'), globals())" % (worker, worker)
    )
    return "; ".join(assignments)


def review_command() -> str:
    worker = str(REVIEW_WORKER.resolve())
    return "; ".join(
        [
            "DM_BUILD_MODULAR_REVIEW_LEVEL=True",
            f"__file__={worker!r}",
            (
                "exec(compile(open(r%r, 'r', encoding='utf-8').read(), "
                "r%r, 'exec'), globals())" % (worker, worker)
            ),
        ]
    )


def run_process(command: list[str]) -> dict:
    process = subprocess.run(
        command,
        cwd=str(LANCE_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": process.returncode,
        "success": process.returncode == 0,
        "stdout_tail": process.stdout[-6000:],
        "stderr_tail": process.stderr[-6000:],
    }


def run_plan() -> dict:
    return run_process([sys.executable, str(PLAN_BUILDER)])


def run_remote(
    project: str,
    mode: str,
    bodyfit_id: str,
    variant_id: str | None,
    motion: bool = False,
) -> dict:
    return run_process(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            project,
            "--command",
            (
                motion_command(mode, bodyfit_id, variant_id)
                if motion
                else runtime_command(mode, bodyfit_id, variant_id)
            ),
            "--discovery-timeout",
            "30",
        ]
    )


def run_review(project: str) -> dict:
    return run_process(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            project,
            "--command",
            review_command(),
            "--discovery-timeout",
            "30",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("plan", *PHASE_TO_MODE, *MOTION_PHASE_TO_MODE, REVIEW_PHASE),
        required=True,
    )
    parser.add_argument("--project", default="datatry_02")
    parser.add_argument("--bodyfit-id", choices=BODYFIT_IDS, action="append")
    parser.add_argument("--variant-id")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser.parse_args()


def selected_bodyfits(requested: list[str] | None) -> list[str]:
    selected = list(requested or BODYFIT_IDS)
    if len(selected) != len(set(selected)):
        raise RuntimeError("Requested bodyfit IDs are not unique")
    return selected


def validate_args(args: argparse.Namespace) -> list[str]:
    if args.phase in {"plan", REVIEW_PHASE}:
        if args.bodyfit_id or args.variant_id or args.continue_on_error:
            raise RuntimeError(
                f"{args.phase} phase accepts no bodyfit, variant, or retry options"
            )
        return []
    bodyfits = selected_bodyfits(args.bodyfit_id)
    if args.phase in {"stage", "motion-stage"}:
        if len(bodyfits) != 1 or not args.variant_id:
            raise RuntimeError("Stage requires one --bodyfit-id and --variant-id")
    elif args.variant_id:
        raise RuntimeError("--variant-id applies only to the stage phase")
    if args.phase in {"build", "motion-import"} and args.continue_on_error:
        raise RuntimeError("Blueprint build stops on the first failure")
    return bodyfits


def main() -> int:
    args = parse_args()
    bodyfits = validate_args(args)
    run_id = f"{args.phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    aggregate = {
        "schema_version": 1,
        "run_id": run_id,
        "phase": args.phase,
        "project": args.project,
        "bodyfit_ids": bodyfits,
        "variant_id": args.variant_id,
        "started_at_utc": utc_now(),
        "finished_at_utc": None,
        "rows": [],
        "success": False,
    }
    output = REPORT_ROOT / f"{run_id}.json"
    if args.phase == "plan":
        aggregate["rows"].append(run_plan())
    elif args.phase == REVIEW_PHASE:
        row = run_review(args.project)
        row["mode"] = REVIEW_PHASE
        row["completed_at_utc"] = utc_now()
        aggregate["rows"].append(row)
    else:
        motion_phase = args.phase in MOTION_PHASE_TO_MODE
        mode = (
            MOTION_PHASE_TO_MODE[args.phase]
            if motion_phase
            else PHASE_TO_MODE[args.phase]
        )
        for bodyfit_id in bodyfits:
            row = run_remote(
                args.project,
                mode,
                bodyfit_id,
                args.variant_id,
                motion=motion_phase,
            )
            row["bodyfit_id"] = bodyfit_id
            row["mode"] = mode
            row["completed_at_utc"] = utc_now()
            aggregate["rows"].append(row)
            write_json(output, aggregate)
            if not row["success"] and not args.continue_on_error:
                break
    aggregate["finished_at_utc"] = utc_now()
    aggregate["passed_count"] = sum(row["success"] for row in aggregate["rows"])
    aggregate["failed_count"] = sum(not row["success"] for row in aggregate["rows"])
    aggregate["success"] = (
        bool(aggregate["rows"])
        and aggregate["failed_count"] == 0
        and (
            args.phase in {"plan", REVIEW_PHASE}
            or len(aggregate["rows"]) == len(bodyfits)
        )
    )
    write_json(output, aggregate)
    print(json.dumps(aggregate, ensure_ascii=True, indent=2))
    return 0 if aggregate["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
