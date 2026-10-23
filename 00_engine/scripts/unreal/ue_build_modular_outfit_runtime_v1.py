"""Build and validate the two modular-outfit pilot runtime actors in Unreal.

Run through ``ue_remote_exec.py``. Set ``DM_MODULAR_RUNTIME_MODE`` to one of
``build_bodyfit``, ``validate_switches``, ``stage_variant``, or ``cleanup_stage``.
All modes require ``DM_MODULAR_BODYFIT_ID``. ``stage_variant`` also requires
``DM_MODULAR_VARIANT_ID`` in ``CASE_ID::variant_id`` form.
"""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_build_modular_outfit_runtime_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


from datetime import datetime, timezone
import json
from pathlib import Path
import re

import unreal


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
PLAN_PATH = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "modular_outfit_pilot_20260829_v1"
    / "runtime_plan_v1.json"
)
REPORT_ROOT = PLAN_PATH.parent / "runtime"
VALID_MODES = {
    "build_bodyfit",
    "validate_switches",
    "stage_variant",
    "cleanup_stage",
}
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_]+$")
STAGE_LABEL_PREFIX = "DM_ModularOutfitPilot_"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return value


def write_report(name: str, value: dict) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / name
    value["report_path"] = str(path)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def object_path(value) -> str | None:
    return value.get_path_name() if value is not None else None


