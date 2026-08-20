#!/usr/bin/env python3
"""Orchestrate the live M02 v003 hybrid-face PIE review."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
STAGE_SCRIPT = (
    ROOT / "scripts" / "unreal" / "ue_stage_m02_face_hybrid_validation_v003.py"
)
PIE_SCRIPT = (
    ROOT / "scripts" / "unreal" / "ue_run_m02_face_hybrid_pie_review_v003.py"
)
CLEANUP_SCRIPT = (
    ROOT / "scripts" / "unreal" / "ue_cleanup_m02_face_hybrid_validation_v003.py"
)
REPORT_PATH = (
    ROOT
    / "outputs"
    / "unreal_character_import"
    / "m02_face_hybrid_review_v003"
    / "pie_review.json"
)
PROJECT_NAME = "datatry_02"
MAX_REMOTE_ATTEMPTS = 3


def execute_file_arguments(path: Path) -> list[str]:
    script_path = str(path.resolve())
    command = (
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    return ["--command", command]


def run_remote(arguments: list[str], timeout: float = 120.0) -> None:
    last_error = ""
    for attempt in range(1, MAX_REMOTE_ATTEMPTS + 1):
        completed = subprocess.run(
            [
                sys.executable,
                str(REMOTE_EXEC),
                "--project",
                PROJECT_NAME,
                "--discovery-timeout",
                "30",
                *arguments,
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if completed.returncode == 0:
            try:
                envelope = json.loads(completed.stdout)
            except json.JSONDecodeError:
                envelope = {}
            for line in envelope.get("command_result", {}).get("output", []):
                output = str(line.get("output", "")).strip()
                if output.startswith("DM_FACE_HYBRID_"):
                    print(output)
            return
        last_error = completed.stdout[-4000:] + completed.stderr[-4000:]
        if attempt < MAX_REMOTE_ATTEMPTS:
            time.sleep(1.5)
    raise RuntimeError(f"Unreal remote command failed:\n{last_error}")


def wait_for_report(timeout_seconds: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if REPORT_PATH.is_file():
            try:
                report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                report = None
            if report is not None:
                if report.get("case_count") == 10:
                    return report
                if report.get("success") is False and report.get("errors"):
                    return report
        time.sleep(0.5)
    raise TimeoutError(f"PIE hybrid-face report did not complete: {REPORT_PATH}")


def main() -> int:
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

    run_remote(execute_file_arguments(STAGE_SCRIPT))
    report = None
    try:
        run_remote(
            [
                "--command",
                "import unreal; s=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); "
                "s.editor_play_simulate() if not s.is_in_play_in_editor() else None",
            ]
        )
        time.sleep(4.0)
        run_remote(execute_file_arguments(PIE_SCRIPT))
        report = wait_for_report()
    finally:
        try:
            run_remote(
                [
                    "--command",
                    "import unreal; s=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); "
                    "s.editor_request_end_play() if s.is_in_play_in_editor() else None",
                ]
            )
            time.sleep(1.0)
        finally:
            run_remote(execute_file_arguments(CLEANUP_SCRIPT))

    if report is None:
        raise RuntimeError("PIE hybrid-face review produced no report")
    if not report.get("success"):
        raise RuntimeError(
            "PIE hybrid-face review failed:\n"
            + "\n".join(str(item) for item in report.get("errors", []))
        )
    print(
        "DM_FACE_HYBRID_PIE_REVIEW="
        + json.dumps(
            {
                "case_count": report["case_count"],
                "report": str(REPORT_PATH),
                "success": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
