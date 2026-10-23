"""Read-only source/render geometry comparison for the isolated shorts probe."""


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_compare_wardrobe_probe_geometry_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

from pathlib import Path
import json

import unreal

ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1\optimization_20260907")


def main():
    report = json.loads((ROOT / "ue_probe.json").read_text(encoding="utf-8"))
    assets = [unreal.load_asset(report[k]["path"]) for k in ("baseline", "derivative")]
    rows = []
    for name, lod_type in (("source", unreal.GeometryScriptLODType.SOURCE_MODEL),
                           ("render", unreal.GeometryScriptLODType.RENDER_DATA)):
        meshes = []
        for asset in assets:
            mesh = unreal.DynamicMesh()
            copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
                asset, mesh, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                unreal.GeometryScriptMeshReadLOD(lod_type=lod_type, lod_index=0))
            if "SUCCESS" not in str(copied[-1]):
                raise RuntimeError(f"Cannot copy {name} geometry: {copied}")
            meshes.append(mesh)
        options = unreal.GeometryScriptIsSameMeshOptions(
            check_connectivity=True, check_normals=True, check_colors=True,
            check_u_vs=True, check_groups=True, check_attributes=True, epsilon=1e-6)
        comparison = unreal.GeometryScript_MeshComparison.is_same_mesh_as(*meshes, options)
        options.set_editor_property("epsilon", 1e-4)
        float_comparison = unreal.GeometryScript_MeshComparison.is_same_mesh_as(*meshes, options)
        skin_weights = None
        if name == "source":
            ids = []
            for mesh in meshes:
                id_result = unreal.GeometryScript_MeshQueries.get_all_vertex_i_ds(mesh)
                ids.append(list(unreal.GeometryScript_List.convert_index_list_to_array(id_result[1])))
            skin_weights = {"same_vertex_ids": ids[0] == ids[1],
                            "compared_vertices": 0, "different_vertices": 0,
                            "invalid_vertices": 0, "max_weight_delta": 0.0}
            if ids[0] == ids[1]:
                for vertex_id in ids[0]:
                    values = [unreal.GeometryScript_BoneWeights.get_vertex_bone_weights(
                        mesh, vertex_id) for mesh in meshes]
                    if not all(value[-1] for value in values):
                        skin_weights["invalid_vertices"] += 1
                        continue
                    pairs = [{int(w.bone_index): float(w.weight) for w in value[1]}
                             for value in values]
                    delta = max((abs(pairs[0].get(bone, 0) - pairs[1].get(bone, 0))
                                 for bone in pairs[0].keys() | pairs[1].keys()), default=0.0)
                    skin_weights["compared_vertices"] += 1
                    skin_weights["different_vertices"] += int(pairs[0] != pairs[1])
                    skin_weights["max_weight_delta"] = max(skin_weights["max_weight_delta"], delta)
        distances = unreal.GeometryScript_MeshComparison.measure_distances_between_meshes(
            *meshes, unreal.GeometryScriptMeasureMeshDistanceOptions(symmetric=True))
        rows.append({"lod_type": name, "same_mesh": bool(comparison[-2]),
                     "same_mesh_at_float_precision": bool(float_comparison[-2]),
                     "float_precision_epsilon_cm": 1e-4,
                     "float_precision_difference": str(float_comparison[-1]),
                     "source_skin_weights": skin_weights,
                     "difference": str(comparison[-1]), "max_distance_cm": distances[-4],
                     "average_distance_cm": distances[-2]})
    result = {"schema_version": 1, "scope": "f02_shorts_read_only_geometry_comparison",
              "rows": rows, "runtime_approved": False}
    (ROOT / "geometry_comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if globals().get("DM_COMPARE_WARDROBE_GEOMETRY"):
    main()
