#!/usr/bin/env python3
"""PEFT/DDP launcher. Default is validation only; training requires --mode train."""
import argparse
from copy import deepcopy
import fcntl
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from datamake_runtime import WORKSPACE_ROOT, LANCE_ROOT, DEFAULT_ENV, workspace_path, build_environment, sha256_file

PEFT_ROOT = LANCE_ROOT.parent / "runtime/peft_0_15_2"
TRAINER = "train/datamake_ddp_train.py"
SOURCE_FILES = [TRAINER, "train/datamake_peft.py", "train/datamake_ddp_checkpoint.py",
                "train/datamake_prefix_data.py", "train/datamake_packed_batch.py",
                "train/datamake_train_state.py",
                "train/datamake_lora_config.py",
                "train/train_utils.py", "train/fsdp_utils.py", "modeling/lance/lance.py",
                "modeling/lance/qwen2_navit.py", "config/config_factory.py", "data/dataset_info.py",
                "data/dataset_base_train.py", "data/common.py",
                "data/datasets_factory/dataset_datamake_multiturn_v2v_local.py",
                "data/datasets_factory/dataset_datamake_mixed_v2v_local.py",
                "data/video/sampler/frames.py", "common/val/utils.py", "data/datamake_reference_image.py"]


def semantic_recipe(profile):
    result = {key: deepcopy(profile[key]) for key in ("data", "model", "optimization", "history", "lora", "freeze", "initialization")}
    result["run"] = {k: v for k, v in profile["run"].items() if k not in ("run_name", "output_root")}
    # Grouping changes hardware batching, while slot-normalized loss preserves
    # the same number and weighting of original microsteps per update.
    batch_size = result["run"]["per_rank_batch_size"]
    result["run"]["per_rank_batch_size"] = 1
    result["run"]["gradient_accumulation_steps"] *= batch_size
    result["world_size"] = profile["distributed"]["gpus_per_node"]
    return result


def load_profile(path):
    profile = json.loads(Path(path).read_text())
    if profile.get("schema_version") != "datamake_lance_ddp_peft_v1":
        raise ValueError("Use the PEFT/DDP profile, not the old FSDP launcher")
    batch_size = profile["run"]["per_rank_batch_size"]
    accumulation = profile["run"]["gradient_accumulation_steps"]
    world_size = profile["distributed"]["gpus_per_node"]
    if profile["distributed"]["nodes"] != 1 or world_size not in (4, 8):
        raise ValueError("DDP entry supports one node with four or eight GPUs")
    if (batch_size not in (1, 2, 4, 8) or type(accumulation) is not int or accumulation < 1
            or profile["run"]["global_batch_size"] != world_size * accumulation * batch_size):
        raise ValueError("Global batch must equal GPUs times batch per rank times accumulation")
    workers = profile["run"]["num_workers_per_rank"]
    if workers not in (1, 2) or profile["data"]["train_parquet_shards"] != world_size * workers:
        raise ValueError("Indexed training requires one parquet per rank/worker slot")
    if profile["ddp"].get("vae_cache_policy", "release") not in ("release", "retain"):
        raise ValueError("VAE cache policy must be release or retain")
    if profile["ddp"].get("attention_padding", "fixed") not in ("fixed", "minimal"):
        raise ValueError("Attention padding must be fixed or minimal")
    disabled = profile["ddp"].get("checkpoint_disabled_layers", [])
    if (not isinstance(disabled, list) or any(type(i) is not int or not 0 <= i < 36 for i in disabled)
            or len(disabled) != len(set(disabled))):
        raise ValueError("Checkpoint-disabled layers must be unique indices in [0, 36)")
    if disabled and profile["ddp"]["activation_checkpointing"] != "all":
        raise ValueError("Explicit disabled layers require activation_checkpointing=all")
    reference = json.loads(workspace_path(profile["ddp"]["source_profile"]).read_text())
    if semantic_recipe(profile) != semantic_recipe(reference):
        raise ValueError("DDP migration must preserve the Stage6 numerical/data recipe")
    if profile["ddp"]["activation_checkpointing"] not in ("all", "alternate", "none"):
        raise ValueError("Invalid activation checkpoint mode")
    if profile["ddp"]["peft_version"] != "0.15.2" or profile["distributed"]["backend"] != "ddp":
        raise ValueError("Unsupported backend/dependency")
    if profile["run"]["run_name"] == reference["run"]["run_name"] or profile["wandb"]["run_id"] == reference["wandb"]["run_id"]:
        raise ValueError("DDP must use a separate output/W&B identity")
    if profile["ddp"].get("adapter_dtype") != "float32" or profile["ddp"].get("base_compute_dtype") != "bfloat16":
        raise ValueError("Unsupported precision policy")
    for key in ("train_config", "validation_config", "test_config", "train_sampling_manifest", "split_manifest"):
        if hashlib.sha256(workspace_path(profile["data"][key]).read_bytes()).hexdigest() != profile["data"][key + "_sha256"]:
            raise ValueError(f"Data contract mismatch: {key}")
    if any(key in profile["data"] for key in (
            "reference_image_audit", "reference_image_audit_sha256", "reference_image_mode")):
        from prepare_datamake_reference_training import validate_reference_profile
        validate_reference_profile(profile)
    return profile


