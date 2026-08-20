"""Run the M02 2x4 layered-animation matrix in a live PIE world."""

from __future__ import annotations

import json
import math
from pathlib import Path
import traceback

import unreal


CHARACTER_BLUEPRINT = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
ANIM_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v002"
)
ACTOR_LABEL = "DM_M02_LayeredAnimValidation"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_layered_animation_matrix_v002.json"
)
BODY_IDS = {0: "audience", 1: "walk_wander"}
FACE_SPECS = {
    0: {"id": "neutral", "pair": 0, "variant": 0, "sample_time": 1.20},
    1: {"id": "natural_blink", "pair": 0, "variant": 1, "sample_time": 0.90},
    2: {"id": "blink_gaze", "pair": 1, "variant": 0, "sample_time": 1.20},
    3: {"id": "subtle_smile", "pair": 1, "variant": 1, "sample_time": 1.50},
}
FACE_ASSETS = [
    "/Game/DataMake/Animations/CC5/Pilot/Face/A_DM_M02_Face_Neutral_Loop_v001",
    "/Game/DataMake/Animations/CC5/Pilot/Face/A_DM_M02_Face_NaturalBlink_Loop_v001",
    "/Game/DataMake/Animations/CC5/Pilot/Face/A_DM_M02_Face_BlinkGaze_Loop_v001",
    "/Game/DataMake/Animations/CC5/Pilot/Face/A_DM_M02_Face_SubtleSmile_Loop_v001",
]
CURVES = [
    "CTRL_expressions_eyeBlinkL",
    "CTRL_expressions_eyeBlinkR",
    "CTRL_expressions_eyeLookLeftL",
    "CTRL_expressions_eyeLookLeftR",
    "CTRL_expressions_eyeLookRightL",
    "CTRL_expressions_eyeLookRightR",
    "CTRL_expressions_mouthCornerPullL",
    "CTRL_expressions_mouthCornerPullR",
]
POSE_BONES = ["hand_l", "hand_r", "head"]


def vector_record(value):
    return {"x": value.x, "y": value.y, "z": value.z}


def vector_distance(left, right):
    return math.sqrt(
        (left["x"] - right["x"]) ** 2
        + (left["y"] - right["y"]) ** 2
        + (left["z"] - right["z"]) ** 2
    )


def write_report(report):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def unregister_previous_callback():
    handle = globals().get("_dm_m02_layer_matrix_callback")
    if handle is None:
        return
    try:
        unreal.unregister_slate_post_tick_callback(handle)
    except Exception:
        pass
    globals()["_dm_m02_layer_matrix_callback"] = None


unregister_previous_callback()
if REPORT_PATH.exists():
    REPORT_PATH.unlink()

character_bp = unreal.load_asset(CHARACTER_BLUEPRINT)
anim_bp = unreal.load_asset(ANIM_BLUEPRINT)
face_assets = [unreal.load_asset(path) for path in FACE_ASSETS]
if not isinstance(character_bp, unreal.Blueprint):
    raise RuntimeError(f"Character Blueprint unavailable: {CHARACTER_BLUEPRINT}")
if not isinstance(anim_bp, unreal.AnimBlueprint):
    raise RuntimeError(f"AnimBlueprint unavailable: {ANIM_BLUEPRINT}")
if not all(isinstance(asset, unreal.AnimSequence) for asset in face_assets):
    raise RuntimeError(f"Face clip library is incomplete: {face_assets}")
anim_class = anim_bp.generated_class()

asset_errors = []
asset_checks = {
    "natural_blink_peak": unreal.AnimationLibrary.get_float_value_at_time(
        face_assets[1], "CTRL_expressions_eyeBlinkL", 0.90
    ),
    "blink_gaze_plateau": unreal.AnimationLibrary.get_float_value_at_time(
        face_assets[2], "CTRL_expressions_eyeLookLeftL", 1.20
    ),
    "subtle_smile_plateau": unreal.AnimationLibrary.get_float_value_at_time(
        face_assets[3], "CTRL_expressions_mouthCornerPullL", 1.50
    ),
}
if asset_checks["natural_blink_peak"] < 0.90:
    asset_errors.append("Natural-blink source curve has no expected peak")
