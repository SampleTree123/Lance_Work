#!/usr/bin/env python3
"""Build validated outfit_family.json files for confirmed CC clothing families."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


WEARABLE_EXTENSIONS = {
    ".ccacc",
    ".cccloth",
    ".ccgloves",
    ".cchair",
    ".ccshoes",
    ".iacc",
    ".icloth",
    ".ihair",
    ".rlhair",
}

SLOT_BY_DIRECTORY = {
    "Coats": "coats",
    "Shirts": "shirts",
    "Pants": "pants",
    "Skirts": "skirts",
    "Full-body": "full_body",
    "Shoes": "shoes",
    "_Accessories-Pending": "family_accessory",
}

VALID_MODES = {"explicit_looks", "slot_groups", "locked_bundle"}
VALID_FOOTWEAR_MODES = {
    "native_pool",
    "shared_pool",
    "integrated_footwear",
    "barefoot_only",
}


class OutfitBuildError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OutfitBuildError(f"Expected JSON object: {path}")
    return value


def atomic_json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def path_key(value: str) -> str:
    return value.replace("\\", "/").casefold()


def asset_id(family_id: str, relative_path: str) -> str:
    suffix = hashlib.sha1(path_key(relative_path).encode("utf-8")).hexdigest()[:12]
    return f"{family_id}.asset.{suffix}"


def discover_wearables(family_path: Path) -> dict[str, Path]:
    discovered: dict[str, Path] = {}
    for path in sorted(family_path.rglob("*"), key=lambda item: str(item).casefold()):
        if not path.is_file() or path.suffix.lower() not in WEARABLE_EXTENSIONS:
            continue
        relative = path.relative_to(family_path).as_posix()
        key = path_key(relative)
        if key in discovered:
            raise OutfitBuildError(f"Case-insensitive path collision in {family_path}: {relative}")
        discovered[key] = path
    return discovered


def slot_for_path(relative_path: str) -> str:
    first = relative_path.split("/", 1)[0]
    if first not in SLOT_BY_DIRECTORY:
        raise OutfitBuildError(f"Path is not in a production garment slot: {relative_path}")
    return SLOT_BY_DIRECTORY[first]


def iter_rule_paths(rule: dict[str, Any]) -> Iterable[str]:
    mode = rule["assembly_mode"]
    if mode == "explicit_looks":
        for look in rule["looks"]:
            yield from look["assets"]
            yield from look.get("optional_assets", [])
    elif mode == "slot_groups":
        for group in rule["groups"]:
            for paths in group["slot_pools"].values():
                yield from paths
            yield from group.get("required_assets", [])
            yield from group.get("optional_assets", [])
    elif mode == "locked_bundle":
        yield from rule["bundle"]["assets"]
    else:
        raise OutfitBuildError(f"Unsupported assembly mode: {mode}")


def is_native_shoe_path(relative_path: str) -> bool:
    return relative_path.replace("\\", "/").split("/", 1)[0].casefold() == "shoes"


def load_shared_shoe_inventory(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    path = root / "both" / "shoes" / "shoe_inventory.json"
    if not path.is_file():
        raise OutfitBuildError(f"Shared shoe inventory is missing: {path}")
    inventory = read_json(path)
    assets = inventory.get("assets")
    if not isinstance(assets, list) or not assets:
        raise OutfitBuildError(f"Shared shoe inventory has no assets: {path}")
    by_id: dict[str, dict[str, Any]] = {}
    for asset in assets:
        identifier = asset.get("shoe_id")
        if not isinstance(identifier, str) or not identifier:
            raise OutfitBuildError(f"Invalid shared shoe ID in {path}")
        if identifier in by_id:
            raise OutfitBuildError(f"Duplicate shared shoe ID in {path}: {identifier}")
        by_id[identifier] = asset
    return inventory, by_id


def build_footwear_policy(rule: dict[str, Any], root: Path) -> dict[str, Any]:
    policy = rule.get("footwear_policy")
    if not isinstance(policy, dict):
        raise OutfitBuildError(f"Missing footwear_policy: {rule.get('family_id')}")
    expected_keys = {
        "mode",
        "allowed_shared_shoe_ids",
        "default_shared_shoe_id",
        "allow_barefoot",
        "shared_inventory_ref",
    }
    if set(policy) != expected_keys:
        raise OutfitBuildError(
            f"Unexpected footwear_policy keys: {rule.get('family_id')}"
        )

    mode = policy["mode"]
    allowed = policy["allowed_shared_shoe_ids"]
    default = policy["default_shared_shoe_id"]
    allow_barefoot = policy["allow_barefoot"]
    inventory_ref = policy["shared_inventory_ref"]
    if mode not in VALID_FOOTWEAR_MODES:
        raise OutfitBuildError(f"Unsupported footwear mode: {mode}")
    if not isinstance(allowed, list) or not all(isinstance(value, str) for value in allowed):
        raise OutfitBuildError("allowed_shared_shoe_ids must be a string array")
    if len(allowed) != len(set(allowed)):
        raise OutfitBuildError("allowed_shared_shoe_ids must be unique")
    if default is not None and not isinstance(default, str):
        raise OutfitBuildError("default_shared_shoe_id must be a string or null")
    if not isinstance(allow_barefoot, bool):
        raise OutfitBuildError("allow_barefoot must be boolean")

    native_paths = [path for path in iter_rule_paths(rule) if is_native_shoe_path(path)]
    integrated_paths = [
        path
        for path in iter_rule_paths(rule)
        if path.lower().endswith(".ccshoes") and not is_native_shoe_path(path)
    ]

    if mode == "native_pool":
        if not native_paths or allowed or default is not None or allow_barefoot:
            raise OutfitBuildError("Invalid native_pool footwear policy")
        if inventory_ref is not None:
            raise OutfitBuildError("native_pool must not reference the shared inventory")
    elif mode == "shared_pool":
        if native_paths or not allowed:
            raise OutfitBuildError("Invalid shared_pool footwear policy")
        if default is not None and default not in allowed:
            raise OutfitBuildError("Default shared shoe is outside the allowed pool")
        if not isinstance(inventory_ref, dict) or set(inventory_ref) != {
            "library_id",
            "revision_id",
        }:
            raise OutfitBuildError("shared_pool requires a complete shared_inventory_ref")
        inventory, inventory_by_id = load_shared_shoe_inventory(root)
        expected_ref = {
            "library_id": inventory.get("library_id"),
            "revision_id": inventory.get("revision_id"),
        }
        if inventory_ref != expected_ref:
            raise OutfitBuildError("Shared shoe inventory identity has changed")
        unknown = sorted(set(allowed) - set(inventory_by_id))
        if unknown:
            raise OutfitBuildError(f"Unknown shared shoe IDs: {unknown}")
        wrong_sex = sorted(
            identifier
            for identifier in allowed
            if inventory_by_id[identifier].get("sex") != rule["sex"]
        )
        if wrong_sex:
            raise OutfitBuildError(f"Wrong-sex shared shoe IDs: {wrong_sex}")
    elif mode == "integrated_footwear":
        if native_paths or not integrated_paths or allowed or default is not None:
            raise OutfitBuildError("Invalid integrated_footwear policy")
        if allow_barefoot or inventory_ref is not None:
            raise OutfitBuildError("Integrated footwear cannot use shared/barefoot options")
    else:
        if native_paths or allowed or default is not None or not allow_barefoot:
            raise OutfitBuildError("Invalid barefoot_only policy")
        if inventory_ref is not None:
            raise OutfitBuildError("barefoot_only must not reference the shared inventory")

    return json.loads(json.dumps(policy, ensure_ascii=False))


def validate_config_partition(root: Path, config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise OutfitBuildError("Rules config schema_version must be 1")
    confirmed = config.get("confirmed_families")
    deferred = config.get("deferred_families")
    if not isinstance(confirmed, list) or not isinstance(deferred, list):
        raise OutfitBuildError("Rules config must contain confirmed_families and deferred_families")

    configured: list[tuple[str, str]] = []
    family_ids: list[str] = []
    for entry in confirmed:
        configured.append((entry["sex"], entry["family"]))
        family_ids.append(entry["family_id"])
        if entry.get("assembly_mode") not in VALID_MODES:
            raise OutfitBuildError(f"Invalid mode for {entry.get('family')}")
        policy = entry.get("footwear_policy")
        if not isinstance(policy, dict) or policy.get("mode") not in VALID_FOOTWEAR_MODES:
            raise OutfitBuildError(f"Invalid footwear policy for {entry.get('family')}")
    for entry in deferred:
        configured.append((entry["sex"], entry["family"]))

    if len(configured) != len(set(configured)):
        raise OutfitBuildError("A family appears more than once in confirmed/deferred config")
    if len(family_ids) != len(set(family_ids)):
        raise OutfitBuildError("Duplicate family_id in confirmed config")

    actual = {
        (sex, family.name)
        for sex in ("female", "male")
        for family in (root / sex).iterdir()
        if family.is_dir()
    }
    configured_set = set(configured)
    missing = sorted(actual - configured_set)
    stale = sorted(configured_set - actual)
    if missing or stale:
        raise OutfitBuildError(
            f"Family partition mismatch; missing_from_config={missing}, stale_in_config={stale}"
        )


def resolve_rule_paths(
    family_path: Path, rule: dict[str, Any]
) -> tuple[dict[str, Path], dict[str, str]]:
    discovered = discover_wearables(family_path)
    references = list(iter_rule_paths(rule))
    reference_keys = [path_key(value) for value in references]
    missing = sorted({value for value in reference_keys if value not in discovered})
    unreferenced = sorted(set(discovered) - set(reference_keys))
    if missing or unreferenced:
        raise OutfitBuildError(
            f"Asset coverage mismatch for {family_path}; missing={missing}, "
            f"unreferenced={unreferenced}"
        )
    canonical_by_key = {
        key: path.relative_to(family_path).as_posix() for key, path in discovered.items()
    }
    return discovered, canonical_by_key


def build_asset_records(
    family_id: str,
    family_path: Path,
    discovered: dict[str, Path],
    canonical_by_key: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    records: list[dict[str, Any]] = []
    ids_by_key: dict[str, str] = {}
    for key in sorted(discovered):
        path = discovered[key]
        relative = canonical_by_key[key]
        slot = slot_for_path(relative)
        identifier = asset_id(family_id, relative)
        ids_by_key[key] = identifier
        record: dict[str, Any] = {
            "asset_id": identifier,
            "display_name": path.stem,
            "path": relative,
            "slot": slot,
            "file_extension": path.suffix,
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path).lower(),
        }
        if "/Locked-Bundle/".casefold() in f"/{relative}/".casefold():
            record["locked_bundle_member"] = True
        if relative.split("/", 1)[0] == "_Accessories-Pending":
            record["component_scope"] = "family_local"
        if path.suffix.lower() == ".ccshoes" and slot != "shoes":
            record["semantic_slot_override"] = True
        records.append(record)
    return records, ids_by_key


def identifier_for(path: str, ids_by_key: dict[str, str]) -> str:
    key = path_key(path)
    try:
        return ids_by_key[key]
    except KeyError as error:
        raise OutfitBuildError(f"Rule references unknown asset: {path}") from error


def build_assembly(rule: dict[str, Any], ids_by_key: dict[str, str]) -> dict[str, Any]:
    mode = rule["assembly_mode"]
    if mode == "explicit_looks":
        look_ids: set[str] = set()
        looks: list[dict[str, Any]] = []
        for look in rule["looks"]:
            look_id = look["look_id"]
            if look_id in look_ids:
                raise OutfitBuildError(f"Duplicate look_id: {look_id}")
            look_ids.add(look_id)
            required = [identifier_for(path, ids_by_key) for path in look["assets"]]
            optional = [
                identifier_for(path, ids_by_key)
                for path in look.get("optional_assets", [])
            ]
            if len(required) != len(set(required)):
                raise OutfitBuildError(f"Duplicate asset in look: {look_id}")
            if len(optional) != len(set(optional)):
                raise OutfitBuildError(f"Duplicate optional asset in look: {look_id}")
            if set(required) & set(optional):
                raise OutfitBuildError(
                    f"Required/optional asset overlap in look: {look_id}"
                )
            looks.append(
                {
                    "look_id": look_id,
                    "required_assets": required,
                    "optional_assets": optional,
                    "optional_asset_policy": "independent_subset",
                }
            )
        if not looks:
            raise OutfitBuildError("explicit_looks family must have at least one look")
        return {"looks": looks}

    if mode == "slot_groups":
        group_ids: set[str] = set()
        groups: list[dict[str, Any]] = []
        for group in rule["groups"]:
            group_id = group["group_id"]
            if group_id in group_ids:
                raise OutfitBuildError(f"Duplicate group_id: {group_id}")
            group_ids.add(group_id)
            required = list(group["required_slots"])
            optional = list(group["optional_slots"])
            if set(required) & set(optional):
                raise OutfitBuildError(f"Required/optional slot overlap: {group_id}")
            pools: dict[str, list[str]] = {}
            for slot, paths in group["slot_pools"].items():
                identifiers = [identifier_for(path, ids_by_key) for path in paths]
                if not identifiers or len(identifiers) != len(set(identifiers)):
                    raise OutfitBuildError(f"Invalid slot pool {group_id}/{slot}")
                for path in paths:
                    if slot_for_path(path) != slot:
                        raise OutfitBuildError(f"Slot/path mismatch in {group_id}: {slot} / {path}")
                pools[slot] = identifiers
            if set(pools) != set(required) | set(optional):
                raise OutfitBuildError(f"Slot pool coverage mismatch: {group_id}")
            fixed_required = [
                identifier_for(path, ids_by_key)
                for path in group.get("required_assets", [])
            ]
            fixed_optional = [
                identifier_for(path, ids_by_key)
                for path in group.get("optional_assets", [])
            ]
            if len(fixed_required) != len(set(fixed_required)):
                raise OutfitBuildError(
                    f"Duplicate required asset in slot group: {group_id}"
                )
            if len(fixed_optional) != len(set(fixed_optional)):
                raise OutfitBuildError(
                    f"Duplicate optional asset in slot group: {group_id}"
                )
            if set(fixed_required) & set(fixed_optional):
                raise OutfitBuildError(
                    f"Required/optional asset overlap in slot group: {group_id}"
                )
            for path in group.get("required_assets", []) + group.get(
                "optional_assets", []
            ):
                if slot_for_path(path) != "family_accessory":
                    raise OutfitBuildError(
                        f"Fixed slot-group asset must be family-local: {group_id} / {path}"
                    )
            built_group = {
                "group_id": group_id,
                "required_slots": required,
                "optional_slots": optional,
                "slot_pools": pools,
            }
            if fixed_required or fixed_optional:
                built_group.update(
                    {
                        "required_assets": fixed_required,
                        "optional_assets": fixed_optional,
                        "optional_asset_policy": "independent_subset",
                    }
                )
            groups.append(built_group)
        if not groups:
            raise OutfitBuildError("slot_groups family must have at least one group")
        return {"groups": groups}

    bundle = rule["bundle"]
    required = [identifier_for(path, ids_by_key) for path in bundle["assets"]]
    if not required or len(required) != len(set(required)):
        raise OutfitBuildError("locked_bundle must contain unique required assets")
    return {"bundle": {"bundle_id": bundle["bundle_id"], "required_assets": required}}


def referenced_asset_ids(document: dict[str, Any]) -> list[str]:
    mode = document["assembly_mode"]
    assembly = document["assembly"]
    if mode == "explicit_looks":
        return [
            identifier
            for look in assembly["looks"]
            for identifier in look["required_assets"] + look["optional_assets"]
        ]
    if mode == "slot_groups":
        return [
            identifier
            for group in assembly["groups"]
            for identifier in (
                [item for pool in group["slot_pools"].values() for item in pool]
                + group.get("required_assets", [])
                + group.get("optional_assets", [])
            )
        ]
    return list(assembly["bundle"]["required_assets"])


def validate_document(document: dict[str, Any], family_path: Path) -> None:
    required_top = {
        "schema_version",
        "family_id",
        "display_name",
        "sex",
        "assembly_mode",
        "rules_status",
        "rules_exhaustive",
        "assets",
        "assembly",
        "footwear_policy",
        "constraints",
        "traceability",
    }
    if set(document) != required_top:
        raise OutfitBuildError(f"Unexpected document keys for {family_path}")
    if document["schema_version"] != 1 or document["rules_status"] != "confirmed":
        raise OutfitBuildError(f"Invalid document metadata for {family_path}")
    if document["rules_exhaustive"] is not True:
        raise OutfitBuildError(f"Rules must be exhaustive for confirmed family: {family_path}")
    if document["assembly_mode"] not in VALID_MODES:
        raise OutfitBuildError(f"Invalid assembly mode for {family_path}")

    footwear = document["footwear_policy"]
    footwear_keys = {
        "mode",
        "allowed_shared_shoe_ids",
        "default_shared_shoe_id",
        "allow_barefoot",
        "shared_inventory_ref",
    }
    if not isinstance(footwear, dict) or set(footwear) != footwear_keys:
        raise OutfitBuildError(f"Invalid footwear policy shape for {family_path}")
    if footwear["mode"] not in VALID_FOOTWEAR_MODES:
        raise OutfitBuildError(f"Invalid footwear mode for {family_path}")
    allowed_shoes = footwear["allowed_shared_shoe_ids"]
    if not isinstance(allowed_shoes, list) or not all(
        isinstance(value, str) for value in allowed_shoes
    ):
        raise OutfitBuildError(f"Invalid shared shoe ID list for {family_path}")
    if len(allowed_shoes) != len(set(allowed_shoes)):
        raise OutfitBuildError(f"Duplicate shared shoe ID for {family_path}")
    if not isinstance(footwear["allow_barefoot"], bool):
        raise OutfitBuildError(f"Invalid barefoot flag for {family_path}")
    default_shoe = footwear["default_shared_shoe_id"]
    if default_shoe is not None and default_shoe not in allowed_shoes:
        raise OutfitBuildError(f"Default shoe is outside the pool for {family_path}")

    ids = [asset["asset_id"] for asset in document["assets"]]
    if not ids or len(ids) != len(set(ids)):
        raise OutfitBuildError(f"Invalid asset IDs for {family_path}")
    for asset in document["assets"]:
        path = family_path / Path(asset["path"])
        if not path.is_file():
            raise OutfitBuildError(f"Missing asset file: {path}")
        if path.stat().st_size != asset["size_bytes"]:
            raise OutfitBuildError(f"Asset size changed: {path}")
        if sha256(path).lower() != asset["sha256"]:
            raise OutfitBuildError(f"Asset SHA-256 changed: {path}")
        if slot_for_path(asset["path"]) != asset["slot"]:
            raise OutfitBuildError(f"Asset slot mismatch: {path}")
        if asset["slot"] == "family_accessory":
            if asset.get("component_scope") != "family_local":
                raise OutfitBuildError(f"Family accessory scope is missing: {path}")
        elif "component_scope" in asset:
            raise OutfitBuildError(f"Unexpected component scope on garment: {path}")

    native_shoe_assets = [asset for asset in document["assets"] if asset["slot"] == "shoes"]
    integrated_assets = [
        asset
        for asset in document["assets"]
        if asset.get("semantic_slot_override") is True
        and asset["file_extension"].casefold() == ".ccshoes"
    ]
    footwear_mode = footwear["mode"]
    if footwear_mode == "native_pool":
        if not native_shoe_assets or allowed_shoes or footwear["shared_inventory_ref"] is not None:
            raise OutfitBuildError(f"Invalid native footwear policy for {family_path}")
    elif footwear_mode == "shared_pool":
        inventory_ref = footwear["shared_inventory_ref"]
        if native_shoe_assets or not allowed_shoes or not isinstance(inventory_ref, dict):
            raise OutfitBuildError(f"Invalid shared footwear policy for {family_path}")
        if set(inventory_ref) != {"library_id", "revision_id"}:
            raise OutfitBuildError(f"Invalid shared inventory reference for {family_path}")
    elif footwear_mode == "integrated_footwear":
        if native_shoe_assets or not integrated_assets or allowed_shoes:
            raise OutfitBuildError(f"Invalid integrated footwear policy for {family_path}")
    elif (
        native_shoe_assets
        or allowed_shoes
        or footwear["shared_inventory_ref"] is not None
        or footwear["allow_barefoot"] is not True
    ):
        raise OutfitBuildError(f"Invalid barefoot-only policy for {family_path}")

    if document["constraints"].get("allow_cross_family_components") is not False:
        raise OutfitBuildError(f"Cross-family components must be disabled: {family_path}")
    if document["constraints"].get("family_accessories_cross_family") is not False:
        raise OutfitBuildError(f"Family accessories must remain local: {family_path}")

    if document["assembly_mode"] == "explicit_looks":
        for look in document["assembly"]["looks"]:
            expected_keys = {
                "look_id",
                "required_assets",
                "optional_assets",
                "optional_asset_policy",
            }
            if set(look) != expected_keys:
                raise OutfitBuildError(
                    f"Unexpected explicit look keys in {family_path}: {look.get('look_id')}"
                )
            if look["optional_asset_policy"] != "independent_subset":
                raise OutfitBuildError(
                    f"Unsupported optional asset policy in {family_path}: "
                    f"{look.get('look_id')}"
                )

    if document["assembly_mode"] == "slot_groups":
        for group in document["assembly"]["groups"]:
            basic_keys = {
                "group_id",
                "required_slots",
                "optional_slots",
                "slot_pools",
            }
            extended_keys = basic_keys | {
                "required_assets",
                "optional_assets",
                "optional_asset_policy",
            }
            if set(group) not in (basic_keys, extended_keys):
                raise OutfitBuildError(
                    f"Unexpected slot group keys in {family_path}: "
                    f"{group.get('group_id')}"
                )
            if set(group["required_slots"]) & set(group["optional_slots"]):
                raise OutfitBuildError(
                    f"Required/optional slot overlap in {family_path}: "
                    f"{group.get('group_id')}"
                )
            if set(group["slot_pools"]) != set(group["required_slots"]) | set(
                group["optional_slots"]
            ):
                raise OutfitBuildError(
                    f"Slot pool coverage mismatch in {family_path}: "
                    f"{group.get('group_id')}"
                )
            garment_slots = set(group["slot_pools"])
            if "full_body" in garment_slots and garment_slots & {
                "coats",
                "shirts",
                "pants",
                "skirts",
            }:
                raise OutfitBuildError(
                    f"Full-body garment conflicts with separates in {family_path}: "
                    f"{group.get('group_id')}"
                )
            if {"pants", "skirts"} <= garment_slots:
                raise OutfitBuildError(
                    f"Pants and skirts conflict in {family_path}: "
                    f"{group.get('group_id')}"
                )
            if set(group) == extended_keys:
                if group["optional_asset_policy"] != "independent_subset":
                    raise OutfitBuildError(
                        f"Unsupported optional asset policy in {family_path}: "
                        f"{group.get('group_id')}"
                    )
                if set(group["required_assets"]) & set(group["optional_assets"]):
                    raise OutfitBuildError(
                        f"Required/optional asset overlap in {family_path}: "
                        f"{group.get('group_id')}"
                    )

    referenced = set(referenced_asset_ids(document))
    if referenced != set(ids):
        raise OutfitBuildError(
            f"Assembly does not cover every asset for {family_path}; "
            f"missing={sorted(set(ids) - referenced)}"
        )


def build_document(rule: dict[str, Any], root: Path, generated_at: str) -> dict[str, Any]:
    family_path = root / rule["sex"] / rule["family"]
    discovered, canonical_by_key = resolve_rule_paths(family_path, rule)
    assets, ids_by_key = build_asset_records(
        rule["family_id"], family_path, discovered, canonical_by_key
    )
    document = {
        "schema_version": 1,
        "family_id": rule["family_id"],
        "display_name": rule["family"],
        "sex": rule["sex"],
        "assembly_mode": rule["assembly_mode"],
        "rules_status": "confirmed",
        "rules_exhaustive": True,
        "assets": assets,
        "assembly": build_assembly(rule, ids_by_key),
        "footwear_policy": build_footwear_policy(rule, root),
        "constraints": {
            "allow_cross_family_components": False,
            "family_accessories_cross_family": False,
            "full_body_exclusive_with": ["coats", "shirts", "pants", "skirts"],
            "pants_skirts_mutually_exclusive": True,
        },
        "traceability": {
            "family_directory": f"{rule['sex']}/{rule['family']}",
            "generated_at": generated_at,
            "generator": "cc_build_confirmed_outfit_family_json_v1.py",
        },
    }
    validate_document(document, family_path)
    return document


def deferred_details(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for entry in config["deferred_families"]:
        family_path = root / entry["sex"] / entry["family"]
        wearables = discover_wearables(family_path)
        slot_counts = Counter(
            slot_for_path(path.relative_to(family_path).as_posix())
            for path in wearables.values()
            if path.relative_to(family_path).parts[0] in SLOT_BY_DIRECTORY
        )
        pending = sorted(
            path.relative_to(family_path).as_posix()
            for path in wearables.values()
            if path.relative_to(family_path).parts[0] == "_Accessories-Pending"
        )
        details.append(
            {
                **entry,
                "wearable_asset_count": len(wearables),
                "slot_counts": dict(sorted(slot_counts.items())),
                "pending_accessories": pending,
            }
        )
    return details


def write_documents(
    root: Path, documents: list[tuple[Path, dict[str, Any]]], replace: bool
) -> None:
    existing = [path for path, _ in documents if path.exists()]
    if existing and not replace:
        raise OutfitBuildError(
            "Refusing to overwrite existing files without --replace: "
            + ", ".join(str(path) for path in existing)
        )
    backups = {path: path.read_bytes() for path in existing}
    written: list[Path] = []
    try:
        for path, document in documents:
            atomic_json_write(path, document)
            written.append(path)
        for path, _ in documents:
            loaded = read_json(path)
            validate_document(loaded, path.parent)
    except Exception:
        for path in reversed(written):
            if path in backups:
                path.write_bytes(backups[path])
            elif path.exists():
                path.unlink()
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path(__file__).with_name("cc_outfit_confirmed_rules_v1.json"),
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    config = read_json(args.rules.resolve())
    validate_config_partition(root, config)
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    documents: list[tuple[Path, dict[str, Any]]] = []
    for rule in config["confirmed_families"]:
        path = root / rule["sex"] / rule["family"] / "outfit_family.json"
        documents.append((path, build_document(rule, root, generated_at)))

    if args.execute:
        write_documents(root, documents, args.replace)

    mode_counts = Counter(
        document["assembly_mode"] for _, document in documents
    )
    footwear_mode_counts = Counter(
        document["footwear_policy"]["mode"] for _, document in documents
    )
    report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "success": True,
        "execution_requested": args.execute,
        "root": str(root),
        "confirmed_family_count": len(documents),
        "deferred_family_count": len(config["deferred_families"]),
        "confirmed_asset_count": sum(len(value["assets"]) for _, value in documents),
        "counts_by_mode": dict(sorted(mode_counts.items())),
        "counts_by_footwear_mode": dict(sorted(footwear_mode_counts.items())),
        "shared_shoe_reference_count": sum(
            len(document["footwear_policy"]["allowed_shared_shoe_ids"])
            for _, document in documents
        ),
        "written_files": [str(path) for path, _ in documents] if args.execute else [],
        "would_write_files": [str(path) for path, _ in documents] if not args.execute else [],
        "deferred_families": deferred_details(root, config),
    }
    atomic_json_write(args.report.resolve(), report)
    print(
        json.dumps(
            {
                "success": True,
                "execution_requested": args.execute,
                "confirmed_family_count": report["confirmed_family_count"],
                "confirmed_asset_count": report["confirmed_asset_count"],
                "deferred_family_count": report["deferred_family_count"],
                "counts_by_mode": report["counts_by_mode"],
                "counts_by_footwear_mode": report["counts_by_footwear_mode"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
