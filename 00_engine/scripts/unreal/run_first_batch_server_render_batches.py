#!/usr/bin/env python3
"""Run First Batch server rendering in restartable multi-node Editor batches."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
SERVER_RUNNER = (
    ROOT / "00_engine/scripts/unreal/run_first_batch_server_render_jobs.py"
)
SCHEMA_VERSION = "first_batch_server_batch_supervisor_v1"
FULL_BATCH_NODE_COUNT = 640


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-invocations-per-batch", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    parser.add_argument("--confirm-full-run", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-existing", action="store_true")
    args, delegated = parser.parse_known_args()
    if delegated[:1] == ["--"]:
        delegated = delegated[1:]
    validate_arguments(args)
    return args, delegated


def validate_arguments(args: argparse.Namespace) -> None:
    if args.start_index < 1:
        raise ValueError("--start-index must be at least 1")
    if args.limit < 1:
        raise ValueError("--limit must be positive")
    if args.batch_size < 2:
        raise ValueError("--batch-size must be at least 2; one Editor per video is forbidden")
    if args.max_invocations_per_batch < 1:
        raise ValueError("--max-invocations-per-batch must be positive")
    if args.limit >= FULL_BATCH_NODE_COUNT and not args.confirm_full_run:
        raise ValueError(
            f"Rendering {args.limit} nodes requires --confirm-full-run"
        )


def build_batches(start_index: int, limit: int, batch_size: int) -> list[dict]:
    batches = []
    remaining = limit
    current = start_index
    while remaining:
        count = min(batch_size, remaining)
        batches.append(
            {
                "batch_index": len(batches),
                "start_index": current,
                "limit": count,
            }
        )
        current += count
        remaining -= count
    return batches


def build_server_command(
    args: argparse.Namespace,
    delegated: list[str],
    *,
    start_index: int,
    limit: int,
    mode: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(SERVER_RUNNER),
        "--run-root",
        str(args.run_root.resolve()),
        *delegated,
        "--start-index",
        str(start_index),
        "--limit",
        str(limit),
    ]
    if mode is not None:
        command.append(mode)
    if args.confirm_full_run:
        command.append("--confirm-full-run")
    return command


def reserve_supervision_record(run_root: Path) -> tuple[str, Path, Path]:
    records_root = run_root / "runtime/server_editor/supervisors"
    for index in range(10000):
        supervision_id = f"supervision_{index:03d}"
        path = records_root / f"{supervision_id}.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write("{}\n")
        return (
            supervision_id,
            path,
            run_root / "runtime/server_editor/supervisor.json",
        )
    raise RuntimeError("Unable to reserve a server batch supervision record")


def read_latest_result(run_root: Path) -> dict | None:
    path = run_root / "result.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_supervision(path: Path, latest: Path, payload: dict) -> None:
    atomic_write_json(path, payload)
    atomic_write_json(latest, payload)


def run_supervised_batches(
    args: argparse.Namespace,
    delegated: list[str],
) -> int:
    if args.dry_run or args.audit_existing:
        mode = "--dry-run" if args.dry_run else "--audit-existing"
        command = build_server_command(
            args,
            delegated,
            start_index=args.start_index,
            limit=args.limit,
            mode=mode,
        )
        return subprocess.run(command, check=False).returncode

    run_root = args.run_root.resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    supervision_id, record_path, latest_path = reserve_supervision_record(run_root)
    batches = build_batches(args.start_index, args.limit, args.batch_size)
    record = {
        "schema_version": SCHEMA_VERSION,
        "supervision_id": supervision_id,
        "status": "running",
        "started_at_utc": utc_now(),
        "supervisor": str(Path(__file__).resolve()),
        "supervisor_sha256": sha256_file(Path(__file__).resolve()),
        "server_runner": str(SERVER_RUNNER.resolve()),
        "server_runner_sha256": sha256_file(SERVER_RUNNER.resolve()),
        "selection": {
            "start_index": args.start_index,
            "limit": args.limit,
            "batch_size": args.batch_size,
            "batch_count": len(batches),
        },
        "recovery_policy": {
            "max_invocations_per_batch": args.max_invocations_per_batch,
            "retry_delay_seconds": args.retry_delay_seconds,
            "restart_scope": "failed_editor_invocation_only",
        },
        "batches": [],
    }
    write_supervision(record_path, latest_path, record)

    for batch in batches:
        batch_record = {**batch, "status": "running", "invocations": []}
        record["batches"].append(batch_record)
        write_supervision(record_path, latest_path, record)
        for invocation_index in range(args.max_invocations_per_batch):
            command = build_server_command(
                args,
                delegated,
                start_index=batch["start_index"],
                limit=batch["limit"],
            )
            invocation = {
                "invocation_index": invocation_index,
                "started_at_utc": utc_now(),
                "command": command,
            }
            batch_record["invocations"].append(invocation)
            write_supervision(record_path, latest_path, record)
            completed = subprocess.run(command, check=False)
            invocation.update(
                {
                    "ended_at_utc": utc_now(),
                    "exit_code": completed.returncode,
                    "render_result": read_latest_result(run_root),
                }
            )
            if completed.returncode == 0:
                batch_record["status"] = "passed"
                break
            invocation["status"] = "retryable_failed"
            write_supervision(record_path, latest_path, record)
            if invocation_index + 1 < args.max_invocations_per_batch:
                time.sleep(args.retry_delay_seconds)
        else:
            batch_record["status"] = "failed"
            record["status"] = "failed"
            record["ended_at_utc"] = utc_now()
            write_supervision(record_path, latest_path, record)
            return batch_record["invocations"][-1]["exit_code"] or 1
        batch_record["invocations"][-1]["status"] = "passed"
        write_supervision(record_path, latest_path, record)

    record["status"] = "passed"
    record["ended_at_utc"] = utc_now()
    write_supervision(record_path, latest_path, record)
    return 0


def main() -> int:
    args, delegated = parse_args()
    return run_supervised_batches(args, delegated)


if __name__ == "__main__":
    raise SystemExit(main())
