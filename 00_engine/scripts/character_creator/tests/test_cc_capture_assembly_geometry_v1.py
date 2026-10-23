"""Offline cases for the CC-side R06 capture layer.

The capture layer is the only part that needs a live Character Creator, which is
exactly why it is worth faking RLPy here: an idiom error (wrong bool argument,
wrong mesh selection, stale proxy read) should surface in this file rather than
part-way through a real assembly run.

The final case wires capture output into the offline comparator, so the two
layers are proven to fit together before anyone drives CC.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).parents[1]


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The capture module imports RLPy at module scope, so it must exist first.
sys.modules.setdefault("RLPy", types.ModuleType("RLPy"))
capture = _load("cc_capture_assembly_geometry", "cc_capture_assembly_geometry_v1.py")
invariants = _load(
    "cc_assembly_geometry_invariants", "cc_assembly_geometry_invariants_v1.py"
)

VERTEX_COUNT = 24


class FakeVector:
    def __init__(self, row):
        self.x, self.y, self.z = row


class FakeMesh:
    """Duck-typed RIMesh.

    Mirrors the two different meanings of the bool argument in neighbouring SDK
    calls: GetMeshes(bAll) selects child inclusion, GetVertices(bWorld) selects
    the coordinate space. Conflating them is the documented trap.
    """

    def __init__(self, name, local, world=None, scalar_override=None):
        self._name = name
        self._local = [list(row) for row in local]
        self._world = [list(row) for row in (world if world is not None else local)]
        self._scalar_override = scalar_override or {}

    def GetName(self):
        return self._name

    def GetVerticesCount(self):
        return len(self._local)

    def GetVertices(self, bWorld):
        rows = self._world if bWorld else self._local
        return [FakeVector(row) for row in rows]

    def GetVertex(self, index, bWorld):
        if index in self._scalar_override:
            return FakeVector(self._scalar_override[index])
        rows = self._world if bWorld else self._local
        return FakeVector(rows[index])


class FakeAvatar:
    def __init__(self, meshes, level=0, max_level=1):
        self._meshes = meshes
        self._level = level
        self._max_level = max_level

    def GetMeshes(self, bAll):
        return list(self._meshes)

    def GetSubdivMeshLevel(self):
        return self._level

    def GetMaxSubdivMeshLevel(self):
        return self._max_level

    def WorldTransform(self):
        return "transform-token"


class FakeApi:
    """Stand-in for cc_validate_body_reconstruction's helper surface."""

    def __init__(self):
        self.settle_calls = 0

    def force_avatar_scene_evaluation(self, avatar):
        self.settle_calls += 1

    def _transform_data(self, transform):
        return {"token": transform}


def rows(offset=0.0, count=VERTEX_COUNT):
    grid = np.linspace(0.0, 150.0, count * 3).reshape(count, 3) + offset
    return grid.tolist()


def body(local=None, **kwargs):
    return FakeMesh(capture.CC_BASE_BODY, local if local is not None else rows(), **kwargs)


def avatar(meshes=None, level=0):
    return FakeAvatar(meshes if meshes is not None else [body()], level=level)


def snapshot(**kwargs):
    kwargs.setdefault("vertex_count", VERTEX_COUNT)
    result = capture.capture_body_snapshot(**kwargs)
    json.dumps(result, allow_nan=False)
    return result


def test_clean_capture_at_subd0_includes_world():
    api = FakeApi()
    result = snapshot(avatar=avatar(), api=api)
    assert result["mesh"] == capture.CC_BASE_BODY
    assert result["working_subdivision_level"] == 0
    assert result["world_eligible"] is True
    assert "world" in result
    assert len(result["local"]) == VERTEX_COUNT
    assert result["scene_explicitly_settled"] is True
    assert api.settle_calls == 1
    assert result["avatar_transform"] == {"token": "transform-token"}


def test_capture_off_level_zero_keeps_local_and_skips_world():
    """Local stays valid off level 0; world must not be captured there."""
    result = snapshot(avatar=avatar(level=1))
    assert result["working_subdivision_level"] == 1
    assert result["world_eligible"] is False
    assert "world" not in result
    assert "world_skipped_reason" in result
    assert len(result["local"]) == VERTEX_COUNT


