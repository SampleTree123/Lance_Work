"""Stage six transient first-batch expression review actors."""

from __future__ import annotations

import json

import unreal


TARGET = str(globals().get("DM_FIRST_BATCH_EXPRESSION_TARGET", "legacy"))
CHARACTERS = {
    "F02": (
        "/Game/DataMake/Characters/FirstBatchExpressionReview/F02/"
        "BP_DM_F02_FirstBatchExpressionReview_v001"
    ),
    "M02": (
        "/Game/DataMake/Characters/FirstBatchExpressionReview/M02/"
        "BP_DM_M02_FirstBatchExpressionReview_v001"
    ),
}
if TARGET == "canonical":
    CHARACTERS = {
        actor_id: (
            f"/Game/DataMake/Characters/FirstDataBatch/ExpressionReview/{actor_id}/"
            f"BP_DM_{actor_id}_FirstBatchExpressionReview_v001"
        )
        for actor_id in ("FB_F", "FB_M")
    }
EXPRESSIONS = ("happy", "angry", "sad")
ACTOR_SPECS = tuple(
    {
        "actor_id": actor_id,
        "expression_id": expression_id,
        "expression_index": expression_index,
        "pair_index": expression_index // 2,
        "variant_index": expression_index % 2,
        "label": f"DM_FBEXP_{actor_id}_{expression_id.title()}",
        "location": unreal.Vector(
            5000.0 + actor_cursor * 2400.0 + expression_index * 700.0,
            7000.0,
            0.0,
        ),
    }
    for actor_cursor, actor_id in enumerate(tuple(CHARACTERS))
    for expression_index, expression_id in enumerate(EXPRESSIONS)
)
STALE_LABELS = {item["label"] for item in ACTOR_SPECS}


def load_blueprint(path):
    asset = unreal.load_asset(path)
    if not isinstance(asset, unreal.Blueprint):
        raise RuntimeError(f"Expression wrapper unavailable: {path}")
    if asset.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError(f"Expression wrapper is not compiled: {path}")
    return asset


def find_body(actor):
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    if len(components) != 1:
        raise RuntimeError(
            f"Expected one Body component on {actor.get_actor_label()}, "
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

created = []
staged = []
try:
    for spec in ACTOR_SPECS:
        actor = actor_subsystem.spawn_actor_from_class(
            wrappers[spec["actor_id"]].generated_class(),
            spec["location"],
            unreal.Rotator(),
            transient=False,
        )
        if actor is None:
            raise RuntimeError(f"Unable to stage {spec['label']}")
        created.append(actor)
        actor.set_actor_label(spec["label"])
        body = find_body(actor)
        body.set_update_animation_in_editor(True)
        body.set_allow_anim_curve_evaluation(True)
        body.set_component_tick_enabled(True)
        body.set_enable_animation(True)
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        body.set_editor_property("disable_post_process_blueprint", True)
        staged.append(
            {
                **{key: value for key, value in spec.items() if key != "location"},
                "actor": actor.get_path_name(),
                "mesh": body.get_skeletal_mesh_asset().get_path_name(),
                "anim_class": body.get_editor_property("anim_class").get_path_name(),
            }
        )
except Exception:
    for actor in created:
        actor_subsystem.destroy_actor(actor)
    raise

actor_subsystem.set_selected_level_actors([])
globals()["_dm_first_batch_expression_stage_labels"] = sorted(STALE_LABELS)
print(
    "DM_FIRST_BATCH_EXPRESSION_STAGE="
    + json.dumps(
        {
            "target": TARGET,
            "actor_count": len(staged),
            "actors": staged,
            "removed": removed,
            "success": len(staged) == len(ACTOR_SPECS),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
