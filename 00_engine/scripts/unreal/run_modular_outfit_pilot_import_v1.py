#!/usr/bin/env python3
"""Run resumable UE import phases for the modular outfit pilot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
REMOTE_EXEC = SCRIPT_ROOT / "ue_remote_exec.py"
UE_WORKER = SCRIPT_ROOT / "ue_modular_outfit_pilot_import_v1.py"
DIALOG_WATCHER = SCRIPT_ROOT / "ue_reallusion_dialog_watcher.py"
LEGACY_PILOT_MANIFEST = SCRIPT_ROOT / "ue_modular_outfit_pilot_manifest_20260829_v1.json"
MANIFEST = LEGACY_PILOT_MANIFEST
REPORT_ROOT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "modular_outfit_pilot_20260829_v1"
)
PHASE_TO_MODE = {
    "cleanup": "cleanup_case",
    "preflight": "preflight",
    "reference": "import_reference",
    "split": "import_split",
    "materials": "apply_materials",
    "validate": "validate_case",
}
MAX_REFERENCE_CASES_PER_SESSION = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def remote_command(
    mode: str, case_id: str | None, interactive: bool = False
) -> str:
    worker = str(UE_WORKER.resolve())
    assignments = [f"DM_MODULAR_MODE={mode!r}"]
    assignments.extend([
        f"DM_MODULAR_MANIFEST_PATH={str(MANIFEST.resolve())!r}",
        f"DM_MODULAR_REPORT_ROOT={str(REPORT_ROOT.resolve())!r}",
    ])
    if case_id is not None:
        assignments.append(f"DM_MODULAR_CASE_ID={case_id!r}")
    if interactive:
        assignments.append("DM_MODULAR_INTERACTIVE=True")
    assignments.append(
        "exec(compile(open(r%r, 'r', encoding='utf-8').read(), "
        "r%r, 'exec'), globals())" % (worker, worker)
    )
    return "; ".join(assignments)


def run_remote(
    project: str,
    mode: str,
    case_id: str | None,
    interactive: bool,
) -> dict:
    command = [
        sys.executable,
        str(REMOTE_EXEC),
        "--project",
        project,
        "--command",
        remote_command(mode, case_id, interactive),
        "--discovery-timeout",
        "30",
    ]
    if interactive:
        command.append("--interactive")
    process = subprocess.run(
        command,
        cwd=str(LANCE_ROOT),
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
        "case_id": case_id,
        "returncode": process.returncode,
        "success": process.returncode == 0,
        "envelope": envelope,
        "stdout_tail": process.stdout[-5000:],
        "stderr_tail": process.stderr[-5000:],
    }


def start_dialog_watcher(project: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            str(DIALOG_WATCHER),
            "--project-title",
            project,
            "--timeout-seconds",
            "3600",
        ],
        cwd=str(LANCE_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def finish_dialog_watcher(watcher: subprocess.Popen) -> dict:
    try:
        stdout, stderr = watcher.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        watcher.terminate()
        stdout, stderr = watcher.communicate(timeout=5)
    parsed = None
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        pass
    return {
        "returncode": watcher.returncode,
        "result": parsed,
        "stdout_tail": stdout[-3000:],
        "stderr_tail": stderr[-3000:],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="datatry_02")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--phase", choices=sorted(PHASE_TO_MODE), required=True)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--auto-dialogs", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=2.0)
    return parser.parse_args()


def select_case_ids(manifest: dict, requested: list[str]) -> list[str]:
    available = [case["case_id"] for case in manifest.get("cases") or []]
    if len(available) != len(set(available)):
        raise RuntimeError("Manifest case IDs are not unique")
    selected = requested or available
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise RuntimeError("Unknown modular pilot case IDs: " + ", ".join(unknown))
    if len(selected) != len(set(selected)):
        raise RuntimeError("Requested modular pilot case IDs are not unique")
    return selected


def main() -> int:
    global MANIFEST, REPORT_ROOT
    args = parse_args()
    MANIFEST = args.manifest.resolve()
    REPORT_ROOT = args.report_root.resolve()
    # Keep this runner as the current wardrobe importer. Only the fixed old
    # 14-case execution input is retired; explicitly selected BASE recovery
    # remains available without changing shared selectors or remote helpers.
    if MANIFEST == LEGACY_PILOT_MANIFEST.resolve():
        if (args.phase == "preflight" or not args.case_id
                or set(args.case_id) - {"M_BASE", "F_BASE"}):
            raise RuntimeError(
                "Retired 14-case modular outfit pilot execution. Use an explicit "
                "current --manifest; legacy recovery requires explicit "
                "--case-id M_BASE/F_BASE and cannot run global preflight."
            )
    manifest = read_json(MANIFEST)
    mode = PHASE_TO_MODE[args.phase]
    selected = [] if args.phase == "preflight" else select_case_ids(
        manifest, args.case_id
    )
    if args.phase == "preflight" and args.case_id:
        raise RuntimeError("Preflight is global and does not accept --case-id")
    if args.phase != "preflight" and manifest.get("import_scope") == "wardrobe_average_v1":
        bases = {c["case_id"] for c in manifest["cases"] if c.get("reuse_existing_base")}
        if set(selected) & bases:
            raise RuntimeError("Select explicit garment units; existing bases are read-only")
        if args.phase == "cleanup":
            raise RuntimeError("Wardrobe cleanup requires a separate reviewed operation")
    if args.phase != "reference" and (args.interactive or args.auto_dialogs):
        raise RuntimeError("Interactive dialog options apply only to reference imports")
    if args.phase == "reference":
        if not (args.interactive or args.auto_dialogs):
            raise RuntimeError(
                "Reference import requires --interactive or --auto-dialogs"
            )
        if len(selected) > MAX_REFERENCE_CASES_PER_SESSION:
            raise RuntimeError(
                "Reference imports are limited to "
                f"{MAX_REFERENCE_CASES_PER_SESSION} cases per UE session"
            )
        if args.continue_on_error:
            raise RuntimeError("Reference imports must stop on the first failure")

    run_id = f"{args.phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    aggregate = {
        "schema_version": 1,
        "run_id": run_id,
        "phase": args.phase,
        "mode": mode,
        "project": args.project,
        "requested_case_ids": selected,
        "started_at_utc": now(),
        "finished_at_utc": None,
        "rows": [],
        "success": False,
    }
    aggregate_path = REPORT_ROOT / "runs" / f"{run_id}.json"
    operations = [None] if args.phase == "preflight" else selected
    for index, case_id in enumerate(operations, 1):
        print(
            f"[{index}/{len(operations)}] {mode}"
            + (f" {case_id}" if case_id else ""),
            flush=True,
        )
        watcher = start_dialog_watcher(args.project) if args.auto_dialogs else None
        row = run_remote(
            args.project,
            mode,
            case_id,
            args.interactive or args.auto_dialogs,
        )
        if watcher is not None:
            row["dialog_automation"] = finish_dialog_watcher(watcher)
        row["index"] = index
        row["completed_at_utc"] = now()
        aggregate["rows"].append(row)
        write_json(aggregate_path, aggregate)
        if not row["success"] and not args.continue_on_error:
            break
        if index < len(operations):
            time.sleep(max(0.0, args.delay_seconds))

    aggregate["finished_at_utc"] = now()
    aggregate["passed_count"] = sum(row["success"] for row in aggregate["rows"])
    aggregate["failed_count"] = sum(
        not row["success"] for row in aggregate["rows"]
    )
    aggregate["success"] = (
        len(aggregate["rows"]) == len(operations)
        and aggregate["failed_count"] == 0
    )
    write_json(aggregate_path, aggregate)
    print(json.dumps(aggregate, ensure_ascii=True, indent=2))
    return 0 if aggregate["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
