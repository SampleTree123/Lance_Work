#!/usr/bin/env python3
"""Decode and pack one DataMake multi-turn parquet row with Lance's train path."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import pyarrow.parquet as pq


def locate_parquet_row(
    data_paths: Sequence[str | Path], global_row_index: int
) -> dict[str, Any]:
    """Load one row addressed across an ordered list of parquet files."""

    paths = [Path(path) for path in data_paths]
    if not paths:
        raise ValueError("inspection config contains no parquet files")
    if global_row_index < 0:
        raise IndexError(f"row index {global_row_index} must be non-negative")

    parquet_files = [pq.ParquetFile(path) for path in paths]
    total_rows = sum(parquet_file.metadata.num_rows for parquet_file in parquet_files)
    if global_row_index >= total_rows:
        raise IndexError(
            f"row index {global_row_index} outside 0..{total_rows - 1}"
        )

    remaining = global_row_index
    for parquet_idx, (path, parquet_file) in enumerate(zip(paths, parquet_files)):
        for row_group_id in range(parquet_file.num_row_groups):
            row_group_rows = parquet_file.metadata.row_group(row_group_id).num_rows
            if remaining < row_group_rows:
                row = parquet_file.read_row_group(row_group_id).slice(remaining, 1)
                return {
                    "row": row.to_pylist()[0],
                    "parquet_idx": parquet_idx,
                    "row_group_id": row_group_id,
                    "row_idx": remaining,
                    "parquet_path": path,
                    "global_row_index": global_row_index,
                    "total_rows": total_rows,
                }
            remaining -= row_group_rows

    raise RuntimeError("failed to locate a validated parquet row index")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    script_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--lance-root", type=Path, default=script_root / "lance")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=script_root / "lance" / "downloads" / "Lance_3B_Video",
    )
    parser.add_argument("--row-index", type=int, default=0)
    parser.add_argument("--max-num-tokens", type=int, default=65536)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lance_root = args.lance_root.resolve()
    sys.path.insert(0, str(lance_root))

    from data.data_utils import add_special_tokens
    from data.dataset_base_train import DataConfig, PackedDataset
    from modeling.qwen2 import Qwen2Tokenizer

    config_path = args.config.resolve()
    config = DataConfig.from_yaml(str(config_path))
    config.vit_patch_size = 14
    config.vit_patch_size_temporal = 2
    config.vit_max_num_patch_per_side = 70
    config.latent_patch_size = (1, 1, 1)
    config.vae_downsample = (4, 16, 16)
    config.max_latent_size = 64
    config.max_num_frames = 121
    config.text_cond_dropout_prob = 0.0
    config.vit_cond_dropout_prob = 0.0
    config.vae_cond_dropout_prob = 0.0

    model_path = args.model_path.resolve()
    with (model_path / "llm_config.json").open("r", encoding="utf-8") as stream:
        image_token_id = int(json.load(stream)["video_token_id"])
    tokenizer = Qwen2Tokenizer.from_pretrained(str(model_path))
    tokenizer, special_tokens, _ = add_special_tokens(tokenizer)
    packed_dataset = PackedDataset(
        config,
        tokenizer=tokenizer,
        special_tokens=special_tokens,
        local_rank=0,
        world_size=1,
        num_workers=0,
        expected_num_tokens=1,
        max_num_tokens_per_sample=args.max_num_tokens,
        max_num_tokens=args.max_num_tokens,
        prefer_buffer_before=1,
        max_buffer_size=2,
        interpolate_pos=False,
        use_flex=True,
        image_token_id=image_token_id,
    )
    raw_dataset = packed_dataset.grouped_datasets[0]
    location = locate_parquet_row(raw_dataset.data_paths, args.row_index)
    parquet_path = location["parquet_path"]
    row = location["row"]
    sample = raw_dataset._process_row(
        row,
        parquet_idx=location["parquet_idx"],
        row_group_id=location["row_group_id"],
        row_idx=location["row_idx"],
        worker_id=0,
        parquet_file_path=str(parquet_path),
    )
    if sample is None:
        raise RuntimeError(f"Lance rejected parquet row {args.row_index}")

    status = packed_dataset.pack_sequence(
        sample, packed_dataset.set_sequence_status()
    )
    plans = sample["sequence_plan"]
    clean_sources = sum(
        plan["type"] == "vae_video" and plan.get("loss") == 0
        for plan in plans
    )
    targets = sum(
        plan["type"] == "vae_video" and plan.get("loss") == 1
        for plan in plans
    )
    result = {
        "sample_id": row["sample_id"],
        "chain_id": row["chain_id"],
        "target_round": row["target_round"],
        "global_row_index": location["global_row_index"],
        "parquet_index": location["parquet_idx"],
        "parquet_path": str(parquet_path),
        "row_group_id": location["row_group_id"],
        "row_index_in_group": location["row_idx"],
        "packed_tokens": status["curr"],
        "max_num_tokens": args.max_num_tokens,
        "within_token_limit": status["curr"] < args.max_num_tokens,
        "vit_conditions": sum(plan["type"] == "vit_video" for plan in plans),
        "clean_vae_sources": clean_sources,
        "vae_targets": targets,
        "source_target_alignment": clean_sources == 1 and targets == 1,
        "plan_types": [plan["type"] for plan in plans],
        "plan_losses": [plan.get("loss") for plan in plans],
        "attention_modes": status["attn_modes"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["within_token_limit"] and result["source_target_alignment"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
