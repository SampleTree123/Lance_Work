"""Run the F02/M02 P0 body-plus-face validation matrix in live PIE."""

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
    r"\p0_runtime_pilot_20260819_v1\runtime_review"
)
REPORT_PATH = OUTPUT_DIR / "pie_runtime_review.json"
CAMERA_SETTLE_SECONDS = 0.28
BODY_SETTLE_SECONDS = 0.60
CASE_TIMEOUT_SECONDS = 5.0
CURVE_NEUTRAL_TOLERANCE = 0.06
RUNTIME_BLINK_CAPTURE_MIN = 0.90

ACTOR_SPECS = (
    {
        "actor_id": "F02",
        "body_id": "walk",
        "body_index": 0,
        "label": "DM_P0_F02_Walk",
    },
    {
        "actor_id": "F02",
        "body_id": "idle",
        "body_index": 1,
        "label": "DM_P0_F02_Idle",
    },
    {
        "actor_id": "M02",
        "body_id": "walk",
        "body_index": 0,
        "label": "DM_P0_M02_Walk",
    },
    {
        "actor_id": "M02",
        "body_id": "understood",
        "body_index": 1,
        "label": "DM_P0_M02_Understood",
    },
)

BLINK_L = "CTRL_expressions_eyeBlinkL"
BLINK_R = "CTRL_expressions_eyeBlinkR"
SMILE_L = "CTRL_expressions_mouthCornerPullL"
SMILE_R = "CTRL_expressions_mouthCornerPullR"
WATCHED_CURVES = (
    BLINK_L,
    BLINK_R,
    SMILE_L,
    SMILE_R,
)

FACE_SPECS = (
    {
        "id": "neutral",
        "pair_index": 0,
        "variant_index": 0,
        "views": ("head_front", "full_front", "full_side"),
    },
    {
        "id": "natural_blink",
        "pair_index": 0,
        "variant_index": 1,
        "views": ("head_front",),
    },
    {
        "id": "asymmetric_blink",
        "pair_index": 1,
        "variant_index": 0,
        "views": ("head_front",),
    },
    {
        "id": "subtle_smile",
        "pair_index": 1,
        "variant_index": 1,
        "views": ("head_front",),
    },
)

POSE_BONES = ("head", "hand_l", "hand_r", "foot_l", "foot_r")


def unregister_previous_callback():
    handle = globals().get("_dm_p0_runtime_review_callback")
    if handle is None:
        return
    try:
        unreal.unregister_slate_post_tick_callback(handle)
    except Exception:
        pass
    globals()["_dm_p0_runtime_review_callback"] = None


def vector_record(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def quat_record(value):
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
        "w": float(value.w),
    }


def transform_record(value):
    return {
        "translation": vector_record(value.translation),
        "rotation": quat_record(value.rotation),
        "scale": vector_record(value.scale3d),
    }


def translation_distance(left, right):
    delta = left.translation - right.translation
    return math.sqrt(delta.x * delta.x + delta.y * delta.y + delta.z * delta.z)


def component_transform(component, bone):
    return component.get_socket_transform(
        unreal.Name(bone), unreal.RelativeTransformSpace.RTS_COMPONENT
    )


def capture_viewport(output_path):
    capture = unreal.get_default_object(unreal.EditorAppToolset).call_method(
        "CaptureViewport", (None, None, False)
    )
    image = capture.image
    if image.mime_type != "image/png" or not image.data:
        raise RuntimeError(
            f"Viewport capture failed: {image.mime_type!r}, {len(image.data)} bytes"
        )
    png_bytes = base64.b64decode(image.data)
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Viewport capture did not return a valid PNG")
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
            f"Expected one SkeletalMeshComponent on {actor.get_actor_label()}, "
            f"found {len(components)}"
        )
    return components[0]


def set_component_running(body, running):
    body.set_component_tick_enabled(bool(running))


def midpoint(left, right):
    return unreal.Vector(
        (left.x + right.x) * 0.5,
        (left.y + right.y) * 0.5,
        (left.z + right.z) * 0.5,
    )


