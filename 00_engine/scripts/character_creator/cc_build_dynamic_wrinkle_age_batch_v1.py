"""Build the six-case CC5 neutral dynamic-wrinkle age matrix."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_build_dynamic_wrinkle_age_batch_v1_config.json"
)
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
    SCRIPT_DIR, "cc_dynamic_wrinkle_age_batch_v1.json"
)
BATCH_ID = "cc5_neutral_dynamic_wrinkle_age_matrix_v1"
FACE_PROFILE = "face_identity_safety_v1"
FACIAL_ASSEMBLY_ORDER = [
    "skin",
    "age_morph",
    "dynamic_wrinkle_profile",
    "teeth",
    "eyebrows",
    "eyelashes",
    "eyes_material_only",
    "facial_hair",
    "scalp_hair",
    "shared_hair_pigmentation",
]


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


def dynamic_profiles_by_sex(registry):
    dynamic = (
        (registry.get("component_pools") or {})
        .get("dynamic_wrinkles")
        or {}
    )
    if float(dynamic.get("fixed_strength", -1.0)) != 1.0:
        raise BatchBuildError(
            "Dynamic wrinkle production strength must be 1.0"
        )
    profiles = indexed(
        dynamic.get("profiles") or [],
        "sex",
        "Dynamic wrinkle profile",
    )
    if set(profiles) != {"female", "male"}:
        raise BatchBuildError(
            "Expected one female and one male dynamic wrinkle profile"
        )
    for sex, profile in profiles.items():
        if profile.get("application_mode") != (
            "inherit_neutral_bodyfit_profile_set_strength"
        ):
            raise BatchBuildError(
                "{} wrinkle profile has unsupported mode".format(sex)
            )
        resolved_file(
            profile.get("path"),
            "{} dynamic wrinkle source asset".format(sex),
        )
    return profiles


def build_preset(
    face_preset,
    skin_asset,
    wrinkle_profile,
    age_level,
):
    preset = copy.deepcopy(face_preset)
    sex = preset["sex"]
    sex_code = "M" if sex == "male" else "F"
    age_label = age_level["label"]
    preset_id = "WRINKLE_{}_{}".format(
        sex_code,
        age_label.upper(),
    )
    for key in (
        "appearance_asset_ids",
        "appearance_cleanup",
        "appearance_recipe",
        "appearance_recipe_id",
    ):
        preset.pop(key, None)
    preset.update(
        {
            "age_label": age_label,
            "appearance_validation_plan": {
                "asset_load_pacing": {
                    "default_after_seconds": 2.0,
                    "default_before_seconds": 1.0,
                    "slots": {
                        "skin": {
                            "after_seconds": 10.0,
                            "before_seconds": 4.0,
                        },
                    },
                },
                "domain": "face_identity",
                "dynamic_wrinkle_validation": {
                    "baseline_strength": 0.0,
                    "pose_ids": [
                        "blink_bilateral_front",
                        "brow_raise_front",
                        "brow_down_front",
                        "squint_bilateral_front",
                        "smile_front",
                    ],
                    "target_strength": 1.0,
                },
                "pose_profile": FACE_PROFILE,
                "required_views": [
                    "reconstructed_preview",
                    "face_front",
                    "face_three_quarter",
                    "face_profile",
                    "face_blink_bilateral_front",
                    "face_brow_raise_front",
                    "face_brow_down_front",
                    "face_squint_front",
                    "face_smile_front",
                ],
                "verification_mode": "dynamic_wrinkle_strength_pair",
                "visual_limitation": (
                    "One safe adult V3 face per sex. The .rlWrinkle "
                    "asset is a hashed reference because CC5 cannot load "
                    "it through the public Python API; the matching "
                    "neutral BodyFit profile is inherited."
                ),
            },
            "character_id": preset_id,
            "dynamic_wrinkle_age_validation": {
                "age_label": age_label,
                "baseline_strength": 0.0,
                "primary_seed_id": (
                    preset["face_generation"]["primary_seed_id"]
                ),
                "profile_id": wrinkle_profile["asset_id"],
                "skin_asset_id": skin_asset["asset_id"],
                "target_strength": 1.0,
            },
            "dynamic_wrinkle_profile_id": wrinkle_profile["asset_id"],
            "dynamic_wrinkle_strength": 1.0,
            "facial_assembly": {
                "age_morph_id": age_level["morph_id"],
                "application_order": list(FACIAL_ASSEMBLY_ORDER),
                "asset_ids": [skin_asset["asset_id"]],
                "dynamic_wrinkle_profile": copy.deepcopy(
                    wrinkle_profile
                ),
            },
            "full_face_elder_weight": float(age_level["weight"]),
            "preset_id": preset_id,
            "review_status": "dynamic-wrinkle-age-candidate",
            "skin_asset_id": skin_asset["asset_id"],
            "visible_gray_fraction": 0.0,
        }
    )
    return preset


def build(
    config_path=DEFAULT_CONFIG,
    registry_path=DEFAULT_REGISTRY,
    face_batch_path=DEFAULT_FACE_BATCH,
    appearance_catalog_path=DEFAULT_APPEARANCE_CATALOG,
    output_path=DEFAULT_OUTPUT,
):
    config_path = resolved_file(config_path, "Dynamic wrinkle config")
    registry_path = resolved_file(registry_path, "Facial production registry")
    face_batch_path = resolved_file(face_batch_path, "V3 face batch")
    appearance_catalog_path = resolved_file(
        appearance_catalog_path,
        "Appearance catalog",
    )

    config = read_json(config_path)
    if int(config.get("schema_version", -1)) != 1:
        raise BatchBuildError("Unsupported dynamic wrinkle config schema")
    registry = read_json(registry_path)
    face_batch = read_json(face_batch_path)
    appearance_catalog = read_json(appearance_catalog_path)
    validation_design = registry.get("validation_design") or {}
    expected_count = int(
        validation_design.get("dynamic_wrinkle_case_count", 0)
    )
    if expected_count != 6:
        raise BatchBuildError(
            "Production registry dynamic wrinkle count must be 6"
        )

    face_presets = primary_seed_presets(face_batch)
    safe_seed_ids = config.get("safe_face_seed_ids") or {}
    if set(safe_seed_ids) != {"female", "male"}:
        raise BatchBuildError(
            "safe_face_seed_ids must define female and male"
        )
    selected_faces = {}
    for sex in ("male", "female"):
        seed_id = safe_seed_ids[sex]
        preset = face_presets.get(seed_id)
        if preset is None or preset.get("sex") != sex:
            raise BatchBuildError(
                "Safe {} face is missing or sex-mismatched: {}".format(
                    sex,
                    seed_id,
                )
            )
        selected_faces[sex] = preset

    production_skins = indexed(
        (registry.get("component_pools") or {}).get("skins") or [],
        "asset_id",
        "Production skin pool",
    )
    catalog_assets = indexed(
        appearance_catalog.get("assets") or [],
        "asset_id",
        "Appearance catalog",
    )
    skin_asset_ids = config.get("skin_asset_ids") or {}
    if set(skin_asset_ids) != {"female", "male"}:
        raise BatchBuildError(
            "skin_asset_ids must define female and male"
        )
    selected_skins = {}
    for sex in ("male", "female"):
        asset_id = skin_asset_ids[sex]
        if asset_id not in production_skins:
            raise BatchBuildError(
                "Skin is outside the production pool: {}".format(
                    asset_id
                )
            )
        asset = catalog_assets.get(asset_id)
        if (
            asset is None
            or asset.get("slot") != "skin"
            or asset.get("sex_hint") != sex
        ):
            raise BatchBuildError(
                "Skin is missing, wrong-slot, or sex-mismatched: {}".format(
                    asset_id
                )
            )
        resolved_file(
            asset.get("preferred_path"),
            "{} skin asset".format(sex),
        )
        selected_skins[sex] = asset

    age = registry.get("age") or {}
    age_morph = age.get("morph") or {}
    age_levels = copy.deepcopy(age.get("levels") or [])
    if [item.get("label") for item in age_levels] != [
        "young",
        "middle",
        "older",
    ]:
        raise BatchBuildError(
            "Age levels must be young, middle, older"
        )
    if not isinstance(age_morph.get("id"), str):
        raise BatchBuildError("Age morph ID is missing")
    for item in age_levels:
        item["morph_id"] = age_morph["id"]

    profiles = dynamic_profiles_by_sex(registry)
    presets = []
    for sex in ("male", "female"):
        for age_level in age_levels:
            presets.append(
                build_preset(
                    selected_faces[sex],
                    selected_skins[sex],
                    profiles[sex],
                    age_level,
                )
            )
    preset_ids = [item["preset_id"] for item in presets]
    if len(presets) != expected_count:
        raise BatchBuildError(
            "Expected {} wrinkle cases, built {}".format(
                expected_count,
                len(presets),
            )
        )
    if len(preset_ids) != len(set(preset_ids)):
        raise BatchBuildError("Dynamic wrinkle preset IDs are not unique")

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
                "age_labels": [
                    item["label"] for item in age_levels
                ],
                "case_count": len(presets),
                "safe_face_seed_ids": copy.deepcopy(safe_seed_ids),
                "skin_asset_ids": copy.deepcopy(skin_asset_ids),
                "strength_pair": {
                    "baseline": 0.0,
                    "target": 1.0,
                },
            },
            "sources": {
                "appearance_catalog": {
                    "path": appearance_catalog_path,
                    "sha256": sha256_file(appearance_catalog_path),
                },
                "config": {
                    "path": config_path,
                    "sha256": sha256_file(config_path),
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
            "status": "dynamic-wrinkle-age-validation-pending",
        }
    )
    write_json(document, output_path)
    return document


def main():
    parser = argparse.ArgumentParser(
        description="Build the six-case neutral dynamic-wrinkle matrix."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--face-batch", default=DEFAULT_FACE_BATCH)
    parser.add_argument(
        "--appearance-catalog",
        default=DEFAULT_APPEARANCE_CATALOG,
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build(
        config_path=args.config,
        registry_path=args.registry,
        face_batch_path=args.face_batch,
        appearance_catalog_path=args.appearance_catalog,
        output_path=os.path.realpath(os.path.abspath(args.output)),
    )
    print(
        "Built {} dynamic wrinkle cases -> {}".format(
            document["character_count"],
            os.path.realpath(os.path.abspath(args.output)),
        )
    )


if __name__ == "__main__":
    main()
