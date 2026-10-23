"""Read-only UE dependency audit for one outfit module and one retained hairstyle."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import unreal


REPORT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\asset_restructure_pilot_20260928_v1\ue_dependency_audit.json"
)
SOURCES = {
    "outfit_pants5": [
        "/Game/Vendor/Reallusion/CC5/Wardrobe/Female/Average/pretty_dresses/"
        "Pants/F_c8e91d70314b5d5f0c13/Modules/"
        "kg5_jeans2_5647_shape.kg5_jeans2_5647_shape"
    ],
    "hair_hb1_01": [
        "/Game/Vendor/Reallusion/CC5/ScalpHairBatch/F02_Average/"
        "HB1_01_Interchange/Modules/curly_long_hair.curly_long_hair",
        "/Game/Vendor/Reallusion/CC5/ScalpHairBatch/F02_Average/"
        "HB1_01_Interchange/Modules/curly_ponytail_back.curly_ponytail_back",
        "/Game/Vendor/Reallusion/CC5/ScalpHairBatch/F02_Average/"
        "HB1_01_Interchange/Modules/hair_base.hair_base",
        "/Game/Vendor/Reallusion/CC5/ScalpHairBatch/F02_Average/"
        "HB1_01_Interchange/Modules/side_bangs.side_bangs",
    ],
}


def path_of(value):
    return value.get_path_name() if value is not None else None


def package_of(object_path):
    return object_path.rsplit(".", 1)[0]


def run():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions()
    for name in (
        "include_hard_package_references",
        "include_soft_package_references",
        "include_game_package_references",
        "include_editor_only_package_references",
    ):
        options.set_editor_property(name, True)
    cases = []
    for label, paths in SOURCES.items():
        root = paths[0].split("/Modules/")[0]
        assets = registry.get_assets_by_path(root, recursive=True)
        counts = Counter(str(asset.asset_class_path.asset_name) for asset in assets)
        class_by_package = {
            str(asset.package_name): str(asset.asset_class_path.asset_name)
            for asset in assets
        }
        meshes = []
        local_closure = set()
        external_dependencies = set()
        for path in paths:
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.SkeletalMesh):
                raise RuntimeError(f"Expected SkeletalMesh: {path}")
            package = package_of(path)
            materials = []
            for slot in mesh.get_editor_property("materials") or []:
                material = slot.get_editor_property("material_interface")
                materials.append(path_of(material))
            meshes.append(
                {
                    "path": path,
                    "skeleton": path_of(mesh.get_editor_property("skeleton")),
                    "materials": materials,
                    "dependencies": sorted(map(str, registry.get_dependencies(package, options) or [])),
                    "referencers": sorted(map(str, registry.get_referencers(package, options) or [])),
                }
            )
            pending = [package]
            seen = set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                for dependency in map(str, registry.get_dependencies(current, options) or []):
                    if dependency.startswith(root + "/"):
                        if dependency not in local_closure:
                            local_closure.add(dependency)
                        pending.append(dependency)
                    else:
                        external_dependencies.add(dependency)
        material_parameters = []
        for dependency in sorted(local_closure):
            if class_by_package.get(dependency) != "MaterialInstanceConstant":
                continue
            material = unreal.load_asset(dependency)
            parameters = []
            for entry in material.get_editor_property("texture_parameter_values") or []:
                info = entry.get_editor_property("parameter_info")
                parameters.append({
                    "name": str(info.get_editor_property("name")),
                    "value": path_of(entry.get_editor_property("parameter_value")),
                })
            material_parameters.append({
                "path": path_of(material),
                "parent": path_of(material.get_editor_property("parent")),
                "override_parameters": parameters,
            })
        cases.append(
            {
                "label": label,
                "case_root": root,
                "asset_class_counts": dict(sorted(counts.items())),
                "full_reference_asset_count": sum(
                    1 for asset in assets if "/FullReference/" in str(asset.package_name)
                ),
                "modules_asset_count": sum(
                    1 for asset in assets if "/Modules/" in str(asset.package_name)
                ),
                "local_dependency_closure": [
                    {"package": package, "class": class_by_package.get(package)}
                    for package in sorted(local_closure)
                ],
                "external_dependencies": sorted(external_dependencies),
                "material_parameters": material_parameters,
                "meshes": meshes,
            }
        )
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "scope": "read_only_pilot_dependency_audit",
        "cases": cases,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake asset restructure dependency audit: {REPORT}")


run()
