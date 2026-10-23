"""Prepare or advance one isolated final-project geometry repair. No preparation/bake.

Uses existing bounded native runtime and durable Bridge driver. Default is
read-only inspection/preparation; --execute is mandatory for Bridge work.
"""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from cc_character_creation_job_state_v1 import (
    RUN_ROOT, STAGE_ROOT, BridgeStepDriver, ControllerError, SAFE_ID,
    bind, controller_lock, fingerprint, read, verify, write,
)
from cc_headshot_geometry_solver_v1 import (
    align_reference, inverse_sparse, points, skin_affine, verified_world,
    verify_identity_origin, write_world_obj,
)

STEP_PLAN = [
    ('01_capture', 'capture'),
    ('02_calibrate_zero', 'replace'), ('02_calibrate_x', 'replace'),
    ('02_calibrate_y', 'replace'), ('02_calibrate_z', 'replace'),
    ('03_identity_roundtrip', 'roundtrip'),
    ('04_external_target', 'offline'), ('05_apply_target', 'replace'),
    ('06_normalize', 'roundtrip'), ('07_normalized_capture', 'capture'),
    ('08_saved_roundtrip', 'roundtrip'), ('09_final_reload_capture', 'capture'),
    ('10_review', 'offline'),
]


def make_library(state, operation, source, target=None):
    if operation not in ('capture', 'replace', 'roundtrip'):
        raise ControllerError('Only capture/replace/roundtrip are authorized')
    config = {'operation': operation, 'source_project': source,
              'appearance_mode': 'headshot_native'}
    library = {'schema_version': 1, 'diagnostic_mode': 'cc_character_creation',
               'presets': [{'preset_id': ('F02' if state['sex'] == 'female' else 'M02') + '_Average',
                            'base_avatar': state['working_project'], 'source_project': state['working_project'],
                            'sex': state['sex']}], 'character_creation': config,
               'eye_snapshot_mode': 'transforms_only'}
    if operation in ('capture', 'replace'):
        probe = {'source_project': source, 'mode': 'capture_only' if operation == 'capture' else 'normalized',
                 'experiment_root': str(RUN_ROOT), 'refinement_iterations': 0,
                 'replacement_backend': 'mesh'}
        if operation == 'replace':
            if not target:
                raise ControllerError('Replace requires a bound target OBJ')
            probe['replacement_obj'] = target
        library['headshot_mesh_replace'] = probe
    return library


def prepare(candidate_id, sex, source_project, candidate_report, *, run_root=RUN_ROOT, stage_root=STAGE_ROOT):
    if not SAFE_ID.fullmatch(candidate_id) or sex not in ('female', 'male'):
        raise ControllerError('Safe candidate ID and explicit sex required')
    directory = Path(run_root).resolve() / candidate_id / 'attempt_001'
    staging = Path(stage_root).resolve() / candidate_id / 'attempt_001'
    if directory.exists() or staging.exists():
        raise ControllerError('Candidate already exists; use --state to inspect or resume')
    source = bind(source_project)
    if Path(source['path']).suffix.lower() != '.ccproject':
        raise ControllerError('Source must be a final .ccProject')
    candidate = bind(candidate_report)
    report = read(candidate['path'])
    arrays = report['candidate_arrays']
    verify(arrays, 'External candidate arrays')
    verify(report['archive_geometry_report'], 'Archive geometry report')
    archive = read(report['archive_geometry_report']['path'])
    if archive['sex'] != sex:
        raise ControllerError('Candidate archive sex differs from request')
    original_world = next(r for r in report['inputs'] if Path(r['path']).name == 'before_world_mesh.json')
    for record in report['inputs']:
        verify(record, 'Candidate provenance')
    refs = archive['reference_config']
    verify(refs, 'Creation references')
    operator = read(refs['path'])['shared']['subdivision_operator']
    verify(operator, 'Subdivision operator')
    archived_attempt = Path(report['archive_geometry_report']['path']).parent.parent
    archived_result = read(archived_attempt / 'creation_result.json')
    verify(archived_result['geometry_result'], 'Archived final geometry review')
    archived_final_world = read(archived_result['geometry_result']['path'])['actual_capture']
    verify(archived_final_world, 'Archived final world identity')
    request = {'character_id': candidate_id, 'sex': sex, 'source_project': source['path'],
               'candidate_report': candidate['path'], 'appearance_mode': 'headshot_native',
               'purpose': 'fresh_final_external_target_repair_no_prepare_no_bake'}
    inputs = {'original_final_project': source, 'candidate_report': candidate,
              'candidate_arrays': arrays, 'archive_world': original_world,
              'archive_geometry_report': report['archive_geometry_report'],
              'archive_final_world': archived_final_world,
              'references': refs, 'subdivision_operator': operator,
              'implementation_controller': bind(__file__)}
    for name in ('cc_character_creation_job_state_v1.py', 'cc_run_character_creation_v1.py',
                 'cc_headshot_geometry_solver_v1.py', 'cc_validate_body_reconstruction.py',
                 'cc_compare_headshot_geometry_v1.py', 'cc_character_creation_pipeline_v1.py'):
        inputs['implementation_' + name] = bind(Path(__file__).with_name(name))
    directory.mkdir(parents=True)
    staging.mkdir(parents=True)
    working_path = staging / 'FINAL_INPUT.ccProject'
    shutil.copyfile(source['path'], working_path)
    working = bind(working_path)
    if working['sha256'] != source['sha256']:
        raise ControllerError('Working project copy SHA mismatch')
    inputs['working_project'] = working
    state = {'schema_version': 1, 'character_id': candidate_id, 'sex': sex,
             'request': request, 'request_fingerprint': fingerprint(request),
             'status': 'prepared', 'appearance_mode': 'headshot_native',
             'attempt_id': 'attempt_001', 'attempt_dir': str(directory), 'stage_dir': str(staging),
             'state_path': str(directory / 'repair_state.json'), 'inputs': inputs,
             'working_project': working, 'steps': {}, 'offline_outputs': {},
             'completed_offline_steps': [], 'step_plan': STEP_PLAN,
             'limits_mm': {'all_target': .1, 'photo_face': .01, 'photo_lash': .01,
                           'upper_head': .1, 'outside_repair': .1}}
    write(directory / 'request.json', request)
    write(directory / 'step_plan.json', {'steps': STEP_PLAN, 'forbidden_operations': ['prepare', 'late_bake', 'assemble', 'repair_support', 'photo'],
          'scope': 'Isolated final-project copy; new calibration; external target; two normalization/save/reload checks; no visual acceptance'})
    write(state['state_path'], state)
    return state


