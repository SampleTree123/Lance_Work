"""Build 3-second curve-only Happy/Angry/Sad clips for F02 and M02."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


CONFIG_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\unreal"
    r"\first_batch_expression_profile_20260820_v1.json"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\first_batch_expressions_20260820_v1\build_report.json"
)


def load_config():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise RuntimeError("Unsupported expression profile schema")
    if config.get("status") != "frozen_for_ue_pilot":
        raise RuntimeError("Expression profile is not frozen for the UE pilot")
    return config


def load_required(path, expected_type, label):
    asset = unreal.load_asset(path)
    if not isinstance(asset, expected_type):
        raise RuntimeError(f"Missing {label}: {path}")
    return asset


def merged_curves(config, expression):
    result = dict(config["common_curves"])
    overlap = set(result).intersection(expression["curves"])
    if overlap:
        raise RuntimeError(
            f"Expression overrides common curves: {sorted(overlap)}"
        )
    result.update(expression["curves"])
    return result


def build_clip(config, actor, expression, mesh, source, skeleton):
    name = f"A_DM_{actor['actor_id']}_Face_{expression['asset_suffix']}"
    path = f"{actor['target_folder']}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"Refusing to overwrite expression clip: {path}")
    target = unreal.EditorAssetLibrary.duplicate_asset(
        source.get_path_name().split(".", 1)[0], path
    )
    if not isinstance(target, unreal.AnimSequence):
        raise RuntimeError(f"Unable to duplicate expression source: {path}")

    controller = target.controller
    model = target.data_model_interface
    if controller is None or model is None:
        raise RuntimeError(f"Animation controller/model unavailable: {path}")
    controller.open_bracket("Create first-batch expression clip", False)
    try:
        for track_name in list(model.get_bone_track_names()):
            if not controller.remove_bone_track(track_name, False):
                raise RuntimeError(f"Unable to remove bone track: {track_name}")
        controller.remove_all_attributes(False)
        controller.set_frame_rate(
            unreal.FrameRate(config["animation_sample_fps"], 1), False
        )
        controller.set_number_of_frames(
            unreal.FrameNumber(config["frame_count"]), False
        )
    finally:
        controller.close_bracket(False)
    unreal.AnimationLibrary.remove_all_curve_data(target)

    curves = merged_curves(config, expression)
    available_morphs = {
        str(name) for name in mesh.get_all_morph_target_names()
    }
    missing = sorted(set(curves) - available_morphs)
    if missing:
        raise RuntimeError(
            f"{actor['actor_id']} mesh lacks expression Morphs: {missing}"
        )
    for curve_name, keys in curves.items():
        curve = unreal.Name(curve_name)
        unreal.AnimationLibrary.add_curve(
            target, curve, unreal.RawCurveTrackTypes.RCT_FLOAT, False
        )
        unreal.AnimationLibrary.add_float_curve_keys(
            target, curve, keys["times"], keys["values"]
        )
        unreal.AnimationLibrary.set_curve_meta_data_morph_target(
            skeleton, curve, True
        )

    target.set_editor_property(
        "additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE
    )
    target.set_editor_property(
        "ref_pose_type", unreal.AdditiveBasePoseType.ABPT_REF_POSE
    )
    target.set_editor_property("enable_root_motion", False)
    target.set_editor_property("force_root_lock", True)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save expression clip: {path}")

    model = target.data_model_interface
    bone_tracks = [str(name) for name in model.get_bone_track_names()]
    curve_names = sorted(
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            target, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    )
    missing_after = sorted(set(curves) - set(curve_names))
    frame_rate = model.get_frame_rate()
    frame_count_value = model.get_number_of_frames()
    frame_count = int(getattr(frame_count_value, "value", frame_count_value))
    play_length = float(model.get_play_length())
    errors = []
    if bone_tracks:
        errors.append(f"bone_tracks={bone_tracks}")
    if missing_after:
        errors.append(f"missing_curves={missing_after}")
    if (
        frame_rate.numerator != config["animation_sample_fps"]
        or frame_rate.denominator != 1
    ):
        errors.append(f"frame_rate={frame_rate.numerator}/{frame_rate.denominator}")
    if frame_count != config["frame_count"]:
        errors.append(f"frame_count={frame_count}")
    if abs(play_length - config["duration_seconds"]) > 1.0e-4:
        errors.append(f"play_length={play_length}")
    if errors:
        raise RuntimeError(f"Expression verification failed for {path}: {errors}")
    return {
        "actor_id": actor["actor_id"],
        "expression_id": expression["expression_id"],
        "asset": target.get_path_name(),
        "skeleton": skeleton.get_path_name(),
        "bone_track_count": 0,
        "curve_count": len(curve_names),
        "curve_names": curve_names,
        "frame_count": frame_count,
        "animation_sample_fps": frame_rate.numerator,
        "render_fps": config["render_fps"],
        "duration_seconds": play_length,
        "additive_anim_type": str(
            target.get_editor_property("additive_anim_type")
        ),
        "ref_pose_type": str(target.get_editor_property("ref_pose_type")),
        "success": True,
    }


config = load_config()
records = []
for actor in config["actors"]:
    mesh = load_required(actor["mesh"], unreal.SkeletalMesh, "mesh")
    source = load_required(
        actor["source_animation"], unreal.AnimSequence, "source animation"
    )
    skeleton = source.get_editor_property("skeleton")
    if skeleton is None or mesh.get_editor_property("skeleton") != skeleton:
        raise RuntimeError(
            f"Mesh/source Skeleton mismatch for {actor['actor_id']}"
        )
    for expression in config["expressions"]:
        records.append(
            build_clip(
                config, actor, expression, mesh, source, skeleton
            )
        )
    unreal.EditorAssetLibrary.save_loaded_asset(
        skeleton, only_if_is_dirty=False
    )

report = {
    "schema_version": 1,
    "profile_id": config["profile_id"],
    "runtime_scope": "full_reference_direct_morph",
    "post_process_policy": "disable_on_full_reference_component",
    "records": records,
    "counts": {
        "actors": len(config["actors"]),
        "expressions": len(config["expressions"]),
        "clips": len(records),
    },
    "success": len(records) == 6 and all(item["success"] for item in records),
    "visual_status": "pending_runtime_composition_review",
    "production_status": "not_approved",
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(
    "DM_FIRST_BATCH_EXPRESSIONS="
    + json.dumps(
        {
            "report": str(REPORT_PATH),
            "clip_count": len(records),
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
