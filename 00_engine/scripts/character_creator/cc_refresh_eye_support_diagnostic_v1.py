"""Isolate lash load, evaluation and save/reload effects; never accept geometry.

This module deliberately does NOT call capture_body_snapshot with the full api:
that capture helper normally injects ObjectModified(MorphWeight) before reading.
No subdivision switch, mesh replacement, new tolerance or asset promotion.
"""
import hashlib
import importlib
import json
import math
import os
import shutil
import sys
import traceback
import types

READBACK_TOLERANCE_MM = .001
SUPPORT_LEVELS = {('CC_Base_EyeOcclusion', 182), ('CC_Base_EyeOcclusion', 650),
                  ('CC_Base_TearLine', 190), ('CC_Base_TearLine', 652)}
PHASES = ('fresh_raw', 'after_apply_raw', 'after_set_time', 'after_render',
          'after_morph_notification', 'post_save_raw', 'reloaded_raw')


def _rows(values):
    result = [[float(v.x), float(v.y), float(v.z)] for v in values]
    if not result or not all(math.isfinite(x) for row in result for x in row):
        raise ValueError('Finite nonempty support3D array required')
    return result


def query_support_levels(avatar):
    """Local scalar/vector/reverse reads on each of four low/high levels.

    No world reads or scene update calls. Reacquire each mesh on repeat so the
    result also detects enumeration/proxy inconsistency rather than assuming it.
    """
    if int(avatar.GetSubdivMeshLevel()) != 0:
        raise ValueError('Actual SubD0 required throughout diagnosis')
    def resolve():
        result = {}
        for part in avatar.GetAvatarParts() or []:
            if str(part.GetAvatarPartType()) not in ('5', '6'):
                continue
            for mesh in part.GetMeshes(False) or []:
                key = (str(mesh.GetName()), int(mesh.GetVerticesCount()))
                if key not in SUPPORT_LEVELS or key in result:
                    raise ValueError('Unexpected or duplicate eye support level: ' + str(key))
                result[key] = ('avatar/' + str(part.GetAvatarPartType()) + ':' + str(part.GetName()), mesh)
        if set(result) != SUPPORT_LEVELS:
            raise ValueError('All four exact low/high support levels required')
        return result
    result = []
    from cc_refresh_eyelash_probe_v2 import _distances
    for key, (owner, mesh) in sorted(resolve().items()):
        vertices = _rows(mesh.GetVertices(False))
        if len(vertices) != key[1]:
            raise ValueError('Support array length differs from declared topology')
        scalar = _rows(mesh.GetVertex(i, False) for i in range(key[1]))
        faces = [[int(i) for i in mesh.GetFace(j)] for j in range(mesh.GetFacesCount())]
        result.append({'owner': owner, 'name': key[0], 'vertex_count': key[1],
            'face_count': len(faces), 'faces': faces,
            'faces_sha256': hashlib.sha256(json.dumps(faces, separators=(',', ':')).encode()).hexdigest(),
            'local': vertices, 'scalar_local': scalar,
            'scalar_vector_max_error_mm': max(_distances(vertices, scalar))})
    reverse = resolve()
    for row in reversed(result):
        owner, mesh = reverse[(row['name'], row['vertex_count'])]
        if owner != row['owner']:
            raise ValueError('Owner changed during support query')
        repeated = _rows(mesh.GetVertices(False))
        row['reverse_vector_max_error_mm'] = max(_distances(row['local'], repeated))
        row['readback_consistent'] = max(row['scalar_vector_max_error_mm'],
            row['reverse_vector_max_error_mm']) <= READBACK_TOLERANCE_MM
    return {'levels': result, 'readback_tolerance_mm': READBACK_TOLERANCE_MM,
            'consistent': all(row['readback_consistent'] for row in result),
            'working_subdivision_level': 0, 'world_queried': False, 'scene_update_performed': False}


