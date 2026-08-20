"""Build the modular Blueprint's explicit Leader Pose construction graph."""

import json
from pathlib import Path
import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


BLUEPRINT_PATH = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v001"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_modular_construction_graph.json"
)
FOLLOWER_VARIABLES = [
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
    "OutfitTop",
    "OutfitBottom",
    "OutfitShoes",
    "HairBangs",
    "HairMullet",
    "HairBackLeft",
    "HairBackRight",
]


def find_pin(node, name):
    for pin in node.list_all_pins():
        if pin.get_pin_name() == name:
            return pin
    raise RuntimeError(f"Pin '{name}' is unavailable on {node.get_node_title()}")


def connect(output_pin, input_pin):
    if not output_pin.try_create_connection(input_pin):
        raise RuntimeError(
            f"Unable to connect {output_pin.get_pin_name()} to {input_pin.get_pin_name()}"
        )


def only_pin(node):
    pins = list(node.list_all_pins())
    if len(pins) != 1:
        raise RuntimeError(
            f"Expected one data pin on {node.get_node_title()}, found {len(pins)}"
        )
    return pins[0]


blueprint = unreal.load_asset(BLUEPRINT_PATH)
if not isinstance(blueprint, unreal.Blueprint):
    raise RuntimeError(f"Modular Blueprint is unavailable: {BLUEPRINT_PATH}")

graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, "UserConstructionScript")
if graph is None:
    raise RuntimeError("UserConstructionScript graph is unavailable")
graph_editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
if graph_editor is None:
    raise RuntimeError("Unable to open the construction graph editor interface")

nodes = list(BlueprintTools.find_nodes(graph))
entry_nodes = [
    node for node in nodes if isinstance(node, unreal.K2Node_FunctionEntry)
]
if len(entry_nodes) != 1:
    raise RuntimeError(f"Expected one construction entry node, found {len(entry_nodes)}")
entry = entry_nodes[0]

stale_nodes = [node for node in nodes if node != entry]
if stale_nodes:
    graph_editor.remove_nodes(stale_nodes)

# Template weak references do not remap to actor instances. The construction graph
# below owns the binding, so clear the template-only references first.
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for handle in sds.k2_gather_subobject_data_for_blueprint(blueprint):
    data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
    obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
    if isinstance(obj, unreal.SkeletalMeshComponent) and obj.get_name() != "Body_GEN_VARIABLE":
        obj.set_leader_pose_component(None, force_update=True)

created_nodes = [entry]
body_getter = BlueprintTools.create_node(
    graph,
    "变量|默认|获取Body",
    unreal.IntPoint(-350, 0),
)
created_nodes.append(body_getter)
body_output = only_pin(body_getter)
previous_exec = find_pin(entry, "then")

for index, variable_name in enumerate(FOLLOWER_VARIABLES):
    x = 250 + index * 360
    follower_getter = BlueprintTools.create_node(
        graph,
        f"变量|默认|获取{variable_name}",
        unreal.IntPoint(x, 220),
    )
    call = BlueprintTools.create_node(
        graph,
        "组件|蒙皮网格|SetLeaderPoseComponent",
        unreal.IntPoint(x, 0),
    )
    created_nodes.extend([follower_getter, call])

    follower_output = only_pin(follower_getter)
    connect(
        previous_exec,
        find_pin(call, "execute"),
    )
    connect(
        follower_output,
        find_pin(call, "self"),
    )
    connect(
        body_output,
        find_pin(
            call,
            "NewLeaderBoneComponent",
        ),
    )
    find_pin(
        call, "bForceUpdate"
    ).set_pin_value("true")
    find_pin(
        call,
        "bInFollowerShouldTickPose",
    ).set_pin_value("false")
    previous_exec = find_pin(call, "then")

BlueprintTools.arrange_nodes(created_nodes)
unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
if not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save Blueprint: {BLUEPRINT_PATH}")

report = {
    "blueprint": blueprint.get_path_name(),
    "graph": graph.get_path_name(),
    "follower_binding_count": len(FOLLOWER_VARIABLES),
    "node_count": len(BlueprintTools.find_nodes(graph)),
    "followers": FOLLOWER_VARIABLES,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DM_MODULAR_CONSTRUCTION_GRAPH="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "follower_binding_count": report["follower_binding_count"],
            "node_count": report["node_count"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
