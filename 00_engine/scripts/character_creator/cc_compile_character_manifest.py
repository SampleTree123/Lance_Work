"""Compile deterministic CC character manifests from reviewed component libraries."""

import argparse
import copy
import datetime
import hashlib
import json
import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BODY_LIBRARY = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v2.json")
DEFAULT_FACE_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_face_recipes_v3_200.json"
)
DEFAULT_COMPATIBILITY = os.path.join(
    SCRIPT_DIR, "cc_appearance_compatibility_v1.json"
)
DEFAULT_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json"
)
DEFAULT_FACIAL_REGISTRY = os.path.join(
    SCRIPT_DIR, "cc_facial_production_registry_v1.json"
)
DEFAULT_BODYFIT_PROPORTION_DECISIONS = os.path.join(
    SCRIPT_DIR, "cc_head_bodyfit_scale_decisions_v1.json"
)
DEFAULT_REQUESTS = os.path.join(
    SCRIPT_DIR, "cc_character_manifest_requests_pilot_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_character_manifest_pilot_v1.json"
)
COMPLETE_PRIMARY_FACE_PIPELINE = (
    "complete_primary_face_plus_local_morphs_v1"
)
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
    "face_material_quality_profile",
)
BODYFIT_PROPORTION_APPLICATION_ORDER = (
    "head_scale",
    "neck_height",
)
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

SLOT_ORDER = {
    "skin": 10,
    "skin_preset": 20,
    "makeup": 30,
    "eyes": 40,
    "teeth": 50,
    "underwear": 100,
    "full_body": 110,
    "upper": 120,
    "lower": 130,
    "outerwear": 140,
    "footwear": 150,
    "gloves": 160,
    "clothing_other": 170,
    "scalp_hair": 180,
    "eyebrows": 190,
    "facial_hair": 200,
    "accessory_head": 210,
    "accessory_torso": 220,
    "accessory_arm": 230,
    "accessory_leg": 240,
    "accessory_other": 250,
}


class CompileError(RuntimeError):
    pass


class RequestCompileError(RuntimeError):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_path(path, label):
    resolved = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(resolved):
        raise CompileError("{} is missing: {}".format(label, resolved))
    return resolved


def content_reference_signature(
    reference,
    label,
    require_application_mode=False,
    require_policy_binding=False,
):
    if not isinstance(reference, dict):
        raise CompileError("{} must be an object".format(label))
    path = reference.get("path")
    expected_hash = reference.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or not isinstance(expected_hash, str)
        or len(expected_hash) != 64
    ):
        raise CompileError("{} path or SHA256 is invalid".format(label))
    result = {
        "path": os.path.normcase(
            os.path.realpath(os.path.abspath(path))
        ),
        "sha256": expected_hash,
    }
    if require_application_mode:
        mode = reference.get("application_mode")
        if mode != FACIAL_PROFILE_APPLICATION_MODE:
            raise CompileError(
                "{} has an unsupported application mode".format(label)
            )
        result["application_mode"] = mode
    if require_policy_binding:
        binding = reference.get("policy_binding")
        if binding not in ("default_by_sex", "seed_override"):
            raise CompileError(
                "{} has an invalid policy binding".format(label)
            )
        result["policy_binding"] = binding
    return result


def resolve_seed_facial_profile(seed_library, seed):
    policy = seed_library.get("facial_profile_policy") or {}
    application_mode = policy.get("application_mode")
    if application_mode != FACIAL_PROFILE_APPLICATION_MODE:
        raise CompileError(
            "Unsupported Facial Profile application mode: {}".format(
                application_mode
            )
        )
    seed_id = seed.get("seed_id")
    sex = seed.get("sex")
    overrides = policy.get("seed_overrides") or {}
    defaults = policy.get("default_by_sex") or {}
    if seed_id in overrides:
        source = overrides[seed_id]
        policy_binding = "seed_override"
    else:
        source = defaults.get(sex)
        policy_binding = "default_by_sex"
    if not isinstance(source, dict):
        raise CompileError(
            "No Facial Profile is bound to seed: {}".format(seed_id)
        )
    if not str(source.get("path", "")).lower().endswith(
        ".ccfacialprofile"
    ):
        raise CompileError(
            "Facial Profile binding has the wrong file type: {}".format(
                seed_id
            )
        )
    result = copy.deepcopy(source)
    result["application_mode"] = application_mode
    result["policy_binding"] = policy_binding
    content_reference_signature(
        result,
        "Facial Profile policy for {}".format(seed_id),
        require_application_mode=True,
        require_policy_binding=True,
    )
    return result


def validate_v3_face_library(face_library):
    if face_library.get("pipeline") != COMPLETE_PRIMARY_FACE_PIPELINE:
        return None
    seed_reference = face_library.get("source_library") or {}
    policy_reference = face_library.get("identity_policy") or {}
    seed_path = canonical_path(
        seed_reference.get("path"), "V3 face seed library"
    )
    policy_path = canonical_path(
        policy_reference.get("path"), "V3 face identity policy"
    )
    if (
        seed_reference.get("sha256") != sha256_file(seed_path)
        or policy_reference.get("sha256") != sha256_file(policy_path)
    ):
        raise CompileError(
            "V3 face resource hash no longer matches its library"
        )

    seed_library = read_json(seed_path)
    seeds = indexed(
        seed_library.get("seeds") or [],
        "seed_id",
        "V3 face seed library",
    )
    verified_assets = {}
    for face in face_library.get("recipes") or []:
        if face.get("pipeline") != COMPLETE_PRIMARY_FACE_PIPELINE:
            raise CompileError(
                "V3 face recipe has an inconsistent pipeline: {}".format(
                    face.get("face_recipe_id")
                )
            )
        seed_id = face.get("primary_face_seed_id")
        seed = seeds.get(seed_id)
        if seed is None:
            raise CompileError(
                "V3 face recipe references an unknown seed: {}".format(
                    seed_id
                )
            )
        if face.get("sex") != seed.get("sex"):
            raise CompileError(
                "V3 face recipe sex differs from its seed: {}".format(
                    face.get("face_recipe_id")
                )
            )

        expected_head = seed.get("source_head_preset")
        expected_profile = resolve_seed_facial_profile(
            seed_library, seed
        )
        head_signature = content_reference_signature(
            face.get("source_head_preset"),
            "V3 face source_head_preset",
        )
        expected_head_signature = content_reference_signature(
            expected_head,
            "V3 seed source_head_preset",
        )
        profile_signature = content_reference_signature(
            face.get("source_facial_profile"),
            "V3 face source_facial_profile",
            require_application_mode=True,
            require_policy_binding=True,
        )
        expected_profile_signature = content_reference_signature(
            expected_profile,
            "V3 seed Facial Profile",
            require_application_mode=True,
            require_policy_binding=True,
        )
        if head_signature != expected_head_signature:
            raise CompileError(
                "V3 face head preset differs from its seed policy: {}".format(
                    face.get("face_recipe_id")
                )
            )
        if profile_signature != expected_profile_signature:
            raise CompileError(
                "V3 face Facial Profile differs from its seed policy: {}".format(
                    face.get("face_recipe_id")
                )
            )
        for reference, label in (
            (expected_head, "V3 primary head preset"),
            (expected_profile, "V3 Facial Profile"),
        ):
            signature = content_reference_signature(
                reference,
                label,
                require_application_mode=(
                    label == "V3 Facial Profile"
                ),
                require_policy_binding=(
                    label == "V3 Facial Profile"
                ),
            )
            asset_path = signature["path"]
            if asset_path not in verified_assets:
                canonical_asset = canonical_path(asset_path, label)
                actual_hash = sha256_file(canonical_asset)
                if actual_hash != signature["sha256"]:
                    raise CompileError(
                        "{} hash changed: {}".format(
                            label, canonical_asset
                        )
                    )
                verified_assets[asset_path] = actual_hash
    return {
        "seed_library": seed_path,
        "identity_policy": policy_path,
    }


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise CompileError("{} IDs are invalid or duplicated".format(label))
        result[value] = item
    if not result:
        raise CompileError("{} is empty".format(label))
    return result


