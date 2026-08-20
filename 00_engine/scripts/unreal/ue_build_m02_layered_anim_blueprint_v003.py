"""Build the M02 v003 body plus hybrid facial-support AnimBlueprint."""

from __future__ import annotations

import json
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


TARGET_FOLDER = "/Game/DataMake/Animations/CC5/Pilot"
TARGET_NAME = "ABP_DM_M02_BodyFaceLayer_v003"
TARGET_PATH = f"{TARGET_FOLDER}/{TARGET_NAME}"
BODY_MESH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/"
    "_SplitPilot/cc_base_body"
)
BODY_ANIMATIONS = (
    (
        "/Game/DataMake/Animations/CC5/Pilot/"
        "A_CC_Audience_F_01_BodyOnly_v001"
    ),
    (
        "/Game/DataMake/Animations/CC5/Pilot/"
        "A_CC_Walk_Wander_M_BodyOnly_v001"
    ),
)
HYBRID_FACE_ANIMATION = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_HybridSupport_Loop_v001"
)
BODY_INDEX_VARIABLE = "BodyMotionIndex"
BRANCH_FILTER_ROOT = "cc_base_facialbone"
BRANCH_FILTER_DEPTH = 1
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_layered_anim_blueprint_v003_build.json"
)


def find_pin(node, *names):
    wanted = set(names)
    for pin in node.list_all_pins():
        if str(pin.get_pin_name()) in wanted:
            return pin
    raise RuntimeError(
        f"Pins {sorted(wanted)} are unavailable on {node.get_node_title()}: "
        + ", ".join(str(pin.get_pin_name()) for pin in node.list_all_pins())
    )


def connect(output_pin, input_pin):
    if not output_pin.try_create_connection(input_pin):
        raise RuntimeError(
            f"Unable to connect {output_pin.get_pin_name()} to "
            f"{input_pin.get_pin_name()}"
        )


def only_data_pin(node):
    pins = list(node.list_output_pins())
    if len(pins) != 1:
        raise RuntimeError(
            f"Expected one pin on {node.get_node_title()}, found {len(pins)}"
        )
    return pins[0]


def create_variable_getter(graph, variable_name, position):
    candidates = BlueprintTools.find_node_types(graph, variable_name)
    all_getter_candidates = [
        item
        for item in candidates
        if f"获取{variable_name}" in item or f"Get{variable_name}" in item
    ]
    getter_candidates = [
        item
        for item in all_getter_candidates
        if item.startswith("变量|") or item.startswith("Variable|")
    ]
    if not getter_candidates:
        raise RuntimeError(
            f"No self-variable getter node type found for {variable_name}: "
            f"{all_getter_candidates}"
        )
    attempts = []
    for type_id in getter_candidates:
        node = BlueprintTools.create_node(graph, type_id, position)
        attempts.append(
            {
                "type_id": type_id,
                "node_type": str(type(node)) if node is not None else None,
                "pins": (
                    [str(pin.get_pin_name()) for pin in node.list_all_pins()]
                    if node is not None
                    else []
                ),
            }
        )
        if isinstance(node, unreal.K2Node_VariableGet):
            return node
        if node is not None:
            BlueprintTools.delete_node(node)
    raise RuntimeError(
        f"Unable to create getter for {variable_name}: {attempts}"
    )


def create_sequence_player(graph, animation, position):
    node = BlueprintTools.create_node(
        graph, "动画|序列|序列播放器", position
    )
    if not isinstance(node, unreal.AnimGraphNode_SequencePlayer):
        raise RuntimeError(f"Unable to create sequence player for {animation}")
    anim_node = node.get_editor_property("node")
    anim_node.set_editor_property("sequence", animation)
    anim_node.set_editor_property("loop_animation", True)
    anim_node.set_editor_property("play_rate", 1.0)
    node.set_editor_property("node", anim_node)
    return node


body_assets = [unreal.load_asset(path) for path in BODY_ANIMATIONS]
hybrid_face = unreal.load_asset(HYBRID_FACE_ANIMATION)
body_mesh = unreal.load_asset(BODY_MESH)
if not all(isinstance(item, unreal.AnimSequence) for item in body_assets):
    raise RuntimeError(f"Body animation library is incomplete: {body_assets}")
if not isinstance(hybrid_face, unreal.AnimSequence):
    raise RuntimeError(f"Hybrid face animation unavailable: {HYBRID_FACE_ANIMATION}")
if not isinstance(body_mesh, unreal.SkeletalMesh):
    raise RuntimeError(f"Body mesh unavailable: {BODY_MESH}")
skeleton = body_assets[0].get_editor_property("skeleton")
if any(item.get_editor_property("skeleton") != skeleton for item in body_assets):
    raise RuntimeError("Body animations do not share one Skeleton")
