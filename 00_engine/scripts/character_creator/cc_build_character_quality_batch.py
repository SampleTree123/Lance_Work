"""Build a deterministic 16-character BodyFit/FaceRecipe quality batch."""

import argparse
import datetime
import hashlib
import json
import math
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BODY_LIBRARY = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v1.json")
DEFAULT_FACE_RECIPES = (
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_face_recipes"
    r"\adult_face_recipes_v1_200_seed20260721_20260721_172052_991280"
    r"\face_recipes.json"
)
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_character_quality_batch_v1.json")
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
BASE_FACE_CAMERA = (
    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera"
    r"\Headshot Ref\Ref Cam Base L.ccCam"
)


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


def vector_map(recipe):
    return dict(
        (item["id"], float(item["weight"]))
        for item in recipe["target_face_morphs"]
    )


def normalized_ranges(recipes):
    maps = [vector_map(item) for item in recipes]
    morph_ids = sorted(set().union(*(set(item) for item in maps)))
    ranges = {}
    for morph_id in morph_ids:
        values = [item.get(morph_id, 0.0) for item in maps]
        span = max(values) - min(values)
        if span > 1e-9:
            ranges[morph_id] = span
    if not ranges:
        raise BatchBuildError("Face recipe set has no variable dimensions")
    return ranges


def distance(left, right, ranges):
    left_map = vector_map(left)
    right_map = vector_map(right)
    squared = sum(
        ((left_map.get(morph_id, 0.0) - right_map.get(morph_id, 0.0)) / span) ** 2
        for morph_id, span in ranges.items()
    )
    return math.sqrt(squared / float(len(ranges)))


def centroid_distance(recipe, recipes, ranges):
    maps = [vector_map(item) for item in recipes]
    target = vector_map(recipe)
    squared = 0.0
    for morph_id, span in ranges.items():
        center = sum(item.get(morph_id, 0.0) for item in maps) / float(len(maps))
        squared += ((target.get(morph_id, 0.0) - center) / span) ** 2
    return math.sqrt(squared / float(len(ranges)))


def select_coverage_sample(recipes, count):
    if len(recipes) < count:
        raise BatchBuildError("Not enough recipes for coverage sample")
    ranges = normalized_ranges(recipes)
    ordered = sorted(recipes, key=lambda item: item["recipe_id"])
    first = max(
        ordered,
        key=lambda item: (centroid_distance(item, ordered, ranges), item["recipe_id"]),
    )
    selected = [first]
    remaining = [item for item in ordered if item is not first]
    selection_details = [
        {
            "recipe_id": first["recipe_id"],
            "selection_step": 1,
            "distance_to_centroid": centroid_distance(first, ordered, ranges),
            "minimum_distance_to_selected": None,
        }
    ]
    while len(selected) < count:
        scored = []
        for candidate in remaining:
            minimum = min(distance(candidate, item, ranges) for item in selected)
            scored.append((minimum, candidate["recipe_id"], candidate))
        minimum, unused_id, chosen = max(scored, key=lambda item: (item[0], item[1]))
        selected.append(chosen)
        remaining.remove(chosen)
        selection_details.append(
            {
                "recipe_id": chosen["recipe_id"],
                "selection_step": len(selected),
                "distance_to_centroid": centroid_distance(chosen, ordered, ranges),
                "minimum_distance_to_selected": minimum,
            }
        )
    return selected, selection_details, len(ranges)


def build_batch(body_library_path, face_recipes_path, output_path, face_camera_mode):
    body_library_path = os.path.realpath(os.path.abspath(body_library_path))
    face_recipes_path = os.path.realpath(os.path.abspath(face_recipes_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    for path, label in (
        (body_library_path, "BodyFit library"),
        (face_recipes_path, "Face recipe set"),
    ):
        if not os.path.isfile(path):
            raise BatchBuildError("{} is missing: {}".format(label, path))
    body_library = read_json(body_library_path)
    face_document = read_json(face_recipes_path)
    bodies = body_library.get("presets") or []
    recipes = face_document.get("recipes") or []

    selected_by_sex = {}
    selection_details = {}
    dimension_counts = {}
    for sex in ("male", "female"):
        sex_bodies = [item for item in bodies if item.get("sex") == sex]
        sex_recipes = [item for item in recipes if item.get("sex") == sex]
        if len(sex_bodies) != 4:
            raise BatchBuildError("Expected four {} BodyFits".format(sex))
        selected, details, dimensions = select_coverage_sample(sex_recipes, 8)
        selected_by_sex[sex] = selected
        selection_details[sex] = details
        dimension_counts[sex] = dimensions

    characters = []
    for sex in ("male", "female"):
        sex_bodies = [item for item in bodies if item["sex"] == sex]
        selected = selected_by_sex[sex]
        for index, body in enumerate(sex_bodies):
            for variant, face in zip(("A", "B"), (selected[index], selected[index + 4])):
                character_id = "QC_{}_{}".format(body["preset_id"], variant)
                characters.append(
                    {
                        "preset_id": character_id,
                        "character_id": character_id,
                        "bodyfit_id": body["preset_id"],
                        "face_recipe_id": face["recipe_id"],
                        "sex": sex,
                        "body_class": body["body_class"],
                        "review_status": "quality-candidate",
                        "base_avatar": body["base_avatar"],
                        "source_project": body["source_project"],
                        "target_body_morphs": body["target_body_morphs"],
                        "target_junction_morphs": body["target_junction_morphs"],
                        "body_and_junction_fingerprint": body[
                            "body_and_junction_fingerprint"
                        ],
                        "target_face_morphs": face["target_face_morphs"],
                        "target_face_fingerprint": face["target_face_fingerprint"],
                        "face_parents": face.get("parents"),
                        "face_camera": (
                            BASE_FACE_CAMERA
                            if face_camera_mode == "base"
                            else FACE_CAMERAS[sex]
                        ),
                    }
                )

    batch = {
        "schema_version": 1,
        "library_id": "adult_character_quality_batch_v1",
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
            "recipe_set_id": face_document.get("recipe_set_id"),
            "sha256": sha256_file(face_recipes_path),
        },
        "selection": {
            "method": "normalized_morph_space_greedy_farthest_point",
            "sample_count_per_sex": 8,
            "face_camera_mode": face_camera_mode,
            "dimension_counts": dimension_counts,
            "details": selection_details,
        },
        "character_count": len(characters),
        "presets": characters,
    }
    if len(characters) != 16:
        raise BatchBuildError("Quality batch must contain exactly 16 characters")
    write_json(batch, output_path)
    return {
        "success": True,
        "output": output_path,
        "character_count": len(characters),
        "male_faces": [item["recipe_id"] for item in selected_by_sex["male"]],
        "female_faces": [item["recipe_id"] for item in selected_by_sex["female"]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-library", default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--face-recipes", default=DEFAULT_FACE_RECIPES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--face-camera-mode", choices=("sex", "base"), default="sex"
    )
    args = parser.parse_args()
    result = build_batch(
        args.body_library,
        args.face_recipes,
        args.output,
        args.face_camera_mode,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
