#!/usr/bin/env python3
"""One-time, lossless Stage6 v5 adapter/Adam -> PEFT/DDP v6 conversion."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

from run_datamake_ddp_training import PEFT_ROOT, LANCE_ROOT, load_profile, make_contract, semantic_recipe, workspace_path
sys.path[:0] = [str(PEFT_ROOT), str(LANCE_ROOT)]


def convert_optimizer(source, adapters):
    """Map canonical FQNs to ordinary PyTorch optimizer IDs; retain all moments."""
    import torch
    states, names, groups = {}, {}, []
    if len(source["param_groups"]) != 1:
        raise ValueError("Stage6 converter expects one Adam group")
    for old_group in source["param_groups"]:
        indexes = []
        for old_name in old_group["params"]:
            new_name = old_name + ".weight"
            if new_name not in adapters:
                raise ValueError(f"Unexpected optimizer parameter: {old_name}")
            index = len(names)
            names[index] = new_name
            indexes.append(index)
            state = dict(source["state"][old_name])
            live = state.pop("_datamake_parameter_value")
            if not torch.equal(live, adapters[new_name]):
                raise ValueError(f"Adapter differs from live optimizer value: {old_name}")
            if set(state) != {"step", "exp_avg", "exp_avg_sq"}:
                raise ValueError(f"Unknown Adam fields: {set(state)}")
            for key in ("exp_avg", "exp_avg_sq"):
                if state[key].shape != live.shape or not torch.isfinite(state[key]).all():
                    raise ValueError(f"Invalid {key}: {old_name}")
            states[index] = state
        groups.append({**old_group, "params": indexes})
    if set(names.values()) != set(adapters):
        raise ValueError("Optimizer does not cover every adapter")
    return {"state_dict": {"state": states, "param_groups": groups}, "parameter_names": names}


def convert(source, destination, profile):
    import torch
    from safetensors.torch import load_file, save_file
    from torch.distributed.checkpoint.format_utils import dcp_to_torch_save
    from train.datamake_lora_checkpoint import validate_lora_checkpoint
    from train.datamake_branch_lora import BranchLoRAConfig
    from train.datamake_peft import metadata, require_peft
    from train.datamake_ddp_checkpoint import finalize, sha256, validate, write_json
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    legacy = validate_lora_checkpoint(source, 4)
    source_profile = json.loads((source.parent.parent / "configs/profile.json").read_text())
    if semantic_recipe(source_profile) != semantic_recipe(profile):
        raise ValueError("Cannot migrate across changed training recipes")
    old_contract = json.loads((source / "datamake_online_training_contract.json").read_text())
    reference_path = workspace_path(profile["ddp"]["source_profile"])
    if (source_profile != json.loads(reference_path.read_text()) or
            sha256(reference_path) != old_contract["profile_sha256"]):
        raise ValueError("Source profile differs from saved training contract")
    contract = make_contract(profile)
    for key in ("base_model", "base_model_sha256", "dataset_config", "dataset_config_sha256"):
        if old_contract[key] != contract[key]:
            raise ValueError(f"Source/target contract differs: {key}")
    config = BranchLoRAConfig.from_dict(json.loads((source / "datamake_lora_config.json").read_text()))
    state = json.loads((source / "trainer_state.json").read_text())
    completed = legacy["completed_steps"]
    if state["next_microstep"] != completed * profile["run"]["gradient_accumulation_steps"]:
        raise ValueError("Source cursor does not match completed updates")
    adapters = {name + ".weight": value for name, value in load_file(str(source / "adapter.safetensors")).items()}
    if any(not torch.isfinite(v).all() for v in adapters.values()):
        raise ValueError("Nonfinite adapter")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".peft-convert-", dir=destination.parent) as temporary:
        temporary = Path(temporary)
        full = temporary / "consolidated.pt"
        dcp_to_torch_save(source / "optimizer", full)
        payload = torch.load(full, weights_only=False, map_location="cpu")["optimizer"]
        converted = convert_optimizer(payload, adapters)
        full.unlink()
        staging = temporary / "checkpoint"
        staging.mkdir()
        save_file(adapters, str(staging / "adapter.safetensors"))
        torch.save(converted, staging / "optimizer.pt")
        targets = sorted({n.rsplit(".lora_", 1)[0] for n in adapters})
        require_peft().LoraConfig(r=config.rank, lora_alpha=config.alpha, lora_dropout=config.dropout,
                                  bias="none", target_modules=targets).save_pretrained(staging)
        write_json(staging / "datamake_lora_config.json", metadata(config))
        for name in ("scheduler.pt", *[f"rng.rank-{r:05d}-of-00004.pt" for r in range(4)]):
            shutil.copyfile(source / name, staging / name)
        write_json(staging / "migration.json", {
            "source": str(source), "source_complete_sha256": sha256(source / "checkpoint_complete.json"),
            "source_adapter_sha256": sha256(source / "adapter.safetensors"), "completed_steps": completed,
            "adapter_tensors_exact": len(adapters), "optimizer_states_exact": len(converted["state_dict"]["state"]),
            "status": "converted_not_gpu_validated", "resume_kind": "full_state_backend_migration",
        })
        # A dedicated destination parent is required: conversion never retires old files.
        finalize(staging, destination, completed, 4, contract, state["next_microstep"], keep_last=10**9)
    validate(destination, contract, 4)
    print(json.dumps({"status": "converted_not_gpu_validated", "destination": str(destination), "completed_steps": completed}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    convert(args.source, args.destination, load_profile(args.profile))


if __name__ == "__main__":
    main()
