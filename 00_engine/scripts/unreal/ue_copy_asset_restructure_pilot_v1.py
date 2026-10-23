"""Copy two approved module examples into self-contained UE runtime folders.

The original imported case trees are never changed or removed. Run the read-only
dependency audit first; this script refuses an occupied destination.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\asset_restructure_pilot_20260928_v1"
)
AUDIT = ROOT / "ue_dependency_audit.json"
REPORT = ROOT / "ue_copy_report.json"
DESTINATIONS = {
    "outfit_pants5": "/Game/DataMake/CharacterFactory/RestructurePilot/Wardrobe/Female/pretty_dresses/Pants5",
    "hair_hb1_01": "/Game/DataMake/CharacterFactory/RestructurePilot/Hair/HB1_01",
}


def path_of(asset):
    return asset.get_path_name() if asset is not None else None


def package_name(object_path):
    return object_path.rsplit(".", 1)[0]


def object_path(package):
    return package + "." + package.rsplit("/", 1)[-1]


def copy_asset(source_package, target_package):
    source = object_path(source_package)
    target = object_path(target_package)
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        asset = unreal.load_asset(target)
        original = unreal.load_asset(source)
        if asset is None or original is None or asset.get_class() != original.get_class():
            raise RuntimeError(f"destination occupied by wrong class: {target}")
    else:
        asset = unreal.EditorAssetLibrary.duplicate_asset(source, target)
    if asset is None:
        raise RuntimeError(f"duplicate failed: {source} -> {target}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save duplicated asset: {target}")
    return asset


def remap_material_textures(material, texture_map):
    parameters = list(material.get_editor_property("texture_parameter_values") or [])
    changed = []
    for parameter in parameters:
        name = parameter.get_editor_property("parameter_info").get_editor_property("name")
        original = parameter.get_editor_property("parameter_value")
        old_path = path_of(original)
        if old_path not in texture_map:
            continue
        replacement = unreal.load_asset(texture_map[old_path])
        if replacement is None:
            raise RuntimeError(f"missing duplicated texture: {texture_map[old_path]}")
        parameter.set_editor_property("parameter_value", replacement)
        changed.append({"parameter": str(name), "old": old_path, "new": path_of(replacement)})
    material.set_editor_property("texture_parameter_values", parameters)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save material: {path_of(material)}")
    return changed


def copy_case(case):
    label = case["label"]
    destination = DESTINATIONS[label]
    local = case["local_dependency_closure"]
    unsupported = sorted({item["class"] for item in local} - {"Texture2D", "MaterialInstanceConstant"})
    if unsupported:
        raise RuntimeError(f"unsupported local dependency classes for {label}: {unsupported}")
    result = {"label": label, "source_root": case["case_root"], "destination_root": destination,
              "textures": [], "materials": [], "meshes": [], "success": False}
    texture_map = {}
    material_map = {}
    for item in local:
        if item["class"] != "Texture2D":
            continue
        old_package = item["package"]
        new_package = destination + "/Textures/" + old_package.rsplit("/", 1)[-1]
        copy_asset(old_package, new_package)
        texture_map[object_path(old_package)] = object_path(new_package)
        result["textures"].append({"old": object_path(old_package), "new": object_path(new_package)})
    for item in local:
        if item["class"] != "MaterialInstanceConstant":
            continue
        old_package = item["package"]
        new_package = destination + "/Materials/" + old_package.rsplit("/", 1)[-1]
        material = copy_asset(old_package, new_package)
        changed = remap_material_textures(material, texture_map)
        material_map[object_path(old_package)] = object_path(new_package)
        result["materials"].append({"old": object_path(old_package), "new": object_path(new_package),
                                    "texture_parameters_rewired": changed})
    for item in case["meshes"]:
        old_path = item["path"]
        new_package = destination + "/Meshes/" + package_name(old_path).rsplit("/", 1)[-1]
        mesh = copy_asset(package_name(old_path), new_package)
        slots = list(mesh.get_editor_property("materials") or [])
        for slot in slots:
            old_material = path_of(slot.get_editor_property("material_interface"))
            if old_material in material_map.values():
                continue
            if old_material not in material_map:
                raise RuntimeError(f"unmapped mesh material: {old_path} -> {old_material}")
            replacement = unreal.load_asset(material_map[old_material])
            if replacement is None:
                raise RuntimeError(f"missing duplicated material: {material_map[old_material]}")
            slot.set_editor_property("material_interface", replacement)
        mesh.set_editor_property("materials", slots)
        if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save mesh: {path_of(mesh)}")
        if path_of(mesh.get_editor_property("skeleton")) != item["skeleton"]:
            raise RuntimeError(f"skeleton changed: {old_path}")
        actual_materials = [path_of(slot.get_editor_property("material_interface"))
                            for slot in mesh.get_editor_property("materials") or []]
        if not actual_materials or any(path not in material_map.values() for path in actual_materials):
            raise RuntimeError(f"mesh material remap incomplete: {path_of(mesh)}")
        result["meshes"].append({"old": old_path, "new": path_of(mesh),
                                 "skeleton": item["skeleton"], "materials": actual_materials})
    all_copies = result["textures"] + result["materials"] + result["meshes"]
    content_root = Path(unreal.Paths.project_content_dir())
    for item in all_copies:
        target_package = package_name(item["new"])
        if not target_package.startswith("/Game/"):
            raise RuntimeError(f"unexpected target package: {target_package}")
        physical = content_root / (target_package.removeprefix("/Game/") + ".uasset")
        if not physical.is_file() or physical.stat().st_size == 0:
            raise RuntimeError(f"duplicated asset not saved to disk: {physical}")
    result["success"] = True
    return result


def run():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    cases = audit["cases"]
    if {case["label"] for case in cases} != set(DESTINATIONS):
        raise RuntimeError("audit scope does not match pilot destinations")
    report = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "additive_ue_copy_pilot_no_source_deletion", "cases": [], "success": False}
    try:
        for case in cases:
            report["cases"].append(copy_case(case))
        report["success"] = all(case["success"] for case in report["cases"])
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        unreal.log(f"DataMake asset restructure copy pilot: {REPORT}")


run()
