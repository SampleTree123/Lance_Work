"""Validate one shared hybrid face clip over two Body-only motions in PIE."""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path
import struct
import traceback

import unreal


TEST_ANIM_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003"
)
CONTROL_ANIM_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "ABP_DM_M02_BodyFaceLayer_v003_ControlNeutral"
)
HYBRID_FACE_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_HybridSupport_Loop_v001"
)
OUTPUT_DIR = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_face_hybrid_review_v003"
)
REPORT_PATH = OUTPUT_DIR / "pie_review.json"
EXPECTED_COMPONENT_COUNT = 20
CURVE_TOLERANCE = 0.16
HEAD_TRANSLATION_TOLERANCE_CM = 0.40
HEAD_ROTATION_TOLERANCE_DEG = 0.75
CAMERA_SETTLE_SECONDS = 0.40

PAIR_SPECS = (
    {
        "body_index": 0,
        "body_id": "audience",
        "test_label": "DM_M02_FaceHybridTest_Audience_v003",
        "control_label": "DM_M02_FaceHybridControl_Audience_v003",
    },
    {
        "body_index": 1,
        "body_id": "walk_wander",
        "test_label": "DM_M02_FaceHybridTest_Walk_v003",
        "control_label": "DM_M02_FaceHybridControl_Walk_v003",
    },
)
HEAD_NECK_BONES = ("neck_01", "neck_02", "head")
POSE_BONES = ("hand_l", "hand_r", "head")
SUPPORT_BONES = (
    "cc_base_facialbone",
    "cc_base_jawroot",
    "cc_base_upperjaw",
    "cc_base_teeth01",
    "cc_base_teeth02",
    "cc_base_tongue01",
    "cc_base_tongue02",
    "cc_base_tongue03",
    "cc_base_l_eye",
    "cc_base_r_eye",
)
CURVES = (
    "CTRL_expressions_eyeBlinkL",
    "CTRL_expressions_eyeBlinkR",
    "CTRL_expressions_jawOpen",
    "CTRL_expressions_mouthLowerLipDepressL",
    "CTRL_expressions_mouthLowerLipDepressR",
    "CTRL_expressions_mouthUpperLipRaiseL",
    "CTRL_expressions_mouthUpperLipRaiseR",
    "CTRL_expressions_mouthCornerPullL",
    "CTRL_expressions_mouthCornerPullR",
    "CTRL_expressions_eyeLookRightL",
    "CTRL_expressions_eyeLookRightR",
)


def unregister_previous_callback():
    handle = globals().get("_dm_m02_face_hybrid_review_callback")
    if handle is None:
        return
    try:
        unreal.unregister_slate_post_tick_callback(handle)
    except Exception:
        pass
    globals()["_dm_m02_face_hybrid_review_callback"] = None


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
        "height": height,
        "path": str(output_path),
        "width": width,
    }


def vector_record(value):
    return {"x": value.x, "y": value.y, "z": value.z}


def quat_record(value):
    return {"x": value.x, "y": value.y, "z": value.z, "w": value.w}


def transform_record(value):
    return {
        "translation": vector_record(value.translation),
        "rotation": quat_record(value.rotation),
        "scale": vector_record(value.scale3d),
    }


def translation_distance(left, right):
    delta = left.translation - right.translation
    return math.sqrt(delta.x * delta.x + delta.y * delta.y + delta.z * delta.z)


def rotation_distance_degrees(left, right):
    return math.degrees(left.rotation.angular_distance(right.rotation))


def component_transform(component, bone):
    return component.get_socket_transform(
        unreal.Name(bone), unreal.RelativeTransformSpace.RTS_COMPONENT
    )


def morph_names(component):
    mesh = component.get_skeletal_mesh_asset()
    if mesh is None:
        return set()
    return {str(name) for name in mesh.get_all_morph_target_names()}


def find_actor(world, label):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    actor = next((item for item in actors if item.get_actor_label() == label), None)
    if actor is None:
        raise RuntimeError(f"PIE actor unavailable: {label}")
    return actor


def find_body(actor):
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    body = next((item for item in components if item.get_name() == "Body"), None)
    if body is None:
        raise RuntimeError(f"PIE actor has no Body component: {actor.get_actor_label()}")
    if len(components) != EXPECTED_COMPONENT_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_COMPONENT_COUNT} components on "
            f"{actor.get_actor_label()}, found {len(components)}"
        )
    return components, body


