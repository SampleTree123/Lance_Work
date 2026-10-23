"""Assembly geometry invariants (R06) -- pure offline comparison layer.

Purpose
-------
CC base-appearance assembly (skin / eyebrows / eyelashes / eye material) must not
move the photo facial identity or the fixed-scalp correction. The existing
protection in ``cc_validate_body_reconstruction.apply_facial_assembly`` compares
*Morph slider weights* only (``capture_vectors`` -> ``GetShapingMorphWeight``), so
it is structurally blind to mesh vertex changes. That blindness matters most for
exactly these characters: their shape lives in baked vertices after geometry
correction / Bake Morph Slider, and most sliders read zero, so the weight-based
policy degenerates to near-vacuous.

This module owns the acceptance logic and carries no RLPy dependency, so every
threshold decision is unit-testable without a live Character Creator instance.
The thin RLPy capture side lives in ``cc_capture_assembly_geometry_v1.py``.

Units
-----
CC5 ``GetVertices`` returns centimetres. Every reported displacement here is
millimetres (cm * 10), matching the existing reports in this directory.

Coordinate space
----------------
``local`` (``GetVertices(False)``) is the primary criterion because it stays
valid at any working subdivision level. ``world`` comparison is refused unless
both snapshots are explicitly marked as captured at working SubD 0: measured CC5
behaviour is that an inactive low cage reports meaningless world coordinates
while the avatar displays level 1 (0.0 mm local difference against 805.26 mm
world difference with an identical actor root transform; see
``inactive_world_query_guard_review_20261003_v1.json``).
"""

import json

import numpy as np

CM_TO_MM = 10.0

# float32 at a ~150 cm coordinate magnitude resolves to roughly 3e-4 mm; the
# measured repeat-read noise floor was 0.000305 mm. Thresholds at or below that
# produce guaranteed false positives, so they are rejected outright.
NUMERIC_FLOOR_MM = 0.001

# Default per-region tolerance. 0.002 mm is not a new invention: it is the
# threshold the project already asserts for the same class of operation --
# "skin-only preparation must not change the body" in
# cc_headshot_route_validation_v1.py:949, and the skin scalar adjustment check
# at :1064. Root alignment uses the stricter 0.001 mm at :432.
DEFAULT_TOLERANCE_MM = {
    "body_outside_head": 0.002,
    "scalp_mask_zero": 0.002,
    "face_mask_full": 0.002,
    "transition": 0.002,
}

# Region partition produced by cc_compare_headshot_geometry_v1.compare().
# NOTE ON SCOPE: this is a UV-mask partition, not an anatomical assertion.
# "scalp_mask_zero" covers scalp AND ears AND neck; it is not a scalp-only mask.
# Any report built from it must carry that limitation forward.
REGION_SCOPE = (
    "Clean Soft UV mask partition; scalp_mask_zero includes scalp, ears and "
    "neck and is not a production scalp-only mask"
)
EXPECTED_REGION_SIZES = {
    "head": 4563,
    "scalp_mask_zero": 2741,
    "face_mask_full": 1343,
    "transition": 479,
    "body_outside_head": 9601,
}
# Regions actually gated. "head" is the union of the three head sub-regions and
# would double-count, so it is loaded for reference but never gated directly.
GATED_REGIONS = ("body_outside_head", "scalp_mask_zero", "face_mask_full", "transition")

CC_BASE_BODY_SUBD0_VERTEX_COUNT = 14164


class InvariantError(Exception):
    """Raised when the comparison cannot be performed or a contract is violated.

    A threshold being exceeded is a *result* (``passed: False``), not an
    exception. Exceptions are reserved for inputs that make the comparison
    meaningless -- mismatched topology, a missing subdivision marker, a
    threshold below the numeric floor.
    """


