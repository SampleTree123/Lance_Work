"""Build one Body-only Elder Morph Target from the CC5 snapshot pair."""

import json
from pathlib import Path

import unreal


YOUNG_BODY = (
    "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/Young/"
    "cc_base_body"
)
ELDER_BODY = (
    "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/Elder/"
    "cc_base_body"
)
TARGET_BODY = (
    "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/Generated/"
    "SK_DM_M02_ElderMorph_Body_v001"
)
MORPH_NAME = "Full_Face_Elder"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_elder_body_morph_build_v001.json"
)


young = unreal.load_asset(YOUNG_BODY)
elder = unreal.load_asset(ELDER_BODY)
if not isinstance(young, unreal.SkeletalMesh):
    raise RuntimeError(f"Young Body is unavailable: {YOUNG_BODY}")
if not isinstance(elder, unreal.SkeletalMesh):
    raise RuntimeError(f"Elder Body is unavailable: {ELDER_BODY}")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET_BODY):
    raise RuntimeError(f"Target Body already exists; refusing to overwrite: {TARGET_BODY}")

target = unreal.EditorAssetLibrary.duplicate_asset(YOUNG_BODY, TARGET_BODY)
if not isinstance(target, unreal.SkeletalMesh):
    raise RuntimeError(f"Unable to duplicate the young Body: {TARGET_BODY}")

dynamic_mesh = unreal.DynamicMesh()
read_options = unreal.GeometryScriptCopyMeshFromAssetOptions()
read_options.set_editor_property("apply_build_settings", False)
read_options.set_editor_property("ignore_remove_degenerates", True)
read_options.set_editor_property("request_tangents", True)
read_options.set_editor_property("use_build_scale", True)
read_lod = unreal.GeometryScriptMeshReadLOD()
read_lod.set_editor_property("lod_index", 0)
read_lod.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)

dynamic_mesh, read_outcome = (
    unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        elder,
        dynamic_mesh,
        read_options,
        read_lod,
    )
)
if read_outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError(f"Unable to extract Elder Body geometry: {read_outcome}")

write_options = unreal.GeometryScriptCopyMorphTargetToAssetOptions()
write_options.set_editor_property("copy_normals", False)
write_options.set_editor_property("defer_mesh_post_edit_change", False)
write_options.set_editor_property("emit_transaction", True)
write_options.set_editor_property("overwrite_existing_target", False)
write_lod = unreal.GeometryScriptMeshWriteLOD()
write_lod.set_editor_property("lod_index", 0)
write_lod.set_editor_property("write_hi_res_source", False)

dynamic_mesh, write_outcome = (
    unreal.GeometryScript_AssetUtils.copy_morph_target_to_skeletal_mesh(
        dynamic_mesh,
        target,
        MORPH_NAME,
        write_options,
        write_lod,
    )
)
if write_outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError(f"Unable to write Elder Body Morph Target: {write_outcome}")

if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save generated Body: {TARGET_BODY}")

morph_names = sorted(str(name) for name in target.get_all_morph_target_names())
if MORPH_NAME not in morph_names:
    raise RuntimeError(f"Generated Body is missing {MORPH_NAME}")

subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
report = {
    "elder_body": elder.get_path_name(),
    "elder_lod0_vertices": subsystem.get_num_verts(elder, 0),
    "morph_count": len(morph_names),
    "morph_name": MORPH_NAME,
    "morph_present": MORPH_NAME in morph_names,
    "read_lod": str(read_lod),
    "read_options": str(read_options),
    "read_outcome": str(read_outcome),
    "target_body": target.get_path_name(),
    "target_lod0_vertices": subsystem.get_num_verts(target, 0),
    "write_lod": str(write_lod),
    "write_options": str(write_options),
    "write_outcome": str(write_outcome),
    "young_body": young.get_path_name(),
    "young_lod0_vertices": subsystem.get_num_verts(young, 0),
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("DM_ELDER_BODY_MORPH=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
