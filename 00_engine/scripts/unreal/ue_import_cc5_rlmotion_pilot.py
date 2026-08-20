"""Import two CC5 motion-only FBX files onto the existing M02 UE5 skeleton."""

import json
from pathlib import Path

import unreal


SOURCES = (
    (
        Path(
            r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge"
            r"\artifacts\rlmotion_fbx_export_20260804_05\audience_f"
            r"\Audience_F_01_UE5_ASCII_Patched.fbx"
        ),
        "A_CC_Audience_F_01_Pilot",
    ),
    (
        Path(
            r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge"
            r"\artifacts\rlmotion_fbx_export_20260804_05\walk_wander_m"
            r"\Walk_Wander_M_UE5_ASCII_Patched.fbx"
        ),
        "A_CC_Walk_Wander_M_Pilot",
    ),
)
DESTINATION = "/Game/Vendor/Reallusion/CC5/Animations/Pilot"
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
PILOT_PIPELINE = "/Game/DataMake/Config/Import/DM_CC5_Animation_Pipeline_v001"
MASTER_SKELETON = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58_Skeleton"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\cc5_rlmotion_pilot_import_20260804.json"
)


def object_record(obj):
    return {
        "class": obj.get_class().get_name(),
        "name": obj.get_name(),
        "path": obj.get_path_name(),
    }


def safe_call(obj, method_name):
    try:
        return getattr(obj, method_name)()
    except Exception as exc:
        return {"error": str(exc)}


def safe_property(obj, property_name):
    try:
        value = obj.get_editor_property(property_name)
        if isinstance(value, unreal.Object):
            return value.get_path_name()
        return str(value)
    except Exception as exc:
        return {"error": str(exc)}


def animation_record(animation_asset):
    imported_skeleton = animation_asset.get_editor_property("skeleton")
    return {
        **object_record(animation_asset),
        "skeleton": (
            imported_skeleton.get_path_name()
            if imported_skeleton is not None
            else None
        ),
        "play_length_seconds": safe_call(
            animation_asset, "get_play_length"
        ),
        "rate_scale": safe_property(animation_asset, "rate_scale"),
    }


for source_path, _ in SOURCES:
    if not source_path.is_file():
        raise FileNotFoundError(str(source_path))

master_skeleton = unreal.load_asset(MASTER_SKELETON)
if master_skeleton is None:
    raise RuntimeError(f"Master skeleton is unavailable: {MASTER_SKELETON}")

unreal.EditorAssetLibrary.make_directory(DESTINATION)
unreal.EditorAssetLibrary.make_directory("/Game/DataMake/Config/Import")

pipeline = unreal.load_asset(PILOT_PIPELINE)
if pipeline is None:
    pipeline = unreal.EditorAssetLibrary.duplicate_asset(
        DEFAULT_PIPELINE, PILOT_PIPELINE
    )
if pipeline is None:
    raise RuntimeError("Unable to create the CC5 animation import pipeline")

mesh = pipeline.get_editor_property("mesh_pipeline")
common_skeletal = pipeline.get_editor_property(
    "common_skeletal_meshes_and_animations_properties"
)
animation = pipeline.get_editor_property("animation_pipeline")
material = pipeline.get_editor_property("material_pipeline")
texture = material.get_editor_property("texture_pipeline")

mesh.set_editor_property("import_skeletal_meshes", False)
mesh.set_editor_property("import_static_meshes", False)
mesh.set_editor_property("create_physics_asset", False)
mesh.set_editor_property("physics_asset", None)
common_skeletal.set_editor_property("skeleton", master_skeleton)
common_skeletal.set_editor_property("try_auto_select_skeleton", False)
common_skeletal.set_editor_property("import_only_animations", True)
animation.set_editor_property("import_animations", True)
material.set_editor_property("import_materials", False)
texture.set_editor_property("import_textures", False)

if not unreal.EditorAssetLibrary.save_loaded_asset(
    pipeline, only_if_is_dirty=False
):
    raise RuntimeError(f"Unable to save pipeline asset: {PILOT_PIPELINE}")

manager = unreal.InterchangeManager.get_interchange_manager_scripted()
editor_world = unreal.get_editor_subsystem(
    unreal.UnrealEditorSubsystem
).get_editor_world()


