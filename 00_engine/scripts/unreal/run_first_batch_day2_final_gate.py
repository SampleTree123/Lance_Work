#!/usr/bin/env python3
"""Build and execute the canonical first-batch Day 2 final gate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ENGINE_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_ROOT = Path(__file__).resolve().parent
REMOTE_EXEC = SCRIPT_ROOT / "ue_remote_exec.py"
BUILD_LIBRARY = SCRIPT_ROOT / "ue_build_first_batch_expression_library.py"
BUILD_COMPOSITION = SCRIPT_ROOT / "ue_build_first_batch_expression_composition.py"
VALIDATE_RUNTIME = SCRIPT_ROOT / "ue_validate_first_batch_day2_runtime.py"
DYNAMIC_RUNNER = SCRIPT_ROOT / "run_first_batch_expression_dynamic_review.py"
OUTPUT_DIR = (
    ENGINE_ROOT
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day2_20260822_v1"
)
FINAL_REPORT = OUTPUT_DIR / "day2_final_gate.json"
EXPRESSION_BUILD_REPORT = OUTPUT_DIR / "canonical_expression_build.json"
COMPOSITION_BUILD_REPORT = OUTPUT_DIR / "canonical_expression_composition.json"


def remote_script(path: Path) -> None:
    source = str(path.resolve())
    command = (
        "DM_FIRST_BATCH_EXPRESSION_TARGET='canonical'; "
        f"exec(compile(open({source!r}, 'r', encoding='utf-8').read(), "
        f"{source!r}, 'exec'), globals())"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            "datatry_02",
            "--command",
            command,
            "--discovery-timeout",
            "30",
        ],
        cwd=str(WORKSPACE_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"UE script failed: {path.name}\n"
            + (completed.stdout or "")[-6000:]
            + (completed.stderr or "")[-6000:]
        )
    print(f"DAY2_STEP_OK={path.name}")


def run_dynamic() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(DYNAMIC_RUNNER),
            "--canonical-first-batch",
        ],
        cwd=str(WORKSPACE_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Canonical dynamic review failed:\n"
            + (completed.stdout or "")[-8000:]
            + (completed.stderr or "")[-8000:]
        )
    print(completed.stdout.strip())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not EXPRESSION_BUILD_REPORT.is_file():
        remote_script(BUILD_LIBRARY)
    else:
        print(f"DAY2_REUSE={EXPRESSION_BUILD_REPORT.name}")
    if not COMPOSITION_BUILD_REPORT.is_file():
        remote_script(BUILD_COMPOSITION)
    else:
        print(f"DAY2_REUSE={COMPOSITION_BUILD_REPORT.name}")
    remote_script(VALIDATE_RUNTIME)
    run_dynamic()

    runtime_path = OUTPUT_DIR / "day2_runtime_gate.json"
    dynamic_path = OUTPUT_DIR / "dynamic_review_v1" / "dynamic_capture_report.json"
    video_path = OUTPUT_DIR / "dynamic_review_v1" / "dynamic_video_manifest.json"
    runtime = read_json(runtime_path)
    dynamic = read_json(dynamic_path)
    videos = read_json(video_path)
    success = (
        runtime.get("automatic_success") is True
        and dynamic.get("automatic_success") is True
        and videos.get("case_count") == 6
    )
    report = {
        "schema_version": 1,
        "gate_id": "first_batch_day2_final_gate_20260822_v1",
        "runtime_gate": str(runtime_path),
        "dynamic_capture": str(dynamic_path),
        "dynamic_videos": str(video_path),
        "counts": runtime["counts"],
        "dynamic_case_count": dynamic["case_count"],
        "automatic_success": success,
        "visual_review": "pending_user_review",
        "production_status": "automatic_gate_passed_visual_review_pending",
    }
    report["success"] = success
    FINAL_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not success:
        raise RuntimeError(f"Day 2 final gate failed: {FINAL_REPORT}")
    print(
        "DM_FIRST_BATCH_DAY2_FINAL="
        + json.dumps(
            {
                "report": str(FINAL_REPORT),
                "looks": runtime["counts"]["looks"],
                "motions": runtime["counts"]["motions"],
                "expressions": runtime["counts"]["expressions"],
                "dynamic_cases": dynamic["case_count"],
                "success": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
