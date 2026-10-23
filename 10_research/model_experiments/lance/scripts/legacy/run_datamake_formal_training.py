#!/usr/bin/env python3
"""Validate and launch the frozen four-H200 DataMake Lance training profile."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Mapping

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PROFILE = (
    WORKSPACE_ROOT
    / "10_research/model_experiments/lance/configs/datamake_dialogue_first_batch_v1.json"
)
LANCE_ROOT = WORKSPACE_ROOT / "10_research/model_experiments/lance/lance"
DEFAULT_ENV = Path(
    os.environ.get(
        "DATAMAKE_LANCE_ENV",
        "/scratch/prj0000000275/jcy/.conda/envs/xks_lance",
    )
)
PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)
WANDB_PREFLIGHT_TIMEOUT_SECONDS = 45
WANDB_PREFLIGHT_CODE = """
import json
import wandb

api = wandb.Api(timeout=10)
print(json.dumps({
    "username": str(api.viewer.username),
    "entity": str(api.default_entity),
}))
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def read_yaml(path: Path) -> Dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return payload


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (WORKSPACE_ROOT / path).resolve()


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")


def validate_profile(profile_path: Path) -> Dict[str, Any]:
    profile_path = profile_path.resolve()
    profile = read_json(profile_path)
    profile_schema = profile.get("schema_version")
    if profile_schema not in {
        "datamake_lance_formal_training_profile_v1",
        "datamake_lance_stage2_training_profile_v1",
    }:
        raise ValueError(f"unsupported profile schema: {profile_schema!r}")

    source = profile["source"]
    commit = subprocess.run(
        ["git", "-C", str(LANCE_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    require_equal(commit, source["lance_commit"], "Lance commit")
    for relative_path, expected_sha256 in source["patches"].items():
        patch_path = workspace_path(relative_path)
        if not patch_path.is_file():
            raise FileNotFoundError(f"required patch is missing: {patch_path}")
        require_equal(sha256_file(patch_path), expected_sha256, str(patch_path))
    implementation_files = source.get("implementation_files", {})
    if profile_schema == "datamake_lance_stage2_training_profile_v1" and not implementation_files:
        raise ValueError("stage2 profile must freeze implementation file hashes")
    for relative_path, expected_sha256 in implementation_files.items():
        implementation_path = workspace_path(relative_path)
        if not implementation_path.is_file():
            raise FileNotFoundError(
                f"stage2 implementation file is missing: {implementation_path}"
            )
        require_equal(
            sha256_file(implementation_path),
            expected_sha256,
            str(implementation_path),
        )

    data = profile["data"]
    artifact_pairs = [
        ("split_manifest", "split_manifest_sha256"),
        ("train_config", "train_config_sha256"),
        ("validation_config", "validation_config_sha256"),
        ("test_config", "test_config_sha256"),
    ]
    if "train_sampling_manifest" in data:
        artifact_pairs.append(
            ("train_sampling_manifest", "train_sampling_manifest_sha256")
        )
    for path_key, hash_key in artifact_pairs:
        artifact = workspace_path(data[path_key])
        if not artifact.is_file():
            raise FileNotFoundError(f"profile artifact is missing: {artifact}")
        require_equal(sha256_file(artifact), data[hash_key], str(artifact))

    split_manifest = read_json(workspace_path(data["split_manifest"]))
    require_equal(split_manifest["seed"], data["split_seed"], "split seed")
    require_equal(split_manifest["prompt_view"], data["prompt_view"], "prompt view")
    for split_name in ("validation", "test"):
        record = split_manifest["splits"][split_name]
        require_equal(
            record["chain_count"], data[f"{split_name}_chains"], f"{split_name} chains"
        )
        require_equal(
            record["sample_count"],
            data[f"{split_name}_prefixes"],
            f"{split_name} prefixes",
        )
    source_train_record = split_manifest["splits"]["train"]
    require_equal(
        source_train_record["chain_count"], data["train_chains"], "train chains"
    )
    if "train_sampling_manifest" in data:
        sampling_manifest_path = workspace_path(data["train_sampling_manifest"])
        sampling_manifest = read_json(sampling_manifest_path)
        require_equal(
            sampling_manifest["schema_version"],
            "datamake_lance_round_oversample_v1",
            "train sampling schema",
        )
        require_equal(
            sampling_manifest["source_split_manifest_sha256"],
            data["split_manifest_sha256"],
            "sampling source split hash",
        )
        require_equal(
            sampling_manifest["source_train_rows"],
            data["source_train_prefixes"],
            "source train prefixes",
        )
        require_equal(
            source_train_record["sample_count"],
            data["source_train_prefixes"],
            "split source train prefixes",
        )
        require_equal(
            sampling_manifest["effective_train_rows"],
            data["train_prefixes"],
            "effective train prefixes",
        )
        require_equal(
            sampling_manifest["one_epoch_total_steps"],
            profile["run"]["total_steps"],
            "one-epoch total steps",
        )
        require_equal(
            sampling_manifest["parquet_shard_count"],
            data["train_parquet_shards"],
            "train parquet shards",
        )
        require_equal(
            sampling_manifest["distributed_allocation"]["data_seed"],
            profile["run"]["data_seed"],
            "distributed data seed",
        )
        train_manifest_record = sampling_manifest
        train_manifest_root = sampling_manifest_path.parent
    else:
        require_equal(
            source_train_record["sample_count"],
            data["train_prefixes"],
            "train prefixes",
        )
        require_equal(
            split_manifest["training_math"][
                "global_batch_size_4_train_steps_ceil"
            ],
            profile["run"]["total_steps"],
            "one-epoch total steps",
        )
        require_equal(
            split_manifest["training_math"]["train_parquet_shards"],
            data["train_parquet_shards"],
            "train parquet shards",
        )
        train_manifest_record = source_train_record
        train_manifest_root = workspace_path(data["split_manifest"]).parent
    require_equal(profile["run"]["global_batch_size"], 4, "global batch size")
    require_equal(profile["run"]["per_rank_batch_size"], 1, "per-rank batch size")
    require_equal(
        profile["run"]["gradient_accumulation_steps"],
        1,
        "gradient accumulation steps",
    )
    require_equal(profile["distributed"]["gpus_per_node"], 4, "GPU count")
    parquet_shards = int(data["train_parquet_shards"])
    rank_count = int(profile["distributed"]["gpus_per_node"])
    workers_per_rank = int(profile["run"]["num_workers_per_rank"])
    if parquet_shards % rank_count != 0:
        raise ValueError("train parquet shards must divide evenly across ranks")
    if (parquet_shards // rank_count) % workers_per_rank != 0:
        raise ValueError("each DataLoader worker must receive at least one whole parquet file")

    train_shards = [
        (record["path"], int(record["rows"]))
        for record in train_manifest_record["parquet_files"]
    ]
    require_equal(len(train_shards), parquet_shards, "train shard records")
    train_shards.sort(key=lambda record: record[0])
    random.Random(int(profile["run"]["data_seed"])).shuffle(train_shards)
    files_per_rank = parquet_shards // rank_count
    files_per_worker = files_per_rank // workers_per_rank
    total_steps = int(profile["run"]["total_steps"])
    worker_step_quotas = [
        (total_steps + workers_per_rank - 1 - worker_id) // workers_per_rank
        for worker_id in range(workers_per_rank)
    ]
    rank_rows: List[int] = []
    worker_rows: List[List[int]] = []
    for rank in range(rank_count):
        rank_shards = train_shards[
            rank * files_per_rank : (rank + 1) * files_per_rank
        ]
        current_worker_rows = [
            sum(
                rows
                for _, rows in rank_shards[
                    worker_id * files_per_worker : (worker_id + 1)
                    * files_per_worker
                ]
            )
            for worker_id in range(workers_per_rank)
        ]
        worker_rows.append(current_worker_rows)
        rank_rows.append(sum(current_worker_rows))
        for worker_id, rows in enumerate(current_worker_rows):
            if rows > worker_step_quotas[worker_id]:
                raise ValueError(
                    "one-epoch horizon would omit unique rows: "
                    f"rank={rank}, worker={worker_id}, rows={rows}, "
                    f"step_quota={worker_step_quotas[worker_id]}"
                )
    padded_samples = total_steps * rank_count
    expected_padding = padded_samples - int(data["train_prefixes"])
    actual_padding = sum(
        worker_step_quotas[worker_id] - rows
        for rank_workers in worker_rows
        for worker_id, rows in enumerate(rank_workers)
    )
    require_equal(actual_padding, expected_padding, "one-epoch synchronization padding")
    profile["_data_allocation"] = {
        "rank_rows": rank_rows,
        "worker_rows": worker_rows,
        "worker_step_quotas": worker_step_quotas,
        "unique_prefixes": int(data["train_prefixes"]),
        "processed_prefixes": padded_samples,
        "padding_repeats": actual_padding,
    }
    require_equal(
        profile["distributed"]["num_replicate"]
        * profile["distributed"]["num_shard"],
        4,
        "FSDP mesh size",
    )
    require_equal(
        profile["optimization"]["cosine_cycles"], 0.5, "cosine cycles"
    )
    require_equal(profile["optimization"]["weight_decay"], 0.0, "weight decay")
    require_equal(
        profile["checkpoint"]["completed_step_interval"],
        600,
        "checkpoint interval",
    )
    keep_last_complete = int(profile["checkpoint"]["keep_last_complete"])
    if keep_last_complete not in (1, 2):
        raise ValueError(
            f"checkpoint retention must be 1 or 2, got {keep_last_complete}"
        )
    if profile_schema == "datamake_lance_stage2_training_profile_v1":
        require_equal(keep_last_complete, 1, "stage2 checkpoint retention")
    require_equal(
        profile["checkpoint"]["save_on_slurm_termination"],
        False,
        "save-on-termination policy",
    )
    require_equal(
        profile["checkpoint"]["save_final_checkpoint"], True, "final checkpoint"
    )
    require_equal(profile["checkpoint"]["require_full_state"], True, "full state")

    model = profile["model"]
    for key, expected in (
        ("precision", "bf16"),
        ("use_flex_attention", True),
        ("train_lance_core", True),
        ("freeze_llm_embed_tokens", True),
        ("freeze_vit", True),
        ("freeze_vae", True),
        ("use_lora", False),
    ):
        require_equal(model[key], expected, f"model {key}")
    if not isinstance(model["use_ema"], bool):
        raise ValueError("model use_ema must be boolean")

    optimization = profile["optimization"]
    if profile_schema == "datamake_lance_stage2_training_profile_v1":
        for key in (
            "text_condition_dropout",
            "vit_condition_dropout",
            "vae_condition_dropout",
        ):
            require_equal(optimization[key], 0.0, f"stage2 {key}")
        require_equal(
            optimization["edit_region_weighting"],
            True,
            "stage2 edit-region weighting",
        )
        require_equal(
            optimization["edit_region_weight_boost"],
            1.0,
            "stage2 edit-region boost",
        )
        if not (
            0
            <= float(optimization["edit_region_low_quantile"])
            < float(optimization["edit_region_high_quantile"])
            <= 1
        ):
            raise ValueError("invalid stage2 edit-region quantiles")

    train_yaml = read_yaml(workspace_path(data["train_config"]))
    dataset_yaml = train_yaml["D1"]["datamake_multiturn_v2v_local"]
    require_equal(
        dataset_yaml["dataset_type"],
        "datamake_multiturn_video2video",
        "train dataset type",
    )
    require_equal(dataset_yaml["raw_bytes_input"], False, "path-based media input")
    require_equal(dataset_yaml["sample_task"], "edit", "train sample task")
    require_equal(
        dataset_yaml["vision_cond_type"], ["vit", "vae_Nsplit"], "vision roles"
    )
    require_equal(
        dataset_yaml["video_transform_args"]["resolution"],
        model["vae_resolution"],
        "VAE resolution",
    )
    require_equal(
        dataset_yaml["vit_video_transform_args"]["resolution"],
        model["vit_resolution"],
        "ViT resolution",
    )
    sampler = dataset_yaml["video_frame_sampler_args"]["params"]
    require_equal(sampler["sample_fps"], model["sample_fps"], "sample fps")
    require_equal(
        sampler["max_duration"],
        model["max_duration_seconds"],
        "maximum sample duration",
    )
    yaml_shards = dataset_yaml["dataset_names"]["datamake_multiturn"]["data_dir"]
    require_equal(len(yaml_shards), parquet_shards, "train YAML shard count")
    manifest_shards = [
        str((train_manifest_root / record["path"]).resolve())
        for record in train_manifest_record["parquet_files"]
    ]
    require_equal(sorted(yaml_shards), sorted(manifest_shards), "train YAML shards")

    for path_key in ("model_path", "vit_path"):
        model_path = workspace_path(profile["model"][path_key])
        if not model_path.is_dir():
            raise FileNotFoundError(f"model directory is missing: {model_path}")

    required_code_markers = {
        LANCE_ROOT / "train/unified_train.py": (
            "checkpoint_completed_steps",
            "save_final_checkpoint",
            "keep_last_checkpoints",
        ),
        LANCE_ROOT / "train/train_utils.py": (
            "lr_num_cycles",
            "allow_val_change=True",
            "build_edit_region_mse_weights",
        ),
        LANCE_ROOT
        / "data/datasets_factory/dataset_datamake_multiturn_v2v_local.py": (
            "dataset_x2v_interleave import X2VInterleaveIterableDataset",
            "DataMakeMultiTurnV2VLocalIterableDataset",
        ),
        LANCE_ROOT / "train/fsdp_utils.py": (
            "checkpoint_complete.json",
            ".incomplete",
            "trainer_state.json",
            "param_dtype=torch.bfloat16",
        ),
    }
    for code_path, markers in required_code_markers.items():
        text = code_path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise ValueError(f"{code_path} lacks formal-training markers: {missing}")

    profile["_profile_path"] = str(profile_path)
    profile["_profile_sha256"] = sha256_file(profile_path)
    return profile


def checkpoint_required_files(marker: Mapping[str, Any]) -> List[str]:
    optimizer_shards = int(marker["optimizer_shards"])
    return [
        "model.safetensors",
        "scheduler.pt",
        "data_status.pt",
        "trainer_state.json",
        "checkpoint_complete.json",
        *[
            f"optimizer.{index:05d}-of-{optimizer_shards:05d}.pt"
            for index in range(optimizer_shards)
        ],
    ]


def validate_complete_checkpoint(
    checkpoint_dir: Path,
    expected_optimizer_shards: int,
    total_steps: int,
) -> Dict[str, Any]:
    checkpoint_dir = checkpoint_dir.resolve()
    if not checkpoint_dir.is_dir() or not checkpoint_dir.name.isdigit():
        raise ValueError(f"checkpoint must be a numeric directory: {checkpoint_dir}")
    marker_path = checkpoint_dir / "checkpoint_complete.json"
    state_path = checkpoint_dir / "trainer_state.json"
    if not marker_path.is_file() or not state_path.is_file():
        raise ValueError(f"checkpoint has no complete marker/state: {checkpoint_dir}")

    marker = read_json(marker_path)
    state = read_json(state_path)
    require_equal(marker.get("status"), "complete", "checkpoint status")
    require_equal(marker["optimizer_shards"], expected_optimizer_shards, "optimizer shards")
    require_equal(marker["completed_steps"], int(checkpoint_dir.name), "checkpoint name")
    require_equal(marker["next_step"], marker["completed_steps"], "next step")
    require_equal(state, {key: marker[key] for key in state}, "trainer state")
    if not 0 < int(marker["completed_steps"]) <= total_steps:
        raise ValueError(f"checkpoint step is outside training horizon: {checkpoint_dir}")

    recorded_sizes = marker.get("required_artifact_sizes", {})
    for filename in checkpoint_required_files(marker):
        artifact = checkpoint_dir / filename
        if not artifact.is_file() or artifact.stat().st_size <= 0:
            raise ValueError(f"checkpoint artifact is missing/empty: {artifact}")
        if filename in recorded_sizes:
            require_equal(
                artifact.stat().st_size,
                recorded_sizes[filename],
                f"checkpoint artifact size {filename}",
            )
    return marker


def list_complete_checkpoints(
    checkpoint_root: Path,
    expected_optimizer_shards: int,
    total_steps: int,
) -> List[Path]:
    if not checkpoint_root.is_dir():
        return []
    complete: List[Path] = []
    for candidate in checkpoint_root.iterdir():
        if not candidate.is_dir() or not candidate.name.isdigit():
            continue
        validate_complete_checkpoint(candidate, expected_optimizer_shards, total_steps)
        complete.append(candidate.resolve())
    return sorted(complete, key=lambda path: int(path.name))


def resolve_resume_checkpoint(profile: Mapping[str, Any], value: str) -> Path | None:
    run = profile["run"]
    output_root = workspace_path(run["output_root"])
    checkpoint_root = output_root / run["run_name"] / "checkpoints"
    optimizer_shards = int(profile["distributed"]["num_shard"])
    complete = list_complete_checkpoints(
        checkpoint_root,
        expected_optimizer_shards=optimizer_shards,
        total_steps=int(run["total_steps"]),
    )
    if value == "none":
        if complete:
            raise ValueError(
                "complete checkpoints already exist; resume explicitly with --resume-from latest"
            )
        return None
    if value == "latest":
        if not complete:
            raise ValueError(f"no complete checkpoint under {checkpoint_root}")
        checkpoint = complete[-1]
    else:
        checkpoint = Path(value).resolve()
        if checkpoint.parent != checkpoint_root.resolve():
            raise ValueError(
                f"resume checkpoint must be under the formal run: {checkpoint_root}"
            )
        validate_complete_checkpoint(
            checkpoint,
            expected_optimizer_shards=optimizer_shards,
            total_steps=int(run["total_steps"]),
        )
    if int(checkpoint.name) >= int(run["total_steps"]):
        raise ValueError(f"training is already complete at {checkpoint}")
    return checkpoint


def build_torchrun_command(
    profile: Mapping[str, Any],
    resume_from: Path | None,
    master_port: int,
    python_env: Path = DEFAULT_ENV,
) -> List[str]:
    data = profile["data"]
    run = profile["run"]
    model = profile["model"]
    dist_config = profile["distributed"]
    optim = profile["optimization"]
    checkpoint = profile["checkpoint"]
    wandb_config = profile["wandb"]

    command = [
        str(python_env / "bin/torchrun"),
        "--nnodes", "1",
        "--nproc-per-node", str(dist_config["gpus_per_node"]),
        "--node-rank", "0",
        "--master-addr", "127.0.0.1",
        "--master-port", str(master_port),
        "train/unified_train.py",
        "--model_path", str(workspace_path(model["model_path"])),
        "--vit_path", str(workspace_path(model["vit_path"])),
        "--vit_type", "qwen_2_5_vl_original",
        "--llm_qk_norm", "True",
        "--llm_qk_norm_und", "True",
        "--llm_qk_norm_gen", "True",
        "--tie_word_embeddings", "False",
        "--max_num_frames", str(model["max_num_frames"]),
        "--max_latent_size", "64",
        "--latent_patch_size", "1", "1", "1",
        "--load_from_lance_checkpoint", "True",
        "--init_from_vlm_checkpoint", "False",
        "--copy_init_moe", "True",
        "--visual_und", "True",
        "--visual_gen", "True",
        "--vae_model_type", "wan",
        "--freeze_llm", "False",
        "--freeze_llm_embed_tokens", "True",
        "--freeze_vit", "True",
        "--freeze_vae", "True",
        "--freeze_und_params", "False",
        "--freeze_und", "False",
        "--dataset_config_file", str(workspace_path(data["train_config"])),
        "--val_dataset_config_file", str(workspace_path(data["validation_config"])),
        "--num_workers", str(run["num_workers_per_rank"]),
        "--prefetch_factor", str(run["prefetch_factor"]),
        "--expected_num_tokens", str(model["max_tokens"]),
        "--max_num_tokens", str(model["max_tokens"]),
        "--max_num_tokens_per_sample", str(model["max_tokens"]),
        "--prefer_buffer_before", str(model["max_tokens"]),
        "--max_buffer_size", "0",
        "--require_und_gen", "True",
        "--data_seed", str(run["data_seed"]),
        "--global_seed", str(run["global_seed"]),
        "--text_cond_dropout_prob", str(optim["text_condition_dropout"]),
        "--vae_cond_dropout_prob", str(optim["vae_condition_dropout"]),
        "--vit_cond_dropout_prob", str(optim["vit_condition_dropout"]),
        "--cfg_type", "0",
        "--warmup_steps", str(optim["warmup_steps"]),
        "--lr_scheduler", str(optim["scheduler"]),
        "--lr_num_cycles", str(optim["cosine_cycles"]),
        "--lr", str(optim["learning_rate"]),
        "--min_lr", str(optim["minimum_learning_rate"]),
        "--beta1", str(optim["beta1"]),
        "--beta2", str(optim["beta2"]),
        "--eps", str(optim["epsilon"]),
        "--max_grad_norm", str(optim["max_gradient_norm"]),
        "--ce_weight", str(optim["ce_weight"]),
        "--mse_weight", str(optim["mse_weight"]),
        "--edit_region_weighting", str(optim.get("edit_region_weighting", False)),
        "--edit_region_weight_boost", str(optim.get("edit_region_weight_boost", 1.0)),
        "--edit_region_low_quantile", str(optim.get("edit_region_low_quantile", 0.5)),
        "--edit_region_high_quantile", str(optim.get("edit_region_high_quantile", 0.9)),
        "--timestep_shift", str(optim["timestep_shift"]),
        "--use_flex", "True",
        "--sharding_strategy", str(dist_config["sharding_strategy"]),
        "--num_replicate", str(dist_config["num_replicate"]),
        "--num_shard", str(dist_config["num_shard"]),
        "--cpu_offload", "False",
        "--use_ema", str(model["use_ema"]),
        "--auto_resume", "False",
        "--resume_model_only", "False",
        "--load_data_status", "True",
        "--outputs_dir", str(workspace_path(run["output_root"])),
        "--total_steps", str(run["total_steps"]),
        "--save_every", str(checkpoint["completed_step_interval"]),
        "--save_final_checkpoint", str(checkpoint["save_final_checkpoint"]),
        "--checkpoint_completed_steps", "True",
        "--keep_last_checkpoints", str(checkpoint["keep_last_complete"]),
        "--ckpt_debug_steps", "-1",
        "--log_every", str(wandb_config["log_every_steps"]),
        "--wandb_project", str(wandb_config["project"]),
        "--wandb_name", str(run["run_name"]),
        "--wandb_runid", str(wandb_config["run_id"]),
        "--wandb_resume", "allow",
        "--wandb_offline", str(wandb_config["mode"] != "online"),
        "--validation_step", "-1",
        "--validation_type", "und_gen",
        "--validation_num_timesteps", "30",
        "--validation_timestep_shift", "3.0",
        "--validation_max_samples", "1",
        "--validation_log_type", "direct",
        "--apply_qwen_2_5_vl_pos_emb", "True",
        "--apply_chat_template", "False",
    ]
    if resume_from is not None:
        command.extend(["--resume_from", str(resume_from)])
    return command


def without_proxy_environment(source: Mapping[str, str]) -> Dict[str, str]:
    env = dict(source)
    for key in PROXY_ENV_KEYS:
        env.pop(key, None)
    return env


def wandb_online_preflight(
    profile: Mapping[str, Any],
    timeout_seconds: int = WANDB_PREFLIGHT_TIMEOUT_SECONDS,
) -> Dict[str, str]:
    env = without_proxy_environment(os.environ)
    env.update(
        {
            "WANDB_ENTITY": str(profile["wandb"]["entity"]),
            "WANDB_PROJECT": str(profile["wandb"]["project"]),
            "WANDB_HTTP_TIMEOUT": "10",
            "WANDB_SILENT": "true",
        }
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", WANDB_PREFLIGHT_CODE],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"W&B online preflight timed out after {timeout_seconds} seconds"
        ) from exc
    if result.returncode != 0:
        error_tail = result.stderr.strip()[-2000:]
        raise RuntimeError(
            f"W&B online preflight failed with exit code {result.returncode}: "
            f"{error_tail}"
        )
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not output_lines:
        raise RuntimeError("W&B online preflight returned no identity payload")
    try:
        identity = json.loads(output_lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("W&B online preflight returned invalid JSON") from exc

    default_entity = str(identity["entity"])
    expected_entity = profile["wandb"]["entity"]
    require_equal(default_entity, expected_entity, "W&B default entity")
    return {
        "username": str(identity["username"]),
        "entity": default_entity,
        "project": str(profile["wandb"]["project"]),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=False)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def build_environment(profile: Mapping[str, Any]) -> Dict[str, str]:
    env = without_proxy_environment(os.environ)
    wandb_config = profile["wandb"]
    env.update(
        {
            "NCCL_DEBUG": env.get("NCCL_DEBUG", "WARN"),
            "PYTORCH_CUDA_ALLOC_CONF": env.get(
                "PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True"
            ),
            "HF_HOME": env.get(
                "HF_HOME", "/scratch/prj0000000275/jcy/.cache/huggingface"
            ),
            "WANDB_MODE": str(wandb_config.get("mode", "online")),
            "WANDB_ENTITY": str(wandb_config["entity"]),
            "WANDB_PROJECT": str(wandb_config["project"]),
            "WANDB_RUN_ID": str(wandb_config["run_id"]),
            "WANDB_RESUME": "allow",
            "WANDB_RUN_GROUP": str(wandb_config["group"]),
            "WANDB_JOB_TYPE": str(wandb_config["job_type"]),
            "WANDB_TAGS": ",".join(wandb_config["tags"]),
            "WANDB_DISABLE_CODE": "true",
            "WANDB_CONSOLE": "off",
            "WANDB_LOG_MODEL": "false",
            "WANDB_INIT_TIMEOUT": "60",
            "WANDB_HTTP_TIMEOUT": "10",
        }
    )
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{LANCE_ROOT}:{current_pythonpath}" if current_pythonpath else str(LANCE_ROOT)
    )
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument(
        "--resume-from",
        default="none",
        help="none for a fresh run, latest for manual resume, or an explicit checkpoint",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="run four-GPU and W&B online checks without launching training",
    )
    parser.add_argument("--master-port", type=int)
    parser.add_argument(
        "--smoke-steps",
        type=int,
        default=0,
        help="launch a no-checkpoint offline technical smoke after validating the full profile",
    )
    return parser.parse_args()


def make_smoke_profile(
    profile: Mapping[str, Any], smoke_steps: int, job_id: str
) -> Dict[str, Any]:
    if smoke_steps < 1:
        raise ValueError("smoke steps must be positive")
    smoke = deepcopy(profile)
    smoke["run"]["run_name"] = (
        f"{profile['run']['run_name']}_smoke{smoke_steps}_job{job_id}"
    )
    smoke["run"]["total_steps"] = smoke_steps
    smoke["checkpoint"]["completed_step_interval"] = 0
    smoke["checkpoint"]["save_final_checkpoint"] = False
    smoke["checkpoint"]["keep_last_complete"] = 1
    smoke["wandb"]["mode"] = "offline"
    smoke["wandb"]["run_id"] = (
        f"{profile['wandb']['run_id']}-smoke{smoke_steps}-job{job_id}"
    )
    smoke["wandb"]["job_type"] = "optimization-smoke"
    smoke["wandb"]["tags"] = list(profile["wandb"]["tags"]) + ["smoke"]
    smoke["_data_allocation"] = {
        "mode": "technical_smoke",
        "optimization_steps": smoke_steps,
        "full_profile_unique_prefixes": profile["_data_allocation"][
            "unique_prefixes"
        ],
    }
    return smoke


def main() -> int:
    args = parse_args()
    profile = validate_profile(args.profile)
    job_id = os.environ.get("SLURM_JOB_ID", "manual")
    if args.smoke_steps:
        if args.resume_from != "none":
            raise ValueError("technical smoke cannot resume a formal checkpoint")
        profile = make_smoke_profile(profile, args.smoke_steps, job_id)
        resume_from = None
    else:
        resume_from = resolve_resume_checkpoint(profile, args.resume_from)
    master_port = args.master_port or (29500 + (int(job_id) % 1000 if job_id.isdigit() else 0))
    command = build_torchrun_command(profile, resume_from, master_port)
    launcher_path = Path(__file__).resolve()
    slurm_script_key = "smoke_job_script" if args.smoke_steps else "job_script"
    slurm_script_path = workspace_path(
        profile["slurm"].get(
            slurm_script_key,
            "10_research/model_experiments/lance/jobs/"
            "datamake_dialogue_first_batch_v1.sbatch",
        )
    )

    summary = {
        "profile": profile["_profile_path"],
        "profile_sha256": profile["_profile_sha256"],
        "launcher": str(launcher_path),
        "launcher_sha256": sha256_file(launcher_path),
        "slurm_script": str(slurm_script_path),
        "slurm_script_sha256": sha256_file(slurm_script_path),
        "resume_from": str(resume_from) if resume_from else None,
        "total_steps": profile["run"]["total_steps"],
        "checkpoint_interval": profile["checkpoint"]["completed_step_interval"],
        "data_allocation": profile["_data_allocation"],
        "command": command,
    }
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    import torch

    visible_gpus = torch.cuda.device_count()
    require_equal(
        visible_gpus,
        profile["distributed"]["gpus_per_node"],
        "visible CUDA device count",
    )
    if profile["wandb"]["mode"] == "online":
        wandb_identity = wandb_online_preflight(profile)
    else:
        wandb_identity = {
            "username": "offline",
            "entity": str(profile["wandb"]["entity"]),
            "project": str(profile["wandb"]["project"]),
        }
    print(json.dumps({"gpu_count": visible_gpus, "wandb": wandb_identity}))
    if args.preflight_only:
        return 0

    run_dir = workspace_path(profile["run"]["output_root"]) / profile["run"]["run_name"]
    segment_name = f"job_{job_id}"
    if job_id == "manual":
        segment_name = f"manual_{os.getpid()}"
    segment_manifest = {
        **summary,
        "schema_version": "datamake_lance_training_segment_v1",
        "slurm_job_id": job_id,
        "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
        "slurm_node_list": os.environ.get("SLURM_JOB_NODELIST"),
        "visible_gpu_count": visible_gpus,
        "wandb": wandb_identity,
        "environment": {
            "python_env": str(DEFAULT_ENV),
            "lance_commit": profile["source"]["lance_commit"],
        },
    }
    write_json(run_dir / "segments" / segment_name / "launch_manifest.json", segment_manifest)
    os.chdir(LANCE_ROOT)
    os.execvpe(command[0], command, build_environment(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit("Archived implementation: restore the complete source snapshot to reproduce it; use current DDP entry points for new work.")
    raise SystemExit(main())
