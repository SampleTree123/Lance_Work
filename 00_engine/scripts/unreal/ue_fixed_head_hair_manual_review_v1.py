"""Human UE review of all 40 retained hairs on both fixed reference heads.

Only the independent review map is saved. No capture, mesh/material edits,
CC operations, import, or formal index/report mutation occurs.

runpy globals: DM_FHMR_MODE show/view/status/restore; DM_FHMR_INDEX 1..40;
DM_FHMR_VIEW front/side/back/threequarter; DM_FHMR_SEX both/female/male.
Optional DM_FHMR_HAIR_ID selects the style directly.
"""
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import unreal

REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "00_engine/outputs/unreal_character_import/fixed_head_hair_manual_review_20261005_v1"
IMPORT = REPO / "00_engine/outputs/unreal_character_import/fixed_head_hair_20261004_v1/import_report.json"
LEVEL = "/Game/DataMake/Validation/FixedHeadHair/L_DM_FixedHeadHair_ManualReview_v001"
PREFIX = "DM_FHMR_"
MARKER = "DM_FIXED_HEAD_HAIR_MANUAL_REVIEW="
THROTTLE = "_dm_fhmr_original_cpu_throttle"
TICK = "_dm_fhmr_view_tick"
YAW = {"front": -90., "side": 0., "back": 90., "threequarter": -45.}
POSITION = {"female": unreal.Vector(0, -80, 0), "male": unreal.Vector(0, 80, 0)}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(name, value):
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / name
    partial = path.with_suffix(".json.partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)


def vec(value):
    return [value.x, value.y, value.z]


def rot(value):
    return [value.pitch, value.yaw, value.roll]


def asset_path(asset):
    return asset.get_path_name() if asset is not None else None


def world_path():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return world.get_path_name().split(":")[0].split(".")[0] if world else None


def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def find(label):
    matches = [a for a in actors().get_all_level_actors() if a.get_actor_label() == label]
    if len(matches) > 1:
        raise RuntimeError("Duplicate review actor: " + label)
    return matches[0] if matches else None


def actor(label, cls, location, rotation=None):
    existing = find(label)
    if existing is not None:
        return existing
    created = actors().spawn_actor_from_class(cls, location, rotation or unreal.Rotator())
    if created is None:
        raise RuntimeError("Could not spawn review actor " + label)
    created.set_actor_label(label)
    return created


def performance():
    return unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")


def background_updates():
    settings = performance()
    if not hasattr(unreal, THROTTLE):
        setattr(unreal, THROTTLE, settings.get_editor_property("bThrottleCPUWhenNotForeground"))
    settings.set_editor_property("bThrottleCPUWhenNotForeground", False)


def cancel_tick():
    handle = getattr(unreal, TICK, None)
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
        delattr(unreal, TICK)


def restore():
    cancel_tick()
    previous = getattr(unreal, THROTTLE, None)
    restored = hasattr(unreal, THROTTLE)
    if restored:
        performance().set_editor_property("bThrottleCPUWhenNotForeground", previous)
        delattr(unreal, THROTTLE)
    return {"success": True, "mode": "restore", "level": world_path(),
            "background_cpu_preference_restored": restored, "previous_value": previous,
            "editor_closed": False, "at_utc": now()}


def ensure_level():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    original = world_path()
    if original != LEVEL:
        dirty = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError("Preserve the current map: save its existing changes before review: " + str(dirty))
        if not (ROOT / "entry_context.json").exists():
            location, rotation = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
            write("entry_context.json", {"original_level": original, "editor_pid": os.getpid(),
                "at_utc": now(), "original_camera_position": vec(location),
                "original_camera_rotation": rot(rotation), "original_level_modified": False})
        levels.eject_pilot_level_actor()
        opened = (levels.load_level(LEVEL) if unreal.EditorAssetLibrary.does_asset_exist(LEVEL)
                  else levels.new_level(LEVEL))
        if not opened:
            raise RuntimeError("Cannot open independent review map " + LEVEL)
    return levels


def environment():
    floor = actor(PREFIX + "Floor", unreal.StaticMeshActor, unreal.Vector(0, 0, -5))
    floor.set_actor_scale3d(unreal.Vector(6, 6, .05))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    wall = actor(PREFIX + "Background", unreal.StaticMeshActor, unreal.Vector(-220, 0, 180))
    wall.set_actor_scale3d(unreal.Vector(.05, 6, 4))
    wall.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    key = actor(PREFIX + "Key", unreal.DirectionalLight, unreal.Vector(0, 0, 300),
                unreal.Rotator(pitch=-35, yaw=-35))
    key.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", .7)
    for name, x, yaw, intensity in (("FrontFill", 200, 180, 100.), ("BackFill", -140, 0, 70.)):
        lamp = actor(PREFIX + name, unreal.RectLight, unreal.Vector(x, 0, 190), unreal.Rotator(yaw=yaw))
        lamp.get_component_by_class(unreal.RectLightComponent).set_editor_properties({
            "intensity": intensity, "source_width": 350., "source_height": 300.})
    volume = actor(PREFIX + "Exposure", unreal.PostProcessVolume, unreal.Vector())
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    settings.set_editor_properties({"override_auto_exposure_method": True,
        "auto_exposure_method": unreal.AutoExposureMethod.AEM_MANUAL,
        "override_auto_exposure_apply_physical_camera_exposure": True,
        "auto_exposure_apply_physical_camera_exposure": False,
        "override_auto_exposure_bias": True, "auto_exposure_bias": -.8})
    volume.set_editor_property("settings", settings)
    camera = actor(PREFIX + "Camera", unreal.CameraActor, unreal.Vector(280, 0, 165), unreal.Rotator(yaw=180))
    camera.get_component_by_class(unreal.CameraComponent).set_editor_properties({
        "field_of_view": 45., "constrain_aspect_ratio": False})


def contract():
    spec = importlib.util.spec_from_file_location("dm_fhmr_contract", Path(__file__).with_name("formal_wardrobe_registry_v1.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    index = module.read_registry(module.MATERIAL_REPAIR_REGISTRY)
    hair = sorted(index["hair_assets"], key=lambda row: row["hair_id"])
    if len(hair) != 40:
        raise RuntimeError("Review index must contain exactly 40 styles")
    imported = read(IMPORT)
    if not imported.get("success") or not imported.get("complete"):
        raise RuntimeError("Complete fixed-head import required")
    return module, hair, imported["bases"]


def component(body_actor):
    return body_actor.get_editor_property("skeletal_mesh_component")


def stage_style(module, hair, bases):
    for sex in ("female", "male"):
        title = sex.title()
        base = bases[sex]
        body_actor = actor(PREFIX + title + "_Body", unreal.SkeletalMeshActor,
                           POSITION[sex], unreal.Rotator(yaw=-90))
        body = component(body_actor)
        mesh = unreal.load_asset(base["body_mesh"])
        if mesh is None or asset_path(mesh.get_editor_property("skeleton")) != base["skeleton_path"]:
            raise RuntimeError("Fixed reference body Skeleton mismatch: " + sex)
        body.set_skeletal_mesh_asset(mesh)
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        body_actor.set_actor_location(POSITION[sex], False, False)
        body_actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
        fit = module.hair_fit(hair, sex)
        if fit["skeleton_path"] != base["skeleton_path"]:
            raise RuntimeError("Index fit Skeleton differs from fixed body")
        pool_prefix = PREFIX + title + "_Hair_"
        for number, item in enumerate(fit["meshes"]):
            follower = actor(pool_prefix + f"{number:03d}", unreal.SkeletalMeshActor,
                             body_actor.get_actor_location(), body_actor.get_actor_rotation())
            follower.attach_to_actor(body_actor, "", unreal.AttachmentRule.SNAP_TO_TARGET,
                                    unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET)
            follower.set_actor_hidden_in_game(False)
            follower.set_is_temporarily_hidden_in_editor(False)
            comp = component(follower)
            mesh = unreal.load_asset(item["path"])
            if mesh is None or asset_path(mesh.get_editor_property("skeleton")) != base["skeleton_path"]:
                raise RuntimeError("Hair branch Skeleton mismatch: " + item["path"])
            comp.set_editor_property("override_materials", [])
            comp.set_skeletal_mesh_asset(mesh)
            comp.set_leader_pose_component(body, True)
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        # Clear unused reusable slots; do not accumulate duplicate avatars.
        for follower in actors().get_all_level_actors():
            if follower.get_actor_label().startswith(pool_prefix):
                number = int(follower.get_actor_label().removeprefix(pool_prefix))
                if number >= len(fit["meshes"]):
                    component(follower).set_skeletal_mesh_asset(None)
                    follower.set_actor_hidden_in_game(True)
                    follower.set_is_temporarily_hidden_in_editor(True)


def bindings(hair, bases):
    rows = []
    for sex in ("female", "male"):
        body_actor = find(PREFIX + sex.title() + "_Body")
        if body_actor is None:
            raise RuntimeError("Review body missing: " + sex)
        body = component(body_actor)
        body_mesh = body.get_editor_property("skeletal_mesh_asset")
        expected_skeleton = bases[sex]["skeleton_path"]
        body_ok = asset_path(body_mesh) == bases[sex]["body_mesh"] and asset_path(body_mesh.get_editor_property("skeleton")) == expected_skeleton
        if not body_ok:
            raise RuntimeError("Fixed body binding changed")
        expected = hair["fit_variants"][sex]["meshes"]
        entries = []
        for number, item in enumerate(expected):
            follower = find(PREFIX + sex.title() + "_Hair_" + f"{number:03d}")
            comp = component(follower)
            mesh = comp.get_editor_property("skeletal_mesh_asset")
            skeleton_ok = asset_path(mesh.get_editor_property("skeleton")) == expected_skeleton
            leader_ok = comp.get_editor_property("leader_pose_component") == body
            same_mesh = asset_path(mesh) == item["path"]
            if not skeleton_ok or not leader_ok or not same_mesh:
                raise RuntimeError("Live hair binding mismatch")
            entries.append({"name": item["name"], "path": asset_path(mesh),
                "actor": follower.get_path_name(), "skeleton_match": skeleton_ok,
                "leader_pose_match": leader_ok, "position": vec(follower.get_actor_location()),
                "rotation": rot(follower.get_actor_rotation())})
        rows.append({"sex": sex, "hair_id": hair["hair_id"], "body_mesh": asset_path(body_mesh),
            "mesh_count": len(entries), "skeleton_path": expected_skeleton,
            "skeleton_match": True, "leader_pose_match": True, "meshes": entries,
            "body_position": vec(body_actor.get_actor_location()), "body_rotation": rot(body_actor.get_actor_rotation()),
            "body_scale": vec(body_actor.get_actor_scale3d())})
    return rows


def set_view(view, sex):
    if world_path() != LEVEL:
        raise RuntimeError("Open the independent review level first")
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    background_updates()
    for gender in ("female", "male"):
        find(PREFIX + gender.title() + "_Body").set_actor_rotation(unreal.Rotator(yaw=YAW[view]), False)
    selected = ("female", "male") if sex == "both" else (sex,)
    heights = []
    for gender in selected:
        body = component(find(PREFIX + gender.title() + "_Body"))
        names = [str(body.get_bone_name(i)) for i in range(body.get_num_bones())]
        head = next((name for name in names if name.lower() in ("head", "cc_base_head")), None)
        heights.append(body.get_socket_location(head).z + 10. if head else 165.)
    location = unreal.Vector(280 if sex == "both" else 170, 0 if sex == "both" else POSITION[sex].y,
                             sum(heights) / len(heights))
    rotation = unreal.Rotator(yaw=180)
    camera = find(PREFIX + "Camera")
    camera.set_actor_location(location, False, False)
    camera.set_actor_rotation(rotation, False)
    levels.editor_set_viewport_realtime(True)
    levels.editor_set_game_view(True)
    levels.editor_set_game_view(False)
    levels.editor_set_game_view(True)
    levels.pilot_level_actor(camera)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(location, rotation)
    levels.editor_invalidate_viewports()
    return {"position": vec(location), "rotation": rot(rotation), "field_of_view": 45.,
            "body_yaw": YAW[view], "selected_sex": sex}


def current_state(hair, bases, index, view, sex, pending=False):
    location, rotation = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
    return {"schema_version": 1, "success": True, "index": index,
        "hair_id": hair["hair_id"], "display_name": hair["display_name"], "view": view, "sex": sex,
        "level": LEVEL, "editor_pid": os.getpid(), "at_utc": now(), "bindings": bindings(hair, bases),
        "camera_position": vec(location), "camera_rotation": rot(rotation),
        "viewport_refresh_pending": pending, "background_cpu_throttle": performance().get_editor_property("bThrottleCPUWhenNotForeground"),
        "capture_requested": False, "visual_decision": "human_review_required"}


def queue_refresh(hair, bases, index, view, sex):
    cancel_tick()
    count = [0]
    def tick(delta):
        try:
            if world_path() != LEVEL:
                cancel_tick()
                return
            count[0] += 1
            set_view(view, sex)
            if count[0] >= 4:
                write("current_case.json", current_state(hair, bases, index, view, sex))
                cancel_tick()
        except Exception as exc:
            write("view_refresh_error.json", {"success": False, "error": str(exc), "at_utc": now()})
            cancel_tick()
    setattr(unreal, TICK, unreal.register_slate_post_tick_callback(tick))


def main():
    mode = globals().get("DM_FHMR_MODE", "show")
    if mode == "restore":
        return restore()
    module, styles, bases = contract()
    if mode == "status":
        if world_path() != LEVEL or not (ROOT / "current_case.json").exists():
            return {"success": False, "mode": "status", "level": world_path(), "error": "Review level is not open"}
        saved = read(ROOT / "current_case.json")
        hair = next(row for row in styles if row["hair_id"] == saved["hair_id"])
        return current_state(hair, bases, saved["index"], saved["view"], saved["sex"], saved.get("viewport_refresh_pending", False))
    if mode not in ("show", "view"):
        raise ValueError("Unknown DM_FHMR_MODE")
    view = globals().get("DM_FHMR_VIEW", "front")
    sex = globals().get("DM_FHMR_SEX", "both")
    if view not in YAW or sex not in ("both", "female", "male"):
        raise ValueError("Invalid review view/sex")
    if mode == "show":
        index = int(globals().get("DM_FHMR_INDEX", 1))
        hair_id = globals().get("DM_FHMR_HAIR_ID")
        if hair_id is not None:
            index = next(i for i, item in enumerate(styles, 1) if item["hair_id"] == hair_id)
        if not 1 <= index <= 40:
            raise ValueError("Hair index must be 1..40")
        hair = styles[index - 1]
        levels = ensure_level()
        environment()
        stage_style(module, hair, bases)
    else:
        if world_path() != LEVEL or not (ROOT / "current_case.json").exists():
            raise RuntimeError("Load a hair style with show before changing view")
        previous = read(ROOT / "current_case.json")
        index = previous["index"]
        hair = next(row for row in styles if row["hair_id"] == previous["hair_id"])
        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    camera = set_view(view, sex)
    if not levels.save_current_level():
        raise RuntimeError("Cannot save independent manual review level")
    state = current_state(hair, bases, index, view, sex, pending=True)
    state["requested_camera"] = camera
    write("current_case.json", state)
    queue_refresh(hair, bases, index, view, sex)
    return state


try:
    result = main()
except Exception as exc:
    result = {"success": False, "mode": globals().get("DM_FHMR_MODE", "show"), "error": str(exc), "at_utc": now()}
    write("last_error.json", result)
    print(MARKER + json.dumps(result, ensure_ascii=False))
    raise
else:
    print(MARKER + json.dumps(result, ensure_ascii=False))