def bodyfit_for_id(plan: dict, bodyfit_id: str) -> dict:
    matches = [
        item for item in plan.get("bodyfits") or [] if item.get("bodyfit_id") == bodyfit_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one runtime bodyfit {bodyfit_id}, found {len(matches)}")
    return matches[0]


def all_variants(bodyfit: dict) -> list[dict]:
    variants = bodyfit.get("runtime_variants")
    if not isinstance(variants, list):
        raise RuntimeError(
            f"Runtime variants are missing for {bodyfit.get('bodyfit_id')}"
        )
    return variants


def variant_for_id(bodyfit: dict, qualified_variant_id: str) -> dict:
    matches = [
        item
        for item in all_variants(bodyfit)
        if item.get("qualified_variant_id") == qualified_variant_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one runtime variant {qualified_variant_id}, found {len(matches)}"
        )
    return matches[0]


def validate_runtime_plan(plan: dict) -> dict:
    if plan.get("schema_version") != 1:
        raise RuntimeError("Unsupported modular runtime plan schema")
    if plan.get("status") != "classified_ready_for_blueprint_build":
        raise RuntimeError("Modular runtime plan is not ready for Blueprint build")
    bodyfits = plan.get("bodyfits")
    if not isinstance(bodyfits, list) or len(bodyfits) != 2:
        raise RuntimeError("Runtime plan must contain exactly two bodyfits")
    bodyfit_ids = []
    variant_ids = []
    for bodyfit in bodyfits:
        bodyfit_id = bodyfit.get("bodyfit_id")
        if not isinstance(bodyfit_id, str) or not SAFE_SEGMENT.fullmatch(bodyfit_id):
            raise RuntimeError(f"Unsafe runtime bodyfit ID: {bodyfit_id}")
        bodyfit_ids.append(bodyfit_id)
        component_count = bodyfit.get("component_count")
        component_names = bodyfit.get("component_names")
        components = bodyfit.get("components")
        if not isinstance(component_count, int) or component_count <= 0:
            raise RuntimeError(f"Invalid component count for {bodyfit_id}")
        if (
            not isinstance(component_names, list)
            or not isinstance(components, list)
            or len(component_names) != component_count
            or len(components) != component_count
        ):
            raise RuntimeError(f"Component registry mismatch for {bodyfit_id}")
        if component_names != [item.get("component_name") for item in components]:
            raise RuntimeError(f"Component registry ordering differs for {bodyfit_id}")
        if len(component_names) != len(set(component_names)):
            raise RuntimeError(f"Component names are not unique for {bodyfit_id}")
        if any(not item.get("mesh_path") for item in components):
            raise RuntimeError(f"Component mesh path is empty for {bodyfit_id}")
        for variant in all_variants(bodyfit):
            qualified = variant.get("qualified_variant_id")
            if not isinstance(qualified, str) or "::" not in qualified:
                raise RuntimeError(f"Invalid qualified variant ID: {qualified}")
            enabled = variant.get("enabled_component_names")
            if not isinstance(enabled, list):
                raise RuntimeError(f"Variant component set is invalid: {qualified}")
            if len(enabled) != len(set(enabled)):
                raise RuntimeError(f"Variant component set has duplicates: {qualified}")
            unknown = sorted(set(enabled) - set(component_names))
            if unknown:
                raise RuntimeError(
                    f"Variant references unknown components: {qualified}: {unknown}"
                )
            if variant.get("enabled_component_count") != len(enabled):
                raise RuntimeError(f"Variant component count differs: {qualified}")
            variant_ids.append(qualified)
    if len(bodyfit_ids) != len(set(bodyfit_ids)):
        raise RuntimeError("Runtime bodyfit IDs are not unique")
    if len(variant_ids) != len(set(variant_ids)):
        raise RuntimeError("Qualified runtime variant IDs are not unique")
    return {
        "bodyfit_ids": bodyfit_ids,
        "bodyfit_count": len(bodyfits),
        "variant_count": len(variant_ids),
    }


def get_data(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)


def get_component(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(
        get_data(handle)
    )


def find_pin(node, name: str):
    for pin in node.list_all_pins():
        if pin.get_pin_name() == name:
            return pin
    raise RuntimeError(f"Pin {name!r} is unavailable on {node.get_node_title()}")


def only_pin(node):
    pins = list(node.list_all_pins())
    if len(pins) != 1:
        raise RuntimeError(
            f"Expected one data pin on {node.get_node_title()}, found {len(pins)}"
        )
    return pins[0]


def connect(output_pin, input_pin) -> None:
    if not output_pin.try_create_connection(input_pin):
        raise RuntimeError(
            f"Unable to connect {output_pin.get_pin_name()} to {input_pin.get_pin_name()}"
        )


def create_variable_getter(BlueprintTools, graph, variable_name: str, position):
    search_names = [variable_name]
    compact_name = re.sub(r"[^A-Za-z0-9]+", "", variable_name)
    if compact_name and compact_name != variable_name:
        search_names.append(compact_name)
    candidates = []
    for search_name in search_names:
        for type_id in BlueprintTools.find_node_types(graph, search_name):
            if type_id not in candidates:
                candidates.append(type_id)
    getter_candidates = [
        type_id
        for type_id in candidates
        if (
            f"Get{variable_name}" in type_id
            or f"Get{compact_name}" in type_id
            or f"\u83b7\u53d6{variable_name}" in type_id
            or f"\u83b7\u53d6{compact_name}" in type_id
        )
        and (
            type_id.startswith("Variable|")
            or type_id.startswith("\u53d8\u91cf|")
        )
    ]
    attempts = []
    for type_id in getter_candidates:
        node = BlueprintTools.create_node(graph, type_id, position)
        attempts.append({"type_id": type_id, "class": str(type(node))})
        if isinstance(node, unreal.K2Node_VariableGet):
            return node
        BlueprintTools.delete_node(node)
    raise RuntimeError(
        f"No self-variable getter for {variable_name}; attempts={attempts}"
    )


def create_set_leader_node(BlueprintTools, graph, position):
    candidates = []
    for query in (
        "SetLeaderPoseComponent",
        "Set Leader Pose Component",
        "\u8bbe\u7f6e\u9886\u5bfc\u8005\u59ff\u52bf\u7ec4\u4ef6",
    ):
        for type_id in BlueprintTools.find_node_types(graph, query):
            if type_id not in candidates:
                candidates.append(type_id)
    required_pins = {
        "execute",
        "then",
        "self",
        "NewLeaderBoneComponent",
        "bForceUpdate",
        "bInFollowerShouldTickPose",
    }
    attempts = []
    for type_id in candidates:
        node = BlueprintTools.create_node(graph, type_id, position)
        pin_names = {str(pin.get_pin_name()) for pin in node.list_all_pins()}
        attempts.append(
            {
                "type_id": type_id,
                "class": str(type(node)),
                "pins": sorted(pin_names),
            }
        )
        if isinstance(node, unreal.K2Node_CallFunction) and required_pins <= pin_names:
            return node
        BlueprintTools.delete_node(node)
    raise RuntimeError(
        "Unable to create an exact SetLeaderPoseComponent node; "
        f"attempts={attempts}"
    )


def blueprint_asset_name(path: str) -> tuple[str, str]:
    folder, name = path.rsplit("/", 1)
    if not folder or not name:
        raise RuntimeError(f"Invalid Blueprint path: {path}")
    return folder, name


def unique_skeletal_component(components: list, name: str):
    matches = [component for component in components if component.get_name() == name]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one component {name}, found {len(matches)}")
    return matches[0]


def build_construction_graph(blueprint, component_names: list[str]) -> dict:
    from editor_toolset.toolsets.blueprint import BlueprintTools

    graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, "UserConstructionScript")
    if graph is None:
        raise RuntimeError("UserConstructionScript graph is unavailable")
    graph_editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if graph_editor is None:
        raise RuntimeError("Construction graph editor interface is unavailable")
    nodes = list(BlueprintTools.find_nodes(graph))
    entries = [node for node in nodes if isinstance(node, unreal.K2Node_FunctionEntry)]
    if len(entries) != 1:
        raise RuntimeError(f"Expected one construction entry, found {len(entries)}")
    entry = entries[0]
    stale = [node for node in nodes if node != entry]
    if stale:
        graph_editor.remove_nodes(stale)

    body_getter = create_variable_getter(
        BlueprintTools, graph, "Body", unreal.IntPoint(-350, 0)
    )
    body_pin = only_pin(body_getter)
    previous_exec = find_pin(entry, "then")
    created = [entry, body_getter]
    for index, component_name in enumerate(component_names):
        x = 250 + index * 360
        getter = create_variable_getter(
            BlueprintTools,
            graph,
            component_name,
            unreal.IntPoint(x, 220),
        )
        call = create_set_leader_node(
            BlueprintTools, graph, unreal.IntPoint(x, 0)
        )
        created.extend([getter, call])
        connect(previous_exec, find_pin(call, "execute"))
        connect(only_pin(getter), find_pin(call, "self"))
        connect(body_pin, find_pin(call, "NewLeaderBoneComponent"))
        find_pin(call, "bForceUpdate").set_pin_value("true")
        find_pin(call, "bInFollowerShouldTickPose").set_pin_value("false")
        previous_exec = find_pin(call, "then")
    BlueprintTools.arrange_nodes(created)
    return {
        "graph": graph.get_path_name(),
        "node_count": len(BlueprintTools.find_nodes(graph)),
        "leader_binding_count": len(component_names),
    }


def build_bodyfit_blueprint(bodyfit: dict) -> dict:
    blueprint_path = bodyfit["blueprint_path"]
    if unreal.EditorAssetLibrary.does_asset_exist(blueprint_path):
        raise RuntimeError(f"Refusing to overwrite existing Blueprint: {blueprint_path}")
    body_mesh = unreal.load_asset(bodyfit["body_mesh_path"])
    if not isinstance(body_mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Body mesh is unavailable: {bodyfit['body_mesh_path']}")
    body_skeleton = body_mesh.get_editor_property("skeleton")
    if object_path(body_skeleton) != bodyfit["skeleton_path"]:
        raise RuntimeError(f"Body Skeleton differs from runtime plan: {bodyfit['bodyfit_id']}")

    folder, name = blueprint_asset_name(blueprint_path)
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.Blueprint, factory
    )
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"Unable to create modular Blueprint: {blueprint_path}")

    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
    root_handle = next(
        (
            handle
            for handle in handles
            if unreal.SubobjectDataBlueprintFunctionLibrary.is_root_component(
                get_data(handle)
            )
        ),
        None,
    )
    if root_handle is None:
        raise RuntimeError("Modular Blueprint has no scene root")

    body_handle, failure = subsystem.add_new_subobject(
        unreal.AddNewSubobjectParams(
            parent_handle=root_handle,
            new_class=unreal.SkeletalMeshComponent,
            blueprint_context=blueprint,
        )
    )
    if not failure.is_empty():
        raise RuntimeError(f"Unable to add Body component: {failure}")
    if not subsystem.rename_subobject(handle=body_handle, new_name=unreal.Text("Body")):
        raise RuntimeError("Unable to rename Body component")
    body = get_component(body_handle)
    if not isinstance(body, unreal.SkeletalMeshComponent):
        raise RuntimeError(f"Unexpected Body component type: {body}")
    body.set_skeletal_mesh_asset(body_mesh)
    body.set_update_animation_in_editor(True)
    body.set_allow_anim_curve_evaluation(True)
    body.set_editor_property("component_use_fixed_skel_bounds", False)
    body.set_editor_property("propagate_curves_to_followers", True)

    component_templates = []
    for component_spec in bodyfit["components"]:
        component_name = component_spec["component_name"]
        outfit_mesh = unreal.load_asset(component_spec["mesh_path"])
        if not isinstance(outfit_mesh, unreal.SkeletalMesh):
            raise RuntimeError(
                f"Outfit mesh is unavailable: {component_spec['mesh_path']}"
            )
        if outfit_mesh.get_editor_property("skeleton") != body_skeleton:
            raise RuntimeError(
                f"Outfit mesh Skeleton mismatch: {component_spec['mesh_path']}"
            )
        handle, failure = subsystem.add_new_subobject(
            unreal.AddNewSubobjectParams(
                parent_handle=body_handle,
                new_class=unreal.SkeletalMeshComponent,
                blueprint_context=blueprint,
            )
        )
        if not failure.is_empty():
            raise RuntimeError(f"Unable to add {component_name}: {failure}")
        if not subsystem.rename_subobject(
            handle=handle, new_name=unreal.Text(component_name)
        ):
            raise RuntimeError(f"Unable to rename component: {component_name}")
        component = get_component(handle)
        if not isinstance(component, unreal.SkeletalMeshComponent):
            raise RuntimeError(f"Unexpected component type: {component_name}")
        component.set_skeletal_mesh_asset(outfit_mesh)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_editor_property("component_use_fixed_skel_bounds", False)
        component.set_editor_property("use_bounds_from_leader_pose_component", True)
        component.set_visibility(False, False)
        component.set_hidden_in_game(True)
        component_templates.append(component)

    # Template weak references are not actor-instance references. Bind followers in
    # the construction graph so every spawned actor owns valid Leader Pose links.
    graph_record = build_construction_graph(blueprint, bodyfit["component_names"])
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    status = blueprint.get_editor_property("status")
    if status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError(f"Modular Blueprint compile failed: {status}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        blueprint, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save modular Blueprint: {blueprint_path}")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_subsystem.spawn_actor_from_class(
        blueprint.generated_class(), unreal.Vector(), unreal.Rotator(), transient=True
    )
    if actor is None:
        raise RuntimeError("Unable to spawn modular Blueprint verification actor")
    try:
        components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
        body_instance = unique_skeletal_component(components, "Body")
        follower_records = []
        for component_name in bodyfit["component_names"]:
            follower = unique_skeletal_component(components, component_name)
            follower_records.append(
                {
                    "name": component_name,
                    "leader": object_path(
                        follower.get_editor_property("leader_pose_component")
                    ),
                    "leader_is_body": (
                        follower.get_editor_property("leader_pose_component")
                        == body_instance
                    ),
                    "attach_parent": object_path(follower.get_attach_parent()),
                    "attach_parent_is_body": follower.get_attach_parent() == body_instance,
                    "mesh": object_path(follower.get_skeletal_mesh_asset()),
                    "collision": str(follower.get_collision_enabled()),
                }
            )
        if not all(item["leader_is_body"] for item in follower_records):
            raise RuntimeError("Construction graph did not bind every outfit channel")
        expected_meshes = {
            item["component_name"]: item["mesh_path"]
            for item in bodyfit["components"]
        }
        if any(
            item["mesh"] != expected_meshes[item["name"]]
            for item in follower_records
        ):
            raise RuntimeError("Outfit component hard references differ from the plan")
        verification = {
            "actor": actor.get_path_name(),
            "body_mesh": object_path(body_instance.get_skeletal_mesh_asset()),
            "body_propagates_curves": bool(
                body_instance.get_editor_property("propagate_curves_to_followers")
            ),
            "followers": follower_records,
        }
    finally:
        actor_subsystem.destroy_actor(actor)

    success = (
        verification["body_mesh"] == bodyfit["body_mesh_path"]
        and verification["body_propagates_curves"]
        and len(verification["followers"]) == bodyfit["component_count"]
        and all(item["leader_is_body"] for item in verification["followers"])
        and all(item["attach_parent_is_body"] for item in verification["followers"])
        and all(
            "NO_COLLISION" in item["collision"].upper()
            for item in verification["followers"]
        )
    )
    return {
        "bodyfit_id": bodyfit["bodyfit_id"],
        "sex": bodyfit["sex"],
        "blueprint_path": blueprint_path,
        "compile_status": str(status),
        "body_mesh": bodyfit["body_mesh_path"],
        "skeleton": bodyfit["skeleton_path"],
        "component_count": bodyfit["component_count"],
        "component_names": bodyfit["component_names"],
        "construction_graph": graph_record,
        "spawn_verification": verification,
        "success": success,
    }


