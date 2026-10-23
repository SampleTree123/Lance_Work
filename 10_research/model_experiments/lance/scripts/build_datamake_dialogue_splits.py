#!/usr/bin/env python3
"""Build deterministic chain-level train/validation/test dialogue splits.

The split is a seeded SHA-256 rank over ``chain_id``. It is independent of the
source JSON order, does not stratify by metadata, and keeps every prefix from a
chain in exactly one split. Media remain path references into the released
package and are never copied.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BUILDER_PATH = SCRIPT_DIR / "build_datamake_multiturn_training_data.py"
SPEC = importlib.util.spec_from_file_location("datamake_multiturn_builder", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)

SCHEMA_VERSION = "datamake_lance_chain_split_v1"
SPLIT_ALGORITHM = "sha256(seed_utf8 + null + chain_id_utf8), ascending"
SPLIT_ORDER = ("train", "validation", "test")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def split_rank(chain_id: str, seed: int) -> str:
    return sha256_bytes(f"{seed}\0{chain_id}".encode("utf-8"))


def deterministic_split(
    chains: Sequence[Dict[str, Any]],
    counts: Mapping[str, int],
    seed: int,
) -> Dict[str, List[Dict[str, Any]]]:
    if tuple(counts) != SPLIT_ORDER:
        raise ValueError(f"split counts must be ordered as {SPLIT_ORDER}")
    if any(not isinstance(value, int) or value < 1 for value in counts.values()):
        raise ValueError("all split counts must be positive integers")
    if sum(counts.values()) != len(chains):
        raise ValueError(
            f"split counts total {sum(counts.values())}, source has {len(chains)} chains"
        )

    by_id: Dict[str, Dict[str, Any]] = {}
    for chain in chains:
        chain_id = chain.get("chain_id")
        if not isinstance(chain_id, str) or not chain_id:
            raise ValueError("every chain must have a non-empty chain_id")
        if chain_id in by_id:
            raise ValueError(f"duplicate chain_id {chain_id}")
        by_id[chain_id] = chain

    ranked_ids = sorted(by_id, key=lambda value: (split_rank(value, seed), value))
    result: Dict[str, List[Dict[str, Any]]] = {}
    offset = 0
    for split_name in SPLIT_ORDER:
        next_offset = offset + counts[split_name]
        result[split_name] = [by_id[chain_id] for chain_id in ranked_ids[offset:next_offset]]
        offset = next_offset
    return result


def read_release_manifest(package_root: Path, chains_path: Path) -> Dict[str, Any]:
    manifest_path = package_root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"release manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "released":
        raise ValueError(
            f"source package must be released, got status={manifest.get('status')!r}"
        )
    expected = manifest.get("files", {}).get("chains.json", {}).get("sha256")
    actual = BUILDER.sha256_file(chains_path)
    if not isinstance(expected, str) or expected != actual:
        raise ValueError(
            f"release manifest chains hash mismatch: expected={expected!r}, actual={actual}"
        )
    return manifest


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def build_splits(
    chains_path: Path,
    package_root: Path,
    output_dir: Path,
    counts: Mapping[str, int],
    seed: int,
    languages: Sequence[str],
    row_group_size: int,
    train_parquet_shards: int,
) -> Dict[str, Any]:
    chains_path = chains_path.resolve()
    package_root = package_root.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to reuse output directory: {output_dir}")

    release_manifest = read_release_manifest(package_root, chains_path)
    chains = BUILDER.read_chains(chains_path)
    release_count = release_manifest.get("counts", {}).get("chains")
    if release_count != len(chains):
        raise ValueError(
            f"release manifest chain count={release_count!r}, source has {len(chains)}"
        )

    split_chains = deterministic_split(chains, counts, seed)
    source_ids = {chain["chain_id"] for chain in chains}
    split_id_sets = {
        name: {chain["chain_id"] for chain in subset}
        for name, subset in split_chains.items()
    }
    pairwise_disjoint = all(
        split_id_sets[left].isdisjoint(split_id_sets[right])
        for index, left in enumerate(SPLIT_ORDER)
        for right in SPLIT_ORDER[index + 1 :]
    )
    union_equals_source = set().union(*split_id_sets.values()) == source_ids
    if not pairwise_disjoint or not union_equals_source:
        raise RuntimeError("internal split audit failed")

    output_dir.mkdir(parents=True)
    split_records: Dict[str, Any] = {}
    all_sample_ids: set[str] = set()
    for split_name in SPLIT_ORDER:
        subset = split_chains[split_name]
        parquet_shards = train_parquet_shards if split_name == "train" else 1
        split_dir = output_dir / split_name
        split_dir.mkdir()
        chain_ids = [chain["chain_id"] for chain in subset]
        chain_ids_payload = {
            "schema_version": SCHEMA_VERSION,
            "split": split_name,
            "seed": seed,
            "algorithm": SPLIT_ALGORITHM,
            "chain_count": len(chain_ids),
            "chain_ids": chain_ids,
        }
        chain_ids_path = split_dir / "chain_ids.json"
        write_json(chain_ids_path, chain_ids_payload)

        rows = BUILDER.build_rows(subset, package_root, languages, "dialogue")
        sample_ids = {row["sample_id"] for row in rows}
        if len(sample_ids) != len(rows):
            raise RuntimeError(f"duplicate sample IDs inside {split_name}")
        if all_sample_ids & sample_ids:
            raise RuntimeError(f"sample ID leakage into {split_name}")
        all_sample_ids.update(sample_ids)

        manifest = BUILDER.write_training_dataset(
            chains=subset,
            source_chains_path=chains_path,
            package_root=package_root,
            output_dir=split_dir,
            languages=languages,
            prompt_view="dialogue",
            row_group_size=row_group_size,
            num_parquet_shards=parquet_shards,
            extra_manifest={
                "split_schema_version": SCHEMA_VERSION,
                "split": split_name,
                "split_seed": seed,
                "split_algorithm": SPLIT_ALGORITHM,
                "chain_ids_file": chain_ids_path.name,
                "chain_ids_file_sha256": BUILDER.sha256_file(chain_ids_path),
                "chain_ids_canonical_sha256": canonical_json_sha256(chain_ids),
                "source_release_manifest": str((package_root / "manifest.json").resolve()),
                "source_release_manifest_sha256": BUILDER.sha256_file(
                    package_root / "manifest.json"
                ),
            },
        )
        if manifest["sample_count"] != len(rows):
            raise RuntimeError(f"sample count changed while writing {split_name}")
        split_records[split_name] = {
            "chain_count": manifest["chain_count"],
            "sample_count": manifest["sample_count"],
            "samples_per_target_round": manifest["samples_per_target_round"],
            "chain_ids": str(chain_ids_path.relative_to(output_dir)),
            "chain_ids_sha256": BUILDER.sha256_file(chain_ids_path),
            "parquet_shard_count": manifest["parquet_shard_count"],
            "parquet_files": [
                {
                    **record,
                    "path": str((split_dir / record["path"]).relative_to(output_dir)),
                }
                for record in manifest["parquet_files"]
            ],
            "dataset_config": str(
                (split_dir / manifest["dataset_config"]).relative_to(output_dir)
            ),
            "manifest": str((split_dir / "manifest.json").relative_to(output_dir)),
            "manifest_sha256": BUILDER.sha256_file(split_dir / "manifest.json"),
        }

    total_turns = sum(len(chain["turns"]) for chain in chains)
    split_sample_total = sum(
        record["sample_count"] for record in split_records.values()
    )
    prefix_coverage = split_sample_total == total_turns == len(all_sample_ids)
    if not prefix_coverage:
        raise RuntimeError(
            f"prefix coverage failed: splits={split_sample_total}, turns={total_turns}, "
            f"unique_samples={len(all_sample_ids)}"
        )

    top_manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_by": str(Path(__file__).resolve()),
        "builder_sha256": BUILDER.sha256_file(Path(__file__).resolve()),
        "source_chains": str(chains_path),
        "source_chains_sha256": BUILDER.sha256_file(chains_path),
        "source_release_manifest": str((package_root / "manifest.json").resolve()),
        "source_release_manifest_sha256": BUILDER.sha256_file(
            package_root / "manifest.json"
        ),
        "source_release_status": release_manifest["status"],
        "package_root": str(package_root),
        "prompt_view": "dialogue",
        "languages": list(languages),
        "seed": seed,
        "algorithm": SPLIT_ALGORITHM,
        "stratified": False,
        "source_chain_count": len(chains),
        "source_sample_count": total_turns,
        "splits": split_records,
        "audit": {
            "exact_requested_chain_counts": all(
                split_records[name]["chain_count"] == counts[name]
                for name in SPLIT_ORDER
            ),
            "pairwise_chain_disjoint": pairwise_disjoint,
            "chain_union_equals_source": union_equals_source,
            "all_prefixes_grouped_by_chain": True,
            "pairwise_sample_disjoint": len(all_sample_ids) == split_sample_total,
            "prefix_union_equals_source_turns": prefix_coverage,
            "media_storage": "shared_release_paths_no_copy",
        },
        "training_math": {
            "train_parquet_shards": train_parquet_shards,
            "global_batch_size_4_train_steps_ceil": math.ceil(
                split_records["train"]["sample_count"] / 4
            )
        },
    }
    write_json(output_dir / "split_manifest.json", top_manifest)
    return top_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chains", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--train-chains", type=int, default=3600)
    parser.add_argument("--validation-chains", type=int, default=200)
    parser.add_argument("--test-chains", type=int, default=200)
    parser.add_argument("--language", action="append", default=[])
    parser.add_argument("--row-group-size", type=int, default=128)
    parser.add_argument(
        "--train-parquet-shards",
        type=int,
        default=8,
        help="Train files; 8 supports 4 ranks x 2 DataLoader workers without empty shards",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chains_path = args.chains.resolve()
    package_root = (args.package_root or chains_path.parent).resolve()
    languages = BUILDER.parse_languages(args.language or BUILDER.DEFAULT_LANGUAGES)
    manifest = build_splits(
        chains_path=chains_path,
        package_root=package_root,
        output_dir=args.output_dir,
        counts={
            "train": args.train_chains,
            "validation": args.validation_chains,
            "test": args.test_chains,
        },
        seed=args.seed,
        languages=languages,
        row_group_size=args.row_group_size,
        train_parquet_shards=args.train_parquet_shards,
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "seed": manifest["seed"],
                "splits": {
                    name: {
                        "chains": record["chain_count"],
                        "samples": record["sample_count"],
                    }
                    for name, record in manifest["splits"].items()
                },
                "train_steps_global_batch_4": manifest["training_math"][
                    "global_batch_size_4_train_steps_ceil"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
