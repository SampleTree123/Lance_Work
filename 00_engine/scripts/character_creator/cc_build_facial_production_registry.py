"""Build the reviewed CC5 adult facial-component production registry."""

import argparse
import collections
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.realpath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_facial_production_registry_config.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_facial_production_registry_v1.json"
)
DEFAULT_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json"
)
DEFAULT_COMPATIBILITY = os.path.join(
    SCRIPT_DIR, "cc_appearance_compatibility_v1.json"
)
DEFAULT_SKIN_MATRIX = os.path.join(
    SCRIPT_DIR, "cc_skin_age_matrix_v1.json"
)
DEFAULT_SKIN_VALIDATION = os.path.join(
    REPO_ROOT,
    "00_engine",
    "outputs",
    "character_creator_bridge",
    "artifacts",
    "skin_age_matrix_final_20260726_01",
    "validation_summary.json",
)
DEFAULT_EYELASH_REVIEW = os.path.join(
    SCRIPT_DIR, "cc_eyelash_compatibility_visual_review_v1.json"
)
DEFAULT_EYELASH_V3_SUMMARY = os.path.join(
    SCRIPT_DIR, "cc_eyelash_v3_extreme_automation_summary_v1.json"
)
DEFAULT_EYEBROW_REVIEW = os.path.join(
    SCRIPT_DIR, "cc_eyebrow_compatibility_visual_review_v1.json"
)
DEFAULT_TEETH_REVIEW = os.path.join(
    SCRIPT_DIR, "cc_teeth_compatibility_visual_review_v1.json"
)
DEFAULT_FACIAL_HAIR_REVIEW = os.path.join(
    SCRIPT_DIR, "cc_facial_hair_compatibility_visual_review_v1.json"
)
DEFAULT_SCALP_HAIR_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_asset_catalog_v1.json"
)
DEFAULT_SCALP_HAIR_REVIEW = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_compatibility_visual_review_v1.json"
)
DEFAULT_DYNAMIC_WRINKLE_REVIEW = os.path.join(
    SCRIPT_DIR, "cc_dynamic_wrinkle_age_automation_summary_v1.json"
)
DYNAMIC_REVIEW = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_dynamic_review_v1.json"
)

DYED_COLOR_IDS = (
    "burgundy",
    "copper",
    "blue",
    "teal",
    "pink",
    "silver",
)
COMPONENT_ORDER = (
    "bodyfit_project",
    "primary_head_preset",
    "local_face_morphs",
    "bodyfit_proportion_adjustment",
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
    "face_material_quality_profile",
    "quality_assurance",
)


class RegistryError(RuntimeError):
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
        raise RegistryError("{} is missing: {}".format(label, path))
    return path


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise RegistryError("{} IDs are invalid or duplicated".format(label))
        result[value] = item
    if not result:
        raise RegistryError("{} is empty".format(label))
    return result


def validate_distribution(values, label):
    if not isinstance(values, dict) or not values:
        raise RegistryError("{} must be a non-empty object".format(label))
    if any(
        not isinstance(value, (int, float)) or float(value) <= 0.0
        for value in values.values()
    ):
        raise RegistryError("{} weights must be positive".format(label))
    total = sum(float(value) for value in values.values())
    if abs(total - 1.0) > 1e-9:
        raise RegistryError(
            "{} weights must total 1.0, got {}".format(label, total)
        )


def asset_sha256(asset, known_sha256=None):
    if isinstance(known_sha256, str) and len(known_sha256) == 64:
        return known_sha256
    selected = asset.get("selected_source") or {}
    digest = selected.get("sha256")
    if isinstance(digest, str) and len(digest) == 64:
        return digest
    return sha256_file(asset["preferred_path"])


