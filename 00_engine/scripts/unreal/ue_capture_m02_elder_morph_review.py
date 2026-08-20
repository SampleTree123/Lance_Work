"""Stage or capture one M02 Elder Morph review case in a running editor.

The local orchestrator invokes this file twice per case. Returning to the editor
between the stage and capture calls gives the render thread a real viewport tick;
capturing several Morph states inside one remote command produces stale frames.
"""

import base64
import json
from pathlib import Path
import struct

import unreal


BLUEPRINT_PATH = (
    "/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/"
    "BP_DM_M02_ElderMorphPilot_v001"
)
BODY_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "A_CC_Walk_Wander_M_BodyOnly_v001"
)
ACTOR_LABEL = "DM_M02_ElderMorphReview"
MORPH_NAME = "Full_Face_Elder"
OUTPUT_DIR = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_elder_morph_review_v001"
)
REQUEST_PATH = OUTPUT_DIR / "request.json"
REPORT_PATH = OUTPUT_DIR / "review.json"
ACTOR_LOCATION = [5000.0, 5000.0, 0.0]
ACTOR_ROTATION = [0.0, 0.0, 0.0]
CAMERA_DISTANCE_CM = 42.0
CAMERA_ROTATION = [0.0, -90.0, 0.0]
EXPECTED_COMPONENT_COUNT = 20
TOLERANCE = 1.0e-5


def vector(values):
    return unreal.Vector(float(values[0]), float(values[1]), float(values[2]))


def rotator(values):
    return unreal.Rotator(
        pitch=float(values[0]),
        yaw=float(values[1]),
        roll=float(values[2]),
    )


def object_path(value):
    return value.get_path_name() if value is not None else None


def morph_names(component):
    mesh = component.get_skeletal_mesh_asset()
    if mesh is None:
        return set()
    return {str(name) for name in mesh.get_all_morph_target_names()}


def refresh_component(component):
    if hasattr(component, "tick_animation"):
        component.tick_animation(0.0, False)
    if hasattr(component, "refresh_bone_transforms"):
        component.refresh_bone_transforms()
    if hasattr(component, "mark_render_dynamic_data_dirty"):
        component.mark_render_dynamic_data_dirty()
    if hasattr(component, "mark_render_state_dirty"):
        component.mark_render_state_dirty()


def find_review_actors(actor_subsystem):
    return [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor.get_actor_label() == ACTOR_LABEL
    ]


def destroy_review_actors(actor_subsystem):
    removed = []
    for actor in find_review_actors(actor_subsystem):
        removed.append(actor.get_path_name())
        actor_subsystem.destroy_actor(actor)
    return removed


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


def read_request():
    if not REQUEST_PATH.is_file():
        raise RuntimeError(f"Review request is unavailable: {REQUEST_PATH}")
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    operation = str(request.get("operation", ""))
    if operation not in {"stage", "capture", "cleanup"}:
        raise RuntimeError(f"Unsupported review operation: {operation!r}")
    return request


def initialize_output(request):
    if not request.get("reset_output", False):
        return
    for existing_png in OUTPUT_DIR.glob("*.png"):
        existing_png.unlink()
    for stage_report in OUTPUT_DIR.glob("stage_*.json"):
        stage_report.unlink()
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()


def apply_morph(actor, components, morph_name, weight):
    # The Blueprint broadcaster covers the standard face set. The explicit pass
    # also reaches generated hair and beard meshes carrying the Elder target.
    actor.call_method("BroadcastFaceMorph", (morph_name, weight, False))
    for component in components:
        if morph_name in morph_names(component):
            component.set_morph_target(morph_name, weight, False)


