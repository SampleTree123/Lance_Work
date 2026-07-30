"""Generate CC5 faces from one complete head preset plus local Morph edits."""

import argparse
import collections
import datetime
import hashlib
import json
import math
import os
import random


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_generate_face_recipes_v3_config.json"
)
PIPELINE_ID = "complete_primary_face_plus_local_morphs_v1"
FACIAL_PROFILE_APPLICATION_MODE = "selected_avatar_content_load"
MAJOR_REGIONS = ("skull", "jaw", "nose", "eye", "mouth")
REQUIRED_SAFE_REGIONS = ("jaw", "nose")


class GenerationError(RuntimeError):
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


def is_neutral_seed(seed):
    return "neutral" in str(seed.get("seed_id", "")).lower()


def dynamic_rejection_ids(config, field):
    entries = (
        config.get("dynamic_screening", {}).get(field) or []
    )
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise GenerationError(
                "{} rejection must be an object".format(field)
            )
        item_id = entry.get("id")
        reason = entry.get("reason")
        if (
            not isinstance(item_id, str)
            or not item_id
            or not isinstance(reason, str)
            or not reason
        ):
            raise GenerationError(
                "{} rejection requires id and reason".format(field)
            )
        result.append(item_id)
    if len(result) != len(set(result)):
        raise GenerationError(
            "{} rejection IDs are not unique".format(field)
        )
    return result


def production_seeds(config, library, sex):
    rejected = set(
        dynamic_rejection_ids(config, "excluded_primary_seeds")
    )
    return sorted(
        [
            item
            for item in (library.get("seeds") or [])
            if item.get("sex") == sex
            and not is_neutral_seed(item)
            and item.get("seed_id") not in rejected
        ],
        key=lambda item: item["seed_id"],
    )


def resolve_facial_profile(library, seed):
    policy = library.get("facial_profile_policy") or {}
    application_mode = policy.get("application_mode")
    if application_mode != FACIAL_PROFILE_APPLICATION_MODE:
        raise GenerationError(
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
        raise GenerationError(
            "No Facial Profile is bound to seed: {}".format(seed_id)
        )
    path = source.get("path")
    expected_hash = source.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or not path.lower().endswith(".ccfacialprofile")
        or not isinstance(expected_hash, str)
        or len(expected_hash) != 64
    ):
        raise GenerationError(
            "Facial Profile binding is invalid: {}".format(seed_id)
        )
    return {
        "application_mode": application_mode,
        "path": os.path.realpath(path),
        "policy_binding": policy_binding,
        "sha256": expected_hash,
    }


def production_seed_records(config, library, sex):
    records = []
    for source in production_seeds(config, library, sex):
        item = dict(source)
        item["source_facial_profile"] = resolve_facial_profile(
            library, source
        )
        records.append(item)
    return records


def production_morphs(config, policy):
    rejected = set(
        dynamic_rejection_ids(config, "excluded_local_morphs")
    )
    allowed_roles = set(
        config.get("dynamic_screening", {}).get(
            "allowed_local_morph_roles", ["local"]
        )
    )
    if not allowed_roles or any(
        not isinstance(item, str) or not item
        for item in allowed_roles
    ):
        raise GenerationError(
            "allowed_local_morph_roles must contain role names"
        )
    return [
        item
        for item in (policy.get("approved_morphs") or [])
        if item.get("id") not in rejected
        and item.get("role") in allowed_roles
    ]


def seed_vector(seed):
    return {
        item["id"]: float(item["weight"])
        for item in (seed.get("target_face_morphs") or [])
    }


def policy_bounds(morph, sex):
    bounds = (morph.get("bounds_by_sex") or {}).get(sex)
    if not bounds:
        bounds = morph.get("common_bounds") or {}
    try:
        return float(bounds["minimum"]), float(bounds["maximum"])
    except Exception:
        raise GenerationError(
            "Morph has no valid {} bounds: {}".format(
                sex, morph.get("id")
            )
        )


