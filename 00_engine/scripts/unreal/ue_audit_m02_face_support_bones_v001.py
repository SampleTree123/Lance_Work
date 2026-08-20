"""Audit the M02 facial support-bone hierarchy and source animation data."""

from __future__ import annotations

import json
import math
from pathlib import Path

import unreal


SKELETON_PATH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58_Skeleton"
)
ANIMATIONS = {
    "audience_source": (
        "/Game/Vendor/Reallusion/CC5/Animations/Pilot/"
        "A_CC_Audience_F_01_Pilot"
    ),
    "walk_source": (
        "/Game/Vendor/Reallusion/CC5/Animations/Pilot/"
        "A_CC_Walk_Wander_M_Pilot"
    ),
    "neutral_face": (
        "/Game/DataMake/Animations/CC5/Pilot/Face/"
        "A_DM_M02_Face_Neutral_Loop_v001"
    ),
}
SUPPORT_BONES = (
    "cc_base_facialbone",
    "cc_base_jawroot",
    "cc_base_upperjaw",
    "cc_base_teeth01",
    "cc_base_teeth02",
    "cc_base_tongue01",
    "cc_base_tongue02",
    "cc_base_tongue03",
    "cc_base_l_eye",
    "cc_base_r_eye",
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_face_support_bone_audit_v001.json"
)


def vector_record(value):
    return {"x": value.x, "y": value.y, "z": value.z}


def quat_record(value):
    return {"x": value.x, "y": value.y, "z": value.z, "w": value.w}


def transform_record(value):
    return {
        "translation": vector_record(value.translation),
        "rotation_quat": quat_record(value.rotation),
        "rotation_euler": vector_record(value.rotation.euler()),
        "scale": vector_record(value.scale3d),
    }


def vector_distance(left, right):
    return math.sqrt(
        (left.x - right.x) ** 2
        + (left.y - right.y) ** 2
        + (left.z - right.z) ** 2
    )


def scale_delta(left, right):
    return max(
        abs(left.x - right.x),
        abs(left.y - right.y),
        abs(left.z - right.z),
    )


def audit_animation(animation):
    model = animation.data_model_interface
    frame_count = int(model.get_number_of_frames())
    sample_frames = sorted({0, frame_count // 4, frame_count // 2, frame_count * 3 // 4, frame_count})
    track_names = {str(name) for name in model.get_bone_track_names()}
    records = {}
    for bone in SUPPORT_BONES:
        poses = [
            unreal.AnimationLibrary.get_bone_pose_for_frame(
                animation, unreal.Name(bone), frame, False
            )
            for frame in sample_frames
        ]
        base = poses[0]
        records[bone] = {
            "track_present": bone in track_names,
            "path_to_root": [
                str(name)
                for name in unreal.AnimationLibrary.find_bone_path_to_root(
                    animation, unreal.Name(bone)
                )
            ],
            "sample_frames": sample_frames,
            "sample_poses": [transform_record(pose) for pose in poses],
            "max_translation_delta_cm": max(
                vector_distance(base.translation, pose.translation) for pose in poses
            ),
            "max_rotation_delta_degrees": math.degrees(
                max(base.rotation.angular_distance(pose.rotation) for pose in poses)
            ),
            "max_scale_delta": max(
                scale_delta(base.scale3d, pose.scale3d) for pose in poses
            ),
        }
    return {
        "asset": animation.get_path_name(),
        "frame_count": frame_count,
        "frame_rate": str(model.get_frame_rate()),
        "play_length_seconds": animation.get_play_length(),
        "track_count": len(track_names),
        "support_track_count": sum(
            item["track_present"] for item in records.values()
        ),
        "support_bones": records,
    }


skeleton = unreal.load_asset(SKELETON_PATH)
if not isinstance(skeleton, unreal.Skeleton):
    raise RuntimeError(f"M02 Skeleton unavailable: {SKELETON_PATH}")

assets = {name: unreal.load_asset(path) for name, path in ANIMATIONS.items()}
missing = [
    name for name, asset in assets.items() if not isinstance(asset, unreal.AnimSequence)
]
if missing:
    raise RuntimeError("Missing animation assets: " + ", ".join(missing))

audits = {name: audit_animation(asset) for name, asset in assets.items()}
walk = audits["walk_source"]
report = {
    "schema_version": 1,
    "skeleton": skeleton.get_path_name(),
    "support_bones": list(SUPPORT_BONES),
    "branch_filter_root": "cc_base_facialbone",
    "animations": audits,
    "walk_source_support_tracks_complete": walk["support_track_count"]
    == len(SUPPORT_BONES),
    "head_or_neck_in_support_set": any(
        name in {"head", "neck_01", "neck_02"} for name in SUPPORT_BONES
    ),
}
report["success"] = (
    report["walk_source_support_tracks_complete"]
    and not report["head_or_neck_in_support_set"]
)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    "DM_FACE_SUPPORT_AUDIT="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "walk_support_track_count": walk["support_track_count"],
            "success": report["success"],
        },
        sort_keys=True,
    )
)
