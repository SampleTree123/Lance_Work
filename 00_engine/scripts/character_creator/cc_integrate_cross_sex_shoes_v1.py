"""Integrate approved male shoe copies into the female shared CC shoe pool."""

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


REVISION_ID = "curated_20260814_v2_cross_sex"
CATEGORY_ORDER = {
    "female": ("Boots", "Flats", "Heels", "Sandals"),
    "male": ("Boots", "Casual", "Formal", "Sandals", "Sport"),
}
APPROVED_CROSS_SEX_SOURCES = {
    "M001": "Boots",
    "M003": "Boots",
    "M023": "Flats",
    "M024": "Flats",
    "M026": "Sandals",
    "M027": "Sandals",
    "M028": "Sandals",
    "M029": "Sandals",
}
EXPECTED_COUNTS = {"female": 25, "male": 35}


class ShoeIntegrationError(RuntimeError):
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


def parse_shoe_id(filename):
    match = re.match(r"^([FM])(\d{3})_", filename, flags=re.IGNORECASE)
    if not match:
        raise ShoeIntegrationError(
            "Shoe filename has no recognized ID: {}".format(filename)
        )
    return "{}{}".format(match.group(1).upper(), match.group(2))


def discover_native_restore_plan(clothing_root):
    engine_root = Path(__file__).resolve().parents[2]
    source_root = (
        engine_root
        / "outputs"
        / "character_creator_bridge"
        / "artifacts"
        / "shoe_library_organization"
        / "run_20260814_v1"
        / "source_backup"
        / "external_family_sources"
    )
    manifest_count = 0
    missing = []
    for sex in ("female", "male"):
        for manifest_path in sorted((clothing_root / sex).glob("*/outfit_family.json")):
            manifest = read_json(manifest_path)
            for asset in manifest.get("assets", []):
                if asset.get("slot") != "shoes":
                    continue
                manifest_count += 1
                destination = manifest_path.parent.joinpath(
                    *str(asset["path"]).replace("\\", "/").split("/")
                )
                expected_hash = str(asset["sha256"]).lower()
                if destination.is_file():
                    if sha256_file(destination) != expected_hash:
                        raise ShoeIntegrationError(
                            "Native shoe hash changed: {}".format(destination)
                        )
                    continue
                relative = destination.relative_to(clothing_root)
                source = source_root / relative
                if not source.is_file() or sha256_file(source) != expected_hash:
                    raise ShoeIntegrationError(
                        "Missing native shoe has no valid backup: {}".format(
                            destination
                        )
                    )
                missing.append(
                    {
                        "family_id": manifest["family_id"],
                        "asset_id": asset["asset_id"],
                        "sha256": expected_hash,
                        "size_bytes": int(asset["size_bytes"]),
                        "source": str(source.resolve()),
                        "destination": str(destination.resolve()),
                    }
                )
    if manifest_count != 51:
        raise ShoeIntegrationError(
            "Unexpected native shoe manifest count: {}".format(manifest_count)
        )
    missing_families = {item["family_id"] for item in missing}
    if missing_families not in (
        set(),
        {"male.redsoul", "male.cyberpunk_locked"},
    ):
        raise ShoeIntegrationError(
            "Unexpected native shoe restore set: {}".format(
                sorted(missing_families)
            )
        )
    return manifest_count, missing


