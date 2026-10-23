#!/usr/bin/env python3
"""Run six fixed validation outputs using the existing Lance inference engine.

One model load, a real three-turn rollout, then three GT-history diagnostic
cases. Visual preprocessing comes from the checkpoint's training dataset YAML.
No training, W&B writes, optimizer restore, or diffusion sampler modifications.
Implementation/output owner: ../training_integration.md.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import shutil
import sys
import time

import yaml

from build_datamake_teacher_forced_conversation import (
    build_conversation,
    select_row,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[4]
LANCE = ROOT / "10_research/model_experiments/lance"
SPLIT = LANCE / "outputs/training_data/datamake_dialogue_first_batch_v002_split_seed2026_sharded8_20260831"
MEDIA = ROOT / "00_engine/outputs/delivery/first_batch_candidate_20260830_v002/dataset_v1"
CHAIN3 = "c_7669cabae1467386"
CHAIN5 = "c_c6282282709e3a10"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_training_preprocessing(contract):
    """Reuse the actual VAE/ViT transforms, not Lance's named resolution presets."""
    path = Path(contract["dataset_config"])
    digest = sha256_file(path)
    if contract.get("dataset_config_sha256", digest) != digest:
        raise ValueError("Training dataset YAML changed since checkpoint")
    datasets = yaml.safe_load(path.read_text(encoding="utf-8"))["D1"]
    supported = [key for key in ("datamake_multiturn_v2v_local", "datamake_mixed_v2v_local") if key in datasets]
    if len(supported) != 1:
        raise ValueError("Expected exactly one supported training dataset")
    dataset = datasets[supported[0]]
    return {
        "mode": "training_dataset_config",
        "dataset_config": str(path),
        "dataset_config_sha256": sha256_file(path),
        "resolution_preset_overridden": True,
        "video_transform_args": dataset["video_transform_args"],
        "vit_video_transform_args": dataset["vit_video_transform_args"],
        "video_frame_sampler_args": dataset["video_frame_sampler_args"],
    }


def apply_training_preprocessing(builder, preprocessing):
    """Override this inference builder only; leave training and upstream untouched."""
    from data.transforms import VideoTransform
    from data.video.sampler.utils import FRAME_SAMPLER_TYPES

    builder.transform = VideoTransform(**preprocessing["video_transform_args"])
    builder.vit_transform = VideoTransform(**preprocessing["vit_video_transform_args"])
    frame_sampler = preprocessing["video_frame_sampler_args"]
    builder.frame_sampler = FRAME_SAMPLER_TYPES[frame_sampler["type"]](
        **frame_sampler["params"]
    )


