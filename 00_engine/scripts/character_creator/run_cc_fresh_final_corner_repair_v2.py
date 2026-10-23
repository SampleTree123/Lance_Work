"""Incremental corner-rule repair from a proven same-source calibration.

Explicit evidence-bound operator required. Default prepare/inspect only;
never changes prior failed receipts, original solver/operator, proportions or bake.
"""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from cc_character_creation_job_state_v1 import (
    RUN_ROOT, STAGE_ROOT, BridgeStepDriver, ControllerError, SAFE_ID, bind,
    controller_lock, fingerprint, read, verify, write,
)
from cc_headshot_geometry_solver_v1 import inverse_sparse, verified_world, write_world_obj
from cc_lash_corner_operator_v2 import corner_identity_operator
from run_cc_fresh_final_geometry_repair_v1 import run_step, saved_project

TAIL = [('05_apply_target', 'replace'), ('06_normalize', 'roundtrip'),
        ('07_normalized_capture', 'capture'), ('08_saved_roundtrip', 'roundtrip'),
        ('09_final_reload_capture', 'capture'), ('10_review', 'offline')]


def solve_corrected_submission(fresh_arrays, zero, identity_return, operator):
    correction, stats = inverse_sparse(fresh_arrays['desired_local'] - identity_return, operator)
    submitted = fresh_arrays['current_world'] + np.linalg.solve(
        fresh_arrays['skin_affine'], correction[..., None])[..., 0]
    return {'desired_world': fresh_arrays['desired_world'], 'desired_local': fresh_arrays['desired_local'],
            'submitted_world': submitted, 'precomp': zero + correction,
            'current_world': fresh_arrays['current_world'], 'current_local': fresh_arrays['current_local'],
            'skin_affine': fresh_arrays['skin_affine']}, stats