def finite_weight(value, label, minimum, maximum):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not float("-inf") < float(value) < float("inf")
    ):
        raise CompileError("{} must be a finite number".format(label))
    value = float(value)
    if value < minimum or value > maximum:
        raise CompileError(
            "{} is outside [{}, {}]".format(label, minimum, maximum)
        )
    return value


def proportion_morph_metadata(decisions, field, label):
    metadata = decisions.get(field)
    if not isinstance(metadata, dict):
        raise CompileError("{} metadata is missing".format(label))
    morph_id = metadata.get("id")
    display = metadata.get("display")
    weight_scale = metadata.get("script_weight_scale")
    ui_scale = metadata.get("ui_value_scale")
    if (
        not isinstance(morph_id, str)
        or not morph_id
        or not isinstance(display, str)
        or not display
        or isinstance(weight_scale, bool)
        or not isinstance(weight_scale, (int, float))
        or float(weight_scale) <= 0.0
        or isinstance(ui_scale, bool)
        or not isinstance(ui_scale, (int, float))
        or float(ui_scale) <= 0.0
    ):
        raise CompileError("{} metadata is invalid".format(label))
    return {
        "display": display,
        "id": morph_id,
        "script_weight_scale": float(weight_scale),
        "ui_value_scale": float(ui_scale),
    }


def compile_bodyfit_proportion_adjustments(decisions, bodies):
    if not isinstance(decisions, dict):
        raise CompileError("BodyFit proportion decisions must be an object")
    if int(decisions.get("schema_version", -1)) != 1:
        raise CompileError("Unsupported BodyFit proportion decision schema")
    if decisions.get("status") != (
        "head_and_neck_bodyfit_adjustments_selected"
    ):
        raise CompileError("BodyFit proportion decisions are not final")
    decision_set_id = decisions.get("decision_set_id")
    if not isinstance(decision_set_id, str) or not decision_set_id:
        raise CompileError("BodyFit proportion decision_set_id is missing")
    head = proportion_morph_metadata(
        decisions,
        "head_scale_morph",
        "Head Scale",
    )
    neck = proportion_morph_metadata(
        decisions,
        "neck_height_morph",
        "Neck Height",
    )
    if head["id"] == neck["id"]:
        raise CompileError("Head Scale and Neck Height Morph IDs collide")

    selections = indexed(
        decisions.get("selections") or [],
        "bodyfit_id",
        "BodyFit proportion selections",
    )
    if set(selections) != set(bodies):
        raise CompileError(
            "BodyFit proportion selections do not cover the BodyFit library"
        )
    adjustments = {}
    for bodyfit_id in sorted(bodies):
        selection = selections[bodyfit_id]
        if selection.get("status") != "selected":
            raise CompileError(
                "BodyFit proportion selection is not final: {}".format(
                    bodyfit_id
                )
            )
        head_weight = finite_weight(
            selection.get("head_scale_weight"),
            "{} Head Scale".format(bodyfit_id),
            -1.0,
            1.0,
        )
        head_ui = finite_weight(
            selection.get("ui_value"),
            "{} Head Scale UI value".format(bodyfit_id),
            -100.0,
            100.0,
        )
        if abs(head_ui * head["script_weight_scale"] - head_weight) > 1e-7:
            raise CompileError(
                "{} Head Scale UI and weight differ".format(bodyfit_id)
            )

        neck_selection = selection.get("neck_adjustment")
        if neck_selection is None:
            neck_weight = 0.0
            neck_ui = 0.0
            neck_status = "not_required"
        else:
            if not isinstance(neck_selection, dict):
                raise CompileError(
                    "{} neck_adjustment must be an object".format(bodyfit_id)
                )
            if (
                neck_selection.get("status") != "selected"
                or neck_selection.get("morph_id") != neck["id"]
            ):
                raise CompileError(
                    "{} Neck Height selection is not final".format(bodyfit_id)
                )
            neck_weight = finite_weight(
                neck_selection.get("weight"),
                "{} Neck Height".format(bodyfit_id),
                -1.0,
                0.5,
            )
            neck_ui = finite_weight(
                neck_selection.get("ui_value"),
                "{} Neck Height UI value".format(bodyfit_id),
                -100.0,
                50.0,
            )
            if (
                abs(
                    neck_ui * neck["script_weight_scale"] - neck_weight
                )
                > 1e-7
            ):
                raise CompileError(
                    "{} Neck Height UI and weight differ".format(bodyfit_id)
                )
            neck_status = "selected"

        adjustments[bodyfit_id] = {
            "application_order": list(
                BODYFIT_PROPORTION_APPLICATION_ORDER
            ),
            "decision_set_id": decision_set_id,
            "targets": [
                {
                    "display": head["display"],
                    "id": head["id"],
                    "role": "head_scale",
                    "target": head_weight,
                    "ui_value": int(round(head_ui)),
                },
                {
                    "display": neck["display"],
                    "id": neck["id"],
                    "role": "neck_height",
                    "selection_status": neck_status,
                    "target": neck_weight,
                    "ui_value": int(round(neck_ui)),
                },
            ],
        }
    return adjustments


def stable_choice(items, seed, namespace):
    if not items:
        raise CompileError("stable_choice received no items")
    payload = "{}:{}".format(seed, namespace).encode("utf-8")
    index = int(hashlib.sha256(payload).hexdigest(), 16) % len(items)
    return items[index]


