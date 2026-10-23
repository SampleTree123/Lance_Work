"""Apply the reviewed 40-hair card material plan one hairstyle at a time."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import unreal


ROOT = Path(__file__).resolve().parents[2] / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
PLAN = ROOT / "masked_repair_plan.json"
REPORT_DIR = ROOT / "material_repair_reports"
EXPECTED_PARENT = "/Game/CC_Shaders/HairShader/RL_Hair_Specular.RL_Hair_Specular"


def _path(asset):
    return asset.get_path_name() if asset is not None else None


def _set_texture_parameter(material, name: str, texture) -> None:
    values = list(material.get_editor_property("texture_parameter_values"))
    for value in values:
        info = value.get_editor_property("parameter_info")
        if str(info.get_editor_property("name")) == name:
            value.set_editor_property("parameter_value", texture)
            material.set_editor_property("texture_parameter_values", values)
            return
    raise RuntimeError(f"Masked template has no {name} parameter")


def _report(hair_id: str, result: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / (hair_id + ".json")
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def repair(hair_id: str) -> dict:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    rows = [row for row in plan["rows"] if row["hair_id"] == hair_id]
    if not rows or plan["slot_count"] != 220 or plan["hair_count"] != 40:
        raise RuntimeError(f"Invalid masked material plan or hair ID: {hair_id}")
    result = {"schema_version": 1, "hair_id": hair_id, "at_utc": datetime.now(timezone.utc).isoformat(),
              "expected_slots": len(rows), "success": False, "new_materials": [], "mesh_changes": []}
    try:
        template = unreal.load_asset(plan["template"])
        if not isinstance(template, unreal.MaterialInstanceConstant):
            raise RuntimeError("Previously verified masked hair template is missing")
        if _path(template.get_editor_property("parent")) != EXPECTED_PARENT:
            raise RuntimeError("Masked hair template parent has changed")
        texture_cache = {}
        mesh_cache = {}
        for row in rows:
            for key in ("diffuse", "opacity"):
                path = row[key]
                if path not in texture_cache:
                    texture_cache[path] = unreal.load_asset(path)
                if not isinstance(texture_cache[path], unreal.Texture):
                    raise RuntimeError(f"Hair texture missing: {path}")
            if row["mesh"] not in mesh_cache:
                mesh_cache[row["mesh"]] = unreal.load_asset(row["mesh"])
            if not isinstance(mesh_cache[row["mesh"]], unreal.SkeletalMesh):
                raise RuntimeError(f"Hair mesh missing: {row['mesh']}")
            slots = mesh_cache[row["mesh"]].get_editor_property("materials")
            if row["slot_index"] >= len(slots):
                raise RuntimeError(f"Hair material slot missing: {row['mesh']} / {row['slot_index']}")
            actual = _path(slots[row["slot_index"]].material_interface)
            if actual != row["old_material"] and (actual or "").split(".", 1)[0] != row["new_material"]:
                raise RuntimeError(f"Hair material changed since audit: {row['mesh']} / {row['slot_index']} / {actual}")
        materials = {}
        for row in rows:
            target = row["new_material"]
            if target in materials:
                continue
            material = unreal.load_asset(target)
            created = False
            if material is None:
                material = unreal.EditorAssetLibrary.duplicate_asset(plan["template"], target)
                created = True
            if not isinstance(material, unreal.MaterialInstanceConstant):
                raise RuntimeError(f"Cannot create masked material: {target}")
            if _path(material.get_editor_property("parent")) != EXPECTED_PARENT:
                raise RuntimeError(f"Unexpected masked material parent: {target}")
            _set_texture_parameter(material, "Base Color Map", texture_cache[row["diffuse"]])
            _set_texture_parameter(material, "Opacity Map", texture_cache[row["opacity"]])
            if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
                raise RuntimeError(f"Cannot save masked material: {target}")
            materials[target] = material
            result["new_materials"].append({"path": target, "created": created,
                                             "diffuse": row["diffuse"], "opacity": row["opacity"]})
        for mesh_path, mesh in mesh_cache.items():
            slots = list(mesh.get_editor_property("materials"))
            changes = []
            for row in (item for item in rows if item["mesh"] == mesh_path):
                index = row["slot_index"]
                slots[index].set_editor_property("material_interface", materials[row["new_material"]])
                changes.append({"slot": index, "before": row["old_material"], "after": row["new_material"]})
            mesh.set_editor_property("materials", slots)
            if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError(f"Cannot save hair mesh: {mesh_path}")
            result["mesh_changes"].append({"mesh": mesh_path, "changes": changes})
        result["success"] = True
    except Exception as exc:
        result.update(error_type=type(exc).__name__, error=str(exc))
    path = _report(hair_id, result)
    print("HAIR_MASKED_REPAIR=" + json.dumps({"hair_id": hair_id, "success": result["success"],
                                              "report": str(path)}, ensure_ascii=False))
    if not result["success"]:
        raise RuntimeError(f"Masked hair repair failed; see {path}")
    return result


if __name__ == "__main__" or globals().get("DM_HAIR_REPAIR_ID"):
    repair(globals().get("DM_HAIR_REPAIR_ID"))