if asset_checks["blink_gaze_plateau"] < 0.25:
    asset_errors.append("Blink-gaze source curve has no expected plateau")
if asset_checks["subtle_smile_plateau"] < 0.22:
    asset_errors.append("Subtle-smile source curve has no expected plateau")

editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = editor_subsystem.get_game_world()
if game_world is None:
    raise RuntimeError("PIE/Simulate world is not running")
actors = unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor)
actor = next(
    (item for item in actors if item.get_actor_label() == ACTOR_LABEL), None
)
if actor is None:
    raise RuntimeError(f"PIE validation actor is unavailable: {ACTOR_LABEL}")

components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    raise RuntimeError("Validation actor has no Body component")
followers = [item for item in components if item != body]
followers_without_body_leader = [
    item.get_name()
    for item in followers
    if item.get_editor_property("leader_pose_component") != body
]
body.set_update_animation_in_editor(True)
body.set_allow_anim_curve_evaluation(True)
body.set_component_tick_enabled(True)
body.set_enable_animation(True)
body.propagate_curves_to_followers = True
body.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)

cells = [
    (body_index, body_id, face_index, FACE_SPECS[face_index])
    for body_index, body_id in BODY_IDS.items()
    for face_index in sorted(FACE_SPECS)
]
state = {
    "cell_index": 0,
    "elapsed": 0.0,
    "records": [],
    "errors": list(asset_errors),
    "instance": None,
}


def start_cell():
    body_index, _body_id, _face_index, face_spec = cells[state["cell_index"]]
    body.set_anim_instance_class(None)
    body.set_anim_instance_class(anim_class)
    instance = body.get_anim_instance()
    if instance is None:
        raise RuntimeError("Layered AnimInstance was not initialized")
    instance.set_editor_property("BodyMotionIndex", body_index)
    instance.set_editor_property("FacePairIndex", face_spec["pair"])
    instance.set_editor_property("FaceVariantIndex", face_spec["variant"])
    state["instance"] = instance
    state["elapsed"] = 0.0


def sample_cell():
    body_index, body_id, face_index, face_spec = cells[state["cell_index"]]
    instance = state["instance"]
    curves = {name: float(instance.get_curve_value(name)) for name in CURVES}
    expected_curves = {
        name: float(
            unreal.AnimationLibrary.get_float_value_at_time(
                face_assets[face_index], name, face_spec["sample_time"]
            )
        )
        for name in CURVES
    }
    curve_deltas = {
        name: abs(curves[name] - expected_curves[name]) for name in CURVES
    }
    cell_errors = [
        f"Curve mismatch {name}: runtime={curves[name]:.3f}, "
        f"expected={expected_curves[name]:.3f}"
        for name in CURVES
        if curve_deltas[name] > 0.18
    ]
    pose_signature = {
        bone: vector_record(body.get_socket_location(bone))
        for bone in POSE_BONES
        if body.does_socket_exist(bone)
    }
    state["records"].append(
        {
            "body_index": body_index,
            "body_id": body_id,
            "face_index": face_index,
            "face_id": face_spec["id"],
            "face_pair_index": face_spec["pair"],
            "face_variant_index": face_spec["variant"],
            "sample_time_seconds": face_spec["sample_time"],
            "actual_elapsed_seconds": state["elapsed"],
            "runtime_selectors": {
                "BodyMotionIndex": instance.get_editor_property("BodyMotionIndex"),
                "FacePairIndex": instance.get_editor_property("FacePairIndex"),
                "FaceVariantIndex": instance.get_editor_property(
                    "FaceVariantIndex"
                ),
            },
            "runtime_curves": curves,
            "expected_curves": expected_curves,
            "curve_deltas": curve_deltas,
            "pose_signature": pose_signature,
            "errors": cell_errors,
        }
    )
    state["errors"].extend(
        f"{body_id}+{face_spec['id']}: {message}" for message in cell_errors
    )