def load_blueprint(bodyfit: dict):
    blueprint = unreal.load_asset(bodyfit["blueprint_path"])
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"Modular Blueprint is unavailable: {bodyfit['blueprint_path']}")
    return blueprint


def actor_components(actor, bodyfit: dict) -> tuple[object, list]:
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    body = unique_skeletal_component(components, "Body")
    followers = [
        unique_skeletal_component(components, name)
        for name in bodyfit["component_names"]
    ]
    return body, followers


def apply_variant(actor, bodyfit: dict, variant: dict) -> dict:
    body, followers = actor_components(actor, bodyfit)
    body_mesh_before = object_path(body.get_skeletal_mesh_asset())
    if body_mesh_before != bodyfit["body_mesh_path"]:
        raise RuntimeError("Runtime actor body identity differs from the frozen plan")
    body_skeleton = body.get_skeletal_mesh_asset().get_editor_property("skeleton")
    target_names = set(variant["enabled_component_names"])
    registry = {
        item["component_name"]: item for item in bodyfit["components"]
    }
    if not target_names <= set(registry):
        raise RuntimeError("Runtime variant contains an unregistered component")

    # Validate the complete target before mutating visibility. Unknown or broken
    # variants therefore leave the actor's current outfit unchanged.
    for component in followers:
        component_spec = registry[component.get_name()]
        mesh = component.get_skeletal_mesh_asset()
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError(
                f"Outfit component has no hard-reference mesh: {component.get_name()}"
            )
        if object_path(mesh) != component_spec["mesh_path"]:
            raise RuntimeError(
                f"Outfit component mesh differs from the plan: {component.get_name()}"
            )
        if mesh.get_editor_property("skeleton") != body_skeleton:
            raise RuntimeError(
                f"Outfit component Skeleton mismatch: {component.get_name()}"
            )
        if component.get_editor_property("leader_pose_component") != body:
            raise RuntimeError(
                f"Outfit component has no Body leader: {component.get_name()}"
            )

    configured = []
    for component in followers:
        component_spec = registry[component.get_name()]
        enabled = component.get_name() in target_names
        if enabled:
            component.set_visibility(True, False)
            component.set_hidden_in_game(False)
        else:
            component.set_visibility(False, False)
            component.set_hidden_in_game(True)
        configured.append(
            {
                "component_name": component.get_name(),
                "enabled": enabled,
                "mesh": object_path(component.get_skeletal_mesh_asset()),
                "leader_is_body": (
                    component.get_editor_property("leader_pose_component") == body
                ),
                "collision": str(component.get_collision_enabled()),
                "qualified_module_id": component_spec["qualified_module_id"],
                "module_key": component_spec["module_key"],
                "slot": component_spec.get("slot"),
            }
        )
    body_mesh_after = object_path(body.get_skeletal_mesh_asset())
    return {
        "actor": actor.get_path_name(),
        "body_mesh_before": body_mesh_before,
        "body_mesh_after": body_mesh_after,
        "body_identity_preserved": body_mesh_before == body_mesh_after,
        "body_propagates_curves": bool(
            body.get_editor_property("propagate_curves_to_followers")
        ),
        "qualified_variant_id": variant["qualified_variant_id"],
        "expected_enabled_count": variant["enabled_component_count"],
        "actual_enabled_count": sum(item["enabled"] for item in configured),
        "expected_enabled_names": sorted(target_names),
        "actual_enabled_names": sorted(
            item["component_name"] for item in configured if item["enabled"]
        ),
        "components": configured,
    }