def compensate_external(current_world, current_local, desired_world, calibration, initial_local,
                        identity_return_local, model):
    count = len(current_local)
    world = verified_world(current_world, count)
    local = points(current_local, count, 'current local')
    desired_world = points(desired_world, count, 'external desired world')
    origin = verify_identity_origin(initial_local, calibration['zero'], count)
    baseline, matrix, affine = skin_affine(calibration, count)
    desired_local = local + np.einsum('nij,nj->ni', matrix, desired_world - world)
    correction, solver = inverse_sparse(desired_local - points(identity_return_local, count, 'fresh identity return'), model)
    submitted = world + np.linalg.solve(matrix, correction[..., None])[..., 0]
    return {'desired_world': desired_world, 'desired_local': desired_local,
            'submitted_world': submitted, 'precomp': baseline + correction,
            'current_world': world, 'current_local': local, 'skin_affine': matrix}, {
                'identity_origin': origin, 'skin_affine': affine, 'solver': solver}


def saved_project(state, step_id):
    return read(Path(state['attempt_dir']) / step_id / 'creation_report.json')['saved_project']


def run_step(state, driver, step_id, operation, source, target, wait_seconds):
    library = make_library(state, operation, source, target)
    output = Path(state['attempt_dir']) / step_id
    old = state['steps'].get(step_id)
    if old and old['status'] == 'completed':
        driver.verify_completed_step(state, old)
        return True
    driver.submit_step(state, step_id, library, output)
    result = driver.wait_step(state, step_id, wait_seconds)
    if result['status'] == 'pending':
        return False
    if result['status'] != 'succeeded':
        raise ControllerError('Bridge repair step failed: ' + step_id)
    report = read(output / 'creation_report.json')
    if report.get('success') is not True or report.get('source_unchanged') is not True:
        raise ControllerError('Repair operation did not preserve its source: ' + step_id)
    outputs = {'report': output / 'creation_report.json'}
    if report.get('saved_project'):
        outputs['project'] = report['saved_project']
    for label, record in report.get('native_appearance', {}).items():
        if label in ('before', 'after'):
            outputs['native_' + label] = record
    for filename in ('before_world_mesh.json', 'before_mesh.json', 'before_body.obj', 'after_mesh.json',
                     'initial_0_local_and_bones.json', 'return_0_local_and_bones.json'):
        if (output / filename).is_file():
            outputs[filename] = output / filename
    driver.mark_step_complete(state, step_id, outputs)
    return True


