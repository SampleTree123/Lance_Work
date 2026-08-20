"""Build the F05 body-shape refinement review library."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCE = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_candidates_v1.json",
)
DEFAULT_DECISIONS = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_decisions_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_short_female_refinement_review_v1.json",
)
BODYFIT_ID = "F05_Short_Average"
HEAD_SCALE_MORPH_ID = "cc embed morphs/embed_full_head9"
SHAPE_REVIEWS = (
    (
        "plump_shape_reduction",
        "2025-08-09-16-25-17_female black_body details_body",
        [0.51, 0.4, 0.3, 0.2, 0.1, 0.0],
    ),
    (
        "fit_shape_increase",
        "2025-08-14-17-22-13_female fit_body shape",
        [0.49, 0.6, 0.7, 0.8, 0.9, 1.0],
    ),
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


def build(source, decisions):
    preset = copy.deepcopy(
        select_one(source.get("presets") or [], "preset_id", BODYFIT_ID)
    )
    decision = select_one(
        decisions.get("selections") or [],
        "bodyfit_id",
        BODYFIT_ID,
    )
    head_scale = float(decision.get("head_scale_weight"))
    if abs(head_scale - (-0.1)) > 1e-7:
        raise RuntimeError("F05 Head Scale decision must be -0.1")

    preset.update(
        {
            "character_id": "SHORT_FEMALE_BREAST_REVIEW",
            "preset_id": "SHORT_FEMALE_BREAST_REVIEW",
            "review_status": "pending-body-shape-refinement-review",
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
                        "values": values,
                    }
                    for review_id, morph_id, values in SHAPE_REVIEWS
                ],
                "views": [
                    {"view_id": "yaw_000", "yaw_degrees": 0.0},
                    {"view_id": "yaw_045", "yaw_degrees": 45.0},
                    {"view_id": "yaw_090", "yaw_degrees": 90.0},
                ],
            },
        }
    )
    return {
        "schema_version": 1,
        "library_id": "cc_short_female_refinement_review_v1",
        "diagnostic_mode": "targeted_morph_visual_matrix",
        "body_application_mode": "source_project",
        "expected_eyeball_move_weight": source.get(
            "expected_eyeball_move_weight",
            0.0,
        ),
        "generated_at": (
            datetime.datetime.now()
            .astimezone()
            .replace(microsecond=0)
            .isoformat()
        ),
        "inter_case_delay_seconds": 0.0,
        "presets": [preset],
        "preview_capture_mode": "render_image",
        "preview_lightroom": source.get("preview_lightroom"),
        "source_library_id": source.get("library_id"),
        "status": "diagnostic-ready",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build(read_json(args.source), read_json(args.decisions))
    write_json(document, os.path.realpath(os.path.abspath(args.output)))
    print(
        json.dumps(
            {
                "head_scale": document["presets"][0][
                    "neck_morph_review"
                ]["head_scale"]["target"],
                "output": os.path.realpath(os.path.abspath(args.output)),
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
