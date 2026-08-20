"""Build one deterministic, unaged showcase character per accepted BodyFit."""

import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPILER_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_compile_character_manifest.py",
)
COMPILER_SPEC = importlib.util.spec_from_file_location(
    "cc_compile_character_manifest_for_showcase",
    COMPILER_PATH,
)
manifest_compiler = importlib.util.module_from_spec(COMPILER_SPEC)
COMPILER_SPEC.loader.exec_module(manifest_compiler)
DEFAULT_SOURCE_MANIFEST = os.path.join(
    SCRIPT_DIR,
    "cc_character_integration_manifest_v1.json",
)
DEFAULT_BODY_LIBRARY = os.path.join(
    SCRIPT_DIR,
    "cc_body_preset_library_v2.json",
)
DEFAULT_DECISIONS = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_decisions_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_character_showcase_10_20260803_v1.json",
)

SHOWCASE_ROWS = (
    ("M01_Lean", "CCINT_M01_YOUNG"),
    ("M02_Average", "CCINT_M02_YOUNG"),
    ("M03_Athletic", "CCINT_M03_YOUNG"),
    ("M04_Heavy", "CCINT_M04_YOUNG"),
    ("M05_Short_Average", "CCINT_M02_MIDDLE"),
    ("F01_Lean", "CCINT_F01_YOUNG"),
    ("F02_Average", "CCINT_F02_YOUNG"),
    ("F03_Athletic", "CCINT_F03_YOUNG"),
    ("F04_Heavy", "CCINT_F04_YOUNG"),
    ("F05_Short_Average", "CCINT_F02_MIDDLE"),
)
SHORT_BODYFITS = frozenset(("M05_Short_Average", "F05_Short_Average"))


class ShowcaseBuildError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def canonical_path(path):
    return os.path.realpath(os.path.abspath(path))


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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ShowcaseBuildError(
                "{} has invalid or duplicate {}".format(label, key)
            )
        result[value] = item
    return result


def source_record(path):
    path = canonical_path(path)
    return {"path": path, "sha256": sha256_file(path)}


def clear_age_overlay(preset):
    preset["age_label"] = "young"
    preset["full_face_elder_weight"] = 0.0
    preset["gray_fraction"] = 0.0
    preset["visible_gray_fraction"] = 0.0
    source_request = preset.get("source_request") or {}
    components = source_request.get("facial_components") or {}
    components["age_label"] = "young"
    source_request["facial_components"] = components
    preset["source_request"] = source_request