def set_camera(body, view):
    head = body.get_socket_location(unreal.Name("head"))
    foot_l = body.get_socket_location(unreal.Name("foot_l"))
    foot_r = body.get_socket_location(unreal.Name("foot_r"))
    feet = midpoint(foot_l, foot_r)
    center = midpoint(head, feet) + unreal.Vector(0.0, 0.0, 5.0)
    height = max(150.0, abs(float(head.z - feet.z)) + 24.0)

    if view == "head_front":
        location = head + unreal.Vector(0.0, 67.0, 3.0)
        target = head + unreal.Vector(0.0, 0.0, 1.0)
    elif view == "head_three_quarter":
        location = head + unreal.Vector(43.0, 56.0, 4.0)
        target = head + unreal.Vector(0.0, 0.0, 1.0)
    elif view == "full_front":
        location = center + unreal.Vector(0.0, height * 1.65, 0.0)
        target = center
    elif view == "full_side":
        location = center + unreal.Vector(height * 1.65, 0.0, 0.0)
        target = center
    else:
        raise RuntimeError(f"Unknown camera view: {view}")

    rotation = unreal.MathLibrary.find_look_at_rotation(location, target)
    unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).set_level_viewport_camera_info(location, rotation)
    return {
        "location": vector_record(location),
        "rotation": {
            "pitch": float(rotation.pitch),
            "roll": float(rotation.roll),
            "yaw": float(rotation.yaw),
        },
        "target": vector_record(target),
        "view": view,
    }


def write_report(report):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def curve_values(instance):
    return {
        curve: float(instance.get_curve_value(curve)) for curve in WATCHED_CURVES
    }


def face_trigger_ready(face_id, curves, elapsed):
    if face_id == "neutral":
        return elapsed >= 0.25
    if face_id == "natural_blink":
        return (
            curves[BLINK_L] >= RUNTIME_BLINK_CAPTURE_MIN
            and curves[BLINK_R] >= RUNTIME_BLINK_CAPTURE_MIN
        )
    if face_id == "asymmetric_blink":
        return (
            curves[BLINK_L] >= RUNTIME_BLINK_CAPTURE_MIN
            and curves[BLINK_R] <= CURVE_NEUTRAL_TOLERANCE
        )
    if face_id == "subtle_smile":
        return curves[SMILE_L] >= 0.24 and curves[SMILE_R] >= 0.21
    raise RuntimeError(f"Unknown facial state: {face_id}")


def validate_face_state(face_id, curves):
    errors = []
    if face_id == "neutral":
        for curve, value in curves.items():
            if abs(value) > CURVE_NEUTRAL_TOLERANCE:
                errors.append(f"Neutral curve {curve}={value:.3f}")
    elif face_id == "natural_blink":
        if (
            curves[BLINK_L] < RUNTIME_BLINK_CAPTURE_MIN
            or curves[BLINK_R] < RUNTIME_BLINK_CAPTURE_MIN
        ):
            errors.append("Natural blink did not reach the required peak")
    elif face_id == "asymmetric_blink":
        if curves[BLINK_L] < RUNTIME_BLINK_CAPTURE_MIN:
            errors.append("Asymmetric blink did not close the left eyelid")
        if curves[BLINK_R] > CURVE_NEUTRAL_TOLERANCE:
            errors.append("Asymmetric blink unexpectedly closed the right eyelid")
    elif face_id == "subtle_smile":
        if curves[SMILE_L] < 0.24 or curves[SMILE_R] < 0.21:
            errors.append("Subtle smile did not reach the required plateau")
    return errors


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
        raise RuntimeError(
            f"{spec['label']} must disable its post-process Blueprint for "
            "FullReference direct-Morph validation"
        )
    actors.append(
        {
            **spec,
            "actor": actor,
            "body": body,
            "instance": None,
        }
    )

case_specs = [
    {"actor_cursor": actor_cursor, "face": face_spec}
    for actor_cursor in range(len(actors))
    for face_spec in FACE_SPECS
]

state = {
    "phase": "waiting_instances",
    "elapsed": 0.0,
    "last_world_time": None,
    "wait_ticks": 0,
    "case_cursor": 0,
    "view_cursor": 0,
    "current_record": None,
    "camera": None,
    "records": [],
    "body_snapshots": {},
    "errors": [],
    "finished": False,
}


def initialize_instances():
    for item in actors:
        body = item["body"]
        instance = body.get_anim_instance()
        if instance is None:
            return False
        for variable in ("BodyMotionIndex", "FacePairIndex", "FaceVariantIndex"):
            try:
                instance.get_editor_property(variable)
            except Exception as exc:
                raise RuntimeError(
                    f"{item['label']} AnimInstance lacks selector {variable}"
                ) from exc
        body.set_allow_anim_curve_evaluation(True)
        body.set_component_tick_enabled(True)
        body.set_enable_animation(True)
        instance.set_editor_property("BodyMotionIndex", item["body_index"])
        instance.set_editor_property("FacePairIndex", 0)
        instance.set_editor_property("FaceVariantIndex", 0)
        item["instance"] = instance
    state["elapsed"] = 0.0
    state["last_world_time"] = float(
        unreal.GameplayStatics.get_time_seconds(game_world)
    )
    state["phase"] = "body_settle"
    return True


