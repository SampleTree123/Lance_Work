"""Import and audit the M02 young/elder CC5 FBX snapshot pair."""

import json
from pathlib import Path

import unreal


SOURCE_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge"
    r"\artifacts\elder_morph_export_m02_20260804_02"
)
SOURCES = {
    "young": SOURCE_ROOT / "M02_Young_Base_UE5.fbx",
    "elder": SOURCE_ROOT / "M02_Elder_Target_UE5.fbx",
}
PILOT_ROOT = "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001"
DESTINATIONS = {
    "young": PILOT_ROOT + "/Young",
    "elder": PILOT_ROOT + "/Elder",
}
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
PILOT_PIPELINE = PILOT_ROOT + "/DM_FBX_ElderMorph_Pipeline_v001"
MASTER_SKELETON = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58_Skeleton"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_elder_morph_snapshot_import_v001.json"
)


def object_path(obj):
    return obj.get_path_name() if obj is not None else None


def vector_record(vector):
    return {"x": vector.x, "y": vector.y, "z": vector.z}


def object_record(obj):
    return {
        "class": obj.get_class().get_name(),
        "name": obj.get_name(),
        "path": obj.get_path_name(),
    }


for label, source in SOURCES.items():
    if not source.is_file() or source.stat().st_size <= 0:
        raise FileNotFoundError(f"{label} source FBX is unavailable: {source}")

master_skeleton = unreal.load_asset(MASTER_SKELETON)
if master_skeleton is None:
    raise RuntimeError(f"Master skeleton is unavailable: {MASTER_SKELETON}")

for label, destination in DESTINATIONS.items():
    existing = unreal.EditorAssetLibrary.list_assets(
        destination, recursive=True, include_folder=False
    )
    if existing:
        raise RuntimeError(
            f"{label} Elder Morph destination is not empty; refusing to overwrite: "
            + ", ".join(existing[:10])
        )

pipeline = unreal.load_asset(PILOT_PIPELINE)
if pipeline is None:
    pipeline = unreal.EditorAssetLibrary.duplicate_asset(
        DEFAULT_PIPELINE, PILOT_PIPELINE
    )
if pipeline is None:
    raise RuntimeError("Unable to create the Elder Morph Interchange pipeline")

mesh_pipeline = pipeline.get_editor_property("mesh_pipeline")
common_skeletal = pipeline.get_editor_property(
    "common_skeletal_meshes_and_animations_properties"
)
animation_pipeline = pipeline.get_editor_property("animation_pipeline")
material_pipeline = pipeline.get_editor_property("material_pipeline")
texture_pipeline = material_pipeline.get_editor_property("texture_pipeline")

mesh_pipeline.set_editor_property("import_skeletal_meshes", True)
mesh_pipeline.set_editor_property("import_static_meshes", False)
mesh_pipeline.set_editor_property(
    "combine_skeletal_meshes_behavior",
    unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE,
)
mesh_pipeline.set_editor_property("import_morph_targets", True)
mesh_pipeline.set_editor_property("create_physics_asset", False)
mesh_pipeline.set_editor_property("physics_asset", None)
mesh_pipeline.set_editor_property(
    "skeletal_mesh_import_content_type",
    unreal.InterchangeSkeletalMeshContentType.ALL,
)
common_skeletal.set_editor_property("skeleton", master_skeleton)
common_skeletal.set_editor_property("try_auto_select_skeleton", False)
common_skeletal.set_editor_property("import_only_animations", False)
animation_pipeline.set_editor_property("import_animations", False)
material_pipeline.set_editor_property("import_materials", False)
texture_pipeline.set_editor_property("import_textures", False)

if not unreal.EditorAssetLibrary.save_loaded_asset(
    pipeline, only_if_is_dirty=False
):
    raise RuntimeError(f"Unable to save pipeline asset: {PILOT_PIPELINE}")

manager = unreal.InterchangeManager.get_interchange_manager_scripted()
fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
previous_fbx_flag = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
editor_world = unreal.get_editor_subsystem(
    unreal.UnrealEditorSubsystem
).get_editor_world()
import_returns = {}

if previous_fbx_flag != 1:
    unreal.SystemLibrary.execute_console_command(editor_world, f"{fbx_cvar} 1")
if unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar) != 1:
    raise RuntimeError(f"Unable to enable {fbx_cvar}")

try:
    for label in ("young", "elder"):
        source_data = manager.create_source_data(str(SOURCES[label]))
        if source_data is None:
            raise RuntimeError(f"Unable to create source data for {SOURCES[label]}")
        parameters = unreal.ImportAssetParameters()
        parameters.set_editor_property("is_automated", True)
        parameters.set_editor_property("force_show_dialog", False)
        parameters.set_editor_property("replace_existing", False)
        parameters.set_editor_property(
            "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
        )
        unreal.log(f"DataMake Elder Morph pilot: importing {label} snapshot")
        imported = manager.import_asset(
            DESTINATIONS[label], source_data, parameters
        ) or []
        import_returns[label] = [object_record(obj) for obj in imported]
        unreal.EditorAssetLibrary.save_directory(
            DESTINATIONS[label], only_if_is_dirty=False, recursive=True
        )
