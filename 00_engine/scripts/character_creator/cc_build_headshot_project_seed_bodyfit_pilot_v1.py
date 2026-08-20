"""Build the minimal Headshot project-seed plus average BodyFit pilot."""

import argparse
import copy
import hashlib
import json
import os


SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
ASSET_ROOT = os.path.realpath(
    os.path.join(SCRIPT_ROOT, "..", "..", "assets", "character_creator")
)
DEFAULT_HEAD_LIBRARY = os.path.join(
    SCRIPT_ROOT, "cc_headshot_skull_profile_library_v1.json"
)
DEFAULT_BODY_LIBRARY = os.path.join(
    SCRIPT_ROOT, "cc_body_preset_library_v2.json"
)
DEFAULT_SCALE_DECISIONS = os.path.join(
    SCRIPT_ROOT, "cc_head_bodyfit_scale_decisions_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_ROOT, "cc_headshot_project_seed_bodyfit_pilot_v1.json"
)

PILOT_PROFILE_ID = "H00_BASELINE"
PILOT_BODYFITS = {
    "female": "F02_Average",
    "male": "M02_Average",
}
FULL_BODY_POSITION = (-600.0, 8.0, 75.0)
HEAD_SHAPE_MORPHS = (
    ("head_width", "2019-08-13-15-33-14_head width"),
    ("head_depth", "2019-08-13-16-00-36_head depth"),
    ("skull_height", "2019-08-13-15-25-44_skull height"),
    ("skull_width", "2019-08-13-15-26-49_skull width"),
    ("skull_depth", "2019-08-13-15-27-43_skull depth"),
    ("skull_back_depth", "2019-08-21-13-57-18_skull back depth"),
    ("skull_peak", "2019-08-21-14-02-10_skull peak"),
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def require_file_record(record, label):
    if not isinstance(record, dict):
        raise RuntimeError("{} must be a file record".format(label))
    path = record.get("path")
    expected = record.get("sha256")
    if not isinstance(path, str) or not os.path.isfile(path):
        raise RuntimeError("{} is missing: {}".format(label, path))
    actual = sha256_file(path)
    if expected is not None and expected != actual:
        raise RuntimeError("{} SHA-256 changed".format(label))
    result = copy.deepcopy(record)
    result["path"] = os.path.realpath(path)
    result["bytes"] = os.path.getsize(path)
    result["sha256"] = actual
    return result


def prototype_manifest_for_source(source_project):
    project_path = os.path.realpath(source_project["path"])
    manifest_path = os.path.join(os.path.dirname(project_path), "prototype.json")
    if not os.path.isfile(manifest_path):
        raise RuntimeError(
            "Headshot prototype manifest is missing: {}".format(manifest_path)
        )
    manifest = read_json(manifest_path)
    identity = require_file_record(
        (manifest.get("canonical_assets") or {}).get("identity_project"),
        "Headshot identity project",
    )
    if identity["path"] != project_path:
        raise RuntimeError("Headshot profile and prototype identity paths differ")
    return manifest_path, manifest


def proportion_adjustment(selection, decision_set):
    targets = [
        {
            "display": decision_set["head_scale_morph"]["display"],
            "id": decision_set["head_scale_morph"]["id"],
            "role": "head_scale",
            "target": float(selection["head_scale_weight"]),
            "ui_value": int(selection["ui_value"]),
        }
    ]
    neck = selection.get("neck_adjustment")
    if neck is not None:
        targets.append(
            {
                "display": neck["display"],
                "id": neck["morph_id"],
                "role": "neck_height",
                "selection_status": neck["status"],
                "target": float(neck["weight"]),
                "ui_value": int(neck["ui_value"]),
            }
        )
    else:
        neck_morph = decision_set["neck_height_morph"]
        targets.append(
            {
                "display": neck_morph["display"],
                "id": neck_morph["id"],
                "role": "neck_height",
                "selection_status": "implicit_neutral",
                "target": 0.0,
                "ui_value": 0,
            }
        )
    return {
        "application_order": [item["role"] for item in targets],
        "decision_set_id": decision_set["decision_set_id"],
        "targets": targets,
    }


def build_library(
    head_library_path=DEFAULT_HEAD_LIBRARY,
    body_library_path=DEFAULT_BODY_LIBRARY,
    scale_decisions_path=DEFAULT_SCALE_DECISIONS,
):
    head_library = read_json(head_library_path)
    body_library = read_json(body_library_path)
    decisions = read_json(scale_decisions_path)
    head_policy = head_library.get("canonical_profile_policy") or {}
    if not head_policy.get("dynamic_validation_complete"):
        raise RuntimeError("Canonical Headshot dynamic review is not complete")
    if PILOT_PROFILE_ID not in head_policy.get("canonical_profile_ids", []):
        raise RuntimeError("Pilot Headshot profile is not canonical")

    heads = dict(
        ((item["sex"], item["head_shape_profile"]["id"]), item)
        for item in head_library.get("presets") or []
    )
    bodies = dict(
        (item["preset_id"], item) for item in body_library.get("presets") or []
    )
    scale_by_body = dict(
        (item["bodyfit_id"], item) for item in decisions.get("selections") or []
    )
    scene = head_library.get("targeted_morph_review_scene") or {}
    cameras = scene.get("face_camera_by_sex") or {}
    positions = scene.get("face_position_by_sex") or {}
    presets = []
    for sex in ("female", "male"):
        bodyfit_id = PILOT_BODYFITS[sex]
        key = (sex, PILOT_PROFILE_ID)
        if key not in heads or bodyfit_id not in bodies or bodyfit_id not in scale_by_body:
            raise RuntimeError("Pilot inputs are incomplete for {}".format(sex))
        head = heads[key]
        body = bodies[bodyfit_id]
        if body.get("sex") != sex:
            raise RuntimeError("BodyFit sex mismatch for {}".format(bodyfit_id))
        identity_project = require_file_record(
            head.get("source_project"), "{} Headshot source".format(sex)
        )
        manifest_path, prototype = prototype_manifest_for_source(identity_project)
        facial_profile = require_file_record(
            prototype["canonical_assets"]["facial_profile"],
            "{} canonical Facial Profile".format(sex),
        )
        body_reference = require_file_record(
            body.get("source_project"), "{} BodyFit source".format(bodyfit_id)
        )
        profile = copy.deepcopy(head["head_shape_profile"])
        head_targets = [
            {
                "axis": axis,
                "id": morph_id,
                "target": float(profile[axis]),
            }
            for axis, morph_id in HEAD_SHAPE_MORPHS
        ]
        camera = cameras.get(sex)
        position = positions.get(sex)
        if not isinstance(camera, str) or not os.path.isfile(camera):
            raise RuntimeError("Pilot face camera is missing for {}".format(sex))
        if not isinstance(position, list) or len(position) != 3:
            raise RuntimeError("Pilot face position is invalid for {}".format(sex))
        prototype_id = prototype["prototype_id"]
        presets.append(
            {
                "preset_id": "{}_{}_{}".format(
                    prototype_id, PILOT_PROFILE_ID, bodyfit_id
                ),
                "character_id": "{}_{}_{}".format(
                    prototype_id, PILOT_PROFILE_ID, bodyfit_id
                ),
                "sex": sex,
                "prototype_id": prototype_id,
                "bodyfit_id": bodyfit_id,
                "head_profile_id": PILOT_PROFILE_ID,
                "base_avatar": copy.deepcopy(body["base_avatar"]),
                "source_project": identity_project,
                "prototype_manifest": {
                    "path": os.path.realpath(manifest_path),
                    "sha256": sha256_file(manifest_path),
                },
                "source_facial_profile": facial_profile,
                "bodyfit_reference_project": body_reference,
                "body_and_junction_fingerprint": body[
                    "body_and_junction_fingerprint"
                ],
                "target_body_morphs": copy.deepcopy(body["target_body_morphs"]),
                "target_junction_morphs": copy.deepcopy(
                    body["target_junction_morphs"]
                ),
                "bodyfit_proportion_adjustment": proportion_adjustment(
                    scale_by_body[bodyfit_id], decisions
                ),
                "project_seed_assembly": {
                    "pipeline": "headshot_project_seed_then_bodyfit_v1",
                    "head_shape_profile": profile,
                    "head_shape_targets": head_targets,
                    "canonical_facial_profile": facial_profile,
                    "expected_expression_set_uid": "CC5 MetaHuman",
                    "expected_expression_count": 379,
                    "reconcile_actor_parts_mode": (
                        "preserve_identity_project_eye_and_teeth_verify_unchanged"
                    ),
                    "safe_local_face_morphs": [],
                },
                "face_camera": os.path.realpath(camera),
                "face_position": [float(value) for value in position],
                "full_body_position": list(FULL_BODY_POSITION),
                "review_status": "project-seed-bodyfit-pilot",
            }
        )

    preview_lightroom = scene.get("preview_lightroom")
    if not isinstance(preview_lightroom, str) or not os.path.isfile(
        preview_lightroom
    ):
        raise RuntimeError("Pilot preview Lightroom is missing")
    return {
        "schema_version": 1,
        "library_id": "cc_headshot_project_seed_bodyfit_pilot_v1",
        "diagnostic_mode": "headshot_project_seed_bodyfit_pilot",
        "preview_capture_mode": "render_image",
        "preview_resolution": [1536, 1536],
        "inter_case_delay_seconds": 6.0,
        "preview_lightroom": os.path.realpath(preview_lightroom),
        "save_character_projects": True,
        "pilot_policy": {
            "pipeline": "headshot_project_seed_then_bodyfit_v1",
            "scope": "one_average_bodyfit_per_sex_with_H00",
            "profile_id": PILOT_PROFILE_ID,
            "bodyfit_ids": [PILOT_BODYFITS["female"], PILOT_BODYFITS["male"]],
            "case_count": 2,
            "requires_saved_project_reload": True,
            "requires_dynamic_pose_gate": True,
            "production_approved": False,
            "full_body_capture_mode": (
                "standardized_avatar_offset_with_sex_face_camera"
            ),
        },
        "source_authorities": {
            "head_profile_library": os.path.realpath(head_library_path),
            "bodyfit_library": os.path.realpath(body_library_path),
            "proportion_decisions": os.path.realpath(scale_decisions_path),
        },
        "presets": presets,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build the Headshot project-seed plus average BodyFit pilot"
    )
    parser.add_argument("--head-library", default=DEFAULT_HEAD_LIBRARY)
    parser.add_argument("--body-library", default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--scale-decisions", default=DEFAULT_SCALE_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    library = build_library(
        os.path.realpath(os.path.abspath(args.head_library)),
        os.path.realpath(os.path.abspath(args.body_library)),
        os.path.realpath(os.path.abspath(args.scale_decisions)),
    )
    output = os.path.realpath(os.path.abspath(args.output))
    write_json(library, output)
    print(output)
    print("presets={}".format(len(library["presets"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
