"""Spawn and validate a transient instance of the M02 modular Blueprint."""

import json
from pathlib import Path
import unreal


BLUEPRINT_PATH = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v001"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_modular_blueprint_validation.json"
)


blueprint = unreal.load_asset(BLUEPRINT_PATH)
if not isinstance(blueprint, unreal.Blueprint):
    raise RuntimeError(f"Modular Blueprint is unavailable: {BLUEPRINT_PATH}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actor = actor_subsystem.spawn_actor_from_class(
    blueprint.generated_class(),
    unreal.Vector(0.0, 0.0, 0.0),
    unreal.Rotator(0.0, 0.0, 0.0),
    transient=True,
)
if actor is None:
    raise RuntimeError("Unable to spawn a transient modular actor")

try:
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    body = next((item for item in components if item.get_name() == "Body"), None)
    if body is None:
        raise RuntimeError("Spawned modular actor has no Body component")

    records = []
    for component in components:
        leader = component.get_editor_property("leader_pose_component")
        parent = component.get_attach_parent()
        mesh = component.get_skeletal_mesh_asset()
        records.append(
            {
                "name": component.get_name(),
                "mesh": mesh.get_path_name() if mesh is not None else None,
                "leader": leader.get_name() if leader is not None else None,
                "leader_is_instance_body": leader == body,
                "parent": parent.get_name() if parent is not None else None,
                "collision_enabled": str(component.get_collision_enabled()),
                "visible": component.is_visible(),
            }
        )
    records.sort(key=lambda item: item["name"])

    followers = [item for item in records if item["name"] != "Body"]
    origin, extent = actor.get_actor_bounds(False, True)
    report = {
        "blueprint": blueprint.get_path_name(),
        "component_count": len(records),
        "body_mesh": body.get_skeletal_mesh_asset().get_path_name(),
        "followers_without_instance_body_leader": [
            item["name"]
            for item in followers
            if not item["leader_is_instance_body"]
        ],
        "followers_not_attached_to_body": [
            item["name"] for item in followers if item["parent"] != "Body"
        ],
        "components_without_mesh": [
            item["name"] for item in records if item["mesh"] is None
        ],
        "actor_bounds": {
            "origin": {"x": origin.x, "y": origin.y, "z": origin.z},
            "extent": {"x": extent.x, "y": extent.y, "z": extent.z},
        },
        "components": records,
    }
finally:
    actor_subsystem.destroy_actor(actor)

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_MODULAR_VALIDATION="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "component_count": report["component_count"],
            "followers_without_instance_body_leader": report[
                "followers_without_instance_body_leader"
            ],
            "followers_not_attached_to_body": report[
                "followers_not_attached_to_body"
            ],
            "components_without_mesh": report["components_without_mesh"],
            "actor_bounds": report["actor_bounds"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
