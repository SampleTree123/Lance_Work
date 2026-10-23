"""Build a bounded Average-body restoration target without operating CC.

Restore vertices outside the installed Headshot head set to a measured canonical
reference, tapering the correction through a few head-side topology rings. The
photo face is locked. This is an experiment, not an accepted anatomical mask.
"""
import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np

from cc_compare_headshot_geometry_v1 import RESOURCE, head_ids, mask_weights, read_obj


def record(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def build(reference_world, reference_obj, candidate_world, candidate_obj, output, rings=6,
          native_obj_space=False):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing to overwrite an existing experiment directory")
    if not 1 <= rings <= 12:
        raise ValueError("Boundary taper must be 1..12 topology rings")
    obj_a, uva, fa = read_obj(reference_obj)
    obj_b, uvb, fb = read_obj(candidate_obj)
    if native_obj_space:
        if reference_world is not None or candidate_world is not None:
            raise ValueError("Native OBJ mode must not mix SDK world-coordinate inputs")
        a, b = obj_a, obj_b
        translation_correction = np.zeros(3)
    else:
        reference = json.loads(Path(reference_world).read_text(encoding="utf-8-sig"))
        candidate = json.loads(Path(candidate_world).read_text(encoding="utf-8-sig"))
        a = np.asarray(reference["vertices"], dtype=float)
        b = np.asarray(candidate["vertices"], dtype=float)
        for key in ("rotation", "s"):
            if reference["avatar_transform"][key] != candidate["avatar_transform"][key]:
                raise ValueError("Root rotation/scale differ")
        ta = np.array([reference["avatar_transform"]["translation"][k] for k in "xyz"])
        tb = np.array([candidate["avatar_transform"]["translation"][k] for k in "xyz"])
        translation_correction = tb - ta
        a = a + translation_correction
    if a.shape != (14164, 3) or b.shape != a.shape or not np.isfinite([a, b]).all():
        raise ValueError("Expected two finite CC3+ base body meshes")
    if fa != fb or not np.array_equal(uva, uvb):
        raise ValueError("Canonical/candidate body topology or UV mismatch")

    head = head_ids()
    is_head = np.zeros(len(a), dtype=bool)
    is_head[head] = True
    weights, alpha_path = mask_weights(uvb, fb)
    face = is_head & (weights >= .99)
    adjacency = [set() for _ in range(len(a))]
    for polygon in fb:
        ids = [v for v, _ in polygon]
        for i, j in zip(ids, ids[1:] + ids[:1]):
            adjacency[i].add(j)
            adjacency[j].add(i)
    boundary = [i for i in head if any(not is_head[j] for j in adjacency[i])]
    if not boundary:
        raise ValueError("No head/body topology boundary found")
    distance = np.full(len(a), rings + 2, dtype=int)
    queue = deque(boundary)
    distance[boundary] = 1
    while queue:
        i = queue.popleft()
        if distance[i] >= rings:
            continue
        for j in adjacency[i]:
            if is_head[j] and distance[j] > distance[i] + 1:
                distance[j] = distance[i] + 1
                queue.append(j)
    blend = np.ones(len(a))
    t = np.clip(distance[head] / (rings + 1), 0, 1)
    blend[head] = 1 - t * t * (3 - 2 * t)
    if np.any(blend[face] > 0):
        raise ValueError("Taper reaches the photo face; use fewer rings")
    target = b + blend[:, None] * (a - b)
    target[~is_head] = a[~is_head]
    target[blend == 0] = b[blend == 0]

    lines = Path(candidate_obj).read_text(encoding="utf-8-sig").splitlines(True)
    group, body_ids = "", set()
    for line in lines:
        p = line.split()
        if p and p[0] in ("g", "o"):
            group = p[1]
        elif p and p[0] == "f" and group == "CC_Base_Body":
            body_ids.update(int(x.split("/")[0]) - 1 for x in p[1:])
    ordered = sorted(body_ids)
    if len(ordered) != len(a) or ordered != list(range(ordered[0], ordered[0] + len(a))):
        raise ValueError("Unexpected OBJ body vertex layout")
    output.mkdir(parents=True)
    obj = output / ("target_native.obj" if native_obj_space else "target_world.obj")
    with obj.open("w", encoding="utf-8") as stream:
        vi = 0
        for line in lines:
            if line.startswith("v "):
                if vi in body_ids:
                    line = "v %.12f %.12f %.12f\n" % tuple(target[vi - ordered[0]])
                vi += 1
            stream.write(line)
    np.savez_compressed(output / "target_geometry.npz", reference=a, candidate=b,
                        target=target, blend=blend, head_ids=head, face_ids=np.flatnonzero(face),
                        boundary_ids=np.asarray(boundary), distance=distance)
    delta = np.linalg.norm(target - b, axis=1) * 10
    report = {
        "status": "offline_target_only_not_accepted",
        "scope": "Restore measured canonical body outside installed Headshot head set; head-side taper is provisional, not an anatomical acceptance mask",
        "implementation": record(__file__),
        "inputs": [record(p) for p in (reference_world, reference_obj, candidate_world,
                                       candidate_obj, RESOURCE / "CreateHead.ini", alpha_path) if p is not None],
        "coordinate_space": "native_ZUp_bind_pose_OBJ" if native_obj_space else "SDK_world",
        "root_translation_correction_cm": translation_correction.tolist(),
        "topology_uv_identical": True, "taper_rings": rings,
        "body_vertices_restored": int((~is_head).sum()),
        "head_boundary_vertices": len(boundary),
        "head_taper_vertices": int((is_head & (blend > 0)).sum()),
        "photo_face_vertices_locked": int(face.sum()),
        "target_body_reference_max_mm": float(np.linalg.norm(target[~is_head] - a[~is_head], axis=1).max() * 10),
        "target_photo_face_change_max_mm": float(delta[face].max()),
        "body_correction_max_mm": float(delta[~is_head].max()),
        "taper_correction_max_mm": float(delta[is_head].max()),
        "target_obj": record(obj),
        "required_followup": ["CC native morph application and reload" if native_obj_space else "CC replacement and reload",
                              "subdivision roundtrip", "Average final export", "eyes/expression/neck visual inspection"],
    }
    (output / "target_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("reference-world", "candidate-world"):
        parser.add_argument("--" + key)
    for key in ("reference-obj", "candidate-obj", "output"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--rings", type=int, default=6)
    parser.add_argument("--native-obj-space", action="store_true")
    args = parser.parse_args()
    if not args.native_obj_space and (not args.reference_world or not args.candidate_world):
        parser.error("World-coordinate mode requires --reference-world and --candidate-world")
    print(json.dumps(build(args.reference_world, args.reference_obj, args.candidate_world,
                           args.candidate_obj, args.output, args.rings, args.native_obj_space), indent=2))