def scan_shared_pool(active_root, previous_inventory):
    previous_assets = previous_inventory.get("assets", [])
    previous_by_key = {}
    previous_by_id = {}
    for asset in previous_assets:
        key = (asset["sex"], str(asset["sha256"]).lower())
        if key in previous_by_key or asset["shoe_id"] in previous_by_id:
            raise ShoeIntegrationError("Previous inventory identity is ambiguous")
        previous_by_key[key] = asset
        previous_by_id[asset["shoe_id"]] = asset

    inventory_path = active_root / "shoe_inventory.json"
    records = []
    seen_by_sex = set()
    copied_source_ids = set()
    for path in sorted(active_root.rglob("*"), key=lambda item: str(item).lower()):
        if not path.is_file():
            continue
        if path.resolve() == inventory_path.resolve():
            continue
        if path.suffix.lower() != ".ccshoes":
            raise ShoeIntegrationError(
                "Unexpected file in shared shoe root: {}".format(path)
            )
        relative = path.relative_to(active_root)
        digest = sha256_file(path)
        if len(relative.parts) == 3:
            sex_folder, category, _ = relative.parts
            sex = sex_folder.lower()
            if sex not in CATEGORY_ORDER or category not in CATEGORY_ORDER[sex]:
                raise ShoeIntegrationError(
                    "Unknown structured shoe path: {}".format(relative)
                )
            key = (sex, digest)
            if key not in previous_by_key:
                raise ShoeIntegrationError(
                    "Structured shoe is absent from inventory: {}".format(relative)
                )
            previous = previous_by_key[key]
            copied_from = previous.get("copied_from")
            if copied_from:
                copied_source_ids.add(copied_from["shoe_id"])
            existing_id = parse_shoe_id(path.name)
            is_new_copy = False
        elif len(relative.parts) == 2 and relative.parts[0] == "Female":
            source_matches = [
                asset
                for (sex, asset_hash), asset in previous_by_key.items()
                if sex == "male" and asset_hash == digest
            ]
            if len(source_matches) != 1:
                raise ShoeIntegrationError(
                    "Female root copy has no unique male source: {}".format(relative)
                )
            previous = source_matches[0]
            source_id = previous["shoe_id"]
            if source_id not in APPROVED_CROSS_SEX_SOURCES:
                raise ShoeIntegrationError(
                    "Female copy is not approved: {}".format(source_id)
                )
            sex = "female"
            category = APPROVED_CROSS_SEX_SOURCES[source_id]
            copied_source_ids.add(source_id)
            existing_id = source_id
            is_new_copy = True
        else:
            raise ShoeIntegrationError(
                "Shoe is outside the accepted layout: {}".format(relative)
            )

        identity_key = (sex, digest)
        if identity_key in seen_by_sex:
            raise ShoeIntegrationError(
                "Duplicate geometry within one sex pool: {}".format(relative)
            )
        seen_by_sex.add(identity_key)
        records.append(
            {
                "path": path.resolve(),
                "relative_path": relative.as_posix(),
                "sha256": digest,
                "size_bytes": path.stat().st_size,
                "sex": sex,
                "category": category,
                "existing_id": existing_id,
                "is_new_copy": is_new_copy,
                "previous": previous,
            }
        )

    if copied_source_ids != set(APPROVED_CROSS_SEX_SOURCES):
        raise ShoeIntegrationError(
            "Cross-sex source set is incomplete: {}".format(
                sorted(copied_source_ids)
            )
        )
    counts = collections.Counter(record["sex"] for record in records)
    if dict(counts) != EXPECTED_COUNTS:
        raise ShoeIntegrationError(
            "Unexpected shared shoe counts: {}".format(dict(counts))
        )
    unique_geometry = {record["sha256"] for record in records}
    if len(unique_geometry) != 52:
        raise ShoeIntegrationError(
            "Unexpected unique geometry count: {}".format(len(unique_geometry))
        )
    return records