def validate_variant_application(record: dict) -> list[str]:
    errors = []
    if not record["body_identity_preserved"]:
        errors.append("body identity changed during outfit switch")
    if not record["body_propagates_curves"]:
        errors.append("body curve propagation is disabled")
    if record["actual_enabled_count"] != record["expected_enabled_count"]:
        errors.append("enabled outfit component count differs from the runtime plan")
    if record["actual_enabled_names"] != record["expected_enabled_names"]:
        errors.append("visible outfit components differ from the runtime plan")
    for component in record["components"]:
        if not component["leader_is_body"]:
            errors.append(f"{component['component_name']} has no Body leader")
        if component["enabled"] and not component["mesh"]:
            errors.append(f"{component['component_name']} is enabled without a mesh")
        if not component["mesh"]:
            errors.append(f"{component['component_name']} has no hard-reference mesh")
        if "NO_COLLISION" not in component["collision"].upper():
            errors.append(f"{component['component_name']} owns collision")
    return errors


def run_validate_switches(bodyfit: dict) -> dict:
    blueprint = load_blueprint(bodyfit)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_subsystem.spawn_actor_from_class(
        blueprint.generated_class(), unreal.Vector(), unreal.Rotator(), transient=True
    )
    if actor is None:
        raise RuntimeError("Unable to spawn transient modular validation actor")
    transitions = []
    errors = []
    actor_path = actor.get_path_name()
    body, _followers = actor_components(actor, bodyfit)
    initial_body_component = body.get_path_name()
    initial_body_mesh = object_path(body.get_skeletal_mesh_asset())
    variants = all_variants(bodyfit)
    try:
        for source in variants:
            source_record = apply_variant(actor, bodyfit, source)
            source_errors = validate_variant_application(source_record)
            errors.extend(
                f"source {source['qualified_variant_id']}: {error}"
                for error in source_errors
            )
            for target in variants:
                record = apply_variant(actor, bodyfit, target)
                transition_errors = validate_variant_application(record)
                current_body, _followers = actor_components(actor, bodyfit)
                if current_body.get_path_name() != initial_body_component:
                    transition_errors.append("Body component identity changed")
                if object_path(current_body.get_skeletal_mesh_asset()) != initial_body_mesh:
                    transition_errors.append("Body mesh identity changed")
                transition = {
                    "source_variant_id": source["qualified_variant_id"],
                    "target_variant_id": target["qualified_variant_id"],
                    "self_transition": (
                        source["qualified_variant_id"]
                        == target["qualified_variant_id"]
                    ),
                    "application": record,
                    "errors": transition_errors,
                    "success": not transition_errors,
                }
                transitions.append(transition)
                errors.extend(
                    f"{source['qualified_variant_id']} -> "
                    f"{target['qualified_variant_id']}: {error}"
                    for error in transition_errors
                )
    finally:
        actor_subsystem.destroy_actor(actor)
    return {
        "schema_version": 1,
        "mode": "validate_switches",
        "created_at_utc": utc_now(),
        "bodyfit_id": bodyfit["bodyfit_id"],
        "sex": bodyfit["sex"],
        "blueprint": bodyfit["blueprint_path"],
        "actor_path": actor_path,
        "same_actor_for_all_variants": True,
        "initial_body_component": initial_body_component,
        "initial_body_mesh": initial_body_mesh,
        "variant_count": len(variants),
        "ordered_transition_count": len(transitions),
        "expected_ordered_transition_count": len(variants) ** 2,
        "includes_self_transitions": True,
        "transitions": transitions,
        "errors": errors,
        "validation_scope": [
            "same_actor_identity",
            "same_body_component_and_mesh",
            "registered_variant_channel_assignment",
            "shared_skeleton_precondition",
            "leader_pose_binding",
            "outfit_collision_disabled",
            "body_curve_propagation_enabled",
        ],
        "not_evaluated": [
            "animation_pose_motion_over_time",
            "morph_visual_propagation",
            "body_surface_hiding",
            "cloth_physics",
            "lod_sync",
            "visual_clipping",
            "hair_outfit_compatibility",
        ],
        "success": (
            bool(variants)
            and len(transitions) == len(variants) ** 2
            and not errors
        ),
    }


