"""Build the combined F05 final review or save library."""

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
DEFAULT_REVIEW_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_short_female_final_review_v1.json",
)
DEFAULT_SAVE_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_short_female_final_save_v1.json",
)
DEFAULT_PROJECT_OUTPUT = (
    "D:\\CharacterCreator_sucai\\Reallusion Custom\\Project\\CC Project"
    "\\F05_Short_Average.ccProject"
)
BODYFIT_ID = "F05_Short_Average"
HEAD_SCALE_ID = "cc embed morphs/embed_full_head9"
PLUMP_SHAPE_ID = "2025-08-09-16-25-17_female black_body details_body"
SHOULDER_HEIGHT_B_ID = "2018-09-25-18-34-43_shoulder top peak"
DEFAULT_SELECTED_SHOULDER_VALUE = 0.25


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


def build(
    source,
    decisions,
    save=False,
    project_output=None,
    selected_shoulder_value=DEFAULT_SELECTED_SHOULDER_VALUE,
):
    preset = copy.deepcopy(
        select_one(source.get("presets") or [], "preset_id", BODYFIT_ID)
    )
    decision = select_one(
        decisions.get("selections") or [],
        "bodyfit_id",
        BODYFIT_ID,
    )
    selected_head_scale = float(decision.get("head_scale_weight"))
    if abs(selected_head_scale - (-0.1)) > 1e-7:
        raise RuntimeError("F05 Head Scale decision must be -0.1")
    selected_shoulder_value = float(selected_shoulder_value)
    if selected_shoulder_value not in (0.25, 0.5, 0.75):
        raise RuntimeError(
            "F05 Shoulder B selection must be 0.25, 0.5, or 0.75"
        )

    review = {
        "head_scale": {
            "morph_id": HEAD_SCALE_ID,
            "target": 0.0 if save else selected_head_scale,
        },
        "fixed_morphs": [
            {
                "morph_id": PLUMP_SHAPE_ID,
                "target": 0.3,
            }
        ],
        "morphs": [
            {
                "morph_id": SHOULDER_HEIGHT_B_ID,
                "review_id": "selected_shoulder_top_height_b",
                "values": (
                    [selected_shoulder_value]
                    if save
                    else [0.25, 0.5, 0.75]
                ),
            }
        ],
        "views": [
            {"view_id": "yaw_000", "yaw_degrees": 0.0},
            {"view_id": "yaw_045", "yaw_degrees": 45.0},
            {"view_id": "yaw_090", "yaw_degrees": 90.0},
        ],
    }
    if save:
        if not isinstance(project_output, str) or not project_output:
            raise RuntimeError("Final F05 project output is missing")
        review["save_selected_candidate"] = {
            "project_path": os.path.realpath(os.path.abspath(project_output)),
            "review_id": "selected_shoulder_top_height_b",
            "value": selected_shoulder_value,
        }

    preset.update(
        {
            "character_id": (
                "SHORT_FEMALE_FINAL_SAVE"
                if save
                else "SHORT_FEMALE_FINAL_REVIEW"
            ),
            "preset_id": (
                "SHORT_FEMALE_FINAL_SAVE"
                if save
                else "SHORT_FEMALE_FINAL_REVIEW"
            ),
            "review_status": (
                "selected-body-refinement-save"
                if save
                else "pending-combined-refinement-review"
            ),
            "skip_post_diagnostic_face_validation": True,
            "neck_morph_review": review,
        }
    )
    return {
        "schema_version": 1,
        "library_id": (
            "cc_short_female_final_save_v1"
            if save
            else "cc_short_female_final_review_v1"
        ),
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
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--project-output", default=DEFAULT_PROJECT_OUTPUT)
    parser.add_argument(
        "--shoulder-value",
        type=float,
        choices=(0.25, 0.5, 0.75),
        default=DEFAULT_SELECTED_SHOULDER_VALUE,
    )
    parser.add_argument("--output")
    args = parser.parse_args()
    output = args.output or (
        DEFAULT_SAVE_OUTPUT if args.save else DEFAULT_REVIEW_OUTPUT
    )
    document = build(
        read_json(args.source),
        read_json(args.decisions),
        save=args.save,
        project_output=args.project_output,
        selected_shoulder_value=args.shoulder_value,
    )
    output = os.path.realpath(os.path.abspath(output))
    write_json(document, output)
    print(
        json.dumps(
            {
                "mode": "save" if args.save else "review",
                "output": output,
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
