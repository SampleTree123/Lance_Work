"""Build and reload-check two wardrobe outfits using the accepted v002 blueprints.

Run in UE with DM_WARDROBE_REVIEW_PLAN and DM_WARDROBE_REVIEW_REPORT set.
The pilot level and blueprint defaults are never modified.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import unreal


LEVEL_PATH = "/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Review"


def load_review_worker():
    path = Path(__file__).resolve().with_name("ue_build_modular_outfit_review_level_v2.py")
    spec = importlib.util.spec_from_file_location("dm_wardrobe_review_base", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_actor(runtime, actor, bodyfit, variant):
    body, followers = runtime.actor_components(actor, bodyfit)
    expected = {a["target_component"]: a["mesh_path"] for a in variant["assignments"]}
    rows = []
    errors = []
    if runtime.object_path(body.get_skeletal_mesh_asset()) != bodyfit["body_mesh_path"]:
        errors.append("Body identity differs after reload")
    for component in followers:
        name = component.get_name()
        mesh = runtime.object_path(component.get_skeletal_mesh_asset())
        visible = bool(component.get_editor_property("visible"))
        hidden = bool(component.get_editor_property("hidden_in_game"))
        leader = component.get_editor_property("leader_pose_component") == body
        collision = str(component.get_collision_enabled())
        if mesh != expected.get(name):
            errors.append(f"{name}: persisted mesh differs")
        if visible != (name in expected) or hidden != (name not in expected):
            errors.append(f"{name}: persisted visibility differs")
        if not leader or "NO_COLLISION" not in collision.upper():
            errors.append(f"{name}: leader or collision differs")
        rows.append({"component": name, "mesh": mesh, "leader_is_body": leader,
                     "visible": visible, "hidden_in_game": hidden})
    animation_data = body.get_editor_property("animation_data")
    animation = runtime.object_path(animation_data.get_editor_property("anim_to_play"))
    return {"bodyfit_id": bodyfit["bodyfit_id"], "actor": actor.get_path_name(),
            "body_mesh": runtime.object_path(body.get_skeletal_mesh_asset()),
            "animation": animation, "components": rows, "errors": errors}


def main():
    plan_path = Path(globals()["DM_WARDROBE_REVIEW_PLAN"])
    report_path = Path(globals()["DM_WARDROBE_REVIEW_REPORT"])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("usage") != "reuse_existing_blueprints_for_review_only":
        raise RuntimeError("Not a wardrobe review plan")
    for record in plan["source_evidence"]:
        digest = hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest()
        if digest != record["sha256"]:
            raise RuntimeError(f"Review input changed: {record['path']}")
    dirty_maps = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty_maps:
        raise RuntimeError("Save the current edited map before building wardrobe review")
    worker = load_review_worker()
    motion = worker.load_module(
        "dm_wardrobe_motion_checks",
        Path(__file__).resolve().with_name("ue_modular_outfit_motion_validation_v1.py"))
    worker.PLAN_PATH = plan_path
    worker.REPORT_PATH = report_path
    worker.LEVEL_PATH = LEVEL_PATH
    worker.REVIEW_VARIANTS = {
        b["bodyfit_id"]: b["runtime_variants"][0]["qualified_variant_id"]
        for b in plan["bodyfits"]
    }
    result = worker.main()
    result["scope"] = "wardrobe_average_two_complete_outfits"
    result["runtime_approved"] = False
    result["reload_validation"] = []
    result["success"] = False
    worker.write_report(result)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not levels.load_level("/Engine/Maps/Entry") or not levels.load_level(LEVEL_PATH):
        raise RuntimeError("Unable to reload saved wardrobe review")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for bodyfit in plan["bodyfits"]:
        label = f"DM_ModularReview_{bodyfit['bodyfit_id']}"
        matches = [a for a in actors if a.get_actor_label() == label]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one saved actor: {label}")
        row = inspect_actor(worker.RUNTIME, matches[0], bodyfit, bodyfit["runtime_variants"][0])
        expected_motion = unreal.load_asset(worker.MOTION_ASSETS[bodyfit["bodyfit_id"]])
        if row["animation"] != expected_motion.get_path_name():
            row["errors"].append("Body motion differs after reload")
        start = motion.sample_animation_pose(expected_motion, 0.0)
        end = motion.sample_animation_pose(expected_motion, 0.75)
        row["animation_data_rotation_delta_degrees"] = max(
            motion.quaternion_angular_distance_degrees(start[b]["rotation"], end[b]["rotation"])
            for b in motion.POSE_BONES)
        if row["animation_data_rotation_delta_degrees"] < 1.0:
            row["errors"].append("No meaningful motion in sampled animation data")
        result["reload_validation"].append(row)
        body, _followers = worker.RUNTIME.actor_components(matches[0], bodyfit)
        body.set_update_animation_in_editor(True)
    result["success"] = all(not row["errors"] for row in result["reload_validation"])
    worker.write_report(result)
    if not result["success"]:
        raise RuntimeError(f"Wardrobe reload validation failed: {report_path}")
    levels.editor_set_viewport_realtime(True)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        worker.REVIEW_CAMERA_LOCATION, unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0))
    print("DM_WARDROBE_REVIEW=" + json.dumps({"level": LEVEL_PATH, "success": True,
          "report": str(report_path), "manual_fit_review": "pending"}))


if __name__ == "__main__" or globals().get("DM_BUILD_WARDROBE_REVIEW"):
    main()