def staged_actors(bodyfit_id: str) -> list:
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    label = STAGE_LABEL_PREFIX + bodyfit_id
    return [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor.get_actor_label() == label
    ]


def run_stage_variant(bodyfit: dict, variant: dict) -> dict:
    actors = staged_actors(bodyfit["bodyfit_id"])
    if len(actors) > 1:
        raise RuntimeError("Multiple staged modular actors use the same bodyfit label")
    created = not actors
    if created:
        blueprint = load_blueprint(bodyfit)
        actor = unreal.get_editor_subsystem(
            unreal.EditorActorSubsystem
        ).spawn_actor_from_class(
            blueprint.generated_class(), unreal.Vector(), unreal.Rotator(), transient=False
        )
        if actor is None:
            raise RuntimeError("Unable to spawn staged modular outfit actor")
        actor.set_actor_label(STAGE_LABEL_PREFIX + bodyfit["bodyfit_id"])
    else:
        actor = actors[0]
    record = apply_variant(actor, bodyfit, variant)
    errors = validate_variant_application(record)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors(
        [actor]
    )
    return {
        "schema_version": 1,
        "mode": "stage_variant",
        "created_at_utc": utc_now(),
        "bodyfit_id": bodyfit["bodyfit_id"],
        "variant": variant["qualified_variant_id"],
        "actor": actor.get_path_name(),
        "actor_label": actor.get_actor_label(),
        "actor_created": created,
        "application": record,
        "errors": errors,
        "level_saved": False,
        "success": not errors,
    }


