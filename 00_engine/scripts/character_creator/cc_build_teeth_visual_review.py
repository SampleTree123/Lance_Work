"""Build the reviewed teeth compatibility records from a completed CC batch."""

import argparse
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(SCRIPT_DIR, "cc_teeth_compatibility_batch_v1.json")
DEFAULT_VALIDATION = os.path.join(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts",
    "teeth_compatibility_v1_consolidated_20260724",
    "validation_result.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_teeth_compatibility_visual_review_v1.json"
)

ASSET_NOTES = {
    "CCAPP_TEETH_b67a818a4484": [
        "Accepted on M01-M04 and F01-F04 across the current 32 adult face recipes.",
        "Neutral, smile, jaw-open front, and jaw-open three-quarter previews show no obvious floating, lip penetration, or jaw detachment.",
        "Use full-object replacement; remove the existing Teeth avatar part before loading this asset to avoid CC's interactive replace/material-only dialog.",
        "Approval does not cover child presets, future third-party face morphs, or final material look development.",
    ],
    "CCAPP_TEETH_4a7877c8220c": [
        "Accepted on M01-M04 and F01-F04 across the current 32 adult face recipes.",
        "Neutral, smile, jaw-open front, and jaw-open three-quarter previews show no obvious floating, lip penetration, or jaw detachment.",
        "The teeth appear darker and slightly more recessed in the clay validation viewport; geometry is accepted, while final material appearance remains outside this review.",
        "Use full-object replacement; remove the existing Teeth avatar part before loading this asset to avoid CC's interactive replace/material-only dialog.",
        "Approval does not cover child presets, future third-party face morphs, or final material look development.",
    ],
}

REQUIRED_ARTIFACTS = (
    "face_front_preview",
    "teeth_smile_preview",
    "teeth_jaw_open_preview",
    "teeth_jaw_open_three_quarter_preview",
)


class ReviewError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


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
        validation.get("results") or [], "preset_id", "Validation result"
    )
    if set(presets) != set(results):
        raise ReviewError("Batch and validation preset sets differ")

    reviews = []
    observed_assets = set()
    for preset_id in sorted(presets):
        preset = presets[preset_id]
        result = results[preset_id]
        if result.get("success") is not True:
            raise ReviewError("Validation failed: {}".format(preset_id))
        if result.get("appearance_matches_recipe") is not True:
            raise ReviewError("Appearance did not match recipe: {}".format(preset_id))
        if result.get("appearance_morphs_within_policy") is not True:
            raise ReviewError("Protected morphs changed: {}".format(preset_id))

        asset_ids = preset.get("appearance_asset_ids") or []
        if len(asset_ids) != 1 or asset_ids[0] not in ASSET_NOTES:
            raise ReviewError(
                "Preset has an unsupported teeth asset: {}".format(preset_id)
            )
        asset_id = asset_ids[0]
        observed_assets.add(asset_id)

        artifacts = result.get("artifacts") or {}
        missing = [
            key
            for key in REQUIRED_ARTIFACTS
            if not os.path.isfile(artifacts.get(key) or "")
        ]
        if missing:
            raise ReviewError(
                "Required previews are missing for {}: {}".format(
                    preset_id, ", ".join(missing)
                )
            )

        notes = [
            "Reviewed neutral, smile, jaw-open front, and jaw-open three-quarter previews.",
            "No obvious teeth floating, lip penetration, gum displacement, or jaw detachment is visible.",
        ]
        if asset_id == "CCAPP_TEETH_4a7877c8220c":
            notes.append(
                "HD Teeth 2K is darker and slightly more recessed in the clay preview; this was not treated as a geometry failure."
            )
        reviews.append(
            {
                "notes": notes,
                "preset_id": preset_id,
                "visual_status": "accepted",
            }
        )

    if observed_assets != set(ASSET_NOTES):
        raise ReviewError("The completed batch does not cover both approved teeth assets")

    document = {
        "schema_version": 1,
        "review_id": "adult_teeth_compatibility_visual_review_v1",
        "reviewed_at": now(),
        "scope": (
            "Manual geometry review of the current eight adult BodyFits and "
            "32 adult face recipes; material look development is excluded."
        ),
        "sources": {
            "batch": batch_path,
            "validation": validation_path,
        },
        "asset_notes": ASSET_NOTES,
        "reviews": reviews,
    }
    write_json(document, output_path)
    return {
        "success": True,
        "output": output_path,
        "review_count": len(reviews),
        "asset_count": len(observed_assets),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Write the completed teeth compatibility visual review."
    )
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--validation", default=DEFAULT_VALIDATION)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.batch, args.validation, args.output), indent=2))


if __name__ == "__main__":
    main()