def load_regions(path, expect_sizes=True):
    """Load the region index partition from a ``regions.json`` artifact.

    ``regions.json`` is currently only ever written as an output of
    ``cc_compare_headshot_geometry_v1.compare()``; nothing reads it back. This is
    that reader. Index lists are 0-based and interleaved, not contiguous blocks.
    """
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return parse_regions(raw, expect_sizes=expect_sizes)


def parse_regions(raw, expect_sizes=True):
    """Validate an already-decoded region partition.

    Kept separate from file reading so the validation rules are testable
    without touching the filesystem.
    """
    if not isinstance(raw, dict):
        raise InvariantError("regions.json must be an object")
    missing = sorted(set(EXPECTED_REGION_SIZES) - set(raw))
    if missing:
        raise InvariantError("regions.json lacks regions: {}".format(missing))

    regions = {}
    for name in EXPECTED_REGION_SIZES:
        values = raw[name]
        if not isinstance(values, list) or not values:
            raise InvariantError("Region {} must be a non-empty list".format(name))
        indices = np.asarray(values, dtype=np.int64)
        if indices.ndim != 1:
            raise InvariantError("Region {} must be one-dimensional".format(name))
        if np.unique(indices).size != indices.size:
            raise InvariantError("Region {} contains duplicate indices".format(name))
        if indices.min() < 0:
            raise InvariantError("Region {} contains a negative index".format(name))
        if expect_sizes and indices.size != EXPECTED_REGION_SIZES[name]:
            raise InvariantError(
                "Region {} has {} indices, expected {} for CC3+ body topology".format(
                    name, indices.size, EXPECTED_REGION_SIZES[name]
                )
            )
        regions[name] = indices
    return regions


