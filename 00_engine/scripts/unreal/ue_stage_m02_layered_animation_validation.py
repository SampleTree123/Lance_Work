"""Stage the unsaved editor actor used by the Phase 1 PIE matrix."""

from __future__ import annotations

import json

import unreal


CHARACTER_BLUEPRINT = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
ANIM_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v002"
)
ACTOR_LABEL = "DM_M02_LayeredAnimValidation"
STALE_LABELS = {ACTOR_LABEL, "DM_M02_LayeredRuntimeProbe"}


character_bp = unreal.load_asset(CHARACTER_BLUEPRINT)
anim_bp = unreal.load_asset(ANIM_BLUEPRINT)
if not isinstance(character_bp, unreal.Blueprint):
    raise RuntimeError(f"Character Blueprint unavailable: {CHARACTER_BLUEPRINT}")
if not isinstance(anim_bp, unreal.AnimBlueprint):
    raise RuntimeError(f"AnimBlueprint unavailable: {ANIM_BLUEPRINT}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed = []
for existing in actor_subsystem.get_all_level_actors():
    if existing.get_actor_label() in STALE_LABELS:
        removed.append(existing.get_path_name())
        actor_subsystem.destroy_actor(existing)

actor = actor_subsystem.spawn_actor_from_class(
    character_bp.generated_class(),
    unreal.Vector(450.0, 20.0, 0.0),
    unreal.Rotator(),
    transient=False,
)
if actor is None:
    raise RuntimeError("Unable to stage layered-animation validation actor")
actor.set_actor_label(ACTOR_LABEL)

components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    actor_subsystem.destroy_actor(actor)
    raise RuntimeError("Validation actor has no Body component")
body.set_update_animation_in_editor(True)
body.set_allow_anim_curve_evaluation(True)
body.set_component_tick_enabled(True)
body.set_enable_animation(True)
body.propagate_curves_to_followers = True
body.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
body.set_anim_instance_class(anim_bp.generated_class())

followers = [item for item in components if item != body]
followers_without_body_leader = [
    item.get_name()
    for item in followers
    if item.get_editor_property("leader_pose_component") != body
]
actor_subsystem.set_selected_level_actors([actor])
globals()["_dm_m02_layered_validation_actor"] = actor
print(
    "DM_LAYERED_VALIDATION_STAGED="
    + json.dumps(
        {
            "actor": actor.get_path_name(),
            "component_count": len(components),
            "follower_count": len(followers),
            "followers_without_body_leader": followers_without_body_leader,
            "removed": removed,
            "success": not followers_without_body_leader,
        },
        sort_keys=True,
    )
)
