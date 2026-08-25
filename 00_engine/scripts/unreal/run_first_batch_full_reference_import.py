#!/usr/bin/env python3
"""Run the resumable first-batch FullReference UE import gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time


SCRIPT_ROOT = Path(__file__).resolve().parent
REMOTE_EXEC = SCRIPT_ROOT / "ue_remote_exec.py"
UE_PAYLOAD = SCRIPT_ROOT / "ue_import_first_batch_full_reference_looks.py"
DIALOG_WATCHER = SCRIPT_ROOT / "ue_reallusion_dialog_watcher.py"
REQUIRED_EXPORTS = (
    SCRIPT_ROOT.parent
    / "dataset"
    / "first_batch_required_exports_20260820_v1.json"
)
REQUIRED_EXPORTS_V2 = (
    SCRIPT_ROOT.parent
    / "dataset"
    / "first_batch_required_exports_20260822_v2.json"
)
REPORT_ROOT = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "unreal_character_import"
    / "first_batch_full_reference_20260821_v1"
)
REPORT_ROOT_V2 = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "unreal_character_import"
    / "first_batch_full_reference_expansion_20260822_v2"
)
MAX_INTERACTIVE_LOOKS_PER_SESSION = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def remote_command(
    mode: str,
    required_exports: Path,
    report_root: Path,
    look_id: str | None = None,
    interactive: bool = False,
    automated_task: bool = False,
) -> str:
    script_path = str(UE_PAYLOAD.resolve())
    assignments = [
        f"DM_FIRST_BATCH_LOOK_MODE={mode!r}",
        f"DM_FIRST_BATCH_REQUIRED_EXPORTS_PATH={str(required_exports.resolve())!r}",
        f"DM_FIRST_BATCH_LOOK_REPORT_ROOT={str(report_root.resolve())!r}",
    ]
    if look_id:
        assignments.append(f"DM_FIRST_BATCH_LOOK_ID={look_id!r}")
    assignments.append(f"DM_FIRST_BATCH_LOOK_INTERACTIVE={interactive!r}")
    assignments.append(f"DM_FIRST_BATCH_LOOK_AUTOMATED_TASK={automated_task!r}")
    assignments.append(
        "exec(compile(open(r%r, 'r', encoding='utf-8').read(), "
        "r%r, 'exec'), globals())" % (script_path, script_path)
    )
    return "; ".join(assignments)


def run_remote(
    project: str,
    mode: str,
    required_exports: Path,
    report_root: Path,
    look_id: str | None = None,
    interactive: bool = False,
    automated_task: bool = False,
) -> dict:
    command = [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            project,
            "--command",
            remote_command(
                mode,
                required_exports,
                report_root,
                look_id,
                interactive,
                automated_task,
            ),
            "--discovery-timeout",
            "30",
        ]
    if interactive:
        command.append("--interactive")
    process = subprocess.run(
        command,
        cwd=str(SCRIPT_ROOT.parents[2]),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    envelope = None
    try:
        envelope = json.loads(process.stdout)
    except json.JSONDecodeError:
        pass
    return {
        "mode": mode,
        "look_id": look_id,
        "returncode": process.returncode,
        "success": process.returncode == 0,
        "envelope": envelope,
        "stdout_tail": process.stdout[-4000:],
        "stderr_tail": process.stderr[-4000:],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="datatry_02")
    parser.add_argument("--required-exports", type=Path, default=REQUIRED_EXPORTS)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    parser.add_argument(
        "--expanded-matrix",
        action="store_true",
        help="Use the frozen 32-Look v2 manifest and expansion report root.",
    )
    parser.add_argument("--look-id", action="append", default=[])
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Permit Reallusion modal UI during import",
    )
    parser.add_argument(
        "--automated-task",
        action="store_true",
        help="Preconfigure FBX options while still permitting Auto Setup modal UI",
    )
    parser.add_argument(
        "--auto-dialogs",
        action="store_true",
        help="Confirm the known Auto Setup and FBX modal dialogs by keyboard",
    )
    return parser.parse_args()


def validate_interactive_batch_policy(
    *,
    selected_ids: list[str],
    interactive: bool,
    auto_dialogs: bool,
    continue_on_error: bool,
) -> None:
    if not (interactive or auto_dialogs):
        return
    if continue_on_error:
        raise RuntimeError(
            "Interactive FullReference imports must stop on the first failure; "
            "do not use --continue-on-error."
        )
    if len(selected_ids) > MAX_INTERACTIVE_LOOKS_PER_SESSION:
        raise RuntimeError(
            "Interactive FullReference imports are limited to "
            f"{MAX_INTERACTIVE_LOOKS_PER_SESSION} Look IDs per UE session; "
            "restart Unreal Editor between batches."
        )


def main() -> int:
    args = parse_args()
    if args.expanded_matrix:
        args.required_exports = REQUIRED_EXPORTS_V2
        args.report_root = REPORT_ROOT_V2
    manifest = read_json(args.required_exports)
    available_ids = [
        row["look_id"] for row in manifest.get("full_reference_looks") or []
    ]
    selected_ids = args.look_id or available_ids
    unknown = sorted(set(selected_ids) - set(available_ids))
    if unknown:
        raise RuntimeError("Unknown Look IDs: " + ", ".join(unknown))
    validate_interactive_batch_policy(
        selected_ids=selected_ids,
        interactive=args.interactive,
        auto_dialogs=args.auto_dialogs,
        continue_on_error=args.continue_on_error,
    )

    aggregate = {
        "schema_version": 1,
        "run_id": (
            "first_batch_full_reference_ue_import_20260822_v2"
            if args.expanded_matrix
            else "first_batch_full_reference_ue_import_20260821_v1"
        ),
        "started_at_utc": now(),
        "finished_at_utc": None,
        "project": args.project,
        "requested_look_ids": selected_ids,
        "preflight": None,
        "rows": [],
        "success": False,
    }
    aggregate_path = args.report_root / "aggregate_import_gate.json"

    if not args.skip_preflight:
        aggregate["preflight"] = run_remote(
            args.project, "preflight", args.required_exports, args.report_root
        )
        write_json(aggregate_path, aggregate)
        if not aggregate["preflight"]["success"]:
            print(json.dumps(aggregate, ensure_ascii=True, indent=2))
            return 1

    for index, look_id in enumerate(selected_ids, 1):
        print(f"[{index}/{len(selected_ids)}] Importing/validating {look_id}", flush=True)
        watcher = None
        if args.auto_dialogs:
            watcher = subprocess.Popen(
                [
                    sys.executable,
                    str(DIALOG_WATCHER),
                    "--project-title",
                    args.project,
                ],
                cwd=str(SCRIPT_ROOT.parents[2]),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        row = run_remote(
            args.project,
            "import",
            args.required_exports,
            args.report_root,
            look_id,
            args.interactive or args.auto_dialogs,
            (args.automated_task or not args.interactive) and not args.auto_dialogs,
        )
        if watcher is not None:
            try:
                watcher_stdout, watcher_stderr = watcher.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                watcher.terminate()
                watcher_stdout, watcher_stderr = watcher.communicate(timeout=5)
            watcher_result = None
            try:
                watcher_result = json.loads(watcher_stdout)
            except json.JSONDecodeError:
                pass
            row["dialog_automation"] = {
                "returncode": watcher.returncode,
                "result": watcher_result,
                "stdout": watcher_stdout[-2000:],
                "stderr": watcher_stderr[-2000:],
            }
        row["index"] = index
        row["completed_at_utc"] = now()
        aggregate["rows"].append(row)
        write_json(aggregate_path, aggregate)
        if not row["success"] and not args.continue_on_error:
            break
        if index < len(selected_ids):
            time.sleep(max(0.0, args.delay_seconds))

    aggregate["finished_at_utc"] = now()
    aggregate["passed_count"] = sum(row["success"] for row in aggregate["rows"])
    aggregate["failed_count"] = sum(not row["success"] for row in aggregate["rows"])
    aggregate["success"] = (
        len(aggregate["rows"]) == len(selected_ids)
        and aggregate["failed_count"] == 0
    )
    write_json(aggregate_path, aggregate)
    print(json.dumps(aggregate, ensure_ascii=True, indent=2))
    return 0 if aggregate["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
