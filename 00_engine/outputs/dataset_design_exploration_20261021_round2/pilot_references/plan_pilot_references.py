"""Read-only projection of the 12-session proposal; never renders or submits jobs."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
OUTPUTS = RUN.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def unit(a):
    norm = math.sqrt(dot(a, a))
    return [x/norm for x in a] if norm > 1e-8 else [0, 0, 0]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def main():
    proposal_path = RUN/"pilot_session_proposal.json"
    appearance_path = RUN/"graph/appearance_catalog.json"
    geometry_path = OUTPUTS/"production_workflow_20261017_v1/camera_library/production10/geometry.json"
    proposal, appearance, geometry = map(read, (proposal_path, appearance_path, geometry_path))
    identities = {x["id"]: x for x in appearance["identities"]}
    nodes = {x["node_id"]: x for x in proposal["unique_main_nodes"]}
    shots = {(x["motion_id"], x["camera_id"], x["orientation"]): x for x in geometry["shots"]}
    actions = {x["motion_id"]: x for x in geometry["actions"]}
    garments, hairs = {}, defaultdict(list)
    for sex, families in appearance["families_by_sex"].items():
        for family in families:
            for group in family["groups"]:
                for slot, assets in group.get("slot_options", {}).items():
                    for asset in assets:
                        garments[asset["asset_id"]] = {**asset, "sex": sex, "family_id": family["family_id"], "group_id": group["group_id"]}
    for sex, rows in appearance["hairs_by_sex"].items():
        for row in rows:
            hairs[row["hair_id"]].append({"fit_sex": sex, "fit": row.get("fit"), "reviewed_sexes": row.get("reviewed_sexes")})
    media, requests, unresolved = {}, [], []
    full_views = ["front", "anatomical_right", "back", "anatomical_left"]

    def add(role, kind, key, **details):
        rid = role+"_"+digest(key)
        if rid not in media:
            media[rid] = {"reference_id": rid, "role": role, "media_type": kind, "dedup_key": key,
                          "media_path": None, "status": "planned_not_rendered", **details}
        return rid

    def trajectory(state):
        row = shots.get((state["action"], state["camera"], state["aspect"]))
        if row is None:
            return None
        return {"shot_id": row["shot_id"], "trajectory_sha256": row["trajectory_sha256"],
                "planner_representative_sex": row["sex"], "clock": row["clock"],
                "motion_id": row["motion_id"], "camera_id": row["camera_id"],
                "aspect": row["orientation"], "width": row["width"], "height": row["height"],
                "binding_status": "formal_planner_trajectory_not_runtime_verified_for_all_carriers"}

    def garment_views(state):
        shot = shots.get((state["action"], state["camera"], state["aspect"]))
        action = actions.get(state["action"])
        if not shot or not action:
            return None, {"status": "unresolved_missing_camera_or_motion"}
        counts = Counter()
        for sample in shot["samples"]:
            body = min(action["samples"], key=lambda x: abs(x["t"]-sample["t"]))
            bones = body["bones"]
            right = unit(sub(bones["upperarm_r"], bones["upperarm_l"]))
            up = unit(sub(bones["neck_01"], bones["pelvis"]))
            front = unit(cross(right, up))
            towards = unit(sub(sample["position"], bones["pelvis"]))
            angle = math.degrees(math.atan2(dot(towards, right), dot(towards, front))) % 360
            counts[full_views[int((angle+45)//90) % 4]] += 1
        # A union of nearest four-view bins over sparse samples. No extra views for padding.
        selected = [v for v in full_views if counts[v]]
        return selected, {"status": "proposed_sparse_torso_heading_selection_not_pixel_verified",
                          "sample_counts_by_nearest_view": dict(counts),
                          "rule": "union_of_nearest_90_degree_bins_over_0.5s_camera_body_samples",
                          "limitations": ["torso proxy is not garment surface visibility", "sparse samples may miss brief turns", "anatomical left/right convention must be checked when gallery is made"]}

    for session in proposal["sessions"]:
        for turn, axis in enumerate(session["edge_axes"], 1):
            parent = session["parent_occurrence_indices_gt"][turn]
            src = nodes[session["node_ids"][parent]]["state"]
            dst = nodes[session["node_ids"][turn]]["state"]
            changed = [k for k in src if src[k] != dst[k]]
            assert changed == [axis], (session["session_id"], turn, changed, axis)
            sex = identities[src["identity"]]["sex"]
            req = {"request_id": session["session_id"]+f":t{turn}", "split": session["split"],
                   "session_id": session["session_id"], "turn": turn, "source_occurrence": parent,
                   "source_node": session["node_ids"][parent], "target_node": session["node_ids"][turn],
                   "axis": axis, "target_value": dst[axis], "required_media": [], "alternatives": {}}
            if axis == "identity":
                req["required_media"] = [add("identity_front", "image", {"identity": dst[axis], "view": "front", "carrier_policy": "target_identity_independent_studio"},
                    carrier_identity=dst[axis], source_is_gt=False, unresolved=["studio camera/pose and neutral appearance selection", "whether identity edit includes body shape requires task contract"]) ]
            elif axis == "hair":
                if dst[axis] == "none":
                    req["text_only"] = "remove hair; no positive hair reference"
                elif dst[axis] not in hairs:
                    unresolved.append({"request_id": req["request_id"], "reason": "hair_asset_missing", "value": dst[axis]})
                else:
                    for view in ("front", "back"):
                        req["required_media"].append(add("hair_gallery", "image", {"hair_id": dst[axis], "view": view, "carrier_policy": "independent_carrier_v1"},
                            carrier_identity=None, source_is_gt=False, available_fit_sexes=[x["fit_sex"] for x in hairs[dst[axis]]],
                            unresolved=["independent carrier identity and neutral hair color", "shared hair_id appearance vs sex-fit reference contract"]))
            elif axis == "garment_slot":
                asset = garments.get(dst[axis])
                if not asset:
                    unresolved.append({"request_id": req["request_id"], "reason": "slot_asset_missing", "value": dst[axis]})
                else:
                    gallery = {}
                    for view in full_views:
                        gallery[view] = add("garment_gallery", "image", {"asset_id": dst[axis], "view": view, "carrier_policy": "independent_carrier_v1"},
                            asset_slot=asset["slot"], asset_mesh_paths=asset["mesh_paths"], asset_family_id=asset["family_id"],
                            carrier_identity=None, source_is_gt=False,
                            unresolved=["formal slot assembly and compatible independent carrier", "neutral support garments and shoes"]) 
                    selected, evidence = garment_views(src)
                    req["complete_shared_gallery"] = gallery
                    req["selected_reference_views"] = selected
                    req["view_selection_evidence"] = evidence
                    req["resolved_asset_slot"] = asset["slot"]
                    if selected:
                        req["required_media"] = [gallery[v] for v in selected]
                    else:
                        unresolved.append({"request_id": req["request_id"], "reason": "garment_view_selection_unresolved"})
            elif axis == "action":
                motion = dst[axis]
                timing = {"profile": "production10", "duration_seconds": 10, "fps": 30, "frames": 300}
                req["alternatives"]["canonical_semantic"] = [add("action_canonical", "clip", {"motion": motion, "fit_sex": sex, "view": "canonical_studio", "timing_profile": "production10"},
                    carrier_identity=None, camera_plan=None, timing=timing, source_is_gt=False,
                    supervision="semantic_motion; same_timing_family_does_not_imply_pixel_or_spatial_alignment",
                    unresolved=["independent carrier and canonical camera contract"])]
                src_traj = trajectory(src)
                target_traj = trajectory({**src, "action": motion})
                req["alternatives"]["matched_view_timing"] = [add("action_matched", "clip", {"motion": motion, "fit_sex": sex, "camera": src["camera"], "aspect": src["aspect"], "timing_profile": "production10", "camera_binding_policy": "unresolved"},
                    carrier_identity=None, timing=timing, source_is_gt=False,
                    source_trajectory_candidate=src_traj, target_motion_tracking_candidate=target_traj,
                    unresolved=["choose source frozen trajectory vs target-motion-following same camera preset", "independent carrier; representative planner sex is not a verified fit"]) ]
                if not src_traj or not target_traj:
                    unresolved.append({"request_id": req["request_id"], "reason": "matched_action_trajectory_candidate_missing"})
            elif axis == "site":
                req["alternatives"]["semantic_image"] = [add("site_semantic", "image", {"site": dst[axis], "view": "canonical_scene_semantic"},
                    source_is_gt=False, contains_person=False, camera_plan=None,
                    supervision="scene_identity_semantics_not_exact_motion_plate", unresolved=["canonical scene viewpoint and snapshot selection"]) ]
                tr = trajectory(src)
                if tr:
                    req["alternatives"]["exact_trajectory_clip"] = [add("site_exact", "clip", {"site": dst[axis], "source_motion": src["action"], "camera": src["camera"], "aspect": src["aspect"], "trajectory_sha256": tr["trajectory_sha256"], "timing_profile": "production10"},
                        contains_person=False, source_is_gt=False, trajectory=tr,
                        supervision="target_site_conditioned_strong_background_plate",
                        unresolved=["scene anchor/placement and scene-owned exposure snapshot", "reuse actor-derived trajectory after removing actor; no subject tracking re-solve", "runtime plate equivalence and carrier-space transform"]) ]
                else:
                    unresolved.append({"request_id": req["request_id"], "reason": "background_trajectory_missing"})
            elif axis in ("camera", "hair_color"):
                req["text_only"] = "camera preset semantic axis" if axis == "camera" else "hair color attribute; visibility not guaranteed"
            else:
                unresolved.append({"request_id": req["request_id"], "reason": "unexpected_axis", "axis": axis})
            requests.append(req)

    base = {i for q in requests for i in q["required_media"]}
    alternatives = {name: {i for q in requests for i in q["alternatives"].get(name, [])}
                    for name in ("canonical_semantic", "matched_view_timing", "semantic_image", "exact_trajectory_clip")}
    galleries = {i for q in requests for i in q.get("complete_shared_gallery", {}).values()}
    scenarios = []
    for act in ("canonical_semantic", "matched_view_timing"):
        for bg in ("semantic_image", "exact_trajectory_clip"):
            ids = base | alternatives[act] | alternatives[bg]
            scenarios.append({"action_scheme": act, "site_scheme": bg, "unique_requested_media": len(ids),
                "images": sum(media[i]["media_type"] == "image" for i in ids),
                "clips": sum(media[i]["media_type"] == "clip" for i in ids),
                "clip_frames_at_10s_30fps_scenario": 300*sum(media[i]["media_type"] == "clip" for i in ids),
                "reference_ids": sorted(ids), "status": "demand_projection_not_render_jobs"})
    result = {
        "schema": "pilot_reference_manifest.v1.proposal", "date": "2026-10-21", "status": "offline_demand_only_not_visual_accepted",
        "input_pins": [pin(p) for p in (proposal_path, appearance_path, geometry_path)],
        "main_media": {"sessions": len(proposal["sessions"]), "unique_videos": len(nodes), "separate_from_additional_references": True},
        "shared_library_scope": {
            "identity": {"catalog_identities": len(identities), "front_images_per_identity": 1, "full_library_front_images": len(identities)},
            "hair": {"unique_hair_ids": len(hairs), "sex_fit_entries": sum(map(len, hairs.values())), "views": ["front", "back"],
                "full_library_images_single_carrier_per_hair_id": 2*len(hairs), "full_library_images_separate_sex_fit": 2*sum(map(len, hairs.values())), "carrier_contract": "unresolved_alternative_counts_not_both_required"},
            "garment_slot": {"catalog_slot_option_asset_ids": len(garments), "views": full_views,
                "full_approved_atomic_asset_count": None, "reason": "catalog options are candidate assets; not all formally verified atomic replacements", "pilot_complete_target_asset_gallery_ids": sorted(galleries)},
            "action": {"selected_semantic_motion_families": 25, "canonical_single_carrier_clips": 25, "canonical_two_sex_fit_clips": 50,
                "full_matched_library_count": None, "reason": "trajectory policy/carrier/timing choice not fixed; request projection below"},
            "site": {"selected_sites": 21, "canonical_one_image_per_site": 21, "full_exact_library_count": None, "reason": "exact references depend on action-derived trajectory and scene placement"}},
        "pilot_demand": {"edit_requests": len(requests), "axis_counts": dict(Counter(q["axis"] for q in requests)),
            "fixed_identity_hair_garment_requested_images": len(base), "pilot_complete_garment_gallery_images": len(galleries),
            "counts_by_role_in_manifest_including_unselected_gallery_views": dict(Counter(m["role"] for m in media.values())),
            "alternative_demand_counts": {k: len(v) for k, v in alternatives.items()}, "scenarios": scenarios,
            "do_not_sum_mutually_exclusive_scenarios": True, "counts_are_union_across_train_test": True},
        "contracts": {"all_media_paths_null": True, "independent_reference_carrier_not_user_target_person_for_hair_garment_action": True,
            "garment_request_uses_selected_views_only": True, "hair_front_back_both_requested_in_this_pilot": True,
            "scene_exact_trajectory_role": "strong_target_conditioned_reference; semantic_image is a different input task",
            "camera_axis": "one semantic preset may jointly change framing and trajectory",
            "color_camera_reference_media": "none in current pilot plan", "production_jobs_created": False},
        "unresolved_request_lookups": unresolved, "requests": requests, "media": list(media.values()),
        "limitations": ["Each media record lists unresolved production choices; zero missing lookup records does not mean executable production configuration", "Do not reuse first-round 1332 reference clips; this is a separate 12-session projection", "Sparse geometry validates planning data only, not clothing visibility or finished pixels", "All gallery carriers, formal slot configurations and scene/camera contracts remain to be fixed"]}
    out = HERE/"pilot_reference_manifest.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "main": result["main_media"], "demand": {k:v for k,v in result["pilot_demand"].items() if k != "scenarios"}, "scenario_counts": [{k:v for k,v in s.items() if k != "reference_ids"} for s in scenarios], "unresolved_lookup_count": len(unresolved)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