def stage_case(request, actor_subsystem):
    case = request["case"]
    case_id = str(case["id"])
    age = float(case["age"])
    expressions = {
        str(name): float(weight)
        for name, weight in case.get("expressions", {}).items()
    }
    all_expression_morphs = [
        str(name) for name in request.get("all_expression_morphs", [])
    ]

    initialize_output(request)
    removed_previous = destroy_review_actors(actor_subsystem)

    blueprint_path = str(request.get("blueprint_path", BLUEPRINT_PATH))
    blueprint = unreal.load_asset(blueprint_path)
    animation = unreal.load_asset(BODY_ANIMATION)
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"Review Blueprint is unavailable: {blueprint_path}")
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(f"Body animation is unavailable: {BODY_ANIMATION}")

    actor = actor_subsystem.spawn_actor_from_class(
        blueprint.generated_class(),
        vector(ACTOR_LOCATION),
        rotator(ACTOR_ROTATION),
        transient=False,
    )
    if actor is None:
        raise RuntimeError("Unable to spawn Elder Morph review actor")
    actor.set_actor_label(ACTOR_LABEL)

    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    if len(components) != EXPECTED_COMPONENT_COUNT:
        actor_subsystem.destroy_actor(actor)
        raise RuntimeError(
            f"Expected {EXPECTED_COMPONENT_COUNT} modular components, "
            f"found {len(components)}"
        )
    body = next((item for item in components if item.get_name() == "Body"), None)
    if body is None:
        actor_subsystem.destroy_actor(actor)
        raise RuntimeError("Elder Morph review actor has no Body component")

    body.set_update_animation_in_editor(True)
    body.set_allow_anim_curve_evaluation(True)
    body.propagate_curves_to_followers = True
    body.override_animation_data(animation, False, False, 0.0, 1.0)
    body.play_animation(animation, False)
    body.set_position(0.0, False)
    body.stop()

    # Animation setup can reconstruct editor components.
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    body = next((item for item in components if item.get_name() == "Body"), None)
    if body is None or body.get_bone_index("head") < 0:
        actor_subsystem.destroy_actor(actor)
        raise RuntimeError("Body or head bone is unavailable after animation setup")

    validate_age = bool(request.get("validate_age", True))
    apply_morph(actor, components, MORPH_NAME, 0.0)
    for expression_name in all_expression_morphs:
        apply_morph(actor, components, expression_name, 0.0)
    if validate_age:
        apply_morph(actor, components, MORPH_NAME, age)
    for expression_name, weight in expressions.items():
        apply_morph(actor, components, expression_name, weight)
    for component in components:
        refresh_component(component)

    head_location = body.get_bone_transform("head").translation
    camera_location = [
        float(head_location.x),
        float(head_location.y + CAMERA_DISTANCE_CM),
        float(head_location.z + 2.0),
    ]
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    editor_subsystem.set_level_viewport_camera_info(
        vector(camera_location), rotator(CAMERA_ROTATION)
    )
    actor_subsystem.set_selected_level_actors([])

    component_records = []
    for component in components:
        component_morphs = morph_names(component)
        leader = component.get_editor_property("leader_pose_component")
        component_records.append(
            {
                "leader": leader.get_name() if leader is not None else None,
                "mesh": object_path(component.get_skeletal_mesh_asset()),
                "name": component.get_name(),
                "supports_age": MORPH_NAME in component_morphs,
                "age_weight": float(component.get_morph_target(MORPH_NAME)),
                "expressions": {
                    name: {
                        "supports": name in component_morphs,
                        "weight": float(component.get_morph_target(name)),
                    }
                    for name in expressions
                },
            }
        )

    stage_report = {
        "actor": actor.get_path_name(),
        "age": age,
        "blueprint": blueprint_path,
        "camera_location": camera_location,
        "camera_rotation": CAMERA_ROTATION,
        "case_id": case_id,
        "component_count": len(components),
        "components": sorted(component_records, key=lambda item: item["name"]),
        "expressions": expressions,
        "removed_previous": removed_previous,
    }
    stage_path = OUTPUT_DIR / f"stage_{case_id}.json"
    stage_path.write_text(
        json.dumps(stage_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "DM_ELDER_MORPH_STAGED="
        + json.dumps(
            {
                "case_id": case_id,
                "component_count": len(components),
                "stage_report": str(stage_path),
            },
            sort_keys=True,
        )
    )


def capture_case(request, actor_subsystem):
    case = request["case"]
    case_id = str(case["id"])
    age = float(case["age"])
    expressions = {
        str(name): float(weight)
        for name, weight in case.get("expressions", {}).items()
    }
    validate_age = bool(request.get("validate_age", True))
    actors = find_review_actors(actor_subsystem)
    if len(actors) != 1:
        raise RuntimeError(f"Expected one staged review actor, found {len(actors)}")
    actor = actors[0]

    try:
        components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
        if len(components) != EXPECTED_COMPONENT_COUNT:
            raise RuntimeError(
                f"Expected {EXPECTED_COMPONENT_COUNT} modular components, "
                f"found {len(components)}"
            )
        output_path = OUTPUT_DIR / f"{case_id}.png"
        capture = capture_viewport(
            unreal.get_default_object(unreal.EditorAppToolset), output_path
        )

        supports_age = []
        errors = []
        expression_support = {}
        for component in components:
            component_morphs = morph_names(component)
            if validate_age and MORPH_NAME in component_morphs:
                supports_age.append(component.get_name())
                actual = float(component.get_morph_target(MORPH_NAME))
                if abs(actual - age) > TOLERANCE:
                    errors.append(
                        f"{component.get_name()} age={actual}, requested={age}"
                    )
            for expression_name, requested in expressions.items():
                if expression_name not in component_morphs:
                    continue
                expression_support.setdefault(expression_name, []).append(
                    component.get_name()
                )
                actual = float(component.get_morph_target(expression_name))
                if abs(actual - requested) > TOLERANCE:
                    errors.append(
                        f"{component.get_name()} {expression_name}={actual}, "
                        f"requested={requested}"
                    )

        if validate_age and not supports_age:
            errors.append(f"No component supports {MORPH_NAME}")
        for expression_name in expressions:
            if not expression_support.get(expression_name):
                errors.append(f"No component supports {expression_name}")

        report = {
            "actor_component_count": EXPECTED_COMPONENT_COUNT,
            "animation": BODY_ANIMATION,
            "blueprint": str(request.get("blueprint_path", BLUEPRINT_PATH)),
            "camera_distance_cm": CAMERA_DISTANCE_CM,
            "cases": [],
            "expected_case_count": int(request["expected_case_count"]),
            "morph_name": MORPH_NAME,
            "render_sync": "separate remote stage and capture commands",
            "success": False,
        }
        if REPORT_PATH.exists():
            report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        report["cases"] = [
            item for item in report.get("cases", []) if item["id"] != case_id
        ]
        report["cases"].append(
            {
                "age": age,
                "capture": capture,
                "errors": errors,
                "expression_support": {
                    name: sorted(component_names)
                    for name, component_names in expression_support.items()
                },
                "expressions": expressions,
                "id": case_id,
                "supports_age": sorted(supports_age),
            }
        )
        report["cases"] = sorted(report["cases"], key=lambda item: item["id"])
        report["success"] = (
            len(report["cases"]) == report["expected_case_count"]
            and all(not item["errors"] for item in report["cases"])
        )
        REPORT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    finally:
        actor_subsystem.destroy_actor(actor)

    if errors:
        raise RuntimeError(f"Elder Morph case failed: {case_id}: {errors}")
    print(
        "DM_ELDER_MORPH_CAPTURED="
        + json.dumps(
            {
                "case_id": case_id,
                "capture": str(output_path),
                "report": str(REPORT_PATH),
            },
            sort_keys=True,
        )
    )


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
request = read_request()
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
operation = request["operation"]
if operation == "stage":
    stage_case(request, actor_subsystem)
elif operation == "capture":
    capture_case(request, actor_subsystem)
else:
    removed = destroy_review_actors(actor_subsystem)
    print("DM_ELDER_MORPH_CLEANUP=" + json.dumps({"removed": removed}))
