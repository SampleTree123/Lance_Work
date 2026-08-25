"""Import the first male batch motion on the legacy modular M02 skeleton."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


MANIFEST_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\dataset"
    r"\first_batch_required_exports_20260820_v1.json"
)
ACTION_ID = "ACT_M01_BATTLE_DANCE"
SKELETON_PATH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58_Skeleton"
)
DESTINATION = "/Game/DataMake/Animations/CC5/FirstDataBatch/Comparisons/M02_Modular"
ASSET_NAME = "A_DM_M01_BATTLE_DANCE_M02ModularCompare_v001"
PIPELINE_PATH = (
    "/Game/DataMake/Config/Import/FirstDataBatch/"
    "DM_CC5_M02_Modular_MotionCompare_Pipeline_v001"
)
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\first_batch_motions_20260822_v1\m02_modular_compare_import.json"
)
REQUIRED_TRACKS = {
    "root",
    "pelvis",
    "cc_base_pelvis",
    "cc_base_l_forearmtwist01",
    "cc_base_r_forearmtwist01",
    "cc_base_l_thightwist01",
    "cc_base_r_thightwist01",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
action = next(row for row in manifest["actions"] if row["action_id"] == ACTION_ID)
expected = action["expected_export"]
source = Path(expected["local_path"])
if (
    not source.is_file()
    or source.stat().st_size != expected["bytes"]
    or sha256(source) != expected["sha256"]
):
    raise RuntimeError(f"Frozen source validation failed: {source}")

skeleton = unreal.load_asset(SKELETON_PATH)
if not isinstance(skeleton, unreal.Skeleton):
    raise RuntimeError(f"M02 modular skeleton is unavailable: {SKELETON_PATH}")

pipeline = unreal.load_asset(PIPELINE_PATH)
if pipeline is None:
    pipeline = unreal.EditorAssetLibrary.duplicate_asset(
        DEFAULT_PIPELINE, PIPELINE_PATH
    )
if pipeline is None:
    raise RuntimeError(f"Unable to create pipeline: {PIPELINE_PATH}")
mesh = pipeline.get_editor_property("mesh_pipeline")
common = pipeline.get_editor_property(
    "common_skeletal_meshes_and_animations_properties"
)
animation_pipeline = pipeline.get_editor_property("animation_pipeline")
material = pipeline.get_editor_property("material_pipeline")
texture = material.get_editor_property("texture_pipeline")
mesh.set_editor_property("import_skeletal_meshes", False)
mesh.set_editor_property("import_static_meshes", False)
mesh.set_editor_property("create_physics_asset", False)
mesh.set_editor_property("physics_asset", None)
common.set_editor_property("skeleton", skeleton)
common.set_editor_property("try_auto_select_skeleton", False)
common.set_editor_property("import_only_animations", True)
animation_pipeline.set_editor_property("import_animations", True)
material.set_editor_property("import_materials", False)
texture.set_editor_property("import_textures", False)
unreal.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False)

unreal.EditorAssetLibrary.make_directory(DESTINATION)
target_path = f"{DESTINATION}/{ASSET_NAME}"
if unreal.EditorAssetLibrary.does_asset_exist(target_path):
    if not unreal.EditorAssetLibrary.delete_asset(target_path):
        raise RuntimeError(f"Unable to replace comparison animation: {target_path}")

manager = unreal.InterchangeManager.get_interchange_manager_scripted()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
before = set(
    unreal.EditorAssetLibrary.list_assets(
        DESTINATION, recursive=False, include_folder=False
    )
)
source_data = manager.create_source_data(str(source))
parameters = unreal.ImportAssetParameters()
parameters.set_editor_property("is_automated", True)
parameters.set_editor_property("force_show_dialog", False)
parameters.set_editor_property("replace_existing", False)
parameters.set_editor_property("destination_name", ASSET_NAME)
parameters.set_editor_property(
    "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
)
fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
previous = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
if previous != 1:
    unreal.SystemLibrary.execute_console_command(world, f"{fbx_cvar} 1")
try:
    manager.import_asset(DESTINATION, source_data, parameters)
finally:
    if previous != 1:
        unreal.SystemLibrary.execute_console_command(world, f"{fbx_cvar} {previous}")

after = set(
    unreal.EditorAssetLibrary.list_assets(
        DESTINATION, recursive=False, include_folder=False
    )
)
new_paths = sorted(after - before)
assets = [unreal.load_asset(path) for path in new_paths]
animations = [asset for asset in assets if isinstance(asset, unreal.AnimSequence)]
if len(animations) != 1:
    raise RuntimeError(
        f"Expected one comparison AnimSequence; found {len(animations)}: {new_paths}"
    )
animation = animations[0]
if animation.get_name() != ASSET_NAME:
    package = animation.get_path_name().split(".", 1)[0]
    if not unreal.EditorAssetLibrary.rename_asset(package, target_path):
        raise RuntimeError(f"Unable to rename comparison animation: {package}")
    animation = unreal.load_asset(target_path)
if not isinstance(animation, unreal.AnimSequence):
    raise RuntimeError(f"Comparison animation unavailable: {target_path}")

tracks = [str(name) for name in animation.data_model_interface.get_bone_track_names()]
missing = sorted(REQUIRED_TRACKS - set(tracks))
checks = {
    "skeleton_matches": animation.get_editor_property("skeleton") == skeleton,
    "track_count_supported": len(tracks) >= 110,
    "required_tracks_present": not missing,
}
report = {
    "action_id": ACTION_ID,
    "source": str(source),
    "source_sha256": expected["sha256"],
    "animation": animation.get_path_name(),
    "skeleton": animation.get_editor_property("skeleton").get_path_name(),
    "bone_track_count": len(tracks),
    "missing_required_tracks": missing,
    "checks": checks,
    "success": all(checks.values()),
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
if not report["success"]:
    raise RuntimeError(f"M02 modular comparison import failed: {REPORT_PATH}")
unreal.EditorAssetLibrary.save_loaded_asset(animation, only_if_is_dirty=False)
print("DM_M02_MODULAR_COMPARE=" + json.dumps(report, ensure_ascii=False))