def canonical_local_fingerprint(primary_seed_id, local_morphs):
    payload = {
        "pipeline": PIPELINE_ID,
        "primary_face_seed_id": primary_seed_id,
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
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def balanced_seed_schedule(seeds, count, rng):
    schedule = []
    while len(schedule) < count:
        cycle = list(seeds)
        rng.shuffle(cycle)
        schedule.extend(cycle)
    return schedule[:count]


def choose_regions(rng, by_region, strength_tier, limits):
    available = sorted(by_region)
    maximum = int(
        limits[
            "maximum_regions_modified_extreme"
            if strength_tier == "strong"
            else "maximum_regions_modified_normal"
        ]
    )
    maximum = min(maximum, len(available))
    minimum = min(
        maximum,
        5 if strength_tier == "strong" else 4,
    )
    count = rng.randint(minimum, maximum)
    required_count = 3 if strength_tier == "strong" else 2
    major = [item for item in MAJOR_REGIONS if item in by_region]
    chosen = rng.sample(major, min(required_count, len(major)))
    remaining = [item for item in available if item not in chosen]
    chosen.extend(rng.sample(remaining, count - len(chosen)))
    return sorted(chosen)


def bounded_local_target(
    baseline,
    direction,
    magnitude,
    minimum,
    maximum,
    absolute_limit,
):
    safe_minimum = max(minimum, -float(absolute_limit))
    safe_maximum = min(maximum, float(absolute_limit))
    if safe_minimum > safe_maximum:
        safe_minimum, safe_maximum = minimum, maximum
    target = baseline + direction * magnitude
    target = min(max(target, safe_minimum), safe_maximum)
    if abs(target - baseline) < 0.07:
        target = baseline - direction * magnitude
        target = min(max(target, safe_minimum), safe_maximum)
    return target


def make_local_candidate(
    primary,
    approved,
    policy,
    sex,
    strength_tier,
    rng,
):
    by_region = collections.defaultdict(list)
    for item in approved:
        by_region[item["region"]].append(item)
    limits = policy["sampling_limits"]
    regions = choose_regions(
        rng, by_region, strength_tier, limits
    )
    if strength_tier == "strong":
        delta_minimum = 0.24
        delta_maximum = float(limits["strong_local_delta"])
        absolute_limit = float(limits["extreme_absolute_limit"])
    else:
        delta_minimum = 0.12
        delta_maximum = float(limits["normal_local_delta"])
        absolute_limit = float(limits["ordinary_absolute_limit"])

    baseline_vector = seed_vector(primary)
    selected = []
    for region in regions:
        choices = list(by_region[region])
        rng.shuffle(choices)
        count = 1
        if (
            strength_tier == "strong"
            and len(choices) > 1
            and rng.random() < 0.35
        ):
            count = 2
        selected.extend(choices[:count])

    local_morphs = []
    for morph in sorted(selected, key=lambda value: value["id"]):
        morph_id = morph["id"]
        baseline = float(baseline_vector.get(morph_id, 0.0))
        minimum, maximum = policy_bounds(morph, sex)
        magnitude = rng.uniform(delta_minimum, delta_maximum)
        direction = rng.choice((-1.0, 1.0))
        target = bounded_local_target(
            baseline,
            direction,
            magnitude,
            minimum,
            maximum,
            absolute_limit,
        )
        if abs(target - baseline) < 0.07:
            continue
        local_morphs.append(
            {
                "baseline_weight": baseline,
                "bounds": {
                    "maximum": maximum,
                    "minimum": minimum,
                },
                "categories": morph.get("categories") or [],
                "delta": target - baseline,
                "display": morph.get("display") or morph_id,
                "id": morph_id,
                "region": morph["region"],
                "weight": target,
            }
        )
    if len({item["region"] for item in local_morphs}) < len(regions):
        raise GenerationError(
            "Unable to produce one effective Morph per selected region"
        )
    return local_morphs


def full_local_vector(primary, approved, local_morphs):
    baseline = seed_vector(primary)
    result = {
        item["id"]: float(baseline.get(item["id"], 0.0))
        for item in approved
    }
    for item in local_morphs:
        result[item["id"]] = float(item["weight"])
    return result


def normalized_local_distance(left, right, approved):
    squared = 0.0
    for morph in approved:
        morph_id = morph["id"]
        span = float(morph["common_bounds"]["maximum"]) - float(
            morph["common_bounds"]["minimum"]
        )
        span = max(span, 0.25)
        delta = (
            float(left.get(morph_id, 0.0))
            - float(right.get(morph_id, 0.0))
        ) / span
        squared += delta * delta
    return math.sqrt(squared / float(len(approved)))


def make_recipe(
    recipe_index,
    sex,
    primary,
    strength_tier,
    approved,
    policy,
    accepted_by_primary,
    recipe_seed,
    candidate_pool_size,
):
    rng = random.Random(recipe_seed)
    pool = []
    prior = accepted_by_primary.get(primary["seed_id"]) or []
    baseline_vector = full_local_vector(primary, approved, [])
    for unused_index in range(candidate_pool_size):
        local_morphs = make_local_candidate(
            primary,
            approved,
            policy,
            sex,
            strength_tier,
            rng,
        )
        vector = full_local_vector(primary, approved, local_morphs)
        comparisons = prior or [baseline_vector]
        minimum_distance = min(
            normalized_local_distance(vector, item, approved)
            for item in comparisons
        )
        pool.append(
            {
                "local_morphs": local_morphs,
                "minimum_local_distance": minimum_distance,
                "vector": vector,
            }
        )
    selected = max(
        pool,
        key=lambda item: (
            item["minimum_local_distance"],
            canonical_local_fingerprint(
                primary["seed_id"], item["local_morphs"]
            ),
        ),
    )
    prefix = "M" if sex == "male" else "F"
    recipe_id = "{}FACEV3_{:04d}".format(prefix, recipe_index)
    local_morphs = selected["local_morphs"]
    source_head_preset = primary["source_head_preset"]
    source_facial_profile = primary["source_facial_profile"]
    return {
        "face_recipe_id": recipe_id,
        "local_morph_fingerprint": canonical_local_fingerprint(
            primary["seed_id"], local_morphs
        ),
        "local_morphs": local_morphs,
        "modified_regions": sorted(
            {item["region"] for item in local_morphs}
        ),
        "pipeline": PIPELINE_ID,
        "primary_face_seed_id": primary["seed_id"],
        "recipe_seed": recipe_seed,
        "sex": sex,
        "source_head_preset": {
            "path": os.path.realpath(source_head_preset["path"]),
            "sha256": source_head_preset["sha256"],
        },
        "source_facial_profile": {
            "application_mode": source_facial_profile[
                "application_mode"
            ],
            "path": os.path.realpath(source_facial_profile["path"]),
            "policy_binding": source_facial_profile["policy_binding"],
            "sha256": source_facial_profile["sha256"],
        },
        "strength_tier": strength_tier,
        "_minimum_local_distance": selected[
            "minimum_local_distance"
        ],
        "_vector": selected["vector"],
    }


def validate_inputs(config, library, policy):
    if library.get("technical_validation", {}).get("success") is not True:
        raise GenerationError(
            "Face seed library is not technically validated"
        )
    approved = policy.get("approved_morphs") or []
    if len(approved) != int(policy.get("approved_morph_count", -1)):
        raise GenerationError("Approved Morph count is inconsistent")
    approved_ids = [item.get("id") for item in approved]
    if (
        not approved_ids
        or len(approved_ids) != len(set(approved_ids))
        or any(item.get("namespace") != "actor_head" for item in approved)
        or any(
            item.get("role") not in ("local", "macro")
            for item in approved
        )
    ):
        raise GenerationError("Identity policy local Morphs are invalid")
    count = int(config["count_per_sex"])
    if count <= 0:
        raise GenerationError("count_per_sex must be positive")
    strong_fraction = float(config["strong_fraction"])
    if strong_fraction < 0.0 or strong_fraction > 0.5:
        raise GenerationError("strong_fraction must be in [0, 0.5]")
    if int(config["candidate_pool_size"]) <= 0:
        raise GenerationError(
            "candidate_pool_size must be positive"
        )
    neutral_ids = set(
        policy.get("neutral_policy", {}).get("neutral_seed_ids") or []
    )
    all_non_neutral_ids = {
        item.get("seed_id")
        for item in (library.get("seeds") or [])
        if not is_neutral_seed(item)
    }
    rejected_seed_ids = set(
        dynamic_rejection_ids(config, "excluded_primary_seeds")
    )
    if not rejected_seed_ids.issubset(all_non_neutral_ids):
        raise GenerationError(
            "Unknown dynamically rejected primary seed IDs: {}".format(
                sorted(rejected_seed_ids - all_non_neutral_ids)
            )
        )
    all_approved_ids = set(approved_ids)
    rejected_morph_ids = set(
        dynamic_rejection_ids(config, "excluded_local_morphs")
    )
    if not rejected_morph_ids.issubset(all_approved_ids):
        raise GenerationError(
            "Unknown dynamically rejected local Morph IDs: {}".format(
                sorted(rejected_morph_ids - all_approved_ids)
            )
        )
    usable_morphs = production_morphs(config, policy)
    usable_regions = {item.get("region") for item in usable_morphs}
    if (
        len(usable_morphs) < 8
        or not set(REQUIRED_SAFE_REGIONS).issubset(usable_regions)
    ):
        raise GenerationError(
            "Dynamic screening leaves an invalid local Morph pool"
    )
    for sex in ("male", "female"):
        seeds = production_seed_records(config, library, sex)
        if len(seeds) < 2:
            raise GenerationError(
                "Expected at least two production {} seeds, found {}".format(
                    sex, len(seeds)
                )
            )
        for seed in seeds:
            if seed["seed_id"] in neutral_ids:
                raise GenerationError(
                    "Neutral seed leaked into production pool"
                )
            preset = seed.get("source_head_preset") or {}
            path = preset.get("path")
            expected_hash = preset.get("sha256")
            if not isinstance(path, str) or not os.path.isfile(path):
                raise GenerationError(
                    "Head preset is missing: {}".format(path)
                )
            if sha256_file(path) != expected_hash:
                raise GenerationError(
                    "Head preset hash changed: {}".format(path)
                )
            profile = seed["source_facial_profile"]
            profile_path = profile["path"]
            if not os.path.isfile(profile_path):
                raise GenerationError(
                    "Facial Profile is missing: {}".format(profile_path)
                )
            if sha256_file(profile_path) != profile["sha256"]:
                raise GenerationError(
                    "Facial Profile hash changed: {}".format(
                        profile_path
                    )
                )


def generate_document(config, library, policy):
    validate_inputs(config, library, policy)
    approved = production_morphs(config, policy)
    random_seed = int(config["random_seed"])
    master_rng = random.Random(random_seed)
    count = int(config["count_per_sex"])
    strong_count = int(round(count * float(config["strong_fraction"])))
    candidate_pool_size = int(config["candidate_pool_size"])
    recipes = []
    summaries = []
    primary_ids_by_sex = {}
    for sex in ("male", "female"):
        seeds = production_seed_records(config, library, sex)
        primary_ids_by_sex[sex] = [
            item["seed_id"] for item in seeds
        ]
        schedule = balanced_seed_schedule(
            seeds, count, master_rng
        )
        strong_indices = set(
            master_rng.sample(range(count), strong_count)
        )
        accepted_by_primary = collections.defaultdict(list)
        primary_usage = collections.Counter()
        tier_usage = collections.Counter()
        minimum_distances = []
        for index, primary in enumerate(schedule, 1):
            strength_tier = (
                "strong" if index - 1 in strong_indices else "normal"
            )
            recipe_seed = master_rng.getrandbits(63)
            recipe = make_recipe(
                index,
                sex,
                primary,
                strength_tier,
                approved,
                policy,
                accepted_by_primary,
                recipe_seed,
                candidate_pool_size,
            )
            accepted_by_primary[primary["seed_id"]].append(
                recipe["_vector"]
            )
            primary_usage[primary["seed_id"]] += 1
            tier_usage[strength_tier] += 1
            minimum_distances.append(
                recipe["_minimum_local_distance"]
            )
            recipe.pop("_vector", None)
            recipe.pop("_minimum_local_distance", None)
            recipes.append(recipe)
        summaries.append(
            {
                "count": count,
                "minimum_local_distance": min(minimum_distances),
                "primary_seed_usage": dict(
                    sorted(primary_usage.items())
                ),
                "sex": sex,
                "strength_tier_counts": dict(sorted(tier_usage.items())),
            }
        )

    fingerprints = [
        item["local_morph_fingerprint"] for item in recipes
    ]
    if len(fingerprints) != len(set(fingerprints)):
        raise GenerationError("Generated face fingerprints are not unique")
    return {
        "generated_at": now(),
        "generation_summaries": summaries,
        "identity_policy_id": policy.get("policy_id"),
        "pipeline": PIPELINE_ID,
        "random_seed": random_seed,
        "recipe_count": len(recipes),
        "recipes": recipes,
        "schema_version": 3,
        "seed_library_id": library.get("library_id"),
        "status": "quality-review-only",
        "strategy": {
            "candidate_pool_size": candidate_pool_size,
            "complete_head_preset_required": True,
            "facial_profile_application_mode": (
                FACIAL_PROFILE_APPLICATION_MODE
            ),
            "facial_profile_required": True,
            "dynamic_screening": config.get(
                "dynamic_screening", {}
            ),
            "local_morph_count": len(approved),
            "missing_morphs_are_preserved": True,
            "multiple_identity_parent_blending": False,
            "neutral_identity_parents_allowed": False,
            "pipeline": PIPELINE_ID,
            "production_primary_seed_ids_by_sex": (
                primary_ids_by_sex
            ),
            "sampling_limits": policy["sampling_limits"],
            "strong_fraction": float(config["strong_fraction"]),
        },
    }


def generate(config_path, count_override=None, seed_override=None):
    config_path = os.path.realpath(os.path.abspath(config_path))
    config = read_json(config_path)
    if count_override is not None:
        config["count_per_sex"] = int(count_override)
    if seed_override is not None:
        config["random_seed"] = int(seed_override)
    library_path = os.path.realpath(
        os.path.abspath(config["source_library"])
    )
    policy_path = os.path.realpath(
        os.path.abspath(config["identity_policy"])
    )
    library = read_json(library_path)
    policy = read_json(policy_path)
    document = generate_document(config, library, policy)
    document["source_library"] = {
        "path": library_path,
        "sha256": sha256_file(library_path),
    }
    document["identity_policy"] = {
        "path": policy_path,
        "sha256": sha256_file(policy_path),
    }
    run_id = "{}_seed{}_{}".format(
        config["batch_id"],
        config["random_seed"],
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
    )
    document["recipe_set_id"] = config["batch_id"]
    document["run_id"] = run_id
    output_dir = os.path.join(config["output_root"], run_id)
    output_path = os.path.join(
        output_dir,
        config.get("output_filename", "face_recipes_v3.json"),
    )
    write_json(document, output_path)
    write_json(
        config, os.path.join(output_dir, "resolved_config.json")
    )
    return output_path, document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--count-per-sex", type=int)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    output_path, document = generate(
        args.config, args.count_per_sex, args.seed
    )
    print(
        json.dumps(
            {
                "output": output_path,
                "pipeline": document["pipeline"],
                "recipe_count": document["recipe_count"],
                "summaries": document["generation_summaries"],
                "success": True,
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
