"""Build the eight frozen first-batch identities on the two average BodyFits."""

import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPILER_PATH = os.path.join(SCRIPT_DIR, "cc_compile_character_manifest.py")
COMPILER_SPEC = importlib.util.spec_from_file_location(
    "cc_compile_character_manifest_for_first_batch",
    COMPILER_PATH,
)
manifest_compiler = importlib.util.module_from_spec(COMPILER_SPEC)
COMPILER_SPEC.loader.exec_module(manifest_compiler)

DEFAULT_SOURCE_MANIFEST = os.path.join(
    SCRIPT_DIR, "cc_character_integration_manifest_v1.json"
)
DEFAULT_BODY_LIBRARY = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v2.json")
DEFAULT_DECISIONS = os.path.join(
    SCRIPT_DIR, "cc_head_bodyfit_scale_decisions_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_first_batch_identity_library_20260820_v1.json"
)

IDENTITY_ROWS = (
    ("F_ID01", "F02_Average", "CCINT_F01_YOUNG"),
    ("F_ID02", "F02_Average", "CCINT_F02_YOUNG"),
    ("F_ID03", "F02_Average", "CCINT_F03_YOUNG"),
    ("F_ID04", "F02_Average", "CCINT_F04_YOUNG"),
    ("M_ID01", "M02_Average", "CCINT_M01_YOUNG"),
    ("M_ID02", "M02_Average", "CCINT_M02_YOUNG"),
    ("M_ID03", "M02_Average", "CCINT_M03_YOUNG"),
    ("M_ID04", "M02_Average", "CCINT_M04_YOUNG"),
)


class FirstBatchIdentityBuildError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


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


def source_record(path):
    path = canonical_path(path)
    return {"path": path, "sha256": sha256_file(path)}


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise FirstBatchIdentityBuildError(
                "{} has invalid or duplicate {}".format(label, key)
            )
        result[value] = item
    return result


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


def build(source_manifest_path, body_library_path, decisions_path):
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
    adjustments = manifest_compiler.compile_bodyfit_proportion_adjustments(
        decisions, bodies
    )

    presets = []
    for identity_id, bodyfit_id, donor_id in IDENTITY_ROWS:
        if donor_id not in donors or bodyfit_id not in bodies:
            raise FirstBatchIdentityBuildError(
                "Missing donor or BodyFit for {}".format(identity_id)
            )
        donor = donors[donor_id]
        body = bodies[bodyfit_id]
        if donor.get("sex") != body.get("sex"):
            raise FirstBatchIdentityBuildError(
                "Sex mismatch for {}".format(identity_id)
            )
        preset = copy.deepcopy(donor)
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
                "character_id": identity_id,
                "preset_id": identity_id,
                "review_status": "first-batch-frozen-from-accepted-face-v3",
                "source_project": copy.deepcopy(body["source_project"]),
                "target_body_morphs": copy.deepcopy(body["target_body_morphs"]),
                "target_junction_morphs": copy.deepcopy(
                    body["target_junction_morphs"]
                ),
            }
        )
        clear_age_overlay(preset)
        preset["appearance_validation_plan"] = {
            "asset_load_pacing": {
                "default_after_seconds": 1.5,
                "default_before_seconds": 0.75,
                "slots": {
                    "facial_hair": {
                        "after_seconds": 5.0,
                        "before_seconds": 2.0,
                    },
                    "scalp_hair": {
                        "after_seconds": 6.0,
                        "before_seconds": 3.0,
                    },
                    "skin": {
                        "after_seconds": 5.0,
                        "before_seconds": 2.0,
                    },
                },
            },
            "domain": "face_identity",
            "integrated_facial_assembly_validation": {
                "render_static_hair_views": False,
                "required_invariants": [
                    "body_and_junction_unchanged",
                    "face_identity_matches_recipe",
                    "eye_geometry_preserved",
                    "eye_support_preserved",
                    "hair_pigmentation_shared",
                ],
            },
            "pose_profile": None,
            "required_views": [
                "reconstructed_preview",
                "face_front",
                "face_three_quarter",
                "face_profile",
            ],
            "verification_mode": "first_batch_static_identity_assembly",
        }
        preset["source_request"]["bodyfit_id"] = bodyfit_id
        preset["source_request"]["character_id"] = identity_id
        preset["first_batch_identity"] = {
            "donor_preset_id": donor_id,
            "identity_id": identity_id,
            "production_bodyfit_id": bodyfit_id,
            "source_face_recipe_id": donor.get("face_recipe_id"),
        }
        presets.append(preset)

    face_recipe_ids = [item.get("face_recipe_id") for item in presets]
    if len(face_recipe_ids) != len(set(face_recipe_ids)):
        raise FirstBatchIdentityBuildError(
            "First-batch identity face recipes must be unique"
        )
    if any(item.get("full_face_elder_weight") != 0.0 for item in presets):
        raise FirstBatchIdentityBuildError("Age overlay must be disabled")

    document = copy.deepcopy(source_manifest)
    document.update(
        {
            "body_application_mode": "source_project",
            "character_count": len(presets),
            "generated_at": now(),
            "library_id": "cc_first_batch_identity_library_20260820_v1",
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
            "status": "ready-for-first-batch-identity-assembly",
            "success": True,
        }
    )
    document["first_batch_design"] = {
        "age_overlay": "disabled",
        "female_bodyfit_id": "F02_Average",
        "identity_count": 8,
        "identities_per_sex": 4,
        "male_bodyfit_id": "M02_Average",
        "source_identity_system": "accepted_face_v3",
    }
    document["sources"]["body_library"] = source_record(body_library_path)
    document["sources"]["bodyfit_proportion_decisions"] = source_record(
        decisions_path
    )
    document["sources"]["first_batch_source_manifest"] = source_record(
        source_manifest_path
    )
    document["selection_policy"] = {
        "age_overlay": "disabled",
        "face_recipe_uniqueness": "required",
        "method": "four_accepted_face_v3_donors_per_sex_on_average_bodyfit",
    }
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--body-library", default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_path = canonical_path(args.output)
    document = build(args.source_manifest, args.body_library, args.decisions)
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "identity_count": document["character_count"],
                "output": output_path,
                "preset_ids": [item["preset_id"] for item in document["presets"]],
                "success": True,
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
