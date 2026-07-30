"""Sync selected Hair Builder paths into the stable appearance catalog."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CANONICAL = os.path.join(
    SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json"
)
DEFAULT_SELECTED = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_asset_catalog_v1.json"
)


class SyncError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise SyncError(
                "{} IDs are invalid or duplicated".format(label)
            )
        result[value] = item
    return result


def sync(canonical_path, selected_path, output_path):
    canonical_path = os.path.realpath(os.path.abspath(canonical_path))
    selected_path = os.path.realpath(os.path.abspath(selected_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    for path in (canonical_path, selected_path):
        if not os.path.isfile(path):
            raise SyncError("Input is missing: {}".format(path))

    canonical = read_json(canonical_path)
    selected = read_json(selected_path)
    canonical_assets = indexed(
        canonical.get("assets") or [],
        "asset_id",
        "Canonical asset",
    )
    selected_assets = indexed(
        selected.get("assets") or [],
        "asset_id",
        "Selected asset",
    )
    if len(selected_assets) != 60:
        raise SyncError(
            "Expected 60 selected scalp-hair assets; found {}".format(
                len(selected_assets)
            )
        )
    missing = sorted(set(selected_assets).difference(canonical_assets))
    if missing:
        raise SyncError(
            "Selected assets are absent from the canonical catalog: {}".format(
                ", ".join(missing)
            )
        )

    migration_count = 0
    for asset_id, selected_asset in selected_assets.items():
        canonical_asset = canonical_assets[asset_id]
        for invariant in ("asset_form", "asset_type", "display_name", "slot"):
            if canonical_asset.get(invariant) != selected_asset.get(invariant):
                raise SyncError(
                    "{} differs for {}".format(invariant, asset_id)
                )
        path = selected_asset.get("preferred_path")
        if not isinstance(path, str) or not os.path.isfile(path):
            raise SyncError(
                "Selected physical path is missing for {}".format(asset_id)
            )
        if os.path.normcase(
            os.path.realpath(canonical_asset.get("preferred_path"))
        ) != os.path.normcase(os.path.realpath(path)):
            migration_count += 1
        canonical_asset.update(
            {
                "hair_builder_pack": copy.deepcopy(
                    selected_asset["hair_builder_pack"]
                ),
                "path_migration": copy.deepcopy(
                    selected_asset.get("path_migration")
                ),
                "preferred_origin": selected_asset["preferred_origin"],
                "preferred_path": path,
                "presentation_prior": copy.deepcopy(
                    selected_asset["presentation_prior"]
                ),
                "sex_hint": selected_asset["sex_hint"],
                "variants": copy.deepcopy(selected_asset["variants"]),
            }
        )
        if canonical_asset["path_migration"] is None:
            canonical_asset.pop("path_migration")

    syncs = [
        item
        for item in canonical.get("selected_pool_syncs") or []
        if item.get("catalog_id") != selected.get("catalog_id")
    ]
    syncs.append(
        {
            "asset_count": len(selected_assets),
            "catalog_id": selected.get("catalog_id"),
            "catalog_path": selected_path,
            "synced_at": now(),
        }
    )
    canonical["selected_pool_syncs"] = syncs
    canonical["generated_at"] = now()
    write_json(canonical, output_path)
    return {
        "asset_count": len(selected_assets),
        "migration_count": migration_count,
        "output": output_path,
        "success": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default=DEFAULT_CANONICAL)
    parser.add_argument("--selected", default=DEFAULT_SELECTED)
    parser.add_argument("--output", default=DEFAULT_CANONICAL)
    args = parser.parse_args()
    print(
        json.dumps(
            sync(args.canonical, args.selected, args.output),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