def _vertices(snapshot, label, space):
    """Extract an (N, 3) float64 array for ``space`` from a capture snapshot."""
    if not isinstance(snapshot, dict):
        raise InvariantError("{} snapshot must be an object".format(label))
    if space not in ("local", "world"):
        raise InvariantError("Unsupported coordinate space: {}".format(space))
    if space not in snapshot:
        raise InvariantError(
            "{} snapshot has no {} vertices".format(label, space)
        )
    array = np.asarray(snapshot[space], dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise InvariantError(
            "{} {} vertices must have shape (N, 3), got {}".format(
                label, space, array.shape
            )
        )
    return array


def _require_subd0_world_contract(before, after):
    """Mirror the two-way marker contract used for world-space targets.

    The CC side writes ``working_subdivision_level`` / ``world_eligible``; the
    offline side refuses to proceed without them. Same pattern as
    ``scalp_target_world_guard_implementation_20261003_v1.py``.
    """
    for label, snapshot in (("before", before), ("after", after)):
        level = snapshot.get("working_subdivision_level")
        if level != 0 or snapshot.get("world_eligible") is not True:
            raise InvariantError(
                "{} requires a capture explicitly verified at working SubD 0 "
                "before world-space comparison (level={!r}, world_eligible={!r})".format(
                    label, level, snapshot.get("world_eligible")
                )
            )


def _finite_audit(before, after, indices):
    """Report non-finite inputs instead of letting them compare as equal.

    Two NaN values must never pass as "unchanged", and ``inf - (-inf)`` must be
    surfaced rather than folded into a finite maximum. Same numeric hygiene as
    ``cc_audit_headshot_fbx_v1.compare()``.
    """
    before_bad = int(np.count_nonzero(~np.isfinite(before[indices])))
    after_bad = int(np.count_nonzero(~np.isfinite(after[indices])))
    return {
        "before_nonfinite_components": before_bad,
        "after_nonfinite_components": after_bad,
        "comparable": before_bad == 0 and after_bad == 0,
    }


def _region_delta(before, after, indices):
    """Per-region statistics plus the raw displacement vector.

    Returns ``(stats, delta_mm_or_None)``. ``delta`` is ``None`` whenever the
    region is not comparable, so callers cannot accidentally gate on zeros.
    """
    audit = _finite_audit(before, after, indices)
    stats = {
        "vertex_count": int(indices.size),
        "finite_audit": audit,
        "max_displacement_mm": None,
        "mean_displacement_mm": None,
        "p95_displacement_mm": None,
        "vertices_above_1mm": None,
        "vertices_above_3mm": None,
    }
    if not audit["comparable"]:
        return stats, None

    # Overflow here is an expected input condition, not a programming error:
    # it is detected and reported below rather than raised as a warning.
    with np.errstate(over="ignore", invalid="ignore"):
        delta = np.linalg.norm(after[indices] - before[indices], axis=1) * CM_TO_MM
    if not np.all(np.isfinite(delta)):
        # Subtraction overflowed even though both inputs were finite.
        stats["finite_audit"] = dict(
            audit, comparable=False, subtraction_overflow=True
        )
        return stats, None

    stats.update(
        {
            "max_displacement_mm": float(delta.max()),
            "mean_displacement_mm": float(delta.mean()),
            "p95_displacement_mm": float(np.percentile(delta, 95)),
            "vertices_above_1mm": int((delta > 1.0).sum()),
            "vertices_above_3mm": int((delta > 3.0).sum()),
        }
    )
    return stats, delta


def region_delta(before, after, indices):
    """Per-region displacement statistics in millimetres, JSON-serialisable.

    Mirrors ``cc_compare_headshot_geometry_v1.stats()`` for the shared keys so
    the two reports stay readable side by side, and adds the finite audit the
    acceptance decision needs.

    When the inputs are not comparable, the displacement fields are ``None``
    rather than ``0.0`` -- an uncomparable region must not look clean.
    """
    stats, _ = _region_delta(before, after, indices)
    return stats


def _resolve_tolerances(tolerance_mm):
    resolved = dict(DEFAULT_TOLERANCE_MM)
    resolved.update(tolerance_mm or {})
    for name, value in sorted(resolved.items()):
        numeric = float(value)
        if not np.isfinite(numeric) or numeric <= 0.0:
            raise InvariantError(
                "Tolerance for {} must be a positive finite value".format(name)
            )
        if numeric < NUMERIC_FLOOR_MM:
            raise InvariantError(
                "Tolerance for {} is {} mm, below the {} mm float32 repeat-read "
                "noise floor; such a threshold only produces false positives".format(
                    name, numeric, NUMERIC_FLOOR_MM
                )
            )
        resolved[name] = numeric
    return resolved


def compare_assembly_snapshots(
    before,
    after,
    regions,
    space="local",
    tolerance_mm=None,
    allowances=None,
    max_offenders=64,
):
    """Compare a pre-assembly and post-assembly capture of the same body mesh.

    ``allowances`` carries named sub-region index sets that are permitted a
    bounded displacement, e.g. an eyelid band if the eyelash ``Apply Morph``
    legitimately moves it:

        {"eyelid_band": {"indices": [...], "tolerance_mm": 0.35,
                         "reason": "...", "evidence": "..."}}

    It is intentionally empty by default. The first representative character
    establishes whether any allowance is needed at all, and what its bound is;
    guessing one here would only mask a real regression.

    Returns a JSON-serialisable report. Exceeding a tolerance sets
    ``passed: False`` -- it does not raise.
    """
    before_vertices = _vertices(before, "before", space)
    after_vertices = _vertices(after, "after", space)

    if before_vertices.shape != after_vertices.shape:
        raise InvariantError(
            "Vertex arrays differ in shape ({} vs {}); different subdivision "
            "topologies are never subtracted point by point".format(
                before_vertices.shape, after_vertices.shape
            )
        )
    for label, snapshot in (("before", before), ("after", after)):
        name = snapshot.get("mesh")
        if name is not None and name != "CC_Base_Body":
            raise InvariantError(
                "{} snapshot is mesh {!r}; this check is defined for "
                "CC_Base_Body".format(label, name)
            )
    if before.get("vertex_count") != after.get("vertex_count"):
        raise InvariantError(
            "Snapshots report different vertex counts ({!r} vs {!r}); mesh "
            "levels are keyed by (name, vertex_count) and never mixed".format(
                before.get("vertex_count"), after.get("vertex_count")
            )
        )
    if space == "world":
        _require_subd0_world_contract(before, after)

    vertex_total = before_vertices.shape[0]
    for name, indices in sorted(regions.items()):
        if indices.size and int(indices.max()) >= vertex_total:
            raise InvariantError(
                "Region {} indexes vertex {} but the mesh has {}".format(
                    name, int(indices.max()), vertex_total
                )
            )

    resolved = _resolve_tolerances(tolerance_mm)
    allowances = allowances or {}
    allowance_lookup = {}
    for allow_name, spec in sorted(allowances.items()):
        bound = float(spec["tolerance_mm"])
        if bound < NUMERIC_FLOOR_MM:
            raise InvariantError(
                "Allowance {} is {} mm, below the {} mm noise floor".format(
                    allow_name, bound, NUMERIC_FLOOR_MM
                )
            )
        for index in np.asarray(spec["indices"], dtype=np.int64).tolist():
            previous = allowance_lookup.get(index)
            if previous is not None and previous[1] != bound:
                raise InvariantError(
                    "Vertex {} is covered by conflicting allowances {} and "
                    "{}".format(index, previous[0], allow_name)
                )
            allowance_lookup[index] = (allow_name, bound)

    report = {
        "schema_version": 1,
        "space": space,
        "mesh": before.get("mesh") or "CC_Base_Body",
        "vertex_count": vertex_total,
        "working_subdivision_level": {
            "before": before.get("working_subdivision_level"),
            "after": after.get("working_subdivision_level"),
        },
        "region_scope": REGION_SCOPE,
        "tolerance_mm": resolved,
        "allowances": {
            name: {
                "tolerance_mm": float(spec["tolerance_mm"]),
                "vertex_count": int(np.asarray(spec["indices"]).size),
                "reason": spec.get("reason"),
                "evidence": spec.get("evidence"),
            }
            for name, spec in sorted(allowances.items())
        },
        "regions": {},
        "failed_regions": [],
        "uncomparable_regions": [],
    }

    for name in GATED_REGIONS:
        if name not in regions:
            raise InvariantError("Gated region {} is absent".format(name))
        indices = regions[name]
        stats, delta = _region_delta(before_vertices, after_vertices, indices)
        tolerance = resolved[name]
        stats["applied_tolerance_mm"] = tolerance

        if delta is None:
            stats["passed"] = False
            stats["reason"] = "non_finite_inputs"
            report["uncomparable_regions"].append(name)
            report["failed_regions"].append(name)
            report["regions"][name] = stats
            continue

        effective = np.full(indices.size, tolerance, dtype=np.float64)
        covered = []
        for position, index in enumerate(indices.tolist()):
            entry = allowance_lookup.get(index)
            if entry is not None:
                effective[position] = entry[1]
                covered.append(entry[0])
        stats["allowance_covered_vertices"] = len(covered)

        exceeded = np.nonzero(delta > effective)[0]
        stats["exceeding_vertex_count"] = int(exceeded.size)
        order = exceeded[np.argsort(-delta[exceeded])][:max_offenders]
        stats["worst_offenders"] = [
            {
                "vertex_index": int(indices[position]),
                "displacement_mm": float(delta[position]),
                "applied_tolerance_mm": float(effective[position]),
                "allowance": allowance_lookup.get(
                    int(indices[position]), (None, None)
                )[0],
            }
            for position in order.tolist()
        ]
        stats["passed"] = bool(exceeded.size == 0)
        if not stats["passed"]:
            report["failed_regions"].append(name)
        report["regions"][name] = stats

    report["passed"] = not report["failed_regions"]
    report["acceptance"] = (
        "Machine geometry invariant over the gated regions in {} space only. "
        "A pass does not assert appearance quality, expression behaviour or "
        "any human visual acceptance.".format(space)
    )
    return report
