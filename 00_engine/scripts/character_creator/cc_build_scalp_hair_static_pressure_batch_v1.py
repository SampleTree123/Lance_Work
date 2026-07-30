"""Build the CC5 scalp-hair static pressure matrix."""

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
DEFAULT_HAIR_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_asset_catalog_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_static_pressure_batch_v1.json"
)
BATCH_ID = "cc5_scalp_hair_static_pressure_v1"
SCALP_HAIR_PROFILE = "scalp_hair_visibility_v1"


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


def build_preset(face_preset, hair_asset, asset_index, face_index):
    preset = copy.deepcopy(face_preset)
    seed_id = preset["face_generation"]["primary_seed_id"]
    sex_code = "M" if preset.get("sex") == "male" else "F"
    preset_id = "HAIRPRESS_{:02d}_{}_{}".format(
        asset_index,
        sex_code,
        seed_id,
    )
    preset.update(
        {
            "appearance_asset_ids": [hair_asset["asset_id"]],
            "appearance_recipe": {
                "assets": [
                    {
                        "asset_form": "group",
                        "asset_id": hair_asset["asset_id"],
                        "display_name": hair_asset["display_name"],
                        "sex_hint": "unknown",
                        "slot": "scalp_hair",
                    }
                ],
                "source_preset_id": face_preset["preset_id"],
            },
            "appearance_recipe_id": "HAIRPRESS_{:02d}_V1".format(
                asset_index
            ),
            "appearance_validation_plan": {
                "asset_load_pacing": {
                    "default_after_seconds": 0.0,
                    "default_before_seconds": 0.0,
                    "slots": {
                        "scalp_hair": {
                            "after_seconds": 12.0,
                            "before_seconds": 8.0,
                        }
                    },
                },
                "domain": "scalp_hair",
                "pose_profile": SCALP_HAIR_PROFILE,
                "required_views": [
                    "reconstructed_preview",
                    "face_front",
                    "face_three_quarter",
                    "face_profile",
                    "hair_rear_three_quarter",
                    "hair_rear",
                ],
                "subject_position_offset": {
                    "x": -25.0,
                    "z": 6.0,
                },
                "verification_mode": "scene_inventory",
                "visual_limitation": (
                    "Static pressure test on four V3 extreme adult faces. "
                    "Presentation mismatch is intentional and does not "
                    "alter the default production presentation filter."
                ),
            },
            "character_id": preset_id,
            "preset_id": preset_id,
            "review_status": "scalp-hair-static-pressure-candidate",
            "scalp_hair_static_pressure": {
                "asset_index": asset_index,
                "face_index": face_index,
                "primary_seed_id": seed_id,
                "presentation_mode": "technical_cross_sex_allowed",
                "silhouette_family": hair_asset.get("silhouette_family"),
            },
        }
    )
    return preset


