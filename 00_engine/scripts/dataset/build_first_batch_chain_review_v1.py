"""Build a deterministic human-review pack from a first-batch config graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_GRAPH_DIR = (
    ENGINE_ROOT / "outputs" / "first_batch_dataset" / "graph_20260824_v1"
)
DEFAULT_OUTPUT_DIR = DEFAULT_GRAPH_DIR / "review_10"
DOMAIN_IDS = ("female_v1", "male_v1")


class ChainReviewError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ChainReviewError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChainReviewError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ChainReviewError(f"Could not read JSONL: {path}") from exc
    require(all(isinstance(value, dict) for value in values), f"Invalid JSONL: {path}")
    return values


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def select_first(
    chains: list[dict[str, Any]],
    used_ids: set[str],
    predicate: Callable[[dict[str, Any]], bool],
    reason: str,
) -> tuple[str, dict[str, Any]]:
    for chain in sorted(chains, key=lambda item: item["chain_id"]):
        if chain["chain_id"] not in used_ids and predicate(chain):
            used_ids.add(chain["chain_id"])
            return reason, chain
    raise ChainReviewError(f"No chain satisfies review selector: {reason}")


def select_representative_chains(
    chains: list[dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    selected: list[tuple[str, dict[str, Any]]] = []
    used_ids: set[str] = set()
    for domain_id in DOMAIN_IDS:
        in_domain = [
            chain
            for chain in chains
            if chain["compatibility_domain_id"] == domain_id
        ]
        selectors: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
            (
                "progressive_shortest_length_3",
                lambda chain: chain["chain_policy"] == "progressive_shortest"
                and chain["edit_length"] == 3,
            ),
            (
                "progressive_shortest_length_4",
                lambda chain: chain["chain_policy"] == "progressive_shortest"
                and chain["edit_length"] == 4,
            ),
            (
                "freeform_consecutive_same_axis_length_3",
                lambda chain: chain["chain_policy"] == "freeform_walk"
                and chain["edit_length"] == 3
                and chain["has_consecutive_same_axis"],
            ),
            (
                "freeform_rollback_length_4",
                lambda chain: chain["chain_policy"] == "freeform_walk"
                and chain["edit_length"] == 4
                and chain["has_rollback"],
            ),
            (
                "freeform_returns_to_start_length_5",
                lambda chain: chain["chain_policy"] == "freeform_walk"
                and chain["edit_length"] == 5
                and chain["returns_to_start"]
                and len(set(chain["edge_types"])) >= 2,
            ),
        ]
        for reason, predicate in selectors:
            selected.append(
                select_first(
                    in_domain,
                    used_ids,
                    predicate,
                    f"{domain_id}:{reason}",
                )
            )
    require(len(selected) == 10, "Review selection must contain exactly 10 chains")
    return selected


def expand_chain(
    reason: str,
    chain: dict[str, Any],
    nodes_by_id: dict[str, dict[str, Any]],
    jobs_by_node: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    node_ids = chain["node_ids"]
    require(
        all(node_id in nodes_by_id for node_id in node_ids),
        f"Chain references missing node: {chain['chain_id']}",
    )
    require(
        all(node_id in jobs_by_node for node_id in node_ids),
        f"Chain references node without render job: {chain['chain_id']}",
    )
    steps = []
    for index, (before_id, after_id) in enumerate(zip(node_ids, node_ids[1:])):
        before = nodes_by_id[before_id]
        after = nodes_by_id[after_id]
        axis = chain["edge_axes"][index]
        differences = [
            key
            for key in before["config"]
            if before["config"].get(key) != after["config"].get(key)
        ]
        require(
            differences == [axis],
            f"Review step is not atomic: {chain['chain_id']} round {index + 1}",
        )
        steps.append(
            {
                "round": index + 1,
                "edge_id": chain["edge_ids"][index],
                "edge_type": chain["edge_types"][index],
                "edit_axis": axis,
                "before_value": before["config"][axis],
                "after_value": after["config"][axis],
                "instruction": chain["instructions"][index],
                "source_node_id": before_id,
                "target_node_id": after_id,
                "target_expected_media_uri": after["expected_media_uri"],
            }
        )
    return {
        "selection_reason": reason,
        "chain": chain,
        "start_config": nodes_by_id[node_ids[0]]["config"],
        "end_config": nodes_by_id[node_ids[-1]]["config"],
        "steps": steps,
        "node_render_plan": [
            {
                "node_id": node_id,
                "config": nodes_by_id[node_id]["config"],
                "look_id": nodes_by_id[node_id]["look_id"],
                "character_blueprint": nodes_by_id[node_id]["character_blueprint"],
                "render_job": jobs_by_node[node_id],
            }
            for node_id in node_ids
        ],
        "review": {
            "status": "pending_human_review",
            "checks": [
                "Every round changes exactly one semantic field.",
                "Instruction text matches before_value and after_value.",
                "All nodes remain in one compatibility domain.",
                "Policy and derived Boolean labels match the path semantics.",
                "Rendered identity, outfit, action, and camera match node config.",
            ],
        },
    }


def markdown_report(pack: dict[str, Any]) -> str:
    lines = [
        "# First-Batch Representative Chain Review",
        "",
        "This pack selects ten deterministic chains from the frozen 4,000-chain graph.",
        "It is a semantic review set; visual status stays pending until UE renders are reviewed.",
        "",
        "## Summary",
        "",
        "| Chain | Domain | Policy | Length | Axes | Repeated | Consecutive | Rollback | Returns |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for item in pack["chains"]:
        chain = item["chain"]
        lines.append(
            "| {chain_id} | {domain} | {policy} | {length} | {axes} | {repeated} | "
            "{consecutive} | {rollback} | {returns} |".format(
                chain_id=chain["chain_id"],
                domain=chain["compatibility_domain_id"],
                policy=chain["chain_policy"],
                length=chain["edit_length"],
                axes=" -> ".join(chain["edge_types"]),
                repeated=chain["has_repeated_axis"],
                consecutive=chain["has_consecutive_same_axis"],
                rollback=chain["has_rollback"],
                returns=chain["returns_to_start"],
            )
        )
    for item in pack["chains"]:
        chain = item["chain"]
        lines.extend(
            [
                "",
                f"## {chain['chain_id']}",
                "",
                f"Selector: `{item['selection_reason']}`",
                "",
                "| Round | Type | Field | Before | After | Target node |",
                "|---:|---|---|---|---|---|",
            ]
        )
        for step in item["steps"]:
            lines.append(
                f"| {step['round']} | {step['edge_type']} | {step['edit_axis']} | "
                f"`{step['before_value']}` | `{step['after_value']}` | "
                f"`{step['target_node_id']}` |"
            )
    lines.extend(
        [
            "",
            "## UE Render Candidates",
            "",
            "Render all nodes in these two chains, preserving node IDs as output keys:",
            "",
        ]
    )
    for candidate in pack["ue_render_candidates"]:
        lines.append(
            f"- `{candidate['chain_id']}`: {candidate['selection_reason']} "
            f"({len(candidate['node_ids'])} nodes)"
        )
    return "\n".join(lines) + "\n"


def build_review_pack(graph_dir: Path, output_dir: Path) -> dict[str, Any]:
    report = read_json(graph_dir / "build_report.json")
    require(report.get("status") == "passed", "Graph build report is not passed")
    require(report.get("counts", {}).get("chains") == 4000, "Expected 4,000 chains")
    nodes = read_jsonl(graph_dir / "nodes.jsonl")
    chains = read_jsonl(graph_dir / "chains.jsonl")
    jobs = read_jsonl(graph_dir / "render_jobs.jsonl")
    nodes_by_id = {node["node_id"]: node for node in nodes}
    jobs_by_node = {job["node_id"]: job for job in jobs}
    require(len(nodes_by_id) == 640, "Expected 640 unique nodes")
    require(len(chains) == 4000, "Expected 4,000 chains")
    require(len(jobs_by_node) == 640, "Expected 640 unique render jobs")

    selected = select_representative_chains(chains)
    expanded = [
        expand_chain(reason, chain, nodes_by_id, jobs_by_node)
        for reason, chain in selected
    ]
    render_candidates = []
    for preferred_reason in (
        "female_v1:progressive_shortest_length_4",
        "male_v1:freeform_returns_to_start_length_5",
    ):
        item = next(row for row in expanded if row["selection_reason"] == preferred_reason)
        render_candidates.append(
            {
                "chain_id": item["chain"]["chain_id"],
                "selection_reason": item["selection_reason"],
                "node_ids": item["chain"]["node_ids"],
                "node_render_plan": item["node_render_plan"],
            }
        )
    pack = {
        "schema_version": "first_batch_chain_review_v1",
        "source_manifest_id": report["source_manifest_id"],
        "sampling_spec_version": report["sampling_spec_version"],
        "graph_counts": report["counts"],
        "selection_count": len(expanded),
        "selection_policy": (
            "Five deterministic semantic representatives per compatibility domain"
        ),
        "chains": expanded,
        "ue_render_candidates": render_candidates,
    }
    write_json(output_dir / "representative_chains.json", pack)
    write_json(
        output_dir / "ue_render_candidates.json",
        {
            "schema_version": "first_batch_chain_render_candidates_v1",
            "source_manifest_id": report["source_manifest_id"],
            "candidates": render_candidates,
        },
    )
    write_text(output_dir / "README.md", markdown_report(pack))
    return pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", type=Path, default=DEFAULT_GRAPH_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        pack = build_review_pack(args.graph_dir.resolve(), args.output_dir.resolve())
    except ChainReviewError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "selection_count": pack["selection_count"],
                "ue_render_candidates": [
                    item["chain_id"] for item in pack["ue_render_candidates"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
