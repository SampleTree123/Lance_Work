"""Generate diverse CC5 faces from identity anchors and approved local morphs."""

import argparse
import collections
import datetime
import hashlib
import json
import math
import os
import random


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(SCRIPT_DIR, "cc_generate_face_recipes_v2_1_config.json")


class GenerationError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
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


def is_neutral_seed(seed):
    return "neutral" in seed.get("seed_id", "").lower()


def vector_map(item):
    return dict(
        (entry["id"], float(entry["weight"]))
        for entry in item.get("target_face_morphs") or []
    )


def canonical_entries(vector, metadata):
    result = []
    for morph_id in sorted(vector):
        weight = float(vector[morph_id])
        if abs(weight) <= 1e-8:
            continue
        if morph_id not in metadata:
            raise GenerationError("Missing metadata for morph {}".format(morph_id))
        source = metadata[morph_id]
        result.append(
            {
                "id": morph_id,
                "display": source.get("display") or morph_id,
                "categories": source.get("categories") or [],
                "weight": weight,
            }
        )
    return result


def canonical_fingerprint(entries):
    canonical = json.dumps(
        [(item["id"], round(float(item["weight"]), 8)) for item in entries],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def blend_vectors(left, right, right_weight):
    left_map = vector_map(left) if "target_face_morphs" in left else left
    right_map = vector_map(right) if "target_face_morphs" in right else right
    morph_ids = set(left_map) | set(right_map)
    return dict(
        (
            morph_id,
            (1.0 - right_weight) * left_map.get(morph_id, 0.0)
            + right_weight * right_map.get(morph_id, 0.0),
        )
        for morph_id in morph_ids
    )


def build_metadata(seed_library, approved_morphs):
    metadata = {}
    for seed in seed_library.get("seeds") or []:
        for entry in seed.get("target_face_morphs") or []:
            metadata.setdefault(entry["id"], entry)
    for entry in approved_morphs:
        metadata.setdefault(entry["id"], entry)
    return metadata


def distance_dimensions(seeds, approved):
    maps = [vector_map(seed) for seed in seeds]
    dimensions = {}
    all_ids = set().union(*(set(item) for item in maps))
    approved_by_id = dict((item["id"], item) for item in approved)
    all_ids.update(approved_by_id)
    for morph_id in all_ids:
        values = [item.get(morph_id, 0.0) for item in maps]
        span = max(values) - min(values)
        if morph_id in approved_by_id:
            bounds = approved_by_id[morph_id]["common_bounds"]
            bound_span = float(bounds["maximum"]) - float(bounds["minimum"])
            span = max(span, min(bound_span, 1.0), 0.25)
        if span > 1e-8:
            dimensions[morph_id] = span
    if not dimensions:
        raise GenerationError("No usable face distance dimensions")
    return dimensions


def normalized_distance(left, right, dimensions):
    left_map = vector_map(left) if "target_face_morphs" in left else left
    right_map = vector_map(right) if "target_face_morphs" in right else right
    squared = 0.0
    for morph_id, span in dimensions.items():
        delta = (left_map.get(morph_id, 0.0) - right_map.get(morph_id, 0.0)) / span
        squared += delta * delta
    return math.sqrt(squared / float(len(dimensions)))


def farthest_seed(source, seeds, dimensions):
    candidates = [item for item in seeds if item["seed_id"] != source["seed_id"]]
    return max(
        candidates,
        key=lambda item: (
            normalized_distance(source, item, dimensions),
            item["seed_id"],
        ),
    )


def bounded_target(current, delta, morph, sex, absolute_limit):
    bounds = morph.get("bounds_by_sex", {}).get(sex) or morph["common_bounds"]
    minimum = float(bounds["minimum"])
    maximum = float(bounds["maximum"])
    safe_minimum = max(minimum, -float(absolute_limit))
    safe_maximum = min(maximum, float(absolute_limit))
    if safe_minimum > safe_maximum:
        safe_minimum, safe_maximum = minimum, maximum

    target = current + delta
    target = min(max(target, safe_minimum), safe_maximum)
    if abs(target - current) < min(0.08, abs(delta) * 0.5):
        target = current - delta
        target = min(max(target, safe_minimum), safe_maximum)
    return target


def conflict_map(policy):
    result = collections.defaultdict(set)
    groups = policy.get("duplicate_policy", {}).get(
        "cross_namespace_collision_groups", []
    )
    for group in groups:
        ids = set(group.get("ids") or [])
        for morph_id in ids:
            result[morph_id].update(ids - {morph_id})
    return result


def select_morphs(rng, by_region, regions, mode, conflicts):
    selected = []
    selected_ids = set()
    for region in regions:
        choices = [
            item
            for item in by_region[region]
            if not (conflicts[item["id"]] & selected_ids)
        ]
        if not choices:
            continue
        count = 1
        if mode == "controlled_extreme" and len(choices) > 1 and rng.random() < 0.6:
            count = 2
        elif mode == "regional_sculpt" and len(choices) > 1 and rng.random() < 0.3:
            count = 2
        rng.shuffle(choices)
        for item in choices:
            if len([m for m in selected if m["region"] == region]) >= count:
                break
            if conflicts[item["id"]] & selected_ids:
                continue
            selected.append(item)
            selected_ids.add(item["id"])
    return selected


def apply_regional_sculpt(rng, vector, sex, approved, policy, mode, secondary=None):
    by_region = collections.defaultdict(list)
    for item in approved:
        by_region[item["region"]].append(item)
    available_regions = sorted(by_region)
    required_major = [
        item
        for item in ("skull", "jaw", "nose", "eye", "mouth")
        if item in by_region
    ]
    limits = policy["sampling_limits"]
    if mode == "controlled_extreme":
        region_count = min(
            int(limits["maximum_regions_modified_extreme"]),
            len(available_regions),
        )
        delta_limit = float(limits["strong_local_delta"])
        absolute_limit = float(limits["extreme_absolute_limit"])
    else:
        region_count = rng.randint(
            max(3, int(limits["maximum_regions_modified_normal"]) - 1),
            min(int(limits["maximum_regions_modified_normal"]), len(available_regions)),
        )
        delta_limit = float(limits["normal_local_delta"])
        absolute_limit = float(limits["ordinary_absolute_limit"])

    chosen_regions = []
    if required_major:
        chosen_regions.extend(rng.sample(required_major, min(2, len(required_major))))
    remaining = [item for item in available_regions if item not in chosen_regions]
    chosen_regions.extend(rng.sample(remaining, region_count - len(chosen_regions)))
    morphs = select_morphs(
        rng,
        by_region,
        chosen_regions,
        mode,
        conflict_map(policy),
    )

    secondary_map = vector_map(secondary) if secondary is not None else {}
    modifications = []
    for morph in morphs:
        morph_id = morph["id"]
        current = vector.get(morph_id, 0.0)
        if mode == "controlled_extreme":
            away = current - secondary_map.get(morph_id, 0.0)
            if abs(away) >= 0.08:
                delta = away * rng.uniform(0.28, 0.48)
            else:
                delta = rng.choice((-1.0, 1.0)) * rng.uniform(0.28, delta_limit)
        else:
            delta = rng.choice((-1.0, 1.0)) * rng.uniform(0.16, delta_limit)
        target = bounded_target(current, delta, morph, sex, absolute_limit)
        if abs(target - current) <= 0.04:
            continue
        vector[morph_id] = target
        modifications.append(
            {
                "id": morph_id,
                "display": morph["display"],
                "region": morph["region"],
                "before": current,
                "after": target,
                "delta": target - current,
            }
        )
    return modifications


def make_candidate(
    mode,
    sex,
    seeds,
    approved,
    policy,
    dimensions,
    metadata,
    rng,
    primary=None,
):
    primary = primary or rng.choice(seeds)
    secondary = farthest_seed(primary, seeds, dimensions)
    parents = [{"seed_id": primary["seed_id"], "weight": 1.0}]
    modifications = []

    if mode == "direct_anchor":
        vector = vector_map(primary)
    elif mode == "dominant_blend":
        secondary_weight = rng.uniform(0.08, 0.18)
        vector = blend_vectors(primary, secondary, secondary_weight)
        parents = [
            {"seed_id": primary["seed_id"], "weight": 1.0 - secondary_weight},
            {"seed_id": secondary["seed_id"], "weight": secondary_weight},
        ]
    elif mode in ("regional_sculpt", "controlled_extreme"):
        vector = vector_map(primary)
        modifications = apply_regional_sculpt(
            rng,
            vector,
            sex,
            approved,
            policy,
            mode,
            secondary if mode == "controlled_extreme" else None,
        )
        if mode == "controlled_extreme":
            parents.append(
                {
                    "seed_id": secondary["seed_id"],
                    "weight": 0.0,
                    "role": "extrapolation_reference_only",
                }
            )
    else:
        raise GenerationError("Unsupported generation mode {}".format(mode))

    entries = canonical_entries(vector, metadata)
    return {
        "sex": sex,
        "method": mode,
        "primary_seed_id": primary["seed_id"],
        "parents": parents,
        "modified_regions": sorted({item["region"] for item in modifications}),
        "modifications": modifications,
        "target_face_morphs": entries,
        "target_face_fingerprint": canonical_fingerprint(entries),
        "_vector": vector,
    }


def candidate_score(candidate, accepted, seeds, dimensions):
    if accepted:
        return min(
            normalized_distance(candidate["_vector"], item["_vector"], dimensions)
            for item in accepted
        )
    maps = [vector_map(item) for item in seeds]
    centroid = {}
    for morph_id in dimensions:
        centroid[morph_id] = sum(
            item.get(morph_id, 0.0) for item in maps
        ) / float(len(maps))
    return normalized_distance(candidate["_vector"], centroid, dimensions)


def generate_for_sex(sex, seeds, approved, policy, config, metadata, rng):
    dimensions = distance_dimensions(seeds, approved)
    mode_counts = config["mode_counts"]
    schedule = []
    mode_order = (
        "direct_anchor",
        "dominant_blend",
        "regional_sculpt",
        "controlled_extreme",
    )
    for mode in mode_order:
        schedule.extend([mode] * int(mode_counts[sex][mode]))

    accepted = []
    fingerprints = set()
    pool_size = int(config["candidate_pool_size"])
    maximum_primary_uses = int(
        config.get("maximum_primary_anchor_uses", len(schedule))
    )
    primary_usage = collections.Counter()
    attempts = collections.Counter()
    for mode in schedule:
        pool = []
        eligible_seeds = [
            item
            for item in seeds
            if primary_usage[item["seed_id"]] < maximum_primary_uses
        ]
        if not eligible_seeds:
            raise GenerationError(
                "Primary anchor usage limit exhausted for {}".format(sex)
            )
        requested_primaries = list(eligible_seeds)
        if mode != "direct_anchor":
            requested_primaries.extend(
                rng.choice(eligible_seeds) for _ in range(pool_size)
            )
        for primary in requested_primaries:
            attempts[mode] += 1
            candidate = make_candidate(
                mode,
                sex,
                seeds,
                approved,
                policy,
                dimensions,
                metadata,
                rng,
                primary=primary,
            )
            if candidate["target_face_fingerprint"] in fingerprints:
                continue
            if mode in ("regional_sculpt", "controlled_extreme") and not candidate[
                "modifications"
            ]:
                continue
            candidate["minimum_distance_to_accepted"] = candidate_score(
                candidate, accepted, seeds, dimensions
            )
            pool.append(candidate)
        if not pool:
            raise GenerationError(
                "No unique {} candidate available for {}".format(mode, sex)
            )
        selected = max(
            pool,
            key=lambda item: (
                -primary_usage[item["primary_seed_id"]],
                item["minimum_distance_to_accepted"],
                item["target_face_fingerprint"],
            ),
        )
        selected["recipe_id"] = "{}FACE{}_{:04d}".format(
            "M" if sex == "male" else "F",
            config.get("recipe_id_version", "V2"),
            len(accepted) + 1,
        )
        accepted.append(selected)
        fingerprints.add(selected["target_face_fingerprint"])
        primary_usage[selected["primary_seed_id"]] += 1

    for item in accepted:
        item.pop("_vector", None)
    return accepted, {
        "sex": sex,
        "generated_count": len(accepted),
        "mode_counts": dict(collections.Counter(item["method"] for item in accepted)),
        "candidate_attempts": dict(attempts),
        "distance_dimension_count": len(dimensions),
        "minimum_pairwise_distance": min(
            item["minimum_distance_to_accepted"]
            for item in accepted[1:]
        ),
        "identity_anchor_count": len(seeds),
        "identity_anchors_used": sorted({item["primary_seed_id"] for item in accepted}),
        "maximum_primary_anchor_uses": maximum_primary_uses,
        "primary_anchor_usage": dict(sorted(primary_usage.items())),
    }


def validate_inputs(config, library, policy):
    errors = []
    if library.get("technical_validation", {}).get("success") is not True:
        errors.append("Face seed library is not technically validated")
    if not policy.get("approved_morphs"):
        errors.append("Identity policy has no approved morphs")
    neutral_ids = set(
        policy.get("neutral_policy", {}).get("neutral_seed_ids") or []
    )
    for sex in ("male", "female"):
        seeds = [
            item
            for item in library.get("seeds") or []
            if item.get("sex") == sex and not is_neutral_seed(item)
        ]
        if len(seeds) < 3:
            errors.append("At least three non-neutral {} seeds are required".format(sex))
        if any(item["seed_id"] in neutral_ids for item in seeds):
            errors.append("Neutral seed leaked into {} identity pool".format(sex))
        configured = sum(int(value) for value in config["mode_counts"][sex].values())
        if configured != int(config["counts"][sex]):
            errors.append("Mode counts do not sum to counts.{}".format(sex))
        maximum_primary_uses = int(
            config.get("maximum_primary_anchor_uses", configured)
        )
        if maximum_primary_uses <= 0:
            errors.append("maximum_primary_anchor_uses must be positive")
        elif len(seeds) * maximum_primary_uses < configured:
            errors.append(
                "Primary anchor capacity is too small for counts.{}".format(sex)
            )
    if errors:
        raise GenerationError("; ".join(errors))


def generate(config_path, count_override=None, seed_override=None):
    config_path = os.path.realpath(os.path.abspath(config_path))
    config = read_json(config_path)
    library_path = os.path.realpath(config["source_library"])
    policy_path = os.path.realpath(config["identity_policy"])
    library = read_json(library_path)
    policy = read_json(policy_path)
    if seed_override is not None:
        config["random_seed"] = seed_override
    if count_override is not None:
        raise GenerationError(
            "V2 count overrides require explicit mode counts; edit the config instead"
        )
    validate_inputs(config, library, policy)

    approved = policy["approved_morphs"]
    metadata = build_metadata(library, approved)
    rng = random.Random(int(config["random_seed"]))
    recipes = []
    summaries = []
    for sex in ("male", "female"):
        seeds = [
            item
            for item in library["seeds"]
            if item["sex"] == sex and not is_neutral_seed(item)
        ]
        generated, summary = generate_for_sex(
            sex, seeds, approved, policy, config, metadata, rng
        )
        recipes.extend(generated)
        summaries.append(summary)

    run_id = "{}_seed{}_{}".format(
        config["batch_id"],
        config["random_seed"],
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
    )
    output_dir = os.path.join(config["output_root"], run_id)
    output_path = os.path.join(
        output_dir, config.get("output_filename", "face_recipes_v2.json")
    )
    document = {
        "schema_version": 2,
        "recipe_set_id": config["batch_id"],
        "run_id": run_id,
        "generated_at": now(),
        "status": "quality-review-only",
        "source_library": library_path,
        "source_library_sha256": sha256_file(library_path),
        "identity_policy": policy_path,
        "identity_policy_sha256": sha256_file(policy_path),
        "random_seed": int(config["random_seed"]),
        "strategy": {
            "method": "identity_anchor_with_bounded_local_sculpt",
            "neutral_identity_parents_allowed": False,
            "headshot_randomization_allowed": False,
            "mode_counts": config["mode_counts"],
            "candidate_pool_size": config["candidate_pool_size"],
            "maximum_primary_anchor_uses": config.get(
                "maximum_primary_anchor_uses"
            ),
            "sampling_limits": policy["sampling_limits"],
        },
        "generation_summaries": summaries,
        "recipe_count": len(recipes),
        "recipes": recipes,
    }
    write_json(document, output_path)
    write_json(config, os.path.join(output_dir, "resolved_config.json"))
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
                "success": True,
                "output": output_path,
                "recipe_count": document["recipe_count"],
                "summaries": document["generation_summaries"],
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
