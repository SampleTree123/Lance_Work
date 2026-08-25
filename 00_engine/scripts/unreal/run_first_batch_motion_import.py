#!/usr/bin/env python3
"""Run the frozen first-batch Motion FBX import gate in the active UE project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


SCRIPT_ROOT = Path(__file__).resolve().parent
REMOTE_EXEC = SCRIPT_ROOT / "ue_remote_exec.py"
UE_PAYLOAD = SCRIPT_ROOT / "ue_import_first_batch_motions.py"
PREPARE_NORMALIZED = SCRIPT_ROOT / "prepare_first_batch_motion_fbxs.py"
REQUIRED_EXPORTS = (
    SCRIPT_ROOT.parent
    / "dataset"
    / "first_batch_required_exports_20260824_v3.json"
)


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def remote_command(mode: str, action_ids: list[str]) -> str:
    script_path = str(UE_PAYLOAD.resolve())
    assignments = [f"DM_FIRST_BATCH_MOTION_MODE={mode!r}"]
    if action_ids:
        assignments.append(f"DM_FIRST_BATCH_MOTION_IDS={action_ids!r}")
    assignments.append(
        "exec(compile(open(r%r, 'r', encoding='utf-8').read(), "
        "r%r, 'exec'), globals())" % (script_path, script_path)
    )
    return "; ".join(assignments)


def run_remote(project: str, mode: str, action_ids: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            project,
            "--command",
            remote_command(mode, action_ids),
            "--discovery-timeout",
            "60",
        ],
        cwd=str(SCRIPT_ROOT.parents[2]),
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="datatry_02")
    parser.add_argument("--action-id", action="append", default=[])
    parser.add_argument("--skip-preflight", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = read_json(REQUIRED_EXPORTS)
    available = [row["action_id"] for row in manifest.get("actions") or []]
    selected = args.action_id or available
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise RuntimeError("Unknown action IDs: " + ", ".join(unknown))

    prepare_command = [sys.executable, str(PREPARE_NORMALIZED)]
    for action_id in selected:
        prepare_command.extend(["--action-id", action_id])
    prepared = subprocess.run(
        prepare_command,
        cwd=str(SCRIPT_ROOT.parents[2]),
        check=False,
    )
    if prepared.returncode != 0:
        return prepared.returncode

    if not args.skip_preflight:
        preflight = run_remote(args.project, "preflight", selected)
        if preflight.returncode != 0:
            return preflight.returncode
    imported = run_remote(args.project, "import", selected)
    return imported.returncode


if __name__ == "__main__":
    raise SystemExit(main())
