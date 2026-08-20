"""Stage a temporary M02 actor with concurrent body motion and face expression."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


BLUEPRINT_PATH = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
CONFIG_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\unreal"
    r"\ue_m02_body_face_demo_config.json"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_body_face_demo_stage.json"
)
ACTOR_LABEL = "DM_M02_BodyFaceDemo"


def object_path(value):
    return value.get_path_name() if value is not None else None


def vector(values):
    return unreal.Vector(float(values[0]), float(values[1]), float(values[2]))


def rotator(values):
    return unreal.Rotator(
        pitch=float(values[0]),
        yaw=float(values[1]),
        roll=float(values[2]),
    )


def morph_names(component):
    mesh = component.get_skeletal_mesh_asset()
    if mesh is None:
        return set()
    return {str(name) for name in mesh.get_all_morph_target_names()}


def refresh_component(component):
    if hasattr(component, "tick_animation"):
        component.tick_animation(0.0, False)
    if hasattr(component, "refresh_bone_transforms"):
        component.refresh_bone_transforms()
    if hasattr(component, "mark_render_dynamic_data_dirty"):
        component.mark_render_dynamic_data_dirty()


def clean_previous(actor_subsystem):
    removed = []
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == ACTOR_LABEL:
            removed.append(actor.get_path_name())
            actor_subsystem.destroy_actor(actor)
    return removed


config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
animation_path = str(config["animation_path"])
play_mode = str(config.get("play_mode", "static"))
normalized_time = float(config.get("normalized_time", 0.5))
play_rate = float(config.get("play_rate", 1.0))
expressions = {
    str(name): float(weight)
    for name, weight in config.get("expressions", {}).items()
}

if play_mode not in {"static", "live"}:
    raise RuntimeError(f"Unsupported play_mode: {play_mode}")
if not 0.0 <= normalized_time <= 1.0:
    raise RuntimeError("normalized_time must be between 0 and 1")
if any(not 0.0 <= value <= 1.0 for value in expressions.values()):
    raise RuntimeError("Expression weights must be between 0 and 1")

blueprint = unreal.load_asset(BLUEPRINT_PATH)
animation = unreal.load_asset(animation_path)
if not isinstance(blueprint, unreal.Blueprint):
    raise RuntimeError(f"Blueprint is unavailable: {BLUEPRINT_PATH}")
if not isinstance(animation, unreal.AnimSequence):
    raise RuntimeError(f"Animation is unavailable: {animation_path}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed_previous = clean_previous(actor_subsystem)
actor = actor_subsystem.spawn_actor_from_class(
    blueprint.generated_class(),
    vector(config.get("actor_location", [450.0, 20.0, 0.0])),
    rotator(config.get("actor_rotation", [0.0, 0.0, 0.0])),
    transient=False,
)
if actor is None:
    raise RuntimeError("Unable to spawn body/face demonstration actor")
actor.set_actor_label(ACTOR_LABEL)

components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    actor_subsystem.destroy_actor(actor)
    raise RuntimeError("Demonstration actor has no Body component")

sample_time = animation.get_play_length() * normalized_time
body.set_update_animation_in_editor(True)
body.set_allow_anim_curve_evaluation(True)
body.propagate_curves_to_followers = True
body.override_animation_data(
    animation,
    play_mode == "live",
    play_mode == "live",
    sample_time if play_mode == "static" else 0.0,
    play_rate,
)
body.play_animation(animation, play_mode == "live")
body.set_play_rate(play_rate)
if play_mode == "static":
    body.set_position(sample_time, False)
    body.stop()

# Animation setup can reconstruct editor components, so reacquire them before
# applying Morphs through the Blueprint's reusable broadcast function.
components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    actor_subsystem.destroy_actor(actor)
    raise RuntimeError("Body component is unavailable after animation setup")
body.set_update_animation_in_editor(True)

for morph_name, weight in expressions.items():
    actor.call_method("BroadcastFaceMorph", (morph_name, weight, False))

for component in components:
    refresh_component(component)

component_records = []
for component in components:
    leader = component.get_editor_property("leader_pose_component")
    component_records.append(
        {
            "name": component.get_name(),
            "mesh": object_path(component.get_skeletal_mesh_asset()),
            "leader": leader.get_name() if leader is not None else None,
            "expressions": {
                morph_name: {
                    "supports_morph": morph_name in morph_names(component),
                    "weight": float(component.get_morph_target(morph_name)),
                }
                for morph_name in expressions
            },
        }
    )

actor_subsystem.set_selected_level_actors([actor])
camera_location = config.get("viewport_camera_location")
camera_rotation = config.get("viewport_camera_rotation")
if camera_location is not None and camera_rotation is not None:
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        vector(camera_location), rotator(camera_rotation)
    )

followers = [item for item in component_records if item["name"] != "Body"]
errors = []
followers_without_body_leader = [
    item["name"] for item in followers if item["leader"] != "Body"
]
if followers_without_body_leader:
    errors.append(
        "Followers without Body leader: " + ", ".join(followers_without_body_leader)
    )

for morph_name, requested_weight in expressions.items():
    supported = [
        item
        for item in component_records
        if item["expressions"][morph_name]["supports_morph"]
    ]
    mismatched = [
        item["name"]
        for item in supported
        if abs(
            item["expressions"][morph_name]["weight"] - requested_weight
        )
        > 1.0e-5
    ]
    if mismatched:
        errors.append(
            f"Morph {morph_name} mismatched on: {', '.join(mismatched)}"
        )

report = {
    "actor": actor.get_path_name(),
    "actor_label": actor.get_actor_label(),
    "blueprint": blueprint.get_path_name(),
    "animation": animation.get_path_name(),
    "animation_skeleton": object_path(animation.get_editor_property("skeleton")),
    "play_mode": play_mode,
    "play_rate": play_rate,
    "play_length_seconds": animation.get_play_length(),
    "normalized_time": normalized_time,
    "sample_time_seconds": sample_time,
    "evaluated_position_seconds": body.get_position(),
    "propagate_curves_to_followers": body.propagate_curves_to_followers,
    "animation_curve_values": {
        str(name): body.get_anim_instance().get_curve_value(str(name))
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            animation, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    },
    "expressions": expressions,
    "component_count": len(component_records),
    "followers_without_body_leader": followers_without_body_leader,
    "removed_previous_actors": removed_previous,
    "components": sorted(component_records, key=lambda item: item["name"]),
    "errors": errors,
    "success": not errors,
}

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
if not report["success"]:
    raise RuntimeError(f"Body/face demo staging failed: {report['errors']}")

print(
    "DM_BODY_FACE_STAGE="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "actor": report["actor"],
            "blueprint": report["blueprint"],
            "animation": report["animation"],
            "play_mode": report["play_mode"],
            "expressions": report["expressions"],
            "component_count": report["component_count"],
            "followers_without_body_leader": report[
                "followers_without_body_leader"
            ],
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