def production_asset(asset, evidence, application_mode, known_sha256=None):
    path = resolved_file(
        asset.get("preferred_path"),
        "Asset {}".format(asset.get("asset_id")),
    )
    return {
        "application_mode": application_mode,
        "asset_form": asset.get("asset_form"),
        "asset_id": asset["asset_id"],
        "display_name": asset.get("display_name"),
        "evidence": evidence,
        "path": path,
        "sha256": asset_sha256(asset, known_sha256),
        "sex_hint": asset.get("sex_hint"),
        "slot": asset.get("slot"),
    }


def reviewed_compatibility_ids(compatibility, slot):
    result = []
    for item in compatibility.get("assets") or []:
        if item.get("slot") != slot:
            continue
        validations = item.get("validations") or []
        if not validations or any(
            validation.get("visual_status") != "accepted"
            for validation in validations
        ):
            continue
        result.append(item["asset_id"])
    return sorted(result)


def review_asset_note_ids(review, label):
    notes = review.get("asset_notes")
    if not isinstance(notes, dict) or not notes:
        raise RegistryError("{} has no asset_notes".format(label))
    rejected = [
        item
        for item in review.get("reviews") or []
        if item.get("visual_status") != "accepted"
    ]
    if rejected:
        raise RegistryError("{} contains rejected review cases".format(label))
    return sorted(notes)


def build_skin_pool(config, matrix, validation, catalog):
    summary = validation.get("summary") or {}
    if (
        summary.get("success") is not True
        or int(summary.get("successful_case_count", -1)) != 21
        or int(summary.get("expected_case_count", -1)) != 21
    ):
        raise RegistryError("Skin validation does not prove 21/21 success")
    successful_ids = {
        item.get("preset_id")
        for item in validation.get("cases") or []
        if item.get("success") is True
    }
    presets = matrix.get("presets") or []
    if len(presets) != 21 or {
        item.get("preset_id") for item in presets
    } != successful_ids:
        raise RegistryError("Skin matrix and validation case IDs differ")
    group_profiles = config.get("skin_group_profiles") or {}
    skins = []
    for item in presets:
        group = item.get("group")
        profile_id = group_profiles.get(group)
        if profile_id not in (config.get("pigmentation_profiles") or {}):
            raise RegistryError(
                "Skin group has no valid pigmentation profile: {}".format(group)
            )
        source = item.get("skin_asset") or {}
        asset = catalog.get(source.get("asset_id"))
        if asset is None or asset.get("slot") != "skin":
            raise RegistryError(
                "Skin is absent from appearance catalog: {}".format(
                    source.get("asset_id")
                )
            )
        record = production_asset(
            asset,
            {
                "preset_id": item["preset_id"],
                "validation_summary": DEFAULT_SKIN_VALIDATION,
            },
            "skin_material_dialog_exact",
            known_sha256=source.get("sha256"),
        )
        record.update(
            {
                "age_from_filename": item.get("age_from_filename"),
                "identity_label": item.get("identity_label"),
                "pigmentation_profile_id": profile_id,
                "region_label": item.get("region_label"),
                "skin_group": group,
                "sex": item.get("sex"),
            }
        )
        skins.append(record)
    if len({item["asset_id"] for item in skins}) != 21:
        raise RegistryError("Skin asset IDs are not unique")
    return sorted(skins, key=lambda item: item["asset_id"])


def scalp_component_count(item):
    return max(
        (
            int(structure.get("hair_part_count", 0))
            + int(structure.get("accessory_count", 0))
        )
        for structure in (item.get("structures_by_sex") or {}).values()
    )


