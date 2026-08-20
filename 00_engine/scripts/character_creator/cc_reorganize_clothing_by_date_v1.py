"""Classify Character Creator clothing packages by embedded asset date.

The source library is never modified. By default this command only writes a
manifest under the Lance workspace. Passing ``--execute`` copies one canonical
representation of every logical package into a new, atomically published tree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import zlib
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_ROOT = Path("D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5")
DEFAULT_TARGET_ROOT = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5_2022plus_sorted"
)
DEFAULT_NEWEST_HALF_TARGET_ROOT = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5_newest50pct_sorted"
)
DEFAULT_MANIFEST_DIR = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "clothing_date_reorganization"
    / "reorg_20260811_v1"
)
DEFAULT_NEWEST_HALF_MANIFEST_DIR = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "clothing_date_reorganization"
    / "reorg_20260811_v2_newest50"
)

CUTOFF = datetime(2022, 1, 1)
DEFAULT_OR_SENTINEL_YEAR = 1980
POLICY_CUTOFF = "cutoff-2022"
POLICY_NEWEST_HALF = "newest-half-per-sex"

# Dates are evaluated only for files that can materially affect a CC character.
# Preview images, readmes, installers, and download metadata are deliberately
# excluded because their dates say nothing useful about garment generation.
CC_ASSET_EXTENSIONS = {
    ".ccacc",
    ".ccavatar",
    ".ccavatarpreset",
    ".cccloth",
    ".ccfacialprofile",
    ".ccgloves",
    ".cchair",
    ".ccmaterial",
    ".ccmixerpackage",
    ".ccmixerpreset",
    ".ccproject",
    ".ccshoes",
    ".ccskin",
    ".ccslider",
    ".iacc",
    ".iavatar",
    ".icloth",
    ".igloves",
    ".iimotion",
    ".imotion",
    ".imtlplus",
    ".iprop",
    ".ishoes",
    ".rlhair",
    ".rlmotion",
    ".rlmtrl",
    ".rlpose",
}

TEMPLATE_MARKERS = re.compile(
    r"^(character creator [345] template|reallusion (custom|templates))$",
    re.IGNORECASE,
)
GENERIC_FIRST_LEVEL = {
    "3\u670d\u88c5",
    "\u670d\u88c5",
    "\u66f4\u65b01",
    "\u7537\u88c5\u5408\u96c6",
    "\u7537\u58eb\u670d\u88c5+\u5e3d\u5b50",
}
GENERIC_SECOND_LEVEL = {"\u5185\u8863", "\u670d\u88c5"}


class ReorganizationError(RuntimeError):
    pass


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def normalized_extension(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).suffix.lower()


def is_cc_asset(name: str) -> bool:
    return normalized_extension(name) in CC_ASSET_EXTENSIONS


def safe_datetime(parts: tuple[int, int, int, int, int, int]) -> datetime | None:
    try:
        return datetime(*parts)
    except (TypeError, ValueError, OverflowError):
        return None


def date_record(value: datetime | None, *, loose_file: bool = False) -> dict[str, Any]:
    if value is None or value.year <= DEFAULT_OR_SENTINEL_YEAR:
        return {"value": None, "status": "unknown_or_default"}
    if loose_file and value.year >= datetime.now().year:
        # Current-year loose timestamps can be rewritten by download, extraction,
        # migration, or copying. Unlike ZIP member dates, they are not adequate
        # evidence that the asset itself was authored this year.
        return {"value": None, "status": "unknown_current_year_filesystem_time"}
    return {"value": value.isoformat(timespec="seconds"), "status": "valid"}


def crc32_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    value = 0
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            value = zlib.crc32(chunk, value)
    return f"{value & 0xFFFFFFFF:08x}"


def normalize_payload_path(name: str) -> str:
    parts = [part for part in name.replace("\\", "/").split("/") if part]
    lowered = [part.casefold() for part in parts]
    for index, part in enumerate(parts):
        if TEMPLATE_MARKERS.match(part):
            return "/".join(lowered[index:])
    content_roots = {
        "accessory",
        "actor",
        "avatar preset",
        "cloth",
        "hair",
        "materialplus",
        "motion",
        "project",
        "prop",
        "skin",
    }
    for index, part in enumerate(lowered):
        if part in content_roots:
            return "/".join(lowered[index:])
    # Old packs often contain only a product folder and the asset file. Keeping
    # the final two components removes arbitrary download wrapper directories.
    return "/".join(lowered[-2:])


def payload_fingerprint(entries: Iterable[dict[str, Any]]) -> str | None:
    rows = sorted(
        "|".join(
            (
                str(entry["normalized_path"]),
                str(entry["bytes"]),
                str(entry["crc32"]),
            )
        )
        for entry in entries
    )
    if not rows:
        return None
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def classify_dates(entries: list[dict[str, Any]]) -> tuple[str, str]:
    valid = [
        datetime.fromisoformat(entry["asset_date"])
        for entry in entries
        if entry.get("asset_date")
    ]
    unknown_count = sum(not entry.get("asset_date") for entry in entries)
    if any(value < CUTOFF for value in valid):
        return "outdated", "at_least_one_cc_asset_before_2022"
    if not valid or unknown_count:
        return "date_unknown", "missing_or_default_cc_asset_date"
    return "accepted", "all_cc_assets_are_2022_or_newer"


def package_summary(
    *,
    package_id: str,
    sex: str,
    source_type: str,
    source_path: Path,
    relative_path: str,
    entries: list[dict[str, Any]],
    source_bytes: int,
) -> dict[str, Any]:
    classification, reason = classify_dates(entries)
    dates = sorted(entry["asset_date"] for entry in entries if entry["asset_date"])
    return {
        "package_id": package_id,
        "label": source_path.stem if source_type == "zip" else source_path.name,
        "sex_source": sex,
        "source_type": source_type,
        "source_path": str(source_path.resolve()),
        "relative_path": relative_path,
        "source_bytes": source_bytes,
        "cc_asset_count": len(entries),
        "unknown_date_count": sum(not entry["asset_date"] for entry in entries),
        "earliest_asset_date": dates[0] if dates else None,
        "latest_asset_date": dates[-1] if dates else None,
        "classification": classification,
        "classification_reason": reason,
        "payload_fingerprint": payload_fingerprint(entries),
        "entries": entries,
    }


def stable_package_id(sex: str, source_type: str, relative_path: str) -> str:
    digest = hashlib.sha1(
        f"{sex}|{source_type}|{relative_path}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{sex[0]}-{source_type[0]}-{digest}"


def scan_archive(path: Path, root: Path, sex: str) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    entries: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for info in archive.infolist():
                if info.is_dir() or not is_cc_asset(info.filename):
                    continue
                timestamp = date_record(safe_datetime(info.date_time))
                entries.append(
                    {
                        "path": info.filename.replace("\\", "/"),
                        "normalized_path": normalize_payload_path(info.filename),
                        "bytes": info.file_size,
                        "crc32": f"{info.CRC:08x}",
                        "asset_date": timestamp["value"],
                        "date_status": timestamp["status"],
                    }
                )
    except (OSError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as exc:
        entries = []
        archive_error = str(exc)
    else:
        archive_error = None
    package = package_summary(
        package_id=stable_package_id(sex, "zip", relative),
        sex=sex,
        source_type="zip",
        source_path=path,
        relative_path=relative,
        entries=entries,
        source_bytes=path.stat().st_size,
    )
    package["archive_error"] = archive_error
    if archive_error:
        package["classification"] = "date_unknown"
        package["classification_reason"] = "archive_unreadable"
    return package


def inferred_loose_root(path: Path, root: Path) -> Path:
    relative = path.relative_to(root)
    parts = relative.parts
    for index, part in enumerate(parts[:-1]):
        if TEMPLATE_MARKERS.match(part):
            return root.joinpath(*parts[:index])
    if not parts:
        return path.parent
    if parts[0] in GENERIC_FIRST_LEVEL:
        depth = 2
        if len(parts) > 2 and parts[1] in GENERIC_SECOND_LEVEL:
            depth = 3
        return root.joinpath(*parts[: min(depth, len(parts) - 1)])
    return root / parts[0]


def directory_bytes(path: Path) -> int:
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() != ".zip"
    )


def discover_loose_roots(root: Path, archives: list[Path]) -> list[Path]:
    shadow_roots = {
        archive.with_suffix("").resolve()
        for archive in archives
        if archive.with_suffix("").is_dir()
    }
    candidates: set[Path] = set()
    for path in root.rglob("*"):
        if not path.is_file() or not is_cc_asset(path.name):
            continue
        resolved = path.resolve()
        if any(shadow == resolved or shadow in resolved.parents for shadow in shadow_roots):
            continue
        candidates.add(inferred_loose_root(path, root).resolve())

    # A product root must not be emitted twice. If heuristics yield nested roots,
    # retain the ancestor because it preserves the complete product payload.
    roots: list[Path] = []
    for candidate in sorted(candidates, key=lambda item: (len(item.parts), str(item))):
        if any(parent == candidate or parent in candidate.parents for parent in roots):
            continue
        roots.append(candidate)
    return roots


def scan_loose_package(path: Path, root: Path, sex: str) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    entries: list[dict[str, Any]] = []
    for asset in sorted(path.rglob("*"), key=lambda item: str(item).casefold()):
        if not asset.is_file() or asset.suffix.lower() == ".zip" or not is_cc_asset(asset.name):
            continue
        timestamp = date_record(
            datetime.fromtimestamp(asset.stat().st_mtime), loose_file=True
        )
        rel_asset = asset.relative_to(path).as_posix()
        entries.append(
            {
                "path": rel_asset,
                "normalized_path": normalize_payload_path(rel_asset),
                "bytes": asset.stat().st_size,
                "crc32": crc32_file(asset),
                "asset_date": timestamp["value"],
                "date_status": timestamp["status"],
            }
        )
    return package_summary(
        package_id=stable_package_id(sex, "loose", relative),
        sex=sex,
        source_type="loose_directory",
        source_path=path,
        relative_path=relative,
        entries=entries,
        source_bytes=directory_bytes(path),
    )


def scan_sources(source_root: Path) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for sex in ("female", "male"):
        root = (source_root / sex).resolve()
        if not root.is_dir():
            raise ReorganizationError(f"Missing source root: {root}")
        archives = sorted(root.rglob("*.zip"), key=lambda item: str(item).casefold())
        packages.extend(scan_archive(path, root, sex) for path in archives)
        packages.extend(
            scan_loose_package(path, root, sex)
            for path in discover_loose_roots(root, archives)
        )
    return packages


def merge_duplicate_packages(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    singles: list[dict[str, Any]] = []
    for package in packages:
        fingerprint = package.get("payload_fingerprint")
        if fingerprint:
            grouped[fingerprint].append(package)
        else:
            singles.append(package)

    logical: list[dict[str, Any]] = []
    for fingerprint, records in grouped.items():
        records.sort(
            key=lambda item: (
                item["source_type"] != "zip",
                item["source_bytes"],
                item["source_path"].casefold(),
            )
        )
        representative = dict(records[0])
        source_sexes = sorted({record["sex_source"] for record in records})
        classifications = {record["classification"] for record in records}
        if "outdated" in classifications:
            classification = "outdated"
            reason = "duplicate_group_contains_pre_2022_asset_date"
        elif "date_unknown" in classifications:
            classification = "date_unknown"
            reason = "duplicate_group_contains_unknown_asset_date"
        else:
            classification = "accepted"
            reason = "all_duplicate_sources_are_2022_or_newer"
        representative.update(
            {
                "logical_sex": "both" if len(source_sexes) > 1 else source_sexes[0],
                "classification": classification,
                "classification_reason": reason,
                "duplicate_source_count": len(records),
                "duplicate_sources": [
                    {
                        "package_id": record["package_id"],
                        "sex_source": record["sex_source"],
                        "source_path": record["source_path"],
                        "classification": record["classification"],
                    }
                    for record in records
                ],
            }
        )
        logical.append(representative)

    for package in singles:
        record = dict(package)
        record.update(
            {
                "logical_sex": package["sex_source"],
                "duplicate_source_count": 1,
                "duplicate_sources": [
                    {
                        "package_id": package["package_id"],
                        "sex_source": package["sex_source"],
                        "source_path": package["source_path"],
                        "classification": package["classification"],
                    }
                ],
            }
        )
        logical.append(record)
    logical.sort(key=lambda item: (item["logical_sex"], item["label"].casefold()))
    return logical


def apply_policy(
    logical: list[dict[str, Any]], policy: str
) -> dict[str, dict[str, Any]]:
    if policy == POLICY_CUTOFF:
        return {}
    if policy != POLICY_NEWEST_HALF:
        raise ReorganizationError(f"Unknown classification policy: {policy}")

    boundaries: dict[str, dict[str, Any]] = {}
    for sex in ("female", "male", "both"):
        candidates = [
            package
            for package in logical
            if package["logical_sex"] == sex
            and package.get("earliest_asset_date")
            and not package.get("unknown_date_count")
        ]
        candidates.sort(
            key=lambda package: (
                datetime.fromisoformat(package["earliest_asset_date"]),
                package["label"].casefold(),
            ),
            reverse=True,
        )
        target_count = math.ceil(len(candidates) / 2)
        boundary = (
            datetime.fromisoformat(candidates[target_count - 1]["earliest_asset_date"])
            if target_count
            else None
        )
        accepted_count = 0
        for package in logical:
            if package["logical_sex"] != sex:
                continue
            if not package.get("earliest_asset_date") or package.get("unknown_date_count"):
                package["classification"] = "date_unknown"
                package["classification_reason"] = (
                    "excluded_from_percentile_due_to_unknown_asset_date"
                )
                continue
            package_date = datetime.fromisoformat(package["earliest_asset_date"])
            if boundary is not None and package_date >= boundary:
                package["classification"] = "accepted"
                package["classification_reason"] = (
                    "package_is_in_newest_half_for_logical_sex"
                )
                accepted_count += 1
            else:
                package["classification"] = "older_half"
                package["classification_reason"] = (
                    "package_is_in_older_half_for_logical_sex"
                )
        boundaries[sex] = {
            "known_date_package_count": len(candidates),
            "target_count_before_boundary_ties": target_count,
            "accepted_count_after_boundary_ties": accepted_count,
            "boundary_earliest_asset_date": (
                boundary.isoformat(timespec="seconds") if boundary else None
            ),
        }
    return boundaries


def destination_directory(stage: Path, package: dict[str, Any]) -> Path:
    base = stage / package["logical_sex"]
    if package["classification"] == "outdated":
        return base / "_outdated"
    if package["classification"] == "older_half":
        return base / "_older_half"
    if package["classification"] == "date_unknown":
        return base / "_date_unknown"
    return base


def unique_destination(parent: Path, source: Path, package_id: str) -> Path:
    destination = parent / source.name
    if not destination.exists():
        return destination
    if source.is_file():
        return parent / f"{source.stem}__{package_id}{source.suffix}"
    return parent / f"{source.name}__{package_id}"


def ignore_archives(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name.lower().endswith(".zip")}


def copy_packages(logical: list[dict[str, Any]], target: Path) -> None:
    target = target.resolve()
    stage = target.with_name(target.name + "__building")
    if target.exists():
        raise ReorganizationError(f"Target already exists: {target}")
    if stage.exists():
        raise ReorganizationError(f"Staging directory already exists: {stage}")
    for sex in ("male", "female", "both"):
        (stage / sex / "_outdated").mkdir(parents=True, exist_ok=True)
        (stage / sex / "_older_half").mkdir(parents=True, exist_ok=True)
        (stage / sex / "_date_unknown").mkdir(parents=True, exist_ok=True)

    copy_records: list[dict[str, str]] = []
    for package in logical:
        source = Path(package["source_path"])
        parent = destination_directory(stage, package)
        destination = unique_destination(parent, source, package["package_id"])
        if source.is_file():
            shutil.copy2(source, destination)
        else:
            shutil.copytree(source, destination, ignore=ignore_archives)
        copy_records.append(
            {
                "package_id": package["package_id"],
                "source": str(source),
                "destination": str(destination.relative_to(stage)),
            }
        )

    write_json_atomic(stage / "COPY_MAP.json", copy_records)
    (stage / "README.md").write_text(
        "# Character Creator clothing date filter\n\n"
        "Cutoff: 2022-01-01. Original source was not modified.\n\n"
        "- Packages directly under `male`, `female`, or `both` passed the date gate.\n"
        "- `_outdated` contains packages with at least one CC asset dated before 2022.\n"
        "- `_older_half` contains packages outside the newest half when percentile policy is used.\n"
        "- `_date_unknown` contains unreadable, missing, or default/sentinel dates.\n"
        "- `both` contains one canonical copy of payload-identical male/female packages.\n",
        encoding="utf-8",
    )
    os.replace(stage, target)


def summarize(packages: list[dict[str, Any]], logical: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, int] = defaultdict(int)
    by_sex: dict[str, int] = defaultdict(int)
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for package in logical:
        by_class[package["classification"]] += 1
        by_sex[package["logical_sex"]] += 1
        matrix[package["logical_sex"]][package["classification"]] += 1
    return {
        "physical_package_count": len(packages),
        "logical_package_count": len(logical),
        "duplicate_source_count_removed": len(packages) - len(logical),
        "logical_counts_by_classification": dict(sorted(by_class.items())),
        "logical_counts_by_sex": dict(sorted(by_sex.items())),
        "logical_matrix": {
            sex: dict(sorted(values.items())) for sex, values in sorted(matrix.items())
        },
        "estimated_copy_bytes": sum(int(package["source_bytes"]) for package in logical),
    }


def write_csv(path: Path, packages: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "package_id",
        "label",
        "logical_sex",
        "classification",
        "classification_reason",
        "source_type",
        "source_path",
        "cc_asset_count",
        "earliest_asset_date",
        "latest_asset_date",
        "unknown_date_count",
        "duplicate_source_count",
        "source_bytes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(packages)


def build_manifest(
    source: Path, target: Path, execute: bool, policy: str = POLICY_CUTOFF
) -> dict[str, Any]:
    packages = scan_sources(source.resolve())
    logical = merge_duplicate_packages(packages)
    policy_boundaries = apply_policy(logical, policy)
    return {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_root": str(source.resolve()),
        "target_root": str(target.resolve()),
        "cutoff": CUTOFF.date().isoformat(),
        "classification_policy": policy,
        "policy_boundaries": policy_boundaries,
        "execution_requested": execute,
        "source_preservation": "copy_only_original_source_unchanged",
        "date_semantics": "ZIP member or loose file last-modified time",
        "summary": summarize(packages, logical),
        "logical_packages": logical,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument(
        "--policy",
        choices=(POLICY_CUTOFF, POLICY_NEWEST_HALF),
        default=POLICY_CUTOFF,
    )
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.policy == POLICY_NEWEST_HALF:
        if args.target_root == DEFAULT_TARGET_ROOT:
            args.target_root = DEFAULT_NEWEST_HALF_TARGET_ROOT
        if args.manifest_dir == DEFAULT_MANIFEST_DIR:
            args.manifest_dir = DEFAULT_NEWEST_HALF_MANIFEST_DIR
    manifest = build_manifest(
        args.source_root, args.target_root, args.execute, args.policy
    )
    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(args.manifest_dir / "manifest.json", manifest)
    write_csv(args.manifest_dir / "packages.csv", manifest["logical_packages"])
    if args.execute:
        copy_packages(manifest["logical_packages"], args.target_root)
        manifest["execution_completed"] = True
        write_json_atomic(args.manifest_dir / "manifest.json", manifest)
    print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
