#!/usr/bin/env python3
"""Summarize Lance DataMake optimization metrics from a launcher log."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import mean, median
from typing import Dict, List


METRIC_RE = re.compile(
    r"step=(?P<step>\d+)\).*?Train Loss mse: (?P<mse>[0-9.eE+-]+).*?"
    r"Train Loss ce: (?P<ce>[0-9.eE+-]+).*?lr=(?P<lr>[0-9.eE+-]+)"
)
ERROR_PATTERNS = (
    "[TRAINING EXCEPTION]",
    "Non-finite loss",
    "bad data at step",
    "CUDA out of memory",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_metrics(text: str) -> List[Dict[str, float | int]]:
    # tqdm can render the final step more than once. Keep the last occurrence.
    by_step: Dict[int, Dict[str, float | int]] = {}
    for match in METRIC_RE.finditer(text):
        step = int(match.group("step"))
        by_step[step] = {
            "step": step,
            "mse": float(match.group("mse")),
            "ce": float(match.group("ce")),
            "lr": float(match.group("lr")),
        }
    return [by_step[step] for step in sorted(by_step)]


def linear_slope(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2
    y_mean = mean(values)
    numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    return numerator / denominator


def trimmed_mean(values: List[float], fraction: float = 0.1) -> float:
    if not values:
        raise ValueError("cannot compute a trimmed mean of an empty list")
    trim = int(len(values) * fraction)
    ordered = sorted(values)
    if trim == 0:
        return mean(ordered)
    return mean(ordered[trim:-trim])


def summarize(log_path: Path, expected_steps: int | None, window: int) -> Dict[str, object]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    metrics = parse_metrics(text)
    if not metrics:
        raise ValueError(f"no Lance training metrics found in {log_path}")
    if window < 1:
        raise ValueError("--window must be >= 1")
    values = [float(item["mse"]) for item in metrics]
    actual_window = min(window, len(values))
    first_mean = mean(values[:actual_window])
    last_mean = mean(values[-actual_window:])
    first_median = median(values[:actual_window])
    last_median = median(values[-actual_window:])
    first_trimmed = trimmed_mean(values[:actual_window])
    last_trimmed = trimmed_mean(values[-actual_window:])
    relative_change = (last_mean - first_mean) / first_mean if first_mean else math.nan
    errors = {pattern: text.count(pattern) for pattern in ERROR_PATTERNS}
    completed_steps = len(metrics)
    expected_ok = expected_steps is None or completed_steps == expected_steps
    contiguous = [int(item["step"]) for item in metrics] == list(
        range(int(metrics[0]["step"]), int(metrics[-1]["step"]) + 1)
    )
    normal_done = "Done!" in text
    passed_integrity = expected_ok and contiguous and normal_done and not any(errors.values())
    return {
        "schema_version": "datamake_lance_training_log_report_v1",
        "log": str(log_path.resolve()),
        "log_sha256": sha256_file(log_path),
        "expected_steps": expected_steps,
        "completed_metric_steps": completed_steps,
        "first_step": int(metrics[0]["step"]),
        "last_step": int(metrics[-1]["step"]),
        "steps_contiguous": contiguous,
        "normal_done": normal_done,
        "error_counts": errors,
        "integrity_passed": passed_integrity,
        "mse": {
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
            "median": median(values),
            "linear_slope_per_step": linear_slope(values),
            "window_size": actual_window,
            "first_window_mean": first_mean,
            "last_window_mean": last_mean,
            "last_vs_first_relative_change": relative_change,
            "first_window_median": first_median,
            "last_window_median": last_median,
            "last_vs_first_median_relative_change": (
                (last_median - first_median) / first_median
                if first_median
                else math.nan
            ),
            "trim_fraction": 0.1,
            "first_window_trimmed_mean": first_trimmed,
            "last_window_trimmed_mean": last_trimmed,
            "last_vs_first_trimmed_mean_relative_change": (
                (last_trimmed - first_trimmed) / first_trimmed
                if first_trimmed
                else math.nan
            ),
        },
        "metrics": metrics,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--expected-steps", type=int)
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = summarize(args.log.resolve(), args.expected_steps, args.window)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["integrity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
