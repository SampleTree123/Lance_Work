"""Build exact 5-second first-batch clips by holding endpoint poses.

This script runs inside Unreal Editor. It never resamples the source motion:
all source bone keys are copied verbatim and the missing frames are split
between a leading hold and a trailing hold.
"""

from __future__ import annotations

import json
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
REPORT_PATH = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day3_20260823_v1"
    / "idle_padding_build.json"
)
TARGET_SECONDS = 5.0
REPLACE_OUTPUT = bool(globals().get("DM_REPLACE_OUTPUT", False))
AUDIT_BONES = ("root", "pelvis", "spine_03", "hand_l", "hand_r", "head")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def copy_vector(value) -> unreal.Vector:
    return unreal.Vector(float(value.x), float(value.y), float(value.z))


def copy_quat(value) -> unreal.Quat:
    return unreal.Quat(
        float(value.x), float(value.y), float(value.z), float(value.w)
    )


def vector_error(left, right) -> float:
    return float((left - right).length())


def quat_error(left, right) -> float:
    dot = (
        float(left.x) * float(right.x)
        + float(left.y) * float(right.y)
        + float(left.z) * float(right.z)
        + float(left.w) * float(right.w)
    )
    return 1.0 - abs(dot)


def target_path(action: dict) -> str:
    sex_folder = "Female" if action["sex"] == "female" else "Male"
    slug = action["action_id"].removeprefix("ACT_")
    return (
        f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
        f"IdlePadded/A_DM_{slug}_IdlePadded5s_v001"
    )


def load_anim(path: str) -> unreal.AnimSequence:
    asset = unreal.load_asset(path)
    if not isinstance(asset, unreal.AnimSequence):
        raise RuntimeError(f"Missing AnimSequence: {path}")
    return asset


def sample_track(
    animation: unreal.AnimSequence, bone: str, frame_count: int
) -> tuple[list[unreal.Vector], list[unreal.Quat], list[unreal.Vector]]:
    positions = []
    rotations = []
    scales = []
    for frame in range(frame_count + 1):
        pose = unreal.AnimationLibrary.get_bone_pose_for_frame(
            animation, unreal.Name(bone), frame, False
        )
        positions.append(copy_vector(pose.translation))
        rotations.append(copy_quat(pose.rotation))
        scales.append(copy_vector(pose.scale3d))
    return positions, rotations, scales


def audit_pose(
    source: unreal.AnimSequence,
    target: unreal.AnimSequence,
    bone: str,
    source_frame: int,
    target_frame: int,
    sample: str,
) -> dict:
    expected = unreal.AnimationLibrary.get_bone_pose_for_frame(
        source, unreal.Name(bone), source_frame, False
    )
    observed = unreal.AnimationLibrary.get_bone_pose_for_frame(
        target, unreal.Name(bone), target_frame, False
    )
    return {
        "bone": bone,
        "sample": sample,
        "source_frame": source_frame,
        "target_frame": target_frame,
        "translation_error": vector_error(
            expected.translation, observed.translation
        ),
        "rotation_error": quat_error(expected.rotation, observed.rotation),
        "scale_error": vector_error(expected.scale3d, observed.scale3d),
    }