def select_static_pressure_assets(approved):
    by_family = collections.defaultdict(list)
    for item in approved:
        family = item.get("silhouette_family")
        if not isinstance(family, str) or not family:
            raise RegistryError(
                "Scalp hair has no silhouette family: {}".format(
                    item.get("asset_id")
                )
            )
        by_family[family].append(item)
    selected = []
    for family in sorted(by_family):
        candidates = sorted(
            by_family[family],
            key=lambda item: (
                -scalp_component_count(item),
                item["asset_id"],
            ),
        )
        selected.append(candidates[0])
    selected_ids = {item["asset_id"] for item in selected}
    risk_families = {
        "braid",
        "bun_updo",
        "half_up",
        "long_loose",
        "ponytail",
        "twin_tail",
    }
    extras = sorted(
        (
            item
            for item in approved
            if item["asset_id"] not in selected_ids
            and item.get("silhouette_family") in risk_families
        ),
        key=lambda item: (
            -scalp_component_count(item),
            item.get("silhouette_family"),
            item["asset_id"],
        ),
    )
    for item in extras:
        if len(selected) >= 16:
            break
        selected.append(item)
    if len(selected) != 16:
        raise RegistryError(
            "Unable to select 16 static-pressure scalp-hair assets"
        )
    return sorted(item["asset_id"] for item in selected)


def build_scalp_hair_pool(
    config,
    selected_catalog,
    visual_review,
    canonical_catalog,
):
    selected_assets = indexed(
        selected_catalog.get("assets") or [],
        "asset_id",
        "Selected scalp-hair catalog",
    )
    reviews = visual_review.get("presentation_reviews") or []
    if len(reviews) != 60:
        raise RegistryError("Scalp-hair visual review must contain 60 assets")
    dynamic = {}
    if os.path.isfile(DYNAMIC_REVIEW):
        document = read_json(DYNAMIC_REVIEW)
        dynamic = {
            item["asset_id"]: item
            for item in document.get("assets") or []
        }
    production_statuses = set(config.get("production_hair_statuses") or [])
    approved_reviews = [
        item
        for item in reviews
        if item.get("production_status") in production_statuses
    ]
    rejected_reviews = [
        item
        for item in reviews
        if item.get("production_status") not in production_statuses
    ]
    if len(approved_reviews) != 58 or len(rejected_reviews) != 2:
        raise RegistryError(
            "Expected 58 approved and 2 excluded scalp-hair assets"
        )
    if dynamic and set(dynamic) != {
        item["asset_id"] for item in approved_reviews
    }:
        raise RegistryError(
            "Dynamic scalp-hair review must cover all 58 approved assets"
        )
    pool = []
    for review in approved_reviews:
        asset_id = review["asset_id"]
        selected = selected_assets.get(asset_id)
        canonical = canonical_catalog.get(asset_id)
        if selected is None or canonical is None:
            raise RegistryError(
                "Scalp-hair asset is missing from a catalog: {}".format(
                    asset_id
                )
            )
        record = production_asset(
            selected,
            {
                "visual_review": DEFAULT_SCALP_HAIR_REVIEW,
            },
            "replace_scalp_hair_group",
        )
        dynamic_item = dynamic.get(asset_id) or {}
        production_status = dynamic_item.get(
            "production_status",
            review.get("production_status"),
        )
        risk_tags = sorted(
            set(review.get("risk_tags") or [])
            | set(dynamic_item.get("risk_tags") or [])
        )
        record.update(
            {
                "accepted_sexes": list(review.get("accepted_sexes") or []),
                "dynamic_status": dynamic_item.get(
                    "dynamic_status",
                    review.get("production_status"),
                ),
                "female_presentation_score": float(
                    review.get("female_presentation_score")
                ),
                "hair_builder_pack": review.get("hair_builder_pack"),
                "presentation_label": review.get("presentation_label"),
                "production_status": production_status,
                "risk_tags": risk_tags,
                "silhouette_family": review.get("silhouette_family"),
                "structures_by_sex": review.get("structures_by_sex"),
                "style_tags": list(review.get("style_tags") or []),
            }
        )
        pool.append(record)
    rejected = []
    for review in rejected_reviews:
        asset = selected_assets[review["asset_id"]]
        rejected.append(
            {
                "asset_id": review["asset_id"],
                "display_name": asset.get("display_name"),
                "path": asset.get("preferred_path"),
                "production_status": review.get("production_status"),
                "reason_tags": list(review.get("risk_tags") or []),
                "source_asset_retained": True,
            }
        )
    return (
        sorted(pool, key=lambda item: item["asset_id"]),
        sorted(rejected, key=lambda item: item["asset_id"]),
        select_static_pressure_assets(approved_reviews),
    )


