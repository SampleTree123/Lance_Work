"""Print the Interchange settings needed by the split skeletal-mesh pilot."""

import json
import unreal


PIPELINE_PATH = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
MASTER_SKELETON_PATH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58_Skeleton"
)


def describe_value(value):
    record = {
        "python_type": type(value).__name__,
        "repr": str(value),
    }
    if isinstance(value, unreal.Object):
        record["class"] = value.get_class().get_name()
        record["path"] = value.get_path_name()
    return record


def read_properties(obj, names):
    result = {}
    for name in names:
        try:
            result[name] = describe_value(obj.get_editor_property(name))
        except Exception as exc:
            result[name] = {"error": str(exc)}
    return result


pipeline = unreal.load_asset(PIPELINE_PATH)
if pipeline is None:
    raise RuntimeError("Default Interchange pipeline asset is unavailable")

mesh = pipeline.get_editor_property("mesh_pipeline")
common_skeletal = pipeline.get_editor_property(
    "common_skeletal_meshes_and_animations_properties"
)
animation = pipeline.get_editor_property("animation_pipeline")
material = pipeline.get_editor_property("material_pipeline")
texture = material.get_editor_property("texture_pipeline")
master_skeleton = unreal.load_asset(MASTER_SKELETON_PATH)
import_parameters = unreal.ImportAssetParameters()
manager = unreal.InterchangeManager.get_interchange_manager_scripted()

report = {
    "pipeline": describe_value(pipeline),
    "mesh": read_properties(
        mesh,
        [
            "import_skeletal_meshes",
            "import_static_meshes",
            "combine_skeletal_meshes_behavior",
            "import_morph_targets",
            "create_physics_asset",
            "skeletal_mesh_import_content_type",
            "physics_asset",
            "import_vertex_attributes",
        ],
    ),
    "common_skeletal": read_properties(
        common_skeletal,
        [
            "skeleton",
            "try_auto_select_skeleton",
            "import_meshes_in_bone_hierarchy",
            "import_only_animations",
        ],
    ),
    "animation": read_properties(animation, ["import_animations"]),
    "material": read_properties(
        material,
        [
            "import_materials",
            "material_import",
            "reuse_existing_materials",
            "create_new_materials",
        ],
    ),
    "texture": read_properties(texture, ["import_textures"]),
    "master_skeleton": describe_value(master_skeleton),
    "import_parameters": read_properties(
        import_parameters,
        [
            "is_automated",
            "override_pipelines",
            "destination_name",
            "replace_existing",
            "force_show_dialog",
            "reimport_asset",
        ],
    ),
    "manager_class": describe_value(manager),
    "import_asset_doc": str(getattr(manager.import_asset, "__doc__", "")),
    "scripted_import_asset_async_doc": str(
        getattr(manager.scripted_import_asset_async, "__doc__", "")
    ),
    "combine_enum": [
        name
        for name in dir(unreal.InterchangeCombineSkeletalMeshesBehavior)
        if name.isupper()
    ],
    "content_type_enum": [
        name
        for name in dir(unreal.InterchangeSkeletalMeshContentType)
        if name.isupper()
    ],
}
print("DM_INTERCHANGE_INSPECT=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
