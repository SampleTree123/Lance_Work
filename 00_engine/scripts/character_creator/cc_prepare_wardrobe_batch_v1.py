#!/usr/bin/env python3
"""Create a bounded CC export batch and finalize its UE import work order."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import cc_build_modular_outfit_pilot_v1 as common
import cc_build_wardrobe_library_v1 as wardrobe
import cc_finalize_modular_outfit_pilot_v1 as finalizer


def prepare(library_dir: Path, batch_dir: Path, unit_ids: list[str]):
    if not unit_ids or len(unit_ids) != len(set(unit_ids)):
        raise ValueError("Select unique, explicit unit IDs")
    if batch_dir.exists():
        raise FileExistsError(f"Batch already exists: {batch_dir}")
    cc = common.read_json(library_dir / "cc_export.json")
    ue = common.read_json(library_dir / "ue_import.json")
    presets = {p["preset_id"]: p for p in cc["presets"]}
    unknown = set(unit_ids) - set(presets)
    if unknown:
        raise ValueError(f"Unknown units: {sorted(unknown)}")
    cc["presets"] = [presets[uid] for uid in unit_ids]
    for preset in cc["presets"]:
        outputs = preset["production_output"]
        if Path(outputs["project_path"]).exists() or Path(outputs["export_root"]).exists():
            raise FileExistsError(f"Output already exists: {preset['preset_id']}")
    cc["counts"] = {"case_count": len(unit_ids)}
    ue["cases"] = [c for c in ue["cases"] if c["case_id"] in unit_ids]
    ue["counts"] = {"case_count": len(unit_ids)}
    common.write_json(batch_dir / "cc_export.json", cc)
    common.write_json(batch_dir / "ue_pending.json", ue)


def finalize(library_dir: Path, batch_dir: Path, result_path: Path):
    completed = finalizer.finalize_manifest(
        batch_dir / "ue_pending.json", batch_dir / "cc_export.json", result_path
    )
    full = common.read_json(library_dir / "ue_import.json")
    bases = [copy.deepcopy(c) for c in full["cases"] if c["case_role"] == "base_body"]
    completed["cases"] = bases + completed["cases"]
    completed["counts"]["case_count"] = len(completed["cases"])
    common.write_json(batch_dir / "ue_import.json", completed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-dir", type=Path, default=wardrobe.DEFAULT_OUTPUT)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--unit-id", action="append", default=[])
    parser.add_argument("--finalize-result", type=Path)
    args = parser.parse_args()
    if args.finalize_result:
        finalize(args.library_dir, args.batch_dir, args.finalize_result)
    else:
        prepare(args.library_dir, args.batch_dir, args.unit_id)


if __name__ == "__main__":
    main()
