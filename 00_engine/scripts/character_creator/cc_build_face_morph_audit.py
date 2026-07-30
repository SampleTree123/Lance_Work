"""Audit CC5 face morph catalogs and build a conservative identity policy."""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CAPTURE_ROOT = (
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge"
    r"\artifacts\face_catalog_capture_v2_20260722_01\catalogs"
)
DEFAULT_MALE_CATALOG = os.path.join(DEFAULT_CAPTURE_ROOT, "male_face_catalog.json")
DEFAULT_FEMALE_CATALOG = os.path.join(DEFAULT_CAPTURE_ROOT, "female_face_catalog.json")
DEFAULT_SEED_LIBRARY = os.path.join(SCRIPT_DIR, "cc_face_seed_library_v1.json")
DEFAULT_AUDIT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_face_morph_audit_v1.json")
DEFAULT_POLICY_OUTPUT = os.path.join(SCRIPT_DIR, "cc_face_identity_policy_v1.json")


REGION_RULES = (
    ("forehead", ("forehead",)),
    ("brow", ("brow", "eyebrow")),
    ("eye", ("eye", "eyelid", "canthus", "orbit")),
    ("cheek", ("cheek", "zygomatic")),
    ("nose", ("nose", "nostril", "nasal")),
    ("mouth", ("mouth", "lip", "philtrum")),
    ("jaw", ("jaw", "mandible")),
    ("chin", ("chin",)),
    ("ear", ("ear",)),
    ("skull", ("full head", "head shape", "skull", "scalp", "cranium")),
    ("teeth_tongue", ("teeth", "tooth", "tongue", "gum")),
)

EXCLUDED_IDENTITY_TERMS = (
    "expression",
    "viseme",
    "phoneme",
    "facial profile",
    "corrective",
    "wrinkle",
    "blink",
    "look up",
    "look down",
    "look left",
    "look right",
    "eye occlusion",
    "tearline",
    "eyelash",
    "teeth",
    "tooth",
    "tongue",
)

SEMANTIC_STOP_WORDS = {
    "actor",
    "cc",
    "embed",
    "headshot",
    "morph",
    "morphs",
    "slider",
    "sliders",
}


class AuditError(RuntimeError):
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


def normalize_display(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value).lower()))


def semantic_key(value):
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", str(value).lower())
        if token not in SEMANTIC_STOP_WORDS
    ]
    return " ".join(tokens)


def merged_text(entry):
    return " ".join(
        [entry.get("id", ""), entry.get("display", "")]
        + list(entry.get("categories") or [])
    ).lower()


def classify_region(entry):
    text = merged_text(entry)
    for region, terms in REGION_RULES:
        if any(term in text for term in terms):
            return region
    return "other"


def classify_namespace(entry):
    categories = [item.lower() for item in entry.get("categories") or []]
    text = " ".join(categories)
    if "headshot" in text:
        return "headshot"
    if any(item.startswith("actor/head") for item in categories):
        if any(item.startswith("actor/hd head") for item in categories):
            return "actor_hd_head"
        return "actor_head"
    if any(item.startswith("actor parts") for item in categories):
        return "actor_parts"
    if any("cc embed morphs" in item for item in categories):
        return "cc_embed_other"
    if categories:
        return categories[-1].split("/")[0].replace(" ", "_")
    return "uncategorized"


def is_neutral_seed(seed):
    return "neutral" in seed.get("seed_id", "").lower()


def seed_usage(seed_library):
    usage = collections.defaultdict(lambda: {"all": set(), "identity": set()})
    identity_seeds = {"male": [], "female": []}
    neutral_seeds = {"male": [], "female": []}
    for seed in seed_library.get("seeds") or []:
        neutral = is_neutral_seed(seed)
        target = neutral_seeds if neutral else identity_seeds
        target.setdefault(seed["sex"], []).append(seed["seed_id"])
        for morph in seed.get("target_face_morphs") or []:
            usage[morph["id"]]["all"].add(seed["seed_id"])
            if not neutral:
                usage[morph["id"]]["identity"].add(seed["seed_id"])
    return usage, identity_seeds, neutral_seeds


