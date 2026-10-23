"""UE-side scoped mesh coverage checks and a reusable two-outfit review stage."""

from __future__ import annotations

import gc
import hashlib
import importlib.util
import json
from pathlib import Path

import unreal

LEVEL = "/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Coverage"
PREFIX = "DM_WardrobeCoverage_"
ROOT = Path(__file__).resolve().parent
THROTTLE_STATE = "_dm_wardrobe_preview_previous_throttle"


def preview_background_updates(playing):
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    if playing:
        # Keep the original setting on unreal: the command runner reloads this module.
        if not hasattr(unreal, THROTTLE_STATE):
            setattr(unreal, THROTTLE_STATE, settings.get_editor_property("bThrottleCPUWhenNotForeground"))
        settings.set_editor_property("bThrottleCPUWhenNotForeground", False)
    elif hasattr(unreal, THROTTLE_STATE):
        settings.set_editor_property("bThrottleCPUWhenNotForeground", getattr(unreal, THROTTLE_STATE))
        delattr(unreal, THROTTLE_STATE)


def set_body_playback(body, playing):
    motion = body.get_editor_property("animation_data").get_editor_property("anim_to_play")
    if not isinstance(motion, unreal.AnimSequence):
        raise RuntimeError("Missing review motion")
    body.set_enable_animation(True)
    body.set_component_tick_enabled(True)
    body.set_editor_property("pause_anims", False)
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    # Serialized AnimationData alone can leave an existing live instance unbound.
    body.play_animation(motion, True)
    body.set_play_rate(1.0)
    body.set_position(0.0, False)
    body.override_animation_data(motion, True, playing, 0.0, 1.0)
    instance = body.get_anim_instance()
    if instance is None:
        raise RuntimeError("Review animation instance was not initialized")
    instance.set_playing(playing)
    body.set_update_animation_in_editor(True)
    if body.is_playing() != playing or instance.get_animation_asset() != motion:
        raise RuntimeError("Review live animation differs from requested playback")


def sample_playback():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(':')[0].split('.')[0] != LEVEL:
        raise RuntimeError("Open the coverage review stage first")
    rows = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if not actor.get_actor_label().startswith(PREFIX):
            continue
        components = actor.get_components_by_class(unreal.SkeletalMeshComponent)
        body = next(c for c in components if c.get_name() == "Body")
        bones = ("pelvis", "head", "hand_l", "hand_r", "foot_l", "foot_r")
        def positions(component):
            result = {}
            for bone in bones:
                if component.get_bone_index(bone) >= 0:
                    value = component.get_socket_location(bone)
                    result[bone] = [value.x, value.y, value.z]
            return result
        rows.append({"actor": actor.get_actor_label(), "playing": body.is_playing(),
                     "position": body.get_position(), "bones": positions(body),
                     "followers": [{"name": c.get_name(), "bones": positions(c),
                                    "leader_is_body": c.get_editor_property("leader_pose_component") == body}
                                   for c in components if c != body and c.get_skeletal_mesh_asset() is not None]})
    if not rows:
        raise RuntimeError("No coverage review actors")
    return {"rows": rows, "success": True, "scope": "instantaneous_pose_not_motion_acceptance"}


