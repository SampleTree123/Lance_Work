"""Summarize completed CC5 canonical character-integration validation."""

import argparse
import datetime
import json
import math
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(
    SCRIPT_DIR, "cc_character_integration_manifest_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_character_integration_automation_summary_v1.json"
)
REQUIRED_ARTIFACTS = (
    "reconstructed_preview",
    "face_front_preview",
    "face_three_quarter_preview",
    "face_profile_preview",
    "face_post_pose_neutral_preview",
    "hair_rear_three_quarter_preview",
    "hair_rear_preview",
    "face_blink_bilateral_preview",
    "face_blink_left_preview",
    "face_look_left_preview",
    "face_look_right_preview",
    "face_look_up_preview",
    "face_look_down_preview",
    "face_squint_preview",
    "face_widen_preview",
    "face_brow_raise_preview",
    "face_brow_down_preview",
    "face_smile_preview",
    "face_jaw_open_preview",
    "face_jaw_open_three_quarter_preview",
)
REQUIRED_POSE_IDS = (
    "blink_bilateral_front",
    "blink_left_front",
    "blink_right_front",
    "look_left_front",
    "look_right_front",
    "look_up_front",
    "look_down_front",
    "squint_bilateral_front",
    "widen_bilateral_front",
    "brow_raise_front",
    "brow_down_front",
    "brow_raise_left_front",
    "smile_front",
    "jaw_open_front",
    "jaw_open_three_quarter",
)
FACE_EVIDENCE_CAPTURE_STRATEGY = (
    "facial_profile_start_frame_snapshot_restore_v1"
)
FACE_POSE_CAPTURE_MODE = "render_image_start_frame_snapshot_restore_v1"
FACE_NEUTRAL_CAPTURE_MODE = (
    "render_image_same_scene_restored_neutral_v1"
)
FACE_EVIDENCE_MIN_RMSE = 0.35


class SummaryError(RuntimeError):
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
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        handle.write("\n")
    os.replace(temporary, path)


def discover_validation_results(artifact_root):
    paths = []
    for root, unused_directories, files in os.walk(artifact_root):
        if "validation_result.json" in files:
            paths.append(os.path.join(root, "validation_result.json"))
    return sorted(paths)


def resolve_result_paths(artifact_root, result_paths=None):
    if not result_paths:
        return discover_validation_results(artifact_root)
    resolved = []
    seen = set()
    for path in result_paths:
        canonical = os.path.realpath(os.path.abspath(path))
        if not os.path.isfile(canonical):
            raise SummaryError(
                "Explicit integration result is missing: {}".format(
                    canonical
                )
            )
        if canonical in seen:
            raise SummaryError(
                "Explicit integration result was repeated: {}".format(
                    canonical
                )
            )
        seen.add(canonical)
        resolved.append(canonical)
    return resolved


def load_case_results(result_path):
    document = read_json(result_path)
    if isinstance(document.get("results"), list):
        return document["results"]
    if isinstance(document.get("preset_id"), str):
        return [document]
    raise SummaryError(
        "Integration result has no case payload: {}".format(result_path)
    )


def complete_file(path):
    return (
        isinstance(path, str)
        and os.path.isfile(path)
        and os.path.getsize(path) > 0
    )


def close_number(actual, expected, tolerance=1.0e-5):
    try:
        return math.isclose(
            float(actual),
            float(expected),
            rel_tol=0.0,
            abs_tol=tolerance,
        )
    except (TypeError, ValueError):
        return False


def close_vector(actual, expected, tolerance=1.0e-5):
    if not isinstance(actual, list) or not isinstance(expected, list):
        return False
    return (
        len(actual) == len(expected)
        and all(
            close_number(left, right, tolerance)
            for left, right in zip(actual, expected)
        )
    )


def eye_integrity_pass(case_result):
    report = case_result.get("eye_integrity") or {}
    if report.get("identity_write_attempted") is not False:
        return False
    expected_weight = report.get("expected_weight")
    phases = report.get("phases") or {}
    required_phases = [
        "source_project",
        "after_body",
        "after_head_preset",
        "after_primary_support",
        "after_facial_profile",
        "after_face_identity",
    ]
    if case_result.get("bodyfit_proportion_adjustment") is not None:
        required_phases.append("after_bodyfit_proportion_adjustment")
    required_phases.extend(("after_facial_assembly", "final"))
    for phase_id in required_phases:
        phase = phases.get(phase_id) or {}
        eyeball_move = phase.get("eyeball_move") or {}
        look_at = phase.get("look_at") or {}
        if eyeball_move.get("available") is not True:
            return False
        if not close_number(eyeball_move.get("weight"), expected_weight):
            return False
        if look_at.get("valid") is not True:
            return False
        if phase.get("avatar_part_count") != 1:
            return False
        if len(phase.get("eye_bones") or []) != 2:
            return False
    post_comparison = (
        report.get("post_face_validation_comparison") or {}
    )
    refresh_attempts = (
        report.get("post_face_validation_refresh_attempts") or []
    )
    if post_comparison.get("matches") is not True:
        return False
    return (
        not refresh_attempts
        or refresh_attempts[-1].get("matches") is True
    )