if hybrid_face.get_editor_property("skeleton") != skeleton:
    raise RuntimeError("Hybrid face clip does not use the M02 Skeleton")

blueprint = unreal.load_asset(TARGET_PATH)
if blueprint is not None:
    raise RuntimeError(
        f"Refusing to rewrite existing AnimBlueprint in place: {TARGET_PATH}. "
        "Audit a completed asset separately, or remove a failed package while "
        "the editor is closed before rebuilding."
    )
factory = unreal.AnimBlueprintFactory()
factory.set_editor_property("target_skeleton", skeleton)
factory.set_editor_property("parent_class", unreal.AnimInstance)
factory.set_editor_property("preview_skeletal_mesh", body_mesh)
blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    TARGET_NAME, TARGET_FOLDER, unreal.AnimBlueprint, factory
)
created = True
if not isinstance(blueprint, unreal.AnimBlueprint):
    raise RuntimeError(f"Unable to create AnimBlueprint: {TARGET_PATH}")

BlueprintTools.add_variable(blueprint, BODY_INDEX_VARIABLE, "int")
for variable_name in (BODY_INDEX_VARIABLE,):
    BlueprintTools.set_variable_category(
        blueprint, variable_name, "DataMake|Layer Selection"
    )
    BlueprintTools.set_variable_instance_editable(
        blueprint, variable_name, True
    )

graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, "AnimGraph")
if graph is None:
    raise RuntimeError("Generated AnimBlueprint has no AnimGraph")
root_nodes = [
    node
    for node in BlueprintTools.find_nodes(graph)
    if isinstance(node, unreal.AnimGraphNode_Root)
]
if len(root_nodes) != 1:
    raise RuntimeError(f"Expected one AnimGraph root, found {len(root_nodes)}")
root = root_nodes[0]
unexpected_nodes = [
    node for node in BlueprintTools.find_nodes(graph) if node != root
]
if unexpected_nodes:
    raise RuntimeError(
        "Fresh AnimBlueprint unexpectedly contains non-root AnimGraph nodes: "
        + ", ".join(node.get_node_title() for node in unexpected_nodes)
    )

body_players = [
    create_sequence_player(
        graph, animation, unreal.IntPoint(-1050, -280 + index * 300)
    )
    for index, animation in enumerate(body_assets)
]
body_blend = BlueprintTools.create_node(
    graph,
    "Animation|Blends|按整型混合姿势",
    unreal.IntPoint(-620, -140),
)
body_pose_pins = [
    pin
    for pin in body_blend.list_all_pins()
    if str(pin.get_pin_name()).startswith("BlendPose_")
]
if len(body_pose_pins) != len(body_players):
    raise RuntimeError(
        f"Expected {len(body_players)} Body blend poses, found {len(body_pose_pins)}"
    )
body_getter = create_variable_getter(
    graph, BODY_INDEX_VARIABLE, unreal.IntPoint(-900, 390)
)

face_player = create_sequence_player(
    graph, hybrid_face, unreal.IntPoint(-620, 620)
)
layered_blend = BlueprintTools.create_node(
    graph,
    "Animation|Blends|每个骨骼的分层混合",
    unreal.IntPoint(-150, 20),
)
if not isinstance(layered_blend, unreal.AnimGraphNode_LayeredBoneBlend):
    raise RuntimeError("Unable to create Layered Blend per Bone node")

branch_filter = unreal.BranchFilter()
branch_filter.set_editor_property("bone_name", unreal.Name(BRANCH_FILTER_ROOT))
branch_filter.set_editor_property("blend_depth", BRANCH_FILTER_DEPTH)
input_pose = unreal.InputBlendPose()
input_pose.set_editor_property("branch_filters", [branch_filter])
layered_node = layered_blend.get_editor_property("node")
layered_node.set_editor_property("blend_mode", unreal.LayeredBoneBlendMode.BRANCH_FILTER)
layered_node.set_editor_property("layer_setup", [input_pose])
layered_node.set_editor_property("blend_weights", [1.0])
layered_node.set_editor_property("curve_blend_option", unreal.CurveBlendOption.OVERRIDE)
layered_node.set_editor_property("mesh_space_rotation_blend", False)
layered_node.set_editor_property("mesh_space_scale_blend", False)
layered_node.set_editor_property("root_space_rotation_blend", False)
layered_node.set_editor_property("update_base_pose_first", True)
layered_blend.set_editor_property("node", layered_node)

for index, player in enumerate(body_players):
    connect(
        find_pin(player, "Pose"),
        find_pin(body_blend, f"BlendPose_{index}"),
    )
    find_pin(body_blend, f"BlendTime_{index}").set_pin_value("0.20")
connect(only_data_pin(body_getter), find_pin(body_blend, "ActiveChildIndex"))

