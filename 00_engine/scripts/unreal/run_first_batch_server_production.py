#!/usr/bin/env python3
"""Validate a 50-node Editor batch, finish 640 nodes, and build dataset_v1."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SUPERVISOR = ROOT / "00_engine/scripts/unreal/run_first_batch_server_render_batches.py"
DELIVERY_BUILDER = ROOT / "00_engine/scripts/dataset/build_first_batch_delivery_v1.py"
DEFAULT_GRAPH_ROOT = ROOT / "00_engine/outputs/first_batch_dataset/graph_20260824_v1"
DEFAULT_PROMPT_ROOT = DEFAULT_GRAPH_ROOT / "text_first_batch_20260824_v2"
SCHEMA_VERSION = "first_batch_server_production_controller_v1"

STAGES = (
    {"id": "stage_0050", "start_index": 1, "limit": 50, "audit_limit": 50},
    {"id": "stage_0640", "start_index": 51, "limit": 590, "audit_limit": 640},
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--delivery-root", required=True, type=Path)
    parser.add_argument("--engine-root", required=True, type=Path)
    parser.add_argument("--uproject", required=True, type=Path)
    parser.add_argument("--graph-root", type=Path, default=DEFAULT_GRAPH_ROOT)
    parser.add_argument("--prompt-root", type=Path, default=DEFAULT_PROMPT_ROOT)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-invocations-per-batch", type=int, default=2)
    parser.add_argument("--confirm-full-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.confirm_full_run:
        raise ValueError("Full production requires --confirm-full-run")
    if args.batch_size != 50:
        raise ValueError("This production run requires --batch-size 50")
    if args.max_invocations_per_batch != 2:
        raise ValueError(
            "The accepted recovery policy requires --max-invocations-per-batch 2"
        )
    if args.delivery_root.exists() and not (args.delivery_root / "manifest.json").is_file():
        raise ValueError(
            f"Delivery root exists without a manifest: {args.delivery_root}"
        )


def supervisor_command(
    args: argparse.Namespace,
    *,
    start_index: int,
    limit: int,
    mode: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(SUPERVISOR),
        "--run-root",
        str(args.run_root.resolve()),
        "--start-index",
        str(start_index),
        "--limit",
        str(limit),
        "--batch-size",
        str(args.batch_size),
        "--max-invocations-per-batch",
        str(args.max_invocations_per_batch),
        "--engine-root",
        str(args.engine_root.resolve()),
        "--uproject",
        str(args.uproject.resolve()),
        "--graph-root",
        str(args.graph_root.resolve()),
    ]
    if limit >= 640:
        command.append("--confirm-full-run")
    if mode:
        command.append(mode)
    return command


def run_logged(command: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{utc_now()}] command={json.dumps(command)}\n")
        log.flush()
        completed = subprocess.run(
            command,
            check=False,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        log.write(f"[{utc_now()}] exit_code={completed.returncode}\n")
    return completed.returncode


def audit_passed(run_root: Path, expected: int) -> bool:
    result_path = run_root / "result.json"
    if not result_path.is_file():
        return False
    result = read_json(result_path)
    return (
        result.get("status") == "passed"
        and result.get("selected_count") == expected
        and result.get("accepted_count") == expected
    )


def can_audit_existing(run_root: Path) -> bool:
    return (
        (run_root / "inputs.lock.json").is_file()
        and (run_root / "runtime/server_editor/profile.json").is_file()
    )


def package_passed(delivery_root: Path) -> bool:
    manifest_path = delivery_root / "manifest.json"
    chains_path = delivery_root / "chains.json"
    simple_chains_path = delivery_root / "chains_simple.json"
    if not all(
        path.is_file()
        for path in (manifest_path, chains_path, simple_chains_path)
    ):
        return False
    manifest = read_json(manifest_path)
    counts = manifest.get("counts", {})
    checks = manifest.get("checks", {})
    return (
        manifest.get("status") == "package_candidate_pending_release_qa"
        and counts == {"videos": 640, "chains": 4000, "turns": 15000}
        and bool(checks)
        and all(checks.values())
        and len(list((delivery_root / "videos").glob("*.mp4"))) == 640
    )


def update_status(status_path: Path, status: dict, **changes: object) -> None:
    status.update(changes)
    status["updated_at_utc"] = utc_now()
    atomic_write_json(status_path, status)


def run_stage(args: argparse.Namespace, stage: dict, control_root: Path, status: dict) -> None:
    stage_id = stage["id"]
    audit_log = control_root / "logs" / f"{stage_id}_audit.log"
    render_log = control_root / "logs" / f"{stage_id}_render.log"
    status_path = control_root / "status.json"
    audit = supervisor_command(
        args,
        start_index=1,
        limit=stage["audit_limit"],
        mode="--audit-existing",
    )
    existing_audit_passed = False
    if can_audit_existing(args.run_root.resolve()):
        update_status(status_path, status, state="auditing", current_stage=stage_id)
        existing_audit_passed = (
            run_logged(audit, audit_log) == 0
            and audit_passed(args.run_root.resolve(), stage["audit_limit"])
        )
    if not existing_audit_passed:
        render = supervisor_command(
            args,
            start_index=stage["start_index"],
            limit=stage["limit"],
        )
        update_status(status_path, status, state="rendering", current_stage=stage_id)
        if run_logged(render, render_log) != 0:
            raise RuntimeError(f"Render stage failed: {stage_id}")
        update_status(status_path, status, state="auditing", current_stage=stage_id)
        if run_logged(audit, audit_log) != 0 or not audit_passed(
            args.run_root.resolve(), stage["audit_limit"]
        ):
            raise RuntimeError(f"Acceptance audit failed: {stage_id}")
    checkpoint = {
        "schema_version": SCHEMA_VERSION,
        "stage_id": stage_id,
        "status": "passed",
        "accepted_node_count": stage["audit_limit"],
        "passed_at_utc": utc_now(),
    }
    atomic_write_json(control_root / "checkpoints" / f"{stage_id}.json", checkpoint)
    status.setdefault("passed_stages", []).append(stage_id)
    update_status(status_path, status, state="stage_passed", current_stage=stage_id)


def build_package(args: argparse.Namespace, control_root: Path, status: dict) -> None:
    status_path = control_root / "status.json"
    update_status(status_path, status, state="packaging", current_stage="dataset_v1")
    if not package_passed(args.delivery_root.resolve()):
        command = [
            sys.executable,
            str(DELIVERY_BUILDER),
            "--graph-dir",
            str(args.graph_root.resolve()),
            "--prompt-dir",
            str(args.prompt_root.resolve()),
            "--render-run-root",
            str(args.run_root.resolve()),
            "--output-dir",
            str(args.delivery_root.resolve()),
            "--dataset-id",
            "dataset_v1",
            "--package-scope",
            "full_first_batch",
        ]
        if run_logged(command, control_root / "logs/dataset_v1_package.log") != 0:
            raise RuntimeError("dataset_v1 packaging failed")
    if not package_passed(args.delivery_root.resolve()):
        raise RuntimeError("dataset_v1 package validation failed")
    atomic_write_json(
        control_root / "checkpoints/package.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "passed",
            "delivery_root": str(args.delivery_root.resolve()),
            "passed_at_utc": utc_now(),
        },
    )
    update_status(status_path, status, state="passed", current_stage="complete")


def main() -> int:
    args = parse_args()
    validate_args(args)
    args.run_root = args.run_root.resolve()
    args.delivery_root = args.delivery_root.resolve()
    control_root = args.run_root / "runtime/production_controller"
    status_path = control_root / "status.json"
    status = {
        "schema_version": SCHEMA_VERSION,
        "state": "starting",
        "started_at_utc": utc_now(),
        "run_root": str(args.run_root),
        "delivery_root": str(args.delivery_root),
        "stage_policy": list(STAGES),
        "batch_size": args.batch_size,
        "max_invocations_per_batch": args.max_invocations_per_batch,
        "passed_stages": [],
    }
    atomic_write_json(status_path, status)
    try:
        dry_run = supervisor_command(
            args,
            start_index=1,
            limit=640,
            mode="--dry-run",
        )
        update_status(status_path, status, state="dry_run", current_stage="selection_0640")
        if run_logged(dry_run, control_root / "logs/selection_0640_dry_run.log") != 0:
            raise RuntimeError("640-node dry-run failed")
        for stage in STAGES:
            run_stage(args, stage, control_root, status)
        build_package(args, control_root, status)
    except Exception as exc:
        update_status(
            status_path,
            status,
            state="failed",
            error=str(exc),
            failed_at_utc=utc_now(),
        )
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
