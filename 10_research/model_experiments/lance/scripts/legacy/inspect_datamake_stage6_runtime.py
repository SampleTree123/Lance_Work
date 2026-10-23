#!/usr/bin/env python3
"""CPU-only Stage6 target topology and real-media indexed-prefix pack check."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import torch
from safetensors import safe_open

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lance"))
from run_datamake_stage2_lora_training import load_profile, workspace_path
from train.datamake_branch_lora import (
    apply_branch_lora, config_from_profile, is_generation_target, is_understanding_target,
)
from train.datamake_stage2_lora_train import recipe_arguments
from train.datamake_stage2_lora_data import IndexedPrefixDataset
from train.train_utils import build_train_dataset_config
from data.dataset_base_train import PackedDataset, simple_custom_collate
from data.data_utils import add_special_tokens
from modeling.qwen2 import Qwen2Tokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    profile = load_profile(args.profile)
    base = workspace_path(profile["model"]["model_path"])
    model = torch.nn.Module()
    with safe_open(str(base / "model.safetensors"), framework="pt", device="cpu") as source:
        for key in source.keys():
            if not key.endswith(".weight"):
                continue
            name = key[:-7]
            if not (is_generation_target(name) or is_understanding_target(name)):
                continue
            out_features, in_features = source.get_slice(key).get_shape()
            parent = model
            segments = name.split(".")
            for segment in segments[:-1]:
                if not hasattr(parent, segment):
                    parent.add_module(segment, torch.nn.Module())
                parent = getattr(parent, segment)
            parent.add_module(segments[-1], torch.nn.Linear(in_features, out_features, bias=False, device="meta"))
    targets = apply_branch_lora(model, config_from_profile(profile))
    count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    expected = profile["lora"]["architecture_audit"][
        "generation_r64_parameters" if profile["freeze"]["understanding_adapters"] else "all_branch_r64_parameters"]
    assert count == expected, (count, expected)
    print(json.dumps({"target_modules": len(targets), "adapter_parameters": count}), flush=True)
    m, d, t = recipe_arguments(profile)
    tokenizer, specials, _ = add_special_tokens(Qwen2Tokenizer.from_pretrained(str(base)))
    config = build_train_dataset_config(d, m, t, SimpleNamespace(downsample_temporal=4, downsample_spatial=16))
    image_token_id = json.loads((base / "llm_config.json").read_text())["video_token_id"]
    packer = PackedDataset(
        config, tokenizer=tokenizer, special_tokens=specials, local_rank=0, world_size=4,
        interpolate_pos=m.interpolate_pos, use_flex=t.use_flex, data_status=None,
        apply_chat_template=False, image_token_id=image_token_id,
        cfg_type=t.cfg_type, cfg_uncond_token_id=t.cfg_uncond_token_id, **asdict(d),
    )
    packer.set_epoch(d.data_seed)
    dataset = IndexedPrefixDataset(packer, 24000, d.data_seed)
    # Spawn workers just like training. Check resumed absolute microstep16
    # against a direct pack, independent of the worker's prefetch position.
    expected_pack = dataset[16]
    expected_ids = expected_pack["packed_text_ids"].clone()
    expected_video = expected_pack["padded_videos"][0].clone()
    del expected_pack
    loader = torch.utils.data.DataLoader(dataset, sampler=[16, 17], batch_size=1,
        num_workers=2, multiprocessing_context="spawn", prefetch_factor=2,
        collate_fn=simple_custom_collate, generator=torch.Generator().manual_seed(2081))
    for i, batch in enumerate(loader):
        data = batch.to_dict()
        assert data["vae_edit_roles"] == ["source", "target"], data["vae_edit_roles"]
        assert len(data["batch_data_indexes"]) == 1
        if i == 0:
            assert torch.equal(data["packed_text_ids"], expected_ids)
            assert torch.equal(data["padded_videos"][0], expected_video)
        print(json.dumps({"microstep": 16 + i, "sample": data["batch_data_indexes"],
                          "vae_roles": data["vae_edit_roles"],
                          "sample_lens": data["sample_lens"],
                          "video_shapes": [list(v.shape) for v in data["padded_videos"]]}), flush=True)
    print("CPU_STAGE6_TOPOLOGY_PACK_AND_PREFETCH_RESUME=PASSED", flush=True)


if __name__ == "__main__":
    raise SystemExit("Archived implementation: restore the complete source snapshot to reproduce it; use current DDP entry points for new work.")
    main()
