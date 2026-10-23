"""Shared paths, environment and official model argument mapping for current trainers."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]

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

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def workspace_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (WORKSPACE_ROOT / path).resolve()

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
