#!/usr/bin/env python3
"""Run the frozen stage-2 recipe as a one-H200, no-checkpoint smoke."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

import run_datamake_formal_training as formal


DEFAULT_PROFILE = (
    formal.WORKSPACE_ROOT
    / "10_research/model_experiments/lance/configs/"
    "datamake_dialogue_stage2_r5x3_region_v1.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--smoke-steps", type=int, default=2)
    parser.add_argument("--master-port", type=int, default=30417)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def make_local_smoke_profile(
    profile: dict, smoke_steps: int, allocation_id: str
) -> dict:
    smoke = formal.make_smoke_profile(profile, smoke_steps, allocation_id)
    smoke["run"]["run_name"] = (
        f"{profile['run']['run_name']}_local1xh200_smoke{smoke_steps}_job"
        f"{allocation_id}"
    )
    smoke["run"]["global_batch_size"] = 1
    smoke["distributed"]["gpus_per_node"] = 1
    smoke["distributed"]["num_replicate"] = 1
    smoke["distributed"]["num_shard"] = 1
    smoke["_data_allocation"]["world_size"] = 1
    return smoke


def main() -> int:
    args = parse_args()
    profile = formal.validate_profile(args.profile)
    allocation_id = os.environ.get("SLURM_JOB_ID", "manual")
    smoke = make_local_smoke_profile(profile, args.smoke_steps, allocation_id)
    command = formal.build_torchrun_command(
        smoke,
        resume_from=None,
        master_port=args.master_port,
    )
    summary = {
        "schema_version": "datamake_lance_local_smoke_segment_v1",
        "profile": smoke["_profile_path"],
        "profile_sha256": smoke["_profile_sha256"],
        "allocation_id": allocation_id,
        "host": os.uname().nodename,
        "run_name": smoke["run"]["run_name"],
        "smoke_steps": args.smoke_steps,
        "world_size": 1,
        "checkpoint_interval": 0,
        "save_final_checkpoint": False,
        "wandb_mode": "offline",
        "command": command,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        return 0

    import torch

    formal.require_equal(torch.cuda.device_count(), 1, "visible CUDA device count")
    run_dir = formal.workspace_path(smoke["run"]["output_root"]) / smoke["run"][
        "run_name"
    ]
    manifest_path = run_dir / "segments" / f"local_job_{allocation_id}" / "launch_manifest.json"
    formal.write_json(manifest_path, summary)

    environment = formal.build_environment(smoke)
    result = subprocess.run(
        command,
        cwd=formal.LANCE_ROOT,
        env=environment,
        check=False,
    )
    print(
        json.dumps(
            {
                "event": "local_smoke_finished",
                "returncode": result.returncode,
                "run_dir": str(run_dir),
            }
        ),
        flush=True,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit("Archived implementation: restore the complete source snapshot to reproduce it; use current DDP entry points for new work.")
    raise SystemExit(main())