def stop_preview():
    preview_background_updates(False)
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if actor.get_actor_label().startswith(PREFIX):
            for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                if component.get_name() == "Body" and component.get_anim_instance() is not None:
                    component.get_anim_instance().set_playing(False)
    return {"success": True, "playing": False}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_worker():
    spec = importlib.util.spec_from_file_location("dm_coverage_environment", ROOT / "ue_build_modular_outfit_review_level_v2.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker


def read_plan(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("coverage", {}).get("scope") != "all_imported_meshes_in_at_least_one_approved_outfit":
        raise ValueError("Not a mesh coverage review plan")
    for record in plan["source_evidence"]:
        if hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Input changed: {record['path']}")
    return plan


def resolve(worker, plan, choice):
    bodyfit = worker.RUNTIME.bodyfit_for_id(plan, choice["bodyfit_id"])
    return bodyfit, worker.RUNTIME.variant_for_id(bodyfit, choice["qualified_variant_id"])


def check_application(worker, actor, bodyfit, variant):
    runtime = worker.RUNTIME
    application = runtime.apply_variant(actor, bodyfit, variant)
    errors = runtime.validate_variant_application(application)
    body, followers = runtime.actor_components(actor, bodyfit)
    motion = unreal.load_asset(worker.MOTION_ASSETS[bodyfit["bodyfit_id"]])
    if not isinstance(motion, unreal.AnimSequence) or motion.get_editor_property("skeleton") != body.get_skeletal_mesh_asset().get_editor_property("skeleton"):
        raise RuntimeError("Missing or wrong-skeleton review animation")
    worker.configure_body_animation(body, motion)
    materials = []
    for component in followers:
        mesh = component.get_skeletal_mesh_asset()
        if mesh is None:
            continue
        slots = mesh.get_editor_property("materials")
        if not slots:
            errors.append(f"No material slots: {mesh.get_path_name()}")
        for index, slot in enumerate(slots):
            material = slot.get_editor_property("material_interface")
            if material is None:
                errors.append(f"Missing material: {mesh.get_path_name()}:{index}")
            materials.append({"mesh": mesh.get_path_name(), "slot": index,
                              "material": runtime.object_path(material)})
    return {"application": application, "materials": materials,
            "animation": motion.get_path_name(), "errors": errors,
            "success": not errors, "visual_review": "pending"}


def ensure_level(worker):
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    current = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name().split(':')[0]
    if current.split('.')[0] == LEVEL:
        return levels
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError("Save the current map before opening the wardrobe review")
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        if not levels.load_level(LEVEL):
            raise RuntimeError("Cannot load review stage")
    else:
        if not levels.new_level(LEVEL):
            raise RuntimeError("Cannot create review stage")
        worker.add_review_environment()
    return levels


def show_page(worker, plan, page):
    pages = plan["coverage"]["pages"]
    if not 1 <= page <= len(pages):
        raise ValueError("Page out of range")
    row = pages[page - 1]
    choices = [c for c in plan["review_selection"]["outfits"] if c["review_index"] in row["review_indices"]]
    levels = ensure_level(worker)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Delete only our two stage actors, not user actors or the accepted pilot.
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(PREFIX):
            actors.destroy_actor(actor)
    staged = []
    for index, choice in enumerate(choices):
        bodyfit, variant = resolve(worker, plan, choice)
        location = unreal.Vector(0.0, (-90.0 if index == 0 else 90.0) if len(choices) == 2 else 0.0, 0.0)
        bp = worker.RUNTIME.load_blueprint(bodyfit)
        actor = worker.spawn_actor(bp.generated_class(), location, unreal.Rotator(roll=0, pitch=0, yaw=-90))
        actor.set_actor_label(f"{PREFIX}{choice['review_index']:03d}_{choice['family_display_name']}")
        result = check_application(worker, actor, bodyfit, variant)
        result.update(review_index=choice["review_index"], actor=actor.get_path_name())
        staged.append(result)
    if any(not r["success"] for r in staged):
        raise RuntimeError(f"Review assembly errors: {staged}")
    set_view(worker, "front", False)
    if not levels.save_current_level():
        raise RuntimeError("Cannot save review stage")
    levels.editor_set_viewport_realtime(True)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector(350, 0, 105), unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0))
    return {"level": LEVEL, "page": page, "review_indices": row["review_indices"],
            "staged": staged, "success": True, "visual_acceptance": "pending"}


def set_view(worker, view, playing):
    yaw = {"front": -90, "side": 0, "back": 90}[view]
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(':')[0].split('.')[0] != LEVEL:
        raise RuntimeError("Open the coverage review stage first")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected = [a for a in actors.get_all_level_actors() if a.get_actor_label().startswith(PREFIX)]
    if not selected:
        raise RuntimeError("No coverage review actors")
    for actor in selected:
        actor.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=yaw), False)
        body = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
        set_body_playback(body, playing)
    preview_background_updates(playing)
    actors.set_selected_level_actors([])
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.editor_set_game_view(True)
    levels.editor_set_viewport_realtime(True)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector(350, 0, 105), unreal.Rotator(roll=0, pitch=0, yaw=180))
    return {"view": view, "playing": playing, "success": True,
            "actors": [a.get_actor_label() for a in selected],
            "background_updates_held": hasattr(unreal, THROTTLE_STATE)}


