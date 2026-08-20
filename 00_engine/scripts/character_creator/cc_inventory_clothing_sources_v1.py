"""Build a read-only inventory of Character Creator clothing source packages.

The source roots may contain ZIP archives and already extracted CC assets. The
scanner never modifies either root and never extracts arbitrary archive files.
Only a small, bounded set of embedded preview images is copied to the output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_ROOT = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5"
)
DEFAULT_OUTPUT = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "clothing_source_inventory"
    / "inventory_20260811_v1"
)

ARCHIVE_EXTENSIONS = {".zip"}
PREVIEW_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
ASSET_CATEGORIES = {
    ".cccloth": "garment",
    ".ccshoes": "shoes",
    ".ccgloves": "gloves",
    ".ccacc": "accessory",
    ".iacc": "accessory",
    ".ccavatar": "character",
    ".iavatar": "character",
    ".ccproject": "character",
    ".rlhair": "hair",
    ".cchair": "hair",
    ".iprop": "prop",
    ".rlmotion": "motion",
    ".iimotion": "motion",
    ".imtlplus": "material",
    ".rlmtrl": "material",
    ".ccskin": "skin",
    ".ccavatarpreset": "avatar_preset",
}
METADATA_EXTENSIONS = {
    ".json",
    ".ini",
    ".txt",
    ".xml",
    ".csv",
    ".md",
    ".url",
    ".lnk",
    ".db",
    ".dat",
}
WEARABLE_CATEGORIES = {"garment", "shoes", "gloves"}
CHARACTER_CATEGORIES = {"character"}
MIN_PLAUSIBLE_WEARABLE_BYTES = 64 * 1024

SLOT_RULES = (
    (
        "full_body",
        (
            "full-body",
            "full body",
            "fullbody",
            "dress",
            "gown",
            "jumpsuit",
            "overall",
            "romper",
            "robe",
        ),
    ),
    (
        "outerwear",
        (
            "coat",
            "coats",
            "jacket",
            "blazer",
            "cloak",
            "cape",
            "overcoat",
        ),
    ),
    (
        "upper",
        (
            "shirt",
            "shirts",
            "t-shirt",
            "tshirt",
            "top",
            "tops",
            "blouse",
            "sweater",
            "hoodie",
            "vest",
        ),
    ),
    (
        "lower",
        (
            "pants",
            "pant",
            "trousers",
            "shorts",
            "skirt",
            "jeans",
            "leggings",
        ),
    ),
    (
        "underwear",
        ("underwear", "lingerie", "panties", "briefs", "bra"),
    ),
    ("socks", ("sock", "socks", "stocking", "stockings")),
)

STYLE_RULES = {
    "apocalypse_horror": (
        "apocalypse",
        "zombie",
        "undead",
        "horror",
        "\u4e27\u5c38",
    ),
    "historical_fantasy": (
        "ancient",
        "rome",
        "medieval",
        "viking",
        "fantasy",
        "warrior",
        "knight",
        "\u4e2d\u4e16\u7eaa",
        "\u53e4\u7f57\u9a6c",
    ),
    "uniform_tactical": (
        "soldier",
        "military",
        "special forces",
        "police",
        "firefighter",
        "uniform",
        "tactical",
        "\u519b",
        "\u6d88\u9632",
    ),
    "professional": (
        "business",
        "office",
        "professional",
        "formal",
        "suit",
        "\u804c\u4e1a",
        "\u529e\u516c",
    ),
    "sport": (
        "sport",
        "athletic",
        "fitness",
        "boxing",
        "gym",
        "\u8fd0\u52a8",
        "\u62f3\u51fb",
    ),
    "sleep_swim": (
        "pajama",
        "sleep",
        "bikini",
        "swim",
        "lingerie",
        "\u7761\u8863",
        "\u6cf3\u88c5",
    ),
    "casual_fashion": (
        "casual",
        "fashion",
        "street",
        "trendy",
        "chic",
        "jacket",
        "\u65f6\u5c1a",
        "\u4f11\u95f2",
    ),
}

LOCKED_LOOK_STYLES = {
    "apocalypse_horror",
    "historical_fantasy",
    "uniform_tactical",
}


class InventoryError(RuntimeError):
    pass


def utc_local_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def stable_package_id(sex: str, source_type: str, relative_path: str) -> str:
    stem = Path(relative_path).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "package"
    digest = hashlib.sha1(
        f"{sex}|{source_type}|{relative_path}".encode("utf-8")
    ).hexdigest()[:10]
    return f"{sex[:1]}-{source_type[:1]}-{stem[:42]}-{digest}"


def normalized_extension(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).suffix.lower()


def category_for(name: str) -> str:
    extension = normalized_extension(name)
    if extension in ASSET_CATEGORIES:
        return ASSET_CATEGORIES[extension]
    if extension in PREVIEW_EXTENSIONS:
        return "preview"
    if extension in METADATA_EXTENSIONS:
        return "metadata"
    return "other"


def infer_slot(name: str, category: str) -> str | None:
    if category == "shoes":
        return "footwear"
    if category == "gloves":
        return "gloves"
    if category != "garment":
        return None
    lowered = name.replace("\\", "/").lower()
    for slot, tokens in SLOT_RULES:
        if any(token in lowered for token in tokens):
            return slot
    return "other"


def infer_style_tags(label: str) -> list[str]:
    lowered = label.lower()
    return sorted(
        style
        for style, tokens in STYLE_RULES.items()
        if any(token in lowered for token in tokens)
    )


def classify_content(counts: Counter[str]) -> str:
    wearable = sum(counts[category] for category in WEARABLE_CATEGORIES)
    characters = sum(counts[category] for category in CHARACTER_CATEGORIES)
    accessories = counts["accessory"]
    if wearable and characters:
        return "clothing_with_character"
    if wearable:
        return "clothing_only"
    if characters:
        return "character_only"
    if accessories:
        return "accessory_only"
    if sum(counts.values()):
        return "mixed_nonclothing"
    return "empty_or_unknown"


def infer_modularity(
    content_class: str,
    slots: Iterable[str],
    style_tags: Iterable[str],
) -> tuple[str, str]:
    slot_set = set(slots)
    style_set = set(style_tags)
    if not content_class.startswith("clothing"):
        return "not_clothing", "not_applicable"
    if "full_body" in slot_set or style_set & LOCKED_LOOK_STYLES:
        return "full_body_or_locked", "locked_look_first"
    major = slot_set & {"outerwear", "upper", "lower", "footwear", "gloves"}
    if len(major) >= 2:
        return "multi_slot_candidate", "constrained_modular_candidate"
    if len(major) == 1:
        return "single_slot_candidate", "swap_group_candidate"
    return "unresolved_slot", "manual_classification_required"


def entry_record(name: str, size: int, crc: int | None = None) -> dict[str, Any]:
    category = category_for(name)
    record: dict[str, Any] = {
        "path": name.replace("\\", "/"),
        "name": PurePosixPath(name.replace("\\", "/")).name,
        "extension": normalized_extension(name),
        "bytes": int(size),
        "category": category,
    }
    slot = infer_slot(name, category)
    if slot:
        record["slot"] = slot
    if category in WEARABLE_CATEGORIES:
        record["payload_status"] = (
            "suspected_placeholder"
            if int(size) < MIN_PLAUSIBLE_WEARABLE_BYTES
            else "payload_present"
        )
    if crc is not None:
        record["crc32"] = f"{crc:08x}"
    return record


def content_fingerprint(entries: Iterable[dict[str, Any]]) -> str | None:
    normalized = sorted(
        "|".join(
            (
                str(entry.get("category", "")),
                str(entry.get("slot", "")),
                str(entry.get("name", "")).casefold(),
                str(entry.get("bytes", 0)),
            )
        )
        for entry in entries
        if entry.get("category") not in {"preview", "metadata", "other"}
    )
    if not normalized:
        return None
    return hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest()


def preview_score(name: str, size: int) -> tuple[int, int, str]:
    lowered = name.lower()
    score = 0
    for token, value in (
        ("preview", 100),
        ("thumbnail", 90),
        ("thumb", 80),
        ("cover", 70),
        ("sample", 65),
        ("icon", 45),
    ):
        if token in lowered:
            score += value
    for token in (
        "normal",
        "roughness",
        "metallic",
        "opacity",
        "diffuse",
        "albedo",
        "basecolor",
        "base_color",
        "ao.",
    ):
        if token in lowered:
            score -= 90
    return score, min(int(size), 50_000_000), lowered


def copy_archive_previews(
    archive: zipfile.ZipFile,
    package_id: str,
    output_dir: Path,
    max_previews: int,
    max_preview_bytes: int,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    candidates = [
        info
        for info in archive.infolist()
        if not info.is_dir()
        and normalized_extension(info.filename) in PREVIEW_EXTENSIONS
        and 0 < info.file_size <= max_preview_bytes
    ]
    candidates.sort(
        key=lambda info: preview_score(info.filename, info.file_size), reverse=True
    )
    copied: list[str] = []
    target_dir = output_dir / "previews" / package_id
    for index, info in enumerate(candidates[:max_previews], start=1):
        extension = normalized_extension(info.filename) or ".img"
        target = target_dir / f"preview_{index:02d}{extension}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
            copied.append(str(target.resolve()))
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            errors.append(f"{info.filename}: {exc}")
            target.unlink(missing_ok=True)
    return copied, errors


def copy_loose_previews(
    directory: Path,
    package_id: str,
    output_dir: Path,
    max_previews: int,
    max_preview_bytes: int,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in PREVIEW_EXTENSIONS
        and 0 < path.stat().st_size <= max_preview_bytes
    ]
    candidates.sort(
        key=lambda path: preview_score(path.name, path.stat().st_size), reverse=True
    )
    copied: list[str] = []
    target_dir = output_dir / "previews" / package_id
    for index, source in enumerate(candidates[:max_previews], start=1):
        target = target_dir / f"preview_{index:02d}{source.suffix.lower()}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied.append(str(target.resolve()))
        except OSError as exc:
            errors.append(f"{source}: {exc}")
            target.unlink(missing_ok=True)
    return copied, errors


def finalize_package(package: dict[str, Any]) -> dict[str, Any]:
    entries = package["entries"]
    counts = Counter(entry["category"] for entry in entries)
    wearable_entries = [
        entry for entry in entries if entry["category"] in WEARABLE_CATEGORIES
    ]
    suspected_placeholders = [
        entry
        for entry in wearable_entries
        if entry.get("payload_status") == "suspected_placeholder"
    ]
    usable_wearables = len(wearable_entries) - len(suspected_placeholders)
    if not wearable_entries:
        payload_gate = "not_applicable"
    elif not usable_wearables:
        payload_gate = "all_wearables_suspected_placeholders"
    elif suspected_placeholders:
        payload_gate = "mixed_payload_and_suspected_placeholders"
    else:
        payload_gate = "payload_present"
    slots = sorted(
        {entry["slot"] for entry in entries if entry.get("slot") is not None}
    )
    style_tags = infer_style_tags(
        package["label"] + " " + package.get("relative_path", "")
    )
    content_class = classify_content(counts)
    modularity, policy = infer_modularity(content_class, slots, style_tags)
    package.update(
        {
            "entry_count": len(entries),
            "asset_count": sum(
                count
                for category, count in counts.items()
                if category not in {"preview", "metadata", "other"}
            ),
            "wearable_count": sum(
                counts[category] for category in WEARABLE_CATEGORIES
            ),
            "usable_wearable_count": usable_wearables,
            "suspected_placeholder_count": len(suspected_placeholders),
            "payload_gate": payload_gate,
            "category_counts": dict(sorted(counts.items())),
            "slots": slots,
            "style_tags": style_tags,
            "content_class": content_class,
            "clothing_candidate": content_class.startswith("clothing"),
            "pilot_candidate": (
                content_class.startswith("clothing") and usable_wearables > 0
            ),
            "modularity_hint": modularity,
            "look_policy_hint": policy,
            "content_fingerprint": content_fingerprint(entries),
        }
    )
    return package


def scan_archive(
    path: Path,
    root: Path,
    sex: str,
    output_dir: Path,
    max_previews: int,
    max_preview_bytes: int,
) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    package_id = stable_package_id(sex, "zip", relative)
    package: dict[str, Any] = {
        "package_id": package_id,
        "label": path.stem,
        "sex_label": sex,
        "source_type": "zip",
        "source_path": str(path.resolve()),
        "relative_path": relative,
        "source_bytes": path.stat().st_size,
        "source_sha256": sha256_file(path),
        "archive_status": "readable",
        "entries": [],
        "preview_paths": [],
        "preview_errors": [],
    }
    try:
        with zipfile.ZipFile(path, "r") as archive:
            package["entries"] = [
                entry_record(info.filename, info.file_size, info.CRC)
                for info in archive.infolist()
                if not info.is_dir()
            ]
            previews, errors = copy_archive_previews(
                archive,
                package_id,
                output_dir,
                max_previews,
                max_preview_bytes,
            )
            package["preview_paths"] = previews
            package["preview_errors"] = errors
    except (OSError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as exc:
        package["archive_status"] = "unreadable"
        package["archive_error"] = str(exc)
    return finalize_package(package)


def scan_loose_directory(
    directory: Path,
    files: list[Path],
    root: Path,
    sex: str,
    output_dir: Path,
    max_previews: int,
    max_preview_bytes: int,
) -> dict[str, Any]:
    relative = directory.relative_to(root).as_posix() or "."
    package_id = stable_package_id(sex, "loose", relative)
    records = [
        entry_record(path.relative_to(directory).as_posix(), path.stat().st_size)
        for path in sorted(files, key=lambda item: item.name.casefold())
    ]
    previews, errors = copy_loose_previews(
        directory,
        package_id,
        output_dir,
        max_previews,
        max_preview_bytes,
    )
    package = {
        "package_id": package_id,
        "label": directory.name or root.name,
        "sex_label": sex,
        "source_type": "loose_directory",
        "source_path": str(directory.resolve()),
        "relative_path": relative,
        "source_bytes": sum(path.stat().st_size for path in files),
        "archive_status": "not_applicable",
        "entries": records,
        "preview_paths": previews,
        "preview_errors": errors,
    }
    return finalize_package(package)


def group_duplicates(
    packages: list[dict[str, Any]], key: str
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for package in packages:
        value = package.get(key)
        if value:
            grouped[str(value)].append(package)
    result = []
    for value, records in grouped.items():
        if len(records) < 2:
            continue
        result.append(
            {
                key: value,
                "count": len(records),
                "package_ids": sorted(record["package_id"] for record in records),
                "source_paths": sorted(record["source_path"] for record in records),
                "total_bytes": sum(int(record["source_bytes"]) for record in records),
            }
        )
    return sorted(result, key=lambda item: (-item["count"], item[key]))


def summarize_packages(packages: list[dict[str, Any]]) -> dict[str, Any]:
    category_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    source_type_counts: Counter[str] = Counter()
    sex_counts: Counter[str] = Counter()
    slot_counts: Counter[str] = Counter()
    archive_status_counts: Counter[str] = Counter()
    payload_gate_counts: Counter[str] = Counter()
    for package in packages:
        category_counts.update(package["category_counts"])
        class_counts[package["content_class"]] += 1
        source_type_counts[package["source_type"]] += 1
        sex_counts[package["sex_label"]] += 1
        slot_counts.update(package["slots"])
        archive_status_counts[package["archive_status"]] += 1
        payload_gate_counts[package["payload_gate"]] += 1
    return {
        "package_count": len(packages),
        "clothing_candidate_count": sum(
            bool(package["clothing_candidate"]) for package in packages
        ),
        "pilot_candidate_count": sum(
            bool(package["pilot_candidate"]) for package in packages
        ),
        "non_clothing_package_count": sum(
            not bool(package["clothing_candidate"]) for package in packages
        ),
        "package_bytes": sum(int(package["source_bytes"]) for package in packages),
        "entry_count": sum(int(package["entry_count"]) for package in packages),
        "wearable_count": sum(int(package["wearable_count"]) for package in packages),
        "usable_wearable_count": sum(
            int(package["usable_wearable_count"]) for package in packages
        ),
        "suspected_placeholder_count": sum(
            int(package["suspected_placeholder_count"]) for package in packages
        ),
        "preview_count": sum(len(package["preview_paths"]) for package in packages),
        "category_counts": dict(sorted(category_counts.items())),
        "content_class_counts": dict(sorted(class_counts.items())),
        "source_type_counts": dict(sorted(source_type_counts.items())),
        "sex_package_counts": dict(sorted(sex_counts.items())),
        "slot_package_counts": dict(sorted(slot_counts.items())),
        "archive_status_counts": dict(sorted(archive_status_counts.items())),
        "payload_gate_counts": dict(sorted(payload_gate_counts.items())),
    }


def validate_inventory(
    inventory: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    packages = inventory.get("packages") or []
    package_ids = [package.get("package_id") for package in packages]
    if len(package_ids) != len(set(package_ids)):
        errors.append("package_id values are not unique")
    if inventory.get("summary", {}).get("package_count") != len(packages):
        errors.append("summary.package_count does not match packages")

    output_dir = output_dir.resolve()
    for package in packages:
        prefix = str(package.get("package_id") or "unknown")
        source = Path(str(package.get("source_path", "")))
        if not source.exists():
            errors.append(f"{prefix}: source path is missing")
        if package.get("source_type") == "zip":
            digest = str(package.get("source_sha256") or "")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                errors.append(f"{prefix}: archive SHA-256 is missing or invalid")
            if package.get("archive_status") != "readable":
                errors.append(f"{prefix}: archive is not readable")
        for preview_value in package.get("preview_paths") or []:
            preview = Path(preview_value).resolve()
            if not preview.is_file():
                errors.append(f"{prefix}: copied preview is missing: {preview}")
            elif not preview.is_relative_to(output_dir):
                errors.append(f"{prefix}: preview escaped the output directory")

    archive_packages = [
        package for package in packages if package.get("source_type") == "zip"
    ]
    preview_packages = [
        package for package in packages if package.get("preview_paths")
    ]
    unresolved = [
        package
        for package in packages
        if package.get("look_policy_hint") == "manual_classification_required"
    ]
    all_placeholder = [
        package
        for package in packages
        if package.get("payload_gate") == "all_wearables_suspected_placeholders"
    ]
    if unresolved:
        warnings.append(
            f"{len(unresolved)} clothing packages still have unresolved garment slots"
        )
    if all_placeholder:
        warnings.append(
            f"{len(all_placeholder)} clothing packages contain only suspected "
            "placeholder wearable files and must not enter a CC pilot"
        )
    if len(preview_packages) < len(packages):
        warnings.append(
            f"{len(packages) - len(preview_packages)} packages require CC visual review "
            "because no package preview was copied"
        )
    return {
        "success": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checked_package_count": len(packages),
        "checked_archive_count": len(archive_packages),
        "readable_archive_count": sum(
            package.get("archive_status") == "readable"
            for package in archive_packages
        ),
        "unique_package_id_count": len(set(package_ids)),
        "package_with_preview_count": len(preview_packages),
    }


def build_inventory(
    roots: dict[str, Path],
    output_dir: Path,
    *,
    max_previews: int = 4,
    max_preview_bytes: int = 20 * 1024 * 1024,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    packages: list[dict[str, Any]] = []
    root_records: list[dict[str, Any]] = []

    for sex, raw_root in roots.items():
        root = raw_root.resolve()
        if not root.is_dir():
            raise InventoryError(f"Missing {sex} source root: {root}")
        all_files = sorted(
            (path for path in root.rglob("*") if path.is_file()),
            key=lambda item: item.as_posix().casefold(),
        )
        archives = [
            path for path in all_files if path.suffix.lower() in ARCHIVE_EXTENSIONS
        ]
        loose_assets = [
            path
            for path in all_files
            if path.suffix.lower() in ASSET_CATEGORIES
            or path.suffix.lower() in PREVIEW_EXTENSIONS
            or path.suffix.lower() in METADATA_EXTENSIONS
        ]
        loose_by_parent: dict[Path, list[Path]] = defaultdict(list)
        for path in loose_assets:
            if path.suffix.lower() in ARCHIVE_EXTENSIONS:
                continue
            loose_by_parent[path.parent].append(path)

        root_start = len(packages)
        for archive in archives:
            packages.append(
                scan_archive(
                    archive,
                    root,
                    sex,
                    output_dir,
                    max_previews,
                    max_preview_bytes,
                )
            )
        for directory, files in sorted(
            loose_by_parent.items(), key=lambda item: item[0].as_posix().casefold()
        ):
            if not any(
                path.suffix.lower() in ASSET_CATEGORIES for path in files
            ):
                continue
            packages.append(
                scan_loose_directory(
                    directory,
                    files,
                    root,
                    sex,
                    output_dir,
                    max_previews,
                    max_preview_bytes,
                )
            )
        root_packages = packages[root_start:]
        root_records.append(
            {
                "sex_label": sex,
                "root": str(root),
                "physical_file_count": len(all_files),
                "physical_bytes": sum(path.stat().st_size for path in all_files),
                "archive_count": len(archives),
                "loose_package_count": sum(
                    package["source_type"] == "loose_directory"
                    for package in root_packages
                ),
                "inventory_package_count": len(root_packages),
                "clothing_candidate_count": sum(
                    package["clothing_candidate"] for package in root_packages
                ),
            }
        )

    packages.sort(
        key=lambda package: (
            package["sex_label"],
            package["source_type"],
            package["relative_path"].casefold(),
        )
    )
    archive_duplicates = group_duplicates(packages, "source_sha256")
    content_duplicates = group_duplicates(packages, "content_fingerprint")
    inventory = {
        "schema_version": 1,
        "inventory_id": "cc_clothing_source_inventory_20260811_v1",
        "generated_at": utc_local_timestamp(),
        "status": "source_discovery_complete_visual_review_pending",
        "read_only_source_scan": True,
        "classification_notes": {
            "sex_label": (
                "Inherited from the user-provided female/male source root; it is "
                "not a machine-verified garment fit result."
            ),
            "content_class": (
                "Derived from archive members or loose CC file extensions, not "
                "from the package or folder name."
            ),
            "look_policy_hint": (
                "A triage hint only. Every production Look still requires CC "
                "static and dynamic visual validation."
            ),
            "payload_gate": (
                "Wearable files smaller than 64 KiB are retained in the source "
                "inventory but marked as suspected placeholders. Packages with "
                "only such files are not pilot candidates."
            ),
            "loose_package_boundary": (
                "Each immediate directory containing CC assets is preserved as "
                "one source package to avoid false merges."
            ),
        },
        "source_roots": root_records,
        "summary": summarize_packages(packages),
        "duplicate_archive_groups": archive_duplicates,
        "duplicate_content_groups": content_duplicates,
        "packages": packages,
    }
    inventory["validation"] = validate_inventory(inventory, output_dir)
    write_json_atomic(output_dir / "inventory.json", inventory)
    if not inventory["validation"]["success"]:
        raise InventoryError(
            "Inventory validation failed: "
            + "; ".join(inventory["validation"]["errors"][:5])
        )
    return inventory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory CC clothing archives and loose source assets"
    )
    parser.add_argument(
        "--female-root", type=Path, default=DEFAULT_SOURCE_ROOT / "female"
    )
    parser.add_argument(
        "--male-root", type=Path, default=DEFAULT_SOURCE_ROOT / "male"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-previews", type=int, default=4)
    parser.add_argument(
        "--max-preview-mib",
        type=int,
        default=20,
        help="Maximum bytes per copied preview image, in MiB",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(
        {"female": args.female_root, "male": args.male_root},
        args.output_dir,
        max_previews=max(0, args.max_previews),
        max_preview_bytes=max(1, args.max_preview_mib) * 1024 * 1024,
    )
    summary = inventory["summary"]
    print((args.output_dir.resolve() / "inventory.json"))
    print(
        "packages={package_count} clothing={clothing_candidate_count} "
        "non_clothing={non_clothing_package_count} wearables={wearable_count} "
        "previews={preview_count}".format(**summary)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
