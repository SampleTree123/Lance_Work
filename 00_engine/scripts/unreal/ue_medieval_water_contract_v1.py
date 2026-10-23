"""Finite Medieval derived WaterInfoMesh identity contract.

Copy this independent module beside the relocation helper after review. It has
no runtime dependency on TEMP collectors, never changes a live object, and
never installs a global path alias. Only one comparison-copy mesh field changes.
"""
import copy
import json
from pathlib import Path

ROOT = '/Game/Medieval_Environment'
MAP = ROOT + '/Asset/Level/Castle_medieval_Map'
DESTINATION = '/Game/Scenes/Medieval_Environment'
OWNER = MAP + '.Castle_medieval_Map:PersistentLevel.WaterBodyOcean_1'
SOURCE_MESH = OWNER + '.WaterInfoMesh_3'
TARGET_MESH = OWNER + '.WaterInfoMesh_6'
ACTOR_CLASS = '/Script/Water.WaterBodyOcean'
COMPONENT_CLASS = '/Script/Water.WaterBodyInfoMeshComponent'
COMPONENT = 'WaterInfoMeshComponent'
COLLECTOR_SHA = '2cc1f1235053f21720a85d555b22369367a94b751ba04c8867aa60b8cfb98742'
RECEIPT_PINS = {
    'baseline_Medieval_Environment_v1.json': '47c6379783f801cdf37a146894efe0eb4e7d118ecd3d6967c90d829cdffd2bff',
    'cold_baseline_Medieval_Environment_v1.json': 'c209ebea1dcbfc811c89e592dbc280ab8649308723eb63b3b1c887035a0e29d8',
    'medieval_original_water_load_witness_v1.json': '0eb1541cd314e8b654ece6aca61c116024f52edea835f1ae54e4e239a817d749',
    'medieval_original_water_geometry_supplement_v2.json': '35e6273ca911cccae6cab85171af9f0ba1a6a248708c18a3615f2a6bd277c8b9',
    'medieval_target_water_geometry_v2.json': 'b7d59e5e6d3ee90237742f70c3c24b846d60366dd32b7bb2716a395a5768d233',
    'backup_manifest_v1.json': '8f6013c9a09d3dbca5cdcd6946aeb93308b17d69bd17020d0dce03fef198ccb1',
}
ENGINE_PINS = {
    'Build/Build.version': 'd35d3d5f4de0636fbb62386b63dee8056889fb2baf199d012dc32ee77f7a2997',
    'Plugins/Experimental/Water/Source/Runtime/Private/WaterBodyMeshBuilder.cpp': '925fff859c9b4b47dcdcb736208893269e60c8c9fd985211962e6ef9f4340a1b',
    'Plugins/Experimental/Water/Source/Runtime/Private/WaterBodyComponent.cpp': 'a06415c267533a27a95c78dea1fa8183232c6353252efc24a3ca9cda8f2191b5',
    'Plugins/Experimental/Water/Source/Runtime/Public/WaterEditorServices.h': '4c7589a64f3eda20750a3b440478571e1040b278f3263a9ff3b86680e929ce4f',
}


def require(condition, reason):
    if not condition:
        raise RuntimeError('Medieval WaterInfoMesh contract: ' + reason)


def exact(m, left, right):
    # The existing fully qualified object-path case equivalence remains the
    # only normalization. No float tolerance or material/transform relaxation.
    return m.normalize_object_path_case(left) == m.normalize_object_path_case(right)


def water_component(signature):
    require(signature['map'].casefold() == MAP.casefold() and signature['actor_count'] == 3667
            and len(signature['actors']) == 3667, 'wrong map/actor coverage')
    actors = [a for a in signature['actors'] if a['name'] == 'WaterBodyOcean_1']
    require(len(actors) == 1 and actors[0]['class'] == ACTOR_CLASS, 'wrong unique owner')
    components = [c for c in actors[0]['components'] if c['name'] == COMPONENT]
    require(len(components) == 1, 'wrong unique component')
    return components[0]


def check_water_identity(m, water, destination):
    owner = OWNER.replace(ROOT, DESTINATION, 1) if destination else OWNER
    mesh_name = 'WaterInfoMesh_6' if destination else 'WaterInfoMesh_3'
    expected = {'owner': owner, 'owner_class': ACTOR_CLASS,
        'component': owner + '.' + COMPONENT, 'component_name': COMPONENT,
        'component_class': COMPONENT_CLASS, 'mesh': owner + '.' + mesh_name,
        'mesh_name': mesh_name, 'mesh_class': '/Script/Engine.StaticMesh', 'mesh_outer': owner}
    require(exact(m, {k: water[k] for k in expected}, expected), 'wrong derived mesh/owner/component identity')
    geometry = water['geometry']
    require(geometry['available'] is True and geometry['value']['copy_outcome'] == 'SUCCESS', 'complete geometry missing')
    g = geometry['value']
    require(g['schema'] == 'water_derived_source_model_geometry_v2' and g['lod_type'] == 'SOURCE_MODEL'
            and g['lod_index'] == 0 and g['vertex_count'] == g['num_vertex_ids'] == len(g['vertices']) == 124
            and g['num_triangle_ids'] == len(g['triangles']) == 122 and g['num_uv_sets'] == 3,
            'wrong complete geometry coverage')
    for key in ('bounds', 'num_lods', 'editor_lod_count', 'lod0_vertices', 'lod0_triangles',
                'lod0_sections', 'build_settings_lod0'):
        require(water['descriptor'][key]['available'] is True, 'public descriptor missing: ' + key)


