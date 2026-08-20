#!/usr/bin/env python3
"""Validate immutable Headshot face prototype packages."""

import argparse
import hashlib
import json
import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_REGISTRY = os.path.join(
    SCRIPT_DIR, "cc_headshot_face_prototype_registry_v1.json"
)


class RegistryError(RuntimeError):
    pass


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_file_record(record, label, expected_extension=None):
    if not isinstance(record, dict):
        raise RegistryError("{} must be a file record".format(label))
    path = os.path.realpath(str(record.get("path") or ""))
    expected_hash = str(record.get("sha256") or "").lower()
    expected_bytes = record.get("bytes")
    if not os.path.isfile(path):
        raise RegistryError("{} is missing: {}".format(label, path))
    if expected_extension and not path.lower().endswith(expected_extension):
        raise RegistryError(
            "{} must use {}: {}".format(label, expected_extension, path)
        )
    if len(expected_hash) != 64:
        raise RegistryError("{} has no valid SHA256".format(label))
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise RegistryError("{} hash changed: {}".format(label, path))
    actual_bytes = os.path.getsize(path)
    if expected_bytes is not None and int(expected_bytes) != actual_bytes:
        raise RegistryError("{} byte count changed: {}".format(label, path))
    return {
        "path": path,
        "bytes": actual_bytes,
        "sha256": actual_hash,
    }


def validate_prototype(manifest_record, expected_id, expected_sex):
    manifest_file = require_file_record(
        manifest_record, "{} manifest".format(expected_id), ".json"
    )
    manifest = read_json(manifest_file["path"])
    if int(manifest.get("schema_version", -1)) != 1:
        raise RegistryError("{} uses an unsupported schema".format(expected_id))
    if manifest.get("prototype_id") != expected_id:
        raise RegistryError("{} manifest ID differs".format(expected_id))
    if manifest.get("sex") != expected_sex:
        raise RegistryError("{} manifest sex differs".format(expected_id))
    identity = manifest.get("identity_representation") or {}
    if identity.get("mode") != "baked_geometry_project":
        raise RegistryError("{} identity mode is unsupported".format(expected_id))
    shaping_morph_count = identity.get("nonzero_shaping_morph_count")
    shaping_morph_count_verified = shaping_morph_count is not None
    if shaping_morph_count_verified and int(shaping_morph_count) != 0:
        raise RegistryError(
            "{} must remain a baked identity prototype".format(expected_id)
        )
    if (
        not shaping_morph_count_verified
        and identity.get("measurement_status")
        != "not_recorded_in_rm05c_batch"
    ):
        raise RegistryError(
            "{} has no shaping Morph measurement status".format(expected_id)
        )
    assets = manifest.get("canonical_assets") or {}
    verified_assets = {
        "identity_project": require_file_record(
            assets.get("identity_project"),
            "{} identity project".format(expected_id),
            ".ccproject",
        ),
        "facial_profile": require_file_record(
            assets.get("facial_profile"),
            "{} Facial Profile".format(expected_id),
            ".ccfacialprofile",
        ),
        "rollback_facial_profile": require_file_record(
            assets.get("rollback_facial_profile"),
            "{} rollback Facial Profile".format(expected_id),
            ".ccfacialprofile",
        ),
    }
    source_reference_match = manifest.get("source_reference_match") or {}
    source_reference_status = source_reference_match.get("confirmation_status")
    source_reference_record = assets.get("source_reference")
    if source_reference_record is None:
        if source_reference_status != "pending_user_mapping":
            raise RegistryError(
                "{} has no source reference without a pending mapping status".format(
                    expected_id
                )
            )
        verified_assets["source_reference"] = None
        source_reference_mapped = False
    else:
        verified_assets["source_reference"] = require_file_record(
            source_reference_record,
            "{} source reference".format(expected_id),
            ".jpg",
        )
        source_reference_mapped = source_reference_status != "pending_user_mapping"
    source = manifest.get("frozen_source") or {}
    require_file_record(
        {
            "path": source.get("project_path"),
            "bytes": source.get("project_bytes"),
            "sha256": source.get("project_sha256"),
        },
        "{} frozen source project".format(expected_id),
        ".ccproject",
    )
    profile = manifest.get("profile_upgrade") or {}
    if (
        profile.get("derived_uid") != "CC5 MetaHuman"
        or int(profile.get("derived_expression_count", -1)) != 379
    ):
        raise RegistryError(
            "{} does not satisfy the CC5 HD Profile gate".format(expected_id)
        )
    validation = manifest.get("validation") or {}
    if (
        not source_reference_mapped
        and validation.get("visual_status") == "passed"
    ):
        raise RegistryError(
            "{} cannot pass visual review before source mapping".format(expected_id)
        )
    required_machine_gates = (
        "static_morphs_unchanged",
        "material_assignments_unchanged",
        "eye_structure_unchanged",
        "neutral_eye_integrity",
        "profile_persisted_after_reload",
        "source_project_unchanged",
    )
    if validation.get("machine_status") != "passed" or not all(
        validation.get(item) is True for item in required_machine_gates
    ):
        raise RegistryError(
            "{} has not passed all machine gates".format(expected_id)
        )
    assembly = manifest.get("assembly_contract") or {}
    if assembly.get("pipeline") != "headshot_project_seed_then_bodyfit_v1":
        raise RegistryError("{} assembly pipeline differs".format(expected_id))
    return {
        "prototype_id": expected_id,
        "sex": expected_sex,
        "status": manifest.get("status"),
        "visual_status": validation.get("visual_status"),
        "source_reference_mapped": source_reference_mapped,
        "source_reference_status": source_reference_status,
        "shaping_morph_count_verified": shaping_morph_count_verified,
        "assembly_implemented": bool(assembly.get("implemented")),
        "manifest": manifest_file,
        "assets": verified_assets,
    }


def validate_registry(path):
    registry_path = os.path.realpath(path)
    registry = read_json(registry_path)
    if int(registry.get("schema_version", -1)) != 1:
        raise RegistryError("Unsupported Headshot registry schema")
    prototypes = registry.get("prototypes")
    if not isinstance(prototypes, list) or not prototypes:
        raise RegistryError("Headshot registry has no prototypes")
    ids = [item.get("prototype_id") for item in prototypes]
    if any(not isinstance(item, str) or not item for item in ids):
        raise RegistryError("Headshot registry contains an invalid ID")
    if len(ids) != len(set(ids)):
        raise RegistryError("Headshot registry IDs are not unique")
    verified = []
    for item in prototypes:
        sex = item.get("sex")
        if sex not in ("female", "male"):
            raise RegistryError("{} has an invalid sex".format(item.get("prototype_id")))
        verified.append(
            validate_prototype(
                item.get("manifest"), item["prototype_id"], sex
            )
        )
    return {
        "schema_version": 1,
        "registry": registry_path,
        "registry_sha256": sha256_file(registry_path),
        "prototype_count": len(verified),
        "production_enabled_count": sum(
            1
            for item in verified
            if item["visual_status"] == "passed"
            and item["source_reference_mapped"]
            and item["shaping_morph_count_verified"]
            and item["assembly_implemented"]
        ),
        "prototypes": verified,
        "success": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate Headshot face prototype packages and hashes."
    )
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        result = validate_registry(args.registry)
    except (OSError, ValueError, RegistryError) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 1
    encoded = json.dumps(result, indent=2, sort_keys=True)
    print(encoded)
    if args.output:
        output = os.path.realpath(args.output)
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
