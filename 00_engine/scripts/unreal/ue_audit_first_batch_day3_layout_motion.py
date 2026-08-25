"""Read-only audit for the first-batch Day 3 layout and motion windows."""

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
    / "first_batch_day3_20260822_v2"
)
REPORT_PATH = OUTPUT_DIR / "layout_motion_audit.json"
RUNTIME_PROBE_PATH = OUTPUT_DIR / "sequence_runtime_pose_probe.json"

SEQUENCE_PATH = str(
    globals().get(
        "DM_SEQUENCE_PATH",
        "/Game/DataMake/Sequences/FirstBatch/"
        "LS_DM_FirstBatch_F02_20s_Pilot_v001",
    )
)
TARGET_ACTOR_NAME = "CC_FB_F_ID02_O04_Blueprint_LiveLink_C_1"
EXPECTED_CAMERA_LABELS = ("near", "far", "side", "high")
EXPECTED_DISPLAY_FPS = 30.0
EXPECTED_DURATION_SECONDS = 20.0
EXPECTED_FRAME_COUNT = 600
EXPECTED_CAMERA_CUTS = (
    (0, 150, "near"),
    (150, 300, "far"),
    (300, 450, "high"),
    (450, 600, "side"),
)
EXPECTED_ACTION_SECTIONS = ((0, 150), (150, 300), (300, 450), (450, 600))
F02_INPLACE_ASSET = (
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/InPlaceCandidates/"
    "A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001"
)
APPROVED_ORIGINAL_MOVING_ACTIONS = {
    "ACT_F01_SEXY_DANCE",
    "ACT_M01_BATTLE_DANCE",
    "ACT_M04_LIVING_ROOM_SWING",
}

# A static multi-camera first batch should not allow an actor to translate far
# enough to materially change framing. These thresholds are audit labels only.
IN_PLACE_THRESHOLD_CM = 5.0
BOUNDED_THRESHOLD_CM = 30.0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def vector_record(value) -> dict:
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
    }


def rotator_record(value) -> dict:
    return {
        "pitch": float(value.pitch),
        "yaw": float(value.yaw),
        "roll": float(value.roll),
    }


def dot(a, b) -> float:
    return float(a.x * b.x + a.y * b.y + a.z * b.z)


def length(value) -> float:
    return math.sqrt(dot(value, value))


def normalized(value):
    magnitude = length(value)
    if magnitude <= 1.0e-8:
        return unreal.Vector()
    return unreal.Vector(value.x / magnitude, value.y / magnitude, value.z / magnitude)


def frame_value(value) -> int:
    if hasattr(value, "value"):
        return int(value.value)
    return int(value)


def find_level_actor(actor_subsystem, name: str):
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_name() == name or actor.get_actor_label() == name:
            return actor
    return None


def actor_bounds_record(actor) -> tuple[dict, object, object]:
    origin, extent = actor.get_actor_bounds(False, False)
    minimum = unreal.Vector(
        origin.x - extent.x,
        origin.y - extent.y,
        origin.z - extent.z,
    )
    maximum = unreal.Vector(
        origin.x + extent.x,
        origin.y + extent.y,
        origin.z + extent.z,
    )
    return (
        {
            "origin": vector_record(origin),
            "extent": vector_record(extent),
            "min": vector_record(minimum),
            "max": vector_record(maximum),
        },
        minimum,
        maximum,
    )


def bounds_corners(minimum, maximum):
    for x in (minimum.x, maximum.x):
        for y in (minimum.y, maximum.y):
            for z in (minimum.z, maximum.z):
                yield unreal.Vector(x, y, z)


