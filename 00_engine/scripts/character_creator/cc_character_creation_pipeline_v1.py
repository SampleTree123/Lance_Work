"""Unified photo/raw-project -> corrected CC project, with optional assembly.

BodyFit Technical owns this pipeline. CC mutations remain serial Bridge steps;
the offline solver only consumes current-character captures. No UE or export.
"""
from pathlib import Path
import json
import shutil
import numpy as np

from cc_character_creation_job_state_v1 import (
    RUN_ROOT, STAGE_ROOT, SAFE_ID, ControllerError, bind, fingerprint, read, sha, verify, write,
)
from cc_headshot_geometry_solver_v1 import load_references, build_geometry_targets, write_world_obj
from cc_compile_headshot_base_assembly_v1 import compile_base_assembly, COMPONENT_FIELDS

REFERENCES = Path(__file__).with_name('cc_headshot_creation_references_v1.json')
POLICY = Path(__file__).with_name('cc_base_assembly_geometry_policy_v2.json')


def reference_records(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            yield value
        if 'evidence' in value and 'evidence_sha256' in value:
            yield {'path': value['evidence'], 'sha256': value['evidence_sha256']}
        for child in value.values():
            yield from reference_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from reference_records(child)


def normalize_request(request):
    request = dict(request)
    if ('photo' in request) == ('source_project' in request):
        raise ControllerError('Provide exactly one photo or raw Headshot source_project')
    if request.get('sex') not in ('female', 'male') or not isinstance(request.get('character_id'), str) or not SAFE_ID.fullmatch(request['character_id']):
        raise ControllerError('Valid sex and simple character_id required')
    if type(request.get('seed')) is not int:
        raise ControllerError('Integer seed required')
    appearance_mode = request.get('appearance_mode', 'assembled')
    if appearance_mode not in ('assembled', 'headshot_native'):
        raise ControllerError('appearance_mode must be assembled or headshot_native')
    if appearance_mode == 'headshot_native' and 'facial_components' in request:
        raise ControllerError('headshot_native preserves generated appearance and cannot select facial_components')
    key = 'photo' if 'photo' in request else 'source_project'
    if not isinstance(request[key], str) or not request[key]:
        raise ControllerError('Creation input path must be a nonempty string')
    components = request.get('facial_components', {})
    if not isinstance(components, dict) or set(components) - COMPONENT_FIELDS:
        raise ControllerError('facial_components must use supported assembly fields')
    path = Path(request[key]).resolve()
    allowed = ('.jpg', '.jpeg', '.png', '.bmp') if key == 'photo' else ('.ccproject',)
    if not path.is_file() or path.suffix.lower() not in allowed:
        raise ControllerError('Unsupported or missing creation input')
    request[key] = str(path)
    return request


def prepare_request(request):
    request = normalize_request(request)
    appearance_mode = request.get('appearance_mode', 'assembled')
    refs, selected = load_references(request['sex'], REFERENCES)
    root = RUN_ROOT / request['character_id']
    attempts = sorted(root.glob('attempt_[0-9][0-9][0-9]'))
    if attempts:
        previous = read(attempts[-1] / 'creation_state.json')
        if previous['status'] != 'failed':
            if previous['request_fingerprint'] != fingerprint(request):
                raise ControllerError('Existing character uses different input/config; use a new character_id')
            for value in previous['inputs'].values():
                verify(value, 'Creation input')
            return previous
    attempt = 'attempt_{:03d}'.format(len(attempts) + 1)
    directory = root / attempt
    staging = STAGE_ROOT / request['character_id'] / attempt
    directory.mkdir(parents=True, exist_ok=False)
    staging.mkdir(parents=True, exist_ok=False)
    inputs = {'references': bind(REFERENCES)}
    implementation_names = ['cc_character_creation_pipeline_v1.py', 'cc_character_creation_job_state_v1.py',
                 'cc_run_character_creation_v1.py', 'cc_headshot_geometry_solver_v1.py',
                 'cc_validate_body_reconstruction.py', 'cc_headshot_route_validation_v1.py']
    if appearance_mode == 'assembled':
        inputs['assembly_geometry_policy'] = bind(POLICY)
        implementation_names += [
                 'cc_compile_headshot_base_assembly_v1.py', 'cc_run_headshot_base_assembly_v1.py',
                 'cc_assembly_geometry_invariants_v1.py', 'cc_capture_assembly_geometry_v1.py']
    for name in implementation_names:
        inputs['implementation_' + name] = bind(Path(__file__).with_name(name))
    for index, record in enumerate(reference_records(refs)):
        verify(record, 'Reference')
        inputs['reference_' + str(index)] = dict(record)
    if appearance_mode == 'assembled':
        for index, record in enumerate(reference_records(read(POLICY))):
            verify(record, 'Assembly policy evidence')
            inputs['assembly_policy_evidence_' + str(index)] = dict(record)
    key = 'photo' if 'photo' in request else 'source_project'
    original = bind(request[key])
    copied = staging / ('PHOTO' + Path(original['path']).suffix if key == 'photo' else 'INPUT.ccProject')
    shutil.copyfile(original['path'], copied)
    if sha(copied) != original['sha256'] or sha(original['path']) != original['sha256']:
        raise ControllerError('Input changed during copying')
    inputs['original'] = original
    inputs['working_input'] = bind(copied)
    if key == 'photo':
        starter_record = selected['starter_project']
        if appearance_mode == 'headshot_native' and 'native_starter_project' in selected:
            starter_record = selected['native_starter_project']
        verify(starter_record, 'Selected photo starter')
        inputs['selected_starter'] = dict(starter_record)
        starter = staging / 'START.ccProject'
        shutil.copyfile(starter_record['path'], starter)
        if sha(starter) != starter_record['sha256'] or sha(starter_record['path']) != starter_record['sha256']:
            raise ControllerError('Starter copy differs')
        inputs['working_starter'] = bind(starter)
    preset_source = inputs.get('working_starter', inputs['working_input'])
    state = {'schema_version': 1, 'character_id': request['character_id'], 'request': request,
             'request_fingerprint': fingerprint(request), 'status': 'prepared', 'attempt_id': attempt,
             'attempt_dir': str(directory), 'stage_dir': str(staging),
             'state_path': str(directory / 'creation_state.json'), 'inputs': inputs,
             'steps': {}, 'offline_outputs': {}, 'preset_source': preset_source,
             'appearance_mode': appearance_mode,
             'source_mode': key, 'sex': request['sex'], 'references_path': str(REFERENCES)}
    write(directory / 'request.json', request)
    write(state['state_path'], state)
    return state


def advance(state, driver, wait_seconds=600):
    driver.verify_state_inputs(state)
    request = state['request']
    appearance_mode = request.get('appearance_mode', 'assembled')
    refs, selected = load_references(state['sex'], state['references_path'])
    directory = Path(state['attempt_dir'])
    if state['status'] == 'completed':
        for step in state['steps'].values():
            driver.verify_completed_step(state, step)
        for record in state['offline_outputs'].values():
            verify(record, 'Offline result')
        verify(state['result_project'], 'Final project')
        return state

    def step(step_id, operation, source, extra=None):
        output = directory / step_id
        if step_id in state['steps'] and state['steps'][step_id]['status'] == 'completed':
            driver.verify_completed_step(state, step_id)
            return read(output / 'creation_report.json')
        config = {'operation': operation, 'source_project': source, 'appearance_mode': appearance_mode}
        if extra:
            config.update(extra.pop('character_creation', {}))
        preset = {'preset_id': ('F02' if state['sex'] == 'female' else 'M02') + '_Average',
                  'base_avatar': state['preset_source'], 'source_project': state['preset_source'], 'sex': state['sex']}
        library = {'schema_version': 1, 'diagnostic_mode': 'cc_character_creation',
                   'presets': [preset], 'character_creation': config, 'eye_snapshot_mode': 'transforms_only'}
        if extra:
            library.update(extra)
        print('Creation ' + state['character_id'] + ': ' + step_id, flush=True)
        result = driver.submit_step(state, step_id, library, output)
        result = driver.wait_step(state, step_id, wait_seconds)
        if result['status'] == 'pending':
            raise PendingStep()
        if result['status'] == 'failed':
            raise ControllerError('Bridge step failed: ' + step_id)
        report = read(output / 'creation_report.json')
        if report.get('success') is not True or report.get('source_unchanged') is not True:
            raise ControllerError('Creation operation rejected: ' + step_id + ': ' + str(report.get('error')))
        outputs = {'report': output / 'creation_report.json'}
        appearance = report.get('native_appearance', {})
        if appearance_mode == 'headshot_native' and 'after' not in appearance:
            raise ControllerError('Native operation omitted the after appearance snapshot: ' + step_id)
        for label in ('before','after'):
            if label not in appearance:
                continue
            record = appearance[label]
            verify(record, 'Native appearance snapshot ' + label)
            outputs['native_appearance_' + label] = record
        if report.get('saved_project'):
            outputs['project'] = report['saved_project']
        for filename in ('before_world_mesh.json', 'before_mesh.json', 'before_body.obj', 'after_mesh.json',
                         'initial_0_local_and_bones.json', 'return_0_local_and_bones.json', 'assembly_report.json', 'assembly_geometry_invariants.json'):
            if (output / filename).is_file():
                outputs[filename] = output / filename
        driver.mark_step_complete(state, step_id, outputs)
        return report

    def mesh_extra(source, mode, obj=None):
        config = {'source_project': source, 'mode': mode, 'experiment_root': str(RUN_ROOT),
                  'refinement_iterations': 0, 'replacement_backend': 'mesh'}
        if obj:
            config['replacement_obj'] = obj
        return {'headshot_mesh_replace': config}

    def offline_bind(name, path):
        if name in state['offline_outputs']:
            verify(state['offline_outputs'][name], 'Offline ' + name)
        else:
            state['offline_outputs'][name] = bind(path)
            driver.persist(state)
        return state['offline_outputs'][name]

    try:
        source = state['preset_source']
        if state['source_mode'] == 'photo':
            photo = state['inputs']['working_input']
            result = step('01_photo', 'photo', source, {'headshot_photo_probe': {
                'photo_path': photo['path'], 'photo_sha256': photo['sha256'], 'skin_preset': 'Clean Soft',
                'body_type': 'current', 'pre_generation_subdiv_level': 0, 'capture_route_previews': False}})
            source = result['saved_project']
        support = {'proportion_preset': selected['proportion_preset']}
        if appearance_mode == 'assembled':
            support.update({'support_assets': selected['appearance_support_assets'],
                            'eyelash_diffuse': selected['eyelash_diffuse_repair'],
                            'tongue_diffuse': selected['tongue_diffuse']})
        prepared = step('02_prepare', 'prepare', source, {'character_creation': support})['saved_project']
        step('03_capture', 'capture', prepared, mesh_extra(prepared, 'capture_only'))
        capture_dir = directory / '03_capture'
        world = np.asarray(read(capture_dir / 'before_world_mesh.json')['vertices'], dtype=float)
        for axis in ('zero', 'x', 'y', 'z'):
            target_path = directory / ('calibration_' + axis + '.obj')
            name = 'calibration_' + axis
            if name not in state['offline_outputs']:
                vertices = world.copy()
                if axis != 'zero':
                    vertices[:, ('x', 'y', 'z').index(axis)] += .1
                write_world_obj(capture_dir / 'before_body.obj', vertices, target_path)
            target = offline_bind(name, target_path)
            step('04_calibrate_' + axis, 'replace', prepared, mesh_extra(prepared, 'normalized', target))
        identity_source = read(directory / '04_calibrate_zero/creation_report.json')['saved_project']
        step('05_identity_roundtrip', 'roundtrip', identity_source)
        target_dir = directory / '06_geometry_target'
        if 'geometry_report' not in state['offline_outputs']:
            build_geometry_targets(capture_dir, {axis: directory / ('04_calibrate_' + axis) for axis in ('zero', 'x', 'y', 'z')},
                                   directory / '05_identity_roundtrip', state['sex'], target_dir, state['references_path'])
            offline_bind('geometry_report', target_dir / 'geometry_report.json')
            offline_bind('geometry_arrays', target_dir / 'target_geometry.npz')
            offline_bind('geometry_target', target_dir / 'target_world.obj')
        for name in ('geometry_report', 'geometry_arrays', 'geometry_target'):
            verify(state['offline_outputs'][name], name)
        applied = step('07_apply_geometry', 'replace', prepared, mesh_extra(prepared, 'normalized', state['offline_outputs']['geometry_target']))['saved_project']
        corrected = step('08_normalize_geometry', 'roundtrip', applied)['saved_project']
        if selected['requires_final_neutral_morph_bake']:
            evidence_path = directory / 'late_bake_input.json'
            if 'late_bake_input' not in state['offline_outputs']:
                write(evidence_path, {'candidate_project': corrected, 'geometry_target': state['offline_outputs']['geometry_report']})
            evidence = offline_bind('late_bake_input', evidence_path)
            baked = step('09_late_bake', 'late_bake', corrected, {'headshot_execution_root': str(RUN_ROOT),
                'headshot_route_validation': {'operation': 'late_bake_native_control', 'source_project': corrected,
                    'geometry_evidence': evidence, 'case_id': request['character_id'], 'route': 'r1', 'sex': 'female'}})['saved_project']
            corrected = step('10_post_bake_roundtrip', 'roundtrip', baked)['saved_project']
        step('11_final_capture', 'capture', corrected, mesh_extra(corrected, 'capture_only'))
        verify_final_geometry(state, driver, target_dir, directory / '11_final_capture')
        if appearance_mode == 'headshot_native':
            review = verify_native_appearance(state, driver)
            state.update(status='completed', result_project=corrected,
                geometry_result=state['offline_outputs']['final_geometry_review'],
                native_appearance_review=review,
                scope='CC-only Average/fixed-head geometry correction; native appearance sampled comparison passed; no assembly, export, UE or render',
                appearance_mode=appearance_mode, appearance_source='headshot_generated_or_supplied_project',
                visual_acceptance='geometry_only_representative_review_pending')
            driver.persist(state)
            write(directory / 'creation_result.json', {'status':'completed','character_id':request['character_id'],
                'source_mode':state['source_mode'],'appearance_mode':appearance_mode,
                'inputs':state['inputs'],'result_project':state['result_project'],'geometry_result':state['geometry_result'],
                'native_appearance_review':review,
                'appearance_source':state['appearance_source'],'state_path':state['state_path'],
                'scope':state['scope'],'visual_acceptance':state['visual_acceptance']})
            return state
        assembly_request = {'character_id': request['character_id'], 'sex': state['sex'], 'seed': request['seed'],
            'source_project': corrected['path'], 'source_sha256': corrected['sha256'],
            'output_project': str(directory / '12_assemble' / ('CHARACTER_' + request['character_id'] + '.ccProject')),
            'regions_path': selected['regions']['path'], 'geometry_policy_path': str(POLICY),
            'geometry_policy_sha256': state['inputs']['assembly_geometry_policy']['sha256'],
            'facial_components': dict(request.get('facial_components', {}))}
        # The existing real-CC allowance is asset-specific. Pin this known lash
        # recipe by default; other requested assets retain strict no-exemption.
        assembly_request['facial_components'].setdefault('eyelash_asset_id', 'CCAPP_EYELASHES_284c3a142668')
        manifest_path = directory / 'assembly_manifest.json'
        if 'assembly_manifest' not in state['offline_outputs']:
            manifest = compile_base_assembly(assembly_request)
            manifest['creation_lineage'] = {'mode': state['source_mode'], 'original_input': state['inputs']['original'],
                                            'references': state['inputs']['references']}
            write(manifest_path, manifest)
        offline_bind('assembly_manifest', manifest_path)
        manifest = read(manifest_path)
        assembled = step('12_assemble', 'assemble', corrected, {'base_assembly': manifest})
        state.update(status='completed', result_project=assembled['saved_project'],
                     geometry_result=state['offline_outputs']['final_geometry_review'],
                     scope='CC-only corrected and assembled project; no export, UE or render',
                     visual_acceptance='representative_review_pending')
        driver.persist(state)
        write(directory / 'creation_result.json', {'status': 'completed', 'character_id': request['character_id'],
            'source_mode': state['source_mode'], 'appearance_mode': appearance_mode,
            'inputs': state['inputs'], 'result_project': state['result_project'],
            'assembly_manifest': state['offline_outputs']['assembly_manifest'], 'geometry_result': state['geometry_result'],
            'state_path': state['state_path'], 'scope': state['scope'], 'visual_acceptance': state['visual_acceptance']})
        return state
    except PendingStep:
        state['status'] = 'pending'
        driver.persist(state)
        return state
    except Exception as error:
        # Uncertain submission remains pending; only known/offline failures may
        # start a new attempt. No completed step is erased or overwritten.
        if any(s['status'] == 'pending' for s in state['steps'].values()):
            state['status'] = 'pending'
        else:
            state['status'] = 'failed'
        state['failure'] = {'message': str(error)}
        driver.persist(state)
        raise


class PendingStep(Exception):
    pass


def native_appearance_comparison(before, after, before_obj=None, after_obj=None):
    """Compare observed appearance only; intended geometry positions are excluded."""
    mismatches, limitations = [], [
        'Texture fingerprints compare 25 ARGB samples and shader metadata, not every texture pixel.',
        'This check does not imply visual, expression, export or UE acceptance.']
    checks = {}
    def equal(name, left, right):
        checks[name] = left == right
        if not checks[name]:
            mismatches.append(name)
    for value in (before, after):
        if value.get('appearance_mode') != 'headshot_native':
            raise ControllerError('Native appearance snapshot has the wrong mode')
    equal('working_subdivision', before.get('working_subdivision'), after.get('working_subdivision'))
    equal('geometry_topology', sorted(before['geometry_topology'], key=lambda v:v['name']),
          sorted(after['geometry_topology'], key=lambda v:v['name']))
    for key, items_key, fields in (
        ('parts', 'parts', ('avatar_part_type','name','python_type')),
        ('assets', 'objects', ('collection','name','python_type'))):
        def stable(snapshot):
            records = snapshot[key][items_key]
            if any(item.get('python_type') == 'GetterError' for item in records):
                limitations.append(key + ' inventory contains a getter observation error.')
            return sorted(tuple(item.get(field) for field in fields) for item in records)
        equal(key, stable(before), stable(after))
    for label, snapshot in (('before', before), ('after', after)):
        materials = snapshot['materials']
        if not materials.get('digest') or not materials.get('mesh_digests'):
            raise ControllerError('Native appearance material observation is incomplete: ' + label)
        if materials.get('observation_error_count', 0) or materials.get('observation_errors'):
            limitations.append(label + ' material observation errors: ' +
                               str(materials.get('observation_error_count', len(materials.get('observation_errors', [])))))
    for field in ('digest','mesh_digests','material_count','texture_count'):
        equal('materials.' + field, before['materials'].get(field), after['materials'].get(field))
    def obj_layout(path):
        if path is None:
            return None
        # Positions/normals legitimately change during correction. Preserve UV
        # values, material selection and the face vertex/UV/normal index layout.
        records = []
        has_uv = False
        with Path(path).open(encoding='utf-8-sig') as stream:
            for line in stream:
                tokens = line.split()
                if tokens and tokens[0] in ('vt','usemtl','f'):
                    records.append(tokens)
                    has_uv |= tokens[0] == 'vt'
        return records if has_uv else None
    left, right = obj_layout(before_obj), obj_layout(after_obj)
    if left is None or right is None:
        limitations.append('Body OBJ UV layout was unavailable; UV preservation is not proven by this review.')
        checks['body_obj_uv_material_index_layout'] = None
    else:
        equal('body_obj_uv_material_index_layout', left, right)
    return {'schema_version':1, 'passed':not mismatches, 'checks':checks,
            'mismatches':mismatches, 'limitations':list(dict.fromkeys(limitations)),
            'observation_errors':{label:snapshot['materials'].get('observation_errors', [])
                                  for label,snapshot in (('before',before),('after',after))}}


def verify_native_appearance(state, driver):
    directory = Path(state['attempt_dir'])
    key = 'native_appearance_review'
    if key in state['offline_outputs']:
        verify(state['offline_outputs'][key], 'Native appearance review')
        if read(state['offline_outputs'][key]['path']).get('passed') is not True:
            raise ControllerError('Recorded native appearance comparison failed')
        return state['offline_outputs'][key]
    baseline_step, label = ('01_photo','after') if state['source_mode'] == 'photo' else ('02_prepare','before')
    baseline = read(directory / baseline_step / 'creation_report.json')['native_appearance'][label]
    final = read(directory / '11_final_capture/creation_report.json')['native_appearance']['after']
    verify(baseline, 'Native baseline appearance')
    verify(final, 'Native final appearance')
    before_obj, after_obj = directory / '03_capture/before_body.obj', directory / '11_final_capture/before_body.obj'
    review = native_appearance_comparison(read(baseline['path']), read(final['path']), before_obj, after_obj)
    review.update(baseline=baseline, final=final, baseline_step=baseline_step,
                  body_obj_before=bind(before_obj), body_obj_after=bind(after_obj))
    path = directory / 'native_appearance_review.json'
    write(path, review)
    state['offline_outputs'][key] = bind(path)
    driver.persist(state)
    if not review['passed']:
        raise ControllerError('Native appearance changed: ' + ', '.join(review['mismatches']))
    return state['offline_outputs'][key]


def verify_final_geometry(state, driver, target_dir, capture_dir):
    from cc_compare_headshot_geometry_v1 import head_ids, stats
    path = Path(state['attempt_dir']) / 'final_geometry_review.json'
    if 'final_geometry_review' in state['offline_outputs']:
        verify(state['offline_outputs']['final_geometry_review'], 'Final geometry')
        if read(path)['passed'] is not True:
            raise ControllerError('Recorded final geometry failed')
        return
    actual = np.asarray(read(capture_dir / 'before_world_mesh.json')['vertices'], dtype=float)
    capture = read(capture_dir / 'before_world_mesh.json')
    if capture['working_subdivision_level'] != 0 or capture['world_target_eligible'] is not True:
        raise ControllerError('Final geometry capture must be active SubD0')
    with np.load(target_dir / 'target_geometry.npz', allow_pickle=False) as arrays:
        head = head_ids()
        ids = np.arange(len(actual))
        groups = {'body': (arrays['reference_world'], np.setdiff1d(ids, head), .1),
                  'face': (arrays['source_world'], head[arrays['weights'][head] >= .99], .01),
                  'fixed_head': (arrays['scalp_reference'], head[arrays['weights'][head] <= .01], .2)}
        results = {name: {'stats': stats(reference, actual, indices), 'limit_mm': limit}
                   for name, (reference, indices, limit) in groups.items()}
    # Limits cover the already accepted manual-photo final measurements
    # (.061568/.006487/.103751mm), not the unchanged assembly R06 thresholds.
    for value in results.values():
        value['passed'] = value['stats']['max_displacement_mm'] <= value['limit_mm']
    passed = all(value['passed'] for value in results.values())
    write(path, {'schema_version': 1, 'passed': passed, 'regions': results,
                 'threshold_basis': 'Accepted manual photo01 final CC geometry; separate from assembly R06 0.002mm.',
                 'actual_capture': bind(capture_dir / 'before_world_mesh.json'),
                 'target_arrays': bind(target_dir / 'target_geometry.npz')})
    state['offline_outputs']['final_geometry_review'] = bind(path)
    driver.persist(state)
    if not passed:
        raise ControllerError('Final body/face/fixed-head geometry exceeded the measured correction bounds')
