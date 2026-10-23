"""One original support mesh identity roundtrip; no lash application/repair.

Whole-avatar native OBJ supplies original face-corner UV/normals; a unique
support group is extracted with complete v/vt/vn reindexing. Vertices are
replaced by separately cross-checked active SubD0 world queries, matching the
proven hair/body template strategy. Native OBJ positions belong to another
pose/coordinate domain and are measured, never mistaken for active SDK world.
"""
import hashlib
import json
import math
import os
import shutil
import sys
import traceback
import types

TARGETS = {
    ('5', 'CC_Base_EyeOcclusion', 182): (144, '768c25657bf625b4b10b9c7e8293296cee4cbe2131bd13cf12d2239a32a12019'),
    ('6', 'CC_Base_TearLine', 190): (136, '53606b3425e1c4a27874c4125c46aabb0980f2635c9640244d41d81f85a06edf')}


def extract_native_group(whole_path, output_path, name, count, expected_faces):
    """Extract source attributes unchanged; never generate UVs or normals.

    Global OBJ indices are independent for v/vt/vn. Negative indices resolve
    against the corresponding array size at that exact source face line.
    Vertex order is ascending source v ID and must match SDK faces exactly.
    """
    if os.path.exists(output_path): raise ValueError('Refuse existing extracted OBJ')
    arrays = {'v': [], 'vt': [], 'vn': []}
    rows = []; group = ''; block = 0; mtllibs = []; material = None; smoothing = None
    with open(whole_path, encoding='utf-8-sig') as handle:
        for line in handle:
            t = line.split()
            if not t or t[0].startswith('#'): continue
            if t[0] in arrays:
                arrays[t[0]].append(line if line.endswith('\n') else line + '\n')
            elif t[0] in ('g', 'o'):
                group = t[1] if len(t) == 2 else ''; block += 1
            elif t[0] == 'mtllib': mtllibs.append(line if line.endswith('\n') else line + '\n')
            elif t[0] == 'usemtl': material = ' '.join(t)
            elif t[0] == 's': smoothing = ' '.join(t)
            elif t[0] == 'f' and group == name:
                corners = []
                for token in t[1:]:
                    fields = token.split('/')
                    if len(fields) != 3 or any(not x or int(x) == 0 for x in fields):
                        raise ValueError('Whole-avatar support face lacks original v/vt/vn')
                    corners.append([int(x) if int(x) > 0 else len(arrays[k]) + int(x) + 1
                                    for k, x in zip(('v', 'vt', 'vn'), fields)])
                if len(corners) < 3: raise ValueError('Invalid source support polygon')
                rows.append({'corners': corners, 'block': block, 'material': material, 'smoothing': smoothing})
    if not rows or len({row['block'] for row in rows}) != 1:
        raise ValueError('One unique source support group required')
    ids = {k: sorted({corner[i] for row in rows for corner in row['corners']}) for i, k in enumerate(('v', 'vt', 'vn'))}
    for key, used in ids.items():
        if any(i <= 0 or i > len(arrays[key]) for i in used):
            raise ValueError('Support corner outside original OBJ ' + key + ' array')
    maps = {k: {value: index + 1 for index, value in enumerate(used)} for k, used in ids.items()}
    faces = [[maps['v'][corner[0]] - 1 for corner in row['corners']] for row in rows]
    if len(ids['v']) != count or faces != expected_faces:
        raise ValueError('Extracted support vertex order/topology differs from SDK')
    with open(output_path, 'w', encoding='utf-8') as handle:
        handle.write('# Exact unique support group extracted from native whole-avatar OBJ\n')
        for line in mtllibs: handle.write(line)
        handle.write('g ' + name + '\n')
        for key in ('v', 'vt', 'vn'):
            for index in ids[key]: handle.write(arrays[key][index - 1])
        previous_material = previous_smoothing = None
        for row in rows:
            if row['material'] != previous_material:
                if row['material'] is None: raise ValueError('Unsupported material-state reset within source group')
                handle.write(row['material'] + '\n'); previous_material = row['material']
            if row['smoothing'] != previous_smoothing:
                if row['smoothing'] is None: raise ValueError('Unsupported smoothing-state reset within source group')
                handle.write(row['smoothing'] + '\n'); previous_smoothing = row['smoothing']
            handle.write('f ' + ' '.join('/'.join(str(maps[k][corner[i]]) for i, k in enumerate(('v', 'vt', 'vn')))
                                       for corner in row['corners']) + '\n')
    parsed = parse_native_obj(output_path, name, count, expected_faces)
    return {'source_vertex_indices_1based': ids['v'], 'source_uv_indices_1based': ids['vt'],
            'source_normal_indices_1based': ids['vn'], 'face_count': len(rows), 'vertex_count': count,
            'uv_count': parsed['uv_count'], 'normal_count': parsed['normal_count'],
            'uv_normal_material_corner_sha256': parsed['uv_normal_material_corner_sha256'],
            'normals_generated': False, 'uv_generated': False, 'source_group_occurrences': 1}


