"""Build the frozen CC-to-UE export manifest for the first data batch."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
CC_SCRIPT_ROOT = ENGINE_ROOT / "scripts" / "character_creator"
ARTIFACT_ROOT = ENGINE_ROOT / "outputs" / "character_creator_bridge" / "artifacts"

DEFAULT_LOOK_CONFIG = CC_SCRIPT_ROOT / "cc_first_batch_full_reference_looks_20260822_v3.json"
DEFAULT_LOOK_AUDIT = (
    ARTIFACT_ROOT
    / "first_batch_full_reference_expansion"
    / "final_audit_20260822_v1.json"
)
DEFAULT_ACTION_REGISTRY = CC_SCRIPT_ROOT / "cc_first_batch_action_registry_20260821_v4.json"
DEFAULT_ACTION_POOL = CC_SCRIPT_ROOT / "cc_first_batch_action_pool_20260824_v1.json"
DEFAULT_ACTION_WINDOWS = (
    ARTIFACT_ROOT
    / "first_batch_action_window_selection"
    / "frozen_20260821_v4"
    / "frozen_action_windows.json"
)
DEFAULT_EXPRESSION_PROFILE = (
    ENGINE_ROOT / "scripts" / "unreal" / "first_batch_expression_profile_20260820_v1.json"
)
DEFAULT_OUTPUT = SCRIPT_ROOT / "first_batch_required_exports_20260824_v3.json"
DEFAULT_MOTION_EXPORT_ROOT = Path(
    r"D:\UE\exports\character_creator\first_data_batch_20260820_v1\motions"
)

EXPECTED_LOOKS = 32
EXPECTED_ACTIONS = 10
EXPECTED_ACTIONS_PER_SEX = 5
EXPECTED_EXPRESSIONS = ("happy", "angry", "sad")
ACCEPTED_ACTION_REGISTRY_STATUSES = {
    "frozen_pending_cc_and_ue_validation",
    "frozen_pending_replacement_window_and_ue_validation",
}


class RequiredExportsError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RequiredExportsError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RequiredExportsError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected JSON object: {path}")
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


def locked_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    require(resolved.is_file(), f"Required file is missing: {resolved}")
    return {
        "local_path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def verify_locked_file(record: dict[str, Any], label: str) -> dict[str, Any]:
    require(isinstance(record, dict), f"{label} lock is missing")
    path = Path(str(record.get("path") or record.get("local_path") or ""))
    actual = locked_file(path)
    expected_bytes = record.get("bytes", record.get("size_bytes"))
    require(expected_bytes is not None, f"{label} byte lock is missing")
    require(actual["bytes"] == int(expected_bytes), f"{label} size drifted")
    require(record.get("sha256") == actual["sha256"], f"{label} hash drifted")
    return actual


def source_ref(*parts: str) -> str:
    clean = [part.strip("/\\") for part in parts]
    return "bundle://first_data_batch_20260820_v1/" + "/".join(clean)


def validate_fbm(fbx_path: Path, row: dict[str, Any], label: str) -> dict[str, Any]:
    fbm_root = fbx_path.with_suffix(".fbm")
    require(fbm_root.is_dir(), f"{label} FBM directory is missing: {fbm_root}")
    files = [path for path in fbm_root.rglob("*") if path.is_file()]
    expected_count = int(row.get("fbm_file_count", -1))
    expected_bytes = int(row.get("fbm_total_bytes", -1))
    actual_bytes = sum(path.stat().st_size for path in files)
    require(len(files) == expected_count, f"{label} FBM file count drifted")
    require(actual_bytes == expected_bytes, f"{label} FBM byte count drifted")
    return {
        "local_path": str(fbm_root.resolve()),
        "source_ref": source_ref("full_reference", label, fbm_root.name),
        "file_count": len(files),
        "bytes": actual_bytes,
    }


def build_looks(
    look_config: dict[str, Any],
    look_audit: dict[str, Any],
    expected_looks: int = EXPECTED_LOOKS,
) -> list[dict[str, Any]]:
    require(look_audit.get("status") == "passed", "FullReference audit did not pass")
    summary = look_audit.get("summary") or {}
    require(
        int(summary.get("expected_look_count", -1)) == expected_looks,
        f"Expected {expected_looks} looks",
    )
    require(
        int(summary.get("passed_count", -1)) == expected_looks,
        "Not all looks passed",
    )
    require(int(summary.get("failed_count", -1)) == 0, "FullReference audit has failures")

    configured = {row["look_id"]: row for row in look_config.get("look_rows") or []}
    audited = {row["look_id"]: row for row in look_audit.get("rows") or []}
    require(
        len(configured) == expected_looks,
        f"Look config must contain {expected_looks} unique looks",
    )
    require(set(configured) == set(audited), "Look config/audit IDs differ")

    result = []
    for look_id in sorted(configured):
        config_row = configured[look_id]
        audit_row = audited[look_id]
        require(audit_row.get("passed") is True, f"Look did not pass: {look_id}")
        project = verify_locked_file(audit_row.get("project") or {}, f"{look_id} project")
        fbx = verify_locked_file(audit_row.get("fbx") or {}, f"{look_id} FBX")
        material_json = verify_locked_file(audit_row.get("json") or {}, f"{look_id} JSON")
        fbx_path = Path(fbx["local_path"])
        project["source_ref"] = source_ref("projects", Path(project["local_path"]).name)
        fbx["source_ref"] = source_ref("full_reference", look_id, fbx_path.name)
        material_json["source_ref"] = source_ref(
            "full_reference", look_id, Path(material_json["local_path"]).name
        )
        result.append(
            {
                "look_id": look_id,
                "sex": config_row["sex"],
                "bodyfit_id": config_row["bodyfit_id"],
                "identity_id": config_row["identity_id"],
                "outfit_id": config_row["outfit_id"],
                "source_validated_look_id": config_row["source_validated_look_id"],
                "outfit_asset_override_id": config_row.get("outfit_asset_override_id"),
                "cc_project": project,
                "fbx": fbx,
                "auto_setup_json": material_json,
                "fbm": validate_fbm(fbx_path, audit_row, look_id),
                "cc_export_status": "validated",
                "unreal_import_status": "pending",
                "expected_unreal_folder": (
                    f"/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/{look_id}"
                ),
            }
        )
    return result


def export_basename(action_id: str) -> str:
    value = "A_" + action_id.removeprefix("ACT_")
    require(value.replace("_", "").isalnum(), f"Unsafe action ID: {action_id}")
    return value


def build_actions(
    registry: dict[str, Any],
    windows: dict[str, Any],
    action_pool: dict[str, Any],
    motion_export_root: Path,
) -> list[dict[str, Any]]:
    registry_status = registry.get("status")
    require(
        registry_status in ACCEPTED_ACTION_REGISTRY_STATUSES,
        "Action registry is not frozen",
    )
    require(
        windows.get("status") == "frozen_ready_for_cc_export",
        "Action windows are not frozen for CC export",
    )
    require(
        action_pool.get("status") == "frozen_for_first_batch_local_and_server_render",
        "Action pool is not frozen for production",
    )
    active_sets = action_pool.get("active_actions")
    require(isinstance(active_sets, dict), "Action pool active_actions is missing")
    active_ids: list[str] = []
    for sex in ("female", "male"):
        sex_ids = active_sets.get(sex)
        require(
            isinstance(sex_ids, list) and len(sex_ids) == EXPECTED_ACTIONS_PER_SEX,
            f"Expected {EXPECTED_ACTIONS_PER_SEX} active {sex} actions",
        )
        require(len(set(sex_ids)) == len(sex_ids), f"Duplicate active {sex} actions")
        active_ids.extend(sex_ids)
    require(len(set(active_ids)) == EXPECTED_ACTIONS, "Active action IDs must be unique")

    registry_source = {row["action_id"]: row for row in registry.get("actions") or []}
    window_source = {row["action_id"]: row for row in windows.get("actions") or []}
    require(set(active_ids) <= set(registry_source), "Active action is missing from registry")
    require(set(active_ids) <= set(window_source), "Active action is missing from windows")
    registry_rows = {action_id: registry_source[action_id] for action_id in active_ids}
    window_rows = {action_id: window_source[action_id] for action_id in active_ids}
    counts = {
        sex: sum(row.get("sex") == sex for row in registry_rows.values())
        for sex in ("female", "male")
    }
    require(
        counts == {"female": EXPECTED_ACTIONS_PER_SEX, "male": EXPECTED_ACTIONS_PER_SEX},
        f"Expected five actions per sex, got {counts}",
    )

    root_policy = action_pool.get("root_motion_policy") or {}
    default_root_policy = root_policy.get("default")
    overrides = root_policy.get("overrides") or {}
    require(
        default_root_policy == "preserve_source_root_motion",
        "Unexpected default root-motion policy",
    )
    require(set(overrides) == {"ACT_F02_CATCH_BREATH"}, "Only Catch Breath may override root motion")

    result = []
    for action_id in sorted(registry_rows):
        registry_row = registry_rows[action_id]
        window_row = window_rows[action_id]
        source = verify_locked_file(registry_row.get("runtime_file") or {}, action_id)
        window_source = verify_locked_file(window_row.get("source_motion") or {}, action_id)
        require(source["sha256"] == window_source["sha256"], f"Window source differs: {action_id}")
        sex = registry_row["sex"]
        basename = export_basename(action_id)
        expected_path = (motion_export_root / sex / f"{basename}.fbx").resolve()
        export_record = registry_row.get("export_fbx")
        if export_record:
            exported = verify_locked_file(export_record, f"{action_id} export FBX")
            require(
                Path(exported["local_path"]).resolve() == expected_path,
                f"Export FBX path differs from canonical path: {action_id}",
            )
            export_status = "validated"
        else:
            require(
                registry_status != "frozen_pending_replacement_window_and_ue_validation",
                f"Frozen v4 registry is missing export FBX lock: {action_id}",
            )
            exported = None
            export_status = "pending"
        source["source_ref"] = source_ref("motion_sources", sex, Path(source["local_path"]).name)
        expected_export = {
            "basename": basename,
            "local_path": str(expected_path),
            "source_ref": source_ref("motions", sex, expected_path.name),
        }
        if exported:
            expected_export.update(
                {
                    "bytes": exported["bytes"],
                    "sha256": exported["sha256"],
                }
            )
        result.append(
            {
                "action_id": action_id,
                "sex": sex,
                "actor_id": registry_row["actor_id"],
                "semantic_family": registry_row["semantic_family"],
                "source_motion": source,
                "window": window_row["window"],
                "expected_export": expected_export,
                "root_motion_policy": (
                    overrides.get(action_id, {}).get("policy", default_root_policy)
                ),
                "root_motion_override_asset": overrides.get(action_id, {}).get("ue_asset"),
                "face_policy": "replaceable",
                "cc_export_status": export_status,
                "unreal_import_status": "pending",
            }
        )
    return result


def build_expressions(profile_path: Path, profile: dict[str, Any]) -> list[dict[str, Any]]:
    require(profile.get("status") == "frozen_for_ue_pilot", "Expression profile is not frozen")
    rows = {row["expression_id"]: row for row in profile.get("expressions") or []}
    require(tuple(sorted(rows)) == tuple(sorted(EXPECTED_EXPRESSIONS)), "Expression roles differ")
    profile_lock = locked_file(profile_path)
    return [
        {
            "expression_id": expression_id,
            "profile_id": profile["profile_id"],
            "profile_sha256": profile_lock["sha256"],
            "duration_seconds": profile["duration_seconds"],
            "asset_suffix": rows[expression_id]["asset_suffix"],
            "unreal_assets": {
                actor["actor_id"]: (
                    f"{actor['target_folder']}/A_DM_{actor['actor_id']}_"
                    f"{rows[expression_id]['asset_suffix']}"
                )
                for actor in profile.get("actors") or []
            },
            "machine_validation_status": "passed",
            "visual_review_status": "pending",
        }
        for expression_id in EXPECTED_EXPRESSIONS
    ]


def build_required_exports(
    look_config_path: Path,
    look_audit_path: Path,
    action_registry_path: Path,
    action_pool_path: Path,
    action_windows_path: Path,
    expression_profile_path: Path,
    output_path: Path,
    motion_export_root: Path,
    expected_looks: int = EXPECTED_LOOKS,
) -> dict[str, Any]:
    look_config = read_json(look_config_path)
    look_audit = read_json(look_audit_path)
    action_registry = read_json(action_registry_path)
    action_pool = read_json(action_pool_path)
    action_windows = read_json(action_windows_path)
    expression_profile = read_json(expression_profile_path)

    looks = build_looks(look_config, look_audit, expected_looks=expected_looks)
    actions = build_actions(
        action_registry,
        action_windows,
        action_pool,
        motion_export_root,
    )
    expressions = build_expressions(expression_profile_path, expression_profile)
    actions_exported = all(row["cc_export_status"] == "validated" for row in actions)
    manifest = {
        "schema_version": "required_exports_v1",
        "batch_id": "first_data_batch_20260820_v1",
        "generated_at": now(),
        "status": (
            "frozen_sources_ready_for_unreal_import"
            if actions_exported
            else "frozen_sources_pending_motion_export_and_unreal_validation"
        ),
        "production_status": "not_approved",
        "counts": {
            "full_reference_looks": len(looks),
            "action_assets": len(actions),
            "female_actions": sum(row["sex"] == "female" for row in actions),
            "male_actions": sum(row["sex"] == "male" for row in actions),
            "expression_assets": len(expressions),
        },
        "provenance": {
            "look_config": locked_file(look_config_path),
            "look_audit": locked_file(look_audit_path),
            "action_registry": locked_file(action_registry_path),
            "action_pool": locked_file(action_pool_path),
            "action_windows": locked_file(action_windows_path),
            "expression_profile": locked_file(expression_profile_path),
        },
        "full_reference_looks": looks,
        "actions": actions,
        "expressions": expressions,
        "expression_policy": action_pool["expression_policy"],
        "pending_runtime_bindings": [
            "scene_id",
            "anchor_id",
            "lighting_id",
            "camera_medium_id",
            "camera_full_body_id",
            "sequence_asset",
            "render_profile_id",
        ],
    }
    require(manifest["counts"] == {
        "full_reference_looks": expected_looks,
        "action_assets": 10,
        "female_actions": 5,
        "male_actions": 5,
        "expression_assets": 3,
    }, "Required export cardinality contract failed")
    write_json(output_path, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--look-config", type=Path, default=DEFAULT_LOOK_CONFIG)
    parser.add_argument("--look-audit", type=Path, default=DEFAULT_LOOK_AUDIT)
    parser.add_argument("--action-registry", type=Path, default=DEFAULT_ACTION_REGISTRY)
    parser.add_argument("--action-pool", type=Path, default=DEFAULT_ACTION_POOL)
    parser.add_argument("--action-windows", type=Path, default=DEFAULT_ACTION_WINDOWS)
    parser.add_argument("--expression-profile", type=Path, default=DEFAULT_EXPRESSION_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--motion-export-root", type=Path, default=DEFAULT_MOTION_EXPORT_ROOT)
    parser.add_argument("--expected-looks", type=int, default=EXPECTED_LOOKS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_required_exports(
        args.look_config,
        args.look_audit,
        args.action_registry,
        args.action_pool,
        args.action_windows,
        args.expression_profile,
        args.output,
        args.motion_export_root,
        expected_looks=args.expected_looks,
    )
    print(json.dumps({
        "output": str(args.output.resolve()),
        "status": manifest["status"],
        "counts": manifest["counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
