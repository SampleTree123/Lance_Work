"""Build the isolated CC5 Head Scale versus BodyFit coarse pilot."""

import argparse
import copy
import datetime
import hashlib
import json
import math
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_head_bodyfit_scale_pilot_v1_config.json"
)
PIPELINE_ID = "complete_primary_face_plus_local_morphs_v1"


class PilotBuildError(RuntimeError):
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


def resolve_path(value, base_dir=SCRIPT_DIR):
    if not isinstance(value, str) or not value:
        raise PilotBuildError("Configured path is missing")
    if not os.path.isabs(value):
        value = os.path.join(base_dir, value)
    return os.path.realpath(os.path.abspath(value))


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


def scale_token(value):
    points = int(round(float(value) * 100.0))
    if points < 0:
        return "N{:02d}".format(abs(points))
    if points > 0:
        return "P{:02d}".format(points)
    return "Z00"


def finite_scale_values(values, label):
    if not isinstance(values, list) or not values:
        raise PilotBuildError("{} must be a non-empty list".format(label))
    result = []
    for value in values:
        try:
            number = float(value)
        except Exception:
            raise PilotBuildError("{} contains an invalid value".format(label))
        if not math.isfinite(number):
            raise PilotBuildError("{} contains a non-finite value".format(label))
        result.append(number)
    if len(result) != len(set(result)):
        raise PilotBuildError("{} contains duplicate values".format(label))
    return result


def candidate_values_for_body(config, body):
    overrides = config.get("bodyfit_scale_candidate_overrides") or {}
    if not isinstance(overrides, dict):
        raise PilotBuildError(
            "bodyfit_scale_candidate_overrides must be an object"
        )
    bodyfit_id = body.get("preset_id")
    if bodyfit_id in overrides:
        return finite_scale_values(
            overrides[bodyfit_id],
            "bodyfit_scale_candidate_overrides.{}".format(bodyfit_id),
        )
    key = (
        "average_scale_candidates"
        if body.get("body_class") == "average"
        else "full_scale_candidates"
    )
    return finite_scale_values(config.get(key), key)


def seed_head_scale_baseline(seed, morph_id):
    matches = [
        item
        for item in (seed.get("target_face_morphs") or [])
        if item.get("id") == morph_id
    ]
    if len(matches) > 1:
        raise PilotBuildError(
            "Seed {} contains duplicate Head Scale targets".format(
                seed.get("seed_id")
            )
        )
    return float(matches[0]["weight"]) if matches else 0.0


def inject_head_scale(
    local_morphs,
    policy_entry,
    baseline_weight,
    target_weight,
):
    morph_id = policy_entry["id"]
    result = [
        copy.deepcopy(item)
        for item in local_morphs
        if item.get("id") != morph_id
    ]
    bounds = policy_entry.get("common_bounds") or {}
    minimum = float(bounds.get("minimum"))
    maximum = float(bounds.get("maximum"))
    target_weight = float(target_weight)
    baseline_weight = float(baseline_weight)
    if not minimum <= target_weight <= maximum:
        raise PilotBuildError(
            "Head Scale {} is outside [{}, {}]".format(
                target_weight, minimum, maximum
            )
        )
    result.append(
        {
            "baseline_weight": baseline_weight,
            "bounds": {
                "maximum": maximum,
                "minimum": minimum,
            },
            "categories": copy.deepcopy(
                policy_entry.get("categories") or []
            ),
            "delta": target_weight - baseline_weight,
            "display": policy_entry.get("display", "Head Scale"),
            "id": morph_id,
            "region": policy_entry.get("region", "skull"),
            "weight": target_weight,
        }
    )
    return sorted(result, key=lambda item: item["id"])


