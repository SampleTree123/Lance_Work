"""Build a limited-scope compatibility registry from reviewed CC validations."""

import argparse
import collections
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CATALOG = os.path.join(SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json")
DEFAULT_BATCH = os.path.join(SCRIPT_DIR, "cc_appearance_quality_batch_v1.json")
DEFAULT_VALIDATION = os.path.join(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts",
    "appearance_quality_v1_consolidated_20260723_02",
    "validation_result.json",
)
DEFAULT_REVIEW = os.path.join(SCRIPT_DIR, "cc_appearance_visual_review_v1.json")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_appearance_compatibility_v1.json")


class RegistryError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


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
            raise RegistryError("{} IDs are invalid or duplicated".format(label))
        result[value] = item
    return result


def normalized_paths(value, label):
    values = [value] if isinstance(value, str) else list(value or [])
    if not values:
        raise RegistryError("At least one {} input is required".format(label))
    return [os.path.realpath(os.path.abspath(path)) for path in values]


def merged_index(documents, collection_key, item_key, label):
    result = {}
    for document, source_path in documents:
        current = indexed(document.get(collection_key) or [], item_key, label)
        duplicate_ids = sorted(set(result).intersection(current))
        if duplicate_ids:
            raise RegistryError(
                "{} IDs occur in multiple inputs: {} ({})".format(
                    label,
                    ", ".join(duplicate_ids),
                    source_path,
                )
            )
        result.update(current)
    return result


def build(catalog_path, batch_paths, validation_paths, review_paths, output_path):
    catalog_path = os.path.realpath(os.path.abspath(catalog_path))
    batch_paths = normalized_paths(batch_paths, "batch")
    validation_paths = normalized_paths(validation_paths, "validation")
    review_paths = normalized_paths(review_paths, "visual review")
    paths = [catalog_path] + batch_paths + validation_paths + review_paths
    for path in paths:
        if not os.path.isfile(path):
            raise RegistryError("Input is missing: {}".format(path))

    catalog = read_json(catalog_path)
    batches = [(read_json(path), path) for path in batch_paths]
    validations = [(read_json(path), path) for path in validation_paths]
    reviews_documents = [(read_json(path), path) for path in review_paths]
    assets = indexed(catalog.get("assets") or [], "asset_id", "Appearance asset")
    presets = merged_index(batches, "presets", "preset_id", "Batch preset")
    results = merged_index(
        validations, "results", "preset_id", "Validation result"
    )
    reviews = merged_index(
        reviews_documents, "reviews", "preset_id", "Visual review"
    )
    if set(results) != set(reviews):
        raise RegistryError("Validation and visual review preset sets differ")

    records = collections.defaultdict(list)
    accepted_preset_ids = []
    rejected_combinations = []
    for preset_id in sorted(results):
        result = results[preset_id]
        preset = presets.get(preset_id)
        if preset is None:
            raise RegistryError("Validated preset is absent from batch: {}".format(preset_id))
        visual = reviews[preset_id]
        if result.get("success") is not True:
            raise RegistryError("Validation was not successful: {}".format(preset_id))
        if result.get("appearance_matches_recipe") is not True:
            raise RegistryError("Appearance did not match recipe: {}".format(preset_id))
        morph_policy_ok = result.get("appearance_morphs_within_policy")
        if morph_policy_ok is None:
            morph_policy_ok = result.get(
                "morphs_unchanged_after_appearance"
            )
        if morph_policy_ok is not True:
            raise RegistryError(
                "Appearance changed protected morphs: {}".format(preset_id)
            )
        visual_status = visual.get("visual_status")
        if visual_status not in ("accepted", "rejected"):
            raise RegistryError(
                "Visual review has an unsupported status: {}".format(preset_id)
            )
        if visual_status == "rejected":
            rejected_combinations.append(
                {
                    "preset_id": preset_id,
                    "appearance_recipe_id": preset.get("appearance_recipe_id"),
                    "appearance_asset_ids": preset.get("appearance_asset_ids") or [],
                    "appearance_cleanup": preset.get("appearance_cleanup"),
                    "sex": preset.get("sex"),
                    "bodyfit_id": preset.get("bodyfit_id"),
                    "face_recipe_id": preset.get("face_recipe_id"),
                    "visual_status": visual_status,
                    "visual_notes": visual.get("notes") or [],
                    "source_result_path": result.get("source_result_path"),
                }
            )
            continue
        accepted_preset_ids.append(preset_id)
        for asset_id in preset.get("appearance_asset_ids") or []:
            if asset_id not in assets:
                raise RegistryError("Validated asset is absent from catalog: {}".format(asset_id))
            records[asset_id].append(
                {
                    "preset_id": preset_id,
                    "appearance_recipe_id": preset.get("appearance_recipe_id"),
                    "appearance_asset_ids": preset.get("appearance_asset_ids") or [],
                    "appearance_cleanup": preset.get("appearance_cleanup"),
                    "sex": preset.get("sex"),
                    "bodyfit_id": preset.get("bodyfit_id"),
                    "face_recipe_id": preset.get("face_recipe_id"),
                    "geometry_status": "accepted",
                    "appearance_morphs_within_policy": morph_policy_ok,
                    "appearance_morph_policy": result.get(
                        "appearance_morph_policy"
                    ),
                    "visual_status": visual.get("visual_status"),
                    "visual_notes": visual.get("notes") or [],
                    "source_result_path": result.get("source_result_path"),
                }
            )

    asset_notes = collections.defaultdict(list)
    for review, source_path in reviews_documents:
        for asset_id, notes in (review.get("asset_notes") or {}).items():
            if asset_id not in assets:
                raise RegistryError(
                    "Visual review references an unknown asset: {} ({})".format(
                        asset_id, source_path
                    )
                )
            if not isinstance(notes, list):
                raise RegistryError(
                    "Asset notes must be a list: {} ({})".format(
                        asset_id, source_path
                    )
                )
            for note in notes:
                if note not in asset_notes[asset_id]:
                    asset_notes[asset_id].append(note)

    entries = []
    for asset_id in sorted(records):
        asset = assets[asset_id]
        validations = records[asset_id]
        entries.append(
            {
                "asset_id": asset_id,
                "display_name": asset.get("display_name"),
                "asset_type": asset.get("asset_type"),
                "slot": asset.get("slot"),
                "status": "validated_on_listed_presets",
                "tested_bodyfit_ids": sorted(
                    {item["bodyfit_id"] for item in validations if item["bodyfit_id"]}
                ),
                "tested_face_recipe_ids": sorted(
                    {item["face_recipe_id"] for item in validations if item["face_recipe_id"]}
                ),
                "tested_sexes": sorted({item["sex"] for item in validations}),
                "usage_notes": asset_notes.get(asset_id) or [],
                "validations": validations,
            }
        )

    result = {
        "schema_version": 2,
        "registry_id": "cc_appearance_compatibility_v1",
        "generated_at": now(),
        "catalog_id": catalog.get("catalog_id"),
        "scope": "Compatibility is proven only for the listed presets, not globally.",
        "sources": {
            "catalog": catalog_path,
            "batches": batch_paths,
            "validations": validation_paths,
            "visual_reviews": review_paths,
        },
        "summary": {
            "catalog_asset_count": len(assets),
            "validated_asset_count": len(entries),
            "unvalidated_asset_count": len(assets) - len(entries),
            "reviewed_preset_count": len(results),
            "validated_preset_count": len(accepted_preset_ids),
            "rejected_preset_count": len(rejected_combinations),
        },
        "assets": entries,
        "rejected_combinations": rejected_combinations,
    }
    output_path = os.path.realpath(os.path.abspath(output_path))
    write_json(result, output_path)
    return {"success": True, "output": output_path, "summary": result["summary"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument(
        "--batch",
        dest="batches",
        action="append",
        help="Batch manifest; repeat to merge independent reviewed batches.",
    )
    parser.add_argument(
        "--validation",
        dest="validations",
        action="append",
        help="Validation result; repeat to merge independent reviewed batches.",
    )
    parser.add_argument(
        "--review",
        dest="reviews",
        action="append",
        help="Visual review; repeat to merge independent reviewed batches.",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.catalog,
                args.batches or [DEFAULT_BATCH],
                args.validations or [DEFAULT_VALIDATION],
                args.reviews or [DEFAULT_REVIEW],
                args.output,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
