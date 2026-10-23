"""Repair integration invariants without CC or Bridge submission."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_cc_fresh_final_geometry_repair_v1 as repair


def world_record(vertices):
    return {'vertices': np.asarray(vertices).tolist(), 'working_subdivision_level': 0,
            'world_target_eligible': True, 'avatar_transform': {
                'rotation': dict(x=0, y=0, z=0, w=1), 's': dict(x=1, y=1, z=1),
                'translation': dict(x=0, y=0, z=0)}}


def test_external_target_compensates_fresh_affine_and_coupled_subdivision():
    world = np.array([[1., 2, 3], [4., 5, 6]])
    matrix = np.diag([2., 3., 4.])
    local = world @ matrix.T
    desired = world + np.array([[.2, -.1, .3], [-.1, .4, -.2]])
    calibration = {'zero': local.copy()}
    for j, axis in enumerate('xyz'):
        calibration[axis] = local + .1 * matrix[:, j]
    observed = local + .05
    model = {'rows': np.array([0, 0, 1, 1]), 'cols': np.array([0, 1, 0, 1]),
             'values': np.array([.8, .2, .2, .8])}
    arrays, stats = repair.compensate_external(world_record(world), local, desired,
        calibration, local, observed, model)
    correction = arrays['precomp'] - calibration['zero']
    expected = local + (desired - world) @ matrix.T
    np.testing.assert_allclose(observed + np.array([[.8, .2], [.2, .8]]) @ correction, expected, atol=1e-7)
    np.testing.assert_allclose((arrays['submitted_world'] - world) @ matrix.T, correction)
    assert stats['identity_origin']['passed']
    assert stats['solver']['residual_mm'] < 1e-6


def test_external_target_refuses_identity_from_other_source():
    zero = np.zeros((2, 3))
    cal = {'zero': zero}
    for j, axis in enumerate('xyz'):
        cal[axis] = zero + np.eye(3)[j] * .1
    model = {'rows': np.arange(2), 'cols': np.arange(2), 'values': np.ones(2)}
    with pytest.raises(ValueError, match='current zero calibration'):
        repair.compensate_external(world_record(zero), zero, zero, cal,
            zero + .01, zero, model)


@pytest.mark.parametrize('operation', ['prepare', 'late_bake', 'assemble', 'photo', 'repair_support'])
def test_final_repair_forbids_appearance_and_double_preparation(operation):
    state = {'sex': 'female', 'working_project': {'path': 'input.ccProject', 'sha256': 'x'}}
    with pytest.raises(repair.ControllerError, match='Only capture'):
        repair.make_library(state, operation, state['working_project'])


def test_native_replacement_library_has_no_proportion_or_support_operations():
    source = {'path': 'copy.ccProject', 'sha256': 's'}
    target = {'path': 'target.obj', 'sha256': 't'}
    state = {'sex': 'female', 'working_project': source}
    library = repair.make_library(state, 'replace', source, target)
    assert library['character_creation'] == {'operation': 'replace', 'source_project': source,
                                              'appearance_mode': 'headshot_native'}
    assert library['headshot_mesh_replace']['replacement_obj'] == target
    assert library['headshot_mesh_replace']['refinement_iterations'] == 0
    assert all(op not in ('prepare', 'late_bake') for _, op in repair.STEP_PLAN)


def test_pending_stops_before_calibration_and_never_consumes_missing_outputs(tmp_path):
    class Driver:
        def __init__(self):
            self.calls = []
        def verify_state_inputs(self, state):
            pass
        def submit_step(self, state, step_id, library, output):
            self.calls.append(step_id)
        def wait_step(self, state, step_id, seconds):
            return {'status': 'pending'}
    source = {'path': 'copy.ccProject', 'sha256': 's'}
    state = {'sex': 'female', 'working_project': source, 'attempt_dir': str(tmp_path),
             'steps': {}, 'status': 'prepared', 'offline_outputs': {}, 'completed_offline_steps': []}
    driver = Driver()
    assert repair.advance(state, driver, max_steps=50) is state
    assert driver.calls == ['01_capture']
    assert not list(tmp_path.iterdir())


def test_one_step_bound_cannot_run_remaining_steps(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(repair, 'run_step', lambda *args: calls.append(args[2]) or True)
    class Driver:
        def verify_state_inputs(self, state):
            pass
    state = {'working_project': {}, 'attempt_dir': str(tmp_path), 'steps': {},
             'status': 'prepared', 'offline_outputs': {}, 'completed_offline_steps': []}
    repair.advance(state, Driver(), max_steps=1)
    assert calls == ['01_capture']
