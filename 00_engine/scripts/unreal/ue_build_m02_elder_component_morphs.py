"""Build M02 Elder Morph Targets for every changed modular component."""

import json
import math
from pathlib import Path

import unreal


PILOT_ROOT = "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001"
YOUNG_ROOT = PILOT_ROOT + "/Young"
ELDER_ROOT = PILOT_ROOT + "/Elder"
GENERATED_ROOT = PILOT_ROOT + "/Generated"
MATERIAL_SOURCE_ROOT = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot"
)
MORPH_NAME = "Full_Face_Elder"
DELTA_EPSILON_CM = 1.0e-5
BODY_TARGET = GENERATED_ROOT + "/SK_DM_M02_ElderMorph_Body_v001"
EXCLUDED_NONFACIAL_COMPONENTS = {
    "basic_t_shirts",
    "canvas_shoes",
    "jeans",
}
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_elder_component_morph_build_v001.json"
)


def list_skeletal_meshes(root):
    result = {}
    for asset_path in unreal.EditorAssetLibrary.list_assets(
        root, recursive=False, include_folder=False
    ):
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, unreal.SkeletalMesh):
            result[asset.get_name().lower()] = asset
    return result


def extract_source_model(skeletal_mesh):
    dynamic_mesh = unreal.DynamicMesh()
    options = unreal.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property("apply_build_settings", False)
    options.set_editor_property("ignore_remove_degenerates", True)
    options.set_editor_property("request_tangents", True)
    options.set_editor_property("use_build_scale", True)
    requested_lod = unreal.GeometryScriptMeshReadLOD()
    requested_lod.set_editor_property("lod_index", 0)
    requested_lod.set_editor_property(
        "lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL
    )
    dynamic_mesh, outcome = (
        unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
            skeletal_mesh,
            dynamic_mesh,
            options,
            requested_lod,
        )
    )
    if outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError(
            f"Unable to extract source geometry from {skeletal_mesh.get_path_name()}: "
            f"{outcome}"
        )
    return dynamic_mesh


def positions(dynamic_mesh):
    _mesh, position_list, has_gaps = (
        unreal.GeometryScript_MeshQueries.get_all_vertex_positions(
            dynamic_mesh, False
        )
    )
    return list(position_list.convert_vector_list_to_array()), bool(has_gaps)


def delta_metrics(young_dynamic, elder_dynamic):
    young_positions, young_has_gaps = positions(young_dynamic)
    elder_positions, elder_has_gaps = positions(elder_dynamic)
    if len(young_positions) != len(elder_positions):
        raise RuntimeError(
            "Source-model vertex count mismatch: {} vs {}".format(
                len(young_positions), len(elder_positions)
            )
        )
    distances = []
    changed = 0
    sum_distance = 0.0
    sum_squared = 0.0
    maximum = 0.0
    for young_position, elder_position in zip(
        young_positions, elder_positions
    ):
        dx = float(elder_position.x - young_position.x)
        dy = float(elder_position.y - young_position.y)
        dz = float(elder_position.z - young_position.z)
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        distances.append(distance)
        maximum = max(maximum, distance)
        sum_distance += distance
        sum_squared += distance * distance
        if distance > DELTA_EPSILON_CM:
            changed += 1
    count = len(distances)
    return {
        "changed_vertex_count": changed,
        "has_vertex_id_gaps_elder": elder_has_gaps,
        "has_vertex_id_gaps_young": young_has_gaps,
        "max_delta_cm": maximum,
        "mean_delta_cm": sum_distance / count if count else 0.0,
        "rms_delta_cm": math.sqrt(sum_squared / count) if count else 0.0,
        "source_vertex_count": count,
    }


def generated_path(component_name):
    if component_name == "cc_base_body":
        return BODY_TARGET
    return (
        GENERATED_ROOT
        + "/SK_DM_M02_ElderMorph_{}_v001".format(component_name)
    )


def copy_materials(component_name, target):
    material_source = unreal.load_asset(
        MATERIAL_SOURCE_ROOT + "/" + component_name
    )
    if not isinstance(material_source, unreal.SkeletalMesh):
        return None
    target.set_editor_property(
        "materials", material_source.get_editor_property("materials")
    )
    return material_source.get_path_name()


