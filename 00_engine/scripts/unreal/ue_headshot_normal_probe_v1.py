"""Isolated UE experiment for the Headshot FBX morph-normal anomaly.

Only runs in the dedicated empty experiment project. Does not load or modify
the production project. Raw FBX inputs are read-only and locked by a manifest.
"""
import hashlib
import gzip
import json
import math
from array import array
from pathlib import Path
import sys
import traceback

import unreal


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_route_compare_20261002_v1")
PROJECT = ROOT / "ue_normal_probe_project_v1"
RUN = Path(globals().get("DM_HS_NORMAL_RUN", str(ROOT / "ue_normal_probe_v1"))).resolve()
if RUN.parent != ROOT.resolve() or not RUN.name.startswith("ue_normal_probe_"):
    raise ValueError("Normal probe outputs must remain in a dedicated experiment run")


def attempt_name():
    value = globals().get("DM_HS_NORMAL_ATTEMPT", "v2")
    if not isinstance(value, str) or not value.isalnum():
        raise ValueError("Unsafe attempt name")
    return value


def run_tag():
    value = globals()["DM_HS_NORMAL_TAG"]
    if not isinstance(value, str) or not value.replace("_", "").isalnum():
        raise ValueError("Unsafe report tag")
    return value


def geometry_api():
    tag = run_tag()
    output = RUN / (tag + "_api.json")
    if output.exists():
        raise RuntimeError("Refusing to overwrite geometry API evidence")
    names = {
        "GeometryScript_AssetUtils": ["copy_mesh_from_skeletal_mesh"],
        "GeometryScript_SceneUtils": ["copy_mesh_from_component"],
        "GeometryScript_MeshQueries": ["get_all_triangle_i_ds", "get_all_vertex_positions", "get_triangle_normals", "get_triangle_indices"],
        "GeometryScript_List": ["convert_vector_list_to_array", "convert_index_list_to_array"],
        "SkeletalMeshComponent": ["set_skeletal_mesh", "set_morph_target", "set_position", "set_update_animation_in_editor", "set_animation_mode"],
        "GeometryScriptMeshReadLOD": [],
        "GeometryScriptCopyMeshFromAssetOptions": [],
        "GeometryScriptCopyMeshFromComponentOptions": [],
        "GeometryScriptLODType": [],
        "GeometryScriptOutcomePins": [],
        "EditorActorSubsystem": ["spawn_actor_from_class", "destroy_actor"],
    }
    result = {}
    for class_name, methods in names.items():
        cls = getattr(unreal, class_name, None)
        result[class_name] = dict(doc=getattr(cls, "__doc__", None),
            methods={n: getattr(getattr(cls, n, None), "__doc__", None) for n in methods},
            names=[n for n in dir(cls) if not n.startswith("_")])
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def geometry_probe():
    tag = run_tag()
    attempt = attempt_name()
    output = RUN / (tag + "_geometry.json")
    data_dir = RUN / (tag + "_arrays")
    if output.exists() or data_dir.exists():
        raise RuntimeError("Refusing to overwrite geometry evidence")
    data_dir.mkdir()
    report = dict(success=False, engine_version=unreal.SystemLibrary.get_engine_version(),
                  implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope="LOD0 RenderData base positions/topology/split normals and saved morph inventory; no GPU/material/posed acceptance",
                  meshes=[], comparisons=[])
    query = unreal.GeometryScript_MeshQueries
    lists = unreal.GeometryScript_List
    inputs = {}
    for case in ("reload_0", "reload_1"):
        path = RUN / (case + "_" + attempt + "_import.json")
        imported = json.loads(path.read_text(encoding="utf-8"))
        if not imported["success"] or not imported["source_unchanged"]:
            raise RuntimeError("Import prerequisite failed")
        inputs[case] = imported
    report["import_reports"] = {c: hashlib.sha256((RUN / (c + "_" + attempt + "_import.json")).read_bytes()).hexdigest() for c in inputs}

    def flush():
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def serialize(values, key, typecode):
        binary = array(typecode, values)
        if sys.byteorder != "little":
            binary.byteswap()
        raw = binary.tobytes()
        path = data_dir / (key + ".bin.gz")
        path.write_bytes(gzip.compress(raw))
        return dict(path=str(path), elements=len(values), type=typecode, byte_order="little",
                    uncompressed_sha256=hashlib.sha256(raw).hexdigest(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def extract(case, row):
        asset = unreal.load_asset(row["path"])
        if not isinstance(asset, unreal.SkeletalMesh):
            raise RuntimeError("Saved mesh could not be reloaded")
        lod = unreal.GeometryScriptMeshReadLOD(lod_type=unreal.GeometryScriptLODType.RENDER_DATA, lod_index=0)
        dyn, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
            asset, unreal.DynamicMesh(), unreal.GeometryScriptCopyMeshFromAssetOptions(), lod)
        if outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError("RenderData extraction failed")
        _, vec_list, gaps = query.get_all_vertex_positions(dyn, False)
        if gaps:
            raise RuntimeError("Unexpected vertex gaps")
        pos = [tuple(float(getattr(v, a)) for a in ("x", "y", "z")) for v in lists.convert_vector_list_to_array(vec_list)]
        _, tri_list, tri_gaps = query.get_all_triangle_i_ds(dyn)
        triangles, normals = [], []
        for tid in lists.convert_index_list_to_array(tri_list):
            indices, valid = query.get_triangle_indices(dyn, tid)
            _, n1, n2, n3, valid_normals = query.get_triangle_normals(dyn, tid)
            if not valid or not valid_normals:
                raise RuntimeError("Invalid triangle or missing normals")
            triangles.append(tuple(int(getattr(indices, a)) for a in ("x", "y", "z")))
            normals.extend(tuple(float(getattr(n, a)) for a in ("x", "y", "z")) for n in (n1, n2, n3))
        if not pos or not triangles:
            raise RuntimeError("Empty extracted geometry")
        if not all(math.isfinite(v) for values in (pos, normals) for row_values in values for v in row_values):
            raise RuntimeError("Nonfinite RenderData")
        lengths = [math.sqrt(sum(v*v for v in n)) for n in normals]
        morphs = sorted(str(x.get_name()) for x in asset.get_editor_property("morph_targets") if x is not None)
        if morphs != row["morph_names"]:
            raise RuntimeError("Saved/reloaded morph inventory changed")
        evidence = dict(case=case, name=row["name"], asset=row["path"], vertices=len(pos), triangle_count=len(triangles),
                        triangle_id_gaps=tri_gaps, normal_count=len(normals), min_normal_length=min(lengths),
                        max_normal_length=max(lengths), zero_normals=sum(x < 1e-8 for x in lengths),
                        morphs=morphs)
        for key, values, typecode in (("positions", pos, "d"), ("triangles", triangles, "i"), ("normals", normals, "d")):
            evidence[key] = serialize([v for values_row in values for v in values_row], case + "_" + row["name"] + "_" + key, typecode)
        report["meshes"].append(evidence)
        flush()
        unreal.log("Headshot RenderData captured: " + case + " " + row["name"])
        return pos, triangles, normals, morphs

    try:
        flush()
        first_rows = {r["name"]: r for r in inputs["reload_0"]["assets"] if r["class"] == "SkeletalMesh"}
        second_rows = {r["name"]: r for r in inputs["reload_1"]["assets"] if r["class"] == "SkeletalMesh"}
        expected_count = int(json.loads((RUN / "inputs.json").read_text(encoding="utf-8")).get("expected_skeletal_mesh_count", 6))
        if len(first_rows) != expected_count or first_rows.keys() != second_rows.keys():
            raise RuntimeError("Mesh inventory mismatch")
        for name in sorted(first_rows):
            a = extract("reload_0", first_rows[name])
            b = extract("reload_1", second_rows[name])
            same_topology = a[1] == b[1] and len(a[0]) == len(b[0])
            same_normals = a[2] == b[2]
            comparison = dict(name=name, indexed_topology_equal=same_topology,
                              positions_exact_equal=a[0] == b[0], normals_exact_equal=same_normals,
                              morph_inventory_equal=a[3] == b[3], lip_open_present="V_Lip_Open" in a[3])
            if same_topology:
                comparison["max_position_delta_mm"] = max(math.dist(x, y) for x, y in zip(a[0], b[0])) * 10.0
                comparison["max_normal_vector_delta"] = max(math.dist(x, y) for x, y in zip(a[2], b[2]))
            report["comparisons"].append(comparison)
            flush()
        report["all_base_renderdata_exact_equal"] = all(
            c["indexed_topology_equal"] and c["positions_exact_equal"] and c["normals_exact_equal"] for c in report["comparisons"])
        report["all_morph_inventories_equal"] = all(c["morph_inventory_equal"] for c in report["comparisons"])
        report["raw_sources_unchanged"] = all(hashlib.sha256(Path(r["source"]["path"]).read_bytes()).hexdigest() == r["source"]["sha256"] for r in inputs.values())
        report["success"] = True
    except Exception:
        report["error"] = traceback.format_exc()
        raise
    finally:
        flush()


def import_case(case_id):
    attempt = attempt_name()
    manifest = json.loads((RUN / "inputs.json").read_text(encoding="utf-8"))
    matches = [x for x in manifest["sources"] if x["id"] == case_id]
    if len(matches) != 1 or case_id not in ("reload_0", "reload_1"):
        raise ValueError("Unknown locked input")
    source = matches[0]
    source_path = Path(source["path"])
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != source["sha256"]:
        raise RuntimeError("Raw FBX hash mismatch")
    output = RUN / (case_id + "_" + attempt + "_import.json")
    destination = "/Game/HeadshotNormalProbe/" + case_id + "_" + attempt
    pipeline_path = "/Game/HeadshotNormalProbe/Pipelines/P_" + case_id + "_" + attempt
    if output.exists() or unreal.EditorAssetLibrary.does_directory_exist(destination):
        raise RuntimeError("Refusing to overwrite an import attempt")
    report = {"success": False, "case_id": case_id, "attempt": attempt, "source": source,
              "project": str(PROJECT), "destination": destination,
              "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "engine_version": unreal.SystemLibrary.get_engine_version(),
              "scope": "Isolated split import with existing pipeline defaults; no material or visual acceptance"}

    def phase(name):
        report["phase"] = name
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        unreal.log("Headshot normal probe: " + case_id + " " + name)

    try:
        phase("configure_pipeline")
        default_pipeline = unreal.load_asset("/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline")
        if default_pipeline is None:
            raise RuntimeError("Could not load the engine pipeline object")
        folder, name = pipeline_path.rsplit("/", 1)
        pipeline = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, folder, default_pipeline)
        if pipeline is None:
            raise RuntimeError("Could not duplicate isolated import pipeline")
        mesh = pipeline.get_editor_property("mesh_pipeline")
        common = pipeline.get_editor_property("common_skeletal_meshes_and_animations_properties")
        normals = pipeline.get_editor_property("common_meshes_properties")
        animation_only = bool(manifest.get("animation_only", False))
        target_skeleton = None
        if animation_only:
            skeleton_path = manifest.get("target_skeleton", "")
            if not skeleton_path.startswith("/Game/HeadshotNormalProbe/"):
                raise RuntimeError("Animation-only import requires an isolated target skeleton")
            target_skeleton = unreal.load_asset(skeleton_path)
            if not isinstance(target_skeleton, unreal.Skeleton):
                raise RuntimeError("Target skeleton could not be loaded")
        if "recompute_normals" in manifest:
            normals.set_editor_property("recompute_normals", bool(manifest["recompute_normals"]))
        if "recompute_tangents" in manifest:
            normals.set_editor_property("recompute_tangents", bool(manifest["recompute_tangents"]))
        mesh.set_editor_property("import_skeletal_meshes", not animation_only)
        mesh.set_editor_property("import_static_meshes", False)
        mesh.set_editor_property("combine_skeletal_meshes_behavior", unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE)
        mesh.set_editor_property("import_morph_targets", True)
        if "morph_threshold_position" in manifest:
            mesh.set_editor_property("morph_threshold_position", float(manifest["morph_threshold_position"]))
        mesh.set_editor_property("create_physics_asset", False)
        mesh.set_editor_property("physics_asset", None)
        mesh.set_editor_property("skeletal_mesh_import_content_type", unreal.InterchangeSkeletalMeshContentType.ALL)
        common.set_editor_property("skeleton", target_skeleton)
        common.set_editor_property("try_auto_select_skeleton", False)
        common.set_editor_property("import_only_animations", animation_only)
        import_animations = animation_only or bool(manifest.get("import_animations", False))
        pipeline.get_editor_property("animation_pipeline").set_editor_property("import_animations", import_animations)
        material = pipeline.get_editor_property("material_pipeline")
        material.set_editor_property("import_materials", False)
        material.get_editor_property("texture_pipeline").set_editor_property("import_textures", False)
        report["settings"] = {
            "combine": "DO_NOT_COMBINE", "import_morph_targets": True,
            "materials": False, "textures": False, "animations": import_animations,
            "recompute_normals": normals.get_editor_property("recompute_normals"),
            "recompute_tangents": normals.get_editor_property("recompute_tangents"),
            "morph_threshold_position": mesh.get_editor_property("morph_threshold_position"),
            "animation_only": animation_only,
            "target_skeleton": target_skeleton.get_path_name() if target_skeleton else None,
        }
        if not unreal.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False):
            raise RuntimeError("Could not save isolated pipeline")
        if unreal.SystemLibrary.get_console_variable_int_value("Interchange.FeatureFlags.Import.FBX") != 1:
            raise RuntimeError("Interchange FBX must already be enabled")
        manager = unreal.InterchangeManager.get_interchange_manager_scripted()
        source_data = manager.create_source_data(str(source_path))
        params = unreal.ImportAssetParameters()
        params.set_editor_property("is_automated", True)
        params.set_editor_property("force_show_dialog", False)
        params.set_editor_property("replace_existing", False)
        params.set_editor_property("override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())])
        phase("importing_fbx")
        objects = manager.import_asset(destination, source_data, params) or []
        report["returned_objects"] = [x.get_path_name() for x in objects]
        phase("saving_and_inspecting")
        if not unreal.EditorAssetLibrary.save_directory(destination, only_if_is_dirty=False, recursive=True):
            raise RuntimeError("Could not save isolated imported assets")
        subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        records = []
        for path in unreal.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False):
            asset = unreal.load_asset(path)
            row = {"path": path, "name": asset.get_name(), "class": asset.get_class().get_name()}
            if isinstance(asset, unreal.SkeletalMesh):
                morphs = [str(x.get_name()) for x in asset.get_editor_property("morph_targets") if x is not None]
                row.update(morph_names=sorted(morphs), morph_count=len(morphs),
                           lod_count=subsystem.get_lod_count(asset), lod0_vertices=subsystem.get_num_verts(asset, 0),
                           skeleton=asset.get_editor_property("skeleton").get_path_name())
            if isinstance(asset, unreal.AnimSequence):
                row.update(skeleton=asset.get_editor_property("skeleton").get_path_name(),
                           duration_seconds=float(asset.get_play_length()))
            records.append(row)
        report["assets"] = records
        skeletal = [x for x in records if x["class"] == "SkeletalMesh"]
        expected_count = 0 if animation_only else int(manifest.get("expected_skeletal_mesh_count", 6))
        if len(skeletal) != expected_count or any(x["lod0_vertices"] <= 0 for x in skeletal):
            raise RuntimeError("Unexpected nonempty imported skeletal mesh count")
        if not animation_only and not any(x["morph_count"] > 0 for x in skeletal):
            raise RuntimeError("No imported morphs; comparison would be invalid")
        if import_animations and not any(x["class"] == "AnimSequence" for x in records):
            raise RuntimeError("Motion import requested but no animation imported")
        if animation_only and any(x['skeleton'] != target_skeleton.get_path_name() for x in records if x['class'] == 'AnimSequence'):
            raise RuntimeError("Animation imported onto an unexpected skeleton")
        report["geometry_query_methods"] = [n for n in dir(unreal.GeometryScript_MeshQueries) if not n.startswith("_")]
        report["source_unchanged"] = hashlib.sha256(source_path.read_bytes()).hexdigest() == source["sha256"]
        if not report["source_unchanged"]:
            raise RuntimeError("Raw input changed during import")
        report["success"] = True
        phase("import_inspection_complete")
    except Exception:
        report["error"] = traceback.format_exc()
        phase("failed")
        raise


