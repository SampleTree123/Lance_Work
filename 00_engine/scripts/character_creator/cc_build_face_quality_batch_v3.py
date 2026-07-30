"""Build the CC5 V3 face baseline and BodyFit validation matrix."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BODY_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_body_preset_library_v1.json"
)
DEFAULT_SEED_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_face_seed_library_v1.json"
)
DEFAULT_IDENTITY_POLICY = os.path.join(
    SCRIPT_DIR, "cc_face_identity_policy_v1.json"
)
DEFAULT_RECIPES = os.path.join(
    SCRIPT_DIR, "cc_face_recipes_v3_200.json"
)
DEFAULT_FACIAL_REGISTRY = os.path.join(
    SCRIPT_DIR, "cc_facial_production_registry_v1.json"
)
DEFAULT_APPEARANCE_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_face_quality_batch_v3_validation.json"
)
PIPELINE_ID = "complete_primary_face_plus_local_morphs_v1"
FACIAL_PROFILE_APPLICATION_MODE = "selected_avatar_content_load"
FACIAL_ASSEMBLY_ORDER = (
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
)
POSE_PROFILE = "face_identity_safety_v1"
FACE_CAMERAS = {
    "female": (
        r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera"
        r"\Headshot Ref\Ref Cam Female L.ccCam"
    ),
    "male": (
        r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera"
        r"\Headshot Ref\Ref Cam Male L.ccCam"
    ),
}
FACE_CAMERA_REFERENCE_TOP_Z = {
    "female": 166.9602508544922,
    "male": 175.70965576171875,
}


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
    os.makedirs(os.path.dirname(path), exist_ok=True)
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


def canonical_local_fingerprint(primary_seed_id, local_morphs):
    payload = {
        "local_morphs": [
            (
                item["id"],
                round(float(item["baseline_weight"]), 8),
                round(float(item["weight"]), 8),
            )
            for item in sorted(
                local_morphs, key=lambda value: value["id"]
            )
        ],
        "pipeline": PIPELINE_ID,
        "primary_face_seed_id": primary_seed_id,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def average_body(bodies, sex):
    matches = [
        item
        for item in bodies
        if item.get("sex") == sex
        and item.get("body_class") == "average"
    ]
    if len(matches) != 1:
        raise BatchBuildError(
            "Expected one average {} body".format(sex)
        )
    return matches[0]


def validate_asset_reference(reference, label, extension=None):
    if not isinstance(reference, dict):
        raise BatchBuildError("{} must be an object".format(label))
    path = reference.get("path")
    expected_hash = reference.get("sha256")
    if (
        not isinstance(path, str)
        or not os.path.isfile(path)
        or not isinstance(expected_hash, str)
        or len(expected_hash) != 64
    ):
        raise BatchBuildError(
            "{} path or SHA256 is invalid".format(label)
        )
    path = os.path.realpath(os.path.abspath(path))
    if extension and not path.lower().endswith(extension.lower()):
        raise BatchBuildError(
            "{} must use {}".format(label, extension)
        )
    if sha256_file(path) != expected_hash:
        raise BatchBuildError("{} hash changed".format(label))
    result = copy.deepcopy(reference)
    result["path"] = path
    return result


def resolve_facial_profile(seed_library, seed):
    policy = seed_library.get("facial_profile_policy") or {}
    application_mode = policy.get("application_mode")
    if application_mode != FACIAL_PROFILE_APPLICATION_MODE:
        raise BatchBuildError(
            "Unsupported Facial Profile application mode"
        )
    seed_id = seed["seed_id"]
    overrides = policy.get("seed_overrides") or {}
    defaults = policy.get("default_by_sex") or {}
    if seed_id in overrides:
        reference = overrides[seed_id]
        policy_binding = "seed_override"
    else:
        reference = defaults.get(seed["sex"])
        policy_binding = "default_by_sex"
    result = validate_asset_reference(
        reference,
        "{} Facial Profile".format(seed_id),
        extension=".ccFacialProfile",
    )
    result["application_mode"] = application_mode
    result["policy_binding"] = policy_binding
    return result


def select_matrix_components(registry, sex):
    skins = [
        item
        for item in (registry.get("component_pools", {}).get("skins") or [])
        if item.get("sex") == sex
        and item.get("region_label") == "African"
    ]
    if not skins:
        raise BatchBuildError(
            "No high-contrast {} matrix skin".format(sex)
        )
    skin = sorted(skins, key=lambda item: item["asset_id"])[0]
    eyes = [
        item
        for item in (registry.get("component_pools", {}).get("eyes") or [])
        if item.get("display_name") == "Eyes_03"
    ]
    if len(eyes) != 1:
        raise BatchBuildError("Expected one Eyes_03 asset")
    profiles = [
        item
        for item in (
            registry.get("component_pools", {})
            .get("dynamic_wrinkles", {})
            .get("profiles")
            or []
        )
        if item.get("sex") == sex
    ]
    if len(profiles) != 1:
        raise BatchBuildError(
            "Expected one {} dynamic wrinkle profile".format(sex)
        )
    age = registry.get("age") or {}
    age_morph = age.get("morph") or {}
    registry_order = registry.get("assembly_order")
    wrinkle_pool = (
        registry.get("component_pools", {})
        .get("dynamic_wrinkles", {})
    )
    if (
        not isinstance(age_morph.get("id"), str)
        or not isinstance(registry_order, list)
        or not all(
            item in registry_order
            for item in FACIAL_ASSEMBLY_ORDER
        )
        or not isinstance(
            wrinkle_pool.get("fixed_strength"), (int, float)
        )
    ):
        raise BatchBuildError(
            "Facial registry assembly policy is incomplete"
        )
    return {
        "age_label": "young",
        "dynamic_wrinkle_profile_id": profiles[0]["asset_id"],
        "dynamic_wrinkle_strength": float(
            wrinkle_pool["fixed_strength"]
        ),
        "eye_asset_id": eyes[0]["asset_id"],
        "facial_assembly": {
            "age_morph_id": age_morph["id"],
            "application_order": list(FACIAL_ASSEMBLY_ORDER),
            "asset_ids": [
                skin["asset_id"],
                eyes[0]["asset_id"],
            ],
            "dynamic_wrinkle_profile": copy.deepcopy(profiles[0]),
        },
        "full_face_elder_weight": 0.0,
        "matrix_material_policy": {
            "eyes": eyes[0]["display_name"],
            "purpose": "high_contrast_eye_occlusion_review",
            "skin": skin["display_name"],
        },
        "skin_asset_id": skin["asset_id"],
    }


def common_body_fields(body):
    return {
        "base_avatar": body["base_avatar"],
        "body_and_junction_fingerprint": body[
            "body_and_junction_fingerprint"
        ],
        "body_class": body["body_class"],
        "bodyfit_id": body["preset_id"],
        "sex": body["sex"],
        "source_project": body["source_project"],
        "target_body_morphs": body["target_body_morphs"],
        "target_junction_morphs": body[
            "target_junction_morphs"
        ],
    }


def validation_fields(sex):
    return {
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
            "integrated_facial_assembly_validation": {
                "render_static_hair_views": False,
                "required_invariants": [
                    "body_and_junction_unchanged",
                    "face_identity_matches_recipe",
                    "eye_geometry_preserved",
                    "eye_support_preserved",
                ],
            },
            "face_camera_reference_top_z": FACE_CAMERA_REFERENCE_TOP_Z[sex],
            "pose_profile": POSE_PROFILE,
            "verification_mode": "primary_profile_matrix",
        },
        "face_camera": FACE_CAMERAS[sex],
    }


def baseline_preset(seed, body, seed_library, components):
    local_morphs = []
    preset_id = "V3BASE_{}".format(seed["seed_id"])
    result = common_body_fields(body)
    result.update(validation_fields(seed["sex"]))
    result.update(copy.deepcopy(components))
    result.update(
        {
            "character_id": preset_id,
            "face_generation": {
                "pipeline": PIPELINE_ID,
                "primary_seed_id": seed["seed_id"],
                "strength_tier": "baseline",
            },
            "face_recipe_id": preset_id,
            "local_face_morphs": local_morphs,
            "local_morph_fingerprint": canonical_local_fingerprint(
                seed["seed_id"], local_morphs
            ),
            "preset_id": preset_id,
            "review_status": "v3-primary-baseline-candidate",
            "source_facial_profile": resolve_facial_profile(
                seed_library, seed
            ),
            "source_head_preset": validate_asset_reference(
                seed.get("source_head_preset"),
                "{} Head Preset".format(seed["seed_id"]),
                extension=".ccAvatarPreset",
            ),
        }
    )
    return result


def select_random_recipe(recipes, sex, tier, used_primary_ids):
    candidates = [
        item
        for item in recipes
        if item.get("sex") == sex
        and item.get("strength_tier") == tier
        and item.get("primary_face_seed_id") not in used_primary_ids
    ]
    if not candidates:
        candidates = [
            item
            for item in recipes
            if item.get("sex") == sex
            and item.get("strength_tier") == tier
        ]
    if not candidates:
        raise BatchBuildError(
            "No {} {} random face recipe".format(sex, tier)
        )
    return sorted(
        candidates, key=lambda item: item["face_recipe_id"]
    )[0]


def random_preset(recipe, body, components):
    preset_id = "V3RANDOM_{}_{}".format(
        body["preset_id"], recipe["face_recipe_id"]
    )
    result = common_body_fields(body)
    result.update(validation_fields(recipe["sex"]))
    result.update(copy.deepcopy(components))
    result.update(
        {
            "character_id": preset_id,
            "face_generation": {
                "modified_regions": recipe[
                    "modified_regions"
                ],
                "pipeline": PIPELINE_ID,
                "primary_seed_id": recipe[
                    "primary_face_seed_id"
                ],
                "recipe_seed": recipe["recipe_seed"],
                "strength_tier": recipe["strength_tier"],
            },
            "face_recipe_id": recipe["face_recipe_id"],
            "local_face_morphs": recipe["local_morphs"],
            "local_morph_fingerprint": recipe[
                "local_morph_fingerprint"
            ],
            "preset_id": preset_id,
            "review_status": "v3-random-bodyfit-candidate",
            "source_facial_profile": copy.deepcopy(
                recipe["source_facial_profile"]
            ),
            "source_head_preset": copy.deepcopy(
                recipe["source_head_preset"]
            ),
        }
    )
    return result


def build_batch(
    body_library_path,
    seed_library_path,
    identity_policy_path,
    recipes_path,
    output_path,
    facial_registry_path=DEFAULT_FACIAL_REGISTRY,
    appearance_catalog_path=DEFAULT_APPEARANCE_CATALOG,
):
    paths = [
        os.path.realpath(os.path.abspath(value))
        for value in (
            body_library_path,
            seed_library_path,
            identity_policy_path,
            recipes_path,
            facial_registry_path,
            appearance_catalog_path,
        )
    ]
    for path in paths:
        if not os.path.isfile(path):
            raise BatchBuildError("Input is missing: {}".format(path))
    (
        body_library_path,
        seed_library_path,
        identity_policy_path,
        recipes_path,
        facial_registry_path,
        appearance_catalog_path,
    ) = paths
    body_library = read_json(body_library_path)
    seed_library = read_json(seed_library_path)
    identity_policy = read_json(identity_policy_path)
    recipe_document = read_json(recipes_path)
    facial_registry = read_json(facial_registry_path)
    appearance_catalog = read_json(appearance_catalog_path)
    bodies = body_library.get("presets") or []
    recipes = recipe_document.get("recipes") or []
    if len(bodies) != 8:
        raise BatchBuildError("Expected eight BodyFit presets")
    if (
        recipe_document.get("pipeline") != PIPELINE_ID
        or len(recipes) != 200
    ):
        raise BatchBuildError("V3 recipe document is invalid")
    production_ids_by_sex = (
        recipe_document.get("strategy", {}).get(
            "production_primary_seed_ids_by_sex"
        )
        or {}
    )
    if set(production_ids_by_sex) != {"male", "female"}:
        raise BatchBuildError(
            "Recipe document has no production primary seed policy"
        )
    production_ids = {
        item
        for values in production_ids_by_sex.values()
        for item in values
    }
    seed_index = {
        item["seed_id"]: item
        for item in (seed_library.get("seeds") or [])
    }
    if (
        not production_ids
        or not production_ids.issubset(seed_index)
    ):
        raise BatchBuildError(
            "Recipe document references unknown production seeds"
        )
    seeds = [seed_index[item] for item in sorted(production_ids)]
    components_by_sex = {
        sex: select_matrix_components(facial_registry, sex)
        for sex in ("male", "female")
    }
    catalog_ids = {
        item.get("asset_id")
        for item in (appearance_catalog.get("assets") or [])
    }
    required_component_ids = {
        asset_id
        for components in components_by_sex.values()
        for asset_id in components["facial_assembly"]["asset_ids"]
    }
    if not required_component_ids.issubset(catalog_ids):
        raise BatchBuildError(
            "Matrix components are missing from the appearance catalog"
        )
    for sex in ("male", "female"):
        expected = set(production_ids_by_sex[sex])
        actual = {
            item["seed_id"]
            for item in seeds
            if item.get("sex") == sex
        }
        if expected != actual or len(actual) < 2:
            raise BatchBuildError(
                "Invalid {} production primary seed policy".format(
                    sex
                )
            )

    presets = []
    for sex in ("male", "female"):
        body = average_body(bodies, sex)
        for seed in sorted(
            [item for item in seeds if item["sex"] == sex],
            key=lambda item: item["seed_id"],
        ):
            presets.append(
                baseline_preset(
                    seed,
                    body,
                    seed_library,
                    components_by_sex[sex],
                )
            )

    used_primary_ids = set()
    tier_by_body_class = {
        "lean": "normal",
        "average": "strong",
        "athletic": "normal",
        "heavy": "strong",
    }
    random_selection = []
    for body in bodies:
        tier = tier_by_body_class[body["body_class"]]
        recipe = select_random_recipe(
            recipes,
            body["sex"],
            tier,
            used_primary_ids,
        )
        used_primary_ids.add(recipe["primary_face_seed_id"])
        presets.append(
            random_preset(
                recipe,
                body,
                components_by_sex[body["sex"]],
            )
        )
        random_selection.append(
            {
                "bodyfit_id": body["preset_id"],
                "face_recipe_id": recipe["face_recipe_id"],
                "primary_face_seed_id": recipe[
                    "primary_face_seed_id"
                ],
                "strength_tier": tier,
            }
        )

    output_path = os.path.realpath(os.path.abspath(output_path))
    baseline_count = len(seeds)
    document = {
        "body_application_mode": "source_project",
        "character_count": len(presets),
        "expected_eyeball_move_weight": 0.0,
        "appearance_catalog": {
            "catalog_id": appearance_catalog.get("catalog_id"),
            "path": appearance_catalog_path,
        },
        "face_resources": {
            "identity_policy": identity_policy_path,
            "identity_policy_id": identity_policy.get("policy_id"),
            "identity_policy_sha256": sha256_file(
                identity_policy_path
            ),
            "seed_library": seed_library_path,
            "seed_library_id": seed_library.get("library_id"),
            "seed_library_sha256": sha256_file(seed_library_path),
        },
        "generated_at": now(),
        "library_id": "adult_face_v3_dynamic_validation_v2",
        "pipeline": PIPELINE_ID,
        "presets": presets,
        "preview_lightroom": body_library.get(
            "preview_lightroom"
        ),
        "schema_version": 1,
        "selection": {
            "primary_baseline_count": baseline_count,
            "random_bodyfit_count": 8,
            "random_bodyfit_selection": random_selection,
        },
        "source_body_library": {
            "library_id": body_library.get("library_id"),
            "path": body_library_path,
            "sha256": sha256_file(body_library_path),
        },
        "source_face_recipes": {
            "path": recipes_path,
            "recipe_set_id": recipe_document.get(
                "recipe_set_id"
            ),
            "sha256": sha256_file(recipes_path),
        },
        "source_facial_registry": {
            "path": facial_registry_path,
            "registry_id": facial_registry.get("registry_id"),
            "sha256": sha256_file(facial_registry_path),
        },
        "strategy": recipe_document.get("strategy", {}),
        "status": "quality-review-only",
    }
    write_json(document, output_path)
    return {
        "baseline_count": baseline_count,
        "character_count": len(presets),
        "output": output_path,
        "random_bodyfit_count": 8,
        "success": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--body-library", default=DEFAULT_BODY_LIBRARY
    )
    parser.add_argument(
        "--seed-library", default=DEFAULT_SEED_LIBRARY
    )
    parser.add_argument(
        "--identity-policy", default=DEFAULT_IDENTITY_POLICY
    )
    parser.add_argument("--recipes", default=DEFAULT_RECIPES)
    parser.add_argument(
        "--facial-registry", default=DEFAULT_FACIAL_REGISTRY
    )
    parser.add_argument(
        "--appearance-catalog",
        default=DEFAULT_APPEARANCE_CATALOG,
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build_batch(
                args.body_library,
                args.seed_library,
                args.identity_policy,
                args.recipes,
                args.output,
                args.facial_registry,
                args.appearance_catalog,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
