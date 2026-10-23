"""Offline camera/bone projection probes. No UE and no pixel visibility claims."""
from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import json
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRIPTS = ROOT / "00_engine/scripts/unreal"
sys.path.insert(0, str(SCRIPTS))
from camera_motion_planner_v1 import project


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def length(a):
    return math.sqrt(sum(x*x for x in a))


def unit(a):
    n = length(a)
    return [x/n for x in a] if n > 1e-9 else [0, 0, 0]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def quantile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs)-1, int((len(xs)-1)*q))] if xs else None


def dist(xs):
    return {"min": min(xs), "median": quantile(xs, .5), "p95": quantile(xs, .95), "max": max(xs)}


def box_points(center, hx, hy, zlo, zhi):
    return [[center[0]+x, center[1]+y, center[2]+z]
            for x in (-hx, hx) for y in (-hy, hy) for z in (zlo, zhi)]


def project_box(points, row, width, height):
    pp = [project(p, row, width/height) for p in points]
    if any(p is None for p in pp):
        return {"intersection_fraction": 0, "projected_height_px": 0, "crosses_near_plane": True}
    u0, u1 = min(p[0] for p in pp), max(p[0] for p in pp)
    v0, v1 = min(p[1] for p in pp), max(p[1] for p in pp)
    area = max(0, u1-u0)*max(0, v1-v0)
    overlap = max(0, min(1, u1)-max(0, u0))*max(0, min(1, v1)-max(0, v0))
    return {"intersection_fraction": overlap/area if area else 0,
            "projected_height_px": (v1-v0)*height, "crosses_near_plane": False}


