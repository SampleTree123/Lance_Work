"""Offline reference-demand projection. Reads JSON snapshots; never renders media.

Default: final main scene-holdout hybrid graphs + sessions. Timing and trajectories are catalog hints because
the topology graph is not a complete render configuration. No claim of UE legality.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def key_hash(value) -> str:
    return digest(stable_json(value).encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--prefix", default="main_scene_holdout_hybrid")
    parser.add_argument("--inventory-name", default="topology_inventory_landscape.json")
    parser.add_argument("--split-regime", choices=["capacity_only", "scene_holdout"], default="scene_holdout")
    parser.add_argument("--examples-per-kind", type=int, default=2)
    parser.add_argument("--confirmed-static-cameras", nargs="*", default=[],
                        help="Explicit planning override; do not infer static from camera names")
    args = parser.parse_args()
    root = args.task_root.resolve()
    out = root / "references"
    out.mkdir(parents=True, exist_ok=True)
    snapshots = []

    def read_snapshot(path, jsonl=False):
        path = path.resolve()
        raw = path.read_bytes()  # Exactly one content read for this run.
        snapshots.append({"path": str(path), "sha256": digest(raw), "bytes": len(raw),
                          "mtime_ns_at_read": path.stat().st_mtime_ns})
        text = raw.decode("utf-8-sig")
        return [json.loads(line) for line in text.splitlines() if line.strip()] if jsonl else json.loads(text)

    inventory = read_snapshot(root / "graph" / args.inventory_name)
    catalog_path = root.parents[0] / "pair_scene_review_20261019_v1" / "site_review_catalog_v1.json"
    catalog = read_snapshot(catalog_path) if catalog_path.exists() else {"actions": [], "shots": []}
    sexes = {row["id"]: row["sex"] for row in inventory["identities"]}
    clocks = {(row["motion_id"], row["sex"]): row.get("clock", {}) for row in catalog["actions"]}
    trajectories = {(row["motion_id"], row["sex"], row["camera_id"], row["orientation"]):
                    row.get("trajectory_sha256") for row in catalog["shots"]}
    manifest = []
    summaries = {}
    global_keys = defaultdict(set)
    global_payloads = {}
    global_upper_payloads = {}
    varying_axes = set()
    examples = Counter()
    static_overrides = set(args.confirmed_static_cameras)

    def timing_profile(state):
        clock = clocks.get((state["action"], sexes[state["identity"]]))
        # A catalog clock is a hint, NOT proof the graph requests its full window.
        return {"status": "graph_timing_not_specified", "catalog_clock_hint_sha256":
                key_hash(clock) if clock else None}

    def trajectory_profile(state):
        motion, sex = state["action"], sexes[state["identity"]]
        hint = trajectories.get((motion, sex, state["camera"], state["aspect"]))
        return {"motion": motion, "sex": sex, "trajectory_hint_sha256": hint,
                "status": "catalog_hint_not_complete_site_ground_follow_trajectory",
                "resolved_trajectory_sha256": None}

    def reference_for(source, target, axis):
        if axis == "identity":
            return "identity_image", {"identity": target["identity"], "view": "canonical_front",
                                      "appearance_scope": "identity_definition_pending"}, {
                "carrier_policy": "target_identity_with_neutral_context",
                "ignore": ["hair", "outfit", "expression", "lighting", "scene"]}
        if axis == "action":
            sex = sexes[source["identity"]]
            condition = {"motion": target["action"], "sex": sex, "camera": source["camera"],
                         "aspect": source["aspect"], "timing_profile": timing_profile(target),
                         "trajectory_profile": trajectory_profile(target)}
            return "action_clip", condition, {
                "carrier_policy": "independent_neutral_reference_carrier_by_sex",
                "carrier_identity_id": None,
                "camera_binding": "source_camera_preset_with_target_motion_tracking_rule",
                "ignore": ["identity", "outfit", "body_shape", "expression", "scene", "lighting"]}
        if axis == "site":
            camera = source["camera"]
            if camera in static_overrides:
                kind, movement = "background_image", "explicit_static_planning_override"
            elif camera.startswith(("orbit_", "dolly_")):
                kind, movement = "background_clip", "moving_preset"
            else:
                kind, movement = "background_clip", "unresolved_follow_capable_conservative_clip"
            condition = {"site": target["site"], "camera": camera, "aspect": source["aspect"],
                         "camera_motion_status": movement,
                         "lighting_policy": "scene_owned_illumination_and_exposure",
                         "timing_profile": timing_profile(source),
                         "motion_and_trajectory": trajectory_profile(source)}
            return kind, condition, {"carrier_policy": "no_person_no_person_shadow_no_person_reflection",
                                     "camera_binding": "source_motion_dependent_path_in_target_site",
                                     "static_camera_rule": "image_if_confirmed_static_else_clip",
                                     "needs_final_trajectory_resolution": True}
        if axis in {"hair_color", "camera", "aspect"}:
            return None, {"text_axis": axis, "target_value": target[axis]}, {}
        raise ValueError(f"Unsupported varying axis {axis!r}; do not invent fixed-axis references")

    for split in ("train", "test"):
        graph = read_snapshot(root / "graph" / f"{args.prefix}_{split}_graph.json")
        sessions = read_snapshot(root / "graph" / f"{args.prefix}_{split}_sessions.jsonl", jsonl=True)
        nodes = graph["nodes"]
        varying_axes.update(edge["axis"] for edge in graph["edges"])
        all_edges = {(edge["source_index"], edge["target_index"], edge["axis"]) for edge in graph["edges"]}
        used = Counter()
        for session in sessions:
            indices = session["node_indices"]
            parents = session["parent_occurrence_indices_gt"]
            axes = session["edge_axes"]
            if len(parents) != len(indices) or len(axes) != len(indices) - 1:
                raise ValueError("Malformed session occurrence arrays")
            for occurrence in range(1, len(indices)):
                parent = parents[occurrence]
                if parent is None or not 0 <= parent < occurrence:
                    raise ValueError("Source occurrence must precede target occurrence")
                edge = (indices[parent], indices[occurrence], axes[occurrence - 1])
                if edge not in all_edges:
                    raise ValueError(f"Session edge absent from graph: {edge}")
                used[edge] += 1

        def project(edge_set, add_examples=False, collect_upper=False):
            refs = {}
            axes = Counter()
            text_axes = Counter()
            for edge in sorted(edge_set):
                si, ti, axis = edge
                source, target = nodes[si]["state"], nodes[ti]["state"]
                changed = [k for k in source if source[k] != target.get(k)]
                if changed != [axis]:
                    raise ValueError(f"Projection is not a one-axis edge: {edge}: {changed}")
                axes[axis] += 1
                kind, condition, policy = reference_for(source, target, axis)
                if kind is None:
                    text_axes[axis] += 1
                    continue
                payload = {"kind": kind, "condition": condition, "carrier_policy_version": "proposal_v1"}
                semantic_key = key_hash(payload)
                if semantic_key not in refs:
                    refs[semantic_key] = payload
                    if collect_upper:
                        global_upper_payloads[semantic_key] = payload
                    if add_examples:
                        global_keys[semantic_key].add(split)
                        global_payloads[semantic_key] = payload
                        if examples[(split, kind)] < args.examples_per_kind:
                            examples[(split, kind)] += 1
                            manifest.append({"ref_id": f"ref_{split}_{semantic_key[:16]}", "split": split,
                                             "master_library_ref_id": f"ref_{semantic_key[:16]}",
                                             "semantic_key_sha256": semantic_key, **payload, **policy,
                                             "example_source_node_id": nodes[si]["node_id"],
                                             "example_target_node_id": nodes[ti]["node_id"],
                                             "requested_edge_axis": axis, "media_path": None,
                                             "media_sha256": None, "render_status": "not_rendered",
                                             "source_fields_are_private_planning_metadata": True})
            counts = Counter(row["kind"] for row in refs.values())
            background_status = Counter(row["condition"]["camera_motion_status"] for row in refs.values()
                                        if row["kind"].startswith("background_"))
            return {"unique_reference_requests": len(refs), "by_kind": dict(counts),
                    "background_requests_by_camera_motion_status": dict(background_status),
                    "unique_edges_by_axis": dict(axes), "text_only_edges_by_axis": dict(text_axes),
                    "reference_keyset_sha256": key_hash(sorted(refs)),
                    "additional_reference_clips": counts["action_clip"] + counts["background_clip"],
                    "additional_reference_images": counts["identity_image"] + counts["background_image"]}

        actual = project(used, add_examples=True)
        graph_ceiling = project(all_edges, collect_upper=True)
        summaries[split] = {"main_node_video_plan_count": len(nodes), "session_count": len(sessions),
                            "node_value_counts": {field: len({node["state"][field] for node in nodes})
                                                  for field in nodes[0]["state"]},
                            "identity_edges_cross_sex": sum(sexes[nodes[si]["state"]["identity"]] != sexes[nodes[ti]["state"]["identity"]]
                                                            for si, ti, axis in used if axis == "identity"),
                            "edit_occurrences": sum(used.values()), "unique_used_edges": len(used),
                            "all_graph_edges": len(all_edges),
                            "session_edge_occurrences_by_axis": dict(Counter({axis: sum(n for (_, _, a), n in used.items() if a == axis) for axis in graph["axes"]})),
                            "demand_derived_from_actual_session_edges": actual,
                            "upper_bound_relative_to_these_sessions_from_all_graph_edges": graph_ceiling}
    # Metadata-only change detection avoids reading graph/session content a second time.
    for row in snapshots:
        stat = Path(row["path"]).stat()
        row["metadata_unchanged_after_projection"] = stat.st_size == row["bytes"] and stat.st_mtime_ns == row["mtime_ns_at_read"]
    main_count = sum(s["main_node_video_plan_count"] for s in summaries.values())
    union_counts = Counter(row["kind"] for row in global_payloads.values())
    upper_union_counts = Counter(row["kind"] for row in global_upper_payloads.values())
    shared_counts = Counter(global_payloads[k]["kind"] for k, splits in global_keys.items() if len(splits) > 1)
    union_clips = union_counts["action_clip"] + union_counts["background_clip"]
    union_images = union_counts["identity_image"] + union_counts["background_image"]
    summary = {
        "schema_status": "offline_projection_not_render_manifest", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_snapshot_policy": "Each input read once; SHA256 identifies exact bytes; end check uses size+mtime only; multiple files are not an atomic filesystem snapshot",
        "input_snapshots": snapshots, "graph_prefix": args.prefix,
        "split_regime": args.split_regime,
        "scope_is_partial_reference_demand_not_full_budget": True,
        "supported_axes": ["identity", "action", "site", "hair_color", "camera", "aspect"],
        "varying_axes_in_inputs": sorted(varying_axes),
        "six_state_fields": ["identity", "action", "site", "hair_color", "camera", "aspect"],
        "fixed_axes_not_projected": ["hair_style", "outfit", "expression", "independent_lighting"],
        "split_summaries": summaries,
        "main_node_video_plan_count_total": main_count,
        "main_3000_target_met_by_input_node_count": main_count == 3000,
        "additional_reference_clips_total_split_local": sum(s["demand_derived_from_actual_session_edges"]["additional_reference_clips"] for s in summaries.values()),
        "additional_reference_images_total_split_local": sum(s["demand_derived_from_actual_session_edges"]["additional_reference_images"] for s in summaries.values()),
        "master_library_union_demand": {"by_kind": dict(union_counts), "additional_reference_clips": union_clips,
                                        "additional_reference_images": union_images, "total_references": len(global_keys)},
        "master_library_union_upper_bound_from_all_graph_edges": {"by_kind": dict(upper_union_counts),
                           "additional_reference_clips": upper_union_counts["action_clip"] + upper_union_counts["background_clip"],
                           "additional_reference_images": upper_union_counts["identity_image"] + upper_union_counts["background_image"],
                           "total_references": len(global_upper_payloads)},
        "rendered_main_videos_by_this_script": 0, "rendered_reference_media_by_this_script": 0,
        "shared_semantic_keys_between_splits": sum(len(v) > 1 for v in global_keys.values()),
        "shared_semantic_keys_by_kind": dict(shared_counts),
        "cross_split_policy": ("Scene holdout: canonical identity photos and site-independent matched action refs may share a declared seen-identity neutral carrier; master library uses union keys. Site-specific background refs remain site-held-out. Carrier identity must be declared and not claimed unseen."
                               if args.split_regime == "scene_holdout" else
                               "Capacity baseline only: union counts are diagnostic; split-local counts do not imply semantic holdout or sharing permission"),
        "confirmed_static_camera_overrides": sorted(static_overrides),
        "background_camera_policy": "Only explicit static confirmation yields image; orbit/dolly or unresolved follow-capable cameras yield clip; key includes motion+trajectory hint",
        "timing_policy": "Graph has no timing profile; per-motion catalog clock hash is only a planning hint. New windows/rates need new keys",
        "upper_bound_scope": "All graph edges upper-bound used-session requests for this exact projection only; not a universal render/storage bound",
        "limitations": ["No UE/asset/media access or rendering", "Graph is an abstract projection, not complete render state",
                        "Catalog trajectory hashes do not resolve site ground-follow, carrier fitting or all current runtime corrections",
                        "No media counted as produced; null media paths only", "Counts conditional on one unresolved timing profile per motion/sex",
                        "Conservative background clips may become images after final trajectory confirms static; keys must then be regenerated",
                        "Independent reference carriers are roles only and require asset/split selection before rendering"]}
    (out / "demand_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "manifest_example.json").write_text(json.dumps({"schema_status": "illustrative_subset_of_demand_not_frozen", "input_snapshot_sha256s": {Path(r["path"]).name: r["sha256"] for r in snapshots}, "items": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"graph_prefix": args.prefix, "split_regime": args.split_regime, "main_node_video_plan_count": main_count,
                      "master_union_reference_clips": union_clips, "master_union_reference_images": union_images,
                      "split_local_reference_clips": summary["additional_reference_clips_total_split_local"],
                      "shared_semantic_keys": summary["shared_semantic_keys_between_splits"], "example_items": len(manifest),
                      "snapshot_metadata_stable": all(r["metadata_unchanged_after_projection"] for r in snapshots)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
