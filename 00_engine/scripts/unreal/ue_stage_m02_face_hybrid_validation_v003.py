"""Stage four editor actors for the M02 hybrid-face PIE review."""

from __future__ import annotations

import json

import unreal


CHARACTER_BLUEPRINT = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
TEST_ANIM_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003"
)
CONTROL_ANIM_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v002"
)
EXPECTED_COMPONENT_COUNT = 20
ACTOR_SPECS = (
    {
        "label": "DM_M02_FaceHybridTest_Audience_v003",
        "role": "test",
        "body_index": 0,
        "location": unreal.Vector(5000.0, 5000.0, 0.0),
    },
    {
        "label": "DM_M02_FaceHybridControl_Audience_v003",
        "role": "control",
        "body_index": 0,
        "location": unreal.Vector(8500.0, 8500.0, 0.0),
    },
    {
        "label": "DM_M02_FaceHybridTest_Walk_v003",
        "role": "test",
        "body_index": 1,
        "location": unreal.Vector(6000.0, 5000.0, 0.0),
    },
    {
        "label": "DM_M02_FaceHybridControl_Walk_v003",
        "role": "control",
        "body_index": 1,
        "location": unreal.Vector(9500.0, 8500.0, 0.0),
    },
)
STALE_LABELS = {spec["label"] for spec in ACTOR_SPECS}


def load_blueprint(path):
    asset = unreal.load_asset(path)
    if not isinstance(asset, unreal.Blueprint):
        raise RuntimeError(f"Blueprint unavailable: {path}")
    return asset


def find_body(actor):
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    body = next((item for item in components if item.get_name() == "Body"), None)
    if body is None:
        raise RuntimeError(f"Actor has no Body component: {actor.get_actor_label()}")
    return components, body


def configure_body(body):
    body.set_update_animation_in_editor(True)
    body.set_allow_anim_curve_evaluation(True)
    body.set_component_tick_enabled(True)
    body.set_enable_animation(True)
    body.propagate_curves_to_followers = True


character = load_blueprint(CHARACTER_BLUEPRINT)
test_anim = unreal.load_asset(TEST_ANIM_BLUEPRINT)
control_anim = unreal.load_asset(CONTROL_ANIM_BLUEPRINT)
if not isinstance(test_anim, unreal.AnimBlueprint):
    raise RuntimeError(f"Test AnimBlueprint unavailable: {TEST_ANIM_BLUEPRINT}")
if not isinstance(control_anim, unreal.AnimBlueprint):
    raise RuntimeError(f"Control AnimBlueprint unavailable: {CONTROL_ANIM_BLUEPRINT}")
if test_anim.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
    raise RuntimeError(f"Test AnimBlueprint is not compiled: {test_anim.get_editor_property('status')}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed = []
for existing in actor_subsystem.get_all_level_actors():
    if existing.get_actor_label() in STALE_LABELS:
        removed.append(existing.get_path_name())
        actor_subsystem.destroy_actor(existing)

records = []
actors = {}
try:
    for spec in ACTOR_SPECS:
        actor = actor_subsystem.spawn_actor_from_class(
            character.generated_class(),
            spec["location"],
            unreal.Rotator(),
            transient=False,
        )
        if actor is None:
            raise RuntimeError(f"Unable to stage actor: {spec['label']}")
        actor.set_actor_label(spec["label"])
        actors[spec["label"]] = actor
        components, body = find_body(actor)
        if len(components) != EXPECTED_COMPONENT_COUNT:
            raise RuntimeError(
                f"Expected {EXPECTED_COMPONENT_COUNT} components on "
                f"{spec['label']}, found {len(components)}"
            )
        configure_body(body)
        followers_without_leader = [
            component.get_name()
            for component in components
            if component != body
            and component.get_editor_property("leader_pose_component") != body
        ]
        records.append(
            {
                "label": spec["label"],
                "role": spec["role"],
                "body_index": spec["body_index"],
                "actor": actor.get_path_name(),
                "component_count": len(components),
                "follower_count": len(components) - 1,
                "followers_without_body_leader": followers_without_leader,
            }
        )
except Exception:
    for actor in actors.values():
        actor_subsystem.destroy_actor(actor)
    raise

preview_actor = actors["DM_M02_FaceHybridTest_Audience_v003"]
preview_location = preview_actor.get_actor_location()
head_location = preview_location + unreal.Vector(0.0, 0.0, 168.0)
camera_location = head_location + unreal.Vector(0.0, 58.0, 2.0)
camera_rotation = unreal.MathLibrary.find_look_at_rotation(
    camera_location, head_location + unreal.Vector(0.0, 0.0, 1.0)
)
unreal.get_editor_subsystem(
    unreal.UnrealEditorSubsystem
).set_level_viewport_camera_info(camera_location, camera_rotation)
actor_subsystem.set_selected_level_actors([])

globals()["_dm_m02_face_hybrid_stage_actors"] = actors
errors = [
    f"{record['label']}: {name}"
    for record in records
    for name in record["followers_without_body_leader"]
]
print(
    "DM_FACE_HYBRID_STAGE="
    + json.dumps(
        {
            "actor_count": len(records),
            "actors": records,
            "removed": removed,
            "errors": errors,
            "success": not errors,
        },
        sort_keys=True,
    )
)
