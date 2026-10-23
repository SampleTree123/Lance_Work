#!/usr/bin/env python3
"""Detached pred_x0 history variant of the frozen mixed-prefix DDP launcher."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import run_datamake_ddp_training as control

CONTROL_PROFILE = "10_research/model_experiments/lance/configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json"
TRAINER = "train/datamake_pred_x0_ddp_train.py"
HISTORY = {
    "record_level": "dialogue_prefix",
    "mode": "online_pred_x0",
    "vit_history": "detached_pred_x0_decoded_video",
    "direct_vae_source": "detached_pred_x0_decoded_video_except_initial_source",
    "target": "dataset_ground_truth",
    "online_rollout": True,
    "one_step_x0_history": True,
    "detach_generated_history": True,
    "generation_grad_enabled": False,
    "rollout_policy": "regenerate_previous_rounds_for_each_selected_prefix",
    "noise_policy": "official_gt_noised_target_isolated_rng_v1",
}
_load_control = control.load_profile
_make_control_contract = control.make_contract


def load_profile(path):
    profile = _load_control(path)
    baseline = _load_control(control.workspace_path(CONTROL_PROFILE))
    if profile["history"] != HISTORY:
        raise ValueError("Expected detached online pred_x0 history policy")
    candidate = deepcopy(profile)
    candidate["history"] = baseline["history"]
    if control.semantic_recipe(candidate) != control.semantic_recipe(baseline):
        raise ValueError("Only history may differ from the eight-GPU control recipe")
    for key in ("checkpoint", "distributed"):
        if candidate[key] != baseline[key]:
            raise ValueError(f"Control configuration changed: {key}")
    if {k: v for k, v in candidate["ddp"].items() if k != "source_profile"} != {
        k: v for k, v in baseline["ddp"].items() if k != "source_profile"
    }:
        raise ValueError("Control DDP optimization settings changed")
    if (profile["run"]["run_name"] == baseline["run"]["run_name"] or
            profile["wandb"]["run_id"] == baseline["wandb"]["run_id"]):
        raise ValueError("History variant requires an independent run identity")
    if profile["preparation"]["training_entry"] != str(Path(CONTROL_PROFILE).parents[1] / "lance" / TRAINER):
        raise ValueError("Incorrect pred_x0 training entry")
    return profile


def make_contract(profile):
    contract = _make_control_contract(profile)
    extra = [Path(__file__), control.LANCE_ROOT / TRAINER,
             control.LANCE_ROOT / "train/datamake_pred_x0_prefix.py",
             control.LANCE_ROOT / "train/datamake_flow_history.py",
             control.LANCE_ROOT / "data/datasets_factory/datamake_online_rollout_turn.py"]
    contract["implementation_sha256"].update({
        str(p.resolve().relative_to(control.WORKSPACE_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in extra
    })
    return contract


def main():
    # Process-local extension: keep the control's source hashes and resume contract intact.
    control.TRAINER = TRAINER
    control.load_profile = load_profile
    control.make_contract = make_contract
    return control.main()


if __name__ == "__main__":
    raise SystemExit(main())
