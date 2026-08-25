#!/usr/bin/env python3
"""Prepare or open a first-batch action-matrix staging level."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
STAGE_SCRIPT = (
    ROOT / "scripts" / "unreal" / "ue_prepare_first_batch_action_matrix_stage.py"
)
BASE_MAP = "/Game/DataMake/Scenes/TokyoStylized/L_DM_TokyoStylized"
MALE_MAP = (
    "/Game/DataMake/Scenes/TokyoStylized/"
    "L_DM_TokyoStylized_MalePilot_v001"
)


def run_remote(command: str, timeout: int = 180) -> dict:
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
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout + "\n" + completed.stderr)
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("base", "male"))
    args = parser.parse_args()
    if args.mode == "male":
        # UE 5.8 can retain the duplicated UWorld until the Python execution
        # frame exits. Loading that map in the same invocation then triggers
        # the editor's World Memory Leaks fatal check, so duplication is an
        # intentionally separate Remote Execution transaction.
        ensure_command = (
            "import unreal, json; "
            f"source={BASE_MAP!r}; target={MALE_MAP!r}; "
            "created=False; "
            "exists=unreal.EditorAssetLibrary.does_asset_exist(target); "
            "asset=None if exists else unreal.EditorAssetLibrary.duplicate_asset(source,target); "
            "created=not exists; "
            "ok=exists or asset is not None; "
            "saved=unreal.EditorAssetLibrary.save_asset(target, only_if_is_dirty=False) if ok else False; "
            "asset=None; unreal.SystemLibrary.collect_garbage(); "
            "print('DM_STAGE_MAP_ENSURED=' + json.dumps({'created':created,'exists':ok,'saved':saved,'map':target}))"
        )
        ensured = run_remote(ensure_command, 240)
        records = [
            str(item.get("output", ""))
            for item in ensured.get("command_result", {}).get("output", [])
            if str(item.get("output", "")).startswith("DM_STAGE_MAP_ENSURED=")
        ]
        if len(records) != 1:
            raise RuntimeError(f"Expected one map-ensure report, found {len(records)}")
        ensure_report = json.loads(records[0].split("=", 1)[1])
        if not ensure_report["exists"] or not ensure_report["saved"]:
            raise RuntimeError(f"Unable to create/save male staging map: {ensure_report}")

    script_path = str(STAGE_SCRIPT.resolve())
    command = (
        f"DM_STAGE_MODE={args.mode!r}; "
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    envelope = run_remote(command)
    records = [
        str(item.get("output", ""))
        for item in envelope.get("command_result", {}).get("output", [])
        if str(item.get("output", "")).startswith("DM_ACTION_MATRIX_STAGE=")
    ]
    if len(records) != 1:
        raise RuntimeError(f"Expected one staging report, found {len(records)}")
    report = json.loads(records[0].split("=", 1)[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