def morph_probe():
    """Audit actual saved LOD0 deltas through the isolated read-only C++ module."""
    output = RUN / (run_tag() + "_morphs.json")
    if output.exists():
        raise RuntimeError("Refusing to overwrite morph evidence")
    report = dict(success=False, meshes=[], comparisons=[],
                  scope="Stored LOD0 position/normal deltas after reload; no pose or visual acceptance",
                  engine_version=unreal.SystemLibrary.get_engine_version(),
                  implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    try:
        api = getattr(unreal, "HeadshotMorphProbeLibrary", None)
        if api is None:
            raise RuntimeError("Read-only morph probe plugin unavailable")
        inputs, records = {}, {}
        for case in ("reload_0", "reload_1"):
            path = RUN / (case + "_" + attempt_name() + "_import.json")
            imported = json.loads(path.read_text(encoding="utf-8"))
            if not imported["success"] or not imported["source_unchanged"]:
                raise RuntimeError("Failed import prerequisite")
            inputs[case] = imported
            records[case] = {}
            for item in imported["assets"]:
                if item["class"] != "SkeletalMesh":
                    continue
                mesh = unreal.load_asset(item["path"])
                row = json.loads(api.audit_morphs(mesh))
                if not row["success"]:
                    raise RuntimeError("Cannot read stored morph deltas: " + str(row))
                row.update(case=case, name=item["name"])
                if sorted(m["name"] for m in row["morphs"]) != item["morph_names"]:
                    raise RuntimeError("Reloaded morph inventory differs from import")
                row["finite_and_valid_indices"] = all(
                    m["nonfinite_position_components"] == 0 and m["nonfinite_normal_components"] == 0
                    and m["invalid_source_indices"] == 0 for m in row["morphs"])
                row["normal_components_within_unit_delta_bound"] = all(
                    m["max_normal_component"] <= 2.001 for m in row["morphs"])
                records[case][item["name"]] = row
                report["meshes"].append(row)
                output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        expected = int(json.loads((RUN / "inputs.json").read_text(encoding="utf-8")).get("expected_skeletal_mesh_count", 6))
        if len(records["reload_0"]) != expected or records["reload_0"].keys() != records["reload_1"].keys():
            raise RuntimeError("Mesh inventory mismatch")
        for name in sorted(records["reload_0"]):
            pair = [records[c][name] for c in ("reload_0", "reload_1")]
            maps = [{m["name"]: m for m in row["morphs"]} for row in pair]
            shared = sorted(maps[0].keys() & maps[1].keys())
            different = [n for n in shared if maps[0][n] != maps[1][n]]
            report["comparisons"].append(dict(name=name,
                inventories_equal=maps[0].keys() == maps[1].keys(),
                morph_count=len(maps[0]), different_morphs=different,
                all_stored_deltas_exact_equal=maps[0] == maps[1]))
        required = ["CTRL_expressions_eyeBlinkL", "CTRL_expressions_eyeBlinkR", "CTRL_expressions_jawOpen",
                    "CTRL_expressions_mouthCornerPullL", "CTRL_expressions_mouthCornerPullR"]
        body = {m["name"]: m for m in records["reload_0"]["cc_base_body"]["morphs"]}
        report["representative_body_morphs"] = {n: body.get(n) for n in required}
        report["representative_body_morphs_nonempty"] = all(
            n in body and body[n]["delta_count"] > 0 and body[n]["max_position_component_cm"] > 0 for n in required)
        report["all_stored_deltas_exact_equal"] = all(c["all_stored_deltas_exact_equal"] for c in report["comparisons"])
        report["all_stored_deltas_finite_and_index_valid"] = all(r["finite_and_valid_indices"] for r in report["meshes"])
        report["all_normal_components_within_unit_delta_bound"] = all(r["normal_components_within_unit_delta_bound"] for r in report["meshes"])
        report["raw_sources_unchanged"] = all(
            hashlib.sha256(Path(r["source"]["path"]).read_bytes()).hexdigest() == r["source"]["sha256"] for r in inputs.values())
        report["success"] = True
    except Exception:
        report["error"] = traceback.format_exc()
        raise
    finally:
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def animation_probe():
    output = RUN / (run_tag() + '_animation.json')
    if output.exists():
        raise RuntimeError('Refusing to overwrite animation audit')
    imported = json.loads((RUN / ('reload_0_' + attempt_name() + '_import.json')).read_text(encoding='utf-8'))
    if not imported['success']:
        raise RuntimeError('Import prerequisite failed')
    report = dict(success=False, animations=[], meshes=[],
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    try:
        for item in imported['assets']:
            if item['class'] == 'SkeletalMesh':
                report['meshes'].append(dict(name=item['name'], morph_names=item['morph_names']))
            if item['class'] != 'AnimSequence':
                continue
            asset = unreal.load_asset(item['path'])
            names = unreal.AnimationLibrary.get_animation_curve_names(asset, unreal.RawCurveTrackTypes.RCT_FLOAT)
            row = dict(path=item['path'], duration=asset.get_play_length(), curves=[],
                bone_track_names=[str(x) for x in asset.data_model_interface.get_bone_track_names()])
            for name in names:
                times, values = unreal.AnimationLibrary.get_float_keys(asset, name)
                row['curves'].append(dict(name=str(name), times=[float(x) for x in times], values=[float(x) for x in values]))
            report['animations'].append(row)
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')


def main():
    if Path(unreal.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError("Headshot normal probe requires its isolated project")
    mode = globals().get("DM_HS_NORMAL_MODE", "api")
    if mode == "animation":
        return animation_probe()
    if mode == "geometry_api":
        return geometry_api()
    if mode == "geometry":
        return geometry_probe()
    if mode == "morphs":
        return morph_probe()
    if mode == "import":
        return import_case(globals().get("DM_HS_NORMAL_CASE"))
    if mode != "api":
        raise ValueError("Unsupported probe mode")
    output = RUN / "api_probe.json"
    if output.exists():
        raise RuntimeError("Refusing to overwrite API evidence")
    report = {"success": False, "project": str(PROJECT), "mode": mode,
              "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "engine_version": unreal.SystemLibrary.get_engine_version()}
    try:
        report["api_docs"] = {}
        queries = {
            "GeometryScript_SceneUtils": ["copy_mesh_from_component"],
            "GeometryScript_AssetUtils": ["copy_mesh_from_skeletal_mesh"],
            "GeometryScript_MeshQueries": ["get_all_vertex_positions", "get_triangle_normals", "get_all_triangle_ids"],
            "SkeletalMeshComponent": ["set_morph_target", "set_update_animation_in_editor", "set_position", "set_animation_mode"],
        }
        for class_name, names in queries.items():
            cls = getattr(unreal, class_name, None)
            report["api_docs"][class_name] = {name: getattr(getattr(cls, name, None), "__doc__", None) for name in names}
        default = unreal.load_asset("/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline")
        if default is None:
            raise RuntimeError("Default Interchange assets pipeline unavailable")
        report["pipeline_class"] = default.get_class().get_name()
        report["pipeline_properties"] = {}
        for key in ("mesh_pipeline", "common_meshes_properties", "common_skeletal_meshes_and_animations_properties"):
            obj = default.get_editor_property(key)
            report["pipeline_properties"][key] = {}
            names = [n for n in dir(obj) if any(t in n for t in ("normal", "tangent", "morph", "threshold", "skeletal"))]
            for name in names:
                try:
                    value = obj.get_editor_property(name)
                    report["pipeline_properties"][key][name] = str(value)
                except Exception:
                    pass
        report["success"] = True
    except Exception:
        report["error"] = traceback.format_exc()
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
