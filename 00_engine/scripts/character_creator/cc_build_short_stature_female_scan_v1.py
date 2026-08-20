"""Build reversible female Body Ratio scans for a short-adult BodyFit."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_PATH = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v1.json")
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_short_stature_female_scan_v1.json",
)
SOURCE_PRESET_ID = "F02_Average"
HEAD_SCALE_MORPH_ID = "cc embed morphs/embed_full_head9"
MACRO_VALUES = (0.0, 0.5, 1.0)
FINE_VALUES = (0.80, 0.85, 0.90, 0.95, 1.00)
FEMALE_RATIO_MORPHS = (
    ("cc4_alika_ratio", "2025-08-25-11-45-49_alika_body ratio_body"),
    ("cc4_camila_ratio", "2025-08-22-11-48-30_camila_body ratio_body"),
    (
        "ha_female_athletic_ratio",
        "2025-08-14-17-20-34_female athletic_body ratio",
    ),
    ("ha_female_fit_ratio", "2025-08-14-17-21-18_female fit_body ratio"),
    (
        "ha_female_heavy_ratio",
        "2025-08-21-16-38-01_ha female heavy_body ratio_body",
    ),
    (
        "ha_female_plump_ratio",
        "2025-08-09-16-30-48_female black_body ratio_body",
    ),
    (
        "ha_female_slim_ratio",
        "2025-08-09-16-57-37_asian female_body ratio_body",
    ),
    ("hd_ariana_ratio", "2025-08-14-15-52-15_ariana_body ratio_body"),
    ("hd_mila_ratio", "2025-08-15-19-53-01_mila"),
    (
        "hd_neutral_f_ratio",
        "2025-08-21-12-30-11_hd neutral f_body ratio_0820_body",
    ),
)


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


def profile(
    mode,
    morph_id=None,
    project_path=None,
    selected_value=None,
    probe=False,
):
    if mode == "macro":
        if probe:
            return FEMALE_RATIO_MORPHS[:1], MACRO_VALUES[:1], None
        return FEMALE_RATIO_MORPHS, MACRO_VALUES, None
    if mode != "fine":
        raise RuntimeError("Unsupported mode: {}".format(mode))
    if not morph_id or not project_path or selected_value is None:
        raise RuntimeError(
            "Fine mode requires morph-id, project-path, and selected-value"
        )
    review_id = "selected_female_ratio"
    return (
        ((review_id, morph_id),),
        FINE_VALUES,
        {
            "project_path": os.path.realpath(os.path.abspath(project_path)),
            "review_id": review_id,
            "value": float(selected_value),
        },
    )


def build(source, mode, morphs, values, selection):
    matches = [
        item
        for item in source["presets"]
        if item.get("preset_id") == SOURCE_PRESET_ID
    ]
    if len(matches) != 1:
        raise RuntimeError("Expected one {} preset".format(SOURCE_PRESET_ID))
    preset_id = "SHORT_FEMALE_{}_SCAN".format(mode.upper())
    review = {
        "head_scale": {
            "morph_id": HEAD_SCALE_MORPH_ID,
            "target": 0.0,
        },
        "morphs": [
            {
                "morph_id": morph_id,
                "review_id": review_id,
                "values": list(values),
            }
            for review_id, morph_id in morphs
        ],
        "views": [{"view_id": "yaw_000", "yaw_degrees": 0.0}],
    }
    if selection is not None:
        review["save_selected_candidate"] = selection
    preset = copy.deepcopy(matches[0])
    preset.update(
        {
            "character_id": preset_id,
            "neck_morph_review": review,
            "preset_id": preset_id,
            "review_status": "short-stature-female-{}-scan".format(mode),
            "skip_post_diagnostic_face_validation": True,
            "source_bodyfit_id": SOURCE_PRESET_ID,
        }
    )
    return {
        "schema_version": 1,
        "library_id": "cc_short_stature_female_{}_scan_v1".format(mode),
        "diagnostic_mode": "targeted_morph_visual_matrix",
        "body_application_mode": source["body_application_mode"],
        "expected_eyeball_move_weight": source.get(
            "expected_eyeball_move_weight"
        ),
        "generated_at": now(),
        "inter_case_delay_seconds": 0.0,
        "presets": [preset],
        "preview_capture_mode": "pixel_stream",
        "preview_lightroom": source.get("preview_lightroom"),
        "source_library_id": source.get("library_id"),
        "status": "diagnostic-ready",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("macro", "fine"), default="macro")
    parser.add_argument("--morph-id")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--project-path")
    parser.add_argument("--selected-value", type=float)
    args = parser.parse_args()
    morphs, values, selection = profile(
        args.mode,
        morph_id=args.morph_id,
        project_path=args.project_path,
        selected_value=args.selected_value,
        probe=args.probe,
    )
    output_path = os.path.realpath(os.path.abspath(args.output))
    document = build(
        read_json(SOURCE_PATH),
        args.mode,
        morphs,
        values,
        selection,
    )
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "morph_count": len(morphs),
                "output": output_path,
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
