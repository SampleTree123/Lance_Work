#!/usr/bin/env python3
"""Compute simple frame-aligned pixel metrics for two evaluation videos.

Frames are aligned by normalized temporal position and the reference is resized
to the candidate resolution. These metrics are diagnostics, not a semantic
video-edit quality score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Sequence, Tuple

import cv2
import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_video(path: Path) -> Tuple[List[np.ndarray], Dict[str, Any]]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"could not open video {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames: List[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    if not frames:
        raise ValueError(f"video has no decodable frames: {path}")
    height, width = frames[0].shape[:2]
    return frames, {
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "frames": len(frames),
        "fps": fps,
        "width": width,
        "height": height,
        "duration_seconds": len(frames) / fps if fps else None,
    }


def normalized_indexes(source_length: int, target_length: int) -> List[int]:
    if source_length < 1 or target_length < 1:
        raise ValueError("frame counts must be positive")
    return [int(round(value)) for value in np.linspace(0, source_length - 1, target_length)]


def ssim_luma(first: np.ndarray, second: np.ndarray) -> float:
    first_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY).astype(np.float64)
    second_gray = cv2.cvtColor(second, cv2.COLOR_BGR2GRAY).astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_first = cv2.GaussianBlur(first_gray, (11, 11), 1.5)
    mu_second = cv2.GaussianBlur(second_gray, (11, 11), 1.5)
    mu_first_sq = mu_first * mu_first
    mu_second_sq = mu_second * mu_second
    mu_both = mu_first * mu_second
    sigma_first = cv2.GaussianBlur(first_gray * first_gray, (11, 11), 1.5) - mu_first_sq
    sigma_second = cv2.GaussianBlur(second_gray * second_gray, (11, 11), 1.5) - mu_second_sq
    sigma_both = cv2.GaussianBlur(first_gray * second_gray, (11, 11), 1.5) - mu_both
    numerator = (2 * mu_both + c1) * (2 * sigma_both + c2)
    denominator = (mu_first_sq + mu_second_sq + c1) * (
        sigma_first + sigma_second + c2
    )
    return float(np.mean(numerator / denominator))


def compare_frames(
    candidate_frames: Sequence[np.ndarray], reference_frames: Sequence[np.ndarray]
) -> Dict[str, Any]:
    reference_indexes = normalized_indexes(len(reference_frames), len(candidate_frames))
    per_frame: List[Dict[str, float | int]] = []
    for candidate_index, (candidate, reference_index) in enumerate(
        zip(candidate_frames, reference_indexes)
    ):
        reference = reference_frames[reference_index]
        height, width = candidate.shape[:2]
        if reference.shape[:2] != (height, width):
            reference = cv2.resize(reference, (width, height), interpolation=cv2.INTER_AREA)
        difference = candidate.astype(np.float64) - reference.astype(np.float64)
        mse = float(np.mean(difference * difference))
        l1 = float(np.mean(np.abs(difference)))
        psnr = float("inf") if mse == 0 else 10 * math.log10((255 * 255) / mse)
        per_frame.append(
            {
                "candidate_frame": candidate_index,
                "reference_frame": reference_index,
                "mse": mse,
                "l1": l1,
                "psnr_db": psnr,
                "ssim_luma": ssim_luma(candidate, reference),
            }
        )
    return {
        "alignment": "normalized_temporal_position_reference_resized_to_candidate",
        "frame_count": len(per_frame),
        "mean_mse": mean(float(item["mse"]) for item in per_frame),
        "mean_l1": mean(float(item["l1"]) for item in per_frame),
        "mean_psnr_db": mean(float(item["psnr_db"]) for item in per_frame),
        "median_psnr_db": median(float(item["psnr_db"]) for item in per_frame),
        "mean_ssim_luma": mean(float(item["ssim_luma"]) for item in per_frame),
        "per_frame": per_frame,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate_frames, candidate_meta = read_video(args.candidate.resolve())
    reference_frames, reference_meta = read_video(args.reference.resolve())
    report = {
        "schema_version": "datamake_framewise_video_comparison_v1",
        "scope": "diagnostic_pixel_similarity_not_semantic_edit_quality",
        "candidate": candidate_meta,
        "reference": reference_meta,
        "metrics": compare_frames(candidate_frames, reference_frames),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
