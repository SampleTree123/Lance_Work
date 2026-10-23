#!/usr/bin/env python3
"""Build a deterministic training-only round-oversampled DataMake parquet set.

Validation and test data are never rewritten. Media remain references to the
released package; only lightweight parquet rows are duplicated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq
import yaml


SCHEMA_VERSION = "datamake_lance_round_oversample_v1"


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


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def parse_round_repeats(values: Sequence[str]) -> Dict[int, int]:
    repeats = {round_index: 1 for round_index in range(1, 6)}
    for value in values:
        try:
            round_text, repeat_text = value.split("=", 1)
            round_index = int(round_text)
            repeat = int(repeat_text)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid round repeat {value!r}; expected ROUND=COUNT"
            ) from exc
        if round_index not in repeats:
            raise ValueError(f"round must be in 1..5, got {round_index}")
        if repeat < 1:
            raise ValueError(f"repeat count must be >= 1, got {repeat}")
        repeats[round_index] = repeat
    return repeats


def deterministic_instance_rank(instance_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}\0{instance_id}".encode("utf-8")).hexdigest()


def expand_and_shuffle_rows(
    rows: Sequence[Mapping[str, Any]],
    round_repeats: Mapping[int, int],
    seed: int,
) -> List[Dict[str, Any]]:
    expanded: List[Dict[str, Any]] = []
    seen_sample_ids: set[str] = set()
    for source_row in rows:
        row = dict(source_row)
        sample_id = str(row["sample_id"])
        target_round = int(row["target_round"])
        if sample_id in seen_sample_ids:
            raise ValueError(f"source train data has duplicate sample_id {sample_id}")
        if target_round not in round_repeats:
            raise ValueError(f"no repeat policy for target round {target_round}")
        seen_sample_ids.add(sample_id)
        for repeat_index in range(int(round_repeats[target_round])):
            instance = dict(row)
            instance_id = f"{sample_id}::repeat{repeat_index}"
            instance["sampling_repeat_index"] = repeat_index
            instance["sampling_instance_id"] = instance_id
            expanded.append(instance)
    expanded.sort(
        key=lambda row: (
            deterministic_instance_rank(row["sampling_instance_id"], seed),
            row["sampling_instance_id"],
        )
    )
    return expanded


def allocation_for_seed(
    shard_rows: Sequence[int],
    data_seed: int,
    total_steps: int,
    ranks: int = 4,
    workers_per_rank: int = 2,
) -> Dict[str, Any] | None:
    records = list(enumerate(shard_rows))
    random.Random(data_seed).shuffle(records)
    worker_quotas = [
        (total_steps + workers_per_rank - 1 - worker_id) // workers_per_rank
        for worker_id in range(workers_per_rank)
    ]
    if len(records) != ranks * workers_per_rank:
        raise ValueError("shard count must equal ranks times workers per rank")
    worker_rows: List[List[int]] = []
    rank_rows: List[int] = []
    for rank in range(ranks):
        assigned = records[
            rank * workers_per_rank : (rank + 1) * workers_per_rank
        ]
        rows = [record[1] for record in assigned]
        if any(value > worker_quotas[index] for index, value in enumerate(rows)):
            return None
        worker_rows.append(rows)
        rank_rows.append(sum(rows))
    return {
        "data_seed": data_seed,
        "rank_rows": rank_rows,
        "worker_rows": worker_rows,
        "worker_step_quotas": worker_quotas,
        "padding_repeats": total_steps * ranks - sum(shard_rows),
    }


def choose_data_seed(
    shard_rows: Sequence[int],
    total_steps: int,
    first_seed: int,
) -> Dict[str, Any]:
    for data_seed in range(first_seed, first_seed + 100000):
        allocation = allocation_for_seed(shard_rows, data_seed, total_steps)
        if allocation is not None:
            return allocation
    raise RuntimeError("could not find a distributed data seed without omitted rows")


def build_weighted_train(
    source_split_manifest: Path,
    output_dir: Path,
    round_repeats: Mapping[int, int],
    sampling_seed: int,
    first_data_seed: int,
    parquet_shards: int = 8,
    row_group_size: int = 128,
) -> Dict[str, Any]:
    source_split_manifest = source_split_manifest.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to reuse output directory: {output_dir}")
    if parquet_shards != 8:
        raise ValueError("formal 4-rank x 2-worker training requires exactly 8 shards")
    if row_group_size < 1:
        raise ValueError("row_group_size must be >= 1")

    split_manifest = read_json(source_split_manifest)
    train_record = split_manifest["splits"]["train"]
    source_root = source_split_manifest.parent
    source_parquets = [
        (source_root / record["path"]).resolve()
        for record in train_record["parquet_files"]
    ]
    for path, record in zip(source_parquets, train_record["parquet_files"]):
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256_file(path) != record["sha256"]:
            raise ValueError(f"source parquet hash mismatch: {path}")

    table = pq.read_table(source_parquets)
    source_rows = table.to_pylist()
    if len(source_rows) != int(train_record["sample_count"]):
        raise ValueError("source train row count does not match split manifest")
    weighted_rows = expand_and_shuffle_rows(source_rows, round_repeats, sampling_seed)

    output_dir.mkdir(parents=True)
    train_dir = output_dir / "train"
    train_dir.mkdir()
    rows_per_shard, remainder = divmod(len(weighted_rows), parquet_shards)
    shard_sizes = [
        rows_per_shard + (1 if index < remainder else 0)
        for index in range(parquet_shards)
    ]
    total_steps = math.ceil(len(weighted_rows) / 4)
    allocation = choose_data_seed(shard_sizes, total_steps, first_data_seed)

    parquet_records: List[Dict[str, Any]] = []
    offset = 0
    for shard_index, shard_size in enumerate(shard_sizes):
        next_offset = offset + shard_size
        path = train_dir / (
            f"datamake_multiturn-{shard_index:05d}-of-{parquet_shards:05d}.parquet"
        )
        pq.write_table(
            pa.Table.from_pylist(weighted_rows[offset:next_offset]),
            path,
            compression="zstd",
            row_group_size=row_group_size,
        )
        parquet_records.append(
            {
                "path": str(path.relative_to(output_dir)),
                "rows": shard_size,
                "sha256": sha256_file(path),
            }
        )
        offset = next_offset

    source_train_config = (source_root / train_record["dataset_config"]).resolve()
    config = yaml.safe_load(source_train_config.read_text(encoding="utf-8"))
    dataset = config["D1"]["datamake_multiturn_v2v_local"]
    dataset["dataset_names"]["datamake_multiturn"]["data_dir"] = [
        str((output_dir / record["path"]).resolve()) for record in parquet_records
    ]
    train_config = train_dir / "lance_dataset.yaml"
    with train_config.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(config, stream, allow_unicode=True, sort_keys=False)

    source_per_round = {
        str(key): int(value)
        for key, value in train_record["samples_per_target_round"].items()
    }
    effective_per_round = {
        key: source_per_round[key] * int(round_repeats[int(key)])
        for key in sorted(source_per_round, key=int)
    }
    unique_sample_ids = {str(row["sample_id"]) for row in weighted_rows}
    instance_ids = {str(row["sampling_instance_id"]) for row in weighted_rows}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_by": str(Path(__file__).resolve()),
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        "source_split_manifest": str(source_split_manifest),
        "source_split_manifest_sha256": sha256_file(source_split_manifest),
        "source_train_config": str(source_train_config),
        "source_train_config_sha256": sha256_file(source_train_config),
        "source_train_chains": int(train_record["chain_count"]),
        "source_train_rows": len(source_rows),
        "source_samples_per_target_round": source_per_round,
        "round_repeats": {str(key): int(value) for key, value in round_repeats.items()},
        "sampling_seed": sampling_seed,
        "sampling_algorithm": "sha256(seed_utf8 + null + sampling_instance_id_utf8), ascending",
        "effective_train_rows": len(weighted_rows),
        "effective_samples_per_target_round": effective_per_round,
        "unique_source_sample_ids": len(unique_sample_ids),
        "unique_sampling_instance_ids": len(instance_ids),
        "parquet_shard_count": parquet_shards,
        "parquet_files": parquet_records,
        "dataset_config": str(train_config.relative_to(output_dir)),
        "dataset_config_sha256": sha256_file(train_config),
        "global_batch_size": 4,
        "one_epoch_total_steps": total_steps,
        "distributed_allocation": allocation,
        "audit": {
            "all_source_rows_present": len(unique_sample_ids) == len(source_rows),
            "all_sampling_instances_unique": len(instance_ids) == len(weighted_rows),
            "only_round_five_oversampled": all(
                int(round_repeats[index]) == (3 if index == 5 else 1)
                for index in range(1, 6)
            ),
            "validation_and_test_unchanged": True,
            "media_storage": "shared_release_paths_no_copy",
            "one_epoch_has_only_synchronization_padding": allocation[
                "padding_repeats"
            ]
            == total_steps * 4 - len(weighted_rows),
        },
    }
    if not all(manifest["audit"].values()):
        raise RuntimeError(f"weighted train audit failed: {manifest['audit']}")
    write_json(output_dir / "sampling_manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-split-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--round-repeat", action="append", default=["5=3"])
    parser.add_argument("--sampling-seed", type=int, default=2041)
    parser.add_argument("--first-data-seed", type=int, default=2041)
    parser.add_argument("--parquet-shards", type=int, default=8)
    parser.add_argument("--row-group-size", type=int, default=128)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_weighted_train(
        source_split_manifest=args.source_split_manifest,
        output_dir=args.output_dir,
        round_repeats=parse_round_repeats(args.round_repeat),
        sampling_seed=args.sampling_seed,
        first_data_seed=args.first_data_seed,
        parquet_shards=args.parquet_shards,
        row_group_size=args.row_group_size,
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "effective_train_rows": manifest["effective_train_rows"],
                "one_epoch_total_steps": manifest["one_epoch_total_steps"],
                "data_seed": manifest["distributed_allocation"]["data_seed"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
