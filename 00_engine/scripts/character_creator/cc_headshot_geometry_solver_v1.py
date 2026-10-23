"""Offline, per-character Headshot Average / fixed-scalp compensation.

All SDK captures and affine probes must belong to the current input character.
This module never imports RLPy, operates CC, or modifies reference projects.
Distances use CC centimeters internally and millimeters in reports.
"""
from collections import deque
import hashlib
import json
from pathlib import Path

import numpy as np

BODY_COUNT = 14164
DEFAULT_REFERENCES = Path(__file__).with_name("cc_headshot_creation_references_v1.json")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_record(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size}


def verify_record(record):
    actual = file_record(record["path"])
    if actual["sha256"] != record["sha256"]:
        raise ValueError("Reference SHA mismatch: " + str(record["path"]))
    return Path(actual["path"])


def points(value, count, label):
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (count, 3) or not np.isfinite(array).all():
        raise ValueError(label + " requires finite (vertex_count,3) coordinates")
    return array


def verified_world(record, count=BODY_COUNT):
    if record.get("working_subdivision_level") != 0 or record.get("world_target_eligible") is not True:
        raise ValueError("World target requires a verified active SubD0 capture")
    return points(record["vertices"], count, "world capture")


def align_reference(reference_record, candidate_record, count=BODY_COUNT):
    reference = verified_world(reference_record, count)
    verified_world(candidate_record, count)
    for key in ("rotation", "s"):
        if reference_record["avatar_transform"][key] != candidate_record["avatar_transform"][key]:
            raise ValueError("Root rotation/scale differ; refusing hidden registration")
    ta = np.array([reference_record["avatar_transform"]["translation"][k] for k in "xyz"])
    tb = np.array([candidate_record["avatar_transform"]["translation"][k] for k in "xyz"])
    return reference - ta + tb


def restore_blend(count, faces, head, weights, rings=6):
    """Existing six-ring Average neck taper; full photo-face vertices locked."""
    if not isinstance(rings, int) or isinstance(rings, bool) or not 1 <= rings <= 12:
        raise ValueError("rings must be 1..12")
    head = np.asarray(head, dtype=np.int64)
    if head.ndim != 1 or not len(head) or len(np.unique(head)) != len(head) or np.any((head < 0) | (head >= count)):
        raise ValueError("Invalid head indices")
    w = np.asarray(weights, dtype=float)
    if w.shape != (count,) or not np.isfinite(w).all() or np.any((w < 0) | (w > 1)):
        raise ValueError("Invalid face weights")
    is_head = np.zeros(count, dtype=bool)
    is_head[head] = True
    adjacency = [set() for _ in range(count)]
    for polygon in faces:
        ids = [int(v) for v, _ in polygon]
        if len(ids) < 3 or any(v < 0 or v >= count for v in ids):
            raise ValueError("Invalid topology")
        for i, j in zip(ids, ids[1:] + ids[:1]):
            adjacency[i].add(j)
            adjacency[j].add(i)
    boundary = [i for i in head if any(not is_head[j] for j in adjacency[i])]
    if not boundary:
        raise ValueError("No head/body topology boundary")
    distance = np.full(count, rings + 2, dtype=int)
    distance[boundary] = 1
    queue = deque(boundary)
    while queue:
        i = queue.popleft()
        if distance[i] >= rings:
            continue
        for j in adjacency[i]:
            if is_head[j] and distance[j] > distance[i] + 1:
                distance[j] = distance[i] + 1
                queue.append(j)
    blend = np.ones(count)
    t = np.clip(distance[head] / (rings + 1), 0, 1)
    blend[head] = 1 - t * t * (3 - 2 * t)
    if np.any(blend[is_head & (w >= .99)] > 0):
        raise ValueError("Average taper reaches full photo-face region")
    return blend


def build_desired_world(source_world, average_world, scalp_world, head, weights, faces, rings=6):
    count = len(source_world)
    source = points(source_world, count, "source")
    average = points(average_world, count, "average")
    scalp = points(scalp_world, count, "scalp")
    blend = restore_blend(count, faces, head, weights, rings)
    head = np.asarray(head, dtype=int)
    weights = np.asarray(weights, dtype=float).copy()
    weights[weights <= .01] = 0
    weights[weights >= .99] = 1
    desired = source + blend[:, None] * (average - source)
    outside = np.setdiff1d(np.arange(count), head)
    desired[outside] = average[outside]
    desired[blend == 0] = source[blend == 0]
    # Already Average-normalized scalp is applied last: no double neck taper.
    desired[head] = scalp[head] * (1 - weights[head, None]) + desired[head] * weights[head, None]
    return desired, blend, weights


