#!/usr/bin/env python3
"""Tiny real packed-data/LoRA backward check; never saves model weights.

Owner: ../training_integration.md. Artificial identity target tests wiring only.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--fixture", required=True, help="Existing engineering_source.mp4 and red.png directory")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    lance = Path(__file__).resolve().parents[1]
    checkpoint, fixture, output = (Path(value).resolve() for value in (args.checkpoint, args.fixture, args.output))
    output.mkdir(parents=True, exist_ok=True)
    if (output / "evidence.json").exists():
        raise FileExistsError("Use a fresh output directory")
    os.chdir(lance / "lance")
    sys.path[:0] = [str(lance / "lance"), str(lance / "runtime/peft_0_15_2")]
    import pyarrow as pa
    import pyarrow.parquet as pq
    import torch
    import yaml
    from transformers import set_seed
    from config.config_factory import DataArguments, InferenceArguments, ModelArguments
    from train.datamake_peft import install_inference_loader
    from train.datamake_branch_lora import is_generation_target, is_understanding_target
    from multiturn.engine import MultiTurnChatEngine
    from data.dataset_base_train import DataConfig, PackedDataset, simple_custom_collate
    from data.datasets_factory.dataset_datamake_mixed_v2v_local import register_mixed_dataset
    from train.datamake_packed_batch import trim_attention_padding
    from common.val.utils import make_padded_latent
    register_mixed_dataset()
    set_seed(42)
    torch.cuda.set_device(0)
    base = str(lance / "models/Lance/Lance_3B_Video")
    model_args = ModelArguments(
        model_path=base, llm_path=base, vit_path=str(lance / "models/Lance/Qwen2.5-VL-ViT"),
        vit_type="qwen_2_5_vl_original", llm_qk_norm=True, llm_qk_norm_und=True,
        llm_qk_norm_gen=True, tie_word_embeddings=False, max_num_frames=121,
        max_latent_size=64, latent_patch_size=[1, 1, 1], cfg_text_scale=1.0)
    inference_args = InferenceArguments(
        copy_init_moe=True, visual_und=True, visual_gen=True, vae_model_type="wan",
        apply_qwen_2_5_vl_pos_emb=True, apply_chat_template=False, cfg_type=0,
        resolution="video_360p", text_template=True, use_KVcache=True)
    install_inference_loader(str(checkpoint))
    engine = MultiTurnChatEngine(model_args, DataArguments(), inference_args, device=0)
    model = engine.model
    model.train()
    model.vit_model.eval()
    engine.vae_model.vae.model.requires_grad_(False).eval()
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(".lora_" in name)
        if parameter.requires_grad:
            parameter.data = parameter.data.float()
    model.timestep_shift = 4.0

    profile = json.loads((lance / "configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json").read_text())
    config = yaml.safe_load(Path(profile["data"]["train_config"]).read_text())
    entry = config["D1"]["datamake_mixed_v2v_local"]
    row = {"sample_id": "engineering_reference", "chain_id": "engineering", "target_round": 1,
           "context_length": 1, "dataset_origin": "ue_synthetic",
           "prompts": ["Change the object's appearance to the reference color."],
           "video_paths": [str(fixture / "engineering_source.mp4")] * 2,
           "reference_images": [str(fixture / "red.png")]}
    pq.write_table(pa.Table.from_pylist([row]), output / "engineering.parquet")
    entry["dataset_names"] = {"engineering": {"data_dir": [str(output / "engineering.parquet")]}}
    entry["media_root"] = str(fixture)
    entry["video_transform_args"].update(resolution=64, aspect_ratios=["1:1"])
    entry["vit_video_transform_args"].update(resolution=56, aspect_ratios=["1:1"])
    data_config = DataConfig(config, text_cond_dropout_prob=0, vit_cond_dropout_prob=0,
                             vae_cond_dropout_prob=0, latent_patch_size=[1, 1, 1], max_num_frames=121)
    packer = PackedDataset(data_config, engine.tokenizer, engine.new_token_ids,
                           local_rank=0, world_size=1, num_workers=1, expected_num_tokens=2048,
                           max_num_tokens_per_sample=2048, max_num_tokens=2048, use_flex=True,
                           apply_chat_template=False, image_token_id=engine.image_token_id)
    source = packer.grouped_datasets[0]

    frozen = [(n, p) for n, p in model.named_parameters() if not p.requires_grad]
    probes = [frozen[0], frozen[len(frozen)//2], frozen[-1]]
    def fingerprint(parameter):
        return hashlib.sha256(parameter.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    before = {name: fingerprint(p) for name, p in probes}
    trainable = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW([p for _, p in trainable], lr=3e-4, betas=(0.9, 0.95), weight_decay=0)
    evidence = {"scope": "tiny_real_training_wiring_not_quality_no_checkpoint_write",
                "checkpoint": str(checkpoint), "cases": [], "status": "running"}
    for reference in (False, True):
        set_seed(42)
        optimizer.zero_grad(set_to_none=True)
        sample_row = deepcopy(row)
        if not reference:
            sample_row.pop("reference_images")
        sample = source._process_row(sample_row, 0, 0, 0, 0, str(output / "engineering.parquet"))
        if sample is None:
            raise RuntimeError("Engineering row failed to decode")
        packed = packer.to_tensor(packer.pack_sequence(sample, packer.set_sequence_status()))
        data = trim_attention_padding(simple_custom_collate([packed]).cuda(0).to_dict())
        details = {"reference": reference, "mse_tokens": data["mse_loss_indexes"].numel(),
                   "vae_tokens": data["packed_vae_token_indexes"].numel(),
                   "vit_tokens": data["packed_vit_token_indexes"].numel(),
                   "vae_roles": data.pop("vae_edit_roles"), "sequence_length": data["sequence_length"]}
        videos, modes = data.pop("padded_videos"), data.pop("vae_data_mode")
        data.pop("padded_videos_vit", None)
        data.pop("ce_loss_weights", None)
        torch.cuda.reset_peak_memory_stats()
        started = time.monotonic()
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            data["padded_latent"] = make_padded_latent(videos, modes, engine.vae_model)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            losses = model(**data)
            loss = losses["mse"].float().mean()
        assert torch.isfinite(loss), "non-finite training loss"
        loss.backward()
        grad_stats = {"und_nonzero_B": 0, "gen_nonzero_B": 0, "finite_gradients": 0}
        for name, parameter in trainable:
            if parameter.grad is None:
                continue
            assert torch.isfinite(parameter.grad).all(), f"non-finite grad: {name}"
            grad_stats["finite_gradients"] += 1
            if ".lora_B." in name and bool(parameter.grad.count_nonzero()):
                module = name.split(".lora_B.")[0]
                if is_understanding_target(module): grad_stats["und_nonzero_B"] += 1
                if is_generation_target(module): grad_stats["gen_nonzero_B"] += 1
        assert grad_stats["und_nonzero_B"] > 0 and grad_stats["gen_nonzero_B"] > 0
        assert all(p.grad is None for _, p in frozen), "frozen model parameter received gradient"
        assert all(p.grad is None for p in engine.vae_model.vae.model.parameters()), "VAE received gradient"
        details.update(loss=loss.item(), **grad_stats)
        if reference:
            updated_name, updated = next((n, p) for n, p in trainable if p.grad is not None and bool(p.grad.count_nonzero()))
            adapter_before = updated.detach().clone()
            optimizer.step()
            details["updated_adapter_probe"] = updated_name
            details["adapter_probe_changed"] = not torch.equal(adapter_before, updated)
            assert details["adapter_probe_changed"]
        torch.cuda.synchronize()
        details["seconds"] = time.monotonic() - started
        details["peak_allocated_gib"] = torch.cuda.max_memory_allocated() / 2**30
        evidence["cases"].append(details)
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(details), flush=True)
    assert evidence["cases"][0]["mse_tokens"] == evidence["cases"][1]["mse_tokens"]
    assert evidence["cases"][0]["vae_tokens"] == evidence["cases"][1]["vae_tokens"]
    after = {name: fingerprint(p) for name, p in probes}
    assert before == after, "frozen model probe changed after optimizer update"
    evidence.update(status="passed", frozen_probe_hashes=after, frozen_parameters_without_grad=len(frozen),
                    vae_no_grad=True, optimizer_steps=1)
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Training verification passed: {output / 'evidence.json'}", flush=True)


if __name__ == "__main__":
    main()
