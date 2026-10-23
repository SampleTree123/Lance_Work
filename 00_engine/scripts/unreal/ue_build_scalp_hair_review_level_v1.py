"""Stage the imported hb1-01 scalp hair on male and female review actors.

This is a visual probe only.  It deliberately keeps hair as separate
SkeletalMeshActor instances because the current modular outfit Blueprint has
no hair slot.  The saved level is therefore suitable for manual inspection,
not a declaration that cross-skeleton hair compatibility has been accepted.
"""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_build_scalp_hair_review_level_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import unreal


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
RUNTIME_WORKER = SCRIPT_ROOT / "ue_build_modular_outfit_runtime_v2.py"
PLAN_PATH = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "asset_restructure_full_20260929_v1"
    / "review_plans"
    / "modular_runtime_v2"
    / "runtime_plan_v2.json"
)
REPORT_PATH = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "scalp_hair_pilot_20260923_111307_interchange"
    / "hair_visual_review_level_v001.json"
)
LEVEL_PATH = "/Game/DataMake/Validation/ScalpHairPilot/L_DM_ScalpHairPilot_Review_v001"
REVIEW_VARIANTS = {
    "M02_Average": "M_1920_LAYERED::coat_on",
    "F02_Average": "F_BIKINI_LAYERED::cover_and_shoes",
}
ACTOR_LOCATIONS = {
    "M02_Average": unreal.Vector(0.0, -120.0, 0.0),
    "F02_Average": unreal.Vector(0.0, 120.0, 0.0),
}
MOTION_ASSETS = {
    "M02_Average": "/Game/DataMake/Animations/CC5/ModularOutfitPilot/M02_Average/A_DM_M02_AUDIENCE_01_ModularPilot_v001",
    "F02_Average": "/Game/DataMake/Animations/CC5/ModularOutfitPilot/F02_Average/A_DM_F03_AUDIENCE_01_ModularPilot_v001",
}
HAIR_MESHES = [
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/hair_base",
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/side_bangs",
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/curly_long_hair",
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/curly_ponytail_back",
]
HAIR_SKELETON = "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/Cases/F_BASE/FullReference/CC_MOD_F_BASE_UE58_Skeleton"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Unable to load worker: {path}")
    spec.loader.exec_module(module)
    return module


RUNTIME = load_module("dm_modular_runtime_scalp_hair_review_v1", RUNTIME_WORKER)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_report(value: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT_PATH.with_name(REPORT_PATH.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(REPORT_PATH)


def spawn_actor(actor_class, location, rotation=unreal.Rotator()):
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        actor_class, location, rotation, transient=False
    )
    if actor is None:
        raise RuntimeError(f"Unable to spawn actor: {actor_class}")
    return actor


def required_component(actor, component_class):
    component = actor.get_component_by_class(component_class)
    if component is None:
        raise RuntimeError(f"{actor.get_name()} has no {component_class.__name__} component")
    return component


def configure_body_animation(body, animation) -> None:
    body.set_update_animation_in_editor(True)
    body.set_component_tick_enabled(True)
    body.set_enable_animation(True)
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    body.override_animation_data(animation, True, True, 0.0, 1.0)
    if hasattr(body, "tick_animation"):
        body.tick_animation(0.0, False)
    if hasattr(body, "refresh_bone_transforms"):
        body.refresh_bone_transforms()
    if hasattr(body, "mark_render_dynamic_data_dirty"):
        body.mark_render_dynamic_data_dirty()


def add_review_environment() -> list:
    actors = []
    floor = spawn_actor(unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, -5.0))
    floor.set_actor_label("DM_ScalpHairReview_Floor")
    floor.set_actor_scale3d(unreal.Vector(6.0, 4.0, 0.05))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    actors.append(floor)
    sun = spawn_actor(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 300.0),
        unreal.Rotator(pitch=-45.0, yaw=-35.0),
    )
    sun.set_actor_label("DM_ScalpHairReview_KeyLight")
    required_component(sun, unreal.DirectionalLightComponent).set_editor_property("intensity", 0.5)
    actors.append(sun)
    fill = spawn_actor(
        unreal.RectLight,
        unreal.Vector(280.0, 0.0, 160.0),
        unreal.Rotator(yaw=180.0),
    )
    fill.set_actor_label("DM_ScalpHairReview_FillLight")
    fill_component = required_component(fill, unreal.RectLightComponent)
    fill_component.set_editor_property("intensity", 120.0)
    fill_component.set_editor_property("source_width", 300.0)
    fill_component.set_editor_property("source_height", 300.0)
    actors.append(fill)
    camera = spawn_actor(
        unreal.CineCameraActor,
        unreal.Vector(780.0, 0.0, 105.0),
        unreal.Rotator(yaw=180.0),
    )
    camera.set_actor_label("DM_ScalpHairReview_Camera")
    camera.get_cine_camera_component().set_editor_property("current_focal_length", 55.0)
    actors.append(camera)
    return actors


