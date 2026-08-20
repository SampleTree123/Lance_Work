"""Capture the six first-batch expressions while a body animation is running."""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path
import struct
import traceback

import unreal


OUTPUT_DIR = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\first_batch_expressions_20260820_v1\runtime_review"
)
REPORT_PATH = OUTPUT_DIR / "pie_expression_review.json"
CAMERA_SETTLE_SECONDS = 0.25
SAMPLE_SPECS = (
    (0.40, "early", "head_front"),
    (1.35, "middle", "head_three_quarter"),
    (2.45, "late", "head_front"),
)
EXPRESSIONS = (
    {
        "expression_id": "happy",
        "pair_index": 0,
        "variant_index": 0,
        "hallmarks": {
            "CTRL_expressions_mouthCornerPullL": 0.20,
            "CTRL_expressions_mouthCornerPullR": 0.18,
        },
    },
    {
        "expression_id": "angry",
        "pair_index": 0,
        "variant_index": 1,
        "hallmarks": {
            "CTRL_expressions_browDownL": 0.25,
            "CTRL_expressions_browDownR": 0.23,
        },
    },
    {
        "expression_id": "sad",
        "pair_index": 1,
        "variant_index": 0,
        "hallmarks": {
            "CTRL_expressions_browRaiseInL": 0.24,
            "CTRL_expressions_browRaiseInR": 0.22,
            "CTRL_expressions_mouthCornerDepressL": 0.17,
            "CTRL_expressions_mouthCornerDepressR": 0.15,
        },
    },
)
ACTOR_SPECS = tuple(
    {
        "actor_id": actor_id,
        "expression_id": expression["expression_id"],
        "pair_index": expression["pair_index"],
        "variant_index": expression["variant_index"],
        "hallmarks": expression["hallmarks"],
        "label": f"DM_FBEXP_{actor_id}_{expression['expression_id'].title()}",
    }
    for actor_id in ("F02", "M02")
    for expression in EXPRESSIONS
)
WATCHED_CURVES = tuple(
    sorted(
        {
            curve
            for expression in EXPRESSIONS
            for curve in expression["hallmarks"]
        }
        | {
            "CTRL_expressions_eyeBlinkL",
            "CTRL_expressions_eyeBlinkR",
        }
    )
)
POSE_BONES = ("head", "hand_l", "hand_r")


def unregister_previous_callback():
    handle = globals().get("_dm_first_batch_expression_review_callback")
    if handle is not None:
        try:
            unreal.unregister_slate_post_tick_callback(handle)
        except Exception:
            pass
    globals()["_dm_first_batch_expression_review_callback"] = None


def capture_viewport(output_path):
    capture = unreal.get_default_object(unreal.EditorAppToolset).call_method(
        "CaptureViewport", (None, None, False)
    )
    image = capture.image
    if image.mime_type != "image/png" or not image.data:
        raise RuntimeError("Viewport capture did not return PNG data")
    png_bytes = base64.b64decode(image.data)
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Viewport capture returned an invalid PNG")
    output_path.write_bytes(png_bytes)
    width, height = struct.unpack(">II", png_bytes[16:24])
    return {
        "bytes": len(png_bytes),
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
            f"Expected one Body component on {actor.get_actor_label()}, "
            f"found {len(components)}"
        )
    return components[0]


def midpoint(left, right):
    return unreal.Vector(
        (left.x + right.x) * 0.5,
        (left.y + right.y) * 0.5,
        (left.z + right.z) * 0.5,
    )


def vector_record(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def set_camera(body, view):
    head = body.get_socket_location(unreal.Name("head"))
    if view == "head_front":
        location = head + unreal.Vector(0.0, 67.0, 3.0)
    elif view == "head_three_quarter":
        location = head + unreal.Vector(43.0, 56.0, 4.0)
    else:
        raise RuntimeError(f"Unknown camera view: {view}")
    target = head + unreal.Vector(0.0, 0.0, 1.0)
    rotation = unreal.MathLibrary.find_look_at_rotation(location, target)
    unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).set_level_viewport_camera_info(location, rotation)
    return {
        "location": vector_record(location),
        "target": vector_record(target),
        "view": view,
    }