def read_evidence(m):
    receipts = {}
    for name, digest in RECEIPT_PINS.items():
        path = m.RUN / name
        require(path.is_file() and m.sha(path) == digest, 'receipt SHA changed/missing: ' + name)
        receipts[name] = json.loads(path.read_text(encoding='utf-8-sig'))
    engine = Path('D:/UE/UE_5.8/Engine')
    for relative, digest in ENGINE_PINS.items():
        require(m.sha(engine / relative) == digest, 'official source/build SHA changed: ' + relative)
    warm = receipts['baseline_Medieval_Environment_v1.json']
    cold = receipts['cold_baseline_Medieval_Environment_v1.json']
    loads = receipts['medieval_original_water_load_witness_v1.json']
    source = receipts['medieval_original_water_geometry_supplement_v2.json']
    target = receipts['medieval_target_water_geometry_v2.json']
    manifest = receipts['backup_manifest_v1.json']
    require(all(x['success'] is True and x['root'] == ROOT for x in (warm, cold, loads, source, target)), 'invalid receipt root/success')
    require(source['schema'] == 'medieval_original_water_geometry_supplement_v2'
            and target['schema'] == 'medieval_target_water_geometry_v2', 'wrong supplemental schema')
    require(source['saved_source_assets'] is False and source['dirty'] == []
            and loads['saved_source_assets'] is False and cold['saved_source_assets'] is False
            and target['saved_scene_assets'] is False and target['camera_render_started'] is False,
            'source/target saving or camera work not excluded')
    require(source['source_witness_sha256'] == RECEIPT_PINS['medieval_original_water_load_witness_v1.json']
            and source['cold_baseline_sha256'] == RECEIPT_PINS['cold_baseline_Medieval_Environment_v1.json']
            and target['collector']['sha256'] == COLLECTOR_SHA, 'receipt cross-pins differ')
    require(len(warm['assets']) == len(cold['assets']) == 516 and len(warm['maps']) == len(cold['maps']) == 1
            and m.registry_identities(warm['assets']) == m.registry_identities(cold['assets']), 'original registry coverage differs')
    require(exact(m, warm['maps'][0], source['signature']) and exact(m, cold['maps'][0], source['signature'])
            and warm['component_transforms'][MAP] == cold['component_transforms'][MAP] == source['component_transforms'],
            'warm/cold/source signature or relative transforms differ')
    proof = source['source_proof_before']
    require(proof == source['source_proof_after'] == loads['source_proof_before'] == loads['source_proof_after']
            == cold['source_proof_before'] == cold['source_proof_after'] and proof['root'] == ROOT
            and proof['success'] is True and proof['manifest_sha256'] == RECEIPT_PINS['backup_manifest_v1.json'],
            'original source proof differs')
    original = (m.PROJECT / 'Content/Medieval_Environment').resolve()
    expected = []
    for row in manifest['files']:
        try:
            relative = Path(row['source']).resolve().relative_to(original).as_posix()
        except ValueError:
            continue
        backup = Path(row['backup'])
        require(backup.is_file() and backup.stat().st_size == row['bytes'] and m.sha(backup) == row['sha256'],
                'original backup bytes/SHA changed: ' + relative)
        expected.append({'relative': relative, 'bytes': row['bytes'], 'sha256': row['sha256']})
    require(len(expected) == 516 and sorted(expected, key=lambda r: r['relative']) == proof['files'], 'full 516-file coverage differs')
    require(len(loads['loads']) == 4, 'four original captures missing')
    check_water_identity(m, source['water'], False)
    for load in loads['loads']:
        require(exact(m, load['signature'], source['signature']) and load['component_transforms'] == source['component_transforms']
                and load['dirty'] == [] and exact(m, load['water']['descriptor'], source['water']['descriptor']),
                'original repeated capture varies')
        # The immutable first collector explicitly reported unavailable geometry;
        # complete geometry is supplied by the pinned supplemental receipt.
        require(load['water']['mesh'] == SOURCE_MESH, 'unexpected original mesh name')
    require(target['map'] == DESTINATION + MAP[len(ROOT):], 'wrong target actual map')
    check_water_identity(m, target['water'], True)
    require(exact(m, source['water']['descriptor'], target['water']['descriptor'])
            and source['water']['geometry'] == target['water']['geometry'], 'source/target material/descriptor/geometry differs')
    comparison = copy.deepcopy(target['signature'])
    require(water_component(comparison)['mesh'].casefold() == TARGET_MESH.casefold(), 'wrong canonical target mesh')
    water_component(comparison)['mesh'] = SOURCE_MESH
    require(exact(m, comparison, source['signature']) and target['component_transforms'] == source['component_transforms'],
            'target changed beyond the exact derived mesh name')
    return {'warm': warm, 'cold': cold, 'source': source, 'target': target}


