"""Focused numerical and reproducibility checks; no photographs or apps needed."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze_cfd_face_diversity_v1 as diversity


def measurements():
    return {'EyeHeightAvg': 4., 'EyeWidthAvg': 10., 'FaceWidthCheeks': 100.,
            'NoseWidth': 20., 'NoseLength': 30., 'LipThickness': 5.,
            'PupilLipAvg': 40., 'BottomLipChin': 20., 'FaceWidthMouth': 80.,
            'CheeksAvg': 90.}


def test_nine_ratios_and_region_weights_do_not_count_regions_twice():
    assert len(diversity.FEATURES) == 9
    np.testing.assert_allclose(diversity.ratios(measurements()),
                               [.4, .1, .2, .3, .05, .4, .2, .8, .9])
    np.testing.assert_allclose(diversity.WEIGHTS,
                               [.125, .125, .125, .125, .20, .15, .05, .05, .05])
    assert diversity.WEIGHTS.sum() == pytest.approx(1.)
    forbidden = {'FaceLength', 'Forehead', 'EyeDistance', 'FaceColorRed', 'Prototypic'}
    assert not forbidden.intersection(diversity.REQUIRED)
    # Every coordinate differing by one has RMS=1, without a second division by nine.
    assert diversity.distance_matrix(np.array([np.zeros(9), np.ones(9)]))[0, 1] == pytest.approx(1.)


@pytest.mark.parametrize('name', ['FaceWidthCheeks', 'EyeWidthAvg'])
@pytest.mark.parametrize('value', [0., -1., float('nan'), float('inf')])
def test_invalid_denominators_are_rejected(name, value):
    data = measurements()
    data[name] = value
    with pytest.raises(ValueError, match='Non-positive/non-finite'):
        diversity.ratios(data)


@pytest.mark.parametrize('value', [float('nan'), float('inf')])
def test_nonfinite_numerator_is_rejected(value):
    data = measurements()
    data['NoseLength'] = value
    with pytest.raises(ValueError, match='Non-positive/non-finite'):
        diversity.ratios(data)


def test_zero_mad_uses_std_for_minority_variation_and_zeroes_only_constant_columns():
    x = np.array([[0., 7., 1.], [0., 7., 2.], [0., 7., 3.],
                  [0., 7., 4.], [10., 7., 100.]])
    z, meta = diversity.robust_standardize(x)
    np.testing.assert_allclose(meta['center'], [0., 7., 3.])
    np.testing.assert_allclose(meta['scale'], [4., 1., 1.4826])
    assert meta['std_fallback'] == [True, True, False]
    assert meta['constant'] == [False, True, False]
    assert z[-1, 0] == pytest.approx(2.5)  # Minority difference must survive zero MAD.
    np.testing.assert_array_equal(z[:, 1], np.zeros(5))
    assert z[-1, 2] == 3.
    assert meta['clipped_cells_per_row'] == [0, 0, 0, 0, 1]
    assert np.isfinite(z).all() and np.abs(z).max() <= 3.


@pytest.mark.parametrize('x', [np.ones((1, 9)), np.ones(9),
                             np.full((2, 9), np.nan)])
def test_standardization_rejects_nonfinite_or_insufficient_matrix(x):
    with pytest.raises(ValueError, match='finite matrix'):
        diversity.robust_standardize(x)


def test_distances_are_symmetric_zero_diagonal_and_have_expected_weight_and_clip_bound():
    x = np.zeros((4, 9))
    x[1, 0] = 2.
    x[2] = -3.
    x[3] = 3.
    d = diversity.distance_matrix(x)
    np.testing.assert_allclose(d, d.T)
    np.testing.assert_array_equal(np.diag(d), np.zeros(4))
    assert np.isfinite(d).all() and (d >= 0).all()
    assert d[0, 1] == pytest.approx(np.sqrt(.125 * 4.))
    assert d[2, 3] == pytest.approx(6.) and d.max() <= 6.


@pytest.mark.parametrize('x', [np.zeros((3, 8)), np.zeros(9),
                             np.full((2, 9), np.inf)])
def test_distance_rejects_wrong_dimensions_or_nonfinite_values(x):
    with pytest.raises(ValueError, match='nine-column'):
        diversity.distance_matrix(x)


def test_neighbors_exclude_self_keep_other_zero_distances_and_break_ties_by_id():
    ids = ['query', 'B', 'A', 'D', 'C']
    x = np.zeros((5, 9))
    x[1:3] = 1.
    x[3] = 2.
    d = diversity.distance_matrix(x)
    nearest = diversity.neighbors(ids, d, 0)
    farthest = diversity.neighbors(ids, d, 0, farthest=True)
    assert [r['subject_id'] for r in nearest] == ['C', 'A', 'B', 'D']
    assert [r['subject_id'] for r in farthest] == ['D', 'A', 'B', 'C']
    assert nearest[0]['distance'] == 0. and farthest[0]['distance'] == pytest.approx(2.)
    assert all(r['subject_id'] != 'query' for r in nearest + farthest)
    assert len(diversity.neighbors(ids, d, 0, count=2)) == 2


def test_maxmin_is_seeded_permutation_invariant_and_excludes_without_repeats():
    ids = ['Z', 'B', 'D', 'A', 'C', 'E']
    x = np.zeros((6, 9))
    x[:, 0] = [-2., 0., 1., 0., -1., 2.]
    d = diversity.distance_matrix(x)
    excluded = ['B', 'not-in-this-group']
    perm = np.array([4, 1, 5, 0, 3, 2])
    for seed in (0, 7, 20261007):
        selected = diversity.select_diverse(ids, d, 4, seed, excluded)
        assert selected == diversity.select_diverse(ids, d, 4, seed, excluded)
        assert selected == diversity.select_diverse([ids[i] for i in perm],
            d[np.ix_(perm, perm)], 4, seed, excluded)
        assert len(selected) == len(set(selected)) == 4
        assert not set(selected).intersection(excluded)
        # Each later choice maximizes its minimum distance to the chosen set.
        for position in range(1, len(selected)):
            before = [ids.index(v) for v in selected[:position]]
            eligible = [i for i, v in enumerate(ids) if v not in excluded + selected[:position]]
            chosen_min = min(d[ids.index(selected[position]), j] for j in before)
            assert chosen_min == pytest.approx(max(min(d[i, j] for j in before) for i in eligible))
    assert set(diversity.select_diverse(ids, d, 5, 1, excluded)) == set(ids) - {'B'}


def test_maxmin_zero_distance_ties_use_stable_ids_after_seeded_first():
    ids = ['D', 'A', 'C', 'B']
    selected = diversity.select_diverse(ids, np.zeros((4, 4)), 4, 11)
    assert selected[1:] == sorted(set(ids) - {selected[0]})


@pytest.mark.parametrize('k', [-1, 0, 3])
def test_maxmin_rejects_k_outside_eligible_pool(k):
    with pytest.raises(ValueError, match='eligible pool'):
        diversity.select_diverse(['A', 'B', 'C'], np.zeros((3, 3)), k, 1, ['C'])


def test_maxmin_rejects_duplicate_ids_and_empty_eligible_pool():
    with pytest.raises(ValueError, match='Duplicate'):
        diversity.select_diverse(['A', 'A'], np.zeros((2, 2)), 1, 1)
    with pytest.raises(ValueError, match='eligible pool'):
        diversity.select_diverse(['A'], np.zeros((1, 1)), 1, 1, ['A'])


def test_selection_stats_use_unordered_pairs_once_and_singleton_has_no_pair_score():
    ids = ['A', 'B', 'C']
    d = np.array([[0., 1., 4.], [1., 0., 3.], [4., 3., 0.]])
    stats = diversity.selection_stats(ids, d, ['C', 'A', 'B'])
    assert stats['min_pair_distance'] == 1.
    assert stats['mean_pair_distance'] == pytest.approx(8. / 3.)
    assert diversity.selection_stats(ids, d, ['A']) == {
        'min_pair_distance': None, 'mean_pair_distance': None}
