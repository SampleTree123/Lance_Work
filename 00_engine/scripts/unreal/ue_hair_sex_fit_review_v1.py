"""Stage and capture the 51 bounded M02/F02 hairstyle review cases in UE Editor."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import unreal


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import formal_wardrobe_registry_v1 as formal  # noqa: E402
import ue_formal_wardrobe_runtime_v1 as runtime  # noqa: E402
import ue_build_modular_outfit_runtime_v2 as base  # noqa: E402


REVIEW_ROOT = ROOT.parents[1] / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
PLAN_PATH = REVIEW_ROOT / "review_plan.json"
CAPTURE_ROOT = REVIEW_ROOT / "captures"
LEVEL_PATH = "/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001"
PREFIX = "DM_HairSexFit_"
BODY_LABEL = PREFIX + "Body"
CAMERA_LOCATION = unreal.Vector(145.0, 0.0, 165.0)
CAMERA_ROTATION = unreal.Rotator(yaw=180.0)
VIEW_YAWS = {
    "front": -90.0,
    "front_left": -45.0,
    "left": 0.0,
    "back": 90.0,
    "right": 180.0,
    "front_right": -135.0,
}


def _write(name: str, value: dict, root: Path = REVIEW_ROOT) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    partial.replace(path)
    return path


def _plan() -> dict:
    value = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or value.get("level_path") != LEVEL_PATH:
        raise RuntimeError("Unexpected hairstyle review plan")
    if value.get("registry_sha256") != hashlib.sha256(formal.LEGACY_REGISTRY.read_bytes()).hexdigest():
        raise RuntimeError("Formal registry changed after the hairstyle review plan was frozen")
    if value.get("counts") != {"total": 51, "female": 30, "male": 21}:
        raise RuntimeError("Unexpected hairstyle review scope")
    return value


def _case(plan: dict, index: int) -> dict:
    if not 1 <= index <= len(plan["cases"]):
        raise ValueError(f"Review index outside 1..{len(plan['cases'])}: {index}")
    return plan["cases"][index - 1]


def _world_path() -> str:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return world.get_path_name().split(":")[0].split(".")[0] if world else ""


def _load_level() -> None:
    if _world_path() != LEVEL_PATH:
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(LEVEL_PATH):
            raise RuntimeError(f"Cannot load hairstyle review level: {LEVEL_PATH}")


def _spawn(cls, location, rotation=unreal.Rotator(), transient=False):
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        cls, location, rotation, transient=transient
    )
    if actor is None:
        raise RuntimeError(f"Cannot spawn review actor: {cls}")
    return actor


def _component(actor, cls):
    item = actor.get_component_by_class(cls)
    if item is None:
        raise RuntimeError(f"{actor.get_name()} lacks {cls.__name__}")
    return item


def _environment() -> None:
    backdrop = _spawn(unreal.StaticMeshActor, unreal.Vector(-100, 0, 165))
    backdrop.set_actor_label(PREFIX + "Backdrop")
    backdrop.set_actor_scale3d(unreal.Vector(0.04, 3.0, 3.0))
    backdrop.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    key = _spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(pitch=-35, yaw=-35))
    key.set_actor_label(PREFIX + "KeyLight")
    _component(key, unreal.DirectionalLightComponent).set_editor_property("intensity", 0.35)
    for name, location, intensity in (
        ("FillLight", unreal.Vector(190, -100, 180), 60.0),
        ("RimLight", unreal.Vector(-50, 100, 210), 70.0),
    ):
        lamp = _spawn(unreal.RectLight, location, unreal.Rotator(yaw=180))
        lamp.set_actor_label(PREFIX + name)
        comp = _component(lamp, unreal.RectLightComponent)
        comp.set_editor_property("intensity", intensity)
        comp.set_editor_property("source_width", 140.0)
        comp.set_editor_property("source_height", 140.0)
    camera = _spawn(unreal.CineCameraActor, CAMERA_LOCATION, CAMERA_ROTATION)
    camera.set_actor_label(PREFIX + "Camera")
    camera.get_cine_camera_component().set_editor_property("current_focal_length", 65.0)
    _configure_exposure(_spawn(unreal.PostProcessVolume, unreal.Vector(0, 0, 0)))


def _configure_exposure(volume) -> None:
    volume.set_actor_label(PREFIX + "PostProcess")
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
    settings.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", -0.8)
    volume.set_editor_property("settings", settings)


def build() -> dict:
    plan = _plan()
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
        _load_level()
        by_label = {actor.get_actor_label(): actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
        expected = (PREFIX + "Camera", PREFIX + "KeyLight", PREFIX + "FillLight", PREFIX + "RimLight")
        if any(label not in by_label for label in expected):
            raise RuntimeError("Existing review level is missing a camera or light")
        by_label[PREFIX + "Camera"].set_actor_rotation(CAMERA_ROTATION, False)
        by_label[PREFIX + "Camera"].set_actor_location(CAMERA_LOCATION, False, False)
        by_label[PREFIX + "KeyLight"].set_actor_rotation(unreal.Rotator(pitch=-35, yaw=-35), False)
        _component(by_label[PREFIX + "KeyLight"], unreal.DirectionalLightComponent).set_editor_property("intensity", 0.35)
        by_label[PREFIX + "FillLight"].set_actor_rotation(unreal.Rotator(yaw=180), False)
        by_label[PREFIX + "RimLight"].set_actor_rotation(unreal.Rotator(yaw=180), False)
        _component(by_label[PREFIX + "FillLight"], unreal.RectLightComponent).set_editor_property("intensity", 60.0)
        _component(by_label[PREFIX + "RimLight"], unreal.RectLightComponent).set_editor_property("intensity", 70.0)
        volume = by_label.get(PREFIX + "PostProcess") or _spawn(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
        _configure_exposure(volume)
        if not levels.save_current_level():
            raise RuntimeError("Cannot save repaired hairstyle review level")
        return {"level": LEVEL_PATH, "created": False, "case_count": len(plan["cases"]), "success": True}
    if not levels.new_level(LEVEL_PATH):
        raise RuntimeError(f"Cannot create review level: {LEVEL_PATH}")
    _environment()
    if not levels.save_current_level():
        raise RuntimeError("Cannot save hairstyle review level")
    result = {"level": LEVEL_PATH, "created": True, "case_count": len(plan["cases"]), "success": True}
    _write("level_build_report.json", result)
    return result


def _remove_body() -> None:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    # EditorActorSubsystem's enumeration omits transient capture actors.
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if actor.get_actor_label() == BODY_LABEL:
            actors.destroy_actor(actor)


def _stage(case: dict, *, transient: bool = False):
    registry = formal.read_registry(formal.LEGACY_REGISTRY)
    hair = next((row for row in registry["hair_assets"] if row["hair_id"] == case["hair_id"]), None)
    if hair is None or hair["sex"] not in {case["sex"], "both"}:
        raise RuntimeError(f"Hairstyle no longer eligible: {case['hair_id']}/{case['sex']}")
    if [mesh["path"] for mesh in hair["meshes"]] != case["mesh_paths"]:
        raise RuntimeError("Frozen review mesh list differs from registry")
    bodyfit = runtime.bodyfit_record(case["bodyfit_id"])
    blueprint = unreal.load_asset(bodyfit["blueprint_path"])
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"v003 review Blueprint missing: {bodyfit['blueprint_path']}")
    meshes = []
    for path in case["mesh_paths"]:
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError(f"Hairstyle mesh missing: {path}")
        if base.object_path(mesh.get_editor_property("skeleton")) != runtime.HAIR_SKELETON:
            raise RuntimeError(f"Hairstyle Skeleton differs from F02: {path}")
        meshes.append(mesh)
    _remove_body()
    actor = _spawn(blueprint.generated_class(), unreal.Vector(0, 0, 0), unreal.Rotator(yaw=-90), transient=transient)
    actor.set_actor_label(BODY_LABEL)
    body, followers = base.actor_components(actor, bodyfit)
    components = {component.get_name(): component for component in followers}
    for index, mesh in enumerate(meshes, 1):
        component = components[f"HairPart{index:02d}"]
        if component.get_editor_property("leader_pose_component") != body:
            raise RuntimeError(f"HairPart{index:02d} has no Body leader")
        component.set_skeletal_mesh_asset(mesh)
        component.set_visibility(True, False)
        component.set_hidden_in_game(False)
    active = [component for component in followers if component.get_skeletal_mesh_asset() is not None]
    if len(active) != len(meshes) or any(not c.get_name().startswith("HairPart") for c in active):
        raise RuntimeError("Review actor contains unexpected clothing or hair mesh")
    return actor


def _invisible_scalp_material():
    material = unreal.Material()
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("used_with_skeletal_mesh", True)
    zero = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant)
    zero.set_editor_property("r", 0.0)
    if not unreal.MaterialEditingLibrary.connect_material_property(zero, "", unreal.MaterialProperty.MP_OPACITY_MASK):
        raise RuntimeError("Cannot connect constant-zero scalp visibility mask")
    unreal.MaterialEditingLibrary.recompile_material(material)
    return material


def _hide_scalp(actor, case: dict, rows: list, invisible) -> dict:
    expected = {(row["mesh"], row["slot_index"]): row for row in rows
                if row["hair_id"] == case["hair_id"] and row["slot_name"].lower().startswith("scalp")}
    hidden = []
    unchanged = []
    seen = set()
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh = component.get_skeletal_mesh_asset()
        if mesh is None or not component.get_name().startswith("HairPart"):
            continue
        for index, slot in enumerate(mesh.get_editor_property("materials")):
            key = (mesh.get_path_name(), index)
            before = component.get_material(index)
            name = str(slot.get_editor_property("material_slot_name"))
            row = {"mesh": key[0], "slot_index": index, "slot_name": name,
                   "component": component.get_name(), "original_material": before.get_path_name() if before else None}
            if key in expected:
                if name != expected[key]["slot_name"] or not name.lower().startswith("scalp"):
                    raise RuntimeError(f"Scalp slot mapping changed: {key}/{name}")
                component.set_material(index, invisible)
                if component.get_material(index) != invisible:
                    raise RuntimeError(f"Invisible scalp override failed: {key}")
                row["override_material"] = invisible.get_path_name()
                hidden.append(row)
                seen.add(key)
            else:
                if name.lower().startswith("scalp"):
                    raise RuntimeError(f"Unmapped scalp slot: {key}/{name}")
                if component.get_material(index) != before:
                    raise RuntimeError(f"Non-scalp material changed: {key}")
                unchanged.append(row)
            if slot.get_editor_property("material_interface") != before:
                raise RuntimeError(f"Source mesh material differs from staged original: {key}")
    if seen != set(expected):
        raise RuntimeError(f"Missing staged scalp slots: {set(expected) - seen}")
    return {"review_index": case["review_index"], "hair_id": case["hair_id"], "sex": case["sex"],
            "hidden_slots": hidden, "unchanged_slots": unchanged,
            "no_scalp_slot": not hidden, "source_assets_modified": False}


def set_view(view: str) -> dict:
    if view not in VIEW_YAWS:
        raise ValueError(f"Unknown view: {view}")
    _load_level()
    actor = next((item for item in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                  if item.get_actor_label() == BODY_LABEL), None)
    if actor is None:
        raise RuntimeError("Show a hairstyle review case first")
    actor.set_actor_rotation(unreal.Rotator(yaw=VIEW_YAWS[view]), False)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.editor_set_viewport_realtime(True)
    levels.editor_set_game_view(True)
    levels.editor_set_game_view(False)
    levels.editor_set_game_view(True)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector(100, 0, 165), CAMERA_ROTATION
    )
    return {"view": view, "success": True}


def show(index: int) -> dict:
    plan = _plan()
    case = _case(plan, index)
    _load_level()
    actor = _stage(case)
    set_view("front")
    result = {"review_index": index, "sex": case["sex"], "hair_id": case["hair_id"],
              "mesh_count": len(case["mesh_paths"]), "actor": actor.get_path_name(),
              "visual_decision": "pending", "success": True}
    _write("current_case.json", result)
    return result


def capture_range(start: int, count: int) -> dict:
    if getattr(unreal, "_dm_hair_fit_cancel", None) is not None or getattr(unreal, "_dm_scalp_probe_cancel", None) is not None:
        raise RuntimeError("A hairstyle capture is already active; finish or cancel it before starting another")
    plan = _plan()
    if count <= 0 or start < 1 or start + count - 1 > len(plan["cases"]):
        raise ValueError("Capture range outside review plan")
    _load_level()
    capture_root = Path(globals().get("DM_HSF_CAPTURE_ROOT", str(CAPTURE_ROOT))).resolve()
    if not capture_root.is_relative_to(REVIEW_ROOT.resolve()):
        raise ValueError("Capture output must remain within the review Run Root")
    capture_root.mkdir(parents=True, exist_ok=True)
    hide_scalp = bool(globals().get("DM_HSF_HIDE_SCALP", False))
    progress_root = Path(globals().get("DM_HSF_PROGRESS_ROOT", str(REVIEW_ROOT))).resolve()
    if not progress_root.is_relative_to(REVIEW_ROOT.resolve()):
        raise ValueError("Capture progress must remain within the review Run Root")
    if hide_scalp and (capture_root == CAPTURE_ROOT.resolve() or progress_root == REVIEW_ROOT.resolve()):
        raise ValueError("Hidden-scalp candidates need separate image and progress directories")
    cases = plan["cases"][start - 1:start - 1 + count]
    if hide_scalp and any((capture_root / f"{case['review_index']:03d}_{case['sex']}_{case['hair_id']}_{view}.png").exists()
                          for case in cases for view in VIEW_YAWS):
        raise FileExistsError("Keep existing candidate evidence; choose a new run or an uncaptured range")
    scalp_rows = (json.loads((REVIEW_ROOT / "rendering_repair_v2/repair_plan.json").read_text(encoding="utf-8"))["rows"]
                  if hide_scalp else [])
    invisible = _invisible_scalp_material() if hide_scalp else None
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    camera = _spawn(unreal.SceneCapture2D, CAMERA_LOCATION, CAMERA_ROTATION, transient=True)
    capture = _component(camera, unreal.SceneCaptureComponent2D)
    capture.set_editor_property("capture_every_frame", False)
    capture.set_editor_property("always_persist_rendering_state", True)
    capture.set_editor_property("capture_on_movement", False)
    capture.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    capture.set_editor_property("show_flag_settings", [
        unreal.EngineShowFlagsSetting(show_flag_name=name, enabled=True)
        for name in ("AntiAliasing", "TemporalAA", "PostProcessing")
    ])
    capture.set_editor_property("fov_angle", 28.0)
    target = unreal.RenderingLibrary.create_render_target2d(
        world, 900, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8,
        unreal.LinearColor(0.18, 0.18, 0.18, 1.0),
    )
    capture.set_editor_property("texture_target", target)
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    previous_throttle = settings.get_editor_property("bThrottleCPUWhenNotForeground")
    settings.set_editor_property("bThrottleCPUWhenNotForeground", False)
    previous_aa = unreal.SystemLibrary.get_console_variable_int_value("r.AntiAliasingMethod")
    if previous_aa not in (2, 4):
        unreal.SystemLibrary.execute_console_command(world, "r.AntiAliasingMethod 4")
    capture_aa = unreal.SystemLibrary.get_console_variable_int_value("r.AntiAliasingMethod")
    steps = [(case, view) for case in cases for view in VIEW_YAWS]
    state = {"index": 0, "active_case": None, "prepared": False, "deadline": 0.0, "warmup_frames": 0,
             "completed_images": 0, "error": None, "handle": None, "scalp_audits": [], "active_actor": None}
    progress_name = f"capture_progress_{start:03d}_{start + count - 1:03d}.json"

    def progress(done=False):
        _write(progress_name, {
            "start": start, "count": count, "total_images": len(steps),
            "completed_images": state["completed_images"], "success": done and state["error"] is None,
            "done": done, "error": state["error"], "at_utc": datetime.now(timezone.utc).isoformat(),
            "capture_root": str(capture_root), "temporal_warmup_frames": 32,
            "always_persist_rendering_state": True, "anti_aliasing_method": capture_aa,
            "explicit_frame_capture": True,
            "scalp_hidden_candidate": hide_scalp, "source_assets_modified": False,
        }, root=progress_root)
        if hide_scalp:
            _write(f"scalp_hiding_audit_{start:03d}_{start + count - 1:03d}.json",
                   {"done": done, "success": done and state["error"] is None,
                    "cases": state["scalp_audits"], "method": "transient constant-zero opacity mask per Scalp slot",
                    "source_assets_modified": False, "visual_acceptance": "pending_human_review"}, root=progress_root)

    def finish(error=None):
        state["error"] = error
        unreal.unregister_slate_post_tick_callback(state["handle"])
        actors.destroy_actor(camera)
        if hide_scalp:
            if state["active_actor"] is not None:
                actors.destroy_actor(state["active_actor"])
                state["active_actor"] = None
        settings.set_editor_property("bThrottleCPUWhenNotForeground", previous_throttle)
        if previous_aa != capture_aa:
            unreal.SystemLibrary.execute_console_command(world, f"r.AntiAliasingMethod {previous_aa}")
        progress(done=True)
        if getattr(unreal, "_dm_hair_fit_cancel", None) is finish:
            del unreal._dm_hair_fit_cancel

    def tick(_delta):
        try:
            if state["index"] == len(steps):
                finish()
                return
            case, view = steps[state["index"]]
            if state["active_case"] != case["review_index"]:
                if hide_scalp and state["active_actor"] is not None:
                    actors.destroy_actor(state["active_actor"])
                actor = _stage(case, transient=hide_scalp)
                state["active_actor"] = actor
                if hide_scalp:
                    state["scalp_audits"].append(_hide_scalp(actor, case, scalp_rows, invisible))
                state["active_case"] = case["review_index"]
            body = state["active_actor"]
            if not state["prepared"]:
                body.set_actor_rotation(unreal.Rotator(yaw=VIEW_YAWS[view]), False)
                state["prepared"] = True
                state["deadline"] = time.monotonic() + 1.0
                state["warmup_frames"] = 0
                capture.set_editor_property("camera_cut_this_frame", True)
                return
            state["warmup_frames"] += 1
            # Editor worlds may not run automatic SceneCapture while hidden/unattended.
            # Render each warmup frame explicitly while retaining temporal history.
            capture.capture_scene()
            if time.monotonic() < state["deadline"] or state["warmup_frames"] < 32:
                return
            basename = f"{case['review_index']:03d}_{case['sex']}_{case['hair_id']}_{view}"
            unreal.RenderingLibrary.export_render_target(world, target, str(capture_root), basename + ".png")
            image_path = capture_root / (basename + ".png")
            if not image_path.is_file() or image_path.stat().st_size < 1000:
                raise RuntimeError(f"Capture image missing or empty: {image_path}")
            state["completed_images"] += 1
            state["index"] += 1
            state["prepared"] = False
            if state["completed_images"] % len(VIEW_YAWS) == 0:
                progress()
        except Exception as exc:
            finish(f"{type(exc).__name__}: {exc}")

    progress()
    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    unreal._dm_hair_fit_cancel = finish
    return {"started": True, "start": start, "count": count, "progress": str(progress_root / progress_name)}


def main():
    mode = globals().get("DM_HSF_MODE", "")
    if mode == "build":
        result = build()
    elif mode == "show":
        result = show(int(globals().get("DM_HSF_INDEX", 1)))
    elif mode == "view":
        result = set_view(str(globals().get("DM_HSF_VIEW", "front")))
    elif mode == "capture":
        result = capture_range(int(globals().get("DM_HSF_START", 1)), int(globals().get("DM_HSF_COUNT", 1)))
    else:
        raise ValueError("Set DM_HSF_MODE to build, show, view or capture")
    print("DM_HAIR_SEX_FIT_RESULT=" + json.dumps(result, ensure_ascii=False, default=str))
    return result


if __name__ == "__main__" or globals().get("DM_HSF_MODE"):
    main()
