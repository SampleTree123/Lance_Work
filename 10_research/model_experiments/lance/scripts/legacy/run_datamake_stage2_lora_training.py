#!/usr/bin/env python3
"""Stage6 launcher: short profile command, automatic 3 vs 2+resume GPU gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from run_datamake_formal_training import (
    WORKSPACE_ROOT, LANCE_ROOT, DEFAULT_ENV, workspace_path, build_environment,
)

BASE_SHA256 = "7f0550e1d1511b29a4740a67c1e18e176302a4ecb3177c8a5850ff5fe6447c25"
TRAINER = "train/datamake_stage2_lora_train.py"


def load_profile(path):
    profile = json.loads(Path(path).read_text())
    if profile["schema_version"] != "datamake_lance_stage2_lora_pair_v1":
        raise ValueError("Use an implemented Stage6 profile")
    if not profile["training_authorized"]:
        raise ValueError("Stage6 profile is not authorized for training")
    if profile["history"]["mode"] != "teacher_forced" or profile["history"]["online_rollout"]:
        raise ValueError("Stage6 is GT prefix training, not online rollout")
    if profile["freeze"]["understanding_activation_detach"]:
        raise ValueError("Both arms must preserve freeze_und=False")
    run = profile["run"]
    world = profile["distributed"]["gpus_per_node"]
    if run["per_rank_batch_size"] != 1 or run["global_batch_size"] != world * run["gradient_accumulation_steps"]:
        raise ValueError("Invalid effective batch size")
    return profile


def make_contract(profile, profile_path):
    paths = [
        LANCE_ROOT / TRAINER,
        *[LANCE_ROOT / "train" / name for name in (
            "datamake_branch_lora.py", "datamake_stage2_lora_checkpoint.py",
            "datamake_stage2_lora_data.py", "datamake_lora_checkpoint.py",
            "datamake_generation_lora.py", "train_utils.py", "fsdp_utils.py")],
        LANCE_ROOT / "data/dataset_base_train.py",
        LANCE_ROOT / "data/datasets_factory/dataset_datamake_multiturn_v2v_local.py",
        Path(__file__), Path(__file__).with_name("run_datamake_formal_training.py"),
    ]
    return {
        "schema_version": "datamake_stage6_prefix_lora_contract_v1",
        "profile_sha256": hashlib.sha256(Path(profile_path).read_bytes()).hexdigest(),
        "base_model": str(workspace_path(profile["model"]["model_path"])),
        "base_model_sha256": BASE_SHA256,
        "dataset_config": str(workspace_path(profile["data"]["train_config"])),
        "dataset_config_sha256": profile["data"]["train_config_sha256"],
        "schedule": "rank_shards_alternating_workers_indexed_prefix_v1",
        "implementation_sha256": {
            str(path.resolve().relative_to(WORKSPACE_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
    }


def torchrun_command(profile_path, run_dir, resume=None, stop=None, smoke=False, port=29500):
    command = [
        str(DEFAULT_ENV / "bin/torchrun"), "--nnodes=1", "--nproc-per-node=4",
        "--master-addr=127.0.0.1", f"--master-port={port}", TRAINER,
        "--profile", str(Path(profile_path).resolve()), "--run-dir", str(run_dir),
    ]
    if resume:
        command += ["--resume-from", str(resume)]
    if stop:
        command += ["--stop-after", str(stop)]
    if smoke:
        command.append("--smoke")
    return command


def verify_gate(continuous, prefix, resumed):
    """Compare every saved tensor; unused final UND adapters may remain zero."""
    import torch
    from safetensors.torch import load_file
    from verify_datamake_online_rollout_resume import comparison, load_optimizer
    sys.path.insert(0, str(LANCE_ROOT))
    from train.datamake_branch_lora import is_generation_target, is_understanding_target
    # Predeclared tolerances; exact counts are also reported.
    atol, rtol = 1e-7, 1e-5
    c = continuous / "checkpoints/0000003"
    p = prefix / "checkpoints/0000002"
    r = resumed / "checkpoints/0000003"
    for path in (c, p, r):
        if not (path / "checkpoint_complete.json").is_file():
            raise ValueError(f"Missing complete checkpoint: {path}")
    result = {"atol": atol, "rtol": rtol}
    result["adapter"] = comparison(load_file(str(c / "adapter.safetensors")), load_file(str(r / "adapter.safetensors")), atol, rtol)
    adapter = load_file(str(p / "adapter.safetensors"))
    config = json.loads((p / "datamake_lora_config.json").read_text())
    gen = {k: v for k, v in adapter.items() if k.endswith(".lora_B") and is_generation_target(k[:-7])}
    und = {k: v for k, v in adapter.items() if k.endswith(".lora_B") and is_understanding_target(k[:-7])}
    result["nonzero"] = {
        "gen_total": len(gen), "gen_nonzero": sum(bool(v.count_nonzero()) for v in gen.values()),
        "und_total": len(und), "und_nonzero": sum(bool(v.count_nonzero()) for v in und.values()),
    }
    if len(adapter) != 2 * config["expected_target_modules"] or len(gen) != 256 or result["nonzero"]["gen_nonzero"] != 256:
        raise RuntimeError(f"Nonzero GEN adapter gate failed: {result['nonzero']}")
    if config["target_scope"] == "both_branches" and (len(und) != 252 or not result["nonzero"]["und_nonzero"]):
        raise RuntimeError("Understanding adapters received no updates")
    del adapter, gen, und
    for name in ("scheduler.pt", *[f"rng.rank-{rank:05d}-of-00004.pt" for rank in range(4)]):
        result[name] = comparison(torch.load(c / name, weights_only=False, map_location="cpu"),
                                  torch.load(r / name, weights_only=False, map_location="cpu"), atol, rtol)
    result["cursor"] = comparison(json.loads((c / "trainer_state.json").read_text()),
                                  json.loads((r / "trainer_state.json").read_text()), atol, rtol)
    # Keep DCP consolidation on the project's network storage, not /local.
    with tempfile.TemporaryDirectory(prefix="compare-", dir=continuous.parent) as temporary:
        left = load_optimizer(c, Path(temporary) / "continuous.pt")
        right = load_optimizer(r, Path(temporary) / "resumed.pt")
        result["optimizer"] = comparison(left, right, atol, rtol)
    for rank in range(4):
        a = json.loads((continuous / f"trace.rank-{rank}.jsonl").read_text().splitlines()[-1])
        b = json.loads((resumed / f"trace.rank-{rank}.jsonl").read_text().splitlines()[-1])
        # Scalar comparison helper is exact; encode loss as a tensor for tolerance.
        a["loss"], b["loss"] = torch.tensor(a["loss"]), torch.tensor(b["loss"])
        result[f"trace_rank_{rank}"] = comparison(a, b, atol, rtol)
    result["status"] = "passed" if all(v["within_tolerance"] for v in result.values()
                                      if isinstance(v, dict) and "within_tolerance" in v) else "failed"
    if result["status"] != "passed":
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--resume-from", default="none", help="none, latest, or checkpoint directory")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()
    profile = load_profile(args.profile)
    run = workspace_path(profile["run"]["output_root"]) / profile["run"]["run_name"]
    for key in ("train_config", "validation_config", "test_config", "train_sampling_manifest", "split_manifest"):
        path = workspace_path(profile["data"][key])
        if hashlib.sha256(path.read_bytes()).hexdigest() != profile["data"][key + "_sha256"]:
            raise ValueError(f"Data input differs: {path}")
    if not (workspace_path(profile["model"]["model_path"]) / "model.safetensors").is_file():
        raise FileNotFoundError("Official Lance base is missing")
    checkpoints = sorted((run / "checkpoints").glob("[0-9]*/checkpoint_complete.json"))
    resume = None
    if args.resume_from == "latest":
        if not checkpoints:
            raise FileNotFoundError("No complete checkpoint to resume")
        resume = checkpoints[-1].parent
    elif args.resume_from != "none":
        resume = Path(args.resume_from).resolve()
    elif checkpoints:
        raise ValueError("This run already has checkpoints; use --resume-from latest")
    contract = make_contract(profile, args.profile)
    gate_key = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    gate_file = run / "startup_validation" / f"passed-{gate_key}.json"
    port = 20000 + int(os.environ.get("SLURM_JOB_ID", os.getpid())) % 20000
    command = torchrun_command(args.profile, run, resume=resume, port=port)
    if args.dry_run:
        print(json.dumps({"run_dir": str(run), "command": command,
                          "startup_gate_required": not gate_file.is_file(), "contract": contract}, indent=2))
        return 0
    if os.environ.get("SLURM_JOB_PARTITION") != "testqueue":
        raise RuntimeError("Launch using the testqueue Slurm script")
    env = build_environment(profile)
    if not gate_file.is_file():
        parent = run / "startup_validation" / f"job-{os.environ['SLURM_JOB_ID']}"
        continuous, prefix, resumed = [parent / name for name in ("continuous", "prefix", "resumed")]
        for directory, stop, source in ((continuous, 3, None), (prefix, 2, None), (resumed, 3, prefix / "checkpoints/0000002")):
            print(f"[startup gate] {directory.name}: stop at {stop}, resume={source}", flush=True)
            subprocess.run(torchrun_command(args.profile, directory, source, stop, True, port),
                           cwd=LANCE_ROOT, env={**env, "WANDB_MODE": "disabled"}, check=True)
        report = verify_gate(continuous, prefix, resumed)
        report["contract_sha256"] = gate_key
        gate_file.write_text(json.dumps(report, indent=2) + "\n")
        print(f"[startup gate] PASSED: {gate_file}", flush=True)
    if args.smoke_only:
        return 0
    print(f"[formal] run={run.name}, resume={resume or 'fresh official base'}", flush=True)
    subprocess.run(command, cwd=LANCE_ROOT, env=env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit("Archived implementation: restore the complete source snapshot to reproduce it; use current DDP entry points for new work.")
    raise SystemExit(main())