def set_rate(body, rate):
    # Editor-property writes reconstruct modular SkeletalMeshComponents in UE 5.8.
    # Pausing the component tick preserves the last evaluated pose without that reset.
    body.set_component_tick_enabled(float(rate) > 0.0)


def set_camera(body, view):
    head = body.get_socket_location(unreal.Name("head"))
    offset = (
        unreal.Vector(38.0, 50.0, 2.0)
        if view == "three_quarter"
        else unreal.Vector(0.0, 58.0, 2.0)
    )
    location = head + offset
    target = head + unreal.Vector(0.0, 0.0, 1.0)
    rotation = unreal.MathLibrary.find_look_at_rotation(location, target)
    unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).set_level_viewport_camera_info(location, rotation)
    return {
        "location": vector_record(location),
        "rotation": {
            "pitch": rotation.pitch,
            "yaw": rotation.yaw,
            "roll": rotation.roll,
        },
        "view": view,
    }


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

test_anim_bp = unreal.load_asset(TEST_ANIM_BLUEPRINT)
control_anim_bp = unreal.load_asset(CONTROL_ANIM_BLUEPRINT)
hybrid_face = unreal.load_asset(HYBRID_FACE_ANIMATION)
if not isinstance(test_anim_bp, unreal.AnimBlueprint):
    raise RuntimeError(f"Test AnimBlueprint unavailable: {TEST_ANIM_BLUEPRINT}")
if not isinstance(control_anim_bp, unreal.AnimBlueprint):
    raise RuntimeError(f"Control AnimBlueprint unavailable: {CONTROL_ANIM_BLUEPRINT}")
if not isinstance(hybrid_face, unreal.AnimSequence):
    raise RuntimeError(f"Hybrid face clip unavailable: {HYBRID_FACE_ANIMATION}")
if test_anim_bp.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
    raise RuntimeError(f"Test AnimBlueprint compile status is {test_anim_bp.get_editor_property('status')}")

play_length = float(hybrid_face.get_play_length())
face_specs = (
    {"id": "neutral_front", "sample_time": 0.30, "view": "front"},
    {"id": "blink_front", "sample_time": 0.88, "view": "front"},
    {"id": "jaw_front", "sample_time": 1.70, "view": "front"},
    {"id": "jaw_three_quarter", "sample_time": 1.70, "view": "three_quarter"},
    {
        "id": "gaze_opposite_front",
        "sample_time": play_length * 0.75,
        "view": "front",
    },
)

game_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if game_world is None:
    raise RuntimeError("PIE/Simulate world is not running")

pairs = []
for spec in PAIR_SPECS:
    test_actor = find_actor(game_world, spec["test_label"])
    control_actor = find_actor(game_world, spec["control_label"])
    test_components, test_body = find_body(test_actor)
    control_components, control_body = find_body(control_actor)
    pairs.append(
        {
            **spec,
            "test_actor": test_actor,
            "control_actor": control_actor,
            "test_components": test_components,
            "control_components": control_components,
            "test_body": test_body,
            "control_body": control_body,
            "test_instance": None,
            "control_instance": None,
        }
    )

followers_without_body_leader = []
for pair in pairs:
    for role in ("test", "control"):
        body = pair[f"{role}_body"]
        for component in pair[f"{role}_components"]:
            if component == body:
                continue
            if component.get_editor_property("leader_pose_component") != body:
                followers_without_body_leader.append(
                    f"{pair['body_id']}:{role}:{component.get_name()}"
                )

curve_support = {
    curve: sorted(
        component.get_name()
        for component in pairs[0]["test_components"]
        if curve in morph_names(component)
    )
    for curve in CURVES
}

state = {
    "face_index": 0,
    "body_cursor": 0,
    "elapsed": 0.0,
    "camera_elapsed": 0.0,
    "instance_wait_ticks": 0,
    "phase": "waiting_instances",
    "camera": None,
    "records": [],
    "errors": [],
    "last_world_time": None,
}


def assign_anim_classes_once():
    test_class = test_anim_bp.generated_class()
    control_class = control_anim_bp.generated_class()
    for pair in pairs:
        for role, anim_class in (
            ("test", test_class),
            ("control", control_class),
        ):
            body = pair[f"{role}_body"]
            body.set_allow_anim_curve_evaluation(True)
            body.set_component_tick_enabled(True)
            body.set_enable_animation(True)
            body.propagate_curves_to_followers = True
            if body.get_editor_property("animation_mode") != unreal.AnimationMode.ANIMATION_BLUEPRINT:
                body.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
            # Clear first because assigning the same v002 class is otherwise a no-op.
            body.set_anim_instance_class(None)
            body.set_anim_instance_class(anim_class)