def run_cleanup_stage(bodyfit: dict) -> dict:
    actors = staged_actors(bodyfit["bodyfit_id"])
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    paths = [actor.get_path_name() for actor in actors]
    for actor in actors:
        actor_subsystem.destroy_actor(actor)
    return {
        "schema_version": 1,
        "mode": "cleanup_stage",
        "created_at_utc": utc_now(),
        "bodyfit_id": bodyfit["bodyfit_id"],
        "destroyed_actor_count": len(paths),
        "destroyed_actors": paths,
        "success": True,
    }


def required_global(name: str) -> str:
    value = globals().get(name)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{name} is required")
    return value


def main() -> dict:
    mode = globals().get("DM_MODULAR_RUNTIME_MODE", "validate_switches")
    bodyfit_id = globals().get("DM_MODULAR_BODYFIT_ID")
    variant_id = globals().get("DM_MODULAR_VARIANT_ID")
    try:
        if mode not in VALID_MODES:
            raise RuntimeError(f"Unsupported modular runtime mode: {mode}")
        if not PLAN_PATH.is_file():
            raise FileNotFoundError(str(PLAN_PATH))
        plan = read_json(PLAN_PATH)
        plan_summary = validate_runtime_plan(plan)
        bodyfit_id = required_global("DM_MODULAR_BODYFIT_ID")
        bodyfit = bodyfit_for_id(plan, bodyfit_id)
        if mode == "build_bodyfit":
            result = build_bodyfit_blueprint(bodyfit)
        elif mode == "validate_switches":
            result = run_validate_switches(bodyfit)
        elif mode == "stage_variant":
            variant_id = required_global("DM_MODULAR_VARIANT_ID")
            result = run_stage_variant(bodyfit, variant_for_id(bodyfit, variant_id))
        else:
            result = run_cleanup_stage(bodyfit)
        result["plan_summary"] = plan_summary
        report_name = (
            f"{bodyfit_id}_{mode}"
            + (f"_{variant_id.replace('::', '__')}" if variant_id else "")
            + ".json"
        )
        report_path = write_report(report_name, result)
        if result.get("success") is not True:
            raise RuntimeError(f"Modular runtime operation failed; see {report_path}")
    except Exception as exc:
        safe_bodyfit = re.sub(r"[^A-Za-z0-9_]+", "_", str(bodyfit_id or "global"))
        failure = {
            "schema_version": 1,
            "mode": mode,
            "bodyfit_id": bodyfit_id,
            "variant_id": variant_id,
            "created_at_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "success": False,
        }
        path = write_report(f"{safe_bodyfit}_{mode}_error.json", failure)
        unreal.log_error(f"DataMake modular runtime failed; see {path}: {exc}")
        print("DM_MODULAR_RUNTIME_RESULT=" + json.dumps(failure, ensure_ascii=False))
        raise
    summary = {
        "mode": mode,
        "bodyfit_id": bodyfit_id,
        "variant_id": variant_id,
        "success": result["success"],
        "report_path": str(report_path),
    }
    print("DM_MODULAR_RUNTIME_RESULT=" + json.dumps(summary, ensure_ascii=False))
    return result


if globals().get("__name__") == "__main__" or "DM_MODULAR_RUNTIME_MODE" in globals():
    main()
