"""Build the CC5 face-shape and BodyFit Head Scale review matrix."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_review_matrix_v1_config.json",
)


class MatrixBuildError(RuntimeError):
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
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def resolve_path(value, base_dir=SCRIPT_DIR):
    if not isinstance(value, str) or not value:
        raise MatrixBuildError("Configured path is missing")
    if not os.path.isabs(value):
        value = os.path.join(base_dir, value)
    return os.path.realpath(os.path.abspath(value))


def indexed(items, key, label):
    result = {}
    for item in items:
        item_id = item.get(key)
        if not isinstance(item_id, str) or not item_id:
            raise MatrixBuildError("{} contains an invalid ID".format(label))
        if item_id in result:
            raise MatrixBuildError(
                "{} contains duplicate ID {}".format(label, item_id)
            )
        result[item_id] = item
    return result


def minimal_body_fields(body):
    return {
        "base_avatar": copy.deepcopy(body["base_avatar"]),
        "body_and_junction_fingerprint": body[
            "body_and_junction_fingerprint"
        ],
        "body_class": body["body_class"],
        "bodyfit_id": body["preset_id"],
        "sex": body["sex"],
        "source_project": copy.deepcopy(body["source_project"]),
        "target_body_morphs": copy.deepcopy(body["target_body_morphs"]),
        "target_junction_morphs": copy.deepcopy(
            body["target_junction_morphs"]
        ),
    }


def minimal_face_fields(face):
    required = (
        "face_camera",
        "face_generation",
        "face_recipe_id",
        "local_face_morphs",
        "local_morph_fingerprint",
        "source_facial_profile",
        "source_head_preset",
    )
    missing = [key for key in required if key not in face]
    if missing:
        raise MatrixBuildError(
            "Face preset {} is missing {}".format(
                face.get("preset_id"),
                missing,
            )
        )
    return dict((key, copy.deepcopy(face[key])) for key in required)


def build_combination(
    preset_id,
    body,
    face,
    face_shape_role,
    review_groups,
    morph_id,
    values,
):
    if body["sex"] != face["sex"]:
        raise MatrixBuildError(
            "Sex mismatch for {} and {}".format(
                body["preset_id"],
                face["preset_id"],
            )
        )
    result = minimal_body_fields(body)
    result.update(minimal_face_fields(face))
    result.update(
        {
            "character_id": preset_id,
            "face_shape_role": face_shape_role,
            "head_scale_review": {
                "face_shape_role": face_shape_role,
                "morph_id": morph_id,
                "review_groups": sorted(set(review_groups)),
                "values": list(values),
            },
            "preset_id": preset_id,
            "reference_face_preset_id": face["preset_id"],
            "review_groups": sorted(set(review_groups)),
            "review_status": "pending-human-head-scale-selection",
        }
    )
    return result


def build_document(config, body_library, face_library, pipeline_library):
    if int(config.get("schema_version", -1)) != 1:
        raise MatrixBuildError("Unsupported matrix config schema")
    bodies = indexed(
        body_library.get("presets") or [],
        "preset_id",
        "BodyFit library",
    )
    if len(bodies) != 8:
        raise MatrixBuildError("Expected exactly eight BodyFit presets")
    faces = indexed(
        face_library.get("presets") or [],
        "preset_id",
        "face baseline library",
    )
    values = [float(value) for value in config.get("head_scale_values") or []]
    if not values or len(values) != len(set(values)):
        raise MatrixBuildError(
            "head_scale_values must be non-empty and unique"
        )
    morph_id = config.get("head_scale_morph_id")
    if not isinstance(morph_id, str) or not morph_id:
        raise MatrixBuildError("head_scale_morph_id is missing")

    combinations = []
    seen_pairs = {}
    variation = config.get("face_variation") or {}
    variation_body_id = variation.get("bodyfit_id")
    if variation_body_id not in bodies:
        raise MatrixBuildError("Face variation BodyFit is unknown")
    for item in variation.get("faces") or []:
        face_id = item.get("face_preset_id")
        role = item.get("role")
        if face_id not in faces or not isinstance(role, str) or not role:
            raise MatrixBuildError("Face variation entry is invalid")
        pair = (variation_body_id, face_id)
        preset_id = "HBS_FACE_M04_{}".format(role.upper())
        combination = build_combination(
            preset_id,
            bodies[variation_body_id],
            faces[face_id],
            role,
            ["face_variation"],
            morph_id,
            values,
        )
        combinations.append(combination)
        seen_pairs[pair] = combination

    reference_faces = config.get("bodyfit_reference_faces") or {}
    for body_id in sorted(bodies):
        body = bodies[body_id]
        face_id = reference_faces.get(body["sex"])
        if face_id not in faces:
            raise MatrixBuildError(
                "Reference face is missing for {}".format(body["sex"])
            )
        pair = (body_id, face_id)
        if pair in seen_pairs:
            combination = seen_pairs[pair]
            combination["review_groups"] = sorted(
                set(combination["review_groups"]) | {"bodyfit_matrix"}
            )
            combination["head_scale_review"]["review_groups"] = list(
                combination["review_groups"]
            )
            continue
        body_token = body_id.split("_")[0].upper()
        combination = build_combination(
            "HBS_BODY_{}".format(body_token),
            body,
            faces[face_id],
            "sex_reference",
            ["bodyfit_matrix"],
            morph_id,
            values,
        )
        combinations.append(combination)
        seen_pairs[pair] = combination

    face_resources = copy.deepcopy(
        pipeline_library.get("face_resources") or {}
    )
    if not face_resources:
        raise MatrixBuildError("Pipeline library has no face_resources")
    document = {
        "schema_version": 1,
        "library_id": "head_bodyfit_scale_review_matrix_v1",
        "diagnostic_mode": "head_bodyfit_scale_review_matrix",
        "body_application_mode": "source_project",
        "expected_eyeball_move_weight": 0.0,
        "face_resources": face_resources,
        "generated_at": now(),
        "inter_case_delay_seconds": float(
            config.get("inter_case_delay_seconds", 5.0)
        ),
        "matrix": {
            "bodyfit_count": 8,
            "combination_count": len(combinations),
            "face_variation_bodyfit_id": variation_body_id,
            "head_scale_morph_id": morph_id,
            "head_scale_values": values,
            "purpose": "human_head_to_body_proportion_review",
        },
        "pipeline": pipeline_library.get("pipeline"),
        "presets": combinations,
        "preview_lightroom": pipeline_library.get("preview_lightroom"),
        "status": "pending-human-review",
    }
    return document


def main():
    parser = argparse.ArgumentParser(
        description="Build the CC5 Head Scale review matrix."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output")
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = read_json(config_path)
    body_path = resolve_path(config["body_library"])
    face_path = resolve_path(config["face_baseline_library"])
    pipeline_path = resolve_path(config["pipeline_library"])
    output_path = resolve_path(args.output or config["output"])
    document = build_document(
        config,
        read_json(body_path),
        read_json(face_path),
        read_json(pipeline_path),
    )
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "combination_count": len(document["presets"]),
                "output": output_path,
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