def build(action: dict, motion: dict) -> dict:
    source_path = motion["body_only_animation"]["asset"]
    source = load_anim(source_path)
    source_model = source.data_model_interface
    source_controller = source.controller
    if source_model is None or source_controller is None:
        raise RuntimeError(f"Animation model/controller unavailable: {source_path}")

    rate = source_model.get_frame_rate()
    fps = float(rate.numerator) / float(rate.denominator)
    if abs(fps - 30.0) > 1.0e-6:
        raise RuntimeError(f"Expected 30 fps source, got {fps}: {source_path}")
    source_frames = int(source_model.get_number_of_frames())
    target_frames = int(round(TARGET_SECONDS * fps))
    padding_frames = target_frames - source_frames
    if padding_frames <= 0:
        raise RuntimeError(f"Source does not need padding: {source_path}")
    before_frames = padding_frames // 2
    after_frames = padding_frames - before_frames
    source_tracks = [str(name) for name in source_model.get_bone_track_names()]
    if not source_tracks:
        raise RuntimeError(f"Source has no bone tracks: {source_path}")

    sampled = {
        bone: sample_track(source, bone, source_frames) for bone in source_tracks
    }
    destination = target_path(action)
    existed = unreal.EditorAssetLibrary.does_asset_exist(destination)
    if existed and REPLACE_OUTPUT:
        if not unreal.EditorAssetLibrary.delete_asset(destination):
            raise RuntimeError(f"Unable to replace padded asset: {destination}")
        existed = False

    if existed:
        target = load_anim(destination)
        operation = "audited_existing"
    else:
        target = unreal.EditorAssetLibrary.duplicate_asset(source_path, destination)
        if not isinstance(target, unreal.AnimSequence):
            raise RuntimeError(f"Unable to duplicate source: {destination}")
        controller = target.controller
        if controller is None:
            raise RuntimeError(f"Target controller unavailable: {destination}")
        controller.open_bracket("Build symmetric endpoint-hold padding", False)
        try:
            controller.set_number_of_frames(unreal.FrameNumber(target_frames), False)
            for bone in source_tracks:
                positions, rotations, scales = sampled[bone]
                expanded_positions = (
                    [copy_vector(positions[0]) for _ in range(before_frames)]
                    + positions
                    + [copy_vector(positions[-1]) for _ in range(after_frames)]
                )
                expanded_rotations = (
                    [copy_quat(rotations[0]) for _ in range(before_frames)]
                    + rotations
                    + [copy_quat(rotations[-1]) for _ in range(after_frames)]
                )
                expanded_scales = (
                    [copy_vector(scales[0]) for _ in range(before_frames)]
                    + scales
                    + [copy_vector(scales[-1]) for _ in range(after_frames)]
                )
                if len(expanded_positions) != target_frames + 1:
                    raise RuntimeError(
                        f"Expanded key count mismatch for {bone}: "
                        f"{len(expanded_positions)} != {target_frames + 1}"
                    )
                if not controller.set_bone_track_keys(
                    unreal.Name(bone),
                    expanded_positions,
                    expanded_rotations,
                    expanded_scales,
                    False,
                ):
                    raise RuntimeError(f"Unable to write track {bone}: {destination}")
            controller.remove_all_attributes(False)
        finally:
            controller.close_bracket(False)
        unreal.AnimationLibrary.remove_all_curve_data(target)
        target.set_editor_property("enable_root_motion", False)
        target.set_editor_property("force_root_lock", True)
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            target, only_if_is_dirty=False
        ):
            raise RuntimeError(f"Unable to save padded asset: {destination}")
        operation = "created_exact_endpoint_holds"

    target_model = target.data_model_interface
    target_rate = target_model.get_frame_rate()
    target_tracks = [str(name) for name in target_model.get_bone_track_names()]
    errors = []
    if target.get_skeleton() != source.get_skeleton():
        errors.append("skeleton_changed")
    if target_tracks != source_tracks:
        errors.append("bone_tracks_changed")
    if int(target_model.get_number_of_frames()) != target_frames:
        errors.append("frame_count_mismatch")
    if (
        target_rate.numerator != rate.numerator
        or target_rate.denominator != rate.denominator
    ):
        errors.append("frame_rate_changed")
    if abs(float(target.get_play_length()) - TARGET_SECONDS) > 1.0 / fps:
        errors.append("duration_mismatch")

    checks = []
    source_middle = source_frames // 2
    for bone in AUDIT_BONES:
        if bone not in source_tracks:
            errors.append(f"missing_audit_bone:{bone}")
            continue
        checks.extend(
            (
                audit_pose(source, target, bone, 0, 0, "leading_hold"),
                audit_pose(
                    source, target, bone, 0, before_frames, "source_start"
                ),
                audit_pose(
                    source,
                    target,
                    bone,
                    source_middle,
                    before_frames + source_middle,
                    "source_middle",
                ),
                audit_pose(
                    source,
                    target,
                    bone,
                    source_frames,
                    before_frames + source_frames,
                    "source_end",
                ),
                audit_pose(
                    source,
                    target,
                    bone,
                    source_frames,
                    target_frames,
                    "trailing_hold",
                ),
            )
        )
    maximum_translation = max(item["translation_error"] for item in checks)
    maximum_rotation = max(item["rotation_error"] for item in checks)
    maximum_scale = max(item["scale_error"] for item in checks)
    if maximum_translation > 1.0e-3:
        errors.append("pose_translation_changed")
    if maximum_rotation > 1.0e-5:
        errors.append("pose_rotation_changed")
    if maximum_scale > 1.0e-5:
        errors.append("pose_scale_changed")
    if errors:
        raise RuntimeError(
            f"Idle-padding verification failed for {action['action_id']}: {errors}"
        )

    return {
        "action_id": action["action_id"],
        "sex": action["sex"],
        "source_asset": source.get_path_name(),
        "target_asset": target.get_path_name(),
        "operation": operation,
        "policy": "symmetric_exact_endpoint_holds_v1",
        "fps": fps,
        "source_frames": source_frames,
        "target_frames": target_frames,
        "before_hold_frames": before_frames,
        "after_hold_frames": after_frames,
        "before_hold_seconds": before_frames / fps,
        "after_hold_seconds": after_frames / fps,
        "bone_track_count": len(target_tracks),
        "maximum_translation_error": maximum_translation,
        "maximum_rotation_error": maximum_rotation,
        "maximum_scale_error": maximum_scale,
        "passed": True,
    }


windows = read_json(WINDOWS_PATH)
action_pool = read_json(ACTION_POOL_PATH)
motion_gate = read_json(MOTION_GATE_PATH)
motions = {item["action_id"]: item for item in motion_gate["records"]}
active_action_ids = {
    action_id
    for sex in ("female", "male")
    for action_id in action_pool["active_actions"][sex]
}
short_actions = [
    item
    for item in windows["actions"]
    if item["action_id"] in active_action_ids
    and float(item["window"]["padding_required_seconds"]) > 1.0e-6
]
if len(short_actions) != 2:
    raise RuntimeError(f"Expected two active short actions, found {len(short_actions)}")
missing = sorted(item["action_id"] for item in short_actions if item["action_id"] not in motions)
if missing:
    raise RuntimeError("Missing motion records: " + ", ".join(missing))

records = [build(item, motions[item["action_id"]]) for item in short_actions]
report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed" if all(item["passed"] for item in records) else "failed",
    "target_seconds": TARGET_SECONDS,
    "policy": "symmetric_exact_endpoint_holds_v1",
    "record_count": len(records),
    "records": records,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("DM_IDLE_PADDING_BUILD=" + json.dumps(report, ensure_ascii=False))
