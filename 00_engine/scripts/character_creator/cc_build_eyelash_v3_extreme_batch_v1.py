"""Build the CC5 HD Natural eyelash matrix on four V3 extreme faces."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY = os.path.join(
    SCRIPT_DIR, "cc_facial_production_registry_v1.json"
)
DEFAULT_FACE_BATCH = os.path.join(
    SCRIPT_DIR, "cc_face_quality_batch_v3_validation.json"
)
DEFAULT_APPEARANCE_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_eyelash_v3_extreme_batch_v1.json"
)
BATCH_ID = "cc5_hd_natural_eyelash_v3_extreme_v1"
EYELASH_PROFILE = "eyelash_visibility_v1"


class BatchBuildError(RuntimeError):
    pass


def now():
    return (
        datetime.datetime.now()
        .astimezone()
        .replace(microsecond=0)
        .isoformat()
    )


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        handle.write("\n")
    os.replace(temporary, path)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolved_file(path, label):
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise BatchBuildError("{} is missing: {}".format(label, path))
    return path


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            raise BatchBuildError("{} item has no {}".format(label, key))
        if value in result:
            raise BatchBuildError(
                "{} contains duplicate {} {!r}".format(label, key, value)
            )
        result[value] = item
    return result


def primary_seed_presets(face_batch):
    result = {}
    for preset in face_batch.get("presets") or []:
        generation = preset.get("face_generation") or {}
        seed_id = generation.get("primary_seed_id")
        if generation.get("strength_tier") != "baseline":
            continue
        if not isinstance(seed_id, str) or not seed_id:
            continue
        if seed_id in result:
            raise BatchBuildError(
                "Duplicate baseline primary seed {!r}".format(seed_id)
            )
        result[seed_id] = preset
    return result


def build_preset(face_preset, eyelash_asset, asset_index, face_index):
    preset = copy.deepcopy(face_preset)
    seed_id = preset["face_generation"]["primary_seed_id"]
    sex_code = "M" if preset.get("sex") == "male" else "F"
    preset_id = "EYLV3_{:02d}_{}_{}".format(
        asset_index,
        sex_code,
        seed_id,
    )
    preset.update(
        {
            "appearance_asset_ids": [eyelash_asset["asset_id"]],
            "appearance_recipe": {
                "assets": [
                    {
                        "asset_form": eyelash_asset.get("asset_form"),
                        "asset_id": eyelash_asset["asset_id"],
                        "display_name": eyelash_asset["display_name"],
                        "sex_hint": eyelash_asset.get("sex_hint"),
                        "slot": "eyelashes",
                    }
                ],
                "source_preset_id": face_preset["preset_id"],
            },
            "appearance_recipe_id": "EYLV3_{:02d}_V1".format(
                asset_index
            ),
            "appearance_validation_plan": {
                "asset_load_pacing": {
                    "default_after_seconds": 2.0,
                    "default_before_seconds": 1.0,
                    "slots": {
                        "eyelashes": {
                            "after_seconds": 12.0,
                            "before_seconds": 6.0,
                        },
                    },
                },
                "domain": "eyelashes",
                "pose_profile": EYELASH_PROFILE,
                "required_views": [
                    "face_front",
                    "face_three_quarter",
                    "face_profile",
                    "eyelash_blink_front",
                    "eyelash_asymmetric_blink_front",
                    "eyelash_wide_front",
                ],
                "verification_mode": "scene_inventory",
                "visual_limitation": (
                    "Four V3 extreme adult faces only. Child and "
                    "third-party head generations require separate "
                    "validation."
                ),
            },
            "character_id": preset_id,
            "eyelash_v3_extreme": {
                "asset_index": asset_index,
                "face_index": face_index,
                "primary_seed_id": seed_id,
                "sex": preset.get("sex"),
            },
            "preset_id": preset_id,
            "review_status": "eyelash-v3-extreme-candidate",
        }
    )
    return preset


def build(
    registry_path=DEFAULT_REGISTRY,
    face_batch_path=DEFAULT_FACE_BATCH,
    appearance_catalog_path=DEFAULT_APPEARANCE_CATALOG,
    output_path=DEFAULT_OUTPUT,
):
    registry_path = resolved_file(registry_path, "Facial production registry")
    face_batch_path = resolved_file(face_batch_path, "V3 face batch")
    appearance_catalog_path = resolved_file(
        appearance_catalog_path,
        "Appearance catalog",
    )

    registry = read_json(registry_path)
    face_batch = read_json(face_batch_path)
    appearance_catalog = read_json(appearance_catalog_path)
    validation_design = registry.get("validation_design") or {}
    seed_ids = list(
        validation_design.get("v3_extreme_primary_face_seed_ids") or []
    )
    expected_count = int(
        validation_design.get("eyelash_v3_extreme_case_count", 0)
    )
    if len(seed_ids) != 4 or len(set(seed_ids)) != 4:
        raise BatchBuildError(
            "Production registry must select four unique extreme faces"
        )
    if expected_count != 36:
        raise BatchBuildError(
            "Production registry eyelash extreme count must be 36"
        )

    registry_assets = list(
        (registry.get("component_pools") or {}).get("eyelashes") or []
    )
    if len(registry_assets) != 9:
        raise BatchBuildError(
            "Production registry must contain nine approved eyelashes"
        )
    registry_by_id = indexed(
        registry_assets,
        "asset_id",
        "Production eyelash pool",
    )
    catalog_by_id = indexed(
        appearance_catalog.get("assets") or [],
        "asset_id",
        "Appearance catalog",
    )
    eyelash_assets = []
    for asset_id in sorted(registry_by_id):
        asset = catalog_by_id.get(asset_id)
        if asset is None:
            raise BatchBuildError(
                "Approved eyelash is missing from catalog: {}".format(
                    asset_id
                )
            )
        if asset.get("slot") != "eyelashes":
            raise BatchBuildError(
                "Approved asset is not an eyelash: {}".format(asset_id)
            )
        asset_path = resolved_file(
            asset.get("preferred_path"),
            "Eyelash asset {}".format(asset_id),
        )
        if os.path.realpath(registry_by_id[asset_id]["path"]) != asset_path:
            raise BatchBuildError(
                "Registry and catalog paths disagree for {}".format(
                    asset_id
                )
            )
        eyelash_assets.append(asset)

    face_presets = primary_seed_presets(face_batch)
    selected_faces = []
    for seed_id in seed_ids:
        if seed_id not in face_presets:
            raise BatchBuildError(
                "Extreme face seed is not a V3 baseline: {}".format(
                    seed_id
                )
            )
        selected_faces.append(face_presets[seed_id])

    presets = []
    for asset_index, eyelash_asset in enumerate(eyelash_assets, 1):
        for face_index, face_preset in enumerate(selected_faces, 1):
            presets.append(
                build_preset(
                    face_preset,
                    eyelash_asset,
                    asset_index,
                    face_index,
                )
            )
    preset_ids = [item["preset_id"] for item in presets]
    if len(presets) != expected_count:
        raise BatchBuildError(
            "Expected {} eyelash cases, built {}".format(
                expected_count,
                len(presets),
            )
        )
    if len(preset_ids) != len(set(preset_ids)):
        raise BatchBuildError("Eyelash preset IDs are not unique")

    document = copy.deepcopy(face_batch)
    document.update(
        {
            "appearance_catalog": {
                "catalog_id": appearance_catalog.get("catalog_id"),
                "path": appearance_catalog_path,
                "sha256": sha256_file(appearance_catalog_path),
            },
            "character_count": len(presets),
            "generated_at": now(),
            "library_id": BATCH_ID,
            "presets": presets,
            "selection": {
                "asset_count": len(eyelash_assets),
                "asset_ids": [
                    item["asset_id"] for item in eyelash_assets
                ],
                "case_count": len(presets),
                "face_count": len(selected_faces),
                "primary_seed_ids": seed_ids,
                "purpose": (
                    "Regression of all approved HD Natural eyelashes "
                    "against four V3 extreme adult faces"
                ),
            },
            "sources": {
                "appearance_catalog": {
                    "path": appearance_catalog_path,
                    "sha256": sha256_file(appearance_catalog_path),
                },
                "facial_production_registry": {
                    "path": registry_path,
                    "sha256": sha256_file(registry_path),
                },
                "v3_face_batch": {
                    "path": face_batch_path,
                    "sha256": sha256_file(face_batch_path),
                },
            },
            "status": "eyelash-v3-extreme-validation-pending",
        }
    )
    write_json(document, output_path)
    return document


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build the CC5 HD Natural eyelash V3 extreme-face matrix."
        )
    )
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--face-batch", default=DEFAULT_FACE_BATCH)
    parser.add_argument(
        "--appearance-catalog",
        default=DEFAULT_APPEARANCE_CATALOG,
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build(
        registry_path=args.registry,
        face_batch_path=args.face_batch,
        appearance_catalog_path=args.appearance_catalog,
        output_path=os.path.realpath(os.path.abspath(args.output)),
    )
    print(
        "Built {} eyelash extreme cases -> {}".format(
            document["character_count"],
            os.path.realpath(os.path.abspath(args.output)),
        )
    )


if __name__ == "__main__":
    main()
