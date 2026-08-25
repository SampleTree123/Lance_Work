#!/usr/bin/env python3
"""Build or audit all active first-batch action-expression composites."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(r"D:\UE\Lance_Work")
ENGINE_ROOT = ROOT / "00_engine"
REMOTE_EXEC = ENGINE_ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
BUILD_SCRIPT = (
    ENGINE_ROOT
    / "scripts"
    / "unreal"
    / "ue_build_first_batch_action_expression_composites.py"
)
WINDOWS_PATH = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_window_selection"
    / "frozen_20260821_v4"
    / "frozen_action_windows.json"
)
ACTION_POOL_PATH = (
    ENGINE_ROOT
    / "scripts"
    / "character_creator"
    / "cc_first_batch_action_pool_20260824_v1.json"
)
REPORT_PATH = (
    ENGINE_ROOT
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day3_20260823_v1"
    / "all_action_expression_composites.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    windows = json.loads(WINDOWS_PATH.read_text(encoding="utf-8-sig"))
    pool = json.loads(ACTION_POOL_PATH.read_text(encoding="utf-8-sig"))
    action_ids = [
        action_id
        for sex in ("female", "male")
        for action_id in pool["active_actions"][sex]
    ]
    window_ids = {item["action_id"] for item in windows["actions"]}
    if len(action_ids) != 10 or len(set(action_ids)) != 10:
        raise RuntimeError(f"Expected 10 unique active action IDs, found {len(action_ids)}")
    missing = sorted(set(action_ids) - window_ids)
    if missing:
        raise RuntimeError(f"Active actions missing frozen windows: {missing}")

    script_path = str(BUILD_SCRIPT.resolve())
    command = (
        f"_dm_source=compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'); "
        f"_dm_actions={action_ids!r}; "
        f"_dm_replace={args.replace!r}; "
        "[_dm_run := exec(_dm_source, "
        "{'DM_ACTION_ID': _dm_action, 'DM_REPLACE_OUTPUT': _dm_replace, "
        "'DM_PRINT_REPORT': False}) for _dm_action in _dm_actions]; "
        "print('DM_ALL_COMPOSITES_DONE=' + str(len(_dm_actions)))"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            "datatry_02",
            "--discovery-timeout",
            "30",
            "--command",
            command,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
    )
    if completed.returncode != 0:
        print(completed.stdout, file=sys.stderr)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode
    envelope = json.loads(completed.stdout)
    result = envelope.get("command_result", {})
    if not result.get("success"):
        raise RuntimeError(f"UE composite command failed: {result}")
    outputs = result.get("output", [])
    marker = f"DM_ALL_COMPOSITES_DONE={len(action_ids)}"
    if marker not in [str(line.get("output", "")).strip() for line in outputs]:
        raise RuntimeError(f"Missing UE completion marker: {marker}")
    reports = []
    for action_id in action_ids:
        path = REPORT_PATH.parent / (
            f"action_expression_composites_{action_id.lower()}.json"
        )
        if not path.is_file():
            raise RuntimeError(f"Missing composite report: {path}")
        reports.append(json.loads(path.read_text(encoding="utf-8-sig")))
    observed = [item["action_id"] for item in reports]
    if observed != action_ids:
        raise RuntimeError(
            f"Composite report order/count mismatch: expected={action_ids}, "
            f"observed={observed}"
        )
    aggregate = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed"
        if all(item.get("status") == "passed" for item in reports)
        else "failed",
        "action_count": len(reports),
        "composite_count": sum(len(item["composites"]) for item in reports),
        "action_ids": action_ids,
        "reports": reports,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": aggregate["status"],
                "action_count": aggregate["action_count"],
                "composite_count": aggregate["composite_count"],
                "report": str(REPORT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if aggregate["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
