"""Validate the copied Character Creator clothing date-filter result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_TARGET_ROOT = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5_2022plus_sorted"
)
DEFAULT_REPORT = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "clothing_date_reorganization"
    / "reorg_20260811_v1"
    / "validation.json"
)
V2_TARGET_ROOT = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5_newest50pct_sorted"
)
V2_REPORT = DEFAULT_REPORT.parent.parent / "reorg_20260811_v2_newest50" / "validation.json"


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def tree_files(path: Path) -> dict[str, Path]:
    return {
        item.relative_to(path).as_posix(): item
        for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() != ".zip"
    }


def validate_file(source: Path, destination: Path) -> tuple[list[str], int, int]:
    errors: list[str] = []
    if not destination.is_file():
        return [f"Missing destination file: {destination}"], 0, 0
    source_size = source.stat().st_size
    destination_size = destination.stat().st_size
    if source_size != destination_size:
        errors.append(
            f"File size mismatch: {source} ({source_size}) != "
            f"{destination} ({destination_size})"
        )
    elif sha256_file(source) != sha256_file(destination):
        errors.append(f"SHA-256 mismatch: {source} != {destination}")
    return errors, 1, destination_size


def validate_directory(
    source: Path, destination: Path
) -> tuple[list[str], int, int]:
    errors: list[str] = []
    if not destination.is_dir():
        return [f"Missing destination directory: {destination}"], 0, 0
    source_files = tree_files(source)
    destination_files = tree_files(destination)
    source_keys = set(source_files)
    destination_keys = set(destination_files)
    for relative in sorted(source_keys - destination_keys):
        errors.append(f"Missing copied file: {destination / relative}")
    for relative in sorted(destination_keys - source_keys):
        errors.append(f"Unexpected copied file: {destination / relative}")
    verified_count = 0
    verified_bytes = 0
    for relative in sorted(source_keys & destination_keys):
        source_file = source_files[relative]
        destination_file = destination_files[relative]
        source_size = source_file.stat().st_size
        destination_size = destination_file.stat().st_size
        if source_size != destination_size:
            errors.append(f"File size mismatch: {source_file} != {destination_file}")
            continue
        if sha256_file(source_file) != sha256_file(destination_file):
            errors.append(f"SHA-256 mismatch: {source_file} != {destination_file}")
            continue
        verified_count += 1
        verified_bytes += destination_size
    return errors, verified_count, verified_bytes


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def validate(target: Path) -> dict[str, Any]:
    target = target.resolve()
    copy_map_path = target / "COPY_MAP.json"
    rows = json.loads(copy_map_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected_files = {
        "COPY_MAP.json",
        "README.md",
    }
    optional_review_files = {"人工审查说明.md"}
    optional_review_files.update(path.name for path in target.glob("clothing_human_review_queue_*.csv"))
    expected_files.update(name for name in optional_review_files if (target / name).is_file())
    verified_files = 0
    verified_bytes = 0
    for index, row in enumerate(rows, start=1):
        source = Path(row["source"])
        destination = target / row["destination"]
        if source.is_file():
            package_errors, count, byte_count = validate_file(source, destination)
            expected_files.add(destination.relative_to(target).as_posix())
        elif source.is_dir():
            package_errors, count, byte_count = validate_directory(source, destination)
            for relative in tree_files(destination):
                expected_files.add((destination / relative).relative_to(target).as_posix())
        else:
            package_errors, count, byte_count = [f"Missing source: {source}"], 0, 0
        errors.extend(package_errors)
        verified_files += count
        verified_bytes += byte_count
        if index % 10 == 0 or index == len(rows):
            print(f"validated {index}/{len(rows)} packages", flush=True)

    actual_files = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file()
    }
    for relative in sorted(expected_files - actual_files):
        errors.append(f"Missing expected target file: {relative}")
    for relative in sorted(actual_files - expected_files):
        errors.append(f"Unexpected target file: {relative}")

    return {
        "schema_version": 1,
        "target_root": str(target),
        "success": not errors,
        "logical_package_count": len(rows),
        "verified_file_count": verified_files,
        "verified_bytes": verified_bytes,
        "actual_target_file_count": len(actual_files),
        "expected_target_file_count": len(expected_files),
        "error_count": len(errors),
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--profile", choices=("cutoff-v1", "newest50-v2"), default="cutoff-v1"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.profile == "newest50-v2":
        if args.target_root == DEFAULT_TARGET_ROOT:
            args.target_root = V2_TARGET_ROOT
        if args.report == DEFAULT_REPORT:
            args.report = V2_REPORT
    report = validate(args.target_root)
    write_json_atomic(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
