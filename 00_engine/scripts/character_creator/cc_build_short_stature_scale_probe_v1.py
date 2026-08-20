"""Build a reversible Character Scale probe from the M02 adult BodyFit."""

import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_PATH = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v1.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "cc_short_stature_scale_probe_v1.json")
SOURCE_PRESET_ID = "M02_Average"
SCALE_MORPH_ID = "2018-09-14-22-07-28_character scale"
SCALE_VALUES = (0.0, 0.25, 0.50, 0.75, 1.0)


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
            "character_id": "SHORT_SCALE_PROBE_M02",
            "head_scale_review": {
                "face_shape_role": "short_adult_scale_probe",
                "morph_id": SCALE_MORPH_ID,
                "review_groups": ["short_stature", "adult_proportions"],
                "values": list(SCALE_VALUES),
            },
            "preset_id": "SHORT_SCALE_PROBE_M02",
            "review_status": "short-stature-scale-probe",
            "skip_post_diagnostic_face_validation": True,
            "source_bodyfit_id": SOURCE_PRESET_ID,
        }
    )
    return {
        "schema_version": 1,
        "library_id": "cc_short_stature_scale_probe_v1",
        "diagnostic_mode": "head_bodyfit_scale_review_matrix",
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
                "output": OUTPUT_PATH,
                "preset_count": len(document["presets"]),
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