def camera_record(camera, target_center, target_min, target_max) -> dict:
    component = camera.get_cine_camera_component()
    location = camera.get_actor_location()
    rotation = camera.get_actor_rotation()
    forward = camera.get_actor_forward_vector()
    right = camera.get_actor_right_vector()
    up = camera.get_actor_up_vector()
    to_target = target_center - location
    target_distance = length(to_target)
    target_direction = normalized(to_target)
    aim_dot = max(-1.0, min(1.0, dot(forward, target_direction)))
    aim_error_degrees = math.degrees(math.acos(aim_dot))

    focal_length = float(component.get_editor_property("current_focal_length"))
    aperture = float(component.get_editor_property("current_aperture"))
    filmback = component.get_editor_property("filmback")
    sensor_width = float(filmback.sensor_width)
    sensor_height = float(filmback.sensor_height)
    horizontal_fov = math.degrees(
        2.0 * math.atan(sensor_width / (2.0 * focal_length))
    )
    vertical_fov = math.degrees(
        2.0 * math.atan(sensor_height / (2.0 * focal_length))
    )
    tan_horizontal = math.tan(math.radians(horizontal_fov) * 0.5)
    tan_vertical = math.tan(math.radians(vertical_fov) * 0.5)

    projected = []
    all_in_front = True
    for corner in bounds_corners(target_min, target_max):
        relative = corner - location
        depth = dot(relative, forward)
        all_in_front = all_in_front and depth > 0.01
        if depth <= 0.01:
            continue
        projected.append(
            {
                "x": dot(relative, right) / (depth * tan_horizontal),
                "y": dot(relative, up) / (depth * tan_vertical),
                "depth_cm": depth,
            }
        )

    target_relative = target_center - location
    target_depth = dot(target_relative, forward)
    target_ndc = None
    if target_depth > 0.01:
        target_ndc = {
            "x": dot(target_relative, right) / (target_depth * tan_horizontal),
            "y": dot(target_relative, up) / (target_depth * tan_vertical),
        }

    bounds_ndc = None
    full_bounds_in_frame = False
    if projected:
        bounds_ndc = {
            "min_x": min(value["x"] for value in projected),
            "max_x": max(value["x"] for value in projected),
            "min_y": min(value["y"] for value in projected),
            "max_y": max(value["y"] for value in projected),
        }
        full_bounds_in_frame = all_in_front and all(
            abs(value["x"]) <= 1.0 and abs(value["y"]) <= 1.0
            for value in projected
        )
    actor_bounds_intersect_frame = bool(
        all_in_front
        and bounds_ndc
        and bounds_ndc["min_x"] <= 1.0
        and bounds_ndc["max_x"] >= -1.0
        and bounds_ndc["min_y"] <= 1.0
        and bounds_ndc["max_y"] >= -1.0
    )

    focus_settings = component.get_editor_property("focus_settings")
    return {
        "name": camera.get_name(),
        "label": camera.get_actor_label(),
        "path": camera.get_path_name(),
        "location": vector_record(location),
        "rotation": rotator_record(rotation),
        "focal_length_mm": focal_length,
        "aperture": aperture,
        "sensor_width_mm": sensor_width,
        "sensor_height_mm": sensor_height,
        "horizontal_fov_degrees": horizontal_fov,
        "vertical_fov_degrees": vertical_fov,
        "focus_method": str(focus_settings.focus_method),
        "manual_focus_distance_cm": float(focus_settings.manual_focus_distance),
        "target_distance_cm": target_distance,
        "aim_error_degrees": aim_error_degrees,
        "target_center_ndc": target_ndc,
        "target_bounds_ndc": bounds_ndc,
        "actor_bounds_intersect_frame": actor_bounds_intersect_frame,
        "full_actor_bounds_in_frame": full_bounds_in_frame,
    }


