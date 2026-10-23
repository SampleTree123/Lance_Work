"""Corner correction must be topology-limited and preserve the original model."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cc_lash_corner_operator_v2 import apply_operator, corner_identity_operator
from run_cc_fresh_final_corner_repair_v2 import TAIL, solve_corrected_submission
from cc_headshot_geometry_solver_v1 import inverse_sparse


def model_fixture():
    faces = [[(v, 0) for v in range(4)], [(v, 0) for v in range(4, 8)]]
    rows, cols, values = [], [], []
    for base in (0, 4):
        for j in range(4):
            i = base + j
            for k, value in ((i, .75), (base + (j - 1) % 4, .125), (base + (j + 1) % 4, .125)):
                rows.append(i); cols.append(k); values.append(value)
    return {'rows': np.asarray(rows), 'cols': np.asarray(cols), 'values': np.asarray(values),
            'offset': np.ones((8, 3)) * .03}, faces


def test_only_single_face_lash_corners_change_and_input_stays_immutable():
    model, faces = model_fixture()
    backup = {k: v.copy() for k, v in model.items()}
    fixed, corners = corner_identity_operator(model, faces, np.arange(4), 8)
    np.testing.assert_array_equal(corners, np.arange(4))
    delta = np.arange(24).reshape(8, 3).astype(float)
    np.testing.assert_array_equal(apply_operator(fixed, delta)[:4], delta[:4])
    np.testing.assert_array_equal(apply_operator(fixed, delta)[4:], apply_operator(model, delta)[4:])
    for key in model:
        np.testing.assert_array_equal(model[key], backup[key])
    np.testing.assert_array_equal(fixed['offset'], model['offset'])


def test_unrecognized_corner_rule_is_rejected_instead_of_silently_overridden():
    model, faces = model_fixture()
    model['values'][0] = .7
    with pytest.raises(ValueError, match='diagnosed'):
        corner_identity_operator(model, faces, np.arange(4), 8)


def test_new_submission_reaches_same_target_without_new_affine_or_nonlash_model_change():
    model, faces = model_fixture()
    fixed, _ = corner_identity_operator(model, faces, np.arange(4), 8)
    target = np.arange(24).reshape(8, 3).astype(float) * .01
    old_correction, _ = inverse_sparse(target, model)
    fresh = {'desired_local': target, 'desired_world': target, 'current_world': np.zeros((8, 3)),
             'current_local': np.zeros((8, 3)), 'skin_affine': np.repeat(np.eye(3)[None], 8, axis=0)}
    corrected, stats = solve_corrected_submission(fresh, np.zeros((8, 3)), np.zeros((8, 3)), fixed)
    np.testing.assert_allclose(apply_operator(fixed, corrected['precomp']), target, atol=1e-7)
    np.testing.assert_allclose(corrected['precomp'][4:], old_correction[4:], atol=1e-7)
    assert np.linalg.norm(corrected['precomp'][:4] - old_correction[:4]) > 0
    assert stats['residual_mm'] < 1e-6


def test_incremental_tail_excludes_calibration_preparation_bake_and_appearance():
    assert [name for name, op in TAIL] == ['05_apply_target', '06_normalize', '07_normalized_capture',
                                           '08_saved_roundtrip', '09_final_reload_capture', '10_review']
    assert all(op in ('replace', 'roundtrip', 'capture', 'offline') for _, op in TAIL)
