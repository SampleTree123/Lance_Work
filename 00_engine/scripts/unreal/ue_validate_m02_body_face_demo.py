"""Validate the M02 body-motion and facial-expression demo in PIE."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ACTOR_LABEL = "DM_M02_BodyFaceDemo"
EXPECTED_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "A_CC_Audience_F_01_BodyFaceDemo_v001"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_body_face_demo_validation.json"
)


editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = editor_subsystem.get_game_world()
if game_world is None:
    raise RuntimeError("PIE/Simulate world is not running")

actors = unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor)
actor = next(
    (item for item in actors if item.get_actor_label() == ACTOR_LABEL), None
)
if actor is None:
    raise RuntimeError(f"PIE actor is unavailable: {ACTOR_LABEL}")

components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    raise RuntimeError("PIE actor has no Body component")
instance = body.get_anim_instance()
if instance is None:
    raise RuntimeError("Body animation instance is unavailable")
animation = instance.get_animation_asset()
if not isinstance(animation, unreal.AnimSequence):
    raise RuntimeError("Body is not playing an AnimSequence")

curve_names = [
    "CTRL_expressions_eyeBlinkL",
    "CTRL_expressions_eyeBlinkR",
    "CTRL_expressions_mouthCornerPullL",
    "CTRL_expressions_mouthCornerPullR",
]
sample_times = [0.0, 0.96, 1.50, 2.49, animation.get_play_length()]
curve_samples = {
    str(time_value): {
        name: unreal.AnimationLibrary.get_float_value_at_time(
            animation, name, time_value
        )
        for name in curve_names
    }
    for time_value in sample_times
}

followers = [item for item in components if item != body]
followers_without_body_leader = [
    item.get_name()
    for item in followers
    if item.get_editor_property("leader_pose_component") != body
]
runtime_values = {
    name: instance.get_curve_value(name) for name in curve_names
}
errors = []
if animation.get_path_name().split(".", 1)[0] != EXPECTED_ANIMATION:
    errors.append(f"Unexpected PIE animation: {animation.get_path_name()}")
if followers_without_body_leader:
    errors.append(
        "Followers without Body leader: "
        + ", ".join(followers_without_body_leader)
    )
if not body.propagate_curves_to_followers:
    errors.append("Body curve propagation to followers is disabled")
if curve_samples["0.96"]["CTRL_expressions_eyeBlinkL"] < 0.95:
    errors.append("First blink curve does not reach its expected peak")
if curve_samples["2.49"]["CTRL_expressions_eyeBlinkR"] < 0.95:
    errors.append("Second blink curve does not reach its expected peak")
if curve_samples["1.5"]["CTRL_expressions_mouthCornerPullL"] < 0.55:
    errors.append("Smile curve does not reach its expected plateau")

report = {
    "world": game_world.get_path_name(),
    "actor": actor.get_path_name(),
    "animation": animation.get_path_name(),
    "animation_position_seconds": body.get_position(),
    "is_playing": body.is_playing(),
    "component_count": len(components),
    "follower_count": len(followers),
    "followers_without_body_leader": followers_without_body_leader,
    "propagate_curves_to_followers": body.propagate_curves_to_followers,
    "runtime_curve_values": runtime_values,
    "curve_samples": curve_samples,
    "errors": errors,
    "success": not errors,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
if errors:
    raise RuntimeError(f"Body/face demo validation failed: {errors}")

print(
    "DM_BODY_FACE_VALIDATION="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "animation": report["animation"],
            "component_count": report["component_count"],
            "follower_count": report["follower_count"],
            "runtime_curve_values": report["runtime_curve_values"],
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
