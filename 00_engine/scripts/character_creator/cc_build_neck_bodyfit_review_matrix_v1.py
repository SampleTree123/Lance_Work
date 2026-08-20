"""Build the M01/M03 fixed-Head-Scale neck-height review matrix."""

import argparse
import copy
import json
import os
from datetime import datetime, timezone


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR,
    "cc_neck_bodyfit_review_matrix_v1_config.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_neck_bodyfit_review_matrix_v1.json",
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


def validate_config(config):
    bodyfits = config.get("bodyfits")
    if not isinstance(bodyfits, list) or not bodyfits:
        raise RuntimeError("bodyfits must be a non-empty list")
    bodyfit_ids = [item.get("bodyfit_id") for item in bodyfits]
    source_ids = [item.get("source_preset_id") for item in bodyfits]
    if any(not isinstance(item, str) or not item for item in bodyfit_ids):
        raise RuntimeError("Every bodyfit_id must be a non-empty string")
    if len(bodyfit_ids) != len(set(bodyfit_ids)):
        raise RuntimeError("bodyfit_id values must be unique")
    if any(not isinstance(item, str) or not item for item in source_ids):
        raise RuntimeError("Every source_preset_id must be a non-empty string")
    if len(source_ids) != len(set(source_ids)):
        raise RuntimeError("source_preset_id values must be unique")
    values = config.get("neck_morph", {}).get("values")
    if not isinstance(values, list) or not values:
        raise RuntimeError("neck_morph.values must be a non-empty list")
    normalized_values = [float(value) for value in values]
    if len(normalized_values) != len(set(normalized_values)):
        raise RuntimeError("neck_morph.values must be unique")
    if not any(abs(value) <= 1e-7 for value in normalized_values):
        raise RuntimeError("neck_morph.values must include a zero baseline")


def build_library(config):
    validate_config(config)
    source_path = os.path.realpath(os.path.abspath(config["source_library"]))
    source = read_json(source_path)
    source_presets = dict(
        (preset.get("preset_id"), preset)
        for preset in source.get("presets", [])
    )
    selected_presets = []
    neck_morph = copy.deepcopy(config["neck_morph"])
    head_scale_morph_id = config["head_scale_morph_id"]
    for bodyfit in config["bodyfits"]:
        source_preset_id = bodyfit["source_preset_id"]
        source_preset = source_presets.get(source_preset_id)
        if source_preset is None:
            raise RuntimeError(
                "Missing source preset: {}".format(source_preset_id)
            )
        if source_preset.get("bodyfit_id") != bodyfit["bodyfit_id"]:
            raise RuntimeError(
                "Source preset bodyfit mismatch for {}".format(
                    source_preset_id
                )
            )
        preset = copy.deepcopy(source_preset)
        preset.pop("head_scale_review", None)
        preset_id = "NECK_{}".format(bodyfit["bodyfit_id"].upper())
        preset["character_id"] = preset_id
        preset["preset_id"] = preset_id
        preset["neck_morph_review"] = {
            "head_scale": {
                "morph_id": head_scale_morph_id,
                "target": float(bodyfit["head_scale_target"]),
            },
            "morphs": [copy.deepcopy(neck_morph)],
            "views": copy.deepcopy(config["views"]),
        }
        preset["review_status"] = "pending-human-neck-height-selection"
        preset["skip_post_diagnostic_face_validation"] = True
        selected_presets.append(preset)

    library = copy.deepcopy(source)
    library["diagnostic_mode"] = "neck_morph_review_matrix"
    library["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    library["library_id"] = "adult_male_neck_bodyfit_review_matrix_v1"
    library["matrix"] = {
        "bodyfit_count": len(selected_presets),
        "bodyfit_ids": [item["bodyfit_id"] for item in config["bodyfits"]],
        "candidate_count_per_bodyfit": len(neck_morph["values"]),
        "head_scale_morph_id": head_scale_morph_id,
        "neck_morph_id": neck_morph["morph_id"],
        "purpose": "fixed_bodyfit_neck_height_human_review",
    }
    library["presets"] = selected_presets
    library["status"] = "diagnostic-ready"
    return library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    config = read_json(os.path.realpath(os.path.abspath(args.config)))
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(build_library(config), output_path)
    print("Built neck BodyFit review matrix: {}".format(output_path))


if __name__ == "__main__":
    main()
