"""Freeze and safely extract the RM-09 P0 dynamic Pilot whitelist."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_INVENTORY = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_source_inventory"
    / "p0_20260817_v3"
    / "inventory.json"
)
DEFAULT_SPEC = SCRIPT_ROOT / "cc_p0_animation_pilot_20260817_v1.json"
DEFAULT_OUTPUT = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_pilot"
    / "pilot_20260817_v1"
)

CASE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{7,95}$")
SUPPORTED_ARCHIVE_EXTENSIONS = {".zip"}


class PilotBuildError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PilotBuildError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def restore_inherited_permissions(path: Path) -> None:
    """Make atomically moved artifacts readable by desktop CC processes."""
    if os.name != "nt":
        return
    completed = subprocess.run(
        ["icacls", str(path), "/inheritance:e", "/T", "/C", "/Q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown error").strip()
        raise PilotBuildError(
            f"Could not restore inherited permissions for {path}: {detail}"
        )


def resolved_child(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise PilotBuildError("Source container relative path is missing")
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PilotBuildError(
            f"Source container escapes the P0 root: {relative}"
        ) from exc
    return candidate


def archive_records(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for package in inventory.get("packages") or []:
        for archive in package.get("archives") or []:
            relative = archive.get("relative_path")
            if not isinstance(relative, str) or not relative:
                raise PilotBuildError("Inventory archive has no relative path")
            if relative in records:
                raise PilotBuildError(
                    f"Inventory contains a duplicate archive path: {relative}"
                )
            records[relative] = archive
    return records


def validate_selection(
    inventory: dict[str, Any], spec: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    if inventory.get("inventory_id") != spec.get("source_inventory_id"):
        raise PilotBuildError("Pilot spec and source inventory IDs differ")
    policy = spec.get("selection_policy") or {}
    cases = spec.get("cases") or []
    minimum = int(policy.get("minimum_case_count", 10))
    maximum = int(policy.get("maximum_case_count", 20))
    if not minimum <= len(cases) <= maximum:
        raise PilotBuildError(
            f"Pilot case count {len(cases)} is outside {minimum}..{maximum}"
        )

    case_ids = [case.get("case_id") for case in cases]
    motion_ids = [case.get("motion_id") for case in cases]
    if any(
        not isinstance(case_id, str) or not CASE_ID_PATTERN.match(case_id)
        for case_id in case_ids
    ):
        raise PilotBuildError("Pilot contains an invalid case_id")
    if len(case_ids) != len(set(case_ids)):
        raise PilotBuildError("Pilot case IDs are not unique")
    if any(not isinstance(item, str) or not item for item in motion_ids):
        raise PilotBuildError("Pilot contains an invalid motion_id")
    if len(motion_ids) != len(set(motion_ids)):
        raise PilotBuildError("Pilot motion IDs are not unique")

    motions = inventory.get("motions") or []
    motions_by_id = {item.get("motion_id"): item for item in motions}
    if len(motions_by_id) != len(motions):
        raise PilotBuildError("Source inventory motion IDs are not unique")
    unknown = sorted(set(motion_ids) - set(motions_by_id))
    if unknown:
        raise PilotBuildError(f"Pilot references unknown motions: {unknown}")

    required_bucket = policy.get("required_review_bucket", "standalone_first")
    selected = []
    for case in cases:
        motion = motions_by_id[case["motion_id"]]
        if motion.get("review_bucket") != required_bucket:
            raise PilotBuildError(
                f"Pilot motion is outside {required_bucket}: {case['motion_id']}"
            )
        if motion.get("production_status") != "not_approved":
            raise PilotBuildError(
                "Pilot selection must not inherit production approval"
            )
        actor = case.get("pilot_actor_preset_id")
        if actor not in {"F02_Average", "M02_Average"}:
            raise PilotBuildError(f"Unsupported Pilot actor: {actor}")
        if not isinstance(case.get("review_family"), str):
            raise PilotBuildError("Pilot case has no review_family")
        selected.append((case, motion))
    return selected


def extract_zip_member(
    archive_path: Path,
    member_path: str,
    target: Path,
    expected_size: int | None,
    expected_crc32: str | None,
) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        try:
            info = archive.getinfo(member_path)
        except KeyError as exc:
            raise PilotBuildError(
                f"Selected member is absent from {archive_path.name}: {member_path}"
            ) from exc
        if info.is_dir():
            raise PilotBuildError(f"Selected member is a directory: {member_path}")
        if expected_size is not None and info.file_size != int(expected_size):
            raise PilotBuildError(f"Selected member size changed: {member_path}")
        actual_crc32 = f"{info.CRC:08x}"
        if expected_crc32 and actual_crc32.lower() != expected_crc32.lower():
            raise PilotBuildError(f"Selected member CRC changed: {member_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)


def build_pilot(
    inventory_path: Path, spec_path: Path, output_dir: Path
) -> dict[str, Any]:
    inventory_path = inventory_path.resolve()
    spec_path = spec_path.resolve()
    output_dir = output_dir.resolve()
    if not inventory_path.is_file() or not spec_path.is_file():
        raise PilotBuildError("Pilot inventory or spec file is missing")
    if output_dir.exists():
        raise PilotBuildError(f"Pilot output already exists: {output_dir}")

    inventory = read_json(inventory_path)
    spec = read_json(spec_path)
    selected = validate_selection(inventory, spec)
    source_root = Path(inventory.get("source_root", "")).resolve()
    if not source_root.is_dir():
        raise PilotBuildError(f"P0 source root is missing: {source_root}")
    archives = archive_records(inventory)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.", dir=str(output_dir.parent)
        )
    )
    verified_archives: dict[str, dict[str, Any]] = {}
    extracted_cases: list[dict[str, Any]] = []
    try:
        for index, (case, motion) in enumerate(selected, 1):
            relative_container = motion.get("source_container_relative_path")
            archive_record = archives.get(relative_container)
            if archive_record is None:
                raise PilotBuildError(
                    f"No archive record for selected motion: {relative_container}"
                )
            archive_path = resolved_child(source_root, relative_container)
            if not archive_path.is_file():
                raise PilotBuildError(f"Source archive is missing: {archive_path}")
            if archive_path.suffix.lower() not in SUPPORTED_ARCHIVE_EXTENSIONS:
                raise PilotBuildError(
                    f"Pilot extractor does not support {archive_path.suffix}: "
                    f"{archive_path}"
                )
            if relative_container not in verified_archives:
                expected_size = int(archive_record.get("size", -1))
                if archive_path.stat().st_size != expected_size:
                    raise PilotBuildError(f"Source archive size changed: {archive_path}")
                actual_sha256 = sha256_file(archive_path)
                if actual_sha256 != archive_record.get("sha256"):
                    raise PilotBuildError(f"Source archive SHA-256 changed: {archive_path}")
                verified_archives[relative_container] = {
                    "path": str(archive_path),
                    "relative_path": relative_container,
                    "size_bytes": expected_size,
                    "sha256": actual_sha256,
                }

            extension = motion.get("extension")
            if not isinstance(extension, str) or not extension.startswith("."):
                raise PilotBuildError("Selected motion has an invalid extension")
            relative_output = Path("motions") / (
                f"{index:02d}_{case['case_id']}{extension}"
            )
            staging_target = staging / relative_output
            extract_zip_member(
                archive_path,
                motion["member_path"],
                staging_target,
                motion.get("size"),
                motion.get("crc32"),
            )
            extracted_size = staging_target.stat().st_size
            if motion.get("size") is not None and extracted_size != int(
                motion["size"]
            ):
                raise PilotBuildError(
                    f"Extracted motion size changed: {case['case_id']}"
                )
            extracted_cases.append(
                {
                    "case_id": case["case_id"],
                    "motion_id": motion["motion_id"],
                    "filename": motion["filename"],
                    "source_format": motion["extension"],
                    "format_generation": (
                        "legacy_compatible"
                        if motion["extension"].lower() == ".imotion"
                        else "current"
                    ),
                    "package_name": motion["package_name"],
                    "source_container_relative_path": relative_container,
                    "source_member_path": motion["member_path"],
                    "source_member_crc32": motion.get("crc32"),
                    "sex_hint": motion.get("sex_hint"),
                    "semantic_tags": motion.get("semantic_tags") or [],
                    "dependency_class": motion.get("dependency_class"),
                    "review_bucket": motion.get("review_bucket"),
                    "pilot_actor_preset_id": case["pilot_actor_preset_id"],
                    "review_family": case["review_family"],
                    "loop_hint": case.get("loop_hint", "unknown"),
                    "extracted_file": {
                        "path": str(output_dir / relative_output),
                        "relative_path": relative_output.as_posix(),
                        "size_bytes": extracted_size,
                        "sha256": sha256_file(staging_target),
                    },
                    "review_status": "pending_cc_dynamic_review",
                    "production_status": "not_approved",
                }
            )

        digest_groups: dict[str, list[str]] = defaultdict(list)
        for case in extracted_cases:
            digest_groups[case["extracted_file"]["sha256"]].append(case["case_id"])
        duplicates = [
            {"sha256": digest, "case_ids": case_ids}
            for digest, case_ids in sorted(digest_groups.items())
            if len(case_ids) > 1
        ]
        if spec["selection_policy"].get("require_unique_content") and duplicates:
            raise PilotBuildError(
                f"Pilot contains byte-identical motions: {duplicates}"
            )

        actor_counts = Counter(
            case["pilot_actor_preset_id"] for case in extracted_cases
        )
        format_counts = Counter(case["source_format"] for case in extracted_cases)
        family_counts = Counter(case["review_family"] for case in extracted_cases)
        manifest = {
            "schema_version": 1,
            "pilot_id": spec["pilot_id"],
            "generated_at": now(),
            "status": "extracted_pending_cc_dynamic_review",
            "source_inventory": {
                "inventory_id": inventory["inventory_id"],
                "path": str(inventory_path),
                "sha256": sha256_file(inventory_path),
            },
            "selection_spec": {
                "path": str(spec_path),
                "sha256": sha256_file(spec_path),
            },
            "source_root": str(source_root),
            "source_archives": list(verified_archives.values()),
            "boundaries": list(spec.get("boundaries") or []),
            "counts": {
                "case_count": len(extracted_cases),
                "by_pilot_actor": dict(sorted(actor_counts.items())),
                "by_source_format": dict(sorted(format_counts.items())),
                "by_review_family": dict(sorted(family_counts.items())),
                "production_approved_count": 0,
            },
            "cases": extracted_cases,
            "validation": {
                "success": True,
                "all_selected_from_required_bucket": True,
                "all_extracted_files_unique": not duplicates,
                "duplicate_content_groups": duplicates,
                "source_archives_unchanged": True,
            },
        }
        review = {
            "schema_version": 1,
            "pilot_id": spec["pilot_id"],
            "status": "not_started",
            "required_fields": [
                "load_status",
                "motion_length_frames",
                "loop_class",
                "root_motion_class",
                "facial_channel_class",
                "hidden_dependencies",
                "visual_decision",
            ],
            "cases": [
                {
                    "case_id": case["case_id"],
                    "motion_id": case["motion_id"],
                    "load_status": "not_run",
                    "motion_length_frames": None,
                    "fps": None,
                    "loop_class": "pending",
                    "root_motion_class": "pending",
                    "facial_channel_class": "pending",
                    "hidden_dependencies": [],
                    "visual_decision": "pending",
                    "notes": [],
                }
                for case in extracted_cases
            ],
        }
        write_json(staging / "pilot_manifest.json", manifest)
        write_json(staging / "dynamic_review.json", review)
        restore_inherited_permissions(staging)
        os.replace(staging, output_dir)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_pilot(args.inventory, args.spec, args.output)
    print(
        json.dumps(
            {
                "pilot_id": result["pilot_id"],
                "status": result["status"],
                "counts": result["counts"],
                "output": str(args.output.resolve()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
