"""Capture M02 Elder Morph age levels and expression safety in live PIE."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import struct
import traceback

import unreal


ACTOR_LABEL = "DM_M02_ElderMorphReview"
MORPH_NAME = "Full_Face_Elder"
OUTPUT_DIR = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_elder_morph_review_v001"
)
REPORT_PATH = OUTPUT_DIR / "pie_review.json"
SETTLE_SECONDS = 0.65
EXPECTED_COMPONENT_COUNT = 20
TOLERANCE = 0.06

NEUTRAL = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_Neutral_Loop_v001"
)
BLINK = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_NaturalBlink_Loop_v001"
)
SMILE = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_SubtleSmile_Loop_v001"
)
JAW_OPEN = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_JawOpen_Test_v001"
)

CASES = [
    {
        "id": "age_000_neutral",
        "age": 0.0,
        "animation": NEUTRAL,
        "sample_time": 0.0,
        "curves": [],
    },
    {
        "id": "age_050_neutral",
        "age": 0.5,
        "animation": NEUTRAL,
        "sample_time": 0.0,
        "curves": [],
    },
    {
        "id": "age_100_neutral",
        "age": 1.0,
        "animation": NEUTRAL,
        "sample_time": 0.0,
        "curves": [],
    },
    {
        "id": "age_100_blink",
        "age": 1.0,
        "animation": BLINK,
        "sample_time": 0.90,
        "curves": [
            "CTRL_expressions_eyeBlinkL",
            "CTRL_expressions_eyeBlinkR",
        ],
    },
    {
        "id": "age_100_smile",
        "age": 1.0,
        "animation": SMILE,
        "sample_time": 1.50,
        "curves": [
            "CTRL_expressions_mouthCornerPullL",
            "CTRL_expressions_mouthCornerPullR",
        ],
    },
    {
        "id": "age_100_jaw_open",
        "age": 1.0,
        "animation": JAW_OPEN,
        "sample_time": 1.50,
        "curves": ["CTRL_expressions_jawOpen"],
    },
]


def unregister_previous_callback():
    handle = globals().get("_dm_m02_elder_pie_review_callback")
    if handle is None:
        return
    try:
        unreal.unregister_slate_post_tick_callback(handle)
    except Exception:
        pass
    globals()["_dm_m02_elder_pie_review_callback"] = None


def morph_names(component):
    mesh = component.get_skeletal_mesh_asset()
    if mesh is None:
        return set()
    return {str(name) for name in mesh.get_all_morph_target_names()}


def apply_age(components, weight):
    for component in components:
        if MORPH_NAME in morph_names(component):
            component.set_morph_target(MORPH_NAME, weight, False)
            if hasattr(component, "mark_render_dynamic_data_dirty"):
                component.mark_render_dynamic_data_dirty()


def capture_viewport(toolset, output_path):
    capture = toolset.call_method("CaptureViewport", (None, None, False))
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


def write_report(report):
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


unregister_previous_callback()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if REPORT_PATH.exists():
    REPORT_PATH.unlink()
for case in CASES:
    output_path = OUTPUT_DIR / f"{case['id']}.png"
    if output_path.exists():
        output_path.unlink()

animations = {case["animation"]: unreal.load_asset(case["animation"]) for case in CASES}
if not all(isinstance(asset, unreal.AnimSequence) for asset in animations.values()):
    raise RuntimeError(f"Face review clip library is incomplete: {animations}")

editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = editor_subsystem.get_game_world()
if game_world is None:
    raise RuntimeError("PIE/Simulate world is not running")
actors = unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor)
actor = next((item for item in actors if item.get_actor_label() == ACTOR_LABEL), None)
if actor is None:
    raise RuntimeError(f"PIE review actor is unavailable: {ACTOR_LABEL}")

components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
if len(components) != EXPECTED_COMPONENT_COUNT:
    raise RuntimeError(
        f"Expected {EXPECTED_COMPONENT_COUNT} modular components, found {len(components)}"
    )
body = next((item for item in components if item.get_name() == "Body"), None)
if body is None:
    raise RuntimeError("PIE review actor has no Body component")

body.set_allow_anim_curve_evaluation(True)
body.set_component_tick_enabled(True)
body.set_enable_animation(True)
body.propagate_curves_to_followers = True
toolset = unreal.get_default_object(unreal.EditorAppToolset)

state = {
    "case_index": 0,
    "elapsed": 0.0,
    "records": [],
    "errors": [],
}


def start_case():
    case = CASES[state["case_index"]]
    animation = animations[case["animation"]]
    body.play_animation(animation, False)
    body.set_position(float(case["sample_time"]), False)
    body.stop()
    apply_age(components, float(case["age"]))
    state["elapsed"] = 0.0


def sample_case():
    case = CASES[state["case_index"]]
    animation = animations[case["animation"]]
    instance = body.get_anim_instance()
    if instance is None:
        raise RuntimeError("Body AnimSingleNode instance is unavailable")

    age_support = []
    age_errors = []
    for component in components:
        if MORPH_NAME not in morph_names(component):
            continue
        age_support.append(component.get_name())
        actual = float(component.get_morph_target(MORPH_NAME))
        if abs(actual - float(case["age"])) > 1.0e-5:
            age_errors.append(
                f"{component.get_name()} age={actual}, requested={case['age']}"
            )

    runtime_curves = {
        curve: float(instance.get_curve_value(curve)) for curve in case["curves"]
    }
    expected_curves = {
        curve: float(
            unreal.AnimationLibrary.get_float_value_at_time(
                animation, curve, float(case["sample_time"])
            )
        )
        for curve in case["curves"]
    }
    curve_errors = [
        f"{curve}: runtime={runtime_curves[curve]:.3f}, "
        f"expected={expected_curves[curve]:.3f}"
        for curve in case["curves"]
        if abs(runtime_curves[curve] - expected_curves[curve]) > TOLERANCE
    ]
    output_path = OUTPUT_DIR / f"{case['id']}.png"
    record = {
        "age": case["age"],
        "age_support": sorted(age_support),
        "animation": animation.get_path_name(),
        "capture": capture_viewport(toolset, output_path),
        "curve_errors": curve_errors,
        "expected_curves": expected_curves,
        "id": case["id"],
        "runtime_curves": runtime_curves,
        "sample_time_seconds": case["sample_time"],
        "weight_errors": age_errors,
    }
    state["records"].append(record)
    state["errors"].extend(f"{case['id']}: {item}" for item in age_errors)
    state["errors"].extend(f"{case['id']}: {item}" for item in curve_errors)


def finish(successful_execution):
    support_sets = [set(item["age_support"]) for item in state["records"]]
    consistent_support = len({tuple(sorted(item)) for item in support_sets}) <= 1
    if not consistent_support:
        state["errors"].append("Age Morph component support changed between cases")
    report = {
        "schema_version": 1,
        "actor": actor.get_path_name(),
        "actor_component_count": len(components),
        "case_count": len(state["records"]),
        "cases": state["records"],
        "component_support_consistent": consistent_support,
        "errors": state["errors"],
        "morph_name": MORPH_NAME,
        "propagate_curves_to_followers": body.propagate_curves_to_followers,
        "runtime_world": game_world.get_path_name(),
        "success": (
            successful_execution
            and len(state["records"]) == len(CASES)
            and not state["errors"]
        ),
    }
    write_report(report)
    globals()["_dm_m02_elder_pie_review_result"] = report


def on_tick(delta_seconds):
    try:
        state["elapsed"] += float(delta_seconds)
        if state["elapsed"] < SETTLE_SECONDS:
            return
        sample_case()
        state["case_index"] += 1
        if state["case_index"] < len(CASES):
            start_case()
            return
        finish(True)
        unreal.unregister_slate_post_tick_callback(
            globals()["_dm_m02_elder_pie_review_callback"]
        )
        globals()["_dm_m02_elder_pie_review_callback"] = None
    except Exception:
        state["errors"].append(traceback.format_exc())
        finish(False)
        handle = globals().get("_dm_m02_elder_pie_review_callback")
        if handle is not None:
            unreal.unregister_slate_post_tick_callback(handle)
        globals()["_dm_m02_elder_pie_review_callback"] = None


start_case()
globals()["_dm_m02_elder_pie_review_state"] = state
globals()["_dm_m02_elder_pie_review_callback"] = (
    unreal.register_slate_post_tick_callback(on_tick)
)
print(
    "DM_ELDER_PIE_REVIEW_STARTED="
    + json.dumps(
        {"case_count": len(CASES), "report": str(REPORT_PATH), "success": True},
        sort_keys=True,
    )
)
