"""Build the deterministic 24-character CC5 facial integration request set."""

import argparse
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BODY_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_body_preset_library_v1.json"
)
DEFAULT_FACE_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_face_recipes_v3_200.json"
)
DEFAULT_REGISTRY = os.path.join(
    SCRIPT_DIR, "cc_facial_production_registry_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_character_integration_requests_v1.json"
)
REQUEST_ID = "cc_character_factory_integration_24_v1"
AGE_LABELS = ("young", "middle", "older")
HAIR_COLOR_MODES = (
    "natural_common",
    "natural_rare",
    "dyed",
)


class RequestBuildError(RuntimeError):
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
        raise RequestBuildError("{} is missing: {}".format(label, path))
    return path


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            raise RequestBuildError("{} item has no {}".format(label, key))
        if value in result:
            raise RequestBuildError(
                "{} contains duplicate {} {!r}".format(label, key, value)
            )
        result[value] = item
    return result


def registry_pool(registry, name):
    pool = (registry.get("component_pools") or {}).get(name)
    if not isinstance(pool, list) or not pool:
        raise RequestBuildError(
            "Facial registry pool is missing or empty: {}".format(name)
        )
    return list(pool)


def normal_face_recipes_by_seed(face_library):
    recipes = {}
    for item in face_library.get("recipes") or []:
        if item.get("strength_tier") != "normal":
            continue
        seed_id = item.get("primary_face_seed_id")
        if not isinstance(seed_id, str) or not seed_id:
            continue
        recipes.setdefault(seed_id, []).append(item)
    for seed_id in recipes:
        recipes[seed_id].sort(key=lambda item: item["face_recipe_id"])
    return recipes


def default_hair_candidates(registry, sex):
    policy = (
        (registry.get("production_policy") or {}).get(
            "hair_presentation"
        )
        or {}
    )
    default_policy = (policy.get("modes") or {}).get("default") or {}
    if sex == "male":
        threshold = float(default_policy.get("male_maximum_score"))
        accepted = lambda score: score <= threshold
    elif sex == "female":
        threshold = float(default_policy.get("female_minimum_score"))
        accepted = lambda score: score >= threshold
    else:
        raise RequestBuildError("Unsupported sex: {}".format(sex))
    candidates = []
    for item in registry_pool(registry, "scalp_hair"):
        if sex not in (item.get("accepted_sexes") or []):
            continue
        try:
            score = float(item.get("female_presentation_score"))
        except (TypeError, ValueError):
            raise RequestBuildError(
                "Scalp hair has no presentation score: {}".format(
                    item.get("asset_id")
                )
            )
        if accepted(score):
            candidates.append(item)
    return sorted(candidates, key=lambda item: item["asset_id"])


def stratified_hair_selection(registry, sex, count):
    candidates = default_hair_candidates(registry, sex)
    if len(candidates) < count:
        raise RequestBuildError(
            "{} default hair pool has only {} assets; need {}".format(
                sex,
                len(candidates),
                count,
            )
        )
    by_family = {}
    for item in candidates:
        family = item.get("silhouette_family")
        if not isinstance(family, str) or not family:
            raise RequestBuildError(
                "Scalp hair has no silhouette family: {}".format(
                    item.get("asset_id")
                )
            )
        by_family.setdefault(family, []).append(item)
    selected = [
        sorted(items, key=lambda item: item["asset_id"])[0]
        for unused_family, items in sorted(by_family.items())
    ]
    selected_ids = {item["asset_id"] for item in selected}
    selected.extend(
        item
        for item in candidates
        if item["asset_id"] not in selected_ids
    )
    return selected[:count]


def sex_pool(registry, name, sex, field):
    items = [
        item
        for item in registry_pool(registry, name)
        if item.get(field) == sex
    ]
    if not items:
        raise RequestBuildError(
            "{} has no {} candidates".format(name, sex)
        )
    return sorted(items, key=lambda item: item["asset_id"])


def cyclic(items, index):
    if not items:
        raise RequestBuildError("Cannot select from an empty pool")
    return items[index % len(items)]


