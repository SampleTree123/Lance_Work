#!/usr/bin/env python3
"""Build or audit first-batch action-expression composites in Unreal Editor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
BUILD_SCRIPT = (
    ROOT
    / "scripts"
    / "unreal"
    / "ue_build_first_batch_action_expression_composites.py"
)
PROJECT_NAME = "datatry_02"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action-id", default="ACT_F02_CATCH_BREATH")
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = str(BUILD_SCRIPT.resolve())
    command = (
        f"DM_ACTION_ID={args.action_id!r}; "
        f"DM_REPLACE_OUTPUT={args.replace!r}; "
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            PROJECT_NAME,
            "--discovery-timeout",
            "30",
            "--command",
            command,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
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
        if str(line.get("output", "")).startswith(
            "DM_ACTION_EXPRESSION_COMPOSITES="
        )
    ]
    if len(records) != 1:
        raise RuntimeError(f"Expected one composite report, found {len(records)}")
    report = json.loads(records[0].split("=", 1)[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