def audit_chunk(worker, plan, start, count):
    if start < 1 or count < 1:
        raise ValueError("start and count must be positive")
    choices = plan["review_selection"]["outfits"][start - 1:start - 1 + count]
    if not choices:
        raise ValueError("No review cases selected")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    instances = {}
    rows = []
    try:
        for choice in choices:
            try:
                bodyfit, variant = resolve(worker, plan, choice)
                bid = bodyfit["bodyfit_id"]
                if bid not in instances:
                    bp = worker.RUNTIME.load_blueprint(bodyfit)
                    instances[bid] = actors.spawn_actor_from_class(bp.generated_class(), unreal.Vector(0, 0, -1000), transient=True)
                result = check_application(worker, instances[bid], bodyfit, variant)
            except Exception as exc:
                result = {"success": False, "errors": [str(exc)], "visual_review": "pending"}
            result.update(review_index=choice["review_index"], qualified_variant_id=choice["qualified_variant_id"])
            rows.append(result)
    finally:
        for actor in instances.values():
            actors.destroy_actor(actor)
    return {"scope": "loaded_mesh_skeleton_slots_material_presence_not_visual_fit",
            "rows": rows, "success": all(r["success"] for r in rows), "visual_acceptance": "pending"}


def reload_page(worker, plan, page):
    levels = ensure_level(worker)
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError("Save review stage before reload check")
    if not levels.load_level("/Engine/Maps/Entry") or not levels.load_level(LEVEL):
        raise RuntimeError("Cannot reload saved coverage stage")
    inspector = worker.load_module("dm_coverage_reload_check", ROOT / "ue_build_wardrobe_review_level_v1.py")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    indices = plan["coverage"]["pages"][page - 1]["review_indices"]
    rows = []
    for choice in plan["review_selection"]["outfits"]:
        if choice["review_index"] not in indices:
            continue
        matches = [a for a in actors if a.get_actor_label().startswith(f"{PREFIX}{choice['review_index']:03d}_")]
        if len(matches) != 1:
            raise RuntimeError("Saved stage does not contain the selected page")
        bodyfit, variant = resolve(worker, plan, choice)
        row = inspector.inspect_actor(worker.RUNTIME, matches[0], bodyfit, variant)
        motion = unreal.load_asset(worker.MOTION_ASSETS[bodyfit["bodyfit_id"]])
        if row["animation"] != motion.get_path_name():
            row["errors"].append("Saved body animation differs")
        body, _ = worker.RUNTIME.actor_components(matches[0], bodyfit)
        body.set_update_animation_in_editor(True)
        rows.append(row)
    levels.editor_set_viewport_realtime(True)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector(350, 0, 105), unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0))
    return {"page": page, "rows": rows, "success": all(not r["errors"] for r in rows), "visual_acceptance": "pending"}


def run(plan_path, action="show", page=1, start=1, count=10, view="front", playing=False):
    path = Path(plan_path)
    plan = read_plan(path)
    worker = load_worker()
    worker.RUNTIME.validate_runtime_plan(plan)
    if action == "show":
        preview_background_updates(False)
        result = show_page(worker, plan, page)
        output = path.parent / "stage" / f"page_{page:03d}.json"
        write_json(path.parent / "current_page.json", {"page": page, "level": LEVEL})
        write_json(path.parent / "stage" / "view.json", {"page": page, "view": "front", "playing": False})
    elif action == "audit":
        result = audit_chunk(worker, plan, start, count)
        output = path.parent / "assembly" / f"checks_{start:03d}_{start + len(result['rows']) - 1:03d}.json"
    elif action == "reload":
        result = reload_page(worker, plan, page)
        output = path.parent / "stage" / f"reload_{page:03d}.json"
    elif action == "view":
        result = set_view(worker, view, playing)
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
            raise RuntimeError("Cannot save coverage view")
        output = path.parent / "stage" / "view.json"
        result["page"] = json.loads((path.parent / "current_page.json").read_text(encoding="utf-8"))["page"]
    elif action == "sample":
        result = sample_playback()
        output = path.parent / "stage" / "playback_sample.json"
    elif action == "stop":
        result = stop_preview()
        output = path.parent / "stage" / "view.json"
    else:
        raise ValueError(action)
    result["plan_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(output, result)
    gc.collect()
    unreal.SystemLibrary.collect_garbage()
    print("WARDROBE_COVERAGE=" + json.dumps({"success": result["success"], "report": str(output)}))
    if not result["success"]:
        raise RuntimeError(f"Assembly issues recorded in {output}")
    return str(output)
