"""Validate the assets produced by the M02 Interchange split pilot."""

import json
from pathlib import Path
import unreal


DESTINATION = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot"
)
MASTER_SKELETON = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58_Skeleton."
    "CC_M02_Average_Pilot_UE58_Skeleton"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_split_pilot_validation.json"
)
EXPECTED_MESHES = {
    "back_swept_l",
    "back_swept_r",
    "basic_t_shirts",
    "brows_bushy",
    "canvas_shoes",
    "cc_base_body",
    "cc_base_eye",
    "cc_base_eyeocclusion",
    "cc_base_tear_ducts",
    "cc_base_tearline",
    "cc_base_teeth",
    "cc_base_tongue",
    "chin_curtain_sparse",
    "jeans",
    "lash_low_bushy",
    "lash_up_bushy",
    "mullet_hair",
    "mustache_horseshoe",
    "side_part_bangs",
    "stubble_neck",
}


def object_path(obj):
    return obj.get_path_name() if obj is not None else None


def vector_record(vector):
    return {"x": vector.x, "y": vector.y, "z": vector.z}


subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
records = []

for asset_path in unreal.EditorAssetLibrary.list_assets(
    DESTINATION, recursive=False, include_folder=False
):
    mesh = unreal.load_asset(asset_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        continue

    materials = []
    for skeletal_material in mesh.get_editor_property("materials"):
        material = skeletal_material.get_editor_property("material_interface")
        materials.append(
            {
                "slot": str(skeletal_material.get_editor_property("material_slot_name")),
                "imported_slot": str(
                    skeletal_material.get_editor_property("imported_material_slot_name")
                ),
                "material": object_path(material),
            }
        )

    bounds = mesh.get_bounds()
    morph_names = [str(name) for name in mesh.get_all_morph_target_names()]
    records.append(
        {
            "name": mesh.get_name(),
            "path": mesh.get_path_name(),
            "skeleton": object_path(mesh.get_editor_property("skeleton")),
            "physics_asset": object_path(mesh.get_editor_property("physics_asset")),
            "lod_count": subsystem.get_lod_count(mesh),
            "lod0_vertices": subsystem.get_num_verts(mesh, 0),
            "lod0_sections": subsystem.get_num_sections(mesh, 0),
            "materials": materials,
            "morph_count": len(morph_names),
            "morph_sample": morph_names[:12],
            "bounds": {
                "origin": vector_record(bounds.origin),
                "box_extent": vector_record(bounds.box_extent),
                "sphere_radius": bounds.sphere_radius,
            },
        }
    )

records.sort(key=lambda item: item["name"])
actual_names = {item["name"] for item in records}
report = {
    "destination": DESTINATION,
    "master_skeleton": MASTER_SKELETON,
    "mesh_count": len(records),
    "missing_expected_meshes": sorted(EXPECTED_MESHES - actual_names),
    "unexpected_meshes": sorted(actual_names - EXPECTED_MESHES),
    "skeleton_mismatches": [
        item["name"] for item in records if item["skeleton"] != MASTER_SKELETON
    ],
    "empty_meshes": [
        item["name"] for item in records if item["lod0_vertices"] <= 0
    ],
    "interchange_fbx_flag_after_import": (
        unreal.SystemLibrary.get_console_variable_int_value(
            "Interchange.FeatureFlags.Import.FBX"
        )
    ),
    "meshes": records,
}

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
summary = {
    "report_path": str(REPORT_PATH),
    "mesh_count": report["mesh_count"],
    "missing_expected_meshes": report["missing_expected_meshes"],
    "unexpected_meshes": report["unexpected_meshes"],
    "skeleton_mismatches": report["skeleton_mismatches"],
    "empty_meshes": report["empty_meshes"],
    "interchange_fbx_flag_after_import": report[
        "interchange_fbx_flag_after_import"
    ],
}
print("DM_SPLIT_VALIDATION=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
