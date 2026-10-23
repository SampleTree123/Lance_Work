"""Capture only the isolated garment, using temporary actors and shared materials."""
import json
import time
from pathlib import Path

import unreal

ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1\optimization_20260907")


def main():
    destination = ROOT / globals().get("DM_WARDROBE_CAPTURE_SUBDIR", "visual_probe")
    if destination.resolve().parent != ROOT.resolve():
        raise ValueError("Capture output must be directly under the probe root")
    if destination.exists():
        raise FileExistsError(destination)
    report = json.loads((ROOT / "ue_probe.json").read_text(encoding="utf-8"))
    meshes = [unreal.load_asset(report[k]["path"]) for k in ("baseline", "derivative")]
    if not all(isinstance(mesh, unreal.SkeletalMesh) for mesh in meshes):
        raise RuntimeError("Probe meshes unavailable")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    spawned = []
    scheduled = False
    destination.mkdir()
    try:
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(10000, 0, 0), transient=True)
        spawned.append(actor)
        garment = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        camera = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(10100, 0, 100),
                                              unreal.Rotator(0, 180, 0), transient=True)
        spawned.append(camera)
        capture = camera.get_component_by_class(unreal.SceneCaptureComponent2D)
        capture.set_editor_property("capture_every_frame", False)
        capture.set_editor_property("capture_on_movement", False)
        source_name = globals().get("DM_WARDROBE_CAPTURE_SOURCE", "SCS_FINAL_COLOR_LDR")
        if source_name not in {"SCS_FINAL_COLOR_LDR", "SCS_BASE_COLOR"}:
            raise ValueError("Unsupported probe capture source")
        capture.set_editor_property("capture_source", getattr(unreal.SceneCaptureSource, source_name))
        capture.set_editor_property("primitive_render_mode", unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
        capture.show_only_actor_components(actor)
        capture.set_editor_property("fov_angle", 30.0)
        target = unreal.RenderingLibrary.create_render_target2d(world, 768, 768,
                    unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.LinearColor(0, 0, 0, 1))
        capture.set_editor_property("texture_target", target)
        light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(10080, 0, 170), transient=True)
        spawned.append(light)
        component = light.get_component_by_class(unreal.PointLightComponent)
        component.set_intensity(3000.0)
        component.set_editor_property("attenuation_radius", 500.0)
        steps = [(name, mesh, view, location, rotation)
                 for name, mesh in zip(("baseline", "derivative"), meshes)
                 for view, location, rotation in (
                     ("front", unreal.Vector(10100, 0, 100), unreal.Rotator(0, 180, 0)),
                     ("back", unreal.Vector(9900, 0, 100), unreal.Rotator(0, 0, 0)))]
        state = {"index": 0, "prepared": False, "deadline": 0.0}

        def cleanup(error=None):
            unreal.unregister_slate_post_tick_callback(state["handle"])
            for item in reversed(spawned):
                actors.destroy_actor(item)
            (destination / "capture_result.json").write_text(json.dumps({
                "capture_commands_completed": error is None, "error": error,
                "visual_approval": "pending_pixel_check", "transient_actors_removed": True,
                "capture_source": source_name
            }, indent=2) + "\n", encoding="utf-8")

        def tick(_delta):
            try:
                if state["index"] >= len(steps):
                    cleanup()
                    return
                name, mesh, view, location, rotation = steps[state["index"]]
                if not state["prepared"]:
                    garment.set_skeletal_mesh_asset(mesh)
                    garment.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                    garment.set_update_animation_in_editor(True)
                    garment.set_component_tick_enabled(True)
                    for index, material in enumerate(meshes[0].get_editor_property("materials")):
                        garment.set_material(index, material.material_interface)
                    camera.set_actor_location_and_rotation(location, rotation, False, True)
                    state["prepared"] = True
                    state["deadline"] = time.monotonic() + 3.0
                    return
                if time.monotonic() < state["deadline"]:
                    return
                capture.capture_scene()
                unreal.RenderingLibrary.export_render_target(world, target, str(destination), f"{name}_{view}.png")
                state["index"] += 1
                state["prepared"] = False
            except Exception as exc:
                cleanup(str(exc))

        state["handle"] = unreal.register_slate_post_tick_callback(tick)
        scheduled = True
        print("WARDROBE_PROBE_CAPTURE_SCHEDULED " + str(destination))
    finally:
        if not scheduled:
            for actor in reversed(spawned):
                actors.destroy_actor(actor)


if globals().get("DM_CAPTURE_WARDROBE_PROBE"):
    main()