def stable_unit_interval(seed, namespace):
    payload = "{}:{}".format(seed, namespace).encode("utf-8")
    integer = int(hashlib.sha256(payload).hexdigest(), 16)
    return integer / float((1 << 256) - 1)


def stable_weighted_choice(items, weights, seed, namespace):
    if not items or len(items) != len(weights):
        raise CompileError("Weighted choice inputs are invalid")
    normalized = [float(weight) for weight in weights]
    if any(weight <= 0.0 for weight in normalized):
        raise CompileError("Weighted choice values must be positive")
    target = stable_unit_interval(seed, namespace) * sum(normalized)
    cumulative = 0.0
    for item, weight in zip(items, normalized):
        cumulative += weight
        if target <= cumulative:
            return item
    return items[-1]


def stable_distribution_choice(distribution, seed, namespace):
    if not isinstance(distribution, dict) or not distribution:
        raise CompileError("Distribution is empty")
    items = sorted(distribution)
    return stable_weighted_choice(
        items,
        [distribution[item] for item in items],
        seed,
        namespace,
    )


def stable_gray_fraction(policy, seed, namespace):
    distribution = policy.get("distribution")
    minimum = float(policy.get("minimum"))
    maximum = float(policy.get("maximum"))
    if not 0.0 <= minimum <= maximum <= 1.0:
        raise CompileError("Gray-fraction bounds are invalid")
    unit = stable_unit_interval(seed, namespace)
    if distribution == "uniform":
        return minimum + (maximum - minimum) * unit
    if distribution != "triangular":
        raise CompileError(
            "Unsupported gray-fraction distribution: {}".format(
                distribution
            )
        )
    mode = float(policy.get("mode"))
    if not minimum <= mode <= maximum:
        raise CompileError("Triangular gray-fraction mode is invalid")
    if maximum == minimum:
        return minimum
    split = (mode - minimum) / (maximum - minimum)
    if unit <= split:
        return minimum + (
            unit * (maximum - minimum) * (mode - minimum)
        ) ** 0.5
    return maximum - (
        (1.0 - unit) * (maximum - minimum) * (maximum - mode)
    ) ** 0.5


def facial_pool(registry, name):
    pools = registry.get("component_pools") or {}
    pool = pools.get(name)
    if not isinstance(pool, list) or not pool:
        raise CompileError(
            "Facial registry pool is missing or empty: {}".format(name)
        )
    return indexed(pool, "asset_id", "Facial {} pool".format(name))


def requested_component(
    specification,
    field,
    candidates,
    seed,
    namespace,
):
    requested_id = specification.get(field)
    if requested_id is None:
        return stable_choice(
            sorted(candidates.values(), key=lambda item: item["asset_id"]),
            seed,
            namespace,
        )
    selected = candidates.get(requested_id)
    if selected is None:
        request_error(
            "unknown_facial_component",
            "Requested facial component is not approved",
            field=field,
            asset_id=requested_id,
        )
    return selected


def scalp_hair_presentation_eligible(
    item,
    sex,
    mode,
    policy,
):
    try:
        score = float(item.get("female_presentation_score"))
    except (TypeError, ValueError):
        raise CompileError(
            "Scalp hair has no valid presentation score: {}".format(
                item.get("asset_id")
            )
        )
    if not 0.0 <= score <= 1.0:
        raise CompileError(
            "Scalp hair presentation score is outside [0, 1]"
        )
    modes = policy.get("modes") or {}
    mode_policy = modes.get(mode)
    if not isinstance(mode_policy, dict):
        request_error(
            "unknown_hair_presentation_mode",
            "Requested hair presentation mode is not approved",
            hair_presentation_mode=mode,
        )
    if mode == "cross_presentation":
        return bool(mode_policy.get("allow_all"))
    if mode == "neutral_only":
        minimum = float(mode_policy.get("minimum_score"))
        maximum = float(mode_policy.get("maximum_score"))
        return minimum <= score <= maximum
    if mode == "default":
        if sex == "male":
            return score <= float(
                mode_policy.get("male_maximum_score")
            )
        if sex == "female":
            return score >= float(
                mode_policy.get("female_minimum_score")
            )
        raise CompileError(
            "Unsupported sex for scalp hair presentation: {}".format(
                sex
            )
        )
    request_error(
        "unknown_hair_presentation_mode",
        "Requested hair presentation mode is not approved",
        hair_presentation_mode=mode,
    )


