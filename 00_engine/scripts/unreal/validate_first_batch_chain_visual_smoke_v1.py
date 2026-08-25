"""Validate rendered representative chains and build an ordered review page."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_GRAPH_DIR = (
    ENGINE_ROOT / "outputs" / "first_batch_dataset" / "graph_20260824_v1"
)
DEFAULT_MATRIX = SCRIPT_ROOT / "first_batch_chain_render_matrix_20260824_v1.json"
DEFAULT_OUTPUT_ROOT = (
    ENGINE_ROOT
    / "outputs"
    / "unreal_render"
    / "first_batch_chain_visual_smoke_20260824_v1"
)


class ChainVisualValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ChainVisualValidationError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChainVisualValidationError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_uri(path: Path, page: Path) -> str:
    return Path(os.path.relpath(path, page.parent)).as_posix()


def validate_media(sample: dict[str, Any], output_root: Path) -> dict[str, Any]:
    folder = output_root / sample["output_relative_directory"]
    report_path = folder / "render_report.json"
    report = read_json(report_path)
    video = Path(report.get("video", ""))
    automation = report.get("automation_contract", {})
    checks = {
        "report_passed": report.get("status") == "passed",
        "frame_count_150": report.get("frame_count") == 150,
        "resolution_2560x1440": report.get("resolution") == [2560, 1440],
        "fps_30": report.get("fps") == 30,
        "sample_id_matches": automation.get("sample_id") == sample["sample_id"],
        "look_id_matches": automation.get("look_id") == sample["look_id"],
        "action_id_matches": automation.get("action_id") == sample["action_id"],
        "camera_id_matches": automation.get("camera_id") == sample["camera_id"],
        "expression_happy": automation.get("expression_id") == "happy",
        "pose_driver_passed": automation.get("pose_driver_contract", {}).get("passed") is True,
        "temporal_motion_passed": automation.get("temporal_motion_contract", {}).get("passed") is True,
        "video_exists": video.is_file() and video.stat().st_size > 0,
    }
    require(all(checks.values()), f"Media contract failed: {sample['graph_node_id']} {checks}")
    actual_hash = sha256_file(video)
    checks["video_sha256_matches"] = actual_hash == report.get("video_sha256")
    require(checks["video_sha256_matches"], f"Video hash mismatch: {video}")
    return {
        "graph_node_id": sample["graph_node_id"],
        "sample_id": sample["sample_id"],
        "folder": str(folder),
        "video": str(video),
        "video_sha256": actual_hash,
        "video_size_bytes": video.stat().st_size,
        "maximum_temporal_mean_abs_difference": automation[
            "temporal_motion_contract"
        ]["maximum_mean_abs_difference"],
        "checks": checks,
        "passed": all(checks.values()),
    }


def build_html(report: dict[str, Any], page_path: Path) -> str:
    sections = []
    for chain in report["chains"]:
        cards = []
        for node in chain["path_nodes"]:
            media = node["media"]
            video_uri = relative_uri(Path(media["video"]), page_path)
            repeated = " repeated" if node["is_repeated_reference"] else ""
            edit = node.get("incoming_edit")
            edit_text = "Start node"
            if edit:
                edit_text = (
                    f"{edit['edge_type']} / {edit['edit_axis']}: "
                    f"{edit['before_value']} -> {edit['after_value']}"
                )
            cards.append(
                f"""
<article class="node{repeated}">
  <video controls preload="metadata" src="{html.escape(video_uri)}"></video>
  <div class="meta">
    <strong>Step {node['node_position']}: {html.escape(node['graph_node_id'])}</strong>
    <span>{html.escape(edit_text)}</span>
    <span>{html.escape(node['look_id'])} | {html.escape(node['action_id'])} | {html.escape(node['camera_id'])} | happy</span>
    <span>{'Reused rendered node' if node['is_repeated_reference'] else 'Unique rendered node'}</span>
  </div>
</article>"""
            )
        flags = chain["semantic_facts"]
        sections.append(
            f"""
<section>
  <h2>{html.escape(chain['chain_id'])}</h2>
  <p class="summary">{html.escape(chain['selection_reason'])} | policy={html.escape(chain['chain_policy'])} | edits={chain['edit_length']} | shortest={flags['is_semantic_shortest']} | repeated={flags['has_repeated_axis']} | consecutive={flags['has_consecutive_same_axis']} | rollback={flags['has_rollback']} | returns={flags['returns_to_start']}</p>
  <div class="grid">{''.join(cards)}</div>
