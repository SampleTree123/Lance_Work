"""Preserve accepted review evidence and create new plans for curated UE paths."""

from __future__ import annotations

import json
from pathlib import Path


ENGINE = Path(r"D:\UE\Lance_Work\00_engine")
ROOT = ENGINE / "outputs/unreal_character_import/asset_restructure_full_20260929_v1"
ORIGINALS = {
    "modular_runtime_v2": ENGINE / "outputs/unreal_character_import/modular_outfit_pilot_20260829_v1/runtime_plan_v2.json",
    "wardrobe_coverage": ENGINE / "outputs/unreal_character_import/wardrobe_average_20260906_v1/coverage_review_20260912_v1/review_plan.json",
    "hair_outfit_compatibility": ENGINE / "outputs/unreal_character_import/hair_outfit_compatibility_20260926_v1/compatibility_plan.json",
}


def convert(value, mapping, roots):
    if isinstance(value, str):
        return mapping.get(value, roots.get(value, value))
    if isinstance(value, list):
        return [convert(item, mapping, roots) for item in value]
    if isinstance(value, dict):
        return {convert(key, mapping, roots): convert(item, mapping, roots) for key, item in value.items()}
    return value


def run():
    plan = json.loads((ROOT / "migration_plan.json").read_text(encoding="utf-8"))
    mapping = {asset["old"]: asset["new"] for case in plan["cases"] for asset in case["assets"]}
    roots = {case["old_root"]: case["new_root"] for case in plan["cases"]}
    result = {}
    for name, original in ORIGINALS.items():
        data = json.loads(original.read_text(encoding="utf-8"))
        updated = convert(data, mapping, roots)
        filename = "runtime_plan_v2.json" if name == "modular_runtime_v2" else "review_plan.json"
        path = ROOT / "review_plans" / name / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        remaining = [token for token in ("/Game/Vendor/Reallusion/CC5/Wardrobe/",
                                        "/Game/Vendor/Reallusion/CC5/ScalpHairBatch/")
                     if token in json.dumps(updated, ensure_ascii=False)]
        result[name] = {"path": str(path), "unresolved_old_path_prefixes": remaining}
    report = ROOT / "review_plan_migration_report.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    run()
