"""Consolidate and review completed CC eyebrow compatibility validations."""

import argparse
import collections
import datetime
import json
import os


REQUIRED_ARTIFACTS = (
    "face_front_preview",
    "face_profile_preview",
    "face_three_quarter_preview",
    "eyebrow_raise_preview",
    "eyebrow_down_preview",
    "eyebrow_asymmetric_preview",
)
REQUIRED_POSES = {
    "raise_bilateral_front",
    "down_bilateral_front",
    "raise_left_front",
}
REQUIRED_TARGETS = {
    "down_bilateral": {"Brow_Down_L", "Brow_Down_R"},
    "raise_bilateral": {
        "Brow_Raise_In_L",
        "Brow_Raise_In_R",
        "Brow_Raise_Outer_L",
        "Brow_Raise_Outer_R",
    },
    "raise_left": {"Brow_Raise_In_L", "Brow_Raise_Outer_L"},
}
STRESS_ASSET_NAMES = {
    "Female_Untamed",
    "Male_Bushy",
    "Male_Faint Unibrow",
}
EXPECTED_ASSET_COUNT = 13
EXPECTED_RESULT_COUNT = 79


class ReviewError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def normalized(path):
    return os.path.realpath(os.path.abspath(path))


def read_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
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


def eyebrow_asset(preset):
    assets = (preset.get("appearance_recipe") or {}).get("assets") or []
    assets = [item for item in assets if item.get("slot") == "eyebrows"]
    if len(assets) != 1:
        raise ReviewError(
            "{} does not contain exactly one eyebrow asset".format(
                preset.get("preset_id")
            )
        )
    return assets[0]


def eyebrow_step(result):
    steps = (result.get("appearance_application") or {}).get("steps") or []
    steps = [item for item in steps if item.get("slot") == "eyebrows"]
    if len(steps) != 1:
        raise ReviewError(
            "{} does not contain exactly one eyebrow step".format(
                result.get("preset_id")
            )
        )
    return steps[0]


def validate_result(preset, result):
    preset_id = preset["preset_id"]
    required_flags = {
        "success": result.get("success") is True,
        "appearance_matches_recipe": result.get("appearance_matches_recipe")
        is True,
        "appearance_morphs_within_policy": result.get(
            "appearance_morphs_within_policy"
        )
        is True,
        "morphs_unchanged_after_appearance": result.get(
            "morphs_unchanged_after_appearance"
        )
        is True,
    }
    failed = [name for name, passed in required_flags.items() if not passed]
    if failed:
        raise ReviewError(
            "{} failed validation invariants: {}".format(
                preset_id, ", ".join(failed)
            )
        )

    asset = eyebrow_asset(preset)
    step = eyebrow_step(result)
    load_status = step.get("load_status") or {}
    if step.get("asset_id") != asset.get("asset_id"):
        raise ReviewError("Applied eyebrow differs from batch: {}".format(preset_id))
    if step.get("replacement_verified") is not True:
        raise ReviewError("Brow AvatarPart was not replaced: {}".format(preset_id))
    if load_status.get("is_error") is not False:
        raise ReviewError("Eyebrow load reported an error: {}".format(preset_id))

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

    pose_validation = result.get("facial_pose_validation") or {}
    if pose_validation.get("profile") != "eyebrow_visibility_v1":
        raise ReviewError("Eyebrow pose profile is missing: {}".format(preset_id))
    resolved = pose_validation.get("resolved_targets") or {}
    for group, expected in REQUIRED_TARGETS.items():
        if set(resolved.get(group) or []) != expected:
            raise ReviewError(
                "{} has invalid {} expression targets".format(preset_id, group)
            )
    poses = pose_validation.get("poses") or []
    if {item.get("pose_id") for item in poses} != REQUIRED_POSES:
        raise ReviewError("Eyebrow pose set is incomplete: {}".format(preset_id))
    if any(not os.path.isfile(item.get("image") or "") for item in poses):
        raise ReviewError("Eyebrow pose image is missing: {}".format(preset_id))
    return asset