def prepare(candidate_id, prior_state_path, operator_path, operator_evidence_path):
    from cc_compare_headshot_geometry_v1 import read_obj
    if not SAFE_ID.fullmatch(candidate_id):
        raise ControllerError('Safe new candidate ID required')
    root = Path(RUN_ROOT) / candidate_id / 'attempt_001'
    stage = Path(STAGE_ROOT) / candidate_id / 'attempt_001'
    if root.exists() or stage.exists():
        raise ControllerError('Candidate exists; resume via --state')
    prior = read(prior_state_path)
    driver = BridgeStepDriver()
    driver.verify_state_inputs(prior)
    if prior['status'] != 'failed':
        raise ControllerError('Requires retained failed v1 candidate')
    for step in prior['steps'].values():
        driver.verify_completed_step(prior, step)
    for record in prior['offline_outputs'].values():
        verify(record, 'Prior offline receipt')
    prior_root = Path(prior['attempt_dir'])
    failed = read(prior_root / 'final_repair_review.json')
    if [name for name, region in failed['regions'].items() if not region['passed']] != ['photo_lash']:
        raise ControllerError('Incremental tail is limited to the diagnosed photo_lash failure')
    evidence = read(operator_evidence_path)
    verify(evidence['prior_state'], 'Operator prior state')
    if Path(evidence['prior_state']['path']).resolve() != Path(prior_state_path).resolve():
        raise ControllerError('Operator evidence belongs to a different prior state')
    verify(evidence['operator'], 'Corner operator')
    if Path(evidence['operator']['path']).resolve() != Path(operator_path).resolve():
        raise ControllerError('Explicit operator differs from evidence')
    for record in evidence['inputs']:
        verify(record, 'Operator calibration evidence')
    with np.load(prior['inputs']['subdivision_operator']['path'], allow_pickle=False) as original:
        old_operator = {k: original[k].copy() for k in original.files}
    with np.load(prior['inputs']['candidate_arrays']['path'], allow_pickle=False) as candidate:
        lash = candidate['lash_indices'].copy()
    _, _, faces = read_obj(prior_root / '01_capture/before_body.obj')
    expected, corners = corner_identity_operator(old_operator, faces, lash, 14164)
    with np.load(operator_path, allow_pickle=False) as op:
        operator = {k: op[k].copy() for k in op.files}
    if set(expected) != set(operator) or any(not np.array_equal(expected[k], operator[k]) for k in expected):
        raise ControllerError('Explicit operator changes more than the evidenced16 rows')
    if len(corners) != 16 or evidence['changed_row_indices'] != corners.tolist():
        raise ControllerError('Corner membership differs from measured evidence')
    with np.load(prior['offline_outputs']['target_arrays']['path'], allow_pickle=False) as f:
        fresh = {k: f[k].copy() for k in f.files}
    zero = np.asarray(read(prior_root / '02_calibrate_zero/after_mesh.json')['vertices'])
    identity = np.asarray(read(prior_root / '03_identity_roundtrip/return_0_local_and_bones.json')['vertices'])
    arrays, stats = solve_corrected_submission(fresh, zero, identity, operator)
    increment = np.linalg.norm(arrays['submitted_world'] - fresh['submitted_world'], axis=1) * 10
    nonlash = np.setdiff1d(np.arange(14164), lash)
    if increment[nonlash].max() > 1e-9 or increment.max() > .1:
        raise ControllerError('Increment exceeds native-lash-only0.1mm corrective bound')
    source = prior['inputs']['original_final_project']
    verify(source, 'Same immutable calibrated original source')
    if source['sha256'] != prior['inputs']['working_project']['sha256']:
        raise ControllerError('Prior calibrated copy is not exact same original source')
    inputs = {**prior['inputs'], 'prior_failed_state': bind(prior_state_path),
              'prior_failed_review': bind(prior_root / 'final_repair_review.json'),
              'original_subdivision_operator': prior['inputs']['subdivision_operator'],
              'subdivision_operator': bind(operator_path), 'corner_operator_evidence': bind(operator_evidence_path),
              'implementation_incremental_controller': bind(__file__),
              'implementation_corner_operator': bind(Path(__file__).with_name('cc_lash_corner_operator_v2.py')),
              'reused_fresh_arrays': prior['offline_outputs']['target_arrays']}
    for step_id, step in prior['steps'].items():
        for name, record in step['outputs'].items():
            inputs['prior_' + step_id + '_' + name] = record
    request = {'character_id': candidate_id, 'sex': prior['sex'], 'appearance_mode': 'headshot_native',
               'source_project': source['path'], 'prior_failed_state': str(Path(prior_state_path).resolve()),
               'operator': str(Path(operator_path).resolve()), 'operator_evidence': str(Path(operator_evidence_path).resolve()),
               'purpose': 'same_source_calibration_reuse_only16native_corner_operator_fix'}
    root.mkdir(parents=True)
    stage.mkdir(parents=True)
    working_path = stage / 'FINAL_INPUT.ccProject'
    shutil.copyfile(source['path'], working_path)
    working = bind(working_path)
    if working['sha256'] != source['sha256']:
        raise ControllerError('New working source differs from proven calibration source')
    inputs['previous_working_project'] = prior['inputs']['working_project']
    inputs['working_project'] = working
    output = root / '04_external_target'
    output.mkdir()
    target = output / 'submitted_world.obj'
    write_world_obj(prior_root / '01_capture/before_body.obj', arrays['submitted_world'], target)
    np.savez_compressed(output / 'fresh_compensation.npz', **arrays)
    target_report = {'schema_version': 2, 'status': 'offline_corrected_corner_target_requires_CC_application',
        'reused_calibration_source': source, 'prior_failed_state': bind(prior_state_path),
        'explicit_operator': bind(operator_path), 'operator_evidence': bind(operator_evidence_path),
        'changed_operator_rows': corners.tolist(), 'solver': stats,
        'submitted_increment_max_mm': float(increment.max()),
        'submitted_nonlash_increment_max_mm': float(increment[nonlash].max()),
        'target': bind(target), 'arrays': bind(output / 'fresh_compensation.npz')}
    write(output / 'external_target_report.json', target_report)
    state = {'schema_version': 2, 'character_id': candidate_id, 'sex': prior['sex'], 'request': request,
             'request_fingerprint': fingerprint(request), 'appearance_mode': 'headshot_native',
             'status': 'prepared', 'attempt_id': 'attempt_001', 'attempt_dir': str(root), 'stage_dir': str(stage),
             'state_path': str(root / 'repair_state.json'), 'inputs': inputs, 'working_project': working,
             'steps': {}, 'offline_outputs': {'target_obj': bind(target),
                'target_arrays': bind(output / 'fresh_compensation.npz'), 'target_report': bind(output / 'external_target_report.json')},
             'step_plan': TAIL, 'limits_mm': prior['limits_mm'], 'baseline_capture_dir': str(prior_root / '01_capture')}
    write(root / 'request.json', request)
    write(root / 'step_plan.json', {'steps': TAIL, 'reuses': 'Same immutable character/source capture and four-probe calibration; bound original receipts',
        'forbidden': ['prepare', 'bake', 'appearance changes', 'original operator/state edits']})
    write(state['state_path'], state)
    return state


