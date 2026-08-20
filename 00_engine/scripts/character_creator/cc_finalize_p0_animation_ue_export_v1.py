#!/usr/bin/env python3
"""Patch P0 animation FBXs and freeze a UE-importable export manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cc_patch_unreal_animation_fbx_ascii import patch_fbx


class P0ExportFinalizeError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P0ExportFinalizeError(f"Unable to read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise P0ExportFinalizeError(f"Expected a JSON object: {path}")
    return value


def verified_file(record: dict, label: str) -> dict:
    path = Path(str(record.get("path", ""))).resolve()
    if not path.is_file():
        raise P0ExportFinalizeError(f"Missing {label}: {path}")
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record.get("bytes", -1)):
        raise P0ExportFinalizeError(f"{label} size drift: {path}")
    if actual_sha256 != record.get("sha256"):
        raise P0ExportFinalizeError(f"{label} hash drift: {path}")
    return {
        "path": str(path),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--work-order", type=Path, required=True)
    return parser.parse_args()


def finalize_export(export_root: Path, work_order_path: Path) -> dict:
    export_root = export_root.resolve()
    work_order_path = work_order_path.resolve()
    report_path = export_root / "p0_ue_runtime_cc_export.json"
    if not report_path.is_file():
        raise P0ExportFinalizeError(f"Missing CC export report: {report_path}")
    if not work_order_path.is_file():
        raise P0ExportFinalizeError(f"Missing work order: {work_order_path}")

    report = read_json(report_path)
    work_order = read_json(work_order_path)
    if report.get("status") != "cc_export_complete_patch_pending":
        raise P0ExportFinalizeError("CC export is not ready for bone-name patching")
    if report.get("success") is not True:
        raise P0ExportFinalizeError("CC export report is not successful")
    work_order_sha256 = sha256_file(work_order_path)
    report_work_order = report.get("work_order") or {}
    if report_work_order.get("sha256") != work_order_sha256:
        raise P0ExportFinalizeError("CC export work-order provenance drift")
    if report_work_order.get("id") != work_order.get("work_order_id"):
        raise P0ExportFinalizeError("CC export work-order ID mismatch")

    actor_records = []
    for actor in report.get("actors") or []:
        reference = actor.get("reference") or {}
        actor_records.append(
            {
                "actor_binding_id": actor.get("actor_binding_id"),
                "character_id": actor.get("character_id"),
                "sex": actor.get("sex"),
                "bodyfit_id": actor.get("bodyfit_id"),
                "appearance_recipe_id": actor.get("appearance_recipe_id"),
                "reference_fbx": verified_file(
                    reference.get("fbx") or {}, "reference FBX"
                ),
                "auto_setup_json": verified_file(
                    reference.get("json") or {}, "Auto Setup JSON"
                ),
                "fbm": reference.get("fbm"),
                "textures": reference.get("textures"),
                "ue_import_status": "pending",
            }
        )
    if len(actor_records) != 2:
        raise P0ExportFinalizeError("Expected two exported reference actors")

    motion_records = []
    for motion in report.get("motions") or []:
        raw = verified_file(motion.get("fbx") or {}, "raw animation FBX")
        raw_path = Path(raw["path"])
        suffix = "_UE5_ASCII.fbx"
        if not raw_path.name.endswith(suffix):
            raise P0ExportFinalizeError(
                f"Unexpected animation FBX name: {raw_path.name}"
            )
        patched_path = raw_path.with_name(
            raw_path.name[: -len(suffix)] + "_UE5_Patched.fbx"
        )
        patch_report_path = raw_path.with_name(
            raw_path.name[: -len(suffix)] + "_bone_patch.json"
        )
        patch_report = patch_fbx(raw_path, patched_path, patch_report_path)
        if patch_report.get("mapping_count") != 47:
            raise P0ExportFinalizeError(
                f"Expected 47 bone-name mappings for {motion.get('case_id')}"
            )
        motion_records.append(
            {
                "actor_binding_id": motion.get("actor_binding_id"),
                "case_id": motion.get("case_id"),
                "clip": motion.get("clip"),
                "root_motion_policy": (motion.get("options") or {}).get(
                    "root_motion_policy"
                ),
                "source_motion": motion.get("source_motion"),
                "raw_ascii_fbx": raw,
                "patched_fbx": {
                    "path": str(patched_path),
                    "bytes": patched_path.stat().st_size,
                    "sha256": sha256_file(patched_path),
                },
                "bone_patch_report": {
                    "path": str(patch_report_path),
                    "bytes": patch_report_path.stat().st_size,
                    "sha256": sha256_file(patch_report_path),
                    "mapping_count": patch_report["mapping_count"],
                },
                "ue_import_status": "pending",
                "ue_runtime_status": "pending",
                "production_status": "not_approved",
            }
        )
    expected_motion_count = int(
        (work_order.get("scope") or {}).get(
            "motion_count", len(report.get("motions") or [])
        )
    )
    if expected_motion_count < 1 or len(motion_records) != expected_motion_count:
        raise P0ExportFinalizeError(
            "Exported animation count differs from the work order"
        )

    manifest = {
        "schema_version": 1,
        "manifest_id": str(work_order.get("work_order_id")) + "_bundle",
        "status": "ready_for_ue_import",
        "production_status": "not_approved",
        "export_root": str(export_root),
        "work_order": {
            "id": work_order.get("work_order_id"),
            "path": str(work_order_path),
            "bytes": work_order_path.stat().st_size,
            "sha256": work_order_sha256,
        },
        "cc_export_report": {
            "path": str(report_path),
            "bytes": report_path.stat().st_size,
            "sha256": sha256_file(report_path),
        },
        "actors": actor_records,
        "motions": motion_records,
        "unreal": {
            "vendor_root": (work_order.get("unreal") or {}).get("vendor_root"),
            "datamake_root": (work_order.get("unreal") or {}).get(
                "datamake_root"
            ),
            "reference_import": "FBX plus same-basename JSON via Auto Setup",
            "animation_import": "patched_fbx only; bind to matching actor skeleton",
            "required_checks": (work_order.get("unreal") or {}).get(
                "required_runtime_checks"
            ),
            "status": "pending_import",
        },
        "notes": [
            "Both reference actors are saved generated characters with clothing.",
            "Raw ASCII animation FBXs are retained only as patch provenance.",
            "Patched FBXs modify 47 auxiliary bone-name tokens only.",
            "Morph and material acceptance remains an Unreal-side gate.",
        ],
    }
    manifest_path = export_root / "export_bundle_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    args = parse_args()
    manifest = finalize_export(args.export_root, args.work_order)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
