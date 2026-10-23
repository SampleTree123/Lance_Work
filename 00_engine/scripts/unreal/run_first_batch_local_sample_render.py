#!/usr/bin/env python3
"""Render, validate, and encode one local first-batch five-second sample."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageChops, ImageStat

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = ROOT / "00_engine"
REMOTE_EXEC = ENGINE_ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
START_SCRIPT = (
    ENGINE_ROOT
    / "scripts"
    / "unreal"
    / "ue_start_first_batch_local_sample_render.py"
)
PROFILE_RUNNER = (
    ENGINE_ROOT / "scripts" / "unreal" / "run_first_batch_render_profile.py"
)
DEFAULT_OUTPUT_ROOT = ENGINE_ROOT / "outputs" / "unreal_render"
DEFAULT_PROJECT_NAME = os.environ.get("DM_UE_PROJECT_NAME", "datatry_02")
DEFAULT_UE_ENGINE_ROOT = (
    Path(os.environ["DM_UE_ENGINE_ROOT"])
    if os.environ.get("DM_UE_ENGINE_ROOT")
    else None
)
_remote_project_name = DEFAULT_PROJECT_NAME
_remote_engine_root = DEFAULT_UE_ENGINE_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", default=DEFAULT_PROJECT_NAME)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_UE_ENGINE_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--map-path",
        default=(
            "/Game/DataMake/Scenes/TokyoStylized/"
            "L_DM_TokyoStylized.L_DM_TokyoStylized"
        ),
    )
    parser.add_argument(
        "--sequence-path",
        default=(
            "/Game/DataMake/Sequences/FirstBatch/"
            "LS_DM_FirstBatch_F02_20s_Pilot_v001."
            "LS_DM_FirstBatch_F02_20s_Pilot_v001"
        ),
    )
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--end-frame", type=int, default=150)
    parser.add_argument("--job-name", default="DM_FirstBatch_LocalSample_v001")
    parser.add_argument("--skip-profile", action="store_true")
    parser.add_argument(
        "--render-offscreen",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override MRQ PIE offscreen mode (defaults on for Linux without DISPLAY).",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow a non-150-frame diagnostic render.",
    )
    parser.add_argument(
        "--evaluation-preroll-frames",
        type=int,
        default=0,
        help=(
            "Render and discard this many frames before the requested range so "
            "PIE/Sequencer bindings are evaluated before the first delivery frame."
        ),
    )
    return parser.parse_args()


def configure_remote(project_name: str, engine_root: Path | None = None) -> None:
    global _remote_project_name, _remote_engine_root
    _remote_project_name = project_name
    _remote_engine_root = engine_root.resolve() if engine_root is not None else None


def resolve_render_offscreen(
    requested: bool | None,
    *,
    platform_name: str | None = None,
    display: str | None = None,
) -> bool:
    if requested is not None:
        return requested
    platform_name = sys.platform if platform_name is None else platform_name
    display = os.environ.get("DISPLAY") if display is None else display
    return platform_name.startswith("linux") and not display


def resolve_ffmpeg_exe() -> str:
    configured = os.environ.get("DM_FFMPEG_EXE")
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
        raise RuntimeError(f"DM_FFMPEG_EXE is not executable: {path}")

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    if imageio_ffmpeg is not None:
        return imageio_ffmpeg.get_ffmpeg_exe()
    raise RuntimeError(
        "ffmpeg is unavailable; install imageio-ffmpeg or set DM_FFMPEG_EXE "
        "to an executable ffmpeg binary"
    )


def remote(command: str, timeout: int = 120) -> dict:
    remote_command = [
        sys.executable,
        str(REMOTE_EXEC),
        "--project",
        _remote_project_name,
        "--discovery-timeout",
        "30",
        "--command",
        command,
    ]
    if _remote_engine_root is not None:
        remote_command.extend(["--engine-root", str(_remote_engine_root)])
    completed = subprocess.run(
        remote_command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout + "\n" + completed.stderr)
    envelope = json.loads(completed.stdout)
    result = envelope.get("command_result", {})
    if not result.get("success"):
        raise RuntimeError(f"UE command failed: {result}")
    return result


def tagged(result: dict, prefix: str) -> dict:
    records = [
        json.loads(str(item["output"])[len(prefix) :])
        for item in result.get("output", [])
        if str(item.get("output", "")).startswith(prefix)
    ]
    if len(records) != 1:
        raise RuntimeError(f"Expected one {prefix} record, found {len(records)}")
    return records[0]


def encode_video(frames: list[Path], output: Path) -> None:
    manifest = output.with_suffix(".frames.txt")
    lines = []
    for frame in frames:
        escaped = frame.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
        lines.append("duration 0.0333333333333333")
    # The concat demuxer needs the last image repeated to honor its duration.
    escaped_last = frames[-1].resolve().as_posix().replace("'", "'\\''")
    lines.append(f"file '{escaped_last}'")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [
        resolve_ffmpeg_exe(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(manifest),
        "-r",
        "30",
        "-frames:v",
        str(len(frames)),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(completed.stdout + "\n" + completed.stderr)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_rendered_frames(
    frames: list[Path], expected_delivery_frames: int, preroll_frames: int
) -> tuple[list[Path], list[Path], str]:
    if preroll_frames < 0:
        raise ValueError("Evaluation preroll frame count must be non-negative")
    expected_rendered_frames = expected_delivery_frames + preroll_frames
    if len(frames) == expected_rendered_frames:
        discarded = frames[:preroll_frames]
        delivery = frames[preroll_frames:]
        mode = "explicit_output_discard"
    elif preroll_frames and len(frames) == expected_delivery_frames:
        # MRQ clips output before the Level Sequence playback start, while still
        # evaluating section preroll at the requested negative frame.
        discarded = []
        delivery = frames
        mode = "playback_range_clipped_preroll"
    else:
        raise RuntimeError(
            f"Expected {expected_rendered_frames} rendered PNG frames, or "
            f"{expected_delivery_frames} after playback-range clipping; found "
            f"{len(frames)}"
        )
    if len(delivery) != expected_delivery_frames:
        raise RuntimeError(
            f"Expected {expected_delivery_frames} delivery frames, found "
            f"{len(delivery)}"
        )
    return discarded, delivery, mode


def grayscale_mean_abs_difference(first_path: Path, second_path: Path) -> float:
    with Image.open(first_path) as source:
        first = source.convert("L").resize((320, 180))
    with Image.open(second_path) as source:
        second = source.convert("L").resize((320, 180))
    return float(ImageStat.Stat(ImageChops.difference(first, second)).mean[0])


def main() -> int:
    args = parse_args()
    configure_remote(args.project_name, args.engine_root)
    render_offscreen = resolve_render_offscreen(args.render_offscreen)
    expected_frame_count = args.end_frame - args.start_frame
    if expected_frame_count <= 0:
        raise ValueError("The render frame range must be positive")
    if expected_frame_count != 150 and not args.allow_partial:
        raise ValueError(
            "A first-batch sample must contain exactly 150 frames: "
            f"{args.start_frame}..{args.end_frame}"
        )
    if args.evaluation_preroll_frames < 0:
        raise ValueError("Evaluation preroll frame count must be non-negative")
    render_start_frame = args.start_frame - args.evaluation_preroll_frames
    expected_rendered_frame_count = (
        expected_frame_count + args.evaluation_preroll_frames
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir
        else (DEFAULT_OUTPUT_ROOT / f"first_batch_local_sample_{timestamp}_v001")
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    if not args.skip_profile:
        profile_command = [
            sys.executable,
            str(PROFILE_RUNNER),
            "--project-name",
            args.project_name,
        ]
        if args.engine_root is not None:
            profile_command.extend(["--engine-root", str(args.engine_root.resolve())])
        profile = subprocess.run(
            profile_command,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if profile.returncode != 0:
            raise RuntimeError(profile.stdout + "\n" + profile.stderr)

    script_path = str(START_SCRIPT.resolve())
    command = (
        f"DM_OUTPUT_DIRECTORY={output_dir.as_posix()!r}; "
        f"DM_MAP_PATH={args.map_path!r}; "
        f"DM_SEQUENCE_PATH={args.sequence_path!r}; "
        f"DM_START_FRAME={render_start_frame!r}; "
        f"DM_END_FRAME={args.end_frame!r}; "
        f"DM_JOB_NAME={args.job_name!r}; "
        f"DM_ALLOW_PARTIAL={bool(args.allow_partial or args.evaluation_preroll_frames)!r}; "
        f"DM_RENDER_OFFSCREEN={render_offscreen!r}; "
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    started = tagged(remote(command), "DM_SAMPLE_RENDER_STARTED=")
    deadline = time.monotonic() + args.timeout_seconds
    poll_failures = []
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"MRQ did not finish within {args.timeout_seconds} seconds"
            )
        time.sleep(5)
        try:
            status_result = remote(
                "import unreal; import json; "
                "print('DM_RENDER_STATUS=' + json.dumps({"
                "'rendering': bool(unreal.get_editor_subsystem("
                "unreal.MoviePipelineQueueSubsystem).is_rendering())}))",
                timeout=90,
            )
            status = tagged(status_result, "DM_RENDER_STATUS=")
            print(
                json.dumps(
                    {"elapsed_seconds": round(args.timeout_seconds - (deadline - time.monotonic()), 1), **status},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if not status["rendering"]:
                break
        except Exception as exc:  # PIE may briefly stop answering remote discovery.
            poll_failures.append(str(exc))
            print("MRQ status poll unavailable; retrying.", flush=True)

    time.sleep(2)
    rendered_frames = sorted(output_dir.rglob("*.png"))
    discarded_frames, frames, preroll_mode = split_rendered_frames(
        rendered_frames,
        expected_frame_count,
        args.evaluation_preroll_frames,
    )
    discarded_records = [
        {
            "file_name": frame.name,
            "bytes": frame.stat().st_size,
            "sha256": sha256(frame),
        }
        for frame in discarded_frames
    ]
    discarded_to_first_difference = (
        grayscale_mean_abs_difference(discarded_frames[-1], frames[0])
        if discarded_frames
        else None
    )
    for frame in discarded_frames:
        frame.unlink()
    dimensions = set()
    for frame in (frames[0], frames[len(frames) // 2], frames[-1]):
        with Image.open(frame) as image:
            dimensions.add(image.size)
    if dimensions != {(2560, 1440)}:
        raise RuntimeError(f"Unexpected frame dimensions: {sorted(dimensions)}")

    video = output_dir / "first_batch_local_sample.mp4"
    encode_video(frames, video)
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "render_job": started,
        "requested_rendered_frame_count": expected_rendered_frame_count,
        "rendered_frame_count_before_preroll_discard": len(rendered_frames),
        "frame_count": len(frames),
        "resolution": [2560, 1440],
        "fps": 30,
        "duration_seconds": len(frames) / 30.0,
        "map": args.map_path,
        "sequence": args.sequence_path,
        "start_frame_inclusive": args.start_frame,
        "end_frame_exclusive": args.end_frame,
        "evaluation_preroll": {
            "schema_version": 1,
            "requested_frames": args.evaluation_preroll_frames,
            "render_start_frame_inclusive": render_start_frame,
            "render_end_frame_exclusive": args.end_frame,
            "discarded_frame_count": len(discarded_frames),
            "mode": preroll_mode,
            "discarded_frames": discarded_records,
            "discarded_to_first_delivery_mean_abs_difference": (
                round(discarded_to_first_difference, 6)
                if discarded_to_first_difference is not None
                else None
            ),
            "retained_frame_count": len(frames),
            "checks": {
                "requested_one_frame": args.evaluation_preroll_frames == 1,
                "requested_before_delivery_range": render_start_frame
                == args.start_frame - 1,
                "retained_delivery_count": len(frames) == expected_frame_count,
                "valid_output_mode": preroll_mode
                in {
                    "explicit_output_discard",
                    "playback_range_clipped_preroll",
                },
            },
        },
        "first_frame": str(frames[0]),
        "last_frame": str(frames[-1]),
        "video": str(video),
        "video_size_bytes": video.stat().st_size,
        "video_sha256": sha256(video),
        "poll_failure_count": len(poll_failures),
        "poll_failures": poll_failures,
    }
    report_path = output_dir / "render_report.json"
    report["evaluation_preroll"]["passed"] = all(
        report["evaluation_preroll"]["checks"].values()
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
