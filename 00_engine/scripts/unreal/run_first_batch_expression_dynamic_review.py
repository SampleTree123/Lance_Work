#!/usr/bin/env python3
"""Capture and encode dynamic Happy, Angry, and Sad first-batch reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import imageio_ffmpeg


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
STAGE_SCRIPT = ROOT / "scripts" / "unreal" / "ue_stage_first_batch_expression_review.py"
CAPTURE_SCRIPT = (
    ROOT / "scripts" / "unreal" / "ue_capture_first_batch_expression_dynamic_review.py"
)
BOOTSTRAP_SCRIPT = (
    ROOT / "scripts" / "unreal" / "ue_bootstrap_first_batch_expression_dynamic_review.py"
)
CLEANUP_SCRIPT = ROOT / "scripts" / "unreal" / "ue_cleanup_first_batch_expression_review.py"
PROJECT_NAME = "datatry_02"


def execute_file_arguments(path: Path, target: str) -> list[str]:
    script_path = str(path.resolve())
    command = (
        f"DM_FIRST_BATCH_EXPRESSION_TARGET={target!r}; "
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    return ["--command", command]


def run_remote(arguments: list[str], timeout: float = 120.0) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            PROJECT_NAME,
            "--discovery-timeout",
            "30",
            *arguments,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Unreal remote command failed:\n"
            + completed.stdout[-5000:]
            + completed.stderr[-5000:]
        )
    envelope = json.loads(completed.stdout)
    for line in envelope.get("command_result", {}).get("output", []):
        output = str(line.get("output", "")).strip()
        if output.startswith("DM_FIRST_BATCH_EXPRESSION_"):
            print(output)


def wait_for_report(timeout_seconds: float = 600.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if REPORT_PATH.is_file():
            try:
                report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                report = None
            if report is not None:
                return report
        time.sleep(0.5)
    raise TimeoutError(f"Dynamic expression capture did not complete: {REPORT_PATH}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def encode_case(case: dict, fps: int, ffmpeg: str) -> dict:
    case_id = case["case_id"]
    frame_dir = OUTPUT_DIR / "frames" / case_id
    output_path = OUTPUT_DIR / "videos" / f"{case_id}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frame_dir / "frame_%03d.png"),
        "-vf",
        "scale=-2:720,tpad=stop_mode=clone:stop_duration=0.1,"
        "fps=30,format=yuv420p",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError(f"ffmpeg did not produce {output_path}")
    first_frame = Path(case["frames"][0]["image"]["path"])
    return {
        "actor_id": case["actor_id"],
        "case_id": case_id,
        "duration_seconds": len(case["frames"]) / fps,
        "expression_id": case["expression_id"],
        "first_frame": str(first_frame.resolve()),
        "frame_count": len(case["frames"]),
        "video": {
            "bytes": output_path.stat().st_size,
            "path": str(output_path.resolve()),
            "sha256": sha256(output_path),
        },
    }


def encode_report(report: dict) -> dict:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    videos = [
        encode_case(case, int(report["capture_fps"]), ffmpeg)
        for case in report["cases"]
    ]
    manifest = {
        "schema_version": 1,
        "review_id": report["review_id"],
        "status": "automatic_gate_passed_visual_review_pending",
        "capture_report": str(REPORT_PATH.resolve()),
        "case_count": len(videos),
        "videos": videos,
        "visual_review": "pending",
        "production_status": "not_approved",
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--encode-existing",
        action="store_true",
        help="Skip UE capture and encode the existing successful report.",
    )
    parser.add_argument(
        "--canonical-first-batch",
        action="store_true",
        help="Review the imported first-batch canonical female/male skeletons.",
    )
    args = parser.parse_args()
    target = "canonical" if args.canonical_first_batch else "legacy"
    output_dir = (
        ROOT
        / "outputs"
        / "unreal_character_import"
        / (
            "first_batch_day2_20260822_v1"
            if target == "canonical"
            else "first_batch_expressions_20260820_v1"
        )
        / "dynamic_review_v1"
    )
    global OUTPUT_DIR, REPORT_PATH, MANIFEST_PATH
    OUTPUT_DIR = output_dir
    REPORT_PATH = OUTPUT_DIR / "dynamic_capture_report.json"
    MANIFEST_PATH = OUTPUT_DIR / "dynamic_video_manifest.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.encode_existing:
        if not REPORT_PATH.is_file():
            raise FileNotFoundError(REPORT_PATH)
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    else:
        for path in (REPORT_PATH, MANIFEST_PATH):
            if path.exists():
                path.unlink()
        run_remote(execute_file_arguments(STAGE_SCRIPT, target))
        report = None
        try:
            run_remote(execute_file_arguments(BOOTSTRAP_SCRIPT, target))
            report = wait_for_report()
        finally:
            time.sleep(2.0)
            try:
                run_remote(
                    [
                        "--command",
                        "import unreal; s=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); "
                        "s.editor_request_end_play() if s.is_in_play_in_editor() else None",
                    ]
                )
                time.sleep(1.0)
            finally:
                run_remote(execute_file_arguments(CLEANUP_SCRIPT, target))
    if report is None:
        raise RuntimeError("Dynamic expression capture produced no report")
    if not report.get("automatic_success"):
        raise RuntimeError(
            "Dynamic expression capture failed:\n"
            + "\n".join(str(item) for item in report.get("errors", []))
        )
    manifest = encode_report(report)
    print(
        "DM_FIRST_BATCH_EXPRESSION_DYNAMIC_REVIEW="
        + json.dumps(
            {
                "manifest": str(MANIFEST_PATH),
                "case_count": manifest["case_count"],
                "success": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
