"""Separate configuration differences from visible edit evidence; offline only."""
from pathlib import Path
from collections import Counter, defaultdict
import json
import hashlib

HERE = Path(__file__).resolve().parent
RUN = HERE.parent


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def main():
    cameras = read(HERE / "camera_observability.json")
    shots = {(r["action"], r["camera"], r["aspect"]): r for r in cameras["shots"]}
    results = {}
    examples = defaultdict(list)
    for split in ("train", "test"):
        prefix = f"motif_a7_f5_n3000_s20261021_{split}_uq1_ab3"
        graphfile = RUN / "graph" / (prefix + "_graph.json")
        sessionsfile = RUN / "graph" / (prefix + "_sessions.jsonl")
        graph = read(graphfile)
        nodes = [n["state"] for n in graph["nodes"]]
        sessions = [json.loads(s) for s in sessionsfile.read_text(encoding="utf-8").splitlines()]
        counts = Counter()
        unique_edges = set()
        flags_per_edge = {}
        session_flags = Counter()
        collapsed = defaultdict(list)
        for i, state in enumerate(nodes):
            canonical = dict(state)
            if canonical["hair"] == "none":
                counts["no_hair_nodes"] += 1
                canonical["hair_color"] = "__inactive_without_hair__"
            collapsed[json.dumps(canonical, sort_keys=True)].append(i)
        alias_groups = [v for v in collapsed.values() if len(v) > 1]
        for session in sessions:
            present = set()
            ids = session["node_indices"]
            for occurrence, axis in enumerate(session["edge_axes"], start=1):
                source_i = ids[session["parent_occurrence_indices_gt"][occurrence]]
                target_i = ids[occurrence]
                a, b = nodes[source_i], nodes[target_i]
                edge = (source_i, target_i, axis)
                unique_edges.add(edge)
                probe = shots[(a["action"], a["camera"], a["aspect"])]
                flags = []
                if axis == "hair_color" and a["hair"] == "none":
                    flags.append("hair_color_without_hair")
                if axis == "hair" and a["hair_color"] == "original":
                    flags.append("hair_shape_with_asset_dependent_original_color")
                if axis == "garment_slot" and graph["nodes"][source_i]["family"].startswith("male"):
                    # Experimental male garment domain is pants, not all clothing.
                    if probe["flags"]["lower_proxy_never_intersects_sparse_samples"]:
                        flags.append("male_pants_edit_lower_proxy_absent")
                if axis == "identity" and probe["identity_proxy_threshold_sweep"]["64"] == 0:
                    flags.append("identity_edit_without_64px_front_head_proxy")
                if axis in ("hair", "hair_color") and probe["flags"]["head_box_never_intersects_sparse_samples"]:
                    flags.append("hair_edit_head_proxy_absent")
                counts["edit_occurrences"] += 1
                counts["axis_occurrences_" + axis] += 1
                for flag in flags:
                    counts["occurrences_" + flag] += 1
                    present.add(flag)
                    if len(examples[split + "_" + flag]) < 5:
                        examples[split + "_" + flag].append({
                            "session_id": session["session_id"], "target_occurrence": occurrence,
                            "source": a, "target": b, "proxy_shot_id": probe["shot_id"]})
                flags_per_edge[edge] = flags
            session_flags.update(present)
        edge_counts = Counter(flag for flags in flags_per_edge.values() for flag in flags)
        results[split] = {
            "nodes": len(nodes), "sessions": len(sessions), "unique_used_edges": len(unique_edges),
            "counts": dict(counts), "flagged_unique_edges": dict(edge_counts),
            "flagged_sessions": dict(session_flags),
            "inactive_hair_color_alias_groups": len(alias_groups),
            "inactive_hair_color_redundant_nodes": sum(len(v)-1 for v in alias_groups),
            "alias_examples": alias_groups[:10],
            "sources": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in (graphfile, sessionsfile)]
        }
    out = {
        "status": "configuration_and_sparse_geometry_diagnostic_not_pixel_acceptance",
        "interpretation": {
            "hair_color_without_hair": "Scalp-hair color has no active hair asset to affect. Exclude as an ordinary visible edit; canonicalize inactive state separately.",
            "hair_shape_with_asset_dependent_original_color": "Review candidate: original is not a fixed cross-asset color. Not proof every pair changes perceived color.",
            "male_pants_edit_lower_proxy_absent": "Sparse representative skeleton lower-body envelope out of frame; likely unobservable pants change, but not pixel or shadow proof.",
            "identity_edit_without_64px_front_head_proxy": "Reference-based face identity evidence may be weak. Identity can still change visible body/skin; not an invalid edge automatically."
        },
        "results": results, "examples": dict(examples)
    }
    (HERE / "semantic_visibility.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {x: v[x] for x in (
        "nodes", "sessions", "flagged_unique_edges", "flagged_sessions",
        "inactive_hair_color_alias_groups", "inactive_hair_color_redundant_nodes")}
        for k, v in results.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
