"""Bind current V2.1 face recipes to a sex-matched average BodyFit for review."""

import argparse
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BODY_LIBRARY = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v1.json")
DEFAULT_FACE_RECIPES = (
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_face_recipes_v2_1"
    r"\adult_face_recipes_v2_1_balanced_pilot_32_seed20260723_20260723_021608_964917"
    r"\face_recipes_v2_1.json"
)
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_face_quality_batch_v2_1_32.json")
FACE_CAMERAS = {
    "male": (
        r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera"
        r"\Headshot Ref\Ref Cam Male L.ccCam"
    ),
    "female": (
        r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera"
        r"\Headshot Ref\Ref Cam Female L.ccCam"
    ),
}


class BatchBuildError(RuntimeError):
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


def select_average_body(presets, sex):
    matches = []
    for item in presets:
        if item.get("sex") != sex:
            continue
        searchable = "{} {}".format(
            item.get("preset_id", ""), item.get("body_class", "")
        ).lower()
        if "average" in searchable:
            matches.append(item)
    if len(matches) != 1:
        raise BatchBuildError(
            "Expected one average {} BodyFit, found {}".format(sex, len(matches))
        )
    return matches[0]


def build_batch(body_library_path, face_recipes_path, output_path):
    body_library_path = os.path.realpath(os.path.abspath(body_library_path))
    face_recipes_path = os.path.realpath(os.path.abspath(face_recipes_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    for path, label in (
        (body_library_path, "BodyFit library"),
        (face_recipes_path, "V2 face recipes"),
    ):
        if not os.path.isfile(path):
            raise BatchBuildError("{} is missing: {}".format(label, path))

    body_library = read_json(body_library_path)
    face_document = read_json(face_recipes_path)
    recipes = face_document.get("recipes") or []
    if len(recipes) != 32:
        raise BatchBuildError("Expected 32 V2 face recipes, found {}".format(len(recipes)))
    if any("neutral" in item.get("primary_seed_id", "").lower() for item in recipes):
        raise BatchBuildError("Neutral seed found in V2 primary identity parents")

    average_bodies = {
        sex: select_average_body(body_library.get("presets") or [], sex)
        for sex in ("male", "female")
    }
    characters = []
    for recipe in recipes:
        sex = recipe["sex"]
        body = average_bodies[sex]
        character_id = "V2_{}".format(recipe["recipe_id"])
        characters.append(
            {
                "preset_id": character_id,
                "character_id": character_id,
                "bodyfit_id": body["preset_id"],
                "face_recipe_id": recipe["recipe_id"],
                "sex": sex,
                "body_class": body.get("body_class"),
                "review_status": "face-v2-quality-candidate",
                "base_avatar": body["base_avatar"],
                "source_project": body["source_project"],
                "target_body_morphs": body["target_body_morphs"],
                "target_junction_morphs": body["target_junction_morphs"],
                "body_and_junction_fingerprint": body[
                    "body_and_junction_fingerprint"
                ],
                "target_face_morphs": recipe["target_face_morphs"],
                "target_face_fingerprint": recipe["target_face_fingerprint"],
                "face_camera": FACE_CAMERAS[sex],
                "face_generation": {
                    "method": recipe["method"],
                    "primary_seed_id": recipe["primary_seed_id"],
                    "parents": recipe.get("parents") or [],
                    "modified_regions": recipe.get("modified_regions") or [],
                    "modification_count": len(recipe.get("modifications") or []),
                    "minimum_distance_to_accepted": recipe.get(
                        "minimum_distance_to_accepted"
                    ),
                },
            }
        )

    recipe_set_id = face_document.get("recipe_set_id") or "unknown_face_recipe_set"
    batch = {
        "schema_version": 1,
        "library_id": "{}_quality".format(recipe_set_id),
        "generated_at": now(),
        "status": "quality-review-only",
        "preview_lightroom": body_library.get("preview_lightroom"),
        "source_body_library": {
            "path": body_library_path,
            "library_id": body_library.get("library_id"),
            "sha256": sha256_file(body_library_path),
        },
        "source_face_recipes": {
            "path": face_recipes_path,
            "recipe_set_id": recipe_set_id,
            "sha256": sha256_file(face_recipes_path),
        },
        "selection": {
            "method": "all_v2_pilot_faces_on_sex_matched_average_body",
            "count_per_sex": 16,
            "bodyfit_by_sex": dict(
                (sex, item["preset_id"]) for sex, item in average_bodies.items()
            ),
        },
        "character_count": len(characters),
        "presets": characters,
    }
    write_json(batch, output_path)
    return {
        "success": True,
        "output": output_path,
        "character_count": len(characters),
        "male_count": sum(item["sex"] == "male" for item in characters),
        "female_count": sum(item["sex"] == "female" for item in characters),
        "bodyfit_by_sex": batch["selection"]["bodyfit_by_sex"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-library", default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--face-recipes", default=DEFAULT_FACE_RECIPES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build_batch(args.body_library, args.face_recipes, args.output),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
