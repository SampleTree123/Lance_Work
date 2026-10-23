"""Offline order-only cost comparison. Does not submit any render jobs."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import random

HERE = Path(__file__).resolve().parent
AXES = ("site", "identity", "action", "camera", "garment_slot", "hair", "hair_color")


def switches(jobs):
    return {axis: 1 + sum(a["state"][axis] != b["state"][axis]
                         for a, b in zip(jobs, jobs[1:])) for axis in AXES}


def ordered(jobs, axes):
    return sorted(jobs, key=lambda j: tuple(j["state"][a] for a in axes) + (j["node_id"],))


def main():
    jobs = []
    sources = []
    for split in ("train", "test"):
        p = HERE/"graph"/f"motif_a7_f5_n3000_s20261021_{split}_uq1_ab3_graph.json"
        graph = json.loads(p.read_text(encoding="utf-8"))
        jobs.extend({"node_id": n["node_id"], "split": split, "state": n["state"]} for n in graph["nodes"])
        sources.append({"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    assert len({j["node_id"] for j in jobs}) == len(jobs) == 3000
    shuffled = list(jobs)
    random.Random(20261021).shuffle(shuffled)
    orders = {
        "graph_growth_order": jobs,
        "seeded_random_order": shuffled,
        "scene_identity_first": ordered(jobs, ("site", "identity", "garment_slot", "hair", "hair_color", "action", "camera")),
        "scene_motion_first": ordered(jobs, ("site", "action", "camera", "identity", "garment_slot", "hair", "hair_color")),
        "identity_scene_first": ordered(jobs, ("identity", "site", "garment_slot", "hair", "hair_color", "action", "camera"))
    }
    counts = {name: switches(sequence) for name, sequence in orders.items()}
    result = {
        "status": "offline_order_only_simulation_no_runtime_benchmark",
        "sources": sources, "jobs": len(jobs),
        "definitions": "Each count is first setup + consecutive changes of that state key; not actual cache misses, additive time or asset loads.",
        "counts": counts,
        "unique_values": {a: len({j["state"][a] for j in jobs}) for a in AXES},
        "quality_invariants": [
            "All orderings contain exactly the same 3000 node jobs and no repeats.",
            "Ordering is not model training order; sessions remain chronological.",
            "Render state and clocks must reset per job; seed tied to node/profile rather than queue index.",
            "Do not remove per-shot warmup based on ordering alone.",
            "No reference jobs included: current reference planner is tied to first-round five-axis graph.",
            "Scene snapshots and source assets unchanged."
        ]
    }
    for name, order in orders.items():
        assert {j["node_id"] for j in order} == {j["node_id"] for j in jobs}
    (HERE/"render_order_comparison.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    proposal = {
        "status": "candidate_order_not_render_manifest",
        "order_policy": "scene_identity_first",
        "missing_to_submit": ["resolved slots/assets", "scene snapshot", "final video parameters", "reference plan", "render profile", "visual edge eligibility"],
        "node_order": [j["node_id"] for j in orders["scene_identity_first"]]
    }
    (HERE/"candidate_render_order.json").write_text(json.dumps(proposal, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result["counts"]))


if __name__ == "__main__":
    main()
