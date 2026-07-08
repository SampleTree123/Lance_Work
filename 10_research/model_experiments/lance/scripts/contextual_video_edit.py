#!/usr/bin/env python3
"""Build and inspect Lance contextual video-edit configs.

This tool is intentionally separate from run_video_edit.sh. The existing shell
script represents chained single-turn editing; this file builds one Lance
interleave sample whose context contains the original video, previous prompts,
previous outputs, and the current prompt.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


TOOL_VERSION = "contextual-video-edit-v2"


def datamake_root_from_script() -> Path:
    return Path(__file__).resolve().parents[4]


def default_lance_repo() -> Path:
    return datamake_root_from_script() / "10_research/model_experiments/lance/lance"


def default_model_path() -> Path:
    return default_lance_repo() / "downloads/Lance_3B_Video"


def read_prompt_lines(path: Path) -> list[str]:
    prompts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            prompts.append(line)
    return prompts


def resolve_file(path: str | Path, *, must_exist: bool = True) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved
    resolved = resolved.resolve()
    if must_exist and not resolved.is_file():
        raise SystemExit(f"file not found: {resolved}")
    return resolved


def load_prompts(args: argparse.Namespace) -> list[str]:
    if args.prompts_file and args.prompt:
        raise SystemExit("use --prompts-file or --prompt, not both")
    if args.prompts_file:
        prompts = read_prompt_lines(resolve_file(args.prompts_file))
    else:
        prompts = [p.strip() for p in (args.prompt or []) if p.strip()]
    if not prompts:
        raise SystemExit("no prompts provided")
    return prompts


def build_context_text(prompts: list[str], turn: int, style: str) -> str:
    """Build the single text instruction used after Lance's template rotation."""

    current_prompt = prompts[turn - 1]
    if style == "current-only":
        return current_prompt

    if style == "minimal":
        if turn == 1:
            return current_prompt
        return f"Please edit the last video according to this instruction: {current_prompt}"

    if style == "timeline":
        if turn == 1:
            return current_prompt
        return (
            "The videos are ordered chronologically and the last video is the current source. "
            f"Edit only the last video with this instruction: {current_prompt}"
        )

    if style == "structured":
        lines = [
            "The videos are ordered chronologically.",
            "C0 is the original source video.",
        ]
        for idx in range(1, turn):
            lines.append(f"C{idx} is the result after applying edit {idx}: {prompts[idx - 1]}")
        lines.append(
            f"Use C{turn - 1}, the latest video, as the direct source. "
            f"Apply edit {turn}: {current_prompt}"
        )
        return " ".join(lines)

    if style != "natural":
        raise SystemExit(f"unsupported prompt style: {style}")

    if turn == 1:
        return current_prompt

    previous_edits = " ".join(
        f"The video after edit {idx} was generated with this instruction: {prompts[idx - 1]}"
        for idx in range(1, turn)
    )
    return (
        "The videos are shown in chronological order, ending with the latest generated video. "
        f"{previous_edits} Please use the last video as the direct source, keep the previous "
        f"accepted edits unless contradicted, and now make this edit: {current_prompt}"
    )


