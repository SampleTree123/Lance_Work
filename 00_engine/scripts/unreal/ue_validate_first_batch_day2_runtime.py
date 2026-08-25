"""Validate all first-batch motions and canonical expression compatibility in UE."""

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
LOOK_GATE_DIR = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_full_reference_20260821_v1"
)
PROFILE_PATH = (
    ROOT
    / "00_engine"
    / "scripts"
    / "unreal"
    / "first_batch_expression_profile_20260820_v1.json"
)
EXPRESSION_BUILD = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day2_20260822_v1"
    / "canonical_expression_build.json"
)
COMPOSITION_BUILD = EXPRESSION_BUILD.with_name(
    "canonical_expression_composition.json"
)
REPORT_PATH = EXPRESSION_BUILD.with_name("day2_runtime_gate.json")

CANONICAL_MESHES = {
    "female": (
        "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/F_ID01_O01/"
        "CC_FB_F_ID01_O01"
    ),
    "male": (
        "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/M_ID01_O01/"
        "CC_FB_M_ID01_O01"
    ),
}
MAJOR_BONES = (
    "root",
    "pelvis",
    "spine_03",
    "head",
    "hand_l",
    "hand_r",
    "foot_l",
    "foot_r",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def object_path(value) -> str | None:
    return value.get_path_name() if value is not None else None


def vector_delta(a, b) -> float:
    return math.sqrt(
        float(b.x - a.x) ** 2
        + float(b.y - a.y) ** 2
        + float(b.z - a.z) ** 2
    )


def rotation_delta(a, b) -> float:
    dot = abs(float(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w))
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def frame_pose(animation, bone: str, frame: int):
    return unreal.AnimationLibrary.get_bone_pose_for_frame(
        animation, unreal.Name(bone), frame, False
    )


def refresh_component(component):
    if hasattr(component, "tick_animation"):
        component.tick_animation(0.0, False)
    if hasattr(component, "refresh_bone_transforms"):
        component.refresh_bone_transforms()
    if hasattr(component, "mark_render_dynamic_data_dirty"):
        component.mark_render_dynamic_data_dirty()


def component_pose(component) -> dict:
    values = {}
    for bone in MAJOR_BONES:
        if component.does_socket_exist(bone):
            transform = component.get_socket_transform(
                unreal.Name(bone), unreal.RelativeTransformSpace.RTS_COMPONENT
            )
            values[bone] = transform.translation
    return values


def component_pose_delta(first: dict, current: dict) -> float:
    return max(
        (
            vector_delta(first[bone], current[bone])
            for bone in sorted(set(first).intersection(current))
        ),
        default=0.0,
    )


for required in (MOTION_GATE, PROFILE_PATH, EXPRESSION_BUILD, COMPOSITION_BUILD):
    if not required.is_file():
        raise FileNotFoundError(str(required))

motion_gate = read_json(MOTION_GATE)
profile = read_json(PROFILE_PATH)
expression_build = read_json(EXPRESSION_BUILD)
composition_build = read_json(COMPOSITION_BUILD)
required_morphs = set(profile["common_curves"])
for expression in profile["expressions"]:
    required_morphs.update(expression["curves"])

look_records = []
for path in sorted(LOOK_GATE_DIR.glob("*_import_validation.json")):
    source = read_json(path)
    look_id = source["look_id"]
    mesh_name = f"CC_FB_{look_id}"
    mesh_path = f"/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/{look_id}/{mesh_name}"
    mesh = unreal.load_asset(mesh_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Missing first-batch look mesh: {mesh_path}")
    available = {str(name) for name in mesh.get_all_morph_target_names()}
    missing = sorted(required_morphs - available)
    expected_skeleton = source["expected_skeleton"]
    actual_skeleton = object_path(mesh.get_editor_property("skeleton"))
    look_records.append(
        {
            "look_id": look_id,
            "mesh": mesh.get_path_name(),
            "skeleton": actual_skeleton,
            "expected_skeleton": expected_skeleton,
            "required_morph_count": len(required_morphs),
            "missing_morphs": missing,
            "passed": actual_skeleton == expected_skeleton and not missing,
        }
    )

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
review_actor = actor_subsystem.spawn_actor_from_class(
    unreal.SkeletalMeshActor,
    unreal.Vector(18000.0, 18000.0, 0.0),
    unreal.Rotator(),
    transient=True,
)
if review_actor is None:
    raise RuntimeError("Unable to spawn transient Day 2 playback actor")
components = list(
    review_actor.get_components_by_class(unreal.SkeletalMeshComponent)
)
if len(components) != 1:
    actor_subsystem.destroy_actor(review_actor)
    raise RuntimeError("Transient Day 2 actor lacks one SkeletalMeshComponent")
component = components[0]
component.set_update_animation_in_editor(True)
component.set_allow_anim_curve_evaluation(True)
component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
component.set_editor_property("disable_post_process_blueprint", True)

motion_records = []
try:
    for source in motion_gate["records"]:
        action_id = source["action_id"]
        sex = source["sex"]
        animation = unreal.load_asset(source["body_only_animation"]["asset"])
        mesh = unreal.load_asset(CANONICAL_MESHES[sex])
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError(f"Missing BodyOnly animation: {action_id}")
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError(f"Missing canonical mesh: {sex}")
        skeleton = animation.get_editor_property("skeleton")
        skeleton_passed = mesh.get_editor_property("skeleton") == skeleton
        model = animation.data_model_interface
        track_names = {str(name) for name in model.get_bone_track_names()}
        frame_rate = model.get_frame_rate()
        frame_count = int(model.get_number_of_frames())
        window = source["window"]
        start_frame = max(
            0,
            min(
                frame_count - 1,
                int(round(window["start_seconds"] * frame_rate.numerator / frame_rate.denominator)),
            ),
        )
        end_frame = max(
            start_frame,
            min(
                frame_count - 1,
                int(round(window["source_end_seconds"] * frame_rate.numerator / frame_rate.denominator)),
            ),
        )
        sample_frames = sorted(
            {
                int(round(start_frame + (end_frame - start_frame) * index / 4.0))
                for index in range(5)
            }
        )
        sampled_bones = [bone for bone in MAJOR_BONES if bone in track_names]
        first_poses = {
            bone: frame_pose(animation, bone, sample_frames[0])
            for bone in sampled_bones
        }
        maximum_translation = 0.0
        maximum_rotation = 0.0
        for frame in sample_frames[1:]:
            for bone in sampled_bones:
                current = frame_pose(animation, bone, frame)
                maximum_translation = max(
                    maximum_translation,
                    vector_delta(first_poses[bone].translation, current.translation),
                )
                maximum_rotation = max(
                    maximum_rotation,
                    rotation_delta(first_poses[bone].rotation, current.rotation),
                )
        data_pose_observed = maximum_translation > 0.05 or maximum_rotation > 0.5

        component.set_skeletal_mesh_asset(mesh)
        component.override_animation_data(animation, False, False, 0.0, 1.0)
        component.play_animation(animation, False)
        component.set_play_rate(1.0)
        component_positions = []
        component_poses = []
        for frame in sample_frames:
            seconds = frame * frame_rate.denominator / frame_rate.numerator
            component.play_animation(animation, False)
            component.set_position(seconds, False)
            component.stop()
            refresh_component(component)
            component_positions.append(float(component.get_position()))
            component_poses.append(component_pose(component))
        component_position_passed = all(
            abs(
                component_positions[index]
                - sample_frames[index] * frame_rate.denominator / frame_rate.numerator
            )
            <= 0.04
            for index in range(len(sample_frames))
        )
        maximum_component_pose_delta = max(
            (
                component_pose_delta(component_poses[0], value)
                for value in component_poses[1:]
            ),
            default=0.0,
        )
        component_pose_observed = maximum_component_pose_delta > 0.05
        passed = (
            skeleton_passed
            and data_pose_observed
            and component_position_passed
            and source["checks"]["five_second_window_contract"]
            and source["checks"]["body_face_tracks_removed"]
            and source["checks"]["body_float_curves_removed"]
        )
        motion_records.append(
            {
                "action_id": action_id,
                "sex": sex,
                "animation": animation.get_path_name(),
                "mesh": mesh.get_path_name(),
                "skeleton_passed": skeleton_passed,
                "sample_frames": sample_frames,
                "component_positions_seconds": component_positions,
                "component_position_passed": component_position_passed,
                "maximum_component_pose_delta_cm": maximum_component_pose_delta,
                "component_pose_observed": component_pose_observed,
                "maximum_sampled_translation_delta_cm": maximum_translation,
                "maximum_sampled_rotation_delta_degrees": maximum_rotation,
                "data_pose_observed": data_pose_observed,
                "five_second_window_contract": source["checks"][
                    "five_second_window_contract"
                ],
                "face_tracks_removed": source["checks"][
                    "body_face_tracks_removed"
                ],
                "float_curves_removed": source["checks"][
                    "body_float_curves_removed"
                ],
                "passed": passed,
            }
        )
finally:
    actor_subsystem.destroy_actor(review_actor)
    actor_subsystem.set_selected_level_actors([])

expression_records = []
for source in expression_build["records"]:
    animation = unreal.load_asset(source["asset"])
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(f"Missing canonical expression clip: {source['asset']}")
    model = animation.data_model_interface
    curves = {
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            animation, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    }
    expected = set(profile["common_curves"])
    expression = next(
        item
        for item in profile["expressions"]
        if item["expression_id"] == source["expression_id"]
    )
    expected.update(expression["curves"])
    passed = (
        not list(model.get_bone_track_names())
        and curves == expected
        and source["success"]
    )
    expression_records.append(
        {
            "actor_id": source["actor_id"],
            "expression_id": source["expression_id"],
            "asset": animation.get_path_name(),
            "curve_count": len(curves),
            "bone_track_count": len(list(model.get_bone_track_names())),
            "passed": passed,
        }
    )

errors = []
if len(look_records) != 16 or not all(item["passed"] for item in look_records):
    errors.append("Not all 16 imported Looks support the canonical expression Morphs")
if len(motion_records) != 12 or not all(item["passed"] for item in motion_records):
    errors.append("Not all 12 BodyOnly actions passed binding and sampled-pose checks")
if len(expression_records) != 6 or not all(
    item["passed"] for item in expression_records
):
    errors.append("Canonical Happy/Angry/Sad expression clips are incomplete")
if not composition_build.get("success"):
    errors.append("Canonical body/expression AnimBlueprint composition failed")

report = {
    "schema_version": 1,
    "gate_id": "first_batch_day2_runtime_gate_20260822_v1",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "motion_import_gate": str(MOTION_GATE),
    "expression_profile": str(PROFILE_PATH),
    "canonical_expression_build": str(EXPRESSION_BUILD),
    "canonical_expression_composition": str(COMPOSITION_BUILD),
    "look_records": look_records,
    "motion_records": motion_records,
    "expression_records": expression_records,
    "counts": {
        "looks": len(look_records),
        "motions": len(motion_records),
        "expressions": len(expression_records),
    },
    "errors": errors,
    "component_pose_note": (
        "Editor-static SetPosition does not refresh rendered socket poses without a "
        "world tick. Component binding/position is checked for all 12 actions; actual "
        "PIE playback is checked by the six-case dynamic review."
    ),
    "automatic_success": not errors,
    "visual_review": "pending_dynamic_video_review",
    "production_status": "not_approved",
}
report["success"] = report["automatic_success"]
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
if errors:
    raise RuntimeError("Day 2 runtime gate failed: " + "; ".join(errors))
print(
    "DM_FIRST_BATCH_DAY2_RUNTIME="
    + json.dumps(
        {
            "report": str(REPORT_PATH),
            "looks": len(look_records),
            "motions": len(motion_records),
            "expressions": len(expression_records),
            "success": True,
        },
        sort_keys=True,
    )
)
