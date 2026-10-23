#!/usr/bin/env python3
"""Validate and launch the frozen DataMake chain-history LoRA profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Mapping


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
LANCE_ROOT = WORKSPACE_ROOT / "10_research/model_experiments/lance/lance"
DEFAULT_PROFILE = (
    WORKSPACE_ROOT
    / "10_research/model_experiments/lance/configs/"
    "datamake_dialogue_one_step_x0_lora_r64_v3.json"
)
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


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (WORKSPACE_ROOT / path).resolve()


def read_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")


def validate_profile(profile_path: Path, verify_base_hash: bool = True) -> Dict[str, Any]:
    profile_path = profile_path.resolve()
    profile = read_json(profile_path)
    require_equal(
        profile.get("schema_version"),
        "datamake_lance_one_step_x0_lora_profile_v3",
        "profile schema",
    )
    commit = subprocess.run(
        ["git", "-C", str(LANCE_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    require_equal(commit, profile["source"]["lance_commit"], "Lance commit")
    implementation_files = profile["source"].get("implementation_files", {})
    if not implementation_files:
        raise ValueError("chain-history profile must freeze implementation hashes")
    for relative_path, expected_sha256 in implementation_files.items():
        implementation_path = workspace_path(relative_path)
        if not implementation_path.is_file():
            raise FileNotFoundError(implementation_path)
        require_equal(
            sha256_file(implementation_path),
            expected_sha256,
            f"implementation hash {relative_path}",
        )

    data = profile["data"]
    chain_manifest_path = workspace_path(data["train_chain_manifest"])
    config_path = workspace_path(data["train_config"])
    require_equal(
        sha256_file(chain_manifest_path),
        data["train_chain_manifest_sha256"],
        "train chain manifest hash",
    )
    require_equal(
        sha256_file(config_path), data["train_config_sha256"], "train config hash"
    )
    chain_manifest = read_json(chain_manifest_path)
    for key, expected in (
        ("schema_version", "datamake_lance_chain_dataset_manifest_v1"),
        ("split", "train"),
        ("history_mode", data["chain_artifact_history_mode"]),
        ("record_level", "chain"),
        ("chain_count", data["train_chains"]),
        ("target_video_count", data["train_target_videos_per_epoch"]),
    ):
        require_equal(chain_manifest[key], expected, f"chain manifest {key}")
    require_equal(
        chain_manifest["chain_length_count"], data["chain_length_count"], "chain lengths"
    )

    run = profile["run"]
    require_equal(run["epochs"], 4, "epochs")
    require_equal(run["gradient_accumulation_steps"], 2, "gradient accumulation")
    require_equal(run["optimizer_steps_per_epoch"], 450, "steps per epoch")
    require_equal(run["total_steps"], 1800, "total steps")
    require_equal(run["gpus"], 4, "GPU count")
    expected_steps = (
        data["train_chains"]
        * run["epochs"]
        // run["gpus"]
        // run["gradient_accumulation_steps"]
    )
    require_equal(expected_steps, run["total_steps"], "training math")

    lora = profile["lora"]
    for label, actual, expected in (
        ("LoRA rank", lora["rank"], 64),
        ("LoRA alpha", lora["alpha"], 64.0),
        ("LoRA dropout", lora["dropout"], 0.0),
        ("LoRA targets", lora["target_modules"], 256),
        ("learning rate", profile["optimization"]["learning_rate"], 1e-4),
        ("minimum learning rate", profile["optimization"]["minimum_learning_rate"], 1e-5),
        ("warmup", profile["optimization"]["warmup_steps"], 20),
        ("scheduler", profile["optimization"]["scheduler"], "cosine"),
        ("training timestep shift", profile["optimization"]["timestep_shift"], 4.0),
        ("CE weight", profile["loss"]["ce_weight"], 0.0),
        ("region weighting", profile["loss"]["edit_region_weighting"], False),
        ("history mode", data["history_mode"], "one_step_x0_history"),
        ("history method", profile["rollout"]["method"], "training_forward_pred_x0"),
        ("extra denoising steps", profile["rollout"]["diffusion_steps"], 0),
        ("rollout CFG", profile["rollout"]["text_cfg"], 1.0),
        ("rollout timestep shift", profile["rollout"]["timestep_shift"], 4.0),
        ("reuse training forward", profile["rollout"]["reuse_training_forward"], True),
        ("rollout KV cache", profile["rollout"]["use_kv_cache"], False),
        ("checkpoint interval", profile["checkpoint"]["completed_optimizer_step_interval"], 50),
        ("checkpoint retention", profile["checkpoint"]["keep_last_complete"], 4),
        ("ViT type", profile["model"]["vit_type"], "qwen_2_5_vl_original"),
        ("latent patch size", profile["model"]["latent_patch_size"], [1, 1, 1]),
        ("maximum frames", profile["model"]["max_num_frames"], 121),
        ("maximum latent size", profile["model"]["max_latent_size"], 64),
        ("visual generation path", profile["model"]["visual_gen"], True),
        ("visual understanding path", profile["model"]["visual_und"], True),
        ("FSDP sharding", profile["distributed"]["sharding_strategy"], "HYBRID_SHARD"),
        ("separate online rollout", profile["rollout"]["online_during_training"], False),
    ):
        require_equal(actual, expected, label)
    require_equal(
        profile["optimization"]["timestep_shift"],
        profile["rollout"]["timestep_shift"],
        "optimization/rollout timestep shift",
    )
    require_equal(
        profile["condition_dropout"], {"text": 0.0, "vit": 0.0, "vae": 0.0}, "dropout"
    )
    require_equal(profile["freeze"]["only_lora_A_and_lora_B_trainable"], True, "freeze")
    require_equal(profile["checkpoint"]["adapter_only_model_weights"], True, "adapter checkpoint")
    require_equal(profile["checkpoint"]["store_optimizer"], True, "optimizer checkpoint")
    require_equal(profile["checkpoint"]["format_version"], 5, "checkpoint format")
    require_equal(lora["adapter_weight_dtype"], "float32", "adapter dtype")
    require_equal(
        lora["adapter_tensor_bytes"],
        lora["trainable_parameters"] * 4,
        "adapter tensor bytes",
    )

    model_path = workspace_path(profile["model"]["model_path"])
    model_file = model_path / "model.safetensors"
    if not model_file.is_file():
        raise FileNotFoundError(model_file)
    if (model_path / "datamake_lora_config.json").exists():
        raise ValueError("fresh run base must be the plain official checkpoint")
    if verify_base_hash:
        require_equal(
            sha256_file(model_file),
            profile["model"]["model_safetensors_sha256"],
            "official base model hash",
        )
    return profile


def validate_complete_checkpoint(
    checkpoint: Path, profile: Mapping[str, Any]
) -> Dict[str, Any]:
    checkpoint = checkpoint.resolve()
    marker = read_json(checkpoint / "checkpoint_complete.json")
    require_equal(marker.get("status"), "complete", "checkpoint status")
    require_equal(marker.get("adapter_only"), True, "adapter-only marker")
    require_equal(marker.get("checkpoint_format_version"), 5, "checkpoint format")
    require_equal(marker.get("world_size"), profile["run"]["gpus"], "checkpoint world size")
    completed = int(marker["completed_steps"])
    if not 0 < completed < int(profile["run"]["total_steps"]):
        raise ValueError("resume checkpoint step is outside the unfinished schedule")
    for relative, size in marker["required_artifact_sizes"].items():
        artifact = checkpoint / relative
        if not artifact.is_file() or artifact.stat().st_size != int(size):
            raise ValueError(f"checkpoint artifact differs: {artifact}")
    if not (checkpoint / "optimizer" / ".metadata").is_file():
        raise ValueError("checkpoint optimizer state is incomplete")
    return marker


def list_complete_checkpoints(root: Path, profile: Mapping[str, Any]) -> List[Path]:
    if not root.is_dir():
        return []
    result = []
    for path in root.iterdir():
        if not path.is_dir() or not path.name.isdigit():
            continue
        try:
            validate_complete_checkpoint(path, profile)
        except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError):
            continue
        result.append(path.resolve())
    return sorted(result, key=lambda path: int(path.name))


def execution_run_name(
    profile: Mapping[str, Any], smoke_steps: int = 0, smoke_label: str = ""
) -> str:
    """Return a stable output name across fresh and resumed smoke segments."""

    name = str(profile["run"]["run_name"])
    if not smoke_steps:
        return name
    suffix = f"_{smoke_label}" if smoke_label else ""
    return name + "_smoke" + suffix


def resolve_resume(
    profile: Mapping[str, Any], value: str, smoke_steps: int = 0, smoke_label: str = ""
) -> Path | None:
    root = (
        workspace_path(profile["run"]["output_root"])
        / execution_run_name(profile, smoke_steps, smoke_label)
        / "checkpoints"
    )
    complete = list_complete_checkpoints(root, profile)
    if value == "none":
        if complete:
            raise ValueError("complete checkpoints exist; use --resume-from latest")
        return None
    if value == "latest":
        if not complete:
            raise ValueError("no complete online-LoRA checkpoint exists")
        return complete[-1]
    checkpoint = Path(value).resolve()
    if checkpoint.parent != root.resolve():
        raise ValueError(f"resume checkpoint must be under {root}")
    validate_complete_checkpoint(checkpoint, profile)
    return checkpoint


def build_torchrun_command(
    profile: Mapping[str, Any],
    profile_path: Path,
    resume_from: Path | None,
    master_port: int,
    smoke_steps: int = 0,
    smoke_label: str = "",
    python_env: Path = DEFAULT_ENV,
) -> List[str]:
    data = profile["data"]
    run = profile["run"]
    model = profile["model"]
    lora = profile["lora"]
    rollout = profile["rollout"]
    loss = profile["loss"]
    optim = profile["optimization"]
    checkpoint = profile["checkpoint"]
    distributed = profile["distributed"]
    wandb_config = profile["wandb"]
    is_smoke = smoke_steps > 0
    total_steps = smoke_steps if is_smoke else run["total_steps"]
    run_name = execution_run_name(profile, smoke_steps, smoke_label)
    smoke_suffix = "-smoke" + (f"-{smoke_label}" if smoke_label else "")
    run_id = wandb_config["run_id"] + (smoke_suffix if is_smoke else "")

    command = [
        str(python_env / "bin/torchrun"),
        "--nnodes", "1",
        "--nproc-per-node", str(run["gpus"]),
        "--node-rank", "0",
        "--master-addr", "127.0.0.1",
        "--master-port", str(master_port),
        "train/datamake_online_rollout_lora_train.py",
        "--model_path", str(workspace_path(model["model_path"])),
        "--vit_path", str(workspace_path(model["vit_path"])),
        "--vit_type", str(model["vit_type"]),
        "--llm_qk_norm", str(model["llm_qk_norm"]),
        "--llm_qk_norm_und", str(model["llm_qk_norm_und"]),
        "--llm_qk_norm_gen", str(model["llm_qk_norm_gen"]),
        "--tie_word_embeddings", str(model["tie_word_embeddings"]),
        "--max_num_frames", str(model["max_num_frames"]),
        "--max_latent_size", str(model["max_latent_size"]),
        "--latent_patch_size", *map(str, model["latent_patch_size"]),
        "--load_from_lance_checkpoint", str(model["load_from_lance_checkpoint"]),
        "--init_from_vlm_checkpoint", str(model["init_from_vlm_checkpoint"]),
        "--copy_init_moe", str(model["copy_init_moe"]),
        "--visual_und", str(model["visual_und"]),
        "--visual_gen", str(model["visual_gen"]),
        "--vae_model_type", str(model["vae_model_type"]),
        "--freeze_llm", "False",
        "--freeze_llm_embed_tokens", "True",
        "--freeze_vit", "True",
        "--freeze_vit_connector", "False",
        "--freeze_vae", "True",
        "--freeze_und_params", "True",
        "--freeze_und", "True",
        "--dataset_config_file", str(workspace_path(data["train_config"])),
        "--num_workers", "0",
        "--prefetch_factor", "2",
        "--expected_num_tokens", str(model["max_tokens"]),
        "--max_num_tokens", str(model["max_tokens"]),
        "--max_num_tokens_per_sample", str(model["max_tokens"]),
        "--prefer_buffer_before", str(model["max_tokens"]),
        "--max_buffer_size", "0",
        "--require_und_gen", "True",
        "--data_seed", str(data["schedule_seed"]),
        "--global_seed", str(run["global_seed"]),
        "--text_cond_dropout_prob", str(profile["condition_dropout"]["text"]),
        "--vae_cond_dropout_prob", str(profile["condition_dropout"]["vae"]),
        "--vit_cond_dropout_prob", str(profile["condition_dropout"]["vit"]),
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
        "--ce_weight", str(loss["ce_weight"]),
        "--mse_weight", str(loss["mse_weight"]),
        "--edit_region_weighting", "False",
        "--timestep_shift", str(optim["timestep_shift"]),
        "--use_flex", "True",
        "--sharding_strategy", str(distributed["sharding_strategy"]),
        "--num_replicate", str(distributed["num_replicate"]),
        "--num_shard", str(distributed["num_shard"]),
        "--cpu_offload", "False",
        "--use_ema", "False",
        "--auto_resume", "False",
        "--resume_model_only", "False",
        "--load_data_status", "False",
        "--outputs_dir", str(workspace_path(run["output_root"])),
        "--total_steps", str(total_steps),
        "--save_every", str(0 if is_smoke else checkpoint["completed_optimizer_step_interval"]),
        "--save_final_checkpoint", "True",
        "--checkpoint_completed_steps", "True",
        "--keep_last_checkpoints", str(checkpoint["keep_last_complete"]),
        "--ckpt_debug_steps", "-1",
        "--log_every", str(wandb_config["log_every_steps"]),
        "--wandb_project", str(wandb_config["project"]),
        "--wandb_name", run_name,
        "--wandb_runid", run_id,
        "--wandb_resume", "allow",
        "--wandb_offline", str(is_smoke or wandb_config["mode"] != "online"),
        "--validation_step", "-1",
        "--apply_qwen_2_5_vl_pos_emb", str(model["apply_qwen_2_5_vl_pos_emb"]),
        "--apply_chat_template", str(model["apply_chat_template"]),
        "--datamake_chain_manifest", str(workspace_path(data["train_chain_manifest"])),
        "--datamake_profile_path", str(profile_path.resolve()),
        "--datamake_profile_sha256", sha256_file(profile_path.resolve()),
        "--datamake_history_mode", str(data["history_mode"]),
        "--datamake_gradient_accumulation_steps", str(run["gradient_accumulation_steps"]),
        "--datamake_num_epochs", str(run["epochs"]),
        "--datamake_rollout_diffusion_steps", str(rollout["diffusion_steps"]),
        "--datamake_rollout_cfg_text_scale", str(rollout["text_cfg"]),
        "--datamake_rollout_timestep_shift", str(rollout["timestep_shift"]),
        "--datamake_rollout_cfg_interval", *map(str, rollout["cfg_interval"]),
        "--datamake_rollout_cfg_renorm_min", str(rollout["cfg_renorm_min"]),
        "--datamake_rollout_cfg_renorm_type", str(rollout["cfg_renorm_type"]),
        "--datamake_rollout_use_kv_cache", str(rollout["use_kv_cache"]),
        "--datamake_rollout_retry_count", "1",
        "--datamake_lora_rank", str(lora["rank"]),
        "--datamake_lora_alpha", str(lora["alpha"]),
        "--datamake_lora_dropout", str(lora["dropout"]),
        "--datamake_lora_target_scope", str(lora["target_scope"]),
        "--datamake_lora_expected_target_modules", str(lora["target_modules"]),
        "--datamake_lora_expected_target_signature_sha256", str(lora["target_signature_sha256"]),
        "--datamake_base_model_sha256", str(model["model_safetensors_sha256"]),
        "--datamake_smoke_mode", str(is_smoke),
        "--datamake_smoke_label", smoke_label,
    ]
    if resume_from is not None:
        command.extend(["--resume_from", str(resume_from)])
    return command


def build_environment(profile: Mapping[str, Any]) -> Dict[str, str]:
    environment = dict(os.environ)
    for key in PROXY_ENV_KEYS:
        environment.pop(key, None)
    wandb_config = profile["wandb"]
    environment.update(
        {
            "HF_HOME": environment.get(
                "HF_HOME", "/scratch/prj0000000275/jcy/.cache/huggingface"
            ),
            "NCCL_DEBUG": environment.get("NCCL_DEBUG", "WARN"),
            "PYTORCH_CUDA_ALLOC_CONF": environment.get(
                "PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True"
            ),
            "WANDB_MODE": str(wandb_config["mode"]),
            "WANDB_ENTITY": str(wandb_config["entity"]),
            "WANDB_PROJECT": str(wandb_config["project"]),
            "WANDB_RUN_GROUP": str(wandb_config["group"]),
            "WANDB_JOB_TYPE": str(wandb_config["job_type"]),
            "WANDB_TAGS": ",".join(wandb_config["tags"]),
            "WANDB_DISABLE_CODE": "true",
            "WANDB_CONSOLE": "off",
            "WANDB_LOG_MODEL": "false",
            "WANDB_INIT_TIMEOUT": "60",
            "WANDB_HTTP_TIMEOUT": "10",
            "PYTHONUNBUFFERED": "1",
        }
    )
    previous = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = f"{LANCE_ROOT}:{previous}" if previous else str(LANCE_ROOT)
    return environment


def wandb_online_preflight(
    profile: Mapping[str, Any],
    timeout_seconds: int = WANDB_PREFLIGHT_TIMEOUT_SECONDS,
) -> Dict[str, str]:
    environment = build_environment(profile)
    environment["WANDB_SILENT"] = "true"
    try:
        result = subprocess.run(
            [sys.executable, "-c", WANDB_PREFLIGHT_CODE],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=environment,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"W&B online preflight timed out after {timeout_seconds} seconds"
        ) from error
    if result.returncode != 0:
        raise RuntimeError(
            "W&B online preflight failed: " + result.stderr.strip()[-2000:]
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("W&B online preflight returned no identity")
    identity = json.loads(lines[-1])
    require_equal(
        str(identity["entity"]), str(profile["wandb"]["entity"]), "W&B entity"
    )
    return {
        "username": str(identity["username"]),
        "entity": str(identity["entity"]),
        "project": str(profile["wandb"]["project"]),
    }


def write_json_new(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=False)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--resume-from", default="none")
    parser.add_argument("--master-port", type=int, default=29543)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate four visible GPUs and W&B identity without training.",
    )
    parser.add_argument("--smoke-steps", type=int, default=0)
    parser.add_argument("--smoke-label", default="")
    parser.add_argument(
        "--skip-base-hash",
        action="store_true",
        help="Only for repeated static inspection; never use before a real launch.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 <= args.smoke_steps <= 10:
        raise ValueError("--smoke-steps must be 0..10")
    if args.smoke_label and not args.smoke_steps:
        raise ValueError("--smoke-label requires --smoke-steps")
    if args.smoke_label and re.fullmatch(r"[a-z0-9_-]+", args.smoke_label) is None:
        raise ValueError("--smoke-label must use lowercase letters, digits, '_' or '-'")
    profile_path = args.profile.resolve()
    profile = validate_profile(profile_path, verify_base_hash=not args.skip_base_hash)
    resume_from = resolve_resume(
        profile, args.resume_from, args.smoke_steps, args.smoke_label
    )
    if args.smoke_steps and resume_from is not None:
        completed_steps = int(
            read_json(resume_from / "checkpoint_complete.json")["completed_steps"]
        )
        if completed_steps >= args.smoke_steps:
            raise ValueError(
                "resumed smoke target must exceed the checkpoint completed step"
            )
    command = build_torchrun_command(
        profile,
        profile_path,
        resume_from,
        args.master_port,
        smoke_steps=args.smoke_steps,
        smoke_label=args.smoke_label,
    )
    print(shlex.join(command))
    if args.dry_run:
        return
    if (
        not args.smoke_steps
        and not args.preflight_only
        and not profile.get("training_authorized", False)
    ):
        raise RuntimeError(
            "formal training is not authorized; complete the GPU smoke/review and "
            "change the frozen profile status explicitly"
        )
    import torch

    visible_gpus = torch.cuda.device_count()
    require_equal(visible_gpus, profile["run"]["gpus"], "visible CUDA devices")
    if args.smoke_steps:
        wandb_identity = {
            "username": "offline-smoke",
            "entity": str(profile["wandb"]["entity"]),
            "project": str(profile["wandb"]["project"]),
        }
    else:
        wandb_identity = wandb_online_preflight(profile)
    if args.preflight_only:
        print(json.dumps({"gpu_count": visible_gpus, "wandb": wandb_identity}))
        return

    run = profile["run"]
    run_name = execution_run_name(profile, args.smoke_steps, args.smoke_label)
    job_id = os.environ.get("SLURM_JOB_ID", "manual")
    segment = f"job_{job_id}" if job_id != "manual" else f"manual_{os.getpid()}"
    job_script = profile["slurm"][
        "smoke_job_script" if args.smoke_steps else "job_script"
    ]
    job_script_path = workspace_path(job_script)
    launch_manifest = {
        "schema_version": "datamake_lance_online_rollout_segment_v1",
        "profile": str(profile_path),
        "profile_sha256": sha256_file(profile_path),
        "launcher": str(Path(__file__).resolve()),
        "launcher_sha256": sha256_file(Path(__file__).resolve()),
        "slurm_script": str(job_script_path),
        "slurm_script_sha256": sha256_file(job_script_path),
        "slurm_job_id": job_id,
        "slurm_node_list": os.environ.get("SLURM_JOB_NODELIST"),
        "resume_from": str(resume_from) if resume_from else None,
        "smoke_steps": args.smoke_steps,
        "smoke_label": args.smoke_label or None,
        "visible_gpu_count": visible_gpus,
        "wandb": wandb_identity,
        "command": command,
        "environment": {
            "python_env": str(DEFAULT_ENV),
            "lance_commit": profile["source"]["lance_commit"],
        },
    }
    run_dir = workspace_path(run["output_root"]) / run_name
    write_json_new(
        run_dir / "segments" / segment / "launch_manifest.json",
        launch_manifest,
    )
    subprocess.run(command, cwd=LANCE_ROOT, env=build_environment(profile), check=True)


if __name__ == "__main__":
    raise SystemExit("Archived implementation: restore the complete source snapshot to reproduce it; use current DDP entry points for new work.")
    main()