def write_morph(component_name, young, elder_dynamic):
    target_path = generated_path(component_name)
    target = unreal.load_asset(target_path)
    created = False
    if target is None:
        target = unreal.EditorAssetLibrary.duplicate_asset(
            young.get_path_name(), target_path
        )
        created = True
    if not isinstance(target, unreal.SkeletalMesh):
        raise RuntimeError(f"Unable to create generated component: {target_path}")

    existing_morphs = {
        str(name) for name in target.get_all_morph_target_names()
    }
    try:
        if MORPH_NAME not in existing_morphs:
            options = unreal.GeometryScriptCopyMorphTargetToAssetOptions()
            options.set_editor_property("copy_normals", False)
            options.set_editor_property("defer_mesh_post_edit_change", False)
            options.set_editor_property("emit_transaction", True)
            options.set_editor_property("overwrite_existing_target", False)
            target_lod = unreal.GeometryScriptMeshWriteLOD()
            target_lod.set_editor_property("lod_index", 0)
            target_lod.set_editor_property("write_hi_res_source", False)
            _mesh, outcome = (
                unreal.GeometryScript_AssetUtils.copy_morph_target_to_skeletal_mesh(
                    elder_dynamic,
                    target,
                    MORPH_NAME,
                    options,
                    target_lod,
                )
            )
            if outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError(
                    f"Unable to write {MORPH_NAME} to {target_path}: {outcome}"
                )
    except Exception:
        if created:
            unreal.EditorAssetLibrary.delete_asset(target_path)
        raise
    material_source = copy_materials(component_name, target)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save generated component: {target_path}")
    morph_names = {
        str(name) for name in target.get_all_morph_target_names()
    }
    if MORPH_NAME not in morph_names:
        raise RuntimeError(f"Generated component is missing {MORPH_NAME}: {target_path}")
    return {
        "created": created,
        "material_source": material_source,
        "morph_count": len(morph_names),
        "path": target.get_path_name(),
    }


young_meshes = list_skeletal_meshes(YOUNG_ROOT)
elder_meshes = list_skeletal_meshes(ELDER_ROOT)
if not young_meshes or not elder_meshes:
    raise RuntimeError("Young or Elder snapshot directory contains no skeletal meshes")

component_names = sorted(set(young_meshes) | set(elder_meshes))
records = []
for component_name in component_names:
    young = young_meshes.get(component_name)
    elder = elder_meshes.get(component_name)
    if young is None or elder is None:
        records.append(
            {
                "component": component_name,
                "generated": None,
                "present_in_elder": elder is not None,
                "present_in_young": young is not None,
                "status": "missing_pair",
            }
        )
        continue
    young_dynamic = extract_source_model(young)
    elder_dynamic = extract_source_model(elder)
    metrics = delta_metrics(young_dynamic, elder_dynamic)
    generated = None
    status = "unchanged"
    error = None
    if component_name in EXCLUDED_NONFACIAL_COMPONENTS:
        status = "excluded_nonfacial"
    elif metrics["changed_vertex_count"] > 0:
        try:
            generated = write_morph(
                component_name,
                young,
                elder_dynamic,
            )
            status = "morph_written"
        except Exception as exception:
            error = {
                "message": str(exception),
                "type": type(exception).__name__,
            }
            status = "morph_write_failed"
    records.append(
        {
            "component": component_name,
            "delta": metrics,
            "elder": elder.get_path_name(),
            "error": error,
            "generated": generated,
            "present_in_elder": True,
            "present_in_young": True,
            "status": status,
            "young": young.get_path_name(),
        }
    )

report = {
    "delta_epsilon_cm": DELTA_EPSILON_CM,
    "elder_root": ELDER_ROOT,
    "generated_root": GENERATED_ROOT,
    "material_source_root": MATERIAL_SOURCE_ROOT,
    "morph_name": MORPH_NAME,
    "records": records,
    "summary": {
        "component_count": len(records),
        "failed_or_missing": [
            item["component"]
            for item in records
            if item["status"] in ("missing_pair", "morph_write_failed")
        ],
        "excluded_nonfacial": [
            item["component"]
            for item in records
            if item["status"] == "excluded_nonfacial"
        ],
        "morph_written": [
            item["component"]
            for item in records
            if item["status"] == "morph_written"
        ],
        "unchanged": [
            item["component"]
            for item in records
            if item["status"] == "unchanged"
        ],
    },
    "young_root": YOUNG_ROOT,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_ELDER_COMPONENT_MORPHS="
    + json.dumps(
        {"report_path": str(REPORT_PATH), **report["summary"]},
        ensure_ascii=False,
        sort_keys=True,
    )
)
