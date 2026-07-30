"""Generate deterministic, bounded face recipes from validated CC5 seeds."""

import argparse
import datetime
import hashlib
import json
import math
import os
import random


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(SCRIPT_DIR, "cc_generate_face_recipes_config.json")


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
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def vector_map(item):
    return dict(
        (entry["id"], float(entry["weight"]))
        for entry in item["target_face_morphs"]
    )


def canonical_fingerprint(entries):
    canonical = json.dumps(
        [(entry["id"], round(float(entry["weight"]), 8)) for entry in entries],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def observed_ranges(seeds):
    maps = [vector_map(seed) for seed in seeds]
    morph_ids = sorted(set().union(*(set(item) for item in maps)))
    ranges = {}
    for morph_id in morph_ids:
        values = [item.get(morph_id, 0.0) for item in maps]
        span = max(values) - min(values)
        if span > 1e-9:
            ranges[morph_id] = span
    if not ranges:
        raise GenerationError("Seed library has no variable face morph dimensions")
    return ranges


def normalized_distance(left, right, ranges):
    left_map = vector_map(left)
    right_map = vector_map(right)
    squared = 0.0
    for morph_id, span in ranges.items():
        delta = (left_map.get(morph_id, 0.0) - right_map.get(morph_id, 0.0)) / span
        squared += delta * delta
    return math.sqrt(squared / float(len(ranges)))


def sample_weights(rng, count, minimum, maximum):
    for _ in range(10000):
        raw = [rng.gammavariate(1.5, 1.0) for _ in range(count)]
        total = sum(raw)
        weights = [item / total for item in raw]
        if min(weights) >= minimum and max(weights) <= maximum:
            return weights
    raise GenerationError(
        "Unable to sample parent weights within [{}, {}]".format(minimum, maximum)
    )


def blend_candidate(rng, seeds, config, metadata):
    parent_count = rng.choice(config["parent_count_choices"])
    parents = rng.sample(seeds, parent_count)
    weights = sample_weights(
        rng,
        parent_count,
        float(config["minimum_parent_weight"]),
        float(config["maximum_parent_weight"]),
    )
    source_maps = [vector_map(parent) for parent in parents]
    morph_ids = sorted(set().union(*(set(item) for item in source_maps)))
    entries = []
    for morph_id in morph_ids:
        weight = sum(
            parent_weight * source_map.get(morph_id, 0.0)
            for parent_weight, source_map in zip(weights, source_maps)
        )
        if abs(weight) <= 1e-8:
            continue
        source = metadata[morph_id]
        entries.append(
            {
                "id": morph_id,
                "display": source["display"],
                "categories": source["categories"],
                "weight": weight,
            }
        )
    return {
        "target_face_morphs": entries,
        "target_face_fingerprint": canonical_fingerprint(entries),
        "parents": [
            {"seed_id": parent["seed_id"], "weight": weight}
            for parent, weight in zip(parents, weights)
        ],
    }


def nearest_distance(candidate, population, ranges):
    return min(normalized_distance(candidate, item, ranges) for item in population)


def generate_for_sex(sex, seeds, requested, config, rng):
    ranges = observed_ranges(seeds)
    metadata = {}
    for seed in seeds:
        for entry in seed["target_face_morphs"]:
            metadata.setdefault(entry["id"], entry)

    accepted = []
    fingerprints = set(seed["target_face_fingerprint"] for seed in seeds)
    attempts = 0
    max_attempts = int(config["maximum_candidate_attempts"])
    pool_size = int(config["candidate_pool_size"])
    minimum_seed = float(config["minimum_seed_distance"])
    minimum_recipe = float(config["minimum_recipe_distance"])

    while len(accepted) < requested:
        pool = []
        while len(pool) < pool_size and attempts < max_attempts:
            attempts += 1
            candidate = blend_candidate(rng, seeds, config, metadata)
            fingerprint = candidate["target_face_fingerprint"]
            if fingerprint in fingerprints:
                continue
            seed_distance = nearest_distance(candidate, seeds, ranges)
            if seed_distance < minimum_seed:
                continue
            recipe_distance = (
                nearest_distance(candidate, accepted, ranges) if accepted else None
            )
            if recipe_distance is not None and recipe_distance < minimum_recipe:
                continue
            candidate["minimum_seed_distance"] = seed_distance
            candidate["minimum_recipe_distance"] = recipe_distance
            pool.append(candidate)
        if not pool:
            raise GenerationError(
                "Unable to generate {} recipe {}/{} after {} attempts; "
                "reduce distance thresholds or requested count".format(
                    sex, len(accepted) + 1, requested, attempts
                )
            )
        pool.sort(
            key=lambda item: (
                item["minimum_recipe_distance"]
                if item["minimum_recipe_distance"] is not None
                else item["minimum_seed_distance"]
            ),
            reverse=True,
        )
        selected = pool[0]
        selected["recipe_id"] = "{}FACE_{:06d}".format(
            "M" if sex == "male" else "F", len(accepted) + 1
        )
        selected["sex"] = sex
        selected["method"] = "validated_seed_convex_blend"
        accepted.append(selected)
        fingerprints.add(selected["target_face_fingerprint"])

    return accepted, {
        "sex": sex,
        "requested_count": requested,
        "generated_count": len(accepted),
        "candidate_attempts": attempts,
        "normalized_dimension_count": len(ranges),
        "minimum_observed_seed_distance": min(
            item["minimum_seed_distance"] for item in accepted
        ),
        "minimum_observed_recipe_distance": min(
            item["minimum_recipe_distance"]
            for item in accepted
            if item["minimum_recipe_distance"] is not None
        ),
    }


def validate_config(config, library):
    errors = []
    if library.get("technical_validation", {}).get("success") is not True:
        errors.append("Source face seed library is not technically validated")
    if library.get("status") != "prototype-only":
        errors.append("Expected source library status prototype-only")
    if config.get("parent_count_choices") is None:
        errors.append("parent_count_choices is required")
    else:
        for count in config["parent_count_choices"]:
            if int(count) not in (2, 3):
                errors.append("Only two- or three-parent convex blends are supported")
    for sex in ("male", "female"):
        count = int(config.get("counts", {}).get(sex, 0))
        if count <= 0:
            errors.append("counts.{} must be positive".format(sex))
        available = len([seed for seed in library.get("seeds", []) if seed["sex"] == sex])
        if available < 3:
            errors.append("At least three {} seeds are required".format(sex))
    minimum = float(config.get("minimum_parent_weight", 0.0))
    maximum = float(config.get("maximum_parent_weight", 1.0))
    if minimum <= 0.0 or maximum >= 1.0 or minimum >= maximum:
        errors.append("Parent weight bounds must satisfy 0 < minimum < maximum < 1")
    if errors:
        raise GenerationError("; ".join(errors))


def generate(config_path, count_override=None, seed_override=None):
    config = read_json(config_path)
    library_path = config["source_library"]
    library = read_json(library_path)
    validate_config(config, library)
    if count_override is not None:
        config["counts"] = {"male": count_override, "female": count_override}
    if seed_override is not None:
        config["random_seed"] = seed_override

    rng = random.Random(int(config["random_seed"]))
    recipes = []
    summaries = []
    for sex in ("male", "female"):
        seeds = [item for item in library["seeds"] if item["sex"] == sex]
        generated, summary = generate_for_sex(
            sex, seeds, int(config["counts"][sex]), config, rng
        )
        recipes.extend(generated)
        summaries.append(summary)

    run_id = "{}_seed{}_{}".format(
        config["batch_id"],
        config["random_seed"],
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
    )
    output_dir = os.path.join(config["output_root"], run_id)
    output_path = os.path.join(output_dir, "face_recipes.json")
    document = {
        "schema_version": 1,
        "recipe_set_id": config["batch_id"],
        "run_id": run_id,
        "generated_at": now(),
        "status": "prototype-only",
        "source_library": library_path,
        "source_library_sha256": sha256_file(library_path),
        "random_seed": int(config["random_seed"]),
        "strategy": {
            "method": "two_or_three_seed_convex_blend",
            "parent_count_choices": config["parent_count_choices"],
            "minimum_parent_weight": config["minimum_parent_weight"],
            "maximum_parent_weight": config["maximum_parent_weight"],
            "minimum_seed_distance": config["minimum_seed_distance"],
            "minimum_recipe_distance": config["minimum_recipe_distance"],
        },
        "generation_summaries": summaries,
        "recipe_count": len(recipes),
        "recipes": recipes,
    }
    write_json(document, output_path)
    write_json(config, os.path.join(output_dir, "resolved_config.json"))
    return output_path, document


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--count-per-sex", type=int)
    parser.add_argument("--seed", type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    output_path, document = generate(
        os.path.abspath(args.config), args.count_per_sex, args.seed
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
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
