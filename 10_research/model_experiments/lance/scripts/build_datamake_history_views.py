#!/usr/bin/env python3
"""Build explicit teacher-forced and model-rollout Lance training views.

The source DataMake parquet uses ``video_paths=[v0, ..., vt]`` for target round
``t``.  ``v0..v(t-1)`` are conditions and ``vt`` is always the rendered ground
truth target.  This builder never replaces the target.

Modes:

``teacher_forced``
    Keep all rendered conditions. This is the current training behavior.

``rollout_vit_only``
    Replace older history ``v1..v(t-2)`` with frozen-model outputs, but keep the
    latest direct VAE source ``v(t-1)`` rendered. This isolates noisy semantic
    history while preserving exact source-target pairing.

``rollout_full``
    Replace ``v1..v(t-1)`` with frozen-model outputs. This matches deployment,
    but the rendered target no longer forms an exact atomic pair with the latest
    generated source. Region-weighted loss must therefore be disabled unless a
    separate rendered mask reference is implemented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import pyarrow as pa
import pyarrow.parquet as pq
import yaml


SCHEMA_VERSION = "datamake_lance_history_view_v1"
ROLLOUT_SCHEMA_VERSION = "datamake_lance_rollout_media_v1"
VALID_MODES = ("teacher_forced", "rollout_vit_only", "rollout_full")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def read_source_config(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        dataset = payload["D1"]["datamake_multiturn_v2v_local"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"unsupported Lance dataset YAML: {path}") from error
    paths = dataset["dataset_names"]["datamake_multiturn"]["data_dir"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("source YAML must contain a non-empty parquet path list")
    return payload, dataset


def load_rollouts(
    paths: List[Path],
) -> Tuple[Dict[Tuple[str, int], str], List[Dict[str, Any]]]:
    lookup: Dict[Tuple[str, int], str] = {}
    payloads = []
    shared_contract = None
    for path in paths:
        payload = read_json(path)
        if payload.get("schema_version") != ROLLOUT_SCHEMA_VERSION:
            raise ValueError(f"unsupported rollout manifest schema: {path}")
        contract = {
            "source_config_sha256": payload.get("source_config_sha256"),
            "checkpoint": payload.get("checkpoint"),
            "inference": payload.get("inference"),
            "shard_count": payload.get("shard_count"),
        }
        if shared_contract is None:
            shared_contract = contract
        elif contract != shared_contract:
            raise ValueError(f"rollout shard contract mismatch: {path}")
        payloads.append(payload)
        for chain in payload.get("chains", []):
            chain_id = str(chain["chain_id"])
            for item in chain.get("round_outputs", []):
                key = (chain_id, int(item["round"]))
                if key in lookup:
                    raise ValueError(f"duplicate rollout entry: {key}")
                media = Path(item["output_video"]).resolve()
                if not media.is_file():
                    raise FileNotFoundError(media)
                expected_hash = item.get("sha256")
                if expected_hash and sha256_file(media) != expected_hash:
                    raise ValueError(f"rollout hash mismatch: {media}")
                lookup[key] = str(media)
    return lookup, payloads


def replace_conditions(
    row: Mapping[str, Any],
    mode: str,
    rollout_lookup: Mapping[Tuple[str, int], str],
) -> Tuple[Dict[str, Any], int]:
    original = list(row["video_paths"])
    target_round = int(row["target_round"])
    if len(original) != target_round + 1:
        raise ValueError(
            f"{row['sample_id']}: video path count does not match target round"
        )
    updated = dict(row)
    updated["ground_truth_video_paths"] = original
    updated["condition_history_mode"] = mode

    paths = list(original)
    if mode == "teacher_forced" or target_round == 1:
        replace_rounds: Iterable[int] = ()
    elif mode == "rollout_vit_only":
        replace_rounds = range(1, target_round - 1)
    elif mode == "rollout_full":
        replace_rounds = range(1, target_round)
    else:
        raise ValueError(f"unsupported history mode: {mode}")

    replacements = 0
    for source_round in replace_rounds:
        key = (str(row["chain_id"]), source_round)
        if key not in rollout_lookup:
            raise KeyError(f"missing rollout video for {key}")
        paths[source_round] = rollout_lookup[key]
        replacements += 1

    # The final rendered target is immutable in every arm.
    if paths[-1] != original[-1]:
        raise RuntimeError("history builder must never replace the target video")
    updated["video_paths"] = paths
    updated["rollout_condition_count"] = replacements
    updated["direct_source_is_ground_truth"] = (
        mode != "rollout_full" or target_round == 1
    )
    return updated, replacements


def write_view(
    mode: str,
    source_yaml: Dict[str, Any],
    source_shards: List[Path],
    output_root: Path,
    rollout_lookup: Mapping[Tuple[str, int], str],
    rollout_manifests: List[Path],
) -> Dict[str, Any]:
    view_root = output_root / mode
    parquet_root = view_root / "train"
    parquet_root.mkdir(parents=True, exist_ok=True)
    output_shards: List[Dict[str, Any]] = []
    total_rows = 0
    total_replacements = 0

    for index, source_path in enumerate(source_shards):
        rows = pq.read_table(source_path).to_pylist()
        converted = []
        for row in rows:
            item, replacements = replace_conditions(row, mode, rollout_lookup)
            converted.append(item)
            total_replacements += replacements
        output_path = parquet_root / f"part-{index:05d}.parquet"
        pq.write_table(
            pa.Table.from_pylist(converted),
            output_path,
            compression="zstd",
            use_dictionary=True,
        )
        total_rows += len(converted)
        output_shards.append(
            {
                "path": str(output_path.resolve()),
                "rows": len(converted),
                "sha256": sha256_file(output_path),
            }
        )

    output_yaml = json.loads(json.dumps(source_yaml))
    dataset = output_yaml["D1"]["datamake_multiturn_v2v_local"]
    dataset["dataset_names"]["datamake_multiturn"]["data_dir"] = [
        item["path"] for item in output_shards
    ]
    config_path = view_root / "lance_dataset.yaml"
    config_path.write_text(
        yaml.safe_dump(output_yaml, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "source_shards": [
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
            }
            for path in source_shards
        ],
        "rollout_manifests": [str(path.resolve()) for path in rollout_manifests],
        "rollout_manifest_sha256": {
            str(path.resolve()): sha256_file(path) for path in rollout_manifests
        },
        "rows": total_rows,
        "condition_replacements": total_replacements,
        "target_policy": "always_rendered_ground_truth",
        "direct_source_policy": (
            "generated_for_round_gt_1"
            if mode == "rollout_full"
            else "rendered_ground_truth"
        ),
        "edit_region_weighting_compatible": mode != "rollout_full",
        "lance_dataset_config": str(config_path.resolve()),
        "lance_dataset_config_sha256": sha256_file(config_path),
        "parquet_files": output_shards,
    }
    manifest_path = view_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--mode",
        action="append",
        choices=VALID_MODES,
        required=True,
        help="Repeat to build more than one arm.",
    )
    parser.add_argument(
        "--rollout-manifest",
        type=Path,
        action="append",
        default=[],
        help="Repeat for independently generated rollout shards.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_config = args.source_config.resolve()
    source_yaml, source_dataset = read_source_config(source_config)
    source_shards = [
        Path(path).resolve()
        for path in source_dataset["dataset_names"]["datamake_multiturn"][
            "data_dir"
        ]
    ]
    for path in source_shards:
        if not path.is_file():
            raise FileNotFoundError(path)

    needs_rollout = any(mode != "teacher_forced" for mode in args.mode)
    rollout_manifests = [path.resolve() for path in args.rollout_manifest]
    if needs_rollout and not rollout_manifests:
        raise ValueError("rollout modes require at least one --rollout-manifest")
    rollout_lookup: Dict[Tuple[str, int], str] = {}
    if rollout_manifests:
        rollout_lookup, _ = load_rollouts(rollout_manifests)

    output_root = args.output_dir.resolve()
    results = {}
    for mode in dict.fromkeys(args.mode):
        results[mode] = write_view(
            mode=mode,
            source_yaml=source_yaml,
            source_shards=source_shards,
            output_root=output_root,
            rollout_lookup=rollout_lookup,
            rollout_manifests=rollout_manifests,
        )
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
