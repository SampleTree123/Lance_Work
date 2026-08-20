#!/usr/bin/env python3
"""Patch CC5 ASCII FBX auxiliary bone names to match the imported UE5 skeleton."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re


SOURCE_TO_TARGET = {
    "pelvis_0": "cc_base_pelvis",
    "l_forearmtwist01": "cc_base_l_forearmtwist01",
    "l_forearmtwist02": "cc_base_l_forearmtwist02",
    "l_elbowsharebone": "cc_base_l_elbowsharebone",
    "l_upperarmtwist01": "cc_base_l_upperarmtwist01",
    "l_upperarmtwist02": "cc_base_l_upperarmtwist02",
    "facialbone": "cc_base_facialbone",
    "jawroot": "cc_base_jawroot",
    "tongue01": "cc_base_tongue01",
    "tongue02": "cc_base_tongue02",
    "tongue03": "cc_base_tongue03",
    "teeth02": "cc_base_teeth02",
    "r_eye": "cc_base_r_eye",
    "l_eye": "cc_base_l_eye",
    "upperjaw": "cc_base_upperjaw",
    "teeth01": "cc_base_teeth01",
    "r_elbowsharebone": "cc_base_r_elbowsharebone",
    "r_forearmtwist01": "cc_base_r_forearmtwist01",
    "r_forearmtwist02": "cc_base_r_forearmtwist02",
    "r_upperarmtwist01": "cc_base_r_upperarmtwist01",
    "r_upperarmtwist02": "cc_base_r_upperarmtwist02",
    "l_ribstwist": "cc_base_l_ribstwist",
    "l_breast": "cc_base_l_breast",
    "r_ribstwist": "cc_base_r_ribstwist",
    "r_breast": "cc_base_r_breast",
    "l_toebasesharebone": "cc_base_l_toebasesharebone",
    "l_pinkytoe1": "cc_base_l_pinkytoe1",
    "l_ringtoe1": "cc_base_l_ringtoe1",
    "l_midtoe1": "cc_base_l_midtoe1",
    "l_indextoe1": "cc_base_l_indextoe1",
    "l_bigtoe1": "cc_base_l_bigtoe1",
    "l_calftwist01": "cc_base_l_calftwist01",
    "l_calftwist02": "cc_base_l_calftwist02",
    "l_kneesharebone": "cc_base_l_kneesharebone",
    "l_thightwist01": "cc_base_l_thightwist01",
    "l_thightwist02": "cc_base_l_thightwist02",
    "r_kneesharebone": "cc_base_r_kneesharebone",
    "r_bigtoe1": "cc_base_r_bigtoe1",
    "r_pinkytoe1": "cc_base_r_pinkytoe1",
    "r_ringtoe1": "cc_base_r_ringtoe1",
    "r_indextoe1": "cc_base_r_indextoe1",
    "r_midtoe1": "cc_base_r_midtoe1",
    "r_toebasesharebone": "cc_base_r_toebasesharebone",
    "r_calftwist01": "cc_base_r_calftwist01",
    "r_calftwist02": "cc_base_r_calftwist02",
    "r_thightwist01": "cc_base_r_thightwist01",
    "r_thightwist02": "cc_base_r_thightwist02",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def patch_fbx(source: Path, destination: Path, report_path: Path) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    report_path = report_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source == destination:
        raise ValueError("Destination must differ from source")

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        text = handle.read()
    if not text.startswith("; FBX"):
        raise ValueError(f"Source is not an ASCII FBX: {source}")

    boundary_prefix = r"(?<![A-Za-z0-9_])(?:"
    boundary_suffix = r")(?![A-Za-z0-9_])"
    source_pattern = re.compile(
        boundary_prefix
        + "|".join(
            re.escape(name)
            for name in sorted(SOURCE_TO_TARGET, key=len, reverse=True)
        )
        + boundary_suffix
    )
    target_pattern = re.compile(
        boundary_prefix
        + "|".join(
            re.escape(name)
            for name in sorted(
                SOURCE_TO_TARGET.values(), key=len, reverse=True
            )
        )
        + boundary_suffix
    )
    existing_target = target_pattern.search(text)
    if existing_target is not None:
        raise ValueError(
            "Target bone already exists before patch: "
            + existing_target.group(0)
        )

    counts = collections.Counter()

    def replace_source(match):
        source_name = match.group(0)
        counts[source_name] += 1
        return SOURCE_TO_TARGET[source_name]

    text = source_pattern.sub(replace_source, text)
    replacements = []
    for old_name, new_name in SOURCE_TO_TARGET.items():
        count = counts[old_name]
        if count <= 0:
            raise ValueError(f"Source bone is absent from ASCII FBX: {old_name}")
        replacements.append(
            {"source": old_name, "target": new_name, "count": count}
        )
    remaining = source_pattern.search(text)
    if remaining is not None:
        raise RuntimeError(
            "Source bone remains after patch: " + remaining.group(0)
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    report = {
        "destination": str(destination),
        "destination_bytes": destination.stat().st_size,
        "destination_sha256": sha256_file(destination),
        "mapping_count": len(replacements),
        "replacements": replacements,
        "source": str(source),
        "source_bytes": source.stat().st_size,
        "source_sha256": sha256_file(source),
        "success": True,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    args = parse_args()
    report = patch_fbx(args.source, args.destination, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
