"""Build an editable shared-shoe assignment draft for outfit families."""

import argparse
import collections
import datetime
import json
import os
from pathlib import Path


EXPECTED_PENDING_COUNTS = {"female": 11, "male": 4}
BAREFOOT_PLAUSIBLE = {"female.bikini_ruana", "male.pyjamas"}


class AssignmentDraftError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data, force=False):
    if path.exists() and not force:
        raise AssignmentDraftError(
            "Output already exists; refusing to overwrite user input: {}".format(path)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")
    os.replace(temporary, path)


def build_available_ids(inventory):
    result = {"female": collections.defaultdict(list), "male": collections.defaultdict(list)}
    for asset in inventory.get("assets", []):
        result[asset["sex"]][asset["style_category"]].append(asset["shoe_id"])
    return {
        sex: {
            category: sorted(ids)
            for category, ids in sorted(categories.items())
        }
        for sex, categories in result.items()
    }


def build_entry(sex, manifest_path, manifest):
    assets = manifest.get("assets", [])
    slot_counts = collections.Counter(asset.get("slot") for asset in assets)
    review_flags = []
    semantic_footwear = []
    for asset in assets:
        path = str(asset.get("path", ""))
        if path.lower().endswith(".ccshoes") and asset.get("slot") != "shoes":
            review_flags.append("semantic_full_body_ccshoes")
            semantic_footwear.append(
                {
                    "asset_id": asset.get("asset_id"),
                    "display_name": asset.get("display_name"),
                    "slot": asset.get("slot"),
                    "path": path,
                }
            )
    if manifest.get("assembly_mode") == "locked_bundle":
        review_flags.append("locked_bundle_may_include_footwear")
    if manifest.get("family_id") in BAREFOOT_PLAUSIBLE:
        review_flags.append("barefoot_may_be_valid")
    review_flags = sorted(set(review_flags))
    status = (
        "review_before_assignment"
        if any(
            flag in review_flags
            for flag in (
                "semantic_full_body_ccshoes",
                "locked_bundle_may_include_footwear",
            )
        )
        else "awaiting_allowed_shared_shoe_ids"
    )
    return {
        "family_id": manifest["family_id"],
        "sex": sex,
        "display_name": manifest.get("display_name"),
        "family_path": str(manifest_path.parent.resolve()),
        "family_manifest_path": str(manifest_path.resolve()),
        "assembly_mode": manifest.get("assembly_mode"),
        "existing_slot_counts": dict(sorted(slot_counts.items())),
        "native_shoe_asset_count": 0,
        "assignment_status": status,
        "review_flags": review_flags,
        "semantic_footwear_assets": semantic_footwear,
        "shoe_resolution": None,
        "allowed_shared_shoe_ids": [],
        "default_shared_shoe_id": None,
        "allow_barefoot": False,
        "look_overrides": [],
        "notes": "",
    }


def build_draft(clothing_root):
    clothing_root = clothing_root.resolve()
    inventory_path = clothing_root / "both" / "shoes" / "shoe_inventory.json"
    if not inventory_path.is_file():
        raise AssignmentDraftError("Shared shoe inventory is missing")
    inventory = read_json(inventory_path)
    if inventory.get("schema_version") != 3:
        raise AssignmentDraftError("Shared shoe inventory must be schema 3")

    pending = []
    native_family_count = 0
    family_count = 0
    for sex in ("female", "male"):
        for manifest_path in sorted((clothing_root / sex).glob("*/outfit_family.json")):
            family_count += 1
            manifest = read_json(manifest_path)
            native_shoes = [
                asset
                for asset in manifest.get("assets", [])
                if asset.get("slot") == "shoes"
            ]
            if native_shoes:
                native_family_count += 1
                continue
            pending.append(build_entry(sex, manifest_path, manifest))

    pending_counts = collections.Counter(item["sex"] for item in pending)
    if dict(pending_counts) != EXPECTED_PENDING_COUNTS:
        raise AssignmentDraftError(
            "Unexpected pending family counts: {}".format(dict(pending_counts))
        )
    if family_count != 41 or native_family_count != 26:
        raise AssignmentDraftError(
            "Unexpected family partition: total={}, native={}".format(
                family_count, native_family_count
            )
        )

    pending.sort(key=lambda item: (item["sex"], item["family_id"]))
    review_count = sum(
        item["assignment_status"] == "review_before_assignment"
        for item in pending
    )
    return {
        "schema_version": 1,
        "document_id": "shared_shoe_assignment_draft_v1",
        "generated_at": now(),
        "status": "awaiting_user_input",
        "clothing_root": str(clothing_root),
        "shared_shoe_inventory": {
            "path": str(inventory_path.resolve()),
            "library_id": inventory["library_id"],
            "revision_id": inventory["revision_id"],
            "schema_version": inventory["schema_version"],
        },
        "rules": {
            "native_family_pool": (
                "Families with native slot=shoes assets are excluded from this "
                "draft and keep using their own Shoes directory."
            ),
            "shared_pool_scope": (
                "For each listed family using shared_pool, choose one or more "
                "same-sex shared shoe IDs. Multiple IDs are allowed."
            ),
            "shared_deletion": (
                "Shared-pool membership never enables or disables a family's "
                "native shoes."
            ),
            "shoe_resolution_values": [
                "shared_pool",
                "integrated_footwear",
                "barefoot_only",
            ],
            "barefoot_rule": (
                "allow_barefoot is independent from shared_pool. Set it true "
                "to randomize between the allowed shoe IDs and barefoot. Use "
                "barefoot_only only when shoes must never be used."
            ),
            "default_rule": (
                "default_shared_shoe_id may be null; when set, it must also "
                "appear in allowed_shared_shoe_ids."
            ),
            "sex_rule": "Female families use F IDs; male families use M IDs.",
            "look_overrides": (
                "Leave empty for one family-wide pool. Use only when a specific "
                "look needs a narrower pool."
            ),
        },
        "available_shared_shoe_ids": build_available_ids(inventory),
        "counts": {
            "all_outfit_families": family_count,
            "families_with_native_shoes": native_family_count,
            "families_requiring_resolution": len(pending),
            "female_requiring_resolution": pending_counts["female"],
            "male_requiring_resolution": pending_counts["male"],
            "review_before_assignment": review_count,
        },
        "families": pending,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clothing-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    draft = build_draft(Path(args.clothing_root))
    output = Path(args.output).resolve()
    write_json(output, draft, force=args.force)
    print(
        json.dumps(
            {
                "success": True,
                "output": str(output),
                "counts": draft["counts"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
