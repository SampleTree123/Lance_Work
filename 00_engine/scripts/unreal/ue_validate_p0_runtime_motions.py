"""Validate and configure P0 UE animation semantics after import."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import unreal


IMPORT_REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\p0_runtime_pilot_20260819_v1\motion_import_report.json"
)
WORK_ORDER_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\animation_p0_ue_runtime_pilot\work_order_20260818_v1\work_order.json"
)
REPORT_PATH = IMPORT_REPORT_PATH.with_name("motion_runtime_validation.json")

LOOP_CASE_ID = "p0_004_legacy_stand_idle_f"
MAJOR_BONES = (
    "root",
    "pelvis",
    "spine_01",
    "spine_03",
    "head",
    "upperarm_l",
    "lowerarm_l",
    "hand_l",
    "upperarm_r",
    "lowerarm_r",
    "hand_r",
    "thigh_l",
    "calf_l",
    "foot_l",
    "thigh_r",
    "calf_r",
    "foot_r",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def vector_record(vector) -> dict:
    return {
        "x": float(vector.x),
        "y": float(vector.y),
        "z": float(vector.z),
    }


def vector_delta(a, b) -> tuple[float, float, float]:
    return float(b.x - a.x), float(b.y - a.y), float(b.z - a.z)


def distance(delta: tuple[float, float, float]) -> float:
    return math.sqrt(sum(value * value for value in delta))


def horizontal_distance(delta: tuple[float, float, float]) -> float:
    return math.sqrt(delta[0] * delta[0] + delta[1] * delta[1])


def quaternion_angle_degrees(a, b) -> float:
    dot = abs(float(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w))
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def pose(animation, bone_name: str, frame: int):
    return unreal.AnimationLibrary.get_bone_pose_for_frame(
        animation, unreal.Name(bone_name), frame, False
    )


def transform_delta_record(start, end) -> dict:
    translation_delta = vector_delta(start.translation, end.translation)
    return {
        "start_translation_cm": vector_record(start.translation),
        "end_translation_cm": vector_record(end.translation),
        "translation_delta_cm": {
            "x": translation_delta[0],
            "y": translation_delta[1],
            "z": translation_delta[2],
        },
        "translation_distance_cm": distance(translation_delta),
        "horizontal_displacement_cm": horizontal_distance(translation_delta),
        "rotation_delta_degrees": quaternion_angle_degrees(
            start.rotation, end.rotation
        ),
    }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(math.ceil(fraction * len(ordered))) - 1)
    return ordered[max(0, index)]


def endpoint_pose_metrics(animation, track_names: list[str], last_frame: int) -> dict:
    translation_deltas = []
    rotation_deltas = []
    per_bone = []
    for bone_name in track_names:
        metrics = transform_delta_record(
            pose(animation, bone_name, 0),
            pose(animation, bone_name, last_frame),
        )
        translation_deltas.append(metrics["translation_distance_cm"])
        rotation_deltas.append(metrics["rotation_delta_degrees"])
        per_bone.append(
            {
                "bone": bone_name,
                "translation_distance_cm": metrics["translation_distance_cm"],
                "rotation_delta_degrees": metrics["rotation_delta_degrees"],
            }
        )
    per_bone.sort(
        key=lambda item: (
            item["rotation_delta_degrees"],
            item["translation_distance_cm"],
        ),
        reverse=True,
    )
    return {
        "max_translation_distance_cm": max(translation_deltas, default=0.0),
        "p95_translation_distance_cm": percentile(translation_deltas, 0.95),
        "max_rotation_delta_degrees": max(rotation_deltas, default=0.0),
        "p95_rotation_delta_degrees": percentile(rotation_deltas, 0.95),
        "largest_endpoint_deltas": per_bone[:10],
    }


def ending_motion_metrics(animation, track_names: set[str], last_frame: int) -> dict:
    selected = [name for name in MAJOR_BONES if name in track_names]
    start_frame = max(0, last_frame - 5)
    translation_steps = []
    rotation_steps = []
    for frame in range(start_frame, last_frame):
        for bone_name in selected:
            metrics = transform_delta_record(
                pose(animation, bone_name, frame),
                pose(animation, bone_name, frame + 1),
            )
            translation_steps.append(metrics["translation_distance_cm"])
            rotation_steps.append(metrics["rotation_delta_degrees"])
    return {
        "window_start_frame": start_frame,
        "window_end_frame": last_frame,
        "sampled_bones": selected,
        "max_translation_step_cm": max(translation_steps, default=0.0),
        "mean_translation_step_cm": (
            sum(translation_steps) / len(translation_steps)
            if translation_steps
            else 0.0
        ),
        "max_rotation_step_degrees": max(rotation_steps, default=0.0),
        "mean_rotation_step_degrees": (
            sum(rotation_steps) / len(rotation_steps) if rotation_steps else 0.0
        ),
    }


def configure_root_motion(animation, policy: str) -> dict:
    moving = policy == "preserve_source_root_motion"
    animation.set_editor_property("enable_root_motion", moving)
    animation.set_editor_property("force_root_lock", not moving)
    animation.set_editor_property(
        "root_motion_root_lock", unreal.RootMotionRootLock.ANIM_FIRST_FRAME
    )
    animation.set_editor_property("use_normalized_root_motion_scale", False)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        animation, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save root-motion settings: {animation}")
    return {
        "enable_root_motion": bool(
            animation.get_editor_property("enable_root_motion")
        ),
        "force_root_lock": bool(animation.get_editor_property("force_root_lock")),
        "root_motion_root_lock": str(
            animation.get_editor_property("root_motion_root_lock")
        ),
        "use_normalized_root_motion_scale": bool(
            animation.get_editor_property("use_normalized_root_motion_scale")
        ),
    }


if not IMPORT_REPORT_PATH.is_file():
    raise FileNotFoundError(str(IMPORT_REPORT_PATH))
if not WORK_ORDER_PATH.is_file():
    raise FileNotFoundError(str(WORK_ORDER_PATH))

import_report = read_json(IMPORT_REPORT_PATH)
work_order = read_json(WORK_ORDER_PATH)
expected_by_case = {item["case_id"]: item for item in work_order["motions"]}

results = []
for imported in import_report["imports"]:
    case_id = imported["case_id"]
    expected = expected_by_case[case_id]
    animation = unreal.load_asset(imported["animation"]["path"])
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(f"Missing AnimSequence for {case_id}")

    model = animation.data_model_interface
    track_names = [str(name) for name in model.get_bone_track_names()]
    track_name_set = set(track_names)
    frame_count = int(model.get_number_of_frames())
    last_frame = frame_count - 1
    frame_rate = model.get_frame_rate()
    root_delta = transform_delta_record(
        pose(animation, "root", 0), pose(animation, "root", last_frame)
    )
    expected_horizontal = float(
        expected["root_motion"]["horizontal_displacement_cm"]
    )
    measured_horizontal = root_delta["horizontal_displacement_cm"]
    policy = expected["root_motion"]["policy"]
    if policy == "preserve_source_root_motion":
        root_policy_passed = (
            measured_horizontal >= 100.0
            and abs(measured_horizontal - expected_horizontal)
            <= max(0.5, expected_horizontal * 0.005)
        )
    else:
        root_policy_passed = measured_horizontal <= 0.1

    frame_count_passed = frame_count == imported["expected_source_frames"] + 1
    frame_rate_passed = (
        int(frame_rate.numerator) == 60 and int(frame_rate.denominator) == 1
    )
    temporal_usage = expected["temporal_usage"]
    endpoint_metrics = endpoint_pose_metrics(animation, track_names, last_frame)
    loop_validation = None
    if temporal_usage == "loop_candidate":
        loop_validation = {
            "thresholds": {
                "root_horizontal_displacement_cm_max": 0.1,
                "p95_translation_distance_cm_max": 0.5,
                "p95_rotation_delta_degrees_max": 3.0,
                "max_rotation_delta_degrees_max": 8.0,
            },
            "metrics": endpoint_metrics,
        }
        thresholds = loop_validation["thresholds"]
        loop_validation["passed"] = (
            measured_horizontal
            <= thresholds["root_horizontal_displacement_cm_max"]
            and endpoint_metrics["p95_translation_distance_cm"]
            <= thresholds["p95_translation_distance_cm_max"]
            and endpoint_metrics["p95_rotation_delta_degrees"]
            <= thresholds["p95_rotation_delta_degrees_max"]
            and endpoint_metrics["max_rotation_delta_degrees"]
            <= thresholds["max_rotation_delta_degrees_max"]
        )

    one_shot_completion = None
    if temporal_usage == "one_shot":
        one_shot_completion = {
            "passed": frame_count_passed and animation.get_play_length() > 0.0,
            "ending_motion_metrics": ending_motion_metrics(
                animation, track_name_set, last_frame
            ),
            "note": (
                "Ending velocity is recorded for diagnosis; one-shot locomotion "
                "is not required to settle to a neutral pose."
            ),
        }

    asset_settings = configure_root_motion(animation, policy)
    result_passed = (
        frame_count_passed
        and frame_rate_passed
        and root_policy_passed
        and (loop_validation is None or loop_validation["passed"])
        and (one_shot_completion is None or one_shot_completion["passed"])
    )
    results.append(
        {
            "case_id": case_id,
            "animation": animation.get_path_name(),
            "temporal_usage": temporal_usage,
            "root_motion_policy": policy,
            "frame_count": frame_count,
            "expected_last_frame": imported["expected_source_frames"],
            "frame_count_passed": frame_count_passed,
            "frame_rate": {
                "numerator": int(frame_rate.numerator),
                "denominator": int(frame_rate.denominator),
            },
            "frame_rate_passed": frame_rate_passed,
            "expected_horizontal_displacement_cm": expected_horizontal,
            "root_delta": root_delta,
            "root_policy_passed": root_policy_passed,
            "loop_validation": loop_validation,
            "one_shot_completion": one_shot_completion,
            "asset_settings": asset_settings,
            "passed": result_passed,
        }
    )

report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "import_report_path": str(IMPORT_REPORT_PATH),
    "work_order_path": str(WORK_ORDER_PATH),
    "results": results,
    "case_count": len(results),
    "success": len(results) == 4 and all(item["passed"] for item in results),
    "production_status": "not_approved",
}
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
    encoding="utf-8",
)
if not report["success"]:
    raise RuntimeError(f"P0 motion runtime validation failed: {REPORT_PATH}")
unreal.log(f"DataMake P0 motion runtime validation passed: {REPORT_PATH}")
print("DM_P0_MOTION_RUNTIME=" + json.dumps(report, ensure_ascii=False))
