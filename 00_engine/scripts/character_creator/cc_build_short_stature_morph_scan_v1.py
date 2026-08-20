"""Build a reversible scan of stature-related Morphs on M02 Average."""

import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_PATH = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v1.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "cc_short_stature_morph_scan_v1.json")
SOURCE_PRESET_ID = "M02_Average"
HEAD_SCALE_MORPH_ID = "cc embed morphs/embed_full_head9"
VALUES = (0.20, 0.25, 0.30, 0.35, 0.40)
SELECTED_VALUE = 0.30
SELECTED_PROJECT_PATH = os.path.join(
    r"D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project",
    "M05_Short_Average_candidate.ccProject",
)
MORPHS = (
    ("hd_gibro_ratio", "2025-08-15-16-46-49_gibro_body ratio_body"),
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


def build(source):
    matches = [
        item
        for item in source["presets"]
        if item.get("preset_id") == SOURCE_PRESET_ID
    ]
    if len(matches) != 1:
        raise RuntimeError("Expected one {} preset".format(SOURCE_PRESET_ID))

    preset = copy.deepcopy(matches[0])
    preset.update(
        {
            "character_id": "SHORT_MORPH_SCAN_M02",
            "neck_morph_review": {
                "head_scale": {
                    "morph_id": HEAD_SCALE_MORPH_ID,
                    "target": 0.0,
                },
                "morphs": [
                    {
                        "morph_id": morph_id,
                        "review_id": review_id,
                        "values": list(VALUES),
                    }
                    for review_id, morph_id in MORPHS
                ],
                "save_selected_candidate": {
                    "project_path": SELECTED_PROJECT_PATH,
                    "review_id": "hd_gibro_ratio",
                    "value": SELECTED_VALUE,
                },
                "views": [
                    {"view_id": "yaw_000", "yaw_degrees": 0.0},
                ],
            },
            "preset_id": "SHORT_MORPH_SCAN_M02",
            "review_status": "short-stature-morph-scan",
            "skip_post_diagnostic_face_validation": True,
            "source_bodyfit_id": SOURCE_PRESET_ID,
        }
    )
    return {
        "schema_version": 1,
        "library_id": "cc_short_stature_morph_scan_v1",
        "diagnostic_mode": "neck_morph_review_matrix",
        "body_application_mode": source["body_application_mode"],
        "expected_eyeball_move_weight": source.get(
            "expected_eyeball_move_weight"
        ),
        "generated_at": now(),
        "inter_case_delay_seconds": 0.0,
        "presets": [preset],
        "preview_lightroom": source.get("preview_lightroom"),
        "source_library_id": source.get("library_id"),
        "status": "diagnostic-ready",
    }


def main():
    document = build(read_json(SOURCE_PATH))
    write_json(document, OUTPUT_PATH)
    print(
        json.dumps(
            {
                "morph_count": len(MORPHS),
                "output": OUTPUT_PATH,
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
