"""Capture the staged M02 body-motion and face-expression demonstration."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import struct

import unreal


CONFIG_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\unreal"
    r"\ue_m02_body_face_capture_config.json"
)
ACTOR_LABEL = "DM_M02_BodyFaceDemo"
CAMERA_LABEL = "DM_M02_BodyFaceCaptureCamera"


def vector(values):
    return unreal.Vector(float(values[0]), float(values[1]), float(values[2]))


def rotator(values):
    return unreal.Rotator(
        pitch=float(values[0]),
        yaw=float(values[1]),
        roll=float(values[2]),
    )


config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
output_path = Path(config["output_path"])
resolution = config.get("resolution", [1600, 1000])
expressions = {
    str(name): float(weight)
    for name, weight in config.get("expressions", {}).items()
}
output_path.parent.mkdir(parents=True, exist_ok=True)
if output_path.exists():
    output_path.unlink()

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor_actors = actor_subsystem.get_all_level_actors()
unreal_editor_subsystem = unreal.get_editor_subsystem(
    unreal.UnrealEditorSubsystem
)
game_world = unreal_editor_subsystem.get_game_world()
is_pie = game_world is not None
actors = (
    unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor)
    if is_pie
    else editor_actors
)
toolset = unreal.get_default_object(unreal.EditorAppToolset)
visible_actors = toolset.call_method("GetVisibleActors", ())
demo_actor = next(
    (actor for actor in actors if actor.get_actor_label() == ACTOR_LABEL), None
)
if demo_actor is None:
    raise RuntimeError(f"Staged actor is unavailable: {ACTOR_LABEL}")

for morph_name, weight in expressions.items():
    demo_actor.call_method("BroadcastFaceMorph", (morph_name, weight, False))

hidden_component_names = set(
    config.get("temporarily_hidden_component_names", [])
)
temporarily_hidden_components = [
    component
    for component in demo_actor.get_components_by_class(unreal.SkeletalMeshComponent)
    if component.get_name() in hidden_component_names
]
for component in temporarily_hidden_components:
    component.set_visibility(False, False)

for actor in list({*editor_actors, *visible_actors}):
    if actor.get_actor_label() == CAMERA_LABEL:
        actor_subsystem.destroy_actor(actor)

hidden_labels = set(config.get("temporarily_hidden_actor_labels", []))
temporarily_hidden_actors = [
    actor for actor in actors if actor.get_actor_label() in hidden_labels
]
for actor in temporarily_hidden_actors:
    if is_pie:
        actor.set_actor_hidden_in_game(True)
    else:
        actor.set_is_temporarily_hidden_in_editor(True)

if not is_pie:
    actor_subsystem.set_selected_level_actors([])
unreal.EditorLevelLibrary.set_level_viewport_camera_info(
    vector(config["camera_location"]), rotator(config["camera_rotation"])
)

try:
    capture = toolset.call_method("CaptureViewport", (None, None, False))
    image = capture.image
    if image.mime_type != "image/png" or not image.data:
        raise RuntimeError(
            f"Viewport capture failed: mime_type={image.mime_type!r}, "
            f"data_length={len(image.data)}"
        )
    png_bytes = base64.b64decode(image.data)
    output_path.write_bytes(png_bytes)
finally:
    for actor in temporarily_hidden_actors:
        if is_pie:
            actor.set_actor_hidden_in_game(False)
        else:
            actor.set_is_temporarily_hidden_in_editor(False)
    for component in temporarily_hidden_components:
        component.set_visibility(True, False)
if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
    raise RuntimeError("Viewport capture did not return a valid PNG")
actual_width, actual_height = struct.unpack(">II", png_bytes[16:24])

print(
    "DM_BODY_FACE_CAPTURED="
    + json.dumps(
        {
            "actor": demo_actor.get_path_name(),
            "world": game_world.get_path_name() if is_pie else "editor",
            "is_pie": is_pie,
            "output_path": str(output_path),
            "requested_resolution": resolution,
            "actual_resolution": [actual_width, actual_height],
            "file_size_bytes": len(png_bytes),
            "camera_location": config["camera_location"],
            "camera_rotation": config["camera_rotation"],
            "temporarily_hidden_actor_labels": sorted(hidden_labels),
            "temporarily_hidden_component_names": sorted(hidden_component_names),
            "camera_fov_note": (
                "CaptureViewport uses the active editor viewport FOV; "
                "camera_fov is informational only"
            ),
            "expressions": expressions,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