def build_context_payload(
    *,
    source_video: Path,
    prompts: list[str],
    history_videos: list[Path],
    turn: int,
    sample_id: str,
    prompt_style: str,
    history_role_mode: str,
) -> dict[str, Any]:
    if turn < 1:
        raise SystemExit("--turn must be >= 1")
    if len(prompts) < turn:
        raise SystemExit(f"--turn {turn} requires at least {turn} prompts, got {len(prompts)}")
    if len(history_videos) != turn - 1:
        raise SystemExit(
            f"--turn {turn} requires exactly {turn - 1} --history-video values, "
            f"got {len(history_videos)}"
        )
    if not sample_id.isdigit():
        raise SystemExit("--sample-id must be numeric because Lance ValidationDataset casts sample ids to int")

    context_text = build_context_text(prompts, turn, prompt_style)
    interleave_array: list[str] = [context_text]
    element_dtype_array: list[str] = ["text"]
    element_role_array: list[str] = ["text"]

    if history_role_mode == "all-source":
        video_sequence = [source_video] + history_videos
        video_roles = ["source"] * len(video_sequence)
    elif history_role_mode == "history-vit-latest-source":
        if history_videos:
            direct_source = history_videos[-1]
            history_refs = [source_video] + history_videos[:-1]
        else:
            direct_source = source_video
            history_refs = []
        video_sequence = history_refs + [direct_source]
        video_roles = ["history_vit"] * len(history_refs) + ["direct_source"]
    else:
        raise SystemExit(f"unsupported history role mode: {history_role_mode}")

    for video, role in zip(video_sequence, video_roles):
        interleave_array.append(str(video))
        element_dtype_array.append("video")
        element_role_array.append(role)

    payload = {
        sample_id: {
            "interleave_array": interleave_array,
            "element_dtype_array": element_dtype_array,
            "element_role_array": element_role_array,
            "istarget_in_interleave": [0] * len(interleave_array),
            "additional_info": {
                "builder": TOOL_VERSION,
                "context_type": "contextual_multiturn_video_edit",
                "prompt_style": prompt_style,
                "history_role_mode": history_role_mode,
                "turn": turn,
                "source_video": str(source_video),
                "history_videos": [str(p) for p in history_videos],
                "video_roles": video_roles,
                "prompts_used": prompts[:turn],
                "direct_source_video": str(history_videos[-1] if history_videos else source_video),
                "note": (
                    "This JSON starts with text and ends with video on purpose. "
                    "Lance text_template rotates the first text block after the "
                    "videos, while the final JSON element keeps the system prompt "
                    "vision_type as video. In history-vit-latest-source mode, older "
                    "videos are semantic references only and the latest video is the "
                    "only clean VAE edit source."
                ),
            },
        }
    }
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_samples(config_path: Path) -> list[tuple[str, dict[str, Any]]]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [(str(k), v) for k, v in data.items()]
    if isinstance(data, list):
        samples = []
        for idx, item in enumerate(data):
            sample_id = str(item.get("index", idx)) if isinstance(item, dict) else str(idx)
            sample_data = item.get("data", item) if isinstance(item, dict) else item
            samples.append((sample_id, sample_data))
        return samples
    raise SystemExit(f"unsupported JSON top level in {config_path}")