def build(
    body_library_path=DEFAULT_BODY_LIBRARY,
    face_library_path=DEFAULT_FACE_LIBRARY,
    registry_path=DEFAULT_REGISTRY,
    output_path=DEFAULT_OUTPUT,
):
    body_library_path = resolved_file(body_library_path, "BodyFit library")
    face_library_path = resolved_file(face_library_path, "V3 face library")
    registry_path = resolved_file(
        registry_path, "Facial production registry"
    )
    body_library = read_json(body_library_path)
    face_library = read_json(face_library_path)
    registry = read_json(registry_path)

    bodies = sorted(
        body_library.get("presets") or [],
        key=lambda item: item["preset_id"],
    )
    if len(bodies) != 8:
        raise RequestBuildError(
            "Integration set requires exactly eight BodyFits"
        )
    if {item.get("sex") for item in bodies} != {"female", "male"}:
        raise RequestBuildError("BodyFit sexes are incomplete")

    face_recipes = normal_face_recipes_by_seed(face_library)
    seed_ids_by_sex = {}
    for sex in ("male", "female"):
        seed_ids = sorted(
            {
                item.get("primary_face_seed_id")
                for item in face_library.get("recipes") or []
                if item.get("sex") == sex
                and item.get("primary_face_seed_id") in face_recipes
            }
        )
        expected = 9 if sex == "male" else 8
        if len(seed_ids) != expected:
            raise RequestBuildError(
                "Expected {} {} primary face seeds; found {}".format(
                    expected,
                    sex,
                    len(seed_ids),
                )
            )
        seed_ids_by_sex[sex] = seed_ids

    skins = {
        sex: sex_pool(registry, "skins", sex, "sex")
        for sex in ("male", "female")
    }
    eyebrows = {
        sex: sex_pool(registry, "eyebrows", sex, "sex_hint")
        for sex in ("male", "female")
    }
    eyes = sorted(
        registry_pool(registry, "eyes"),
        key=lambda item: item["asset_id"],
    )
    eyelashes = sorted(
        registry_pool(registry, "eyelashes"),
        key=lambda item: item["asset_id"],
    )
    teeth = sorted(
        registry_pool(registry, "teeth"),
        key=lambda item: item["asset_id"],
    )
    facial_hair = sorted(
        registry_pool(registry, "facial_hair"),
        key=lambda item: item["asset_id"],
    )
    if (
        len(skins["male"]) + len(skins["female"]) != 21
        or len(eyes) != 12
        or len(eyebrows["male"]) + len(eyebrows["female"]) != 13
        or len(eyelashes) != 9
        or len(teeth) != 2
        or len(facial_hair) != 5
    ):
        raise RequestBuildError(
            "Production component pool sizes differ from the 24-case design"
        )

    slots_by_sex = {
        sex: [
            (body, age_label)
            for body in bodies
            if body.get("sex") == sex
            for age_label in AGE_LABELS
        ]
        for sex in ("male", "female")
    }
    hair_by_sex = {
        sex: stratified_hair_selection(
            registry,
            sex,
            len(slots_by_sex[sex]),
        )
        for sex in ("male", "female")
    }

    characters = []
    global_index = 0
    face_recipe_use_count = {}
    for sex in ("male", "female"):
        seeds = seed_ids_by_sex[sex]
        for sex_index, (body, age_label) in enumerate(slots_by_sex[sex]):
            seed_id = cyclic(seeds, sex_index)
            seed_recipes = face_recipes[seed_id]
            use_index = face_recipe_use_count.get(seed_id, 0)
            face_recipe = cyclic(seed_recipes, use_index)
            face_recipe_use_count[seed_id] = use_index + 1
            skin = cyclic(skins[sex], sex_index)
            eyebrow = cyclic(eyebrows[sex], sex_index)
            eye = cyclic(eyes, global_index)
            eyelash = cyclic(eyelashes, global_index)
            tooth = cyclic(teeth, global_index)
            scalp_hair = hair_by_sex[sex][sex_index]

            body_code = body["preset_id"].split("_", 1)[0]
            character_id = "CCINT_{}_{}".format(
                body_code,
                age_label.upper(),
            )
            components = {
                "age_label": age_label,
                "eye_asset_id": eye["asset_id"],
                "eyebrow_asset_id": eyebrow["asset_id"],
                "eyelash_asset_id": eyelash["asset_id"],
                "hair_color_mode": cyclic(
                    HAIR_COLOR_MODES,
                    global_index,
                ),
                "hair_presentation_mode": "default",
                "scalp_hair_asset_id": scalp_hair["asset_id"],
                "skin_asset_id": skin["asset_id"],
                "teeth_asset_id": tooth["asset_id"],
            }
            if sex == "male":
                beard_cycle = [None] + [
                    item["asset_id"] for item in facial_hair
                ]
                components["facial_hair_asset_id"] = cyclic(
                    beard_cycle,
                    sex_index,
                )
            else:
                components["facial_hair_asset_id"] = None
            characters.append(
                {
                    "bodyfit_id": body["preset_id"],
                    "character_id": character_id,
                    "face_recipe_id": face_recipe["face_recipe_id"],
                    "facial_components": components,
                }
            )
            global_index += 1

    if len(characters) != 24:
        raise RequestBuildError(
            "Expected 24 integration characters; built {}".format(
                len(characters)
            )
        )
    document = {
        "characters": characters,
        "generated_at": now(),
        "integration_design": {
            "age_labels": list(AGE_LABELS),
            "character_count": len(characters),
            "hair_color_modes": list(HAIR_COLOR_MODES),
            "hair_presentation_mode": "default",
            "primary_face_seed_count": len(
                set(seed_ids_by_sex["male"])
                | set(seed_ids_by_sex["female"])
            ),
            "requirements": {
                "bodyfit_age_cross_product": True,
                "cover_all_approved_eyebrows": True,
                "cover_all_approved_eyes": True,
                "cover_all_approved_eyelashes": True,
                "cover_all_approved_skins": True,
                "cover_all_approved_teeth": True,
                "cover_all_primary_face_seeds": True,
                "cover_male_beard_and_clean_shaven": True,
                "stratify_default_scalp_hair_by_silhouette": True,
            },
        },
        "manifest_id": REQUEST_ID,
        "schema_version": 1,
        "seed": 20260728,
        "sources": {
            "body_library": {
                "path": body_library_path,
                "sha256": sha256_file(body_library_path),
            },
            "face_library": {
                "path": face_library_path,
                "sha256": sha256_file(face_library_path),
            },
            "facial_registry": {
                "path": registry_path,
                "sha256": sha256_file(registry_path),
            },
        },
    }
    write_json(document, output_path)
    return document


def main():
    parser = argparse.ArgumentParser(
        description="Build the deterministic 24-character request set."
    )
    parser.add_argument("--body-library", default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--face-library", default=DEFAULT_FACE_LIBRARY)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build(
        body_library_path=args.body_library,
        face_library_path=args.face_library,
        registry_path=args.registry,
        output_path=os.path.realpath(os.path.abspath(args.output)),
    )
    print(
        "Built {} integration requests -> {}".format(
            len(document["characters"]),
            os.path.realpath(os.path.abspath(args.output)),
        )
    )


if __name__ == "__main__":
    main()
