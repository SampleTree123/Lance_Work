"""Resume-safe batched UE copy of the audited wardrobe/hair runtime subset.

Set max_cases in run_config.json. A case is committed to progress only after its
assets have been saved and direct runtime references remapped. Source is untouched.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1")
PLAN = ROOT / "migration_plan.json"
CONFIG = ROOT / "run_config.json"
PROGRESS = ROOT / "copy_progress.json"


def path(asset):
    return asset.get_path_name() if asset is not None else None


def save_json(target, data):
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def copy_asset(item):
    old, new = item["old"], item["new"]
    if unreal.EditorAssetLibrary.does_asset_exist(new):
        asset = unreal.load_asset(new)
        source = unreal.load_asset(old)
        if asset is None or source is None or asset.get_class() != source.get_class():
            raise RuntimeError(f"occupied destination has wrong class: {new}")
    else:
        asset = unreal.EditorAssetLibrary.duplicate_asset(old, new)
    if asset is None:
        raise RuntimeError(f"duplicate failed: {old} -> {new}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {new}")
    return asset


def replace_property_reference(asset, property_name, mapping):
    try:
        current = asset.get_editor_property(property_name)
    except Exception:
        return False
    old = path(current)
    if old not in mapping:
        return False
    replacement = unreal.load_asset(mapping[old])
    if replacement is None:
        raise RuntimeError(f"missing mapped reference {mapping[old]}")
    asset.set_editor_property(property_name, replacement)
    return True


def copy_case(case):
    by_class = {}
    for item in case["assets"]:
        by_class.setdefault(item["class"], []).append(item)
    mapping = {item["old"]: item["new"] for item in case["assets"]}
    for kind in ("Texture2D", "SubsurfaceProfile"):
        for item in by_class.get(kind, []):
            copy_asset(item)
    for item in by_class.get("MaterialInstanceConstant", []):
        material = copy_asset(item)
        parameters = list(material.get_editor_property("texture_parameter_values") or [])
        for parameter in parameters:
            current = path(parameter.get_editor_property("parameter_value"))
            if current in mapping:
                replacement = unreal.load_asset(mapping[current])
                if replacement is None:
                    raise RuntimeError(f"missing copied texture {mapping[current]}")
                parameter.set_editor_property("parameter_value", replacement)
        material.set_editor_property("texture_parameter_values", parameters)
        replace_property_reference(material, "parent", mapping)
        replace_property_reference(material, "subsurface_profile", mapping)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError(f"save failed: {item['new']}")
    skeletons = {}
    for item in by_class.get("SkeletalMesh", []):
        source = unreal.load_asset(item["old"])
        if not isinstance(source, unreal.SkeletalMesh):
            raise RuntimeError(f"source mesh missing: {item['old']}")
        expected_skeleton = path(source.get_editor_property("skeleton"))
        mesh = copy_asset(item)
        slots = list(mesh.get_editor_property("materials") or [])
        for slot in slots:
            current = path(slot.get_editor_property("material_interface"))
            if current in mapping:
                replacement = unreal.load_asset(mapping[current])
                if replacement is None:
                    raise RuntimeError(f"missing mapped material {mapping[current]}")
                slot.set_editor_property("material_interface", replacement)
            elif current and current.startswith(case["old_root"] + "/"):
                raise RuntimeError(f"unmapped local mesh material: {current}")
        mesh.set_editor_property("materials", slots)
        if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError(f"save failed: {item['new']}")
        if path(mesh.get_editor_property("skeleton")) != expected_skeleton:
            raise RuntimeError(f"skeleton changed: {item['new']}")
        skeletons[item["new"]] = expected_skeleton
    content = Path(unreal.Paths.project_content_dir())
    for item in case["assets"]:
        package = item["new"].rsplit(".", 1)[0]
        physical = content / (package.removeprefix("/Game/") + ".uasset")
        if not physical.is_file() or physical.stat().st_size == 0:
            raise RuntimeError(f"missing saved package: {physical}")
    return {"kind": case["kind"], "id": case["id"], "new_root": case["new_root"],
            "asset_count": len(case["assets"]), "skeletons": skeletons}


def run():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    max_cases = int(config["max_cases"])
    if max_cases < 1 or max_cases > 100:
        raise RuntimeError("max_cases must be between 1 and 100")
    progress = json.loads(PROGRESS.read_text(encoding="utf-8")) if PROGRESS.exists() else {
        "schema_version": 1, "completed": [], "failed": None}
    done = {row["id"] for row in progress["completed"]}
    pending = [case for case in plan["cases"] if case["id"] not in done]
    if config.get("case_ids"):
        requested = set(config["case_ids"])
        unknown = requested - {case["id"] for case in plan["cases"]}
        if unknown:
            raise RuntimeError(f"unknown case IDs: {sorted(unknown)}")
        pending = [case for case in pending if case["id"] in requested]
    unreal.log(f"DataMake full restructure: {len(done)} complete, {len(pending)} pending, batch {max_cases}")
    progress["failed"] = None
    for case in pending[:max_cases]:
        try:
            result = copy_case(case)
        except Exception as exc:
            progress["failed"] = {"id": case["id"], "error": str(exc),
                                  "at_utc": datetime.now(timezone.utc).isoformat()}
            save_json(PROGRESS, progress)
            raise
        progress["completed"].append(result)
        save_json(PROGRESS, progress)
        unreal.log(f"DataMake copied {len(progress['completed'])}/{len(plan['cases'])}: {case['id']} ({len(case['assets'])} assets)")
    unreal.log(f"DataMake full restructure batch complete: {len(progress['completed'])}/{len(plan['cases'])}")


run()
