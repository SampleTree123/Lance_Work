"""Encode and verify one v11 PNG job. Never deletes raw frames.

Output is committed only after a full decode confirms 300 frames, dimensions,
30 fps, H.264/yuv420p, BT.709 limited range and no audio. A successful receipt
binds both content hashes and the job specification for safe repeated calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_RUN = WORKSPACE / "00_engine/outputs/dataset_render_pilot_20261023_v1"
ENCODING = {"encoder": "libx264", "preset": "medium", "crf": 16,
            "pixel_format": "yuv420p", "fps": 30, "frames": 300,
            "filter": "format=rgb24,scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=bicubic+accurate_rnd+full_chroma_int,format=yuv420p",
            "color_range": "tv", "colorspace": "bt709", "color_primaries": "bt709", "color_trc": "bt709",
            "audio": False, "faststart": True,
            "alpha_policy": "discard input alpha without compositing; main MP4 contains RGB-derived video only",
            "transfer_policy": "preserve display-referred PNG sample values; RGB full to BT709 limited YUV; no additional gamma transform"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def find_ffmpeg(explicit=None):
    if explicit:
        value = shutil.which(explicit) or explicit
        if not Path(value).is_file():
            raise ValueError(f"FFmpeg not found: {explicit}")
        return str(value)
    value = shutil.which("ffmpeg")
    if value:
        return value
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise RuntimeError("Provide --ffmpeg or install imageio-ffmpeg") from e


def valid_job_id(value):
    return bool(re.fullmatch(r"(?:(?:train|test)_node_\d{6,}|ref_[A-Za-z0-9][A-Za-z0-9_-]{0,90})", value))


def checked_run(command):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"FFmpeg exited {result.returncode}: {result.stderr[-5000:]}")
    return result


def inspect_video(ffmpeg, path, job):
    # The same FFmpeg binary verifies on Windows and Linux; ffprobe is optional.
    result = checked_run([ffmpeg, "-hide_banner", "-nostdin", "-xerror", "-i", str(path),
                          "-map", "0:v:0", "-progress", "pipe:1", "-nostats", "-f", "null", "-"])
    input_info = result.stderr.split("Stream mapping:", 1)[0]
    video_line = next((x for x in input_info.splitlines() if "Video:" in x), "")
    if "Audio:" in input_info:
        raise ValueError("Unexpected audio stream")
    if len(re.findall(r"Video:", input_info)) != 1:
        raise ValueError("Expected exactly one video stream")
    if not re.search(r"Video: h264\b", video_line) or not re.search(r"\byuv420p\(", video_line):
        raise ValueError(f"Expected H.264 yuv420p: {video_line}")
    if "tv, bt709" not in video_line:
        raise ValueError(f"Missing limited-range BT.709 metadata: {video_line}")
    if not re.search(rf"\b{job['width']}x{job['height']}\b", video_line):
        raise ValueError(f"Unexpected video dimensions: {video_line}")
    match = re.search(r"([\d.]+) fps", video_line)
    if not match or abs(float(match.group(1)) - job["fps"]) > 0.001:
        raise ValueError(f"Unexpected frame rate: {video_line}")
    counts = re.findall(r"^frame=(\d+)\s*$", result.stdout, re.MULTILINE)
    if not counts or int(counts[-1]) != job["frames"]:
        raise ValueError(f"Decoded frame count mismatch: {counts[-1:]}")
    times = re.findall(r"^out_time_us=(\d+)\s*$", result.stdout, re.MULTILINE)
    duration = int(times[-1]) / 1e6 if times else None
    if duration is None or abs(duration - job["frames"] / job["fps"]) > 1 / job["fps"] + 0.001:
        raise ValueError(f"Decoded duration mismatch: {duration}")
    # Decoding with -xerror additionally fails on damaged packets/frames.
    return {"codec": "h264", "pixel_format": "yuv420p", "width": job["width"], "height": job["height"],
            "fps": job["fps"], "decoded_frames": int(counts[-1]), "duration_seconds": duration,
            "audio_streams": 0, "color_range": "tv", "colorspace": "bt709", "stream_description": video_line.strip(),
            "verification": "full_ffmpeg_decode_xerror"}


def frame_signature(frames_dir, job):
    expected = [frames_dir / f"frame_{n:04d}.png" for n in range(job["frames"])]
    actual = set(frames_dir.glob("*.png"))
    missing, extra = set(expected) - actual, actual - set(expected)
    if missing or extra:
        raise ValueError(f"PNG sequence must be exactly frame_0000..frame_0299: missing={len(missing)}, extra={len(extra)}")
    entries = []
    for path in expected:
        with path.open("rb") as f:
            header = f.read(33)
        if len(header) < 33 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise ValueError(f"Invalid PNG header: {path.name}")
        width, height, bits, color = struct.unpack(">IIBB", header[16:26])
        if (width, height, bits) != (job["width"], job["height"], 8) or color not in (2, 6):
            raise ValueError(f"Expected 8-bit RGB/RGBA {job['width']}x{job['height']}, got {(width,height,bits,color)} in {path.name}")
        entries.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest(path),
                        "channels": "RGBA" if color == 6 else "RGB"})
    signature = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return signature, entries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--jobs", type=Path, help="Explicit job manifest; relative paths use run root")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    run_root = args.run_root.resolve()
    if not valid_job_id(args.job_id):
        parser.error("Invalid job ID; expected train/test_node_000000 or a safe ref_* identifier")
    job_dir = run_root / "jobs" / args.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    receipt_path, video_path = job_dir / "media_receipt.json", job_dir / "video.mp4"
    attempt_path, temporary = job_dir / "media_attempt.json", job_dir / "video.encoding.mp4"
    started, phase = time.perf_counter(), "resolve_job"
    try:
        job = None
        manifests = [args.jobs if args.jobs.is_absolute() else run_root / args.jobs] if args.jobs else [run_root / name for name in ("main_jobs.json", "pilot_jobs.json")]
        for path in manifests:
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                job = next((x for x in payload["jobs"] if x["job_id"] == args.job_id), None)
                if job:
                    break
        if job is None:
            raise ValueError(f"Job not found: {args.job_id}")
        if job["fps"] != 30 or job["frames"] != 300 or job["width"] % 2 or job["height"] % 2:
            raise ValueError("Expected 30 fps, 300 frames, and even dimensions")
        spec_hash = hashlib.sha256(json.dumps({"job": job, "encoding": ENCODING}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        ffmpeg = find_ffmpeg(args.ffmpeg)
        phase = "hash_input"
        signature, entries = frame_signature(job_dir / "frames", job)
        input_check_seconds = time.perf_counter() - started
        if not args.force and receipt_path.exists() and video_path.exists():
            old = json.loads(receipt_path.read_text(encoding="utf-8"))
            if old.get("status") == "success" and old.get("spec_sha256") == spec_hash and old.get("input_sha256") == signature and old.get("video_sha256") == digest(video_path):
                print(json.dumps({"status": "reused_verified_receipt", "job_id": args.job_id, "video": str(video_path)}))
                return 0
        phase = "encode"
        command = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-xerror", "-framerate", "30", "-start_number", "0",
                   "-i", str(job_dir / "frames/frame_%04d.png"), "-map", "0:v:0", "-an", "-frames:v", "300",
                   "-vf", ENCODING["filter"], "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                   "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                   "-fps_mode", "cfr", "-r", "30", "-movflags", "+faststart", str(temporary)]
        encode_start = time.perf_counter()
        checked_run(command)
        encode_seconds = time.perf_counter() - encode_start
        phase = "verify_media"
        verification_start = time.perf_counter()
        media = inspect_video(ffmpeg, temporary, job)
        verify_seconds = time.perf_counter() - verification_start
        output_hash, output_bytes = digest(temporary), temporary.stat().st_size
        os.replace(temporary, video_path)
        receipt = {"schema": "dataset_media_receipt_v11_v1", "status": "success", "job_id": args.job_id,
                   "finished_at": datetime.now(timezone.utc).isoformat(), "spec_sha256": spec_hash,
                   "input_sha256": signature, "input_frames": entries, "input_channels": sorted({e["channels"] for e in entries}),
                   "alpha_policy": ENCODING["alpha_policy"], "video_sha256": output_hash, "video_bytes": output_bytes,
                   "video": f"jobs/{args.job_id}/video.mp4", "media": media, "encoding": ENCODING,
                   "ffmpeg_version": checked_run([ffmpeg, "-version"]).stdout.splitlines()[0],
                   "command": command, "timing": {"input_check_seconds": input_check_seconds, "encode_seconds": encode_seconds,
                   "verification_seconds": verify_seconds, "total_seconds": time.perf_counter() - started}, "raw_frames_deleted": False}
        atomic_json(receipt_path, receipt)
        atomic_json(attempt_path, {"status": "success", "job_id": args.job_id, "receipt": "media_receipt.json"})
        print(json.dumps({"status": "success", "job_id": args.job_id, "video_bytes": output_bytes, "encode_seconds": encode_seconds}))
        return 0
    except Exception as exc:
        # Preserve any previous success receipt/video; a failure is a separate attempt.
        atomic_json(attempt_path, {"status": "failed", "job_id": args.job_id, "phase": phase,
                    "error": str(exc), "finished_at": datetime.now(timezone.utc).isoformat(), "seconds": time.perf_counter() - started})
        print(json.dumps({"status": "failed", "job_id": args.job_id, "phase": phase, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
