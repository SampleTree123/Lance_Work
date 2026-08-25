"""Import and validate the frozen first-batch Motion FBXs in Unreal Engine."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import unreal


REQUIRED_EXPORTS_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\dataset"
    r"\first_batch_required_exports_20260824_v3.json"
)
NORMALIZED_MANIFEST_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\first_batch_motions_20260822_v1\normalized_motion_manifest.json"
)
REPORT_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\first_batch_motions_20260822_v1"
)
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
CONFIG_ROOT = "/Game/DataMake/Config/Import/FirstDataBatch"
RAW_ROOT = "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Motions"
BODY_ROOT = "/Game/DataMake/Animations/CC5/FirstDataBatch"

SEX_CONFIG = {
    "female": {
        "skeleton": (
            "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/F_ID01_O01/"
            "CC_FB_F_ID01_O01_Skeleton.CC_FB_F_ID01_O01_Skeleton"
        ),
        "raw_destination": f"{RAW_ROOT}/Female/Raw",
        "body_destination": f"{BODY_ROOT}/Female/BodyOnly",
        "pipeline": f"{CONFIG_ROOT}/DM_CC5_FirstBatch_Female_Animation_Pipeline_v001",
    },
    "male": {
        "skeleton": (
            "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/M_ID01_O01/"
            "CC_FB_M_ID01_O01_Skeleton.CC_FB_M_ID01_O01_Skeleton"
        ),
        "raw_destination": f"{RAW_ROOT}/Male/Raw",
        "body_destination": f"{BODY_ROOT}/Male/BodyOnly",
        "pipeline": f"{CONFIG_ROOT}/DM_CC5_FirstBatch_Male_Animation_Pipeline_v001",
    },
}

REQUIRED_RAW_TRACKS = {
    "root",
    "pelvis",
    "pelvis_0",
    "facialbone",
    "l_forearmtwist01",
    "r_forearmtwist01",
    "l_thightwist01",
    "r_thightwist01",
    "ik_foot_root",
    "ik_hand_root",
}
REQUIRED_BODY_TRACKS = REQUIRED_RAW_TRACKS - {"facialbone"}
FACE_SUPPORT_TRACKS = {
    "facialbone",
    "jawroot",
    "tongue01",
    "tongue02",
    "tongue03",
    "teeth02",
    "r_eye",
    "l_eye",
    "upperjaw",
    "teeth01",
    "cc_base_facialbone",
    "cc_base_jawroot",
    "cc_base_tongue01",
    "cc_base_tongue02",
    "cc_base_tongue03",
    "cc_base_teeth02",
    "cc_base_r_eye",
    "cc_base_l_eye",
    "cc_base_upperjaw",
    "cc_base_teeth01",
}
MIN_RAW_TRACKS = 100
MIN_BODY_TRACKS = 90
SUPPORTED_SOURCE_FRAME_RATES = {(30, 1), (60, 1)}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source(action: dict) -> dict:
    expected = action["expected_export"]
    path = Path(expected["local_path"])
    exists = path.is_file()
    actual_bytes = path.stat().st_size if exists else None
    actual_sha256 = sha256(path) if exists else None
    return {
        "path": str(path),
        "exists": exists,
        "expected_bytes": expected["bytes"],
        "actual_bytes": actual_bytes,
        "expected_sha256": expected["sha256"],
        "actual_sha256": actual_sha256,
        "passed": (
            exists
            and actual_bytes == expected["bytes"]
            and actual_sha256 == expected["sha256"]
        ),
    }


def verify_normalized(action: dict, normalized_records: dict[str, dict]) -> dict:
    action_id = action["action_id"]
    record = normalized_records.get(action_id)
    if not isinstance(record, dict):
        return {
            "action_id": action_id,
            "path": None,
            "exists": False,
            "passed": False,
            "reason": "missing_normalized_record",
        }
    path = Path(record.get("normalized_path") or "")
    exists = path.is_file()
    actual_bytes = path.stat().st_size if exists else None
    actual_sha256 = sha256(path) if exists else None
    expected_source = action["expected_export"]
    tool_record = record.get("tool_record") or {}
    passed = (
        record.get("success") is True
        and record.get("source_path") == expected_source["local_path"]
        and record.get("source_bytes") == expected_source["bytes"]
        and record.get("source_sha256") == expected_source["sha256"]
        and exists
        and actual_bytes == record.get("normalized_bytes")
        and actual_sha256 == record.get("normalized_sha256")
        and int(tool_record.get("renamed_count", 0)) >= 40
        and int(tool_record.get("remaining_prefixed", -1)) == 0
    )
    return {
        "action_id": action_id,
        "path": str(path),
        "exists": exists,
        "expected_bytes": record.get("normalized_bytes"),
        "actual_bytes": actual_bytes,
        "expected_sha256": record.get("normalized_sha256"),
        "actual_sha256": actual_sha256,
        "renamed_count": tool_record.get("renamed_count"),
        "remaining_prefixed": tool_record.get("remaining_prefixed"),
        "passed": passed,
    }


def animation_curve_names(animation: unreal.AnimSequence) -> list[str]:
    return sorted(
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            animation, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    )


def animation_record(animation: unreal.AnimSequence) -> dict:
    skeleton = animation.get_editor_property("skeleton")
    model = animation.data_model_interface
    tracks = [str(name) for name in model.get_bone_track_names()]
    frame_rate = model.get_frame_rate()
    frame_count = int(model.get_number_of_frames())
    return {
        "asset": animation.get_path_name(),
        "skeleton": skeleton.get_path_name() if skeleton else None,
        "play_length_seconds": float(model.get_play_length()),
        "frame_count": frame_count,
        "frame_rate": {
            "numerator": int(frame_rate.numerator),
            "denominator": int(frame_rate.denominator),
        },
        "bone_track_count": len(tracks),
        "bone_tracks": tracks,
        "float_curve_count": len(animation_curve_names(animation)),
        "float_curves": animation_curve_names(animation),
    }


def prepare_pipeline(config: dict, skeleton: unreal.Skeleton):
    pipeline = unreal.load_asset(config["pipeline"])
    if pipeline is None:
        pipeline = unreal.EditorAssetLibrary.duplicate_asset(
            DEFAULT_PIPELINE, config["pipeline"]
        )
    if pipeline is None:
        raise RuntimeError(f"Unable to create pipeline: {config['pipeline']}")

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

    if not unreal.EditorAssetLibrary.save_loaded_asset(
        pipeline, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save pipeline: {config['pipeline']}")
    return pipeline


def raw_animation_is_reusable(
    animation: unreal.Object | None, skeleton: unreal.Skeleton
) -> bool:
    if not isinstance(animation, unreal.AnimSequence):
        return False
    if animation.get_editor_property("skeleton") != skeleton:
        return False
    record = animation_record(animation)
    tracks = set(record["bone_tracks"])
    return (
        record["bone_track_count"] >= MIN_RAW_TRACKS
        and not (REQUIRED_RAW_TRACKS - tracks)
    )


def import_raw_animation(
    manager,
    world,
    action: dict,
    config: dict,
    skeleton: unreal.Skeleton,
    pipeline,
    normalized_check: dict,
) -> tuple[unreal.AnimSequence, dict]:
    source = Path(normalized_check["path"])
    desired_name = action["expected_export"]["basename"]
    destination = config["raw_destination"]
    desired_path = f"{destination}/{desired_name}"
    existing = unreal.load_asset(desired_path)
    if raw_animation_is_reusable(existing, skeleton):
        return existing, {
            "reused_existing": True,
            "replaced_invalid_existing": False,
            "import_source": str(source),
            "new_asset_paths": [],
        }
    replaced_invalid = existing is not None
    if existing is not None and not unreal.EditorAssetLibrary.delete_asset(desired_path):
        raise RuntimeError(f"Unable to replace invalid animation: {desired_path}")

    before = set(
        unreal.EditorAssetLibrary.list_assets(
            destination, recursive=False, include_folder=False
        )
    )
    source_data = manager.create_source_data(str(source))
    if source_data is None:
        raise RuntimeError(f"Unable to create Interchange source data: {source}")
    parameters = unreal.ImportAssetParameters()
    parameters.set_editor_property("is_automated", True)
    parameters.set_editor_property("force_show_dialog", False)
    parameters.set_editor_property("replace_existing", False)
    parameters.set_editor_property("destination_name", desired_name)
    parameters.set_editor_property(
        "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
    )

    fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
    previous_value = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
    if previous_value != 1:
        unreal.SystemLibrary.execute_console_command(world, f"{fbx_cvar} 1")
    try:
        manager.import_asset(destination, source_data, parameters)
    finally:
        if previous_value != 1:
            unreal.SystemLibrary.execute_console_command(
                world, f"{fbx_cvar} {previous_value}"
            )

    after = set(
        unreal.EditorAssetLibrary.list_assets(
            destination, recursive=False, include_folder=False
        )
    )
    new_paths = sorted(after - before)
    animations = []
    for asset_path in new_paths:
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, unreal.AnimSequence):
            animations.append(asset)
    if len(animations) != 1:
        raise RuntimeError(
            f"Expected one AnimSequence from {source}; found {len(animations)}; "
            f"new assets={new_paths}"
        )
    imported = animations[0]
    if imported.get_name() != desired_name:
        imported_package = imported.get_path_name().split(".", 1)[0]
        if not unreal.EditorAssetLibrary.rename_asset(imported_package, desired_path):
            raise RuntimeError(
                f"Unable to rename {imported_package} to {desired_path}"
            )
        imported = unreal.load_asset(desired_path)
    if not isinstance(imported, unreal.AnimSequence):
        raise RuntimeError(f"Imported animation unavailable: {desired_path}")
    return imported, {
        "reused_existing": False,
        "replaced_invalid_existing": replaced_invalid,
        "import_source": str(source),
        "new_asset_paths": new_paths,
    }


def build_body_only(
    action: dict, raw: unreal.AnimSequence, config: dict
) -> tuple[unreal.AnimSequence, dict]:
    raw_name = action["expected_export"]["basename"]
    target_name = f"A_DM_{raw_name[2:]}_BodyOnly_v001"
    target_path = f"{config['body_destination']}/{target_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        if not unreal.EditorAssetLibrary.delete_asset(target_path):
            raise RuntimeError(f"Unable to replace generated BodyOnly asset: {target_path}")
    target = unreal.EditorAssetLibrary.duplicate_asset(
        raw.get_path_name().split(".", 1)[0], target_path
    )
    if not isinstance(target, unreal.AnimSequence):
        raise RuntimeError(f"Unable to create BodyOnly asset: {target_path}")

    model = target.data_model_interface
    controller = target.controller
    if model is None or controller is None:
        raise RuntimeError(f"Animation controller/model unavailable: {target_path}")
    tracks_before = [str(name) for name in model.get_bone_track_names()]
    removed_tracks = []
    controller.open_bracket("Create first-batch BodyOnly animation", False)
    try:
        for track_name in sorted(FACE_SUPPORT_TRACKS & set(tracks_before)):
            if not controller.remove_bone_track(unreal.Name(track_name), False):
                raise RuntimeError(f"Unable to remove face track: {track_name}")
            removed_tracks.append(track_name)
        controller.remove_all_attributes(False)
    finally:
        controller.close_bracket(False)
    unreal.AnimationLibrary.remove_all_curve_data(target)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save BodyOnly asset: {target_path}")
    return target, {
        "removed_face_tracks": removed_tracks,
        "target_path": target_path,
    }


def root_window_record(animation: unreal.AnimSequence, window: dict) -> dict:
    model = animation.data_model_interface
    frame_rate = model.get_frame_rate()
    fps = float(frame_rate.numerator) / float(frame_rate.denominator)
    frame_count = int(model.get_number_of_frames())
    last_frame = max(0, frame_count - 1)
    start_frame = min(last_frame, max(0, int(round(window["start_seconds"] * fps))))
    end_frame = min(
        last_frame, max(start_frame, int(round(window["source_end_seconds"] * fps)))
    )
    start = unreal.AnimationLibrary.get_bone_pose_for_frame(
        animation, unreal.Name("root"), start_frame, False
    )
    end = unreal.AnimationLibrary.get_bone_pose_for_frame(
        animation, unreal.Name("root"), end_frame, False
    )
    dx = float(end.translation.x - start.translation.x)
    dy = float(end.translation.y - start.translation.y)
    dz = float(end.translation.z - start.translation.z)
    return {
        "start_frame": start_frame,
        "end_frame": end_frame,
        "translation_delta_cm": {"x": dx, "y": dy, "z": dz},
        "horizontal_displacement_cm": math.sqrt(dx * dx + dy * dy),
        "translation_distance_cm": math.sqrt(dx * dx + dy * dy + dz * dz),
    }


def validate_action(
    action: dict,
    source_check: dict,
    raw: unreal.AnimSequence,
    body: unreal.AnimSequence,
    expected_skeleton: unreal.Skeleton,
    import_state: dict,
    body_state: dict,
) -> dict:
    raw_record = animation_record(raw)
    body_record = animation_record(body)
    raw_tracks = set(raw_record["bone_tracks"])
    body_tracks = set(body_record["bone_tracks"])
    window = action["window"]
    frame_tolerance = 1.0 / max(1.0, raw_record["frame_rate"]["numerator"])
    window_contract = {
        "start_seconds": float(window["start_seconds"]),
        "source_end_seconds": float(window["source_end_seconds"]),
        "source_duration_seconds": float(window["source_duration_seconds"]),
        "production_duration_seconds": float(window["production_duration_seconds"]),
        "padding_required_seconds": float(window["padding_required_seconds"]),
        "source_available": (
            raw_record["play_length_seconds"] + frame_tolerance + 0.01
            >= float(window["source_end_seconds"])
        ),
        "five_second_contract": abs(
            float(window["source_duration_seconds"])
            + float(window["padding_required_seconds"])
            - float(window["production_duration_seconds"])
        )
        <= 1.0e-4
        and abs(float(window["production_duration_seconds"]) - 5.0) <= 1.0e-4,
    }
    skeleton_path = expected_skeleton.get_path_name()
    checks = {
        "source_hash_passed": source_check["passed"],
        "raw_skeleton_passed": raw_record["skeleton"] == skeleton_path,
        "body_skeleton_passed": body_record["skeleton"] == skeleton_path,
        "raw_track_count_passed": raw_record["bone_track_count"] >= MIN_RAW_TRACKS,
        "body_track_count_passed": body_record["bone_track_count"] >= MIN_BODY_TRACKS,
        "raw_required_tracks_passed": not (REQUIRED_RAW_TRACKS - raw_tracks),
        "body_required_tracks_passed": not (REQUIRED_BODY_TRACKS - body_tracks),
        "body_face_tracks_removed": not (FACE_SUPPORT_TRACKS & body_tracks),
        "body_float_curves_removed": body_record["float_curve_count"] == 0,
        "source_frame_rate_supported": (
            raw_record["frame_rate"]["numerator"],
            raw_record["frame_rate"]["denominator"],
        )
        in SUPPORTED_SOURCE_FRAME_RATES,
        "body_timing_matches_raw": (
            body_record["frame_count"] == raw_record["frame_count"]
            and body_record["frame_rate"] == raw_record["frame_rate"]
            and abs(
                body_record["play_length_seconds"]
                - raw_record["play_length_seconds"]
            )
            <= 1.0e-4
        ),
        "window_source_available": window_contract["source_available"],
        "five_second_window_contract": window_contract["five_second_contract"],
    }
    return {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "action_id": action["action_id"],
        "sex": action["sex"],
        "face_policy": action["face_policy"],
        "root_motion_policy": action["root_motion_policy"],
        "source_check": source_check,
        "import_state": import_state,
        "body_only_state": body_state,
        "raw_animation": raw_record,
        "body_only_animation": body_record,
        "window": window_contract,
        "root_window": root_window_record(body, window),
        "checks": checks,
        "success": all(checks.values()),
        "production_status": "not_approved",
    }


def selected_actions(manifest: dict) -> list[dict]:
    actions = manifest.get("actions") or []
    requested = globals().get("DM_FIRST_BATCH_MOTION_IDS")
    if not requested:
        return actions
    requested_ids = [str(value) for value in requested]
    by_id = {row["action_id"]: row for row in actions}
    unknown = sorted(set(requested_ids) - set(by_id))
    if unknown:
        raise RuntimeError("Unknown first-batch action IDs: " + ", ".join(unknown))
    return [by_id[action_id] for action_id in requested_ids]


def run() -> dict:
    mode = str(globals().get("DM_FIRST_BATCH_MOTION_MODE", "import"))
    if mode not in {"preflight", "import"}:
        raise RuntimeError(f"Unsupported first-batch motion mode: {mode}")
    if not REQUIRED_EXPORTS_PATH.is_file():
        raise FileNotFoundError(str(REQUIRED_EXPORTS_PATH))
    manifest = read_json(REQUIRED_EXPORTS_PATH)
    if manifest.get("status") != "frozen_sources_ready_for_unreal_import":
        raise RuntimeError(f"Unexpected required-exports status: {manifest.get('status')}")
    actions = selected_actions(manifest)
    if not actions:
        raise RuntimeError("No first-batch actions selected")

    source_checks = {
        action["action_id"]: verify_source(action) for action in actions
    }
    if not NORMALIZED_MANIFEST_PATH.is_file():
        raise FileNotFoundError(str(NORMALIZED_MANIFEST_PATH))
    normalized_manifest = read_json(NORMALIZED_MANIFEST_PATH)
    normalized_records = {
        row["action_id"]: row
        for row in normalized_manifest.get("records", [])
        if isinstance(row, dict) and row.get("action_id")
    }
    normalized_checks = {
        action["action_id"]: verify_normalized(action, normalized_records)
        for action in actions
    }
    skeletons = {}
    for sex in sorted({action["sex"] for action in actions}):
        if sex not in SEX_CONFIG:
            raise RuntimeError(f"Unsupported action sex: {sex}")
        skeleton = unreal.load_asset(SEX_CONFIG[sex]["skeleton"])
        if not isinstance(skeleton, unreal.Skeleton):
            raise RuntimeError(f"Missing target skeleton: {SEX_CONFIG[sex]['skeleton']}")
        skeletons[sex] = skeleton

    if mode == "preflight":
        report = {
            "schema_version": 1,
            "mode": mode,
            "created_at_utc": utc_now(),
            "required_exports_path": str(REQUIRED_EXPORTS_PATH),
            "required_exports_sha256": sha256(REQUIRED_EXPORTS_PATH),
            "selected_action_ids": [action["action_id"] for action in actions],
            "source_checks": list(source_checks.values()),
            "normalized_manifest_path": str(NORMALIZED_MANIFEST_PATH),
            "normalized_manifest_sha256": sha256(NORMALIZED_MANIFEST_PATH),
            "normalized_checks": list(normalized_checks.values()),
            "skeletons": {
                sex: skeleton.get_path_name() for sex, skeleton in skeletons.items()
            },
            "success": (
                all(row["passed"] for row in source_checks.values())
                and all(row["passed"] for row in normalized_checks.values())
            ),
        }
        write_json(REPORT_ROOT / "preflight.json", report)
        return report

    for config in SEX_CONFIG.values():
        unreal.EditorAssetLibrary.make_directory(config["raw_destination"])
        unreal.EditorAssetLibrary.make_directory(config["body_destination"])
    unreal.EditorAssetLibrary.make_directory(CONFIG_ROOT)
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    pipelines = {
        sex: prepare_pipeline(SEX_CONFIG[sex], skeletons[sex])
        for sex in skeletons
    }

    records = []
    for action in actions:
        action_id = action["action_id"]
        source_check = source_checks[action_id]
        if not source_check["passed"]:
            raise RuntimeError(f"Motion source hash failed: {source_check}")
        normalized_check = normalized_checks[action_id]
        if not normalized_check["passed"]:
            raise RuntimeError(
                f"Normalized Motion source failed: {normalized_check}"
            )
        sex = action["sex"]
        raw, import_state = import_raw_animation(
            manager,
            world,
            action,
            SEX_CONFIG[sex],
            skeletons[sex],
            pipelines[sex],
            normalized_check,
        )
        body, body_state = build_body_only(action, raw, SEX_CONFIG[sex])
        record = validate_action(
            action,
            source_check,
            raw,
            body,
            skeletons[sex],
            import_state,
            body_state,
        )
        write_json(REPORT_ROOT / f"{action_id}_import_validation.json", record)
        records.append(record)
        if not record["success"]:
            raise RuntimeError(
                f"First-batch motion validation failed for {action_id}: "
                f"{REPORT_ROOT / (action_id + '_import_validation.json')}"
            )

    unreal.EditorAssetLibrary.save_directory(
        RAW_ROOT, only_if_is_dirty=False, recursive=True
    )
    unreal.EditorAssetLibrary.save_directory(
        BODY_ROOT, only_if_is_dirty=False, recursive=True
    )
    report = {
        "schema_version": 1,
        "mode": mode,
        "created_at_utc": utc_now(),
        "required_exports_path": str(REQUIRED_EXPORTS_PATH),
        "required_exports_sha256": sha256(REQUIRED_EXPORTS_PATH),
        "normalized_manifest_path": str(NORMALIZED_MANIFEST_PATH),
        "normalized_manifest_sha256": sha256(NORMALIZED_MANIFEST_PATH),
        "selected_action_ids": [action["action_id"] for action in actions],
        "records": records,
        "passed_count": sum(record["success"] for record in records),
        "failed_count": sum(not record["success"] for record in records),
        "success": len(records) == len(actions) and all(
            record["success"] for record in records
        ),
        "production_status": "not_approved",
    }
    write_json(REPORT_ROOT / "aggregate_motion_import_gate.json", report)
    return report


result = run()
print(
    "DM_FIRST_BATCH_MOTIONS="
    + json.dumps(
        {
            "mode": result["mode"],
            "selected_count": len(result["selected_action_ids"]),
            "passed_count": result.get("passed_count"),
            "failed_count": result.get("failed_count"),
            "report_root": str(REPORT_ROOT),
            "success": result["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
