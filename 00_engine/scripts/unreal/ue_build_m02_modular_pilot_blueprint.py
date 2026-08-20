"""Build a DataMake Blueprint that assembles the M02 split mesh pilot."""

import json
from pathlib import Path
import unreal


SOURCE_FOLDER = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot"
)
FULL_REFERENCE_MESH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58"
)
BLUEPRINT_FOLDER = "/Game/DataMake/Characters/M02_Average"
BLUEPRINT_NAME = "BP_DM_M02_ModularPilot_v001"
BLUEPRINT_PATH = f"{BLUEPRINT_FOLDER}/{BLUEPRINT_NAME}"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_modular_blueprint_build.json"
)

COMPONENTS = [
    ("Body", "cc_base_body", True),
    ("Face_Eyes", "cc_base_eye", False),
    ("Face_EyeOcclusion", "cc_base_eyeocclusion", False),
    ("Face_TearDucts", "cc_base_tear_ducts", False),
    ("Face_Tearline", "cc_base_tearline", False),
    ("Face_Teeth", "cc_base_teeth", False),
    ("Face_Tongue", "cc_base_tongue", False),
    ("Face_Brows", "brows_bushy", False),
    ("Face_LashesUpper", "lash_up_bushy", False),
    ("Face_LashesLower", "lash_low_bushy", False),
    ("Face_BeardChin", "chin_curtain_sparse", False),
    ("Face_BeardNeck", "stubble_neck", False),
    ("Face_Mustache", "mustache_horseshoe", False),
    ("Outfit_Top", "basic_t_shirts", False),
    ("Outfit_Bottom", "jeans", False),
    ("Outfit_Shoes", "canvas_shoes", False),
    ("Hair_Bangs", "side_part_bangs", False),
    ("Hair_Mullet", "mullet_hair", False),
    ("Hair_BackLeft", "back_swept_l", False),
    ("Hair_BackRight", "back_swept_r", False),
]


def get_data(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)


def get_component(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(
        get_data(handle)
    )


if unreal.EditorAssetLibrary.does_asset_exist(BLUEPRINT_PATH):
    raise RuntimeError(f"Blueprint already exists; refusing to overwrite: {BLUEPRINT_PATH}")

meshes = {}
for component_name, mesh_name, _is_body in COMPONENTS:
    mesh = unreal.load_asset(f"{SOURCE_FOLDER}/{mesh_name}")
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Missing split mesh for {component_name}: {mesh_name}")
    meshes[component_name] = mesh

full_reference = unreal.load_asset(FULL_REFERENCE_MESH)
if not isinstance(full_reference, unreal.SkeletalMesh):
    raise RuntimeError(f"FullReference mesh is unavailable: {FULL_REFERENCE_MESH}")
post_process_class = full_reference.get_editor_property("post_process_anim_blueprint")
body_mesh = meshes["Body"]
body_mesh.set_editor_property("post_process_anim_blueprint", post_process_class)
if not unreal.EditorAssetLibrary.save_loaded_asset(body_mesh, only_if_is_dirty=False):
    raise RuntimeError("Unable to persist the body post-process animation class")

factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.Actor)
blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    BLUEPRINT_NAME,
    BLUEPRINT_FOLDER,
    unreal.Blueprint,
    factory,
)
if not isinstance(blueprint, unreal.Blueprint):
    raise RuntimeError(f"Unable to create Blueprint: {BLUEPRINT_PATH}")

sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
handles = sds.k2_gather_subobject_data_for_blueprint(blueprint)
root_handle = None
for handle in handles:
    if unreal.SubobjectDataBlueprintFunctionLibrary.is_root_component(get_data(handle)):
        root_handle = handle
        break
if root_handle is None:
    raise RuntimeError("Blueprint has no scene root")

created = {}
body_handle = None
body_component = None
for component_name, _mesh_name, is_body in COMPONENTS:
    parent_handle = root_handle if is_body else body_handle
    if parent_handle is None:
        raise RuntimeError("Body component must be created before followers")

    handle, failure_reason = sds.add_new_subobject(
        unreal.AddNewSubobjectParams(
            parent_handle=parent_handle,
            new_class=unreal.SkeletalMeshComponent,
            blueprint_context=blueprint,
        )
    )
    if not failure_reason.is_empty():
        raise RuntimeError(f"Unable to add {component_name}: {failure_reason}")
    if not sds.rename_subobject(handle=handle, new_name=unreal.Text(component_name)):
        raise RuntimeError(f"Unable to rename component: {component_name}")

    component = get_component(handle)
    if not isinstance(component, unreal.SkeletalMeshComponent):
        raise RuntimeError(f"Unexpected component type for {component_name}: {component}")
    component.set_skeletal_mesh_asset(meshes[component_name])
    component.set_editor_property("component_use_fixed_skel_bounds", False)

    if is_body:
        body_handle = handle
        body_component = component
    else:
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_editor_property("use_bounds_from_leader_pose_component", True)
        component.set_leader_pose_component(
            body_component,
            force_update=True,
            follower_should_tick_pose=False,
        )

    created[component_name] = {
        "component_template": component.get_path_name(),
        "mesh": meshes[component_name].get_path_name(),
        "leader": (
            component.get_editor_property("leader_pose_component").get_path_name()
            if component.get_editor_property("leader_pose_component") is not None
            else None
        ),
    }

unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
if not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save Blueprint: {BLUEPRINT_PATH}")

generated_class = blueprint.generated_class()
cdo = unreal.get_default_object(generated_class)
cdo_components = []
for component in cdo.get_components_by_class(unreal.SkeletalMeshComponent):
    leader = component.get_editor_property("leader_pose_component")
    cdo_components.append(
        {
            "name": component.get_name(),
            "mesh": (
                component.get_skeletal_mesh_asset().get_path_name()
                if component.get_skeletal_mesh_asset() is not None
                else None
            ),
            "leader": leader.get_name() if leader is not None else None,
            "parent": (
                component.get_attach_parent().get_name()
                if component.get_attach_parent() is not None
                else None
            ),
        }
    )
cdo_components.sort(key=lambda item: item["name"])

report = {
    "blueprint": blueprint.get_path_name(),
    "generated_class": generated_class.get_path_name(),
    "post_process_anim_blueprint": (
        post_process_class.get_path_name() if post_process_class is not None else None
    ),
    "source_component_count": len(COMPONENTS),
    "created_templates": created,
    "cdo_component_count": len(cdo_components),
    "cdo_components": cdo_components,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_MODULAR_BLUEPRINT="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "blueprint": report["blueprint"],
            "source_component_count": report["source_component_count"],
            "cdo_component_count": report["cdo_component_count"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
