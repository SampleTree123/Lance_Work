"""Fresh per-character calibration with an explicit evidence-bound corner operator.

No prior calibration is reused. Default preparation only; frozen v1/v2 sources
remain immutable. Every new subject still requires its actual final CC gates.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import run_cc_fresh_final_geometry_repair_v1 as fresh
from run_cc_fresh_final_corner_repair_v2 import review as explicit_pixel_review
from cc_character_creation_job_state_v1 import (
    BridgeStepDriver, ControllerError, bind, controller_lock, fingerprint, read, verify, write,
)
from cc_lash_corner_operator_v2 import corner_identity_operator


def validate_operator(candidate_report_path, operator_path, evidence_path):
    from cc_compare_headshot_geometry_v1 import read_obj
    candidate_report = read(candidate_report_path)
    verify(candidate_report['archive_geometry_report'], 'Subject archive')
    verify(candidate_report['candidate_arrays'], 'Subject desired arrays')
    archive = read(candidate_report['archive_geometry_report']['path'])
    verify(archive['reference_config'], 'Subject references')
    references = read(archive['reference_config']['path'])
    original = references['shared']['subdivision_operator']
    verify(original, 'Original operator')
    template = next(r for r in candidate_report['inputs'] if Path(r['path']).name == 'before_body.obj')
    verify(template, 'Subject topology OBJ')
    _, _, faces = read_obj(template['path'])
    with np.load(candidate_report['candidate_arrays']['path'], allow_pickle=False) as c:
        lash = c['lash_indices'].copy()
    if not np.array_equal(lash, np.arange(13411, 14115)):
        raise ControllerError('Subject does not have the verified704 native lash topology')
    with np.load(original['path'], allow_pickle=False) as model:
        expected, corners = corner_identity_operator(model, faces, lash, 14164)
    evidence = read(evidence_path)
    verify(evidence['operator'], 'Measured corner operator')
    verify(evidence['prior_state'], 'Measured operator trial')
    for record in evidence['inputs']:
        verify(record, 'Measured operator evidence')
    if Path(evidence['operator']['path']).resolve() != Path(operator_path).resolve():
        raise ControllerError('Explicit operator differs from evidence')
    with np.load(operator_path, allow_pickle=False) as operator:
        if set(operator.files) != set(expected) or any(not np.array_equal(operator[k], expected[k]) for k in expected):
            raise ControllerError('Operator modifies more than current subject16 native corner rows')
    if len(corners) != 16 or evidence['changed_row_indices'] != corners.tolist():
        raise ControllerError('Subject-derived corners differ from evidence')
    return original, corners


def prepare(candidate_id, sex, source_project, candidate_report, operator, operator_evidence):
    # Validate before creating the new candidate so rejected model inputs leave
    # no partially prepared subject directory.
    original_operator, corners = validate_operator(candidate_report, operator, operator_evidence)
    state = fresh.prepare(candidate_id, sex, source_project, candidate_report)
    state['inputs'].update(original_subdivision_operator=original_operator,
        subdivision_operator=bind(operator), corner_operator_evidence=bind(operator_evidence),
        implementation_explicit_operator_controller=bind(__file__),
        implementation_corner_rule=bind(Path(__file__).with_name('cc_lash_corner_operator_v2.py')),
        implementation_explicit_pixel_review=bind(Path(__file__).with_name('run_cc_fresh_final_corner_repair_v2.py')))
    state['request'].update(purpose='fresh_subject_calibration_explicit16corner_operator_no_prepare_no_bake',
        operator=str(Path(operator).resolve()), operator_evidence=str(Path(operator_evidence).resolve()))
    state['request_fingerprint'] = fingerprint(state['request'])
    state['baseline_capture_dir'] = str(Path(state['attempt_dir']) / '01_capture')
    state['operator_corner_indices'] = corners.tolist()
    state['operator_acceptance'] = 'Measured female trial rule; current subject topology verified; current subject actual CC gate pending'
    write(Path(state['attempt_dir']) / 'request.json', state['request'])
    write(state['state_path'], state)
    return state


def next_step(state):
    if state['status'] == 'completed':
        return None
    for name, operation in fresh.STEP_PLAN:
        if operation == 'offline':
            if name not in state['completed_offline_steps']:
                return name
        elif state['steps'].get(name, {}).get('status') != 'completed':
            return name
    return None


def advance(state, driver, max_steps=1, wait_seconds=0):
    if type(max_steps) is not int or max_steps < 1:
        raise ControllerError('max_steps must be positive')
    driver.verify_state_inputs(state)
    if state['status'] == 'failed':
        raise ControllerError('Failed subject requires new ID')
    for _ in range(max_steps):
        name = next_step(state)
        if name is None:
            return state
        if name == '10_review':
            # Reuse the v2 review that explicitly disclaims unavailable texture
            # pixels. No mutation/monkeypatch of the frozen v1 module is needed.
            explicit_pixel_review(state, driver)
            state['completed_offline_steps'].append(name)
            driver.persist(state)
        else:
            fresh.advance(state, driver, wait_seconds=wait_seconds, max_steps=1)
            if next_step(state) == name:
                return state  # same pending job; caller queries it again
    return state


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state')
    p.add_argument('--candidate-id')
    p.add_argument('--sex', choices=('male', 'female'))
    p.add_argument('--source-project')
    p.add_argument('--candidate-report')
    p.add_argument('--operator')
    p.add_argument('--operator-evidence')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--max-steps', type=int, default=1)
    p.add_argument('--wait-seconds', type=float, default=0)
    a = p.parse_args(argv)
    arguments = (a.candidate_id, a.sex, a.source_project, a.candidate_report, a.operator, a.operator_evidence)
    if not np.isfinite(a.wait_seconds) or a.wait_seconds < 0:
        p.error('wait-seconds must be finite/nonnegative')
    if a.state and any(arguments):
        p.error('--state is exclusive with preparation arguments')
    if not a.state and not all(arguments):
        p.error('New subject requires candidate-id/sex/source-project/candidate-report/operator/operator-evidence')
    with controller_lock():
        state = read(a.state) if a.state else prepare(*arguments)
        driver = BridgeStepDriver()
        driver.verify_state_inputs(state)
        if a.execute:
            state = advance(state, driver, a.max_steps, a.wait_seconds)
        print(json.dumps({k: state.get(k) for k in ('character_id', 'status', 'state_path', 'result_project')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