def build_external_target(state, driver):
    from cc_compare_headshot_geometry_v1 import read_obj
    directory = Path(state['attempt_dir'])
    capture = directory / '01_capture'
    world = read(capture / 'before_world_mesh.json')
    local = read(capture / 'before_mesh.json')['vertices']
    archived_final = read(state['inputs']['archive_final_world']['path'])
    aligned_final = align_reference(archived_final, world, len(local))
    identity_error = float(np.linalg.norm(verified_world(world, len(local)) - aligned_final, axis=1).max() * 10)
    if identity_error > .01:
        raise ControllerError('Fresh final geometry does not match archived character within 0.01mm')
    source_topology = read_obj(capture / 'before_body.obj')
    archive_report = read(state['inputs']['archive_geometry_report']['path'])
    archive_obj = next(r for r in archive_report['inputs'] if Path(r['path']).name == 'before_body.obj')
    verify(archive_obj, 'Archived Body OBJ')
    archive_topology = read_obj(archive_obj['path'])
    if source_topology[2] != archive_topology[2] or not np.array_equal(source_topology[1], archive_topology[1]):
        raise ControllerError('Fresh final topology/UV differs from archive')
    calibration = {}
    for axis in ('zero', 'x', 'y', 'z'):
        folder = directory / ('02_calibrate_' + axis)
        if read(folder / 'before_world_mesh.json') != world:
            raise ControllerError('Calibration belongs to a different current world state: ' + axis)
        if not np.array_equal(read(folder / 'before_mesh.json')['vertices'], local):
            raise ControllerError('Calibration belongs to a different current local state: ' + axis)
        calibration[axis] = read(folder / 'after_mesh.json')['vertices']
    archive_world = read(state['inputs']['archive_world']['path'])
    # align_reference enforces active SubD0, exact rotation/scale, translation only.
    aligned_archive_source = align_reference(archive_world, world, len(local))
    archive_source = verified_world(archive_world, len(local))
    with np.load(state['inputs']['candidate_arrays']['path'], allow_pickle=False) as candidate:
        desired_world = candidate['desired_world'] + aligned_archive_source - archive_source
    with np.load(state['inputs']['subdivision_operator']['path'], allow_pickle=False) as model:
        arrays, stats = compensate_external(world, local, desired_world, calibration,
            read(directory / '03_identity_roundtrip/initial_0_local_and_bones.json')['vertices'],
            read(directory / '03_identity_roundtrip/return_0_local_and_bones.json')['vertices'], model)
    output = directory / '04_external_target'
    output.mkdir(exist_ok=False)
    target = output / 'submitted_world.obj'
    write_world_obj(capture / 'before_body.obj', arrays['submitted_world'], target)
    np.savez_compressed(output / 'fresh_compensation.npz', **arrays)
    report = {'schema_version': 1, 'status': 'offline_external_target_requires_application', 'stats': stats,
              'fresh_final_identity_error_mm': identity_error, 'fresh_final_identity_limit_mm': .01,
              'source': state['inputs']['original_final_project'], 'candidate': state['inputs']['candidate_report'],
              'submitted_obj': bind(target), 'fresh_arrays': bind(output / 'fresh_compensation.npz')}
    write(output / 'external_target_report.json', report)
    state['offline_outputs'].update(target_obj=bind(target), target_arrays=bind(output / 'fresh_compensation.npz'),
                                    target_report=bind(output / 'external_target_report.json'))
    state['completed_offline_steps'].append('04_external_target')
    driver.persist(state)


def review(state, driver):
    from cc_character_creation_pipeline_v1 import native_appearance_comparison
    directory = Path(state['attempt_dir'])
    current = read(directory / '01_capture/before_world_mesh.json')
    final = read(directory / '09_final_reload_capture/before_world_mesh.json')
    normalized = read(directory / '07_normalized_capture/before_world_mesh.json')
    actual = verified_world(final)
    with np.load(state['offline_outputs']['target_arrays']['path'], allow_pickle=False) as fresh:
        desired = fresh['desired_world']
    with np.load(state['inputs']['candidate_arrays']['path'], allow_pickle=False) as c:
        groups = {'all_target': np.arange(len(actual)), 'photo_face': c['head_indices'][c['weights'][c['head_indices']] >= .99],
                  'photo_lash': c['lash_indices'], 'upper_head': c['protected_upper_head_indices'],
                  'outside_repair': np.setdiff1d(np.arange(len(actual)), np.union1d(c['jaw_band_indices'], c['lash_indices']))}
    regions = {}
    for name, ids in groups.items():
        maximum = float(np.linalg.norm(actual[ids] - desired[ids], axis=1).max() * 10)
        limit = state['limits_mm'][name]
        regions[name] = {'vertex_count': len(ids), 'target_max_error_mm': maximum, 'limit_mm': limit, 'passed': maximum <= limit}
    drift = float(np.linalg.norm(actual - verified_world(normalized), axis=1).max() * 10)
    baseline_report = read(directory / '01_capture/creation_report.json')
    final_report = read(directory / '09_final_reload_capture/creation_report.json')
    appearance = native_appearance_comparison(read(baseline_report['native_appearance']['after']['path']),
        read(final_report['native_appearance']['after']['path']), directory / '01_capture/before_body.obj',
        directory / '09_final_reload_capture/before_body.obj')
    report = {'schema_version': 1, 'passed': all(r['passed'] for r in regions.values()) and appearance['passed'] and drift <= .01,
              'regions': regions, 'second_roundtrip_reload_max_drift_mm': drift,
              'second_roundtrip_reload_limit_mm': .01, 'native_appearance': appearance,
              'actual_capture': bind(directory / '09_final_reload_capture/before_world_mesh.json'),
              'scope': 'CC geometry/native metadata only; visual, expression and export/UE gates pending',
              'source_unchanged': True}
    path = directory / 'final_repair_review.json'
    write(path, report)
    state['offline_outputs']['final_review'] = bind(path)
    state['completed_offline_steps'].append('10_review')
    if not report['passed']:
        state['status'] = 'failed'
        driver.persist(state)
        raise ControllerError('Final candidate mechanical review failed; inspect final_repair_review.json')
    state.update(status='completed', result_project=saved_project(state, '08_saved_roundtrip'),
                 visual_acceptance='pending', scope=report['scope'])
    driver.persist(state)
    write(directory / 'repair_result.json', {'status': 'completed', 'result_project': state['result_project'],
          'inputs': state['inputs'], 'review': state['offline_outputs']['final_review'],
          'scope': report['scope'], 'visual_acceptance': 'pending'})


