"""Fresh-process structural check for every completed full migration case."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1")
PLAN = ROOT / "migration_plan.json"
PROGRESS = ROOT / "copy_progress.json"
REPORT = ROOT / "fresh_load_verification.json"


def path(asset):
    return asset.get_path_name() if asset is not None else None


def run():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    done = {entry["id"] for entry in progress["completed"]}
    recorded_skeletons = {mesh: skeleton for entry in progress["completed"]
                          for mesh, skeleton in entry["skeletons"].items()}
    all_old_roots = tuple(case["old_root"] + "/" for case in plan["cases"])
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions()
    for name in ("include_hard_package_references", "include_soft_package_references",
                 "include_game_package_references", "include_editor_only_package_references"):
        options.set_editor_property(name, True)
    summary = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "checked_cases": 0, "checked_assets": 0, "old_source_meshes_available": 0,
               "old_source_meshes_removed": 0, "errors": [], "success": False}
    for case in plan["cases"]:
        if case["id"] not in done:
            continue
        old_root, new_root = case["old_root"], case["new_root"]
        for item in case["assets"]:
            asset = unreal.load_asset(item["new"])
            if asset is None or str(asset.get_class().get_name()) != item["class"]:
                summary["errors"].append(f"missing or wrong class: {item['new']}")
                continue
            summary["checked_assets"] += 1
            if item["class"] == "SkeletalMesh":
                if unreal.EditorAssetLibrary.does_asset_exist(item["old"]):
                    summary["old_source_meshes_available"] += 1
                    old = unreal.load_asset(item["old"])
                    expected_skeleton = path(old.get_editor_property("skeleton")) if old else None
                else:
                    summary["old_source_meshes_removed"] += 1
                    expected_skeleton = recorded_skeletons.get(item["new"])
                if not expected_skeleton or path(asset.get_editor_property("skeleton")) != expected_skeleton:
                    summary["errors"].append(f"skeleton changed: {item['new']}")
            package = item["new"].rsplit(".", 1)[0]
            deps = [str(value) for value in registry.get_dependencies(package, options) or []]
            leaking = [value for value in deps if value.startswith(all_old_roots)]
            if leaking:
                summary["errors"].append(f"source dependency: {item['new']} -> {leaking}")
        summary["checked_cases"] += 1
        if summary["checked_cases"] % 25 == 0:
            unreal.log(f"DataMake full restructure verify {summary['checked_cases']}/{len(done)}")
    summary["success"] = not summary["errors"] and summary["checked_cases"] == len(done)
    summary["registry_roots"] = {
        "new_runtime_assets": len(registry.get_assets_by_path("/Game/DataMake/CharacterFactory", recursive=True)),
        "old_wardrobe_assets": len(registry.get_assets_by_path("/Game/Vendor/Reallusion/CC5/Wardrobe", recursive=True)),
        "old_hair_assets": len(registry.get_assets_by_path("/Game/Vendor/Reallusion/CC5/ScalpHairBatch", recursive=True)),
        "old_pilot_assets": len(registry.get_assets_by_path("/Game/DataMake/CharacterFactory/RestructurePilot", recursive=True)),
    }
    if summary["registry_roots"] != {"new_runtime_assets": 4732, "old_wardrobe_assets": 0,
                                      "old_hair_assets": 0, "old_pilot_assets": 0}:
        summary["errors"].append(f"root inventory mismatch: {summary['registry_roots']}")
        summary["success"] = False
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake full restructure verify: {summary}")
    if not summary["success"]:
        raise RuntimeError(f"verification failed: {len(summary['errors'])} errors")


run()