def capture_body_snapshots():
    for item in actors:
        body = item["body"]
        mesh = body.get_skeletal_mesh_asset()
        missing_bones = [bone for bone in POSE_BONES if not body.does_socket_exist(bone)]
        if missing_bones:
            state["errors"].append(
                f"{item['label']} missing pose bones: {missing_bones}"
            )
        snapshot = {
            "actor_id": item["actor_id"],
            "body_id": item["body_id"],
            "body_index": item["body_index"],
            "anim_class": item["instance"].get_class().get_path_name(),
            "mesh": mesh.get_path_name() if mesh else None,
            "post_process_anim_blueprint": (
                mesh.get_editor_property("post_process_anim_blueprint").get_path_name()
                if mesh and mesh.get_editor_property("post_process_anim_blueprint")
                else None
            ),
            "disable_post_process_blueprint": bool(
                body.get_editor_property("disable_post_process_blueprint")
            ),
            "pose": {
                bone: transform_record(component_transform(body, bone))
                for bone in POSE_BONES
                if body.does_socket_exist(bone)
            },
            "selectors": {
                "BodyMotionIndex": int(
                    item["instance"].get_editor_property("BodyMotionIndex")
                ),
                "FacePairIndex": int(
                    item["instance"].get_editor_property("FacePairIndex")
                ),
                "FaceVariantIndex": int(
                    item["instance"].get_editor_property("FaceVariantIndex")
                ),
            },
        }
        state["body_snapshots"][item["label"]] = snapshot
        set_component_running(body, False)


def start_current_case():
    if state["case_cursor"] >= len(case_specs):
        finish(True)
        return
    case = case_specs[state["case_cursor"]]
    target = actors[case["actor_cursor"]]
    face = case["face"]
    for item in actors:
        item["actor"].set_actor_hidden_in_game(item is not target)
        set_component_running(item["body"], False)
    target["actor"].set_actor_hidden_in_game(False)
    target["instance"].set_editor_property("BodyMotionIndex", target["body_index"])
    target["instance"].set_editor_property("FacePairIndex", face["pair_index"])
    target["instance"].set_editor_property(
        "FaceVariantIndex", face["variant_index"]
    )
    set_component_running(target["body"], True)
    state["elapsed"] = 0.0
    state["last_world_time"] = float(
        unreal.GameplayStatics.get_time_seconds(game_world)
    )
    state["view_cursor"] = 0
    state["current_record"] = None
    state["phase"] = "case_playing"


def begin_capture():
    case = case_specs[state["case_cursor"]]
    target = actors[case["actor_cursor"]]
    face = case["face"]
    curves = curve_values(target["instance"])
    errors = validate_face_state(face["id"], curves)
    record = {
        "actor_id": target["actor_id"],
        "body_id": target["body_id"],
        "body_index": target["body_index"],
        "case_id": f"{target['actor_id'].lower()}_{target['body_id']}_{face['id']}",
        "face_id": face["id"],
        "runtime_curves": curves,
        "runtime_selectors": {
            "BodyMotionIndex": int(
                target["instance"].get_editor_property("BodyMotionIndex")
            ),
            "FacePairIndex": int(
                target["instance"].get_editor_property("FacePairIndex")
            ),
            "FaceVariantIndex": int(
                target["instance"].get_editor_property("FaceVariantIndex")
            ),
        },
        "trigger_elapsed_seconds": float(state["elapsed"]),
        "captures": {},
        "errors": errors,
    }
    state["errors"].extend(
        f"{record['case_id']}: {message}" for message in errors
    )
    state["current_record"] = record
    set_component_running(target["body"], False)
    first_view = face["views"][0]
    state["camera"] = set_camera(target["body"], first_view)
    state["elapsed"] = 0.0
    state["phase"] = "camera_settle"


def capture_current_view():
    case = case_specs[state["case_cursor"]]
    target = actors[case["actor_cursor"]]
    face = case["face"]
    view = face["views"][state["view_cursor"]]
    filename = (
        f"{target['actor_id'].lower()}__{target['body_id']}__"
        f"{face['id']}__{view}.png"
    )
    output_path = OUTPUT_DIR / filename
    state["current_record"]["captures"][view] = {
        "camera": state["camera"],
        "image": capture_viewport(output_path),
    }

    state["view_cursor"] += 1
    if state["view_cursor"] < len(face["views"]):
        next_view = face["views"][state["view_cursor"]]
        state["camera"] = set_camera(target["body"], next_view)
        state["elapsed"] = 0.0
        return

    state["records"].append(state["current_record"])
    target["instance"].set_editor_property("FacePairIndex", 0)
    target["instance"].set_editor_property("FaceVariantIndex", 0)
    set_component_running(target["body"], False)
    state["case_cursor"] += 1
    start_current_case()


