"""Build reversible in-place candidates for first-batch moving animations."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work")
MOTION_GATE = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_motions_20260822_v1"
    / "aggregate_motion_import_gate.json"
)
OUTPUT_DIR = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day3_20260822_v1"
)
REPORT_PATH = OUTPUT_DIR / "inplace_candidate_build.json"

ACTION_IDS = (
    "ACT_F02_CATCH_BREATH",
    "ACT_M04_LIVING_ROOM_SWING",
    "ACT_F01_SEXY_DANCE",
    "ACT_M01_BATTLE_DANCE",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def copy_vector(value) -> unreal.Vector:
    return unreal.Vector(float(value.x), float(value.y), float(value.z))


def copy_quat(value) -> unreal.Quat:
    return unreal.Quat(
        float(value.x), float(value.y), float(value.z), float(value.w)
    )


def frame_window(animation, window: dict) -> tuple[int, int, float]:
    model = animation.data_model_interface
    frame_rate = model.get_frame_rate()
    fps = float(frame_rate.numerator) / float(frame_rate.denominator)
    frame_count = int(model.get_number_of_frames())
    last_frame = max(0, frame_count)
    start_frame = min(
        last_frame,
        max(0, int(round(float(window["start_seconds"]) * fps))),
    )
    end_frame = min(
        last_frame,
        max(start_frame, int(round(float(window["source_end_seconds"]) * fps))),
    )
    return start_frame, end_frame, fps


def horizontal_excursion(animation, window: dict) -> dict:
    start_frame, end_frame, fps = frame_window(animation, window)
    start = unreal.AnimationLibrary.get_bone_pose_for_frame(
        animation, unreal.Name("root"), start_frame, False
    )
    maximum = 0.0
    maximum_frame = start_frame
    end_delta = {"x": 0.0, "y": 0.0, "z": 0.0}
    for frame in range(start_frame, end_frame + 1):
        pose = unreal.AnimationLibrary.get_bone_pose_for_frame(
            animation, unreal.Name("root"), frame, False
        )
        dx = float(pose.translation.x - start.translation.x)
        dy = float(pose.translation.y - start.translation.y)
        dz = float(pose.translation.z - start.translation.z)
        value = math.sqrt(dx * dx + dy * dy)
        if value > maximum:
            maximum = value
            maximum_frame = frame
        if frame == end_frame:
            end_delta = {"x": dx, "y": dy, "z": dz}
    return {
        "start_frame": start_frame,
        "end_frame": end_frame,
        "maximum_horizontal_excursion_cm": maximum,
        "maximum_excursion_frame": maximum_frame,
        "maximum_excursion_seconds": maximum_frame / fps,
        "end_delta_cm": end_delta,
        "passed_5cm_gate": maximum <= 5.0,
    }


def destination_path(source: dict) -> str:
    sex_folder = "Female" if source["sex"] == "female" else "Male"
    action_name = source["action_id"].replace("ACT_", "")
    return (
        f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
        f"InPlaceCandidates/A_DM_{action_name}_InPlaceCandidate_v001"
    )


def build_candidate(source: dict) -> dict:
    source_path = source["body_only_animation"]["asset"]
    source_asset = unreal.load_asset(source_path)
    if not isinstance(source_asset, unreal.AnimSequence):
        raise RuntimeError(f"Missing BodyOnly source animation: {source_path}")

    target_path = destination_path(source)
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        if not unreal.EditorAssetLibrary.delete_asset(target_path):
            raise RuntimeError(f"Unable to replace generated candidate: {target_path}")
    target = unreal.EditorAssetLibrary.duplicate_asset(
        source_asset.get_path_name().split(".", 1)[0], target_path
    )
    if not isinstance(target, unreal.AnimSequence):
        raise RuntimeError(f"Unable to duplicate candidate: {target_path}")

    model = target.data_model_interface
    controller = target.controller
    if model is None or controller is None:
        raise RuntimeError(f"Animation model/controller unavailable: {target_path}")

    frame_count = int(model.get_number_of_frames())
    key_count = frame_count + 1
    poses = [
        unreal.AnimationLibrary.get_bone_pose_for_frame(
            target, unreal.Name("root"), frame, False
        )
        for frame in range(key_count)
    ]
    if not poses:
        raise RuntimeError(f"Root track has no poses: {target_path}")

    initial_x = float(poses[0].translation.x)
    initial_y = float(poses[0].translation.y)
    positions = [
        unreal.Vector(initial_x, initial_y, float(pose.translation.z))
        for pose in poses
    ]
    rotations = [copy_quat(pose.rotation) for pose in poses]
    scales = [copy_vector(pose.scale3d) for pose in poses]

    controller.open_bracket("Build first-batch in-place candidate", False)
    try:
        if not controller.set_bone_track_keys(
            unreal.Name("root"), positions, rotations, scales, False
        ):
            raise RuntimeError(f"Unable to replace root keys: {target_path}")
        controller.remove_all_attributes(False)
    finally:
        controller.close_bracket(False)

    target.set_editor_property("enable_root_motion", False)
    target.set_editor_property("force_root_lock", True)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save candidate: {target_path}")

    source_tracks = {
        str(name) for name in source_asset.data_model_interface.get_bone_track_names()
    }
    target_tracks = {
        str(name) for name in target.data_model_interface.get_bone_track_names()
    }
    validation = horizontal_excursion(target, source["window"])
    return {
        "action_id": source["action_id"],
        "sex": source["sex"],
        "source_asset": source_asset.get_path_name(),
        "candidate_asset": target.get_path_name(),
        "window": source["window"],
        "source_excursion": horizontal_excursion(source_asset, source["window"]),
        "candidate_excursion": validation,
        "source_track_count": len(source_tracks),
        "candidate_track_count": len(target_tracks),
        "track_set_unchanged": source_tracks == target_tracks,
        "enable_root_motion": bool(target.get_editor_property("enable_root_motion")),
        "force_root_lock": bool(target.get_editor_property("force_root_lock")),
        "passed": validation["passed_5cm_gate"]
        and source_tracks == target_tracks,
    }


if not MOTION_GATE.is_file():
    raise FileNotFoundError(str(MOTION_GATE))

gate = read_json(MOTION_GATE)
sources = {record["action_id"]: record for record in gate["records"]}
missing = sorted(set(ACTION_IDS) - set(sources))
if missing:
    raise RuntimeError("Missing action records: " + ", ".join(missing))

records = [build_candidate(sources[action_id]) for action_id in ACTION_IDS]
report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "generated_inplace_candidates_not_production_approved",
    "records": records,
    "success": all(record["passed"] for record in records),
}
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {
            "report": str(REPORT_PATH),
            "success": report["success"],
            "candidates": [
                {
                    "action_id": record["action_id"],
                    "asset": record["candidate_asset"],
                    "source_max_cm": record["source_excursion"][
                        "maximum_horizontal_excursion_cm"
                    ],
                    "candidate_max_cm": record["candidate_excursion"][
                        "maximum_horizontal_excursion_cm"
                    ],
                }
                for record in records
            ],
        },
        indent=2,
    )
)