def build(
    registry_path=DEFAULT_REGISTRY,
    face_batch_path=DEFAULT_FACE_BATCH,
    hair_catalog_path=DEFAULT_HAIR_CATALOG,
    output_path=DEFAULT_OUTPUT,
):
    registry_path = resolved_file(registry_path, "Facial production registry")
    face_batch_path = resolved_file(face_batch_path, "V3 face batch")
    hair_catalog_path = resolved_file(hair_catalog_path, "Scalp-hair catalog")

    registry = read_json(registry_path)
    face_batch = read_json(face_batch_path)
    hair_catalog = read_json(hair_catalog_path)
    validation_design = registry.get("validation_design") or {}
    pressure_ids = list(
        validation_design.get("scalp_hair_static_pressure_asset_ids") or []
    )
    seed_ids = list(
        validation_design.get("v3_extreme_primary_face_seed_ids") or []
    )
    expected_count = int(
        validation_design.get(
            "scalp_hair_static_pressure_case_count", 0
        )
    )
    if len(pressure_ids) != 16 or len(set(pressure_ids)) != 16:
        raise BatchBuildError(
            "Production registry must select 16 unique pressure assets"
        )
    if len(seed_ids) != 4 or len(set(seed_ids)) != 4:
        raise BatchBuildError(
            "Production registry must select four unique extreme faces"
        )
    if expected_count != 64:
        raise BatchBuildError(
            "Production registry static pressure count must be 64"
        )

    production_hair = indexed(
        (registry.get("component_pools") or {}).get("scalp_hair") or [],
        "asset_id",
        "Production scalp-hair pool",
    )
    catalog_hair = indexed(
        hair_catalog.get("assets") or [],
        "asset_id",
        "Scalp-hair catalog",
    )
    face_presets = primary_seed_presets(face_batch)

    selected_hair = []
    for asset_id in pressure_ids:
        if asset_id not in production_hair:
            raise BatchBuildError(
                "Pressure asset is not in production pool: {}".format(
                    asset_id
                )
            )
        if asset_id not in catalog_hair:
            raise BatchBuildError(
                "Pressure asset is not in selected catalog: {}".format(
                    asset_id
                )
            )
        asset = copy.deepcopy(catalog_hair[asset_id])
        production = production_hair[asset_id]
        asset["accepted_sexes"] = list(
            production.get("accepted_sexes") or []
        )
        asset["female_presentation_score"] = production.get(
            "female_presentation_score"
        )
        asset["silhouette_family"] = production.get(
            "silhouette_family"
        )
        selected_hair.append(asset)

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
    for asset_index, hair_asset in enumerate(selected_hair, 1):
        for face_index, face_preset in enumerate(selected_faces, 1):
            presets.append(
                build_preset(
                    face_preset,
                    hair_asset,
                    asset_index,
                    face_index,
                )
            )
    preset_ids = [item["preset_id"] for item in presets]
    if len(presets) != expected_count:
        raise BatchBuildError(
            "Expected {} pressure cases, built {}".format(
                expected_count,
                len(presets),
            )
        )
    if len(preset_ids) != len(set(preset_ids)):
        raise BatchBuildError("Static pressure preset IDs are not unique")

    document = copy.deepcopy(face_batch)
    document.update(
        {
            "appearance_catalog": {
                "catalog_id": hair_catalog.get("catalog_id"),
                "path": hair_catalog_path,
                "sha256": sha256_file(hair_catalog_path),
            },
            "character_count": len(presets),
            "generated_at": now(),
            "library_id": BATCH_ID,
            "presets": presets,
            "selection": {
                "asset_count": len(selected_hair),
                "asset_ids": pressure_ids,
                "case_count": len(presets),
                "face_count": len(selected_faces),
                "primary_seed_ids": seed_ids,
                "purpose": (
                    "Static scalp-hair pressure matrix across the "
                    "highest-risk approved assets and V3 extreme faces"
                ),
            },
            "sources": {
                "facial_production_registry": {
                    "path": registry_path,
                    "sha256": sha256_file(registry_path),
                },
                "scalp_hair_catalog": {
                    "path": hair_catalog_path,
                    "sha256": sha256_file(hair_catalog_path),
                },
                "v3_face_batch": {
                    "path": face_batch_path,
                    "sha256": sha256_file(face_batch_path),
                },
            },
            "status": "static-pressure-validation-pending",
        }
    )
    write_json(document, output_path)
    return document


def main():
    parser = argparse.ArgumentParser(
        description="Build the CC5 scalp-hair static pressure matrix."
    )
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--face-batch", default=DEFAULT_FACE_BATCH)
    parser.add_argument("--hair-catalog", default=DEFAULT_HAIR_CATALOG)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build(
        registry_path=args.registry,
        face_batch_path=args.face_batch,
        hair_catalog_path=args.hair_catalog,
        output_path=os.path.realpath(os.path.abspath(args.output)),
    )
    print(
        "Built {} scalp-hair pressure cases -> {}".format(
            document["character_count"],
            os.path.realpath(os.path.abspath(args.output)),
        )
    )


if __name__ == "__main__":
    main()
