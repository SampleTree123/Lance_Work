"""Reimport hb1-01 materials/textures and copy them to runtime hair meshes."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_repair_scalp_hair_materials_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


from datetime import datetime, timezone
import json
from pathlib import Path

import unreal


SOURCE_FBX = Path(
    r"D:\UE\exports\character_creator\scalp_hair_pilot_20260923_111307\HAIR_HB1_01_F\fbx\CC_HAIR_F_HB1_01.fbx"
)
PIPELINE_PATH = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/FullReference/DM_Interchange_Split_Pipeline_v1"
FULL_REFERENCE = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/FullReference"
MODULES = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\scalp_hair_pilot_20260923_111307_interchange\hair_material_repair_v1.json"
)
HAIR_NAMES = ("hair_base", "side_bangs", "curly_long_hair", "curly_ponytail_back")


def path_name(asset):
    return asset.get_path_name() if asset is not None else None


def materials_for(mesh):
    return [
        item.get_editor_property("material_interface") if item else None
        for item in mesh.get_editor_property("materials")
    ]


def material_paths(mesh):
    return [path_name(item) for item in materials_for(mesh)]


def write_report(payload):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def run():
    payload = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_fbx": str(SOURCE_FBX),
        "pipeline": PIPELINE_PATH,
        "success": False,
    }
    try:
        if not SOURCE_FBX.is_file():
            raise RuntimeError(f"Source FBX is missing: {SOURCE_FBX}")
        pipeline = unreal.load_asset(PIPELINE_PATH)
        if pipeline is None:
            raise RuntimeError(f"Pipeline is missing: {PIPELINE_PATH}")
        material_pipeline = pipeline.get_editor_property("material_pipeline")
        texture_pipeline = material_pipeline.get_editor_property("texture_pipeline")
        material_pipeline.set_editor_property("import_materials", True)
        texture_pipeline.set_editor_property("import_textures", True)
        unreal.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False)

        manager = unreal.InterchangeManager.get_interchange_manager_scripted()
        fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
        previous_fbx_flag = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
        editor_world = unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).get_editor_world()
        if previous_fbx_flag != 1:
            unreal.SystemLibrary.execute_console_command(editor_world, f"{fbx_cvar} 1")
        try:
            source_data = manager.create_source_data(str(SOURCE_FBX))
            if source_data is None:
                raise RuntimeError("Unable to create FBX source data")
            parameters = unreal.ImportAssetParameters()
            parameters.set_editor_property("is_automated", True)
            parameters.set_editor_property("force_show_dialog", False)
            parameters.set_editor_property("replace_existing", True)
            parameters.set_editor_property(
                "override_pipelines", [unreal.SoftObjectPath(PIPELINE_PATH)]
            )
            imported_objects = manager.import_asset(FULL_REFERENCE, source_data, parameters) or []
        finally:
            if previous_fbx_flag != 1:
                unreal.SystemLibrary.execute_console_command(editor_world, f"{fbx_cvar} {previous_fbx_flag}")

        copied = []
        for name in HAIR_NAMES:
            source = unreal.load_asset(f"{FULL_REFERENCE}/{name}")
            target = unreal.load_asset(f"{MODULES}/{name}")
            if source is None or target is None:
                raise RuntimeError(f"Missing reimported hair mesh: {name}")
            source_materials = materials_for(source)
            target.set_editor_property("materials", source.get_editor_property("materials"))
            unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False)
            copied.append(
                {
                    "name": name,
                    "source": path_name(source),
                    "target": path_name(target),
                    "source_materials": [path_name(m) for m in source_materials],
                    "target_materials": material_paths(target),
                }
            )
        unreal.EditorAssetLibrary.save_directory(MODULES, only_if_is_dirty=False, recursive=True)
        payload.update(
            {
                "imported_object_paths": [path_name(obj) for obj in imported_objects],
                "import_materials": True,
                "import_textures": True,
                "copied": copied,
                "success": all(
                    item["target_materials"]
                    and all(
                        path and not path.startswith("/Engine/EngineMaterials/WorldGridMaterial")
                        for path in item["target_materials"]
                    )
                    for item in copied
                ),
            }
        )
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        write_report(payload)
    unreal.log("DataMake scalp hair material repair: " + json.dumps(payload, ensure_ascii=False, default=str))
    if not payload["success"]:
        unreal.log_error("Scalp hair material repair did not pass")


run()
