"""Build a lightweight cross-face smoke matrix for BodyFit proportions."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCE = os.path.join(
    SCRIPT_DIR,
    "cc_character_integration_manifest_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_bodyfit_proportion_smoke_v1.json",
)
TARGET_BODYFITS = (
    "F01_Lean",
    "M01_Lean",
    "M03_Athletic",
)
SELECTED_AGE_LABELS = ("young", "middle")
PRESET_FIELDS = (
    "base_avatar",
    "body_and_junction_fingerprint",
    "body_class",
    "bodyfit_id",
    "bodyfit_proportion_adjustment",
    "face_camera",
    "face_generation",
    "face_recipe_id",
    "local_face_morphs",
    "local_morph_fingerprint",
    "sex",
    "source_facial_profile",
    "source_head_preset",
    "source_project",
    "target_body_morphs",
    "target_junction_morphs",
)


class SmokeBuildError(RuntimeError):
    pass


def now():
    return (
        datetime.datetime.now()
        .astimezone()
        .replace(microsecond=0)
        .isoformat()
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


def build(source):
    if int(source.get("schema_version", -1)) != 1:
        raise SmokeBuildError("Unsupported production manifest schema")
    if source.get("success") is not True:
        raise SmokeBuildError("Production manifest is not successful")
    presets = source.get("presets") or []
    selected = []
    matrix_cases = []
    for bodyfit_id in TARGET_BODYFITS:
        candidates = {
            item.get("age_label"): item
            for item in presets
            if item.get("bodyfit_id") == bodyfit_id
        }
        missing_ages = sorted(set(SELECTED_AGE_LABELS) - set(candidates))
        if missing_ages:
            raise SmokeBuildError(
                "{} is missing age cases {}".format(
                    bodyfit_id,
                    missing_ages,
                )
            )
        bodyfit_cases = [candidates[label] for label in SELECTED_AGE_LABELS]
        face_ids = {item.get("face_recipe_id") for item in bodyfit_cases}
        seed_ids = {
            (item.get("face_generation") or {}).get("primary_seed_id")
            for item in bodyfit_cases
        }
        if len(face_ids) != 2 or len(seed_ids) != 2 or None in seed_ids:
            raise SmokeBuildError(
                "{} smoke cases must use two distinct faces".format(
                    bodyfit_id
                )
            )
        for source_preset in bodyfit_cases:
            missing_fields = [
                field
                for field in PRESET_FIELDS
                if field not in source_preset
            ]
            if missing_fields:
                raise SmokeBuildError(
                    "{} is missing {}".format(
                        source_preset.get("preset_id"),
                        missing_fields,
                    )
                )
            age_label = source_preset["age_label"]
            preset_id = "PROPSMOKE_{}_{}".format(
                bodyfit_id.upper(),
                age_label.upper(),
            )
            preset = {
                field: copy.deepcopy(source_preset[field])
                for field in PRESET_FIELDS
            }
            preset.update(
                {
                    "appearance_validation_plan": {
                        "domain": "bodyfit_proportion",
                        "face_camera_reference_top_z": float(
                            source_preset["appearance_validation_plan"][
                                "face_camera_reference_top_z"
                            ]
                        ),
                    },
                    "character_id": preset_id,
                    "preset_id": preset_id,
                    "review_status": "bodyfit-proportion-smoke",
                    "source_production_preset_id": source_preset[
                        "preset_id"
                    ],
                }
            )
            selected.append(preset)
            matrix_cases.append(
                {
                    "bodyfit_id": bodyfit_id,
                    "face_recipe_id": preset["face_recipe_id"],
                    "head_scale": preset[
                        "bodyfit_proportion_adjustment"
                    ]["targets"][0]["target"],
                    "neck_height": preset[
                        "bodyfit_proportion_adjustment"
                    ]["targets"][1]["target"],
                    "preset_id": preset_id,
                    "primary_seed_id": preset["face_generation"][
                        "primary_seed_id"
                    ],
                    "source_production_preset_id": source_preset[
                        "preset_id"
                    ],
                }
            )

    document = {
        "schema_version": 1,
        "library_id": "cc_bodyfit_proportion_smoke_v1",
        "diagnostic_mode": "bodyfit_proportion_smoke_matrix",
        "body_application_mode": source["body_application_mode"],
        "expected_eyeball_move_weight": source[
            "expected_eyeball_move_weight"
        ],
        "face_resources": copy.deepcopy(source["face_resources"]),
        "generated_at": now(),
        "inter_case_delay_seconds": 5.0,
        "matrix": {
            "case_count": len(selected),
            "cases": matrix_cases,
            "faces_per_bodyfit": 2,
            "purpose": (
                "cross_face_runtime_validation_of_fixed_bodyfit_proportions"
            ),
            "target_bodyfits": list(TARGET_BODYFITS),
        },
        "presets": selected,
        "preview_lightroom": copy.deepcopy(source.get("preview_lightroom")),
        "source_library_id": source.get("library_id"),
        "status": "diagnostic-ready",
    }
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source_path = os.path.realpath(os.path.abspath(args.source))
    output_path = os.path.realpath(os.path.abspath(args.output))
    document = build(read_json(source_path))
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "case_count": len(document["presets"]),
                "output": output_path,
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
