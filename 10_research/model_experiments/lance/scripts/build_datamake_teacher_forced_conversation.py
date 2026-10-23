#!/usr/bin/env python3
"""Build a teacher-forced Lance inference conversation from one prefix row.

Prior assistant videos are the paired ground-truth intermediate endpoints. Only
the final user turn carries ``edit_video``, so inference evaluates exactly one
target round while preserving the same full dialogue/visual history layout used
by the DataMake training adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

import pyarrow.parquet as pq


SCHEMA_VERSION = "datamake_lance_teacher_forced_eval_v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_media(media_root: Path, relative: str) -> Path:
    value = Path(relative)
    if value.is_absolute():
        raise ValueError(f"parquet media paths must be relative, got {relative}")
    resolved = (media_root / value).resolve()
    try:
        resolved.relative_to(media_root.resolve())
    except ValueError as error:
        raise ValueError(f"media path escapes root: {relative}") from error
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved


def select_row(
    parquet_path: Path,
    sample_id: str | None,
    chain_id: str | None,
    target_round: int | None,
) -> Dict[str, Any]:
    rows = pq.read_table(parquet_path).to_pylist()
    if sample_id:
        matches = [row for row in rows if row["sample_id"] == sample_id]
    else:
        if not chain_id or target_round is None:
            raise ValueError("provide --sample-id, or both --chain-id and --target-round")
        matches = [
            row
            for row in rows
            if row["chain_id"] == chain_id and int(row["target_round"]) == target_round
        ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one matching parquet row, found {len(matches)}")
    row = matches[0]
    if row.get("prompt_view") != "dialogue":
        raise ValueError("teacher-forced evaluation requires a dialogue row")
    return row


def build_conversation(row: Dict[str, Any], media_root: Path) -> Dict[str, Any]:
    prompts = list(row["prompts"])
    videos = [resolve_media(media_root, value) for value in row["video_paths"]]
    if len(videos) != len(prompts) + 1:
        raise ValueError(
            f"expected one more video than prompts, got {len(videos)} and {len(prompts)}"
        )
    if int(row["target_round"]) != len(prompts):
        raise ValueError("target_round must equal dialogue prefix length")

    turns: List[Dict[str, Any]] = []
    for index, prompt in enumerate(prompts):
        user_content: List[Dict[str, str]] = []
        if index == 0:
            user_content.append({"type": "video", "value": str(videos[0])})
        user_content.append({"type": "text", "value": prompt})
        user_turn: Dict[str, Any] = {
            "role": "user",
            "content": user_content,
            "meta": {
                "sample_id": row["sample_id"],
                "chain_id": row["chain_id"],
                "round": index + 1,
            },
        }
        if index == len(prompts) - 1:
            user_turn["action"] = "edit_video"
            turns.append(user_turn)
        else:
            turns.append(user_turn)
            turns.append(
                {
                    "role": "assistant",
                    "content": [{"type": "video", "value": str(videos[index + 1])}],
                    "meta": {"teacher_forced_ground_truth_round": index + 1},
                }
            )
    return {"system_prompt": None, "turns": turns}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--sample-id")
    selection.add_argument("--chain-id")
    parser.add_argument("--target-round", type=int)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    parquet_path = args.parquet.resolve()
    media_root = args.media_root.resolve()
    row = select_row(
        parquet_path,
        sample_id=args.sample_id,
        chain_id=args.chain_id,
        target_round=args.target_round,
    )
    conversation = build_conversation(row, media_root)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(conversation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    target = resolve_media(media_root, row["output_video_path"])
    eval_manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_parquet": str(parquet_path),
        "source_parquet_sha256": sha256_file(parquet_path),
        "sample_id": row["sample_id"],
        "chain_id": row["chain_id"],
        "target_round": int(row["target_round"]),
        "context_length": int(row["context_length"]),
        "turn_ids": list(row["turn_ids"]),
        "edit_axes": list(row["edit_axes"]),
        "conversation": str(output),
        "conversation_sha256": sha256_file(output),
        "target_video": str(target),
        "target_video_sha256": sha256_file(target),
        "evaluation_mode": "teacher_forced_prior_assistant_endpoints_generate_final_target_only",
    }
    manifest_path = output.with_suffix(".evaluation.json")
    manifest_path.write_text(
        json.dumps(eval_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "conversation": str(output),
                "evaluation_manifest": str(manifest_path),
                "sample_id": row["sample_id"],
                "target_video": str(target),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
