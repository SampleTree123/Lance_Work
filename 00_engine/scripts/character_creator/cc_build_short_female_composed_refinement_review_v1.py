"""Build the composed F05 neck refinement review library."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FACE_SOURCE = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_review_matrix_v1.json",
)
DEFAULT_BODY_SOURCE = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_candidates_v1.json",
)
DEFAULT_DECISIONS = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_decisions_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_short_female_composed_refinement_review_v1.json",
)
BODYFIT_ID = "F05_Short_Average"
FACE_SOURCE_PRESET_ID = "HBS_BODY_F02"
HEAD_SCALE_MORPH_ID = "cc embed morphs/embed_full_head9"
REVIEW_MORPHS = (
    ("neck_height", "2019-08-30-20-14-55_neck height"),
)
BODY_FIELDS = (
    "base_avatar",
    "body_and_junction_fingerprint",
    "body_class",
    "body_morph_count",
    "body_only_fingerprint",
    "junction_fingerprint",
    "junction_morph_count",
    "source_project",
    "target_body_morphs",
    "target_junction_morphs",
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
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def select_one(items, field, value):
    matches = [item for item in items if item.get(field) == value]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one {}={}, got {}".format(field, value, len(matches))
        )
    return matches[0]


def build(face_source, body_source, decisions):
    preset = copy.deepcopy(
        select_one(
            face_source.get("presets") or [],
            "preset_id",
            FACE_SOURCE_PRESET_ID,
        )
    )
    body = select_one(
        body_source.get("presets") or [],
        "preset_id",
        BODYFIT_ID,
    )
    decision = select_one(
        decisions.get("selections") or [],
        "bodyfit_id",
        BODYFIT_ID,
    )
    head_scale = float(decision.get("head_scale_weight"))
    if abs(head_scale - (-0.1)) > 1e-7:
        raise RuntimeError("F05 Head Scale decision must be -0.1")

    preset.pop("head_scale_review", None)
    preset.pop("bodyfit_proportion_adjustment", None)
    for field in BODY_FIELDS:
        if field in body:
            preset[field] = copy.deepcopy(body[field])
        else:
            preset.pop(field, None)
    preset.update(
        {
            "bodyfit_id": BODYFIT_ID,
            "character_id": "SHORT_FEMALE_COMPOSED_REFINEMENT",
            "preset_id": "SHORT_FEMALE_COMPOSED_REFINEMENT",
            "review_status": "pending-composed-neck-review",
            "skip_post_diagnostic_face_validation": True,
            "neck_morph_review": {
                "head_scale": {
                    "morph_id": HEAD_SCALE_MORPH_ID,
                    "target": head_scale,
                },
                "morphs": [
                    {
                        "morph_id": morph_id,
                        "review_id": review_id,
                        "values": [0.0, -0.1, -0.2, -0.3, -0.4],
                    }
                    for review_id, morph_id in REVIEW_MORPHS
                ],
                "views": [
                    {"view_id": "yaw_000", "yaw_degrees": 0.0},
                    {"view_id": "yaw_045", "yaw_degrees": 45.0},
                    {"view_id": "yaw_090", "yaw_degrees": 90.0},
                ],
            },
        }
    )

    library = copy.deepcopy(face_source)
    library.update(
        {
            "diagnostic_mode": "neck_morph_review_matrix",
            "generated_at": (
                datetime.datetime.now()
                .astimezone()
                .replace(microsecond=0)
                .isoformat()
            ),
            "library_id": "cc_short_female_composed_refinement_review_v1",
            "matrix": {
                "bodyfit_id": BODYFIT_ID,
                "purpose": "composed_neck_refinement_review",
            },
            "presets": [preset],
            "preview_capture_mode": "render_image",
            "status": "diagnostic-ready",
        }
    )
    return library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--face-source", default=DEFAULT_FACE_SOURCE)
    parser.add_argument("--body-source", default=DEFAULT_BODY_SOURCE)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build(
        read_json(args.face_source),
        read_json(args.body_source),
        read_json(args.decisions),
    )
    output = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output)
    print(
        json.dumps(
            {
                "output": output,
                "review_morph_count": len(REVIEW_MORPHS),
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
