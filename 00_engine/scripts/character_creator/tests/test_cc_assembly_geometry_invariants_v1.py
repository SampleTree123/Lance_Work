"""Acceptance cases for the assembly geometry invariant (R06).

These run entirely offline: no RLPy, no Character Creator instance. The point of
splitting the pure comparison out of the capture layer is that every threshold
decision can be exercised here with synthetic arrays.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    'cc_assembly_geometry_invariants',
    Path(__file__).parents[1] / 'cc_assembly_geometry_invariants_v1.py',
)
invariants = importlib.util.module_from_spec(spec)
spec.loader.exec_module(invariants)

# 20-vertex stand-in for CC_Base_Body. Real indices are interleaved rather than
# contiguous blocks; the comparison never relies on ordering, so contiguous
# ranges are fine here.
REGIONS = {
    'body_outside_head': list(range(0, 11)),
    'scalp_mask_zero': [11, 12, 13, 14],
    'face_mask_full': [15, 16, 17],
    'transition': [18, 19],
    'head': list(range(11, 20)),
}
VERTEX_TOTAL = 20


def regions(overrides=None):
    source = dict(REGIONS)
    source.update(overrides or {})
    return {
        name: np.asarray(values, dtype=np.int64)
        for name, values in source.items()
    }


def snapshot(vertices, level=0, world_eligible=True, vertex_count=VERTEX_TOTAL, space='local'):
    return {
        'mesh': 'CC_Base_Body',
        'vertex_count': vertex_count,
        'working_subdivision_level': level,
        'world_eligible': world_eligible,
        space: np.asarray(vertices, dtype=np.float64).tolist(),
    }


def base_vertices():
    # Spread over a ~150 cm range so the float magnitudes resemble a real body.
    return np.linspace(0.0, 150.0, VERTEX_TOTAL * 3).reshape(VERTEX_TOTAL, 3)


def compare(before, after, **kwargs):
    result = invariants.compare_assembly_snapshots(before, after, regions(), **kwargs)
    json.dumps(result, allow_nan=False)
    return result


def test_identical_snapshots_pass():
    vertices = base_vertices()
    result = compare(snapshot(vertices), snapshot(vertices.copy()))
    assert result['passed']
    assert result['failed_regions'] == []
    for name in invariants.GATED_REGIONS:
        assert result['regions'][name]['max_displacement_mm'] == 0.0
        assert result['regions'][name]['exceeding_vertex_count'] == 0


def test_displacement_under_tolerance_passes():
    vertices = base_vertices()
    moved = vertices.copy()
    moved[3, 0] += 0.00001  # 0.0001 mm, well under the 0.002 mm tolerance
    result = compare(snapshot(vertices), snapshot(moved))
    assert result['passed']
    assert result['regions']['body_outside_head']['max_displacement_mm'] < 0.002


def test_body_region_displacement_fails_and_names_offenders():
    vertices = base_vertices()
    moved = vertices.copy()
    moved[3, 0] += 0.001  # 0.01 mm
    result = compare(snapshot(vertices), snapshot(moved))
    assert not result['passed']
    assert result['failed_regions'] == ['body_outside_head']
    region = result['regions']['body_outside_head']
    assert region['exceeding_vertex_count'] == 1
    assert region['worst_offenders'][0]['vertex_index'] == 3
    assert region['worst_offenders'][0]['displacement_mm'] == pytest.approx(0.01)
    assert region['worst_offenders'][0]['allowance'] is None


def test_preserved_face_displacement_fails():
    """The photo facial identity is the expensive input; it must not drift."""
    vertices = base_vertices()
    moved = vertices.copy()
    moved[16, 1] += 0.01  # 0.1 mm inside face_mask_full
    result = compare(snapshot(vertices), snapshot(moved))
    assert not result['passed']
    assert result['failed_regions'] == ['face_mask_full']


def test_fixed_scalp_displacement_fails():
    vertices = base_vertices()
    moved = vertices.copy()
    moved[12, 2] += 0.01
    result = compare(snapshot(vertices), snapshot(moved))
    assert not result['passed']
    assert result['failed_regions'] == ['scalp_mask_zero']


def test_nan_region_cannot_pass_as_unchanged():
    """Two NaN values must never compare as equal, and must not report 0.0."""
    vertices = base_vertices()
    moved = vertices.copy()
    vertices[16, 0] = float('nan')
    moved[16, 0] = float('nan')
    result = compare(snapshot(vertices), snapshot(moved))
    assert not result['passed']
    assert 'face_mask_full' in result['uncomparable_regions']
    region = result['regions']['face_mask_full']
    assert region['max_displacement_mm'] is None
    assert region['reason'] == 'non_finite_inputs'
    assert region['finite_audit']['before_nonfinite_components'] == 1


def test_finite_subtraction_overflow_is_explicit():
    vertices = base_vertices()
    moved = vertices.copy()
    vertices[18, 0] = 1.7e308
    moved[18, 0] = -1.7e308
    result = compare(snapshot(vertices), snapshot(moved))
    assert not result['passed']
    assert 'transition' in result['uncomparable_regions']
    region = result['regions']['transition']
    assert region['max_displacement_mm'] is None
    assert region['finite_audit']['subtraction_overflow']


def test_shape_mismatch_is_refused():
    """Different subdivision topologies are never subtracted point by point."""
    vertices = base_vertices()
    with pytest.raises(invariants.InvariantError, match='shape'):
        compare(snapshot(vertices), snapshot(vertices[:-1]))


def test_vertex_count_disagreement_is_refused():
    vertices = base_vertices()
    with pytest.raises(invariants.InvariantError, match='vertex counts'):
        compare(snapshot(vertices), snapshot(vertices.copy(), vertex_count=56412))


def test_foreign_mesh_is_refused():
    vertices = base_vertices()
    other = snapshot(vertices.copy())
    other['mesh'] = 'CC_Base_Tongue'
    with pytest.raises(invariants.InvariantError, match='CC_Base_Body'):
        compare(snapshot(vertices), other)


def test_world_space_requires_verified_subd0():
    """Measured CC5 behaviour: an inactive low cage reports meaningless world
    coordinates while the avatar displays level 1 (805 mm apart with an
    identical root transform), so world comparison needs the marker."""
    vertices = base_vertices()
    before = snapshot(vertices, level=1, world_eligible=False, space='world')
    after = snapshot(vertices.copy(), level=1, world_eligible=False, space='world')
    with pytest.raises(invariants.InvariantError, match='SubD 0'):
        compare(before, after, space='world')


def test_world_space_passes_with_verified_subd0():
    vertices = base_vertices()
    result = compare(
        snapshot(vertices, space='world'),
        snapshot(vertices.copy(), space='world'),
        space='world',
    )
    assert result['passed']
    assert result['space'] == 'world'


def test_local_space_is_valid_at_any_working_level():
    """Local coordinates stay correct off level 0, so they are the primary
    criterion and must not inherit the world-space restriction."""
    vertices = base_vertices()
    result = compare(
        snapshot(vertices, level=1, world_eligible=False),
        snapshot(vertices.copy(), level=1, world_eligible=False),
    )
    assert result['passed']


def test_tolerance_below_noise_floor_is_refused():
    vertices = base_vertices()
    with pytest.raises(invariants.InvariantError, match='noise floor'):
        compare(
            snapshot(vertices),
            snapshot(vertices.copy()),
            tolerance_mm={'face_mask_full': 0.0001},
        )


def test_allowance_permits_a_bounded_change():
    """An eyelash Apply Morph may legitimately move an eyelid band. Such an
    allowance must be explicit, bounded and evidenced -- never a global loosening."""
    vertices = base_vertices()
    moved = vertices.copy()
    moved[16, 1] += 0.02  # 0.2 mm
    allowances = {
        'eyelid_band': {
            'indices': [16],
            'tolerance_mm': 0.35,
            'reason': 'eyelash Apply Morph',
            'evidence': 'measured on the representative character',
        }
    }
    result = compare(snapshot(vertices), snapshot(moved), allowances=allowances)
    assert result['passed']
    region = result['regions']['face_mask_full']
    assert region['allowance_covered_vertices'] == 1
    assert region['max_displacement_mm'] == pytest.approx(0.2)
    assert result['allowances']['eyelid_band']['tolerance_mm'] == 0.35


def test_allowance_does_not_cover_neighbouring_vertices():
    vertices = base_vertices()
    moved = vertices.copy()
    moved[17, 1] += 0.02
    allowances = {
        'eyelid_band': {'indices': [16], 'tolerance_mm': 0.35},
    }
    result = compare(snapshot(vertices), snapshot(moved), allowances=allowances)
    assert not result['passed']
    assert result['regions']['face_mask_full']['worst_offenders'][0]['vertex_index'] == 17


def test_allowance_beyond_its_own_bound_still_fails():
    vertices = base_vertices()
    moved = vertices.copy()
    moved[16, 1] += 0.1  # 1.0 mm against a 0.35 mm allowance
    allowances = {'eyelid_band': {'indices': [16], 'tolerance_mm': 0.35}}
    result = compare(snapshot(vertices), snapshot(moved), allowances=allowances)
    assert not result['passed']
    offender = result['regions']['face_mask_full']['worst_offenders'][0]
    assert offender['allowance'] == 'eyelid_band'
    assert offender['applied_tolerance_mm'] == 0.35


def test_conflicting_allowances_are_refused():
    vertices = base_vertices()
    allowances = {
        'a': {'indices': [16], 'tolerance_mm': 0.3},
        'b': {'indices': [16], 'tolerance_mm': 0.5},
    }
    with pytest.raises(invariants.InvariantError, match='conflicting'):
        compare(snapshot(vertices), snapshot(vertices.copy()), allowances=allowances)


def test_region_index_beyond_mesh_is_refused():
    vertices = base_vertices()
    bad = regions({'transition': [18, 999]})
    with pytest.raises(invariants.InvariantError, match='indexes vertex'):
        invariants.compare_assembly_snapshots(
            snapshot(vertices), snapshot(vertices.copy()), bad
        )


def test_missing_gated_region_is_refused():
    vertices = base_vertices()
    partial = regions()
    del partial['transition']
    with pytest.raises(invariants.InvariantError, match='transition'):
        invariants.compare_assembly_snapshots(
            snapshot(vertices), snapshot(vertices.copy()), partial
        )


def test_parse_regions_round_trip():
    loaded = invariants.parse_regions(REGIONS, expect_sizes=False)
    assert sorted(loaded) == sorted(REGIONS)
    assert loaded['face_mask_full'].tolist() == [15, 16, 17]


def test_parse_regions_rejects_duplicate_indices():
    broken = dict(REGIONS, transition=[18, 18])
    with pytest.raises(invariants.InvariantError, match='duplicate'):
        invariants.parse_regions(broken, expect_sizes=False)


def test_parse_regions_rejects_missing_region():
    broken = {name: values for name, values in REGIONS.items() if name != 'head'}
    with pytest.raises(invariants.InvariantError, match='lacks regions'):
        invariants.parse_regions(broken, expect_sizes=False)


def test_parse_regions_rejects_negative_index():
    broken = dict(REGIONS, transition=[18, -1])
    with pytest.raises(invariants.InvariantError, match='negative'):
        invariants.parse_regions(broken, expect_sizes=False)


def test_parse_regions_rejects_empty_region():
    broken = dict(REGIONS, transition=[])
    with pytest.raises(invariants.InvariantError, match='non-empty'):
        invariants.parse_regions(broken, expect_sizes=False)


def test_parse_regions_enforces_cc3plus_sizes_by_default():
    with pytest.raises(invariants.InvariantError, match=r'CC3\+ body topology'):
        invariants.parse_regions(REGIONS)


def test_real_region_artifact_matches_expected_topology():
    """The shipped partition must still match the sizes this module gates on."""
    path = (
        Path('D:/UE/Lance_Work/00_engine/outputs/character_creator_bridge/artifacts')
        / 'headshot_fixed_scalp_20261002_v1'
        / 'female_clean_soft_comparison'
        / 'regions.json'
    )
    if not path.exists():
        pytest.skip('region artifact not present on this machine')
    loaded = invariants.load_regions(path)
    assert loaded['scalp_mask_zero'].size == 2741
    assert loaded['face_mask_full'].size == 1343
    union = np.concatenate(
        [loaded[name] for name in invariants.GATED_REGIONS]
    )
    assert np.unique(union).size == invariants.CC_BASE_BODY_SUBD0_VERTEX_COUNT


def test_acceptance_text_does_not_claim_visual_approval():
    vertices = base_vertices()
    result = compare(snapshot(vertices), snapshot(vertices.copy()))
    assert 'human visual acceptance' in result['acceptance']
    assert invariants.REGION_SCOPE in result['region_scope']