def static_inspect(config_path: Path) -> tuple[list[str], int]:
    warnings: list[str] = []
    samples = iter_samples(config_path)
    print(f"Config: {config_path}")
    print(f"Samples: {len(samples)}")
    for sample_id, sample in samples:
        arrays = {
            "interleave_array": sample.get("interleave_array", []),
            "element_dtype_array": sample.get("element_dtype_array", []),
            "istarget_in_interleave": sample.get("istarget_in_interleave", []),
        }
        roles = sample.get("element_role_array")
        if roles is not None:
            arrays["element_role_array"] = roles
        lengths = {name: len(value) for name, value in arrays.items()}
        print()
        print(f"Sample {sample_id}")
        print(f"  lengths: {lengths}")
        if len(set(lengths.values())) != 1:
            warnings.append(f"{sample_id}: interleave/dtype/target lengths differ")
            continue

        dtypes = arrays["element_dtype_array"]
        targets = arrays["istarget_in_interleave"]
        roles = arrays.get("element_role_array", ["source"] * len(dtypes))
        n_text = sum(1 for x in dtypes if x == "text")
        n_video = sum(1 for x in dtypes if x == "video")
        n_image = sum(1 for x in dtypes if x == "image")
        n_target = sum(1 for x in targets if int(x) != 0)
        role_counts = {role: roles.count(role) for role in sorted(set(roles))}
        print(f"  dtype sequence: {' -> '.join(dtypes)}")
        if "element_role_array" in arrays:
            print(f"  role sequence: {' -> '.join(str(x) for x in roles)}")
        print(f"  text={n_text} video={n_video} image={n_image} explicit_targets={n_target}")
        if "element_role_array" in arrays:
            print(f"  role_counts={role_counts}")
        if dtypes and dtypes[0] == "text":
            if dtypes[-1] in {"video", "image"}:
                print("  note: starts with text; Lance text_template will rotate this first text after the media")
            else:
                warnings.append(
                    f"{sample_id}: starts with text but does not end with media; Lance system prompt may use the wrong vision type"
                )
        if dtypes and dtypes[-1] not in {"video", "image"}:
            warnings.append(
                f"{sample_id}: last dtype is {dtypes[-1]!r}; Lance video_edit system prompt uses the last dtype as vision_type"
            )
        if n_target:
            warnings.append(
                f"{sample_id}: explicit targets are present; current contextual inference expects all zeros"
            )

        direct_sources = [role for role in roles if role == "direct_source"]
        if "element_role_array" in arrays and len(direct_sources) > 1:
            warnings.append(f"{sample_id}: expected at most one direct_source, got {len(direct_sources)}")
        for idx, (element, dtype, role) in enumerate(zip(arrays["interleave_array"], dtypes, roles), start=1):
            if dtype in {"video", "image"}:
                path = Path(str(element))
                exists = path.is_file()
                role_text = f" role={role}" if "element_role_array" in arrays else ""
                print(f"  {idx:02d} {dtype}{role_text}: {path} exists={exists}")
                if not exists:
                    warnings.append(f"{sample_id}: media path does not exist: {path}")
            elif dtype == "text":
                text = str(element).replace("\n", " ")
                preview = text[:140] + ("..." if len(text) > 140 else "")
                print(f"  {idx:02d} text: {preview}")
            else:
                warnings.append(f"{sample_id}: unsupported dtype: {dtype}")

    if warnings:
        print()
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    return warnings, len(samples)


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def inspect_lance_pack(args: argparse.Namespace, config_path: Path) -> None:
    lance_repo = Path(args.lance_repo).expanduser().resolve()
    model_path = Path(args.model_path).expanduser()
    if not model_path.is_absolute():
        model_path = (lance_repo / model_path).resolve()

    if not lance_repo.is_dir():
        raise SystemExit(f"Lance repo not found: {lance_repo}")
    if not model_path.is_dir():
        raise SystemExit(f"Lance model path not found: {model_path}")

    sys.path.insert(0, str(lance_repo))
    os.chdir(lance_repo)

    from config.config_factory import DataArguments, ModelArguments, TrainingArguments
    from data.data_utils import add_special_tokens
    from data.dataset_base import DataConfig
    from data.datasets_custom.validation_dataset import ValidationDataset, modality_map
    from modeling.qwen2 import Qwen2Tokenizer

    model_args = ModelArguments()
    data_args = DataArguments(val_dataset_config_file=str(config_path))
    training_args = TrainingArguments()
    training_args.visual_gen = True
    training_args.visual_und = True

    tokenizer = Qwen2Tokenizer.from_pretrained(str(model_path))
    tokenizer, new_token_ids, _ = add_special_tokens(tokenizer)

    llm_config = load_json_if_exists(model_path / "llm_config.json")
    image_token_id = llm_config.get("video_token_id") or llm_config.get("image_token_id") or 151656
    new_token_ids.update({"image_token_id": int(image_token_id)})

    dataset_config = DataConfig.from_yaml(str(config_path))
    dataset_config.vit_patch_size = model_args.vit_patch_size
    dataset_config.vit_patch_size_temporal = model_args.vit_patch_size_temporal
    dataset_config.vit_max_num_patch_per_side = model_args.vit_max_num_patch_per_side
    model_args.latent_patch_size = tuple(args.latent_patch_size)
    dataset_config.latent_patch_size = model_args.latent_patch_size
    dataset_config.vae_downsample = tuple(
        int(a) * int(b)
        for a, b in zip(tuple(model_args.latent_patch_size), (4, 16, 16))
    )
    dataset_config.max_latent_size = model_args.max_latent_size
    dataset_config.max_num_frames = model_args.max_num_frames
    dataset_config.text_cond_dropout_prob = model_args.text_cond_dropout_prob
    dataset_config.vae_cond_dropout_prob = model_args.vae_cond_dropout_prob
    dataset_config.vit_cond_dropout_prob = model_args.vit_cond_dropout_prob
    dataset_config.num_frames = args.frames
    dataset_config.H = args.height
    dataset_config.W = args.width
    dataset_config.task = "video_edit"
    dataset_config.resolution = args.resolution
    dataset_config.text_template = True
    dataset_config.enhance_prompt = False

    dataset = ValidationDataset(
        jsonl_path=str(config_path),
        tokenizer=tokenizer,
        data_args=data_args,
        model_args=model_args,
        training_args=training_args,
        new_token_ids=new_token_ids,
        dataset_config=dataset_config,
        local_rank=0,
        world_size=1,
    )

    if args.synthetic_media:
        import types

        import torch

        vae_t = max(1, args.frames)
        vae_h = max(dataset_config.vae_downsample[1], args.height // dataset_config.vae_downsample[1] * dataset_config.vae_downsample[1])
        vae_w = max(dataset_config.vae_downsample[2], args.width // dataset_config.vae_downsample[2] * dataset_config.vae_downsample[2])
        vit_t = vae_t if vae_t % 2 == 0 else vae_t + 1
        vit_stride = dataset_config.vit_patch_size * 2
        vit_h = max(vit_stride, args.height // vit_stride * vit_stride)
        vit_w = max(vit_stride, args.width // vit_stride * vit_stride)

        def synthetic_get_video_tensor_online(self, media_url, vision_stream, worker_id=0, element_dtype="image"):
            if element_dtype == "image":
                t = 1
            elif vision_stream == "vit_video":
                t = vit_t
            else:
                t = vae_t

            if vision_stream == "vit_video":
                return torch.zeros((3, t, vit_h, vit_w), dtype=torch.float32)
            if vision_stream == "vae_video":
                return torch.zeros((3, t, vae_h, vae_w), dtype=torch.float32)
            raise ValueError(f"Unknown vision_stream: {vision_stream}")

        dataset.get_video_tensor_online = types.MethodType(synthetic_get_video_tensor_online, dataset)

    print()
    print("Lance pack inspection")
    print(f"  Lance repo: {lance_repo}")
    print(f"  Model path: {model_path}")
    print(f"  resolution={args.resolution} frames={args.frames} height={args.height} width={args.width}")
    print(f"  latent_patch_size={tuple(args.latent_patch_size)}")
    print(f"  vae_downsample={dataset_config.vae_downsample}")
    if args.synthetic_media:
        print("  media=synthetic tensors; real MP4 decode is skipped")

    limit = min(len(dataset), args.max_samples)
    for idx in range(limit):
        sample = dataset[idx]
        packed_len = int(sample["sample_lens"][0])
        attn_modes = [str(x) for x in sample["attn_modes"]]
        split_lens = [int(x) for x in sample["split_lens"]]
        vit_grid = sample["vit_video_grid_thw"]
        vit_blocks = int(vit_grid.numel() // 3) if hasattr(vit_grid, "numel") else 0
        vae_blocks = int(sample["vae_video_grid_thw"].shape[0])
        target_blocks = int(sample["sample_N_target"][0][0])
        cond_vae_blocks = max(0, vae_blocks - target_blocks)
        mse_indexes = int(sample["mse_loss_indexes"].numel())
        modality_counts: dict[str, int] = {}
        if "sample_modality" in sample:
            reverse_modality = {value: key for key, value in modality_map.items()}
            modalities = sample["sample_modality"].tolist()
            for value in sorted(set(int(v) for v in modalities)):
                modality_counts[reverse_modality.get(value, str(value))] = sum(1 for v in modalities if int(v) == value)
        ref_source_tokens = modality_counts.get("ref_source", 0)
        noise_tokens = modality_counts.get("noise", 0)

        print()
        print(f"  sample[{idx}] index={sample.get('index')}")
        print(f"    packed_len={packed_len}")
        print(f"    split_lens={split_lens}")
        print(f"    attn_modes={attn_modes}")
        print(f"    vit_condition_blocks={vit_blocks}")
        print(f"    vae_condition_blocks={cond_vae_blocks}")
        print(f"    target_vae_blocks={target_blocks}")
        print(f"    mse_loss_indexes={mse_indexes}")
        print(f"    vae_latent_shapes={sample.get('vae_latent_shapes')}")
        if modality_counts:
            print(f"    modality_counts={modality_counts}")
            if ref_source_tokens == noise_tokens:
                print("    source_target_alignment=PASS")
            else:
                print(
                    "    source_target_alignment=FAIL "
                    f"(ref_source={ref_source_tokens}, noise={noise_tokens})"
                )
        if packed_len > args.warn_tokens:
            print(f"    WARNING: packed_len exceeds --warn-tokens={args.warn_tokens}")


def cmd_build(args: argparse.Namespace) -> None:
    prompts = load_prompts(args)
    source_video = resolve_file(args.source_video)
    history_videos = [resolve_file(p) for p in (args.history_video or [])]
    turn = args.turn or (len(history_videos) + 1)
    payload = build_context_payload(
        source_video=source_video,
        prompts=prompts,
        history_videos=history_videos,
        turn=turn,
        sample_id=args.sample_id,
        prompt_style=args.prompt_style,
        history_role_mode=args.history_role_mode,
    )
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = Path.cwd() / output
    output = output.resolve()
    write_json(output, payload)
    print(f"Wrote contextual config: {output}")
    static_inspect(output)


def cmd_inspect(args: argparse.Namespace) -> None:
    config_path = resolve_file(args.config)
    warnings, _ = static_inspect(config_path)
    if args.pack:
        inspect_lance_pack(args, config_path)
    if args.strict and warnings:
        raise SystemExit(1)


def add_common_inference_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--resolution", default="video_480p")
    parser.add_argument("--frames", type=int, default=50)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--width", type=int, default=480)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    build = subparsers.add_parser("build", help="build one contextual Lance JSON config")
    build.add_argument("--source-video", required=True)
    prompt_group = build.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompts-file")
    prompt_group.add_argument("--prompt", action="append")
    build.add_argument("--history-video", action="append", default=[])
    build.add_argument("--turn", type=int)
    build.add_argument(
        "--prompt-style",
        choices=["natural", "structured", "minimal", "timeline", "current-only"],
        default="current-only",
    )
    build.add_argument(
        "--history-role-mode",
        choices=["history-vit-latest-source", "all-source"],
        default="history-vit-latest-source",
        help="history-vit-latest-source keeps only the latest video as clean VAE source; all-source is the old v1 behavior",
    )
    build.add_argument("--sample-id", default="0001")
    build.add_argument("--output", required=True)
    build.set_defaults(func=cmd_build)

    inspect = subparsers.add_parser("inspect", help="inspect JSON statically and optionally through Lance dataset packing")
    inspect.add_argument("--config", required=True)
    inspect.add_argument("--strict", action="store_true")
    inspect.add_argument("--pack", action="store_true", help="instantiate Lance ValidationDataset and inspect packed sequence")
    inspect.add_argument("--synthetic-media", action="store_true", help="skip real media decoding during --pack and use zero tensors")
    inspect.add_argument("--lance-repo", default=str(default_lance_repo()))
    inspect.add_argument("--model-path", default=str(default_model_path()))
    inspect.add_argument("--max-samples", type=int, default=1)
    inspect.add_argument("--warn-tokens", type=int, default=16384)
    inspect.add_argument("--latent-patch-size", type=int, nargs=3, default=[1, 1, 1], metavar=("PT", "PH", "PW"))
    add_common_inference_args(inspect)
    inspect.set_defaults(func=cmd_inspect)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