def common_body_fields(body):
    return {
        "base_avatar": copy.deepcopy(body["base_avatar"]),
        "body_and_junction_fingerprint": body[
            "body_and_junction_fingerprint"
        ],
        "body_class": body["body_class"],
        "bodyfit_id": body["preset_id"],
        "sex": body["sex"],
        "source_project": copy.deepcopy(body["source_project"]),
        "target_body_morphs": copy.deepcopy(
            body["target_body_morphs"]
        ),
        "target_junction_morphs": copy.deepcopy(
            body["target_junction_morphs"]
        ),
    }


def build_preset(
    body,
    recipe,
    seed,
    policy_entry,
    target_weight,
    face_camera,
    pilot_id,
):
    morph_id = policy_entry["id"]
    baseline = seed_head_scale_baseline(seed, morph_id)
    local_morphs = inject_head_scale(
        recipe.get("local_morphs") or [],
        policy_entry,
        baseline,
        target_weight,
    )
    preset_id = "HBF_{}_{}".format(
        body["preset_id"].split("_")[0],
        scale_token(target_weight),
    )
    result = common_body_fields(body)
    result.update(
        {
            "character_id": preset_id,
            "face_camera": face_camera,
            "face_generation": {
                "modified_regions": sorted(
                    set(recipe.get("modified_regions") or [])
                    | {"skull"}
                ),
                "pipeline": PIPELINE_ID,
                "primary_seed_id": recipe["primary_face_seed_id"],
                "recipe_seed": recipe.get("recipe_seed"),
                "strength_tier": recipe.get("strength_tier"),
            },
            "face_recipe_id": "{}_HBF_{}".format(
                recipe["face_recipe_id"], scale_token(target_weight)
            ),
            "head_bodyfit_scale_pilot": {
                "bodyfit_id": body["preset_id"],
                "head_scale_baseline": baseline,
                "head_scale_morph_id": morph_id,
                "head_scale_target": float(target_weight),
                "pilot_id": pilot_id,
                "reference_face_recipe_id": recipe["face_recipe_id"],
            },
            "local_face_morphs": local_morphs,
            "local_morph_fingerprint": canonical_local_fingerprint(
                recipe["primary_face_seed_id"], local_morphs
            ),
            "preset_id": preset_id,
            "review_status": "head-bodyfit-scale-coarse-candidate",
            "source_facial_profile": copy.deepcopy(
                recipe["source_facial_profile"]
            ),
            "source_head_preset": copy.deepcopy(
                recipe["source_head_preset"]
            ),
        }
    )
    return result