def try_initialize_instances():
    test_class = test_anim_bp.generated_class()
    control_class = control_anim_bp.generated_class()
    for pair in pairs:
        test_instance = pair["test_body"].get_anim_instance()
        control_instance = pair["control_body"].get_anim_instance()
        if test_instance is None or control_instance is None:
            return False
        if test_instance.get_class() != test_class:
            return False
        if control_instance.get_class() != control_class:
            return False
        pair["test_instance"] = test_instance
        pair["control_instance"] = control_instance

    for pair in pairs:
        set_rate(pair["test_body"], 1.0)
        set_rate(pair["control_body"], 1.0)
        pair["test_instance"].set_editor_property(
            "BodyMotionIndex", pair["body_index"]
        )
        pair["control_instance"].set_editor_property(
            "BodyMotionIndex", pair["body_index"]
        )
    state["elapsed"] = 0.0
    state["last_world_time"] = float(
        unreal.GameplayStatics.get_time_seconds(game_world)
    )
    state["phase"] = "playing"
    return True


def freeze_all_and_frame_first():
    for pair in pairs:
        set_rate(pair["test_body"], 0.0)
        set_rate(pair["control_body"], 0.0)
    state["body_cursor"] = 0
    state["camera"] = set_camera(
        pairs[0]["test_body"], face_specs[state["face_index"]]["view"]
    )
    state["camera_elapsed"] = 0.0
    state["phase"] = "camera_settle"


def unfreeze_all():
    for pair in pairs:
        set_rate(pair["test_body"], 1.0)
        set_rate(pair["control_body"], 1.0)
    state["last_world_time"] = float(
        unreal.GameplayStatics.get_time_seconds(game_world)
    )


def face_trigger_ready():
    face_id = face_specs[state["face_index"]]["id"]
    if face_id == "neutral_front":
        return state["elapsed"] >= 0.30
    if face_id == "blink_front":
        return all(
            float(pair["test_instance"].get_curve_value(BLINK)) >= 0.85
            for pair in pairs
            for BLINK in ("CTRL_expressions_eyeBlinkL", "CTRL_expressions_eyeBlinkR")
        )
    if face_id in {"jaw_front", "jaw_three_quarter"}:
        return all(
            float(pair["test_instance"].get_curve_value("CTRL_expressions_jawOpen"))
            >= 0.50
            for pair in pairs
        )
    if face_id == "gaze_opposite_front":
        return all(
            float(pair["test_instance"].get_curve_value(curve)) >= 0.60
            for pair in pairs
            for curve in (
                "CTRL_expressions_eyeLookRightL",
                "CTRL_expressions_eyeLookRightR",
            )
        )
    raise RuntimeError(f"Unknown facial review state: {face_id}")


