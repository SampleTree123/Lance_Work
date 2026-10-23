"""Measure one explicit registered lash asset; no invented lash tolerance.

Only native704 Body vertices may move. Existing supports retain0.002mm.
Two evidence-bound Delicate type9 lash parts may be added, never substituted.
Successful geometry evidence still needs eyelid fitting/blink visual acceptance.
"""
import hashlib
import importlib
import json
import math
import os
import shutil
import sys
import traceback

CREATION_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_character_creation_20261005_v1'
RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'character_refresh_20261018_v1')
REGISTRY = os.path.join(os.path.dirname(__file__), 'cc_facial_production_registry_v1.json')
RESOURCE = r'D:\CharacterCreator\Character Creator 5\Resource\CCHeadshot\BlendShape\G3Plus_Eyelash_for_Male.obj'
BODY_COUNT = 14164
LASH = tuple(range(13411, 14115))
DELICATE_ID = 'CCAPP_EYELASHES_6afb64efe09b'
DELICATE_SHA = 'cc7ea946db6669a32962a1a2974a1b5d0de4f4786448c52620795fd1a3e4020e'
DELICATE_ADDITIONS = (
    ('avatar/9:Lash_Low_Bushy', 'Lash_Low_Bushy', 1704, 737,
     '6c3a653ef9a03175e270b7b541f13c6f075d511a3a099566aa08b8b5be02c445'),
    ('avatar/9:Lash_Up_Bushy', 'Lash_Up_Bushy', 2946, 1289,
     '459482b468cf4fcea62567f9733fcdb424573ade749897bf3b6072c281b3f2df'))


def mesh_key(mesh):
    return tuple(mesh[k] for k in ('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256'))


def _part_key(part):
    return tuple(part[k] for k in ('owner', 'type', 'name'))


def compare_existing_supports(before, after, comparator):
    """Authorize exactly the observed Delicate additions; retain every old row.

    Keys contain owner/name/topology, not enumeration position or runtime ID.
    Calling code must verify source/asset/evidence before using this contract.
    """
    old_keys = [mesh_key(m) for m in before['meshes']]
    new_keys = [mesh_key(m) for m in after['meshes']]
    expected_parts = [('avatar', '9', key[1]) for key in DELICATE_ADDITIONS]
    old_parts = [_part_key(p) for p in before['parts']]
    new_parts = [_part_key(p) for p in after['parts']]
    additions = set(DELICATE_ADDITIONS)
    owners = {key[0] for key in additions}
    valid_structure = (len(set(old_keys)) == len(old_keys) and len(set(new_keys)) == len(new_keys)
        and not (set(old_keys) & additions) and set(new_keys) == set(old_keys) | additions
        and len(set(old_parts)) == len(old_parts) and len(set(new_parts)) == len(new_parts)
        and not (set(old_parts) & set(expected_parts))
        and set(new_parts) == set(old_parts) | set(expected_parts))
    old_t = [(t['owner'], t['space']) for t in before.get('owner_transforms', [])]
    new_t = [(t['owner'], t['space']) for t in after.get('owner_transforms', [])]
    expected_t = {(owner, space) for owner in owners for space in ('local', 'world')}
    transforms_observed = (len(set(old_t)) == len(old_t) and len(set(new_t)) == len(new_t)
        and not (set(old_t) & expected_t) and set(new_t) == set(old_t) | expected_t
        and not before.get('owner_transform_errors') and not after.get('owner_transform_errors'))
    # Removed/modified existing owners, unrelated additions and duplicates stay
    # hard failures even if the preserved subset itself would compare equal.
    def protected(snapshot):
        return dict(snapshot,
            meshes=sorted([m for m in snapshot['meshes'] if m['owner'] not in owners], key=mesh_key),
            parts=sorted([p for p in snapshot['parts'] if _part_key(p) not in expected_parts], key=_part_key),
            owner_transforms=sorted([t for t in snapshot.get('owner_transforms', []) if t['owner'] not in owners],
                                    key=lambda t: (t['owner'], t['space'])))
    result = comparator(protected(before), protected(after))
    result.update(allowed_new_parts_exact=valid_structure,
        added_owner_transforms_observed=transforms_observed,
        expected_new_meshes=[dict(zip(('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256'), k))
                             for k in DELICATE_ADDITIONS],
        observed_added_meshes=[dict(zip(('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256'), k))
                               for k in new_keys if k not in old_keys],
        passed=result['passed'] and valid_structure and transforms_observed)
    return result