def compile_facial_components(
    request,
    registry,
    sex,
    seed,
    character_id,
):
    if int(registry.get("schema_version", -1)) != 1:
        raise CompileError("Unsupported facial registry schema")
    quality_reference = registry.get("face_material_quality_profile") or {}
    if not isinstance(quality_reference, dict):
        raise CompileError("Facial material quality reference must be an object")
    quality_path = canonical_path(
        quality_reference.get("path"),
        "Facial material quality profile",
    )
    quality_profile = read_json(quality_path)
    quality_profile_id = quality_reference.get("profile_id")
    required_quality_status = quality_reference.get("required_status")
    if quality_profile.get("profile_id") != quality_profile_id:
        raise CompileError("Facial material quality profile ID changed")
    if quality_profile.get("status") != required_quality_status:
        raise CompileError("Facial material quality profile status changed")
    actual_quality_sha256 = sha256_file(quality_path)
    expected_quality_sha256 = quality_reference.get("sha256")
    if expected_quality_sha256 != actual_quality_sha256:
        raise CompileError("Facial material quality profile hash changed")
    compiled_quality_reference = {
        "path": quality_path,
        "profile_id": quality_profile_id,
        "required_status": required_quality_status,
        "sha256": actual_quality_sha256,
    }
    specification = request.get("facial_components") or {}
    if not isinstance(specification, dict):
        request_error(
            "invalid_facial_components",
            "facial_components must be an object",
        )

    skins = facial_pool(registry, "skins")
    skin_candidates = {
        asset_id: item
        for asset_id, item in skins.items()
        if item.get("sex") == sex
    }
    skin = requested_component(
        specification,
        "skin_asset_id",
        skin_candidates,
        seed,
        "{}:skin".format(character_id),
    )

    age = registry.get("age") or {}
    age_distribution = age.get("distribution") or {}
    requested_age = specification.get("age_label")
    if requested_age is None:
        age_label = stable_distribution_choice(
            age_distribution,
            seed,
            "{}:age".format(character_id),
        )
    else:
        age_label = requested_age
    age_levels = {
        item.get("label"): item
        for item in age.get("levels") or []
    }
    if age_label not in age_levels:
        request_error(
            "unknown_age_label",
            "Requested age label is not approved",
            age_label=age_label,
        )
    age_level = age_levels[age_label]
    age_morph = age.get("morph") or {}
    age_morph_id = age_morph.get("id")
    if not isinstance(age_morph_id, str) or not age_morph_id:
        raise CompileError("Facial registry has no age Morph ID")

    eyes = requested_component(
        specification,
        "eye_asset_id",
        facial_pool(registry, "eyes"),
        seed,
        "{}:eyes".format(character_id),
    )
    teeth = requested_component(
        specification,
        "teeth_asset_id",
        facial_pool(registry, "teeth"),
        seed,
        "{}:teeth".format(character_id),
    )

    eyebrow_pool = facial_pool(registry, "eyebrows")
    eyebrow_candidates = {
        asset_id: item
        for asset_id, item in eyebrow_pool.items()
        if item.get("sex_hint") == sex
    }
    eyebrows = requested_component(
        specification,
        "eyebrow_asset_id",
        eyebrow_candidates,
        seed,
        "{}:eyebrows".format(character_id),
    )
    eyelashes = requested_component(
        specification,
        "eyelash_asset_id",
        facial_pool(registry, "eyelashes"),
        seed,
        "{}:eyelashes".format(character_id),
    )

    facial_hair = None
    facial_hair_pool = facial_pool(registry, "facial_hair")
    if sex == "female":
        if (
            "facial_hair_asset_id" in specification
            and specification.get("facial_hair_asset_id") is not None
        ):
            request_error(
                "facial_hair_sex_mismatch",
                "Current production policy only approves facial hair for males",
            )
    elif "facial_hair_asset_id" in specification:
        requested_facial_hair = specification.get(
            "facial_hair_asset_id"
        )
        if requested_facial_hair is not None:
            facial_hair = facial_hair_pool.get(requested_facial_hair)
            if facial_hair is None:
                request_error(
                    "unknown_facial_component",
                    "Requested facial hair is not approved",
                    field="facial_hair_asset_id",
                    asset_id=requested_facial_hair,
                )
    else:
        probability = float(
            (registry.get("production_policy") or {}).get(
                "facial_hair_probability_male"
            )
        )
        if stable_unit_interval(
            seed, "{}:facial_hair_enabled".format(character_id)
        ) < probability:
            facial_hair = stable_choice(
                sorted(
                    facial_hair_pool.values(),
                    key=lambda item: item["asset_id"],
                ),
                seed,
                "{}:facial_hair".format(character_id),
            )

    scalp_pool = facial_pool(registry, "scalp_hair")
    presentation_policy = (
        (registry.get("production_policy") or {}).get(
            "hair_presentation"
        )
        or {}
    )
    requested_presentation_mode = specification.get(
        "hair_presentation_mode"
    )
    hair_presentation_mode = (
        requested_presentation_mode
        if requested_presentation_mode is not None
        else presentation_policy.get("default_mode")
    )
    if not isinstance(hair_presentation_mode, str):
        raise CompileError(
            "Facial registry has no default hair presentation mode"
        )
    requested_scalp_id = specification.get("scalp_hair_asset_id")
    technically_compatible_scalp = {
        asset_id: item
        for asset_id, item in scalp_pool.items()
        if sex in (item.get("accepted_sexes") or [])
    }
    eligible_scalp = {
        asset_id: item
        for asset_id, item in technically_compatible_scalp.items()
        if scalp_hair_presentation_eligible(
            item,
            sex,
            hair_presentation_mode,
            presentation_policy,
        )
    }
    if not eligible_scalp:
        request_error(
            "no_eligible_scalp_hair_for_sex",
            "No production scalp hair remains after presentation filtering",
            sex=sex,
            hair_presentation_mode=hair_presentation_mode,
        )
    if requested_scalp_id is not None:
        scalp_hair = technically_compatible_scalp.get(
            requested_scalp_id
        )
        if scalp_hair is None:
            request_error(
                "unknown_or_incompatible_scalp_hair",
                "Requested scalp hair is not approved for this character",
                scalp_hair_asset_id=requested_scalp_id,
                sex=sex,
            )
        if requested_scalp_id not in eligible_scalp:
            request_error(
                "scalp_hair_presentation_mismatch",
                "Requested scalp hair is outside the selected "
                "presentation mode",
                scalp_hair_asset_id=requested_scalp_id,
                sex=sex,
                hair_presentation_mode=hair_presentation_mode,
                female_presentation_score=float(
                    scalp_hair.get("female_presentation_score")
                ),
            )
    else:
        families = sorted(
            {
                item.get("silhouette_family")
                for item in eligible_scalp.values()
            }
        )
        if not families or any(
            not isinstance(family, str) or not family
            for family in families
        ):
            raise CompileError(
                "Eligible scalp hair has no valid silhouette family"
            )
        family = stable_choice(
            families,
            seed,
            "{}:scalp_hair_family".format(character_id),
        )
        family_items = sorted(
            [
                item
                for item in eligible_scalp.values()
                if item.get("silhouette_family") == family
            ],
            key=lambda item: item["asset_id"],
        )
        if not family_items:
            raise CompileError(
                "Selected scalp hair silhouette family is empty"
            )
        scalp_hair = stable_choice(
            family_items,
            seed,
            "{}:scalp_hair_asset".format(character_id),
        )

    pigmentation = registry.get("pigmentation") or {}
    requested_mode = specification.get("hair_color_mode")
    if requested_mode is None:
        hair_color_mode = stable_distribution_choice(
            pigmentation.get("mode_weights") or {},
            seed,
            "{}:hair_color_mode".format(character_id),
        )
    else:
        hair_color_mode = requested_mode
    if hair_color_mode not in (
        "natural_common",
        "natural_rare",
        "dyed",
    ):
        request_error(
            "unknown_hair_color_mode",
            "Requested hair color mode is invalid",
            hair_color_mode=hair_color_mode,
        )
    pigmentation_profile_id = skin["pigmentation_profile_id"]
    profiles = pigmentation.get("profiles") or {}
    profile = profiles.get(pigmentation_profile_id)
    if profile is None:
        raise CompileError(
            "Skin references an unknown pigmentation profile"
        )
    if hair_color_mode == "dyed":
        color_distribution = {
            color_id: 1.0
            for color_id in pigmentation.get("dyed_color_ids") or []
        }
    else:
        color_distribution = profile.get(hair_color_mode) or {}
    requested_color = specification.get("hair_color_id")
    if requested_color is None:
        hair_color_id = stable_distribution_choice(
            color_distribution,
            seed,
            "{}:hair_color".format(character_id),
        )
    elif requested_color not in color_distribution:
        request_error(
            "hair_color_not_allowed",
            "Requested hair color is outside the selected profile and mode",
            hair_color_id=requested_color,
            hair_color_mode=hair_color_mode,
            pigmentation_profile_id=pigmentation_profile_id,
        )
    else:
        hair_color_id = requested_color

    gray_policy = (age.get("gray_policy") or {}).get(age_label)
    if gray_policy is None:
        raise CompileError("Age label has no gray-fraction policy")
    requested_gray = specification.get("gray_fraction")
    if requested_gray is None:
        gray_fraction = stable_gray_fraction(
            gray_policy,
            seed,
            "{}:gray_fraction".format(character_id),
        )
    else:
        gray_fraction = float(requested_gray)
        if not 0.0 <= gray_fraction <= 1.0:
            request_error(
                "invalid_gray_fraction",
                "gray_fraction must be in [0, 1]",
                gray_fraction=gray_fraction,
            )
    visible_gray_fraction = (
        float(
            (age.get("gray_policy") or {}).get(
                "dyed_visible_gray_fraction", 0.0
            )
        )
        if hair_color_mode == "dyed"
        else gray_fraction
    )

    wrinkle_pool = (
        (registry.get("component_pools") or {})
        .get("dynamic_wrinkles", {})
        .get("profiles", [])
    )
    matching_wrinkles = [
        item for item in wrinkle_pool if item.get("sex") == sex
    ]
    if len(matching_wrinkles) != 1:
        raise CompileError(
            "Facial registry must contain one wrinkle profile per sex"
        )
    wrinkle = matching_wrinkles[0]
    fixed_wrinkle_strength = float(
        (registry.get("component_pools") or {})
        .get("dynamic_wrinkles", {})
        .get("fixed_strength")
    )

    assets = [
        skin,
        teeth,
        eyebrows,
        eyelashes,
        eyes,
    ]
    if facial_hair is not None:
        assets.append(facial_hair)
    assets.append(scalp_hair)
    return {
        "age_label": age_label,
        "age_morph_id": age_morph_id,
        "assets": assets,
        "dynamic_wrinkle_profile": wrinkle,
        "dynamic_wrinkle_strength": fixed_wrinkle_strength,
        "eyebrow_asset_id": eyebrows["asset_id"],
        "eyelash_asset_id": eyelashes["asset_id"],
        "eye_asset_id": eyes["asset_id"],
        "face_material_quality_profile": compiled_quality_reference,
        "facial_hair_asset_id": (
            facial_hair["asset_id"] if facial_hair is not None else None
        ),
        "full_face_elder_weight": float(age_level["weight"]),
        "gray_fraction": round(gray_fraction, 8),
        "hair_color": copy.deepcopy(
            (pigmentation.get("palette") or {})[hair_color_id]
        ),
        "hair_color_id": hair_color_id,
        "hair_color_mode": hair_color_mode,
        "hair_presentation_mode": hair_presentation_mode,
        "pigmentation_profile_id": pigmentation_profile_id,
        "scalp_hair_asset_id": scalp_hair["asset_id"],
        "scalp_hair_display_name": scalp_hair.get("display_name"),
        "scalp_hair_female_presentation_score": float(
            scalp_hair["female_presentation_score"]
        ),
        "scalp_hair_presentation_label": scalp_hair.get(
            "presentation_label"
        ),
        "scalp_hair_silhouette_family": scalp_hair.get(
            "silhouette_family"
        ),
        "skin_asset_id": skin["asset_id"],
        "teeth_asset_id": teeth["asset_id"],
        "visible_gray_fraction": round(visible_gray_fraction, 8),
    }