def advance(state, driver, *, wait_seconds=0, max_steps=1):
    if type(max_steps) is not int or max_steps < 1:
        raise ControllerError('max_steps must be positive')
    driver.verify_state_inputs(state)
    for record in state['offline_outputs'].values():
        verify(record, 'Offline result')
    if state['status'] == 'failed':
        raise ControllerError('Failed candidate needs an independent new ID')
    completed = 0
    directory = Path(state['attempt_dir'])
    for step_id, operation in STEP_PLAN:
        if operation == 'offline':
            if step_id in state['completed_offline_steps']:
                continue
            (build_external_target if step_id == '04_external_target' else review)(state, driver)
        else:
            old = state['steps'].get(step_id)
            if old and old['status'] == 'completed':
                driver.verify_completed_step(state, old)
                continue
            source = state['working_project']
            target = None
            if step_id.startswith('02_calibrate_'):
                axis = step_id.removeprefix('02_calibrate_')
                key = 'calibration_obj_' + axis
                if key not in state['offline_outputs']:
                    world = np.asarray(read(directory / '01_capture/before_world_mesh.json')['vertices'])
                    if axis != 'zero':
                        world[:, 'xyz'.index(axis)] += .1
                    path = directory / ('calibration_' + axis + '.obj')
                    write_world_obj(directory / '01_capture/before_body.obj', world, path)
                    state['offline_outputs'][key] = bind(path)
                    driver.persist(state)
                target = state['offline_outputs'][key]
            elif step_id == '03_identity_roundtrip':
                source = saved_project(state, '02_calibrate_zero')
            elif step_id == '05_apply_target':
                target = state['offline_outputs']['target_obj']
            elif step_id == '06_normalize':
                source = saved_project(state, '05_apply_target')
            elif step_id in ('07_normalized_capture', '08_saved_roundtrip'):
                source = saved_project(state, '06_normalize')
            elif step_id == '09_final_reload_capture':
                source = saved_project(state, '08_saved_roundtrip')
            if not run_step(state, driver, step_id, operation, source, target, wait_seconds):
                return state
        completed += 1
        if completed >= max_steps:
            return state
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state')
    parser.add_argument('--candidate-id')
    parser.add_argument('--sex', choices=('female', 'male'))
    parser.add_argument('--source-project')
    parser.add_argument('--candidate-report')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--max-steps', type=int, default=1)
    parser.add_argument('--wait-seconds', type=float, default=0)
    args = parser.parse_args(argv)
    if args.wait_seconds < 0 or not np.isfinite(args.wait_seconds):
        parser.error('wait-seconds must be finite and nonnegative')
    if args.state and any((args.candidate_id, args.sex, args.source_project, args.candidate_report)):
        parser.error('--state cannot be combined with new candidate inputs')
    if not args.state and not all((args.candidate_id, args.sex, args.source_project, args.candidate_report)):
        parser.error('New candidate requires candidate-id, sex, source-project and candidate-report')
    with controller_lock():
        state = read(args.state) if args.state else prepare(args.candidate_id, args.sex, args.source_project, args.candidate_report)
        driver = BridgeStepDriver()
        driver.verify_state_inputs(state)
        if args.execute:
            state = advance(state, driver, wait_seconds=args.wait_seconds, max_steps=args.max_steps)
        print(json.dumps({k: state.get(k) for k in ('character_id', 'status', 'state_path', 'result_project', 'visual_acceptance')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
