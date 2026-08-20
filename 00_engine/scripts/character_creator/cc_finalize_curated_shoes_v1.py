"""Finalize a user-curated CC shoe pool with contiguous IDs and audit records."""

import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata


CATEGORY_ORDER = {
    "female": ("Flats", "Heels"),
    "male": ("Boots", "Casual", "Formal", "Sandals", "Sport"),
}

CATEGORY_ALIASES = {
    ("female", "Formal"): "Flats",
}

EXPECTED_COUNTS = {"female": 17, "male": 35}
EXPECTED_REMOVED_IDS = {"M009", "M013", "M014", "M026", "M029", "M037"}


class ShoeFinalizationError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_within(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def slug(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    result = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value).strip("_")
    return result or "Asset"


def parse_existing_id(filename):
    match = re.match(r"^([FM])(\d{3})_", filename, flags=re.IGNORECASE)
    if not match:
        raise ShoeFinalizationError(
            "Shoe filename has no recognized ID: {}".format(filename)
        )
    return "{}{}".format(match.group(1).upper(), match.group(2))


def scan_curated_pool(active_root, previous_inventory, expected_removed_ids):
    previous_assets = previous_inventory.get("assets", [])
    previous_by_hash = {}
    for asset in previous_assets:
        digest = str(asset.get("sha256", "")).lower()
        if not digest or digest in previous_by_hash:
            raise ShoeFinalizationError(
                "Previous inventory has a missing or duplicate hash"
            )
        previous_by_hash[digest] = asset

    current = []
    current_hashes = set()
    inventory_path = active_root / "shoe_inventory.json"
    for path in sorted(active_root.rglob("*"), key=lambda item: str(item).lower()):
        if not path.is_file():
            continue
        if path.resolve() == inventory_path.resolve():
            continue
        if path.suffix.lower() != ".ccshoes":
            raise ShoeFinalizationError(
                "Unexpected file in active shoe pool: {}".format(path)
            )
        relative = path.relative_to(active_root)
        if len(relative.parts) != 3:
            raise ShoeFinalizationError(
                "Shoe is not in Sex/Category/File layout: {}".format(relative)
            )
        sex_folder, current_category, _ = relative.parts
        sex = sex_folder.lower()
        if sex not in CATEGORY_ORDER:
            raise ShoeFinalizationError("Unknown sex folder: {}".format(sex_folder))
        category = CATEGORY_ALIASES.get(
            (sex, current_category), current_category
        )
        if category not in CATEGORY_ORDER[sex]:
            raise ShoeFinalizationError(
                "Unknown category for {}: {}".format(sex, current_category)
            )
        digest = sha256_file(path)
        if digest in current_hashes:
            raise ShoeFinalizationError(
                "Curated pool still has a duplicate hash: {}".format(digest)
            )
        current_hashes.add(digest)
        if digest not in previous_by_hash:
            raise ShoeFinalizationError(
                "Curated shoe is absent from previous inventory: {}".format(path)
            )
        previous = previous_by_hash[digest]
        if previous.get("sex") != sex:
            raise ShoeFinalizationError(
                "Shoe moved across sex pools: {}".format(relative)
            )
        current.append(
            {
                "path": path.resolve(),
                "relative_path": relative.as_posix(),
                "existing_id": parse_existing_id(path.name),
                "sex": sex,
                "category": category,
                "sha256": digest,
                "size_bytes": path.stat().st_size,
                "previous": previous,
            }
        )

    actual_counts = collections.Counter(item["sex"] for item in current)
    if dict(actual_counts) != EXPECTED_COUNTS:
        raise ShoeFinalizationError(
            "Unexpected curated counts: {}".format(dict(actual_counts))
        )

    removed = [
        asset
        for digest, asset in previous_by_hash.items()
        if digest not in current_hashes
    ]
    removed_ids = {asset["shoe_id"] for asset in removed}
    if removed_ids != expected_removed_ids:
        raise ShoeFinalizationError(
            "Unexpected removed IDs: {}".format(sorted(removed_ids))
        )
    return current, removed


def build_plan(clothing_root):
    clothing_root = clothing_root.resolve()
    active_root = (clothing_root / "both" / "shoes").resolve()
    inventory_path = active_root / "shoe_inventory.json"
    if not active_root.is_dir() or not is_within(active_root, clothing_root):
        raise ShoeFinalizationError("Active shoe root is invalid")
    if not inventory_path.is_file():
        raise ShoeFinalizationError("Previous shoe inventory is missing")
    previous_inventory = read_json(inventory_path)
    if previous_inventory.get("library_id") != "cc_shared_shoes_v1":
        raise ShoeFinalizationError("Previous shoe inventory has an unknown ID")

    already_finalized = (
        previous_inventory.get("revision_id") == "curated_20260814_v1"
    )
    expected_removed_ids = set() if already_finalized else EXPECTED_REMOVED_IDS

    current, removed = scan_curated_pool(
        active_root, previous_inventory, expected_removed_ids
    )
    category_rank = {
        sex: {name: index for index, name in enumerate(categories)}
        for sex, categories in CATEGORY_ORDER.items()
    }
    current.sort(
        key=lambda item: (
            item["sex"],
            category_rank[item["sex"]][item["category"]],
            int(item["existing_id"][1:]),
            item["sha256"],
        )
    )

    counters = collections.Counter()
    assets = []
    rename_map = []
    for item in current:
        sex = item["sex"]
        counters[sex] += 1
        prefix = "F" if sex == "female" else "M"
        shoe_id = "{}{:03d}".format(prefix, counters[sex])
        previous = item["previous"]
        family_slug = slug(str(previous["family_id"]).split(".", 1)[-1])
        display_slug = slug(previous["display_name"])
        filename = "{}_{}_{}_{}.ccShoes".format(
            shoe_id,
            item["category"],
            family_slug,
            display_slug,
        )
        sex_folder = "Female" if sex == "female" else "Male"
        new_relative = (
            Path(sex_folder) / item["category"] / filename
        ).as_posix()
        final_path = active_root.joinpath(*new_relative.split("/"))

        asset = dict(previous)
        asset.update(
            {
                "shoe_id": shoe_id,
                "sex": sex,
                "style_category": item["category"],
                "new_relative_path": new_relative,
                "sha256": item["sha256"],
                "size_bytes": item["size_bytes"],
                "source_paths": [str(final_path)],
                "source_path_count": 1,
                "classification_status": "user_curated_v1",
                "previous_shoe_id": item["existing_id"],
                "previous_relative_path": item["relative_path"],
            }
        )
        assets.append(asset)
        rename_map.append(
            {
                "sha256": item["sha256"],
                "old_shoe_id": item["existing_id"],
                "new_shoe_id": shoe_id,
                "old_relative_path": item["relative_path"],
                "new_relative_path": new_relative,
            }
        )

    relative_paths = [asset["new_relative_path"] for asset in assets]
    if len(relative_paths) != len(set(relative_paths)):
        raise ShoeFinalizationError("Final shoe paths are not unique")

    category_counts = collections.Counter(
        "{}/{}".format(asset["sex"], asset["style_category"])
        for asset in assets
    )
    if already_finalized:
        removed_records = previous_inventory.get(
            "removed_from_previous_inventory", []
        )
    else:
        removed_records = [
            {
                "shoe_id": asset["shoe_id"],
                "display_name": asset["display_name"],
                "family_id": asset["family_id"],
                "style_category": asset["style_category"],
                "sha256": asset["sha256"],
                "previous_relative_path": asset["new_relative_path"],
                "removal_reason": "removed_by_user_during_visual_curation",
            }
            for asset in sorted(removed, key=lambda value: value["shoe_id"])
        ]

    inventory = {
        "schema_version": 2,
        "library_id": "cc_shared_shoes_v1",
        "revision_id": "curated_20260814_v1",
        "generated_at": now(),
        "active_root": str(active_root),
        "curation_status": "user_curated_structure_recorded",
        "numbering_policy": "contiguous_per_sex_after_user_curation",
        "style_policy": "user_curated_categories",
        "unisex_pool_removed": True,
        "counts": {
            "female": counters["female"],
            "male": counters["male"],
            "total": len(assets),
            "removed_from_previous_revision": len(removed_records),
        },
        "category_counts": dict(sorted(category_counts.items())),
        "assets": assets,
        "removed_from_previous_inventory": removed_records,
        "downstream_status": {
            "outfit_family_json": (
                "shoe paths remain stale until shared shoe ID migration"
            ),
            "visual_validation": "pending_per-shoe CC review",
        },
    }
    return {
        "schema_version": 1,
        "operation": "finalize_curated_shoes_v1",
        "generated_at": now(),
        "active_root": str(active_root),
        "already_finalized": already_finalized,
        "changed_path_count": sum(
            item["old_relative_path"] != item["new_relative_path"]
            for item in rename_map
        ),
        "counts": inventory["counts"],
        "category_counts": inventory["category_counts"],
        "rename_map": rename_map,
        "removed_from_previous_inventory": inventory[
            "removed_from_previous_inventory"
        ],
        "inventory": inventory,
    }


def stage_plan(plan, stage_root):
    if stage_root.exists():
        raise ShoeFinalizationError("Staging root already exists")
    stage_root.mkdir(parents=True)
    source_by_hash = {
        item["sha256"]: Path(plan["active_root"]).joinpath(
            *item["old_relative_path"].split("/")
        )
        for item in plan["rename_map"]
    }
    for asset in plan["inventory"]["assets"]:
        source = source_by_hash[asset["sha256"]]
        destination = stage_root.joinpath(
            *asset["new_relative_path"].split("/")
        )
        if not source.is_file():
            raise ShoeFinalizationError("Source shoe disappeared: {}".format(source))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if destination.stat().st_size != asset["size_bytes"]:
            raise ShoeFinalizationError("Staged shoe size changed")
        if sha256_file(destination) != asset["sha256"]:
            raise ShoeFinalizationError("Staged shoe hash changed")
    write_json(stage_root / "shoe_inventory.json", plan["inventory"])


def verify_active(plan):
    active_root = Path(plan["active_root"])
    files = sorted(active_root.rglob("*.ccShoes"))
    if len(files) != plan["counts"]["total"]:
        raise ShoeFinalizationError("Final shoe count is incorrect")
    for asset in plan["inventory"]["assets"]:
        path = active_root.joinpath(*asset["new_relative_path"].split("/"))
        if not path.is_file() or sha256_file(path) != asset["sha256"]:
            raise ShoeFinalizationError(
                "Final verification failed: {}".format(asset["shoe_id"])
            )
    unexpected = [
        path
        for path in active_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() != ".ccshoes"
        and path.name != "shoe_inventory.json"
    ]
    if unexpected:
        raise ShoeFinalizationError("Unexpected final files remain")
    return len(files)


def execute_plan(clothing_root, run_dir, plan):
    clothing_root = clothing_root.resolve()
    run_dir = run_dir.resolve()
    active_root = Path(plan["active_root"]).resolve()
    if is_within(run_dir, clothing_root):
        raise ShoeFinalizationError("Run directory must be outside clothing root")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ShoeFinalizationError("Execution run directory is not empty")
    run_dir.mkdir(parents=True, exist_ok=True)
    if plan["already_finalized"]:
        return {
            "active_root": str(active_root),
            "backup_root": None,
            "final_shoe_count": verify_active(plan),
            "no_op": True,
        }
    stage_root = run_dir / "staged_shoes"
    backup_root = run_dir / "source_backup"
    active_backup = backup_root / "shoes_before_curated_reindex"
    stage_plan(plan, stage_root)
    backup_root.mkdir(parents=True, exist_ok=False)

    moved_old = False
    moved_new = False
    try:
        shutil.move(str(active_root), str(active_backup))
        moved_old = True
        shutil.move(str(stage_root), str(active_root))
        moved_new = True
        final_count = verify_active(plan)
    except Exception:
        failed_root = run_dir / "failed_active_shoes"
        if moved_new and active_root.exists():
            shutil.move(str(active_root), str(failed_root))
        if moved_old and active_backup.exists() and not active_root.exists():
            shutil.move(str(active_backup), str(active_root))
        raise

    return {
        "active_root": str(active_root),
        "backup_root": str(backup_root),
        "final_shoe_count": final_count,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clothing-root", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    clothing_root = Path(args.clothing_root).resolve()
    run_dir = Path(args.run_dir).resolve()
    plan = build_plan(clothing_root)
    report = {
        "schema_version": 1,
        "operation": plan["operation"],
        "mode": "execute" if args.execute else "dry_run",
        "success": False,
        "plan": plan,
        "execution": None,
    }
    if args.execute:
        report["execution"] = execute_plan(clothing_root, run_dir, plan)
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
    report["success"] = True
    write_json(run_dir / "migration_report.json", report)
    print(
        json.dumps(
            {
                "success": True,
                "mode": report["mode"],
                "counts": plan["counts"],
                "category_counts": plan["category_counts"],
                "renamed": plan["changed_path_count"],
                "run_dir": str(run_dir),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
