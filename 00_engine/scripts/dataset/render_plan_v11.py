"""Resolve adopted v11 nodes to portable render jobs without changing their state.

Paths outside state are workspace-relative POSIX paths; /Game paths are UE paths.
This is an offline planner, never an Unreal asset or media acceptance check.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_CANDIDATE = "00_engine/outputs/dataset_return_control_20261022_v11/selected_candidate"
DEFAULT_PROFILE = "00_engine/outputs/dataset_return_control_20261022_v11/render_preparation/VIDEO_PROFILE.json"
DEFAULT_OUT = "00_engine/outputs/dataset_render_pilot_20261023_v1"
PILOT_NODES = (0, 1, 2, 5, 18, 3775, 3792, 967, 978, 979, 4040, 4058)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def portable_path(value):
    value = re.sub(r"/+", "/", str(value).replace("\\", "/"))
    # Historical source manifests contain the original Windows workspace prefix.
    marker = "/Lance_Work/"
    if marker.lower() in value.lower():
        return value[value.lower().index(marker.lower()) + len(marker):]
    try:
        return Path(value).resolve().relative_to(WORKSPACE).as_posix()
    except ValueError:
        return value


def local_path(value):
    value = portable_path(value)
    p = Path(value)
    return p if p.is_absolute() else WORKSPACE / p


def walk(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", default=DEFAULT_CANDIDATE)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--out", default=DEFAULT_OUT, help="Run directory")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--job-ids", help="Comma separated split_node_000000 IDs")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    args = parser.parse_args(argv)
    if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
        parser.error("shard index must be in [0, shard count)")
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    candidate, profile_path, out = map(local_path, (args.candidate_root, args.profile, args.out))
    manifest_path = candidate / "reference_manifest.json"
    manifest, profile = read_json(manifest_path), read_json(profile_path)
    catalog_path = local_path(next(x["path"] for x in manifest["inputs"] if portable_path(x["path"]).endswith("/catalog.json")))
    catalog = read_json(catalog_path)
    sites = {x["site_id"]: x for x in catalog["sites"]}
    # Reference manifest is the frozen source for saved scene targets when present.
    sites.update({x["site_id"]: x["site"] for x in manifest["requirements"] if x["kind"] == "scene"})
    assets = {x["asset_id"]: x for x in walk(catalog["sexes"]) if x.get("asset_id") and x.get("mesh_paths")}
    requested = set(args.job_ids.split(",")) if args.job_ids else None
    jobs, source_paths = [], [manifest_path, profile_path, catalog_path]
    fps, frames = profile["fps"], profile["output_frame_count"]
    if fps != 30 or frames != 300:
        raise ValueError("v11 pilot requires 30 fps and exactly 300 output frames")
    for split in ("train", "test"):
        requests_path = candidate / split / "render_requests.json"
        source_paths.append(requests_path)
        for request in read_json(requests_path):
            node = request["node_id"]
            job_id = f"{split}_node_{node:06d}"
            state = copy.deepcopy(request["state"])
            sex_domain = catalog["sexes"][state["sex"]]
            identity = next(x for x in sex_domain["identities"] if x["id"] == state["identity"])
            hair = next(x for x in sex_domain["hairs"] if x["hair_id"] == state["hair"])
            wardrobe = state["wardrobe"]
            family = next(x for x in sex_domain["families"] if x["family_id"] == wardrobe["family_id"])
            group = next(x for x in family["groups"] if x["group_id"] == wardrobe["group_id"])
            asset_ids = list(wardrobe["slot_choices"].values()) + wardrobe["optional_asset_ids"]
            asset_ids += [x["asset_id"] if isinstance(x, dict) else x for x in group.get("required_assets", [])]
            asset_ids += group.get("lock_required_asset_ids", [])
            if wardrobe.get("shared_shoe_id"):
                asset_ids.append(wardrobe["shared_shoe_id"])
            resolved_assets = [{k: assets[a][k] for k in ("asset_id", "label", "slot", "mesh_paths") if k in assets[a]} for a in dict.fromkeys(asset_ids)]
            action = next(x for x in catalog["actions"] if x["id"] == state["action"])
            variant = next(x for x in action["variants"] if x["sex"] == state["sex"])
            site = sites[state["site"]]
            site = {k: copy.deepcopy(site[k]) for k in ("site_id", "name", "map", "position", "yaw", "appearance_config_id", "source_mode") if k in site}
            binding = copy.deepcopy(request["camera_binding"])
            binding["plan_path"] = portable_path(binding["plan_path"])
            resolution = profile["resolution"][state["aspect"]]
            jobs.append({
                "job_id": job_id, "split": split, "node_id": node,
                "original_node_id": request.get("original_node_id"), "content_id": request.get("content_id"),
                "state": state, "site": site, "camera_binding": binding,
                "appearance": {"identity": {"character_id": state["identity"], "skeleton": identity["skeleton"], "meshes": identity["meshes"]},
                               "hair": {"hair_id": state["hair"], "fit": hair["fit"], "color": state["hair_color"]},
                               "wardrobe_assets": resolved_assets},
                "motion": {"action_id": state["action"], "sex": state["sex"], "animation": variant["production10"]["asset"],
                           "fps": fps, "frames": frames, "play_rate": 1.0, "start_frame": 0},
                "width": resolution["width"], "height": resolution["height"], "fps": fps, "frames": frames,
                "paths": {"frames": f"jobs/{job_id}/frames", "video": f"jobs/{job_id}/video.mp4", "receipt": f"jobs/{job_id}/media_receipt.json"},
                "status": "planned_not_rendered",
            })
    all_ids = {x["job_id"] for x in jobs}
    if requested and requested - all_ids:
        raise ValueError(f"Unknown job IDs: {sorted(requested - all_ids)}")
    pilot = [next(j for j in jobs if j["job_id"] == f"train_node_{n:06d}") for n in PILOT_NODES]
    selected = [x for i, x in enumerate(jobs) if i % args.shard_count == args.shard_index and (requested is None or x["job_id"] in requested)]
    if args.limit:
        selected = selected[:args.limit]
    common = {"schema": "dataset_render_jobs_v11_v1", "path_base": "workspace", "output_path_base": "run_root",
              "profile": profile, "sources": [{"path": portable_path(p), "sha256": sha256(p)} for p in source_paths],
              "offline_only": True, "state_policy": "exact copy of adopted render_requests state"}
    out.mkdir(parents=True, exist_ok=True)
    for name, entries in (("main_jobs.json", selected), ("pilot_jobs.json", pilot)):
        (out / name).write_text(json.dumps({**common, "job_count": len(entries), "jobs": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    note = """# v11 本地小样选择

12个任务全部来自现有train节点；没有新增或修改state。

- 0 → 1：女横屏，Synthwave_city，相机单轴变更；0 → 5：服装单轴变更；5 → 18：身份单轴变更；0 → 2：动作单轴变更。
- 967 → 978、967 → 979：男横屏，Evening_Highway，固定front_full，分别只改发色/发型。
- 3775 → 3792：女竖屏，Synthwave_city，固定front_full，只改发型。
- 4040 → 4058：男竖屏，RedDesertPack，移动orbit_120，只改发色。

建议执行顺序沿pilot_jobs数组顺序；分开记录同场景角色切换与跨场景加载时间。
以上静止指固定镜头，角色仍使用原有10秒动作，不新增静止动作。
正式分片作用于main_jobs；pilot固定12节点，方便不同机器复验。
状态为离线计划，资产可加载、画面和颜色需实际渲染后验收。
"""
    (out / "PILOT_SELECTION.md").write_text(note, encoding="utf-8")
    print(json.dumps({"main_jobs": len(selected), "pilot_jobs": len(pilot), "out": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
