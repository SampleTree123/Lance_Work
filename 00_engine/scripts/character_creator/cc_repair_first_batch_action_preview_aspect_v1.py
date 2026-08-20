"""Repair the three 2026-08-20 replacement previews captured in a flat render band."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import imageio_ffmpeg


ENGINE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_full_preview"
    / "review_20260820_v2_5s"
    / "action_window_manifest.json"
)
AFFECTED_ACTION_IDS = {
    "ACT_F02_SENSUAL_DANCE_03",
    "ACT_F05_TIE_SHOES",
    "ACT_M04_WATCH_GAME_HAPPY_DANCING",
}
VIDEO_FILTER = "crop=640:140:0:250,scale=640:640:flags=lanczos,setsar=1,format=yuv420p"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locked_file(path: Path) -> dict:
    path = path.resolve()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def repair(manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases") or []
    by_action = {case.get("action_id"): case for case in cases}
    missing = AFFECTED_ACTION_IDS - set(by_action)
    if missing:
        raise RuntimeError(f"Manifest is missing affected actions: {sorted(missing)}")

    existing = manifest.get("aspect_correction") or {}
    if existing.get("status") == "applied":
        for action_id in AFFECTED_ACTION_IDS:
            path = Path(by_action[action_id]["video"]["path"])
            if not path.is_file() or sha256_file(path) != by_action[action_id]["video"]["sha256"]:
                raise RuntimeError(f"Corrected video drifted: {action_id}")
        return {
            "status": "already_applied",
            "manifest": str(manifest_path),
            "corrected_count": len(AFFECTED_ACTION_IDS),
        }

    backup_path = manifest_path.with_name("action_window_manifest.pre_aspect_fix.json")
    if not backup_path.exists():
        shutil.copy2(manifest_path, backup_path)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_root = manifest_path.parent / "corrected_videos"
    output_root.mkdir(parents=True, exist_ok=True)
    corrections = []
    for action_id in sorted(AFFECTED_ACTION_IDS):
        case = by_action[action_id]
        source_path = Path(case["video"]["path"]).resolve()
        source_record = locked_file(source_path)
        if source_record["sha256"] != case["video"].get("sha256"):
            raise RuntimeError(f"Source preview hash drifted: {action_id}")

        output_path = output_root / f"{case['case_id']}.mp4"
        temporary = output_path.with_name(output_path.stem + ".tmp.mp4")
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source_path),
            "-vf",
            VIDEO_FILTER,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-movflags",
            "+faststart",
            str(temporary),
        ]
        subprocess.run(command, check=True)
        if not temporary.is_file() or temporary.stat().st_size <= 0:
            raise RuntimeError(f"Aspect correction produced no video: {action_id}")
        temporary.replace(output_path)
        corrected_record = locked_file(output_path)
        case["video"].update(corrected_record)
        case["video"]["aspect_correction"] = {
            "status": "applied",
            "source_video": source_record,
            "filter": VIDEO_FILTER,
            "reason": "cc_render_was_letterboxed_and_vertically_compressed_into_y250_389",
        }
        corrections.append(
            {
                "action_id": action_id,
                "source_video": source_record,
                "corrected_video": corrected_record,
            }
        )

    manifest["aspect_correction"] = {
        "status": "applied",
        "applied_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "affected_action_count": len(corrections),
        "affected_action_ids": sorted(AFFECTED_ACTION_IDS),
        "filter": VIDEO_FILTER,
        "pre_correction_manifest": locked_file(backup_path),
        "corrections": corrections,
    }
    write_json(manifest_path, manifest)
    return {
        "status": "applied",
        "manifest": str(manifest_path),
        "corrected_count": len(corrections),
        "output_root": str(output_root.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    print(json.dumps(repair(args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
