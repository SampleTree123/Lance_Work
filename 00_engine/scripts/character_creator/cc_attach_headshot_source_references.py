#!/usr/bin/env python3
"""Attach verified source photographs to staged Headshot prototype packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_MAPPING = SCRIPT_ROOT / "cc_headshot_rm05c_source_reference_mapping_v1.json"
DEFAULT_REGISTRY = SCRIPT_ROOT / "cc_headshot_face_prototype_registry_v1.json"
DEFAULT_OUTPUT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "headshot_rm05c_source_mapping_20260810_v1.json"
)


class SourceMappingError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def copy_source_once(source: Path, destination: Path, expected_hash: str) -> str:
    if destination.exists():
        if sha256_file(destination) != expected_hash:
            raise SourceMappingError(
                f"Existing source reference differs: {destination}"
            )
        return "already_present"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "wb", dir=destination.parent, delete=False, suffix=".tmp"
    ) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        if sha256_file(temporary) != expected_hash:
            raise SourceMappingError(f"Copied source hash differs: {source}")
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return "copied"


def attach_sources(
    mapping_path: Path,
    registry_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    mapping = read_json(mapping_path)
    registry = read_json(registry_path)
    if int(mapping.get("schema_version", -1)) != 1:
        raise SourceMappingError("Unsupported source mapping schema")
    if int(registry.get("schema_version", -1)) != 1:
        raise SourceMappingError("Unsupported Headshot registry schema")
    entries = mapping.get("entries") or []
    if len(entries) != int(mapping.get("expected_count", -1)):
        raise SourceMappingError("Source mapping count differs from policy")
    ids = [str(entry.get("prototype_id") or "") for entry in entries]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise SourceMappingError("Source mapping IDs are invalid or duplicated")

    registry_by_id = {
        item.get("prototype_id"): item for item in registry.get("prototypes") or []
    }
    prepared = []
    for entry in entries:
        prototype_id = entry["prototype_id"]
        registry_entry = registry_by_id.get(prototype_id)
        if registry_entry is None:
            raise SourceMappingError(f"Prototype is absent from registry: {prototype_id}")
        manifest_path = Path(registry_entry["manifest"]["path"]).resolve()
        manifest = read_json(manifest_path)
        if manifest.get("prototype_id") != prototype_id:
            raise SourceMappingError(f"Manifest ID differs: {prototype_id}")
        source = Path(entry["source_path"]).resolve()
        if not source.is_file() or source.suffix.lower() not in (".jpg", ".jpeg"):
            raise SourceMappingError(f"Source photograph is missing: {source}")
        expected_hash = str(entry.get("source_sha256") or "").lower()
        if len(expected_hash) != 64 or sha256_file(source) != expected_hash:
            raise SourceMappingError(f"Source photograph hash differs: {source}")
        prepared.append(
            {
                "prototype_id": prototype_id,
                "registry_entry": registry_entry,
                "manifest_path": manifest_path,
                "manifest": manifest,
                "source": source,
                "source_hash": expected_hash,
                "destination": manifest_path.parent / "source_reference.jpg",
            }
        )

    results = []
    for item in prepared:
        copy_status = copy_source_once(
            item["source"], item["destination"], item["source_hash"]
        )
        manifest = item["manifest"]
        manifest_before = file_record(item["manifest_path"])
        manifest["status"] = mapping["status_after"]
        manifest.setdefault("canonical_assets", {})["source_reference"] = file_record(
            item["destination"]
        )
        manifest["source_reference_match"] = {
            "original_path": str(item["source"]),
            "confirmation_status": mapping["confirmation_status"],
            "mapping_method": "filename_classification_plus_agent_visual_identity_match",
            "mapped_at": mapping["mapped_at"],
            "required_before_visual_acceptance": True,
        }
        blockers = list(
            (manifest.get("assembly_contract") or {}).get("production_blockers")
            or []
        )
        blockers = [
            blocker
            for blocker in blockers
            if blocker
            not in (
                "source_reference_mapping_pending",
                "rm05c_identity_pool_scale_comparison_pending",
            )
        ]
        for blocker in (
            "shaping_morph_count_measurement_pending",
            "headshot_production_migration_deferred_until_after_clothing_animation",
        ):
            if blocker not in blockers:
                blockers.append(blocker)
        manifest.setdefault("assembly_contract", {})[
            "production_blockers"
        ] = blockers
        write_json(manifest, item["manifest_path"])
        manifest_after = file_record(item["manifest_path"])
        item["registry_entry"]["status"] = manifest["status"]
        item["registry_entry"]["manifest"] = manifest_after
        results.append(
            {
                "prototype_id": item["prototype_id"],
                "source": file_record(item["source"]),
                "package_source_reference": file_record(item["destination"]),
                "copy_status": copy_status,
                "manifest_before": manifest_before,
                "manifest_after": manifest_after,
            }
        )

    policy = registry.setdefault("selection_policy", {})
    policy["enabled_for_production"] = False
    policy["source_reference_mapping_pending_count"] = 0
    policy["visual_acceptance_status"] = "passed_4_pending_6"
    policy["identity_pool_evaluation_status"] = (
        "deferred_until_after_clothing_and_animation_validation"
    )
    blockers = list(policy.get("production_activation_blocked_by") or [])
    blockers = [
        blocker
        for blocker in blockers
        if blocker != "rm05c_identity_pool_scale_comparison"
    ]
    for blocker in (
        "six_candidate_user_visual_acceptance",
        "six_candidate_shaping_morph_count_measurement",
        "headshot_migration_deferred_until_after_clothing_animation",
    ):
        if blocker not in blockers:
            blockers.append(blocker)
    policy["production_activation_blocked_by"] = blockers
    registry["status"] = "rm05c_10_candidate_registry_all_sources_mapped_6_visual_pending"
    registry_before = file_record(registry_path)
    write_json(registry, registry_path)
    registry_after = file_record(registry_path)
    result = {
        "schema_version": 1,
        "mapping_id": mapping["mapping_id"],
        "status": "all_sources_mapped_user_visual_review_pending",
        "mapped_count": len(results),
        "production_enabled": False,
        "results": results,
        "registry_before": registry_before,
        "registry_after": registry_after,
    }
    write_json(result, output_path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = attach_sources(
            args.mapping.resolve(), args.registry.resolve(), args.output.resolve()
        )
    except (OSError, ValueError, KeyError, SourceMappingError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
