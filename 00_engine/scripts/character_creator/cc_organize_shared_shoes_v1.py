"""Normalize the curated CC shoe pool into sex and provisional style folders."""

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


STYLE_BY_FAMILY_ID = {
    "female.dress_collection": "Formal",
    "female.pretty_dresses": "Formal",
    "male.1920s_collection": "Formal",
    "male.casual_01_04": "Casual",
    "male.cheer_leader": "Sport",
    "male.cyberpunk_locked": "Boots",
    "male.dash": "Casual",
    "male.dawkins": "Casual",
    "male.hippasuta": "Casual",
    "male.kilt": "Traditional",
    "male.lederhosen": "Traditional",
    "male.lift_haul": "Boots",
    "male.lincoln": "Formal",
    "male.mercenery": "Boots",
    "male.mesh_it_up": "Boots",
    "male.oahu": "Sandals",
    "male.owen": "Boots",
    "male.pop_style": "Casual",
    "male.redsoul": "Boots",
    "male.streetscape": "Casual",
    "male.streetstyle": "Casual",
    "male.summer": "Casual",
    "male.underbelly": "Casual",
    "male.vacation": "Sandals",
    "male.white_tie": "Formal",
    "male.workout": "Sport",
}


class ShoeOrganizationError(RuntimeError):
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


def natural_key(value):
    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
    )


def slug(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    result = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value).strip("_")
    return result or "Asset"


def discover_manifest_shoes(clothing_root):
    records = []
    for sex in ("female", "male"):
        for manifest_path in sorted((clothing_root / sex).glob("*/outfit_family.json")):
            manifest = read_json(manifest_path)
            family_id = manifest.get("family_id")
            if family_id not in STYLE_BY_FAMILY_ID and any(
                item.get("slot") == "shoes"
                for item in manifest.get("assets", [])
            ):
                raise ShoeOrganizationError(
                    "Missing style mapping for {}".format(family_id)
                )
            for asset in manifest.get("assets", []):
                if asset.get("slot") != "shoes":
                    continue
                old_path = manifest_path.parent.joinpath(
                    *str(asset["path"]).replace("\\", "/").split("/")
                )
                records.append(
                    {
                        "sex": sex,
                        "family_id": family_id,
                        "family_display_name": manifest.get("display_name"),
                        "display_name": asset.get("display_name"),
                        "sha256": str(asset["sha256"]).lower(),
                        "size_bytes": int(asset["size_bytes"]),
                        "manifest_path": str(manifest_path),
                        "manifest_asset_id": asset.get("asset_id"),
                        "old_family_path": str(old_path),
                        "style_category": STYLE_BY_FAMILY_ID[family_id],
                    }
                )
    return records


def infer_unregistered_record(path, shoe_root, digest, size_bytes):
    relative = path.relative_to(shoe_root)
    if not relative.parts or relative.parts[0].lower() != "female":
        raise ShoeOrganizationError(
            "Unregistered shoe is not in the female source pool: {}".format(path)
        )
    name = path.stem.lower()
    if "heel" not in name:
        raise ShoeOrganizationError(
            "Unregistered female shoe has no safe provisional style: {}".format(path)
        )
    return {
        "sex": "female",
        "family_id": "shared.female_heels",
        "family_display_name": "Shared female heels",
        "display_name": path.stem,
        "sha256": digest,
        "size_bytes": size_bytes,
        "manifest_path": None,
        "manifest_asset_id": None,
        "old_family_path": None,
        "style_category": "Heels",
    }