def sample_current_body():
    face_spec = face_specs[state["face_index"]]
    pair = pairs[state["body_cursor"]]
    sample_time = float(face_spec["sample_time"])
    test_instance = pair["test_instance"]
    control_instance = pair["control_instance"]

    runtime_curves = {
        curve: float(test_instance.get_curve_value(curve)) for curve in CURVES
    }
    control_curves = {
        curve: float(control_instance.get_curve_value(curve)) for curve in CURVES
    }
    expected_curves = {
        curve: float(
            unreal.AnimationLibrary.get_float_value_at_time(
                hybrid_face, curve, sample_time
            )
        )
        for curve in CURVES
    }
    curve_deltas = {
        curve: abs(runtime_curves[curve] - expected_curves[curve])
        for curve in CURVES
    }
    errors = [
        f"Curve mismatch {curve}: runtime={runtime_curves[curve]:.3f}, "
        f"expected={expected_curves[curve]:.3f}"
        for curve in CURVES
        if curve_deltas[curve] > CURVE_TOLERANCE
    ]
    errors.extend(
        f"Control curve is not neutral {curve}={value:.3f}"
        for curve, value in control_curves.items()
        if abs(value) > 0.05
    )

    head_neck = {}
    for bone in HEAD_NECK_BONES:
        test_transform = component_transform(pair["test_body"], bone)
        control_transform = component_transform(pair["control_body"], bone)
        translation_delta = translation_distance(test_transform, control_transform)
        rotation_delta = rotation_distance_degrees(test_transform, control_transform)
        head_neck[bone] = {
            "test": transform_record(test_transform),
            "control": transform_record(control_transform),
            "translation_delta_cm": translation_delta,
            "rotation_delta_degrees": rotation_delta,
        }
        if translation_delta > HEAD_TRANSLATION_TOLERANCE_CM:
            errors.append(f"{bone} translation changed by {translation_delta:.3f} cm")
        if rotation_delta > HEAD_ROTATION_TOLERANCE_DEG:
            errors.append(f"{bone} rotation changed by {rotation_delta:.3f} degrees")

    support_deltas = {}
    for bone in SUPPORT_BONES:
        test_transform = component_transform(pair["test_body"], bone)
        control_transform = component_transform(pair["control_body"], bone)
        support_deltas[bone] = {
            "translation_delta_cm": translation_distance(
                test_transform, control_transform
            ),
            "rotation_delta_degrees": rotation_distance_degrees(
                test_transform, control_transform
            ),
        }

    if face_spec["id"] == "blink_front":
        for curve in (
            "CTRL_expressions_eyeBlinkL",
            "CTRL_expressions_eyeBlinkR",
        ):
            if runtime_curves[curve] < 0.84:
                errors.append(f"Blink peak is too low: {curve}={runtime_curves[curve]:.3f}")
    if face_spec["id"] in {"jaw_front", "jaw_three_quarter"}:
        if runtime_curves["CTRL_expressions_jawOpen"] < 0.50:
            errors.append("Jaw-open Morph curve did not reach its plateau")
        if support_deltas["cc_base_jawroot"]["rotation_delta_degrees"] < 12.0:
            errors.append("Jaw support bone did not reach the expected rotation")
        if support_deltas["cc_base_tongue02"]["rotation_delta_degrees"] < 2.5:
            errors.append("Tongue support bone did not reach the expected rotation")
        if support_deltas["cc_base_teeth02"]["rotation_delta_degrees"] < 12.0:
            errors.append("Lower teeth did not follow the jaw support branch")
    if face_spec["id"] == "gaze_opposite_front":
        for bone in ("cc_base_l_eye", "cc_base_r_eye"):
            if support_deltas[bone]["rotation_delta_degrees"] < 5.0:
                errors.append(f"Eye support bone did not reach gaze extreme: {bone}")

    pose_signature = {
        bone: transform_record(component_transform(pair["test_body"], bone))
        for bone in POSE_BONES
    }
    output_path = OUTPUT_DIR / f"{pair['body_id']}__{face_spec['id']}.png"
    record = {
        "body_index": pair["body_index"],
        "body_id": pair["body_id"],
        **face_spec,
        "actual_elapsed_seconds": state["elapsed"],
        "camera": state["camera"],
        "capture": capture_viewport(output_path),
        "control_curves": control_curves,
        "curve_deltas": curve_deltas,
        "errors": errors,
        "expected_curves": expected_curves,
        "head_neck_comparison": head_neck,
        "pose_signature": pose_signature,
        "runtime_curves": runtime_curves,
        "runtime_selectors": {
            "test_BodyMotionIndex": test_instance.get_editor_property(
                "BodyMotionIndex"
            ),
            "control_BodyMotionIndex": control_instance.get_editor_property(
                "BodyMotionIndex"
            ),
        },
        "support_bone_deltas": support_deltas,
    }
    state["records"].append(record)
    state["errors"].extend(
        f"{pair['body_id']}+{face_spec['id']}: {message}" for message in errors
    )


def body_pose_comparisons():
    comparisons = []
    for face_spec in face_specs:
        audience = next(
            item
            for item in state["records"]
            if item["body_id"] == "audience" and item["id"] == face_spec["id"]
        )
        walk = next(
            item
            for item in state["records"]
            if item["body_id"] == "walk_wander" and item["id"] == face_spec["id"]
        )
        distances = {}
        for bone in POSE_BONES:
            left = audience["pose_signature"][bone]["translation"]
            right = walk["pose_signature"][bone]["translation"]
            distances[bone] = math.sqrt(
                (left["x"] - right["x"]) ** 2
                + (left["y"] - right["y"]) ** 2
                + (left["z"] - right["z"]) ** 2
            )
        maximum = max(distances.values(), default=0.0)
        if maximum <= 2.0:
            state["errors"].append(
                f"Body selector did not change the pose for {face_spec['id']}"
            )
        comparisons.append(
            {
                "face_state": face_spec["id"],
                "bone_translation_deltas_cm": distances,
                "max_delta_cm": maximum,
                "different_body_pose": maximum > 2.0,
            }
        )
    return comparisons


