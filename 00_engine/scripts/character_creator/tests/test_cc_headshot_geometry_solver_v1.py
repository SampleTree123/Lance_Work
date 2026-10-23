"""Geometric failure modes, coordinate calibration, and solver behavior."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_headshot_geometry_solver_v1 as g


def record(vertices, shift=(0, 0, 0)):
    return dict(vertices=np.asarray(vertices).tolist(), working_subdivision_level=0,
                world_target_eligible=True, avatar_transform=dict(rotation=dict(x=0, y=0, z=0, w=1),
                s=dict(x=1, y=1, z=1), translation=dict(zip('xyz', shift))))


def test_translation_alignment_without_skull_registration():
    source = np.zeros((3, 3))
    aligned = g.align_reference(record(source, (0, 0, 0)), record(source, (1, 2, 3)), 3)
    np.testing.assert_array_equal(aligned, [[1, 2, 3]] * 3)


@pytest.mark.parametrize('key,value', [('world_target_eligible', False), ('working_subdivision_level', 1)])
def test_world_guard(key, value):
    r = record(np.zeros((3, 3)))
    r[key] = value
    with pytest.raises(ValueError, match='SubD0'):
        g.verified_world(r, 3)


@pytest.mark.parametrize('key', ['s', 'rotation'])
def test_root_change_refused(key):
    a = record(np.zeros((3, 3)))
    b = record(np.zeros((3, 3)))
    b['avatar_transform'][key]['x'] = 2
    with pytest.raises(ValueError, match='rotation/scale'):
        g.align_reference(a, b, 3)


def test_current_character_affine_maps_world_shift_and_not_global_reused_matrix():
    base = np.arange(12).reshape(4, 3).astype(float)
    matrices = np.repeat(np.diag([2, 3, 4])[None], 4, axis=0)
    probes = {'zero': base}
    for j, axis in enumerate('xyz'):
        probes[axis] = base + .1 * matrices[:, :, j]
    actual_base, actual, summary = g.skin_affine(probes, 4)
    np.testing.assert_allclose(actual, matrices)
    np.testing.assert_array_equal(actual_base, base)
    assert summary['condition_max'] == pytest.approx(2)
    assert summary['determinant_min_abs'] == pytest.approx(24)


@pytest.mark.parametrize('diag', [[1, 0, 1], [1, 101, 1]])
def test_singular_or_ill_conditioned_affine_refused(diag):
    probes = {'zero': np.zeros((2, 3))}
    for j, axis in enumerate('xyz'):
        probes[axis] = np.repeat((.1 * np.diag(diag)[:, j])[None], 2, axis=0)
    with pytest.raises(ValueError, match='ill-conditioned'):
        g.skin_affine(probes, 2)


def test_inverse_handles_off_diagonal_skinning_subdivision():
    model = dict(rows=np.array([0, 0, 1, 1]), cols=np.array([0, 1, 0, 1]),
                 values=np.array([.8, .2, .2, .8]))
    rhs = np.array([[1, 3, 2], [3, 1, -1]], dtype=float)
    solved, stats = g.inverse_sparse(rhs, model)
    np.testing.assert_allclose(np.array([[.8, .2], [.2, .8]]) @ solved, rhs, atol=1e-7)
    assert stats['iterations'] > 0
    assert stats['residual_mm'] < 1e-6


@pytest.mark.parametrize('model', [dict(rows=[0], cols=[1], values=[1]),
                                   dict(rows=[0.5], cols=[0], values=[1]),
                                   dict(rows=[0], cols=[4], values=[1]),
                                   dict(rows=[0], cols=[0], values=[float('nan')])])
def test_invalid_or_zero_diagonal_operators_rejected(model):
    with pytest.raises(ValueError):
        g.inverse_sparse(np.zeros((2, 3)), model)


def test_nonconvergent_operator_stops():
    model = dict(rows=np.array([0, 1]), cols=np.array([0, 1]), values=np.ones(2))
    with pytest.raises(ValueError, match='did not converge'):
        g.inverse_sparse(np.ones((2, 3)), model, max_iterations=1)


def topology():
    # Long strip: outside vertex0, head1..7, photo face vertex7.
    return [[(i, 0), (i + 1, 0), (i + 2, 0)] for i in range(6)]


def test_average_outside_and_scalp_last_face_identity_exact():
    source = np.ones((8, 3))
    average = np.ones((8, 3)) * 10
    scalp = np.ones((8, 3)) * 20
    head = np.arange(1, 8)
    weights = np.zeros(8)
    weights[7] = 1
    desired, blend, effective = g.build_desired_world(source, average, scalp, head, weights, topology(), rings=1)
    np.testing.assert_array_equal(desired[0], average[0])
    np.testing.assert_array_equal(desired[1:7], scalp[1:7])
    np.testing.assert_array_equal(desired[7], source[7])
    assert blend[7] == 0


def test_neck_taper_cannot_change_full_face():
    weights = np.zeros(8)
    weights[1] = 1
    with pytest.raises(ValueError, match='photo-face'):
        g.restore_blend(8, topology(), np.arange(1, 8), weights, rings=6)


def test_end_to_end_coupled_coordinate_solution():
    source = np.ones((8, 3))
    average = np.ones((8, 3)) * 10
    scalp = np.ones((8, 3)) * 20
    weights = np.zeros(8)
    weights[7] = 1
    baseline = source * 2
    cal = {'zero': baseline}
    for j, axis in enumerate('xyz'):
        cal[axis] = baseline + np.eye(3)[j] * .2
    op = dict(rows=np.arange(8), cols=np.arange(8), values=np.ones(8))
    arrays, stats = g.solve_geometry(record(source), baseline, record(average), record(scalp),
        topology(), np.arange(1, 8), weights, cal, baseline, op, rings=1)
    np.testing.assert_allclose(arrays['submitted_world'], arrays['desired_world'], atol=1e-7)
    np.testing.assert_allclose(arrays['desired'], arrays['desired_world'] * 2)
    assert stats['solver']['residual_mm'] < 1e-6


def test_reference_hash_tampering(tmp_path):
    p = tmp_path / 'input.json'
    p.write_text('first')
    r = g.file_record(p)
    p.write_text('second')
    with pytest.raises(ValueError, match='SHA mismatch'):
        g.verify_record(r)


def test_identity_origin_matches_current_zero_capture():
    zero = np.array([[1, 2, 3], [4, 5, 6]])
    assert g.verify_identity_origin(zero.tolist(), zero, 2)['max_displacement_mm'] == 0


def test_another_character_identity_capture_is_refused():
    zero = np.array([[1, 2, 3], [4, 5, 6]], dtype=float)
    wrong = zero.copy()
    wrong[0, 0] += 1e-4
    with pytest.raises(ValueError, match='current zero calibration'):
        g.verify_identity_origin(wrong, zero, 2)


def test_identity_origin_shape_invalid():
    with pytest.raises(ValueError, match='finite'):
        g.verify_identity_origin([[1, 2]], np.zeros((2, 3)), 2)


def test_identity_origin_allows_measured_serialization_noise():
    zero = np.zeros((2, 3))
    initial = zero.copy()
    initial[0, 0] = .0001528856233776226 / 10
    report = g.verify_identity_origin(initial, zero, 2)
    assert report['passed']
    assert report['max_displacement_mm'] == pytest.approx(.0001528856233776226)


def test_identity_origin_exceeding_fixed_noise_bound_rejected():
    with pytest.raises(ValueError, match='current zero calibration'):
        g.verify_identity_origin([[.0002001 / 10, 0, 0]], [[0, 0, 0]], 1)
