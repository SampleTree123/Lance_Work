#!/usr/bin/env python3
"""Pack every round of one chain using in-memory simulated rollout history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

import torch


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHAIN_ROOT = (
    ROOT
    / "outputs/training_data/"
    "datamake_dialogue_first_batch_v002_chain_seed2026_20260904/train"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_CHAIN_ROOT / "manifest.json")
    parser.add_argument("--config", type=Path, default=DEFAULT_CHAIN_ROOT / "lance_dataset.yaml")
    parser.add_argument("--model-path", type=Path, default=ROOT / "lance/downloads/Lance_3B_Video")
    parser.add_argument("--chain-length", type=int, default=5)
    parser.add_argument("--max-num-tokens", type=int, default=65536)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lance_root = ROOT / "lance"
    sys.path.insert(0, str(lance_root))

    from data.data_utils import add_special_tokens
    from data.dataset_base_train import DataConfig, PackedDataset
    from data.datasets_factory.datamake_online_rollout_turn import (
        get_online_video_tensor,
        process_online_rollout_row,
    )
    from modeling.qwen2 import Qwen2Tokenizer
    from train.datamake_online_rollout import load_chain_records, make_turn_row

    records, _manifest = load_chain_records(args.manifest)
    record = next(
        value for value in records if value.round_count == args.chain_length
    )
    config = DataConfig.from_yaml(str(args.config.resolve()))
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

    with (args.model_path / "llm_config.json").open(encoding="utf-8") as stream:
        image_token_id = int(json.load(stream)["video_token_id"])
    tokenizer = Qwen2Tokenizer.from_pretrained(str(args.model_path.resolve()))
    tokenizer, special_tokens, _ = add_special_tokens(tokenizer)
    packer = PackedDataset(
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
        max_buffer_size=0,
        interpolate_pos=False,
        use_flex=True,
        image_token_id=image_token_id,
    )
    row_encoder = packer.grouped_datasets[0]
    random.seed(2026)
    torch.manual_seed(2026)

    generated_history = []
    rounds = []
    for round_number in range(1, record.round_count + 1):
        row = make_turn_row(record, round_number, generated_history)
        sample = process_online_rollout_row(
            row_encoder,
            row,
            -1,
            -1,
            round_number - 1,
            0,
            "<online-pack-audit>",
        )
        if sample is None:
            raise RuntimeError(f"round {round_number} was rejected")
        packed = packer.pack_sequence(sample, packer.set_sequence_status())
        plans = sample["sequence_plan"]
        rounds.append(
            {
                "round": round_number,
                "packed_tokens": packed["curr"],
                "within_limit": packed["curr"] <= args.max_num_tokens,
                "vit_conditions": sum(item["type"] == "vit_video" for item in plans),
                "vae_sources": sum(
                    item["type"] == "vae_video"
                    and item.get("datamake_edit_role") == "source"
                    for item in plans
                ),
                "vae_targets": sum(
                    item["type"] == "vae_video"
                    and item.get("datamake_edit_role") == "target"
                    for item in plans
                ),
            }
        )
        if round_number < record.round_count:
            # A normalized GT frame tensor is used only as a shape/range stand-in
            # for the model-decoded tensor; no semantic quality claim is made.
            tensor, _tokens, _thw = get_online_video_tensor(
                row_encoder, record.video_paths[round_number], "vae_video", 0, {}
            )
            generated_history.append(tensor.to(dtype=torch.float16))

    result = {
        "chain_id": record.chain_id,
        "chain_length": record.round_count,
        "history_transport": "in_memory_cthw_float16_simulated",
        "semantic_rollout_generated": False,
        "rounds": rounds,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    healthy = all(
        item["within_limit"]
        and item["vit_conditions"] == item["round"]
        and item["vae_sources"] == 1
        and item["vae_targets"] == 1
        for item in rounds
    )
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
