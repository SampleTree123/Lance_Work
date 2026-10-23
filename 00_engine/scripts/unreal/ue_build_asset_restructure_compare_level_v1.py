"""Stage old and copied pilot meshes side by side on identical F02 bodies."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_build_asset_restructure_compare_level_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\asset_restructure_pilot_20260928_v1"
)
COPY_REPORT = ROOT / "ue_copy_report.json"
REPORT = ROOT / "ue_compare_level_report.json"
LEVEL = "/Game/DataMake/Validation/AssetRestructurePilot/L_DM_AssetRestructure_Compare_v001"
BODY_BLUEPRINT = "/Game/DataMake/Characters/ModularOutfitPilot/F02_Average/BP_DM_F02_Average_ModularOutfitPilot_v002"
BODY_MESH = "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/F02_Average/Cases/F_BASE/FullReference/CC_MOD_F_BASE_UE58"


def spawn(actor_class, location, rotation=unreal.Rotator()):
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        actor_class, location, rotation, transient=False
    )
    if actor is None:
        raise RuntimeError(f"could not spawn actor: {actor_class}")
    return actor


def body_component(actor):
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh = component.get_skeletal_mesh_asset()
        if mesh and mesh.get_path_name().split(".", 1)[0] == BODY_MESH:
            return component
    raise RuntimeError(f"base body component not found: {actor.get_path_name()}")


def add_mesh(body_actor, body, mesh_path, label):
    mesh = unreal.load_asset(mesh_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"invalid mesh: {mesh_path}")
    actor = spawn(unreal.SkeletalMeshActor, body_actor.get_actor_location())
    actor.set_actor_label(label)
    component = actor.get_editor_property("skeletal_mesh_component")
    component.set_skeletal_mesh_asset(mesh)
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    actor.attach_to_actor(
        body_actor, "", unreal.AttachmentRule.KEEP_WORLD,
        unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD
    )
    component.set_leader_pose_component(body, force_update=True)
    return {"label": label, "actor": actor.get_path_name(), "mesh": mesh_path}


def run():
    copied = json.loads(COPY_REPORT.read_text(encoding="utf-8"))
    if not copied.get("success"):
        raise RuntimeError("copy pilot did not pass")
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        raise RuntimeError(f"review level already exists: {LEVEL}")
    blueprint = unreal.load_asset(BODY_BLUEPRINT)
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"body blueprint unavailable: {BODY_BLUEPRINT}")
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.new_level(LEVEL):
        raise RuntimeError(f"cannot create level: {LEVEL}")
    floor = spawn(unreal.StaticMeshActor, unreal.Vector(0, 0, -5))
    floor.set_actor_label("DM_RestructureCompare_Floor")
    floor.set_actor_scale3d(unreal.Vector(5, 5, 0.05))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    key = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(pitch=-45, yaw=-35))
    key.set_actor_label("DM_RestructureCompare_KeyLight")
    fill = spawn(unreal.RectLight, unreal.Vector(300, 0, 160), unreal.Rotator(yaw=180))
    fill.set_actor_label("DM_RestructureCompare_FillLight")
    camera = spawn(unreal.CineCameraActor, unreal.Vector(760, 0, 110), unreal.Rotator(yaw=180))
    camera.set_actor_label("DM_RestructureCompare_Camera")
    camera.get_cine_camera_component().set_editor_property("current_focal_length", 55.0)
    staged = []
    for side, y, key_name in (("Original", -125.0, "old"), ("Copied", 125.0, "new")):
        location = unreal.Vector(0, y, 0)
        body_actor = spawn(blueprint.generated_class(), location)
        body_actor.set_actor_label(f"DM_RestructureCompare_{side}_F02")
        body = body_component(body_actor)
        meshes = []
        for case in copied["cases"]:
            for index, item in enumerate(case["meshes"], 1):
                meshes.append(add_mesh(body_actor, body, item[key_name],
                                       f"DM_RestructureCompare_{side}_{case['label']}_{index:02d}"))
        staged.append({"side": side, "body": body_actor.get_path_name(),
                       "body_mesh": body.get_skeletal_mesh_asset().get_path_name(),
                       "position_y": y, "meshes": meshes})
    if not level_subsystem.save_current_level():
        raise RuntimeError(f"could not save level: {LEVEL}")
    result = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "side_by_side_visual_review_pending", "level": LEVEL,
              "camera": camera.get_path_name(), "staged": staged, "success": True}
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake asset restructure compare level: {REPORT}")


run()
