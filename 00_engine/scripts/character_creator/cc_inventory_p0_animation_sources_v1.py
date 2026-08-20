"""Build a read-only static inventory of the RM-09 P0 animation sources.

The scanner lists ZIP and RAR members without extracting them. Dependency and
semantic labels are filename-only review hints; no motion is production-approved
by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_ROOT = Path(
    "D:/BaiduNetdiskDownload/iclone\u52a8\u4f5c/P0_Core_Everyday"
)
DEFAULT_OUTPUT = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_source_inventory"
    / "p0_20260817_v3"
)
DEFAULT_UNRAR_CANDIDATES = (
    Path("C:/Program Files/WinRAR/UnRAR.exe"),
    Path("C:/Program Files/WinRAR/unrar.exe"),
)

ARCHIVE_EXTENSIONS = {".zip", ".rar"}
MOTION_EXTENSIONS = {
    ".rlmotion",
    ".imotion",
    ".imotionplus",
    ".iimotion",
    ".iimotionplus",
}

PROP_RULES = {
    "phone": r"phone|selfie|phubbing|calling|mobile",
    "drinkware": r"coffee|cup|mug|drink|bottle|glass",
    "food_tableware": r"dish|dishes|plate|tray|fork|spoon|meal",
    "bag_luggage": r"shopping.?bag|handbag|purse|bag|luggage|suitcase",
    "box_package": r"box|package|parcel",
    "computer_device": r"laptop|tablet|computer|keyboard",
    "camera": r"dslr|camera|photo_",
    "reading_writing": r"book|newspaper|magazine|paper|pen|clipboard",
    "household_tool": r"broom|mop|vacuum|towel|remote",
    "generic_held_item": r"hold.?item|carry.?item",
    "shopping_equipment": r"basket|cart",
    "payment_item": r"cash|checkout|receipt|wallet|credit.?card",
    "umbrella": r"umbrella",
}

SCENE_RULES = {
    "seating": r"sit(?:ting)?|seat(?:ed)?|chair|dining",
    "furniture_surface": r"desk|table|drawer|sofa|couch|bed|lay.?down",
    "floor_contact": r"floor",
    "leaning_support": r"lean(?:ing)?",
    "transit_contact": r"handrail|stanchion|carriage|platform",
    "home_environment": (
        r"home.?life|kitchen|living.?room|bathroom|microwave|door|mirror|"
        r"iron.?clothes"
    ),
    "workplace_environment": r"office.?work|meeting|concall|minutes.?taker",
    "retail_environment": (
        r"shopping|department.?store|grocery.?store|market_|shop_|"
        r"window.?shopping|try.?on"
    ),
}

PAIRED_RULES = {
    "explicit_interaction": r"interaction",
    "physical_partner": (
        r"greet.?friend|be.?fed|hold.?hand|handshake|hug|high.?five|"
        r"kiss|pat.?shoulder|arm.?in.?arm|couple"
    ),
}

PARTNER_CONTEXT_RULES = {
    "conversation_context": r"chat|talk|discuss|argument|listen|conversation",
    "social_context": r"greeting|social|colleague|audience",
}

SEMANTIC_RULES = {
    "locomotion": r"walk|jog|run|coming.?through|commute",
    "idle_pose": r"idle|waiting|stand.?idle",
    "conversation": r"chat|talk|discuss|argument|listen|greet|social",
    "gesture_signal": r"signal|halt|freeze|point|gesture|wave|hello",
    "seated_floor": r"sit|seat|dining|floor",
    "daily_task": r"kitchen|shopping|office|work|drawer|clean|carry|meal",
    "exercise_dance": r"stretch|catch.?breath|cooldown|dance|sports?",
    "transit": r"carriage|platform|commute|travel|station",
}


class InventoryError(RuntimeError):
    pass


def local_timestamp() -> str:
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
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, value: str) -> str:
    label = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or prefix
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{label[:42]}-{digest}"


def normalized_member_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("/")


def normalized_extension(value: str) -> str:
    return PurePosixPath(normalized_member_path(value)).suffix.lower()


def decode_process_output(data: bytes) -> str:
    candidates = ["utf-8-sig", locale.getpreferredencoding(False), "cp936"]
    for encoding in dict.fromkeys(candidates):
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def resolve_unrar(explicit: Path | None = None) -> Path | None:
    if explicit:
        resolved = explicit.expanduser().resolve()
        return resolved if resolved.is_file() else None
    command = shutil.which("unrar")
    if command:
        return Path(command).resolve()
    for candidate in DEFAULT_UNRAR_CANDIDATES:
        if candidate.is_file():
            return candidate.resolve()
    return None


def list_zip_members(path: Path) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            members.append(
                {
                    "path": normalized_member_path(item.filename),
                    "size": item.file_size,
                    "crc32": f"{item.CRC:08x}",
                }
            )
    return members


def list_rar_members(path: Path, unrar_path: Path | None) -> list[dict[str, Any]]:
    if not unrar_path:
        raise InventoryError(f"UnRAR is required to list RAR archive: {path}")
    completed = subprocess.run(
        [str(unrar_path), "lb", "-p-", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        error = decode_process_output(completed.stderr).strip()
        raise InventoryError(
            f"UnRAR failed with code {completed.returncode}: {path}: {error}"
        )
    names = [
        normalized_member_path(line.strip())
        for line in decode_process_output(completed.stdout).splitlines()
        if line.strip()
    ]
    return [{"path": name, "size": None, "crc32": None} for name in names]


def list_archive_members(
    path: Path, unrar_path: Path | None
) -> list[dict[str, Any]]:
    extension = path.suffix.lower()
    if extension == ".zip":
        return list_zip_members(path)
    if extension == ".rar":
        return list_rar_members(path, unrar_path)
    raise InventoryError(f"Unsupported archive extension: {path}")


def matching_rules(text: str, rules: dict[str, str]) -> list[str]:
    return [name for name, pattern in rules.items() if re.search(pattern, text)]


def infer_sex_hint(member_path: str, package_name: str) -> str:
    text = normalized_member_path(member_path).lower()
    stem = PurePosixPath(text).stem
    package = package_name.lower()
    female = bool(
        re.search(r"(?:^|[_\- ])f(?:\d+)?(?:$|[_\- ])", stem)
        or re.search(r"\bfemale\b", text)
        or "female casual" in package
    )
    male = bool(
        re.search(r"(?:^|[_\- ])m(?:\d+)?(?:$|[_\- ])", stem)
        or re.search(r"\bmale\b", text)
    )
    if female and male:
        return "mixed_or_paired"
    if female:
        return "female"
    if male:
        return "male"
    return "unknown"


def infer_motion_hints(member_path: str) -> dict[str, Any]:
    text = normalized_member_path(member_path).lower()
    prop = matching_rules(text, PROP_RULES)
    scene = matching_rules(text, SCENE_RULES)
    paired = matching_rules(text, PAIRED_RULES)
    partner_context = matching_rules(text, PARTNER_CONTEXT_RULES)
    semantics = matching_rules(text, SEMANTIC_RULES)

    dependency_labels: list[str] = []
    dependency_labels.extend(f"prop:{value}" for value in prop)
    dependency_labels.extend(f"scene:{value}" for value in scene)
    dependency_labels.extend(f"paired:{value}" for value in paired)
    dependency_labels.extend(
        f"partner_context:{value}" for value in partner_context
    )

    if paired:
        dependency_class = "paired_candidate"
        review_bucket = "dependency_review_later"
    elif prop:
        dependency_class = "prop_candidate"
        review_bucket = "dependency_review_later"
    elif scene:
        dependency_class = "scene_locked_candidate"
        review_bucket = "dependency_review_later"
    elif partner_context:
        dependency_class = "partner_context_candidate"
        review_bucket = "contextual_standalone_review"
    else:
        dependency_class = "standalone_candidate"
        review_bucket = "standalone_first"

    score = {
        "standalone_first": 300,
        "contextual_standalone_review": 200,
        "dependency_review_later": 100,
    }[review_bucket]
    for tag, bonus in {
        "locomotion": 30,
        "idle_pose": 25,
        "gesture_signal": 20,
        "conversation": 10,
    }.items():
        if tag in semantics:
            score += bonus
    if re.search(r"(?:^|[_\- ])loop(?:$|[_\- ])", text):
        score += 5

    return {
        "dependency_class": dependency_class,
        "dependency_hints": dependency_labels,
        "semantic_tags": semantics or ["unclassified"],
        "review_bucket": review_bucket,
        "review_priority_score": score,
    }


def motion_record(
    package_id: str,
    package_name: str,
    container_relative_path: str,
    member: dict[str, Any],
    source_type: str,
) -> dict[str, Any]:
    member_path = normalized_member_path(member["path"])
    identity = f"{package_id}|{container_relative_path}|{member_path}"
    hints = infer_motion_hints(member_path)
    return {
        "motion_id": stable_id("motion", identity),
        "package_id": package_id,
        "package_name": package_name,
        "source_type": source_type,
        "source_container_relative_path": container_relative_path,
        "member_path": member_path,
        "filename": PurePosixPath(member_path).name,
        "extension": normalized_extension(member_path),
        "size": member.get("size"),
        "crc32": member.get("crc32"),
        "sex_hint": infer_sex_hint(member_path, package_name),
        **hints,
        "classification_basis": "filename_only_static_hint",
        "review_status": "not_reviewed",
        "production_status": "not_approved",
    }


def package_sources(package_path: Path) -> tuple[list[Path], list[Path]]:
    if package_path.is_file():
        if package_path.suffix.lower() not in ARCHIVE_EXTENSIONS:
            return [], []
        return [package_path], []
    archives = sorted(
        (
            path
            for path in package_path.rglob("*")
            if path.is_file() and path.suffix.lower() in ARCHIVE_EXTENSIONS
        ),
        key=lambda item: item.as_posix().casefold(),
    )
    loose_motions = sorted(
        (
            path
            for path in package_path.rglob("*")
            if path.is_file() and path.suffix.lower() in MOTION_EXTENSIONS
        ),
        key=lambda item: item.as_posix().casefold(),
    )
    return archives, loose_motions


def scan_package(
    package_path: Path,
    source_root: Path,
    unrar_path: Path | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    package_name = package_path.name
    package_relative = package_path.relative_to(source_root).as_posix()
    package_id = stable_id("p0-package", package_relative)
    archives, loose_motions = package_sources(package_path)
    archive_records: list[dict[str, Any]] = []
    motions: list[dict[str, Any]] = []
    non_motion_extensions: Counter[str] = Counter()
    nested_archive_entries: list[str] = []

    for archive in archives:
        relative_archive = archive.relative_to(source_root).as_posix()
        try:
            members = list_archive_members(archive, unrar_path)
            status = "readable"
            error = None
        except (InventoryError, OSError, zipfile.BadZipFile) as exc:
            members = []
            status = "unreadable"
            error = str(exc)
        for member in members:
            extension = normalized_extension(member["path"])
            if extension in MOTION_EXTENSIONS:
                motions.append(
                    motion_record(
                        package_id,
                        package_name,
                        relative_archive,
                        member,
                        "archive_member",
                    )
                )
            else:
                non_motion_extensions[extension or "<none>"] += 1
                if extension in ARCHIVE_EXTENSIONS:
                    nested_archive_entries.append(
                        f"{relative_archive}::{normalized_member_path(member['path'])}"
                    )
        archive_records.append(
            {
                "relative_path": relative_archive,
                "extension": archive.suffix.lower(),
                "size": archive.stat().st_size,
                "sha256": sha256_file(archive),
                "status": status,
                "error": error,
                "member_count": len(members),
                "motion_member_count": sum(
                    normalized_extension(member["path"]) in MOTION_EXTENSIONS
                    for member in members
                ),
            }
        )

    for motion in loose_motions:
        relative_motion = motion.relative_to(source_root).as_posix()
        motions.append(
            motion_record(
                package_id,
                package_name,
                relative_motion,
                {
                    "path": relative_motion,
                    "size": motion.stat().st_size,
                    "crc32": None,
                },
                "loose_file",
            )
        )

    motions.sort(key=lambda item: item["motion_id"])
    package_record = {
        "package_id": package_id,
        "package_name": package_name,
        "relative_path": package_relative,
        "source_kind": "archive" if package_path.is_file() else "directory_bundle",
        "archive_count": len(archive_records),
        "readable_archive_count": sum(
            archive["status"] == "readable" for archive in archive_records
        ),
        "loose_motion_count": len(loose_motions),
        "motion_count": len(motions),
        "motion_extension_counts": dict(
            sorted(Counter(item["extension"] for item in motions).items())
        ),
        "sex_hint_counts": dict(
            sorted(Counter(item["sex_hint"] for item in motions).items())
        ),
        "dependency_class_counts": dict(
            sorted(Counter(item["dependency_class"] for item in motions).items())
        ),
        "review_bucket_counts": dict(
            sorted(Counter(item["review_bucket"] for item in motions).items())
        ),
        "non_motion_extension_counts": dict(sorted(non_motion_extensions.items())),
        "nested_archive_entries": nested_archive_entries,
        "archives": archive_records,
    }
    return package_record, motions


def counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def build_review_queue(
    inventory_id: str, motions: list[dict[str, Any]]
) -> dict[str, Any]:
    buckets: dict[str, list[str]] = {
        "standalone_first": [],
        "contextual_standalone_review": [],
        "dependency_review_later": [],
    }
    ordered = sorted(
        motions,
        key=lambda item: (
            -item["review_priority_score"],
            item["package_name"].casefold(),
            item["member_path"].casefold(),
        ),
    )
    for motion in ordered:
        buckets[motion["review_bucket"]].append(motion["motion_id"])
    return {
        "schema_version": 1,
        "queue_id": "cc_p0_animation_static_review_queue_20260817_v3",
        "inventory_id": inventory_id,
        "status": "static_hints_only_not_approved",
        "boundaries": [
            "Queue order is derived from filenames only.",
            "A standalone hint does not prove absence of hidden prop or contact dependencies.",
            "Every production motion requires CC visual review and technical metadata capture.",
        ],
        "counts": {name: len(ids) for name, ids in buckets.items()},
        "buckets": buckets,
    }


def validate_inventory(
    inventory: dict[str, Any], expected_package_count: int | None
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    packages = inventory["packages"]
    motions = inventory["motions"]
    if expected_package_count is not None and len(packages) != expected_package_count:
        errors.append(
            f"Expected {expected_package_count} packages, found {len(packages)}"
        )
    unreadable = [
        archive["relative_path"]
        for package in packages
        for archive in package["archives"]
        if archive["status"] != "readable"
    ]
    if unreadable:
        errors.append(f"Unreadable archives: {unreadable}")
    package_ids = [package["package_id"] for package in packages]
    motion_ids = [motion["motion_id"] for motion in motions]
    if len(package_ids) != len(set(package_ids)):
        errors.append("Duplicate package IDs")
    if len(motion_ids) != len(set(motion_ids)):
        errors.append("Duplicate motion IDs")
    if not motions:
        errors.append("No motion files discovered")
    if any(motion["production_status"] != "not_approved" for motion in motions):
        errors.append("Static inventory unexpectedly approved a production motion")
    unknown_sex = sum(motion["sex_hint"] == "unknown" for motion in motions)
    if unknown_sex:
        warnings.append(
            f"{unknown_sex} motions have no reliable filename sex hint"
        )
    return {
        "success": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checked_package_count": len(packages),
        "checked_archive_count": sum(
            package["archive_count"] for package in packages
        ),
        "checked_motion_count": len(motions),
        "production_approved_count": sum(
            motion["production_status"] == "approved" for motion in motions
        ),
    }


def build_inventory(
    source_root: Path,
    output_dir: Path,
    *,
    unrar_path: Path | None = None,
    expected_package_count: int | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()
    if not source_root.is_dir():
        raise InventoryError(f"Missing P0 source root: {source_root}")
    resolved_unrar = resolve_unrar(unrar_path)
    children = sorted(
        source_root.iterdir(), key=lambda item: item.name.casefold()
    )
    package_paths = [
        child
        for child in children
        if child.is_dir()
        or (child.is_file() and child.suffix.lower() in ARCHIVE_EXTENSIONS)
    ]
    ignored_root_entries = [
        child.name
        for child in children
        if child not in package_paths and not child.name.startswith("_")
    ]

    packages: list[dict[str, Any]] = []
    motions: list[dict[str, Any]] = []
    for package_path in package_paths:
        package, package_motions = scan_package(
            package_path, source_root, resolved_unrar
        )
        packages.append(package)
        motions.extend(package_motions)
    packages.sort(key=lambda item: item["package_name"].casefold())
    motions.sort(
        key=lambda item: (
            item["package_name"].casefold(),
            item["member_path"].casefold(),
        )
    )

    inventory_id = "cc_p0_animation_source_inventory_20260817_v3"
    inventory = {
        "schema_version": 1,
        "inventory_id": inventory_id,
        "generated_at": local_timestamp(),
        "status": "static_inventory_complete_visual_review_not_started",
        "source_tier": "P0_Core_Everyday",
        "source_root": str(source_root),
        "read_only_source_scan": True,
        "classification_level": "motion_filename_static_hint",
        "final_motion_approval": False,
        "toolchain": {
            "zip_reader": "python.zipfile",
            "unrar": str(resolved_unrar) if resolved_unrar else None,
        },
        "boundaries": [
            "No archive is extracted or modified.",
            "Dependency and sex fields are filename-only hints.",
            "P0 package membership does not grant per-motion production approval.",
        ],
        "ignored_root_entries": ignored_root_entries,
        "summary": {
            "package_count": len(packages),
            "archive_count": sum(package["archive_count"] for package in packages),
            "motion_count": len(motions),
            "motion_extension_counts": counter_dict(
                motion["extension"] for motion in motions
            ),
            "sex_hint_counts": counter_dict(
                motion["sex_hint"] for motion in motions
            ),
            "dependency_class_counts": counter_dict(
                motion["dependency_class"] for motion in motions
            ),
            "review_bucket_counts": counter_dict(
                motion["review_bucket"] for motion in motions
            ),
            "nested_archive_entry_count": sum(
                len(package["nested_archive_entries"]) for package in packages
            ),
            "production_approved_count": 0,
        },
        "packages": packages,
        "motions": motions,
    }
    inventory["validation"] = validate_inventory(
        inventory, expected_package_count
    )
    review_queue = build_review_queue(inventory_id, motions)
    write_json_atomic(output_dir / "inventory.json", inventory)
    write_json_atomic(output_dir / "review_queue.json", review_queue)
    if not inventory["validation"]["success"]:
        raise InventoryError(
            "P0 animation inventory validation failed: "
            + "; ".join(inventory["validation"]["errors"])
        )
    return inventory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory RM-09 P0 animation sources without extraction"
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--unrar", type=Path)
    parser.add_argument("--expected-packages", type=int, default=11)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(
        args.source_root,
        args.output_dir,
        unrar_path=args.unrar,
        expected_package_count=args.expected_packages,
    )
    summary = inventory["summary"]
    print(args.output_dir.resolve() / "inventory.json")
    print(
        "packages={package_count} archives={archive_count} motions={motion_count} "
        "standalone_first={standalone} approved={approved}".format(
            package_count=summary["package_count"],
            archive_count=summary["archive_count"],
            motion_count=summary["motion_count"],
            standalone=summary["review_bucket_counts"].get(
                "standalone_first", 0
            ),
            approved=summary["production_approved_count"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