def facial_profile_pass(case_result):
    application = (
        case_result.get("face_facial_profile_application") or {}
    )
    load_status = application.get("load_status") or {}
    artifacts = case_result.get("artifacts") or {}
    return (
        application.get("application_mode")
        == "selected_avatar_content_load"
        and isinstance(application.get("sha256"), str)
        and len(application["sha256"]) == 64
        and load_status.get("is_error") is False
        and case_result.get(
            "face_facial_profile_morphs_unchanged"
        )
        is True
        and case_result.get(
            "face_facial_profile_eye_structure_unchanged"
        )
        is True
        and complete_file(artifacts.get("facial_profile_vectors"))
    )


def bodyfit_proportion_pass(case_result, preset):
    expected = preset.get("bodyfit_proportion_adjustment")
    actual = case_result.get("bodyfit_proportion_adjustment")
    if expected is None:
        return actual is None
    if not isinstance(actual, dict):
        return False
    if (
        actual.get("canonical_order_verified") is not True
        or actual.get("protected_morphs_unchanged") is not True
        or actual.get("eye_structure_preserved") is not True
        or actual.get("targets_match") is not True
        or actual.get("decision_set_id")
        != expected.get("decision_set_id")
        or actual.get("application_order")
        != expected.get("application_order")
    ):
        return False
    expected_targets = expected.get("targets") or []
    applications = actual.get("applications") or []
    if len(applications) != len(expected_targets):
        return False
    for application, target in zip(applications, expected_targets):
        if (
            application.get("role") != target.get("role")
            or application.get("id") != target.get("id")
            or not close_number(
                application.get("target"),
                target.get("target"),
            )
            or not close_number(
                application.get("actual"),
                target.get("target"),
            )
        ):
            return False
    return complete_file(
        (case_result.get("artifacts") or {}).get(
            "bodyfit_proportion_adjustment"
        )
    )


def assembly_policy_pass(case_result, preset):
    assembly = case_result.get("facial_assembly") or {}
    if assembly.get("canonical_order_verified") is not True:
        return False
    expected_order = (preset.get("facial_assembly") or {}).get(
        "application_order"
    )
    if assembly.get("application_order") != expected_order:
        return False
    steps = assembly.get("asset_steps") or []
    expected_assets = set(
        (preset.get("facial_assembly") or {}).get("asset_ids") or []
    )
    actual_assets = {item.get("asset_id") for item in steps}
    if actual_assets != expected_assets:
        return False
    return all(
        (item.get("morph_policy") or {}).get("status") == "accepted"
        and (item.get("morph_policy") or {}).get(
            "protected_morphs_unchanged"
        )
        is True
        and (item.get("morph_policy") or {}).get(
            "disallowed_change_count"
        )
        == 0
        for item in steps
    )


def age_and_wrinkle_pass(case_result, preset):
    assembly = case_result.get("facial_assembly") or {}
    age = assembly.get("age_morph") or {}
    target_age = preset.get("full_face_elder_weight")
    if age.get("id") != (
        (preset.get("facial_assembly") or {}).get("age_morph_id")
    ):
        return False
    if not close_number(age.get("actual"), target_age):
        return False
    if not close_number(age.get("target"), target_age):
        return False
    wrinkle = assembly.get("dynamic_wrinkles") or {}
    expected_profile = (
        (preset.get("facial_assembly") or {})
        .get("dynamic_wrinkle_profile", {})
        .get("asset_id")
    )
    if wrinkle.get("profile_id") != expected_profile:
        return False
    if not close_number(
        wrinkle.get("strength"),
        preset.get("dynamic_wrinkle_strength"),
    ):
        return False
    strength_results = wrinkle.get("strength_results") or []
    return bool(strength_results) and all(
        (item.get("status") or {}).get("is_error") is False
        and (item.get("status") or {}).get("status_code") == "0"
        for item in strength_results
    )


