"""Capture fixed-camera videos for the six first-batch expression combinations."""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path
import struct
import traceback

import unreal


TARGET = str(globals().get("DM_FIRST_BATCH_EXPRESSION_TARGET", "legacy"))
if TARGET == "canonical":
    OUTPUT_DIR = Path(
        r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
        r"\first_batch_day2_20260822_v1\dynamic_review_v1"
    )
else:
    OUTPUT_DIR = Path(
        r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
        r"\first_batch_expressions_20260820_v1\dynamic_review_v1"
    )
REPORT_PATH = OUTPUT_DIR / "dynamic_capture_report.json"
CAPTURE_FPS = 10
DURATION_SECONDS = 3.0
FRAME_COUNT = int(CAPTURE_FPS * DURATION_SECONDS)
TIME_DILATION = 0.25
CAMERA_SETTLE_SECONDS = 0.35
EXPRESSIONS = (
    {
        "expression_id": "happy",
        "pair_index": 0,
        "variant_index": 0,
        "hallmarks": (
            "CTRL_expressions_mouthCornerPullL",
            "CTRL_expressions_mouthCornerPullR",
        ),
    },
    {
        "expression_id": "angry",
        "pair_index": 0,
        "variant_index": 1,
        "hallmarks": (
            "CTRL_expressions_browDownL",
            "CTRL_expressions_browDownR",
        ),
    },
    {
        "expression_id": "sad",
        "pair_index": 1,
        "variant_index": 0,
        "hallmarks": (
            "CTRL_expressions_browRaiseInL",
            "CTRL_expressions_browRaiseInR",
            "CTRL_expressions_mouthCornerDepressL",
            "CTRL_expressions_mouthCornerDepressR",
        ),
    },
)
ACTOR_IDS = ("FB_F", "FB_M") if TARGET == "canonical" else ("F02", "M02")
ACTOR_SPECS = tuple(
    {
        "actor_id": actor_id,
        "expression_id": expression["expression_id"],
        "pair_index": expression["pair_index"],
        "variant_index": expression["variant_index"],
        "hallmarks": expression["hallmarks"],
        "label": f"DM_FBEXP_{actor_id}_{expression['expression_id'].title()}",
    }
    for actor_id in ACTOR_IDS
    for expression in EXPRESSIONS
)
POSE_BONES = ("head", "hand_l", "hand_r")


def unregister_previous_callback():
    handle = globals().get("_dm_first_batch_expression_dynamic_callback")
    if handle is not None:
        try:
            unreal.unregister_slate_post_tick_callback(handle)
        except Exception:
            pass
    globals()["_dm_first_batch_expression_dynamic_callback"] = None


def capture_viewport(output_path):
    capture = unreal.get_default_object(unreal.EditorAppToolset).call_method(
        "CaptureViewport", (None, None, False)
    )
    image = capture.image
    if image.mime_type != "image/png" or not image.data:
        raise RuntimeError("Viewport capture did not return PNG data")
    payload = base64.b64decode(image.data)
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Viewport capture returned an invalid PNG")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    width, height = struct.unpack(">II", payload[16:24])
    return {
        "bytes": len(payload),
        "height": int(height),
        "path": str(output_path),
        "width": int(width),
    }


def find_actor(world, label):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    actor = next((item for item in actors if item.get_actor_label() == label), None)
    if actor is None:
        raise RuntimeError(f"PIE actor unavailable: {label}")
    return actor


def find_body(actor):
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    if len(components) != 1:
        raise RuntimeError(
            f"Expected one Body component on {actor.get_actor_label()}, found {len(components)}"
        )
    return components[0]


def vector_record(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def set_head_camera(body):
    head = body.get_socket_location(unreal.Name("head"))
    location = head + unreal.Vector(0.0, 67.0, 3.0)
    target = head + unreal.Vector(0.0, 0.0, 1.0)
    rotation = unreal.MathLibrary.find_look_at_rotation(location, target)
    unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).set_level_viewport_camera_info(location, rotation)
    return {
        "location": vector_record(location),
        "target": vector_record(target),
        "view": "head_front_fixed",
    }


def pose_values(body):
    result = {}
    for bone in POSE_BONES:
        if body.does_socket_exist(bone):
            transform = body.get_socket_transform(
                unreal.Name(bone), unreal.RelativeTransformSpace.RTS_COMPONENT
            )
            result[bone] = vector_record(transform.translation)
    return result