finally:
    if previous_fbx_flag != 1:
        unreal.SystemLibrary.execute_console_command(
            editor_world, f"{fbx_cvar} {previous_fbx_flag}"
        )

subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def audit_destination(destination):
    records = []
    for asset_path in unreal.EditorAssetLibrary.list_assets(
        destination, recursive=True, include_folder=False
    ):
        skeletal_mesh = unreal.load_asset(asset_path)
        if not isinstance(skeletal_mesh, unreal.SkeletalMesh):
            continue
        morph_names = sorted(
            str(name) for name in skeletal_mesh.get_all_morph_target_names()
        )
        materials = skeletal_mesh.get_editor_property("materials")
        bounds = skeletal_mesh.get_bounds()
        records.append(
            {
                "bounds": {
                    "box_extent": vector_record(bounds.box_extent),
                    "origin": vector_record(bounds.origin),
                    "sphere_radius": bounds.sphere_radius,
                },
                "lod0_sections": subsystem.get_num_sections(skeletal_mesh, 0),
                "lod0_vertices": subsystem.get_num_verts(skeletal_mesh, 0),
                "material_slots": [
                    str(item.get_editor_property("material_slot_name"))
                    for item in materials
                ],
                "morph_count": len(morph_names),
                "morph_names": morph_names,
                "morph_names_age_like": [
                    name
                    for name in morph_names
                    if any(
                        token in name.lower()
                        for token in ("elder", "age", "old", "head_scale")
                    )
                ],
                "name": skeletal_mesh.get_name(),
                "path": skeletal_mesh.get_path_name(),
                "skeleton": object_path(
                    skeletal_mesh.get_editor_property("skeleton")
                ),
            }
        )
    records.sort(key=lambda item: item["name"].lower())
    return records


audits = {
    label: audit_destination(destination)
    for label, destination in DESTINATIONS.items()
}
young_by_name = {item["name"].lower(): item for item in audits["young"]}
elder_by_name = {item["name"].lower(): item for item in audits["elder"]}
all_names = sorted(set(young_by_name) | set(elder_by_name))
comparisons = []
for name in all_names:
    young = young_by_name.get(name)
    elder = elder_by_name.get(name)
    comparisons.append(
        {
            "elder_morph_count": elder["morph_count"] if elder else None,
            "elder_vertices": elder["lod0_vertices"] if elder else None,
            "material_slots_match": bool(
                young
                and elder
                and young["material_slots"] == elder["material_slots"]
            ),
            "mesh": name,
            "morph_names_match": bool(
                young and elder and young["morph_names"] == elder["morph_names"]
            ),
            "present_in_elder": elder is not None,
            "present_in_young": young is not None,
            "sections_match": bool(
                young
                and elder
                and young["lod0_sections"] == elder["lod0_sections"]
            ),
            "topology_counts_match": bool(
                young
                and elder
                and young["lod0_vertices"] == elder["lod0_vertices"]
            ),
            "young_morph_count": young["morph_count"] if young else None,
            "young_vertices": young["lod0_vertices"] if young else None,
        }
    )

report = {
    "audits": audits,
    "comparisons": comparisons,
    "destinations": DESTINATIONS,
    "direct_age_like_morphs": {
        label: {
            item["name"]: item["morph_names_age_like"]
            for item in records
            if item["morph_names_age_like"]
        }
        for label, records in audits.items()
    },
    "import_returns": import_returns,
    "interchange_fbx_flag_after_import": (
        unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
    ),
    "master_skeleton": master_skeleton.get_path_name(),
    "pipeline": pipeline.get_path_name(),
    "pilot_root": PILOT_ROOT,
    "sources": {label: str(path) for label, path in SOURCES.items()},
    "summary": {
        "all_components_topology_counts_match": all(
            item["topology_counts_match"] for item in comparisons
        ),
        "component_count_elder": len(audits["elder"]),
        "component_count_young": len(audits["young"]),
        "direct_age_like_morph_count_elder": sum(
            len(item["morph_names_age_like"]) for item in audits["elder"]
        ),
        "direct_age_like_morph_count_young": sum(
            len(item["morph_names_age_like"]) for item in audits["young"]
        ),
        "mismatched_topology_components": [
            item["mesh"]
            for item in comparisons
            if not item["topology_counts_match"]
        ],
        "skeleton_mismatches": {
            label: [
                item["name"]
                for item in records
                if item["skeleton"] != master_skeleton.get_path_name()
            ]
            for label, records in audits.items()
        },
    },
}

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_ELDER_MORPH_IMPORT="
    + json.dumps(
        {"report_path": str(REPORT_PATH), **report["summary"]},
        ensure_ascii=False,
        sort_keys=True,
    )
)
