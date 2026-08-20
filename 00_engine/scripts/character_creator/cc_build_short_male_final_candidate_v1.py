"""Build the accepted M05 short-adult BodyFit save library."""

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
    "cc_short_male_final_save_v1.json",
)
DEFAULT_PROJECT_OUTPUT = (
    "D:\\CharacterCreator_sucai\\Reallusion Custom\\Project\\CC Project"
    "\\M05_Short_Average.ccProject"
)
BODYFIT_ID = "M05_Short_Average"
HEAD_SCALE_ID = "cc embed morphs/embed_full_head9"
GIBRO_RATIO_ID = "2025-08-15-16-46-49_gibro_body ratio_body"
GIBRO_RATIO_WEIGHT = 0.3


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


def build(source, decisions, project_output):
    preset = copy.deepcopy(
        select_one(source.get("presets") or [], "preset_id", BODYFIT_ID)
    )
    decision = select_one(
        decisions.get("selections") or [],
        "bodyfit_id",
        BODYFIT_ID,
    )
    selected_head_scale = float(decision.get("head_scale_weight"))
    if abs(selected_head_scale) > 1e-7:
        raise RuntimeError("M05 Head Scale decision must be 0")
    if not isinstance(project_output, str) or not project_output:
        raise RuntimeError("Final M05 project output is missing")

    review = {
        "head_scale": {
            "morph_id": HEAD_SCALE_ID,
            "target": 0.0,
        },
        "morphs": [
            {
                "morph_id": GIBRO_RATIO_ID,
                "review_id": "selected_hd_gibro_body_ratio",
                "values": [GIBRO_RATIO_WEIGHT],
            }
        ],
        "save_selected_candidate": {
            "project_path": os.path.realpath(
                os.path.abspath(project_output)
            ),
            "review_id": "selected_hd_gibro_body_ratio",
            "value": GIBRO_RATIO_WEIGHT,
        },
        "views": [
            {"view_id": "yaw_000", "yaw_degrees": 0.0},
            {"view_id": "yaw_045", "yaw_degrees": 45.0},
            {"view_id": "yaw_090", "yaw_degrees": 90.0},
        ],
    }
    preset.update(
        {
            "character_id": "SHORT_MALE_FINAL_SAVE",
            "preset_id": "SHORT_MALE_FINAL_SAVE",
            "review_status": "selected-bodyfit-save",
            "skip_post_diagnostic_face_validation": True,
            "neck_morph_review": review,
        }
    )
    return {
        "schema_version": 1,
        "library_id": "cc_short_male_final_save_v1",
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
        "status": "save-ready",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--project-output", default=DEFAULT_PROJECT_OUTPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build(
        read_json(args.source),
        read_json(args.decisions),
        args.project_output,
    )
    output = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output)
    print(
        json.dumps(
            {
                "output": output,
                "project_output": os.path.realpath(
                    os.path.abspath(args.project_output)
                ),
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
