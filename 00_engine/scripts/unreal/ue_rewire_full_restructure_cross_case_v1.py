"""Remap dependencies shared across old case roots after all copies exist."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1")


def path(asset):
    return asset.get_path_name() if asset is not None else None


def replacement(mapping, value):
    old = path(value)
    if old not in mapping:
        return None
    new = unreal.load_asset(mapping[old])
    if new is None:
        raise RuntimeError(f"mapped asset absent: {mapping[old]}")
    return new


def run():
    plan = json.loads((ROOT / "migration_plan.json").read_text(encoding="utf-8"))
    mapping = {item["old"]: item["new"] for case in plan["cases"] for item in case["assets"]}
    counts = Counter()
    changes = []
    for case in plan["cases"]:
        for item in case["assets"]:
            kind = item["class"]
            if kind not in {"MaterialInstanceConstant", "SkeletalMesh"}:
                continue
            asset = unreal.load_asset(item["new"])
            if asset is None:
                raise RuntimeError(f"copied asset absent: {item['new']}")
            edits = []
            if kind == "MaterialInstanceConstant":
                for field in ("parent", "subsurface_profile"):
                    try:
                        current = asset.get_editor_property(field)
                    except Exception:
                        continue
                    new = replacement(mapping, current)
                    if new is not None:
                        asset.set_editor_property(field, new)
                        edits.append(field)
                parameters = list(asset.get_editor_property("texture_parameter_values") or [])
                for entry in parameters:
                    new = replacement(mapping, entry.get_editor_property("parameter_value"))
                    if new is not None:
                        entry.set_editor_property("parameter_value", new)
                        edits.append("texture_parameter_values")
                if "texture_parameter_values" in edits:
                    asset.set_editor_property("texture_parameter_values", parameters)
            else:
                slots = list(asset.get_editor_property("materials") or [])
                for slot in slots:
                    new = replacement(mapping, slot.get_editor_property("material_interface"))
                    if new is not None:
                        slot.set_editor_property("material_interface", new)
                        edits.append("materials")
                if edits:
                    asset.set_editor_property("materials", slots)
            if edits:
                if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
                    raise RuntimeError(f"save failed: {item['new']}")
                counts[kind] += 1
                changes.append({"asset": item["new"], "fields": sorted(set(edits))})
    target = ROOT / "cross_case_rewire_report.json"
    target.write_text(json.dumps({"schema_version": 1, "counts": dict(counts),
                                  "changes": changes, "success": True}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake cross-case rewire: {dict(counts)}")


run()