def skin_affine(calibration_after, count=BODY_COUNT, shift_cm=.1):
    if not np.isfinite(shift_cm) or shift_cm <= 0:
        raise ValueError("Invalid affine probe shift")
    baseline = points(calibration_after["zero"], count, "zero probe")
    matrix = np.stack([(points(calibration_after[a], count, a + " probe") - baseline) / shift_cm
                       for a in ("x", "y", "z")], axis=2)
    condition = np.linalg.cond(matrix)
    determinant = np.abs(np.linalg.det(matrix))
    if not np.isfinite(condition).all() or condition.max() >= 100 or determinant.min() <= 1e-6:
        raise ValueError("Per-character coordinate calibration is ill-conditioned")
    return baseline, matrix, {"condition_max": float(condition.max()),
                              "determinant_min_abs": float(determinant.min())}


def verify_identity_origin(initial_local, zero_local, count=BODY_COUNT):
    initial = points(initial_local, count, "identity initial local")
    baseline = points(zero_local, count, "zero calibration local")
    maximum = float(np.linalg.norm(initial - baseline, axis=1).max() * 10)
    # Saving / loading the successful historical female zero probe changed
    # float32 coordinates by at most 0.000152885623 mm. This origin-only gate
    # permits that serialization noise, not a different input or geometry drift.
    if maximum > .0002:
        raise ValueError("Identity roundtrip initial local is not current zero calibration baseline")
    return {"passed": True, "max_displacement_mm": maximum, "limit_mm": .0002,
            "basis": "Accepted historical female photo01 zero save/reload max 0.0001528856233776226mm; male02 exact"}


def inverse_sparse(rhs, model, max_iterations=2000, tolerance_mm=1e-6):
    count = len(rhs)
    rhs = points(rhs, count, "inverse rhs")
    rows, cols = np.asarray(model["rows"]), np.asarray(model["cols"])
    values = np.asarray(model["values"], dtype=float)
    if (rows.ndim != 1 or cols.shape != rows.shape or values.shape != rows.shape or not len(rows)
            or rows.dtype.kind not in "iu" or cols.dtype.kind not in "iu"
            or not np.isfinite(values).all() or np.any((rows < 0) | (rows >= count))
            or np.any((cols < 0) | (cols >= count))):
        raise ValueError("Invalid sparse subdivision operator")
    if not np.isfinite(tolerance_mm) or tolerance_mm <= 0 or not isinstance(max_iterations, int) or max_iterations < 1:
        raise ValueError("Invalid inverse solver limits")
    diag = np.bincount(rows[rows == cols], weights=values[rows == cols], minlength=count)
    if np.any(~np.isfinite(diag)) or np.any(np.abs(diag) <= 1e-12):
        raise ValueError("Subdivision operator has a zero/nonfinite diagonal")
    correction = np.zeros_like(rhs)
    for iteration in range(max_iterations):
        transformed = np.column_stack([np.bincount(rows, weights=values * correction[cols, j], minlength=count)
                                       for j in range(3)])
        residual = rhs - transformed
        maximum = float(np.linalg.norm(residual, axis=1).max() * 10)
        if not np.isfinite(maximum):
            raise ValueError("Inverse solve diverged")
        if maximum < tolerance_mm:
            return correction, {"iterations": iteration, "residual_mm": maximum}
        correction += .7 * residual / diag[:, None]
    raise ValueError("Inverse subdivision compensation did not converge")


def solve_geometry(source_world_record, source_local, average_world_record, scalp_world_record,
                   faces, head, weights, calibration_after, identity_return_local, model, rings=6):
    count = len(source_local)
    world = verified_world(source_world_record, count)
    local = points(source_local, count, "source local")
    average = align_reference(average_world_record, source_world_record, count)
    scalp = align_reference(scalp_world_record, source_world_record, count)
    desired_world, blend, weights = build_desired_world(world, average, scalp, head, weights, faces, rings)
    baseline, matrix, affine_stats = skin_affine(calibration_after, count)
    desired = local + np.einsum("nij,nj->ni", matrix, desired_world - world)
    observed = points(identity_return_local, count, "current character identity roundtrip")
    correction, solver_stats = inverse_sparse(desired - observed, model)
    precomp = baseline + correction
    submitted = world + np.linalg.solve(matrix, correction[..., None])[..., 0]
    points(submitted, count, "submitted world")
    arrays = dict(desired=desired, desired_world=desired_world, precomp=precomp,
                  submitted_world=submitted, source_world=world, source_local=local,
                  reference_world=average, scalp_reference=scalp, weights=weights,
                  body_blend=blend, skin_affine=matrix, identity_return_local=observed)
    return arrays, {"solver": solver_stats, "skin_affine": affine_stats,
                    "head_vertices": len(head), "body_outside_head_vertices": count - len(head),
                    "face_full_vertices": int(np.sum(weights[np.asarray(head)] == 1)),
                    "fixed_region_vertices": int(np.sum(weights[np.asarray(head)] == 0))}