def build(config_path=DEFAULT_CONFIG, output_path=DEFAULT_OUTPUT):
    paths = {
        "appearance_catalog": resolved_file(
            DEFAULT_CATALOG, "Appearance catalog"
        ),
        "appearance_compatibility": resolved_file(
            DEFAULT_COMPATIBILITY, "Appearance compatibility"
        ),
        "config": resolved_file(config_path, "Registry config"),
        "eyebrow_review": resolved_file(
            DEFAULT_EYEBROW_REVIEW, "Eyebrow review"
        ),
        "dynamic_wrinkle_review": resolved_file(
            DEFAULT_DYNAMIC_WRINKLE_REVIEW,
            "Dynamic wrinkle age review",
        ),
        "eyelash_review": resolved_file(
            DEFAULT_EYELASH_REVIEW, "Eyelash review"
        ),
        "eyelash_v3_summary": resolved_file(
            DEFAULT_EYELASH_V3_SUMMARY,
            "Eyelash V3 extreme summary",
        ),
        "facial_hair_review": resolved_file(
            DEFAULT_FACIAL_HAIR_REVIEW, "Facial-hair review"
        ),
        "scalp_hair_catalog": resolved_file(
            DEFAULT_SCALP_HAIR_CATALOG, "Scalp-hair catalog"
        ),
        "scalp_hair_review": resolved_file(
            DEFAULT_SCALP_HAIR_REVIEW, "Scalp-hair review"
        ),
        "skin_matrix": resolved_file(
            DEFAULT_SKIN_MATRIX, "Skin matrix"
        ),
        "skin_validation": resolved_file(
            DEFAULT_SKIN_VALIDATION, "Skin validation"
        ),
        "teeth_review": resolved_file(
            DEFAULT_TEETH_REVIEW, "Teeth review"
        ),
    }
    config = read_json(paths["config"])
    if int(config.get("schema_version", -1)) != 1:
        raise RegistryError("Unsupported registry config schema")
    quality_config = config.get("face_material_quality_profile") or {}
    if not isinstance(quality_config, dict):
        raise RegistryError("Face material quality profile must be an object")
    quality_path = resolved_file(
        quality_config.get("path"),
        "Face material quality profile",
    )
    quality_profile = read_json(quality_path)
    quality_profile_id = quality_config.get("profile_id")
    required_quality_status = quality_config.get("required_status")
    if quality_profile.get("profile_id") != quality_profile_id:
        raise RegistryError("Face material quality profile ID changed")
    if quality_profile.get("status") != required_quality_status:
        raise RegistryError(
            "Face material quality profile is not production approved"
        )
    if not quality_profile.get("recommended_changes"):
        raise RegistryError("Face material quality profile has no changes")
    paths["face_material_quality_profile"] = quality_path
    quality_reference = {
        "path": quality_path,
        "profile_id": quality_profile_id,
        "required_status": required_quality_status,
        "sha256": sha256_file(quality_path),
    }
    mode_weights = config.get("hair_color_mode_weights") or {}
    validate_distribution(mode_weights, "Hair color modes")
    age_distribution = config.get("age_distribution") or {}
    validate_distribution(age_distribution, "Age distribution")
    hair_presentation_policy = (
        config.get("hair_presentation_policy") or {}
    )
    presentation_modes = (
        hair_presentation_policy.get("modes") or {}
    )
    default_presentation_mode = hair_presentation_policy.get(
        "default_mode"
    )
    if default_presentation_mode not in presentation_modes:
        raise RegistryError(
            "Hair presentation default mode is not configured"
        )
    default_presentation = presentation_modes.get("default") or {}
    male_maximum = float(
        default_presentation.get("male_maximum_score")
    )
    female_minimum = float(
        default_presentation.get("female_minimum_score")
    )
    if not (
        0.0 <= male_maximum <= 1.0
        and 0.0 <= female_minimum <= 1.0
        and male_maximum == female_minimum
    ):
        raise RegistryError(
            "Default hair presentation boundary must be one "
            "shared score in [0, 1]"
        )
    palette = config.get("hair_color_palette") or {}
    if set(DYED_COLOR_IDS) - set(palette):
        raise RegistryError("Dyed palette entries are incomplete")
    profiles = config.get("pigmentation_profiles") or {}
    for profile_id, profile in profiles.items():
        for mode in ("natural_common", "natural_rare"):
            distribution = profile.get(mode) or {}
            validate_distribution(
                distribution,
                "{} {}".format(profile_id, mode),
            )
            unknown = set(distribution) - set(palette)
            if unknown:
                raise RegistryError(
                    "Pigmentation profile references unknown colors: {}".format(
                        sorted(unknown)
                    )
                )

    catalog_document = read_json(paths["appearance_catalog"])
    catalog = indexed(
        catalog_document.get("assets") or [],
        "asset_id",
        "Appearance catalog",
    )
    compatibility = read_json(paths["appearance_compatibility"])
    skin_matrix = read_json(paths["skin_matrix"])
    skin_validation = read_json(paths["skin_validation"])
    skins = build_skin_pool(
        config, skin_matrix, skin_validation, catalog
    )
    dynamic_wrinkle_review = read_json(
        paths["dynamic_wrinkle_review"]
    )
    wrinkle_cases = dynamic_wrinkle_review.get("cases") or []
    if (
        int(
            dynamic_wrinkle_review.get(
                "completed_case_count", -1
            )
        )
        != 6
        or int(
            dynamic_wrinkle_review.get(
                "pending_case_count", -1
            )
        )
        != 0
        or len(wrinkle_cases) != 6
        or any(
            item.get("structural_pass") is not True
            for item in wrinkle_cases
        )
    ):
        raise RegistryError(
            "Dynamic wrinkle age review does not prove 6/6 success"
        )
    wrinkle_cases_by_sex = collections.defaultdict(list)
    for item in wrinkle_cases:
        wrinkle_cases_by_sex[item.get("sex")].append(item)
    if any(
        {
            item.get("age_label")
            for item in wrinkle_cases_by_sex.get(sex) or []
        }
        != {"young", "middle", "older"}
        for sex in ("female", "male")
    ):
        raise RegistryError(
            "Dynamic wrinkle review lacks a complete age matrix"
        )

    eyebrow_review = read_json(paths["eyebrow_review"])
    eyebrow_ids = review_asset_note_ids(eyebrow_review, "Eyebrow review")
    if set(eyebrow_ids) != set(
        reviewed_compatibility_ids(compatibility, "eyebrows")
    ):
        raise RegistryError("Eyebrow review and registry IDs differ")

    teeth_review = read_json(paths["teeth_review"])
    teeth_ids = review_asset_note_ids(teeth_review, "Teeth review")
    facial_hair_review = read_json(paths["facial_hair_review"])
    facial_hair_ids = review_asset_note_ids(
        facial_hair_review, "Facial-hair review"
    )
    eye_ids = reviewed_compatibility_ids(compatibility, "eyes")
    if len(eye_ids) != 12:
        raise RegistryError("Expected 12 reviewed eye assets")

    eyelash_review = read_json(paths["eyelash_review"])
    if eyelash_review.get("status") not in (
        "accepted_with_final_random_face_dynamic_regression_required",
        "accepted",
    ):
        raise RegistryError("Eyelash pool is not approved")
    eyelash_ids = [
        item["asset_id"]
        for item in eyelash_review.get("approved_assets") or []
    ]
    if len(eyelash_ids) != 9 or len(set(eyelash_ids)) != 9:
        raise RegistryError("Expected 9 unique HD Natural eyelashes")
    eyelash_v3_summary = read_json(paths["eyelash_v3_summary"])
    eyelash_v3_cases = eyelash_v3_summary.get("cases") or []
    if (
        eyelash_v3_summary.get("status")
        != "automation-complete-visual-review-pending"
        or int(eyelash_v3_summary.get("completed_case_count", -1))
        != 36
        or int(eyelash_v3_summary.get("pending_case_count", -1))
        != 0
        or len(eyelash_v3_cases) != 36
        or any(
            item.get("structural_pass") is not True
            for item in eyelash_v3_cases
        )
    ):
        raise RegistryError(
            "Eyelash V3 extreme review does not prove 36/36 success"
        )
    expected_extreme_seeds = {
        "M01_Aaron",
        "M09_Male_F",
        "F06_Female_C",
        "F08_Female_E",
    }
    cases_by_eyelash = collections.defaultdict(list)
    for item in eyelash_v3_cases:
        cases_by_eyelash[item.get("asset_id")].append(item)
    if set(cases_by_eyelash) != set(eyelash_ids) or any(
        len(cases_by_eyelash[asset_id]) != 4
        or {
            item.get("primary_seed_id")
            for item in cases_by_eyelash[asset_id]
        }
        != expected_extreme_seeds
        for asset_id in eyelash_ids
    ):
        raise RegistryError(
            "Eyelash V3 extreme review lacks the 9 x 4 matrix"
        )
    eyelash_v3_visual = (
        (eyelash_review.get("validation") or {}).get("v3_extreme")
        or {}
    )
    if (
        eyelash_v3_visual.get("visual_review_status") != "accepted"
        or int(eyelash_v3_visual.get("passed_count", -1)) != 36
        or int(eyelash_v3_visual.get("failed_count", -1)) != 0
    ):
        raise RegistryError(
            "Eyelash V3 extreme visual review is not accepted"
        )

    selected_hair = read_json(paths["scalp_hair_catalog"])
    scalp_review = read_json(paths["scalp_hair_review"])
    scalp_hair, rejected_hair, pressure_ids = build_scalp_hair_pool(
        config,
        selected_hair,
        scalp_review,
        catalog,
    )

    def component_pool(ids, evidence_path, application_mode):
        return [
            production_asset(
                catalog[asset_id],
                {"visual_review": evidence_path},
                application_mode,
            )
            for asset_id in sorted(ids)
        ]

    eyelash_pool = []
    for asset_id in sorted(eyelash_ids):
        record = production_asset(
            catalog[asset_id],
            {
                "source_face_visual_review": paths["eyelash_review"],
                "v3_extreme_automation": paths[
                    "eyelash_v3_summary"
                ],
            },
            "character_preset_replace",
        )
        record["validation_status"] = (
            "approved_source_faces_and_v3_extreme_matrix"
        )
        eyelash_pool.append(record)

    wrinkle_profiles = []
    wrinkle_config = config.get("dynamic_wrinkles") or {}
    for sex in ("female", "male"):
        path = resolved_file(
            (wrinkle_config.get("profiles") or {}).get(sex),
            "{} dynamic wrinkle profile".format(sex),
        )
        asset_id = "CCWRINKLE_NEUTRAL_2K_{}".format(
            "F" if sex == "female" else "M"
        )
        sex_cases = wrinkle_cases_by_sex[sex]
        if {
            item.get("profile_id") for item in sex_cases
        } != {asset_id}:
            raise RegistryError(
                "{} wrinkle review profile IDs differ".format(sex)
            )
        wrinkle_profiles.append(
            {
                "application_mode": (
                    "inherit_neutral_bodyfit_profile_set_strength"
                ),
                "asset_id": asset_id,
                "display_name": "HD Neutral {} 2K".format(
                    "F" if sex == "female" else "M"
                ),
                "path": path,
                "sex": sex,
                "sha256": sha256_file(path),
                "source_asset_reference_only": True,
                "validated_age_labels": [
                    "young",
                    "middle",
                    "older",
                ],
                "validation_evidence": (
                    paths["dynamic_wrinkle_review"]
                ),
                "validation_status": "approved_age_matrix",
            }
        )

    result = {
        "age": {
            "distribution": age_distribution,
            "gray_policy": config["age_gray_policy"],
            "levels": skin_matrix.get("age_levels"),
            "morph": skin_matrix.get("age_morph"),
        },
        "assembly_order": list(COMPONENT_ORDER),
        "component_pools": {
            "dynamic_wrinkles": {
                "fixed_strength": float(
                    wrinkle_config.get("fixed_strength")
                ),
                "profiles": wrinkle_profiles,
            },
            "eyebrows": component_pool(
                eyebrow_ids,
                paths["eyebrow_review"],
                "replace_brow_avatar_part",
            ),
            "eyelashes": eyelash_pool,
            "eyes": component_pool(
                eye_ids,
                os.path.join(
                    SCRIPT_DIR,
                    "cc_eye_compatibility_matrix_visual_review_v1.json",
                ),
                "material_only_preserve_geometry",
            ),
            "facial_hair": component_pool(
                facial_hair_ids,
                paths["facial_hair_review"],
                "replace_beard_group",
            ),
            "scalp_hair": scalp_hair,
            "skins": skins,
            "teeth": component_pool(
                teeth_ids,
                paths["teeth_review"],
                "replace_teeth_avatar_part",
            ),
        },
        "face_material_quality_profile": quality_reference,
        "generated_at": now(),
        "pigmentation": {
            "dyed_color_ids": list(DYED_COLOR_IDS),
            "mode_weights": mode_weights,
            "palette": palette,
            "profiles": profiles,
            "shared_targets": [
                "scalp_hair",
                "eyebrows",
                "facial_hair",
            ],
        },
        "production_policy": {
            "adult_cc5_hd_only": True,
            "facial_hair_probability_male": float(
                config.get("facial_hair_probability_male")
            ),
            "hair_presentation": hair_presentation_policy,
            "iris_color_is_independent": True,
            "production_hair_statuses": list(
                config.get("production_hair_statuses") or []
            ),
            "request_paths_allowed": False,
            "scalp_hair_selection": (
                "presentation_filter_then_uniform_nonempty_silhouette_family"
            ),
            "single_hair_color_per_character": True,
        },
        "registry_id": config["registry_id"],
        "rejected_assets": {
            "scalp_hair": rejected_hair,
        },
        "schema_version": 1,
        "sources": {
            name: {
                "path": path,
                "sha256": sha256_file(path),
            }
            for name, path in sorted(paths.items())
        },
        "validation_design": {
            "dynamic_wrinkle_case_count": 6,
            "eyelash_v3_extreme_case_count": 36,
            "integration_character_count": 24,
            "scalp_hair_dynamic_base_case_count": 58,
            "scalp_hair_dynamic_cross_sex_case_count": 16,
            "scalp_hair_static_pressure_asset_ids": pressure_ids,
            "scalp_hair_static_pressure_case_count": 64,
            "v3_extreme_primary_face_seed_ids": [
                "M01_Aaron",
                "M09_Male_F",
                "F06_Female_C",
                "F08_Female_E",
            ],
        },
    }
    output_path = os.path.realpath(os.path.abspath(output_path))
    write_json(result, output_path)
    return {
        "component_counts": {
            key: (
                len(value)
                if isinstance(value, list)
                else len(value.get("profiles") or [])
            )
            for key, value in result["component_pools"].items()
        },
        "output": output_path,
        "registry_id": result["registry_id"],
        "rejected_scalp_hair_count": len(rejected_hair),
        "success": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build(args.config, args.output)
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        )
        return 0
    except RegistryError as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "success": False,
                },
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
