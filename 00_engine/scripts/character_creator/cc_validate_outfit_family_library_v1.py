#!/usr/bin/env python3
"""Validate confirmed outfit_family.json files and deferred-family isolation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BUILDER_PATH = Path(__file__).with_name("cc_build_confirmed_outfit_family_json_v1.py")
SPEC = importlib.util.spec_from_file_location("cc_outfit_family_builder_v1", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(BUILDER)


def validate(root: Path, rules_path: Path) -> dict[str, Any]:
    config = BUILDER.read_json(rules_path)
    BUILDER.validate_config_partition(root, config)
    errors: list[str] = []
    validated_files: list[str] = []
    confirmed_paths: set[Path] = set()

    for rule in config["confirmed_families"]:
        family_path = root / rule["sex"] / rule["family"]
        json_path = family_path / "outfit_family.json"
        confirmed_paths.add(json_path.resolve())
        if not json_path.is_file():
            errors.append(f"missing confirmed family JSON: {json_path}")
            continue
        try:
            document = BUILDER.read_json(json_path)
            BUILDER.validate_document(document, family_path)
            if document["family_id"] != rule["family_id"]:
                raise BUILDER.OutfitBuildError("family_id differs from confirmed rules")
            if document["assembly_mode"] != rule["assembly_mode"]:
                raise BUILDER.OutfitBuildError("assembly_mode differs from confirmed rules")
            prospective = BUILDER.build_document(
                rule, root, document["traceability"]["generated_at"]
            )
            if document != prospective:
                raise BUILDER.OutfitBuildError(
                    "document differs from the current confirmed rules or asset inventory"
                )
            validated_files.append(str(json_path))
        except Exception as error:  # Report every family in one run.
            errors.append(f"{json_path}: {error}")

    deferred_with_json: list[str] = []
    for entry in config["deferred_families"]:
        json_path = root / entry["sex"] / entry["family"] / "outfit_family.json"
        if json_path.exists():
            deferred_with_json.append(str(json_path))
            errors.append(f"deferred family unexpectedly has JSON: {json_path}")

    all_json = {path.resolve() for path in root.glob("*/*/outfit_family.json")}
    for extra in sorted(all_json - confirmed_paths):
        errors.append(f"unregistered outfit family JSON: {extra}")

    return {
        "schema_version": 1,
        "validated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": str(root),
        "success": not errors,
        "confirmed_family_count": len(config["confirmed_families"]),
        "validated_family_count": len(validated_files),
        "deferred_family_count": len(config["deferred_families"]),
        "deferred_with_json_count": len(deferred_with_json),
        "error_count": len(errors),
        "errors": errors,
        "validated_files": validated_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path(__file__).with_name("cc_outfit_confirmed_rules_v1.json"),
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    result = validate(args.root.resolve(), args.rules.resolve())
    BUILDER.atomic_json_write(args.report.resolve(), result)
    print(
        json.dumps(
            {
                "success": result["success"],
                "confirmed_family_count": result["confirmed_family_count"],
                "validated_family_count": result["validated_family_count"],
                "deferred_family_count": result["deferred_family_count"],
                "error_count": result["error_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
