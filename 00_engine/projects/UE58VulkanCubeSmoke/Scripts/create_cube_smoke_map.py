"""Generate the isolated cube map used by the Linux Vulkan pixel smoke."""

from __future__ import annotations

import json
import os

import unreal


MAP_PATH = os.environ.get(
    "DM_CUBE_SMOKE_MAP_PATH", "/Game/Maps/L_UE58_Vulkan_Cube_Smoke"
)
CUBE_MESH_PATH = "/Engine/BasicShapes/Cube.Cube"
CUBE_MATERIAL_PATH = "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"


def env_enabled(name: str) -> bool:
    value = os.environ.get(name, "1")
    if value not in {"0", "1"}:
        raise RuntimeError(f"{name} must be 0 or 1, got {value!r}")
    return value == "1"


INCLUDE_DIRECTIONAL_LIGHT = env_enabled("DM_CUBE_SMOKE_DIRECTIONAL_LIGHT")
INCLUDE_POINT_LIGHT = env_enabled("DM_CUBE_SMOKE_POINT_LIGHT")


def require_asset(path: str, expected_type: type) -> object:
    asset = unreal.load_asset(path)
    if not isinstance(asset, expected_type):
        raise RuntimeError(f"Required asset unavailable or wrong type: {path}")
    return asset


level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
    if not unreal.EditorAssetLibrary.delete_asset(MAP_PATH):
        raise RuntimeError(f"Unable to replace existing diagnostic map: {MAP_PATH}")

if not level_subsystem.new_level(MAP_PATH):
    raise RuntimeError(f"Unable to create diagnostic map: {MAP_PATH}")

cube_mesh = require_asset(CUBE_MESH_PATH, unreal.StaticMesh)
cube_material = require_asset(CUBE_MATERIAL_PATH, unreal.MaterialInterface)


def spawn_mesh(label: str, location: unreal.Vector, scale: unreal.Vector):
    actor = actor_subsystem.spawn_actor_from_class(
        unreal.StaticMeshActor,
        location,
        unreal.Rotator(),
        transient=False,
    )
    if actor is None:
        raise RuntimeError(f"Unable to spawn {label}")
    actor.set_actor_label(label)
    actor.set_actor_scale3d(scale)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component is None or not component.set_static_mesh(cube_mesh):
        raise RuntimeError(f"Unable to assign cube mesh to {label}")
    component.set_material(0, cube_material)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    return actor


floor = spawn_mesh(
    "DM_CubeSmoke_Floor",
    unreal.Vector(0.0, 0.0, -5.0),
    unreal.Vector(8.0, 8.0, 0.1),
)
cube = spawn_mesh(
    "DM_CubeSmoke_Cube",
    unreal.Vector(0.0, 0.0, 50.0),
    unreal.Vector(1.0, 1.0, 1.0),
)

if INCLUDE_DIRECTIONAL_LIGHT:
    directional_light = actor_subsystem.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(),
        unreal.Rotator(-45.0, -35.0, 0.0),
        transient=False,
    )
    if directional_light is None:
        raise RuntimeError("Unable to spawn directional light")
    directional_light.set_actor_label("DM_CubeSmoke_DirectionalLight")
    directional_component = directional_light.get_component_by_class(
        unreal.DirectionalLightComponent
    )
    if directional_component is None:
        raise RuntimeError("Directional light component is unavailable")
    directional_component.set_intensity(8.0)

if INCLUDE_POINT_LIGHT:
    point_light = actor_subsystem.spawn_actor_from_class(
        unreal.PointLight,
        unreal.Vector(250.0, -200.0, 300.0),
        unreal.Rotator(),
        transient=False,
    )
    if point_light is None:
        raise RuntimeError("Unable to spawn point light")
    point_light.set_actor_label("DM_CubeSmoke_PointLight")
    point_component = point_light.get_component_by_class(unreal.PointLightComponent)
    if point_component is None:
        raise RuntimeError("Point light component is unavailable")
    point_component.set_intensity(5000.0)
    point_component.set_attenuation_radius(1200.0)

camera_location = unreal.Vector(450.0, -450.0, 260.0)
camera_rotation = unreal.MathLibrary.find_look_at_rotation(
    camera_location,
    unreal.Vector(0.0, 0.0, 45.0),
)
camera = actor_subsystem.spawn_actor_from_class(
    unreal.CameraActor,
    camera_location,
    camera_rotation,
    transient=False,
)
if camera is None:
    raise RuntimeError("Unable to spawn camera")
camera.set_actor_label("DM_CubeSmoke_Camera")
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera_component = camera.get_component_by_class(unreal.CameraComponent)
if camera_component is None:
    raise RuntimeError("Camera component is unavailable")
camera_component.set_editor_property("field_of_view", 50.0)

if not level_subsystem.save_current_level():
    raise RuntimeError(f"Unable to save diagnostic map: {MAP_PATH}")

actors = sorted(
    actor.get_actor_label() for actor in actor_subsystem.get_all_level_actors()
)
required = {
    "DM_CubeSmoke_Camera",
    "DM_CubeSmoke_Cube",
    "DM_CubeSmoke_Floor",
}
if INCLUDE_DIRECTIONAL_LIGHT:
    required.add("DM_CubeSmoke_DirectionalLight")
if INCLUDE_POINT_LIGHT:
    required.add("DM_CubeSmoke_PointLight")
missing = sorted(required.difference(actors))
if missing:
    raise RuntimeError(f"Generated map is missing actors: {missing}")

print(
    "DM_UE58_CUBE_MAP="
    + json.dumps(
        {
            "actors": actors,
            "camera_location": [camera_location.x, camera_location.y, camera_location.z],
            "directional_light": INCLUDE_DIRECTIONAL_LIGHT,
            "map": MAP_PATH,
            "point_light": INCLUDE_POINT_LIGHT,
            "required_actor_count": len(required),
            "success": True,
        },
        sort_keys=True,
    )
)
