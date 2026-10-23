"""Independently verify a packaged first-batch dataset_v1 directory."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


MANIFEST_SCHEMA_VERSION = "datamake_video_edit_dataset_manifest_v1"
CHAIN_SCHEMA_VERSION = "datamake_multiround_video_chain_v1"
REPORT_SCHEMA_VERSION = "datamake_video_edit_dataset_verification_v1"
INTERNAL_ID_PATTERN = re.compile(r"\b(?:c|e|n|t)_[0-9a-f]{8,}\b", re.IGNORECASE)


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Could not read JSON: {path}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise VerificationError(f"Could not hash file: {path}") from exc
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def safe_package_path(dataset_root: Path, relative: str, label: str) -> Path:
    candidate = Path(relative)
    require(not candidate.is_absolute(), f"{label} must be relative: {relative}")
    resolved_root = dataset_root.resolve()
    resolved = (dataset_root / candidate).resolve()
    require(
        resolved == resolved_root or resolved_root in resolved.parents,
        f"{label} escapes dataset root: {relative}",
    )
    return resolved


def parse_rate(value: object, label: str) -> Fraction:
    require(isinstance(value, str) and value, f"Missing {label}")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise VerificationError(f"Invalid {label}: {value}") from exc


def probe_video(path: Path, ffprobe_bin: str) -> dict[str, Any]:
    command = [
        ffprobe_bin,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,avg_frame_rate,nb_frames:format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError(f"ffprobe could not inspect {path}: {exc}") from exc
    require(
        completed.returncode == 0,
        f"ffprobe failed for {path}: {completed.stderr.strip()}",
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"ffprobe returned invalid JSON for {path}") from exc
    streams = result.get("streams", [])
    require(len(streams) == 1, f"Expected one primary video stream: {path}")
    stream = streams[0]
    duration_value = result.get("format", {}).get("duration")
    require(isinstance(duration_value, str), f"Missing media duration: {path}")
    frames_value = stream.get("nb_frames")
    require(isinstance(frames_value, str) and frames_value.isdigit(), f"Missing frame count: {path}")
    return {
        "codec": stream.get("codec_name"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": float(parse_rate(stream.get("avg_frame_rate"), "average frame rate")),
        "frames": int(frames_value),
        "duration_seconds": float(duration_value),
    }


def verify_bilingual_text(value: object, label: str) -> list[str]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == {"en", "zh-CN"}, f"{label} must contain exactly en and zh-CN")
    texts = [value["en"], value["zh-CN"]]
    require(
        all(isinstance(text, str) and text.strip() for text in texts),
        f"{label} contains empty text",
    )
    return texts


def verify_video_record(
    dataset_root: Path,
    record: dict[str, Any],
    expected_index: int,
    ffprobe_bin: str,
) -> dict[str, Any]:
    expected_path = f"videos/{expected_index}.mp4"
    require(record.get("index") == expected_index, f"Video index mismatch: {expected_index}")
    require(record.get("path") == expected_path, f"Video path mismatch: {expected_index}")
    path = safe_package_path(dataset_root, expected_path, "video path")
    require(path.is_file(), f"Video is missing: {expected_path}")
    media = record.get("media")
    require(isinstance(media, dict), f"Missing media record: {expected_path}")
    require(path.stat().st_size == media.get("bytes"), f"Video byte count mismatch: {expected_path}")
    actual_sha256 = sha256_file(path)
    require(actual_sha256 == media.get("sha256"), f"Video SHA-256 mismatch: {expected_path}")
    probe = probe_video(path, ffprobe_bin)
    for key in ("codec", "width", "height", "frames"):
        require(probe[key] == media.get(key), f"Video {key} mismatch: {expected_path}")
    require(abs(probe["fps"] - float(media.get("fps"))) <= 0.001, f"Video fps mismatch: {expected_path}")
    require(
        abs(probe["duration_seconds"] - float(media.get("duration_seconds"))) <= 0.05,
        f"Video duration mismatch: {expected_path}",
    )
    return {
        "index": expected_index,
        "path": expected_path,
        "node_id": record.get("node_id"),
        "sha256": actual_sha256,
        "probe": probe,
    }


def verify_chains(
    *,
    chains: list[Any],
    manifest: dict[str, Any],
    video_paths: set[str],
) -> dict[str, Any]:
    chain_ids: list[str] = []
    turn_ids: set[str] = set()
    referenced_videos: set[str] = set()
    turn_count = 0
    for chain_index, raw_chain in enumerate(chains, start=1):
        require(isinstance(raw_chain, dict), f"Chain {chain_index} is not an object")
        chain = raw_chain
        chain_id = chain.get("chain_id")
        require(isinstance(chain_id, str) and chain_id, f"Chain {chain_index} has no ID")
        require(chain_id not in chain_ids, f"Duplicate chain ID: {chain_id}")
        chain_ids.append(chain_id)
        require(chain.get("schema_version") == CHAIN_SCHEMA_VERSION, f"Chain schema mismatch: {chain_id}")
        for key in ("dataset_id", "batch_id", "package_scope"):
            require(chain.get(key) == manifest.get(key), f"Chain {key} mismatch: {chain_id}")
        sequence = chain.get("video_sequence")
        turns = chain.get("turns")
        require(isinstance(sequence, list) and len(sequence) >= 2, f"Invalid video sequence: {chain_id}")
        require(isinstance(turns, list), f"Invalid turns: {chain_id}")
        require(chain.get("edit_length") == len(turns), f"Edit length mismatch: {chain_id}")
        require(len(sequence) == len(turns) + 1, f"Chain sequence/turn mismatch: {chain_id}")
        sequence_paths: list[str] = []
        for position, item in enumerate(sequence):
            require(isinstance(item, dict), f"Invalid sequence item: {chain_id}/{position}")
            require(item.get("position") == position, f"Sequence position mismatch: {chain_id}/{position}")
            path = item.get("path")
            require(path in video_paths, f"Unknown sequence video: {chain_id}/{path}")
            sequence_paths.append(path)
            referenced_videos.add(path)
        require(chain.get("initial_video") == sequence_paths[0], f"Initial video mismatch: {chain_id}")
        require(chain.get("final_video") == sequence_paths[-1], f"Final video mismatch: {chain_id}")
        for offset, raw_turn in enumerate(turns):
            require(isinstance(raw_turn, dict), f"Invalid turn: {chain_id}/{offset + 1}")
            turn = raw_turn
            turn_id = turn.get("turn_id")
            require(isinstance(turn_id, str) and turn_id, f"Missing turn ID: {chain_id}/{offset + 1}")
            require(turn_id not in turn_ids, f"Duplicate turn ID: {turn_id}")
            turn_ids.add(turn_id)
            require(turn.get("round") == offset + 1, f"Turn round mismatch: {turn_id}")
            require(turn.get("video_in") == sequence_paths[offset], f"Turn input mismatch: {turn_id}")
            require(turn.get("video_out") == sequence_paths[offset + 1], f"Turn output mismatch: {turn_id}")
            require(
                turn.get("source_node_id") == sequence[offset].get("node_id"),
                f"Turn source node mismatch: {turn_id}",
            )
            require(
                turn.get("target_node_id") == sequence[offset + 1].get("node_id"),
                f"Turn target node mismatch: {turn_id}",
            )
            texts = verify_bilingual_text(turn.get("prompt"), f"Prompt {turn_id}")
            texts += verify_bilingual_text(
                turn.get("standalone_prompt"), f"Standalone prompt {turn_id}"
            )
            require(
                all(INTERNAL_ID_PATTERN.search(text) is None for text in texts),
                f"Internal ID leaked into prompt text: {turn_id}",
            )
            flags = turn.get("quality_flags")
            require(isinstance(flags, dict), f"Missing quality flags: {turn_id}")
            require(flags.get("atomic") is True, f"Non-atomic turn: {turn_id}")
            require(flags.get("language_complete") is True, f"Incomplete language: {turn_id}")
            require(flags.get("contains_internal_id") is False, f"Internal ID flag failed: {turn_id}")
            require(flags.get("paired_media_required") is True, f"Paired media flag failed: {turn_id}")
            change = turn.get("change")
            require(isinstance(change, dict), f"Missing change record: {turn_id}")
            require(change.get("before") != change.get("after"), f"No-op turn: {turn_id}")
            referenced_videos.update((turn["video_in"], turn["video_out"]))
            turn_count += 1
    require(chain_ids == manifest.get("chain_ids"), "Manifest chain ID order/content mismatch")
    return {
        "chains": len(chains),
        "turns": turn_count,
        "unique_turn_ids": len(turn_ids),
        "referenced_videos": len(referenced_videos),
        "all_video_paths_referenced": referenced_videos == video_paths,
    }


def expected_simple_chain(chain: dict[str, Any], chain_index: int) -> dict[str, Any]:
    return {
        "chain_index": chain_index,
        "chain_id": chain["chain_id"],
        "turns": [
            {
                "input_video": turn["video_in"],
                "instruction": turn["prompt"],
                "output_video": turn["video_out"],
            }
            for turn in chain["turns"]
        ],
    }


def verify_simple_chains(
    simple_chains: object, chains: list[Any]
) -> dict[str, Any]:
    require(isinstance(simple_chains, list), "chains_simple.json must contain an array")
    require(len(simple_chains) == len(chains), "Simplified chain count mismatch")
    for chain_index, (simple, full) in enumerate(
        zip(simple_chains, chains), start=1
    ):
        require(isinstance(simple, dict), f"Simplified chain {chain_index} is invalid")
        require(isinstance(full, dict), f"Full chain {chain_index} is invalid")
        require(
            simple == expected_simple_chain(full, chain_index),
            f"Simplified chain differs from full chain: {chain_index}",
        )
    return {
        "chains": len(simple_chains),
        "first_chain_index": simple_chains[0]["chain_index"] if simple_chains else None,
        "last_chain_index": simple_chains[-1]["chain_index"] if simple_chains else None,
    }


def verify_delivery(
    *,
    dataset_root: Path,
    ffprobe_bin: str = "ffprobe",
    workers: int = 4,
    strict_first_batch: bool = True,
) -> dict[str, Any]:
    require(workers >= 1, "workers must be at least 1")
    dataset_root = dataset_root.resolve()
    require(dataset_root.is_dir(), f"Dataset root does not exist: {dataset_root}")
    manifest_path = dataset_root / "manifest.json"
    chains_path = dataset_root / "chains.json"
    simple_chains_path = dataset_root / "chains_simple.json"
    manifest = read_json(manifest_path)
    chains = read_json(chains_path)
    simple_chains = read_json(simple_chains_path)
    require(isinstance(manifest, dict), "manifest.json must contain an object")
    require(isinstance(chains, list), "chains.json must contain an array")
    require(manifest.get("schema_version") == MANIFEST_SCHEMA_VERSION, "Manifest schema mismatch")
    require(
        manifest.get("status") in {"package_candidate_pending_release_qa", "released"},
        "Manifest is not a full package candidate or release",
    )
    counts = manifest.get("counts")
    require(isinstance(counts, dict), "Manifest counts are missing")
    if strict_first_batch:
        require(counts == {"videos": 640, "chains": 4000, "turns": 15000}, "First-batch counts mismatch")
    files = manifest.get("files")
    require(isinstance(files, dict), "Manifest files are missing")
    chains_record = files.get("chains.json")
    require(isinstance(chains_record, dict), "Manifest chains.json record is missing")
    require(chains_path.is_file(), "chains.json is missing")
    require(chains_path.stat().st_size == chains_record.get("bytes"), "chains.json byte count mismatch")
    chains_sha256 = sha256_file(chains_path)
    require(chains_sha256 == chains_record.get("sha256"), "chains.json SHA-256 mismatch")
    simple_chains_record = files.get("chains_simple.json")
    require(
        isinstance(simple_chains_record, dict),
        "Manifest chains_simple.json record is missing",
    )
    require(simple_chains_path.is_file(), "chains_simple.json is missing")
    require(
        simple_chains_path.stat().st_size == simple_chains_record.get("bytes"),
        "chains_simple.json byte count mismatch",
    )
    simple_chains_sha256 = sha256_file(simple_chains_path)
    require(
        simple_chains_sha256 == simple_chains_record.get("sha256"),
        "chains_simple.json SHA-256 mismatch",
    )
    video_records = files.get("videos")
    require(isinstance(video_records, list), "Manifest video records are missing")
    require(len(video_records) == counts.get("videos"), "Manifest video count mismatch")
    expected_paths = {f"videos/{index}.mp4" for index in range(1, len(video_records) + 1)}
    videos_dir = dataset_root / "videos"
    require(videos_dir.is_dir(), "videos directory is missing")
    actual_paths = {
        path.relative_to(dataset_root).as_posix()
        for path in videos_dir.glob("*.mp4")
        if path.is_file()
    }
    require(actual_paths == expected_paths, "Sequential video files are missing or unexpected")
    node_ids = [record.get("node_id") for record in video_records if isinstance(record, dict)]
    require(len(node_ids) == len(video_records), "Invalid video record")
    require(all(isinstance(node_id, str) and node_id for node_id in node_ids), "Missing video node ID")
    require(len(set(node_ids)) == len(node_ids), "Duplicate video node ID")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        verified_videos = list(
            executor.map(
                lambda item: verify_video_record(
                    dataset_root,
                    item[1],
                    item[0],
                    ffprobe_bin,
                ),
                enumerate(video_records, start=1),
            )
        )
    chain_summary = verify_chains(
        chains=chains,
        manifest=manifest,
        video_paths=expected_paths,
    )
    require(chain_summary["chains"] == counts.get("chains"), "Chain count mismatch")
    require(chain_summary["turns"] == counts.get("turns"), "Turn count mismatch")
    require(chain_summary["all_video_paths_referenced"], "Some packaged videos are not referenced")
    simple_chain_summary = verify_simple_chains(simple_chains, chains)
    require(
        simple_chain_summary["chains"] == counts.get("chains"),
        "Simplified chain count differs from manifest",
    )
    checks = manifest.get("checks")
    require(isinstance(checks, dict) and checks and all(checks.values()), "Builder checks are not all passed")
    ordered_hashes = "\n".join(
        f'{item["sha256"]}  {item["path"]}' for item in verified_videos
    ) + "\n"
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "passed",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "verification_scope": "package_only_no_render_sources",
        "dataset_root": str(dataset_root),
        "dataset_id": manifest.get("dataset_id"),
        "manifest_status": manifest.get("status"),
        "counts": {
            "videos": len(verified_videos),
            "chains": chain_summary["chains"],
            "turns": chain_summary["turns"],
            "referenced_videos": chain_summary["referenced_videos"],
        },
        "checks": {
            "manifest_schema_valid": True,
            "builder_checks_passed": True,
            "sequential_video_names": True,
            "all_video_bytes_match": True,
            "all_video_sha256_match": True,
            "all_video_media_specs_match": True,
            "chains_sha256_matches": True,
            "chains_simple_sha256_matches": True,
            "chain_and_turn_counts_match": True,
            "simple_chain_indices_sequential": True,
            "simple_chains_match_full_records": True,
            "all_turn_media_paths_resolve": True,
            "all_packaged_videos_are_referenced": True,
            "all_turns_bilingual": True,
            "all_turns_atomic": True,
            "no_internal_ids_in_prompt_text": True,
        },
        "hashes": {
            "manifest_json_sha256": sha256_file(manifest_path),
            "chains_json_sha256": chains_sha256,
            "chains_simple_json_sha256": simple_chains_sha256,
            "ordered_video_hash_list_sha256": sha256_text(ordered_hashes),
        },
        "media_contract": {
            "codec": sorted({item["probe"]["codec"] for item in verified_videos}),
            "resolutions": sorted(
                {f'{item["probe"]["width"]}x{item["probe"]["height"]}' for item in verified_videos}
            ),
            "fps": sorted({item["probe"]["fps"] for item in verified_videos}),
            "frames": sorted({item["probe"]["frames"] for item in verified_videos}),
        },
        "tooling": {
            "verifier": "00_engine/scripts/dataset/verify_first_batch_delivery_v1.py",
            "verifier_sha256": sha256_file(Path(__file__)),
            "ffprobe": ffprobe_bin,
            "workers": workers,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--ffprobe-bin", default="ffprobe")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--allow-nonproduction-counts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_root = args.dataset_root.resolve()
    if args.output_report is not None:
        output_report = args.output_report.resolve()
        if output_report == dataset_root or dataset_root in output_report.parents:
            raise SystemExit("ERROR: output report must be outside the immutable dataset root")
    try:
        report = verify_delivery(
            dataset_root=dataset_root,
            ffprobe_bin=args.ffprobe_bin,
            workers=args.workers,
            strict_first_batch=not args.allow_nonproduction_counts,
        )
    except VerificationError as exc:
        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "status": "failed",
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "verification_scope": "package_only_no_render_sources",
            "dataset_root": str(dataset_root),
            "error": str(exc),
        }
        if args.output_report is not None:
            write_json_atomic(args.output_report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    if args.output_report is not None:
        write_json_atomic(args.output_report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