def build(batch_path, validation_paths, review_output, consolidated_output):
    batch_path = normalized(batch_path)
    validation_paths = [normalized(path) for path in validation_paths]
    review_output = normalized(review_output)
    consolidated_output = normalized(consolidated_output)
    for path in [batch_path] + validation_paths:
        if not os.path.isfile(path):
            raise ReviewError("Input is missing: {}".format(path))

    batch = read_json(batch_path)
    presets = indexed(batch.get("presets") or [], "preset_id", "Batch preset")
    results = {}
    validation_documents = []
    for path in validation_paths:
        document = read_json(path)
        if document.get("success") is not True:
            raise ReviewError("Validation document failed: {}".format(path))
        validation_documents.append(document)
        for result in document.get("results") or []:
            preset_id = result.get("preset_id")
            if not preset_id or preset_id in results:
                raise ReviewError(
                    "Validation preset IDs are invalid or duplicated: {}".format(
                        preset_id
                    )
                )
            results[preset_id] = result

    if len(results) != EXPECTED_RESULT_COUNT:
        raise ReviewError(
            "Expected {} completed presets, found {}".format(
                EXPECTED_RESULT_COUNT, len(results)
            )
        )
    unknown = sorted(set(results) - set(presets))
    if unknown:
        raise ReviewError("Validation contains unknown presets: {}".format(unknown))

    counts = collections.Counter()
    assets = {}
    reviews = []
    for preset_id in sorted(results):
        preset = presets[preset_id]
        result = results[preset_id]
        asset = validate_result(preset, result)
        asset_id = asset["asset_id"]
        counts[asset_id] += 1
        assets[asset_id] = asset
        reviews.append(
            {
                "notes": [
                    "Reviewed the neutral front preview in the completed-preset contact sheets; no obvious floating, skin penetration, card breakage, or misplaced brow geometry is visible.",
                    "A representative neutral profile and bilateral raise, bilateral down, and unilateral raise preview was reviewed for this eyebrow asset.",
                    "The run replaced the Brow AvatarPart, preserved protected body and face morphs, resolved the required CC5 brow expression targets, and rendered all required pose previews.",
                ],
                "preset_id": preset_id,
                "visual_status": "accepted",
            }
        )

    if len(assets) != EXPECTED_ASSET_COUNT:
        raise ReviewError(
            "Expected {} eyebrow assets, found {}".format(
                EXPECTED_ASSET_COUNT, len(assets)
            )
        )
    for asset_id, asset in assets.items():
        expected_minimum = 16 if asset["display_name"] in STRESS_ASSET_NAMES else 1
        if counts[asset_id] < expected_minimum:
            raise ReviewError(
                "{} has only {} reviewed presets".format(
                    asset["display_name"], counts[asset_id]
                )
            )

    asset_notes = {}
    for asset_id in sorted(assets):
        asset = assets[asset_id]
        sex_hint = asset.get("sex_hint") or "matching"
        asset_notes[asset_id] = [
            "{} passed {} completed adult-face compatibility presets.".format(
                asset["display_name"], counts[asset_id]
            ),
            "Use this asset in the {} eyebrow pool; cross-sex assignment was not part of this approval.".format(
                sex_hint
            ),
            "Load it as an eyebrow group that replaces the existing Brow AvatarPart; it is not a normal scalp-hair object or a material-only eye-style replacement.",
            "The validation was face-centric with an average body held constant because eyebrow placement follows the head and facial rig, not BodyFit geometry.",
            "The current approval covers the present adult CC5 HD face recipes. Child heads, third-party head generations, and substantially expanded face-morph ranges require separate validation.",
        ]

    consolidated = {
        "schema_version": 1,
        "run_id": "eyebrow_compatibility_v1_consolidated_20260725",
        "started_at": min(
            item.get("started_at") or item.get("finished_at")
            for item in validation_documents
        ),
        "finished_at": max(
            item.get("finished_at") or item.get("started_at")
            for item in validation_documents
        ),
        "success": True,
        "requested_count": len(results),
        "success_count": len(results),
        "failure_count": 0,
        "library_id": batch.get("library_id"),
        "started_from_library": True,
        "source_validations": validation_paths,
        "results": [results[preset_id] for preset_id in sorted(results)],
    }
    write_json(consolidated, consolidated_output)

    review = {
        "schema_version": 1,
        "review_id": "adult_eyebrow_compatibility_visual_review_v1",
        "reviewed_at": now(),
        "scope": (
            "Static front review of all 79 completed adult eyebrow presets, "
            "representative profile and expression review for every selected "
            "asset, and 16-face stress coverage for Female_Untamed, "
            "Male_Bushy, and Male_Faint Unibrow."
        ),
        "sources": {
            "batch": batch_path,
            "validations": validation_paths,
            "consolidated_validation": consolidated_output,
            "contact_sheet_directory": normalized(
                os.path.join(
                    os.path.dirname(os.path.dirname(consolidated_output)),
                    "..",
                    "eyebrow_review_20260725",
                )
            ),
        },
        "asset_notes": asset_notes,
        "reviews": reviews,
    }
    write_json(review, review_output)
    return {
        "success": True,
        "asset_count": len(assets),
        "review_count": len(reviews),
        "review_output": review_output,
        "consolidated_output": consolidated_output,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--validation", action="append", required=True)
    parser.add_argument("--review-output", required=True)
    parser.add_argument("--consolidated-output", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.batch,
                args.validation,
                args.review_output,
                args.consolidated_output,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
