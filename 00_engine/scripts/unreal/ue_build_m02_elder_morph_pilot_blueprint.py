"""Create a modular M02 Blueprint wired to the generated Elder Morph meshes."""

import json
from pathlib import Path

import unreal


SOURCE_BLUEPRINT = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
TARGET_BLUEPRINT = (
    "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/"
    "BP_DM_M02_ElderMorphPilot_v001"
)
GENERATED_ROOT = (
    "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/Generated"
)
ORIGINAL_BODY = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/"
    "_SplitPilot/cc_base_body"
)
MORPH_NAME = "Full_Face_Elder"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_elder_morph_pilot_blueprint_v001.json"
)

COMPONENT_ASSETS = {
    "Body": GENERATED_ROOT + "/SK_DM_M02_ElderMorph_Body_v001",
    "Face_Brows": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_brows_bushy_v001",
    "Face_LashesUpper": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_lash_up_bushy_v001",
    "Face_LashesLower": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_lash_low_bushy_v001",
    "Face_BeardChin": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_chin_curtain_sparse_v001",
    "Face_BeardNeck": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_stubble_neck_v001",
    "Face_Mustache": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_mustache_horseshoe_v001",
    "Hair_Bangs": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_side_part_bangs_v001",
    "Hair_Mullet": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_mullet_hair_v001",
    "Hair_BackLeft": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_back_swept_l_v001",
    "Hair_BackRight": GENERATED_ROOT
    + "/SK_DM_M02_ElderMorph_back_swept_r_v001",
}


def get_data(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)


def get_component(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(
        get_data(handle)
    )


source = unreal.load_asset(SOURCE_BLUEPRINT)
if not isinstance(source, unreal.Blueprint):
    raise RuntimeError(f"Source Blueprint is unavailable: {SOURCE_BLUEPRINT}")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET_BLUEPRINT):
    raise RuntimeError(
        f"Target Blueprint already exists; refusing to overwrite: {TARGET_BLUEPRINT}"
    )

meshes = {}
for component_name, asset_path in COMPONENT_ASSETS.items():
    mesh = unreal.load_asset(asset_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Generated mesh is unavailable: {asset_path}")
    morph_names = {str(name) for name in mesh.get_all_morph_target_names()}
    if MORPH_NAME not in morph_names:
        raise RuntimeError(f"{asset_path} is missing {MORPH_NAME}")
    meshes[component_name] = mesh

original_body = unreal.load_asset(ORIGINAL_BODY)
if not isinstance(original_body, unreal.SkeletalMesh):
    raise RuntimeError(f"Original Body is unavailable: {ORIGINAL_BODY}")
post_process_class = original_body.get_editor_property(
    "post_process_anim_blueprint"
)
meshes["Body"].set_editor_property(
    "post_process_anim_blueprint", post_process_class
)
if not unreal.EditorAssetLibrary.save_loaded_asset(
    meshes["Body"], only_if_is_dirty=False
):
    raise RuntimeError("Unable to persist the generated Body post-process class")

target = unreal.EditorAssetLibrary.duplicate_asset(
    SOURCE_BLUEPRINT, TARGET_BLUEPRINT
)
if not isinstance(target, unreal.Blueprint):
    raise RuntimeError(f"Unable to duplicate Elder Morph Blueprint: {TARGET_BLUEPRINT}")

sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
handles = sds.k2_gather_subobject_data_for_blueprint(target)
updated = {}
for handle in handles:
    component = get_component(handle)
    if not isinstance(component, unreal.SkeletalMeshComponent):
        continue
    component_name = component.get_name().removesuffix("_GEN_VARIABLE")
    replacement = meshes.get(component_name)
    if replacement is None:
        continue
    component.set_skeletal_mesh_asset(replacement)
    updated[component_name] = {
        "component_template": component.get_path_name(),
        "mesh": replacement.get_path_name(),
    }

missing_components = sorted(set(COMPONENT_ASSETS) - set(updated))
if missing_components:
    raise RuntimeError(
        "Unable to find component templates: " + ", ".join(missing_components)
    )

unreal.BlueprintEditorLibrary.compile_blueprint(target)
if not unreal.EditorAssetLibrary.save_loaded_asset(
    target, only_if_is_dirty=False
):
    raise RuntimeError(f"Unable to save Elder Morph Blueprint: {TARGET_BLUEPRINT}")

cdo = unreal.get_default_object(target.generated_class())
cdo_records = []
for component in cdo.get_components_by_class(unreal.SkeletalMeshComponent):
    mesh = component.get_skeletal_mesh_asset()
    morph_names = (
        {str(name) for name in mesh.get_all_morph_target_names()}
        if mesh is not None
        else set()
    )
    cdo_records.append(
        {
            "component": component.get_name(),
            "leader": (
                component.get_editor_property("leader_pose_component").get_name()
                if component.get_editor_property("leader_pose_component")
                is not None
                else None
            ),
            "mesh": mesh.get_path_name() if mesh is not None else None,
            "supports_elder_morph": MORPH_NAME in morph_names,
        }
    )
cdo_records.sort(key=lambda item: item["component"])

report = {
    "blueprint": target.get_path_name(),
    "component_count": len(cdo_records),
    "components": cdo_records,
    "generated_class": target.generated_class().get_path_name(),
    "morph_name": MORPH_NAME,
    "post_process_anim_blueprint": (
        post_process_class.get_path_name() if post_process_class is not None else None
    ),
    "source_blueprint": source.get_path_name(),
    "updated_components": updated,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_ELDER_MORPH_BLUEPRINT="
    + json.dumps(
        {
            "blueprint": report["blueprint"],
            "component_count": report["component_count"],
            "elder_morph_components": [
                item["component"]
                for item in cdo_records
                if item["supports_elder_morph"]
            ],
            "report_path": str(REPORT_PATH),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
