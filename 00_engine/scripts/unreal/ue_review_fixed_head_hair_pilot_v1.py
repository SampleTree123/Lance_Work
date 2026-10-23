"""One representative hairstyle on both fixed-head bases, three views each.

Set DM_FIXED_HAIR_PILOT_ID (default HAIR_HB3_17), optionally
DM_FIXED_HAIR_PILOT_CAPTURE=False for an inspectable saved level only.
This does not modify the source meshes or the old review level.
"""
import json
import time
from pathlib import Path
import unreal

REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "00_engine/outputs/unreal_character_import/fixed_head_hair_20261004_v1"
LEVEL = "/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1/Review/L_FixedHeadHair_Pilot"
HAIR = globals().get("DM_FIXED_HAIR_PILOT_ID", "HAIR_HB3_17")
CAPTURE = globals().get("DM_FIXED_HAIR_PILOT_CAPTURE", True)


def write(value):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "pilot_review.json").write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def spawn(cls, position, rotation=unreal.Rotator()):
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(cls, position, rotation)
    if actor is None:
        raise RuntimeError("Cannot spawn " + str(cls))
    return actor


def main():
    report = json.loads((ROOT / "import_report.json").read_text(encoding="utf-8"))
    cases = [r for r in report["records"] if r["hair_id"] == HAIR and r.get("success")]
    if {r["sex"] for r in cases} != {"female", "male"} or len(cases) != 2:
        raise RuntimeError("Both representative branches must have imported successfully")
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        if not levels.new_level(LEVEL):
            raise RuntimeError("Cannot create independent pilot level")
    elif not levels.load_level(LEVEL):
        raise RuntimeError("Cannot load pilot level")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith("DM_FixedHair_"):
            actors.destroy_actor(actor)
    lamp = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(pitch=-35, yaw=-35))
    lamp.set_actor_label("DM_FixedHair_Key")
    lamp.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", .7)
    fill = spawn(unreal.RectLight, unreal.Vector(200, 0, 180), unreal.Rotator(yaw=180))
    fill.set_actor_label("DM_FixedHair_Fill")
    fill.get_component_by_class(unreal.RectLightComponent).set_editor_properties({"intensity": 100.,
        "source_width": 250., "source_height": 400.})
    volume = spawn(unreal.PostProcessVolume, unreal.Vector())
    volume.set_actor_label("DM_FixedHair_Exposure")
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    settings.set_editor_properties({"override_auto_exposure_method": True,
        "auto_exposure_method": unreal.AutoExposureMethod.AEM_MANUAL,
        "override_auto_exposure_apply_physical_camera_exposure": True,
        "auto_exposure_apply_physical_camera_exposure": False,
        "override_auto_exposure_bias": True, "auto_exposure_bias": -.8})
    volume.set_editor_property("settings", settings)
    groups, binding_rows = {}, []
    for row in cases:
        sex = row["sex"]
        position = unreal.Vector(0, -80 if sex == "female" else 80, 0)
        base = report["bases"][sex]
        body_path = base["body_mesh"]
        group = []
        body_actor = spawn(unreal.SkeletalMeshActor, position, unreal.Rotator(yaw=-90))
        body_actor.set_actor_label("DM_FixedHair_" + sex + "_Body")
        body = body_actor.get_editor_property("skeletal_mesh_component")
        body.set_skeletal_mesh_asset(unreal.load_asset(body_path))
        group.append(body_actor)
        for record in base["meshes"] + row["meshes"]:
            if record["path"] == body_path:
                continue
            actor = spawn(unreal.SkeletalMeshActor, position, unreal.Rotator(yaw=-90))
            actor.set_actor_label("DM_FixedHair_" + sex + "_" + record["name"])
            component = actor.get_editor_property("skeletal_mesh_component")
            mesh = unreal.load_asset(record["path"])
            if mesh.get_editor_property("skeleton").get_path_name() != row["skeleton_path"]:
                raise RuntimeError("Pilot follower Skeleton mismatch")
            component.set_skeletal_mesh_asset(mesh)
            component.set_leader_pose_component(body, True)
            component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            if component.get_editor_property("leader_pose_component") != body:
                raise RuntimeError("Pilot leader pose binding failed")
            group.append(actor)
            binding_rows.append({"sex": sex, "mesh": record["path"], "leader": body_path})
        groups[sex] = {"actors": group, "body": body, "position": position}
    if not levels.save_current_level():
        raise RuntimeError("Cannot save representative pilot level")
    result = {"success": True, "visual_review_complete": False, "level": LEVEL,
        "hair_id": HAIR, "bindings": binding_rows, "captures": [], "capture_complete": not CAPTURE,
        "scope": "One hairstyle, male/female branches; no all-hair visual or dynamic review"}
    write(result)
    if not CAPTURE:
        return
    capture_root = ROOT / "pilot_captures"
    capture_root.mkdir(exist_ok=True)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    camera = spawn(unreal.SceneCapture2D, unreal.Vector(145, 0, 165), unreal.Rotator(yaw=180))
    camera.set_actor_label("DM_FixedHair_Capture")
    component = camera.get_component_by_class(unreal.SceneCaptureComponent2D)
    component.set_editor_properties({"capture_every_frame": False, "capture_on_movement": False,
        "always_persist_rendering_state": True, "capture_source": unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR,
        "fov_angle": 35., "show_flag_settings": [unreal.EngineShowFlagsSetting(show_flag_name=n, enabled=True)
            for n in ("AntiAliasing", "TemporalAA", "PostProcessing")]})
    target = unreal.RenderingLibrary.create_render_target2d(world, 900, 900,
        unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.LinearColor(.18, .18, .18, 1))
    component.set_editor_property("texture_target", target)
    steps = [(sex, view, yaw) for sex in ("female", "male")
        for view, yaw in (("front", -90), ("left", 0), ("back", 90))]
    state = {"step": 0, "frames": 0, "handle": None}
    performance = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    old_throttle = performance.get_editor_property("bThrottleCPUWhenNotForeground")
    performance.set_editor_property("bThrottleCPUWhenNotForeground", False)

    def finish(error=None):
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])
        performance.set_editor_property("bThrottleCPUWhenNotForeground", old_throttle)
        for data in groups.values():
            for actor in data["actors"]:
                actor.set_actor_hidden_in_game(False)
                actor.set_actor_rotation(unreal.Rotator(yaw=-90), False)
        actors.destroy_actor(camera)
        if not levels.save_current_level() and error is None:
            error = "Could not save the clean representative review level"
        result.update({"capture_complete": error is None, "error": error})
        write(result)
        unreal.log("Fixed head hair pilot capture finished: " + str(ROOT / "pilot_review.json"))

    def tick(delta):
        try:
            sex, view, yaw = steps[state["step"]]
            group = groups[sex]
            if state["frames"] == 0:
                for gender, data in groups.items():
                    for actor in data["actors"]:
                        actor.set_actor_hidden_in_game(gender != sex)
                        if gender == sex:
                            actor.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
                # Use the actual head bone height, avoiding black images or a
                # cropped neck from a fixed camera trained on another body.
                body = group["body"]
                names = [str(body.get_bone_name(i)) for i in range(body.get_num_bones())]
                head = next((n for n in names if n.lower() in ("head", "cc_base_head")), None)
                z = body.get_socket_location(head).z + 10 if head else 165.
                camera.set_actor_location(unreal.Vector(145, group["position"].y, z), False, False)
            component.capture_scene()
            state["frames"] += 1
            if state["frames"] < 18:
                return
            name = sex + "_" + view + ".png"
            unreal.RenderingLibrary.export_render_target(world, target, str(capture_root), name)
            result["captures"].append({"sex": sex, "view": view, "path": str(capture_root / name)})
            write(result)
            state["step"] += 1
            state["frames"] = 0
            if state["step"] == len(steps):
                finish()
        except Exception as exc:
            finish(str(exc))
    state["handle"] = unreal.register_slate_post_tick_callback(tick)


main()
