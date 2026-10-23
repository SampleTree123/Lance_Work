#!/usr/bin/env python3
"""Compare two accepted First Batch node videos at decoded-frame level."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys


DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 180
DEFAULT_MAX_MEAN_FRAME_MAD = 1.5
DEFAULT_MAX_P95_FRAME_MAD = 2.0
DEFAULT_MAX_SINGLE_FRAME_MAD = 3.0
DEFAULT_PIXEL_DELTA = 5
DEFAULT_MAX_CHANGED_PIXEL_FRACTION = 0.01


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to read JSON: {path}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_exact(stream, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def frame_difference(left: bytes, right: bytes, pixel_delta: int) -> tuple[float, int, int]:
    if len(left) != len(right) or not left:
        raise RuntimeError("Decoded frames have incompatible sizes")
    difference_sum = 0
    changed_pixels = 0
    maximum_delta = 0
    for left_value, right_value in zip(left, right):
        delta = abs(left_value - right_value)
        difference_sum += delta
        changed_pixels += delta > pixel_delta
        maximum_delta = max(maximum_delta, delta)
    return difference_sum / len(left), changed_pixels, maximum_delta


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise RuntimeError("Cannot calculate a percentile without values")
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def compare_videos(
    ffmpeg: Path,
    baseline_video: Path,
    candidate_video: Path,
    *,
    expected_frames: int,
    width: int,
    height: int,
    pixel_delta: int,
) -> dict:
    frame_size = width * height

    def launch(video: Path) -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video),
                "-vf",
                f"scale={width}:{height},format=gray",
                "-f",
                "rawvideo",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    baseline = launch(baseline_video)
    candidate = launch(candidate_video)
    if baseline.stdout is None or candidate.stdout is None:
        raise RuntimeError("Unable to open ffmpeg decoder output")

    frame_mads = []
    changed_pixels = 0
    maximum_pixel_delta = 0
    try:
        for frame_index in range(expected_frames):
            left = read_exact(baseline.stdout, frame_size)
            right = read_exact(candidate.stdout, frame_size)
            if len(left) != frame_size or len(right) != frame_size:
                raise RuntimeError(
                    f"Video ended before frame {frame_index}: "
                    f"baseline={len(left)}, candidate={len(right)}"
                )
            mad, changed, maximum = frame_difference(left, right, pixel_delta)
            frame_mads.append(mad)
            changed_pixels += changed
            maximum_pixel_delta = max(maximum_pixel_delta, maximum)
        if baseline.stdout.read(1) or candidate.stdout.read(1):
            raise RuntimeError(
                f"Video contains more than the expected {expected_frames} frames"
            )
    finally:
        baseline_stdout, baseline_stderr = baseline.communicate()
        candidate_stdout, candidate_stderr = candidate.communicate()
        del baseline_stdout, candidate_stdout

    if baseline.returncode != 0 or candidate.returncode != 0:
        raise RuntimeError(
            "ffmpeg decode failed: "
            f"baseline={baseline.returncode} {baseline_stderr.decode(errors='replace')}; "
            f"candidate={candidate.returncode} {candidate_stderr.decode(errors='replace')}"
        )

    total_pixels = expected_frames * frame_size
    return {
        "decoded_frame_count": len(frame_mads),
        "comparison_resolution": [width, height],
        "mean_frame_mad": sum(frame_mads) / len(frame_mads),
        "p95_frame_mad": percentile(frame_mads, 0.95),
        "maximum_frame_mad": max(frame_mads),
        "maximum_frame_mad_index": frame_mads.index(max(frame_mads)),
        "first_frame_mad": frame_mads[0],
        "pixel_delta_threshold": pixel_delta,
        "changed_pixel_fraction": changed_pixels / total_pixels,
        "maximum_pixel_delta": maximum_pixel_delta,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run-root", type=Path, required=True)
    parser.add_argument("--candidate-run-root", type=Path, required=True)
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--ffmpeg-exe", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument(
        "--max-mean-frame-mad", type=float, default=DEFAULT_MAX_MEAN_FRAME_MAD
    )
    parser.add_argument(
        "--max-p95-frame-mad", type=float, default=DEFAULT_MAX_P95_FRAME_MAD
    )
    parser.add_argument(
        "--max-single-frame-mad", type=float, default=DEFAULT_MAX_SINGLE_FRAME_MAD
    )
    parser.add_argument("--pixel-delta", type=int, default=DEFAULT_PIXEL_DELTA)
    parser.add_argument(
        "--max-changed-pixel-fraction",
        type=float,
        default=DEFAULT_MAX_CHANGED_PIXEL_FRACTION,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline_root = args.baseline_run_root.resolve()
    candidate_root = args.candidate_run_root.resolve()
    relative_video = Path("media") / "nodes" / args.node_id / "video.mp4"
    relative_sidecar = relative_video.with_name("sidecar.json")
    baseline_video = baseline_root / relative_video
    candidate_video = candidate_root / relative_video
    baseline_sidecar = read_json(baseline_root / relative_sidecar)
    candidate_sidecar = read_json(candidate_root / relative_sidecar)
    baseline_profile = baseline_sidecar.get("runtime", {}).get("editor_profile")
    candidate_profile = candidate_sidecar.get("runtime", {}).get("editor_profile")
    baseline_media = baseline_sidecar.get("media", {})
    candidate_media = candidate_sidecar.get("media", {})

    ffmpeg = args.ffmpeg_exe
    if ffmpeg is None and os.environ.get("DM_FFMPEG_EXE"):
        ffmpeg = Path(os.environ["DM_FFMPEG_EXE"])
    if ffmpeg is None and isinstance(candidate_profile, dict):
        value = candidate_profile.get("ffmpeg_executable")
        ffmpeg = Path(value) if value else None
    if ffmpeg is None:
        raise RuntimeError("Pass --ffmpeg-exe or set DM_FFMPEG_EXE")
    ffmpeg = ffmpeg.resolve()
    if not ffmpeg.is_file() or not os.access(ffmpeg, os.X_OK):
        raise RuntimeError(f"ffmpeg is missing or not executable: {ffmpeg}")

    expected_frames = int(candidate_media.get("frames", 0))
    contract_checks = {
        "accepted_sidecars": baseline_sidecar.get("status") == "accepted"
        and candidate_sidecar.get("status") == "accepted",
        "same_node_id": baseline_sidecar.get("node_id") == args.node_id
        and candidate_sidecar.get("node_id") == args.node_id,
        "same_ground_truth": baseline_sidecar.get("ground_truth")
        == candidate_sidecar.get("ground_truth"),
        "same_media_specification": {
            key: baseline_media.get(key)
            for key in ("container", "codec", "width", "height", "fps", "frames")
        }
        == {
            key: candidate_media.get(key)
            for key in ("container", "codec", "width", "height", "fps", "frames")
        },
        "same_editor_profile": isinstance(baseline_profile, dict)
        and baseline_profile == candidate_profile,
        "expected_frame_count": expected_frames == 150,
    }
    if not all(contract_checks.values()):
        raise RuntimeError(f"Determinism input contract failed: {contract_checks}")
    if not baseline_video.is_file() or not candidate_video.is_file():
        raise RuntimeError("One or both accepted videos are missing")

    metrics = compare_videos(
        ffmpeg,
        baseline_video,
        candidate_video,
        expected_frames=expected_frames,
        width=args.width,
        height=args.height,
        pixel_delta=args.pixel_delta,
    )
    threshold_checks = {
        "mean_frame_mad": metrics["mean_frame_mad"] <= args.max_mean_frame_mad,
        "p95_frame_mad": metrics["p95_frame_mad"] <= args.max_p95_frame_mad,
        "maximum_frame_mad": metrics["maximum_frame_mad"]
        <= args.max_single_frame_mad,
        "changed_pixel_fraction": metrics["changed_pixel_fraction"]
        <= args.max_changed_pixel_fraction,
    }
    report = {
        "schema_version": "first_batch_node_determinism_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(threshold_checks.values()) else "failed",
        "node_id": args.node_id,
        "baseline": {
            "run_root": str(baseline_root),
            "video": str(baseline_video),
            "video_sha256": sha256_file(baseline_video),
        },
        "candidate": {
            "run_root": str(candidate_root),
            "video": str(candidate_video),
            "video_sha256": sha256_file(candidate_video),
        },
        "ffmpeg": {"path": str(ffmpeg), "sha256": sha256_file(ffmpeg)},
        "contract_checks": contract_checks,
        "metrics": {
            key: round(value, 6) if isinstance(value, float) else value
            for key, value in metrics.items()
        },
        "thresholds": {
            "max_mean_frame_mad": args.max_mean_frame_mad,
            "max_p95_frame_mad": args.max_p95_frame_mad,
            "max_single_frame_mad": args.max_single_frame_mad,
            "pixel_delta": args.pixel_delta,
            "max_changed_pixel_fraction": args.max_changed_pixel_fraction,
        },
        "threshold_checks": threshold_checks,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        os.replace(temporary, output)
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}), file=sys.stderr)
        raise
