"""Build reviewed CC eye compatibility records from completed validation runs."""

import argparse
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EYE_ASSET_IDS = (
    "CCAPP_EYES_9a42ba5420b0",
    "CCAPP_EYES_2fd4c8984575",
    "CCAPP_EYES_20fe8f283ceb",
    "CCAPP_EYES_dffdc3acba51",
    "CCAPP_EYES_4ea86aadfe2f",
    "CCAPP_EYES_775c56b6c380",
    "CCAPP_EYES_30a67801797b",
    "CCAPP_EYES_f1c5819ce40d",
    "CCAPP_EYES_da24f67fcda7",
    "CCAPP_EYES_6ccfc11f058d",
    "CCAPP_EYES_f4fb1324adfb",
    "CCAPP_EYES_91523528133b",
)
REPRESENTATIVE_ASSET_ID = EYE_ASSET_IDS[0]
REQUIRED_ARTIFACTS = (
    "face_front_preview",
    "face_profile_preview",
    "face_three_quarter_preview",
    "eye_look_left_preview",
    "eye_look_right_preview",
    "eye_look_up_preview",
    "eye_look_down_preview",
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


def eye_step(result):
    steps = (result.get("appearance_application") or {}).get("steps") or []
    steps = [item for item in steps if item.get("slot") == "eyes"]
    if len(steps) != 1:
        raise ReviewError(
            "{} does not contain exactly one eye step".format(
                result.get("preset_id")
            )
        )
    return steps[0]


def validate_result(preset_id, result):
    if result.get("success") is not True:
        raise ReviewError("Validation failed: {}".format(preset_id))
    if result.get("appearance_matches_recipe") is not True:
        raise ReviewError("Appearance did not match recipe: {}".format(preset_id))
    if result.get("appearance_morphs_within_policy") is not True:
        raise ReviewError("Protected morphs changed: {}".format(preset_id))
    step = eye_step(result)
    dialog = step.get("dialog_policy") or {}
    required = {
        "material_only_verified": step.get("material_only_verified") is True,
        "eye_geometry_preserved": step.get("eye_geometry_preserved") is True,
        "eye_support_preserved": step.get("eye_support_preserved") is True,
        "changed_only_eye_mesh": step.get("material_changed_meshes")
        == ["CC_Base_Eye"],
        "material_only_clicked_once": dialog.get("clicked_count") == 1
        and dialog.get("target_button") == "Material Only",
    }
    failed = [name for name, passed in required.items() if not passed]
    if failed:
        raise ReviewError(
            "{} failed eye invariants: {}".format(preset_id, ", ".join(failed))
        )
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
    return step


def common_asset_notes(asset_id):
    notes = [
        "Apply this selected CC eye asset with Material Only; do not replace the eye object.",
        "Material-only application preserved the existing eye object, geometry digest, 130 eye support morph weights, and Eyeball Move=0 in the reviewed samples.",
        "The current approval covers the adult CC5 HD geometry family only; child presets, third-party eye geometry, and future incompatible eye generations require separate validation.",
        "Blink and detailed facial-expression deformation are intentionally deferred to the eyelash and facial-animation validation stage.",
    ]
    if asset_id == REPRESENTATIVE_ASSET_ID:
        notes.insert(
            0,
            "Eyes_01 is the representative material validated on all 32 current adult face recipes and M01-M04/F01-F04 BodyFits.",
        )
    else:
        notes.insert(
            0,
            "Accepted on one male and one female representative face; full adult geometry compatibility is inherited from Eyes_01 because this asset changes only CC_Base_Eye material and preserves the original eye geometry.",
        )
    return notes


def build(batch_path, validation_path, audit_path, output_path, mode):
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    validation_path = os.path.realpath(os.path.abspath(validation_path))
    audit_path = os.path.realpath(os.path.abspath(audit_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    for path in (batch_path, validation_path, audit_path):
        if not os.path.isfile(path):
            raise ReviewError("Input is missing: {}".format(path))

    batch = read_json(batch_path)
    validation = read_json(validation_path)
    audit = read_json(audit_path)
    if audit.get("success") is not True:
        raise ReviewError("Eye audit was not successful: {}".format(audit_path))
    presets = indexed(batch.get("presets") or [], "preset_id", "Batch preset")
    results = indexed(
        validation.get("results") or [], "preset_id", "Validation result"
    )
    if set(presets) != set(results):
        raise ReviewError("Batch and validation preset sets differ")

    expected_assets = (
        set(EYE_ASSET_IDS) if mode == "probe" else {REPRESENTATIVE_ASSET_ID}
    )
    expected_per_asset = 2 if mode == "probe" else 32
    observed_counts = dict((asset_id, 0) for asset_id in expected_assets)
    reviews = []
    for preset_id in sorted(presets):
        preset = presets[preset_id]
        result = results[preset_id]
        step = validate_result(preset_id, result)
        asset_ids = preset.get("appearance_asset_ids") or []
        if len(asset_ids) != 1 or asset_ids[0] not in expected_assets:
            raise ReviewError(
                "Preset has an unsupported eye asset: {}".format(preset_id)
            )
        asset_id = asset_ids[0]
        if step.get("asset_id") != asset_id:
            raise ReviewError(
                "Applied eye asset differs from the batch: {}".format(preset_id)
            )
        observed_counts[asset_id] += 1
        notes = [
            "Reviewed neutral front, profile, three-quarter, and left/right/up/down eye-look previews.",
            "No obvious eye-object protrusion, iris displacement outside the visible eye region, or asymmetric bilateral motion is visible.",
            "Extreme downward gaze can expose additional upper sclera on some source faces; neutral alignment remains correct and this is tracked as a pose/eyelid observation rather than an eye-material failure.",
        ]
        reviews.append(
            {
                "notes": notes,
                "preset_id": preset_id,
                "visual_status": "accepted",
            }
        )

    incorrect_counts = {
        asset_id: count
        for asset_id, count in observed_counts.items()
        if count != expected_per_asset
    }
    if incorrect_counts:
        raise ReviewError(
            "Unexpected per-asset sample counts: {}".format(incorrect_counts)
        )

    review_id = (
        "adult_eye_equivalence_visual_review_v1"
        if mode == "probe"
        else "adult_eye_compatibility_matrix_visual_review_v1"
    )
    scope = (
        "Manual color-variant and motion review on one current male and one "
        "current female representative face per selected eye asset."
        if mode == "probe"
        else "Manual geometry and motion review of Eyes_01 on the current "
        "eight adult BodyFits and 32 adult face recipes."
    )
    document = {
        "schema_version": 1,
        "review_id": review_id,
        "reviewed_at": now(),
        "scope": scope,
        "sources": {
            "batch": batch_path,
            "validation": validation_path,
            "audit": audit_path,
        },
        "compatibility_inheritance": {
            "basis": (
                "All 12 selected assets were loaded through Material Only and "
                "preserved the original eye object, geometry, and support morphs."
            ),
            "representative_asset_id": REPRESENTATIVE_ASSET_ID,
            "representative_matrix": (
                "32 current adult face recipes across M01-M04 and F01-F04"
            ),
            "limit": (
                "Inheritance applies only to these material-only variants on "
                "the current adult CC5 HD eye geometry family."
            ),
        },
        "asset_notes": dict(
            (asset_id, common_asset_notes(asset_id))
            for asset_id in sorted(expected_assets)
        ),
        "reviews": reviews,
    }
    write_json(document, output_path)
    return {
        "success": True,
        "output": output_path,
        "mode": mode,
        "review_count": len(reviews),
        "asset_count": len(expected_assets),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("probe", "matrix"), required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.batch,
                args.validation,
                args.audit,
                args.output,
                args.mode,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
