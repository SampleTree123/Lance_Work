"""Import one CC scalp-hair pilot into the UE5 female base skeleton.

This is intentionally a one-case pilot.  The exported FBX contains the CC body
and hair nodes; the complete import is retained under FullReference, while only
the four hair nodes are duplicated into the runtime Modules directory.  No new
skeleton or physics asset is created for the runtime meshes.
"""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_hair_pilot_import_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


import json
from pathlib import Path

import unreal


SOURCE_FBX = Path(
    r"D:\UE\exports\character_creator\scalp_hair_pilot_20260923_111307\HAIR_HB1_01_F\fbx\CC_HAIR_F_HB1_01.fbx"
)
SOURCE_JSON = Path(
    r"D:\UE\exports\character_creator\scalp_hair_pilot_20260923_111307\HAIR_HB1_01_F\fbx\CC_HAIR_F_HB1_01.json"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\scalp_hair_pilot_20260923_111307_interchange\ue_import_report.json"
)
FULL_REFERENCE = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/FullReference"
MODULES = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules"
SKELETON_PATH = (
    "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/F02_Average/Cases/"
    "F_BASE/FullReference/CC_MOD_F_BASE_UE58_Skeleton"
)
# The stock virtual pipeline is not registered by the UE commandlet in this
# project.  Reuse the same discoverable split pipeline that powers the F02
# modular outfit imports, then apply the hair-specific settings below.
DEFAULT_PIPELINE = (
    "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/F02_Average/Cases/"
    "F_BIKINI_LAYERED/Modules/DM_Interchange_Split_Pipeline_v1"
)
HAIR_TOKENS = ("hair_base", "side_bangs", "curly_long_hair", "curly_ponytail_back")


def path_name(asset):
    return asset.get_path_name() if asset is not None else None


def write_report(payload):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assets_under(root):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    return list(registry.get_assets_by_path(root, recursive=True))


def skeletal_assets_under(root):
    return [
        data.get_asset()
        for data in assets_under(root)
        if data.asset_class_path.asset_name == "SkeletalMesh"
    ]


def mesh_record(mesh):
    skeleton = mesh.get_editor_property("skeleton")
    physics = mesh.get_editor_property("physics_asset")
    skeleton_path = path_name(skeleton)
    # UE object paths include the object name after a dot, while the manifest
    # stores the package path.  Keep the report comparable to the manifest.
    skeleton_package = skeleton_path.rsplit(".", 1)[0] if skeleton_path and "." in skeleton_path else skeleton_path
    return {
        "path": path_name(mesh),
        "name": mesh.get_name(),
        "skeleton": skeleton_package,
        "physics_asset": path_name(physics),
        "material_slots": len(mesh.get_editor_property("materials")),
    }