def main():
    camera_dir = ROOT / "00_engine/outputs/production_workflow_20261017_v1/camera_library/production10"
    geometry_file, plan_file = camera_dir/"geometry.json", camera_dir/"camera_plan.json"
    inventory_file = ROOT/"00_engine/outputs/dataset_design_exploration_20261021_v1/inventory/normalized_inventory.json"
    inv = read(inventory_file)
    active = set(inv["actions"])
    geometry, plan = read(geometry_file), read(plan_file)
    actions = {a["motion_id"]: a for a in geometry["actions"] if a["motion_id"] in active}
    geom_shots = {s["shot_id"]: s for s in geometry["shots"]}
    records = []
    for shot in plan["shots"]:
        if shot["motion_id"] not in active:
            continue
        frames = shot["frames"] + [shot["endpoint_validation_frame"]]
        first = frames[0]
        initial_dir = unit(sub(first["look_at"], first["position"]))
        movements = [length(sub(f["position"], first["position"])) for f in frames]
        cosine_angles = [dot(initial_dir, unit(sub(f["look_at"], f["position"]))) for f in frames]
        angles = [math.degrees(math.acos(max(-1, min(1, cosine)))) for cosine in cosine_angles]
        path_cm = sum(length(sub(a["position"], b["position"])) for a, b in zip(frames, frames[1:]))
        fov_span = max(f["horizontal_fov_degrees"] for f in frames)-min(f["horizontal_fov_degrees"] for f in frames)
        bodies = actions[shot["motion_id"]]["samples"]
        camera_samples = geom_shots[shot["shot_id"]]["samples"]
        proxy = []
        for cam in camera_samples:
            body = min(bodies, key=lambda b: abs(b["t"]-cam["t"]))
            assert abs(body["t"]-cam["t"]) <= .02
            bones = body["bones"]
            head = project_box(box_points(bones["head"], 13, 13, -8, 22), cam, shot["width"], shot["height"])
            torso = project_box(
                [bones[k] for k in ("neck_01", "upperarm_l", "upperarm_r", "pelvis")],
                cam, shot["width"], shot["height"])
            lower = project_box(
                [bones[k] for k in ("pelvis", "thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r")],
                cam, shot["width"], shot["height"])
            foot = [project_box(box_points(bones[k], 8, 10, -6, 6), cam, shot["width"], shot["height"])
                    for k in ("foot_l", "foot_r")]
            # Torso heading is a proxy, not head rotation or face visibility.
            torso_heading = unit(cross(sub(bones["upperarm_r"], bones["upperarm_l"]),
                                       sub(bones["neck_01"], bones["pelvis"])))
            towards_camera = unit(sub(cam["position"], bones["head"]))
            facing = dot(torso_heading, towards_camera)
            proxy.append({"t": cam["t"], "head": head, "torso": torso, "lower": lower,
                          "feet_intersection": max(f["intersection_fraction"] for f in foot),
                          "torso_facing_camera_cosine": facing})
        n = len(proxy)
        flags = {
            "head_box_never_intersects_sparse_samples": all(x["head"]["intersection_fraction"] == 0 for x in proxy),
            "feet_boxes_never_intersect_sparse_samples": all(x["feet_intersection"] == 0 for x in proxy),
            "lower_proxy_never_intersects_sparse_samples": all(x["lower"]["intersection_fraction"] == 0 for x in proxy),
            "torso_proxy_never_intersects_sparse_samples": all(x["torso"]["intersection_fraction"] == 0 for x in proxy),
        }
        rows = {
            "shot_id": shot["shot_id"], "action": shot["motion_id"], "camera": shot["camera_id"],
            "aspect": shot["orientation"], "planner_representative_sex": shot["sex"],
            "width": shot["width"], "height": shot["height"], "trajectory_sha256": shot["trajectory_sha256"],
            "translation_max_from_initial_cm": max(movements), "camera_path_length_cm": path_cm,
            "view_direction_max_from_initial_degrees": max(angles), "horizontal_fov_span_degrees": fov_span,
            "approximately_static_1cm_0p1degree": max(movements) <= 1 and max(angles) <= .1 and fov_span <= .01,
            "flags": flags, "sparse_samples": n,
            "head_projected_height_px": dist([x["head"]["projected_height_px"] for x in proxy]),
            "head_fraction_with_half_box_in_frame": sum(x["head"]["intersection_fraction"] >= .5 for x in proxy)/n,
            "feet_fraction_intersecting_frame": sum(x["feet_intersection"] > 0 for x in proxy)/n,
            "torso_front_fraction": sum(x["torso_facing_camera_cosine"] >= .25 for x in proxy)/n,
            "identity_proxy_threshold_sweep": {
                str(px): sum(x["head"]["intersection_fraction"] >= .5
                             and x["head"]["projected_height_px"] >= px
                             and x["torso_facing_camera_cosine"] >= .25 for x in proxy)/n
                for px in (32, 64, 96, 128)},
        }
        # Deliberately rough bound: no real depth/pixels. Useful only as a sensitivity calculation.
        focal_px = shot["width"]/(2*math.tan(math.radians(first["horizontal_fov_degrees"]/2)))
        rows["translation_only_parallax_scale_px_at_depth_m"] = {
            str(m): focal_px*(max(movements)/100)/m for m in (5, 20, 100)}
        records.append(rows)
    groups = defaultdict(list)
    for r in records:
        groups[(r["aspect"], r["camera"])].append(r)
    summary = []
    for (aspect, camera), rows in sorted(groups.items()):
        summary.append({
            "aspect": aspect, "camera": camera, "motions": len(rows),
            "static_count": sum(r["approximately_static_1cm_0p1degree"] for r in rows),
            "camera_translation_cm": dist([r["translation_max_from_initial_cm"] for r in rows]),
            "camera_rotation_degrees": dist([r["view_direction_max_from_initial_degrees"] for r in rows]),
            "feet_absent_sparse_count": sum(r["flags"]["feet_boxes_never_intersect_sparse_samples"] for r in rows),
            "lower_absent_sparse_count": sum(r["flags"]["lower_proxy_never_intersects_sparse_samples"] for r in rows),
            "head_absent_sparse_count": sum(r["flags"]["head_box_never_intersects_sparse_samples"] for r in rows),
            "identity_proxy_64px_front_ever_count": sum(r["identity_proxy_threshold_sweep"]["64"] > 0 for r in rows),
            "identity_proxy_64px_front_halfclip_count": sum(r["identity_proxy_threshold_sweep"]["64"] >= .5 for r in rows),
        })
    payload = {
        "status": "offline_projection_diagnostic_not_pixel_or_occlusion_acceptance",
        "sources": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p in (geometry_file, plan_file, inventory_file)],
        "limitations": [
            "Bone positions are representative planner data, not every identity mesh.",
            "Sparse body probes do not prove absence between sample times.",
            "World-axis envelopes do not encode hair/clothing silhouette or occlusion.",
            "Torso facing is not eye/head orientation; threshold sweeps are sensitivity, not accepted visibility rules.",
            "No source scene geometry, shadows, lighting, skin or garment texture is evaluated.",
            "Production follow-ground transform can add further camera motion.",
            "Translation parallax scale assumes lateral motion and fixed approximate depth, not measured image error."
        ],
        "shot_count": len(records), "active_motions": len(actions),
        "approx_static_count": sum(r["approximately_static_1cm_0p1degree"] for r in records),
        "by_camera": summary,
        "shots": records,
    }
    assert len(records) == 25*21*2
    write("camera_observability.json", payload)
    write("camera_summary.json", {k: v for k, v in payload.items() if k != "shots"})
    print(json.dumps({"shots": len(records), "static": payload["approx_static_count"],
                      "front_head": [r for r in summary if r["camera"] == "front_head"],
                      "front_full": [r for r in summary if r["camera"] == "front_full"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