def parse_native_obj(path, name, count, expected_faces):
    """Fail closed on omitted corner UV/normals or an ambiguous mesh export."""
    with open(path, encoding='utf-8-sig') as handle: lines = handle.readlines()
    vertices, texcoords, normals, polygons, payload, groups = [], [], [], [], [], set()
    group = ''
    for line in lines:
        t = line.split()
        if not t or t[0].startswith('#'): continue
        if t[0] in ('g', 'o'):
            group = t[1] if len(t) == 2 else ''
        elif t[0] in ('v', 'vt', 'vn'):
            values = [float(x) for x in t[1:]]
            expected = 2 if t[0] == 'vt' else 3
            if len(values) not in ((2, 3) if t[0] == 'vt' else (3,)) or not all(math.isfinite(x) for x in values):
                raise ValueError('Invalid native OBJ coordinate')
            {'v': vertices, 'vt': texcoords, 'vn': normals}[t[0]].append(values)
            if t[0] != 'v': payload.append([t[0], values])
        elif t[0] == 'f':
            groups.add(group)
            face = []
            for token in t[1:]:
                corner = token.split('/')
                if len(corner) != 3 or any(not x or int(x) <= 0 for x in corner):
                    raise ValueError('Native face must retain positive vertex/UV/normal corner indices')
                face.append([int(x) for x in corner])
            if len(face) < 3: raise ValueError('Invalid native OBJ polygon')
            polygons.append(face); payload.append(['f', face])
        elif t[0] in ('usemtl', 's'):
            payload.append(t)
    faces = [[corner[0] - 1 for corner in face] for face in polygons]
    if groups != {name} or len(vertices) != count or faces != expected_faces:
        raise ValueError('Native single-part OBJ differs from exact low support mesh topology/order')
    if not texcoords or not normals:
        raise ValueError('Native OBJ must expose both original UV and normals')
    for face in polygons:
        for vi, ti, ni in face:
            if vi > count or ti > len(texcoords) or ni > len(normals):
                raise ValueError('Native OBJ corner refers beyond available data')
    if any(sum(x*x for x in normal) <= 1e-20 for normal in normals):
        raise ValueError('Native OBJ has a zero normal')
    return {'lines': lines, 'vertices': vertices, 'faces': faces, 'uv_count': len(texcoords),
            'normal_count': len(normals), 'uv_normal_material_corner_sha256': hashlib.sha256(
                json.dumps(payload, separators=(',', ':')).encode()).hexdigest()}


def write_identity_world_obj(native, world, path):
    from cc_refresh_eyelash_probe_v2 import _distances
    error = max(_distances(native['vertices'], world))
    if os.path.exists(path): raise ValueError('Refuse existing identity OBJ')
    index = 0
    with open(path, 'w', encoding='utf-8') as handle:
        for line in native['lines']:
            if line.split()[:1] == ['v']:
                line = 'v {:.12f} {:.12f} {:.12f}\n'.format(*world[index]); index += 1
            handle.write(line)
    if index != len(world): raise ValueError('Identity vertex count changed')
    return {'native_obj_vs_sdk_world_max_mm': error, 'vertex_count': index,
            'native_obj_vs_sdk_world_is_acceptance_gate': False,
            'native_positions_scope': 'Native export pose/domain; topology/UV/normals template only',
            'submitted_positions_scope': 'Same-source active SubD0 SDK world; all scalar/reacquired reads verified',
            'normals_uv_faces_material_payload_copied': True, 'replace_uv': False}


def resolve_target(avatar, selector):
    key = (str(selector['part_type']), selector['mesh_name'], int(selector['vertex_count']))
    if key not in TARGETS: raise ValueError('Only one exact original low eye support allowed')
    found = []
    for part in avatar.GetAvatarParts() or []:
        if str(part.GetAvatarPartType()) == key[0] and str(part.GetName()) == key[1]:
            for mesh in part.GetMeshes(False) or []:
                if str(mesh.GetName()) == key[1] and int(mesh.GetVerticesCount()) == key[2]:
                    found.append((part, mesh))
    if len(found) != 1: raise ValueError('Ambiguous selected original support mesh')
    part, mesh = found[0]
    faces = [[int(x) for x in mesh.GetFace(i)] for i in range(mesh.GetFacesCount())]
    digest = hashlib.sha256(json.dumps(faces, separators=(',', ':')).encode()).hexdigest()
    if (len(faces), digest) != TARGETS[key]: raise ValueError('Selected support topology changed')
    return part, mesh, faces


def target_world(avatar, selector):
    from cc_refresh_eyelash_probe_v2 import _distances
    if int(avatar.GetSubdivMeshLevel()) != 0: raise ValueError('Active SubD0 world required')
    part, mesh, faces = resolve_target(avatar, selector)
    def points(values): return [[float(v.x), float(v.y), float(v.z)] for v in values]
    world = points(mesh.GetVertices(True))
    scalar = points(mesh.GetVertex(i, True) for i in range(mesh.GetVerticesCount()))
    repeated = points(resolve_target(avatar, selector)[1].GetVertices(True))
    scalar_error = max(_distances(world, scalar)); repeated_error = max(_distances(world, repeated))
    if max(scalar_error, repeated_error) > .001: raise ValueError('Target world readback inconsistent')
    return {'world': world, 'faces': faces, 'working_subdivision_level': 0,
            'scalar_world_max_error_mm': scalar_error, 'repeated_world_max_error_mm': repeated_error}