def pigmentation_pass(case_result, preset):
    pigmentation = (
        (case_result.get("facial_assembly") or {}).get("pigmentation")
        or {}
    )
    required_domains = {"scalp_hair", "eyebrows"}
    if preset.get("facial_hair_asset_id"):
        required_domains.add("facial_hair")
    domain_counts = pigmentation.get("domain_material_counts") or {}
    if any(int(domain_counts.get(domain, 0)) < 1 for domain in required_domains):
        return False
    if not close_number(
        pigmentation.get("visible_gray_fraction"),
        preset.get("visible_gray_fraction"),
    ):
        return False
    targets = pigmentation.get("target_colors") or {}
    if not targets:
        return False
    materials = pigmentation.get("materials") or []
    if not materials:
        return False
    for material in materials:
        if material.get("domain") not in required_domains:
            continue
        after = material.get("after") or {}
        if any(
            not close_vector(after.get(parameter), value)
            for parameter, value in targets.items()
        ):
            return False
    return True


def pose_validation_pass(case_result):
    pose_report = case_result.get("facial_pose_validation") or {}
    if pose_report.get("profile") != "face_identity_safety_v1":
        return False

    timeline = pose_report.get("timeline") or {}
    baseline_clip_count = timeline.get("baseline_expression_clip_count")
    if (
        timeline.get("capture_strategy")
        != FACE_EVIDENCE_CAPTURE_STRATEGY
        or timeline.get("capture_frame") != 0
        or timeline.get("preserved_existing_expression_clips") is not True
        or timeline.get("removed_expression_clips") not in (None, [])
        or not isinstance(baseline_clip_count, int)
        or baseline_clip_count < 1
        or pose_report.get("final_expression_clip_count")
        != baseline_clip_count
    ):
        return False

    snapshot = pose_report.get("snapshot") or {}
    if not all(
        snapshot.get(field) is True
        for field in ("saved", "restored", "deleted")
    ):
        return False
    if snapshot.get("cleanup_error"):
        return False

    render_warmup = pose_report.get("render_warmup") or {}
    if render_warmup.get("deleted") is not True:
        return False

    poses = pose_report.get("poses") or []
    pose_ids = {item.get("pose_id") for item in poses}
    if not set(REQUIRED_POSE_IDS).issubset(pose_ids):
        return False
    if any(
        (item.get("capture") or {}).get("capture_mode")
        != FACE_POSE_CAPTURE_MODE
        for item in poses
    ):
        return False

    post_neutral = pose_report.get("post_pose_neutral_image")
    post_capture = pose_report.get("post_pose_neutral_capture") or {}
    if (
        post_capture.get("capture_mode") != FACE_NEUTRAL_CAPTURE_MODE
        or not complete_file(post_neutral)
    ):
        return False

    liveness = pose_report.get("evidence_liveness") or {}
    minimum_rmse = liveness.get("minimum_rmse")
    if (
        liveness.get("status") != "passed"
        or not isinstance(minimum_rmse, (int, float))
        or isinstance(minimum_rmse, bool)
        or not math.isfinite(minimum_rmse)
        or minimum_rmse < FACE_EVIDENCE_MIN_RMSE
        or not complete_file(liveness.get("reference_image"))
        or os.path.realpath(liveness.get("reference_image"))
        != os.path.realpath(post_neutral)
    ):
        return False

    required_liveness_ids = set(REQUIRED_POSE_IDS) - {
        "jaw_open_three_quarter"
    }
    liveness_by_pose = {
        item.get("pose_id"): item
        for item in (liveness.get("poses") or [])
    }
    if not required_liveness_ids.issubset(liveness_by_pose):
        return False
    for pose_id in required_liveness_ids:
        record = liveness_by_pose[pose_id]
        rmse = record.get("rmse")
        if (
            record.get("matches") is not True
            or not isinstance(rmse, (int, float))
            or isinstance(rmse, bool)
            or not math.isfinite(rmse)
            or rmse < minimum_rmse
        ):
            return False

    neutral_eye_integrity = (
        pose_report.get("neutral_eye_integrity") or {}
    )
    return (
        len(poses) >= 15
        and all(complete_file(item.get("image")) for item in poses)
        and neutral_eye_integrity.get("matches") is True
    )


