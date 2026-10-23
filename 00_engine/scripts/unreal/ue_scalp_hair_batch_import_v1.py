"""Import the retained scalp-hair batch and split hair meshes into Modules.

The FBX contains a complete CC character reference.  Each case is imported
under its own UE folder; only meshes whose imported material slots identify
Hair/Scalp content are copied to the runtime Modules folder.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


MANIFEST = Path(r"D:\UE\exports\character_creator\scalp_hair_batch_20260924_v1\manifests\cc_export.json")
REPORT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\scalp_hair_batch_20260924_v1\batch_import_report.json")
UE_ROOT = "/Game/Vendor/Reallusion/CC5/ScalpHairBatch/F02_Average"
SKELETON_PATH = "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/F02_Average/Cases/F_BASE/FullReference/CC_MOD_F_BASE_UE58_Skeleton"
DEFAULT_PIPELINE = "/Game/DataMake/Config/Import/DM_Interchange_Split_Pipeline_v1"


def path_name(asset):
    if asset is None:
        return None
    getter = getattr(asset, "get_path_name", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass
    # UE 5.8 exposes SkeletalMaterial entries as structs.  Resolve the
    # embedded material interface before falling back to a diagnostic string.
    try:
        material_interface = asset.get_editor_property("material_interface")
        if material_interface is not None:
            getter = getattr(material_interface, "get_path_name", None)
            if callable(getter):
                return getter()
    except Exception:
        pass
    return str(asset)


def assets_under(root):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    return list(registry.get_assets_by_path(root, recursive=True))


def skeletal_assets_under(root):
    return [data.get_asset() for data in assets_under(root)
            if data.asset_class_path.asset_name == "SkeletalMesh"]


def materials_for(mesh):
    return list(mesh.get_editor_property("materials") or [])


def is_hair_mesh(mesh):
    names = [mesh.get_name()]
    names.extend(path_name(item) or "" for item in materials_for(mesh))
    text = " ".join(names).casefold()
    return "hair" in text or "scalp" in text or "bang" in text or "ponytail" in text or "braid" in text


def mesh_record(mesh):
    skeleton = mesh.get_editor_property("skeleton")
    physics = mesh.get_editor_property("physics_asset")
    return {
        "path": path_name(mesh),
        "name": mesh.get_name(),
        "skeleton": path_name(skeleton),
        "physics_asset": path_name(physics),
        "materials": [path_name(item) for item in materials_for(mesh)],
    }


def configure_pipeline(pipeline, skeleton):
    mesh_pipeline = pipeline.get_editor_property("mesh_pipeline")
    common = pipeline.get_editor_property("common_skeletal_meshes_and_animations_properties")
    animation_pipeline = pipeline.get_editor_property("animation_pipeline")
    material_pipeline = pipeline.get_editor_property("material_pipeline")
    texture_pipeline = material_pipeline.get_editor_property("texture_pipeline")
    mesh_pipeline.set_editor_property("import_skeletal_meshes", True)
    mesh_pipeline.set_editor_property("import_static_meshes", False)
    mesh_pipeline.set_editor_property("combine_skeletal_meshes_behavior", unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE)
    mesh_pipeline.set_editor_property("import_morph_targets", True)
    mesh_pipeline.set_editor_property("create_physics_asset", False)
    mesh_pipeline.set_editor_property("physics_asset", None)
    mesh_pipeline.set_editor_property("skeletal_mesh_import_content_type", unreal.InterchangeSkeletalMeshContentType.ALL)
    common.set_editor_property("skeleton", skeleton)
    common.set_editor_property("try_auto_select_skeleton", False)
    common.set_editor_property("import_only_animations", False)
    animation_pipeline.set_editor_property("import_animations", False)
    material_pipeline.set_editor_property("import_materials", True)
    texture_pipeline.set_editor_property("import_textures", True)
    unreal.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False)


def import_case(preset, skeleton):
    basename = preset["production_output"]["export_basename"]
    stem = basename.removeprefix("CC_HAIR_F_")
    source_fbx = Path(preset["production_output"]["export_root"]) / f"{basename}.fbx"
    if not source_fbx.is_file():
        raise RuntimeError(f"missing FBX: {source_fbx}")
    case_root = f"{UE_ROOT}/{stem}_Interchange"
    full_reference = f"{case_root}/FullReference"
    modules = f"{case_root}/Modules"
    if unreal.EditorAssetLibrary.does_directory_exist(case_root):
        unreal.EditorAssetLibrary.delete_directory(case_root)
        unreal.SystemLibrary.collect_garbage()
    pipeline_path = f"{full_reference}/DM_Interchange_Split_Pipeline_v1"
    pipeline = unreal.EditorAssetLibrary.duplicate_asset(DEFAULT_PIPELINE, pipeline_path)
    if pipeline is None:
        raise RuntimeError(f"unable to create pipeline: {pipeline_path}")
    configure_pipeline(pipeline, skeleton)
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    cvar = "Interchange.FeatureFlags.Import.FBX"
    previous = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if previous != 1:
        unreal.SystemLibrary.execute_console_command(world, f"{cvar} 1")
    try:
        source_data = manager.create_source_data(str(source_fbx))
        if source_data is None:
            raise RuntimeError(f"unable to create source data: {source_fbx}")
        params = unreal.ImportAssetParameters()
        params.set_editor_property("is_automated", True)
        params.set_editor_property("force_show_dialog", False)
        params.set_editor_property("replace_existing", False)
        params.set_editor_property("override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())])
        imported = manager.import_asset(full_reference, source_data, params) or []
    finally:
        if previous != 1:
            unreal.SystemLibrary.execute_console_command(world, f"{cvar} {previous}")
    source_meshes = skeletal_assets_under(full_reference)
    hair_meshes = [mesh for mesh in source_meshes if is_hair_mesh(mesh)]
    if not hair_meshes:
        raise RuntimeError(f"no hair meshes detected under {full_reference}")
    module_records = []
    for mesh in sorted(hair_meshes, key=lambda value: value.get_name().casefold()):
        if path_name(mesh.get_editor_property("skeleton")) != path_name(skeleton):
            raise RuntimeError(f"unexpected skeleton on {mesh.get_path_name()}")
        target = f"{modules}/{mesh.get_name()}"
        duplicated = unreal.EditorAssetLibrary.duplicate_asset(mesh.get_path_name(), target)
        if duplicated is None:
            raise RuntimeError(f"unable to duplicate hair mesh: {mesh.get_path_name()}")
        module_records.append(mesh_record(duplicated))
    unreal.EditorAssetLibrary.save_directory(full_reference, only_if_is_dirty=False, recursive=True)
    unreal.EditorAssetLibrary.save_directory(modules, only_if_is_dirty=False, recursive=True)
    return {
        "preset_id": preset["preset_id"],
        "asset_id": preset.get("scalp_hair_asset_id"),
        "display_name": preset.get("scalp_hair_display_name"),
        "source_fbx": str(source_fbx),
        "full_reference": full_reference,
        "modules": modules,
        "imported_object_count": len(imported),
        "full_reference_mesh_count": len(source_meshes),
        "runtime_hair_mesh_count": len(module_records),
        "runtime_hair_meshes": module_records,
        "success": True,
    }


def run():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError(f"missing skeleton: {SKELETON_PATH}")
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST),
        "ue_root": UE_ROOT,
        "expected_skeleton": SKELETON_PATH,
        "records": [],
        "success": False,
    }
    for preset in manifest.get("presets", []):
        try:
            report["records"].append(import_case(preset, skeleton))
        except Exception as exc:
            report["records"].append({"preset_id": preset.get("preset_id"), "success": False, "error": str(exc)})
    report["success"] = len(report["records"]) == len(manifest.get("presets", [])) and all(item.get("success") for item in report["records"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    unreal.log(f"DataMake scalp hair batch import {'passed' if report['success'] else 'completed with failures'}: {REPORT}")


run()
