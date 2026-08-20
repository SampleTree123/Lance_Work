#!/usr/bin/env python3
"""Convert explicit outfit looks into one free slot group per family."""

from __future__ import annotations

import argparse
import copy
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_FAMILY_COUNT = 41
EXPECTED_EXPLICIT_COUNT = 24
EXPECTED_SLOT_GROUP_FAMILY_COUNT = 37
EXPECTED_LOCKED_BUNDLE_COUNT = 4
EXPECTED_TEST_UNIT_COUNT = 51

SLOT_ORDER = ("coats", "shirts", "pants", "skirts", "full_body", "shoes")
DIRECTORY_TO_SLOT = {
    "coats": "coats",
    "shirts": "shirts",
    "pants": "pants",
    "skirts": "skirts",
    "full-body": "full_body",
    "shoes": "shoes",
}
ACCESSORY_DIRECTORY = "_accessories-pending"


class OutfitRuleMigrationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_json_write(path: Path, data: dict[str, Any], replace: bool) -> None:
    if path.exists() and not replace:
        raise OutfitRuleMigrationError(f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")
    os.replace(temporary, path)


def ordered_unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def split_asset_path(relative_path: str) -> tuple[str, str]:
    normalized = relative_path.replace("\\", "/")
    directory = normalized.split("/", 1)[0].lower()
    if directory == ACCESSORY_DIRECTORY:
        return "family_accessory", normalized
    slot = DIRECTORY_TO_SLOT.get(directory)
    if slot is None:
        raise OutfitRuleMigrationError(
            f"Unsupported explicit-look asset directory: {relative_path}"
        )
    return slot, normalized


def convert_explicit_family(rule: dict[str, Any]) -> dict[str, Any]:
    if rule.get("assembly_mode") != "explicit_looks":
        return copy.deepcopy(rule)

    looks = rule.get("looks") or []
    if not looks:
        raise OutfitRuleMigrationError(
            f"Explicit family has no looks: {rule.get('family_id')}"
        )

    slot_pools: dict[str, list[str]] = {slot: [] for slot in SLOT_ORDER}
    required_accessory_sets: list[list[str]] = []
    optional_accessory_sets: list[list[str]] = []
    look_slot_sets: list[set[str]] = []

    for look in looks:
        current_slots: set[str] = set()
        required_accessories: list[str] = []
        for relative_path in look.get("assets") or []:
            slot, normalized = split_asset_path(relative_path)
            if slot == "family_accessory":
                required_accessories.append(normalized)
            else:
                current_slots.add(slot)
                slot_pools[slot].append(normalized)

        optional_accessories: list[str] = []
        for relative_path in look.get("optional_assets") or []:
            slot, normalized = split_asset_path(relative_path)
            if slot != "family_accessory":
                raise OutfitRuleMigrationError(
                    "Optional explicit-look assets must be family accessories: "
                    f"{rule.get('family_id')} / {relative_path}"
                )
            optional_accessories.append(normalized)

        look_slot_sets.append(current_slots)
        required_accessory_sets.append(ordered_unique(required_accessories))
        optional_accessory_sets.append(ordered_unique(optional_accessories))

    expected_slots = look_slot_sets[0]
    if any(slots != expected_slots for slots in look_slot_sets[1:]):
        raise OutfitRuleMigrationError(
            f"Explicit looks use different slot sets: {rule.get('family_id')}"
        )
    expected_required = required_accessory_sets[0]
    if any(items != expected_required for items in required_accessory_sets[1:]):
        raise OutfitRuleMigrationError(
            f"Explicit looks use different required accessories: {rule.get('family_id')}"
        )
    expected_optional = optional_accessory_sets[0]
    if any(items != expected_optional for items in optional_accessory_sets[1:]):
        raise OutfitRuleMigrationError(
            f"Explicit looks use different optional accessories: {rule.get('family_id')}"
        )

    required_slots = [slot for slot in SLOT_ORDER if slot in expected_slots]
    normalized_pools = {
        slot: ordered_unique(slot_pools[slot]) for slot in required_slots
    }
    group: dict[str, Any] = {
        "group_id": "default",
        "required_slots": required_slots,
        "optional_slots": [],
        "slot_pools": normalized_pools,
    }
    if expected_required:
        group["required_assets"] = expected_required
    if expected_optional:
        group["optional_assets"] = expected_optional

    converted = {
        key: copy.deepcopy(value)
        for key, value in rule.items()
        if key not in {"assembly_mode", "looks"}
    }
    converted["assembly_mode"] = "slot_groups"
    converted["groups"] = [group]
    return converted


def count_test_units(families: list[dict[str, Any]]) -> int:
    count = 0
    for family in families:
        mode = family.get("assembly_mode")
        if mode == "slot_groups":
            count += len(family.get("groups") or [])
        elif mode == "locked_bundle":
            count += 1
        else:
            raise OutfitRuleMigrationError(f"Unexpected result mode: {mode}")
    return count


def migrate_document(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    families = document.get("confirmed_families") or []
    if len(families) != EXPECTED_FAMILY_COUNT:
        raise OutfitRuleMigrationError(
            f"Expected {EXPECTED_FAMILY_COUNT} families, found {len(families)}"
        )
    explicit_count = sum(
        family.get("assembly_mode") == "explicit_looks" for family in families
    )
    if explicit_count != EXPECTED_EXPLICIT_COUNT:
        raise OutfitRuleMigrationError(
            f"Expected {EXPECTED_EXPLICIT_COUNT} explicit families, found {explicit_count}"
        )

    migrated = copy.deepcopy(document)
    migrated["confirmed_families"] = [
        convert_explicit_family(family) for family in families
    ]
    mode_counts = Counter(
        family.get("assembly_mode") for family in migrated["confirmed_families"]
    )
    if mode_counts != Counter(
        {
            "slot_groups": EXPECTED_SLOT_GROUP_FAMILY_COUNT,
            "locked_bundle": EXPECTED_LOCKED_BUNDLE_COUNT,
        }
    ):
        raise OutfitRuleMigrationError(f"Unexpected result modes: {dict(mode_counts)}")
    test_units = count_test_units(migrated["confirmed_families"])
    if test_units != EXPECTED_TEST_UNIT_COUNT:
        raise OutfitRuleMigrationError(
            f"Expected {EXPECTED_TEST_UNIT_COUNT} test units, found {test_units}"
        )

    report = {
        "success": True,
        "family_count": len(families),
        "converted_family_count": explicit_count,
        "result_mode_counts": dict(mode_counts),
        "result_test_unit_count": test_units,
        "converted_family_ids": [
            family["family_id"]
            for family in families
            if family.get("assembly_mode") == "explicit_looks"
        ],
    }
    return migrated, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    migrated, report = migrate_document(read_json(args.rules.resolve()))
    atomic_json_write(args.output.resolve(), migrated, replace=args.replace)
    report["source_rules"] = str(args.rules.resolve())
    report["output_rules"] = str(args.output.resolve())
    if args.report is not None:
        atomic_json_write(args.report.resolve(), report, replace=args.replace)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