def build_plan(clothing_root):
    clothing_root = clothing_root.resolve()
    shoe_root = (clothing_root / "both" / "shoes").resolve()
    if not shoe_root.is_dir() or not is_within(shoe_root, clothing_root):
        raise ShoeOrganizationError("Active shoe root is invalid")

    inventory_path = shoe_root / "shoe_inventory.json"
    inventory_by_hash = {}
    if inventory_path.is_file():
        inventory = read_json(inventory_path)
        if inventory.get("library_id") != "cc_shared_shoes_v1":
            raise ShoeOrganizationError("Active shoe inventory has an unknown library ID")
        for asset in inventory.get("assets", []):
            digest = str(asset.get("sha256", "")).lower()
            if not digest or digest in inventory_by_hash:
                raise ShoeOrganizationError("Active shoe inventory has duplicate hashes")
            inventory_by_hash[digest] = asset

    manifest_records = discover_manifest_shoes(clothing_root)
    manifests_by_hash = collections.defaultdict(list)
    for record in manifest_records:
        manifests_by_hash[record["sha256"]].append(record)

    physical_by_hash = collections.defaultdict(list)
    for path in sorted(shoe_root.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() == inventory_path.resolve():
            continue
        if path.suffix.lower() != ".ccshoes":
            raise ShoeOrganizationError(
                "Unexpected file in active shoe root: {}".format(path)
            )
        digest = sha256_file(path)
        physical_by_hash[digest].append(path.resolve())

    if inventory_by_hash and set(inventory_by_hash) != set(physical_by_hash):
        raise ShoeOrganizationError(
            "Active shoe files no longer match shoe_inventory.json"
        )

    recovered = []
    for digest, records in manifests_by_hash.items():
        if digest in physical_by_hash:
            continue
        source = Path(records[0]["old_family_path"]).resolve()
        if not source.is_file() or not is_within(source, clothing_root):
            raise ShoeOrganizationError(
                "Manifest shoe is missing from both locations: {}".format(
                    records[0]["display_name"]
                )
            )
        if sha256_file(source) != digest:
            raise ShoeOrganizationError(
                "Recovered shoe hash changed: {}".format(source)
            )
        physical_by_hash[digest].append(source)
        recovered.append(str(source))

    candidates = []
    for digest, paths in physical_by_hash.items():
        paths = sorted(paths, key=lambda value: str(value).lower())
        size_bytes = paths[0].stat().st_size
        if any(path.stat().st_size != size_bytes for path in paths):
            raise ShoeOrganizationError("Equal hashes have unequal sizes")
        manifest_matches = manifests_by_hash.get(digest, [])
        if manifest_matches:
            metadata = dict(manifest_matches[0])
            if any(item["sex"] != metadata["sex"] for item in manifest_matches):
                raise ShoeOrganizationError("A shoe hash crosses sex pools")
        elif digest in inventory_by_hash:
            previous = inventory_by_hash[digest]
            metadata = {
                key: previous.get(key)
                for key in (
                    "sex",
                    "family_id",
                    "family_display_name",
                    "display_name",
                    "sha256",
                    "size_bytes",
                    "manifest_path",
                    "manifest_asset_id",
                    "old_family_path",
                    "style_category",
                )
            }
        else:
            metadata = infer_unregistered_record(
                paths[0], shoe_root, digest, size_bytes
            )
        metadata.update(
            {
                "source_paths": [str(path) for path in paths],
                "source_path_count": len(paths),
                "manifest_origins": manifest_matches,
            }
        )
        candidates.append(metadata)

    candidates.sort(
        key=lambda item: (
            item["sex"],
            natural_key(item["family_id"]),
            natural_key(str(item["display_name"])),
            item["sha256"],
        )
    )
    counters = collections.Counter()
    assets = []
    for item in candidates:
        counters[item["sex"]] += 1
        prefix = "F" if item["sex"] == "female" else "M"
        shoe_id = "{}{:03d}".format(prefix, counters[item["sex"]])
        family_slug = slug(item["family_id"].split(".", 1)[-1])
        display_slug = slug(item["display_name"])
        filename = "{}_{}_{}_{}.ccShoes".format(
            shoe_id,
            item["style_category"],
            family_slug,
            display_slug,
        )
        sex_folder = "Female" if item["sex"] == "female" else "Male"
        relative_path = Path(sex_folder) / item["style_category"] / filename
        asset = dict(item)
        asset.update(
            {
                "shoe_id": shoe_id,
                "new_relative_path": relative_path.as_posix(),
                "classification_status": "provisional_user_review_required",
                "validation_status": "not_tested_on_average_bodyfit",
            }
        )
        assets.append(asset)

    expected = {"female": 17, "male": 41}
    actual = collections.Counter(item["sex"] for item in assets)
    if dict(actual) != expected:
        raise ShoeOrganizationError(
            "Unexpected unique shoe counts: {}".format(dict(actual))
        )

    duplicate_groups = [
        {
            "sha256": item["sha256"],
            "source_paths": item["source_paths"],
            "removed_copy_count": item["source_path_count"] - 1,
        }
        for item in assets
        if item["source_path_count"] > 1
    ]
    return {
        "schema_version": 1,
        "library_id": "cc_shared_shoes_v1",
        "generated_at": now(),
        "active_root": str(shoe_root),
        "numbering_policy": "independent_contiguous_ids_per_sex",
        "style_policy": "provisional_source_family_and_filename_classification",
        "unisex_pool_removed": True,
        "similar_but_nonidentical_assets_removed": False,
        "exact_duplicate_policy": "one_file_per_sha256",
        "counts": {
            "female": actual["female"],
            "male": actual["male"],
            "total": len(assets),
            "physical_source_files": sum(
                item["source_path_count"] for item in assets
            ),
            "exact_duplicate_copies_removed": sum(
                item["removed_copy_count"] for item in duplicate_groups
            ),
            "recovered_manifest_shoes": len(recovered),
        },
        "category_counts": dict(
            sorted(
                collections.Counter(
                    "{}/{}".format(item["sex"], item["style_category"])
                    for item in assets
                ).items()
            )
        ),
        "recovered_source_paths": recovered,
        "exact_duplicate_groups": duplicate_groups,
        "assets": assets,
        "downstream_status": {
            "outfit_family_json": (
                "shoe paths are stale until user curation and shared-pool "
                "reference migration are complete"
            )
        },
    }


def stage_library(plan, stage_root):
    if stage_root.exists():
        raise ShoeOrganizationError("Staging root already exists")
    stage_root.mkdir(parents=True)
    for asset in plan["assets"]:
        source = Path(asset["source_paths"][0])
        destination = stage_root.joinpath(
            *asset["new_relative_path"].split("/")
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if destination.stat().st_size != asset["size_bytes"]:
            raise ShoeOrganizationError("Staged shoe size changed")
        if sha256_file(destination) != asset["sha256"]:
            raise ShoeOrganizationError("Staged shoe hash changed")
    inventory = dict(plan)
    inventory.pop("exact_duplicate_groups", None)
    write_json(stage_root / "shoe_inventory.json", inventory)


def execute_plan(clothing_root, run_dir, plan):
    clothing_root = clothing_root.resolve()
    run_dir = run_dir.resolve()
    active_root = Path(plan["active_root"]).resolve()
    if is_within(run_dir, clothing_root):
        raise ShoeOrganizationError("Run directory must be outside clothing root")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ShoeOrganizationError("Execution run directory is not empty")
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_root = run_dir / "staged_shoes"
    backup_root = run_dir / "source_backup"
    active_backup = backup_root / "shoes_before_organization"
    stage_library(plan, stage_root)

    if not is_within(active_root, clothing_root):
        raise ShoeOrganizationError("Active root escaped clothing root")
    backup_root.mkdir(parents=True, exist_ok=False)
    shutil.move(str(active_root), str(active_backup))
    shutil.move(str(stage_root), str(active_root))

    moved_external = []
    for source_text in plan["recovered_source_paths"]:
        source = Path(source_text).resolve()
        if not source.exists():
            continue
        if not is_within(source, clothing_root):
            raise ShoeOrganizationError("Recovered source escaped clothing root")
        relative = source.relative_to(clothing_root)
        destination = backup_root / "external_family_sources" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        moved_external.append(
            {"source": str(source), "backup": str(destination)}
        )
        try:
            source.parent.rmdir()
        except OSError:
            pass

    final_files = [
        path
        for path in active_root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".ccshoes"
    ]
    if len(final_files) != plan["counts"]["total"]:
        raise ShoeOrganizationError("Final shoe count is incorrect")
    for asset in plan["assets"]:
        final_path = active_root.joinpath(
            *asset["new_relative_path"].split("/")
        )
        if not final_path.is_file() or sha256_file(final_path) != asset["sha256"]:
            raise ShoeOrganizationError(
                "Final shoe verification failed: {}".format(asset["shoe_id"])
            )
    return {
        "active_root": str(active_root),
        "backup_root": str(backup_root),
        "final_shoe_count": len(final_files),
        "moved_external_sources": moved_external,
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
        "operation": "organize_shared_shoes_v1",
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
                "run_dir": str(run_dir),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