def body_pose_comparisons():
    comparisons = []
    for actor_id in ("F02", "M02"):
        relevant = [
            value
            for value in state["body_snapshots"].values()
            if value["actor_id"] == actor_id
        ]
        if len(relevant) != 2:
            state["errors"].append(
                f"{actor_id}: expected two body snapshots, found {len(relevant)}"
            )
            continue
        left, right = sorted(relevant, key=lambda item: item["body_index"])
        distances = {}
        for bone in sorted(set(left["pose"]) & set(right["pose"])):
            left_translation = left["pose"][bone]["translation"]
            right_translation = right["pose"][bone]["translation"]
            distances[bone] = math.sqrt(
                (left_translation["x"] - right_translation["x"]) ** 2
                + (left_translation["y"] - right_translation["y"]) ** 2
                + (left_translation["z"] - right_translation["z"]) ** 2
            )
        maximum = max(distances.values(), default=0.0)
        different = maximum > 2.0
        if not different:
            state["errors"].append(
                f"{actor_id}: BodyMotionIndex did not produce a distinct pose"
            )
        comparisons.append(
            {
                "actor_id": actor_id,
                "body_ids": [left["body_id"], right["body_id"]],
                "bone_translation_deltas_cm": distances,
                "different_body_pose": different,
                "max_delta_cm": maximum,
            }
        )
    return comparisons


def finish(successful_execution):
    if state["finished"]:
        return
    state["finished"] = True
    for item in actors:
        item["actor"].set_actor_hidden_in_game(False)
        set_component_running(item["body"], True)
    complete = len(state["records"]) == len(case_specs)
    comparisons = body_pose_comparisons() if state["body_snapshots"] else []
    image_count = sum(len(item["captures"]) for item in state["records"])
    report = {
        "schema_version": 1,
        "runtime_scope": "full_reference_direct_morph",
        "facial_runtime_mode": "direct_morph_curves",
        "world": game_world.get_path_name(),
        "matrix_dimensions": {
            "actors": len(actors),
            "body_variants_per_identity": 2,
            "face_states": len(FACE_SPECS),
        },
        "case_count": len(state["records"]),
        "expected_case_count": len(case_specs),
        "image_count": image_count,
        "expected_image_count": 24,
        "body_snapshots": state["body_snapshots"],
        "body_pose_comparisons": comparisons,
        "records": state["records"],
        "errors": state["errors"],
        "automatic_success": (
            successful_execution
            and complete
            and image_count == 24
            and not state["errors"]
        ),
        "visual_review": "pending",
        "production_status": "not_approved",
    }
    report["success"] = report["automatic_success"]
    write_report(report)
    globals()["_dm_p0_runtime_review_result"] = report
    handle = globals().get("_dm_p0_runtime_review_callback")
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
    globals()["_dm_p0_runtime_review_callback"] = None


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
                raise RuntimeError(
                    "P0 AnimInstances were not initialized within 300 Slate ticks"
                )
            return

        if state["phase"] == "body_settle":
            state["elapsed"] += world_delta
            if state["elapsed"] >= BODY_SETTLE_SECONDS:
                capture_body_snapshots()
                start_current_case()
            return

        if state["phase"] == "case_playing":
            state["elapsed"] += world_delta
            case = case_specs[state["case_cursor"]]
            target = actors[case["actor_cursor"]]
            curves = curve_values(target["instance"])
            if face_trigger_ready(case["face"]["id"], curves, state["elapsed"]):
                begin_capture()
            elif state["elapsed"] > CASE_TIMEOUT_SECONDS:
                raise RuntimeError(
                    f"Facial state was not observed before timeout: "
                    f"{target['label']} + {case['face']['id']} + {curves}"
                )
            return

        if state["phase"] == "camera_settle":
            state["elapsed"] += delta
            if state["elapsed"] >= CAMERA_SETTLE_SECONDS:
                capture_current_view()
            return
    except Exception:
        state["errors"].append(traceback.format_exc())
        finish(False)


globals()["_dm_p0_runtime_review_state"] = state
globals()["_dm_p0_runtime_review_callback"] = (
    unreal.register_slate_post_tick_callback(on_tick)
)
print(
    "DM_P0_RUNTIME_REVIEW_STARTED="
    + json.dumps(
        {
            "actor_count": len(actors),
            "case_count": len(case_specs),
            "expected_image_count": 24,
            "report": str(REPORT_PATH),
            "success": True,
        },
        sort_keys=True,
    )
)