def complete_appearance(asset_ids, catalog):
    slots = {catalog[asset_id].get("slot") for asset_id in asset_ids}
    has_garments = "full_body" in slots or {"upper", "lower"}.issubset(slots)
    return has_garments and {"footwear", "scalp_hair"}.issubset(slots)


def ordered_asset_ids(asset_ids, catalog):
    return sorted(
        asset_ids,
        key=lambda asset_id: (
            SLOT_ORDER.get(catalog[asset_id].get("slot"), 1000),
            asset_id,
        ),
    )


def appearance_candidates(registry, catalog):
    groups = {}
    for asset in registry.get("assets") or []:
        asset_id = asset.get("asset_id")
        if asset_id not in catalog:
            raise CompileError(
                "Compatibility registry references an unknown asset: {}".format(
                    asset_id
                )
            )
        for validation in asset.get("validations") or []:
            preset_id = validation.get("preset_id")
            if not isinstance(preset_id, str) or not preset_id:
                raise CompileError("Compatibility validation has no preset_id")
            evidence_asset_ids = validation.get("appearance_asset_ids") or []
            if not evidence_asset_ids:
                raise CompileError(
                    "Compatibility validation lacks appearance_asset_ids: {}".format(
                        preset_id
                    )
                )
            unknown = sorted(set(evidence_asset_ids) - set(catalog))
            if unknown:
                raise CompileError(
                    "Compatibility validation references unknown assets: {}".format(
                        unknown
                    )
                )
            if asset_id not in evidence_asset_ids:
                raise CompileError(
                    "Per-asset validation does not include its asset: {}".format(
                        preset_id
                    )
                )
            candidate = {
                "validation_preset_id": preset_id,
                "appearance_recipe_id": validation.get("appearance_recipe_id"),
                "appearance_asset_ids": ordered_asset_ids(
                    evidence_asset_ids, catalog
                ),
                "appearance_cleanup": validation.get("appearance_cleanup"),
                "sex": validation.get("sex"),
                "bodyfit_id": validation.get("bodyfit_id"),
                "visual_status": validation.get("visual_status"),
            }
            previous = groups.get(preset_id)
            if previous is not None and previous != candidate:
                raise CompileError(
                    "Compatibility evidence conflicts within preset: {}".format(
                        preset_id
                    )
                )
            groups[preset_id] = candidate

    candidates = []
    for candidate in groups.values():
        if candidate["visual_status"] != "accepted":
            raise CompileError(
                "Positive compatibility evidence is not accepted: {}".format(
                    candidate["validation_preset_id"]
                )
            )
        candidate["is_complete"] = complete_appearance(
            candidate["appearance_asset_ids"], catalog
        )
        candidates.append(candidate)
    return sorted(
        candidates,
        key=lambda item: (
            item.get("sex") or "",
            item.get("bodyfit_id") or "",
            item.get("appearance_recipe_id") or "",
            item["validation_preset_id"],
        ),
    )


def request_error(code, message, **details):
    raise RequestCompileError(code, message, details)


