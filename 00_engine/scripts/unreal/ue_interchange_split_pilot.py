"""Import the CC5 pilot FBX as separate skeletal meshes using Interchange."""

# RETIRED_EXECUTION_ENTRY_20261001: no current import consumers.
# This script performs asset writes at module top level. Block import as well
# as direct execution; current reimports use the canonical batch manifest and
# /Game/DataMake/Config/Import/DM_Interchange_Split_Pipeline_v1.
raise RuntimeError(
    "Retired Interchange split pilot. Do not rebuild deleted legacy assets; "
    "use the formal wardrobe/hair pipeline and current technical owners."
)


import json
from pathlib import Path
import unreal


SOURCE_FBX = Path(
    r"D:\UE\exports\character_creator\pilot_m02_ue58_v001\CC_M02_Average_Pilot_UE58.Fbx"
)
DESTINATION = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot"
)
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
PILOT_PIPELINE = DESTINATION + "/DM_FBX_Split_Pipeline_v001"
MASTER_SKELETON = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58_Skeleton"
)


def object_record(obj):
    return {
        "name": obj.get_name(),
        "class": obj.get_class().get_name(),
        "path": obj.get_path_name(),
    }


if not SOURCE_FBX.is_file():
    raise FileNotFoundError(str(SOURCE_FBX))

master_skeleton = unreal.load_asset(MASTER_SKELETON)
if master_skeleton is None:
    raise RuntimeError(f"Master skeleton is unavailable: {MASTER_SKELETON}")

existing_skeletal_meshes = []
for asset_path in unreal.EditorAssetLibrary.list_assets(
    DESTINATION, recursive=False, include_folder=False
):
    asset = unreal.load_asset(asset_path)
    if isinstance(asset, unreal.SkeletalMesh):
        existing_skeletal_meshes.append(asset_path)
if existing_skeletal_meshes:
    raise RuntimeError(
        "Split pilot already contains skeletal meshes; refusing to overwrite: "
        + ", ".join(existing_skeletal_meshes)
    )

pipeline = unreal.load_asset(PILOT_PIPELINE)
if pipeline is None:
    pipeline = unreal.EditorAssetLibrary.duplicate_asset(
        DEFAULT_PIPELINE, PILOT_PIPELINE
    )
if pipeline is None:
    raise RuntimeError("Unable to create the project-local Interchange pipeline")

mesh = pipeline.get_editor_property("mesh_pipeline")
common_skeletal = pipeline.get_editor_property(
    "common_skeletal_meshes_and_animations_properties"
)
animation = pipeline.get_editor_property("animation_pipeline")
material = pipeline.get_editor_property("material_pipeline")
texture = material.get_editor_property("texture_pipeline")

mesh.set_editor_property("import_skeletal_meshes", True)
mesh.set_editor_property("import_static_meshes", False)
mesh.set_editor_property(
    "combine_skeletal_meshes_behavior",
    unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE,
)
mesh.set_editor_property("import_morph_targets", True)
mesh.set_editor_property("create_physics_asset", False)
mesh.set_editor_property("physics_asset", None)
mesh.set_editor_property(
    "skeletal_mesh_import_content_type",
    unreal.InterchangeSkeletalMeshContentType.ALL,
)
common_skeletal.set_editor_property("skeleton", master_skeleton)
common_skeletal.set_editor_property("try_auto_select_skeleton", False)
common_skeletal.set_editor_property("import_only_animations", False)
animation.set_editor_property("import_animations", False)
material.set_editor_property("import_materials", False)
texture.set_editor_property("import_textures", False)

if not unreal.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save pipeline asset: {PILOT_PIPELINE}")

manager = unreal.InterchangeManager.get_interchange_manager_scripted()
fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
previous_fbx_flag = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
editor_world = unreal.get_editor_subsystem(
    unreal.UnrealEditorSubsystem
).get_editor_world()

if previous_fbx_flag != 1:
    unreal.SystemLibrary.execute_console_command(editor_world, f"{fbx_cvar} 1")
if unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar) != 1:
    raise RuntimeError(f"Unable to enable {fbx_cvar} for the split pilot")

try:
    source_data = manager.create_source_data(str(SOURCE_FBX))
    if source_data is None:
        raise RuntimeError(f"Unable to create Interchange source data: {SOURCE_FBX}")

    parameters = unreal.ImportAssetParameters()
    parameters.set_editor_property("is_automated", True)
    parameters.set_editor_property("force_show_dialog", False)
    parameters.set_editor_property("replace_existing", False)
    parameters.set_editor_property(
        "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
    )

    unreal.log("DataMake split pilot: starting Interchange import")
    imported_objects = manager.import_asset(DESTINATION, source_data, parameters) or []
    unreal.log(
        f"DataMake split pilot: Interchange returned {len(imported_objects)} object(s)"
    )
finally:
    if previous_fbx_flag != 1:
        unreal.SystemLibrary.execute_console_command(
            editor_world, f"{fbx_cvar} {previous_fbx_flag}"
        )
unreal.EditorAssetLibrary.save_directory(
    DESTINATION, only_if_is_dirty=False, recursive=True
)

all_assets = []
for asset_path in unreal.EditorAssetLibrary.list_assets(
    DESTINATION, recursive=True, include_folder=False
):
    asset = unreal.load_asset(asset_path)
    if asset is not None:
        all_assets.append(object_record(asset))

report = {
    "source_fbx": str(SOURCE_FBX),
    "destination": DESTINATION,
    "pipeline": pipeline.get_path_name(),
    "master_skeleton": master_skeleton.get_path_name(),
    "import_return_objects": [object_record(obj) for obj in imported_objects],
    "destination_assets": all_assets,
}
print("DM_SPLIT_PILOT=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