def test_capture_without_api_records_unsettled_scene():
    result = snapshot(avatar=avatar())
    assert result["scene_explicitly_settled"] is False
    assert "avatar_transform" not in result


def test_ambiguous_mesh_level_is_refused():
    duplicate = [body(), body()]
    with pytest.raises(capture.CaptureError, match="Ambiguous"):
        snapshot(avatar=avatar(duplicate))


def test_absent_topology_is_refused():
    other = FakeMesh("CC_Base_Tongue", rows(count=9))
    with pytest.raises(capture.CaptureError, match="Expected exactly one"):
        snapshot(avatar=avatar([other]))


def test_other_meshes_do_not_confuse_selection():
    """A tongue at a different count must not be mistaken for the body."""
    scene = [FakeMesh("CC_Base_Tongue", rows(count=9)), body()]
    result = snapshot(avatar=avatar(scene))
    assert len(result["local"]) == VERTEX_COUNT


def test_wrong_requested_level_is_refused():
    with pytest.raises(capture.CaptureError, match="Expected exactly one"):
        capture.capture_body_snapshot(avatar=avatar(), vertex_count=56412)


def test_non_finite_coordinates_are_refused():
    broken = rows()
    broken[5][1] = float("nan")
    with pytest.raises(capture.CaptureError, match="Non-finite"):
        snapshot(avatar=avatar([body(local=broken)]))


def test_scalar_query_disagreement_is_refused():
    """Catches a stale Python proxy read rather than trusting the batch array."""
    mesh = body(scalar_override={0: [99.0, 99.0, 99.0]})
    with pytest.raises(capture.CaptureError, match="scalar vertex queries disagree"):
        snapshot(avatar=avatar([mesh]))


def test_scalar_cross_check_can_be_disabled():
    mesh = body(scalar_override={0: [99.0, 99.0, 99.0]})
    result = snapshot(avatar=avatar([mesh]), verify_scalar_queries=False)
    assert "scalar_vertex_query" not in result


def test_scalar_cross_check_reports_samples():
    result = snapshot(avatar=avatar())
    samples = result["scalar_vertex_query"]
    assert samples
    assert all(sample["delta_mm"] == 0.0 for sample in samples)
    assert len({sample["index"] for sample in samples}) == len(samples)


def test_world_capture_can_be_declined():
    result = snapshot(avatar=avatar(), include_world=False)
    assert "world" not in result
    assert result["world_eligible"] is True


def test_capture_output_feeds_the_offline_comparator():
    """The handoff seam: capture twice, compare, with no CC involved."""
    before_mesh = body()
    subject = avatar([before_mesh])
    before = snapshot(avatar=subject)

    moved = rows()
    moved[20][0] += 0.001  # 0.01 mm, above the 0.002 mm tolerance
    after = snapshot(avatar=avatar([body(local=moved)]))

    regions = invariants.parse_regions(
        {
            "body_outside_head": list(range(0, 12)),
            "scalp_mask_zero": [12, 13, 14, 15],
            "face_mask_full": [16, 17, 18],
            "transition": [19, 20, 21, 22, 23],
            "head": list(range(12, 24)),
        },
        expect_sizes=False,
    )
    report = invariants.compare_assembly_snapshots(before, after, regions)
    json.dumps(report, allow_nan=False)

    assert not report["passed"]
    assert report["failed_regions"] == ["transition"]
    assert report["regions"]["transition"]["worst_offenders"][0]["vertex_index"] == 20
    assert report["working_subdivision_level"] == {"before": 0, "after": 0}


def test_identical_captures_compare_clean():
    subject = avatar()
    before = snapshot(avatar=subject)
    after = snapshot(avatar=subject)
    regions = invariants.parse_regions(
        {
            "body_outside_head": list(range(0, 12)),
            "scalp_mask_zero": [12, 13, 14, 15],
            "face_mask_full": [16, 17, 18],
            "transition": [19, 20, 21, 22, 23],
            "head": list(range(12, 24)),
        },
        expect_sizes=False,
    )
    report = invariants.compare_assembly_snapshots(before, after, regions)
    assert report["passed"]
