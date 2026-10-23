#!/usr/bin/env python3
"""Prepare an isolated activation-checkpointing variant; does not launch jobs."""
import argparse
import json
from pathlib import Path
from run_datamake_ddp_training import load_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--activation-checkpointing", choices=("all", "alternate", "none"), required=True)
    parser.add_argument("--checkpoint-disabled-layers", type=int, nargs="*", default=None)
    parser.add_argument("--per-rank-batch-size", type=int, choices=(1, 2, 4, 8), default=None)
    parser.add_argument("--vae-cache-policy", choices=("release", "retain"), default=None)
    parser.add_argument("--attention-padding", choices=("fixed", "minimal"), default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    profile = load_profile(args.profile)
    mode = args.activation_checkpointing
    profile["ddp"]["activation_checkpointing"] = mode
    if args.checkpoint_disabled_layers is not None:
        profile["ddp"]["checkpoint_disabled_layers"] = args.checkpoint_disabled_layers
    if args.per_rank_batch_size is not None:
        profile["run"]["per_rank_batch_size"] = args.per_rank_batch_size
        profile["run"]["gradient_accumulation_steps"] = 8 // args.per_rank_batch_size
    if args.vae_cache_policy is not None:
        profile["ddp"]["vae_cache_policy"] = args.vae_cache_policy
    if args.attention_padding is not None:
        profile["ddp"]["attention_padding"] = args.attention_padding
    suffix = f"_ac_{mode}_b{profile['run']['per_rank_batch_size']}"
    disabled = profile["ddp"].get("checkpoint_disabled_layers", [])
    if disabled:
        suffix += "_off_" + "_".join(str(i) for i in disabled)
    if "vae_cache_policy" in profile["ddp"]:
        suffix += "_vae_cache_" + profile["ddp"]["vae_cache_policy"]
    if "attention_padding" in profile["ddp"]:
        suffix += "_pad_" + profile["ddp"]["attention_padding"]
    profile["profile_id"] += suffix
    profile["run"]["run_name"] += suffix
    profile["wandb"]["run_id"] += suffix.replace("_", "-")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, indent=2) + "\n")
    load_profile(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