def sequence_record() -> dict:
    sequence = unreal.load_asset(SEQUENCE_PATH)
    if not isinstance(sequence, unreal.LevelSequence):
        return {"asset": SEQUENCE_PATH, "exists": False}

    # Camera bindings are spawnables. Evaluating frame zero materializes their
    # transient editor actors so the geometric framing audit can inspect them.
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
    for camera_label in EXPECTED_CAMERA_LABELS:
        binding = sequence.find_binding_by_name(camera_label)
        if binding.is_valid():
            unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(
                sequence.get_binding_id(binding)
            )

    display_rate = sequence.get_display_rate()
    fps = float(display_rate.numerator) / float(display_rate.denominator)
    playback_start = int(sequence.get_playback_start())
    playback_end = int(sequence.get_playback_end())
    duration_frames = playback_end - playback_start
    duration_seconds = duration_frames / fps if fps > 0.0 else 0.0

    bindings = []
    animation_sections = []
    for binding in sequence.get_bindings():
        track_classes = []
        for track in binding.get_tracks():
            track_class = track.get_class().get_name()
            track_classes.append(track_class)
            if track_class != "MovieSceneSkeletalAnimationTrack":
                continue
            for section in track.get_sections():
                params = section.get_editor_property("params")
                animation = params.get_editor_property("animation")
                offset = params.get_editor_property(
                    "first_loop_start_frame_offset"
                )
                animation_sections.append(
                    {
                        "binding": binding.get_name(),
                        "start_frame": frame_value(section.get_start_frame()),
                        "end_frame": frame_value(section.get_end_frame()),
                        "animation": (
                            animation.get_path_name() if animation else None
                        ),
                        "first_loop_start_offset_ticks": frame_value(offset),
                        "force_custom_mode": bool(
                            params.get_editor_property("force_custom_mode")
                        ),
                    }
                )
        bindings.append(
            {
                "name": binding.get_name(),
                "display_name": str(binding.get_display_name()),
                "tracks": track_classes,
            }
        )

    master_tracks = []
    camera_cuts = []
    for track in sequence.get_tracks():
        track_record = {
            "class": track.get_class().get_name(),
            "section_count": len(track.get_sections()),
        }
        master_tracks.append(track_record)
        if track_record["class"] != "MovieSceneCameraCutTrack":
            continue
        for section in track.get_sections():
            binding = sequence.resolve_binding_id(section.get_camera_binding_id())
            camera_cuts.append(
                {
                    "start_frame": frame_value(section.get_start_frame()),
                    "end_frame": frame_value(section.get_end_frame()),
                    "camera_binding": binding.get_name() if binding.is_valid() else None,
                }
            )

    camera_binding_names = sorted(
        {
            binding["name"]
            for binding in bindings
            if "MovieScene3DTransformTrack" in binding["tracks"]
            and "MovieSceneSpawnTrack" in binding["tracks"]
        }
    )
    skeletal_animation_track_count = sum(
        1
        for binding in bindings
        for track_class in binding["tracks"]
        if track_class == "MovieSceneSkeletalAnimationTrack"
    )
    observed_camera_cuts = [
        (cut["start_frame"], cut["end_frame"], cut["camera_binding"])
        for cut in camera_cuts
    ]
    observed_action_sections = [
        (section["start_frame"], section["end_frame"])
        for section in animation_sections
    ]
    expected_f02_asset = unreal.load_asset(F02_INPLACE_ASSET)
    expected_f02_path = (
        expected_f02_asset.get_path_name() if expected_f02_asset else None
    )
    return {
        "asset": sequence.get_path_name(),
        "exists": True,
        "display_rate": {
            "numerator": int(display_rate.numerator),
            "denominator": int(display_rate.denominator),
            "fps": fps,
        },
        "playback_start_frame": playback_start,
        "playback_end_frame": playback_end,
        "duration_frames": duration_frames,
        "duration_seconds": duration_seconds,
        "bindings": bindings,
        "camera_binding_names": camera_binding_names,
        "master_tracks": master_tracks,
        "camera_cuts": camera_cuts,
        "animation_sections": animation_sections,
        "skeletal_animation_track_count": skeletal_animation_track_count,
        "checks": {
            "twenty_second_duration": abs(duration_seconds - EXPECTED_DURATION_SECONDS)
            <= 1.0e-4,
            "display_rate_30fps": abs(fps - EXPECTED_DISPLAY_FPS) <= 1.0e-4,
            "frame_count_600": duration_frames == EXPECTED_FRAME_COUNT,
            "four_camera_bindings": set(camera_binding_names)
            == set(EXPECTED_CAMERA_LABELS),
            "four_sequential_camera_cuts": observed_camera_cuts
            == list(EXPECTED_CAMERA_CUTS),
            "deterministic_motion_track_present": skeletal_animation_track_count > 0,
            "four_repeated_action_sections": observed_action_sections
            == list(EXPECTED_ACTION_SECTIONS),
            "f02_uses_approved_inplace_asset": bool(animation_sections)
            and all(
                section["animation"] == expected_f02_path
                for section in animation_sections
            ),
            "all_action_sections_force_custom_mode": bool(animation_sections)
            and all(
                section["force_custom_mode"] for section in animation_sections
            ),
        },
    }


