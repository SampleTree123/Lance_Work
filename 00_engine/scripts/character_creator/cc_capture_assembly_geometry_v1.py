"""Assembly geometry invariants (R06) -- CC-side capture layer.

This is the only part of the R06 check that needs a live Character Creator
instance, and it is deliberately thin: it reads vertices and records the
metadata contract, and makes no acceptance decision. All thresholds and
pass/fail logic live in ``cc_assembly_geometry_invariants_v1.py``, which carries
no RLPy dependency and is unit-tested offline.

Intended use from the slim base-appearance assembly entry:

    import cc_capture_assembly_geometry_v1 as capture
    import cc_assembly_geometry_invariants_v1 as invariants

    before = capture.capture_body_snapshot(avatar, api=api)
    ...  # apply skin / eyebrows / eyelashes / eye material
    after = capture.capture_body_snapshot(avatar, api=api)
    report = invariants.compare_assembly_snapshots(
        before, after, invariants.load_regions(regions_path)
    )
    if not report["passed"]:
        raise ReconstructionError("Assembly moved protected geometry")

Before wiring it in, run ``self_check(avatar)`` once on a loaded character: it
captures and prints a one-line summary without writing anything, so a bad
capture is caught in seconds rather than mid-assembly.

Units and coordinate space
--------------------------
``GetVertices`` returns centimetres; the offline comparator converts to
millimetres. ``local`` (``GetVertices(False)``) is captured always because it
stays valid at any working subdivision level. ``world`` is captured only when
the avatar is actually at working SubD 0, and the snapshot records
``world_eligible`` so the offline side can refuse an ineligible world
comparison -- an inactive low cage reports meaningless world coordinates while
the avatar displays level 1.
"""

import json
import math
import os

import RLPy

CC_BASE_BODY = "CC_Base_Body"
CC_BASE_BODY_SUBD0_VERTEX_COUNT = 14164
# 128 uniformly spaced scalar re-reads distinguish a reproducible SDK array from
# a stale Python proxy read. Same technique as capture_levels() in
# cc_headshot_route_validation_v1.py.
SCALAR_PROBE_SAMPLES = 128
SCALAR_PROBE_TOLERANCE_MM = 0.001


class CaptureError(Exception):
    """Raised when the live scene cannot yield a trustworthy snapshot."""


def _vertex_rows(mesh, world):
    rows = [
        [float(v.x), float(v.y), float(v.z)]
        for v in mesh.GetVertices(bool(world))
    ]
    if not all(math.isfinite(value) for row in rows for value in row):
        raise CaptureError(
            "Non-finite {} coordinates from {}".format(
                "world" if world else "local", mesh.GetName()
            )
        )
    return rows


def _resolve_body_mesh(avatar, vertex_count):
    """Select the body mesh by (name, vertex_count).

    ``GetMeshes(False)`` controls inclusion of children, NOT subdivision
    selection -- there is no per-level vertex API, so the vertex count is what
    identifies the level. Any ambiguity is refused rather than guessed.
    """
    matches = []
    seen = set()
    for mesh in avatar.GetMeshes(False):
        key = (str(mesh.GetName()), int(mesh.GetVerticesCount()))
        if key in seen:
            raise CaptureError("Ambiguous exposed mesh level: {}".format(key))
        seen.add(key)
        if key[0] == CC_BASE_BODY and key[1] == vertex_count:
            matches.append(mesh)
    if len(matches) != 1:
        raise CaptureError(
            "Expected exactly one {} at {} vertices, found {}".format(
                CC_BASE_BODY, vertex_count, len(matches)
            )
        )
    return matches[0]