def run(library, output_dir, log, api):
    directory = os.path.dirname(__file__)
    if directory not in sys.path: sys.path.insert(0, directory)
    import cc_refresh_eyelash_probe_v2 as lash
    import cc_refresh_eye_support_diagnostic_v1 as queries
    import cc_repair_headshot_support_materials_v1 as capture
    import cc_capture_assembly_geometry_v1 as body_capture
    c = library['refresh_eye_support_identity']
    if (c.get('identity_only') is not True or c.get('save_current_scene_backup') is not True
            or c.get('replace_uv') is not False or c.get('apply_lash_asset') is not False
            or c.get('export_strategy') != 'whole_avatar_extract_sdk_world_identity_v3'
            or c.get('identity_input_space') != 'same_source_scalar_verified_active_sdk_world'):
        raise ValueError('Explicit identity-only/no-lash/UV-preserving/backup contract required')
    source = c['source_project']; evidence = c['persistence_diagnostic_report']
    if (not any(lash.inside(source['path'], r) for r in (lash.CREATION_ROOT, lash.RUN_ROOT, lash.STAGE_ROOT))
            or api.sha256_file(source['path']) != source['sha256']
            or not lash.inside(evidence['path'], lash.RUN_ROOT)
            or api.sha256_file(evidence['path']) != evidence['sha256']):
        raise ValueError('Locked source/diagnostic evidence changed')
    prior = api.read_json(evidence['path'])
    if (prior.get('capture_complete') is not True or prior.get('geometry_accepted') is not False
            or prior['source_project']['sha256'] != source['sha256']):
        raise ValueError('Identity probe must use unmodified source of completed diagnostic')
    failure = c['single_part_failure_report']
    if not lash.inside(failure['path'], lash.RUN_ROOT) or api.sha256_file(failure['path']) != failure['sha256']:
        raise ValueError('Single-part failure evidence changed')
    failed = api.read_json(failure['path'])
    if (failed.get('success') is not False or failed.get('replace_status') is not None
            or failed.get('restored_source') is not True
            or failed['source_project']['sha256'] != source['sha256']
            or 'status_code' not in failed.get('error', {}).get('message', '')
            or "'7'" not in failed['error']['message']):
        raise ValueError('Expected actual pre-Replace single-part export failure required')
    mismatch = c['native_activeworld_mismatch_report']
    if not lash.inside(mismatch['path'], lash.RUN_ROOT) or api.sha256_file(mismatch['path']) != mismatch['sha256']:
        raise ValueError('Native/activeworld mismatch evidence changed')
    mismatched = api.read_json(mismatch['path'])
    exported = [s for s in mismatched.get('steps', []) if s.get('phase') == 'post_source_export']
    if (mismatched.get('success') is not False or mismatched.get('replace_status') is not None
            or mismatched.get('restored_source') is not True
            or mismatched['source_project']['sha256'] != source['sha256']
            or mismatched.get('error', {}).get('message') != 'Native export and active scalar-verified SDK world disagree beyond0.002mm'
            or len(exported) != 1 or exported[0].get('passed') is not True):
        raise ValueError('Exact restored pre-Replace mismatch with source-export protection pass required')
    if not lash.inside(output_dir, lash.RUN_ROOT) or os.path.realpath(output_dir) == os.path.realpath(lash.RUN_ROOT):
        raise ValueError('Independent output child required')
    if os.path.exists(output_dir) and os.listdir(output_dir): raise ValueError('Refuse existing identity outputs')
    os.makedirs(output_dir, exist_ok=True)
    rp = os.path.join(output_dir, 'eye_support_identity_report.json'); sp = os.path.join(output_dir, 'validation_result.json')
    report = {'schema_version': 1, 'success': False, 'identity_only': True, 'geometry_repair_accepted': False,
        'source_project': source, 'persistence_diagnostic_report': evidence, 'target': c['target'],
        'single_part_failure_report': failure, 'export_strategy': c['export_strategy'],
        'native_activeworld_mismatch_report': mismatch, 'identity_input_space': c['identity_input_space'],
        'replace_uv': False, 'material_pixels_verified': False, 'steps': [],
        'implementation_sha256': api.sha256_file(__file__), 'report_path': rp, 'summary_path': sp,
        'dependencies': {name: api.sha256_file(os.path.join(directory, name)) for name in
            ('cc_refresh_eye_support_diagnostic_v1.py', 'cc_refresh_eyelash_probe_v2.py',
             'cc_repair_headshot_support_materials_v1.py', 'cc_capture_assembly_geometry_v1.py')},
        'normal_uv_validation': 'Native OBJ original face-corner UV/normal payload copied; independently re-exported and strictly compared after replacement and reload. No material writes.',
        'scope': 'Single original low support identity only; native whole-avatar export/exact group extraction; no lash application, no true repair, no subdivision switching.'}
    R = api.RLPy; raw_api = types.SimpleNamespace(_transform_data=api._transform_data)
    working = None; baseline = None; attempted = False
    def checkpoint(phase):
        report['phase'] = phase; report['updated_at'] = api.now(); api.write_json(report, rp); log('Support identity: ' + phase)
    def avatar():
        items = list(R.RScene.GetAvatars() or [])
        if len(items) != 1: raise ValueError('One independent avatar required')
        return items[0]
    def load(record, label):
        if api.sha256_file(record['path']) != record['sha256']: raise ValueError('Load SHA changed')
        status, dialogs = api.load_file_with_optional_undo_warning(record['path'], label)
        report.setdefault('loads', []).append({'label': label, 'status': status, 'dialogs': dialogs})
        R.RScene.SelectObject(avatar())
    def snapshot(label):
        a = avatar()
        full = capture.capture_geometry(a, api=raw_api)
        result = {'geometry': full, 'body': body_capture.capture_body_snapshot(a, api=raw_api, include_world=True),
            'support_readbacks': queries.query_support_levels(a), 'target_world': target_world(a, c['target']),
            'eye': api.capture_eye_integrity_state(a), 'weights': api.capture_eye_part_morph_weights(a),
            'materials': api.avatar_material_fingerprint(a)}
        if result['body']['scene_explicitly_settled']: raise ValueError('Unexpected evaluation in raw capture')
        api.write_json(result, os.path.join(output_dir, label + '_snapshot.json'))
        return result
    def gate(label, actual):
        geometry = capture.compare_geometry(baseline['geometry'], actual['geometry'])
        body_local = max(lash._distances(baseline['body']['local'], actual['body']['local']))
        body_world = max(lash._distances(baseline['body']['world'], actual['body']['world']))
        target_error = max(lash._distances(baseline['target_world']['world'], actual['target_world']['world']))
        eye = api.compare_neutral_eye_states(baseline['eye'], actual['eye'], tolerance=.0002,
            include_world=True, include_runtime_ids=False, t_pose_tolerance=.0002, world_translation_tolerance=.0002)
        old = {x['id']:float(x['weight']) for x in baseline['weights']}; new = {x['id']:float(x['weight']) for x in actual['weights']}
        weights = set(old) == set(new) and all(abs(old[k]-new[k]) <= 1e-7 for k in old)
        materials = bool(baseline['materials'].get('digest')) and baseline['materials']['digest'] == actual['materials'].get('digest')
        passed = (geometry['passed'] and max(body_local, body_world, target_error) <= .002 and eye['matches']
            and weights and materials and actual['support_readbacks']['consistent'])
        item = {'phase': label, 'all_low_high_meshes_and_owners': geometry,
            'all_body_local_max_mm': body_local, 'all_body_world_max_mm': body_world,
            'target_world_max_mm': target_error, 'eye': eye, 'weights_unchanged': weights,
            'available_material_fingerprint_unchanged': materials, 'material_pixels_verified': False,
            'material_observation_errors': actual['materials'].get('errors', []), 'passed': passed}
        report['steps'].append(item); checkpoint(label + '_checked')
        if not passed: raise ValueError('Identity changed protected source: ' + label)
    def export_native(label):
        part, mesh, faces = resolve_target(avatar(), c['target'])
        whole = os.path.join(output_dir, label + '_whole_avatar.obj')
        path = os.path.join(output_dir, label + '.obj')
        # Reuse proven hair-route workaround: native exporter rejects subobject
        # owners. Export the avatar, then extract exact original corner data.
        flags = R.EExport3DFileOption_AllClothes | R.EExport3DFileOption_FullBodyPart
        api.checked('Export whole avatar original support layout', R.RFileIO.ExportObjFile(avatar(), whole, flags))
        extraction = extract_native_group(whole, path, c['target']['mesh_name'], c['target']['vertex_count'], faces)
        parsed = parse_native_obj(path, c['target']['mesh_name'], c['target']['vertex_count'], faces)
        report.setdefault('native_exports', []).append(dict(api.bodyfit_freeze_file_record(path),
            whole_avatar=api.bodyfit_freeze_file_record(whole), extraction=extraction,
            export_flags=int(flags), export_flag_names=['AllClothes', 'FullBodyPart'],
            uv_count=parsed['uv_count'], normal_count=parsed['normal_count'],
            uv_normal_material_corner_sha256=parsed['uv_normal_material_corner_sha256']))
        return path, parsed
    try:
        checkpoint('backup_current_scene')
        backup = os.path.join(output_dir, 'scene_before_identity.ccProject')
        api.checked('Backup current scene', R.RFileIO.SaveProject(backup)); report['current_scene_backup'] = api.bodyfit_freeze_file_record(backup)
        path = os.path.join(output_dir, 'immutable_original_source.ccProject'); shutil.copyfile(source['path'], path)
        working = api.bodyfit_freeze_file_record(path)
        if working['sha256'] != source['sha256']: raise ValueError('Working copy differs')
        report['working_source'] = working; attempted = True
        load(working, 'Load original unmodified source for support identity')
        checkpoint('fresh_original'); baseline = snapshot('fresh_original')
        if not baseline['support_readbacks']['consistent']: raise ValueError('Original support readback inconsistent')
        _, native = export_native('native_source')
        after_export = snapshot('post_source_export'); gate('post_source_export', after_export)
        replacement = os.path.join(output_dir, 'IDENTITY_same_support_world.obj')
        report['identity_obj'] = write_identity_world_obj(native, after_export['target_world']['world'], replacement)
        parsed = parse_native_obj(replacement, c['target']['mesh_name'], c['target']['vertex_count'], after_export['target_world']['faces'])
        if parsed['uv_normal_material_corner_sha256'] != native['uv_normal_material_corner_sha256']:
            raise ValueError('Identity OBJ changed original UV/normal payload')
        report['identity_obj']['file'] = api.bodyfit_freeze_file_record(replacement)
        checkpoint('replace_one_original_support_identity')
        mesh = resolve_target(avatar(), c['target'])[1]
        report['replace_status'] = api.checked('Identity replacement of one original support',
            mesh.ReplaceMesh(replacement, R.EReplaceMeshOption_ZUp, False))
        gate('after_identity_raw', snapshot('after_identity_raw'))
        render = os.path.join(output_dir, 'evaluation_trigger.png'); api.render_preview(render)
        report['evaluation_render'] = api.bodyfit_freeze_file_record(render)
        gate('after_identity_render', snapshot('after_identity_render'))
        _, after_native = export_native('native_after_identity')
        gate('after_identity_export', snapshot('after_identity_export'))
        if after_native['uv_normal_material_corner_sha256'] != native['uv_normal_material_corner_sha256']:
            raise ValueError('Identity changed re-exported UV/normals/material-corner assignment')
        saved = os.path.join(output_dir, 'IDENTITY_ONLY_original_support.ccProject')
        api.checked('Save independent identity evidence', R.RFileIO.SaveProject(saved)); report['identity_project'] = api.bodyfit_freeze_file_record(saved)
        gate('post_save', snapshot('post_save'))
        load(report['identity_project'], 'Reload independent identity evidence'); gate('reloaded', snapshot('reloaded'))
        _, reloaded_native = export_native('native_reloaded')
        gate('reloaded_post_export', snapshot('reloaded_post_export'))
        if reloaded_native['uv_normal_material_corner_sha256'] != native['uv_normal_material_corner_sha256']:
            raise ValueError('Save/reload changed re-exported UV/normals/material-corner assignment')
        report['identity_roundtrip_passed'] = True
    except Exception as error:
        report['error'] = {'type':type(error).__name__, 'message':str(error), 'traceback':traceback.format_exc()}
    finally:
        restored = False
        if attempted and working:
            try:
                checkpoint('restore_original_source'); load(working, 'Restore original support identity source')
                restored_state = snapshot('restored_source')
                if baseline:
                    gate('restored_source', restored_state); restored = True
            except Exception as error:
                report['restoration_error'] = str(error)
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        report['restored_source'] = restored
        report['success'] = bool(report.get('identity_roundtrip_passed') and restored and report['source_unchanged'] and not report.get('error'))
        report['status'] = 'identity_roundtrip_supported_no_repair_accepted' if report['success'] else 'identity_probe_failed'
        checkpoint(report['status'])
    summary = {k:report[k] for k in ('success','identity_only','geometry_repair_accepted','status','source_unchanged','restored_source','report_path','summary_path')}
    summary['error'] = report.get('error'); api.write_json(summary, sp); return summary
