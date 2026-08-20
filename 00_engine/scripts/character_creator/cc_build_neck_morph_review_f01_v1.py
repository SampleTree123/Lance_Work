"""Build the F01 neck-morph direction review libraries."""

import argparse
import copy
import json
import os
from datetime import datetime, timezone


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR,
    "cc_neck_morph_review_f01_v1_config.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_neck_morph_review_f01_v1.json",
)
DEFAULT_SMOKE_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_neck_morph_review_f01_v1_smoke.json",
)
DEFAULT_HEADSHOT_SMOKE_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_neck_morph_review_f01_v1_headshot_smoke.json",
)
DEFAULT_HEADSHOT_FOCUS_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_neck_morph_review_f01_v1_headshot_focus.json",
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


def build_library(config, smoke=False, smoke_morph_index=0, focus=False):
    if smoke and focus:
        raise ValueError("A neck review library cannot be smoke and focus mode")
    source_path = os.path.realpath(os.path.abspath(config["source_library"]))
    source = read_json(source_path)
    source_preset_id = config["source_preset_id"]
    matches = [
        preset
        for preset in source.get("presets", [])
        if preset.get("preset_id") == source_preset_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one source preset {}, got {}.".format(
                source_preset_id,
                len(matches),
            )
        )

    library = copy.deepcopy(source)
    library["diagnostic_mode"] = "neck_morph_review_matrix"
    library["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    if smoke:
        library_id = "adult_f01_neck_morph_direction_smoke_v1"
    elif focus:
        library_id = "adult_f01_neck_height_focus_v1"
    else:
        library_id = "adult_f01_neck_morph_direction_v1"
    library["library_id"] = library_id
    library["matrix"] = {
        "bodyfit_id": "F01_Lean",
        "purpose": "neck_morph_direction_and_visual_shortening_review",
        "focus": bool(focus),
        "smoke": bool(smoke),
    }
    library["status"] = "diagnostic-ready"

    preset = copy.deepcopy(matches[0])
    preset.pop("head_scale_review", None)
    if smoke:
        character_id = "NECK_F01_DIRECTION_SMOKE"
    elif focus:
        character_id = "NECK_F01_HEIGHT_FOCUS"
    else:
        character_id = "NECK_F01_DIRECTION"
    preset["character_id"] = character_id
    preset["preset_id"] = preset["character_id"]
    preset["review_status"] = "pending-human-neck-morph-review"
    morphs = copy.deepcopy(config["morphs"])
    if smoke:
        morphs = [morphs[smoke_morph_index]]
        morphs[0]["values"] = morphs[0].pop("smoke_values", [0.0, 1.0])
        morphs[0].pop("focus_values", None)
    elif focus:
        morphs = [morphs[1]]
        morphs[0]["values"] = morphs[0].pop("focus_values")
        morphs[0].pop("smoke_values", None)
    else:
        for item in morphs:
            item.pop("smoke_values", None)
            item.pop("focus_values", None)
    preset["neck_morph_review"] = {
        "head_scale": copy.deepcopy(config["head_scale"]),
        "morphs": morphs,
        "views": copy.deepcopy(config["views"]),
    }
    preset["skip_post_diagnostic_face_validation"] = True
    library["presets"] = [preset]
    return library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--smoke-output", default=DEFAULT_SMOKE_OUTPUT)
    parser.add_argument(
        "--headshot-smoke-output",
        default=DEFAULT_HEADSHOT_SMOKE_OUTPUT,
    )
    parser.add_argument(
        "--headshot-focus-output",
        default=DEFAULT_HEADSHOT_FOCUS_OUTPUT,
    )
    args = parser.parse_args()
    config = read_json(os.path.realpath(os.path.abspath(args.config)))
    write_json(
        build_library(config, smoke=False),
        os.path.realpath(os.path.abspath(args.output)),
    )
    write_json(
        build_library(config, smoke=True),
        os.path.realpath(os.path.abspath(args.smoke_output)),
    )
    write_json(
        build_library(config, smoke=True, smoke_morph_index=1),
        os.path.realpath(os.path.abspath(args.headshot_smoke_output)),
    )
    write_json(
        build_library(config, focus=True),
        os.path.realpath(os.path.abspath(args.headshot_focus_output)),
    )
    print("Built F01 neck review libraries.")


if __name__ == "__main__":
    main()
