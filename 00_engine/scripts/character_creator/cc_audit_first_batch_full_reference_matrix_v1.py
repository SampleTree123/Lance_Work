"""Merge the frozen 16-Look audit with a missing-16 CC export run."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_DIR.parents[1]
ARTIFACT_ROOT = ENGINE_ROOT / "outputs" / "character_creator_bridge" / "artifacts"
DEFAULT_CONFIG = SCRIPT_DIR / "cc_first_batch_full_reference_looks_20260822_v3.json"
DEFAULT_LEGACY_AUDIT = (
    ARTIFACT_ROOT
    / "first_batch_full_reference_assembly"
    / "final_audit_20260820_v1.json"
)
DEFAULT_EXPANSION_RUN = (
    ARTIFACT_ROOT
    / "first_batch_full_reference_expansion"
    / "run_20260822_missing16_v1"
)
DEFAULT_OUTPUT = (
    ARTIFACT_ROOT
    / "first_batch_full_reference_expansion"
    / "final_audit_20260822_v1.json"
)


class MatrixAuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MatrixAuditError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MatrixAuditError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    require(isinstance(record, dict), f"{label} record is missing")
    path = Path(str(record.get("path") or record.get("local_path") or "")).resolve()
    require(path.is_file(), f"{label} file is missing: {path}")
    actual = {
        "bytes": path.stat().st_size,
        "path": str(path),
        "sha256": sha256_file(path),
    }
    require(actual["bytes"] == int(record.get("bytes", -1)), f"{label} size drifted")
    require(actual["sha256"] == record.get("sha256"), f"{label} hash drifted")
    return actual


def verify_directory_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    require(isinstance(record, dict), f"{label} record is missing")
    path = Path(str(record.get("path") or "")).resolve()
    require(path.is_dir(), f"{label} directory is missing: {path}")
    files = [item for item in path.rglob("*") if item.is_file()]
    actual_count = len(files)
    actual_bytes = sum(item.stat().st_size for item in files)
    require(actual_count == int(record.get("file_count", -1)), f"{label} count drifted")
    require(actual_bytes == int(record.get("total_bytes", -1)), f"{label} bytes drifted")
    return {"path": str(path), "file_count": actual_count, "total_bytes": actual_bytes}


def verify_optional_directory_record(
    record: dict[str, Any], label: str
) -> dict[str, Any]:
    """Verify an optional export directory without requiring an empty path to exist."""
    require(isinstance(record, dict), f"{label} record is missing")
    if record.get("present", True):
        return verify_directory_record(record, label)

    expected_count = int(record.get("file_count", -1))
    expected_bytes = int(record.get("total_bytes", -1))
    require(expected_count == 0, f"{label} absent record has nonzero count")
    require(expected_bytes == 0, f"{label} absent record has nonzero bytes")

    path = Path(str(record.get("path") or "")).resolve()
    if path.exists():
        require(path.is_dir(), f"{label} optional path is not a directory: {path}")
        files = [item for item in path.rglob("*") if item.is_file()]
        require(not files, f"{label} is marked absent but contains files")
    return {"path": str(path), "file_count": 0, "total_bytes": 0}


def normalized_results(validation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = validation.get("results") or []
    if isinstance(rows, dict):
        rows = [rows]
    require(isinstance(rows, list), "Expansion validation results must be an array")
    return rows


def build_new_row(
    preset: dict[str, Any], result_summary: dict[str, Any], run_name: str
) -> dict[str, Any]:
    look_id = preset["look_id"]
    require(result_summary.get("look_id") == look_id, f"Result Look differs: {look_id}")
    require(result_summary.get("success") is True, f"Expansion Look failed: {look_id}")
    case_path = Path(str(result_summary.get("result_path") or "")).resolve()
    case = read_json(case_path)
    require(case.get("success") is True, f"Case result failed: {look_id}")
    require(case.get("look_id") == look_id, f"Case Look differs: {look_id}")

    project = verify_file_record(case.get("production_project") or {}, f"{look_id} project")
    export = case.get("production_export") or {}
    fbx = verify_file_record(export.get("fbx") or {}, f"{look_id} FBX")
    material_json = verify_file_record(export.get("json") or {}, f"{look_id} JSON")
    fbm = verify_directory_record(export.get("fbm") or {}, f"{look_id} FBM")
    textures_record = export.get("textures")
    if textures_record:
        textures = verify_optional_directory_record(
            textures_record, f"{look_id} textures"
        )
        texture_count = textures["file_count"]
        texture_bytes = textures["total_bytes"]
    else:
        texture_count = 0
        texture_bytes = 0

    return {
        "look_id": look_id,
        "sex": preset["sex"],
        "identity_id": preset["first_batch_identity_id"],
        "outfit_id": preset["first_batch_outfit_id"],
        "selected_assets": [
            item.get("display_name") or item.get("asset_id")
            for item in preset.get("selected_assets") or []
        ],
        "outfit_asset_override_id": preset.get("outfit_asset_override_id"),
        "source_run": run_name,
        "case_result_path": str(case_path),
        "case_success": True,
        "project": project,
        "fbx": fbx,
        "json": material_json,
        "fbm_file_count": fbm["file_count"],
        "fbm_total_bytes": fbm["total_bytes"],
        "auxiliary_texture_reference_count": texture_count,
        "auxiliary_texture_file_count": texture_count,
        "auxiliary_texture_total_bytes": texture_bytes,
        "passed": True,
    }


def build_audit(
    config_path: Path, legacy_audit_path: Path, expansion_run: Path
) -> dict[str, Any]:
    config = read_json(config_path)
    legacy = read_json(legacy_audit_path)
    validation_path = expansion_run / "validation_result.json"
    validation = read_json(validation_path)

    presets = {item["look_id"]: item for item in config.get("presets") or []}
    require(len(presets) == 32, "Complete config must contain 32 unique Looks")
    legacy_rows = {item["look_id"]: item for item in legacy.get("rows") or []}
    require(legacy.get("status") == "passed", "Legacy audit did not pass")
    require(len(legacy_rows) == 16, "Legacy audit must contain 16 Looks")

    require(validation.get("success") is True, "Expansion Bridge run did not pass")
    require(int(validation.get("requested_count", -1)) == 16, "Expansion must request 16")
    require(int(validation.get("success_count", -1)) == 16, "Expansion must pass 16")
    require(int(validation.get("failure_count", -1)) == 0, "Expansion has failures")
    result_rows = {item["look_id"]: item for item in normalized_results(validation)}
    require(len(result_rows) == 16, "Expansion result must contain 16 unique Looks")
    require(not (set(legacy_rows) & set(result_rows)), "Legacy and expansion IDs overlap")
    require(set(presets) == set(legacy_rows) | set(result_rows), "32-Look coverage differs")

    rows = []
    for look_id in sorted(presets):
        if look_id in legacy_rows:
            row = legacy_rows[look_id]
            require(row.get("passed") is True, f"Legacy Look failed: {look_id}")
            verify_file_record(row.get("project") or {}, f"{look_id} project")
            legacy_fbx = verify_file_record(row.get("fbx") or {}, f"{look_id} FBX")
            verify_file_record(row.get("json") or {}, f"{look_id} JSON")
            verify_directory_record(
                {
                    "path": str(Path(legacy_fbx["path"]).with_suffix(".fbm")),
                    "file_count": row.get("fbm_file_count"),
                    "total_bytes": row.get("fbm_total_bytes"),
                },
                f"{look_id} FBM",
            )
            rows.append(row)
        else:
            rows.append(
                build_new_row(presets[look_id], result_rows[look_id], expansion_run.name)
            )

    export_root = Path(config["presets"][0]["production_output"]["export_root"]).parents[1]
    partial_directories = [
        item for item in export_root.rglob("*") if item.is_dir() and ".partial" in item.name
    ]
    require(not partial_directories, "Partial export directories remain")
    return {
        "schema_version": 1,
        "audit_id": "first_batch_full_reference_matrix_audit_20260822_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "passed",
        "config": {
            "path": str(config_path.resolve()),
            "sha256": sha256_file(config_path),
            "library_id": config.get("library_id"),
        },
        "legacy_audit": {
            "path": str(legacy_audit_path.resolve()),
            "sha256": sha256_file(legacy_audit_path),
        },
        "expansion_validation": {
            "path": str(validation_path.resolve()),
            "sha256": sha256_file(validation_path),
        },
        "export_root": str(export_root.resolve()),
        "validation_policy": {
            "project_required": True,
            "fbx_required": True,
            "json_required": True,
            "fbm_required": True,
            "existing_exports_must_not_drift": True,
        },
        "summary": {
            "expected_look_count": 32,
            "observed_look_count": len(rows),
            "project_count": len(rows),
            "passed_count": sum(item.get("passed") is True for item in rows),
            "failed_count": sum(item.get("passed") is not True for item in rows),
            "partial_directory_count": len(partial_directories),
            "legacy_look_count": 16,
            "expansion_look_count": 16,
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--legacy-audit", type=Path, default=DEFAULT_LEGACY_AUDIT)
    parser.add_argument("--expansion-run", type=Path, default=DEFAULT_EXPANSION_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build_audit(args.config, args.legacy_audit, args.expansion_run)
    write_json(args.output, audit)
    print(
        json.dumps(
            {
                "success": True,
                "status": audit["status"],
                "summary": audit["summary"],
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
