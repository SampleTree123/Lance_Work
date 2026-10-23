#!/usr/bin/env python3
"""Collapse frozen DataMake prefix splits into one record per edit chain.

The source split stays authoritative for train/validation/test membership.  For
each chain, its longest prefix already contains the complete ordered prompt and
ground-truth video sequence, so no media are copied and no semantic fields are
reconstructed from filenames.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pyarrow as pa
import pyarrow.parquet as pq
import yaml


SCHEMA_VERSION = "datamake_lance_chain_dataset_v1"
MANIFEST_SCHEMA_VERSION = "datamake_lance_chain_dataset_manifest_v1"
SPLITS = ("train", "validation", "test")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def atomic_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def resolve_from(root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def validate_prefix_row(row: Dict[str, Any]) -> None:
    required = {
        "sample_id",
        "chain_id",
        "target_round",
        "prompts",
        "video_paths",
        "turn_ids",
        "edit_axes",
    }
    missing = sorted(required - set(row))
    if missing:
        raise ValueError(f"prefix row is missing fields: {missing}")
    target_round = int(row["target_round"])
    prompts = list(row["prompts"])
    video_paths = list(row["video_paths"])
    if target_round != len(prompts):
        raise ValueError(
            f"{row['chain_id']}: target_round={target_round} but prompts={len(prompts)}"
        )
    if len(video_paths) != target_round + 1:
        raise ValueError(
            f"{row['chain_id']}: expected {target_round + 1} videos, got "
            f"{len(video_paths)}"
        )
    if len(row["turn_ids"]) != target_round or len(row["edit_axes"]) != target_round:
        raise ValueError(f"{row['chain_id']}: turn/edit-axis counts do not match")


def longest_rows_for_split(
    split_manifest: Dict[str, Any], split_root: Path, split_name: str
) -> List[Dict[str, Any]]:
    record = split_manifest["splits"][split_name]
    longest: Dict[str, Dict[str, Any]] = {}
    prefix_rows = 0
    for parquet_record in record["parquet_files"]:
        parquet_path = resolve_from(split_root, parquet_record["path"])
        if not parquet_path.is_file():
            raise FileNotFoundError(parquet_path)
        actual_hash = sha256_file(parquet_path)
        if actual_hash != parquet_record["sha256"]:
            raise ValueError(f"source parquet hash differs: {parquet_path}")
        table = pq.read_table(parquet_path)
        rows = table.to_pylist()
        if len(rows) != int(parquet_record["rows"]):
            raise ValueError(f"source parquet row count differs: {parquet_path}")
        prefix_rows += len(rows)
        for row in rows:
            validate_prefix_row(row)
            chain_id = str(row["chain_id"])
            previous = longest.get(chain_id)
            if previous is None or int(row["target_round"]) > int(
                previous["target_round"]
            ):
                longest[chain_id] = row

    if prefix_rows != int(record["sample_count"]):
        raise ValueError(
            f"{split_name}: manifest has {record['sample_count']} prefixes, read {prefix_rows}"
        )
    chain_ids_path = resolve_from(split_root, record["chain_ids"])
    if sha256_file(chain_ids_path) != record["chain_ids_sha256"]:
        raise ValueError(f"chain-id file hash differs: {chain_ids_path}")
    expected_ids = json.loads(chain_ids_path.read_text(encoding="utf-8"))
    if isinstance(expected_ids, dict):
        expected_ids = expected_ids.get("chain_ids")
    if not isinstance(expected_ids, list):
        raise ValueError(f"invalid chain-id list: {chain_ids_path}")
    if set(map(str, expected_ids)) != set(longest):
        raise ValueError(f"{split_name}: longest-prefix chain set differs from frozen split")
    if len(longest) != int(record["chain_count"]):
        raise ValueError(f"{split_name}: chain count differs from frozen split")

    result = []
    for chain_id in sorted(longest):
        source = longest[chain_id]
        rounds = int(source["target_round"])
        result.append(
            {
                "schema_version": SCHEMA_VERSION,
                "chain_sample_id": f"dmchain_{chain_id}",
                "chain_id": chain_id,
                "round_count": rounds,
                "language": str(source.get("language", "en")),
                "prompt_view": str(source.get("prompt_view", "dialogue")),
                "prompts": list(source["prompts"]),
                "video_paths": list(source["video_paths"]),
                "turn_ids": list(source["turn_ids"]),
                "edit_axes": list(source["edit_axes"]),
                "chain_policy": str(source.get("chain_policy", "")),
                "semantic_facts_json": str(source.get("semantic_facts_json", "{}")),
                "source_longest_prefix_sample_id": str(source["sample_id"]),
            }
        )
    return result


def write_parquet(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(pa.Table.from_pylist(materialized), temporary, compression="zstd")
    os.replace(temporary, path)
    return len(materialized)


def build_dataset_yaml(source_yaml: Path, parquet_path: Path, manifest_path: Path) -> str:
    payload = yaml.safe_load(source_yaml.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError(f"unexpected source dataset config: {source_yaml}")
    group = next(iter(payload.values()))
    if not isinstance(group, dict) or len(group) != 1:
        raise ValueError(f"unexpected source dataset group: {source_yaml}")
    dataset = next(iter(group.values()))
    dataset["dataset_names"] = {
        "datamake_online_rollout_chains": {"data_dir": [str(parquet_path)]}
    }
    dataset["datamake_record_level"] = "chain"
    dataset["datamake_history_mode"] = "online_rollout_full"
    dataset["datamake_chain_manifest"] = str(manifest_path)
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


def build(split_manifest_path: Path, output_dir: Path) -> Dict[str, Any]:
    split_manifest_path = split_manifest_path.resolve()
    split_root = split_manifest_path.parent
    split_manifest = read_json(split_manifest_path)
    if split_manifest.get("schema_version") != "datamake_lance_chain_split_v1":
        raise ValueError("unsupported source split manifest schema")

    top_manifest: Dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "source_split_manifest": str(split_manifest_path),
        "source_split_manifest_sha256": sha256_file(split_manifest_path),
        "history_mode": "online_rollout_full",
        "record_level": "chain",
        "target_policy": "rendered_ground_truth_per_turn",
        "splits": {},
    }
    all_chain_ids: Dict[str, set[str]] = {}
    for split_name in SPLITS:
        rows = longest_rows_for_split(split_manifest, split_root, split_name)
        split_dir = output_dir / split_name
        parquet_path = split_dir / "datamake_chains.parquet"
        manifest_path = split_dir / "manifest.json"
        row_count = write_parquet(parquet_path, rows)
        total_targets = sum(int(row["round_count"]) for row in rows)
        per_round_count: Dict[str, int] = {}
        chain_length_count: Dict[str, int] = {}
        for row in rows:
            rounds = int(row["round_count"])
            chain_length_count[str(rounds)] = chain_length_count.get(str(rounds), 0) + 1
            for round_number in range(1, rounds + 1):
                key = str(round_number)
                per_round_count[key] = per_round_count.get(key, 0) + 1
        split_record = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "split": split_name,
            "history_mode": "online_rollout_full",
            "record_level": "chain",
            "chain_count": row_count,
            "target_video_count": total_targets,
            "chain_length_count": chain_length_count,
            "targets_per_round": per_round_count,
            "parquet_file": str(parquet_path),
            "parquet_sha256": sha256_file(parquet_path),
            "source_prefix_count": int(
                split_manifest["splits"][split_name]["sample_count"]
            ),
        }
        atomic_json(manifest_path, split_record)
        source_yaml = resolve_from(
            split_root, split_manifest["splits"][split_name]["dataset_config"]
        )
        yaml_path = split_dir / "lance_dataset.yaml"
        yaml_text = build_dataset_yaml(source_yaml, parquet_path, manifest_path)
        yaml_path.write_text(yaml_text, encoding="utf-8")
        top_manifest["splits"][split_name] = {
            **split_record,
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "dataset_config": str(yaml_path),
            "dataset_config_sha256": sha256_file(yaml_path),
        }
        all_chain_ids[split_name] = {str(row["chain_id"]) for row in rows}

    for left_index, left in enumerate(SPLITS):
        for right in SPLITS[left_index + 1 :]:
            overlap = all_chain_ids[left] & all_chain_ids[right]
            if overlap:
                raise ValueError(f"chain leakage between {left} and {right}: {len(overlap)}")

    top_manifest_path = output_dir / "chain_dataset_manifest.json"
    atomic_json(top_manifest_path, top_manifest)
    return top_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build(args.split_manifest, args.output_dir.resolve())
    print(
        json.dumps(
            {
                "output": str((args.output_dir / "chain_dataset_manifest.json").resolve()),
                "splits": {
                    key: {
                        "chains": value["chain_count"],
                        "targets": value["target_video_count"],
                    }
                    for key, value in manifest["splits"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
