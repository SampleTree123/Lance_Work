"""Build or audit body animations with first-batch expression curves embedded."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work")
WINDOWS_PATH = (
    ROOT
    / "00_engine"
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_window_selection"
    / "frozen_20260821_v4"
    / "frozen_action_windows.json"
)
ACTION_POOL_PATH = (
    ROOT
    / "00_engine"
    / "scripts"
    / "character_creator"
    / "cc_first_batch_action_pool_20260824_v1.json"
)
MOTION_GATE_PATH = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_motions_20260822_v1"
    / "aggregate_motion_import_gate.json"
)
PROFILE_PATH = (
    ROOT
    / "00_engine"
    / "scripts"
    / "unreal"
    / "first_batch_expression_profile_20260820_v1.json"
)
ACTION_ID = str(globals().get("DM_ACTION_ID", "ACT_F02_CATCH_BREATH"))
REPLACE_OUTPUT = bool(globals().get("DM_REPLACE_OUTPUT", False))
PRINT_REPORT = bool(globals().get("DM_PRINT_REPORT", True))
F02_INPLACE_ASSET = (
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/InPlaceCandidates/"
    "A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001"
)
REPORT_ROOT = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day3_20260823_v1"
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def find_action(records: list[dict], action_id: str) -> dict:
    matches = [record for record in records if record.get("action_id") == action_id]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one action record for {action_id}, found {len(matches)}"
        )
    return matches[0]


def load_anim(path: str) -> unreal.AnimSequence:
    asset = unreal.load_asset(path)
    if not isinstance(asset, unreal.AnimSequence):
        raise RuntimeError(f"Missing AnimSequence: {path}")
    return asset


def curve_names(asset: unreal.AnimSequence) -> list[str]:
    return sorted(
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            asset, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    )


def interpolate_pattern(pattern: dict, time_seconds: float) -> float:
    times = [float(value) for value in pattern["times"]]
    values = [float(value) for value in pattern["values"]]
    if time_seconds <= times[0]:
        return values[0]
    if time_seconds >= times[-1]:
        return values[-1]
    for index in range(1, len(times)):
        if time_seconds <= times[index]:
            left_time = times[index - 1]
            right_time = times[index]
            alpha = (time_seconds - left_time) / (right_time - left_time)
            return values[index - 1] + alpha * (values[index] - values[index - 1])
    return values[-1]


def repeated_sparse_keys(
    pattern: dict, pattern_duration: float, target_duration: float
) -> tuple[list[float], list[float]]:
    keys: dict[float, float] = {}
    cycle_count = int(math.ceil(target_duration / pattern_duration)) + 1
    for cycle in range(cycle_count):
        offset = cycle * pattern_duration
        for source_time, value in zip(pattern["times"], pattern["values"]):
            absolute_time = offset + float(source_time)
            if absolute_time > target_duration + 1.0e-6:
                continue
            keys[round(absolute_time, 6)] = float(value)
    end_phase = math.fmod(target_duration, pattern_duration)
    keys[round(target_duration, 6)] = interpolate_pattern(pattern, end_phase)
    ordered = sorted(keys.items())
    return [item[0] for item in ordered], [item[1] for item in ordered]


def scaled_expression_curves(profile: dict, spec: dict) -> dict:
    multiplier = float(profile.get("expression_strength_multiplier", 1.0))
    return {
        name: {
            "times": list(pattern["times"]),
            "values": [
                min(1.0, max(0.0, float(value) * multiplier))
                for value in pattern["values"]
            ],
        }
        for name, pattern in spec["curves"].items()
    }


windows = read_json(WINDOWS_PATH)
action_pool = read_json(ACTION_POOL_PATH)
motion_gate = read_json(MOTION_GATE_PATH)
profile = read_json(PROFILE_PATH)
if profile.get("status") != "frozen_for_ue_pilot":
    raise RuntimeError("Expression profile is not frozen")

active_action_ids = {
    action_id
    for sex in ("female", "male")
    for action_id in action_pool["active_actions"][sex]
}
if ACTION_ID not in active_action_ids:
    raise RuntimeError(f"Action is not active in the frozen production pool: {ACTION_ID}")

window_record = find_action(windows["actions"], ACTION_ID)
motion_record = find_action(motion_gate["records"], ACTION_ID)
sex = str(window_record["sex"]).lower()
if sex not in {"female", "male"}:
    raise RuntimeError(f"Unsupported action sex: {sex}")

if ACTION_ID == "ACT_F02_CATCH_BREATH":
    body_path = F02_INPLACE_ASSET
    body_policy = "approved_inplace_override"
elif float(window_record["window"]["padding_required_seconds"]) > 1.0e-6:
    slug = ACTION_ID.removeprefix("ACT_")
    sex_folder = "Female" if sex == "female" else "Male"
    body_path = (
        f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
        f"IdlePadded/A_DM_{slug}_IdlePadded5s_v001"
    )
    body_policy = "symmetric_exact_endpoint_holds_v1"
else:
    body_path = motion_record["body_only_animation"]["asset"]
    body_policy = "approved_original_body_only"
body = load_anim(body_path)
if curve_names(body):
    raise RuntimeError(f"Body source unexpectedly contains curves: {body_path}")

body_model = body.data_model_interface
body_skeleton = body.get_skeleton()
body_duration = float(body.get_play_length())
body_tracks = [str(name) for name in body_model.get_bone_track_names()]
body_rate = body_model.get_frame_rate()
body_frames_value = body_model.get_number_of_frames()
body_frames = int(getattr(body_frames_value, "value", body_frames_value))

slug = ACTION_ID.removeprefix("ACT_")
actor_id = slug.split("_", 1)[0]
sex_folder = "Female" if sex == "female" else "Male"
target_root = (
    f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
    f"Composites/{actor_id}"
)
pattern_duration = float(profile["duration_seconds"])
expression_specs = {item["expression_id"]: item for item in profile["expressions"]}
results = []

for expression_id in ("happy", "angry", "sad"):
    spec = expression_specs[expression_id]
    curves = dict(profile["common_curves"])
    overlap = set(curves).intersection(spec["curves"])
    if overlap:
        raise RuntimeError(f"Expression overrides common curves: {sorted(overlap)}")
    curves.update(scaled_expression_curves(profile, spec))
    title = expression_id.title()
    target_path = f"{target_root}/A_DM_{slug}_{title}_Composite_v001"
    existed = unreal.EditorAssetLibrary.does_asset_exist(target_path)
    if existed and REPLACE_OUTPUT:
        if not unreal.EditorAssetLibrary.delete_asset(target_path):
            raise RuntimeError(f"Unable to replace composite: {target_path}")
        existed = False

    if existed:
        target = load_anim(target_path)
        operation = "audited_existing"
    else:
        target = unreal.EditorAssetLibrary.duplicate_asset(body_path, target_path)
        if not isinstance(target, unreal.AnimSequence):
            raise RuntimeError(f"Unable to duplicate body animation: {target_path}")
        unreal.AnimationLibrary.remove_all_curve_data(target)
        for name, pattern in curves.items():
            times, values = repeated_sparse_keys(
                pattern, pattern_duration, body_duration
            )
            curve = unreal.Name(name)
            unreal.AnimationLibrary.add_curve(
                target, curve, unreal.RawCurveTrackTypes.RCT_FLOAT, False
            )
            unreal.AnimationLibrary.add_float_curve_keys(target, curve, times, values)
            unreal.AnimationLibrary.set_curve_meta_data_morph_target(
                body_skeleton, curve, True
            )
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            target, only_if_is_dirty=False
        ):
            raise RuntimeError(f"Unable to save composite: {target_path}")
        operation = "created_sparse"

    target_model = target.data_model_interface
    target_tracks = [str(name) for name in target_model.get_bone_track_names()]
    target_curves = curve_names(target)
    target_rate = target_model.get_frame_rate()
    target_frames_value = target_model.get_number_of_frames()
    target_frames = int(
        getattr(target_frames_value, "value", target_frames_value)
    )
    errors = []
    if target.get_skeleton() != body_skeleton:
        errors.append("skeleton_changed")
    if target_tracks != body_tracks:
        errors.append("bone_tracks_changed")
    if target_curves != sorted(curves):
        errors.append("curve_set_mismatch")
    if abs(float(target.get_play_length()) - body_duration) > 1.0e-4:
        errors.append("duration_changed")
    if target_frames != body_frames:
        errors.append("frame_count_changed")
    if (
        target_rate.numerator != body_rate.numerator
        or target_rate.denominator != body_rate.denominator
    ):
        errors.append("frame_rate_changed")
    if errors:
        raise RuntimeError(
            f"Composite verification failed for {expression_id}: {errors}"
        )
    results.append(
        {
            "expression_id": expression_id,
            "asset": target.get_path_name(),
            "operation": operation,
            "bone_track_count": len(target_tracks),
            "curve_count": len(target_curves),
            "curve_names": target_curves,
            "frame_count": target_frames,
            "duration_seconds": float(target.get_play_length()),
        }
    )

report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed",
    "action_id": ACTION_ID,
    "sex": sex,
    "body_source": body.get_path_name(),
    "body_policy": body_policy,
    "expression_strength_multiplier": profile.get(
        "expression_strength_multiplier", 1.0
    ),
    "skeleton": body_skeleton.get_path_name(),
    "frame_rate": {
        "numerator": body_rate.numerator,
        "denominator": body_rate.denominator,
    },
    "frame_count": body_frames,
    "duration_seconds": body_duration,
    "bone_track_count": len(body_tracks),
    "target_root": target_root,
    "composites": results,
}
REPORT_ROOT.mkdir(parents=True, exist_ok=True)
report_path = REPORT_ROOT / f"action_expression_composites_{ACTION_ID.lower()}.json"
report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
if PRINT_REPORT:
    print("DM_ACTION_EXPRESSION_COMPOSITES=" + json.dumps(report, ensure_ascii=False))