def build_plan(clothing_root):
    clothing_root = clothing_root.resolve()
    active_root = (clothing_root / "both" / "shoes").resolve()
    inventory_path = active_root / "shoe_inventory.json"
    if not active_root.is_dir() or not is_within(active_root, clothing_root):
        raise ShoeIntegrationError("Active shoe root is invalid")
    if not inventory_path.is_file():
        raise ShoeIntegrationError("Previous shoe inventory is missing")
    previous_inventory = read_json(inventory_path)
    if previous_inventory.get("library_id") != "cc_shared_shoes_v1":
        raise ShoeIntegrationError("Previous inventory has an unknown ID")
    already_integrated = previous_inventory.get("revision_id") == REVISION_ID

    records = scan_shared_pool(active_root, previous_inventory)
    native_manifest_count, native_restore_plan = discover_native_restore_plan(
        clothing_root
    )
    rank = {
        sex: {category: index for index, category in enumerate(categories)}
        for sex, categories in CATEGORY_ORDER.items()
    }
    records.sort(
        key=lambda item: (
            item["sex"],
            rank[item["sex"]][item["category"]],
            1 if item["is_new_copy"] else 0,
            int(item["existing_id"][1:]),
            item["sha256"],
        )
    )

    counters = collections.Counter()
    assets = []
    rename_map = []
    cross_sex_copies = []
    for record in records:
        sex = record["sex"]
        counters[sex] += 1
        prefix = "F" if sex == "female" else "M"
        shoe_id = "{}{:03d}".format(prefix, counters[sex])
        previous = record["previous"]
        family_slug = slug(str(previous["family_id"]).split(".", 1)[-1])
        display_slug = slug(previous["display_name"])
        filename = "{}_{}_{}_{}.ccShoes".format(
            shoe_id, record["category"], family_slug, display_slug
        )
        sex_folder = "Female" if sex == "female" else "Male"
        relative_path = (
            Path(sex_folder) / record["category"] / filename
        ).as_posix()
        final_path = active_root.joinpath(*relative_path.split("/"))

        asset = dict(previous)
        asset.update(
            {
                "shoe_id": shoe_id,
                "sex": sex,
                "style_category": record["category"],
                "new_relative_path": relative_path,
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
                "source_paths": [str(final_path)],
                "source_path_count": 1,
                "pool_scope": "{}_shared".format(sex),
                "previous_shoe_id": record["existing_id"],
                "previous_relative_path": record["relative_path"],
            }
        )
        if record["is_new_copy"]:
            copied_from = {
                "shoe_id": previous["shoe_id"],
                "sex": "male",
                "family_id": previous["family_id"],
                "sha256": record["sha256"],
            }
            asset.update(
                {
                    "classification_status": "user_approved_cross_sex_copy_v1",
                    "copied_from": copied_from,
                    "native_family_eligible": False,
                }
            )
            cross_sex_copies.append(
                {
                    "female_shoe_id": shoe_id,
                    "male_source_shoe_id": previous["shoe_id"],
                    "sha256": record["sha256"],
                }
            )
        else:
            asset.setdefault("native_family_eligible", False)
            if asset.get("copied_from"):
                cross_sex_copies.append(
                    {
                        "female_shoe_id": shoe_id,
                        "male_source_shoe_id": asset["copied_from"]["shoe_id"],
                        "sha256": record["sha256"],
                    }
                )
        assets.append(asset)
        rename_map.append(
            {
                "sha256": record["sha256"],
                "sex": sex,
                "old_shoe_id": record["existing_id"],
                "new_shoe_id": shoe_id,
                "old_relative_path": record["relative_path"],
                "new_relative_path": relative_path,
            }
        )

    identities = {(asset["sex"], asset["shoe_id"]) for asset in assets}
    paths = {asset["new_relative_path"] for asset in assets}
    if len(identities) != 60 or len(paths) != 60:
        raise ShoeIntegrationError("Final shared shoe identities are not unique")

    category_counts = collections.Counter(
        "{}/{}".format(asset["sex"], asset["style_category"])
        for asset in assets
    )
    removed_records = previous_inventory.get(
        "removed_from_previous_inventory", []
    )
    inventory = {
        "schema_version": 3,
        "library_id": "cc_shared_shoes_v1",
        "revision_id": REVISION_ID,
        "generated_at": now(),
        "active_root": str(active_root),
        "curation_status": "user_curated_cross_sex_copies_recorded",
        "numbering_policy": "contiguous_per_sex_after_user_curation",
        "style_policy": "user_curated_categories",
        "identity_policy": (
            "same geometry may have one identity per sex; duplicates within "
            "one sex are forbidden"
        ),
        "counts": {
            "female": counters["female"],
            "male": counters["male"],
            "physical_assets": len(assets),
            "unique_geometry": len({asset["sha256"] for asset in assets}),
            "cross_sex_copies": len(cross_sex_copies),
            "removed_from_initial_revision": len(removed_records),
        },
        "category_counts": dict(sorted(category_counts.items())),
        "assets": assets,
        "cross_sex_copies": sorted(
            cross_sex_copies, key=lambda item: item["female_shoe_id"]
        ),
        "removed_from_previous_inventory": removed_records,
        "policy_boundaries": {
            "native_family_pool": (
                "A family's own Shoes directory remains authoritative for "
                "that family even when a shoe is absent from the shared pool."
            ),
            "shared_pool": (
                "Used to define per-family allowed fallback pools for outfits "
                "without native shoes; a pool may contain multiple shoe IDs."
            ),
            "shared_deletion": (
                "Removing a shared copy never removes or disables the native "
                "family shoe."
            ),
        },
        "downstream_status": {
            "native_outfit_family_json": (
                "native shoe paths remain family-local and are independently "
                "validated"
            ),
            "fallback_assignment_pools": "pending user definition",
            "visual_validation": "pending exact outfit and motion checks",
        },
    }
    return {
        "schema_version": 1,
        "operation": "integrate_cross_sex_shoes_v1",
        "generated_at": now(),
        "active_root": str(active_root),
        "already_integrated": already_integrated,
        "changed_path_count": sum(
            item["old_relative_path"] != item["new_relative_path"]
            for item in rename_map
        ),
        "counts": inventory["counts"],
        "category_counts": inventory["category_counts"],
        "rename_map": rename_map,
        "native_manifest_shoe_count": native_manifest_count,
        "native_restore_plan": native_restore_plan,
        "inventory": inventory,
    }


