#!/usr/bin/env python3
"""Summarize measured updates; require equal sample schedules for comparisons."""
import argparse
import json
from pathlib import Path
import statistics


def summarize(path, warmup=1):
    path = Path(path)
    rows = [json.loads(line) for line in (path / "metrics.jsonl").read_text().splitlines() if line.strip()]
    # A benchmark directory is a single segment; duplicate steps are an error.
    if len({r["optimizer_step"] for r in rows}) != len(rows):
        raise ValueError("Benchmark includes duplicate/resumed steps; use a single segment")
    measured = rows[warmup:]
    if len(measured) < 2:
        raise ValueError("Need at least two measured updates after warmup")
    times = [r["perf/step_time"] for r in measured]
    samples = {p.name: [json.loads(line)["sample_ids"] for line in p.read_text().splitlines()][warmup:]
               for p in sorted(path.glob("trace.rank-*.jsonl"))}
    result = {"run": str(path.resolve()), "diagnostic_only": measured[0].get("diagnostic_only", False),
              "actual_world_size": measured[0].get("actual_world_size", 4), "measured_updates": len(measured),
              "mean_update_seconds": statistics.mean(times), "median_update_seconds": statistics.median(times),
              "min_update_seconds": min(times), "max_update_seconds": max(times),
              "peak_allocated_gib": max(r["perf/peak_allocated_gib"] for r in measured),
              "peak_reserved_gib": max(r["perf/peak_reserved_gib"] for r in measured),
              "phases_seconds": {}, "sample_schedule": samples}
    for key in ("data_wait_seconds", "vae_region_seconds", "model_forward_seconds", "backward_sync_seconds", "vit_seconds"):
        if all("perf/"+key in r for r in measured):
            result["phases_seconds"][key] = statistics.mean(r["perf/"+key] for r in measured)
    # ViT is part of model_forward; maxima across ranks need not be additive.
    result["timing_scope"] = "step includes data wait; excludes logging/checkpoint save; ViT is included in model_forward; profiler capture can perturb timings"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, help="LABEL=RUN_DIRECTORY; first is baseline")
    parser.add_argument("--warmup-updates", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.warmup_updates < 0:
        raise ValueError("Negative warmup")
    result = {}
    for item in args.run:
        name, path = item.split("=", 1)
        result[name] = summarize(path, args.warmup_updates)
    first = next(iter(result.values()))
    for value in result.values():
        equal = bool(first["sample_schedule"]) and value["sample_schedule"] == first["sample_schedule"] and value["actual_world_size"] == first["actual_world_size"]
        value["same_measured_samples"] = equal
        value["speedup_vs_first"] = first["mean_update_seconds"] / value["mean_update_seconds"] if equal else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: {n: v for n, v in value.items() if n != "sample_schedule"} for k, value in result.items()}, indent=2))


if __name__ == "__main__":
    main()
