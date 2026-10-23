#!/usr/bin/env python3
"""Whole-chain pred_x0 DDP; fixed global target batch and independent resume gate."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import run_datamake_ddp_training as control

TRAINER = "train/datamake_chain_pred_x0_ddp_train.py"
BASELINE = "10_research/model_experiments/lance/configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json"
HISTORY = {
    "record_level": "dialogue_chain",
    "mode": "online_pred_x0_chain",
    "vit_history": "detached_pred_x0_decoded_video",
    "direct_vae_source": "detached_pred_x0_decoded_video_except_initial_source",
    "target": "dataset_ground_truth",
    "online_rollout": True,
    "one_step_x0_history": True,
    "detach_generated_history": True,
    "rollout_policy": "reuse_current_training_forward_within_whole_chain",
    "history_decode_grad_enabled": False,
    "cross_round_backpropagation": False,
    "noise_policy": "current_supervised_flow_forward",
}
SCHEDULE = {
    "version": "whole_chain_fixed_target_window_v1",
    "global_targets_per_update": 32,
    "whole_chain_within_update": True,
    "terminal_repeats": "separate_training_forwards_shared_history",
    "extra_round_loss_weights": [1, 1, 1, 1, 1],
    "loss_normalization": "global_window_target_token_mean",
    "cursor_unit": "optimizer_window",
}
_load_control, _make_control = control.load_profile, control.make_contract


def load_profile(path):
    profile = _load_control(path)
    baseline = _load_control(control.workspace_path(BASELINE))
    if profile["history"] != HISTORY or profile.get("chain_schedule") != SCHEDULE:
        raise ValueError("Unexpected chain history, weighting or window policy")
    candidate = deepcopy(profile)
    candidate["history"] = baseline["history"]
    candidate["run"]["data_seed_selection"] = baseline["run"]["data_seed_selection"]
    if control.semantic_recipe(candidate) != control.semantic_recipe(baseline):
        raise ValueError("Whole-chain variant must retain the control data/model/optimizer recipe")
    for key in ("checkpoint", "distributed"):
        if profile[key] != baseline[key]:
            raise ValueError(f"Control settings changed: {key}")
    if {k: v for k, v in profile["ddp"].items() if k != "source_profile"} != {
        k: v for k, v in baseline["ddp"].items() if k != "source_profile"
    }:
        raise ValueError("Control DDP performance settings changed")
    if profile["run"]["global_batch_size"] != 32 or profile["distributed"]["gpus_per_node"] != 8:
        raise ValueError("This experiment requires eight ranks and 32 target exposures")
    if profile["run"]["run_name"] == baseline["run"]["run_name"] or profile["wandb"]["run_id"] == baseline["wandb"]["run_id"]:
        raise ValueError("Use a separate chain experiment identity")
    return profile


def make_contract(profile):
    contract = _make_control(profile)
    files = [Path(__file__), control.LANCE_ROOT / TRAINER,
             control.LANCE_ROOT / "train/datamake_chain_window_schedule.py",
             control.LANCE_ROOT / "train/datamake_chain_window_data.py",
             control.LANCE_ROOT / "train/datamake_flow_history.py",
             control.LANCE_ROOT / "data/datasets_factory/datamake_online_rollout_turn.py"]
    contract["implementation_sha256"].update({
        str(p.resolve().relative_to(control.WORKSPACE_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    sys.path.insert(0, str(control.LANCE_ROOT))
    from train.datamake_chain_window_schedule import read_chains, make_windows, schedule_digest
    chains = read_chains(profile)
    windows = make_windows(chains, profile["run"]["total_steps"], profile["run"]["data_seed"])
    contract["chain_schedule"] = {**SCHEDULE, "schedule_sha256": schedule_digest(chains, windows)}
    return contract


def main():
    control.TRAINER = TRAINER
    control.load_profile, control.make_contract = load_profile, make_contract
    return control.main()


if __name__ == "__main__":
    raise SystemExit(main())