def select_face(request, faces, sex, seed, character_id):
    requested_id = request.get("face_recipe_id")
    sex_faces = sorted(
        [item for item in faces.values() if item.get("sex") == sex],
        key=lambda item: item["face_recipe_id"],
    )
    if not sex_faces:
        request_error(
            "no_face_candidates",
            "No face recipes exist for the requested sex",
            sex=sex,
        )
    if requested_id is None:
        return stable_choice(
            sex_faces, seed, "{}:face".format(character_id)
        )
    face = faces.get(requested_id)
    if face is None:
        request_error(
            "unknown_face_recipe",
            "Requested face recipe does not exist",
            face_recipe_id=requested_id,
        )
    if face.get("sex") != sex:
        request_error(
            "face_sex_mismatch",
            "Requested face recipe does not match BodyFit sex",
            face_recipe_id=requested_id,
            face_sex=face.get("sex"),
            body_sex=sex,
        )
    return face


def select_appearance(
    request,
    candidates,
    rejections,
    bodyfit_id,
    sex,
    seed,
    character_id,
):
    specification = request.get("appearance") or {}
    if not isinstance(specification, dict):
        request_error(
            "invalid_appearance_request",
            "appearance must be an object",
        )
    requested_recipe = specification.get("appearance_recipe_id")
    requested_validation = specification.get("validation_preset_id")
    require_complete = specification.get("require_complete", True)
    if not isinstance(require_complete, bool):
        request_error(
            "invalid_appearance_request",
            "appearance.require_complete must be boolean",
        )

    available = [
        item
        for item in candidates
        if item.get("bodyfit_id") == bodyfit_id
        and item.get("sex") == sex
        and (not require_complete or item.get("is_complete"))
    ]
    if requested_recipe is not None:
        available = [
            item
            for item in available
            if item.get("appearance_recipe_id") == requested_recipe
        ]
    if requested_validation is not None:
        available = [
            item
            for item in available
            if item.get("validation_preset_id") == requested_validation
        ]

    if not available:
        rejected = [
            item
            for item in rejections
            if item.get("bodyfit_id") == bodyfit_id
            and item.get("sex") == sex
            and (
                requested_recipe is None
                or item.get("appearance_recipe_id") == requested_recipe
            )
            and (
                requested_validation is None
                or item.get("preset_id") == requested_validation
            )
        ]
        available_recipes = sorted(
            {
                item.get("appearance_recipe_id")
                for item in candidates
                if item.get("bodyfit_id") == bodyfit_id
                and item.get("sex") == sex
                and item.get("is_complete")
            }
        )
        if rejected:
            request_error(
                "appearance_recipe_rejected",
                "Requested appearance has reviewed visual rejection evidence",
                bodyfit_id=bodyfit_id,
                appearance_recipe_id=requested_recipe,
                rejected_combinations=rejected,
                available_appearance_recipe_ids=available_recipes,
            )
        request_error(
            "no_compatible_appearance",
            "No reviewed compatible appearance satisfies the request",
            bodyfit_id=bodyfit_id,
            appearance_recipe_id=requested_recipe,
            validation_preset_id=requested_validation,
            available_appearance_recipe_ids=available_recipes,
        )
    available.sort(
        key=lambda item: (
            item.get("appearance_recipe_id") or "",
            item["validation_preset_id"],
        )
    )
    return stable_choice(
        available, seed, "{}:appearance".format(character_id)
    )


