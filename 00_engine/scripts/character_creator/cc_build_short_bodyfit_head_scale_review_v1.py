"""Build Head Scale review cases for the two short-adult BodyFits."""

import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BODY_LIBRARY_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_candidates_v1.json",
)
FACE_LIBRARY_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_face_quality_batch_v3_validation.json",
)
PIPELINE_LIBRARY_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_pilot_v1.json",
)
OUTPUT_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_head_scale_review_v1.json",
)
HEAD_SCALE_MORPH_ID = "cc embed morphs/embed_full_head9"
HEAD_SCALE_VALUES = (-0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4)
REFERENCE_FACE_IDS = {
    "female": "V3BASE_F02_Camila",
    "male": "V3BASE_M02_Kevin",
}


class ReviewBuildError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def index(items, key):
    result = {}
    for item in items:
        item_id = item.get(key)
        if not item_id or item_id in result:
            raise ReviewBuildError("Invalid or duplicated {}".format(key))
        result[item_id] = item
    return result


def build_case(body, face):
    if body["sex"] != face["sex"]:
        raise ReviewBuildError("Body and face sex differ")
    face_fields = (
        "face_camera",
        "face_generation",
        "face_recipe_id",
        "local_face_morphs",
        "local_morph_fingerprint",
        "source_facial_profile",
        "source_head_preset",
    )
    missing = [key for key in face_fields if key not in face]
    if missing:
        raise ReviewBuildError(
            "Reference face is missing fields: {}".format(missing)
        )
    preset_id = "SHORT_HEAD_SCALE_{}".format(body["preset_id"].upper())
    result = {
        "base_avatar": copy.deepcopy(body["base_avatar"]),
        "body_and_junction_fingerprint": body[
            "body_and_junction_fingerprint"
        ],
        "body_class": body["body_class"],
        "bodyfit_id": body["preset_id"],
        "character_id": preset_id,
        "head_scale_review": {
            "face_shape_role": "sex_reference",
            "morph_id": HEAD_SCALE_MORPH_ID,
            "review_groups": ["short_bodyfit"],
            "values": list(HEAD_SCALE_VALUES),
        },
        "preset_id": preset_id,
        "reference_face_preset_id": face["preset_id"],
        "review_groups": ["short_bodyfit"],
        "review_status": "pending-human-head-scale-selection",
        "sex": body["sex"],
        "skip_post_diagnostic_face_validation": True,
        "source_project": copy.deepcopy(body["source_project"]),
        "target_body_morphs": copy.deepcopy(body["target_body_morphs"]),
        "target_junction_morphs": copy.deepcopy(
            body["target_junction_morphs"]
        ),
    }
    result.update(
        dict((key, copy.deepcopy(face[key])) for key in face_fields)
    )
    return result


def build():
    body_library = read_json(BODY_LIBRARY_PATH)
    face_library = read_json(FACE_LIBRARY_PATH)
    pipeline_library = read_json(PIPELINE_LIBRARY_PATH)
    bodies = body_library.get("presets") or []
    if len(bodies) != 2:
        raise ReviewBuildError("Expected two short BodyFit candidates")
    faces = index(face_library.get("presets") or [], "preset_id")
    cases = []
    for body in sorted(bodies, key=lambda item: item["preset_id"]):
        face_id = REFERENCE_FACE_IDS[body["sex"]]
        if face_id not in faces:
            raise ReviewBuildError(
                "Reference face is missing: {}".format(face_id)
            )
        cases.append(build_case(body, faces[face_id]))
    return {
        "schema_version": 1,
        "library_id": "short_bodyfit_head_scale_review_v1",
        "diagnostic_mode": "targeted_morph_visual_matrix",
        "body_application_mode": "source_project",
        "expected_eyeball_move_weight": 0.0,
        "face_resources": copy.deepcopy(
            pipeline_library.get("face_resources") or {}
        ),
        "generated_at": now(),
        "inter_case_delay_seconds": 2.0,
        "matrix": {
            "bodyfit_count": 2,
            "combination_count": 2,
            "head_scale_morph_id": HEAD_SCALE_MORPH_ID,
            "head_scale_values": list(HEAD_SCALE_VALUES),
            "purpose": "short_adult_head_to_body_proportion_review",
        },
        "pipeline": pipeline_library.get("pipeline"),
        "presets": cases,
        "preview_capture_mode": "pixel_stream",
        "preview_lightroom": body_library.get("preview_lightroom"),
        "status": "pending-human-review",
    }


def main():
    document = build()
    write_json(document, OUTPUT_PATH)
    print(
        json.dumps(
            {
                "combination_count": len(document["presets"]),
                "output": OUTPUT_PATH,
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
