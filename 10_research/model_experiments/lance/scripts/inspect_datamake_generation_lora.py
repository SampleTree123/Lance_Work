#!/usr/bin/env python3
"""Audit generation-only LoRA targets from a Lance safetensors checkpoint."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from safetensors import safe_open


GENERATION_EXPERT_SUFFIXES = (
    "self_attn.q_proj_moe_gen",
    "self_attn.k_proj_moe_gen",
    "self_attn.v_proj_moe_gen",
    "self_attn.o_proj_moe_gen",
    "mlp_moe_gen.gate_proj",
    "mlp_moe_gen.up_proj",
    "mlp_moe_gen.down_proj",
)
GENERATION_IO_NAMES = (
    "time_embedder.mlp.0",
    "time_embedder.mlp.2",
    "vae2llm",
    "llm2vae",
)


def is_target(name: str, include_io: bool) -> bool:
    if any(name.endswith(suffix) for suffix in GENERATION_EXPERT_SUFFIXES):
        return True
    return include_io and name in GENERATION_IO_NAMES


def inspect(checkpoint: Path, rank: int, include_io: bool) -> dict:
    model_path = checkpoint / "model.safetensors"
    if not model_path.is_file():
        raise FileNotFoundError(model_path)
    targets = []
    base_parameter_count = 0
    with safe_open(model_path, framework="pt", device="cpu") as stream:
        for key in stream.keys():
            shape = list(stream.get_slice(key).get_shape())
            base_parameter_count += math.prod(shape)
            if not key.endswith(".weight"):
                continue
            name = key[: -len(".weight")]
            if not is_target(name, include_io):
                continue
            if len(shape) != 2:
                raise ValueError(f"LoRA target is not a matrix: {key} {shape}")
            out_features, in_features = shape
            targets.append(
                {
                    "name": name,
                    "in_features": in_features,
                    "out_features": out_features,
                    "lora_parameters": rank * (in_features + out_features),
                }
            )
    targets.sort(key=lambda item: item["name"])
    trainable_parameter_count = sum(item["lora_parameters"] for item in targets)
    return {
        "schema_version": "datamake_lance_lora_target_audit_v1",
        "checkpoint": str(checkpoint.resolve()),
        "rank": rank,
        "target_scope": (
            "generation_experts_and_io" if include_io else "generation_experts"
        ),
        "target_module_count": len(targets),
        "base_checkpoint_parameter_count": base_parameter_count,
        "trainable_parameter_count": trainable_parameter_count,
        "trainable_to_base_ratio": trainable_parameter_count
        / base_parameter_count,
        "bf16_adapter_bytes": 2 * trainable_parameter_count,
        "targets": targets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--rank", type=int, default=64)
    parser.add_argument("--generation-experts-only", action="store_true")
    parser.add_argument("--expected-target-modules", type=int, default=256)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.rank < 1:
        raise ValueError("rank must be positive")
    result = inspect(
        args.checkpoint.resolve(), args.rank, not args.generation_experts_only
    )
    if result["target_module_count"] != args.expected_target_modules:
        raise ValueError(
            "target count changed: "
            f"expected {args.expected_target_modules}, "
            f"found {result['target_module_count']}"
        )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
