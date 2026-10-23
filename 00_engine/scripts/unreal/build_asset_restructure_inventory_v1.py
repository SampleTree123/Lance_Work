"""Inventory imported outfit/hair meshes and duplicate case storage without UE edits."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
CONTENT = Path(r"D:\UE\projects\datatry_02\Content")
WARDROBE_REPORTS = ROOT / "outputs/unreal_character_import/wardrobe_average_20260906_v1"
HAIR_REPORT = ROOT / "outputs/unreal_character_import/scalp_hair_batch_20260924_v1/batch_import_report.json"
DRAFT = ROOT / "assets/character_creator/wardrobe_registry_ue_v4_draft_example_v2.json"
OUTPUT = ROOT / "outputs/unreal_character_import/asset_restructure_pilot_20260928_v1/full_import_inventory.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def on_disk(object_path):
    package = object_path.rsplit(".", 1)[0]
    if not package.startswith("/Game/"):
        raise ValueError(f"not a game asset: {object_path}")
    return CONTENT / (package.removeprefix("/Game/") + ".uasset")


def record(path):
    physical = on_disk(path)
    return {"path": path, "bytes": physical.stat().st_size if physical.is_file() else None}


def tree_bytes(ue_root):
    physical = CONTENT / ue_root.removeprefix("/Game/")
    return sum(path.stat().st_size for path in physical.rglob("*.uasset")) if physical.is_dir() else None


def summarize(rows):
    return {
        "cases": len(rows),
        "selected_meshes": sum(len(row["selected_meshes"]) for row in rows),
        "ignored_split_meshes": sum(len(row["ignored_split_meshes"]) for row in rows),
        "selected_mesh_bytes": sum(item["bytes"] or 0 for row in rows for item in row["selected_meshes"]),
        "ignored_split_mesh_bytes": sum(item["bytes"] or 0 for row in rows for item in row["ignored_split_meshes"]),
        "full_reference_tree_bytes": sum(row["full_reference_tree_bytes"] or 0 for row in rows),
        "missing_selected_meshes": sum(item["bytes"] is None for row in rows for item in row["selected_meshes"]),
        "missing_ignored_meshes": sum(item["bytes"] is None for row in rows for item in row["ignored_split_meshes"]),
    }


def wardrobe_rows():
    rows = []
    reports = sorted(WARDROBE_REPORTS.glob("batch_*/wardrobe_modules.json"))
    for path in reports:
        report = read_json(path)
        if not report.get("success"):
            raise ValueError(f"unsuccessful wardrobe mapping: {path}")
        for case in report["cases"]:
            selected = [record(mesh) for module in case["modules"] for mesh in module["mesh_paths"]]
            ignored = [record(mesh["path"]) for mesh in case["ignored_split_meshes"]]
            if not selected:
                raise ValueError(f"no selected garment mesh: {case['case_id']}")
            case_root = selected[0]["path"].split("/Modules/")[0]
            rows.append({
                "case_id": case["case_id"],
                "sex": case["sex"],
                "case_root": case_root,
                "selected_meshes": selected,
                "ignored_split_meshes": ignored,
                "full_reference_tree_bytes": tree_bytes(case_root + "/FullReference"),
                "source_report": str(path.relative_to(ROOT)).replace("\\", "/"),
            })
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate wardrobe case IDs")
    return rows


def hair_rows():
    report = read_json(HAIR_REPORT)
    draft = read_json(DRAFT)
    kept = {item["preset_id"]: {mesh["path"] for mesh in item["meshes"]}
            for item in draft["hair_assets"]}
    rows = []
    for case in report["records"]:
        if not case.get("success"):
            raise ValueError(f"unsuccessful hair import: {case['preset_id']}")
        expected = kept[case["preset_id"]]
        all_meshes = {mesh["path"] for mesh in case["runtime_hair_meshes"]}
        if not expected <= all_meshes:
            raise ValueError(f"draft hair mesh missing from import report: {case['preset_id']}")
        rows.append({
            "preset_id": case["preset_id"],
            "case_root": case["modules"].rsplit("/Modules", 1)[0],
            "selected_meshes": [record(path) for path in sorted(expected)],
            "ignored_split_meshes": [record(path) for path in sorted(all_meshes - expected)],
            "full_reference_tree_bytes": tree_bytes(case["full_reference"]),
        })
    if len(rows) != len(kept):
        raise ValueError("hair registry and import report counts differ")
    return rows


def main():
    wardrobe = wardrobe_rows()
    hair = hair_rows()
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "read_only_import_inventory_not_cleanup_approval",
        "note": "FullReference bytes include required material/texture dependencies; not all are reclaimable.",
        "wardrobe_summary": summarize(wardrobe),
        "hair_summary": summarize(hair),
        "wardrobe_cases": wardrobe,
        "hair_cases": hair,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "wardrobe": report["wardrobe_summary"],
                      "hair": report["hair_summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
