"""Build a saved visual-review level for the v002 fixed-slot outfit pilot."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_build_modular_outfit_review_level_v2.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


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
REPORT_PATH = PLAN_PATH.parent / "runtime_v2" / "visual_review_level_v2.json"
LEVEL_PATH = (
    "/Game/DataMake/Validation/ModularOutfitPilot/"
    "L_DM_ModularOutfitPilot_Review_v002"
)
REVIEW_VARIANTS = {
    "M02_Average": "M_1920_LAYERED::coat_on",
    "F02_Average": "F_BIKINI_LAYERED::cover_and_shoes",
}
ACTOR_LOCATIONS = {
    "M02_Average": unreal.Vector(0.0, -90.0, 0.0),
    "F02_Average": unreal.Vector(0.0, 90.0, 0.0),
}
REVIEW_EXPOSURE_BIAS = 0.0
REVIEW_KEY_LIGHT_INTENSITY = 0.5
REVIEW_FILL_LIGHT_INTENSITY = 100.0
REVIEW_CAMERA_LOCATION = unreal.Vector(750.0, 0.0, 95.0)
MOTION_ASSETS = {
    "M02_Average": (
        "/Game/DataMake/Animations/CC5/ModularOutfitPilot/M02_Average/"
        "A_DM_M02_AUDIENCE_01_ModularPilot_v001"
    ),
    "F02_Average": (
        "/Game/DataMake/Animations/CC5/ModularOutfitPilot/F02_Average/"
        "A_DM_F03_AUDIENCE_01_ModularPilot_v001"
    ),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Unable to load worker: {path}")
    spec.loader.exec_module(module)
    return module


RUNTIME = load_module("dm_modular_runtime_review_v2", RUNTIME_WORKER)


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
    actor = unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).spawn_actor_from_class(actor_class, location, rotation, transient=False)
    if actor is None:
        raise RuntimeError(f"Unable to spawn review actor: {actor_class}")
    return actor


def required_component(actor, component_class):
    component = actor.get_component_by_class(component_class)
    if component is None:
        raise RuntimeError(
            f"{actor.get_name()} has no {component_class.__name__} component"
        )
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


def configure_review_exposure(volume) -> None:
    """Use a deterministic exposure so the dark test stage cannot overexpose skin."""
    volume.set_actor_label("DM_ModularReview_PostProcess")
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property(
        "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL
    )
    settings.set_editor_property(
        "override_auto_exposure_apply_physical_camera_exposure", True
    )
    settings.set_editor_property(
        "auto_exposure_apply_physical_camera_exposure", False
    )
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", REVIEW_EXPOSURE_BIAS)
    volume.set_editor_property("settings", settings)


def add_review_environment() -> list:
    actors = []
    floor = spawn_actor(unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, -5.0))
    floor.set_actor_label("DM_ModularReview_Floor")
    floor.set_actor_scale3d(unreal.Vector(5.0, 5.0, 0.05))
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    floor.static_mesh_component.set_static_mesh(cube)
    actors.append(floor)

    sun = spawn_actor(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 300.0),
        unreal.Rotator(roll=0.0, pitch=-45.0, yaw=-35.0),
    )
    sun.set_actor_label("DM_ModularReview_KeyLight")
    required_component(sun, unreal.DirectionalLightComponent).set_editor_property(
        "intensity", REVIEW_KEY_LIGHT_INTENSITY
    )
    actors.append(sun)

    fill = spawn_actor(
        unreal.RectLight,
        unreal.Vector(280.0, 0.0, 160.0),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0),
    )
    fill.set_actor_label("DM_ModularReview_FillLight")
    fill_component = required_component(fill, unreal.RectLightComponent)
    fill_component.set_editor_property("intensity", REVIEW_FILL_LIGHT_INTENSITY)
    fill_component.set_editor_property("source_width", 300.0)
    fill_component.set_editor_property("source_height", 300.0)
    actors.append(fill)

    post_process = spawn_actor(
        unreal.PostProcessVolume,
        unreal.Vector(0.0, 0.0, 0.0),
    )
    configure_review_exposure(post_process)
    actors.append(post_process)

    camera = spawn_actor(
        unreal.CineCameraActor,
        REVIEW_CAMERA_LOCATION,
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0),
    )
    camera.set_actor_label("DM_ModularReview_Camera")
    camera.get_cine_camera_component().set_editor_property(
        "current_focal_length", 50.0
    )
    actors.append(camera)
    return actors


def main() -> dict:
    raise RuntimeError("The independent v002 Pilot execution entry is retired. Shared functions remain in use by v003 and current reviews.")
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
        actor = spawn_actor(
            blueprint.generated_class(), ACTOR_LOCATIONS[bodyfit_id]
        )
        actor.set_actor_label(f"DM_ModularReview_{bodyfit_id}")
        application = RUNTIME.apply_variant(actor, bodyfit, variant)
        errors = RUNTIME.validate_variant_application(application)
        if errors:
            raise RuntimeError(f"{bodyfit_id} review variant failed: {errors}")
        body, _followers = RUNTIME.actor_components(actor, bodyfit)
        animation_path = MOTION_ASSETS[bodyfit_id]
        animation = unreal.load_asset(animation_path)
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError(f"Review animation is unavailable: {animation_path}")
        configure_body_animation(body, animation)
        staged.append(
            {
                "bodyfit_id": bodyfit_id,
                "variant": qualified_variant_id,
                "actor": actor.get_path_name(),
                "location": ACTOR_LOCATIONS[bodyfit_id],
                "animation": animation.get_path_name(),
                "enabled_components": application["actual_enabled_names"],
            }
        )
    level_subsystem.editor_set_viewport_realtime(True)
    if not level_subsystem.save_current_level():
        raise RuntimeError(f"Unable to save review level: {LEVEL_PATH}")
    result = {
        "schema_version": 2,
        "created_at_utc": utc_now(),
        "level": LEVEL_PATH,
        "staged": staged,
        "environment_actor_count": len(environment),
        "lighting": {
            "exposure_method": "manual",
            "physical_camera_exposure": False,
            "exposure_bias": REVIEW_EXPOSURE_BIAS,
            "key_light_intensity": REVIEW_KEY_LIGHT_INTENSITY,
            "fill_light_intensity": REVIEW_FILL_LIGHT_INTENSITY,
            "camera_location": REVIEW_CAMERA_LOCATION,
        },
        "level_saved": True,
        "manual_review_required": [
            "visual_clipping",
            "material_appearance",
            "hair_outfit_compatibility",
            "motion_pose_following",
        ],
        "success": True,
    }
    write_report(result)
    print(
        "DM_MODULAR_REVIEW_LEVEL_V2="
        + json.dumps(result, ensure_ascii=False, default=str)
    )
    return result


if globals().get("__name__") == "__main__" or globals().get(
    "DM_BUILD_MODULAR_REVIEW_LEVEL_V2"
):
    main()
