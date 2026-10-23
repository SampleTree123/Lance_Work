#!/usr/bin/env python3
"""Compile a released DataMake ``chains.json`` into Lance training parquet.

The parquet stores portable media paths instead of repeated MP4 bytes. One row
represents one chain prefix and therefore one supervised target round.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq
import yaml


SCHEMA_VERSION = "datamake_lance_multiturn_prefix_v1"
DEFAULT_LANGUAGES = ("en",)
PROMPT_VIEWS = ("dialogue", "standalone")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sample_id(
    chain_id: str,
    target_round: int,
    language: str,
    prompt_view: str,
    prompts: Sequence[str],
    video_paths: Sequence[str],
) -> str:
    payload = json.dumps(
        [
            SCHEMA_VERSION,
            chain_id,
            target_round,
            language,
            prompt_view,
            list(prompts),
            list(video_paths),
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "dmmt_" + hashlib.sha256(payload).hexdigest()[:20]


def read_chains(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty JSON array")
    if not all(isinstance(chain, dict) for chain in payload):
        raise ValueError(f"{path} contains a non-object chain entry")
    return payload


def select_prompt(turn: Dict[str, Any], prompt_view: str, language: str) -> str:
    if prompt_view == "dialogue":
        candidates = ("prompt", "user_prompt")
    elif prompt_view == "standalone":
        candidates = ("standalone_prompt",)
    else:
        raise ValueError(f"unsupported prompt view {prompt_view!r}")

    for key in candidates:
        prompt = turn.get(key)
        if isinstance(prompt, dict):
            value = prompt.get(language)
            if isinstance(value, str) and value.strip():
                return value.strip()
    raise ValueError(
        f"turn {turn.get('turn_id', turn.get('round'))!r} has no "
        f"{prompt_view}/{language} prompt"
    )


def resolve_package_media(package_root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid media path {value!r}")
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"delivery media path must be relative, got {value!r}")
    resolved = (package_root / relative).resolve()
    try:
        resolved.relative_to(package_root.resolve())
    except ValueError as error:
        raise ValueError(f"media path escapes package root: {value!r}") from error
    if not resolved.is_file():
        raise FileNotFoundError(f"delivery media is missing: {resolved}")
    return resolved


def validate_chain(chain: Dict[str, Any], package_root: Path) -> List[Dict[str, Any]]:
    chain_id = chain.get("chain_id")
    turns = chain.get("turns")
    if not isinstance(chain_id, str) or not chain_id:
        raise ValueError("chain_id must be a non-empty string")
    if not isinstance(turns, list) or not turns:
        raise ValueError(f"chain {chain_id} has no turns")
    if chain.get("edit_length") not in (None, len(turns)):
        raise ValueError(
            f"chain {chain_id} edit_length={chain.get('edit_length')} but has "
            f"{len(turns)} turns"
        )

    expected_input = chain.get("initial_video") or chain.get("initial_video_uri")
    if not isinstance(expected_input, str):
        raise ValueError(f"chain {chain_id} has no initial video")

    normalized: List[Dict[str, Any]] = []
    for expected_round, turn in enumerate(turns, start=1):
        if not isinstance(turn, dict):
            raise ValueError(f"chain {chain_id} round {expected_round} is not an object")
        if int(turn.get("round", -1)) != expected_round:
            raise ValueError(
                f"chain {chain_id} expected round {expected_round}, got "
                f"{turn.get('round')!r}"
            )
        video_in = turn.get("video_in") or turn.get("video_in_uri")
        video_out = turn.get("video_out") or turn.get("video_out_uri")
        if video_in != expected_input:
            raise ValueError(
                f"chain {chain_id} round {expected_round} breaks endpoint reuse: "
                f"expected {expected_input!r}, got {video_in!r}"
            )
        resolve_package_media(package_root, video_in)
        resolve_package_media(package_root, video_out)
        normalized.append({**turn, "video_in": video_in, "video_out": video_out})
        expected_input = video_out

    final_video = chain.get("final_video") or chain.get("final_video_uri")
    if final_video is not None and final_video != expected_input:
        raise ValueError(
            f"chain {chain_id} final video {final_video!r} does not match "
            f"last target {expected_input!r}"
        )
    return normalized


def build_rows(
    chains: Sequence[Dict[str, Any]],
    package_root: Path,
    languages: Sequence[str],
    prompt_view: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen_sample_ids = set()

    for chain in chains:
        turns = validate_chain(chain, package_root)
        chain_id = chain["chain_id"]
        for language in languages:
            prompts: List[str] = []
            video_paths: List[str] = [turns[0]["video_in"]]
            turn_ids: List[str] = []
            edit_axes: List[str] = []

            for turn in turns:
                selected_prompt = select_prompt(turn, prompt_view, language)
                if prompt_view == "dialogue":
                    prompts.append(selected_prompt)
                    video_paths.append(turn["video_out"])
                    turn_ids.append(str(turn.get("turn_id", "")))
                    edit_axes.append(str(turn.get("edit_axis", "")))
                else:
                    prompts = [selected_prompt]
                    video_paths = [turn["video_in"], turn["video_out"]]
                    turn_ids = [str(turn.get("turn_id", ""))]
                    edit_axes = [str(turn.get("edit_axis", ""))]
                target_round = int(turn["round"])
                sample_id = stable_sample_id(
                    chain_id,
                    target_round,
                    language,
                    prompt_view,
                    prompts,
                    video_paths,
                )
                if sample_id in seen_sample_ids:
                    raise ValueError(f"duplicate sample_id {sample_id}")
                seen_sample_ids.add(sample_id)

                rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "sample_id": sample_id,
                        "chain_id": chain_id,
                        "target_round": target_round,
                        "context_length": len(prompts),
                        "language": language,
                        "prompt_view": prompt_view,
                        "prompts": list(prompts),
                        "video_paths": list(video_paths),
                        "turn_ids": list(turn_ids),
                        "edit_axes": list(edit_axes),
                        "input_video_path": video_paths[-2],
                        "output_video_path": video_paths[-1],
                        "chain_policy": str(chain.get("chain_policy", "")),
                        "semantic_facts_json": json.dumps(
                            chain.get("semantic_facts", {}),
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    }
                )
    return rows


def build_lance_yaml(
    parquet_paths: Path | Sequence[Path], package_root: Path
) -> Dict[str, Any]:
    if isinstance(parquet_paths, Path):
        parquet_paths = [parquet_paths]
    return {
        "D1": {
            "datamake_multiturn_v2v_local": {
                "dataset_type": "datamake_multiturn_video2video",
                "raw_bytes_input": False,
                "media_root": str(package_root.resolve()),
                "is_image": False,
                "target_modality": "video",
                "task_type": "tv2v",
                "sample_task": "edit",
                "vision_cond_type": ["vit", "vae_Nsplit"],
                "text_template": True,
                "dataset_names": {
                    "datamake_multiturn": {
                        "data_dir": [str(path.resolve()) for path in parquet_paths]
                    }
                },
                "debug_parquet_repeat": 1,
                "video_transform_args": {
                    "resolution": 480,
                    "mode": "bucket",
                    "divisible_crop_size": 16,
                    "stride_spatial": 16,
                    "stride_temporal": 4,
                    "aspect_ratios": ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"],
                    "mean": 0.5,
                    "std": 0.5,
                },
                "vit_video_transform_args": {
                    "resolution": 448,
                    "mode": "bucket",
                    "divisible_crop_size": 28,
                    "aspect_ratios": ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"],
                    "mean": [0.48145466, 0.4578275, 0.40821073],
                    "std": [0.26862954, 0.26130258, 0.27577711],
                },
                "video_frame_sampler_args": {
                    "type": "multi_clips",
                    "res_dump": ["image_480p", "12fps_480p"],
                    "params": {
                        "temporal": 4,
                        "sample_fps": 12,
                        "max_duration": 6,
                        "assert_seconds": False,
                        "truncate": False,
                    },
                },
                "is_mandatory": False,
                "weight": 1.0,
            }
        }
    }


def parse_languages(values: Iterable[str]) -> List[str]:
    languages: List[str] = []
    for value in values:
        for language in value.split(","):
            language = language.strip()
            if language and language not in languages:
                languages.append(language)
    if not languages:
        raise ValueError("at least one language is required")
    return languages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chains", type=Path, required=True)
    parser.add_argument(
        "--package-root",
        type=Path,
        help="Delivery root containing chains.json and videos/; defaults to chains parent",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--language",
        action="append",
        default=[],
        help="Prompt language; repeat or use comma-separated values (default: en)",
    )
    parser.add_argument("--prompt-view", choices=PROMPT_VIEWS, default="dialogue")
    parser.add_argument("--row-group-size", type=int, default=128)
    return parser.parse_args()


def write_training_dataset(
    chains: Sequence[Dict[str, Any]],
    source_chains_path: Path,
    package_root: Path,
    output_dir: Path,
    languages: Sequence[str],
    prompt_view: str,
    row_group_size: int = 128,
    num_parquet_shards: int = 1,
    extra_manifest: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Write one path-referenced Lance dataset and return its manifest."""
    if row_group_size < 1:
        raise ValueError("row_group_size must be >= 1")
    if prompt_view not in PROMPT_VIEWS:
        raise ValueError(f"unsupported prompt view {prompt_view!r}")
    if num_parquet_shards < 1:
        raise ValueError("num_parquet_shards must be >= 1")

    source_chains_path = source_chains_path.resolve()
    package_root = package_root.resolve()
    output_dir = output_dir.resolve()
    rows = build_rows(chains, package_root, languages, prompt_view)
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = output_dir / "lance_dataset.yaml"
    manifest_path = output_dir / "manifest.json"

    if num_parquet_shards > len(rows):
        raise ValueError(
            f"num_parquet_shards={num_parquet_shards} exceeds row count={len(rows)}"
        )
    parquet_records = []
    offset = 0
    rows_per_shard, remainder = divmod(len(rows), num_parquet_shards)
    for shard_index in range(num_parquet_shards):
        shard_rows = rows_per_shard + (1 if shard_index < remainder else 0)
        next_offset = offset + shard_rows
        if num_parquet_shards == 1:
            parquet_path = output_dir / "datamake_multiturn.parquet"
        else:
            parquet_path = output_dir / (
                f"datamake_multiturn-{shard_index:05d}-of-{num_parquet_shards:05d}.parquet"
            )
        table = pa.Table.from_pylist(rows[offset:next_offset])
        pq.write_table(
            table,
            parquet_path,
            compression="zstd",
            row_group_size=row_group_size,
        )
        parquet_records.append(
            {
                "path": parquet_path.name,
                "sha256": sha256_file(parquet_path),
                "rows": shard_rows,
            }
        )
        offset = next_offset

    parquet_paths = [output_dir / record["path"] for record in parquet_records]
    with yaml_path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            build_lance_yaml(parquet_paths, package_root),
            stream,
            allow_unicode=True,
            sort_keys=False,
        )

    per_round: Dict[str, int] = {}
    for row in rows:
        key = str(row["target_round"])
        per_round[key] = per_round.get(key, 0) + 1
    package_scopes = sorted(
        {
            str(chain.get("package_scope", "unspecified"))
            for chain in chains
        }
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        "source_chains": str(source_chains_path),
        "source_chains_sha256": sha256_file(source_chains_path),
        "package_root": str(package_root),
        "prompt_view": prompt_view,
        "languages": list(languages),
        "chain_count": len(chains),
        "source_package_scopes": package_scopes,
        "sample_count": len(rows),
        "samples_per_target_round": per_round,
        "parquet_shard_count": num_parquet_shards,
        "parquet_files": parquet_records,
        "dataset_config": yaml_path.name,
        "media_storage": "path_reference_no_byte_duplication",
        "history_encoding": (
            "full_role_text_history_all_prior_vit_latest_source_vae"
            if prompt_view == "dialogue"
            else "single_turn_no_history_direct_source_vae"
        ),
    }
    if num_parquet_shards == 1:
        manifest["parquet"] = parquet_records[0]["path"]
        manifest["parquet_sha256"] = parquet_records[0]["sha256"]
    if extra_manifest:
        overlap = sorted(set(manifest) & set(extra_manifest))
        if overlap:
            raise ValueError(
                "extra manifest fields cannot replace base fields: "
                + ", ".join(overlap)
            )
        manifest.update(extra_manifest)
    with manifest_path.open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")

    return manifest


def main() -> int:
    args = parse_args()
    chains_path = args.chains.resolve()
    package_root = (args.package_root or chains_path.parent).resolve()
    output_dir = args.output_dir.resolve()
    languages = parse_languages(args.language or DEFAULT_LANGUAGES)
    if args.row_group_size < 1:
        raise ValueError("--row-group-size must be >= 1")

    chains = read_chains(chains_path)
    manifest = write_training_dataset(
        chains=chains,
        source_chains_path=chains_path,
        package_root=package_root,
        output_dir=output_dir,
        languages=languages,
        prompt_view=args.prompt_view,
        row_group_size=args.row_group_size,
        num_parquet_shards=1,
    )

    print(
        json.dumps(
            {
                "chains": manifest["chain_count"],
                "samples": manifest["sample_count"],
                "parquet": str(output_dir / manifest["parquet_files"][0]["path"]),
                "config": str(output_dir / manifest["dataset_config"]),
                "manifest": str(output_dir / "manifest.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