def geometry_capture(u, mesh):
    """Actual successful UE 5.8 public bindings, complete SourceModel LOD0."""
    dynamic = u.DynamicMesh()
    options = u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False, request_tangents=True,
        ignore_remove_degenerates=False, use_build_scale=False)
    lod = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL, lod_index=0)
    copied = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod, False)
    require(isinstance(copied, tuple) and copied[-1] == u.GeometryScriptOutcomePins.SUCCESS, 'live geometry copy failed')
    q = u.GeometryScript_MeshQueries

    def plain(value):
        if value is dynamic:
            return {'returned_target_mesh': True}
        if isinstance(value, (bool, int, float, str)) or value is None:
            return value
        if isinstance(value, (tuple, list)):
            return [plain(x) for x in value]
        if isinstance(value, u.Object):
            raise RuntimeError('Unexpected geometry UObject')
        if hasattr(value, 'x') and hasattr(value, 'y'):
            return [float(getattr(value, k)) for k in ('x', 'y', 'z') if hasattr(value, k)]
        if hasattr(value, 'export_text'):
            return value.export_text()
        raise RuntimeError('Unsupported geometry result ' + str(type(value)))

    vertex_count, vertex_ids = q.get_vertex_count(dynamic), q.get_num_vertex_i_ds(dynamic)
    triangle_ids, uv_count = q.get_num_triangle_i_ds(dynamic), q.get_num_uv_sets(dynamic)
    require(vertex_count > 0 and triangle_ids > 0, 'live geometry empty')
    vertices = [[i, plain(q.get_vertex_position(dynamic, i))] for i in range(vertex_ids) if q.is_valid_vertex_id(dynamic, i)]
    triangles = []
    for i in range(triangle_ids):
        if q.is_valid_triangle_id(dynamic, i):
            triangles.append({'id': i, 'indices': plain(q.get_triangle_indices(dynamic, i)),
                'positions': plain(q.get_triangle_positions(dynamic, i)),
                'normal_tangents': plain(q.get_triangle_normal_tangents(dynamic, i)),
                'colors': plain(q.get_triangle_vertex_colors(dynamic, i)),
                'uvs': [plain(q.get_triangle_u_vs(dynamic, channel, i)) for channel in range(uv_count)],
                'material_id': plain(u.GeometryScript_Materials.get_triangle_material_id(dynamic, i))})
    names = {'GetVertexCount': 'get_vertex_count', 'GetNumVertexIDs': 'get_num_vertex_i_ds',
        'GetNumTriangleIDs': 'get_num_triangle_i_ds', 'GetNumUVSets': 'get_num_uv_sets',
        'IsValidVertexID': 'is_valid_vertex_id', 'GetVertexPosition': 'get_vertex_position',
        'IsValidTriangleID': 'is_valid_triangle_id', 'GetTriangleIndices': 'get_triangle_indices',
        'GetTrianglePositions': 'get_triangle_positions', 'GetTriangleNormalTangents': 'get_triangle_normal_tangents',
        'GetTriangleVertexColors': 'get_triangle_vertex_colors', 'GetTriangleUVs': 'get_triangle_u_vs',
        'GetTriangleMaterialID': 'get_triangle_material_id'}
    return {'schema': 'water_derived_source_model_geometry_v2',
        'scope': 'Complete SourceModel LOD0 vertices/topology/corner normals/tangents/colors/all UV channels/material IDs. No build settings applied; not a full serialized StaticMesh claim.',
        'lod_type': 'SOURCE_MODEL', 'lod_index': 0, 'copy_outcome': 'SUCCESS',
        'vertex_count': vertex_count, 'num_vertex_ids': vertex_ids, 'num_triangle_ids': triangle_ids,
        'num_uv_sets': uv_count, 'vertices': vertices, 'triangles': triangles,
        'public_query_bindings': {k: {'surface': 'library', 'python_name': v} for k, v in names.items()}}