connect(
    find_pin(body_blend, "Pose"),
    find_pin(layered_blend, "BasePose", "Base Pose"),
)
connect(
    find_pin(face_player, "Pose"),
    find_pin(
        layered_blend,
        "BlendPose_0",
        "BlendPoses_0",
        "Blend Poses 0",
    ),
)
find_pin(
    layered_blend,
    "BlendWeight_0",
    "BlendWeights_0",
    "Blend Weights 0",
).set_pin_value("1.0")
connect(find_pin(layered_blend, "Pose"), find_pin(root, "Result"))

created_nodes = (
    body_players
    + [body_blend, body_getter, face_player, layered_blend, root]
)
BlueprintTools.arrange_nodes(created_nodes)
BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=True)
compile_status = blueprint.get_editor_property("status")
if compile_status != unreal.BlueprintStatus.BS_UP_TO_DATE:
    raise RuntimeError(
        f"v003 AnimBlueprint compile status is not up to date: {compile_status}"
    )

generated_class = blueprint.generated_class()
if generated_class is None:
    raise RuntimeError("v003 AnimBlueprint did not generate a class")
default_instance = unreal.get_default_object(generated_class)
default_instance.set_editor_property(BODY_INDEX_VARIABLE, 0)

if not unreal.EditorAssetLibrary.save_loaded_asset(
    blueprint, only_if_is_dirty=False
):
    raise RuntimeError(f"Unable to save AnimBlueprint: {TARGET_PATH}")

compiled_graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, "AnimGraph")
compiled_nodes = list(BlueprintTools.find_nodes(compiled_graph))
layered_nodes = [
    node
    for node in compiled_nodes
    if isinstance(node, unreal.AnimGraphNode_LayeredBoneBlend)
]
if len(layered_nodes) != 1:
    raise RuntimeError(
        f"Expected one Layered Bone Blend node, found {len(layered_nodes)}"
    )
compiled_layer = layered_nodes[0].get_editor_property("node")
compiled_setup = compiled_layer.get_editor_property("layer_setup")
sequence_assets = []
for node in compiled_nodes:
    if isinstance(node, unreal.AnimGraphNode_SequencePlayer):
        sequence = node.get_editor_property("node").get_editor_property("sequence")
        sequence_assets.append(sequence.get_path_name() if sequence else None)

expected_sequences = {
    asset.get_path_name() for asset in body_assets + [hybrid_face]
}
actual_sequences = {path for path in sequence_assets if path}
missing_sequences = sorted(expected_sequences - actual_sequences)
success = (
    not missing_sequences
    and len(compiled_setup) == 1
    and compile_status == unreal.BlueprintStatus.BS_UP_TO_DATE
)
report = {
    "schema_version": 1,
    "anim_blueprint": blueprint.get_path_name(),
    "created": created,
    "compile_status": str(compile_status),
    "generated_class": generated_class.get_path_name(),
    "preview_mesh": body_mesh.get_path_name(),
    "skeleton": skeleton.get_path_name(),
    "body_animations": [asset.get_path_name() for asset in body_assets],
    "hybrid_face_animation": hybrid_face.get_path_name(),
    "selector_variables": {
        BODY_INDEX_VARIABLE: {"default": 0, "values": {"0": "audience", "1": "walk_wander"}},
    },
    "layered_bone_blend": {
        "blend_mode": str(compiled_layer.get_editor_property("blend_mode")),
        "branch_filter_root": BRANCH_FILTER_ROOT,
        "branch_filter_depth": BRANCH_FILTER_DEPTH,
        "fixed_layer_alpha": 1.0,
        "curve_blend_option": str(
            compiled_layer.get_editor_property("curve_blend_option")
        ),
        "mesh_space_rotation_blend": compiled_layer.get_editor_property(
            "mesh_space_rotation_blend"
        ),
        "update_base_pose_first": compiled_layer.get_editor_property(
            "update_base_pose_first"
        ),
        "layer_count": len(compiled_setup),
    },
    "sequence_players": sorted(actual_sequences),
    "missing_sequences": missing_sequences,
    "node_counts": {
        "sequence_player": sum(
            isinstance(node, unreal.AnimGraphNode_SequencePlayer)
            for node in compiled_nodes
        ),
        "blend_by_int": sum(
            isinstance(node, unreal.AnimGraphNode_BlendListByInt)
            for node in compiled_nodes
        ),
        "layered_bone_blend": len(layered_nodes),
    },
    "success": success,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
if not success:
    raise RuntimeError("v003 AnimBlueprint verification failed")
print(
    "DM_LAYERED_ANIM_BLUEPRINT_V003="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "anim_blueprint": blueprint.get_path_name(),
            "node_counts": report["node_counts"],
            "success": success,
        },
        sort_keys=True,
    )
)