def _scalar_cross_check(mesh, rows):
    """Re-read sampled vertices through the scalar API and compare."""
    count = len(rows)
    if count < 2:
        return []
    indices = sorted(
        {
            int(i * (count - 1) / (SCALAR_PROBE_SAMPLES - 1))
            for i in range(SCALAR_PROBE_SAMPLES)
        }
    )
    samples = []
    for index in indices:
        value = mesh.GetVertex(index, False)
        scalar = [float(value.x), float(value.y), float(value.z)]
        if not all(math.isfinite(component) for component in scalar):
            raise CaptureError(
                "Non-finite scalar vertex query at index {}".format(index)
            )
        delta_mm = (
            math.sqrt(
                sum((a - b) ** 2 for a, b in zip(scalar, rows[index]))
            )
            * 10.0
        )
        if delta_mm > SCALAR_PROBE_TOLERANCE_MM:
            raise CaptureError(
                "Batch and scalar vertex queries disagree at index {} by "
                "{} mm; the array read is not trustworthy".format(
                    index, delta_mm
                )
            )
        samples.append({"index": index, "delta_mm": delta_mm})
    return samples


def capture_body_snapshot(
    avatar,
    api=None,
    vertex_count=CC_BASE_BODY_SUBD0_VERTEX_COUNT,
    include_world=True,
    verify_scalar_queries=True,
    output_path=None,
):
    """Capture one comparable snapshot of the base body mesh.

    ``api`` is the ``cc_validate_body_reconstruction`` module when available; it
    supplies ``force_avatar_scene_evaluation`` (settle the scene before reading)
    and ``_transform_data`` (record the root transform). Both are optional --
    without them the snapshot is still valid for local comparison, and records
    that the scene was not explicitly settled.

    This function never switches the subdivision level. It records whatever
    level the avatar is on; switching is a caller decision with its own
    read-back confirmation.
    """
    settled = False
    if api is not None and hasattr(api, "force_avatar_scene_evaluation"):
        api.force_avatar_scene_evaluation(avatar)
        settled = True

    working_level = int(avatar.GetSubdivMeshLevel())
    mesh = _resolve_body_mesh(avatar, vertex_count)

    local_rows = _vertex_rows(mesh, world=False)
    if len(local_rows) != vertex_count:
        raise CaptureError(
            "Vertex count {} disagrees with query length {}".format(
                vertex_count, len(local_rows)
            )
        )

    world_eligible = working_level == 0
    snapshot = {
        "schema_version": 1,
        "mesh": CC_BASE_BODY,
        "vertex_count": vertex_count,
        "working_subdivision_level": working_level,
        "max_subdivision_level": int(avatar.GetMaxSubdivMeshLevel()),
        "world_eligible": world_eligible,
        "scene_explicitly_settled": settled,
        "local": local_rows,
    }

    if include_world:
        if world_eligible:
            snapshot["world"] = _vertex_rows(mesh, world=True)
        else:
            # Capturing it anyway would invite an invalid comparison later.
            snapshot["world_skipped_reason"] = (
                "working subdivision level is {}; an inactive low cage does "
                "not report its posed world geometry".format(working_level)
            )

    if api is not None and hasattr(api, "_transform_data"):
        snapshot["avatar_transform"] = api._transform_data(avatar.WorldTransform())

    if verify_scalar_queries:
        snapshot["scalar_vertex_query"] = _scalar_cross_check(mesh, local_rows)

    if output_path:
        directory = os.path.dirname(output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, allow_nan=False)
        snapshot["output_path"] = output_path

    return snapshot


def self_check(avatar, api=None, vertex_count=CC_BASE_BODY_SUBD0_VERTEX_COUNT):
    """Capture once and print a summary. Writes nothing, changes nothing.

    Run this on a loaded character before wiring the check into the assembly
    entry, so a capture problem surfaces immediately instead of mid-run.
    """
    snapshot = capture_body_snapshot(
        avatar,
        api=api,
        vertex_count=vertex_count,
        output_path=None,
    )
    rows = snapshot["local"]
    axes = list(zip(*rows))
    summary = {
        "mesh": snapshot["mesh"],
        "vertices": len(rows),
        "working_subdivision_level": snapshot["working_subdivision_level"],
        "max_subdivision_level": snapshot["max_subdivision_level"],
        "world_eligible": snapshot["world_eligible"],
        "world_captured": "world" in snapshot,
        "scene_explicitly_settled": snapshot["scene_explicitly_settled"],
        "scalar_cross_checks": len(snapshot.get("scalar_vertex_query") or []),
        "local_bounds_cm": [
            [min(axis) for axis in axes],
            [max(axis) for axis in axes],
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary
