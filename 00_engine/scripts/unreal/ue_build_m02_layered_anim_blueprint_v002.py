"""Build the v002 selectable M02 body/face layered AnimBlueprint."""

from __future__ import annotations

import gc
import json
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


TARGET_FOLDER = "/Game/DataMake/Animations/CC5/Pilot"
TARGET_NAME = "ABP_DM_M02_BodyFaceLayer_v002"
TARGET_PATH = f"{TARGET_FOLDER}/{TARGET_NAME}"
BODY_MESH = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/"
    "_SplitPilot/cc_base_body"
)
BODY_ANIMATIONS = [
    (
        "/Game/DataMake/Animations/CC5/Pilot/"
        "A_CC_Audience_F_01_BodyOnly_v001"
    ),
    (
        "/Game/DataMake/Animations/CC5/Pilot/"
        "A_CC_Walk_Wander_M_BodyOnly_v001"
    ),
]
FACE_ANIMATIONS = [
    (
        "/Game/DataMake/Animations/CC5/Pilot/Face/"
        "A_DM_M02_Face_Neutral_Loop_v001"
    ),
    (
        "/Game/DataMake/Animations/CC5/Pilot/Face/"
        "A_DM_M02_Face_NaturalBlink_Loop_v001"
    ),
    (
        "/Game/DataMake/Animations/CC5/Pilot/Face/"
        "A_DM_M02_Face_BlinkGaze_Loop_v001"
    ),
    (
        "/Game/DataMake/Animations/CC5/Pilot/Face/"
        "A_DM_M02_Face_SubtleSmile_Loop_v001"
    ),
]
BODY_INDEX_VARIABLE = "BodyMotionIndex"
FACE_PAIR_VARIABLE = "FacePairIndex"
FACE_VARIANT_VARIABLE = "FaceVariantIndex"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_layered_anim_blueprint_v002_build.json"
)


def find_pin(node, name):
    for pin in node.list_all_pins():
        if str(pin.get_pin_name()) == name:
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
            f"Expected one pin on {node.get_node_title()}, found {len(pins)}"
        )
    return pins[0]


def create_variable_getter(graph, variable_name, position):
    candidates = BlueprintTools.find_node_types(graph, variable_name)
    getter_candidates = [
        item
        for item in candidates
        if f"获取{variable_name}" in item or f"Get{variable_name}" in item
    ]
    if not getter_candidates:
        raise RuntimeError(
            f"No getter node type found for {variable_name}: {candidates}"
        )
    for type_id in getter_candidates:
        node = BlueprintTools.create_node(graph, type_id, position)
        if isinstance(node, unreal.K2Node_VariableGet):
            return node
        if node is not None:
            BlueprintTools.delete_node(node)
    raise RuntimeError(f"Unable to create getter for {variable_name}")


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


def require_pose_count(node, pose_count):
    current_count = len(
        [
            pin
            for pin in node.list_all_pins()
            if str(pin.get_pin_name()).startswith("BlendPose_")
        ]
    )
    if current_count != pose_count:
        raise RuntimeError(
            f"Expected {pose_count} poses on {node.get_node_title()}, "
            f"found {current_count}"
        )


body_assets = [unreal.load_asset(path) for path in BODY_ANIMATIONS]
face_assets = [unreal.load_asset(path) for path in FACE_ANIMATIONS]
if not all(isinstance(item, unreal.AnimSequence) for item in body_assets):
    raise RuntimeError(f"Body animation library is incomplete: {body_assets}")
if not all(isinstance(item, unreal.AnimSequence) for item in face_assets):
    raise RuntimeError(f"Face animation library is incomplete: {face_assets}")
body_mesh = unreal.load_asset(BODY_MESH)
if not isinstance(body_mesh, unreal.SkeletalMesh):
    raise RuntimeError(f"Body mesh is unavailable: {BODY_MESH}")
skeleton = body_assets[0].get_editor_property("skeleton")

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_PATH):
    raise RuntimeError(
        f"Generated AnimBlueprint already exists; refusing in-place rebuild: {TARGET_PATH}"
    )