def merge_catalogs(catalogs):
    by_id = collections.defaultdict(
        lambda: {
            "displays": set(),
            "categories": set(),
            "per_sex": {},
        }
    )
    for sex, document in catalogs.items():
        for entry in document.get("entries") or []:
            item = by_id[entry["id"]]
            item["displays"].add(entry.get("display") or entry["id"])
            item["categories"].update(entry.get("categories") or [])
            item["per_sex"][sex] = {
                "minimum": float(entry["minimum"]),
                "maximum": float(entry["maximum"]),
                "default_weight": float(entry["default_weight"]),
            }
    merged = []
    for morph_id in sorted(by_id):
        source = by_id[morph_id]
        displays = sorted(source["displays"], key=lambda item: item.lower())
        entry = {
            "id": morph_id,
            "display": displays[0],
            "display_variants": displays,
            "categories": sorted(source["categories"]),
            "per_sex": source["per_sex"],
        }
        entry["namespace"] = classify_namespace(entry)
        entry["region"] = classify_region(entry)
        merged.append(entry)
    return merged


def common_bounds(entry):
    variants = list(entry["per_sex"].values())
    minimum = max(item["minimum"] for item in variants)
    maximum = min(item["maximum"] for item in variants)
    return minimum, maximum


def observed_by_sex(seed_library, morph_id):
    result = {}
    for sex in ("male", "female"):
        values = []
        for seed in seed_library.get("seeds") or []:
            if seed.get("sex") != sex or is_neutral_seed(seed):
                continue
            vector = dict(
                (item["id"], float(item["weight"]))
                for item in seed.get("target_face_morphs") or []
            )
            values.append(vector.get(morph_id, 0.0))
        if values:
            result[sex] = {"minimum": min(values), "maximum": max(values)}
    return result


def approved_seed_local(entry, usage):
    text = merged_text(entry)
    if not usage[entry["id"]]["identity"]:
        return False
    if entry["namespace"] != "actor_head":
        return False
    if not entry["id"].lower().startswith("cc embed morphs/embed_"):
        return False
    if entry["region"] in ("other", "teeth_tongue"):
        return False
    if any(term in text for term in EXCLUDED_IDENTITY_TERMS):
        return False
    return True


def collision_groups(entries, key_function):
    grouped = collections.defaultdict(list)
    for entry in entries:
        key = key_function(entry["display"])
        if key:
            grouped[key].append(entry)
    result = []
    for key, items in sorted(grouped.items()):
        ids = sorted({item["id"] for item in items})
        if len(ids) <= 1:
            continue
        result.append(
            {
                "key": key,
                "ids": ids,
                "items": [
                    {
                        "id": item["id"],
                        "display": item["display"],
                        "namespace": item["namespace"],
                        "region": item["region"],
                    }
                    for item in items
                ],
            }
        )
    return result


