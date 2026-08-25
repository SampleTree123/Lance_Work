"""Stage modular and integrated male characters with the same source motion."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


MODULAR_LABEL = "DM_M02_MotionValidation"
INTEGRATED_LABEL = "DM_M02_IntegratedMotionComparison"
STALE_INTEGRATED_LABELS = {"DM_M01_IntegratedMotionComparison", INTEGRATED_LABEL}
INTEGRATED_MESH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/"
    "CC_M02_Average_Pilot_UE58"
)
INTEGRATED_ANIMATION = (
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Comparisons/M02_Modular/"
    "A_DM_M01_BATTLE_DANCE_M02ModularCompare_v001"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\first_batch_motions_20260822_v1\clothing_architecture_compare_stage.json"
)


def object_path(value):
    return value.get_path_name() if value is not None else None


actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_subsystem.get_all_level_actors()
modular = next(
    (actor for actor in actors if actor.get_actor_label() == MODULAR_LABEL), None
)
if modular is None:
    raise RuntimeError(
        "Modular M02 comparison actor is missing; run the modular stage first"
    )
for actor in actors:
    if actor.get_actor_label() in STALE_INTEGRATED_LABELS:
        actor_subsystem.destroy_actor(actor)

mesh = unreal.load_asset(INTEGRATED_MESH)
animation = unreal.load_asset(INTEGRATED_ANIMATION)
if not isinstance(mesh, unreal.SkeletalMesh):
    raise RuntimeError(f"Integrated comparison mesh unavailable: {INTEGRATED_MESH}")
if not isinstance(animation, unreal.AnimSequence):
    raise RuntimeError(
        f"Integrated comparison animation unavailable: {INTEGRATED_ANIMATION}"
    )
if mesh.get_editor_property("skeleton") != animation.get_editor_property("skeleton"):
    raise RuntimeError("Integrated mesh/animation skeleton mismatch")

modular.set_actor_location(unreal.Vector(300.0, -110.0, 0.0), False, False)
integrated = actor_subsystem.spawn_actor_from_class(
    unreal.SkeletalMeshActor,
    unreal.Vector(300.0, 110.0, 0.0),
    unreal.Rotator(0.0, 0.0, 0.0),
    transient=False,
)
if integrated is None:
    raise RuntimeError("Unable to spawn integrated comparison actor")
integrated.set_actor_label(INTEGRATED_LABEL)
component = integrated.get_editor_property("skeletal_mesh_component")
component.set_skeletal_mesh_asset(mesh)
component.override_animation_data(animation, True, True, 0.0, 1.0)
component.set_update_animation_in_editor(True)
if hasattr(component, "tick_animation"):
    component.tick_animation(0.0, False)
if hasattr(component, "refresh_bone_transforms"):
    component.refresh_bone_transforms()
if hasattr(component, "mark_render_dynamic_data_dirty"):
    component.mark_render_dynamic_data_dirty()

modular_components = modular.get_components_by_class(unreal.SkeletalMeshComponent)
modular_body = next(
    (item for item in modular_components if item.get_name() == "Body"), None
)
if modular_body is None:
    raise RuntimeError("Modular comparison actor has no Body component")
followers = [item for item in modular_components if item != modular_body]
followers_without_leader = [
    item.get_name()
    for item in followers
    if item.get_editor_property("leader_pose_component") != modular_body
]
if followers_without_leader:
    raise RuntimeError(
        "Modular followers are not bound to Body: "
        + ", ".join(followers_without_leader)
    )

actor_subsystem.set_selected_level_actors([modular, integrated])
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
level_subsystem.editor_set_viewport_realtime(True)
level_subsystem.editor_invalidate_viewports()

report = {
    "source_motion": "ACT_M01_BATTLE_DANCE",
    "modular": {
        "actor": modular.get_path_name(),
        "component_count": len(modular_components),
        "leader_followers": len(followers),
        "followers_without_leader": followers_without_leader,
        "body_animation": object_path(
            modular_body.get_editor_property("animation_data").get_editor_property(
                "anim_to_play"
            )
        ),
    },
    "integrated": {
        "actor": integrated.get_path_name(),
        "component_count": 1,
        "mesh": mesh.get_path_name(),
        "animation": animation.get_path_name(),
    },
    "viewport_realtime": level_subsystem.editor_get_game_view() is not None,
    "success": True,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
    encoding="utf-8",
)
print("DM_CLOTHING_ARCH_COMPARE=" + json.dumps(report, ensure_ascii=False))