def compiled_character(
    request,
    body,
    face,
    appearance,
    catalog,
    bodyfit_proportion_adjustment=None,
    facial_components=None,
):
    character_id = request["character_id"]
    pipeline = face.get("pipeline") or (
        (face.get("face_generation") or {}).get("pipeline")
    )
    v3_face = pipeline == COMPLETE_PRIMARY_FACE_PIPELINE
    face_camera = face.get("face_camera") or FACE_CAMERAS.get(
        body["sex"]
    )
    appearance_asset_ids = list(appearance["appearance_asset_ids"])
    if facial_components is not None:
        independently_managed_slots = {
            "skin",
            "skin_preset",
            "eyes",
            "teeth",
            "scalp_hair",
            "eyebrows",
            "eyelashes",
            "facial_hair",
        }
        appearance_asset_ids = [
            asset_id
            for asset_id in appearance_asset_ids
            if catalog[asset_id].get("slot")
            not in independently_managed_slots
        ]
    result = {
        "preset_id": character_id,
        "character_id": character_id,
        "bodyfit_id": body["preset_id"],
        "face_recipe_id": face["face_recipe_id"],
        "sex": body["sex"],
        "body_class": body.get("body_class"),
        "review_status": "compiled-reviewed-compatible",
        "base_avatar": copy.deepcopy(body["base_avatar"]),
        "source_project": copy.deepcopy(body["source_project"]),
        "target_body_morphs": copy.deepcopy(body["target_body_morphs"]),
        "target_junction_morphs": copy.deepcopy(
            body["target_junction_morphs"]
        ),
        "body_and_junction_fingerprint": body[
            "body_and_junction_fingerprint"
        ],
        "face_camera": face_camera,
        "appearance_recipe_id": appearance["appearance_recipe_id"],
        "appearance_asset_ids": appearance_asset_ids,
        "source_appearance_asset_ids": list(
            appearance["appearance_asset_ids"]
        ),
        "appearance_validation_preset_id": appearance[
            "validation_preset_id"
        ],
        "appearance_recipe": {
            "validated_preset_id": appearance["validation_preset_id"],
            "assets": [
                {
                    "asset_id": asset_id,
                    "display_name": catalog[asset_id].get("display_name"),
                    "slot": catalog[asset_id].get("slot"),
                    "asset_form": catalog[asset_id].get("asset_form"),
                    "sex_hint": catalog[asset_id].get("sex_hint"),
                }
                for asset_id in appearance_asset_ids
            ],
        },
        "source_request": copy.deepcopy(request),
    }
    if bodyfit_proportion_adjustment is not None:
        result["bodyfit_proportion_adjustment"] = copy.deepcopy(
            bodyfit_proportion_adjustment
        )
    if v3_face:
        local_morphs = face.get("local_morphs")
        if local_morphs is None:
            local_morphs = face.get("local_face_morphs")
        primary_seed_id = face.get("primary_face_seed_id") or (
            (face.get("face_generation") or {}).get(
                "primary_seed_id"
            )
        )
        if (
            not isinstance(local_morphs, list)
            or not isinstance(primary_seed_id, str)
            or not primary_seed_id
            or not isinstance(
                face.get("local_morph_fingerprint"), str
            )
        ):
            raise CompileError(
                "V3 face recipe fields are incomplete: {}".format(
                    face.get("face_recipe_id")
                )
            )
        content_reference_signature(
            face.get("source_head_preset"),
            "V3 face source_head_preset",
        )
        content_reference_signature(
            face.get("source_facial_profile"),
            "V3 face source_facial_profile",
            require_application_mode=True,
            require_policy_binding=True,
        )
        result["face_generation"] = {
            "pipeline": COMPLETE_PRIMARY_FACE_PIPELINE,
            "primary_seed_id": primary_seed_id,
            "strength_tier": face.get("strength_tier"),
        }
        result["local_face_morphs"] = copy.deepcopy(local_morphs)
        result["local_morph_fingerprint"] = face[
            "local_morph_fingerprint"
        ]
        result["source_head_preset"] = copy.deepcopy(
            face.get("source_head_preset")
        )
        result["source_facial_profile"] = copy.deepcopy(
            face.get("source_facial_profile")
        )
    else:
        result["target_face_morphs"] = copy.deepcopy(
            face["target_face_morphs"]
        )
        result["target_face_fingerprint"] = face[
            "target_face_fingerprint"
        ]
    if not v3_face and face.get("face_generation") is not None:
        result["face_generation"] = copy.deepcopy(
            face["face_generation"]
        )
    if face.get("face_parents") is not None:
        result["face_parents"] = copy.deepcopy(face["face_parents"])
    if appearance.get("appearance_cleanup"):
        result["appearance_cleanup"] = copy.deepcopy(
            appearance["appearance_cleanup"]
        )
    if facial_components is not None:
        for field in (
            "age_label",
            "dynamic_wrinkle_strength",
            "eye_asset_id",
            "eyebrow_asset_id",
            "eyelash_asset_id",
            "facial_hair_asset_id",
            "full_face_elder_weight",
            "gray_fraction",
            "hair_color_id",
            "hair_color_mode",
            "hair_presentation_mode",
            "pigmentation_profile_id",
            "scalp_hair_asset_id",
            "scalp_hair_display_name",
            "scalp_hair_female_presentation_score",
            "scalp_hair_presentation_label",
            "scalp_hair_silhouette_family",
            "skin_asset_id",
            "teeth_asset_id",
            "visible_gray_fraction",
        ):
            result[field] = copy.deepcopy(facial_components[field])
        result["dynamic_wrinkle_profile_id"] = facial_components[
            "dynamic_wrinkle_profile"
        ]["asset_id"]
        result["face_material_quality_profile"] = copy.deepcopy(
            facial_components["face_material_quality_profile"]
        )
        result["appearance_validation_plan"] = {
            "asset_load_pacing": {
                "default_after_seconds": 2.0,
                "default_before_seconds": 1.0,
                "slots": {
                    "facial_hair": {
                        "after_seconds": 8.0,
                        "before_seconds": 4.0,
                    },
                    "scalp_hair": {
                        "after_seconds": 12.0,
                        "before_seconds": 8.0,
                    },
                    "skin": {
                        "after_seconds": 10.0,
                        "before_seconds": 4.0,
                    },
                },
            },
            "domain": "face_identity",
            "integrated_facial_assembly_validation": {
                "render_static_hair_views": True,
                "required_invariants": [
                    "body_and_junction_unchanged",
                    "face_identity_matches_recipe",
                    "eye_geometry_preserved",
                    "eye_support_preserved",
                    "hair_pigmentation_shared",
                ],
            },
            "face_camera_reference_top_z": (
                FACE_CAMERA_REFERENCE_TOP_Z[body["sex"]]
            ),
            "pose_profile": "face_identity_safety_v1",
            "required_views": [
                "reconstructed_preview",
                "face_front",
                "face_three_quarter",
                "face_profile",
                "hair_rear_three_quarter",
                "hair_rear",
                "face_blink_bilateral_front",
                "face_blink_left_front",
                "face_look_left_front",
                "face_look_right_front",
                "face_look_up_front",
                "face_look_down_front",
                "face_squint_front",
                "face_widen_front",
                "face_brow_raise_front",
                "face_brow_down_front",
                "face_smile_front",
                "face_jaw_open_front",
                "face_jaw_open_three_quarter",
            ],
            "verification_mode": "integrated_facial_assembly",
        }
        result["facial_assembly"] = {
            "age_morph_id": facial_components["age_morph_id"],
            "application_order": list(FACIAL_ASSEMBLY_ORDER),
            "asset_ids": [
                item["asset_id"]
                for item in facial_components["assets"]
            ],
            "dynamic_wrinkle_profile": copy.deepcopy(
                facial_components["dynamic_wrinkle_profile"]
            ),
            "hair_color": copy.deepcopy(
                facial_components["hair_color"]
            ),
            "face_material_quality_profile": copy.deepcopy(
                facial_components["face_material_quality_profile"]
            ),
        }
    return result