def finish(successful_execution=True):
    pose_comparisons = []
    if successful_execution:
        for face_index, face_spec in FACE_SPECS.items():
            audience = next(
                item
                for item in state["records"]
                if item["body_index"] == 0 and item["face_index"] == face_index
            )
            walk = next(
                item
                for item in state["records"]
                if item["body_index"] == 1 and item["face_index"] == face_index
            )
            common_bones = set(audience["pose_signature"]) & set(
                walk["pose_signature"]
            )
            distances = {
                bone: vector_distance(
                    audience["pose_signature"][bone], walk["pose_signature"][bone]
                )
                for bone in common_bones
            }
            max_distance = max(distances.values(), default=0.0)
            if max_distance <= 1.0:
                state["errors"].append(
                    f"Body selector did not change pose for {face_spec['id']}"
                )
            pose_comparisons.append(
                {
                    "face_index": face_index,
                    "face_id": face_spec["id"],
                    "bone_distances_cm": distances,
                    "max_distance_cm": max_distance,
                    "different_body_pose": max_distance > 1.0,
                }
            )
    if followers_without_body_leader:
        state["errors"].append(
            "Followers without Body leader: "
            + ", ".join(followers_without_body_leader)
        )
    if not body.propagate_curves_to_followers:
        state["errors"].append("Body curve propagation to followers is disabled")

    report = {
        "schema_version": 3,
        "character_blueprint": character_bp.get_path_name(),
        "anim_blueprint": anim_bp.get_path_name(),
        "anim_class": anim_class.get_path_name(),
        "world": game_world.get_path_name(),
        "actor": actor.get_path_name(),
        "actor_transient": False,
        "matrix_dimensions": {"body": len(BODY_IDS), "face": len(FACE_SPECS)},
        "matrix_cell_count": len(state["records"]),
        "component_count": len(components),
        "follower_count": len(followers),
        "followers_without_body_leader": followers_without_body_leader,
        "propagate_curves_to_followers": body.propagate_curves_to_followers,
        "asset_checks": asset_checks,
        "records": state["records"],
        "pose_comparisons": pose_comparisons,
        "errors": state["errors"],
        "success": successful_execution and not state["errors"],
    }
    write_report(report)
    globals()["_dm_m02_layer_matrix_result"] = report


def on_tick(delta_seconds):
    try:
        state["elapsed"] += float(delta_seconds)
        _body_index, _body_id, _face_index, face_spec = cells[
            state["cell_index"]
        ]
        if state["elapsed"] + 1.0e-6 < face_spec["sample_time"]:
            return
        sample_cell()
        state["cell_index"] += 1
        if state["cell_index"] < len(cells):
            start_cell()
            return

        # Leave a useful Audience + natural-blink preview staged.
        body.set_anim_instance_class(None)
        body.set_anim_instance_class(anim_class)
        preview = body.get_anim_instance()
        preview.set_editor_property("BodyMotionIndex", 0)
        preview.set_editor_property("FacePairIndex", 0)
        preview.set_editor_property("FaceVariantIndex", 1)
        finish(True)
        unreal.unregister_slate_post_tick_callback(
            globals()["_dm_m02_layer_matrix_callback"]
        )
        globals()["_dm_m02_layer_matrix_callback"] = None
    except Exception:
        state["errors"].append(traceback.format_exc())
        finish(False)
        handle = globals().get("_dm_m02_layer_matrix_callback")
        if handle is not None:
            unreal.unregister_slate_post_tick_callback(handle)
        globals()["_dm_m02_layer_matrix_callback"] = None


start_cell()
globals()["_dm_m02_layer_matrix_state"] = state
globals()["_dm_m02_layer_matrix_callback"] = unreal.register_slate_post_tick_callback(
    on_tick
)
print(
    "DM_LAYER_MATRIX_STARTED="
    + json.dumps(
        {"report_path": str(REPORT_PATH), "cell_count": len(cells), "success": True},
        sort_keys=True,
    )
)
