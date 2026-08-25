#!/usr/bin/env python3
"""Build the first-batch 20-second sequence through Unreal Remote Execution."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
BUILD_SCRIPT = ROOT / "scripts" / "unreal" / "ue_build_first_batch_20s_sequence.py"
DEFAULT_PROJECT_NAME = os.environ.get("DM_UE_PROJECT_NAME", "datatry_02")
DEFAULT_ENGINE_ROOT = (
    Path(os.environ["DM_UE_ENGINE_ROOT"])
    if os.environ.get("DM_UE_ENGINE_ROOT")
    else None
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", default=DEFAULT_PROJECT_NAME)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_ENGINE_ROOT)
    parser.add_argument("--action-id", default="ACT_F02_CATCH_BREATH")
    parser.add_argument(
        "--source-sequence", default="/Game/DataMake/Sequences/firstweek"
    )
    parser.add_argument(
        "--output-sequence",
        default=(
            "/Game/DataMake/Sequences/FirstBatch/"
            "LS_DM_FirstBatch_F02_20s_Pilot_v001"
        ),
    )
    parser.add_argument(
        "--target-actor",
        default="CC_FB_F_ID02_O04_Blueprint_LiveLink_C_1",
    )
    parser.add_argument(
        "--expression",
        choices=("happy", "angry", "sad"),
        help="Use one expression for all four camera segments.",
    )
    parser.add_argument("--no-open", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    segment_expressions = (
        [args.expression] * 4
        if args.expression
        else ["happy", "angry", "sad", "happy"]
    )
    script_path = str(BUILD_SCRIPT.resolve())
    command = (
        f"DM_ACTION_ID={args.action_id!r}; "
        f"DM_SOURCE_SEQUENCE={args.source_sequence!r}; "
        f"DM_OUTPUT_SEQUENCE={args.output_sequence!r}; "
        f"DM_TARGET_ACTOR_NAME={args.target_actor!r}; "
        f"DM_SEGMENT_EXPRESSIONS={segment_expressions!r}; "
        f"DM_REPLACE_OUTPUT=True; DM_OPEN_OUTPUT={not args.no_open!r}; "
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    remote_command = [
        sys.executable,
        str(REMOTE_EXEC),
        "--project",
        args.project_name,
        "--discovery-timeout",
        "30",
        "--command",
        command,
    ]
    if args.engine_root is not None:
        remote_command.extend(["--engine-root", str(args.engine_root.resolve())])
    completed = subprocess.run(
        remote_command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if completed.returncode != 0:
        print(completed.stdout, file=sys.stderr)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode
    envelope = json.loads(completed.stdout)
    outputs = envelope.get("command_result", {}).get("output", [])
    records = [
        line["output"]
        for line in outputs
        if str(line.get("output", "")).startswith("DM_FIRST_BATCH_20S_SEQUENCE=")
    ]
    if len(records) != 1:
        raise RuntimeError(f"Expected one sequence report, found {len(records)}")
    report = json.loads(records[0].split("=", 1)[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
