#!/usr/bin/env python3
"""Compare continuous and save/resume DataMake LoRA smoke checkpoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from safetensors.torch import load_file
import torch
from torch.distributed.checkpoint.format_utils import dcp_to_torch_save


def compare_values(
    left: Any,
    right: Any,
    path: str,
    report: dict[str, Any],
    atol: float,
    rtol: float,
) -> None:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        report["tensor_count"] += 1
        if left.shape != right.shape or left.dtype != right.dtype:
            report["mismatches"].append(
                f"{path}: {tuple(left.shape)}/{left.dtype} != "
                f"{tuple(right.shape)}/{right.dtype}"
            )
            return
        if left.numel():
            difference = (left.float() - right.float()).abs().max().item()
            report["max_abs_difference"] = max(
                report["max_abs_difference"], float(difference)
            )
        if torch.equal(left, right):
            report["exact_tensor_count"] += 1
        elif not torch.allclose(left, right, atol=atol, rtol=rtol):
            report["mismatches"].append(f"{path}: tensor differs beyond tolerance")
        return
    if isinstance(left, np.ndarray) and isinstance(right, np.ndarray):
        if not np.array_equal(left, right):
            report["mismatches"].append(f"{path}: numpy array differs")
        return
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            report["mismatches"].append(f"{path}: mapping keys differ")
            return
        for key in sorted(left, key=str):
            compare_values(left[key], right[key], f"{path}.{key}", report, atol, rtol)
        return
    if isinstance(left, (list, tuple)) and isinstance(right, type(left)):
        if len(left) != len(right):
            report["mismatches"].append(f"{path}: sequence lengths differ")
            return
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            compare_values(
                left_item,
                right_item,
                f"{path}[{index}]",
                report,
                atol,
                rtol,
            )
        return
    if left != right:
        report["mismatches"].append(f"{path}: {left!r} != {right!r}")


def comparison(left: Any, right: Any, atol: float, rtol: float) -> dict[str, Any]:
    report: dict[str, Any] = {
        "tensor_count": 0,
        "exact_tensor_count": 0,
        "max_abs_difference": 0.0,
        "mismatches": [],
    }
    compare_values(left, right, "root", report, atol, rtol)
    report["within_tolerance"] = not report["mismatches"]
    return report


def load_optimizer(checkpoint: Path, destination: Path) -> Any:
    dcp_to_torch_save(checkpoint / "optimizer", destination)
    return torch.load(destination, map_location="cpu", weights_only=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuous", type=Path, required=True)
    parser.add_argument("--resumed", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--atol", type=float, default=1e-7)
    parser.add_argument("--rtol", type=float, default=1e-6)
    args = parser.parse_args()

    for checkpoint in (args.continuous, args.resumed, args.prefix):
        if not (checkpoint / "checkpoint_complete.json").is_file():
            raise FileNotFoundError(f"incomplete checkpoint: {checkpoint}")

    continuous_adapter = load_file(
        str(args.continuous / "adapter.safetensors"), device="cpu"
    )
    resumed_adapter = load_file(
        str(args.resumed / "adapter.safetensors"), device="cpu"
    )
    prefix_adapter = load_file(
        str(args.prefix / "adapter.safetensors"), device="cpu"
    )
    lora_b_names = sorted(name for name in prefix_adapter if name.endswith("lora_B"))
    nonzero_lora_b = sum(
        int(torch.count_nonzero(prefix_adapter[name]).item() > 0)
        for name in lora_b_names
    )

    result: dict[str, Any] = {
        "schema_version": "datamake_lora_resume_smoke_audit_v1",
        "continuous": str(args.continuous.resolve()),
        "resumed": str(args.resumed.resolve()),
        "prefix": str(args.prefix.resolve()),
        "tolerance": {"atol": args.atol, "rtol": args.rtol},
        "adapter": comparison(
            continuous_adapter, resumed_adapter, args.atol, args.rtol
        ),
        "prefix_lora_B": {
            "tensor_count": len(lora_b_names),
            "nonzero_tensor_count": nonzero_lora_b,
        },
    }
    del continuous_adapter, resumed_adapter, prefix_adapter

    continuous_scheduler = torch.load(
        args.continuous / "scheduler.pt", map_location="cpu", weights_only=True
    )
    resumed_scheduler = torch.load(
        args.resumed / "scheduler.pt", map_location="cpu", weights_only=True
    )
    result["scheduler"] = comparison(
        continuous_scheduler, resumed_scheduler, args.atol, args.rtol
    )

    continuous_trainer = json.loads(
        (args.continuous / "trainer_state.json").read_text(encoding="utf-8")
    )
    resumed_trainer = json.loads(
        (args.resumed / "trainer_state.json").read_text(encoding="utf-8")
    )
    result["trainer_state"] = comparison(
        continuous_trainer, resumed_trainer, args.atol, args.rtol
    )

    continuous_rng = {
        path.name: torch.load(path, map_location="cpu", weights_only=False)
        for path in sorted(args.continuous.glob("rng.rank-*.pt"))
    }
    resumed_rng = {
        path.name: torch.load(path, map_location="cpu", weights_only=False)
        for path in sorted(args.resumed.glob("rng.rank-*.pt"))
    }
    result["rng"] = comparison(continuous_rng, resumed_rng, args.atol, args.rtol)

    with tempfile.TemporaryDirectory(prefix="datamake-resume-audit-") as temp_dir:
        temporary = Path(temp_dir)
        continuous_optimizer = load_optimizer(
            args.continuous, temporary / "continuous.pt"
        )
        resumed_optimizer = load_optimizer(args.resumed, temporary / "resumed.pt")
        result["optimizer"] = comparison(
            continuous_optimizer, resumed_optimizer, args.atol, args.rtol
        )

    passed = (
        result["adapter"]["within_tolerance"]
        and result["optimizer"]["within_tolerance"]
        and result["scheduler"]["within_tolerance"]
        and result["trainer_state"]["within_tolerance"]
        and result["rng"]["within_tolerance"]
        and len(lora_b_names) == 256
        and nonzero_lora_b == 256
    )
    result["status"] = "passed" if passed else "failed"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
