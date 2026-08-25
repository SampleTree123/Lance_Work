#!/usr/bin/env python3
"""Create UE5-skeleton-compatible derivative FBXs for first-batch motions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[2]
REQUIRED_EXPORTS = (
    SCRIPT_ROOT.parent / "dataset" / "first_batch_required_exports_20260824_v3.json"
)
TOOL_ROOT = REPO_ROOT / "00_engine" / "tools" / "fbx_motion_normalizer"
TOOL_SOURCE = TOOL_ROOT / "fbx_motion_normalizer.cpp"
TOOL_BUILD_SCRIPT = TOOL_ROOT / "build_fbx_motion_normalizer.bat"
TOOL_BINARY = TOOL_ROOT / "bin" / "fbx_motion_normalizer.exe"
OUTPUT_ROOT = (
    REPO_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_motions_20260822_v1"
)
NORMALIZED_ROOT = OUTPUT_ROOT / "normalized_fbx"
MANIFEST_PATH = OUTPUT_ROOT / "normalized_motion_manifest.json"

UE_ROOT = Path(r"D:\UE\UE_5.8")
FBX_ROOT = UE_ROOT / "Engine" / "Source" / "ThirdParty" / "FBX" / "2020.2"
FBX_INCLUDE = FBX_ROOT / "include"
FBX_LIB = FBX_ROOT / "lib" / "vs2017" / "x64" / "release"
FBX_DLL = UE_ROOT / "Engine" / "Binaries" / "Win64" / "libfbxsdk.dll"
VSDEV_CMD = Path(
    r"C:\Program Files\Microsoft Visual Studio\2022\Community"
    r"\Common7\Tools\VsDevCmd.bat"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def build_tool() -> None:
    if TOOL_BINARY.is_file() and TOOL_BINARY.stat().st_mtime >= TOOL_SOURCE.stat().st_mtime:
        return
    required = [
        TOOL_SOURCE,
        TOOL_BUILD_SCRIPT,
        FBX_INCLUDE,
        FBX_LIB,
        FBX_DLL,
        VSDEV_CMD,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing FBX build prerequisites: " + ", ".join(missing))
    TOOL_BINARY.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", str(TOOL_BUILD_SCRIPT)],
        cwd=str(TOOL_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "FBX normalizer build failed:\n"
            + completed.stdout
            + "\n"
            + completed.stderr
        )
    shutil.copy2(FBX_DLL, TOOL_BINARY.parent / FBX_DLL.name)


def parse_tool_output(output: str) -> dict:
    result: dict[str, object] = {"renames": []}
    for raw_line in output.splitlines():
        parts = raw_line.rstrip("\r\n").split("\t")
        if not parts:
            continue
        if parts[0] == "NODE_COUNT" and len(parts) == 2:
            result["node_count"] = int(parts[1])
        elif parts[0] == "RENAMED_COUNT" and len(parts) == 2:
            result["renamed_count"] = int(parts[1])
        elif parts[0] == "REMAINING_PREFIXED" and len(parts) == 2:
            result["remaining_prefixed"] = int(parts[1])
        elif parts[0] == "RENAME" and len(parts) == 3:
            result["renames"].append({"from": parts[1], "to": parts[2]})
    required = {"node_count", "renamed_count", "remaining_prefixed"}
    if not required.issubset(result):
        raise RuntimeError(f"Incomplete FBX normalizer output: {output}")
    return result


def normalize(action: dict) -> dict:
    expected = action["expected_export"]
    source = Path(expected["local_path"])
    if not source.is_file():
        raise FileNotFoundError(str(source))
    source_hash = sha256(source)
    if source.stat().st_size != expected["bytes"] or source_hash != expected["sha256"]:
        raise RuntimeError(f"Frozen source changed: {source}")
    destination = NORMALIZED_ROOT / action["sex"] / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.stem + ".tmp.fbx")
    temporary.unlink(missing_ok=True)
    completed = subprocess.run(
        [str(TOOL_BINARY), str(source), str(temporary)],
        cwd=str(TOOL_BINARY.parent),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"FBX normalization failed for {action['action_id']}:\n"
            + completed.stdout
            + "\n"
            + completed.stderr
        )
    tool_record = parse_tool_output(completed.stdout)
    if tool_record["remaining_prefixed"] != 0 or tool_record["renamed_count"] < 40:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"Unexpected rename coverage for {action['action_id']}: {tool_record}"
        )
    temporary.replace(destination)
    return {
        "action_id": action["action_id"],
        "sex": action["sex"],
        "source_path": str(source),
        "source_bytes": source.stat().st_size,
        "source_sha256": source_hash,
        "normalized_path": str(destination),
        "normalized_bytes": destination.stat().st_size,
        "normalized_sha256": sha256(destination),
        "tool_record": tool_record,
        "success": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action-id", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_tool()
    manifest = read_json(REQUIRED_EXPORTS)
    actions = manifest.get("actions") or []
    by_id = {action["action_id"]: action for action in actions}
    selected_ids = args.action_id or list(by_id)
    unknown = sorted(set(selected_ids) - set(by_id))
    if unknown:
        raise RuntimeError("Unknown action IDs: " + ", ".join(unknown))
    existing = read_json(MANIFEST_PATH) if MANIFEST_PATH.is_file() else {}
    records = {
        record["action_id"]: record
        for record in existing.get("records", [])
        if isinstance(record, dict) and record.get("action_id")
    }
    for action_id in selected_ids:
        records[action_id] = normalize(by_id[action_id])
    ordered = [records[action["action_id"]] for action in actions if action["action_id"] in records]
    report = {
        "schema_version": 1,
        "required_exports_path": str(REQUIRED_EXPORTS),
        "required_exports_sha256": sha256(REQUIRED_EXPORTS),
        "tool_source": str(TOOL_SOURCE),
        "tool_source_sha256": sha256(TOOL_SOURCE),
        "records": ordered,
        "normalized_count": len(ordered),
        "success": len(ordered) == len(actions) and all(row["success"] for row in ordered),
    }
    write_json(MANIFEST_PATH, report)
    print(json.dumps({
        "selected_count": len(selected_ids),
        "selected_success": all(records[action_id]["success"] for action_id in selected_ids),
        "normalized_count": len(ordered),
        "manifest": str(MANIFEST_PATH),
        "all_actions_ready": report["success"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
