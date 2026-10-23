"""Build and control the single UE level used for hair/outfit visual review."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import importlib.util

import unreal


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
PLAN_PATH = (
    LANCE_ROOT / "00_engine" / "outputs" / "unreal_character_import"
    / "current_reviews_20261001_v1" / "hair_outfit_compatibility" / "review_plan.json"
)
RUNTIME_PLAN_PATH = PLAN_PATH.with_name("bodyfit_metadata.json")
REPORT_ROOT = PLAN_PATH.parent
LEVEL_PATH = "/Game/DataMake/Validation/ScalpHairCompatibility/L_DM_ScalpHairCompatibility_Review_v001"
PREFIX = "DM_HOC_"
BODY_LABEL = PREFIX + "Body"
HAIR_PREFIX = PREFIX + "Hair_"
MOTION = "/Game/DataMake/Animations/CC5/ModularOutfitPilot/F02_Average/A_DM_F03_AUDIENCE_01_ModularPilot_v001"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(path)
    spec.loader.exec_module(module)
    return module


RUNTIME = load_module("dm_hoc_runtime", SCRIPT_ROOT / "ue_build_modular_outfit_runtime_v2.py")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write(name: str, value: dict) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / name
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def spawn(cls, location, rotation=unreal.Rotator()):
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        cls, location, rotation, transient=False
    )
    if actor is None:
        raise RuntimeError(f"Unable to spawn {cls}")
    return actor


def component(actor, cls):
    value = actor.get_component_by_class(cls)
    if value is None:
        raise RuntimeError(f"Missing {cls.__name__} on {actor.get_name()}")
    return value


def configure_body_animation(body, animation):
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


def environment():
    actors = []
    floor = spawn(unreal.StaticMeshActor, unreal.Vector(0, 0, -5))
    floor.set_actor_label(PREFIX + "Floor")
    floor.set_actor_scale3d(unreal.Vector(5, 5, 0.05))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    actors.append(floor)
    sun = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(pitch=-45, yaw=-35))
    sun.set_actor_label(PREFIX + "KeyLight")
    component(sun, unreal.DirectionalLightComponent).set_editor_property("intensity", 0.5)
    actors.append(sun)
    fill = spawn(unreal.RectLight, unreal.Vector(280, 0, 160), unreal.Rotator(yaw=180))
    fill.set_actor_label(PREFIX + "FillLight")
    fill_component = component(fill, unreal.RectLightComponent)
    fill_component.set_editor_property("intensity", 100.0)
    fill_component.set_editor_property("source_width", 300.0)
    fill_component.set_editor_property("source_height", 300.0)
    actors.append(fill)
    camera = spawn(unreal.CineCameraActor, unreal.Vector(350, 0, 105), unreal.Rotator(yaw=180))
    camera.set_actor_label(PREFIX + "Camera")
    camera.get_cine_camera_component().set_editor_property("current_focal_length", 55.0)
    actors.append(camera)
    return actors


def remove_review_actors():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(PREFIX + "Body") or actor.get_actor_label().startswith(HAIR_PREFIX):
            actors.destroy_actor(actor)


def remove_hair_actors():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(HAIR_PREFIX):
            actors.destroy_actor(actor)


def plan_and_body():
    plan = read(PLAN_PATH)
    runtime_plan = read(RUNTIME_PLAN_PATH)
    bodyfit = RUNTIME.bodyfit_for_id(runtime_plan, "F02_Average")
    return plan, bodyfit


def spawn_body_actor(bodyfit):
    bp = RUNTIME.load_blueprint(bodyfit)
    actor = spawn(bp.generated_class(), unreal.Vector(0, 0, 0), unreal.Rotator())
    actor.set_actor_label(BODY_LABEL)
    body, _ = RUNTIME.actor_components(actor, bodyfit)
    motion = unreal.load_asset(MOTION)
    if isinstance(motion, unreal.AnimSequence):
        configure_body_animation(body, motion)
    return actor, body


def apply_outfit(actor, bodyfit, target):
    body, followers = RUNTIME.actor_components(actor, bodyfit)
    body_mesh = body.get_skeletal_mesh_asset()
    body_skeleton = body_mesh.get_editor_property("skeleton")
    assignment = {
        "target_component": "FullBody" if target["slot"] == "full_body" else "UpperOuter",
        "target_kind": "fixed_semantic_slot",
        "source_component_name": target["display_name"],
        "qualified_module_id": f"{target['unit_id']}::{target['module_key']}",
        "module_key": target["module_key"],
        "slot": target["slot"],
        "mesh_path": target["mesh_paths"][0],
        "mesh_name": target["mesh_names"][0] if target.get("mesh_names") else target["display_name"],
    }
    mesh = unreal.load_asset(assignment["mesh_path"])
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Missing outfit mesh: {assignment['mesh_path']}")
    if mesh.get_editor_property("skeleton") != body_skeleton:
        raise RuntimeError(f"Outfit Skeleton mismatch: {assignment['mesh_path']}")
    follower_map = {f.get_name(): f for f in followers}
    for follower in followers:
        follower.set_visibility(False, False)
        follower.set_hidden_in_game(True)
        follower.set_skeletal_mesh_asset(None)
    follower = follower_map[assignment["target_component"]]
    follower.set_skeletal_mesh_asset(mesh)
    follower.set_visibility(True, False)
    follower.set_hidden_in_game(False)
    return {
        "target_component": assignment["target_component"],
        "mesh_path": assignment["mesh_path"],
        "body_identity_preserved": body.get_skeletal_mesh_asset().get_path_name() == bodyfit["body_mesh_path"],
        "followers_cleared": all(
            f.get_name() == assignment["target_component"] or f.get_skeletal_mesh_asset() is None
            for f in followers
        ),
    }


def stage_hair(body_actor, body_component, hair):
    remove_hair_actors()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    rows = []
    for index, mesh_spec in enumerate(hair["meshes"], 1):
        mesh = unreal.load_asset(mesh_spec["path"])
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError(f"Missing hair mesh: {mesh_spec['path']}")
        actor = actors.spawn_actor_from_class(
            unreal.SkeletalMeshActor,
            body_actor.get_actor_location(),
            body_actor.get_actor_rotation(),
            transient=False,
        )
        if actor is None:
            raise RuntimeError("Unable to spawn hair actor")
        actor.set_actor_label(f"{HAIR_PREFIX}{hair['hair_id']}_{index:02d}")
        comp = actor.get_editor_property("skeletal_mesh_component")
        comp.set_skeletal_mesh_asset(mesh)
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        actor.attach_to_actor(body_actor, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD)
        comp.set_leader_pose_component(body_component, force_update=True)
        rows.append({"actor": actor.get_path_name(), "mesh": mesh.get_path_name(), "leader_pose": True})
    return rows


def set_view(view: str):
    # Match the established wardrobe review convention: the fixed camera is
    # on +X and the body rotates to expose front, side and back to it.
    yaw = {"front": -90.0, "side": 0.0, "back": 90.0}[view]
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(":")[0].split(".")[0] != LEVEL_PATH:
        raise RuntimeError("Open the compatibility review level first")
    body = next((a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == BODY_LABEL), None)
    if body is None:
        raise RuntimeError("Compatibility review body is missing")
    body.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.editor_set_viewport_realtime(True)
    # Force the editor viewport into the same active game-view mode used by
    # the prior wardrobe review. This makes a remote button press refresh the
    # visible viewport even when the UE window did not have focus.
    levels.editor_set_game_view(True)
    levels.editor_set_game_view(False)
    levels.editor_set_game_view(True)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector(350, 0, 105), unreal.Rotator(yaw=180)
    )
    return {"view": view, "success": True}


def show(case_index: int):
    plan, bodyfit = plan_and_body()
    case = next(c for c in plan["cases"] if c["review_index"] == case_index)
    target = next(t for t in plan["outfit_targets"] if t["outfit_index"] == case["outfit_index"])
    hair = next(h for h in plan["hair_styles"] if h["hair_index"] == case["hair_index"])
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    current = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current_path = current.get_path_name().split(":")[0].split(".")[0] if current else ""
    if current_path != LEVEL_PATH:
        if not levels.load_level(LEVEL_PATH):
            raise RuntimeError(f"Cannot load {LEVEL_PATH}")
    body_actor = next((a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == BODY_LABEL), None)
    body = next((c for c in body_actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body"), None) if body_actor else None
    if body_actor is None or body is None:
        raise RuntimeError("Review body actor is missing; build the level first")
    outfit_result = apply_outfit(body_actor, bodyfit, target)
    hair_result = stage_hair(body_actor, body, hair)
    state = {
        "schema_version": 1,
        "at_utc": now(),
        "level": LEVEL_PATH,
        "review_index": case_index,
        "case": case,
        "outfit": target,
        "hair": hair,
        "outfit_application": outfit_result,
        "hair_meshes": hair_result,
        "visual_decision": "pending",
        "success": True,
    }
    write("current_case.json", state)
    set_view("front")
    write("view.json", {"review_index": case_index, "view": "front", "success": True})
    levels.editor_set_viewport_realtime(True)
    levels.save_current_level()
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(350, 0, 105), unreal.Rotator(yaw=180))
    return state


def build():
    plan, bodyfit = plan_and_body()
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    current = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current_path = current.get_path_name().split(":")[0].split(".")[0] if current else ""
    if current_path != LEVEL_PATH:
        if unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
            raise RuntimeError(f"Refusing to overwrite review level: {LEVEL_PATH}")
        if not levels.new_level(LEVEL_PATH):
            raise RuntimeError(f"Unable to create {LEVEL_PATH}")
    remove_review_actors()
    existing = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                if a.get_actor_label().startswith(PREFIX)]
    if not any(a.get_actor_label() == PREFIX + "Floor" for a in existing):
        environment()
    body_actor, _body = spawn_body_actor(bodyfit)
    if not levels.save_current_level():
        raise RuntimeError("Unable to save review level")
    result = {
        "schema_version": 1,
        "created_at_utc": now(),
        "level": LEVEL_PATH,
        "plan": str(PLAN_PATH),
        "bodyfit_id": "F02_Average",
        "body_actor": body_actor.get_path_name(),
        "review_cases": plan["counts"]["review_cases"],
        "outfit_targets": plan["counts"]["outfit_targets"],
        "hair_styles": plan["counts"]["hair_styles"],
        "manual_review_required": ["front/side/back hair silhouette", "hair x garment penetration", "visual material/color", "optional motion observation"],
        "success": True,
    }
    write("level_build_report.json", result)
    return result


def main():
    mode = globals().get("DM_HOC_MODE", "")
    if mode == "build":
        result = build()
    elif mode == "show":
        result = show(int(globals().get("DM_HOC_CASE_INDEX", 1)))
    elif mode == "view":
        result = set_view(globals().get("DM_HOC_VIEW", "front"))
    else:
        raise RuntimeError("Set DM_HOC_MODE to build, show, or view")
    print("DM_HAIR_OUTFIT_COMPATIBILITY=" + json.dumps(result, ensure_ascii=False, default=str))
    return result


if __name__ == "__main__" or globals().get("DM_HOC_MODE"):
    main()
