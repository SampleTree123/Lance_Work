"""Reuse the validated FullReference materials on split skeletal meshes."""

import json
from pathlib import Path
import unreal


DESTINATION = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot"
)
FULL_REFERENCE_MESH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58"
)
MASTER_PHYSICS_ASSET = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/Rigs/"
    "CC_M02_Average_Pilot_UE58_PhysicsAsset"
)
BODY_MESH_NAME = "cc_base_body"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_split_pilot_material_assignment.json"
)


def material_keys(skeletal_material):
    return {
        str(skeletal_material.get_editor_property("material_slot_name")),
        str(skeletal_material.get_editor_property("imported_material_slot_name")),
    }


full_mesh = unreal.load_asset(FULL_REFERENCE_MESH)
physics_asset = unreal.load_asset(MASTER_PHYSICS_ASSET)
if not isinstance(full_mesh, unreal.SkeletalMesh):
    raise RuntimeError(f"FullReference mesh is unavailable: {FULL_REFERENCE_MESH}")
if not isinstance(physics_asset, unreal.PhysicsAsset):
    raise RuntimeError(f"Master physics asset is unavailable: {MASTER_PHYSICS_ASSET}")

source_materials = {}
for skeletal_material in full_mesh.get_editor_property("materials"):
    material = skeletal_material.get_editor_property("material_interface")
    if material is None:
        continue
    for key in material_keys(skeletal_material):
        if key and key != "None":
            source_materials[key] = material

targets = []
unmatched = []
for asset_path in unreal.EditorAssetLibrary.list_assets(
    DESTINATION, recursive=False, include_folder=False
):
    mesh = unreal.load_asset(asset_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        continue

    assignments = []
    for index, skeletal_material in enumerate(mesh.get_editor_property("materials")):
        source_material = None
        matched_key = None
        for key in material_keys(skeletal_material):
            if key in source_materials:
                source_material = source_materials[key]
                matched_key = key
                break
        if source_material is None:
            unmatched.append(
                {
                    "mesh": mesh.get_name(),
                    "index": index,
                    "keys": sorted(material_keys(skeletal_material)),
                }
            )
        else:
            assignments.append((index, source_material, matched_key))
    targets.append((mesh, assignments))

if unmatched:
    raise RuntimeError("Unmatched split material slots: " + json.dumps(unmatched))

records = []
for mesh, assignments in targets:
    materials = list(mesh.get_editor_property("materials"))
    assigned = []
    for index, source_material, matched_key in assignments:
        materials[index].set_editor_property("material_interface", source_material)
        assigned.append(
            {
                "slot_index": index,
                "matched_key": matched_key,
                "material": source_material.get_path_name(),
            }
        )
    mesh.set_editor_property("materials", materials)
    if mesh.get_name() == BODY_MESH_NAME:
        mesh.set_editor_property("physics_asset", physics_asset)
    elif mesh.get_editor_property("physics_asset") is not None:
        mesh.set_editor_property("physics_asset", None)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError(f"Unable to save split mesh: {mesh.get_path_name()}")
    records.append(
        {
            "mesh": mesh.get_path_name(),
            "assignments": assigned,
            "physics_asset": (
                mesh.get_editor_property("physics_asset").get_path_name()
                if mesh.get_editor_property("physics_asset") is not None
                else None
            ),
        }
    )

report = {
    "full_reference_mesh": full_mesh.get_path_name(),
    "source_material_key_count": len(source_materials),
    "mesh_count": len(records),
    "assigned_slot_count": sum(len(item["assignments"]) for item in records),
    "unmatched": unmatched,
    "meshes": records,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_SPLIT_MATERIALS="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "mesh_count": report["mesh_count"],
            "assigned_slot_count": report["assigned_slot_count"],
            "unmatched_count": len(unmatched),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