def make_cases(parquet):
    cases = []
    for name, chain, target_round in (
        ("autoregressive_chain3", CHAIN3, 3),
        ("teacher_forced_action_r2", CHAIN3, 2),
        ("teacher_forced_outfit_r3", CHAIN3, 3),
        ("teacher_forced_outfit_r5", CHAIN5, 5),
    ):
        row = select_row(parquet, None, chain, target_round)
        conversation = build_conversation(row, MEDIA)
        autoregressive = name == "autoregressive_chain3"
        if autoregressive:
            # Never preload assistant GT endpoints into a real rollout.
            conversation["turns"] = [
                {**turn, "action": "edit_video"}
                for turn in conversation["turns"] if turn["role"] == "user"
            ]
        rounds = range(1, target_round + 1) if autoregressive else [target_round]
        outputs = []
        for output_index, round_no in enumerate(rounds):
            outputs.append({
                "round": round_no,
                "edit_axis": row["edit_axes"][round_no - 1],
                "prompt": row["prompts"][round_no - 1],
                "gt_source": str(MEDIA / row["video_paths"][round_no - 1]),
                "gt_target": str(MEDIA / row["video_paths"][round_no]),
                "actual_source": (
                    f"{name}/turn{output_index - 1:02d}.mp4"
                    if autoregressive and output_index else str(MEDIA / row["video_paths"][round_no - 1])
                ),
                "output": f"{name}/turn{output_index:02d}.mp4",
            })
        cases.append({
            "name": name, "chain_id": chain, "sample_id": row["sample_id"],
            "mode": "autoregressive" if autoregressive else "teacher_forced",
            "conversation": conversation, "outputs": outputs,
        })
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--suite", type=Path, help="Frozen complete-chain suite; omit for historical fixed cases")
    parser.add_argument("--cfg-text-scale", type=float, help="Override text CFG scale for this inference run")
    parser.add_argument("--cfg-vit-scale", type=float, help="Override vision CFG scale for this inference run")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs on CPU without creating a run or loading a model")
    args = parser.parse_args()
    checkpoint = args.checkpoint.resolve()
    complete = json.loads((checkpoint / "checkpoint_complete.json").read_text())
    if complete["status"] != "complete":
        raise ValueError("Select a complete checkpoint, not an in-progress save")
    contract = json.loads((checkpoint / "datamake_online_training_contract.json").read_text())
    preprocessing = load_training_preprocessing(contract)
    suite = None
    if args.suite:
        from prepare_datamake_chain_review import load_suite, make_cases as make_chain_cases
        suite = load_suite(args.suite)
        parquet = Path(suite["parquet"])
        cases = make_chain_cases(suite)
    else:
        parquet = SPLIT / "validation/datamake_multiturn.parquet"
        cases = make_cases(parquet)
    if args.dry_run:
        print(json.dumps({"status": "cpu_inputs_validated", "checkpoint": str(checkpoint),
                          "completed_steps": complete["completed_steps"], "preprocessing": preprocessing,
                          "conversations": len(cases), "generated_videos": sum(len(c["outputs"]) for c in cases)}))
        return
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for case in cases:
        input_path = output / f"{case['name']}.input.json"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(input_path, case["conversation"])
    manifest = {
        "schema_version": "datamake_lora_visual_sanity_v1",
        "status": "running", "started_at": datetime.now().astimezone().isoformat(),
        "hostname": socket.gethostname(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "producer": str(Path(__file__).resolve()), "producer_sha256": sha256_file(Path(__file__)),
        "checkpoint": str(checkpoint), "completed_steps": complete["completed_steps"],
        "adapter_sha256": sha256_file(checkpoint / "adapter.safetensors"),
        "base_model": contract["base_model"], "base_sha256_from_training_contract": contract["base_model_sha256"],
        "split": "validation", "parquet": str(parquet), "parquet_sha256": sha256_file(parquet),
        "quality_status": "pending_user_visual_review", "cases": cases,
        "preprocessing": preprocessing,
    }
    if suite:
        manifest["chain_suite"] = suite
        manifest["chain_suite_sha256"] = sha256_file(args.suite)
        # Retention may remove the source checkpoint during a long rollout.
        # Pin inference-only files; never copy Adam state or label this resumable.
        pinned = output / "inference_adapter"
        pinned.mkdir()
        for name in ("adapter.safetensors", "datamake_lora_config.json", "datamake_online_training_contract.json"):
            shutil.copy2(checkpoint / name, pinned / name)
            expected = complete["artifacts"][name]["sha256"]
            if sha256_file(pinned / name) != expected:
                raise ValueError(f"Checkpoint snapshot mismatch: {name}")
        manifest["inference_adapter_snapshot"] = str(pinned)
        checkpoint = pinned
    write_json(output / "manifest.json", manifest)

    # Use the same construction/loader/sampler as datamake_lora_multiturn_chat.py.
    os.chdir(LANCE / "lance")
    sys.path.insert(0, str(LANCE / "lance"))
    import torch
    from transformers import set_seed
    from config.config_factory import DataArguments, InferenceArguments, ModelArguments
    from train.datamake_generation_lora import install_lora_adapter_inference_loader
    adapter_config = json.loads((checkpoint / "datamake_lora_config.json").read_text())
    if adapter_config["schema_version"] == "datamake_lance_branch_lora_v1":
        from train.datamake_branch_lora import install_branch_adapter_inference_loader
        install_lora_adapter_inference_loader = install_branch_adapter_inference_loader
    elif adapter_config["schema_version"] == "datamake_lance_peft_branch_v1":
        sys.path.insert(0, str(LANCE / "runtime/peft_0_15_2"))
        from train.datamake_peft import install_inference_loader
        install_lora_adapter_inference_loader = install_inference_loader
    from multiturn.conversation import Conversation
    from multiturn.engine import MultiTurnChatEngine

    if not torch.cuda.is_available():
        raise RuntimeError("Run inside an allocated GPU job")
    torch.cuda.set_device(0)
    model_args = ModelArguments(
        model_path=contract["base_model"], llm_path=contract["base_model"],
        vit_path=str(LANCE / "models/Lance/Qwen2.5-VL-ViT"),
        vit_type="qwen_2_5_vl_original", llm_qk_norm=True, llm_qk_norm_und=True,
        llm_qk_norm_gen=True, tie_word_embeddings=False, max_num_frames=121,
        max_latent_size=64, latent_patch_size=[1, 1, 1], cfg_text_scale=1.0,
    )
    data_args = DataArguments()
    inference_args = InferenceArguments(
        validation_num_timesteps=30, validation_timestep_shift=3.5,
        copy_init_moe=True, visual_und=True, visual_gen=True, vae_model_type="wan",
        apply_qwen_2_5_vl_pos_emb=True, apply_chat_template=False, cfg_type=0,
        validation_data_seed=42, video_height=480, video_width=480, num_frames=50,
        # Constructor preset only: both transforms are replaced with training
        # YAML values below, before any case is packed. video_360p alone would
        # still select ViT476 rather than the trained ViT448.
        resolution="video_360p", text_template=True, use_KVcache=True,
    )
    if suite:
        settings = suite["inference"]
        inference_args.validation_num_timesteps = settings["diffusion_steps"]
        inference_args.validation_timestep_shift = settings["timestep_shift"]
        inference_args.global_seed = settings["global_seed"]
        inference_args.validation_noise_seed = settings["noise_seed"]
        inference_args.use_KVcache = settings["use_KVcache"]
        model_args.cfg_text_scale = settings["cfg_text_scale"]
        model_args.cfg_vit_scale = settings.get("cfg_vit_scale", 1.0)
    if args.cfg_text_scale is not None:
        model_args.cfg_text_scale = args.cfg_text_scale
    if args.cfg_vit_scale is not None:
        model_args.cfg_vit_scale = args.cfg_vit_scale
    manifest["arguments"] = {"model": asdict(model_args), "data": asdict(data_args), "inference": asdict(inference_args)}
    write_json(output / "manifest.json", manifest)
    if not install_lora_adapter_inference_loader(str(checkpoint)):
        raise FileNotFoundError(f"Missing adapter/config in {checkpoint}")
    set_seed(inference_args.global_seed)
    engine = MultiTurnChatEngine(model_args, data_args, inference_args, device=0, log=print)
    apply_training_preprocessing(engine.builder, preprocessing)
    print(f"[preprocessing] {json.dumps(preprocessing)}", flush=True)

    # Runtime evidence for the previously broken nested-LoRA save/load boundary.
    from safetensors.torch import load_file
    adapter = load_file(str(checkpoint / "adapter.safetensors"), device="cpu")
    live = dict(engine.model.named_parameters())
    if adapter_config["schema_version"] == "datamake_lance_peft_branch_v1":
        from train.datamake_peft import canonical_name
        live = {canonical_name(key): value for key, value in live.items()}
    matching = sum(torch.equal(live[key].detach().cpu(), value.to(live[key].dtype)) for key, value in adapter.items())
    nonzero_b = sum(bool(torch.count_nonzero(value)) for key, value in adapter.items() if key.endswith(("lora_B", "lora_B.weight")))
    manifest["adapter_load_check"] = {"tensor_count": len(adapter), "matching_after_bf16_cast": matching, "nonzero_lora_B": nonzero_b}
    if matching != len(adapter):
        raise RuntimeError("Loaded adapter differs from checkpoint after inference dtype cast")
    del adapter, live
    print(f"[adapter] {manifest['adapter_load_check']}", flush=True)
    write_json(output / "manifest.json", manifest)
    for case in cases:
        set_seed(inference_args.global_seed)
        torch.cuda.reset_peak_memory_stats()
        start = time.monotonic()
        print(f"[case] {case['name']} started", flush=True)
        conversation = Conversation.from_dict(case["conversation"])
        case_dir = output / case["name"]
        from datamake_coinve_review_media import paired_input
        with paired_input(engine.builder, case):
            engine.run_conversation(conversation, save_dir=str(case_dir))
        write_json(case_dir / "transcript.json", conversation.to_dict())
        torch.cuda.synchronize()
        case["elapsed_seconds"] = time.monotonic() - start
        case["peak_allocated_gib"] = torch.cuda.max_memory_allocated() / 2**30
        case["status"] = "generated"
        write_json(output / "manifest.json", manifest)
        print(f"[case] {case['name']} finished in {case['elapsed_seconds']:.1f}s", flush=True)
    manifest["status"] = "generated"
    manifest["finished_at"] = datetime.now().astimezone().isoformat()
    write_json(output / "manifest.json", manifest)
    print(f"[done] {output}", flush=True)


if __name__ == "__main__":
    main()