def resolve_sequence_camera_actors() -> list:
    sequence = unreal.load_asset(SEQUENCE_PATH)
    if not isinstance(sequence, unreal.LevelSequence):
        return []
    resolved = []
    for camera_label in EXPECTED_CAMERA_LABELS:
        binding = sequence.find_binding_by_name(camera_label)
        if not binding.is_valid():
            continue
        for value in unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(
            sequence.get_binding_id(binding)
        ):
            if isinstance(value, unreal.CineCameraActor):
                resolved.append(value)
    return resolved


def root_motion_record(source: dict) -> dict:
    animation_path = (
        F02_INPLACE_ASSET
        if source["action_id"] == "ACT_F02_CATCH_BREATH"
        else source["body_only_animation"]["asset"]
    )
    animation = unreal.load_asset(animation_path)
    if not isinstance(animation, unreal.AnimSequence):
        return {
            "action_id": source["action_id"],
            "asset": animation_path,
            "exists": False,
        }

    model = animation.data_model_interface
    frame_rate = model.get_frame_rate()
    fps = float(frame_rate.numerator) / float(frame_rate.denominator)
    frame_count = int(model.get_number_of_frames())
    last_frame = max(0, frame_count - 1)
    window = source["window"]
    start_frame = min(
        last_frame, max(0, int(round(float(window["start_seconds"]) * fps)))
    )
    end_frame = min(
        last_frame,
        max(start_frame, int(round(float(window["source_end_seconds"]) * fps))),
    )
    start_pose = unreal.AnimationLibrary.get_bone_pose_for_frame(
        animation, unreal.Name("root"), start_frame, False
    )
    previous_pose = start_pose
    maximum_horizontal = 0.0
    maximum_vertical = 0.0
    maximum_frame = start_frame
    cumulative_horizontal = 0.0
    end_delta = {"x": 0.0, "y": 0.0, "z": 0.0}

    for frame in range(start_frame, end_frame + 1):
        pose = unreal.AnimationLibrary.get_bone_pose_for_frame(
            animation, unreal.Name("root"), frame, False
        )
        dx = float(pose.translation.x - start_pose.translation.x)
        dy = float(pose.translation.y - start_pose.translation.y)
        dz = float(pose.translation.z - start_pose.translation.z)
        horizontal = math.sqrt(dx * dx + dy * dy)
        if horizontal > maximum_horizontal:
            maximum_horizontal = horizontal
            maximum_frame = frame
        maximum_vertical = max(maximum_vertical, abs(dz))

        step_x = float(pose.translation.x - previous_pose.translation.x)
        step_y = float(pose.translation.y - previous_pose.translation.y)
        cumulative_horizontal += math.sqrt(step_x * step_x + step_y * step_y)
        previous_pose = pose
        if frame == end_frame:
            end_delta = {"x": dx, "y": dy, "z": dz}

    end_horizontal = math.sqrt(end_delta["x"] ** 2 + end_delta["y"] ** 2)
    if maximum_horizontal <= IN_PLACE_THRESHOLD_CM:
        classification = "in_place"
    elif maximum_horizontal <= BOUNDED_THRESHOLD_CM:
        classification = "bounded"
    else:
        classification = "moving"

    return {
        "action_id": source["action_id"],
        "sex": source["sex"],
        "asset": animation.get_path_name(),
        "exists": True,
        "window": window,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "end_delta_cm": end_delta,
        "end_horizontal_displacement_cm": end_horizontal,
        "maximum_horizontal_excursion_cm": maximum_horizontal,
        "maximum_excursion_frame": maximum_frame,
        "maximum_excursion_seconds": maximum_frame / fps,
        "maximum_vertical_excursion_cm": maximum_vertical,
        "cumulative_horizontal_path_cm": cumulative_horizontal,
        "classification": classification,
        "static_camera_gate_passed": maximum_horizontal <= BOUNDED_THRESHOLD_CM,
    }


if not MOTION_GATE.is_file():
    raise FileNotFoundError(str(MOTION_GATE))

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.EditorLevelLibrary.get_editor_world()
target_actor = find_level_actor(actor_subsystem, TARGET_ACTOR_NAME)
if target_actor is None:
    raise RuntimeError(f"Target actor not found in current level: {TARGET_ACTOR_NAME}")