def build_audit(male_path, female_path, seed_path):
    paths = {"male": male_path, "female": female_path}
    catalogs = dict((sex, read_json(path)) for sex, path in paths.items())
    seeds = read_json(seed_path)
    usage, identity_seeds, neutral_seeds = seed_usage(seeds)
    entries = merge_catalogs(catalogs)

    namespace_counts = collections.Counter(item["namespace"] for item in entries)
    region_counts = collections.Counter(item["region"] for item in entries)
    approved = [item for item in entries if approved_seed_local(item, usage)]
    approved_by_region = collections.Counter(item["region"] for item in approved)
    headshot = [item for item in entries if item["namespace"] == "headshot"]

    exact_collisions = collision_groups(entries, normalize_display)
    semantic_collisions = collision_groups(entries, semantic_key)
    cross_namespace = [
        group
        for group in semantic_collisions
        if len({item["namespace"] for item in group["items"]}) > 1
    ]

    policy_morphs = []
    for entry in approved:
        minimum, maximum = common_bounds(entry)
        role = "macro" if entry["region"] == "skull" else "local"
        policy_morphs.append(
            {
                "id": entry["id"],
                "display": entry["display"],
                "categories": entry["categories"],
                "namespace": entry["namespace"],
                "region": entry["region"],
                "role": role,
                "common_bounds": {"minimum": minimum, "maximum": maximum},
                "bounds_by_sex": entry["per_sex"],
                "observed_identity_range_by_sex": observed_by_sex(
                    seeds, entry["id"]
                ),
                "identity_seed_users": sorted(usage[entry["id"]]["identity"]),
                "approval": "seed_observed_actor_head",
            }
        )

    audit = {
        "schema_version": 1,
        "audit_id": "cc5_face_morph_audit_v1",
        "generated_at": now(),
        "sources": {
            sex: {
                "path": paths[sex],
                "sha256": sha256_file(paths[sex]),
                "catalog_fingerprint_sha256": catalogs[sex].get(
                    "catalog_fingerprint_sha256"
                ),
                "entry_count": len(catalogs[sex].get("entries") or []),
            }
            for sex in ("male", "female")
        },
        "seed_library": {
            "path": seed_path,
            "sha256": sha256_file(seed_path),
            "identity_seeds": identity_seeds,
            "neutral_technical_seeds": neutral_seeds,
        },
        "summary": {
            "merged_unique_id_count": len(entries),
            "shared_sex_id_count": sum(
                len(item["per_sex"]) == 2 for item in entries
            ),
            "namespace_counts": dict(sorted(namespace_counts.items())),
            "region_counts": dict(sorted(region_counts.items())),
            "approved_seed_observed_count": len(approved),
            "approved_by_region": dict(sorted(approved_by_region.items())),
            "headshot_review_count": len(headshot),
            "exact_display_collision_group_count": len(exact_collisions),
            "semantic_collision_group_count": len(semantic_collisions),
            "cross_namespace_semantic_collision_group_count": len(cross_namespace),
        },
        "exact_display_collision_groups": exact_collisions,
        "semantic_collision_groups": semantic_collisions,
        "cross_namespace_semantic_collision_groups": cross_namespace,
        "headshot_review_items": headshot,
        "entries": entries,
    }

    policy = {
        "schema_version": 1,
        "policy_id": "adult_face_identity_policy_v1",
        "generated_at": now(),
        "status": "pilot-safe",
        "source_audit_id": audit["audit_id"],
        "neutral_policy": {
            "identity_parent_eligible": False,
            "technical_baseline_eligible": True,
            "neutral_seed_ids": sorted(
                neutral_seeds.get("male", []) + neutral_seeds.get("female", [])
            ),
        },
        "duplicate_policy": {
            "same_id_multiple_category_paths": "merged_by_stable_id",
            "same_name_different_ids": "mutually_exclusive_until_visual_probe",
            "headshot_and_plugin_candidates": "audit_only_in_v1",
            "cross_namespace_collision_groups": cross_namespace,
        },
        "sampling_limits": {
            "normal_local_delta": 0.32,
            "strong_local_delta": 0.48,
            "ordinary_absolute_limit": 0.9,
            "extreme_absolute_limit": 1.0,
            "maximum_regions_modified_normal": 5,
            "maximum_regions_modified_extreme": 7,
        },
        "approved_morph_count": len(policy_morphs),
        "approved_morphs": policy_morphs,
        "excluded_from_v1_randomization": [
            "Headshot and third-party namespaces",
            "expression, viseme, wrinkle, corrective, gaze and blink morphs",
            "eyelash, eye-occlusion, tearline, teeth and tongue morphs",
            "unobserved Actor/Head controls",
        ],
    }
    return audit, policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--male-catalog", default=DEFAULT_MALE_CATALOG)
    parser.add_argument("--female-catalog", default=DEFAULT_FEMALE_CATALOG)
    parser.add_argument("--seed-library", default=DEFAULT_SEED_LIBRARY)
    parser.add_argument("--audit-output", default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument("--policy-output", default=DEFAULT_POLICY_OUTPUT)
    args = parser.parse_args()
    for path in (args.male_catalog, args.female_catalog, args.seed_library):
        if not os.path.isfile(path):
            raise AuditError("Missing input: {}".format(path))
    audit, policy = build_audit(
        os.path.realpath(args.male_catalog),
        os.path.realpath(args.female_catalog),
        os.path.realpath(args.seed_library),
    )
    write_json(audit, os.path.realpath(args.audit_output))
    write_json(policy, os.path.realpath(args.policy_output))
    print(
        json.dumps(
            {
                "success": True,
                "audit_output": os.path.realpath(args.audit_output),
                "policy_output": os.path.realpath(args.policy_output),
                "summary": audit["summary"],
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
