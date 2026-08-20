"""Build the Phase 1 M02 body-only animation library."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ANIMATIONS = [
    {
        "id": "audience",
        "source": (
            "/Game/Vendor/Reallusion/CC5/Animations/Pilot/"
            "A_CC_Audience_F_01_Pilot"
        ),
        "target": (
            "/Game/DataMake/Animations/CC5/Pilot/"
            "A_CC_Audience_F_01_BodyOnly_v001"
        ),
    },
    {
        "id": "walk_wander",
        "source": (
            "/Game/Vendor/Reallusion/CC5/Animations/Pilot/"
            "A_CC_Walk_Wander_M_Pilot"
        ),
        "target": (
            "/Game/DataMake/Animations/CC5/Pilot/"
            "A_CC_Walk_Wander_M_BodyOnly_v001"
        ),
    },
]
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_body_motion_library_v001_build.json"
)
FACE_SUPPORT_TRACKS = {
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
}


def build_body_only(spec):
    source = unreal.load_asset(spec["source"])
    if not isinstance(source, unreal.AnimSequence):
        raise RuntimeError(f"Source animation is unavailable: {spec['source']}")

    target = unreal.load_asset(spec["target"])
    created = False
    if target is None:
        target = unreal.EditorAssetLibrary.duplicate_asset(
            spec["source"], spec["target"]
        )
        created = True
    if not isinstance(target, unreal.AnimSequence):
        raise RuntimeError(f"Unable to create body animation: {spec['target']}")

    model = target.data_model_interface
    controller = target.controller
    if model is None or controller is None:
        raise RuntimeError(f"Animation model/controller unavailable: {spec['target']}")

    tracks_before = [str(name) for name in model.get_bone_track_names()]
    removed_tracks = []
    controller.open_bracket("Remove CC face animation data", False)
    try:
        for track_name in sorted(FACE_SUPPORT_TRACKS):
            if track_name in tracks_before:
                if not controller.remove_bone_track(unreal.Name(track_name), False):
                    raise RuntimeError(f"Unable to remove track: {track_name}")
                removed_tracks.append(track_name)
        removed_attributes = controller.remove_all_attributes(False)
    finally:
        controller.close_bracket(False)

    unreal.AnimationLibrary.remove_all_curve_data(target)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save body animation: {spec['target']}")

    tracks_after = [
        str(name) for name in target.data_model_interface.get_bone_track_names()
    ]
    curves_after = [
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            target, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    ]
    remaining_face_tracks = sorted(FACE_SUPPORT_TRACKS & set(tracks_after))
    success = not remaining_face_tracks and not curves_after
    if not success:
        raise RuntimeError(
            f"Body-only verification failed for {spec['target']}: "
            f"tracks={remaining_face_tracks}, curves={curves_after}"
        )
    return {
        "id": spec["id"],
        "source": source.get_path_name(),
        "target": target.get_path_name(),
        "created": created,
        "play_length_seconds": target.get_play_length(),
        "source_track_count": len(tracks_before),
        "target_track_count": len(tracks_after),
        "removed_face_tracks": removed_tracks,
        "removed_attribute_count": removed_attributes,
        "remaining_face_tracks": remaining_face_tracks,
        "remaining_float_curves": curves_after,
        "skeleton": target.get_editor_property("skeleton").get_path_name(),
        "success": success,
    }


records = [build_body_only(spec) for spec in ANIMATIONS]
report = {
    "schema_version": 1,
    "library_role": "body_only",
    "animations": records,
    "success": all(item["success"] for item in records),
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    "DM_BODY_MOTION_LIBRARY="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "targets": [item["target"] for item in records],
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
