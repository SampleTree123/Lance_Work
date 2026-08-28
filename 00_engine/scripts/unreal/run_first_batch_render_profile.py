#!/usr/bin/env python3
"""Create or audit the first-batch MRQ preset in Unreal Editor."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
BUILD_SCRIPT = ROOT / "scripts" / "unreal" / "ue_build_first_batch_render_profile.py"
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = str(BUILD_SCRIPT.resolve())
    command = (
        f"DM_WORKSPACE_ROOT={str(ROOT.parent.resolve())!r}; "
        f"exec(compile(open({path!r}, 'r', encoding='utf-8').read(), "
        f"{path!r}, 'exec'))"
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
        timeout=300,
    )
    if completed.returncode != 0:
        print(completed.stdout, file=sys.stderr)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode
    envelope = json.loads(completed.stdout)
    outputs = envelope.get("command_result", {}).get("output", [])
    prefix = "DM_RENDER_PROFILE="
    records = [
        json.loads(str(line["output"])[len(prefix) :])
        for line in outputs
        if str(line.get("output", "")).startswith(prefix)
    ]
    if len(records) != 1:
        raise RuntimeError(f"Expected one render-profile report, found {len(records)}")
    report = records[0]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
