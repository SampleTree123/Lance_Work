"""Stage a temporary modular M02 actor for body-motion and facial-morph validation."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


BLUEPRINT_PATH = "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v001"
CONFIG_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\unreal"
    r"\ue_m02_motion_stage_config.json"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_modular_motion_stage.json"
)
ACTOR_LABEL = "DM_M02_MotionValidation"
DEFAULT_MORPH = "CTRL_expressions_eyeBlinkL"


def object_path(value):
    return value.get_path_name() if value is not None else None


def vector_record(value):
    return {"x": value.x, "y": value.y, "z": value.z}


def clean_previous_actor(actor_subsystem):
    removed = []
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == ACTOR_LABEL:
            removed.append(actor.get_path_name())
            actor_subsystem.destroy_actor(actor)
    return removed


def component_morph_names(component):
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


config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
animation_path = config["animation_path"]
normalized_time = float(config.get("normalized_time", 0.5))
morph_name = str(config.get("morph_name", DEFAULT_MORPH))
morph_weight = float(config.get("morph_weight", 1.0))
morph_mode = str(config.get("morph_mode", "broadcast"))

if not 0.0 <= normalized_time <= 1.0:
    raise RuntimeError("normalized_time must be between 0 and 1")
if morph_mode not in {"none", "body_only", "broadcast"}:
    raise RuntimeError(f"Unsupported morph_mode: {morph_mode}")

blueprint = unreal.load_asset(BLUEPRINT_PATH)
animation = unreal.load_asset(animation_path)
if not isinstance(blueprint, unreal.Blueprint):
    raise RuntimeError(f"Modular Blueprint is unavailable: {BLUEPRINT_PATH}")
if not isinstance(animation, unreal.AnimSequence):
    raise RuntimeError(f"Animation is unavailable: {animation_path}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed_actors = clean_previous_actor(actor_subsystem)
actor = actor_subsystem.spawn_actor_from_class(
    blueprint.generated_class(),
    unreal.Vector(300.0, 0.0, 0.0),
    unreal.Rotator(0.0, 0.0, 0.0),
    transient=False,
)
if actor is None:
    raise RuntimeError("Unable to spawn a temporary modular actor")
actor.set_actor_label(ACTOR_LABEL)

components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    actor_subsystem.destroy_actor(actor)
    raise RuntimeError("Spawned modular actor has no Body component")

sample_time = animation.get_play_length() * normalized_time
body.override_animation_data(animation, False, False, sample_time, 1.0)

# OverrideAnimationData survives this Blueprint's editor-side reconstruction.
components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    actor_subsystem.destroy_actor(actor)
    raise RuntimeError("Body component is unavailable after animation setup")
body.set_update_animation_in_editor(True)
refresh_component(body)

component_records = []
for component in components:
    morphs = component_morph_names(component)
    leader = component.get_editor_property("leader_pose_component")
    component_records.append(
        {
            "name": component.get_name(),
            "mesh": object_path(component.get_skeletal_mesh_asset()),
            "leader": leader.get_name() if leader is not None else None,
            "supports_morph": morph_name in morphs,
            "morph_weight_before": component.get_morph_target(morph_name),
        }
    )

if morph_mode == "body_only":
    body.set_morph_target(morph_name, morph_weight, False)
elif morph_mode == "broadcast":
    for component, record in zip(components, component_records):
        if record["supports_morph"]:
            component.set_morph_target(morph_name, morph_weight, False)

for component, record in zip(components, component_records):
    refresh_component(component)
    record["morph_weight_after"] = component.get_morph_target(morph_name)

origin, extent = actor.get_actor_bounds(False, True)
followers = [item for item in component_records if item["name"] != "Body"]
report = {
    "actor": actor.get_path_name(),
    "actor_label": actor.get_actor_label(),
    "blueprint": blueprint.get_path_name(),
    "animation": animation.get_path_name(),
    "animation_skeleton": object_path(animation.get_editor_property("skeleton")),
    "play_length_seconds": animation.get_play_length(),
    "normalized_time": normalized_time,
    "sample_time_seconds": sample_time,
    "component_count": len(components),
    "followers_without_body_leader": [
        item["name"] for item in followers if item["leader"] != "Body"
    ],
    "morph_name": morph_name,
    "morph_mode": morph_mode,
    "morph_weight": morph_weight,
    "morph_support_count": sum(
        1 for item in component_records if item["supports_morph"]
    ),
    "morph_applied_count": sum(
        1
        for item in component_records
        if abs(float(item["morph_weight_after"]) - morph_weight) < 1e-6
    ),
    "actor_bounds": {
        "origin": vector_record(origin),
        "extent": vector_record(extent),
    },
    "removed_previous_actors": removed_actors,
    "components": sorted(component_records, key=lambda item: item["name"]),
}

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_MOTION_STAGE="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "actor": report["actor"],
            "animation": report["animation"],
            "sample_time_seconds": report["sample_time_seconds"],
            "component_count": report["component_count"],
            "followers_without_body_leader": report[
                "followers_without_body_leader"
            ],
            "morph_mode": report["morph_mode"],
            "morph_support_count": report["morph_support_count"],
            "morph_applied_count": report["morph_applied_count"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
