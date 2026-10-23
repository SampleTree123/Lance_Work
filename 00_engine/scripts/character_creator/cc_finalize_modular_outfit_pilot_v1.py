#!/usr/bin/env python3
"""Attach successful CC export evidence to the UE modular pilot manifest."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
DEFAULT_CC_MANIFEST = SCRIPT_ROOT / "cc_modular_outfit_pilot_20260829_v1.json"
DEFAULT_RUNTIME_MANIFEST = (
    LANCE_ROOT
    / "00_engine"
    / "scripts"
    / "unreal"
    / "ue_modular_outfit_pilot_manifest_20260829_v1.json"
)


class FinalizeError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinalizeError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_output_file(record: dict[str, Any], label: str) -> dict[str, Any]:
    path = Path(record.get("path", "")).resolve()
    if not path.is_file():
        raise FinalizeError(f"{label} is missing: {path}")
    size_bytes = path.stat().st_size
    expected_size = record.get("bytes", record.get("size_bytes"))
    expected_sha = str(record.get("sha256", "")).lower()
    actual_sha = sha256_file(path)
    if size_bytes != expected_size or actual_sha != expected_sha:
        raise FinalizeError(f"{label} changed after CC export: {path}")
    return {"path": str(path), "size_bytes": size_bytes, "sha256": actual_sha}


def finalize_manifest(
    runtime_manifest_path: Path,
    cc_manifest_path: Path,
    validation_result_path: Path,
) -> dict[str, Any]:
    runtime_manifest_path = runtime_manifest_path.resolve()
    cc_manifest_path = cc_manifest_path.resolve()
    validation_result_path = validation_result_path.resolve()
    runtime = read_json(runtime_manifest_path)
    cc_manifest = read_json(cc_manifest_path)
    summary = read_json(validation_result_path)
    if runtime.get("pilot_id") != cc_manifest.get("pilot_id"):
        raise FinalizeError("CC and UE manifests describe different pilots")
    runtime_cases = runtime.get("cases") or []
    expected_case_ids = {case.get("case_id") for case in runtime_cases}
    if None in expected_case_ids or len(expected_case_ids) != len(runtime_cases):
        raise FinalizeError("Runtime manifest has invalid case IDs")
    if (
        summary.get("success") is not True
        or summary.get("failure_count") != 0
        or summary.get("success_count") != len(runtime_cases)
    ):
        raise FinalizeError("CC modular export summary is not fully successful")
    summary_results = summary.get("results") or []
    by_case = {item.get("case_id"): item for item in summary_results}
    if set(by_case) != expected_case_ids or len(by_case) != len(summary_results):
        raise FinalizeError("CC export evidence does not cover the runtime cases exactly")

    finalized = copy.deepcopy(runtime)
    finalized["status"] = "cc_export_passed"
    finalized["cc_export_evidence"] = {
        "validation_result": {
            "path": str(validation_result_path),
            "sha256": sha256_file(validation_result_path),
        },
        "started_at": summary.get("started_at"),
        "finished_at": summary.get("finished_at"),
        "success_count": summary.get("success_count"),
        "failure_count": summary.get("failure_count"),
    }
    finalized_cases = {case["case_id"]: case for case in finalized["cases"]}
    for case_id in sorted(expected_case_ids):
        summary_record = by_case[case_id]
        if summary_record.get("success") is not True:
            raise FinalizeError(f"CC export case failed: {case_id}")
        result_path = Path(summary_record.get("result_path", "")).resolve()
        result = read_json(result_path)
        if result.get("case_id") != case_id or result.get("success") is not True:
            raise FinalizeError(f"CC case result is invalid: {case_id}")
        case = finalized_cases[case_id]
        expected_modules = {module["asset_id"]: module for module in case["modules"]}
        applications = result.get("asset_applications") or []
        by_asset = {item.get("asset_id"): item for item in applications}
        if set(by_asset) != set(expected_modules) or len(by_asset) != len(applications):
            raise FinalizeError(f"CC module evidence differs from manifest: {case_id}")
        for asset_id, module in expected_modules.items():
            application = by_asset[asset_id]
            added = (application.get("inventory_changes") or {}).get("added") or []
            if not added:
                raise FinalizeError(
                    f"CC module added no independently traceable object: {case_id}/{asset_id}"
                )
            module["cc_scene_objects"] = [
                {
                    "collection": item.get("collection"),
                    "name": item.get("name"),
                    "python_type": item.get("python_type"),
                }
                for item in added
            ]
            module["cc_application"] = {
                "cloth_options_policy": application.get("cloth_options_policy"),
                "dialog_count": len(
                    (application.get("dialogs") or {}).get("observed_dialogs") or []
                ),
                "removed_previously_applied_asset_count": len(
                    application.get("removed_previously_applied_assets") or []
                ),
            }
        assembled = result.get("assembled_inventory") or {}
        clothes = [
            item
            for item in assembled.get("objects") or []
            if item.get("collection") == "GetClothes"
        ]
        if case["case_role"] == "base_body" and clothes:
            raise FinalizeError(f"Base export still contains clothing: {case_id}")

        production = result.get("production_export") or {}
        fbx = verify_output_file(production.get("fbx") or {}, f"{case_id} FBX")
        auto_setup_json = verify_output_file(
            production.get("json") or {}, f"{case_id} Auto Setup JSON"
        )
        project = verify_output_file(
            result.get("production_project") or {}, f"{case_id} CC project"
        )
        planned = case.get("planned_export") or {}
        if (
            Path(planned.get("fbx", "")).resolve() != Path(fbx["path"])
            or Path(planned.get("json", "")).resolve()
            != Path(auto_setup_json["path"])
            or Path(planned.get("project", "")).resolve()
            != Path(project["path"])
        ):
            raise FinalizeError(f"CC export paths differ from the frozen plan: {case_id}")
        case["export"] = {
            "fbx": fbx,
            "auto_setup_json": auto_setup_json,
            "project": project,
            "fbm": production.get("fbm"),
            "textures": production.get("textures"),
        }
        case["cc_inventory"] = {
            "object_count": assembled.get("object_count"),
            "clothing_object_count": len(clothes),
            "hair_object_count": sum(
                item.get("collection") == "GetHairs"
                for item in assembled.get("objects") or []
            ),
        }
        case["cc_result_evidence"] = {
            "path": str(result_path),
            "sha256": sha256_file(result_path),
        }
        case["validation_status"] = "cc_export_passed"
    return finalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-result", type=Path, required=True)
    parser.add_argument("--cc-manifest", type=Path, default=DEFAULT_CC_MANIFEST)
    parser.add_argument(
        "--runtime-manifest", type=Path, default=DEFAULT_RUNTIME_MANIFEST
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_RUNTIME_MANIFEST)
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args()
    finalized = finalize_manifest(
        args.runtime_manifest,
        args.cc_manifest,
        args.validation_result,
    )
    write_json(args.output.resolve(), finalized)
    if args.evidence_output is not None:
        write_json(args.evidence_output.resolve(), finalized)
    print(
        json.dumps(
            {
                "success": True,
                "status": finalized["status"],
                "case_count": len(finalized["cases"]),
                "source_module_count": sum(
                    len(case["modules"]) for case in finalized["cases"]
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
