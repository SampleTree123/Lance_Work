"""Build masked CC hair material instances from imported hair textures."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_build_scalp_hair_material_instances_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


from datetime import datetime, timezone
import json
from pathlib import Path

import unreal


ROOT = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange"
FULL_REFERENCE = ROOT + "/FullReference"
MODULES = ROOT + "/Modules"
MATERIALS = ROOT + "/RuntimeMaterials"
TEMPLATE = "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/Materials/CC_M02_Average_Pilot_UE58/Hair1_Transparency_LWHQ_Inst"
REPORT_PATH = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\scalp_hair_pilot_20260923_111307_interchange\hair_masked_materials_v1.json")

MATERIAL_SPECS = {
    "Hair14_Runtime": {
        "module": "hair_base",
        "slot": 0,
        # CC exported Hair14 with a metallic/opacity pair and no diffuse map;
        # use the adjacent hair-card diffuse as a neutral color source while
        # preserving Hair14's own opacity mask.
        "diffuse": FULL_REFERENCE + "/Hair13_Transparency_Pbr_Diffuse",
        "opacity": FULL_REFERENCE + "/Hair14_Transparency_Pbr_Opacity",
    },
    "Scalp5_Runtime": {
        "module": "hair_base",
        "slot": 1,
        "diffuse": FULL_REFERENCE + "/Scalp5_Transparency_Tra_Diffuse",
        "opacity": FULL_REFERENCE + "/Scalp5_Transparency_Tra_Opacity",
    },
    "Hair13_Runtime": {
        "module": "side_bangs",
        "slot": 0,
        "diffuse": FULL_REFERENCE + "/Hair13_Transparency_Pbr_Diffuse",
        "opacity": FULL_REFERENCE + "/Hair13_Transparency_Pbr_Opacity",
    },
    "BabyHair2_Runtime": {
        "module": "side_bangs",
        "slot": 1,
        "diffuse": FULL_REFERENCE + "/Hair13_Transparency_Pbr_Diffuse",
        "opacity": FULL_REFERENCE + "/Hair13_Transparency_Pbr_Opacity",
    },
    "Hair12_Runtime": {
        "module": "curly_long_hair",
        "slot": 0,
        "diffuse": FULL_REFERENCE + "/Hair12_Transparency_Pbr_Diffuse",
        "opacity": FULL_REFERENCE + "/Hair12_Transparency_Pbr_Opacity",
    },
    "Hair11_Runtime": {
        "module": "curly_ponytail_back",
        "slot": 0,
        "diffuse": FULL_REFERENCE + "/Hair11_Transparency_Pbr_Diffuse",
        "opacity": FULL_REFERENCE + "/Hair11_Transparency_Pbr_Opacity",
    },
}


def path_name(asset):
    return asset.get_path_name() if asset is not None else None


def set_texture_parameter(material, parameter_name, texture):
    values = list(material.get_editor_property("texture_parameter_values"))
    for item in values:
        info = item.get_editor_property("parameter_info")
        if str(info.get_editor_property("name")) == parameter_name:
            item.set_editor_property("parameter_value", texture)
            material.set_editor_property("texture_parameter_values", values)
            return
    raise RuntimeError(f"Material template has no parameter: {parameter_name}")


def write_report(value):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def run():
    result = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "template": TEMPLATE,
        "parent_material": "/Game/CC_Shaders/HairShader/RL_Hair_Specular",
        "success": False,
    }
    try:
        template = unreal.load_asset(TEMPLATE)
        if template is None:
            raise RuntimeError("Hair material template is unavailable")
        records = []
        for name, spec in MATERIAL_SPECS.items():
            material_path = MATERIALS + "/" + name
            material = unreal.load_asset(material_path)
            if material is None:
                material = unreal.EditorAssetLibrary.duplicate_asset(TEMPLATE, material_path)
            if material is None:
                raise RuntimeError(f"Unable to create material instance: {material_path}")
            diffuse = unreal.load_asset(spec["diffuse"])
            opacity = unreal.load_asset(spec["opacity"])
            if diffuse is None or opacity is None:
                raise RuntimeError(f"Missing imported hair textures for {name}")
            set_texture_parameter(material, "Base Color Map", diffuse)
            set_texture_parameter(material, "Opacity Map", opacity)
            unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)

            mesh_path = MODULES + "/" + spec["module"]
            mesh = unreal.load_asset(mesh_path)
            if mesh is None:
                raise RuntimeError(f"Missing runtime hair mesh: {mesh_path}")
            materials = list(mesh.get_editor_property("materials"))
            slot = spec["slot"]
            if slot >= len(materials):
                raise RuntimeError(f"Material slot {slot} is unavailable on {mesh_path}")
            materials[slot].set_editor_property("material_interface", material)
            mesh.set_editor_property("materials", materials)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
            records.append(
                {
                    "material": path_name(material),
                    "module_mesh": path_name(mesh),
                    "slot": slot,
                    "diffuse": path_name(diffuse),
                    "opacity": path_name(opacity),
                }
            )
        unreal.EditorAssetLibrary.save_directory(MATERIALS, only_if_is_dirty=False, recursive=True)
        unreal.EditorAssetLibrary.save_directory(MODULES, only_if_is_dirty=False, recursive=True)
        result.update({"records": records, "success": True})
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        write_report(result)
    unreal.log("DataMake masked scalp hair materials: " + json.dumps(result, ensure_ascii=False, default=str))
    if not result["success"]:
        unreal.log_error("Masked scalp hair material build failed")


run()