bounds, target_min, target_max = actor_bounds_record(target_actor)
target_center = unreal.Vector(
    (target_min.x + target_max.x) * 0.5,
    (target_min.y + target_max.y) * 0.5,
    (target_min.z + target_max.z) * 0.5,
)

sequence = sequence_record()
cameras = []
for actor in resolve_sequence_camera_actors():
    cameras.append(camera_record(actor, target_center, target_min, target_max))
cameras.sort(key=lambda value: value["label"].lower())

motion_gate = read_json(MOTION_GATE)
motions = [root_motion_record(source) for source in motion_gate["records"]]
motions.sort(
    key=lambda value: value.get("maximum_horizontal_excursion_cm", -1.0),
    reverse=True,
)

camera_labels = {camera["label"] for camera in cameras}
layout_checks = {
    "current_level_is_tokyo_stylized": "L_DM_TokyoStylized" in world.get_path_name(),
    "target_actor_found": target_actor is not None,
    "target_scale_is_one": all(
        abs(value - 1.0) <= 1.0e-4
        for value in (
            target_actor.get_actor_scale3d().x,
            target_actor.get_actor_scale3d().y,
            target_actor.get_actor_scale3d().z,
        )
    ),
    "four_expected_cameras_present": set(EXPECTED_CAMERA_LABELS).issubset(
        camera_labels
    ),
    "all_expected_cameras_see_actor": all(
        camera["actor_bounds_intersect_frame"]
        and camera["aim_error_degrees"] <= 25.0
        for camera in cameras
        if camera["label"] in EXPECTED_CAMERA_LABELS
    ),
}
moving_actions = [
    motion["action_id"]
    for motion in motions
    if motion.get("classification") == "moving"
]
unapproved_moving_actions = [
    action_id
    for action_id in moving_actions
    if action_id not in APPROVED_ORIGINAL_MOVING_ACTIONS
]
runtime_probe = (
    read_json(RUNTIME_PROBE_PATH) if RUNTIME_PROBE_PATH.is_file() else None
)
runtime_pose_passed = bool(
    runtime_probe
    and runtime_probe.get("sequence") == SEQUENCE_PATH
    and runtime_probe.get("success")
)

report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "read_only_day3_layout_and_motion_audit",
    "current_world": world.get_path_name(),
    "target_actor": {
        "name": target_actor.get_name(),
        "label": target_actor.get_actor_label(),
        "path": target_actor.get_path_name(),
        "location": vector_record(target_actor.get_actor_location()),
        "rotation": rotator_record(target_actor.get_actor_rotation()),
        "scale": vector_record(target_actor.get_actor_scale3d()),
        "bounds": bounds,
    },
    "cameras": cameras,
    "sequence": sequence,
    "motions": motions,
    "runtime_pose_probe": runtime_probe,
    "layout_checks": layout_checks,
    "summary": {
        "camera_count": len(cameras),
        "expected_camera_count": len(EXPECTED_CAMERA_LABELS),
        "motion_count": len(motions),
        "moving_action_ids": moving_actions,
        "approved_original_moving_action_ids": sorted(
            set(moving_actions) & APPROVED_ORIGINAL_MOVING_ACTIONS
        ),
        "unapproved_moving_action_ids": unapproved_moving_actions,
        "sequence_contract_passed": all(sequence.get("checks", {}).values()),
        "layout_geometry_passed": all(layout_checks.values()),
        "machine_ready_for_visual_review": all(
            sequence.get("checks", {}).values()
        )
        and all(layout_checks.values())
        and not unapproved_moving_actions
        and runtime_pose_passed,
        "runtime_pose_probe_passed": runtime_pose_passed,
        "visual_playback_accepted": False,
        "production_ready": False,
    },
    "recommendation": {
        "first_batch_motion_policy": (
            "F02 uses approved InPlace; every other action uses its approved original"
        ),
        "camera_output_policy": (
            "four sequential 150-frame cuts over one repeated five-second action"
        ),
        "camera_tracking_policy": "defer_to_a_dedicated_future_moving_camera_subset",
        "preserve_imported_sources": True,
        "create_derived_assets_only_for_F02_in_first_batch": True,
    },
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps({"report": str(REPORT_PATH), **report["summary"]}, indent=2))