def write_world_obj(template_path, vertices, output_path):
    from cc_compare_headshot_geometry_v1 import read_obj
    body, _, _ = read_obj(template_path)
    vertices = points(vertices, len(body), "OBJ body")
    lines = Path(template_path).read_text(encoding="utf-8-sig").splitlines(True)
    group, ids = "", set()
    for line in lines:
        tokens = line.split()
        if tokens and tokens[0] in ("o", "g"):
            group = tokens[1]
        elif tokens and tokens[0] == "f" and group == "CC_Base_Body":
            ids.update(int(x.split("/")[0]) - 1 for x in tokens[1:])
    first = min(ids)
    index = 0
    with Path(output_path).open("x", encoding="utf-8") as stream:
        for line in lines:
            if line.startswith("v "):
                if index in ids:
                    line = "v %.12f %.12f %.12f\n" % tuple(vertices[index - first])
                index += 1
            stream.write(line)


def load_references(sex, references_path=DEFAULT_REFERENCES):
    if sex not in ("female", "male"):
        raise ValueError("sex must be female or male")
    references = read_json(references_path)
    if references.get("schema_version") != 1 or references.get("body_vertex_count") != BODY_COUNT:
        raise ValueError("Unsupported creation reference schema")
    shared, selected = references["shared"], references["sexes"][sex]
    def verify_tree(value):
        if isinstance(value, dict):
            if "path" in value and "sha256" in value:
                verify_record(value)
            else:
                for nested in value.values():
                    verify_tree(nested)
        elif isinstance(value, list):
            for nested in value:
                verify_tree(nested)
    verify_tree(shared)
    verify_tree(selected)
    return references, selected


def build_geometry_targets(source_capture_dir, calibration_dirs, identity_dir, sex, output_dir,
                           references_path=DEFAULT_REFERENCES):
    """File orchestration only: inputs are fresh CC captures, output is a new dir."""
    from cc_compare_headshot_geometry_v1 import read_obj, head_ids, mask_weights
    refs, selected = load_references(sex, references_path)
    shared = refs["shared"]
    output = Path(output_dir)
    if output.exists():
        raise ValueError("Refusing existing geometry output; use a new attempt")
    source = Path(source_capture_dir)
    template = source / "before_body.obj"
    topology = read_obj(template)
    for record in (shared["operator_topology_obj"], selected["average_body_obj"], selected["scalp_body_obj"]):
        other = read_obj(record["path"])
        if topology[2] != other[2] or not np.array_equal(topology[1], other[1]):
            raise ValueError("Body topology or UV differs from locked operator / reference")
    inputs = [template, source / "before_world_mesh.json", source / "before_mesh.json",
              Path(identity_dir) / "return_0_local_and_bones.json",
              Path(identity_dir) / "initial_0_local_and_bones.json", Path(references_path)]
    world_record = read_json(source / "before_world_mesh.json")
    local = read_json(source / "before_mesh.json")["vertices"]
    calibration = {}
    # Every affine probe must be applied from this exact source world/local state.
    for axis in ("zero", "x", "y", "z"):
        folder = Path(calibration_dirs[axis])
        before = read_json(folder / "before_world_mesh.json")
        if before != world_record:
            raise ValueError("Affine probe is not from current source capture: " + axis)
        prior_local = read_json(folder / "before_mesh.json")
        if not np.array_equal(np.asarray(prior_local["vertices"]), np.asarray(local)):
            raise ValueError("Affine local source differs: " + axis)
        calibration[axis] = read_json(folder / "after_mesh.json")["vertices"]
        inputs.extend(folder / name for name in ("before_world_mesh.json", "before_mesh.json", "after_mesh.json"))
    origin = verify_identity_origin(read_json(Path(identity_dir) / "initial_0_local_and_bones.json")["vertices"],
                                    calibration["zero"])
    head = head_ids()
    weights, mask = mask_weights(topology[1], topology[2])
    if file_record(mask)["sha256"] != shared["face_mask"]["sha256"]:
        raise ValueError("Mask changed during geometry preparation")
    with np.load(shared["subdivision_operator"]["path"], allow_pickle=False) as operator:
        arrays, stats = solve_geometry(world_record, local, read_json(selected["average_world"]["path"]),
            read_json(selected["scalp_world"]["path"]), topology[2], head, weights, calibration,
            read_json(Path(identity_dir) / "return_0_local_and_bones.json")["vertices"], operator)
    output.mkdir(parents=True)
    target = output / "target_world.obj"
    write_world_obj(template, arrays["submitted_world"], target)
    np.savez_compressed(output / "target_geometry.npz", **arrays)
    report = {"schema_version": 1, "status": "offline_target_requires_CC_application", "sex": sex,
              "coordinate_space": "SDK_world_at_verified_SubD0", "stats": stats, "identity_origin": origin,
              "implementation": file_record(__file__), "inputs": [file_record(p) for p in inputs],
              "reference_config": file_record(references_path), "target_obj": file_record(target),
              "target_geometry": file_record(output / "target_geometry.npz"),
              "limits": ["Installed face alpha defines a fixed region including scalp, ears and neck.",
                         "Current-character affine calibration and identity roundtrip are mandatory.",
                         "Target computation alone does not prove CC application or final baked geometry."]}
    (output / "geometry_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report