def validate_addition_evidence(config, asset, source, api, comparator):
    """Freeze failed v1 observation as provenance, never as a magnitude bound."""
    if asset['asset_id'] != DELICATE_ID or asset['sha256'] != DELICATE_SHA:
        raise ValueError('Only evidenced Delicate asset supports this exact addition contract')
    evidence = config['new_lash_parts_evidence']
    required = {'report', 'before_snapshot', 'after_apply_snapshot'}
    if set(evidence) != required:
        raise ValueError('Explicit failed observation report and both snapshots required')
    for record in evidence.values():
        if not inside(record['path'], RUN_ROOT) or api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Lash addition evidence path/SHA changed')
    prior = api.read_json(evidence['report']['path'])
    if (prior['source_project']['sha256'] != source['sha256']
            or prior['eyelash_asset']['asset_id'] != DELICATE_ID
            or prior['eyelash_asset']['sha256'] != DELICATE_SHA
            or prior['success'] is not False
            or prior['error']['message'] != 'Protected nonlash/eye geometry moved: after_apply'):
        raise ValueError('Evidence source/asset/failure scope differs')
    before = api.read_json(evidence['before_snapshot']['path'])
    after = api.read_json(evidence['after_apply_snapshot']['path'])
    check = compare_existing_supports(before['other_meshes'], after['other_meshes'], comparator)
    # These files authorize *which new parts* belong to this preset. They do
    # not authorize any observed mutation of original supports. The runtime
    # gate independently retains every original support at0.002mm.
    if (not check['allowed_new_parts_exact'] or not check['added_owner_transforms_observed']
            or not body_gate(before['body'], after['body'])['passed']):
        raise ValueError('Recorded observation does not support bounded addition classification')
    return {'files': evidence, 'existing_support_comparison': check,
            'asset_sha256': DELICATE_SHA, 'source_sha256': source['sha256'],
            'lash_magnitude_bound_registered': False}


def inside(path, root):
    try:
        path, root = (os.path.normcase(os.path.realpath(p)) for p in (path, root))
        return os.path.commonpath([path, root]) == root
    except (TypeError, ValueError):
        return False


def canonical_faces(faces):
    return sorted(tuple(sorted(int(i) for i in face)) for face in faces)


def topology_digest(faces):
    return hashlib.sha256(json.dumps(canonical_faces(faces), separators=(',', ':')).encode('utf-8')).hexdigest()


def native_partition(resource_path, current_faces):
    group, material, body, lash, faces = '', '', set(), set(), []
    with open(resource_path, encoding='utf-8-sig') as stream:
        for line in stream:
            tokens = line.split()
            if not tokens:
                continue
            if tokens[0] in ('o', 'g'):
                group = tokens[1]
            elif tokens[0] == 'usemtl':
                material = tokens[1]
            elif tokens[0] == 'f' and group == 'CC_Base_Body':
                ids = [int(token.split('/')[0]) - 1 for token in tokens[1:]]
                body.update(ids); faces.append(ids)
                if material == 'Std_Eyelash': lash.update(ids)
    if not body:
        raise ValueError('Installed native Body topology missing')
    offset = min(body)
    if sorted(body) != list(range(offset, offset + BODY_COUNT)):
        raise ValueError('Installed Body does not have14164 contiguous points')
    indices = sorted(i - offset for i in lash)
    if indices != list(LASH):
        raise ValueError('Installed Std_Eyelash material is not the verified704-point set')
    normalized = [[i - offset for i in face] for face in faces]
    if canonical_faces(normalized) != canonical_faces(current_faces):
        raise ValueError('Current Body differs from installed material-partition topology')
    return {'body_vertex_count': BODY_COUNT, 'body_face_count': len(current_faces),
            'body_global_offset_in_resource': offset, 'native_lash_indices': indices,
            'native_lash_count': len(indices), 'canonical_body_faces_sha256': topology_digest(current_faces)}


def _distances(first, second):
    if len(first) != len(second) or any(len(v) != 3 for v in first + second):
        raise ValueError('Comparable finite3D arrays required')
    values = [math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(u, v))) * 10
              for u, v in zip(first, second)]
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError('Comparable finite3D arrays required')
    return values