factory = unreal.AnimBlueprintFactory()
factory.set_editor_property("target_skeleton", skeleton)
factory.set_editor_property("parent_class", unreal.AnimInstance)
factory.set_editor_property("preview_skeletal_mesh", body_mesh)
blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    TARGET_NAME, TARGET_FOLDER, unreal.AnimBlueprint, factory
)
if not isinstance(blueprint, unreal.AnimBlueprint):
    raise RuntimeError(f"Unable to create AnimBlueprint: {TARGET_PATH}")

BlueprintTools.add_variable(blueprint, BODY_INDEX_VARIABLE, "int")
BlueprintTools.add_variable(blueprint, FACE_PAIR_VARIABLE, "int")
BlueprintTools.add_variable(blueprint, FACE_VARIANT_VARIABLE, "int")
BlueprintTools.set_variable_category(
    blueprint, BODY_INDEX_VARIABLE, "DataMake|Layer Selection"
)
BlueprintTools.set_variable_category(
    blueprint, FACE_PAIR_VARIABLE, "DataMake|Layer Selection"
)
BlueprintTools.set_variable_category(
    blueprint, FACE_VARIANT_VARIABLE, "DataMake|Layer Selection"
)
for variable_name in (
    BODY_INDEX_VARIABLE,
    FACE_PAIR_VARIABLE,
    FACE_VARIANT_VARIABLE,
):
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

body_players = [
    create_sequence_player(
        graph, animation, unreal.IntPoint(-1200, -500 + index * 260)
    )
    for index, animation in enumerate(body_assets)
]
body_blend = BlueprintTools.create_node(
    graph,
    "Animation|Blends|按整型混合姿势",
    unreal.IntPoint(-720, -370),
)
require_pose_count(body_blend, len(body_players))
body_getter = create_variable_getter(
    graph, BODY_INDEX_VARIABLE, unreal.IntPoint(-1020, 110)
)

face_players = [
    create_sequence_player(
        graph, animation, unreal.IntPoint(-1200, 380 + index * 250)
    )
    for index, animation in enumerate(face_assets)
]
face_pair_blends = [
    BlueprintTools.create_node(
        graph,
        "Animation|Blends|按整型混合姿势",
        unreal.IntPoint(-720, 500 + pair_index * 650),
    )
    for pair_index in range(2)
]
for node in face_pair_blends:
    require_pose_count(node, 2)
face_group_blend = BlueprintTools.create_node(
    graph,
    "Animation|Blends|按整型混合姿势",
    unreal.IntPoint(-360, 800),
)
require_pose_count(face_group_blend, 2)
face_pair_getter = create_variable_getter(
    graph, FACE_PAIR_VARIABLE, unreal.IntPoint(-700, 1390)
)
face_variant_getters = [
    create_variable_getter(
        graph,
        FACE_VARIANT_VARIABLE,
        unreal.IntPoint(-1020, 760 + pair_index * 650),
    )
    for pair_index in range(2)
]

apply_additive = BlueprintTools.create_node(
    graph,
    "Animation|Blends|应用Additive动画",
    unreal.IntPoint(-250, 0),
)

for index, player in enumerate(body_players):
    connect(find_pin(player, "Pose"), find_pin(body_blend, f"BlendPose_{index}"))
    find_pin(body_blend, f"BlendTime_{index}").set_pin_value("0.20")
connect(only_data_pin(body_getter), find_pin(body_blend, "ActiveChildIndex"))

for pair_index, pair_blend in enumerate(face_pair_blends):
    for variant_index in range(2):
        player_index = pair_index * 2 + variant_index
        connect(
            find_pin(face_players[player_index], "Pose"),
            find_pin(pair_blend, f"BlendPose_{variant_index}"),
        )
        find_pin(pair_blend, f"BlendTime_{variant_index}").set_pin_value(
            "0.12"
        )
    connect(
        only_data_pin(face_variant_getters[pair_index]),
        find_pin(pair_blend, "ActiveChildIndex"),
    )
    connect(
        find_pin(pair_blend, "Pose"),
        find_pin(face_group_blend, f"BlendPose_{pair_index}"),
    )
    find_pin(face_group_blend, f"BlendTime_{pair_index}").set_pin_value(
        "0.12"
    )