def stage_shared_pool(plan, stage_root):
    if stage_root.exists():
        raise ShoeIntegrationError("Staging root already exists")
    stage_root.mkdir(parents=True)
    sources = {
        (item["sex"], item["sha256"]): Path(plan["active_root"]).joinpath(
            *item["old_relative_path"].split("/")
        )
        for item in plan["rename_map"]
    }
    for asset in plan["inventory"]["assets"]:
        source = sources[(asset["sex"], asset["sha256"])]
        destination = stage_root.joinpath(
            *asset["new_relative_path"].split("/")
        )
        if not source.is_file():
            raise ShoeIntegrationError("Source shoe disappeared: {}".format(source))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if destination.stat().st_size != asset["size_bytes"]:
            raise ShoeIntegrationError("Staged shoe size changed")
        if sha256_file(destination) != asset["sha256"]:
            raise ShoeIntegrationError("Staged shoe hash changed")
    write_json(stage_root / "shoe_inventory.json", plan["inventory"])


def verify_shared_pool(plan):
    active_root = Path(plan["active_root"])
    files = list(active_root.rglob("*.ccShoes"))
    if len(files) != plan["counts"]["physical_assets"]:
        raise ShoeIntegrationError("Final shared shoe count is incorrect")
    for asset in plan["inventory"]["assets"]:
        path = active_root.joinpath(*asset["new_relative_path"].split("/"))
        if not path.is_file() or sha256_file(path) != asset["sha256"]:
            raise ShoeIntegrationError(
                "Final shared shoe failed verification: {}".format(
                    asset["shoe_id"]
                )
            )
    return len(files)


def verify_native_manifest_shoes(clothing_root):
    verified = 0
    for sex in ("female", "male"):
        for manifest_path in sorted((clothing_root / sex).glob("*/outfit_family.json")):
            manifest = read_json(manifest_path)
            for asset in manifest.get("assets", []):
                if asset.get("slot") != "shoes":
                    continue
                path = manifest_path.parent.joinpath(
                    *str(asset["path"]).replace("\\", "/").split("/")
                )
                if not path.is_file() or sha256_file(path) != asset["sha256"]:
                    raise ShoeIntegrationError(
                        "Native manifest shoe failed verification: {}".format(path)
                    )
                verified += 1
    if verified != 51:
        raise ShoeIntegrationError(
            "Final native shoe count is incorrect: {}".format(verified)
        )
    return verified


def execute_plan(clothing_root, run_dir, plan):
    clothing_root = clothing_root.resolve()
    run_dir = run_dir.resolve()
    active_root = Path(plan["active_root"]).resolve()
    if is_within(run_dir, clothing_root):
        raise ShoeIntegrationError("Run directory must be outside clothing root")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ShoeIntegrationError("Execution run directory is not empty")
    run_dir.mkdir(parents=True, exist_ok=True)
    if (
        plan["already_integrated"]
        and plan["changed_path_count"] == 0
        and not plan["native_restore_plan"]
    ):
        return {
            "active_root": str(active_root),
            "backup_root": None,
            "shared_shoe_count": verify_shared_pool(plan),
            "native_manifest_shoe_count": verify_native_manifest_shoes(
                clothing_root
            ),
            "restored_native_shoes": [],
            "no_op": True,
        }

    stage_root = run_dir / "staged_shoes"
    backup_root = run_dir / "source_backup"
    active_backup = backup_root / "shoes_before_cross_sex_integration"
    stage_shared_pool(plan, stage_root)
    backup_root.mkdir(parents=True, exist_ok=False)

    moved_old = False
    moved_new = False
    restored_targets = []
    try:
        shutil.move(str(active_root), str(active_backup))
        moved_old = True
        shutil.move(str(stage_root), str(active_root))
        moved_new = True
        for item in plan["native_restore_plan"]:
            source = Path(item["source"])
            destination = Path(item["destination"])
            if destination.exists():
                raise ShoeIntegrationError(
                    "Native restore destination unexpectedly exists: {}".format(
                        destination
                    )
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if sha256_file(destination) != item["sha256"]:
                raise ShoeIntegrationError("Restored native shoe hash changed")
            restored_targets.append(destination)
        shared_count = verify_shared_pool(plan)
        native_count = verify_native_manifest_shoes(clothing_root)
    except Exception:
        for destination in reversed(restored_targets):
            if destination.exists():
                destination.unlink()
            try:
                destination.parent.rmdir()
            except OSError:
                pass
        failed_root = run_dir / "failed_active_shoes"
        if moved_new and active_root.exists():
            shutil.move(str(active_root), str(failed_root))
        if moved_old and active_backup.exists() and not active_root.exists():
            shutil.move(str(active_backup), str(active_root))
        raise

    return {
        "active_root": str(active_root),
        "backup_root": str(backup_root),
        "shared_shoe_count": shared_count,
        "native_manifest_shoe_count": native_count,
        "restored_native_shoes": [str(path) for path in restored_targets],
        "no_op": False,
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
                "changed_paths": plan["changed_path_count"],
                "native_restore_count": len(plan["native_restore_plan"]),
                "run_dir": str(run_dir),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
