"""Build the first M02 face-only hybrid bone-and-curve animation clip."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


SOURCE_ANIMATION = (
    "/Game/Vendor/Reallusion/CC5/Animations/Pilot/"
    "A_CC_Audience_F_01_Pilot"
)
TARGET_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_HybridSupport_Loop_v001"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_face_hybrid_clip_v001_build.json"
)

SUPPORT_BONES = (
    "cc_base_facialbone",
    "cc_base_jawroot",
    "cc_base_upperjaw",
    "cc_base_teeth01",
    "cc_base_teeth02",
    "cc_base_tongue01",
    "cc_base_tongue02",
    "cc_base_tongue03",
)
ANIMATED_BONES = {
    "cc_base_jawroot": {"axis": "local_y", "degrees": 18.0},
    "cc_base_tongue02": {"axis": "local_y", "degrees": -4.0},
}

BLINK_L = "CTRL_expressions_eyeBlinkL"
BLINK_R = "CTRL_expressions_eyeBlinkR"
JAW_OPEN = "CTRL_expressions_jawOpen"
LOWER_LIP_L = "CTRL_expressions_mouthLowerLipDepressL"
LOWER_LIP_R = "CTRL_expressions_mouthLowerLipDepressR"
UPPER_LIP_L = "CTRL_expressions_mouthUpperLipRaiseL"
UPPER_LIP_R = "CTRL_expressions_mouthUpperLipRaiseR"
SMILE_L = "CTRL_expressions_mouthCornerPullL"
SMILE_R = "CTRL_expressions_mouthCornerPullR"
LOOK_RIGHT_L = "CTRL_expressions_eyeLookRightL"
LOOK_RIGHT_R = "CTRL_expressions_eyeLookRightR"


def smoothstep(edge0, edge1, value):
    if edge0 == edge1:
        return 1.0 if value >= edge1 else 0.0
    alpha = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return alpha * alpha * (3.0 - 2.0 * alpha)


def jaw_alpha(time_seconds):
    return smoothstep(0.55, 1.15, time_seconds) * (
        1.0 - smoothstep(2.75, 3.35, time_seconds)
    )


def make_delta_quat(x=0.0, y=0.0, z=0.0):
    result = unreal.Quat()
    result.set_from_euler(unreal.Vector(x, y, z))
    return result


def compose_rotation(base, x=0.0, y=0.0, z=0.0):
    return base.multiply(make_delta_quat(x, y, z)).normalized()


def copy_vector(value):
    return unreal.Vector(value.x, value.y, value.z)


def transform_record(value):
    euler = value.rotation.euler()
    return {
        "translation": {
            "x": value.translation.x,
            "y": value.translation.y,
            "z": value.translation.z,
        },
        "rotation_euler": {"x": euler.x, "y": euler.y, "z": euler.z},
        "scale": {"x": value.scale3d.x, "y": value.scale3d.y, "z": value.scale3d.z},
    }


source = unreal.load_asset(SOURCE_ANIMATION)
if not isinstance(source, unreal.AnimSequence):
    raise RuntimeError(f"Source animation unavailable: {SOURCE_ANIMATION}")

target = unreal.load_asset(TARGET_ANIMATION)
created = False
if target is None:
    target = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_ANIMATION, TARGET_ANIMATION
    )
    created = True
if not isinstance(target, unreal.AnimSequence):
    raise RuntimeError(f"Unable to create hybrid clip: {TARGET_ANIMATION}")

skeleton = target.get_editor_property("skeleton")
if skeleton is None:
    raise RuntimeError("Hybrid clip has no Skeleton")

controller = target.controller
model = target.data_model_interface
if controller is None or model is None:
    raise RuntimeError("Hybrid clip model/controller unavailable")

source_tracks = {str(name) for name in source.data_model_interface.get_bone_track_names()}
missing_source_tracks = sorted(set(SUPPORT_BONES) - source_tracks)
if missing_source_tracks:
    raise RuntimeError("Source is missing support tracks: " + ", ".join(missing_source_tracks))

frame_count = int(model.get_number_of_frames())
frame_rate = model.get_frame_rate()
fps = float(frame_rate.numerator) / float(frame_rate.denominator)
key_count = frame_count + 1
play_length = target.get_play_length()

target_tracks = {str(name) for name in model.get_bone_track_names()}
controller.open_bracket("Build M02 hybrid facial support clip", False)
try:
    for track_name in sorted(target_tracks - set(SUPPORT_BONES)):
        if not controller.remove_bone_track(unreal.Name(track_name), False):
            raise RuntimeError(f"Unable to remove non-facial track: {track_name}")
    remaining_tracks = {str(name) for name in model.get_bone_track_names()}
    for bone in SUPPORT_BONES:
        if bone not in remaining_tracks:
            controller.add_bone_track(unreal.Name(bone), False)

    for bone in SUPPORT_BONES:
        neutral = unreal.AnimationLibrary.get_bone_pose_for_frame(
            source, unreal.Name(bone), 0, False
        )
        positions = []
        rotations = []
        scales = []
        for frame in range(key_count):
            time_seconds = min(play_length, frame / fps)
            jaw = jaw_alpha(time_seconds)
            x = y = z = 0.0
            if bone == "cc_base_jawroot":
                y = ANIMATED_BONES[bone]["degrees"] * jaw
            elif bone == "cc_base_tongue02":
                y = ANIMATED_BONES[bone]["degrees"] * jaw
            positions.append(copy_vector(neutral.translation))
            rotations.append(compose_rotation(neutral.rotation, x, y, z))
            scales.append(copy_vector(neutral.scale3d))
        if not controller.set_bone_track_keys(
            unreal.Name(bone), positions, rotations, scales, False
        ):
            raise RuntimeError(f"Unable to set keys for support track: {bone}")
    controller.remove_all_attributes(False)
finally:
    controller.close_bracket(False)

unreal.AnimationLibrary.remove_all_curve_data(target)
curve_keys = {
    BLINK_L: (
        [0.0, 0.72, 0.80, 0.88, 0.96, 3.55, 3.63, 3.71, 3.79, play_length],
        [0.0, 0.0, 0.55, 1.0, 0.0, 0.0, 0.50, 1.0, 0.0, 0.0],
    ),
    BLINK_R: (
        [0.0, 0.72, 0.80, 0.88, 0.96, 3.55, 3.63, 3.71, 3.79, play_length],
        [0.0, 0.0, 0.55, 1.0, 0.0, 0.0, 0.50, 1.0, 0.0, 0.0],
    ),
    JAW_OPEN: (
        [0.0, 0.55, 1.15, 2.75, 3.35, play_length],
        [0.0, 0.0, 0.58, 0.58, 0.0, 0.0],
    ),
    LOWER_LIP_L: (
        [0.0, 0.55, 1.15, 2.75, 3.35, play_length],
        [0.0, 0.0, 0.16, 0.16, 0.0, 0.0],
    ),
    LOWER_LIP_R: (
        [0.0, 0.55, 1.15, 2.75, 3.35, play_length],
        [0.0, 0.0, 0.16, 0.16, 0.0, 0.0],
    ),
    UPPER_LIP_L: (
        [0.0, 0.55, 1.15, 2.75, 3.35, play_length],
        [0.0, 0.0, 0.08, 0.08, 0.0, 0.0],
    ),
    UPPER_LIP_R: (
        [0.0, 0.55, 1.15, 2.75, 3.35, play_length],
        [0.0, 0.0, 0.08, 0.08, 0.0, 0.0],
    ),
    SMILE_L: (
        [0.0, 0.55, 1.15, 2.75, 3.35, play_length],
        [0.0, 0.0, 0.14, 0.14, 0.0, 0.0],
    ),
    SMILE_R: (
        [0.0, 0.55, 1.15, 2.75, 3.35, play_length],
        [0.0, 0.0, 0.13, 0.13, 0.0, 0.0],
    ),
    LOOK_RIGHT_L: (
        [0.0, 2.75, 3.15, 3.40, 3.75, 4.15, play_length],
        [0.0, 0.0, 0.45, 0.70, 0.70, 0.0, 0.0],
    ),
    LOOK_RIGHT_R: (
        [0.0, 2.75, 3.15, 3.40, 3.75, 4.15, play_length],
        [0.0, 0.0, 0.45, 0.70, 0.70, 0.0, 0.0],
    ),
}
for curve_name, (times, values) in curve_keys.items():
    curve = unreal.Name(curve_name)
    unreal.AnimationLibrary.add_curve(
        target, curve, unreal.RawCurveTrackTypes.RCT_FLOAT, False
    )
    unreal.AnimationLibrary.add_float_curve_keys(target, curve, times, values)
    unreal.AnimationLibrary.set_curve_meta_data_morph_target(skeleton, curve, True)

target.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_NONE)
unreal.AnimationLibrary.finalize_bone_animation(target)
if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save hybrid clip: {TARGET_ANIMATION}")
unreal.EditorAssetLibrary.save_loaded_asset(skeleton, only_if_is_dirty=False)

tracks_after = {str(name) for name in model.get_bone_track_names()}
curves_after = {
    str(name)
    for name in unreal.AnimationLibrary.get_animation_curve_names(
        target, unreal.RawCurveTrackTypes.RCT_FLOAT
    )
}
sample_frames = {
    "neutral": 0,
    "blink_peak": int(round(0.88 * fps)),
    "jaw_plateau": int(round(1.70 * fps)),
    "gaze_opposite": int(round(play_length * 0.75 * fps)),
}
samples = {}
for sample_id, frame in sample_frames.items():
    samples[sample_id] = {
        bone: transform_record(
            unreal.AnimationLibrary.get_bone_pose_for_frame(
                target, unreal.Name(bone), min(frame, frame_count), False
            )
        )
        for bone in ANIMATED_BONES
    }

required_curves = set(curve_keys)
success = (
    tracks_after == set(SUPPORT_BONES)
    and required_curves.issubset(curves_after)
    and "head" not in tracks_after
    and "neck_01" not in tracks_after
    and "neck_02" not in tracks_after
)
report = {
    "schema_version": 1,
    "library_role": "face_only_hybrid_bones_and_curves",
    "source_animation": source.get_path_name(),
    "target_animation": target.get_path_name(),
    "created": created,
    "skeleton": skeleton.get_path_name(),
    "play_length_seconds": play_length,
    "frame_count": frame_count,
    "key_count": key_count,
    "support_bones": list(SUPPORT_BONES),
    "animated_bones": ANIMATED_BONES,
    "eye_drive": {
        "mode": "rig_logic_curves",
        "curves": [LOOK_RIGHT_L, LOOK_RIGHT_R],
        "reason": "CC post-process Rig Logic owns the final eye-bone pose",
    },
    "tracks_after": sorted(tracks_after),
    "curve_keys": {
        name: {"times": times, "values": values}
        for name, (times, values) in curve_keys.items()
    },
    "curves_after": sorted(curves_after),
    "sample_frames": sample_frames,
    "samples": samples,
    "head_and_neck_excluded": not any(
        name in tracks_after for name in {"head", "neck_01", "neck_02"}
    ),
    "success": success,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
if not success:
    raise RuntimeError("Hybrid face clip verification failed")
print(
    "DM_FACE_HYBRID_CLIP="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "asset": target.get_path_name(),
            "track_count": len(tracks_after),
            "curve_count": len(required_curves),
            "success": success,
        },
        sort_keys=True,
    )
)