def import_reference():
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError("Female base skeleton not found: " + SKELETON_PATH)
    if not SOURCE_FBX.is_file():
        raise RuntimeError("Pilot FBX not found: " + str(SOURCE_FBX))

    # Preserve a completed import when the commandlet is rerun just for
    # validation.  This avoids re-parsing the 148 MB FBX and makes the pilot
    # report deterministic after an interrupted editor session.
    if len(skeletal_assets_under(FULL_REFERENCE)) >= 10:
        return skeleton, skeletal_assets_under(FULL_REFERENCE)

    # This pilot path is disposable while the importer is being validated.
    # Remove a prior partial commandlet import so a retry is deterministic.
    pilot_root = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange"
    if unreal.EditorAssetLibrary.does_directory_exist(pilot_root):
        if not unreal.EditorAssetLibrary.delete_directory(pilot_root):
            raise RuntimeError("Unable to clean prior pilot assets: " + pilot_root)
        unreal.SystemLibrary.collect_garbage()

    pipeline_path = FULL_REFERENCE + "/DM_Interchange_Split_Pipeline_v1"
    pipeline = unreal.EditorAssetLibrary.duplicate_asset(DEFAULT_PIPELINE, pipeline_path)
    if pipeline is None:
        raise RuntimeError("Unable to create pilot Interchange pipeline")
    mesh_pipeline = pipeline.get_editor_property("mesh_pipeline")
    common = pipeline.get_editor_property("common_skeletal_meshes_and_animations_properties")
    animation_pipeline = pipeline.get_editor_property("animation_pipeline")
    mesh_pipeline.set_editor_property("import_skeletal_meshes", True)
    mesh_pipeline.set_editor_property("import_static_meshes", False)
    mesh_pipeline.set_editor_property(
        "combine_skeletal_meshes_behavior",
        unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE,
    )
    mesh_pipeline.set_editor_property("import_morph_targets", True)
    mesh_pipeline.set_editor_property("create_physics_asset", False)
    mesh_pipeline.set_editor_property("physics_asset", None)
    mesh_pipeline.set_editor_property(
        "skeletal_mesh_import_content_type", unreal.InterchangeSkeletalMeshContentType.ALL
    )
    common.set_editor_property("skeleton", skeleton)
    common.set_editor_property("try_auto_select_skeleton", False)
    common.set_editor_property("import_only_animations", False)
    animation_pipeline.set_editor_property("import_animations", False)
    unreal.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False)

    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    # UE 5.8 keeps the FBX Interchange translator behind a feature flag in
    # commandlets.  The normal editor enables this as part of the FBX import
    # UI, so do the same for the automated path and restore the prior value.
    fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
    previous_fbx_flag = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
    editor_world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    if previous_fbx_flag != 1:
        unreal.SystemLibrary.execute_console_command(editor_world, f"{fbx_cvar} 1")
    try:
        if unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar) != 1:
            raise RuntimeError("Unable to enable " + fbx_cvar)
        source_data = manager.create_source_data(str(SOURCE_FBX))
        if source_data is None:
            raise RuntimeError("Unable to create Interchange source data")
        parameters = unreal.ImportAssetParameters()
        parameters.set_editor_property("is_automated", True)
        parameters.set_editor_property("force_show_dialog", False)
        parameters.set_editor_property("replace_existing", False)
        parameters.set_editor_property("override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())])
        imported_objects = manager.import_asset(FULL_REFERENCE, source_data, parameters) or []
    finally:
        if previous_fbx_flag != 1:
            unreal.SystemLibrary.execute_console_command(editor_world, f"{fbx_cvar} {previous_fbx_flag}")
    unreal.EditorAssetLibrary.save_directory(FULL_REFERENCE, only_if_is_dirty=False, recursive=True)
    return skeleton, imported_objects


def duplicate_hair_modules(skeleton):
    source_meshes = skeletal_assets_under(FULL_REFERENCE)
    selected = [
        mesh for mesh in source_meshes
        if any(token in mesh.get_name().casefold() for token in HAIR_TOKENS)
    ]
    if len(selected) < len(HAIR_TOKENS):
        raise RuntimeError(
            "Expected four hair skeletal meshes under FullReference; found "
            + json.dumps([mesh.get_name() for mesh in source_meshes], ensure_ascii=False)
        )
    selected = sorted(selected, key=lambda mesh: mesh.get_name().casefold())
    modules = []
    for mesh in selected:
        if path_name(mesh.get_editor_property("skeleton")) != path_name(skeleton):
            raise RuntimeError("Imported hair mesh uses unexpected skeleton: " + path_name(mesh))
        target = MODULES + "/" + mesh.get_name()
        duplicated = unreal.load_asset(target)
        if duplicated is None:
            duplicated = unreal.EditorAssetLibrary.duplicate_asset(mesh.get_path_name(), target)
        if duplicated is None:
            raise RuntimeError("Unable to duplicate hair mesh to Modules: " + mesh.get_path_name())
        modules.append(duplicated)
    unreal.EditorAssetLibrary.save_directory(MODULES, only_if_is_dirty=False, recursive=True)
    return selected, modules


def run():
    payload = {
        "schema_version": 1,
        "source_fbx": str(SOURCE_FBX),
        "source_json": str(SOURCE_JSON),
        "full_reference": FULL_REFERENCE,
        "modules": MODULES,
        "expected_skeleton": SKELETON_PATH,
        "success": False,
    }
    try:
        skeleton, imported_objects = import_reference()
        source_meshes, modules = duplicate_hair_modules(skeleton)
        source_records = [mesh_record(mesh) for mesh in skeletal_assets_under(FULL_REFERENCE)]
        module_records = [mesh_record(mesh) for mesh in skeletal_assets_under(MODULES)]
        mismatches = [
            record for record in module_records
            if record["skeleton"] != SKELETON_PATH or record["physics_asset"] is not None
        ]
        payload.update(
            {
                "imported_object_paths": [path_name(obj) for obj in imported_objects],
                "full_reference_skeletal_meshes": source_records,
                "module_skeletal_meshes": module_records,
                "module_mesh_count": len(module_records),
                "skeleton_mismatches_or_physics": mismatches,
                "success": len(module_records) == 4 and not mismatches,
            }
        )
        if not payload["success"]:
            raise RuntimeError("Hair module structural validation failed")
        unreal.log("DataMake scalp hair pilot import passed: " + str(REPORT_PATH))
    except Exception as exc:
        payload["error"] = str(exc)
        unreal.log_error("DataMake scalp hair pilot import failed: " + str(exc))
    finally:
        write_report(payload)


# The Python commandlet executes this file after the editor subsystems have
# been initialized, so running directly keeps the pilot usable both in a
# commandlet and from the editor's Execute Python action.
run()



