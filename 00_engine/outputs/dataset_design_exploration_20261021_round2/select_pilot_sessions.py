"""Small, reviewable candidate pilot from existing graphs; no rendering."""
from pathlib import Path
from collections import Counter
import json

HERE = Path(__file__).resolve().parent


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def main():
    shots = {(r["action"], r["camera"], r["aspect"]): r for r in read(HERE/"observability/camera_observability.json")["shots"]}
    chosen, media, coverage = [], {}, set()
    rejection_counts = Counter()
    for split in ("train", "test"):
        prefix = f"motif_a7_f5_n3000_s20261021_{split}_uq1_ab3"
        graph = read(HERE/"graph"/(prefix+"_graph.json"))
        nodes = graph["nodes"]
        sessions = [json.loads(s) for s in (HERE/"graph"/(prefix+"_sessions.jsonl")).read_text(encoding="utf-8").splitlines()]
        candidates = []
        for s in sessions:
            forks = [i for i, p in enumerate(s["parent_occurrence_indices_gt"]) if i and p != i-1]
            flags = []
            if forks and forks[0] < 3:
                flags.append("only_one_nonlatest_slot")
            features = {("axis", a) for a in s["edge_axes"]}
            features.add(("length", len(s["edge_axes"])))
            features.add(("split", split))
            for t, axis in enumerate(s["edge_axes"], 1):
                source = nodes[s["node_indices"][s["parent_occurrence_indices_gt"][t]]]
                a = source["state"]
                probe = shots[(a["action"], a["camera"], a["aspect"])]
                if axis == "hair" and a["hair_color"] == "original":
                    flags.append("shape_original_color_coupling")
                if axis == "garment_slot" and source["family"].startswith("male") and probe["flags"]["lower_proxy_never_intersects_sparse_samples"]:
                    flags.append("pants_proxy_out_of_frame")
                if axis == "identity" and probe["identity_proxy_threshold_sweep"]["64"] == 0:
                    flags.append("weak_face_proxy")
                features.update((("site", a["site"]), ("camera", a["camera"]), ("action", a["action"])))
            if flags:
                rejection_counts.update(set(flags))
                continue
            if forks:
                features.add(("source_depth", s["parent_occurrence_indices_gt"][forks[0]]))
                features.add(("fork_position", forks[0]))
            candidates.append((s, bool(forks), features))
        used = set()
        for want_fork in (True, True, False, False, False, False):
            pool = [row for row in candidates if row[1] == want_fork and row[0]["session_id"] not in used]
            def score(row):
                novelty = row[2] - coverage
                return sum(6 if k == "axis" else 3 if k in ("source_depth", "fork_position") else 1 for k,v in novelty)
            row = max(pool, key=lambda r: (score(r), r[0]["session_id"]))
            s, fork, features = row
            used.add(s["session_id"])
            coverage.update(features)
            chosen.append({
                "split": split, "session_id": s["session_id"],
                "node_ids": [nodes[i]["node_id"] for i in s["node_indices"]],
                "parent_occurrence_indices_gt": s["parent_occurrence_indices_gt"],
                "edge_axes": s["edge_axes"], "fork": fork,
                "status": "structurally_checked_proxy_prioritized_not_visual_accepted"
            })
            for i in s["node_indices"]:
                n = nodes[i]
                media[n["node_id"]] = {"node_id": n["node_id"], "split": split, "state": n["state"], "family": n["family"]}
    axes = Counter(a for s in chosen for a in s["edge_axes"])
    assert len(chosen) == 12 and sum(s["fork"] for s in chosen) == 4
    assert len(axes) == 7
    payload = {
        "status": "proposal_not_submitted_not_frozen",
        "sessions": chosen, "unique_main_nodes": list(media.values()),
        "summary": {"sessions": 12, "linear": 8, "fork": 4, "unique_main_videos": len(media), "edit_axes": dict(axes),
                    "full_10s_30fps_frame_scenario": len(media)*300},
        "proxy_filter_counts_over_candidate_sessions": dict(rejection_counts),
        "scope": "Small functional pilot; not representative benchmark nor all asset/scene acceptance.",
        "before_render": ["Decide motion camera-policy contract", "Resolve formal slot configurations", "Build reference demand from these actual edges", "Confirm media format and scene snapshots"],
        "note": "Reference media not counted here. No model calls, UE calls or rendering."
    }
    (HERE/"pilot_session_proposal.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload["summary"]))


if __name__ == "__main__":
    main()