def body_gate(before, after, lash_indices=LASH):
    if (before['working_subdivision_level'] != 0 or after['working_subdivision_level'] != 0
            or len(before['local']) != BODY_COUNT or len(after['local']) != BODY_COUNT):
        raise ValueError('Active SubD0 and all14164 Body points required')
    if tuple(lash_indices) != LASH:
        raise ValueError('No arbitrary allowance set is permitted')
    local = _distances(before['local'], after['local'])
    world = _distances(before['world'], after['world'])
    lash_set = set(lash_indices)
    nonlash = [i for i in range(BODY_COUNT) if i not in lash_set]
    failed = [i for i in nonlash if max(local[i], world[i]) > .002]
    lash = [local[i] for i in lash_indices]
    sorted_lash = sorted(lash)
    p = .95 * (len(lash) - 1); lo = int(p); hi = min(lo + 1, len(lash) - 1)
    p95 = sorted_lash[lo] + (p - lo) * (sorted_lash[hi] - sorted_lash[lo])
    return {'passed': not failed, 'nonlash_vertex_count': len(nonlash), 'nonlash_limit_mm': .002,
            'nonlash_local_max_mm': max(local[i] for i in nonlash),
            'nonlash_world_max_mm': max(world[i] for i in nonlash), 'nonlash_failed_indices': failed,
            'lash_measurement': {'vertex_count': len(lash), 'local_max_mm': max(lash),
                'local_mean_mm': sum(lash) / len(lash), 'local_p95_mm': p95,
                'world_max_mm': max(world[i] for i in lash_indices), 'local_displacements_mm': lash,
                'upper_bound_mm': None, 'upper_bound_accepted': False,
                'scope': 'Measurement only. No magnitude threshold or fit acceptance registered.'}}


def nonbody_support_snapshot(full):
    """Local arrays remain valid for inactive high cages; never query their world."""
    meshes = [m for m in full['meshes'] if m['name'] != 'CC_Base_Body']
    owners = {m['owner'] for m in meshes}
    return dict(full, meshes=meshes,
        parts=[p for p in full['parts'] if p['owner'] + '/' + p['type'] + ':' + p['name'] in owners],
        owner_transforms=[t for t in full['owner_transforms'] if t['owner'] == 'avatar' or t['owner'] in owners])


