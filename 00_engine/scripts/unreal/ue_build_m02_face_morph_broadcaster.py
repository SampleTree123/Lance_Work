"""Create M02 modular Blueprint v002 with a reusable face-morph broadcaster."""

from __future__ import annotations

import json
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


SOURCE_BLUEPRINT = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v001"
)
TARGET_BLUEPRINT = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
FUNCTION_NAME = "BroadcastFaceMorph"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_face_morph_broadcaster_build.json"
)
COMPONENT_VARIABLES = [
    "Body",
    "FaceEyes",
    "FaceEyeOcclusion",
    "FaceTearDucts",
    "FaceTearline",
    "FaceTeeth",
    "FaceTongue",
    "FaceBrows",
    "FaceLashesUpper",
    "FaceLashesLower",
    "FaceBeardChin",
    "FaceBeardNeck",
    "FaceMustache",
]


def find_pin(node, name):
    for pin in node.list_all_pins():
        if pin.get_pin_name() == name:
            return pin
    raise RuntimeError(f"Pin '{name}' is unavailable on {node.get_node_title()}")


def connect(output_pin, input_pin):
    if not output_pin.try_create_connection(input_pin):
        raise RuntimeError(
            f"Unable to connect {output_pin.get_pin_name()} to "
            f"{input_pin.get_pin_name()}"
        )


def only_data_pin(node):
    pins = list(node.list_all_pins())
    if len(pins) != 1:
        raise RuntimeError(
            f"Expected one data pin on {node.get_node_title()}, found {len(pins)}"
        )
    return pins[0]


source = unreal.load_asset(SOURCE_BLUEPRINT)
if not isinstance(source, unreal.Blueprint):
    raise RuntimeError(f"Source Blueprint is unavailable: {SOURCE_BLUEPRINT}")

target = unreal.load_asset(TARGET_BLUEPRINT)
created_target = False
if target is None:
    target = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_BLUEPRINT, TARGET_BLUEPRINT
    )
    created_target = True
if not isinstance(target, unreal.Blueprint):
    raise RuntimeError(f"Unable to create target Blueprint: {TARGET_BLUEPRINT}")

graph_names = {graph.get_name() for graph in BlueprintTools.list_graphs(target)}
stale_graph_names = sorted(
    name
    for name in graph_names
    if name == FUNCTION_NAME or name.startswith(f"{FUNCTION_NAME}_")
)
for stale_graph_name in stale_graph_names:
    BlueprintTools.remove_function_graph(target, stale_graph_name)

# Compile once after removal so the generated class releases the old function name.
# Without this pass, UE can silently suffix the replacement graph with ``_0``.
if stale_graph_names:
    BlueprintTools.compile_blueprint(target, warnings_as_errors=True)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(
            f"Unable to save cleaned target Blueprint: {TARGET_BLUEPRINT}"
        )

graph = BlueprintTools.add_function_graph(target, FUNCTION_NAME)
BlueprintTools.add_function_param(graph, "MorphTargetName", "name", True)
BlueprintTools.add_function_param(graph, "Value", "float", True)
BlueprintTools.add_function_param(graph, "bRemoveZeroWeight", "bool", True)

nodes = list(BlueprintTools.find_nodes(graph))
entry_nodes = [node for node in nodes if isinstance(node, unreal.K2Node_FunctionEntry)]
result_nodes = [node for node in nodes if isinstance(node, unreal.K2Node_FunctionResult)]
if len(entry_nodes) != 1:
    raise RuntimeError(f"Expected one function entry, found {len(entry_nodes)}")
if len(result_nodes) > 1:
    raise RuntimeError(f"Expected at most one function result, found {len(result_nodes)}")

entry = entry_nodes[0]
result = result_nodes[0] if result_nodes else None
created_nodes = [entry]
if result is not None:
    created_nodes.append(result)

name_pin = find_pin(entry, "MorphTargetName")
value_pin = find_pin(entry, "Value")
remove_zero_pin = find_pin(entry, "bRemoveZeroWeight")
previous_exec = find_pin(entry, "then")

for index, variable_name in enumerate(COMPONENT_VARIABLES):
    x = 300 + index * 360
    getter = BlueprintTools.create_node(
        graph,
        f"变量|默认|获取{variable_name}",
        unreal.IntPoint(x, 260),
    )
    call = BlueprintTools.create_node(
        graph,
        "组件|骨骼网格|SetMorphTarget",
        unreal.IntPoint(x, 0),
    )
    created_nodes.extend([getter, call])

    connect(previous_exec, find_pin(call, "execute"))
    connect(only_data_pin(getter), find_pin(call, "self"))
    connect(name_pin, find_pin(call, "MorphTargetName"))
    connect(value_pin, find_pin(call, "Value"))
    connect(remove_zero_pin, find_pin(call, "bRemoveZeroWeight"))
    previous_exec = find_pin(call, "then")

if result is not None:
    connect(previous_exec, find_pin(result, "execute"))

BlueprintTools.arrange_nodes(created_nodes)
BlueprintTools.compile_blueprint(target, warnings_as_errors=True)
if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save target Blueprint: {TARGET_BLUEPRINT}")

final_graph = unreal.BlueprintEditorLibrary.find_graph(target, FUNCTION_NAME)
if final_graph is None:
    available_graphs = [
        graph.get_name() for graph in BlueprintTools.list_graphs(target)
    ]
    raise RuntimeError(
        f"Compiled function graph is unavailable: {FUNCTION_NAME}; "
        f"available={available_graphs}"
    )
final_nodes = list(BlueprintTools.find_nodes(final_graph))
call_count = sum(
    1
    for node in final_nodes
    if isinstance(node, unreal.K2Node_CallFunction)
    and node.get_node_title().replace(" ", "").lower() == "setmorphtarget"
)

report = {
    "source_blueprint": source.get_path_name(),
    "target_blueprint": target.get_path_name(),
    "created_target": created_target,
    "removed_stale_graphs": stale_graph_names,
    "function": FUNCTION_NAME,
    "component_count": len(COMPONENT_VARIABLES),
    "set_morph_target_call_count": call_count,
    "component_variables": COMPONENT_VARIABLES,
    "graph_node_count": len(final_nodes),
    "success": call_count == len(COMPONENT_VARIABLES),
}
if not report["success"]:
    raise RuntimeError(
        f"Expected {len(COMPONENT_VARIABLES)} SetMorphTarget calls, found {call_count}"
    )

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print("DM_FACE_BROADCASTER=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
