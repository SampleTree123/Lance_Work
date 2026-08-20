"""Build a CC body-motion clip with embedded facial Morph curves."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


SOURCE_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "A_CC_Audience_F_01_BodyOnly_v001"
)
TARGET_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "A_CC_Audience_F_01_BodyFaceDemo_v001"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_body_face_animation_build.json"
)


source = unreal.load_asset(SOURCE_ANIMATION)
if not isinstance(source, unreal.AnimSequence):
    raise RuntimeError(f"Source animation is unavailable: {SOURCE_ANIMATION}")

target = unreal.load_asset(TARGET_ANIMATION)
created_target = False
if target is None:
    target = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_ANIMATION, TARGET_ANIMATION
    )
    created_target = True
if not isinstance(target, unreal.AnimSequence):
    raise RuntimeError(f"Unable to create target animation: {TARGET_ANIMATION}")

unreal.AnimationLibrary.remove_all_curve_data(target)
skeleton = target.get_editor_property("skeleton")
if skeleton is None:
    raise RuntimeError("Target animation has no skeleton")

play_length = target.get_play_length()
blink_times = [0.0, 0.80, 0.88, 0.96, 1.04, 2.30, 2.40, 2.49, 2.58, play_length]
blink_values = [0.0, 0.0, 0.65, 1.0, 0.0, 0.0, 0.65, 1.0, 0.0, 0.0]
smile_times = [0.0, 0.50, max(0.50, play_length - 0.50), play_length]
smile_values = [0.0, 0.60, 0.60, 0.0]
curve_keys = {
    "CTRL_expressions_eyeBlinkL": [blink_times, blink_values],
    "CTRL_expressions_eyeBlinkR": [blink_times, blink_values],
    "CTRL_expressions_mouthCornerPullL": [smile_times, smile_values],
    "CTRL_expressions_mouthCornerPullR": [smile_times, smile_values],
}
for curve_name, (times, values) in curve_keys.items():
    name = unreal.Name(curve_name)
    unreal.AnimationLibrary.add_curve(
        target, name, unreal.RawCurveTrackTypes.RCT_FLOAT, False
    )
    unreal.AnimationLibrary.add_float_curve_keys(
        target, name, times, values
    )
    unreal.AnimationLibrary.set_curve_meta_data_morph_target(
        skeleton, name, True
    )

if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save target animation: {TARGET_ANIMATION}")
unreal.EditorAssetLibrary.save_loaded_asset(skeleton, only_if_is_dirty=False)

curve_names = [
    str(name)
    for name in unreal.AnimationLibrary.get_animation_curve_names(
        target, unreal.RawCurveTrackTypes.RCT_FLOAT
    )
]
missing_curves = sorted(set(curve_keys) - set(curve_names))
report = {
    "source_animation": source.get_path_name(),
    "target_animation": target.get_path_name(),
    "created_target": created_target,
    "play_length_seconds": play_length,
    "curve_keys": {
        name: {"times": times, "values": values}
        for name, (times, values) in curve_keys.items()
    },
    "curve_names": sorted(curve_names),
    "missing_curves": missing_curves,
    "bone_track_count": target.data_model_interface.get_num_bone_tracks(),
    "success": not missing_curves,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
if missing_curves:
    raise RuntimeError(f"Facial curves were not created: {missing_curves}")

print(
    "DM_BODY_FACE_ANIMATION="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "target_animation": report["target_animation"],
            "curve_names": report["curve_names"],
            "bone_track_count": report["bone_track_count"],
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