def compile_document(
    requests,
    body_library,
    face_library,
    compatibility,
    catalog_document,
    sources,
    facial_registry=None,
    proportion_decisions=None,
):
    if int(requests.get("schema_version", -1)) != 1:
        raise CompileError("Unsupported request schema")
    manifest_id = requests.get("manifest_id")
    if not isinstance(manifest_id, str) or not manifest_id:
        raise CompileError("Request manifest_id is required")
    seed = requests.get("seed")
    if not isinstance(seed, int):
        raise CompileError("Request seed must be an integer")
    characters = requests.get("characters")
    if not isinstance(characters, list) or not characters:
        raise CompileError("Request characters must be a non-empty list")
    body_application_mode = body_library.get("body_application_mode")
    if body_application_mode != "source_project":
        raise CompileError(
            "BodyFit library must use source_project application"
        )
    expected_eyeball_move_weight = body_library.get(
        "expected_eyeball_move_weight"
    )
    if not isinstance(expected_eyeball_move_weight, (int, float)):
        raise CompileError(
            "BodyFit library must define expected_eyeball_move_weight"
        )

    character_ids = [item.get("character_id") for item in characters]
    if (
        any(not isinstance(item, str) or not item for item in character_ids)
        or len(character_ids) != len(set(character_ids))
    ):
        raise CompileError("Request character IDs are invalid or duplicated")

    bodies = indexed(
        body_library.get("presets") or [],
        "preset_id",
        "BodyFit library",
    )
    proportion_adjustments = (
        compile_bodyfit_proportion_adjustments(
            proportion_decisions,
            bodies,
        )
        if proportion_decisions is not None
        else {}
    )
    face_items = (
        face_library.get("recipes")
        or face_library.get("presets")
        or []
    )
    faces = indexed(
        face_items,
        "face_recipe_id",
        "Face library",
    )
    face_resources = validate_v3_face_library(face_library)
    catalog = indexed(
        catalog_document.get("assets") or [],
        "asset_id",
        "Appearance catalog",
    )
    candidates = appearance_candidates(compatibility, catalog)
    rejections = compatibility.get("rejected_combinations") or []

    compiled = []
    request_results = []
    for request in characters:
        character_id = request["character_id"]
        try:
            bodyfit_id = request.get("bodyfit_id")
            body = bodies.get(bodyfit_id)
            if body is None:
                request_error(
                    "unknown_bodyfit",
                    "Requested BodyFit does not exist",
                    bodyfit_id=bodyfit_id,
                )
            sex = body.get("sex")
            requested_sex = request.get("sex")
            if requested_sex is not None and requested_sex != sex:
                request_error(
                    "body_sex_mismatch",
                    "Requested sex does not match BodyFit",
                    requested_sex=requested_sex,
                    body_sex=sex,
                )
            face = select_face(request, faces, sex, seed, character_id)
            appearance = select_appearance(
                request,
                candidates,
                rejections,
                bodyfit_id,
                sex,
                seed,
                character_id,
            )
            facial_components = (
                compile_facial_components(
                    request,
                    facial_registry,
                    sex,
                    seed,
                    character_id,
                )
                if facial_registry is not None
                else None
            )
            character = compiled_character(
                request,
                body,
                face,
                appearance,
                catalog,
                bodyfit_proportion_adjustment=(
                    proportion_adjustments.get(bodyfit_id)
                ),
                facial_components=facial_components,
            )
            compiled.append(character)
            request_results.append(
                {
                    "character_id": character_id,
                    "status": "compiled",
                    "bodyfit_id": bodyfit_id,
                    "face_recipe_id": face["face_recipe_id"],
                    "appearance_recipe_id": appearance[
                        "appearance_recipe_id"
                    ],
                    "appearance_validation_preset_id": appearance[
                        "validation_preset_id"
                    ],
                    "bodyfit_proportion_decision_set_id": (
                        character.get(
                            "bodyfit_proportion_adjustment",
                            {},
                        ).get("decision_set_id")
                    ),
                    "appearance_asset_ids": appearance[
                        "appearance_asset_ids"
                    ],
                    "facial_components": (
                        {
                            key: value
                            for key, value in facial_components.items()
                            if key not in ("assets", "hair_color")
                        }
                        if facial_components is not None
                        else None
                    ),
                }
            )
        except RequestCompileError as exc:
            request_results.append(
                {
                    "character_id": character_id,
                    "status": "error",
                    "error": {
                        "code": exc.code,
                        "message": str(exc),
                        "details": exc.details,
                    },
                }
            )

    errors = [item for item in request_results if item["status"] == "error"]
    success = not errors and len(compiled) == len(characters)
    result = {
        "schema_version": 1,
        "library_id": manifest_id,
        "generated_at": now(),
        "status": (
            "compiled-reviewed-compatible"
            if success
            else "compile-failed"
        ),
        "success": success,
        "seed": seed,
        "body_application_mode": body_application_mode,
        "expected_eyeball_move_weight": float(
            expected_eyeball_move_weight
        ),
        "preview_lightroom": body_library.get("preview_lightroom"),
        "face_resources": face_resources,
        "appearance_catalog": {
            "path": sources["catalog"],
            "catalog_id": catalog_document.get("catalog_id"),
        },
        "facial_registry": (
            {
                "path": sources.get("facial_registry"),
                "registry_id": facial_registry.get("registry_id"),
            }
            if facial_registry is not None
            else None
        ),
        "bodyfit_proportion_decisions": (
            {
                "decision_set_id": proportion_decisions.get(
                    "decision_set_id"
                ),
                "path": sources.get(
                    "bodyfit_proportion_decisions"
                ),
            }
            if proportion_decisions is not None
            else None
        ),
        "sources": {
            key: {
                "path": path,
                "sha256": sha256_file(path),
            }
            for key, path in sources.items()
        },
        "selection_policy": {
            "method": "sha256_seeded_choice_over_reviewed_complete_appearances",
            "unverified_assets_allowed": False,
            "rejected_combinations_allowed": False,
            "partial_output_on_error": False,
        },
        "requested_character_count": len(characters),
        "character_count": len(compiled) if success else 0,
        "presets": compiled if success else [],
        "request_results": request_results,
    }
    return result


def compile_manifest(
    requests_path,
    body_library_path,
    face_library_path,
    compatibility_path,
    catalog_path,
    output_path,
    facial_registry_path=DEFAULT_FACIAL_REGISTRY,
    proportion_decisions_path=DEFAULT_BODYFIT_PROPORTION_DECISIONS,
):
    sources = {
        "requests": canonical_path(requests_path, "Request manifest"),
        "body_library": canonical_path(body_library_path, "BodyFit library"),
        "face_library": canonical_path(face_library_path, "Face library"),
        "compatibility_registry": canonical_path(
            compatibility_path, "Compatibility registry"
        ),
        "catalog": canonical_path(catalog_path, "Appearance catalog"),
    }
    if facial_registry_path is not None:
        sources["facial_registry"] = canonical_path(
            facial_registry_path, "Facial production registry"
        )
    if proportion_decisions_path is not None:
        sources["bodyfit_proportion_decisions"] = canonical_path(
            proportion_decisions_path,
            "BodyFit proportion decisions",
        )
    output_path = os.path.realpath(os.path.abspath(output_path))
    result = compile_document(
        read_json(sources["requests"]),
        read_json(sources["body_library"]),
        read_json(sources["face_library"]),
        read_json(sources["compatibility_registry"]),
        read_json(sources["catalog"]),
        sources,
        facial_registry=(
            read_json(sources["facial_registry"])
            if "facial_registry" in sources
            else None
        ),
        proportion_decisions=(
            read_json(sources["bodyfit_proportion_decisions"])
            if "bodyfit_proportion_decisions" in sources
            else None
        ),
    )
    write_json(result, output_path)
    return {
        "success": result["success"],
        "output": output_path,
        "requested_character_count": result["requested_character_count"],
        "character_count": result["character_count"],
        "errors": [
            item for item in result["request_results"]
            if item["status"] == "error"
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", default=DEFAULT_REQUESTS)
    parser.add_argument("--body-library", default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--face-library", default=DEFAULT_FACE_LIBRARY)
    parser.add_argument("--compatibility", default=DEFAULT_COMPATIBILITY)
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument(
        "--facial-registry",
        default=DEFAULT_FACIAL_REGISTRY,
    )
    parser.add_argument(
        "--bodyfit-proportion-decisions",
        default=DEFAULT_BODYFIT_PROPORTION_DECISIONS,
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = compile_manifest(
            args.requests,
            args.body_library,
            args.face_library,
            args.compatibility,
            args.catalog,
            args.output,
            args.facial_registry,
            args.bodyfit_proportion_decisions,
        )
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
        return 0 if result["success"] else 3
    except CompileError as exc:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                },
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