def capture_water(u, m):
    actors = [a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_name() == 'WaterBodyOcean_1']
    require(len(actors) == 1 and actors[0].get_class().get_path_name() == ACTOR_CLASS, 'live owner differs')
    actor = actors[0]
    components = [c for c in actor.get_components_by_class(u.StaticMeshComponent) if c.get_name() == COMPONENT]
    require(len(components) == 1 and components[0].get_class().get_path_name() == COMPONENT_CLASS, 'live component differs')
    c = components[0]
    mesh = c.get_editor_property('static_mesh')
    require(mesh is not None and mesh.get_class().get_path_name() == '/Script/Engine.StaticMesh' and mesh.get_outer() == actor, 'live derived mesh differs')
    editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)

    def optional(call):
        try:
            return {'available': True, 'value': call()}
        except Exception as exc:
            return {'available': False, 'error': type(exc).__name__ + ': ' + str(exc)}

    return {'owner': actor.get_path_name(), 'owner_class': actor.get_class().get_path_name(),
        'component': c.get_path_name(), 'component_name': c.get_name(), 'component_class': c.get_class().get_path_name(),
        'mesh': mesh.get_path_name(), 'mesh_name': mesh.get_name(), 'mesh_class': mesh.get_class().get_path_name(),
        'mesh_outer': mesh.get_outer().get_path_name(),
        'flags': {'available': False, 'reason': 'No exposed public UObject flag API assumed; no private reflection'},
        'descriptor': {'bounds': optional(lambda: mesh.get_bounds().export_text()),
            'num_lods': optional(lambda: mesh.get_num_lods()), 'editor_lod_count': optional(lambda: editor.get_lod_count(mesh)),
            'lod0_vertices': optional(lambda: editor.get_number_verts(mesh, 0)),
            'lod0_triangles': optional(lambda: mesh.get_num_triangles(0)), 'lod0_sections': optional(lambda: mesh.get_num_sections(0)),
            'build_settings_lod0': optional(lambda: editor.get_lod_build_settings(mesh, 0).export_text()),
            'conservative_raster_compatible': optional(lambda: bool(c.get_editor_property('is_conservative_raster_compatible'))),
            'materials': [m.material_signature(u, c.get_material(i), ROOT) for i in range(c.get_num_materials())]},
        'geometry': {'available': True, 'value': geometry_capture(u, mesh)}}


def compare_live(m, evidence, before, after, relative, water):
    source, target = evidence['source'], evidence['target']
    require(exact(m, before, source['signature']), 'selected source signature differs')
    require(exact(m, after, target['signature']), 'current target signature differs from pinned receipt')
    require(relative == source['component_transforms'] == target['component_transforms'], 'current relative transforms differ')
    check_water_identity(m, water, True)
    require(exact(m, water, target['water']), 'current complete geometry/descriptor/identity differs')
    comparison = copy.deepcopy(after)
    require(water_component(comparison)['mesh'].casefold() == TARGET_MESH.casefold(), 'current mesh is outside exact pair')
    water_component(comparison)['mesh'] = SOURCE_MESH
    require(exact(m, comparison, before), 'current target differs beyond one mesh field')
    return comparison


def validated_map_signature(u, m, root, base_path, base, before, after):
    """Call between actual map/relative capture and generic compare_map.

    `after` must retain the helper's existing canonical-original-root format.
    No live references escape this function; raw `after` is never modified.
    """
    if root != ROOT:
        return after, None
    require(Path(base_path).resolve() == (m.RUN / 'baseline_Medieval_Environment_v1.json').resolve(), 'unexpected warm baseline path')
    evidence = read_evidence(m)
    require(base.get('success') is True and base['root'] == ROOT and len(base['assets']) == 516 and len(base['maps']) == 1
            and m.registry_identities(base['assets']) == m.registry_identities(evidence['warm']['assets'])
            and exact(m, base['maps'][0], before) and base['component_transforms'][MAP] == evidence['source']['component_transforms'],
            'selected baseline identities/coverage differ')
    require(not m.dirty(u), 'current editor is dirty')
    relative = m.component_transforms(u)
    water = capture_water(u, m)
    require(not m.dirty(u), 'current geometry capture dirtied editor')
    comparison = compare_live(m, evidence, before, after, relative, water)
    witness = {'schema': 'medieval_water_derived_name_validated_v1',
        'source_mesh': SOURCE_MESH, 'canonical_target_mesh': TARGET_MESH,
        'receipt_pins': dict(RECEIPT_PINS), 'engine_source_pins': dict(ENGINE_PINS),
        'actual_water': water, 'module_sha256': m.sha(__file__),
        'scope': 'Only Castle_medieval_Map/WaterBodyOcean_1/WaterInfoMeshComponent.mesh comparison copy: exact WaterInfoMesh_6 to WaterInfoMesh_3. Full live LOD0 geometry/material/descriptor and all other map/relative fields remain strict.'}
    return comparison, witness
