"""Convert frozen config-graph chain candidates into a local UE render matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_GRAPH_DIR = (
    ENGINE_ROOT / "outputs" / "first_batch_dataset" / "graph_20260824_v1"
)
DEFAULT_BASE_MATRIX = SCRIPT_ROOT / "first_batch_local_render_matrix_20260824_v1.json"
DEFAULT_OUTPUT = SCRIPT_ROOT / "first_batch_chain_render_matrix_20260824_v1.json"


class ChainRenderMatrixError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ChainRenderMatrixError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChainRenderMatrixError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        values = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise ChainRenderMatrixError(f"Could not read JSONL: {path}") from exc
    require(all(isinstance(value, dict) for value in values), f"Invalid JSONL: {path}")
    return values


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def build_chain_render_matrix(
    graph_dir: Path, base_matrix_path: Path
) -> dict[str, Any]:
    source = read_json(graph_dir / "source_manifest.json")
    build_report = read_json(graph_dir / "build_report.json")
    candidates = read_json(graph_dir / "review_10" / "ue_render_candidates.json")
    base = read_json(base_matrix_path)
    nodes = read_jsonl(graph_dir / "nodes.jsonl")

    require(build_report.get("status") == "passed", "Config graph is not passed")
    require(source.get("source_manifest_id") == build_report.get("source_manifest_id"), "Source/report mismatch")
    require(candidates.get("source_manifest_id") == source.get("source_manifest_id"), "Candidate/source mismatch")
    candidate_rows = candidates.get("candidates")
    require(isinstance(candidate_rows, list) and len(candidate_rows) == 2, "Expected two chain candidates")

    nodes_by_id = {node["node_id"]: node for node in nodes}
    looks_by_id = {look["look_id"]: look for look in source["looks"]}
    assets_by_id = {asset["asset_id"]: asset for asset in source["assets"]}

    ordered_node_ids: list[str] = []
    memberships: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidate_rows:
        node_ids = candidate.get("node_ids")
        require(isinstance(node_ids, list) and len(node_ids) in (4, 5, 6), "Invalid candidate path")
        for round_index, node_id in enumerate(node_ids):
            require(node_id in nodes_by_id, f"Candidate references missing node: {node_id}")
            memberships.setdefault(node_id, []).append(
                {
                    "chain_id": candidate["chain_id"],
                    "node_position": round_index,
                    "selection_reason": candidate["selection_reason"],
                }
            )
            if node_id not in ordered_node_ids:
                ordered_node_ids.append(node_id)

    samples = []
    for sample_index, node_id in enumerate(ordered_node_ids, start=1):
        node = nodes_by_id[node_id]
        config = node["config"]
        require(config["expression_id"] == "happy", f"Non-Happy node: {node_id}")
        look = looks_by_id.get(node["look_id"])
        action = assets_by_id.get(config["action_id"])
        camera = assets_by_id.get(config["camera_id"])
        require(look is not None, f"Missing Look source row: {node['look_id']}")
        require(action is not None and action["asset_type"] == "action", f"Missing action: {node_id}")
        require(camera is not None and camera["asset_type"] == "camera", f"Missing camera: {node_id}")
        section_index = camera["constraints"]["section_index"]
        require(section_index in (0, 1, 2, 3), f"Invalid camera section: {node_id}")
        start_frame = section_index * 150
        samples.append(
            {
                "sample_id": f"CHAIN_NODE_{sample_index:02d}_{node_id}",
                "graph_node_id": node_id,
                "chain_memberships": memberships[node_id],
                "look_id": look["source_look_id"],
                "graph_look_id": node["look_id"],
                "sex": config["sex"],
                "compatibility_domain_id": node["compatibility_domain_id"],
                "bodyfit_id": look["bodyfit_id"],
                "identity_id": look["identity_id"],
                "outfit_id": look["outfit_id"],
                "character_blueprint": look["character_blueprint"],
                "character_blueprint_class": look["character_blueprint_class"],
                "action_id": action["constraints"]["source_action_id"],
                "graph_action_id": config["action_id"],
                "expression_id": "happy",
                "expression_is_editable_feature": False,
                "composite_animation": action["constraints"]["happy_composite_animation"],
                "camera_id": config["camera_id"],
                "camera_section_index": section_index,
                "start_frame_inclusive": start_frame,
                "end_frame_exclusive": start_frame + 150,
                "output_relative_directory": node_id,
                "expected_media_uri": node["expected_media_uri"],
                "node_config": config,
            }
        )

    domains = {sample["compatibility_domain_id"] for sample in samples}
    chain_ids = [candidate["chain_id"] for candidate in candidate_rows]
    checks = {
        "exactly_two_candidate_chains": len(chain_ids) == 2 and len(set(chain_ids)) == 2,
        "all_candidate_nodes_resolved": all(
            node_id in nodes_by_id
            for candidate in candidate_rows
            for node_id in candidate["node_ids"]
        ),
        "render_each_unique_node_once": len(samples) == len(set(ordered_node_ids)),
        "both_compatibility_domains_present": domains == {"female_v1", "male_v1"},
        "all_samples_happy_only": all(sample["expression_id"] == "happy" for sample in samples),
        "all_samples_are_150_frames": all(
            sample["end_frame_exclusive"] - sample["start_frame_inclusive"] == 150
            for sample in samples
        ),
        "all_runtime_bindings_resolved": all(
            sample["character_blueprint_class"]
            and sample["composite_animation"]
            and sample["camera_id"]
            for sample in samples
        ),
    }
    require(all(checks.values()), f"Chain render matrix checks failed: {checks}")
    return {
        "schema_version": "first_batch_local_render_matrix_v1",
        "matrix_id": "first_batch_chain_visual_smoke_20260824_v1",
        "matrix_role": "representative_chain_visual_smoke",
        "status": "frozen_for_local_render",
        "source_manifest_id": source["source_manifest_id"],
        "sampling_spec_version": source["sampling_spec_version"],
        "sources": {
            "graph_dir": str(graph_dir),
            "base_matrix": str(base_matrix_path),
            "chain_candidates": str(
                graph_dir / "review_10" / "ue_render_candidates.json"
            ),
        },
        "unreal": base["unreal"],
        "render": base["render"],
        "coverage": {
            "chain_count": len(chain_ids),
            "chain_ids": chain_ids,
            "path_node_reference_count": sum(
                len(candidate["node_ids"]) for candidate in candidate_rows
            ),
            "unique_node_count": len(samples),
            "domain_counts": {
                domain_id: sum(
                    sample["compatibility_domain_id"] == domain_id
                    for sample in samples
                )
                for domain_id in sorted(domains)
            },
            "checks": checks,
        },
        "chains": [
            {
                "chain_id": candidate["chain_id"],
                "selection_reason": candidate["selection_reason"],
                "node_ids": candidate["node_ids"],
            }
            for candidate in candidate_rows
        ],
        "samples": samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", type=Path, default=DEFAULT_GRAPH_DIR)
    parser.add_argument("--base-matrix", type=Path, default=DEFAULT_BASE_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        matrix = build_chain_render_matrix(
            args.graph_dir.resolve(), args.base_matrix.resolve()
        )
        write_json(args.output.resolve(), matrix)
    except ChainRenderMatrixError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "matrix_id": matrix["matrix_id"],
                "chain_count": matrix["coverage"]["chain_count"],
                "path_node_reference_count": matrix["coverage"][
                    "path_node_reference_count"
                ],
                "unique_node_count": matrix["coverage"]["unique_node_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
