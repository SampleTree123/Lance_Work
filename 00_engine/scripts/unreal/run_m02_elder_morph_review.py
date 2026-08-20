#!/usr/bin/env python3
"""Run the M02 Elder Morph visual review against an open Unreal Editor."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
WORKER = ROOT / "scripts" / "unreal" / "ue_capture_m02_elder_morph_review.py"
OUTPUT_DIR = (
    ROOT
    / "outputs"
    / "unreal_character_import"
    / "m02_elder_morph_review_v001"
)
REQUEST_PATH = OUTPUT_DIR / "request.json"
REPORT_PATH = OUTPUT_DIR / "review.json"
PROJECT_NAME = "datatry_02"
EDITOR_TICK_WAIT_SECONDS = 1.0
MAX_CASE_ATTEMPTS = 3

CASES = [
    {"id": "age_000_neutral", "age": 0.0, "expressions": {}},
    {"id": "age_050_neutral", "age": 0.5, "expressions": {}},
    {"id": "age_100_neutral", "age": 1.0, "expressions": {}},
    {
        "id": "age_100_blink",
        "age": 1.0,
        "expressions": {
            "CTRL_expressions_eyeBlinkL": 1.0,
            "CTRL_expressions_eyeBlinkR": 1.0,
        },
    },
    {
        "id": "age_100_smile",
        "age": 1.0,
        "expressions": {
            "CTRL_expressions_mouthCornerPullL": 0.6,
            "CTRL_expressions_mouthCornerPullR": 0.6,
        },
    },
    {
        "id": "age_100_jaw_open",
        "age": 1.0,
        "expressions": {"CTRL_expressions_jawOpen": 0.65},
    },
]
ALL_EXPRESSION_MORPHS = sorted(
    {
        morph_name
        for case in CASES
        for morph_name in case["expressions"]
    }
)


def write_request(operation: str, case: dict, reset_output: bool = False) -> None:
    request = {
        "all_expression_morphs": ALL_EXPRESSION_MORPHS,
        "case": case,
        "expected_case_count": len(CASES),
        "operation": operation,
        "reset_output": reset_output,
    }
    REQUEST_PATH.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_worker() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            PROJECT_NAME,
            "--script",
            str(WORKER),
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if completed.returncode:
        raise RuntimeError(
            "Unreal review worker failed:\n"
            + completed.stdout[-4000:]
            + completed.stderr[-4000:]
        )
    envelope = json.loads(completed.stdout)
    for line in envelope.get("command_result", {}).get("output", []):
        output = str(line.get("output", "")).strip()
        if output.startswith("DM_ELDER_MORPH_"):
            print(output)


def cleanup() -> None:
    write_request("cleanup", CASES[0])
    try:
        run_worker()
    except Exception as exc:
        print(f"Cleanup warning: {exc}", file=sys.stderr)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        for index, case in enumerate(CASES):
            for attempt in range(1, MAX_CASE_ATTEMPTS + 1):
                try:
                    write_request("stage", case, reset_output=index == 0)
                    run_worker()
                    time.sleep(EDITOR_TICK_WAIT_SECONDS)
                    write_request("capture", case)
                    run_worker()
                    time.sleep(0.2)
                    break
                except Exception:
                    cleanup()
                    if attempt == MAX_CASE_ATTEMPTS:
                        raise
                    print(
                        f"Retrying {case['id']} after remote response failure "
                        f"({attempt}/{MAX_CASE_ATTEMPTS})",
                        file=sys.stderr,
                    )
                    time.sleep(1.5)
    finally:
        cleanup()

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    if not report.get("success"):
        raise RuntimeError(f"Elder Morph review did not pass: {REPORT_PATH}")
    print(
        "DM_ELDER_MORPH_REVIEW="
        + json.dumps(
            {
                "case_count": len(report["cases"]),
                "output_dir": str(OUTPUT_DIR),
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
