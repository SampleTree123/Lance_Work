"""Publish repaired material references without changing dual-fit geometry.

Run only after both UE repair workers have saved successful apply reports.
The prior 80-fit registry, import report and publication remain immutable.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import formal_wardrobe_registry_v1 as formal
from build_fixed_head_hair_registry_v1 import read, write_atomic

BATCH_ID = "fixed_head_material_repair_20261005_v1"
RUN = formal.ENGINE / f"outputs/unreal_character_import/{BATCH_ID}"
TARGET_PREFIX = "/Game/DataMake/CharacterFactory/MaterialRemediation_20261005_v1/Hair/"
EXPECTED_IDS = {"HAIR_HB1_18", "HAIR_HB2_02", "HAIR_HB2_05", "HAIR_HB2_06", "HAIR_HB2_12"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_registry(source: dict, hair_report: dict, skin_report: dict) -> dict:
    formal.validate_registry(source)
    for report in (hair_report, skin_report):
        if report.get("success") is not True or report.get("mode") != "apply":
            raise ValueError("Publication requires successful saved apply reports")
    rows = hair_report.get("records", [])
    if len(rows) != 24 or {r.get("hair_id") for r in rows} != EXPECTED_IDS:
        raise ValueError("Expected all 24 diagnosed braid material slots in five hairstyles")
    skin_rows = skin_report.get("changed_slots", [])
    if {r.get("sex") for r in skin_rows} != {"female", "male"} or len({r.get("mesh") for r in skin_rows}) != 2:
        raise ValueError("Expected saved skin materials on both reference bodies")
    result = deepcopy(source)
    slots = {}
    for hair in result["hair_assets"]:
        for sex, fit in hair["fit_variants"].items():
            for mesh in fit["meshes"]:
                for index, binding in enumerate(mesh["materials"]):
                    slots[(mesh["path"], index)] = (hair["hair_id"], sex, mesh, binding)
    changed = set()
    for row in rows:
        key = (row["mesh"], row["slot_index"])
        if key in changed or key not in slots:
            raise ValueError("Duplicate or unknown repair material slot")
        hair_id, sex, mesh, before = slots[key]
        after = row.get("material", "")
        if (hair_id != row.get("hair_id") or sex != row.get("sex")
                or before != row.get("before") or not after.startswith(TARGET_PREFIX)
                or "." not in after.rsplit("/", 1)[-1]):
            raise ValueError("Repair provenance does not match source registry")
        mesh["materials"][key[1]] = after
        changed.add(key)
    formal.validate_registry(result)
    # Deep-copy + only the exact material-slot assignments above preserves all
    # wardrobe rules, shoes, fit Skeletons/meshes, style ordering and sex policy.
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hair-report", type=Path, default=RUN / "hair/hair_apply_latest.json")
    parser.add_argument("--skin-report", type=Path, default=RUN / "skin_apply.json")
    args = parser.parse_args()
    if formal.historical_registry_path() not in {formal.DUAL_FIT_REGISTRY, formal.MATERIAL_REPAIR_REGISTRY}:
        raise ValueError("Original hash-bound 80-fit publication must be valid first")
    source_path = formal.DUAL_FIT_REGISTRY
    result = build_registry(read(source_path), read(args.hair_report), read(args.skin_report))
    output = formal.MATERIAL_REPAIR_REGISTRY
    write_atomic(output, result)
    # Keep durable snapshots instead of binding mutable *_latest diagnostics.
    snapshots = {"hair_apply_report": RUN / "hair_apply_publication.json",
                 "skin_apply_report": RUN / "skin_apply_publication.json"}
    for key, source in (("hair_apply_report", args.hair_report), ("skin_apply_report", args.skin_report)):
        write_atomic(snapshots[key], read(source))
    receipt = {"schema_version": 1, "batch_id": BATCH_ID, "success": True,
               "source_registry": str(source_path.resolve()), "source_registry_sha256": digest(source_path),
               "output_registry": str(output.resolve()), "output_registry_sha256": digest(output),
               "counts": {"hairstyles": 40, "fits": 80, "hair_material_slots": 24},
               "families_meshes_and_usage_permissions_preserved": True,
               "body_geometry_unchanged": True,
               "body_material_bindings_recorded_in": "skin_apply_report"}
    for key, path in snapshots.items():
        receipt[key] = str(path.resolve())
        receipt[key + "_sha256"] = digest(path)
    write_atomic(formal.MATERIAL_REPAIR_PUBLICATION, receipt)
    if formal.historical_registry_path() != output:
        raise RuntimeError("Publication did not pass the historical registry hash gate")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
