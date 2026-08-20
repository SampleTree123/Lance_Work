#!/usr/bin/env python3
"""Merge reviewed shared-shoe assignments into confirmed outfit rules.

The source assignment document is an authoring artifact. The generated rules become
the runtime authority, while the global shoe inventory remains the ID-to-file registry.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


class ShoeMergeError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ShoeMergeError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def iter_rule_paths(rule: dict[str, Any]) -> Iterable[str]:
    mode = rule["assembly_mode"]
    if mode == "explicit_looks":
        for look in rule["looks"]:
            yield from look["assets"]
            yield from look.get("optional_assets", [])
        return
    if mode == "slot_groups":
        for group in rule["groups"]:
            for paths in group["slot_pools"].values():
                yield from paths
            yield from group.get("required_assets", [])
            yield from group.get("optional_assets", [])
        return
    if mode == "locked_bundle":
        yield from rule["bundle"]["assets"]
        return
    raise ShoeMergeError(f"Unsupported assembly mode: {mode}")


def is_native_shoe_path(path: str) -> bool:
    return path.replace("\\", "/").split("/", 1)[0].casefold() == "shoes"


def has_integrated_footwear(rule: dict[str, Any]) -> bool:
    return any(
        path.lower().endswith(".ccshoes") and not is_native_shoe_path(path)
        for path in iter_rule_paths(rule)
    )


def inventory_index(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets = inventory.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ShoeMergeError("Shared shoe inventory has no assets")
    result: dict[str, dict[str, Any]] = {}
    for asset in assets:
        identifier = asset.get("shoe_id")
        if not isinstance(identifier, str) or not identifier:
            raise ShoeMergeError("Shared shoe inventory contains an invalid shoe_id")
        if identifier in result:
            raise ShoeMergeError(f"Duplicate shared shoe ID: {identifier}")
        result[identifier] = asset
    return result


def validate_shared_ids(
    family_id: str,
    sex: str,
    allowed: list[str],
    default: str | None,
    inventory_by_id: dict[str, dict[str, Any]],
) -> None:
    if not allowed or len(allowed) != len(set(allowed)):
        raise ShoeMergeError(f"{family_id}: shared_pool requires unique shoe IDs")
    unknown = sorted(set(allowed) - set(inventory_by_id))
    if unknown:
        raise ShoeMergeError(f"{family_id}: unknown shared shoe IDs: {unknown}")
    wrong_sex = sorted(
        identifier
        for identifier in allowed
        if inventory_by_id[identifier].get("sex") != sex
    )
    if wrong_sex:
        raise ShoeMergeError(f"{family_id}: wrong-sex shoe IDs: {wrong_sex}")
    if default is not None and default not in allowed:
        raise ShoeMergeError(
            f"{family_id}: default_shared_shoe_id is outside the allowed pool"
        )


def build_policy(
    rule: dict[str, Any],
    assignment: dict[str, Any] | None,
    inventory: dict[str, Any],
    inventory_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    family_id = rule["family_id"]
    native_paths = [path for path in iter_rule_paths(rule) if is_native_shoe_path(path)]
    if native_paths:
        if assignment is not None:
            raise ShoeMergeError(
                f"{family_id}: native-shoe family must not have a shared assignment"
            )
        return {
            "mode": "native_pool",
            "allowed_shared_shoe_ids": [],
            "default_shared_shoe_id": None,
            "allow_barefoot": False,
            "shared_inventory_ref": None,
        }

    if assignment is None:
        raise ShoeMergeError(f"{family_id}: family without native shoes has no assignment")
    if assignment.get("family_id") != family_id or assignment.get("sex") != rule["sex"]:
        raise ShoeMergeError(f"{family_id}: assignment identity mismatch")
    if assignment.get("look_overrides", []) != []:
        raise ShoeMergeError(f"{family_id}: look_overrides are not supported in v1")

    mode = assignment.get("shoe_resolution")
    allowed = assignment.get("allowed_shared_shoe_ids", [])
    default = assignment.get("default_shared_shoe_id")
    allow_barefoot = assignment.get("allow_barefoot")
    if not isinstance(allowed, list) or not all(isinstance(value, str) for value in allowed):
        raise ShoeMergeError(f"{family_id}: allowed_shared_shoe_ids must be strings")
    if not isinstance(allow_barefoot, bool):
        raise ShoeMergeError(f"{family_id}: allow_barefoot must be boolean")

    inventory_ref: dict[str, Any] | None = None
    if mode == "shared_pool":
        validate_shared_ids(family_id, rule["sex"], allowed, default, inventory_by_id)
        inventory_ref = {
            "library_id": inventory.get("library_id"),
            "revision_id": inventory.get("revision_id"),
        }
        if not all(isinstance(value, str) and value for value in inventory_ref.values()):
            raise ShoeMergeError("Shared shoe inventory identity is incomplete")
    elif mode == "integrated_footwear":
        if allowed or default is not None or allow_barefoot:
            raise ShoeMergeError(f"{family_id}: invalid integrated_footwear fields")
        if not has_integrated_footwear(rule):
            raise ShoeMergeError(f"{family_id}: no integrated .ccShoes asset found")
    elif mode == "barefoot_only":
        if allowed or default is not None or not allow_barefoot:
            raise ShoeMergeError(f"{family_id}: invalid barefoot_only fields")
    else:
        raise ShoeMergeError(f"{family_id}: unsupported shoe_resolution {mode!r}")

    return {
        "mode": mode,
        "allowed_shared_shoe_ids": allowed,
        "default_shared_shoe_id": default,
        "allow_barefoot": allow_barefoot,
        "shared_inventory_ref": inventory_ref,
    }


def merge(
    rules: dict[str, Any], assignments: dict[str, Any], inventory: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    confirmed = rules.get("confirmed_families")
    assignment_list = assignments.get("families")
    if not isinstance(confirmed, list) or not isinstance(assignment_list, list):
        raise ShoeMergeError("Rules or assignment document has an invalid family list")
    assignment_by_id: dict[str, dict[str, Any]] = {}
    for assignment in assignment_list:
        family_id = assignment.get("family_id")
        if not isinstance(family_id, str) or family_id in assignment_by_id:
            raise ShoeMergeError(f"Invalid or duplicate assignment family_id: {family_id!r}")
        assignment_by_id[family_id] = assignment

    inventory_by_id = inventory_index(inventory)
    confirmed_ids = {rule["family_id"] for rule in confirmed}
    unknown_assignments = sorted(set(assignment_by_id) - confirmed_ids)
    if unknown_assignments:
        raise ShoeMergeError(f"Assignments reference unknown families: {unknown_assignments}")

    merged_rules = json.loads(json.dumps(rules, ensure_ascii=False))
    mode_counts: Counter[str] = Counter()
    shared_reference_count = 0
    consumed_assignments: set[str] = set()
    family_rows: list[dict[str, Any]] = []
    for rule in merged_rules["confirmed_families"]:
        family_id = rule["family_id"]
        assignment = assignment_by_id.get(family_id)
        policy = build_policy(rule, assignment, inventory, inventory_by_id)
        rule["footwear_policy"] = policy
        mode_counts[policy["mode"]] += 1
        shared_reference_count += len(policy["allowed_shared_shoe_ids"])
        if assignment is not None:
            consumed_assignments.add(family_id)
        family_rows.append(
            {
                "family_id": family_id,
                "sex": rule["sex"],
                "mode": policy["mode"],
                "shared_shoe_id_count": len(policy["allowed_shared_shoe_ids"]),
                "allow_barefoot": policy["allow_barefoot"],
            }
        )

    unused_assignments = sorted(set(assignment_by_id) - consumed_assignments)
    if unused_assignments:
        raise ShoeMergeError(f"Assignments were not consumed: {unused_assignments}")

    report = {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "success": True,
        "confirmed_family_count": len(confirmed),
        "assignment_count": len(assignment_list),
        "shared_inventory_asset_count": len(inventory_by_id),
        "counts_by_footwear_mode": dict(sorted(mode_counts.items())),
        "shared_shoe_reference_count": shared_reference_count,
        "unique_shared_shoe_reference_count": len(
            {
                identifier
                for rule in merged_rules["confirmed_families"]
                for identifier in rule["footwear_policy"]["allowed_shared_shoe_ids"]
            }
        ),
        "families": family_rows,
    }
    return merged_rules, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--shoe-assignments", type=Path, required=True)
    parser.add_argument("--shoe-inventory", type=Path, required=True)
    parser.add_argument("--output-rules", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    merged_rules, report = merge(
        read_json(args.rules.resolve()),
        read_json(args.shoe_assignments.resolve()),
        read_json(args.shoe_inventory.resolve()),
    )
    write_json(args.output_rules.resolve(), merged_rules)
    write_json(args.report.resolve(), report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