def make_contract(profile):
    files = [LANCE_ROOT / name for name in SOURCE_FILES] + [Path(__file__), Path(__file__).with_name("datamake_runtime.py")]
    if "reference_image_audit" in profile["data"]:
        files.append(Path(__file__).with_name("prepare_datamake_reference_training.py"))
    return {
        "schema_version": "datamake_ddp_peft_contract_v1",
        "profile_sha256": hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest(),
        "base_model": str(workspace_path(profile["model"]["model_path"])),
        "base_model_sha256": "7f0550e1d1511b29a4740a67c1e18e176302a4ecb3177c8a5850ff5fe6447c25",
        "dataset_config": str(workspace_path(profile["data"]["train_config"])),
        "dataset_config_sha256": profile["data"]["train_config_sha256"],
        "recipe": semantic_recipe(profile), "backend": "ddp", "peft_version": "0.15.2",
        "runtime_versions": {name: version(name) for name in ("torch", "transformers", "accelerate")},
        "implementation_sha256": {str(p.resolve().relative_to(WORKSPACE_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    }


def environment(profile):
    env = build_environment(profile)
    env["PYTHONPATH"] = f"{PEFT_ROOT}:{LANCE_ROOT}:{env.get('PYTHONPATH', '')}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["OMP_NUM_THREADS"] = "1"
    return env


def command(profile_path, run, resume=None, stop=None, smoke=False, port=29500, trace=False, world_size=4):
    cmd = [str(DEFAULT_ENV / "bin/torchrun"), "--nnodes=1", f"--nproc-per-node={world_size}", "--master-addr=127.0.0.1",
           f"--master-port={port}", TRAINER, "--profile", str(Path(profile_path).resolve()), "--run-dir", str(run)]
    if resume:
        cmd += ["--resume-from", str(resume)]
    if stop is not None:
        cmd += ["--stop-after", str(stop)]
    if smoke:
        cmd.append("--smoke")
    if trace:
        cmd.append("--trace")
    return cmd


def gate_passed(path, key):
    try:
        record = json.loads(path.read_text())
        return record.get("status") == "passed" and record.get("contract_sha256") == key
    except (OSError, ValueError):
        return False


def verify_gate(continuous, prefix, resumed, first_step=0, world_size=4):
    import torch
    from safetensors.torch import load_file
    from verify_datamake_online_rollout_resume import comparison
    from train.datamake_ddp_checkpoint import validate
    c, p, r = [d / "checkpoints" / f"{step:07d}" for d, step in
               ((continuous, first_step + 3), (prefix, first_step + 2), (resumed, first_step + 3))]
    for path in (c, p, r):
        validate(path, expected_world=world_size)
    atol, rtol = 1e-7, 1e-5
    report = {"atol": atol, "rtol": rtol}
    continuous_adapter = load_file(str(c / "adapter.safetensors"))
    resumed_adapter = load_file(str(r / "adapter.safetensors"))
    report["adapter"] = comparison(continuous_adapter, resumed_adapter, atol, rtol)
    for name in ("optimizer.pt", "scheduler.pt", *[f"rng.rank-{rank:05d}-of-{world_size:05d}.pt" for rank in range(world_size)]):
        report[name] = comparison(torch.load(c / name, map_location="cpu", weights_only=False), torch.load(r / name, map_location="cpu", weights_only=False), atol, rtol)
    report["cursor"] = comparison(json.loads((c / "trainer_state.json").read_text()), json.loads((r / "trainer_state.json").read_text()), atol, rtol)
    for rank in range(world_size):
        a, b = [json.loads((d / f"trace.rank-{rank}.jsonl").read_text().splitlines()[-1]) for d in (continuous, resumed)]
        # Allocator history changes on restart; it is performance telemetry,
        # not training state. Keep every other trace field in the comparison.
        for trace in (a, b):
            for key in ("peak_allocated_gib", "peak_reserved_gib"):
                trace.pop(key, None)
        a["loss"], b["loss"] = torch.tensor(a["loss"]), torch.tensor(b["loss"])
        report[f"trace_rank_{rank}"] = comparison(a, b, atol, rtol)
    changed = load_file(str(p / "adapter.safetensors"))
    gen_b = [name for name in changed if name.endswith(".lora_B.weight") and ("_moe_gen." in name or name.startswith(("vae2llm.", "llm2vae.", "time_embedder.")))]
    if len(gen_b) != 256 or any(not changed[name].count_nonzero() for name in gen_b):
        raise RuntimeError("Nonzero generation adapter gate failed")
    # B is already nonzero when resuming an existing run. Verify the next
    # update after the prefix in both arms, beyond the fresh LR=0 first step.
    update_counts = {
        label: sum(not torch.equal(changed[name], state[name]) for name in gen_b)
        for label, state in (("continuous", continuous_adapter), ("resumed", resumed_adapter))
    }
    if not all(update_counts.values()):
        raise RuntimeError(f"Generation adapters did not update after prefix: {update_counts}")
    report["generation_update"] = {"within_tolerance": True, "changed_b_tensors": update_counts}
    report["status"] = "passed" if all(v["within_tolerance"] for v in report.values() if isinstance(v, dict)) else "failed"
    if report["status"] != "passed":
        raise RuntimeError(json.dumps(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--resume-from", default="none")
    parser.add_argument("--mode", choices=("validate", "benchmark", "train"), default="validate")
    parser.add_argument("--benchmark-updates", type=int, default=20)
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    profile = load_profile(args.profile)
    world_size = profile["distributed"]["gpus_per_node"]
    run = workspace_path(profile["run"]["output_root"]) / profile["run"]["run_name"]
    resume = None
    if args.resume_from == "latest":
        paths = sorted((run / "checkpoints").glob("[0-9]*/checkpoint_complete.json"))
        if not paths:
            raise FileNotFoundError("No complete DDP checkpoint")
        resume = paths[-1].parent
    elif args.resume_from != "none":
        resume = args.profile.parent.parent / args.resume_from if not Path(args.resume_from).is_absolute() else Path(args.resume_from)
        resume = resume.resolve()
    contract = make_contract(profile)
    if sha256_file(workspace_path(profile["model"]["model_path"]) / "model.safetensors") != contract["base_model_sha256"]:
        raise ValueError("Official base weights differ from the checkpoint contract")
    gate_key = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    gate = run / "startup_validation" / f"passed-{gate_key}.json"
    sys.path[:0] = [str(PEFT_ROOT), str(LANCE_ROOT)]
    from train.datamake_ddp_checkpoint import validate
    first_step = validate(resume, contract, world_size)["next_step"] if resume else 0
    if args.dry_run:
        print(json.dumps({"mode": args.mode, "run": str(run), "resume": str(resume), "next_step": first_step,
                          "gate_required": not gate_passed(gate, gate_key), "contract": contract}, indent=2))
        return
    if os.environ.get("SLURM_JOB_PARTITION") != "testqueue":
        raise RuntimeError("GPU execution requires a testqueue allocation")
    if not (PEFT_ROOT / "peft").is_dir():
        raise RuntimeError("Install the pinned PEFT dependency into runtime/peft_0_15_2")
    if first_step + 3 > profile["run"]["total_steps"] and not gate_passed(gate, gate_key):
        raise ValueError("Not enough remaining steps for startup validation")
    run.mkdir(parents=True, exist_ok=True)
    with (run / ".ddp.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        env = environment(profile)
        port = 20000 + int(os.environ["SLURM_JOB_ID"]) % 20000
        def launch(directory, source=None, stop=None, smoke=True, trace=False):
            started = perf_counter()
            result = subprocess.run(command(args.profile, directory, source, stop, smoke, port, trace, world_size), cwd=LANCE_ROOT, env=env)
            directory.mkdir(parents=True, exist_ok=True)
            with (directory / "launch_segments.jsonl").open("a") as stream:
                stream.write(json.dumps({"wall_seconds": perf_counter() - started,
                                         "returncode": result.returncode, "resume": str(source),
                                         "stop_after": stop, "smoke": smoke, "trace": trace,
                                         "scope": "includes process/model/data startup, logging and checkpoint IO"}) + "\n")
            result.check_returncode()
        if not gate_passed(gate, gate_key):
            parent = run / "startup_validation" / f"job-{os.environ['SLURM_JOB_ID']}"
            parent.mkdir(parents=True, exist_ok=False)
            c, p, r = [parent / name for name in ("continuous", "prefix", "resumed")]
            launch(c, resume, first_step + 3)
            launch(p, resume, first_step + 2)
            launch(r, p / "checkpoints" / f"{first_step+2:07d}", first_step + 3)
            report = verify_gate(c, p, r, first_step, world_size)
            report["contract_sha256"] = gate_key
            temporary_gate = gate.with_suffix(".tmp")
            temporary_gate.write_text(json.dumps(report, indent=2) + "\n")
            os.replace(temporary_gate, gate)
        if args.mode == "benchmark":
            if args.benchmark_updates < 4:
                raise ValueError("Benchmark needs warmup and measured updates")
            directory = run / "benchmarks" / f"job-{os.environ['SLURM_JOB_ID']}"
            launch(directory, resume, first_step + args.benchmark_updates, trace=args.trace)
        elif args.mode == "train":
            if not profile["training_authorized"]:
                raise RuntimeError("Formal training is disabled in this profile")
            if not resume and (run / "metrics.jsonl").exists():
                raise ValueError("Existing training history; explicitly resume a checkpoint")
            launch(run, resume, smoke=False)


if __name__ == "__main__":
    main()
