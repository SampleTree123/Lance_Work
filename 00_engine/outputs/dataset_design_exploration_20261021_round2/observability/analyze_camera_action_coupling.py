"""Quantify camera-policy vs exact-path preservation on existing formal paths."""
from pathlib import Path
from collections import defaultdict
from itertools import combinations
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def norm(v):
    return math.sqrt(sum(x*x for x in v))


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def angle(a, b):
    denom = norm(a)*norm(b)
    return math.degrees(math.acos(max(-1, min(1, sum(x*y for x, y in zip(a, b))/denom))))


def summary(values):
    xs = sorted(values)
    return {"min": xs[0], "median": statistics.median(xs),
            "p95": xs[int((len(xs)-1)*.95)], "max": xs[-1]}


def main():
    plan = json.loads((ROOT / "00_engine/outputs/production_workflow_20261017_v1/camera_library/production10/camera_plan.json").read_text(encoding="utf-8-sig"))
    active = set(json.loads((ROOT / "00_engine/outputs/dataset_design_exploration_20261021_v1/inventory/normalized_inventory.json").read_text(encoding="utf-8-sig"))["actions"])
    groups = defaultdict(list)
    for shot in plan["shots"]:
        if shot["motion_id"] in active:
            groups[(shot["camera_id"], shot["orientation"])].append(shot)
    rows = []
    for (camera, aspect), shots in groups.items():
        for a, b in combinations(shots, 2):
            fa = a["frames"] + [a["endpoint_validation_frame"]]
            fb = b["frames"] + [b["endpoint_validation_frame"]]
            assert len(fa) == len(fb)
            assert all(abs(x["t"]-y["t"]) < 1e-6 for x, y in zip(fa, fb))
            translation = [norm(sub(x["position"], y["position"])) for x, y in zip(fa, fb)]
            relative = [norm(sub(sub(x["position"], fa[0]["position"]), sub(y["position"], fb[0]["position"]))) for x, y in zip(fa, fb)]
            rotation = [angle(sub(x["look_at"], x["position"]), sub(y["look_at"], y["position"])) for x, y in zip(fa, fb)]
            rows.append({
                "camera": camera, "aspect": aspect, "action_a": a["motion_id"], "action_b": b["motion_id"],
                "max_camera_position_difference_cm": max(translation),
                "max_initial_aligned_path_difference_cm": max(relative),
                "max_view_direction_difference_degrees": max(rotation),
                "max_fov_difference_degrees": max(abs(x["horizontal_fov_degrees"]-y["horizontal_fov_degrees"]) for x, y in zip(fa, fb))
            })
    summaries = []
    for camera, aspect in sorted(groups):
        subset = [r for r in rows if r["camera"] == camera and r["aspect"] == aspect]
        summaries.append({
            "camera": camera, "aspect": aspect, "unordered_action_pairs": len(subset),
            "max_camera_position_difference_cm": summary([r["max_camera_position_difference_cm"] for r in subset]),
            "initial_aligned_path_difference_cm": summary([r["max_initial_aligned_path_difference_cm"] for r in subset]),
            "path_pairs_within_cm": {str(t): sum(r["max_initial_aligned_path_difference_cm"] <= t for r in subset) for t in (1, 10, 100)},
            "view_direction_difference_degrees": summary([r["max_view_direction_difference_degrees"] for r in subset])
        })
    out = {
        "status": "offline_formal_camera_paths_not_scene_pixels",
        "meaning": "Same camera policy does not imply same numeric camera trajectory after an action edit.",
        "limitations": ["Representative planner sex only.", "Scene placement and ground-follow omitted.", "This is a semantic contract choice, not a camera implementation defect."],
        "pair_count": len(rows), "by_camera": summaries, "pairs": rows
    }
    (HERE / "camera_action_coupling.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"pairs": len(rows), "front_full": [r for r in summaries if r["camera"] == "front_full"]}))


if __name__ == "__main__":
    main()
