"""Import and validate one body motion per modular-outfit pilot bodyfit.

Run through ``ue_remote_exec.py`` with ``DM_MODULAR_MOTION_MODE`` set to
``import_motion``, ``validate_motion``, or ``stage_motion`` and with
``DM_MODULAR_BODYFIT_ID`` set to ``M02_Average`` or ``F02_Average``.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

import unreal


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
RUNTIME_WORKER = SCRIPT_ROOT / "ue_build_modular_outfit_runtime_v1.py"
PLAN_PATH = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "modular_outfit_pilot_20260829_v1"
    / "runtime_plan_v1.json"
)
REPORT_ROOT = PLAN_PATH.parent / "runtime" / "motion"
REQUIRED_EXPORTS = (
    LANCE_ROOT
    / "00_engine"
    / "scripts"
    / "dataset"
    / "first_batch_required_exports_20260820_v1.json"
)
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
VALID_MODES = {"import_motion", "validate_motion", "stage_motion"}
ACTION_BY_SEX = {
    "female": "ACT_F03_AUDIENCE_01",
    "male": "ACT_M02_AUDIENCE_01",
}
ASSET_NAME_BY_SEX = {
    "female": "A_DM_F03_AUDIENCE_01_ModularPilot_v001",
    "male": "A_DM_M02_AUDIENCE_01_ModularPilot_v001",
}
POSE_BONES = ("head", "hand_l", "hand_r", "foot_l", "foot_r")
MIN_CORE_BONE_TRACKS = 70
SAMPLE_DELTA_SECONDS = 0.75
MIN_BODY_POSE_ROTATION_DELTA_DEGREES = 1.0


def load_runtime_module():
    spec = importlib.util.spec_from_file_location(
        "dm_modular_outfit_runtime_helpers_v1", RUNTIME_WORKER
    )
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Unable to load runtime worker: {RUNTIME_WORKER}")
    spec.loader.exec_module(module)
    return module


RUNTIME = load_runtime_module()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return value


def write_report(name: str, value: dict) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / name
    value["report_path"] = str(path)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_motion_spec(required_exports: dict, sex: str) -> dict:
    action_id = ACTION_BY_SEX.get(sex)
    if action_id is None:
        raise RuntimeError(f"Unsupported modular motion sex: {sex}")
    matches = [
        row for row in required_exports.get("actions") or []
        if row.get("action_id") == action_id and row.get("sex") == sex
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one frozen source motion {action_id}/{sex}, found {len(matches)}"
        )
    expected = matches[0].get("expected_export")
    if not isinstance(expected, dict):
        raise RuntimeError(f"Frozen source motion has no export contract: {action_id}")
    return {
        "action_id": action_id,
        "sex": sex,
        "path": expected.get("local_path"),
        "size_bytes": expected.get("bytes"),
        "sha256": expected.get("sha256"),
    }


def validate_source_motion(spec: dict) -> Path:
    path = Path(spec.get("path") or "").resolve()
    if not path.is_file():
        raise RuntimeError(f"Frozen motion FBX is missing: {path}")
    if path.stat().st_size != spec.get("size_bytes"):
        raise RuntimeError(f"Frozen motion size changed: {path}")
    if sha256_file(path) != spec.get("sha256"):
        raise RuntimeError(f"Frozen motion hash changed: {path}")
    return path


def motion_destination(bodyfit: dict) -> dict:
    root = (
        "/Game/DataMake/Animations/CC5/ModularOutfitPilot/"
        + bodyfit["bodyfit_id"]
    )
    name = ASSET_NAME_BY_SEX[bodyfit["sex"]]
    return {
        "root": root,
        "name": name,
        "asset": f"{root}/{name}",
        "pipeline": (
            "/Game/DataMake/Config/Import/ModularOutfitPilot/"
            f"DM_{bodyfit['bodyfit_id']}_MotionPipeline_v001"
        ),
    }


def configure_animation_pipeline(pipeline, skeleton) -> None:
    mesh = pipeline.get_editor_property("mesh_pipeline")
    common = pipeline.get_editor_property(
        "common_skeletal_meshes_and_animations_properties"
    )
    animation = pipeline.get_editor_property("animation_pipeline")
    material = pipeline.get_editor_property("material_pipeline")
    texture = material.get_editor_property("texture_pipeline")
    mesh.set_editor_property("import_skeletal_meshes", False)
    mesh.set_editor_property("import_static_meshes", False)
    mesh.set_editor_property("create_physics_asset", False)
    mesh.set_editor_property("physics_asset", None)
    common.set_editor_property("skeleton", skeleton)
    common.set_editor_property("try_auto_select_skeleton", False)
    common.set_editor_property("import_only_animations", True)
    animation.set_editor_property("import_animations", True)
    material.set_editor_property("import_materials", False)
    texture.set_editor_property("import_textures", False)


def run_import_motion(bodyfit: dict) -> dict:
    required_exports = read_json(REQUIRED_EXPORTS)
    source_spec = source_motion_spec(required_exports, bodyfit["sex"])
    source = validate_source_motion(source_spec)
    destination = motion_destination(bodyfit)
    if unreal.EditorAssetLibrary.does_asset_exist(destination["asset"]):
        raise RuntimeError(
            f"Refusing to overwrite modular validation motion: {destination['asset']}"
        )
    skeleton = unreal.load_asset(bodyfit["skeleton_path"])
    if not isinstance(skeleton, unreal.Skeleton):
        raise RuntimeError(f"Runtime Skeleton is unavailable: {bodyfit['skeleton_path']}")

    pipeline = unreal.load_asset(destination["pipeline"])
    if pipeline is None:
        pipeline = unreal.EditorAssetLibrary.duplicate_asset(
            DEFAULT_PIPELINE, destination["pipeline"]
        )
    if pipeline is None:
        raise RuntimeError(f"Unable to create motion pipeline: {destination['pipeline']}")
    configure_animation_pipeline(pipeline, skeleton)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        pipeline, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save motion pipeline: {destination['pipeline']}")

    unreal.EditorAssetLibrary.make_directory(destination["root"])
    before = set(
        unreal.EditorAssetLibrary.list_assets(
            destination["root"], recursive=False, include_folder=False
        )
    )
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    source_data = manager.create_source_data(str(source))
    if source_data is None:
        raise RuntimeError(f"Unable to create motion source data: {source}")
    parameters = unreal.ImportAssetParameters()
    parameters.set_editor_property("is_automated", True)
    parameters.set_editor_property("force_show_dialog", False)
    parameters.set_editor_property("replace_existing", False)
    parameters.set_editor_property("destination_name", destination["name"])
    parameters.set_editor_property(
        "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
    )
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
    previous = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
    if previous != 1:
        unreal.SystemLibrary.execute_console_command(world, f"{fbx_cvar} 1")
    interchange_diagnostic = None
    try:
        manager.import_asset(destination["root"], source_data, parameters)
    except RuntimeError as exc:
        # Interchange reports CC auxiliary twist/share tracks that are absent from
        # the selected base Skeleton as an exception even when it materializes a
        # valid core-body AnimSequence. The asset is accepted only after the
        # strict Skeleton and core-track checks below pass.
        interchange_diagnostic = str(exc)
    finally:
        if previous != 1:
            unreal.SystemLibrary.execute_console_command(world, f"{fbx_cvar} {previous}")

    after = set(
        unreal.EditorAssetLibrary.list_assets(
            destination["root"], recursive=False, include_folder=False
        )
    )
    new_paths = sorted(after - before)
    animations = [
        asset
        for path in new_paths
        for asset in [unreal.load_asset(path)]
        if isinstance(asset, unreal.AnimSequence)
    ]
    if len(animations) != 1:
        raise RuntimeError(
            f"Expected one modular AnimSequence, found {len(animations)}: {new_paths}"
        )
    animation = animations[0]
    if animation.get_path_name().split(".", 1)[0] != destination["asset"]:
        source_asset_path = animation.get_path_name().split(".", 1)[0]
        if not unreal.EditorAssetLibrary.rename_asset(
            source_asset_path, destination["asset"]
        ):
            raise RuntimeError(
                f"Unable to rename modular motion: {source_asset_path}"
            )
        animation = unreal.load_asset(destination["asset"])
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(f"Modular validation motion is unavailable: {destination['asset']}")
    tracks = [
        str(name) for name in animation.data_model_interface.get_bone_track_names()
    ]
    missing_pose_bones = [bone for bone in POSE_BONES if bone not in tracks]
    checks = {
        "skeleton_matches": animation.get_editor_property("skeleton") == skeleton,
        "track_count_supported": len(tracks) >= MIN_CORE_BONE_TRACKS,
        "pose_bone_tracks_present": not missing_pose_bones,
    }
    success = all(checks.values())
    if not success:
        raise RuntimeError(
            f"Modular validation motion failed its contract: {checks}"
        )
    unreal.EditorAssetLibrary.save_loaded_asset(animation, only_if_is_dirty=False)
    return {
        "schema_version": 1,
        "mode": "import_motion",
        "created_at_utc": utc_now(),
        "bodyfit_id": bodyfit["bodyfit_id"],
        "sex": bodyfit["sex"],
        "source": source_spec,
        "animation": animation.get_path_name(),
        "skeleton": skeleton.get_path_name(),
        "bone_track_count": len(tracks),
        "minimum_core_bone_tracks": MIN_CORE_BONE_TRACKS,
        "missing_pose_bones": missing_pose_bones,
        "interchange_diagnostic": interchange_diagnostic,
        "pipeline": pipeline.get_path_name(),
        "checks": checks,
        "success": success,
    }


def vector_record(value) -> dict:
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def vector_distance(left: dict, right: dict) -> float:
    return math.sqrt(
        (left["x"] - right["x"]) ** 2
        + (left["y"] - right["y"]) ** 2
        + (left["z"] - right["z"]) ** 2
    )


def quaternion_record(value) -> dict:
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
        "w": float(value.w),
    }


def quaternion_angular_distance_degrees(left: dict, right: dict) -> float:
    dot = abs(
        left["x"] * right["x"]
        + left["y"] * right["y"]
        + left["z"] * right["z"]
        + left["w"] * right["w"]
    )
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def sample_animation_pose(animation, time_seconds: float) -> dict[str, dict]:
    poses = unreal.AnimationLibrary.get_bone_poses_for_time(
        animation,
        list(POSE_BONES),
        float(time_seconds),
        False,
    )
    if len(poses) != len(POSE_BONES):
        raise RuntimeError(
            f"Expected {len(POSE_BONES)} sampled poses, found {len(poses)}"
        )
    return {
        bone: {
            "translation": vector_record(pose.translation),
            "rotation": quaternion_record(pose.rotation),
        }
        for bone, pose in zip(POSE_BONES, poses)
    }


def refresh_component(component) -> None:
    if hasattr(component, "refresh_bone_transforms"):
        component.refresh_bone_transforms()
    if hasattr(component, "mark_render_dynamic_data_dirty"):
        component.mark_render_dynamic_data_dirty()


def configure_body_animation(body, animation) -> None:
    body.set_update_animation_in_editor(True)
    body.set_component_tick_enabled(True)
    body.set_enable_animation(True)
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    body.override_animation_data(animation, True, True, 0.0, 1.0)
    if hasattr(body, "tick_animation"):
        body.tick_animation(0.0, False)
    refresh_component(body)


def run_validate_motion(bodyfit: dict) -> dict:
    destination = motion_destination(bodyfit)
    animation = unreal.load_asset(destination["asset"])
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(
            f"Import modular validation motion first: {destination['asset']}"
        )
    blueprint = RUNTIME.load_blueprint(bodyfit)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_subsystem.spawn_actor_from_class(
        blueprint.generated_class(), unreal.Vector(), unreal.Rotator(), transient=True
    )
    if actor is None:
        raise RuntimeError("Unable to spawn modular motion validation actor")
    sample_end_seconds = min(SAMPLE_DELTA_SECONDS, float(animation.sequence_length))
    pose_start = sample_animation_pose(animation, 0.0)
    pose_end = sample_animation_pose(animation, sample_end_seconds)
    body_rotation_deltas = {
        bone: quaternion_angular_distance_degrees(
            pose_start[bone]["rotation"], pose_end[bone]["rotation"]
        )
        for bone in POSE_BONES
    }
    max_body_rotation_delta = max(body_rotation_deltas.values(), default=0.0)
    records = []
    errors = []
    try:
        for variant in RUNTIME.all_variants(bodyfit):
            application = RUNTIME.apply_variant(actor, bodyfit, variant)
            application_errors = RUNTIME.validate_variant_application(application)
            body, followers = RUNTIME.actor_components(actor, bodyfit)
            configure_body_animation(body, animation)
            variant_errors = list(application_errors)
            if max_body_rotation_delta < MIN_BODY_POSE_ROTATION_DELTA_DEGREES:
                variant_errors.append(
                    "body motion was not observed in animation data; "
                    f"max rotation delta={max_body_rotation_delta:.3f} degrees"
                )
            visible_followers = [
                follower
                for follower in followers
                if follower.get_name() in set(variant["enabled_component_names"])
            ]
            follower_records = []
            for follower in visible_followers:
                leader_is_body = (
                    follower.get_editor_property("leader_pose_component") == body
                )
                skeleton_matches = (
                    follower.get_skeletal_mesh_asset().get_editor_property("skeleton")
                    == body.get_skeletal_mesh_asset().get_editor_property("skeleton")
                )
                uses_leader_bounds = bool(
                    follower.get_editor_property(
                        "use_bounds_from_leader_pose_component"
                    )
                )
                if not leader_is_body:
                    variant_errors.append(
                        f"{follower.get_name()} has no Body leader during motion setup"
                    )
                if not skeleton_matches:
                    variant_errors.append(
                        f"{follower.get_name()} Skeleton differs from Body"
                    )
                if not uses_leader_bounds:
                    variant_errors.append(
                        f"{follower.get_name()} does not inherit Leader Pose bounds"
                    )
                follower_records.append(
                    {
                        "component_name": follower.get_name(),
                        "leader_is_body": leader_is_body,
                        "skeleton_matches_body": skeleton_matches,
                        "uses_leader_pose_bounds": uses_leader_bounds,
                        "pose_sync_contract_passed": (
                            leader_is_body and skeleton_matches and uses_leader_bounds
                        ),
                    }
                )
            record = {
                "qualified_variant_id": variant["qualified_variant_id"],
                "body_pose_rotation_delta_degrees": body_rotation_deltas,
                "max_body_pose_rotation_delta_degrees": max_body_rotation_delta,
                "body_motion_observed": (
                    max_body_rotation_delta
                    >= MIN_BODY_POSE_ROTATION_DELTA_DEGREES
                ),
                "visible_follower_count": len(visible_followers),
                "followers": follower_records,
                "errors": variant_errors,
                "success": not variant_errors,
            }
            records.append(record)
            errors.extend(
                f"{variant['qualified_variant_id']}: {error}"
                for error in variant_errors
            )
    finally:
        actor_subsystem.destroy_actor(actor)
    return {
        "schema_version": 1,
        "mode": "validate_motion",
        "created_at_utc": utc_now(),
        "bodyfit_id": bodyfit["bodyfit_id"],
        "sex": bodyfit["sex"],
        "blueprint": bodyfit["blueprint_path"],
        "animation": animation.get_path_name(),
        "sample_delta_seconds": SAMPLE_DELTA_SECONDS,
        "sample_end_seconds": sample_end_seconds,
        "variant_count": len(records),
        "records": records,
        "errors": errors,
        "validation_scope": [
            "animation_data_pose_rotation_changes",
            "registered_variant_application",
            "visible_follower_leader_pose_contract",
        ],
        "not_evaluated": [
            "editor_component_pose_after_forced_python_tick",
            "visual_clipping",
            "body_surface_hiding",
            "cloth_physics",
            "lod_sync",
            "hair_outfit_compatibility",
        ],
        "success": bool(records) and not errors,
    }


def run_stage_motion(bodyfit: dict, qualified_variant_id: str) -> dict:
    variant = RUNTIME.variant_for_id(bodyfit, qualified_variant_id)
    stage = RUNTIME.run_stage_variant(bodyfit, variant)
    actors = RUNTIME.staged_actors(bodyfit["bodyfit_id"])
    if len(actors) != 1:
        raise RuntimeError("Expected one staged modular actor after variant application")
    actor = actors[0]
    body, _followers = RUNTIME.actor_components(actor, bodyfit)
    destination = motion_destination(bodyfit)
    animation = unreal.load_asset(destination["asset"])
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(f"Modular validation motion is unavailable: {destination['asset']}")
    configure_body_animation(body, animation)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_viewport_realtime(
        True
    )
    return {
        "schema_version": 1,
        "mode": "stage_motion",
        "created_at_utc": utc_now(),
        "bodyfit_id": bodyfit["bodyfit_id"],
        "variant_id": qualified_variant_id,
        "stage": stage,
        "actor": actor.get_path_name(),
        "animation": animation.get_path_name(),
        "level_saved": False,
        "success": True,
    }


def required_global(name: str) -> str:
    value = globals().get(name)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{name} is required")
    return value


def main() -> dict:
    mode = globals().get("DM_MODULAR_MOTION_MODE", "validate_motion")
    bodyfit_id = globals().get("DM_MODULAR_BODYFIT_ID")
    variant_id = globals().get("DM_MODULAR_VARIANT_ID")
    try:
        if mode not in VALID_MODES:
            raise RuntimeError(f"Unsupported modular motion mode: {mode}")
        plan = read_json(PLAN_PATH)
        RUNTIME.validate_runtime_plan(plan)
        bodyfit_id = required_global("DM_MODULAR_BODYFIT_ID")
        bodyfit = RUNTIME.bodyfit_for_id(plan, bodyfit_id)
        if mode == "import_motion":
            result = run_import_motion(bodyfit)
        elif mode == "validate_motion":
            result = run_validate_motion(bodyfit)
        else:
            variant_id = required_global("DM_MODULAR_VARIANT_ID")
            result = run_stage_motion(bodyfit, variant_id)
        suffix = f"_{str(variant_id).replace('::', '__')}" if variant_id else ""
        path = write_report(f"{bodyfit_id}_{mode}{suffix}.json", result)
        if result.get("success") is not True:
            raise RuntimeError(f"Modular motion operation failed; see {path}")
    except Exception as exc:
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", str(bodyfit_id or "global"))
        failure = {
            "schema_version": 1,
            "mode": mode,
            "bodyfit_id": bodyfit_id,
            "variant_id": variant_id,
            "created_at_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "success": False,
        }
        path = write_report(f"{safe}_{mode}_error.json", failure)
        unreal.log_error(f"DataMake modular motion failed; see {path}: {exc}")
        print("DM_MODULAR_MOTION_RESULT=" + json.dumps(failure, ensure_ascii=False))
        raise
    summary = {
        "mode": mode,
        "bodyfit_id": bodyfit_id,
        "variant_id": variant_id,
        "report_path": str(path),
        "success": result["success"],
    }
    print("DM_MODULAR_MOTION_RESULT=" + json.dumps(summary, ensure_ascii=False))
    return result


if globals().get("__name__") == "__main__" or "DM_MODULAR_MOTION_MODE" in globals():
    main()
