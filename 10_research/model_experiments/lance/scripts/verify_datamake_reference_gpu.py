#!/usr/bin/env python3
"""Small real-model reference-input/CFG engineering check, not a quality benchmark.

Owner: ../training_integration.md. Never updates adapters or submits jobs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--code-root", type=Path, help="Explicit source tree for migration comparison")
    parser.add_argument("--save-latents", action="store_true", help="Save tiny diagnostic latents for numerical comparison")
    args = parser.parse_args()
    lance = Path(__file__).resolve().parents[1]
    checkpoint = Path(args.checkpoint).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "evidence.json").exists():
        raise FileExistsError("Use a fresh output directory to preserve verification evidence")
    code_root = (args.code_root or lance / "lance").resolve()
    os.chdir(code_root)
    sys.path.insert(0, str(lance / "runtime/peft_0_15_2"))
    sys.path.insert(0, str(code_root))

    import imageio.v2 as imageio
    import numpy as np
    import torch
    from PIL import Image
    from transformers import set_seed
    from config.config_factory import DataArguments, InferenceArguments, ModelArguments
    from train.datamake_peft import install_inference_loader
    from multiturn.conversation import Conversation
    from multiturn.engine import MultiTurnChatEngine
    from data.transforms import VideoTransform
    import multiturn.engine as engine_module

    if not torch.cuda.is_available():
        raise RuntimeError("An allocated CUDA GPU is required")
    torch.cuda.set_device(0)
    # Explicitly tiny artificial clip; this check makes no visual quality claim.
    frames = []
    for index in range(9):
        frame = np.full((64, 64, 3), 110, dtype=np.uint8)
        frame[16:48, 8 + index:24 + index] = [40, 180, 70]
        frames.append(frame)
    source = output / "engineering_source.mp4"
    imageio.mimwrite(source, frames, fps=12, codec="libx264", quality=9)
    for color in ("red", "blue"):
        Image.new("RGB", (56, 56), color).save(output / f"{color}.png")

    base = str(lance / "models/Lance/Lance_3B_Video")
    model_args = ModelArguments(
        model_path=base, llm_path=base, vit_path=str(lance / "models/Lance/Qwen2.5-VL-ViT"),
        vit_type="qwen_2_5_vl_original", llm_qk_norm=True, llm_qk_norm_und=True,
        llm_qk_norm_gen=True, tie_word_embeddings=False, max_num_frames=121,
        max_latent_size=64, latent_patch_size=[1, 1, 1], cfg_text_scale=1.0,
    )
    infer_args = InferenceArguments(
        validation_num_timesteps=2, validation_timestep_shift=3.5,
        copy_init_moe=True, visual_und=True, visual_gen=True, vae_model_type="wan",
        apply_qwen_2_5_vl_pos_emb=True, apply_chat_template=False, cfg_type=0,
        validation_data_seed=42, video_height=64, video_width=64, num_frames=9,
        resolution="video_360p", text_template=True, use_KVcache=True,
    )
    install_inference_loader(str(checkpoint))
    set_seed(42)
    engine = MultiTurnChatEngine(model_args, DataArguments(), infer_args, device=0)
    engine.builder.transform = VideoTransform(
        resolution=64, mode="bucket", divisible_crop_size=16, stride_spatial=16,
        stride_temporal=4, aspect_ratios=["1:1"], mean=0.5, std=0.5)
    engine.builder.vit_transform = VideoTransform(
        resolution=56, mode="bucket", divisible_crop_size=28, aspect_ratios=["1:1"],
        mean=[0.48145466, 0.4578275, 0.40821073], std=[0.26862954, 0.26130258, 0.27577711])

    evidence = {"scope": "engineering_only_tiny_fixture_not_quality",
                "code_root": str(code_root),
                "checkpoint": str(checkpoint), "gpu": torch.cuda.get_device_name(),
                "steps": 2, "seed": 42, "cases": [], "status": "running"}
    latents = {}
    original_generate = engine.model.validation_gen_KVcache
    original_decode = engine_module.decode_video_tensor
    current = {}

    def checked_generate(**kwargs):
        result = original_generate(**kwargs)
        target = result[0][0][-1].detach().float().cpu()
        assert torch.isfinite(target).all(), "non-finite target latent"
        latents[current["name"]] = target
        current["latent_shape"] = list(target.shape)
        current["latent_finite"] = True
        current["vit_grids"] = kwargs["vit_video_grid_thw"].tolist()
        current["video_sizes"] = kwargs["video_sizes"].tolist()
        return result

    def checked_decode(videos, **kwargs):
        assert all(torch.isfinite(v).all() for v in videos), "non-finite decoded video"
        current["decoded_tensor_shapes"] = [list(v.shape) for v in videos]
        result = original_decode(videos, **kwargs)
        current["output_thwc"] = list(result.shape)
        return result

    cases = [("no_reference", None, 1, 1), ("red", "red", 1, 1), ("blue", "blue", 1, 1),
             ("red_text3", "red", 3, 1), ("red_vit3", "red", 1, 3)]
    with patch.object(engine.model, "validation_gen_KVcache", side_effect=checked_generate), \
         patch.object(engine_module, "decode_video_tensor", side_effect=checked_decode):
        for name, reference, text_cfg, vit_cfg in cases:
            current = {"name": name, "text_cfg": text_cfg, "vit_cfg": vit_cfg}
            turn = {"role": "user", "action": "edit_video", "content": [
                {"type": "video", "value": str(source)},
                {"type": "text", "value": "Change the object's appearance to the reference color; keep its motion and background."}]}
            if reference:
                turn["reference_image"] = str(output / f"{reference}.png")
            conversation = Conversation.from_dict({"turns": [turn]})
            engine.model_args.cfg_text_scale = float(text_cfg)
            engine.model_args.cfg_vit_scale = float(vit_cfg)
            set_seed(42)
            torch.cuda.reset_peak_memory_stats()
            started = time.monotonic()
            engine.run_conversation(conversation, str(output / name))
            torch.cuda.synchronize()
            current["seconds"] = time.monotonic() - started
            current["peak_allocated_gib"] = torch.cuda.max_memory_allocated() / 2**30
            (output / name / "transcript.json").write_text(json.dumps(conversation.to_dict(), indent=2) + "\n")
            evidence["cases"].append(current)
            (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(current), flush=True)
    shapes = {tuple(case["output_thwc"]) for case in evidence["cases"]}
    assert len(shapes) == 1, "reference/CFG changed target output size"
    difference = (latents["red"] - latents["blue"]).abs()
    evidence["red_blue_latent_difference"] = {"mean_abs": difference.mean().item(),
                                                "max_abs": difference.max().item()}
    assert difference.max().item() > 0, "reference pixel changes did not affect prediction"
    evidence["status"] = "passed"
    if args.save_latents:
        torch.save(latents, output / "latents.pt")
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Verification passed: {output / 'evidence.json'}", flush=True)


if __name__ == "__main__":
    main()