def summarize_case(case_result, preset):
    artifacts = case_result.get("artifacts") or {}
    artifact_paths = {
        key: artifacts.get(key) for key in REQUIRED_ARTIFACTS
    }
    images_complete = all(
        complete_file(path) for path in artifact_paths.values()
    )
    checks = {
        "age_and_dynamic_wrinkles": age_and_wrinkle_pass(
            case_result, preset
        ),
        "appearance_matches_recipe": (
            case_result.get("appearance_matches_recipe") is True
        ),
        "appearance_morph_policy": (
            case_result.get("appearance_morphs_within_policy") is True
        ),
        "assembly_policy": assembly_policy_pass(case_result, preset),
        "body_unchanged_after_face": (
            case_result.get("body_unchanged_after_face") is True
        ),
        "bodyfit_proportion_adjustment": bodyfit_proportion_pass(
            case_result,
            preset,
        ),
        "case_success": case_result.get("success") is True,
        "eye_integrity": eye_integrity_pass(case_result),
        "eye_structure_preserved": (
            case_result.get("eye_structure_preserved_after_identity")
            is True
        ),
        "face_matches_recipe": (
            case_result.get("face_matches_recipe") is True
        ),
        "facial_profile": facial_profile_pass(case_result),
        "face_support_preserved_after_identity": (
            case_result.get("face_support_preserved_after_identity")
            is True
        ),
        "face_support_matches_primary_after_preset": (
            case_result.get(
                "face_support_matches_primary_after_preset"
            )
            is True
        ),
        "images_complete": images_complete,
        "junction_unchanged_after_face": (
            case_result.get("junction_unchanged_after_face") is True
        ),
        "other_unchanged": case_result.get("other_unchanged") is True,
        "pigmentation_shared": pigmentation_pass(case_result, preset),
        "pose_validation": pose_validation_pass(case_result),
        "reconstruction_matches_library": (
            case_result.get("reconstruction_matches_library") is True
        ),
    }
    structural_pass = all(checks.values())
    return {
        "age_label": preset.get("age_label"),
        "artifact_paths": artifact_paths,
        "bodyfit_id": preset.get("bodyfit_id"),
        "character_id": preset.get("character_id"),
        "face_recipe_id": preset.get("face_recipe_id"),
        "hair_presentation_mode": preset.get(
            "hair_presentation_mode"
        ),
        "preset_id": preset["preset_id"],
        "scalp_hair_asset_id": preset.get("scalp_hair_asset_id"),
        "scalp_hair_display_name": preset.get(
            "scalp_hair_display_name"
        ),
        "sex": preset.get("sex"),
        "skin_asset_id": preset.get("skin_asset_id"),
        "structural_checks": checks,
        "structural_pass": structural_pass,
        "automation_status": (
            "structural_pass_visual_pending"
            if structural_pass
            else "failed"
        ),
        "visual_review_status": "pending",
    }


def build_summary(
    artifact_root,
    batch_path=DEFAULT_BATCH,
    result_paths=None,
):
    artifact_root = os.path.realpath(os.path.abspath(artifact_root))
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    if not os.path.isdir(artifact_root):
        raise SummaryError(
            "Artifact root is missing: {}".format(artifact_root)
        )
    if not os.path.isfile(batch_path):
        raise SummaryError(
            "Integration manifest is missing: {}".format(batch_path)
        )
    batch = read_json(batch_path)
    presets = {
        item["preset_id"]: item for item in batch.get("presets") or []
    }
    cases = []
    seen = set()
    selected_result_paths = resolve_result_paths(
        artifact_root,
        result_paths,
    )
    for result_path in selected_result_paths:
        for case_result in load_case_results(result_path):
            preset_id = case_result.get("preset_id")
            if preset_id not in presets:
                raise SummaryError(
                    "Unknown integration preset result: {}".format(
                        preset_id
                    )
                )
            if preset_id in seen:
                raise SummaryError(
                    "Duplicate integration result: {}".format(preset_id)
                )
            seen.add(preset_id)
            cases.append(summarize_case(case_result, presets[preset_id]))
    cases.sort(key=lambda item: item["preset_id"])
    status_counts = {}
    for item in cases:
        status = item["automation_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    pending_ids = sorted(set(presets) - seen)
    return {
        "artifact_root": artifact_root,
        "batch_path": batch_path,
        "cases": cases,
        "completed_case_count": len(cases),
        "generated_at": now(),
        "pending_case_count": len(pending_ids),
        "pending_preset_ids": pending_ids,
        "selected_result_paths": selected_result_paths,
        "schema_version": 1,
        "status": (
            "automation-complete-visual-review-pending"
            if len(cases) == len(presets)
            else "automation-partial"
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "summary_id": "cc_character_integration_automation_v1",
        "total_case_count": len(presets),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Summarize CC5 canonical character integration."
    )
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--result",
        action="append",
        default=[],
        help=(
            "Use this exact per-case result.json or validation_result.json. "
            "Repeat for multiple results; otherwise the artifact root is "
            "searched recursively."
        ),
    )
    args = parser.parse_args()
    document = build_summary(
        args.artifact_root,
        args.batch,
        args.result or None,
    )
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output_path)
    print(
        "Summarized {}/{} integration cases -> {}".format(
            document["completed_case_count"],
            document["total_case_count"],
            output_path,
        )
    )


if __name__ == "__main__":
    main()