def pose_delta(left, right):
    deltas = []
    for bone in sorted(set(left) & set(right)):
        a = left[bone]
        b = right[bone]
        deltas.append(
            math.sqrt(
                (a["x"] - b["x"]) ** 2
                + (a["y"] - b["y"]) ** 2
                + (a["z"] - b["z"]) ** 2
            )
        )
    return max(deltas, default=0.0)


def write_report(report):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


unregister_previous_callback()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if REPORT_PATH.exists():
    REPORT_PATH.unlink()
for output_path in (OUTPUT_DIR / "frames").glob("**/*.png"):
    output_path.unlink()

game_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if game_world is None:
    raise RuntimeError("PIE/Simulate world is not running")

actors = []
for spec in ACTOR_SPECS:
    actor = find_actor(game_world, spec["label"])
    body = find_body(actor)
    if not body.get_editor_property("disable_post_process_blueprint"):
        raise RuntimeError(f"Post-process Blueprint must be disabled: {spec['label']}")
    body.set_component_tick_enabled(False)
    actors.append({**spec, "actor": actor, "body": body, "instance": None})

unreal.GameplayStatics.set_global_time_dilation(game_world, TIME_DILATION)
state = {
    "phase": "waiting_instances",
    "wait_ticks": 0,
    "case_cursor": 0,
    "frame_cursor": 0,
    "settle_elapsed": 0.0,
    "playback_elapsed": 0.0,
    "last_world_time": None,
    "camera": None,
    "cases": [],
    "errors": [],
    "finished": False,
}


def initialize_instances():
    for item in actors:
        instance = item["body"].get_anim_instance()
        if instance is None:
            return False
        for variable in ("ExpressionPairIndex", "ExpressionVariantIndex"):
            try:
                instance.get_editor_property(variable)
            except Exception as exc:
                raise RuntimeError(f"{item['label']} lacks selector {variable}") from exc
        instance.set_editor_property("ExpressionPairIndex", item["pair_index"])
        instance.set_editor_property("ExpressionVariantIndex", item["variant_index"])
        item["body"].set_allow_anim_curve_evaluation(True)
        item["instance"] = instance
    start_case()
    return True


def start_case():
    if state["case_cursor"] >= len(actors):
        finish(True)
        return
    target = actors[state["case_cursor"]]
    for item in actors:
        item["actor"].set_actor_hidden_in_game(item is not target)
        item["body"].set_component_tick_enabled(False)
    target["actor"].set_actor_hidden_in_game(False)
    target["instance"].set_editor_property("ExpressionPairIndex", target["pair_index"])
    target["instance"].set_editor_property("ExpressionVariantIndex", target["variant_index"])
    state["frame_cursor"] = 0
    state["settle_elapsed"] = 0.0
    state["playback_elapsed"] = 0.0
    state["camera"] = set_head_camera(target["body"])
    state["phase"] = "camera_settle"


def start_playback():
    target = actors[state["case_cursor"]]
    target["body"].set_component_tick_enabled(True)
    state["playback_elapsed"] = 0.0
    state["last_world_time"] = float(unreal.GameplayStatics.get_time_seconds(game_world))
    state["phase"] = "playing"


def capture_frame():
    target = actors[state["case_cursor"]]
    frame_index = state["frame_cursor"]
    target["body"].set_component_tick_enabled(False)
    case_id = f"{target['actor_id'].lower()}_{target['expression_id']}"
    image = capture_viewport(
        OUTPUT_DIR / "frames" / case_id / f"frame_{frame_index:03d}.png"
    )
    curves = {
        curve: float(target["instance"].get_curve_value(curve))
        for curve in target["hallmarks"]
    }
    if frame_index == 0:
        state["cases"].append(
            {
                "case_id": case_id,
                "actor_id": target["actor_id"],
                "expression_id": target["expression_id"],
                "camera": state["camera"],
                "frames": [],
            }
        )
    state["cases"][-1]["frames"].append(
        {
            "curves": curves,
            "frame": frame_index,
            "image": image,
            "observed_seconds": float(state["playback_elapsed"]),
            "pose": pose_values(target["body"]),
            "target_seconds": frame_index / CAPTURE_FPS,
        }
    )
    state["frame_cursor"] += 1
    if state["frame_cursor"] >= FRAME_COUNT:
        state["case_cursor"] += 1
        start_case()
    else:
        target["body"].set_component_tick_enabled(True)