connect(
    only_data_pin(face_pair_getter),
    find_pin(face_group_blend, "ActiveChildIndex"),
)

connect(find_pin(body_blend, "Pose"), find_pin(apply_additive, "Base"))
connect(find_pin(face_group_blend, "Pose"), find_pin(apply_additive, "Additive"))
find_pin(apply_additive, "Alpha").set_pin_value("1.0")
connect(find_pin(apply_additive, "Pose"), find_pin(root, "Result"))

created_nodes = (
    body_players
    + [body_blend, body_getter]
    + face_players
    + face_pair_blends
    + face_variant_getters
    + [face_group_blend, face_pair_getter, apply_additive, root]
)
BlueprintTools.arrange_nodes(created_nodes)
BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=True)
if not unreal.EditorAssetLibrary.save_loaded_asset(
    blueprint, only_if_is_dirty=False
):
    raise RuntimeError(f"Unable to save AnimBlueprint: {TARGET_PATH}")

compiled_graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, "AnimGraph")
compiled_nodes = list(BlueprintTools.find_nodes(compiled_graph))
sequence_records = []
for node in compiled_nodes:
    if isinstance(node, unreal.AnimGraphNode_SequencePlayer):
        animation = node.get_editor_property("node").get_editor_property("sequence")
        sequence_records.append(animation.get_path_name() if animation else None)

expected_sequences = {
    item.get_path_name() for item in body_assets + face_assets
}
actual_sequences = {item for item in sequence_records if item}
missing_sequences = sorted(expected_sequences - actual_sequences)
report = {
    "schema_version": 1,
    "anim_blueprint": blueprint.get_path_name(),
    "generated_class": blueprint.generated_class().get_path_name(),
    "preview_mesh": body_mesh.get_path_name(),
    "skeleton": skeleton.get_path_name(),
    "selector_variables": {
        BODY_INDEX_VARIABLE: {
            "default": 0,
            "values": {
                str(index): asset.get_path_name()
                for index, asset in enumerate(body_assets)
            },
        },
        FACE_PAIR_VARIABLE: {
            "default": 0,
            "values": {
                "0": "neutral / natural_blink pair",
                "1": "blink_gaze / subtle_smile pair",
            },
        },
        FACE_VARIANT_VARIABLE: {
            "default": 0,
            "values": {"0": "first clip in pair", "1": "second clip in pair"},
        },
    },
    "face_selector_mapping": {
        "0": {"pair": 0, "variant": 0, "asset": face_assets[0].get_path_name()},
        "1": {"pair": 0, "variant": 1, "asset": face_assets[1].get_path_name()},
        "2": {"pair": 1, "variant": 0, "asset": face_assets[2].get_path_name()},
        "3": {"pair": 1, "variant": 1, "asset": face_assets[3].get_path_name()},
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
        "apply_additive": sum(
            isinstance(node, unreal.AnimGraphNode_ApplyAdditive)
            for node in compiled_nodes
        ),
    },
    "runtime_boundary": {
        "anim_blueprint": (
            "Owns continuous body selection, reusable face-loop selection, "
            "and additive composition."
        ),
        "sequencer": (
            "Owns shot timing, selector changes, actor transforms, cameras, "
            "and render orchestration."
        ),
    },
    "success": not missing_sequences,
}
if not report["success"]:
    raise RuntimeError(f"AnimBlueprint lost sequence references: {missing_sequences}")
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    "DM_LAYERED_ANIM_BLUEPRINT="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "anim_blueprint": report["anim_blueprint"],
            "node_counts": report["node_counts"],
            "success": report["success"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
