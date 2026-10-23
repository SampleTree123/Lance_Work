"""Independent invariants for archived native-lash and bounded jaw repair."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cc_native_geometry_repair_candidate_v1 import repair_target


def case():
    # Head strip 1..8, photo face 1, protected scalp 8; disconnected lash 9.
    # The BODY vertex0 remains Average. Triangles have no unintended shortcut.
    faces = [[(i, 0), (i + 1, 0), (i + 1, 0)] for i in range(8)]
    source = np.zeros((10, 3))
    old = np.zeros((10, 3))
    old[0] = 20
    old[2:] = 1
    weights = np.zeros(10)
    weights[1] = 1
    return source, old, weights, np.arange(1, 10), faces


def test_source_lash_and_photo_face_preserved_while_body_and_scalp_are_exact():
    source, old, weights, head, faces = case()
    result, band, distance = repair_target(source, old, weights, head, faces, [9], [2], [8], rings=3)
    np.testing.assert_array_equal(result[9], source[9])
    np.testing.assert_array_equal(result[1], old[1])
    np.testing.assert_array_equal(result[[0, 5, 6, 7, 8]], old[[0, 5, 6, 7, 8]])
    np.testing.assert_array_equal(band, [2, 3, 4])
    assert distance[2] == 1 and distance[4] == 3
    assert np.linalg.norm(result[2]) < np.linalg.norm(result[3]) < np.linalg.norm(result[4])
    assert np.linalg.norm(result[2] - result[1]) < np.linalg.norm(old[2] - old[1])


def test_protected_anchor_stops_topological_propagation():
    source, old, weights, head, faces = case()
    result, band, _ = repair_target(source, old, weights, head, faces, [9], [2], [3, 8], rings=6)
    np.testing.assert_array_equal(band, [2])
    np.testing.assert_array_equal(result[3:9], old[3:9])


@pytest.mark.parametrize('seeds,protected', [([1], [8]), ([0], [8]), ([9], [8]), ([4], [8]), ([2], [2, 8])])
def test_invalid_or_unanchored_seed_rejected(seeds, protected):
    source, old, weights, head, faces = case()
    with pytest.raises(ValueError, match='Jaw seed'):
        repair_target(source, old, weights, head, faces, [9], seeds, protected)


@pytest.mark.parametrize('rings', [0, 13, True])
def test_unbounded_repair_rejected(rings):
    source, old, weights, head, faces = case()
    with pytest.raises(ValueError, match='rings'):
        repair_target(source, old, weights, head, faces, [9], [2], [8], rings=rings)