def curve_values(instance):
    return {
        curve: float(instance.get_curve_value(curve)) for curve in WATCHED_CURVES
    }


def pose_values(body):
    result = {}
    for bone in POSE_BONES:
        if not body.does_socket_exist(bone):
            continue
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
for output_path in OUTPUT_DIR.glob("*.png"):
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
    actors.append({**spec, "actor": actor, "body": body, "instance": None})

state = {
    "phase": "waiting_instances",
    "wait_ticks": 0,
    "case_cursor": 0,
    "sample_cursor": 0,
    "elapsed": 0.0,
    "last_world_time": None,
    "camera": None,
    "records": [],
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
                raise RuntimeError(
                    f"{item['label']} lacks selector {variable}"
                ) from exc
        instance.set_editor_property("ExpressionPairIndex", item["pair_index"])
        instance.set_editor_property(
            "ExpressionVariantIndex", item["variant_index"]
        )
        item["body"].set_allow_anim_curve_evaluation(True)
        item["body"].set_component_tick_enabled(False)
        item["instance"] = instance
    state["last_world_time"] = float(
        unreal.GameplayStatics.get_time_seconds(game_world)
    )
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
    target["instance"].set_editor_property(
        "ExpressionPairIndex", target["pair_index"]
    )
    target["instance"].set_editor_property(
        "ExpressionVariantIndex", target["variant_index"]
    )
    state["sample_cursor"] = 0
    state["elapsed"] = 0.0
    state["camera"] = set_camera(target["body"], SAMPLE_SPECS[0][2])
    state["phase"] = "camera_settle"


def start_playback():
    target = actors[state["case_cursor"]]
    target["body"].set_component_tick_enabled(True)
    state["elapsed"] = 0.0
    state["last_world_time"] = float(
        unreal.GameplayStatics.get_time_seconds(game_world)
    )
    state["phase"] = "playing"


def capture_sample():
    target = actors[state["case_cursor"]]
    sample_time, sample_id, view = SAMPLE_SPECS[state["sample_cursor"]]
    target["body"].set_component_tick_enabled(False)
    curves = curve_values(target["instance"])
    hallmark_errors = [
        f"{curve}={curves[curve]:.3f} < {minimum:.3f}"
        for curve, minimum in target["hallmarks"].items()
        if curves[curve] < minimum
    ]
    filename = (
        f"{target['actor_id'].lower()}__{target['expression_id']}__"
        f"{sample_id}__{view}.png"
    )
    image = capture_viewport(OUTPUT_DIR / filename)
    record = {
        "actor_id": target["actor_id"],
        "expression_id": target["expression_id"],
        "sample_id": sample_id,
        "target_seconds": sample_time,
        "observed_seconds": float(state["elapsed"]),
        "selectors": {
            "ExpressionPairIndex": int(
                target["instance"].get_editor_property("ExpressionPairIndex")
            ),
            "ExpressionVariantIndex": int(
                target["instance"].get_editor_property("ExpressionVariantIndex")
            ),
        },
        "curves": curves,
        "pose": pose_values(target["body"]),
        "camera": state["camera"],
        "image": image,
        "errors": hallmark_errors,
    }
    state["records"].append(record)
    state["errors"].extend(
        f"{target['label']}/{sample_id}: {message}"
        for message in hallmark_errors
    )

    state["sample_cursor"] += 1
    if state["sample_cursor"] >= len(SAMPLE_SPECS):
        state["case_cursor"] += 1
        start_case()
        return
    _, _, next_view = SAMPLE_SPECS[state["sample_cursor"]]
    state["camera"] = set_camera(target["body"], next_view)
    target["body"].set_component_tick_enabled(True)
    state["phase"] = "playing"


def case_diagnostics():
    diagnostics = []
    for actor_id in ("F02", "M02"):
        for expression in EXPRESSIONS:
            rows = [
                item
                for item in state["records"]
                if item["actor_id"] == actor_id
                and item["expression_id"] == expression["expression_id"]
            ]
            hallmark_spans = {}
            for curve in expression["hallmarks"]:
                values = [item["curves"][curve] for item in rows]
                hallmark_spans[curve] = max(values) - min(values) if values else 0.0
            maximum_pose_delta = 0.0
            if len(rows) >= 2:
                maximum_pose_delta = max(
                    pose_delta(rows[0]["pose"], item["pose"])
                    for item in rows[1:]
                )
            diagnostics.append(
                {
                    "actor_id": actor_id,
                    "expression_id": expression["expression_id"],
                    "sample_count": len(rows),
                    "hallmark_curve_spans": hallmark_spans,
                    "maximum_pose_delta_cm": maximum_pose_delta,
                    "body_animation_observed": maximum_pose_delta > 0.05,
                    "dynamic_expression_keys_present": any(
                        value > 0.002 for value in hallmark_spans.values()
                    ),
                }
            )
    return diagnostics


def finish(successful_execution):
    if state["finished"]:
        return
    state["finished"] = True
    for item in actors:
        item["actor"].set_actor_hidden_in_game(False)
        item["body"].set_component_tick_enabled(True)
    diagnostics = case_diagnostics()
    for item in diagnostics:
        if not item["body_animation_observed"]:
            state["errors"].append(
                f"Body animation not observed: {item['actor_id']}/"
                f"{item['expression_id']}"
            )
        if not item["dynamic_expression_keys_present"]:
            state["errors"].append(
                f"Expression variation not observed: {item['actor_id']}/"
                f"{item['expression_id']}"
            )
    expected = len(actors) * len(SAMPLE_SPECS)
    report = {
        "schema_version": 1,
        "runtime_scope": "body_animation_plus_direct_morph_expression",
        "case_count": len(actors),
        "sample_count": len(state["records"]),
        "expected_sample_count": expected,
        "records": state["records"],
        "diagnostics": diagnostics,
        "errors": state["errors"],
        "automatic_success": (
            successful_execution
            and len(state["records"]) == expected
            and not state["errors"]
        ),
        "visual_review": "pending",
        "production_status": "not_approved",
    }
    report["success"] = report["automatic_success"]
    write_report(report)
    handle = globals().get("_dm_first_batch_expression_review_callback")
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
    globals()["_dm_first_batch_expression_review_callback"] = None


def on_tick(delta_seconds):
    try:
        delta = max(0.0, min(float(delta_seconds), 0.10))
        world_time = float(unreal.GameplayStatics.get_time_seconds(game_world))
        last_world_time = state["last_world_time"]
        world_delta = (
            max(0.0, world_time - float(last_world_time))
            if last_world_time is not None
            else 0.0
        )
        state["last_world_time"] = world_time

        if state["phase"] == "waiting_instances":
            state["wait_ticks"] += 1
            if initialize_instances():
                return
            if state["wait_ticks"] > 300:
                raise RuntimeError("AnimInstances were not initialized")
            return
        if state["phase"] == "camera_settle":
            state["elapsed"] += delta
            if state["elapsed"] >= CAMERA_SETTLE_SECONDS:
                start_playback()
            return
        if state["phase"] == "playing":
            state["elapsed"] += world_delta
            target_seconds = SAMPLE_SPECS[state["sample_cursor"]][0]
            if state["elapsed"] >= target_seconds:
                capture_sample()
            return
    except Exception:
        state["errors"].append(traceback.format_exc())
        finish(False)


globals()["_dm_first_batch_expression_review_state"] = state
globals()["_dm_first_batch_expression_review_callback"] = (
    unreal.register_slate_post_tick_callback(on_tick)
)
print(
    "DM_FIRST_BATCH_EXPRESSION_REVIEW_STARTED="
    + json.dumps(
        {
            "actor_count": len(actors),
            "expected_sample_count": len(actors) * len(SAMPLE_SPECS),
            "report": str(REPORT_PATH),
            "success": True,
        },
        sort_keys=True,
    )
)
