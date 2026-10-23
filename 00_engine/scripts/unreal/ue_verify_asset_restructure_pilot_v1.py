"""Verify copied outfit and hair assets after a fresh Unreal process starts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\asset_restructure_pilot_20260928_v1"
)
COPY_REPORT = ROOT / "ue_copy_report.json"
REPORT = ROOT / "ue_fresh_load_verification.json"


def path_of(asset):
    return asset.get_path_name() if asset is not None else None


def package_of(path):
    return path.rsplit(".", 1)[0]


def run():
    copied = json.loads(COPY_REPORT.read_text(encoding="utf-8"))
    if not copied.get("success"):
        raise RuntimeError("copy pilot report is not successful")
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions()
    for name in (
        "include_hard_package_references",
        "include_soft_package_references",
        "include_game_package_references",
        "include_editor_only_package_references",
    ):
        options.set_editor_property(name, True)
    result = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "fresh_ue_process_structural_verification_visual_review_pending",
              "cases": [], "success": False}
    try:
        for case in copied["cases"]:
            source_root = case["source_root"]
            destination_root = case["destination_root"]
            found = {"label": case["label"], "meshes": [], "materials": [],
                     "texture_count": 0, "source_root_dependencies": [], "success": False}
            for item in case["textures"]:
                asset = unreal.load_asset(item["new"])
                if not isinstance(asset, unreal.Texture2D):
                    raise RuntimeError(f"missing duplicated texture: {item['new']}")
                found["texture_count"] += 1
            for item in case["materials"]:
                material = unreal.load_asset(item["new"])
                if not isinstance(material, unreal.MaterialInstanceConstant):
                    raise RuntimeError(f"missing duplicated material: {item['new']}")
                textures = [path_of(entry.get_editor_property("parameter_value"))
                            for entry in material.get_editor_property("texture_parameter_values") or []]
                if any(path and path.startswith(source_root + "/") for path in textures):
                    raise RuntimeError(f"material still references original case: {item['new']}")
                found["materials"].append({"path": item["new"], "texture_parameters": textures})
            for item in case["meshes"]:
                old_mesh = unreal.load_asset(item["old"])
                new_mesh = unreal.load_asset(item["new"])
                if not isinstance(old_mesh, unreal.SkeletalMesh) or not isinstance(new_mesh, unreal.SkeletalMesh):
                    raise RuntimeError(f"missing source or duplicated mesh: {item['new']}")
                if path_of(new_mesh.get_editor_property("skeleton")) != item["skeleton"]:
                    raise RuntimeError(f"skeleton mismatch: {item['new']}")
                old_slots = list(old_mesh.get_editor_property("materials") or [])
                new_slots = list(new_mesh.get_editor_property("materials") or [])
                if len(old_slots) != len(new_slots):
                    raise RuntimeError(f"material slot count changed: {item['new']}")
                paths = [path_of(slot.get_editor_property("material_interface")) for slot in new_slots]
                if any(not path or not path.startswith(destination_root + "/Materials/") for path in paths):
                    raise RuntimeError(f"mesh material outside curated root: {item['new']}")
                pending = [package_of(item["new"])]
                seen = set()
                while pending:
                    package = pending.pop()
                    if package in seen:
                        continue
                    seen.add(package)
                    for dep in map(str, registry.get_dependencies(package, options) or []):
                        if dep.startswith(source_root + "/"):
                            found["source_root_dependencies"].append(dep)
                        if dep.startswith(destination_root + "/"):
                            pending.append(dep)
                found["meshes"].append({"path": item["new"], "skeleton": item["skeleton"],
                                        "material_slot_count": len(paths), "dependency_count": len(seen)})
            found["source_root_dependencies"] = sorted(set(found["source_root_dependencies"]))
            if found["source_root_dependencies"]:
                raise RuntimeError(f"new assets still depend on original case: {found['source_root_dependencies']}")
            found["success"] = True
            result["cases"].append(found)
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        unreal.log(f"DataMake asset restructure fresh-load verification: {REPORT}")


run()
