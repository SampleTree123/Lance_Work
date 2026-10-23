"""Build a compact first-batch delivery with numbered videos and chain text."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DELIVERY_SCHEMA_VERSION = "datamake_video_edit_dataset_manifest_v1"
CHAIN_SCHEMA_VERSION = "datamake_multiround_video_chain_v1"


class DeliveryError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeliveryError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected a JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        values = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"Could not read JSONL: {path}") from exc
    require(all(isinstance(value, dict) for value in values), f"Invalid JSONL: {path}")
    return values


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_unique(
    values: Iterable[dict[str, Any]], key: str, label: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        item_id = value.get(key)
        require(isinstance(item_id, str) and item_id, f"Missing {label} {key}")
        require(item_id not in result, f"Duplicate {label}: {item_id}")
        result[item_id] = value
    return result


def safe_run_path(run_root: Path, relative: str, label: str) -> Path:
    candidate = Path(relative)
    require(not candidate.is_absolute(), f"{label} must be relative: {relative}")
    resolved_root = run_root.resolve()
    resolved = (run_root / candidate).resolve()
    require(
        resolved == resolved_root or resolved_root in resolved.parents,
        f"{label} escapes the render Run Root: {relative}",
    )
    return resolved


def validate_media(
    *,
    run_root: Path,
    node: dict[str, Any],
    media_record: dict[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    node_id = node["node_id"]
    require(media_record.get("node_id") == node_id, f"Media node mismatch: {node_id}")
    require(
        media_record.get("config_sha256") == node.get("config_sha256"),
        f"Media config hash mismatch: {node_id}",
    )
    media_relative = media_record.get("path")
    sidecar_relative = media_record.get("sidecar")
    require(isinstance(media_relative, str) and media_relative, f"Missing media path: {node_id}")
    require(isinstance(sidecar_relative, str) and sidecar_relative, f"Missing sidecar: {node_id}")
    media_path = safe_run_path(run_root, media_relative, "media path")
    sidecar_path = safe_run_path(run_root, sidecar_relative, "sidecar path")
    require(media_path.is_file(), f"Accepted media is missing: {media_path}")
    require(sidecar_path.is_file(), f"Accepted sidecar is missing: {sidecar_path}")
    actual_media_sha = sha256_file(media_path)
    require(
        actual_media_sha == media_record.get("sha256"),
        f"Media SHA-256 mismatch: {node_id}",
    )
    sidecar = read_json(sidecar_path)
    require(sidecar.get("status") == "accepted", f"Sidecar is not accepted: {node_id}")
    require(sidecar.get("node_id") == node_id, f"Sidecar node mismatch: {node_id}")
    ground_truth = sidecar.get("ground_truth", {})
    require(
        ground_truth.get("config_sha256") == node.get("config_sha256"),
        f"Sidecar config hash mismatch: {node_id}",
    )
    require(
        ground_truth.get("config") == node.get("config"),
        f"Sidecar ground truth differs from graph: {node_id}",
    )
    require(
        sidecar.get("media", {}).get("sha256") == actual_media_sha,
        f"Sidecar media hash mismatch: {node_id}",
    )
    return media_path, sidecar_path, sidecar


def materialize_video(source: Path, target: Path, mode: str) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if mode == "copy":
        shutil.copy2(source, target)
        return "copy"
    try:
        os.link(source, target)
        return "hardlink"
    except OSError:
        shutil.copy2(source, target)
        return "copy_fallback"


def quality_flags_pass(flags: object) -> bool:
    return (
        isinstance(flags, dict)
        and flags.get("atomic") is True
        and flags.get("language_complete") is True
        and flags.get("contains_internal_id") is False
        and flags.get("paired_media_required") is True
    )


def build_chain_record(
    *,
    dataset_id: str,
    package_scope: str,
    batch_id: str,
    chain: dict[str, Any],
    dialog: dict[str, Any],
    node_by_id: dict[str, dict[str, Any]],
    turn_by_id: dict[str, dict[str, Any]],
    video_path_by_node: dict[str, str],
) -> dict[str, Any]:
    node_ids = chain.get("node_ids")
    require(isinstance(node_ids, list) and len(node_ids) >= 2, f"Invalid chain: {chain.get('chain_id')}")
    require(dialog.get("chain_id") == chain.get("chain_id"), "Dialog/chain mismatch")
    require(dialog.get("edit_length") == chain.get("edit_length"), "Dialog edit length mismatch")
    turn_ids = dialog.get("turn_ids")
    require(
        isinstance(turn_ids, list) and len(turn_ids) == len(node_ids) - 1,
        f"Dialog turn count mismatch: {chain['chain_id']}",
    )
    video_sequence = []
    for position, node_id in enumerate(node_ids):
        require(node_id in node_by_id, f"Unknown node in chain: {node_id}")
        node = node_by_id[node_id]
        video_sequence.append(
            {
                "position": position,
                "node_id": node_id,
                "path": video_path_by_node[node_id],
                "config_sha256": node["config_sha256"],
                "look_id": node["look_id"],
                "render_profile_id": node["render_profile_id"],
                "config": node["config"],
            }
        )

    turns = []
    for offset, turn_id in enumerate(turn_ids):
        require(turn_id in turn_by_id, f"Missing text turn: {turn_id}")
        turn = turn_by_id[turn_id]
        source_node_id = node_ids[offset]
        target_node_id = node_ids[offset + 1]
        require(turn.get("chain_id") == chain["chain_id"], f"Turn chain mismatch: {turn_id}")
        require(turn.get("round") == offset + 1, f"Turn order mismatch: {turn_id}")
        require(turn.get("source_node_id") == source_node_id, f"Turn source mismatch: {turn_id}")
        require(turn.get("target_node_id") == target_node_id, f"Turn target mismatch: {turn_id}")
        prompt = turn.get("prompt", {})
        quality_flags = turn.get("quality_flags")
        require(
            quality_flags_pass(quality_flags),
            f"Turn quality flags did not pass: {turn_id}",
        )
        turns.append(
            {
                "round": offset + 1,
                "turn_id": turn_id,
                "edge_id": turn["edge_id"],
                "edge_type": turn["edge_type"],
                "edit_axis": turn["edit_axis"],
                "change": {
                    "before": turn["before_value"],
                    "after": turn["after_value"],
                },
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "video_in": video_path_by_node[source_node_id],
                "prompt": prompt["dialogue"],
                "standalone_prompt": prompt["standalone"],
                "grounding": turn.get("grounding"),
                "video_out": video_path_by_node[target_node_id],
                "quality_flags": quality_flags,
            }
        )

    return {
        "schema_version": CHAIN_SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "batch_id": batch_id,
        "package_scope": package_scope,
        "chain_id": chain["chain_id"],
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
        "initial_video": video_path_by_node[node_ids[0]],
        "final_video": video_path_by_node[node_ids[-1]],
        "video_sequence": video_sequence,
        "turns": turns,
    }


def build_simple_chain_record(
    chain_record: dict[str, Any], chain_index: int
) -> dict[str, Any]:
    return {
        "chain_index": chain_index,
        "chain_id": chain_record["chain_id"],
        "turns": [
            {
                "input_video": turn["video_in"],
                "instruction": turn["prompt"],
                "output_video": turn["video_out"],
            }
            for turn in chain_record["turns"]
        ],
    }


def build_delivery(
    *,
    graph_dir: Path,
    prompt_dir: Path,
    render_run_root: Path,
    output_dir: Path,
    dataset_id: str,
    package_scope: str,
    selected_chain_ids: list[str] | None = None,
    materialization_mode: str = "hardlink",
    strict_first_batch: bool = True,
) -> dict[str, Any]:
    require(dataset_id.strip() == dataset_id and dataset_id, "dataset_id must be non-empty")
    require(package_scope.strip() == package_scope and package_scope, "package_scope must be non-empty")
    require(materialization_mode in {"hardlink", "copy"}, "Unsupported materialization mode")
    require(not output_dir.exists(), f"Output already exists: {output_dir}")

    source_manifest_path = graph_dir / "source_manifest.json"
    nodes_path = graph_dir / "nodes.jsonl"
    chains_path = graph_dir / "chains.jsonl"
    prompt_manifest_path = prompt_dir / "prompt_manifest.json"
    dialogs_path = prompt_dir / "dialogs.jsonl"
    turns_path = prompt_dir / "turns.jsonl"
    media_manifest_path = render_run_root / "media_manifest.json"

    source_manifest = read_json(source_manifest_path)
    prompt_manifest = read_json(prompt_manifest_path)
    media_manifest = read_json(media_manifest_path)
    node_by_id = index_unique(read_jsonl(nodes_path), "node_id", "node")
    chain_by_id = index_unique(read_jsonl(chains_path), "chain_id", "chain")
    dialog_by_id = index_unique(read_jsonl(dialogs_path), "chain_id", "dialog")
    turn_by_id = index_unique(read_jsonl(turns_path), "turn_id", "turn")
    media_by_node = index_unique(media_manifest.get("records", []), "node_id", "media record")
    require(source_manifest.get("status") == "frozen", "Graph source manifest is not frozen")
    require(prompt_manifest.get("status") == "passed", "Prompt manifest is not passed")
    prompt_graph = prompt_manifest.get("graph_source", {})
    require(
        prompt_graph.get("source_manifest_sha256") == sha256_file(source_manifest_path),
        "Prompt/source manifest hash mismatch",
    )
    require(
        prompt_graph.get("nodes_sha256") == sha256_file(nodes_path),
        "Prompt/node graph hash mismatch",
    )
    require(
        prompt_graph.get("chains_sha256") == sha256_file(chains_path),
        "Prompt/chain graph hash mismatch",
    )

    if selected_chain_ids:
        require(
            len(selected_chain_ids) == len(set(selected_chain_ids)),
            "Selected chain IDs must be unique",
        )
        chain_ids = sorted(selected_chain_ids)
    else:
        chain_ids = sorted(chain_by_id)
    require(chain_ids, "At least one chain is required")
    for chain_id in chain_ids:
        require(chain_id in chain_by_id, f"Unknown selected chain: {chain_id}")
        require(chain_id in dialog_by_id, f"Missing prompt dialog: {chain_id}")

    selected_node_ids = sorted(
        {
            node_id
            for chain_id in chain_ids
            for node_id in chain_by_id[chain_id]["node_ids"]
        }
    )
    if selected_chain_ids is None and strict_first_batch:
        require(source_manifest.get("expected_nodes") == 640, "First batch expects 640 nodes")
        require(source_manifest.get("expected_chains") == 4000, "First batch expects 4,000 chains")
        require(len(node_by_id) == 640, "First-batch graph must contain 640 nodes")
        require(len(chain_by_id) == 4000, "First-batch graph must contain 4,000 chains")
        require(len(selected_node_ids) == 640, "All first-batch nodes must be referenced")
        require(
            prompt_manifest.get("counts", {}).get("turns") == 15000,
            "First-batch prompt layer must contain 15,000 turns",
        )
    video_path_by_node = {
        node_id: f"videos/{index}.mp4"
        for index, node_id in enumerate(selected_node_ids, start=1)
    }

    staging = output_dir.with_name(f".{output_dir.name}.staging.{os.getpid()}")
    require(not staging.exists(), f"Staging output already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        video_records = []
        materialization_methods: set[str] = set()
        for index, node_id in enumerate(selected_node_ids, start=1):
            require(node_id in node_by_id, f"Unknown selected node: {node_id}")
            require(node_id in media_by_node, f"No accepted media record for node: {node_id}")
            node = node_by_id[node_id]
            media_record = media_by_node[node_id]
            media_path, sidecar_path, sidecar = validate_media(
                run_root=render_run_root,
                node=node,
                media_record=media_record,
            )
            relative_video = video_path_by_node[node_id]
            target = staging / relative_video
            method = materialize_video(media_path, target, materialization_mode)
            materialization_methods.add(method)
            packaged_sha = sha256_file(target)
            require(packaged_sha == media_record["sha256"], f"Packaged media hash mismatch: {node_id}")
            video_records.append(
                {
                    "index": index,
                    "path": relative_video,
                    "node_id": node_id,
                    "config_sha256": node["config_sha256"],
                    "look_id": node["look_id"],
                    "render_profile_id": node["render_profile_id"],
                    "config": node["config"],
                    "media": {
                        key: media_record[key]
                        for key in (
                            "container",
                            "codec",
                            "bytes",
                            "sha256",
                            "width",
                            "height",
                            "fps",
                            "frames",
                            "duration_seconds",
                        )
                    },
                    "source": {
                        "run_relative_media": media_record["path"],
                        "run_relative_sidecar": media_record["sidecar"],
                        "sidecar_sha256": sha256_file(sidecar_path),
                        "accepted_at_utc": sidecar.get("accepted_at_utc"),
                    },
                }
            )

        chain_records = [
            build_chain_record(
                dataset_id=dataset_id,
                package_scope=package_scope,
                batch_id=source_manifest["batch_id"],
                chain=chain_by_id[chain_id],
                dialog=dialog_by_id[chain_id],
                node_by_id=node_by_id,
                turn_by_id=turn_by_id,
                video_path_by_node=video_path_by_node,
            )
            for chain_id in chain_ids
        ]
        chains_output = staging / "chains.json"
        write_json(chains_output, chain_records)
        simple_chain_records = [
            build_simple_chain_record(chain, chain_index)
            for chain_index, chain in enumerate(chain_records, start=1)
        ]
        simple_chains_output = staging / "chains_simple.json"
        write_json(simple_chains_output, simple_chain_records)
        turn_count = sum(len(chain["turns"]) for chain in chain_records)
        full_graph_selected = selected_chain_ids is None and len(chain_ids) == len(chain_by_id)
        manifest = {
            "schema_version": DELIVERY_SCHEMA_VERSION,
            "dataset_id": dataset_id,
            "batch_id": source_manifest["batch_id"],
            "package_scope": package_scope,
            "status": (
                "package_candidate_pending_release_qa"
                if full_graph_selected
                else "sample"
            ),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "layout": {
                "videos": "videos/<positive_integer>.mp4",
                "chains": "chains.json",
                "chains_simple": "chains_simple.json",
                "manifest": "manifest.json",
            },
            "naming": {
                "public_video_id": "positive integer starting at 1",
                "ordering": "lexicographic node_id order",
                "internal_media_key": "node_id",
                "node_id_preserved_in_manifest": True,
            },
            "counts": {
                "videos": len(video_records),
                "chains": len(chain_records),
                "turns": turn_count,
            },
            "sources": {
                "builder": "00_engine/scripts/dataset/build_first_batch_delivery_v1.py",
                "builder_sha256": sha256_file(Path(__file__)),
                "source_manifest_id": source_manifest["source_manifest_id"],
                "prompt_layer_version": prompt_manifest["prompt_layer_version"],
                "render_run_id": read_json(render_run_root / "manifest.json").get("run_id"),
                "source_manifest_sha256": sha256_file(source_manifest_path),
                "nodes_sha256": sha256_file(nodes_path),
                "chains_sha256": sha256_file(chains_path),
                "prompt_manifest_sha256": sha256_file(prompt_manifest_path),
                "dialogs_sha256": sha256_file(dialogs_path),
                "turns_sha256": sha256_file(turns_path),
                "media_manifest_sha256": sha256_file(media_manifest_path),
            },
            "materialization": {
                "requested": materialization_mode,
                "actual_methods": sorted(materialization_methods),
            },
            "checks": {
                "all_media_records_present": True,
                "all_sidecars_accepted": True,
                "all_media_hashes_match": True,
                "all_ground_truth_matches_graph": True,
                "prompt_graph_hashes_match": True,
                "all_chain_turns_have_bilingual_prompts": all(
                    set(turn["prompt"]) == {"en", "zh-CN"}
                    and set(turn["standalone_prompt"]) == {"en", "zh-CN"}
                    and quality_flags_pass(turn["quality_flags"])
                    for chain in chain_records
                    for turn in chain["turns"]
                ),
                "all_video_paths_resolve": True,
                "simple_chain_indices_sequential": [
                    chain["chain_index"] for chain in simple_chain_records
                ]
                == list(range(1, len(simple_chain_records) + 1)),
                "simple_chains_match_full_records": all(
                    simple == build_simple_chain_record(full, chain_index)
                    for chain_index, (simple, full) in enumerate(
                        zip(simple_chain_records, chain_records), start=1
                    )
                ),
                "sequential_video_names": [
                    record["path"] for record in video_records
                ]
                == [f"videos/{index}.mp4" for index in range(1, len(video_records) + 1)],
            },
            "files": {
                "chains.json": {
                    "bytes": chains_output.stat().st_size,
                    "sha256": sha256_file(chains_output),
                },
                "chains_simple.json": {
                    "bytes": simple_chains_output.stat().st_size,
                    "sha256": sha256_file(simple_chains_output),
                },
                "videos": video_records,
            },
            "chain_ids": chain_ids,
        }
        require(all(manifest["checks"].values()), "Delivery checks did not all pass")
        write_json(staging / "manifest.json", manifest)
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(output_dir)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", required=True, type=Path)
    parser.add_argument("--prompt-dir", required=True, type=Path)
    parser.add_argument("--render-run-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dataset-id", default="dataset_v1")
    parser.add_argument("--package-scope", default="full_first_batch")
    parser.add_argument("--chain-id", action="append", dest="chain_ids")
    parser.add_argument(
        "--materialization-mode",
        choices=("hardlink", "copy"),
        default="hardlink",
    )
    parser.add_argument("--allow-nonproduction-counts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_delivery(
            graph_dir=args.graph_dir,
            prompt_dir=args.prompt_dir,
            render_run_root=args.render_run_root,
            output_dir=args.output_dir,
            dataset_id=args.dataset_id,
            package_scope=args.package_scope,
            selected_chain_ids=args.chain_ids,
            materialization_mode=args.materialization_mode,
            strict_first_batch=not args.allow_nonproduction_counts,
        )
    except DeliveryError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
