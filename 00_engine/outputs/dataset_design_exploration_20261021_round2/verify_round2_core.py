"""Independent bounded verifier for the stable seven-axis five-family candidate."""
from pathlib import Path
from collections import Counter
import hashlib
import json

HERE = Path(__file__).resolve().parent


def canonical(state):
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


def main():
    evidence = {}
    states_by_split = {}
    sites = {}
    for split, expected_nodes, expected_sessions in (("train", 2500, 12000), ("test", 500, 3000)):
        prefix = f"motif_a7_f5_n3000_s20261021_{split}_uq1_ab3"
        gp = HERE/"graph"/(prefix+"_graph.json")
        sp = HERE/"graph"/(prefix+"_sessions.jsonl")
        graph = json.loads(gp.read_text(encoding="utf-8-sig"))
        nodes = graph["nodes"]
        sessions = [json.loads(s) for s in sp.read_text(encoding="utf-8").splitlines()]
        states = [n["state"] for n in nodes]
        signatures = [canonical(s) for s in states]
        assert len(nodes) == expected_nodes
        assert len(sessions) == expected_sessions
        assert len(set(signatures)) == len(nodes)
        seen_structure, seen_nodes, edges = set(), set(), set()
        structure_types = Counter()
        fork_sources = Counter()
        axes = Counter()
        for state in states:
            assert state["hair"] != "none" or state["hair_color"] == "original"
        for n in nodes:
            parent = n["generation_parent_index"]
            if parent is not None:
                assert sum(n["state"][a] != states[parent][a] for a in n["state"]) == 1
        for s in sessions:
            ids, parents, edits = s["node_indices"], s["parent_occurrence_indices_gt"], s["edge_axes"]
            length = len(ids)-1
            assert 2 <= length <= 5
            assert len(parents) == len(ids) and len(edits) == length
            assert parents[0] is None
            assert len(set(ids)) == len(ids)
            assert len(set(edits)) >= 2
            structure = (tuple(ids), tuple(parents), tuple(edits))
            assert structure not in seen_structure
            seen_structure.add(structure)
            seen_nodes.update(ids)
            forks = 0
            for t, axis in enumerate(edits, start=1):
                assert 0 <= parents[t] < t
                source = states[ids[parents[t]]]
                target = states[ids[t]]
                assert [a for a in source if source[a] != target[a]] == [axis]
                expected = dict(source)
                expected[axis] = target[axis]
                assert expected == target
                axes[axis] += 1
                edges.add((ids[parents[t]], ids[t], axis))
                if parents[t] != t-1:
                    forks += 1
                    fork_sources["root" if parents[t] == 0 else "nonroot"] += 1
                    matches = []
                    for candidate in range(t):
                        counterfactual = dict(states[ids[candidate]])
                        counterfactual[axis] = target[axis]
                        if counterfactual == target:
                            matches.append(candidate)
                    assert matches == [parents[t]]
            assert forks <= 1
            structure_types[f"{'fork' if forks else 'linear'}_{length}"] += 1
        assert seen_nodes == set(range(len(nodes)))
        states_by_split[split] = set(signatures)
        sites[split] = {s["site"] for s in states}
        evidence[split] = {
            "nodes": len(nodes), "sessions": len(sessions), "unique_used_edges": len(edges),
            "all_nodes_used": True, "strict_unique_fork_source": True,
            "types": dict(structure_types), "fork_sources": dict(fork_sources),
            "axis_occurrences": dict(axes),
            "sources": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in (gp, sp)]
        }
    assert not states_by_split["train"] & states_by_split["test"]
    assert not sites["train"] & sites["test"]
    payload = {
        "status": "passed_scoped_structural_verification",
        "scope": "Stable seven-axis five-family candidate only; not every experiment in this run.",
        "not_checked": ["UE/renderability", "pixel observability", "final split representativeness", "cross-family transition coverage", "learned model performance"],
        "checks": evidence, "train_test_state_overlap": 0, "train_test_site_overlap": 0
    }
    (HERE/"core_verification.json").write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: {"nodes": v["nodes"], "sessions": v["sessions"], "unique_used_edges": v["unique_used_edges"]} for k,v in evidence.items()}))


if __name__ == "__main__":
    main()