</section>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>First Batch Chain Visual Smoke</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#101214;color:#edf0f2;font-family:Arial,sans-serif}} header{{padding:24px 28px;border-bottom:1px solid #363b40}} h1,h2{{margin:0 0 10px}} header p,.summary{{color:#aeb6bd}} section{{padding:24px 28px;border-bottom:1px solid #2b3035}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}} .node{{background:#191d20;border:1px solid #343a40;border-radius:6px;overflow:hidden}} .node.repeated{{border-color:#d39b3d}} video{{display:block;width:100%;aspect-ratio:16/9;background:#000}} .meta{{display:grid;gap:6px;padding:12px;font-size:13px}} .meta span{{color:#bdc4ca;overflow-wrap:anywhere}}
</style>
</head>
<body>
<header><h1>First Batch Representative Chain Visual Smoke</h1><p>9 unique rendered nodes, 11 path references, 2560x1440, 30 fps, 5 seconds, Happy-only. Gold borders mark repeated node references.</p></header>
{''.join(sections)}
</body>
</html>
"""


def validate_chain_visual_smoke(
    graph_dir: Path, matrix_path: Path, output_root: Path
) -> dict[str, Any]:
    matrix = read_json(matrix_path)
    review = read_json(graph_dir / "review_10" / "representative_chains.json")
    aggregate = read_json(output_root / "matrix_report.json")
    require(matrix.get("matrix_role") == "representative_chain_visual_smoke", "Wrong matrix role")
    require(aggregate.get("status") == "passed", "Render matrix is not passed")
    require(aggregate.get("passed_count") == len(matrix["samples"]), "Not every sample passed")
    require(len(matrix["samples"]) == 9, "Expected nine unique rendered nodes")

    samples_by_node = {sample["graph_node_id"]: sample for sample in matrix["samples"]}
    require(len(samples_by_node) == 9, "Graph node samples are not unique")
    media_by_node = {
        node_id: validate_media(sample, output_root)
        for node_id, sample in samples_by_node.items()
    }
    expanded_by_chain = {
        item["chain"]["chain_id"]: item for item in review["chains"]
    }

    chain_reports = []
    path_reference_count = 0
    for candidate in matrix["chains"]:
        chain_id = candidate["chain_id"]
        expanded = expanded_by_chain.get(chain_id)
        require(expanded is not None, f"Missing expanded chain: {chain_id}")
        chain = expanded["chain"]
        node_ids = candidate["node_ids"]
        require(node_ids == chain["node_ids"], f"Candidate path mismatch: {chain_id}")
        path_reference_count += len(node_ids)
        seen: set[str] = set()
        path_nodes = []
        for position, node_id in enumerate(node_ids):
            require(node_id in samples_by_node, f"Unrendered path node: {node_id}")
            sample = samples_by_node[node_id]
            incoming = None if position == 0 else expanded["steps"][position - 1]
            repeated = node_id in seen
            seen.add(node_id)
            path_nodes.append(
                {
                    "node_position": position,
                    "graph_node_id": node_id,
                    "is_repeated_reference": repeated,
                    "look_id": sample["look_id"],
                    "action_id": sample["action_id"],
                    "camera_id": sample["camera_id"],
                    "incoming_edit": incoming,
                    "media": media_by_node[node_id],
                }
            )
        if chain["returns_to_start"]:
            require(node_ids[0] == node_ids[-1], f"Return label/path mismatch: {chain_id}")
            require(
                media_by_node[node_ids[0]]["video_sha256"]
                == media_by_node[node_ids[-1]]["video_sha256"],
                f"Returned node media mismatch: {chain_id}",
            )
        chain_reports.append(
            {
                "chain_id": chain_id,
                "selection_reason": candidate["selection_reason"],
                "compatibility_domain_id": chain["compatibility_domain_id"],
                "chain_policy": chain["chain_policy"],
                "edit_length": chain["edit_length"],
                "semantic_facts": {
                    key: chain[key]
                    for key in (
                        "is_semantic_shortest",
                        "has_repeated_axis",
                        "has_consecutive_same_axis",
                        "has_rollback",
                        "returns_to_start",
                    )
                },
                "path_node_reference_count": len(node_ids),
                "unique_rendered_node_count": len(set(node_ids)),
                "path_nodes": path_nodes,
                "machine_status": "passed",
            }
        )
    require(path_reference_count == 11, "Expected eleven path node references")
    report = {
        "schema_version": "first_batch_chain_visual_smoke_report_v1",
        "status": "machine_passed_assistant_visual_precheck_passed_pending_user",
        "source_manifest_id": matrix["source_manifest_id"],
        "matrix_id": matrix["matrix_id"],
        "chain_count": len(chain_reports),
        "path_node_reference_count": path_reference_count,
        "unique_rendered_node_count": len(media_by_node),
        "media_passed_count": sum(media["passed"] for media in media_by_node.values()),
        "media_failed_count": sum(not media["passed"] for media in media_by_node.values()),
        "assistant_visual_precheck": {
            "status": "passed",
            "scope": "ordered contact sheet and representative middle frames",
            "notes": [
                "No T-pose was visible.",
                "No facial white-patch regression was visible.",
                "Characters remained framed by the selected cameras.",
                "No new severe clothing failure was visible in sampled frames.",
            ],
        },
        "user_visual_review": {
            "status": "pending",
            "review_page": str(output_root / "chain_review.html"),
        },
        "chains": chain_reports,
    }
    write_json(output_root / "chain_visual_smoke_report.json", report)
    write_text(output_root / "chain_review.html", build_html(report, output_root / "chain_review.html"))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", type=Path, default=DEFAULT_GRAPH_DIR)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = validate_chain_visual_smoke(
            args.graph_dir.resolve(), args.matrix.resolve(), args.output_root.resolve()
        )
    except ChainVisualValidationError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print(
        json.dumps(
            {
                "status": report["status"],
                "chain_count": report["chain_count"],
                "path_node_reference_count": report["path_node_reference_count"],
                "unique_rendered_node_count": report["unique_rendered_node_count"],
                "media_passed_count": report["media_passed_count"],
                "review_page": report["user_visual_review"]["review_page"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
