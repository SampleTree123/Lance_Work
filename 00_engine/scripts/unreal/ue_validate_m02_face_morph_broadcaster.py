"""Validate the reusable face-morph broadcaster on the M02 modular Blueprint."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


BLUEPRINT_PATH = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_face_morph_broadcaster_validation.json"
)
ACTOR_LABEL = "DM_M02_FaceBroadcasterValidation"
FACE_COMPONENTS = {
    "Body",
    "Face_Eyes",
    "Face_EyeOcclusion",
    "Face_TearDucts",
    "Face_Tearline",
    "Face_Teeth",
    "Face_Tongue",
    "Face_Brows",
    "Face_LashesUpper",
    "Face_LashesLower",
    "Face_BeardChin",
    "Face_BeardNeck",
    "Face_Mustache",
}
TEST_EXPRESSIONS = {
    "CTRL_expressions_eyeBlinkL": 0.73,
    "CTRL_expressions_mouthCornerPullL": 0.61,
    "CTRL_expressions_mouthCornerPullR": 0.59,
}
TOLERANCE = 1.0e-5


def morph_names(component):
    mesh = component.get_skeletal_mesh_asset()
    if mesh is None:
        return set()
    return {str(name) for name in mesh.get_all_morph_target_names()}


def clean_previous(actor_subsystem):
    removed = []
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == ACTOR_LABEL:
            removed.append(actor.get_path_name())
            actor_subsystem.destroy_actor(actor)
    return removed


blueprint = unreal.load_asset(BLUEPRINT_PATH)
if not isinstance(blueprint, unreal.Blueprint):
    raise RuntimeError(f"Blueprint is unavailable: {BLUEPRINT_PATH}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed_previous = clean_previous(actor_subsystem)
actor = actor_subsystem.spawn_actor_from_class(
    blueprint.generated_class(),
    unreal.Vector(0.0, 0.0, -10000.0),
    unreal.Rotator(),
    transient=True,
)
if actor is None:
    raise RuntimeError("Unable to spawn broadcaster validation actor")
actor.set_actor_label(ACTOR_LABEL)

try:
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    components_by_name = {component.get_name(): component for component in components}
    missing_components = sorted(FACE_COMPONENTS - components_by_name.keys())
    if missing_components:
        raise RuntimeError(f"Missing expected face components: {missing_components}")

    expression_records = []
    errors = []
    non_face_names = sorted(components_by_name.keys() - FACE_COMPONENTS)

    for morph_name, requested_weight in TEST_EXPRESSIONS.items():
        actor.call_method(
            "BroadcastFaceMorph",
            (morph_name, requested_weight, False),
        )

        records = []
        for component_name in sorted(components_by_name):
            component = components_by_name[component_name]
            supports_morph = morph_name in morph_names(component)
            weight = float(component.get_morph_target(morph_name))
            is_face_component = component_name in FACE_COMPONENTS
            records.append(
                {
                    "component": component_name,
                    "is_face_component": is_face_component,
                    "supports_morph": supports_morph,
                    "weight": weight,
                }
            )

            if supports_morph and not is_face_component:
                errors.append(
                    f"{component_name} supports {morph_name} but is outside the "
                    "face broadcast set"
                )
            if supports_morph and is_face_component:
                if abs(weight - requested_weight) > TOLERANCE:
                    errors.append(
                        f"{component_name} did not receive {morph_name}: "
                        f"expected={requested_weight}, actual={weight}"
                    )
            if not is_face_component and abs(weight) > TOLERANCE:
                errors.append(
                    f"Non-face component {component_name} received {morph_name}: "
                    f"{weight}"
                )

        expression_records.append(
            {
                "morph": morph_name,
                "requested_weight": requested_weight,
                "supported_face_component_count": sum(
                    1
                    for record in records
                    if record["is_face_component"] and record["supports_morph"]
                ),
                "non_face_components": non_face_names,
                "components": records,
            }
        )
        actor.call_method("BroadcastFaceMorph", (morph_name, 0.0, True))

    report = {
        "blueprint": blueprint.get_path_name(),
        "function": "BroadcastFaceMorph",
        "face_component_count": len(FACE_COMPONENTS),
        "total_skeletal_mesh_component_count": len(components),
        "removed_previous_actors": removed_previous,
        "expressions": expression_records,
        "errors": errors,
        "success": not errors,
    }
finally:
    actor_subsystem.destroy_actor(actor)

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
if not report["success"]:
    raise RuntimeError(f"Broadcaster validation failed: {report['errors']}")

print(
    "DM_FACE_BROADCASTER_VALIDATION="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "blueprint": report["blueprint"],
            "face_component_count": report["face_component_count"],
            "total_skeletal_mesh_component_count": report[
                "total_skeletal_mesh_component_count"
            ],
            "expression_support_counts": {
                item["morph"]: item["supported_face_component_count"]
                for item in report["expressions"]
            },
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
