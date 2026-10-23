"""Bounded delivery checks for the offline study, not production validation."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import re

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sessions(prefix):
    result = []
    splits = {}
    sexes = {r["id"]: r["sex"] for r in read(RUN / "inventory/normalized_inventory.json")["identities"]}
    for split, nodes_n, sessions_n in (("train", 2500, 12000), ("test", 500, 3000)):
        graph = read(RUN / f"graph/{prefix}hybrid_{split}_graph.json")
        nodes = graph["nodes"]
        assert len(nodes) == nodes_n
        states = [n["state"] for n in nodes]
        splits[split] = states
        edge_keys = {(e["source_index"], e["target_index"]): e["axis"] for e in graph["edges"]}
        for (a, b), axis in edge_keys.items():
            changed = [k for k in states[a] if states[a][k] != states[b][k]]
            assert changed == [axis]
            assert sexes[states[a]["identity"]] == sexes[states[b]["identity"]]
        rows = [json.loads(line) for line in
                (RUN / f"graph/{prefix}hybrid_{split}_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(rows) == len({r["session_id"] for r in rows}) == sessions_n
        quota, source_depth, used = Counter(), Counter(), set()
        for row in rows:
            occ, parents, axes = row["node_indices"], row["parent_occurrence_indices_gt"], row["edge_axes"]
            k = len(occ) - 1
            assert 2 <= k <= 5 and len(set(occ)) == len(occ)
            assert len(set(axes)) >= 2
            assert len(parents) == len(occ)
            branch = []
            used.update(occ)
            for t in range(1, k + 1):
                p = parents[t]
                assert isinstance(p, int) and 0 <= p < t
                a, b = occ[p], occ[t]
                axis = edge_keys[(a, b)]
                assert axes[t - 1] == axis
                if p != t - 1:
                    branch.append(t)
                    assert t < k
                    assert any(states[a][key] != states[occ[t - 1]][key]
                               for key in states[a] if key != axis)
                    source_depth[p] += 1
            assert len(branch) <= 1
            quota[("branch" if branch else "straight", k)] += 1
        factor = 4 if split == "train" else 1
        expected = {("straight", k): 500 * factor for k in (2, 3, 4, 5)}
        expected.update({("branch", 3): 200 * factor, ("branch", 4): 400 * factor,
                         ("branch", 5): 400 * factor})
        assert dict(quota) == expected and len(used) == nodes_n
        if prefix == "sourcebalanced_scene_":
            assert source_depth[0] == 400 * factor
        result.append({"prefix": prefix, "split": split, "nodes": nodes_n, "sessions": len(rows),
                       "edges": len(edge_keys), "quota": {f"{a}_L{b}": v for (a, b), v in sorted(quota.items())},
                       "branch_source_occurrence_counts": dict(source_depth)})
    assert not ({s["site"] for s in splits["train"]} & {s["site"] for s in splits["test"]})
    assert not ({json.dumps(s, sort_keys=True) for s in splits["train"]}
                & {json.dumps(s, sort_keys=True) for s in splits["test"]})
    return result


def main():
    records = check_sessions("main_scene_holdout_") + check_sessions("sourcebalanced_scene_")
    ref = read(RUN / "references/demand_summary.json")
    for entry in ref["input_snapshots"]:
        assert sha(Path(entry["path"])) == entry["sha256"], entry["path"]
    broken = []
    for p in RUN.rglob("*.md"):
        for link in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
            if link.startswith(("https://", "http://", "#")):
                continue
            target = link.split("#", 1)[0].strip("<>")
            if target and not (p.parent / target).exists():
                broken.append({"file": str(p.relative_to(RUN)), "target": target})
    assert not broken, broken
    state = read(ROOT / "20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATE.json")
    assert state["dataset_design_branch_20261021"]["formal_render_started"] is False
    assert state["local_work"]["requirements"]["R17"] == "in_progress"
    result = {
        "status": "passed", "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "main_and_sourcebalanced_topology_reference_snapshot_links_and_branch_status",
        "session_checks": records, "reference_input_hashes_match": True,
        "run_markdown_local_links_exist": True, "R17_still_in_progress": True,
        "not_checked": ["UE rendering", "all wardrobe visibility", "scene asset-family visual independence",
                        "model performance", "full-repository audits"],
    }
    (RUN / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "kind": "offline_research_delivery_not_render_manifest",
        "technical_owner": "20_planning/data_design/character_creator/full_process/technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md",
        "reading_entry": "MORNING_BRIEF.md",
        "generated_at": result["checked_at"],
        "primary_artifacts": ["graph/main_scene_holdout_metrics.json", "graph/sourcebalanced_scene_metrics.json",
                              "references/demand_summary.json", "verification.json"],
        "files": [{"path": str(p.relative_to(RUN)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": sha(p)}
                  for p in sorted(RUN.rglob("*")) if p.is_file() and "__pycache__" not in p.parts
                  and p.name != "DELIVERY_MANIFEST.json"],
        "external_inputs": [
            {"path": str(p), "sha256": sha(p)} for p in (
                ROOT / "00_engine/outputs/render_readiness_20261021_v1/HANDOFF.md",
                Path("C:/Users/Macheniek/Documents/data/未命名.md"))],
    }
    (RUN / "DELIVERY_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "checked_sessions": 30000,
                      "manifest_files": len(manifest["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