def finish(successful_execution):
    if followers_without_body_leader:
        state["errors"].append(
            "Followers without Body leader: "
            + ", ".join(followers_without_body_leader)
        )
    for pair in pairs:
        if not pair["test_body"].propagate_curves_to_followers:
            state["errors"].append(
                f"Curve propagation disabled for {pair['body_id']} test"
            )
    complete = len(state["records"]) == len(face_specs) * len(pairs)
    comparisons = body_pose_comparisons() if complete else []
    report = {
        "schema_version": 2,
        "test_anim_blueprint": test_anim_bp.get_path_name(),
        "test_compile_status": str(test_anim_bp.get_editor_property("status")),
        "control_anim_blueprint": control_anim_bp.get_path_name(),
        "hybrid_face_animation": hybrid_face.get_path_name(),
        "play_length_seconds": play_length,
        "world": game_world.get_path_name(),
        "matrix_dimensions": {"body": len(pairs), "face_state": len(face_specs)},
        "case_count": len(state["records"]),
        "component_count_per_actor": EXPECTED_COMPONENT_COUNT,
        "follower_count_per_actor": EXPECTED_COMPONENT_COUNT - 1,
        "followers_without_body_leader": followers_without_body_leader,
        "curve_support": curve_support,
        "head_neck_tolerance": {
            "translation_cm": HEAD_TRANSLATION_TOLERANCE_CM,
            "rotation_degrees": HEAD_ROTATION_TOLERANCE_DEG,
        },
        "records": state["records"],
        "body_pose_comparisons": comparisons,
        "errors": state["errors"],
        "success": successful_execution and complete and not state["errors"],
    }
    write_report(report)
    globals()["_dm_m02_face_hybrid_review_result"] = report


def advance_after_capture():
    state["body_cursor"] += 1
    if state["body_cursor"] < len(pairs):
        state["camera"] = set_camera(
            pairs[state["body_cursor"]]["test_body"],
            face_specs[state["face_index"]]["view"],
        )
        state["camera_elapsed"] = 0.0
        return

    current_time = float(face_specs[state["face_index"]]["sample_time"])
    state["face_index"] += 1
    if state["face_index"] >= len(face_specs):
        finish(True)
        unreal.unregister_slate_post_tick_callback(
            globals()["_dm_m02_face_hybrid_review_callback"]
        )
        globals()["_dm_m02_face_hybrid_review_callback"] = None
        return

    next_spec = face_specs[state["face_index"]]
    state["body_cursor"] = 0
    if abs(float(next_spec["sample_time"]) - current_time) < 1.0e-4:
        state["camera"] = set_camera(pairs[0]["test_body"], next_spec["view"])
        state["camera_elapsed"] = 0.0
        return
    unfreeze_all()
    state["phase"] = "playing"


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
            state["instance_wait_ticks"] += 1
            if try_initialize_instances():
                return
            if state["instance_wait_ticks"] > 300:
                raise RuntimeError(
                    "AnimInstances were not initialized within 300 Slate ticks"
                )
            return
        if state["phase"] == "playing":
            state["elapsed"] += world_delta
            if face_trigger_ready():
                freeze_all_and_frame_first()
            elif state["elapsed"] > play_length + 0.50:
                raise RuntimeError(
                    "Facial review state was not observed before timeout: "
                    + face_specs[state["face_index"]]["id"]
                )
            return

        state["camera_elapsed"] += delta
        if state["camera_elapsed"] < CAMERA_SETTLE_SECONDS:
            return
        sample_current_body()
        advance_after_capture()
    except Exception:
        state["errors"].append(traceback.format_exc())
        finish(False)
        handle = globals().get("_dm_m02_face_hybrid_review_callback")
        if handle is not None:
            unreal.unregister_slate_post_tick_callback(handle)
        globals()["_dm_m02_face_hybrid_review_callback"] = None


globals()["_dm_m02_face_hybrid_review_state"] = state
assign_anim_classes_once()
globals()["_dm_m02_face_hybrid_review_callback"] = (
    unreal.register_slate_post_tick_callback(on_tick)
)
print(
    "DM_FACE_HYBRID_REVIEW_STARTED="
    + json.dumps(
        {
            "actor_count": len(pairs) * 2,
            "case_count": len(face_specs) * len(pairs),
            "report": str(REPORT_PATH),
            "success": True,
        },
        sort_keys=True,
    )
)
