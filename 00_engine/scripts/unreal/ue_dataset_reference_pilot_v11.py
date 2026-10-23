"""Unaccepted scene/garment/identity/hair prototypes over prepared v11 main nodes.

Import is inert. Only dispatch() imports Unreal, and only explicit prepare/render
requests mutate owned assets. This does not publish the reference manifest.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import time
import uuid

SCRIPTS = Path(__file__).resolve().parent
WORKSPACE = SCRIPTS.parents[2]
ROOT = "/Game/DataMake/Render/References"
LIVE = "_dm_dataset_reference_pilot_v11"
VERSION = 6


def module(name):
    spec = importlib.util.spec_from_file_location("_reference_" + name, SCRIPTS / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def object_path(package):
    return package + "." + package.rsplit("/", 1)[1]


def owned_package(path):
    package = path.split(".")[0]
    if not package.startswith(ROOT + "/") or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", package):
        raise ValueError("Reference destination must stay below its owned asset root")
    return package


def zero_key(u, channel):
    found = []
    for key in channel.get_keys():
        stamp = key.get_time(time_unit=u.MovieSceneTimeUnit.DISPLAY_RATE)
        if int(stamp.frame_number.value) == 0 and abs(float(stamp.sub_frame)) < 1e-8:
            found.append(float(key.get_value()))
    if len(found) != 1 or not math.isfinite(found[0]):
        raise ValueError("Require one finite source-sequence key at frame zero")
    return found[0]


def first_camera(u, sequence, prepared_first):
    """Read actual saved main sequence keys, never infer from a plan alone."""
    rate = sequence.get_display_rate()
    if (rate.numerator, rate.denominator) != (30, 1) or sequence.get_playback_start() != 0:
        raise ValueError("Expected a saved zero-based 30 fps main sequence")
    transforms, fovs = [], []
    for binding in sequence.get_bindings():
        for track in binding.get_tracks():
            for section in track.get_sections():
                if isinstance(track, u.MovieScene3DTransformTrack) and str(binding.get_display_name()) == "Camera pilot baked trajectory":
                    channels = list(section.get_all_channels())
                    names = [str(c.get_editor_property("channel_name")) for c in channels[:9]]
                    if names[3:6] != ["Rotation.X", "Rotation.Y", "Rotation.Z"] or len(channels) != 9:
                        raise ValueError("Unexpected source camera transform channels")
                    transforms.append([zero_key(u, c) for c in channels])
                elif isinstance(track, u.MovieSceneFloatTrack):
                    channels = list(section.get_all_channels())
                    if len(channels) != 1:
                        raise ValueError("Unexpected main float track; cannot identify exact camera FOV")
                    fovs.append(zero_key(u, channels[0]))
    if len(transforms) != 1 or len(fovs) != 1:
        raise ValueError("Require exactly one named main camera transform and one FOV track")
    values = transforms[0]
    result = {"position": values[:3], "rotation_pitch_yaw_roll": [values[4], values[5], values[3]],
              "horizontal_fov_degrees": fovs[0], "scale": values[6:9], "source_frame": 0}
    expected = prepared_first["position"] + prepared_first["rotation_pitch_yaw_roll"] + [prepared_first["horizontal_fov_degrees"]]
    actual = result["position"] + result["rotation_pitch_yaw_roll"] + [result["horizontal_fov_degrees"]]
    # UE channel values can round large world coordinates to float precision.
    tolerances=[0.01,0.01,0.01,1e-4,1e-4,1e-4,1e-4]
    if any(abs(float(a) - float(b)) > tol for a, b,tol in zip(actual, expected,tolerances)):
        raise ValueError("Saved main frame-zero camera differs from its prepared receipt: "+str({'actual':actual,'expected':expected}))
    if any(abs(v - 1.0) > 1e-5 for v in result["scale"]):
        raise ValueError("Unexpected main camera scale")
    return result


def source_job(u, run, job, main):
    source_id = job["source_job_id"]
    if not re.fullmatch(r"(?:train|test)_node_\d{6,}", source_id):
        raise ValueError("Expected one adopted main-node job")
    main_path = Path(job.get("main_jobs_path", "main_jobs.json"))
    if not main_path.is_absolute():
        main_path = run / main_path
    source = next(x for x in read(main_path)["jobs"] if x["job_id"] == source_id)
    prepared_path = run / "jobs" / source_id / "prepared.json"
    prepared = read(prepared_path)
    if prepared.get("success") is not True or prepared.get("signature") != main.signature(source):
        raise ValueError("Prepare this exact source main node before its reference prototype")
    pins = []
    for key, suffix in (("map", ".umap"), ("sequence", ".uasset")):
        asset = prepared["job"][key].split(".")[0]
        if not asset.startswith(main.ASSETS + "/") or not u.EditorAssetLibrary.does_asset_exist(asset):
            raise ValueError("Only a saved owned main map/sequence may source a reference")
        path = Path(u.Paths.project_dir()).resolve() / "Content" / (asset.removeprefix("/Game/") + suffix)
        pins.append({"path": str(path), "sha256": digest(path)})
    return source, prepared, {"path": str(prepared_path), "sha256": digest(prepared_path)}, pins


def ensure_not_rendering(u):
    if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
        raise RuntimeError("MRQ active; reference preparation must run serially")


def copy_main_map(u, source, destination):
    """SaveMap alone does not switch editor worlds: always explicitly load copy."""
    owned_package(destination)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not levels.load_level(source.split(".")[0]):
        raise RuntimeError("Cannot load prepared main map")
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if not u.EditorLoadingAndSavingUtils.save_map(world, destination):
        raise RuntimeError("Cannot create reference map copy")
    if not levels.load_level(destination):
        raise RuntimeError("Cannot load owned reference map copy")
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != destination:
        raise RuntimeError("Editor world did not switch to the owned copy")
    return world


def remove_main_subjects(u):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    removed = []
    for actor in list(actors.get_all_level_actors()):
        label = actor.get_actor_label()
        subject = label.startswith(("DM_SiteReview_Dataset_", "DM_Dataset_")) and label != "DM_Dataset_Camera"
        if subject or isinstance(actor, u.LevelSequenceActor):
            removed.append({"label": label, "path": actor.get_path_name()})
            if not actors.destroy_actor(actor):
                raise RuntimeError("Could not remove an owned subject/follower")
    if not any(r["label"] == "DM_SiteReview_Dataset_Character" for r in removed):
        raise ValueError("Source main character label was absent; refusing an unproven background reference")
    remaining = [a.get_actor_label() for a in actors.get_all_level_actors()
                 if a.get_actor_label().startswith(("DM_SiteReview_Dataset_", "DM_Dataset_DM_SiteReview_"))]
    if remaining:
        raise ValueError("Target character/followers remain: " + str(remaining))
    return removed


def apply_camera(u, camera, pose, width, height):
    p, r = pose["position"], pose["rotation_pitch_yaw_roll"]
    camera.set_actor_location(u.Vector(*p), False, False)
    camera.set_actor_rotation(u.Rotator(pitch=r[0], yaw=r[1], roll=r[2]), False)
    component = camera.get_component_by_class(u.CameraComponent)
    component.set_field_of_view(pose["horizontal_fov_degrees"])
    component.set_editor_property("aspect_ratio", width / height)
    component.set_editor_property("constrain_aspect_ratio", True)
    return component


def static_sequence(u, camera, pose, destination):
    owned_package(destination)
    folder, name = destination.rsplit("/", 1)
    sequence = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.LevelSequence, u.LevelSequenceFactoryNew())
    if not isinstance(sequence, u.LevelSequence):
        raise RuntimeError("Reference sequence creation failed")
    sequence.set_display_rate(u.FrameRate(30, 1))
    sequence.set_tick_resolution_directly(u.FrameRate(24000, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(1)
    binding = sequence.add_possessable(camera)
    binding.set_display_name("Reference exact first camera")
    section = binding.add_track(u.MovieScene3DTransformTrack).add_section()
    section.set_range(0, 2)
    channels = list(section.get_all_channels())
    p, r = pose["position"], pose["rotation_pitch_yaw_roll"]
    values = p + [r[2], r[0], r[1], 1.0, 1.0, 1.0]
    if len(channels) != 9:
        raise RuntimeError("Expected nine static camera channels")
    names = [str(c.get_editor_property("channel_name")) for c in channels]
    if names[3:6] != ["Rotation.X", "Rotation.Y", "Rotation.Z"]:
        raise RuntimeError("Unexpected static camera rotation channels")
    for c, value in zip(channels, values):
        for frame in (0, 1):
            c.add_key(u.FrameNumber(frame), float(value), sub_frame=0.0,
                      time_unit=u.MovieSceneTimeUnit.DISPLAY_RATE, interpolation=u.MovieSceneKeyInterpolation.CONSTANT)
    component = camera.get_component_by_class(u.CameraComponent)
    cb = sequence.add_possessable(component)
    cb.set_parent(binding)
    fov = cb.add_track(u.MovieSceneFloatTrack)
    fov.set_property_name_and_path("FieldOfView", "FieldOfView")
    section = fov.add_section()
    section.set_range(0, 2)
    channel = list(section.get_all_channels())[0]
    for frame in (0, 1):
        channel.add_key(u.FrameNumber(frame), float(pose["horizontal_fov_degrees"]), sub_frame=0.0,
                        time_unit=u.MovieSceneTimeUnit.DISPLAY_RATE, interpolation=u.MovieSceneKeyInterpolation.CONSTANT)
    cut = sequence.add_track(u.MovieSceneCameraCutTrack).add_section()
    cut.set_range(0, 1)
    cut.set_camera_binding_id(sequence.get_binding_id(binding))
    if not u.EditorAssetLibrary.save_loaded_asset(sequence, False):
        raise RuntimeError("Cannot save reference sequence")
    return sequence


def garment_target(source, asset_id):
    matches = [a for a in source["appearance"]["wardrobe_assets"] if a["asset_id"] == asset_id]
    if len(matches) != 1 or not matches[0].get("mesh_paths"):
        raise ValueError("Garment must be one actual asset worn by the source main node")
    if matches[0].get("slot") not in ("full_body", "shirts", "pants", "skirts", "coats"):
        raise ValueError("This prototype supports an explicit garment slot only")
    return copy.deepcopy(matches[0])


def garment_framing(bounds, width, height, fov=32.0, view="front"):
    if not bounds or any(len(b["center"]) != 3 or len(b["extent"]) != 3 for b in bounds):
        raise ValueError("Missing actual garment mesh bounds")
    low = [min(b["center"][k] - b["extent"][k] for b in bounds) for k in range(3)]
    high = [max(b["center"][k] + b["extent"][k] for b in bounds) for k in range(3)]
    center = [(a + b) / 2 for a, b in zip(low, high)]
    extent = [(b - a) / 2 for a, b in zip(low, high)]
    if not all(math.isfinite(v) for v in center + extent) or max(extent) < 1.0:
        raise ValueError("Garment bounds are empty or nonfinite")
    tan_h = math.tan(math.radians(fov / 2))
    tan_v = tan_h / (width / height)
    if view not in ("front", "back"):
        raise ValueError("Prototype supports front/back views only")
    # CC reference-pose meshes face +Y before any actor/site yaw is applied.
    distance = max(100.0, extent[1] + 1.18 * max(extent[0] / tan_h, extent[2] / tan_v))
    sign = 1.0 if view == "front" else -1.0
    return {"position": [center[0], center[1] + sign * distance, center[2]], "rotation_pitch_yaw_roll": [0.0, -90.0 if view == "front" else 90.0, 0.0],
            "horizontal_fov_degrees": fov, "bounds_center": center, "bounds_extent": extent,
            "view": view, "front_axis": "+Y in unrotated CC reference pose",
            "presentation_status": "prototype_unapproved_reference_pose"}


def head_framing(head_position, hair_bounds, kind, view, width, height):
    """Static +Y-front CC carrier; include complete hair, or focus the face."""
    if kind not in ("identity", "hair") or view not in ("front", "back"):
        raise ValueError("Expected identity/hair and a front/back view")
    if kind == "identity" and view != "front":
        raise ValueError("Identity prototype currently supports front face only")
    if len(head_position) != 3 or not all(math.isfinite(float(v)) for v in head_position) or head_position[2] < 20:
        raise ValueError("Expected a valid standing CC head socket")
    face_center = [head_position[0], head_position[1], head_position[2] + 7.0]
    head = {"center": face_center, "extent": [13.0, 13.0, 19.0]}
    if kind == "hair" and not hair_bounds:
        raise ValueError("Complete hairstyle framing requires actual populated HairPart bounds")
    pose = garment_framing(([head] + hair_bounds) if kind == "hair" else [head], width, height, fov=28.0, view=view)
    pose.update(focus_kind=kind, head_socket=head_position, head_proxy_extent_cm=head["extent"],
                framing_scope="complete populated hairstyle asset bounds plus head" if kind == "hair" else "front face/head closeup",
                presentation_status="prototype_unapproved_head_framing")
    return pose


def hair_asset_bounds(u, components):
    """Use actual asset reference bounds; attached component bounds inherit Body."""
    result = []
    for name, component in components.items():
        mesh = component.get_skeletal_mesh_asset()
        if not name.startswith("HairPart") or mesh is None:
            continue
        box = mesh.get_bounds()
        origin = [box.origin.x, box.origin.y, box.origin.z]
        extent = [box.box_extent.x, box.box_extent.y, box.box_extent.z]
        transform = component.get_world_transform()
        points = []
        for x in (-1, 1):
            for y in (-1, 1):
                for z in (-1, 1):
                    local = u.Vector(*[origin[k] + sign * extent[k] for k, sign in enumerate((x, y, z))])
                    p = u.MathLibrary.transform_location(transform, local)
                    points.append([p.x, p.y, p.z])
        low = [min(p[k] for p in points) for k in range(3)]
        high = [max(p[k] for p in points) for k in range(3)]
        result.append({"component": name, "mesh": mesh.get_path_name(),
                       "center": [(a + b) / 2 for a, b in zip(low, high)],
                       "extent": [(b - a) / 2 for a, b in zip(low, high)],
                       "method": "mesh reference bounds corners transformed by live component transform"})
    return result


def neutral_garment_material(u, components, unique):
    """Only owned reference clothes receive this opaque, plain gray material."""
    folder, name = (ROOT + "/Materials/M_HairReferenceClothes_" + unique).rsplit("/", 1)
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    color = u.MaterialEditingLibrary.create_material_expression(material, u.MaterialExpressionConstant3Vector)
    color.set_editor_property("constant", u.LinearColor(0.18, 0.18, 0.18, 1))
    u.MaterialEditingLibrary.connect_material_property(color, "", u.MaterialProperty.MP_BASE_COLOR)
    rough = u.MaterialEditingLibrary.create_material_expression(material, u.MaterialExpressionConstant)
    rough.set_editor_property("r", 0.9)
    u.MaterialEditingLibrary.connect_material_property(rough, "", u.MaterialProperty.MP_ROUGHNESS)
    u.MaterialEditingLibrary.recompile_material(material)
    u.EditorAssetLibrary.save_loaded_asset(material, False)
    changed = []
    for name, component in components.items():
        if name in ("UpperInner", "UpperOuter", "Bottom", "FullBody", "Footwear") or name.startswith("BundlePart"):
            if component.get_skeletal_mesh_asset() is not None:
                for index in range(component.get_num_materials()):
                    component.set_material(index, material)
                changed.append(name)
    return {"material": material.get_path_name(), "components": changed,
            "style": "opaque plain neutral gray, roughness 0.9; source materials unchanged"}


def neutral_environment(u, actors, center, unique):
    # Owned new material only; never modify a garment/source material.
    folder, name = (ROOT + "/Materials/M_Neutral_" + unique).rsplit("/", 1)
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    material.set_editor_property("shading_model", u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)
    expression = u.MaterialEditingLibrary.create_material_expression(material, u.MaterialExpressionConstant3Vector)
    expression.set_editor_property("constant", u.LinearColor(0.18, 0.18, 0.18, 1))
    u.MaterialEditingLibrary.connect_material_property(expression, "", u.MaterialProperty.MP_EMISSIVE_COLOR)
    u.MaterialEditingLibrary.recompile_material(material)
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError("Cannot save owned neutral background material")
    backdrop = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(*center), u.Rotator())
    backdrop.set_actor_label("DM_Reference_Backdrop")
    comp = backdrop.get_component_by_class(u.StaticMeshComponent)
    comp.set_static_mesh(u.load_asset("/Engine/BasicShapes/Sphere"))
    comp.set_material(0, material)
    comp.set_cast_shadow(False)
    backdrop.set_actor_scale3d(u.Vector(100, 100, 100))
    key = actors.spawn_actor_from_class(u.DirectionalLight, u.Vector(0, 0, 300), u.Rotator(pitch=-35, yaw=-145))
    key.get_component_by_class(u.DirectionalLightComponent).set_editor_property("intensity", 0.7)
    # Characters face +Y. Broad front/back fills keep both reference views readable.
    for sign in (1, -1):
        fill = actors.spawn_actor_from_class(u.RectLight, u.Vector(center[0], center[1] + sign * 250, center[2] + 40),
                                             u.Rotator(pitch=-9, yaw=-90 if sign == 1 else 90))
        fill.get_component_by_class(u.RectLightComponent).set_editor_properties(
            {"intensity": 20.0, "source_width": 240.0, "source_height": 240.0})
    volume = actors.spawn_actor_from_class(u.PostProcessVolume, u.Vector(), u.Rotator())
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    settings.set_editor_properties({"override_auto_exposure_method": True, "auto_exposure_method": u.AutoExposureMethod.AEM_MANUAL,
        "override_auto_exposure_apply_physical_camera_exposure": True, "auto_exposure_apply_physical_camera_exposure": False,
        "override_auto_exposure_bias": True, "auto_exposure_bias": -1.0})
    volume.set_editor_property("settings", settings)
    return {"background": "owned unlit 18-percent gray sphere", "key_intensity": 0.7, "fill_intensity": 20.0, "fill_views": ["front", "back"],
            "manual_exposure_bias": -1.0, "status": "prototype_lighting_unapproved"}


def prepare(u, run, job):
    ensure_not_rendering(u)
    if not re.fullmatch(r"ref_[A-Za-z0-9_]{1,80}", job["job_id"]) or job.get("frames") != 1 or job.get("fps") != 30:
        raise ValueError("Reference prototype requires safe ref_* ID and one 30fps frame")
    main = module("ue_dataset_render_v11")
    source, prepared, prepared_pin, pins = source_job(u, run, job, main)
    signature = hashlib.sha256(json.dumps({"version": VERSION, "main_policy": main.presentation_policy(), "job": job, "source_prepared": prepared_pin, "source_files": pins}, sort_keys=True).encode()).hexdigest()
    path = run / "jobs" / job["job_id"] / "prepared.json"
    if path.exists():
        previous = read(path)
        if previous.get("signature") == signature and all(u.EditorAssetLibrary.does_asset_exist(previous["job"][k]) for k in ("map", "sequence")):
            return dict(previous, reused=True)
    # Loaded material assets can acquire editor-only upgrade dirtiness. Keep them
    # untouched; only an unrelated unsaved map would be lost when changing worlds.
    dirty = [p for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
             if not p.get_path_name().startswith((main.ASSETS+'/',ROOT+'/'))]
    if dirty:
        raise RuntimeError("Resolve unsaved packages before switching to a reference stage: " + str([p.get_path_name() for p in dirty]))
    started = time.monotonic()
    unique = uuid.uuid4().hex[:10]
    destination = ROOT + "/Maps/L_" + job["job_id"] + "_" + unique
    sequence_path = ROOT + "/Sequences/LS_" + job["job_id"] + "_" + unique
    owned_package(destination)
    if u.EditorAssetLibrary.does_asset_exist(destination):
        raise ValueError("Refusing to overwrite reference assets")
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    details = {}
    if job["reference_kind"] == "scene":
        if (job["width"], job["height"]) != (source["width"], source["height"]):
            raise ValueError("Scene reference dimensions must equal its source main video")
        sequence = u.load_asset(prepared["job"]["sequence"])
        pose = first_camera(u, sequence, prepared["camera_first_frame"])
        world = copy_main_map(u, prepared["job"]["map"], destination)
        removed = remove_main_subjects(u)
        cameras = [a for a in actors.get_all_level_actors() if a.get_actor_label() == "DM_Dataset_Camera"]
        if len(cameras) != 1 or not isinstance(cameras[0], u.CameraActor):
            raise ValueError("Source main camera was not preserved by the owned map copy")
        camera = cameras[0]
        details = {"camera_binding": "actual saved source sequence frame-zero transform/FOV keys",
                   "removed_main_subjects_and_followers": removed, "target_character_present": False,
                   "shadow_policy": "destroy character and attached lash actors before a new MRQ world/warmup; no hidden shadow caster remains",
                   "source_environment": "inherited source main owned map; dynamic environment equality still requires inspection"}
    elif job["reference_kind"] == "garment":
        if (job["width"], job["height"]) != (1024, 1024):
            raise ValueError("Canonical garment prototype is one 1024-square PNG")
        garment = garment_target(source, job["asset_id"])
        u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
        if not levels.new_level(destination):
            raise RuntimeError("Cannot create empty owned reference stage")
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        if world.get_path_name().split(".")[0] != destination:
            raise RuntimeError("New neutral stage is not the owned world")
        mesh_rows, bounds = [], []
        for index, mesh_path in enumerate(garment["mesh_paths"]):
            mesh = u.load_asset(mesh_path)
            if not isinstance(mesh, u.SkeletalMesh):
                raise ValueError("Garment target is not a skeletal mesh: " + mesh_path)
            actor = actors.spawn_actor_from_class(u.SkeletalMeshActor, u.Vector(), u.Rotator())
            actor.set_actor_label("DM_Reference_Garment_" + str(index))
            component = actor.get_editor_property("skeletal_mesh_component")
            component.set_skeletal_mesh_asset(mesh)
            component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            component.set_simulate_physics(False)
            component.override_animation_data(None, False, False, 0.0, 1.0)
            center, extent = actor.get_actor_bounds(False)
            bounds.append({"center": [center.x, center.y, center.z], "extent": [extent.x, extent.y, extent.z]})
            mesh_rows.append({"actor": actor.get_path_name(), "mesh": mesh_path})
        view = job.get("view", "front")
        pose = garment_framing(bounds, job["width"], job["height"], view=view)
        environment = neutral_environment(u, actors, pose["bounds_center"], unique)
        camera = actors.spawn_actor_from_class(u.CameraActor, u.Vector(), u.Rotator())
        camera.set_actor_label("DM_Reference_Camera")
        actual = [c.get_skeletal_mesh_asset().get_path_name() for a in actors.get_all_level_actors()
                  for c in a.get_components_by_class(u.SkeletalMeshComponent) if c.get_skeletal_mesh_asset()]
        if sorted(actual) != sorted(garment["mesh_paths"]):
            raise ValueError("Garment-only stage contains a mesh outside the one selected item")
        details = {"asset": garment, "mesh_actors": mesh_rows, "all_item_meshes_loaded": True,
                   "body_actor_spawned": False, "identity_hair_lashes_spawned": False,
                   "pose": "unanimated imported skeletal reference pose; no body actor or full actor crop",
                   "view": view, "environment": environment, "all_stage_skeletal_meshes": actual,
                   "presentation_status": "prototype_unapproved_reference_pose_framing_lighting"}
    elif job["reference_kind"] in ("identity", "hair"):
        if (job["width"], job["height"]) != (1024, 1024):
            raise ValueError("Identity/hair prototypes require one 1024-square PNG per view")
        if job.get("target_identity", source["state"]["identity"]) != source["state"]["identity"]:
            raise ValueError("Prototype identity must be the prepared source node identity")
        if job.get("hair_id", source["state"]["hair"]) != source["state"]["hair"]:
            raise ValueError("Prototype hairstyle must be the prepared source node hairstyle")
        view = job.get("view", "front")
        if view not in ("front", "back") or (job["reference_kind"] == "identity" and view != "front"):
            raise ValueError("Identity supports front; hair supports front/back")
        import pair_scene_review_20261019_v1 as pair
        current = pair.worker(u)
        main.release_bindings(u,current)
        u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
        if not levels.new_level(destination):
            raise RuntimeError("Cannot create empty owned identity/hair stage")
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        if world.get_path_name().split(".")[0] != destination:
            raise RuntimeError("Identity/hair stage is not the owned world")
        actor = main.spawn_slot_actor(u, source["state"]["sex"])
        actor.set_actor_label("DM_SiteReview_Reference_Character")
        actor.set_actor_location(u.Vector(), False, False)
        # Keep native CC neutral front +Y. Both view directions use this frame.
        actor.set_actor_rotation(u.Rotator(pitch=0, yaw=0, roll=0), False)
        selected = main.selection(source, current)
        if job["reference_kind"] == "hair":
            selected["hair_color"] = "black"
        applied = main.apply_appearance(u, current, actor, selected, 0.0, None,
            body_action_id=source["state"]["action"])
        lashes = main.persistent_lashes(u, current, actor)
        persistent_materials = main.module('dataset_persistent_materials_v1').freeze_actor(u, actor, main.ASSETS+'/Materials/PersistentV1')
        components = current["assembly"].fixed.actor_components(actor)
        neutral_clothes = neutral_garment_material(u, components, unique) if job.get("neutral_garment_color") else None
        removed_garments = []
        if job.get("garments_present") is False:
            for name, component in components.items():
                if name in ("UpperInner", "UpperOuter", "Bottom", "FullBody", "Footwear") or name.startswith("BundlePart"):
                    mesh = component.get_skeletal_mesh_asset()
                    if mesh is not None:
                        removed_garments.append({"component": name, "mesh": mesh.get_path_name()})
                    component.set_skeletal_mesh_asset(None)
                    component.set_visibility(False, False)
        body = components["Body"]
        head = body.get_socket_location("head")
        bounds = hair_asset_bounds(u, components)
        actual_hair = {r["mesh"] for r in bounds}
        expected_hair = {r["path"] for r in source["appearance"]["hair"]["fit"]["meshes"]}
        if actual_hair != expected_hair:
            raise ValueError("Reference carrier hair meshes differ from the source node")
        pose = head_framing([head.x, head.y, head.z], bounds, job["reference_kind"], view, job["width"], job["height"])
        environment = neutral_environment(u, actors, pose["bounds_center"], unique)
        camera = actors.spawn_actor_from_class(u.CameraActor, u.Vector(), u.Rotator())
        camera.set_actor_label("DM_Reference_Camera")
        details = {"target_identity": source["state"]["identity"], "hair_id": source["state"]["hair"],
                   "view": view, "hair_color": selected["hair_color"], "face_id": selected["face_id"],
                   "carrier": "formal source 38-slot actor with current 40-person revision and permanent lash followers",
                   "template_map": None, "slot_blueprint": actor.get_class().get_path_name(), "actor": actor.get_path_name(),
                   "formal_assembly_readback": applied, "persistent_lashes": lashes, "persistent_materials": persistent_materials,
                   "pose": "imported reference body pose; approved native smile frozen at facial clip time zero",
                   "body_animation": None, "body_time_seconds": 0.0,
                   "actor_rotation_pitch_yaw_roll": [0.0, 0.0, 0.0], "neutral_front_axis": "+Y",
                   "hair_bounds": bounds, "hair_asset_meshes_match_source": True,
                   "garments_present": job.get("garments_present", True), "removed_garments": removed_garments,
                   "neutral_clothes": neutral_clothes,
                   "environment": environment, "presentation_status": "prototype_unapproved_head_framing_lighting",
                   "reference_manifest_binding": "not published; source main node lineage only"}
    else:
        raise ValueError("Only scene, garment, identity and hair prototypes are implemented")
    apply_camera(u, camera, pose, job["width"], job["height"])
    sequence = static_sequence(u, camera, pose, sequence_path)
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not u.EditorLoadingAndSavingUtils.save_map(world, destination):
        raise RuntimeError("Cannot save owned reference map")
    for pin in pins:
        if digest(pin["path"]) != pin["sha256"]:
            raise RuntimeError("Source main package changed during reference preparation")
    result = {"success": True, "schema": "dataset_reference_pilot_prepared_v11_v1", "signature": signature,
              "reference_job_sha256": hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest(),
              "job_id": job["job_id"], "reference_kind": job["reference_kind"],
              "job": {"shot_id": job["job_id"], "map": object_path(destination), "sequence": sequence.get_path_name()},
              "source_job_id": source["job_id"], "source_prepared": prepared_pin, "source_pins": pins,
              "source_packages_unchanged": True, "camera": pose, "details": details,
              "width": job["width"], "height": job["height"], "frames": 1, "fps": 30,
              "preparation_seconds": time.monotonic() - started, "visual_acceptance": "pending",
              "reference_manifest_publication": False, "presentation_status": "prototype_not_frozen"}
    write(path, result)
    return result


def renderer(u, run, job=None, pool_mb=10240):
    value = module("ue_dataset_render_v11").renderer(u, run, job, pool_mb)
    value.LIVE_ATTRIBUTE = LIVE
    value.ASSET_ROOT = ROOT
    return value


def dispatch(request):
    import unreal as u
    run = Path(request["run_root"]).resolve()
    if request["action"] == "status":
        return renderer(u, run).status(u)
    jobs_path = Path(request.get("jobs_path", run / "reference_pilot_jobs.json"))
    if not jobs_path.is_absolute():
        jobs_path = run / jobs_path
    job = next(x for x in read(jobs_path)["jobs"] if x["job_id"] == request["job_id"])
    if request["action"] == "prepare":
        return prepare(u, run, job)
    if request["action"] == "render":
        prepared = read(run / "jobs" / job["job_id"] / "prepared.json")
        if prepared["reference_job_sha256"] != hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest():
            raise ValueError("Reference job changed; prepare again")
        if digest(prepared["source_prepared"]["path"]) != prepared["source_prepared"]["sha256"]:
            raise ValueError("Source main preparation changed; prepare reference again")
        for pin in prepared["source_pins"]:
            if digest(pin["path"]) != pin["sha256"]:
                raise ValueError("Source main package changed; prepare reference again")
        return renderer(u, run, job, request.get("pool_mb", 10240)).start_render(
            u, [prepared["job"]], job["job_id"] + "_" + uuid.uuid4().hex[:8], width=job["width"], height=job["height"])
    raise ValueError("Unknown reference prototype action")