def review(state, driver):
    from cc_character_creation_pipeline_v1 import native_appearance_comparison
    root = Path(state['attempt_dir'])
    baseline = Path(state['baseline_capture_dir'])
    actual = verified_world(read(root / '09_final_reload_capture/before_world_mesh.json'))
    normalized = verified_world(read(root / '07_normalized_capture/before_world_mesh.json'))
    with np.load(state['offline_outputs']['target_arrays']['path'], allow_pickle=False) as f:
        target = f['desired_world'].copy()
    with np.load(state['inputs']['candidate_arrays']['path'], allow_pickle=False) as c:
        groups = {'all_target': np.arange(len(actual)), 'photo_face': c['head_indices'][c['weights'][c['head_indices']] >= .99],
                  'photo_lash': c['lash_indices'], 'upper_head': c['protected_upper_head_indices'],
                  'outside_repair': np.setdiff1d(np.arange(len(actual)), np.union1d(c['jaw_band_indices'], c['lash_indices']))}
    regions = {}
    for name, ids in groups.items():
        error = float(np.linalg.norm(actual[ids] - target[ids], axis=1).max() * 10)
        limit = state['limits_mm'][name]
        regions[name] = {'vertex_count': len(ids), 'target_max_error_mm': error, 'limit_mm': limit, 'passed': error <= limit}
    initial_report = read(baseline / 'creation_report.json')
    final_report = read(root / '09_final_reload_capture/creation_report.json')
    appearance = native_appearance_comparison(read(initial_report['native_appearance']['after']['path']),
        read(final_report['native_appearance']['after']['path']), baseline / 'before_body.obj', root / '09_final_reload_capture/before_body.obj')
    observation_errors = appearance.get('observation_errors', {})
    pixel_available = not any(observation_errors.get(key) for key in ('before', 'after'))
    # Even a successful25-sample getter is not full-pixel verification.
    appearance.update(pixel_sampling_available=pixel_available, material_pixels_verified=False,
        acceptance='Observable metadata/parts/topology/UV only. Texture pixels unavailable when getters report errors.')
    drift = float(np.linalg.norm(actual - normalized, axis=1).max() * 10)
    result = {'schema_version': 2, 'passed': all(v['passed'] for v in regions.values()) and appearance['passed'] and drift <= .01,
              'regions': regions, 'second_roundtrip_reload_max_drift_mm': drift,
              'second_roundtrip_reload_limit_mm': .01, 'native_appearance': appearance,
              'material_pixels_verified': False, 'visual_acceptance': 'pending',
              'scope': 'CC mechanical geometry and observable metadata only; texture pixels/visual/expression/export/UE unverified',
              'actual_capture': bind(root / '09_final_reload_capture/before_world_mesh.json')}
    path = root / 'final_repair_review.json'
    write(path, result)
    state['offline_outputs']['final_review'] = bind(path)
    state.update(status='completed' if result['passed'] else 'failed', visual_acceptance='pending',
                 result_project=saved_project(state, '08_saved_roundtrip'), scope=result['scope'])
    driver.persist(state)
    write(root / 'repair_result.json', {'status': state['status'], 'result_project': state['result_project'],
          'inputs': state['inputs'], 'review': state['offline_outputs']['final_review'],
          'scope': result['scope'], 'material_pixels_verified': False, 'visual_acceptance': 'pending'})
    if not result['passed']:
        raise ControllerError('Corrected corner candidate failed; preserve it and inspect final review')


def advance(state, driver, max_steps=1, wait_seconds=0):
    if type(max_steps) is not int or max_steps < 1:
        raise ControllerError('max_steps must be positive')
    driver.verify_state_inputs(state)
    for record in state['offline_outputs'].values():
        verify(record, 'Offline output')
    if state['status'] == 'failed':
        raise ControllerError('Failed candidate requires new ID')
    done = 0
    for step_id, operation in TAIL:
        if operation == 'offline':
            if state['status'] == 'completed':
                continue
            review(state, driver)
        else:
            old = state['steps'].get(step_id)
            if old and old['status'] == 'completed':
                driver.verify_completed_step(state, old)
                continue
            target = state['offline_outputs']['target_obj'] if step_id == '05_apply_target' else None
            source = state['working_project']
            if step_id == '06_normalize':
                source = saved_project(state, '05_apply_target')
            elif step_id in ('07_normalized_capture', '08_saved_roundtrip'):
                source = saved_project(state, '06_normalize')
            elif step_id == '09_final_reload_capture':
                source = saved_project(state, '08_saved_roundtrip')
            if not run_step(state, driver, step_id, operation, source, target, wait_seconds):
                return state
        done += 1
        if done >= max_steps:
            return state
    return state


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state')
    p.add_argument('--candidate-id')
    p.add_argument('--prior-state')
    p.add_argument('--operator')
    p.add_argument('--operator-evidence')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--max-steps', type=int, default=1)
    p.add_argument('--wait-seconds', type=float, default=0)
    a = p.parse_args(argv)
    if not np.isfinite(a.wait_seconds) or a.wait_seconds < 0:
        p.error('wait-seconds must be finite/nonnegative')
    if a.state and any((a.candidate_id, a.prior_state, a.operator, a.operator_evidence)):
        p.error('--state is exclusive with new candidate arguments')
    if not a.state and not all((a.candidate_id, a.prior_state, a.operator, a.operator_evidence)):
        p.error('New candidate requires candidate-id/prior-state/operator/operator-evidence')
    with controller_lock():
        state = read(a.state) if a.state else prepare(a.candidate_id, a.prior_state, a.operator, a.operator_evidence)
        driver = BridgeStepDriver()
        driver.verify_state_inputs(state)
        if a.execute:
            state = advance(state, driver, a.max_steps, a.wait_seconds)
        print(json.dumps({k: state.get(k) for k in ('character_id', 'status', 'state_path', 'result_project')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
