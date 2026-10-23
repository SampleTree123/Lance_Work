"""Read-only triangle corner diagnostics for the F02 garment derivative."""


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_compare_wardrobe_corners_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

import json
import math
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).parent))
from wardrobe_corner_matching_v1 import match_corners

ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1\optimization_20260907")


def xyz(v):
    return [v.x, v.y, v.z]


def triangle(v):
    return [xyz(getattr(v, f"vector{i}")) for i in range(3)]


def flatten(value):
    if isinstance(value, (list, tuple)):
        return [x for item in value for x in flatten(item)]
    return [value]


def main():
    q = unreal.GeometryScript_MeshQueries
    report = json.loads((ROOT / "ue_probe.json").read_text(encoding="utf-8"))
    assets = [unreal.load_asset(report[k]["path"]) for k in ("baseline", "derivative")]
    result = {"schema_version": 1, "read_only": True, "runtime_approved": False, "rows": []}
    for name, lod in (("source", unreal.GeometryScriptLODType.SOURCE_MODEL),
                      ("render", unreal.GeometryScriptLODType.RENDER_DATA)):
        meshes = []
        for asset in assets:
            copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
                asset, unreal.DynamicMesh(), unreal.GeometryScriptCopyMeshFromAssetOptions(),
                unreal.GeometryScriptMeshReadLOD(lod_type=lod, lod_index=0))
            if "SUCCESS" not in str(copied[-1]):
                raise RuntimeError(str(copied))
            meshes.append(copied[0])
        ids = [list(unreal.GeometryScript_List.convert_index_list_to_array(q.get_all_triangle_i_ds(m)[1]))
               for m in meshes]
        uv_counts = [q.get_num_uv_sets(m) for m in meshes]
        if uv_counts != [1, 1]:
            raise RuntimeError("This isolated probe supports the known single-UV shorts only")
        row = {"lod": name, "triangle_counts": [len(v) for v in ids],
               "same_triangle_ids": ids[0] == ids[1], "uv_counts": uv_counts, "attributes": {}}
        render_records = [[], []]
        if ids[0] != ids[1] or uv_counts[0] != uv_counts[1]:
            result["rows"].append(row)
            continue
        for tid in ids[0]:
            samples = []
            for mesh in meshes:
                positions = q.get_triangle_positions(mesh, tid)
                normals = q.get_triangle_normals(mesh, tid)
                tangents = q.get_triangle_normal_tangents(mesh, tid)
                colors = q.get_triangle_vertex_colors(mesh, tid)
                sample = {"positions": [positions[0], *[xyz(v) for v in positions[1:]]],
                          "normals": [normals[-1], *[xyz(v) for v in normals[1:-1]]],
                          "tangents": [tangents[1], triangle(tangents[3]), triangle(tangents[4])],
                          "colors": [colors[-1], *[[v.r, v.g, v.b, v.a] for v in colors[1:-1]]],
                          "material": list(unreal.GeometryScript_Materials.get_triangle_material_id(mesh, tid))}
                for uv in range(uv_counts[0]):
                    values = q.get_triangle_u_vs(mesh, uv, tid)
                    sample[f"uv_{uv}"] = [values[-1], *[[v.x, v.y] for v in values[:-1]]]
                samples.append(sample)
            if name == "render":
                for index, sample in enumerate(samples):
                    render_records[index].append(sample)
            for key in samples[0]:
                a, b = flatten(samples[0][key]), flatten(samples[1][key])
                stats = row["attributes"].setdefault(key, {"different_triangles": 0, "max_delta": 0.0,
                                                           "validity_mismatches": 0, "nonfinite": 0})
                if len(a) != len(b):
                    raise RuntimeError(f"Attribute layout changed: {key}")
                delta = 0.0
                for left, right in zip(a, b):
                    if not math.isfinite(left) or not math.isfinite(right):
                        stats["nonfinite"] += 1
                    elif isinstance(left, bool) or isinstance(right, bool):
                        stats["validity_mismatches"] += int(left != right)
                    else:
                        delta = max(delta, abs(left-right))
                stats["max_delta"] = max(stats["max_delta"], delta)
                if a != b:
                    stats["different_triangles"] += 1
                    stats.setdefault("first_difference", {"triangle_id": tid, "a": a, "b": b})
        if name == "render":
            matches, missing, extra = match_corners(*render_records)
            aligned = {"matched_triangles": len(matches), "missing": missing, "extra": extra,
                       "max_position_component_delta_cm": 0.0, "max_normal_component_delta": 0.0,
                       "max_tangent_component_delta": 0.0, "color_mismatches": 0,
                       "invalid_attributes": 0, "nonfinite": 0}
            for a, b, rotation in matches:
                first, second = render_records[0][a], render_records[1][b]
                for key, metric in (("positions", "max_position_component_delta_cm"),
                                    ("normals", "max_normal_component_delta"),
                                    ("tangents", "max_tangent_component_delta"),
                                    ("colors", None)):
                    aligned["invalid_attributes"] += int(not first[key][0] or not second[key][0])
                    if key == "tangents":
                        blocks = [(first[key][i], second[key][i]) for i in (1, 2)]
                    else:
                        blocks = [(first[key][1:], second[key][1:])]
                    for left, right in blocks:
                        rotated = right[rotation:] + right[:rotation]
                        deltas = [abs(x-y) for p, q in zip(left, rotated) for x, y in zip(p, q)]
                        if not all(math.isfinite(d) for d in deltas):
                            aligned["nonfinite"] += 1
                        elif metric:
                            aligned[metric] = max(aligned[metric], max(deltas))
                        else:
                            aligned["color_mismatches"] += int(any(deltas))
            row["aligned_by_uv_and_position"] = aligned
        result["rows"].append(row)
    (ROOT / "corner_comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if globals().get("DM_COMPARE_WARDROBE_CORNERS"):
    main()