def build(
    source_manifest_path,
    body_library_path,
    decisions_path,
    dynamic_poses=True,
):
    source_manifest_path = canonical_path(source_manifest_path)
    body_library_path = canonical_path(body_library_path)
    decisions_path = canonical_path(decisions_path)
    source_manifest = read_json(source_manifest_path)
    body_library = read_json(body_library_path)
    decisions = read_json(decisions_path)

    donors = indexed(
        source_manifest.get("presets") or [],
        "preset_id",
        "Source integration manifest",
    )
    bodies = indexed(
        body_library.get("presets") or [],
        "preset_id",
        "BodyFit library",
    )
    expected_bodyfits = [item[0] for item in SHOWCASE_ROWS]
    if set(bodies) != set(expected_bodyfits):
        raise ShowcaseBuildError("BodyFit library must contain the accepted ten")
    adjustments = manifest_compiler.compile_bodyfit_proportion_adjustments(
        decisions,
        bodies,
    )

    presets = []
    for bodyfit_id, donor_id in SHOWCASE_ROWS:
        if donor_id not in donors:
            raise ShowcaseBuildError("Missing showcase donor: {}".format(donor_id))
        donor = donors[donor_id]
        body = bodies[bodyfit_id]
        if donor.get("sex") != body.get("sex"):
            raise ShowcaseBuildError("Showcase donor sex mismatch: {}".format(bodyfit_id))
        preset = copy.deepcopy(donor)
        character_id = "CCSHOW_{}_001".format(bodyfit_id.upper())
        preset.update(
            {
                "base_avatar": copy.deepcopy(body["base_avatar"]),
                "body_and_junction_fingerprint": body[
                    "body_and_junction_fingerprint"
                ],
                "body_class": body.get("body_class"),
                "bodyfit_id": bodyfit_id,
                "bodyfit_proportion_adjustment": copy.deepcopy(
                    adjustments[bodyfit_id]
                ),
                "character_id": character_id,
                "preset_id": character_id,
                "review_status": (
                    "showcase-pending-short-bodyfit-appearance-review"
                    if bodyfit_id in SHORT_BODYFITS
                    else "showcase-reviewed-source-appearance"
                ),
                "source_project": copy.deepcopy(body["source_project"]),
                "target_body_morphs": copy.deepcopy(
                    body["target_body_morphs"]
                ),
                "target_junction_morphs": copy.deepcopy(
                    body["target_junction_morphs"]
                ),
            }
        )
        clear_age_overlay(preset)
        preset["appearance_validation_plan"][
            "post_pose_eye_world_translation_tolerance_cm"
        ] = 0.05
        if not dynamic_poses:
            preset["appearance_validation_plan"].update(
                {
                    "pose_profile": None,
                    "required_views": [
                        "reconstructed_preview",
                        "face_front",
                        "face_three_quarter",
                        "face_profile",
                        "hair_rear_three_quarter",
                        "hair_rear",
                    ],
                    "verification_mode": "integrated_static_showcase",
                }
            )
            preset["appearance_validation_plan"].pop(
                "post_pose_eye_world_translation_tolerance_cm",
                None,
            )
        preset["source_request"]["bodyfit_id"] = bodyfit_id
        preset["source_request"]["character_id"] = character_id
        preset["showcase_provenance"] = {
            "appearance_bodyfit_inheritance": (
                "M02_Average"
                if bodyfit_id == "M05_Short_Average"
                else (
                    "F02_Average"
                    if bodyfit_id == "F05_Short_Average"
                    else bodyfit_id
                )
            ),
            "appearance_requires_visual_review": bodyfit_id in SHORT_BODYFITS,
            "donor_character_id": donor_id,
            "unaged_showcase": True,
        }
        presets.append(preset)

    face_ids = [item.get("face_recipe_id") for item in presets]
    if len(set(face_ids)) != len(face_ids):
        raise ShowcaseBuildError("Showcase face recipes must be unique")
    if any(item.get("full_face_elder_weight") != 0.0 for item in presets):
        raise ShowcaseBuildError("Showcase must not apply the elder Morph")

    document = copy.deepcopy(source_manifest)
    document.update(
        {
            "body_application_mode": "source_project",
            "character_count": len(presets),
            "generated_at": now(),
            "library_id": (
                "cc_character_showcase_10_20260803_v1"
                if dynamic_poses
                else "cc_character_showcase_10_static_20260803_v1"
            ),
            "presets": presets,
            "preview_capture_mode": "render_image",
            "preview_resolution": [1024, 1024],
            "requested_character_count": len(presets),
            "request_results": [
                {
                    "bodyfit_id": item["bodyfit_id"],
                    "character_id": item["character_id"],
                    "success": True,
                }
                for item in presets
            ],
            "save_character_projects": True,
            "showcase_design": {
                "age_cross_product": False,
                "character_count": len(presets),
                "characters_per_bodyfit": 1,
                "pixel_stream_resolution": [1024, 1024],
                "project_saved_per_character": True,
                "dynamic_pose_evidence": bool(dynamic_poses),
                "short_bodyfit_appearance_review_required": True,
            },
            "status": "showcase-ready-pending-visual-review",
            "success": True,
        }
    )
    document["sources"]["body_library"] = source_record(body_library_path)
    document["sources"]["bodyfit_proportion_decisions"] = source_record(
        decisions_path
    )
    document["sources"]["showcase_source_manifest"] = source_record(
        source_manifest_path
    )
    document["selection_policy"] = {
        "age_overlay": "disabled",
        "face_recipe_uniqueness": "required",
        "method": "deterministic_one_character_per_bodyfit",
        "short_bodyfit_appearance": "same-sex-average-donor-pending-review",
    }
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--body-library", default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    output_path = canonical_path(args.output)
    document = build(
        args.source_manifest,
        args.body_library,
        args.decisions,
        dynamic_poses=not args.static_only,
    )
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "character_count": document["character_count"],
                "output": output_path,
                "preset_ids": [item["preset_id"] for item in document["presets"]],
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