def run(library, output_dir, log, api):
    directory = os.path.dirname(__file__)
    if directory not in sys.path: sys.path.insert(0, directory)
    from cc_compile_character_manifest import facial_pool
    capture = importlib.import_module('cc_capture_assembly_geometry_v1')
    support_capture = importlib.import_module('cc_repair_headshot_support_materials_v1')
    config = library['refresh_eyelash_probe']
    if (config.get('geometry_contract') != 'native704_measurement_only_other13460_strict0.002mm'
            or config.get('save_current_scene_backup') is not True or config.get('sex') not in ('female', 'male')):
        raise ValueError('Explicit bounded native-lash measurement contract/sex/backup required')
    if not inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('New independent refresh output child required')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse existing eyelash probe outputs')
    for record, expected in [(config['registry'], REGISTRY), (config['native_lash_resource'], RESOURCE)]:
        if (os.path.normcase(os.path.realpath(record['path'])) != os.path.normcase(os.path.realpath(expected))
                or api.sha256_file(record['path']) != record['sha256']):
            raise ValueError('Registry/native topology reference path or SHA changed')
    registry = api.read_json(REGISTRY)
    pool = facial_pool(registry, 'eyelashes')
    if len(pool) != 9 or config['eyelash_asset_id'] not in pool:
        raise ValueError('Explicit asset from current9-preset pool required')
    selected = pool[config['eyelash_asset_id']]
    if selected.get('application_mode') != 'character_preset_replace' or api.sha256_file(selected['path']) != selected['sha256']:
        raise ValueError('Registered eyelash asset mode/SHA changed')
    asset = {k: selected.get(k) for k in ('asset_id', 'display_name', 'asset_type', 'asset_form', 'application_mode', 'slot', 'path', 'sha256')}
    asset.update(extension=os.path.splitext(asset['path'])[1].lower(), verification_mode='scene_inventory')
    source = config['source_project']
    if (not any(inside(source['path'], r) for r in (CREATION_ROOT, RUN_ROOT, STAGE_ROOT))
            or not source['path'].lower().endswith('.ccproject') or api.sha256_file(source['path']) != source['sha256']):
        raise ValueError('Independent source path/SHA mismatch')
    addition_evidence = validate_addition_evidence(config, asset, source, api, support_capture.compare_geometry)
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'eyelash_probe_report.json')
    summary_path = os.path.join(output_dir, 'validation_result.json')
    report = {'schema_version': 2, 'success': False, 'status': 'measuring', 'sex': config['sex'],
              'case_id': config['case_id'], 'source_project': source, 'eyelash_asset': asset,
              'implementation_sha256': api.sha256_file(__file__), 'steps': [],
              'visual_acceptance': 'pending', 'lash_upper_bound_registered': False, 'material_pixels_verified': False,
              'coordinate_scope': 'Active SubD0 Body local+world; recursive non-Body low/high local meshes and owner transforms. Inactive cage world coordinates are never queried.',
              'dependency_sha256': {name: api.sha256_file(os.path.join(directory, name)) for name in
                  ('cc_capture_assembly_geometry_v1.py', 'cc_repair_headshot_support_materials_v1.py', 'cc_compile_character_manifest.py')},
              'report_path': report_path, 'summary_path': summary_path}
    report['new_lash_parts_evidence'] = addition_evidence
    R = api.RLPy
    working = None
    attempted_load = False
    baseline = None
    applied = None
    def checkpoint(phase=None):
        if phase: report['phase'] = phase; log('Eyelash probe: ' + phase)
        report['updated_at'] = api.now(); api.write_json(report, report_path)
    def avatar():
        items = list(R.RScene.GetAvatars() or [])
        if len(items) != 1: raise ValueError('Expected one independent avatar')
        return items[0]
    def load(record, label):
        if api.sha256_file(record['path']) != record['sha256']: raise ValueError('Load source changed')
        status, dialogs = api.load_file_with_optional_undo_warning(record['path'], label)
        report.setdefault('loads', []).append({'label': label, 'status': status, 'dialogs': dialogs, 'source': record})
        current = avatar(); R.RScene.SelectObject(current); api.force_avatar_scene_evaluation(current)
        return current
    def snapshot(label):
        current = avatar()
        body = capture.capture_body_snapshot(current, api=api, include_world=True,
            output_path=os.path.join(output_dir, label + '_body.json'))
        if body['working_subdivision_level'] != 0: raise ValueError('Actual SubD0 required; no switching')
        meshes = list(current.GetMeshes(False))
        body_mesh = [m for m in meshes if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == BODY_COUNT]
        if len(body_mesh) != 1: raise ValueError('Ambiguous Body mesh')
        faces = [list(body_mesh[0].GetFace(i)) for i in range(body_mesh[0].GetFacesCount())]
        full = support_capture.capture_geometry(current, api=api)
        other = nonbody_support_snapshot(full)
        eye = api.capture_eye_integrity_state(current)
        supports = api.capture_eye_part_morph_weights(current)
        result = {'body': body, 'body_topology_sha256': topology_digest(faces), 'other_meshes': other,
                  'eye_integrity': eye, 'eye_support_weights': supports}
        api.write_json(result, os.path.join(output_dir, label + '_snapshot.json'))
        return result, faces
    def gate(label, actual):
        if baseline['body_topology_sha256'] != actual['body_topology_sha256']:
            raise ValueError('Body topology changed')
        eye = api.compare_neutral_eye_states(baseline['eye_integrity'], actual['eye_integrity'],
            tolerance=.0002, include_world=True, include_runtime_ids=False, t_pose_tolerance=.0002,
            world_translation_tolerance=.0002)
        left = {x['id']: float(x['weight']) for x in baseline['eye_support_weights']}
        right = {x['id']: float(x['weight']) for x in actual['eye_support_weights']}
        weights_ok = set(left) == set(right) and all(abs(left[k] - right[k]) <= 1e-7 for k in left)
        body = body_gate(baseline['body'], actual['body'])
        other = compare_existing_supports(baseline['other_meshes'], actual['other_meshes'], support_capture.compare_geometry)
        # Newly added lash meshes have no source counterpart. Once applied,
        # their chosen geometry and owner transforms must survive save/reload.
        persistence = support_capture.compare_geometry(applied['other_meshes'], actual['other_meshes']) if applied else None
        step = {'phase': label, 'body': body, 'all_other_meshes': other, 'eye_integrity': eye,
                'applied_supports_and_new_lashes_persistence': persistence,
                'eye_support_weights_preserved': weights_ok,
                'passed': body['passed'] and other['passed'] and eye['matches'] and weights_ok
                          and (persistence is None or persistence['passed'])}
        report['steps'].append(step); checkpoint()
        if not step['passed']: raise ValueError('Protected nonlash/eye geometry moved: ' + label)
    try:
        checkpoint('backup_current_scene')
        backup = os.path.join(output_dir, 'scene_before_eyelash.ccProject')
        api.checked('Save independent scene backup', R.RFileIO.SaveProject(backup))
        report['current_scene_backup'] = api.bodyfit_freeze_file_record(backup)
        path = os.path.join(output_dir, 'eyelash_source_copy.ccProject'); shutil.copyfile(source['path'], path)
        working = api.bodyfit_freeze_file_record(path)
        if working['sha256'] != source['sha256']: raise ValueError('Working source copy differs')
        report['working_source'] = working; attempted_load = True
        current = load(working, 'Load independent eyelash source')
        baseline, faces = snapshot('before')
        partition = native_partition(RESOURCE, faces); partition['resource'] = config['native_lash_resource']
        api.write_json(partition, os.path.join(output_dir, 'native_lash_partition.json')); report['native_lash_partition'] = partition
        checkpoint('apply_explicit_registered_eyelash')
        current, application = api.apply_appearance_assets(current, [asset], cleanup_names=[], allow_missing_cleanup=True,
            progress_callback=lambda phase, detail=None: checkpoint('apply:' + phase))
        report['application'] = application
        steps = application.get('steps', [])
        if len(steps) != 1 or any(steps[0].get(k) is not True for k in
                ('character_preset_verified', 'eye_geometry_preserved', 'eye_support_preserved')):
            raise ValueError('Existing character-preset/eye guards did not confirm application')
        after, _ = snapshot('after_apply'); gate('after_apply', after)
        applied = after
        candidate = os.path.join(output_dir, 'CANDIDATE_eyelash_measured.ccProject')
        checkpoint('save_independent_candidate')
        api.checked('Save measured eyelash candidate', R.RFileIO.SaveProject(candidate))
        report['saved_project'] = api.bodyfit_freeze_file_record(candidate)
        post_save, _ = snapshot('post_save'); gate('post_save', post_save)
        checkpoint('reload_saved_candidate')
        load(report['saved_project'], 'Reload measured eyelash candidate')
        reloaded, _ = snapshot('reloaded'); gate('reloaded', reloaded)
        # Save/reload must preserve the chosen lash geometry too: this is a
        # numeric persistence check against post-apply, not a source allowance.
        persistence = max(_distances(after['body']['local'], reloaded['body']['local']))
        report['saved_reload_all_body_max_error_mm'] = persistence
        if persistence > .002: raise ValueError('Save/reload changed chosen geometry beyond0.002mm')
        report.update(success=True, status='geometry_supported_without_visual_acceptance',
            scope='Registered asset application side effects bounded;704 lash magnitude measured only; fit/blink/visual/UE and upper-bound registration pending')
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
        report['status'] = 'failed_protected_geometry_or_application'
    finally:
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        if not report['source_unchanged']:
            report['success'] = False; report['status'] = 'failed_immutable_source_changed'
        if not report['success'] and attempted_load and working is not None:
            try:
                checkpoint('restore_independent_input_after_failure'); load(working, 'Restore failed eyelash probe input')
                restored, _ = snapshot('restored_input')
                report['failure_recovery'] = {'restored': True,
                    'body_local_max_error_mm': max(_distances(baseline['body']['local'], restored['body']['local'])) if baseline else None}
            except Exception as error:
                report['failure_recovery'] = {'restored': False, 'error': str(error)}
        checkpoint('completed_geometry_evidence_visual_pending' if report['success'] else 'failed_eyelash_probe')
    summary = {'success': report['success'], 'status': report['status'], 'report_path': report_path,
               'summary_path': summary_path, 'saved_project': report.get('saved_project'),
               'visual_acceptance': 'pending', 'lash_upper_bound_registered': False,
               'source_unchanged': report['source_unchanged'], 'error': report.get('error')}
    api.write_json(summary, summary_path)
    return summary
