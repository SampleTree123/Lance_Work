"""Build the reviewed male facial-hair compatibility record."""

import argparse
import collections
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(
    SCRIPT_DIR, "cc_facial_hair_compatibility_batch_v1.json"
)
DEFAULT_VALIDATION = os.path.join(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts",
    "facial_hair_matrix_v2_merged_20260727_01",
    "validation_result.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_facial_hair_compatibility_visual_review_v1.json"
)
REQUIRED_ARTIFACT_KEYS = (
    "face_front_preview",
    "face_three_quarter_preview",
    "face_profile_preview",
    "face_smile_preview",
    "face_jaw_open_preview",
    "face_jaw_open_three_quarter_preview",
)
REQUIRED_DYNAMIC_POSES = frozenset(
    ("smile_front", "jaw_open_front", "jaw_open_three_quarter")
)


class ReviewError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


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


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ReviewError("{} IDs are invalid or duplicated".format(label))
        result[value] = item
    return result


def build(batch_path, validation_path, output_path):
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    validation_path = os.path.realpath(os.path.abspath(validation_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    for path in (batch_path, validation_path):
        if not os.path.isfile(path):
            raise ReviewError("Input is missing: {}".format(path))

    batch = read_json(batch_path)
    validation = read_json(validation_path)
    presets = indexed(batch.get("presets") or [], "preset_id", "Batch preset")
    results = indexed(
        validation.get("results") or [],
        "preset_id",
        "Validation result",
    )
    if set(presets) != set(results):
        raise ReviewError("Batch and validation preset sets differ")
    if len(results) != 45:
        raise ReviewError(
            "Expected the complete 45-preset facial-hair matrix"
        )

    asset_records = collections.defaultdict(list)
    reviews = []
    for preset_id in sorted(presets):
        preset = presets[preset_id]
        result = results[preset_id]
        if preset.get("sex") != "male":
            raise ReviewError("Facial-hair preset is not male: {}".format(preset_id))
        if result.get("success") is not True:
            raise ReviewError("Validation failed: {}".format(preset_id))
        if result.get("appearance_matches_recipe") is not True:
            raise ReviewError(
                "Appearance recipe mismatch: {}".format(preset_id)
            )
        if result.get("appearance_morphs_within_policy") is not True:
            raise ReviewError(
                "Protected morph policy failed: {}".format(preset_id)
            )
        artifacts = result.get("artifacts") or {}
        for key in REQUIRED_ARTIFACT_KEYS:
            path = artifacts.get(key)
            if (
                not isinstance(path, str)
                or not os.path.isfile(path)
                or os.path.getsize(path) <= 0
            ):
                raise ReviewError(
                    "Required preview is missing for {}: {}".format(
                        preset_id, key
                    )
                )
        pose_validation = result.get("facial_pose_validation") or {}
        if pose_validation.get("profile") != "facial_hair_visibility_v1":
            raise ReviewError(
                "Unexpected facial-hair pose profile: {}".format(preset_id)
            )
        pose_ids = {
            item.get("pose_id")
            for item in pose_validation.get("poses") or []
        }
        if pose_ids != REQUIRED_DYNAMIC_POSES:
            raise ReviewError(
                "Dynamic pose set is incomplete: {}".format(preset_id)
            )

        steps = (result.get("appearance_application") or {}).get("steps") or []
        if len(steps) != 1 or steps[0].get("replacement_verified") is not True:
            raise ReviewError(
                "Facial-hair replacement was not verified: {}".format(
                    preset_id
                )
            )
        asset_ids = preset.get("appearance_asset_ids") or []
        if len(asset_ids) != 1:
            raise ReviewError(
                "Expected one facial-hair asset: {}".format(preset_id)
            )
        asset_records[asset_ids[0]].append(
            {
                "preset": preset,
                "result": result,
                "step": steps[0],
            }
        )
        reviews.append(
            {
                "preset_id": preset_id,
                "visual_status": "accepted",
                "notes": [
                    (
                        "Reviewed neutral front, three-quarter, and profile "
                        "previews; no obvious floating, facial-surface "
                        "penetration, or misplaced facial-hair geometry is visible."
                    ),
                    (
                        "Reviewed smile and jaw-open front/three-quarter "
                        "previews; no obvious penetration through the lips, "
                        "cheeks, chin, or neck is visible."
                    ),
                    (
                        "The run created a verified facial-hair representation, "
                        "preserved protected body and face morphs, and rendered "
                        "all required visibility views."
                    ),
                ],
            }
        )

    if len(asset_records) != 5:
        raise ReviewError("Expected exactly five reviewed facial-hair assets")
    asset_notes = {}
    for asset_id in sorted(asset_records):
        records = asset_records[asset_id]
        if len(records) != 9:
            raise ReviewError(
                "{} does not have nine male-face validations".format(asset_id)
            )
        display_names = {
            item["step"].get("display_name") for item in records
        }
        if len(display_names) != 1:
            raise ReviewError(
                "{} has inconsistent display names".format(asset_id)
            )
        display_name = next(iter(display_names))
        beard_part_counts = {
            len(item["step"].get("replacement_inventory") or [])
            for item in records
        }
        if len(beard_part_counts) != 1:
            raise ReviewError(
                "{} has inconsistent Beard AvatarPart counts".format(asset_id)
            )
        beard_part_count = next(iter(beard_part_counts))
        scene_additions = sorted(
            {
                added.get("name")
                for item in records
                for added in item["step"].get("added_objects") or []
                if added.get("name")
            }
        )
        representation_note = (
            "{} consistently loaded as {} Beard AvatarPart(s).".format(
                display_name, beard_part_count
            )
        )
        if scene_additions:
            representation_note += (
                " It also added the scene object(s): {}.".format(
                    ", ".join(scene_additions)
                )
            )
        asset_notes[asset_id] = [
            (
                "{} passed nine approved adult male primary-face presets "
                "with M02 Average BodyFit held constant.".format(display_name)
            ),
            (
                "Use this asset in the male facial-hair pool; female and child "
                "assignment was not part of this approval."
            ),
            representation_note,
            (
                "Neutral front/three-quarter/profile plus smile and jaw-open "
                "front/three-quarter views were reviewed with no obvious "
                "facial penetration."
            ),
            (
                "New third-party head generations or materially expanded "
                "face-morph ranges require separate compatibility validation."
            ),
        ]

    review = {
        "schema_version": 1,
        "review_id": "cc_facial_hair_compatibility_visual_review_v1",
        "generated_at": now(),
        "scope": (
            "Complete 45-preset review of five selected facial-hair groups "
            "across nine approved adult male primary faces at M02 Average "
            "BodyFit. Female, child, third-party, and future expanded face "
            "ranges are outside this approval."
        ),
        "sources": {
            "batch": batch_path,
            "consolidated_validation": validation_path,
            "contact_sheet_directory": os.path.join(
                os.path.dirname(validation_path), "review"
            ),
        },
        "asset_notes": asset_notes,
        "reviews": reviews,
    }
    write_json(review, output_path)
    return {
        "success": True,
        "output": output_path,
        "review_count": len(reviews),
        "asset_count": len(asset_notes),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--validation", default=DEFAULT_VALIDATION)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.batch, args.validation, args.output),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