def build_diagnostics():
    diagnostics = []
    for case in state["cases"]:
        frames = case["frames"]
        curve_names = sorted({name for frame in frames for name in frame["curves"]})
        spans = {}
        for curve in curve_names:
            values = [frame["curves"][curve] for frame in frames]
            spans[curve] = max(values) - min(values)
        maximum_pose_delta = max(
            (pose_delta(frames[0]["pose"], frame["pose"]) for frame in frames[1:]),
            default=0.0,
        )
        diagnostics.append(
            {
                "case_id": case["case_id"],
                "frame_count": len(frames),
                "hallmark_curve_spans": spans,
                "dynamic_expression_observed": any(value > 0.002 for value in spans.values()),
                "maximum_pose_delta_cm": maximum_pose_delta,
                "body_animation_observed": maximum_pose_delta > 0.05,
            }
        )
    return diagnostics


def finish(successful_execution):
    if state["finished"]:
        return
    state["finished"] = True
    unreal.GameplayStatics.set_global_time_dilation(game_world, 1.0)
    for item in actors:
        item["actor"].set_actor_hidden_in_game(False)
        item["body"].set_component_tick_enabled(True)
    diagnostics = build_diagnostics()
    for item in diagnostics:
        if item["frame_count"] != FRAME_COUNT:
            state["errors"].append(f"Frame count mismatch: {item['case_id']}")
        if not item["dynamic_expression_observed"]:
            state["errors"].append(f"Expression is static: {item['case_id']}")
        if not item["body_animation_observed"]:
            state["errors"].append(f"Body animation is static: {item['case_id']}")
    report = {
        "schema_version": 1,
        "review_id": (
            "first_batch_day2_dynamic_review_20260822_v1"
            if TARGET == "canonical"
            else "first_batch_expression_dynamic_review_20260820_v1"
        ),
        "target": TARGET,
        "capture_fps": CAPTURE_FPS,
        "duration_seconds": DURATION_SECONDS,
        "frame_count_per_case": FRAME_COUNT,
        "time_dilation_during_capture": TIME_DILATION,
        "case_count": len(state["cases"]),
        "expected_case_count": len(actors),
        "cases": state["cases"],
        "diagnostics": diagnostics,
        "errors": state["errors"],
        "automatic_success": (
            successful_execution
            and len(state["cases"]) == len(actors)
            and not state["errors"]
        ),
        "visual_review": "pending",
        "production_status": "not_approved",
    }
    report["success"] = report["automatic_success"]
    write_report(report)
    handle = globals().get("_dm_first_batch_expression_dynamic_callback")
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
    globals()["_dm_first_batch_expression_dynamic_callback"] = None
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if subsystem.is_in_play_in_editor():
        subsystem.editor_request_end_play()


def on_tick(delta_seconds):
    try:
        if state["phase"] == "waiting_instances":
            state["wait_ticks"] += 1
            if initialize_instances():
                return
            if state["wait_ticks"] > 300:
                raise RuntimeError("AnimInstances were not initialized")
            return
        if state["phase"] == "camera_settle":
            state["settle_elapsed"] += max(0.0, min(float(delta_seconds), 0.10))
            if state["settle_elapsed"] >= CAMERA_SETTLE_SECONDS:
                start_playback()
            return
        if state["phase"] == "playing":
            world_time = float(unreal.GameplayStatics.get_time_seconds(game_world))
            last_world_time = state["last_world_time"]
            state["last_world_time"] = world_time
            if last_world_time is not None:
                state["playback_elapsed"] += max(0.0, world_time - float(last_world_time))
            target_seconds = state["frame_cursor"] / CAPTURE_FPS
            if state["playback_elapsed"] >= target_seconds:
                capture_frame()
    except Exception:
        state["errors"].append(traceback.format_exc())
        finish(False)


globals()["_dm_first_batch_expression_dynamic_state"] = state
globals()["_dm_first_batch_expression_dynamic_callback"] = (
    unreal.register_slate_post_tick_callback(on_tick)
)
print(
    "DM_FIRST_BATCH_EXPRESSION_DYNAMIC_STARTED="
    + json.dumps(
        {
            "case_count": len(actors),
            "frame_count_per_case": FRAME_COUNT,
            "report": str(REPORT_PATH),
            "success": True,
        },
        sort_keys=True,
    )
)
