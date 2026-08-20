"""Encode CC full-preview frame captures into browser-ready MP4 files."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg


DEFAULT_CAPTURE = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\first_batch_action_full_preview\capture_20260820_v1"
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ffconcat_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def encode_case(report_path: Path, output_path: Path, ffmpeg: str) -> dict:
    report = read_json(report_path)
    fps = float(report["fps"])
    samples = sorted(report["samples"], key=lambda item: int(item["frame"]))
    if len(samples) < 2:
        raise RuntimeError(f"insufficient preview samples: {report_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_path = output_path.with_suffix(".ffconcat")
    lines = ["ffconcat version 1.0"]
    for index, sample in enumerate(samples):
        image = Path(sample.get("image_record", {}).get("path", sample["image"]))
        if not image.is_file():
            raise FileNotFoundError(image)
        lines.append(f"file '{ffconcat_path(image)}'")
        if index + 1 < len(samples):
            duration = (int(samples[index + 1]["frame"]) - int(sample["frame"])) / fps
            lines.append(f"duration {duration:.9f}")
    lines.append(f"file '{ffconcat_path(Path(samples[-1]['image']))}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-vf",
        "fps=30,format=yuv420p",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError(f"ffmpeg did not produce {output_path}")
    return {
        "bytes": output_path.stat().st_size,
        "duration_seconds": int(report["clip"]["length_frame"]) / fps,
        "fps_source": fps,
        "frame_count_source": int(report["clip"]["length_frame"]),
        "path": str(output_path.resolve()),
        "sample_count": len(samples),
        "sha256": sha256(output_path),
    }


def build_manifest(capture_root: Path, output_root: Path) -> dict:
    validation = read_json(capture_root / "validation_result.json")
    if not validation.get("success"):
        raise RuntimeError("CC capture is not complete and successful")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cases = []
    for result in validation.get("results") or []:
        if not result.get("success"):
            raise RuntimeError(f"failed capture case: {result.get('case_id')}")
        case_id = result["case_id"]
        report_path = Path(result["motion_report_path"])
        output_path = output_root / "videos" / f"{case_id}.mp4"
        video = encode_case(report_path, output_path, ffmpeg)
        recommended_start = max(
            0.0,
            (float(video["duration_seconds"]) - 3.0) / 2.0,
        )
        cases.append(
            {
                "action_id": case_id.upper(),
                "case_id": case_id,
                "label": case_id.replace("act_", "").replace("_", " ").title(),
                "pilot_actor_preset_id": result["pilot_actor_preset_id"],
                "recommended_start_seconds": round(recommended_start, 2),
                "review_family": result.get("review_family"),
                "sex": "female" if case_id.startswith("act_f") else "male",
                "source_filename": Path(result["motion"]["path"]).name,
                "video": video,
            }
        )
    cases.sort(key=lambda item: item["case_id"])
    return {
        "schema_version": 1,
        "review_id": "first_batch_action_windows_20260820_v1",
        "window_duration_seconds": 3.0,
        "capture_root": str(capture_root.resolve()),
        "case_count": len(cases),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    output_root = args.output_root or args.capture_root / "encoded_review"
    manifest = build_manifest(args.capture_root.resolve(), output_root.resolve())
    manifest_path = output_root / "action_window_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(manifest_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
