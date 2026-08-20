#!/usr/bin/env python3
"""Orchestrate the live PIE review for the M02 Elder Morph pilot."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
EDITOR_WORKER = ROOT / "scripts" / "unreal" / "ue_capture_m02_elder_morph_review.py"
PIE_REVIEW = ROOT / "scripts" / "unreal" / "ue_run_m02_elder_morph_pie_review.py"
OUTPUT_DIR = (
    ROOT
    / "outputs"
    / "unreal_character_import"
    / "m02_elder_morph_review_v001"
)
REQUEST_PATH = OUTPUT_DIR / "request.json"
REPORT_PATH = OUTPUT_DIR / "pie_review.json"
PROJECT_NAME = "datatry_02"
MAX_REMOTE_ATTEMPTS = 3


def run_remote(arguments: list[str]) -> None:
    last_error = ""
    for attempt in range(1, MAX_REMOTE_ATTEMPTS + 1):
        completed = subprocess.run(
            [sys.executable, str(REMOTE_EXEC), "--project", PROJECT_NAME, *arguments],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        if completed.returncode == 0:
            try:
                envelope = json.loads(completed.stdout)
            except json.JSONDecodeError:
                envelope = {}
            for line in envelope.get("command_result", {}).get("output", []):
                output = str(line.get("output", "")).strip()
                if output.startswith("DM_ELDER_"):
                    print(output)
            return
        last_error = completed.stdout[-4000:] + completed.stderr[-4000:]
        if attempt < MAX_REMOTE_ATTEMPTS:
            time.sleep(1.5)
    raise RuntimeError(f"Unreal remote command failed:\n{last_error}")


def write_editor_request(operation: str) -> None:
    request = {
        "all_expression_morphs": [],
        "blueprint_path": (
            "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/"
            "BP_DM_M02_ElderMorphPilot_v001"
        ),
        "case": {"id": "pie_stage", "age": 0.0, "expressions": {}},
        "expected_case_count": 1,
        "operation": operation,
        "reset_output": False,
        "validate_age": True,
    }
    REQUEST_PATH.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def wait_for_report(timeout_seconds: float = 45.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if REPORT_PATH.is_file():
            try:
                report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                report = None
            if report is not None and report.get("case_count") == 6:
                return report
        time.sleep(0.5)
    raise TimeoutError(f"PIE review report did not complete: {REPORT_PATH}")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

    write_editor_request("stage")
    run_remote(["--script", str(EDITOR_WORKER)])
    try:
        run_remote(
            [
                "--command",
                "import unreal; s=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); "
                "s.editor_play_simulate() if not s.is_in_play_in_editor() else None",
            ]
        )
        time.sleep(2.5)
        run_remote(["--script", str(PIE_REVIEW)])
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
            write_editor_request("cleanup")
            run_remote(["--script", str(EDITOR_WORKER)])

    if not report.get("success"):
        raise RuntimeError(f"PIE review failed: {report.get('errors')}")
    print(
        "DM_ELDER_PIE_REVIEW="
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