def build_document(
    config,
    body_library,
    seed_library,
    identity_policy,
    recipe_document,
    source_paths,
):
    if int(config.get("schema_version", -1)) != 1:
        raise PilotBuildError("Unsupported pilot config schema")
    bodies = body_library.get("presets") or []
    if len(bodies) != 8:
        raise PilotBuildError("Expected exactly eight BodyFit presets")
    if recipe_document.get("pipeline") != PIPELINE_ID:
        raise PilotBuildError("Face recipe pipeline is incompatible")

    recipe_index = {
        item["face_recipe_id"]: item
        for item in (recipe_document.get("recipes") or [])
    }
    seed_index = {
        item["seed_id"]: item
        for item in (seed_library.get("seeds") or [])
    }
    approved = [
        item
        for item in (identity_policy.get("approved_morphs") or [])
        if item.get("id") == config.get("head_scale_morph_id")
    ]
    if len(approved) != 1:
        raise PilotBuildError("Identity policy has no unique Head Scale Morph")
    policy_entry = approved[0]
    if policy_entry.get("display") != "Head Scale":
        raise PilotBuildError("Configured Morph is not Actor Head Scale")

    recipes_by_sex = {}
    seeds_by_sex = {}
    cameras = config.get("face_cameras") or {}
    for sex in ("female", "male"):
        recipe_id = (config.get("reference_recipe_ids") or {}).get(sex)
        recipe = recipe_index.get(recipe_id)
        if recipe is None or recipe.get("sex") != sex:
            raise PilotBuildError(
                "Reference {} recipe is invalid".format(sex)
            )
        seed = seed_index.get(recipe.get("primary_face_seed_id"))
        if seed is None or seed.get("sex") != sex:
            raise PilotBuildError(
                "Reference {} seed is invalid".format(sex)
            )
        camera = cameras.get(sex)
        if not isinstance(camera, str) or not camera:
            raise PilotBuildError("{} face camera is missing".format(sex))
        recipes_by_sex[sex] = recipe
        seeds_by_sex[sex] = seed

    pilot_id = config.get("pilot_id")
    if not isinstance(pilot_id, str) or not pilot_id:
        raise PilotBuildError("pilot_id is missing")
    presets = []
    selection = []
    for body in sorted(bodies, key=lambda item: item["preset_id"]):
        sex = body["sex"]
        values = candidate_values_for_body(config, body)
        for value in values:
            preset = build_preset(
                body,
                recipes_by_sex[sex],
                seeds_by_sex[sex],
                policy_entry,
                value,
                cameras[sex],
                pilot_id,
            )
            presets.append(preset)
            selection.append(
                {
                    "bodyfit_id": body["preset_id"],
                    "head_scale_target": value,
                    "preset_id": preset["preset_id"],
                    "reference_face_recipe_id": recipes_by_sex[sex][
                        "face_recipe_id"
                    ],
                }
            )

    return {
        "body_application_mode": "source_project",
        "character_count": len(presets),
        "expected_eyeball_move_weight": 0.0,
        "face_resources": {
            "identity_policy": source_paths["identity_policy"],
            "identity_policy_id": identity_policy.get("policy_id"),
            "identity_policy_sha256": sha256_file(
                source_paths["identity_policy"]
            ),
            "seed_library": source_paths["seed_library"],
            "seed_library_id": seed_library.get("library_id"),
            "seed_library_sha256": sha256_file(
                source_paths["seed_library"]
            ),
        },
        "generated_at": now(),
        "library_id": pilot_id,
        "pilot": {
            "average_scale_candidates": finite_scale_values(
                config.get("average_scale_candidates"),
                "average_scale_candidates",
            ),
            "full_scale_candidates": finite_scale_values(
                config.get("full_scale_candidates"),
                "full_scale_candidates",
            ),
            "head_scale_morph_id": policy_entry["id"],
            "reference_recipe_ids": copy.deepcopy(
                config["reference_recipe_ids"]
            ),
            "selection": selection,
        },
        "pipeline": PIPELINE_ID,
        "presets": presets,
        "preview_lightroom": body_library.get("preview_lightroom"),
        "schema_version": 1,
        "source_body_library": {
            "library_id": body_library.get("library_id"),
            "path": source_paths["body_library"],
            "sha256": sha256_file(source_paths["body_library"]),
        },
        "source_face_recipes": {
            "path": source_paths["recipe_library"],
            "recipe_set_id": recipe_document.get("recipe_set_id"),
            "sha256": sha256_file(source_paths["recipe_library"]),
        },
        "status": "quality-review-only",
    }


def build_batch(config_path, output_override=None):
    config_path = resolve_path(config_path)
    config = read_json(config_path)
    config_dir = os.path.dirname(config_path)
    source_paths = {
        key: resolve_path(config[key], config_dir)
        for key in (
            "body_library",
            "identity_policy",
            "recipe_library",
            "seed_library",
        )
    }
    for path in source_paths.values():
        if not os.path.isfile(path):
            raise PilotBuildError("Input is missing: {}".format(path))
    document = build_document(
        config,
        read_json(source_paths["body_library"]),
        read_json(source_paths["seed_library"]),
        read_json(source_paths["identity_policy"]),
        read_json(source_paths["recipe_library"]),
        source_paths,
    )
    output = resolve_path(
        output_override or config.get("output"), config_dir
    )
    write_json(document, output)
    return {
        "character_count": document["character_count"],
        "output": output,
        "pilot_id": document["library_id"],
        "success": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output")
    args = parser.parse_args()
    print(
        json.dumps(
            build_batch(args.config, args.output),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