def stage_hair(body_actor, body_component, bodyfit_id: str) -> list:
    records = []
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for index, mesh_path in enumerate(HAIR_MESHES, start=1):
        mesh = unreal.load_asset(mesh_path)
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError(f"Hair mesh is unavailable: {mesh_path}")
        hair_actor = actor_subsystem.spawn_actor_from_class(
            unreal.SkeletalMeshActor,
            body_actor.get_actor_location(),
            body_actor.get_actor_rotation(),
            transient=False,
        )
        if hair_actor is None:
            raise RuntimeError(f"Unable to spawn hair actor for {mesh_path}")
        hair_actor.set_actor_label(f"DM_ScalpHairReview_{bodyfit_id}_HB1_01_{index:02d}")
        hair_component = hair_actor.get_editor_property("skeletal_mesh_component")
        hair_component.set_skeletal_mesh_asset(mesh)
        hair_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        try:
            hair_component.set_editor_property("use_bounds_from_leader_pose_component", True)
        except Exception:
            pass
        hair_actor.attach_to_actor(
            body_actor,
            "",
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
        )
        leader_pose_success = False
        leader_pose_error = None
        try:
            hair_component.set_leader_pose_component(body_component, force_update=True)
            leader_pose_success = True
        except Exception as exc:
            leader_pose_error = str(exc)
        records.append(
            {
                "mesh": mesh_path,
                "actor": hair_actor.get_path_name(),
                "bodyfit_id": bodyfit_id,
                "hair_skeleton": HAIR_SKELETON,
                "body_skeleton": body_component.get_skeletal_mesh_asset().get_editor_property("skeleton").get_path_name(),
                "leader_pose_success": leader_pose_success,
                "leader_pose_error": leader_pose_error,
                "manual_cross_skeleton_probe": bodyfit_id == "M02_Average",
            }
        )
    return records


def main() -> dict:
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
        raise RuntimeError(f"Refusing to overwrite review level: {LEVEL_PATH}")
    plan = RUNTIME.read_json(PLAN_PATH)
    RUNTIME.validate_runtime_plan(plan)
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.new_level(LEVEL_PATH):
        raise RuntimeError(f"Unable to create review level: {LEVEL_PATH}")
    environment = add_review_environment()
    staged = []
    for bodyfit_id, qualified_variant_id in REVIEW_VARIANTS.items():
        bodyfit = RUNTIME.bodyfit_for_id(plan, bodyfit_id)
        variant = RUNTIME.variant_for_id(bodyfit, qualified_variant_id)
        blueprint = RUNTIME.load_blueprint(bodyfit)
        body_actor = spawn_actor(blueprint.generated_class(), ACTOR_LOCATIONS[bodyfit_id])
        body_actor.set_actor_label(f"DM_ScalpHairReview_{bodyfit_id}")
        application = RUNTIME.apply_variant(body_actor, bodyfit, variant)
        errors = RUNTIME.validate_variant_application(application)
        if errors:
            raise RuntimeError(f"{bodyfit_id} review variant failed: {errors}")
        body_component, _followers = RUNTIME.actor_components(body_actor, bodyfit)
        animation = unreal.load_asset(MOTION_ASSETS[bodyfit_id])
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError(f"Review animation is unavailable: {MOTION_ASSETS[bodyfit_id]}")
        configure_body_animation(body_component, animation)
        staged.append(
            {
                "bodyfit_id": bodyfit_id,
                "variant": qualified_variant_id,
                "actor": body_actor.get_path_name(),
                "location": ACTOR_LOCATIONS[bodyfit_id],
                "animation": animation.get_path_name(),
                "enabled_components": application["actual_enabled_names"],
                "hair": stage_hair(body_actor, body_component, bodyfit_id),
            }
        )
    level_subsystem.editor_set_viewport_realtime(True)
    if not level_subsystem.save_current_level():
        raise RuntimeError(f"Unable to save review level: {LEVEL_PATH}")
    result = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "level": LEVEL_PATH,
        "hair_style": "hb1-01",
        "hair_mesh_count": len(HAIR_MESHES),
        "staged": staged,
        "environment_actor_count": len(environment),
        "level_saved": True,
        "manual_review_required": [
            "visual scalp fit on F02_Average",
            "cross-skeleton leader-pose fit on M02_Average",
            "hair clothing clipping",
            "side and rear silhouette",
        ],
        "formal_runtime_hair_slot": False,
        "success": True,
    }
    write_report(result)
    print("DM_SCALP_HAIR_REVIEW_LEVEL_V1=" + json.dumps(result, ensure_ascii=False, default=str))
    return result


if globals().get("__name__") == "__main__" or globals().get("DM_BUILD_SCALP_HAIR_REVIEW_V1"):
    main()
