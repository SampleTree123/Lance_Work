#!/usr/bin/env python3
"""Validate a wardrobe batch and publish source-to-module mappings, not fit approval."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import modular_outfit_runtime_plan_v1 as runtime


PHASES = ("import_reference", "import_split", "apply_materials", "validate_case")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_case(case: dict, reports: dict) -> dict:
    for phase in PHASES:
        report = reports[phase]
        if (report.get("success") is not True or report.get("mode") != phase
                or report.get("case_id") != case["case_id"]):
            raise ValueError(f"Unsuccessful or wrong report: {case['case_id']}/{phase}")
    validated = reports["validate_case"]
    classified = runtime.classify_case_meshes(case, validated)
    paths = {p for module in classified["modules"] for p in module["mesh_paths"]}
    for mesh in validated["split_assets"]:
        if mesh.get("path") not in paths:
            continue
        if mesh.get("skeleton") != validated["base_skeleton"]:
            raise ValueError(f"Wrong garment skeleton: {mesh['path']}")
        if mesh.get("physics_asset"):
            raise ValueError(f"Unexpected garment PhysicsAsset: {mesh['path']}")
        if mesh.get("lod0_vertices", 0) <= 0:
            raise ValueError(f"Empty garment: {mesh['path']}")
    return {
        **classified, "sex": case["sex"], "bodyfit_id": case["bodyfit_id"],
        "base_skeleton": validated["base_skeleton"],
        "transfer_passed": True, "fit_review": "pending", "runtime_approved": False,
        "witness_auxiliary_import_exception": reports["import_reference"].get("import_exception"),
        "witness_usage": "material_source_only_not_runtime_body_or_expression",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = runtime.read_json(args.manifest)
    if manifest.get("import_scope") != "wardrobe_average_v1":
        raise ValueError("Expected a wardrobe manifest")
    cases = [c for c in manifest["cases"] if not c.get("reuse_existing_base")]
    if not cases:
        raise ValueError("No garment cases")
    rows, evidence = [], []
    for case in cases:
        for key in ("fbx", "auto_setup_json", "project"):
            source = case["export"][key]
            path = Path(source["path"])
            if file_hash(path) != source["sha256"]:
                raise ValueError(f"Export changed since Finalize: {path}")
        reports = {}
        for phase in PHASES:
            path = args.report_root / f"{case['case_id']}_{phase}.json"
            reports[phase] = runtime.read_json(path)
            evidence.append({"path": str(path.resolve()), "sha256": file_hash(path)})
        rows.append(validate_case(case, reports))
    output = args.output or args.report_root / "wardrobe_modules.json"
    runtime.write_json(output, {
        "schema_version": 1, "scope": "wardrobe_average_batch_transfer",
        "manifest": {"path": str(args.manifest.resolve()), "sha256": file_hash(args.manifest)},
        "success": True, "case_count": len(rows),
        "classified_mesh_count": sum(r["classified_mesh_count"] for r in rows),
        "runtime_approved": False, "cases": rows, "evidence": evidence,
    })
    print(f"Validated {len(rows)} garment units; mapping: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