def import_with_temporary_fbx_interchange(source_data, parameters):
    fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
    previous_value = unreal.SystemLibrary.get_console_variable_int_value(
        fbx_cvar
    )
    if previous_value != 1:
        unreal.SystemLibrary.execute_console_command(
            editor_world, f"{fbx_cvar} 1"
        )
    try:
        if unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar) != 1:
            raise RuntimeError(f"Unable to enable {fbx_cvar}")
        return manager.import_asset(
            DESTINATION, source_data, parameters
        ) or []
    finally:
        if previous_value != 1:
            unreal.SystemLibrary.execute_console_command(
                editor_world, f"{fbx_cvar} {previous_value}"
            )


import_results = []
for source_path, desired_name in SOURCES:
    desired_path = f"{DESTINATION}/{desired_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(desired_path):
        existing_asset = unreal.load_asset(desired_path)
        if not isinstance(existing_asset, unreal.AnimSequence):
            raise RuntimeError(
                f"Existing pilot asset is not an AnimSequence: {desired_path}"
            )
        if existing_asset.get_editor_property("skeleton") != master_skeleton:
            raise RuntimeError(
                f"Existing pilot animation has the wrong skeleton: {desired_path}"
            )
        import_results.append(
            {
                "source_fbx": str(source_path),
                "returned_objects": [],
                "new_asset_paths": [],
                "reused_existing": True,
                "animation": animation_record(existing_asset),
            }
        )
        continue
    before_paths = set(
        unreal.EditorAssetLibrary.list_assets(
            DESTINATION, recursive=False, include_folder=False
        )
    )
    source_data = manager.create_source_data(str(source_path))
    if source_data is None:
        raise RuntimeError(f"Unable to create source data: {source_path}")

    parameters = unreal.ImportAssetParameters()
    parameters.set_editor_property("is_automated", True)
    parameters.set_editor_property("force_show_dialog", False)
    parameters.set_editor_property("replace_existing", False)
    parameters.set_editor_property("destination_name", desired_name)
    parameters.set_editor_property(
        "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
    )
    returned_objects = import_with_temporary_fbx_interchange(
        source_data, parameters
    )
    after_paths = set(
        unreal.EditorAssetLibrary.list_assets(
            DESTINATION, recursive=False, include_folder=False
        )
    )
    new_paths = sorted(after_paths - before_paths)
    animation_assets = []
    for asset_path in new_paths:
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, unreal.AnimSequence):
            animation_assets.append(asset)
    if len(animation_assets) != 1:
        raise RuntimeError(
            f"Expected one AnimSequence from {source_path}, found "
            f"{len(animation_assets)}; new assets={new_paths}"
        )
    animation_asset = animation_assets[0]
    if animation_asset.get_name() != desired_name:
        old_path = animation_asset.get_path_name().split(".", 1)[0]
        if not unreal.EditorAssetLibrary.rename_asset(old_path, desired_path):
            raise RuntimeError(
                f"Unable to rename imported animation {old_path} to {desired_path}"
            )
        animation_asset = unreal.load_asset(desired_path)
    if animation_asset is None:
        raise RuntimeError(f"Imported animation is unavailable: {desired_path}")

    imported_skeleton = animation_asset.get_editor_property("skeleton")
    if imported_skeleton != master_skeleton:
        raise RuntimeError(
            f"Animation skeleton mismatch for {desired_path}: "
            f"{imported_skeleton} != {master_skeleton}"
        )
    import_results.append(
        {
            "source_fbx": str(source_path),
            "returned_objects": [
                object_record(obj) for obj in returned_objects
            ],
            "new_asset_paths": new_paths,
            "reused_existing": False,
            "animation": animation_record(animation_asset),
        }
    )

unreal.EditorAssetLibrary.save_directory(
    DESTINATION, only_if_is_dirty=False, recursive=True
)
report = {
    "destination": DESTINATION,
    "imports": import_results,
    "master_skeleton": master_skeleton.get_path_name(),
    "pipeline": pipeline.get_path_name(),
    "success": True,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
    encoding="utf-8",
)
print("DM_CC5_MOTION_IMPORT=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
