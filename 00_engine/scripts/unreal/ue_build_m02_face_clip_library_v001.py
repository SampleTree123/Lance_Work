"""Build reusable curve-only additive face clips for the M02 pilot."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


SOURCE_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "A_CC_Audience_F_01_BodyOnly_v001"
)
TARGET_FOLDER = "/Game/DataMake/Animations/CC5/Pilot/Face"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_face_clip_library_v001_build.json"
)

BLINK_L = "CTRL_expressions_eyeBlinkL"
BLINK_R = "CTRL_expressions_eyeBlinkR"
LOOK_LEFT_L = "CTRL_expressions_eyeLookLeftL"
LOOK_LEFT_R = "CTRL_expressions_eyeLookLeftR"
LOOK_RIGHT_L = "CTRL_expressions_eyeLookRightL"
LOOK_RIGHT_R = "CTRL_expressions_eyeLookRightR"
SMILE_L = "CTRL_expressions_mouthCornerPullL"
SMILE_R = "CTRL_expressions_mouthCornerPullR"
JAW_OPEN = "CTRL_expressions_jawOpen"

BLINK_KEYS = (
    [0.0, 0.78, 0.84, 0.90, 0.97, 2.65, 2.72, 2.79, 2.87, 4.0],
    [0.0, 0.0, 0.55, 1.0, 0.0, 0.0, 0.50, 1.0, 0.0, 0.0],
)

CLIPS = [
    {
        "id": "neutral",
        "asset_name": "A_DM_M02_Face_Neutral_Loop_v001",
        "curves": {},
    },
    {
        "id": "natural_blink",
        "asset_name": "A_DM_M02_Face_NaturalBlink_Loop_v001",
        "curves": {BLINK_L: BLINK_KEYS, BLINK_R: BLINK_KEYS},
    },
    {
        "id": "blink_gaze",
        "asset_name": "A_DM_M02_Face_BlinkGaze_Loop_v001",
        "curves": {
            BLINK_L: BLINK_KEYS,
            BLINK_R: BLINK_KEYS,
            LOOK_LEFT_L: (
                [0.0, 0.45, 0.75, 1.45, 1.75, 4.0],
                [0.0, 0.0, 0.32, 0.32, 0.0, 0.0],
            ),
            LOOK_LEFT_R: (
                [0.0, 0.45, 0.75, 1.45, 1.75, 4.0],
                [0.0, 0.0, 0.32, 0.32, 0.0, 0.0],
            ),
            LOOK_RIGHT_L: (
                [0.0, 1.95, 2.25, 3.05, 3.35, 4.0],
                [0.0, 0.0, 0.30, 0.30, 0.0, 0.0],
            ),
            LOOK_RIGHT_R: (
                [0.0, 1.95, 2.25, 3.05, 3.35, 4.0],
                [0.0, 0.0, 0.30, 0.30, 0.0, 0.0],
            ),
        },
    },
    {
        "id": "subtle_smile",
        "asset_name": "A_DM_M02_Face_SubtleSmile_Loop_v001",
        "curves": {
            SMILE_L: (
                [0.0, 0.55, 1.15, 2.85, 3.45, 4.0],
                [0.0, 0.0, 0.30, 0.30, 0.0, 0.0],
            ),
            SMILE_R: (
                [0.0, 0.55, 1.15, 2.85, 3.45, 4.0],
                [0.0, 0.0, 0.27, 0.27, 0.0, 0.0],
            ),
        },
    },
    {
        "id": "jaw_open_test",
        "asset_name": "A_DM_M02_Face_JawOpen_Test_v001",
        "curves": {
            JAW_OPEN: (
                [0.0, 0.55, 1.15, 2.85, 3.45, 4.0],
                [0.0, 0.0, 0.65, 0.65, 0.0, 0.0],
            ),
        },
    },
]


def build_clip(source, skeleton, spec):
    target_path = f"{TARGET_FOLDER}/{spec['asset_name']}"
    target = unreal.load_asset(target_path)
    created = False
    if target is None:
        target = unreal.EditorAssetLibrary.duplicate_asset(
            SOURCE_ANIMATION, target_path
        )
        created = True
    if not isinstance(target, unreal.AnimSequence):
        raise RuntimeError(f"Unable to create face clip: {target_path}")

    controller = target.controller
    model = target.data_model_interface
    if controller is None or model is None:
        raise RuntimeError(f"Face clip model/controller unavailable: {target_path}")

    bone_tracks = [str(name) for name in model.get_bone_track_names()]
    controller.open_bracket("Create curve-only face clip", False)
    try:
        for track_name in bone_tracks:
            if not controller.remove_bone_track(unreal.Name(track_name), False):
                raise RuntimeError(f"Unable to remove bone track: {track_name}")
        controller.remove_all_attributes(False)
    finally:
        controller.close_bracket(False)
    unreal.AnimationLibrary.remove_all_curve_data(target)

    for curve_name, (times, values) in spec["curves"].items():
        curve = unreal.Name(curve_name)
        unreal.AnimationLibrary.add_curve(
            target, curve, unreal.RawCurveTrackTypes.RCT_FLOAT, False
        )
        unreal.AnimationLibrary.add_float_curve_keys(target, curve, times, values)
        unreal.AnimationLibrary.set_curve_meta_data_morph_target(
            skeleton, curve, True
        )

    target.set_editor_property(
        "additive_anim_type",
        unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE,
    )
    target.set_editor_property(
        "ref_pose_type", unreal.AdditiveBasePoseType.ABPT_REF_POSE
    )
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save face clip: {target_path}")

    tracks_after = [
        str(name) for name in target.data_model_interface.get_bone_track_names()
    ]
    curves_after = sorted(
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            target, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    )
    missing_curves = sorted(set(spec["curves"]) - set(curves_after))
    success = not tracks_after and not missing_curves
    if not success:
        raise RuntimeError(
            f"Face clip verification failed for {target_path}: "
            f"tracks={tracks_after}, missing={missing_curves}"
        )
    return {
        "id": spec["id"],
        "asset": target.get_path_name(),
        "created": created,
        "play_length_seconds": target.get_play_length(),
        "bone_track_count": len(tracks_after),
        "curve_names": curves_after,
        "curve_keys": {
            name: {"times": times, "values": values}
            for name, (times, values) in spec["curves"].items()
        },
        "additive_anim_type": str(target.get_editor_property("additive_anim_type")),
        "ref_pose_type": str(target.get_editor_property("ref_pose_type")),
        "success": success,
    }


source = unreal.load_asset(SOURCE_ANIMATION)
if not isinstance(source, unreal.AnimSequence):
    raise RuntimeError(f"Source animation is unavailable: {SOURCE_ANIMATION}")
skeleton = source.get_editor_property("skeleton")
if skeleton is None:
    raise RuntimeError("Source animation has no skeleton")

records = [build_clip(source, skeleton, spec) for spec in CLIPS]
unreal.EditorAssetLibrary.save_loaded_asset(skeleton, only_if_is_dirty=False)
report = {
    "schema_version": 1,
    "library_role": "curve_only_additive_face",
    "source_animation": source.get_path_name(),
    "clips": records,
    "success": all(item["success"] for item in records),
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    "DM_FACE_CLIP_LIBRARY="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "assets": [item["asset"] for item in records],
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
