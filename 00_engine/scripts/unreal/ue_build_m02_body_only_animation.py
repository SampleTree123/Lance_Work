"""Create a body-only derivative of the CC Audience animation."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


SOURCE_ANIMATION = (
    "/Game/Vendor/Reallusion/CC5/Animations/Pilot/A_CC_Audience_F_01_Pilot"
)
TARGET_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "A_CC_Audience_F_01_BodyOnly_v001"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_body_only_animation_build.json"
)
FACE_SUPPORT_TRACKS = [
    "cc_base_facialbone",
    "cc_base_jawroot",
    "cc_base_tongue01",
    "cc_base_tongue02",
    "cc_base_tongue03",
    "cc_base_teeth02",
    "cc_base_r_eye",
    "cc_base_l_eye",
    "cc_base_upperjaw",
    "cc_base_teeth01",
]


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

model = target.data_model_interface
controller = target.controller
if model is None or controller is None:
    raise RuntimeError("Animation data model/controller is unavailable")

tracks_before = [str(name) for name in model.get_bone_track_names()]
float_curves_before = [
    str(name)
    for name in unreal.AnimationLibrary.get_animation_curve_names(
        target, unreal.RawCurveTrackTypes.RCT_FLOAT
    )
]
removed_tracks = []
controller.open_bracket("Remove CC face animation data", False)
try:
    for track_name in FACE_SUPPORT_TRACKS:
        if track_name in tracks_before:
            if not controller.remove_bone_track(unreal.Name(track_name), False):
                raise RuntimeError(f"Unable to remove bone track: {track_name}")
            removed_tracks.append(track_name)
    removed_attributes = controller.remove_all_attributes(False)
finally:
    controller.close_bracket(False)

unreal.AnimationLibrary.remove_all_curve_data(target)

tracks_after = [str(name) for name in target.data_model_interface.get_bone_track_names()]
float_curves_after = [
    str(name)
    for name in unreal.AnimationLibrary.get_animation_curve_names(
        target, unreal.RawCurveTrackTypes.RCT_FLOAT
    )
]
remaining_face_tracks = sorted(set(FACE_SUPPORT_TRACKS) & set(tracks_after))
if remaining_face_tracks:
    raise RuntimeError(
        f"Face support tracks remain on body-only animation: {remaining_face_tracks}"
    )
if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save target animation: {TARGET_ANIMATION}")

report = {
    "source_animation": source.get_path_name(),
    "target_animation": target.get_path_name(),
    "created_target": created_target,
    "source_track_count": len(tracks_before),
    "target_track_count": len(tracks_after),
    "requested_face_support_tracks": FACE_SUPPORT_TRACKS,
    "removed_tracks": removed_tracks,
    "float_curves_before": float_curves_before,
    "float_curves_after": float_curves_after,
    "removed_attribute_count": removed_attributes,
    "remaining_face_support_tracks": remaining_face_tracks,
    "play_length_seconds": target.get_play_length(),
    "skeleton": target.get_editor_property("skeleton").get_path_name(),
    "success": not remaining_face_tracks and not float_curves_after,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(
    "DM_BODY_ONLY_ANIMATION="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "target_animation": report["target_animation"],
            "created_target": report["created_target"],
            "source_track_count": report["source_track_count"],
            "target_track_count": report["target_track_count"],
            "removed_tracks": report["removed_tracks"],
            "removed_attribute_count": report["removed_attribute_count"],
            "remaining_float_curves": report["float_curves_after"],
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