def support_deltas(before, after):
    from cc_refresh_eyelash_probe_v2 import _distances
    old = {(m['owner'], m['name'], m['vertex_count'], m['face_count'], m['faces_sha256']): m
           for m in before['levels']}
    new = {(m['owner'], m['name'], m['vertex_count'], m['face_count'], m['faces_sha256']): m
           for m in after['levels']}
    if set(old) != set(new):
        raise ValueError('Eye support topology/owner changed')
    result = []
    for key in sorted(old):
        distances = _distances(old[key]['local'], new[key]['local'])
        result.append({'owner': key[0], 'name': key[1], 'vertex_count': key[2],
            'maximum_local_delta_mm': max(distances),
            'over_protection_limit_indices': [i for i, d in enumerate(distances) if d > .002],
            'displacements_mm': distances, 'protection_limit_mm': .002})
    return result


def capture_complete(labels, restored, source_unchanged):
    return tuple(labels) == PHASES and restored and source_unchanged


def run(library, output_dir, log, api):
    directory = os.path.dirname(__file__)
    if directory not in sys.path: sys.path.insert(0, directory)
    import cc_refresh_eyelash_probe_v2 as lash
    import cc_repair_headshot_support_materials_v1 as support
    from cc_compile_character_manifest import facial_pool
    body_capture = importlib.import_module('cc_capture_assembly_geometry_v1')
    config = library['refresh_eye_support_diagnostic']
    if (config.get('diagnostic_only') is not True or config.get('save_current_scene_backup') is not True
            or config.get('allow_expected_protected_violation_capture') is not True):
        raise ValueError('Explicit diagnostic-only backup and expected-violation capture contract required')
    if not lash.inside(output_dir, lash.RUN_ROOT) or os.path.realpath(output_dir) == os.path.realpath(lash.RUN_ROOT):
        raise ValueError('New independent refresh output child required')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse existing diagnostic outputs')
    source = config['source_project']
    if (not any(lash.inside(source['path'], root) for root in (lash.CREATION_ROOT, lash.RUN_ROOT, lash.STAGE_ROOT))
            or not source['path'].lower().endswith('.ccproject') or api.sha256_file(source['path']) != source['sha256']):
        raise ValueError('Source path/SHA changed')
    if (os.path.normcase(os.path.realpath(config['registry']['path'])) != os.path.normcase(os.path.realpath(lash.REGISTRY))
            or api.sha256_file(lash.REGISTRY) != config['registry']['sha256']):
        raise ValueError('Registry path/SHA changed')
    pool = facial_pool(api.read_json(lash.REGISTRY), 'eyelashes')
    selected = pool.get(config['eyelash_asset_id'])
    if len(pool) != 9 or not selected or selected['application_mode'] != 'character_preset_replace':
        raise ValueError('Exact registered9-pool preset required')
    asset = {k: selected.get(k) for k in ('asset_id', 'display_name', 'asset_type', 'asset_form',
             'application_mode', 'slot', 'path', 'sha256')}
    asset.update(extension=os.path.splitext(asset['path'])[1].lower(), verification_mode='scene_inventory')
    if api.sha256_file(asset['path']) != asset['sha256']:
        raise ValueError('Selected asset changed')
    evidence = lash.validate_addition_evidence(config, asset, source, api, support.compare_geometry)
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'eye_support_diagnostic_report.json')
    summary_path = os.path.join(output_dir, 'validation_result.json')
    report = {'schema_version': 1, 'success': False, 'capture_complete': False,
        'status': 'capturing_diagnostic_only', 'diagnostic_only': True, 'geometry_accepted': False,
        'visual_accepted': False, 'lash_upper_bound_registered': False, 'case_id': config['case_id'],
        'source_project': source, 'asset': asset, 'addition_evidence': evidence, 'captures': [],
        'report_path': report_path, 'summary_path': summary_path,
        'implementation_sha256': api.sha256_file(__file__),
        'dependencies': {name: api.sha256_file(os.path.join(directory, name)) for name in
            ('cc_refresh_eyelash_probe_v2.py', 'cc_capture_assembly_geometry_v1.py',
             'cc_repair_headshot_support_materials_v1.py', 'cc_compile_character_manifest.py')},
        'scope': 'Capture expected violation; no mesh replacement, subdivision switches, geometry acceptance or tolerance changes.'}
    R = api.RLPy
    baseline = None
    previous = None
    working = None
    attempted_load = False
    restore_ok = False
    raw_api = types.SimpleNamespace(_transform_data=api._transform_data)
    def checkpoint(phase):
        report['phase'] = phase; report['updated_at'] = api.now()
        api.write_json(report, report_path); log('Eye support diagnosis: ' + phase)
    def current():
        avatars = list(R.RScene.GetAvatars() or [])
        if len(avatars) != 1: raise ValueError('Exactly one diagnostic avatar required')
        return avatars[0]
    def load(record, label):
        if api.sha256_file(record['path']) != record['sha256']: raise ValueError('Load source changed')
        status, dialogs = api.load_file_with_optional_undo_warning(record['path'], label)
        report.setdefault('loads', []).append({'label': label, 'status': status, 'dialogs': dialogs})
        avatar = current(); R.RScene.SelectObject(avatar)
        # Intentionally no SetTime/ObjectModified/force evaluation here.
        return avatar
    def raw_snapshot(label):
        avatar = current()
        queries = query_support_levels(avatar)  # first reads after each explicit operation
        full = support.capture_geometry(avatar, api=raw_api)
        other = lash.nonbody_support_snapshot(full)
        body = body_capture.capture_body_snapshot(avatar, api=raw_api, include_world=True)
        if body['scene_explicitly_settled'] or body['working_subdivision_level'] != 0:
            raise ValueError('Raw snapshot accidentally evaluated or changed level')
        value = {'support_queries': queries, 'other_meshes': other, 'body': body,
            'eye_integrity': api.capture_eye_integrity_state(avatar),
            'eye_support_weights': api.capture_eye_part_morph_weights(avatar),
            'current_time': str(R.RGlobal.GetTime()), 'scene_update_in_capture': False}
        path = os.path.join(output_dir, label + '_snapshot.json'); api.write_json(value, path)
        return value, api.bodyfit_freeze_file_record(path)
    def observe(label):
        nonlocal baseline, previous
        checkpoint(label)
        actual, record = raw_snapshot(label)
        row = {'label': label, 'snapshot': record,
            'readback_consistent': actual['support_queries']['consistent']}
        if baseline is None:
            baseline = actual
        else:
            eye = api.compare_neutral_eye_states(baseline['eye_integrity'], actual['eye_integrity'],
                tolerance=.0002, include_world=True, include_runtime_ids=False,
                t_pose_tolerance=.0002, world_translation_tolerance=.0002)
            old = {x['id']: float(x['weight']) for x in baseline['eye_support_weights']}
            new = {x['id']: float(x['weight']) for x in actual['eye_support_weights']}
            weights_ok = set(old) == set(new) and all(abs(old[k] - new[k]) <= 1e-7 for k in old)
            body = lash.body_gate(baseline['body'], actual['body'])
            other = lash.compare_existing_supports(baseline['other_meshes'], actual['other_meshes'], support.compare_geometry)
            row.update(support_delta_from_fresh=support_deltas(baseline['support_queries'], actual['support_queries']),
                support_delta_from_previous=support_deltas(previous['support_queries'], actual['support_queries']),
                protected_geometry_check={'body': body, 'existing_supports': other,
                    'eye_integrity': eye, 'eye_support_weights_preserved': weights_ok,
                    'passed': body['passed'] and other['passed'] and eye['matches'] and weights_ok},
                geometry_accepted=False)
        report['captures'].append(row); previous = actual; checkpoint(label + '_captured')
        if not row['readback_consistent']:
            raise ValueError('Inconsistent scalar/vector/reverse support reads; evidence incomplete')
    try:
        checkpoint('backup_current_scene')
        backup = os.path.join(output_dir, 'scene_before_diagnostic.ccProject')
        api.checked('Save current independent diagnostic backup', R.RFileIO.SaveProject(backup))
        report['current_scene_backup'] = api.bodyfit_freeze_file_record(backup)
        copy = os.path.join(output_dir, 'immutable_source_copy.ccProject'); shutil.copyfile(source['path'], copy)
        working = api.bodyfit_freeze_file_record(copy)
        if working['sha256'] != source['sha256']: raise ValueError('Source copy changed')
        report['working_source'] = working; attempted_load = True
        load(working, 'Load fresh diagnostic source'); observe('fresh_raw')
        checkpoint('apply_delicate')
        _, application = api.apply_appearance_assets(current(), [asset], cleanup_names=[], allow_missing_cleanup=True,
            progress_callback=lambda phase, detail=None: checkpoint('apply:' + phase))
        report['application'] = application
        if len(application.get('steps', [])) != 1 or any(application['steps'][0].get(k) is not True
                for k in ('character_preset_verified', 'eye_geometry_preserved', 'eye_support_preserved')):
            raise ValueError('Existing application guards did not confirm exact asset load')
        observe('after_apply_raw')
        api.checked('Explicit diagnostic SetTime only', R.RGlobal.SetTime(R.RGlobal.GetStartTime(), True))
        api.QtWidgets.QApplication.processEvents(); observe('after_set_time')
        render_path = os.path.join(output_dir, 'evaluation_trigger_only.png')
        api.render_preview(render_path)
        image = api.QtGui.QImage(render_path)
        if image.isNull() or image.width() <= 0 or image.height() <= 0:
            raise ValueError('Explicit evaluation render invalid')
        report['render_evaluation_trigger'] = dict(api.bodyfit_freeze_file_record(render_path),
            width=image.width(), height=image.height(), visual_acceptance=False)
        observe('after_render')
        api.checked('Explicit diagnostic MorphWeight notification', R.RGlobal.ObjectModified(current(), R.EObjectModifiedType_MorphWeight))
        api.checked('Evaluate explicit MorphWeight notification', R.RGlobal.SetTime(R.RGlobal.GetStartTime(), True))
        api.QtWidgets.QApplication.processEvents(); observe('after_morph_notification')
        path = os.path.join(output_dir, 'DIAGNOSTIC_ONLY_expected_violation.ccProject')
        api.checked('Save diagnostic evidence only', R.RFileIO.SaveProject(path))
        report['diagnostic_project'] = api.bodyfit_freeze_file_record(path)
        observe('post_save_raw')
        load(report['diagnostic_project'], 'Reload diagnostic expected-violation evidence'); observe('reloaded_raw')
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        if attempted_load and working:
            try:
                checkpoint('restore_immutable_source')
                load(working, 'Restore immutable diagnostic input')
                restored, record = raw_snapshot('restored_input')
                other = support.compare_geometry(baseline['other_meshes'], restored['other_meshes']) if baseline else None
                body_error = max(lash._distances(baseline['body']['local'], restored['body']['local'])) if baseline else None
                eye = api.compare_neutral_eye_states(baseline['eye_integrity'], restored['eye_integrity'],
                    tolerance=.0002, include_world=True, include_runtime_ids=False,
                    t_pose_tolerance=.0002, world_translation_tolerance=.0002) if baseline else None
                old = {x['id']: float(x['weight']) for x in baseline['eye_support_weights']} if baseline else {}
                new = {x['id']: float(x['weight']) for x in restored['eye_support_weights']}
                weights_ok = set(old) == set(new) and all(abs(old[k] - new[k]) <= 1e-7 for k in old)
                restore_ok = bool(other and other['passed'] and body_error <= .002
                    and restored['support_queries']['consistent'] and eye['matches'] and weights_ok)
                report['restoration'] = {'restored': restore_ok, 'snapshot': record,
                    'body_local_max_error_mm': body_error, 'all_original_supports': other,
                    'eye_integrity': eye, 'eye_support_weights_preserved': weights_ok}
            except Exception as error:
                report['restoration'] = {'restored': False, 'error': str(error)}
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        labels = [c['label'] for c in report['captures']]
        report['capture_complete'] = capture_complete(labels, restore_ok, report['source_unchanged']) and not report.get('error')
        report['success'] = report['capture_complete']
        report['status'] = 'diagnostic_capture_complete_geometry_not_accepted' if report['success'] else 'diagnostic_capture_incomplete'
        report['protected_violation_observed'] = any(not c['protected_geometry_check']['passed']
            for c in report['captures'] if 'protected_geometry_check' in c)
        checkpoint(report['status'])
    summary = {k: report[k] for k in ('success', 'capture_complete', 'status', 'diagnostic_only',
        'geometry_accepted', 'visual_accepted', 'lash_upper_bound_registered', 'protected_violation_observed',
        'source_unchanged', 'report_path', 'summary_path')}
    summary.update(error=report.get('error'), restoration=report.get('restoration'))
    api.write_json(summary, summary_path)
    return summary
