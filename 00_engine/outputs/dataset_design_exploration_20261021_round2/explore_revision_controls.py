"""Existing-node revision and algebra controls; no extra renders or training."""
from pathlib import Path
from collections import defaultdict, Counter
import json

HERE = Path(__file__).resolve().parent


def main():
    gp = HERE/"graph/motif_a7_f5_n3000_s20261021_test_uq1_ab3_graph.json"
    g = json.loads(gp.read_text(encoding="utf-8"))
    nodes = g["nodes"]
    edges = {(e["source_index"], e["target_index"]): e["axis"] for e in g["edges"]}
    adj = defaultdict(list)
    for (a, b), axis in edges.items():
        adj[a].append((b, axis))
    counts = Counter()
    examples = defaultdict(list)
    seen_diamonds = set()
    for a, nexts in adj.items():
        for b, axis in nexts:
            if edges.get((b, a)) == axis:
                counts["directed_revert_chains"] += 1
                if len(examples["revert"]) < 28:
                    examples["revert"].append({"nodes": [a, b, a], "parents": [None, 0, 1],
                                               "axes": [axis, axis], "target_equals_root": True})
            for c, axis2 in adj[b]:
                if axis2 == axis and c not in (a, b):
                    counts["same_axis_revision_chains"] += 1
                    counts["revision_axis_" + axis] += 1
                    if len(examples["revision"]) < 28:
                        examples["revision"].append({"nodes": [a, b, c], "parents": [None, 0, 1],
                                                    "axes": [axis, axis], "all_states_distinct": True})
        for b, x in nexts:
            for c, y in nexts:
                if x >= y or b == c:
                    continue
                for d, z in adj[b]:
                    if z != y or edges.get((c, d)) != x or len({a,b,c,d}) != 4:
                        continue
                    key = (a, min(b,c), max(b,c), d)
                    if key in seen_diamonds:
                        continue
                    seen_diamonds.add(key)
                    counts["commuting_two_edit_pairs"] += 1
                    if len(examples["commuting"]) < 28:
                        examples["commuting"].append({
                            "path_a": [a,b,d], "path_b": [a,c,d], "axes_a": [x,y], "axes_b": [y,x],
                            "same_root_and_target": True, "all_four_atomic_edges_registered": True})
    counts["unique_four_state_squares"] = len({frozenset(d) for d in seen_diamonds})
    assert counts["commuting_two_edit_pairs"] == 4 * counts["unique_four_state_squares"]
    for e in examples["revision"] + examples["revert"]:
        for t in (1, 2):
            a, b = nodes[e["nodes"][t-1]]["state"], nodes[e["nodes"][t]]["state"]
            assert [k for k in a if a[k] != b[k]] == [e["axes"][t-1]]
    out = {
        "status": "existing_graph_symbolic_controls_not_media_or_model_validation",
        "source_graph": str(gp),
        "counts": dict(counts), "examples": dict(examples),
        "sampling_note": "Examples are deterministic first examples for schema illustration, not a representative evaluation sample.",
        "interpretation": {
            "revision": "Two actual changes of one attribute; allowed by user. Excluded only by the exploration's >=2-axis heuristic.",
            "revert": "Latest-source two-edit chain returns to root; not a historical-source fork. Reuse root target media, do not count a new unique video.",
            "commuting": "Independent compatible setters can lead to same target in either order. Both are distinct instruction sequences but share supervision content.",
            "future_validation": "Rendered path independence assumes state/reset/time determinism. Real generated videos can accumulate different errors.",
            "scope": "Diagnostic or controlled subset, not a license to inflate main counts by cycles."
        }
    }
    (HERE/"revision_control_candidates.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(out["counts"]))


if __name__ == "__main__":
    main()
