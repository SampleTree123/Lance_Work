"""Stage F02/M02 P0 wrapper actors for a transient PIE validation run."""

from __future__ import annotations

import json

import unreal


CHARACTERS = {
    "F02": (
        "/Game/DataMake/Characters/P0RuntimePilot/F02/"
        "BP_DM_F02_P0RuntimePilot_v001"
    ),
    "M02": (
        "/Game/DataMake/Characters/P0RuntimePilot/M02/"
        "BP_DM_M02_P0RuntimePilot_v001"
    ),
}

ACTOR_SPECS = (
    {
        "actor_id": "F02",
        "body_id": "walk",
        "body_index": 0,
        "label": "DM_P0_F02_Walk",
        "location": unreal.Vector(5000.0, 5000.0, 0.0),
    },
    {
        "actor_id": "F02",
        "body_id": "idle",
        "body_index": 1,
        "label": "DM_P0_F02_Idle",
        "location": unreal.Vector(6500.0, 5000.0, 0.0),
    },
    {
        "actor_id": "M02",
        "body_id": "walk",
        "body_index": 0,
        "label": "DM_P0_M02_Walk",
        "location": unreal.Vector(8000.0, 5000.0, 0.0),
    },
    {
        "actor_id": "M02",
        "body_id": "understood",
        "body_index": 1,
        "label": "DM_P0_M02_Understood",
        "location": unreal.Vector(9500.0, 5000.0, 0.0),
    },
)
STALE_LABELS = {spec["label"] for spec in ACTOR_SPECS}
DISABLE_POST_PROCESS_BLUEPRINT = True


def load_blueprint(path):
    asset = unreal.load_asset(path)
    if not isinstance(asset, unreal.Blueprint):
        raise RuntimeError(f"P0 wrapper Blueprint unavailable: {path}")
    if asset.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError(
            f"P0 wrapper Blueprint is not compiled: {path} "
            f"({asset.get_editor_property('status')})"
        )
    return asset


def find_body(actor):
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    if len(components) != 1:
        raise RuntimeError(
            f"Expected one SkeletalMeshComponent on {actor.get_actor_label()}, "
            f"found {len(components)}"
        )
    return components[0]


wrappers = {key: load_blueprint(path) for key, path in CHARACTERS.items()}
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

removed = []
for existing in actor_subsystem.get_all_level_actors():
    if existing.get_actor_label() in STALE_LABELS:
        removed.append(existing.get_path_name())
        actor_subsystem.destroy_actor(existing)

staged = []
created = []
try:
    for spec in ACTOR_SPECS:
        wrapper = wrappers[spec["actor_id"]]
        actor = actor_subsystem.spawn_actor_from_class(
            wrapper.generated_class(),
            spec["location"],
            unreal.Rotator(),
            transient=False,
        )
        if actor is None:
            raise RuntimeError(f"Unable to stage actor: {spec['label']}")
        created.append(actor)
        actor.set_actor_label(spec["label"])

        body = find_body(actor)
        mesh = body.get_skeletal_mesh_asset()
        anim_class = body.get_editor_property("anim_class")
        if mesh is None or anim_class is None:
            raise RuntimeError(f"Incomplete staged body: {spec['label']}")
        body.set_update_animation_in_editor(True)
        body.set_allow_anim_curve_evaluation(True)
        body.set_component_tick_enabled(True)
        body.set_enable_animation(True)
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        body.set_editor_property(
            "disable_post_process_blueprint",
            DISABLE_POST_PROCESS_BLUEPRINT,
        )
        if not body.get_editor_property("disable_post_process_blueprint"):
            raise RuntimeError(
                f"Direct-Morph wrapper retained its post-process Blueprint: "
                f"{spec['label']}"
            )

        staged.append(
            {
                **{key: value for key, value in spec.items() if key != "location"},
                "actor": actor.get_path_name(),
                "anim_class": anim_class.get_path_name(),
                "mesh": mesh.get_path_name(),
                "disable_post_process_blueprint": body.get_editor_property(
                    "disable_post_process_blueprint"
                ),
                "post_process_anim_blueprint": (
                    mesh.get_editor_property("post_process_anim_blueprint").get_path_name()
                    if mesh.get_editor_property("post_process_anim_blueprint")
                    else None
                ),
            }
        )
except Exception:
    for actor in created:
        actor_subsystem.destroy_actor(actor)
    raise

actor_subsystem.set_selected_level_actors([])
globals()["_dm_p0_runtime_stage_labels"] = sorted(STALE_LABELS)
print(
    "DM_P0_RUNTIME_STAGE="
    + json.dumps(
        {
            "actor_count": len(staged),
            "actors": staged,
            "removed": removed,
            "success": len(staged) == len(ACTOR_SPECS),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
