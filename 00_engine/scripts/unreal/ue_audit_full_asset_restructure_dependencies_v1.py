"""Read-only Asset Registry dependency scan for all imported outfit/hair modules."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\asset_restructure_pilot_20260928_v1"
)
INVENTORY = ROOT / "full_import_inventory.json"
REPORT = ROOT / "full_dependency_audit.json"


def package_of(path):
    return path.rsplit(".", 1)[0]


def run():
    source = json.loads(INVENTORY.read_text(encoding="utf-8"))
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions()
    for name in (
        "include_hard_package_references",
        "include_soft_package_references",
        "include_game_package_references",
        "include_editor_only_package_references",
    ):
        options.set_editor_property(name, True)
    output = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "read_only_full_library_dependency_scan_not_migration_approval",
              "cases": [], "summary": {}, "success": False}
    all_cases = [("wardrobe", case) for case in source["wardrobe_cases"]]
    all_cases += [("hair", case) for case in source["hair_cases"]]
    for index, (kind, case) in enumerate(all_cases, 1):
        root = case["case_root"]
        assets = registry.get_assets_by_path(root, recursive=True)
        classes = {str(asset.package_name): str(asset.asset_class_path.asset_name)
                   for asset in assets}
        selected = [package_of(item["path"]) for item in case["selected_meshes"]]
        for package in selected:
            if classes.get(package) != "SkeletalMesh":
                raise RuntimeError(f"missing selected SkeletalMesh in Asset Registry: {package}")
        seen = set()
        closure = set()
        external = set()
        pending = list(selected)
        while pending:
            package = pending.pop()
            if package in seen:
                continue
            seen.add(package)
            for dependency in map(str, registry.get_dependencies(package, options) or []):
                if dependency.startswith(root + "/"):
                    closure.add(dependency)
                    pending.append(dependency)
                elif dependency.startswith("/Game/") or dependency.startswith("/InterchangeAssets/"):
                    external.add(dependency)
        closure.difference_update(selected)
        class_counts = Counter(classes.get(package, "UNRESOLVED") for package in closure)
        output["cases"].append({
            "kind": kind,
            "id": case.get("case_id", case.get("preset_id")),
            "case_root": root,
            "selected_mesh_count": len(selected),
            "local_dependency_count": len(closure),
            "local_dependency_class_counts": dict(sorted(class_counts.items())),
            "local_dependencies": [
                {"package": package, "class": classes.get(package, "UNRESOLVED")}
                for package in sorted(closure)
            ],
            "external_game_dependencies": sorted(external),
        })
        if index % 25 == 0:
            unreal.log(f"DataMake full asset dependency audit {index}/{len(all_cases)}")
    all_classes = Counter()
    unsupported = []
    for case in output["cases"]:
        all_classes.update(case["local_dependency_class_counts"])
        if any(name not in {"Texture2D", "MaterialInstanceConstant"}
               for name in case["local_dependency_class_counts"]):
            unsupported.append(case["id"])
    output["summary"] = {
        "cases": len(output["cases"]),
        "wardrobe_cases": sum(case["kind"] == "wardrobe" for case in output["cases"]),
        "hair_cases": sum(case["kind"] == "hair" for case in output["cases"]),
        "selected_meshes": sum(case["selected_mesh_count"] for case in output["cases"]),
        "local_dependency_class_counts": dict(sorted(all_classes.items())),
        "cases_requiring_extended_migration_logic": unsupported,
    }
    output["success"] = True
    REPORT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake full asset dependency audit: {REPORT}")


run()
