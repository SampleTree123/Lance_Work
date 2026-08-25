"""Build runtime-selectable first-batch expression layers and review wrappers."""

from __future__ import annotations

import json
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


TARGET = str(globals().get("DM_FIRST_BATCH_EXPRESSION_TARGET", "legacy"))
if TARGET == "canonical":
    ANIMATION_ROOT = "/Game/DataMake/Animations/CC5/FirstDataBatch/Expressions"
    CHARACTER_ROOT = "/Game/DataMake/Characters/FirstDataBatch/ExpressionReview"
    REPORT_PATH = Path(
        r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
        r"\first_batch_day2_20260822_v1\canonical_expression_composition.json"
    )
else:
    ANIMATION_ROOT = "/Game/DataMake/Animations/CC5/FirstBatchExpressions"
    CHARACTER_ROOT = "/Game/DataMake/Characters/FirstBatchExpressionReview"
    REPORT_PATH = Path(
        r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
        r"\first_batch_expressions_20260820_v1\runtime_composition_build.json"
    )
EXPRESSION_PAIR_VARIABLE = "ExpressionPairIndex"
EXPRESSION_VARIANT_VARIABLE = "ExpressionVariantIndex"

ACTORS = {
    "F02": {
        "mesh": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/F02/FullReference/"
            "F02_Clothed"
        ),
        "body_animation": (
            "/Game/DataMake/Animations/CC5/P0RuntimePilot/F02/"
            "A_CC_P0_Idle_F_InPlace_v001"
        ),
    },
    "M02": {
        "mesh": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/M02/FullReference/"
            "M02_Clothed"
        ),
        "body_animation": (
            "/Game/DataMake/Animations/CC5/P0RuntimePilot/M02/"
            "A_CC_P0_Understood_M_InPlace_v001"
        ),
    },
}
if TARGET == "canonical":
    ACTORS = {
        "FB_F": {
            "mesh": (
                "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/F_ID01_O01/"
                "CC_FB_F_ID01_O01"
            ),
            "body_animation": (
                "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/BodyOnly/"
                "A_DM_F03_AUDIENCE_01_BodyOnly_v001"
            ),
        },
        "FB_M": {
            "mesh": (
                "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/M_ID01_O01/"
                "CC_FB_M_ID01_O01"
            ),
            "body_animation": (
                "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/BodyOnly/"
                "A_DM_M02_AUDIENCE_01_BodyOnly_v001"
            ),
        },
    }

EXPRESSIONS = (
    ("happy", "Happy_SubtleDynamic_v001"),
    ("angry", "Angry_SubtleDynamic_v001"),
    ("sad", "Sad_SubtleDynamic_v001"),
)

if TARGET == "canonical":
    # Wrappers reference AnimBlueprints, so remove them in dependency order.
    for actor_id in ACTORS:
        wrapper_path = (
            f"{CHARACTER_ROOT}/{actor_id}/"
            f"BP_DM_{actor_id}_FirstBatchExpressionReview_v001"
        )
        if unreal.EditorAssetLibrary.does_asset_exist(wrapper_path):
            if not unreal.EditorAssetLibrary.delete_asset(wrapper_path):
                raise RuntimeError(f"Unable to replace wrapper: {wrapper_path}")
    for actor_id in ACTORS:
        blueprint_path = (
            f"{ANIMATION_ROOT}/{actor_id}/"
            f"ABP_DM_{actor_id}_FirstBatchExpressionReview_v001"
        )
        if unreal.EditorAssetLibrary.does_asset_exist(blueprint_path):
            if not unreal.EditorAssetLibrary.delete_asset(blueprint_path):
                raise RuntimeError(
                    f"Unable to replace AnimBlueprint: {blueprint_path}"
                )


def get_data(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)


def get_component(handle):
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(
        get_data(handle)
    )


def find_pin(node, *names):
    wanted = set(names)
    for pin in node.list_all_pins():
        if str(pin.get_pin_name()) in wanted:
            return pin
    raise RuntimeError(
        f"Pins {sorted(wanted)} unavailable on {node.get_node_title()}"
    )


def only_output_pin(node):
    pins = list(node.list_output_pins())
    if len(pins) != 1:
        raise RuntimeError(
            f"Expected one output on {node.get_node_title()}, found {len(pins)}"
        )
    return pins[0]


def connect(output_pin, input_pin):
    if not output_pin.try_create_connection(input_pin):
        raise RuntimeError(
            f"Unable to connect {output_pin.get_pin_name()} to "
            f"{input_pin.get_pin_name()}"
        )


def create_node_of_class(graph, filters, expected_class, position):
    candidates = []
    for query in filters:
        for type_id in BlueprintTools.find_node_types(graph, query):
            if type_id not in candidates:
                candidates.append(type_id)
    attempts = []
    for type_id in candidates:
        node = BlueprintTools.create_node(graph, type_id, position)
        attempts.append({"type_id": type_id, "class": str(type(node))})
        if isinstance(node, expected_class):
            return node
        BlueprintTools.delete_node(node)
    raise RuntimeError(
        f"Unable to create {expected_class.__name__}; attempts={attempts}"
    )


def create_variable_getter(graph, variable_name, position):
    candidates = BlueprintTools.find_node_types(graph, variable_name)
    getter_candidates = [
        type_id
        for type_id in candidates
        if (
            f"Get{variable_name}" in type_id
            or f"\u83b7\u53d6{variable_name}" in type_id
        )
        and (
            type_id.startswith("Variable|")
            or type_id.startswith("\u53d8\u91cf|")
        )
    ]
    for type_id in getter_candidates:
        node = BlueprintTools.create_node(graph, type_id, position)
        if isinstance(node, unreal.K2Node_VariableGet):
            return node
        BlueprintTools.delete_node(node)
    raise RuntimeError(
        f"No self-variable getter node found for {variable_name}: "
        f"{getter_candidates}"
    )


def create_sequence_player(graph, animation, position):
    node = create_node_of_class(
        graph,
        (
            "Animation|Sequence|Sequence Player",
            "\u52a8\u753b|\u5e8f\u5217|\u5e8f\u5217\u64ad\u653e\u5668",
            "Sequence Player",
        ),
        unreal.AnimGraphNode_SequencePlayer,
        position,
    )
    anim_node = node.get_editor_property("node")
    anim_node.set_editor_property("sequence", animation)
    anim_node.set_editor_property("loop_animation", True)
    anim_node.set_editor_property("play_rate", 1.0)
    node.set_editor_property("node", anim_node)
    return node


def create_blend_by_int(graph, position):
    node = create_node_of_class(
        graph,
        (
            "Animation|Blends|Blend Poses by int",
            "Animation|Blends|\u6309\u6574\u578b\u6df7\u5408\u59ff\u52bf",
            "Blend Poses by int",
        ),
        unreal.AnimGraphNode_BlendListByInt,
        position,
    )
    actual = sum(
        str(pin.get_pin_name()).startswith("BlendPose_")
        for pin in node.list_all_pins()
    )
    if actual != 2:
        raise RuntimeError(f"Expected two blend poses, found {actual}")
    return node


def create_apply_additive(graph, position):
    return create_node_of_class(
        graph,
        (
            "Animation|Blends|Apply Additive",
            "Animation|Blends|\u5e94\u7528Additive\u52a8\u753b",
            "Apply Additive",
        ),
        unreal.AnimGraphNode_ApplyAdditive,
        position,
    )


def build_anim_blueprint(actor_id, mesh, body_animation, expression_assets):
    folder = f"{ANIMATION_ROOT}/{actor_id}"
    name = f"ABP_DM_{actor_id}_FirstBatchExpressionReview_v001"
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if TARGET != "canonical" or not unreal.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError(f"Refusing to overwrite existing AnimBlueprint: {path}")

    skeleton = body_animation.get_editor_property("skeleton")
    factory = unreal.AnimBlueprintFactory()
    factory.set_editor_property("target_skeleton", skeleton)
    factory.set_editor_property("parent_class", unreal.AnimInstance)
    factory.set_editor_property("preview_skeletal_mesh", mesh)
    blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.AnimBlueprint, factory
    )
    if not isinstance(blueprint, unreal.AnimBlueprint):
        raise RuntimeError(f"Unable to create AnimBlueprint: {path}")

    for variable_name in (
        EXPRESSION_PAIR_VARIABLE,
        EXPRESSION_VARIANT_VARIABLE,
    ):
        BlueprintTools.add_variable(blueprint, variable_name, "int")
        BlueprintTools.set_variable_category(
            blueprint,
            variable_name,
            "DataMake|First Batch Selection",
        )
        BlueprintTools.set_variable_instance_editable(
            blueprint, variable_name, True
        )

    graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, "AnimGraph")
    roots = [
        node
        for node in BlueprintTools.find_nodes(graph)
        if isinstance(node, unreal.AnimGraphNode_Root)
    ]
    if len(roots) != 1:
        raise RuntimeError(f"Expected one AnimGraph root, found {len(roots)}")
    root = roots[0]

    body_player = create_sequence_player(
        graph, body_animation, unreal.IntPoint(-1100, -160)
    )
    expanded_expression_assets = [
        expression_assets[0],
        expression_assets[1],
        expression_assets[2],
        expression_assets[2],
    ]
    face_players = [
        create_sequence_player(
            graph, asset, unreal.IntPoint(-1100, 260 + index * 260)
        )
        for index, asset in enumerate(expanded_expression_assets)
    ]
    face_pair_blends = [
        create_blend_by_int(
            graph, unreal.IntPoint(-680, 430 + pair_index * 620)
        )
        for pair_index in range(2)
    ]
    face_group_blend = create_blend_by_int(graph, unreal.IntPoint(-370, 730))
    pair_getter = create_variable_getter(
        graph, EXPRESSION_PAIR_VARIABLE, unreal.IntPoint(-620, 1370)
    )
    variant_getters = [
        create_variable_getter(
            graph,
            EXPRESSION_VARIANT_VARIABLE,
            unreal.IntPoint(-930, 690 + pair_index * 620),
        )
        for pair_index in range(2)
    ]
    apply_additive = create_apply_additive(graph, unreal.IntPoint(-120, 60))

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
            only_output_pin(variant_getters[pair_index]),
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
        only_output_pin(pair_getter),
        find_pin(face_group_blend, "ActiveChildIndex"),
    )
    connect(find_pin(body_player, "Pose"), find_pin(apply_additive, "Base"))
    connect(
        find_pin(face_group_blend, "Pose"),
        find_pin(apply_additive, "Additive"),
    )
    find_pin(apply_additive, "Alpha").set_pin_value("1.0")
    connect(find_pin(apply_additive, "Pose"), find_pin(root, "Result"))

    BlueprintTools.arrange_nodes(
        [
            body_player,
            *face_players,
            *face_pair_blends,
            face_group_blend,
            pair_getter,
            *variant_getters,
            apply_additive,
            root,
        ]
    )
    BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=True)
    status = blueprint.get_editor_property("status")
    if status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError(f"AnimBlueprint compile failed: {status}")

    default_instance = unreal.get_default_object(blueprint.generated_class())
    default_instance.set_editor_property(EXPRESSION_PAIR_VARIABLE, 0)
    default_instance.set_editor_property(EXPRESSION_VARIANT_VARIABLE, 0)
    default_instance.set_editor_property(
        "root_motion_mode", unreal.RootMotionMode.ROOT_MOTION_FROM_EVERYTHING
    )
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        blueprint, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save AnimBlueprint: {path}")
    return blueprint, {
        "asset": blueprint.get_path_name(),
        "compile_status": str(status),
        "default_selection": {
            EXPRESSION_PAIR_VARIABLE: 0,
            EXPRESSION_VARIANT_VARIABLE: 0,
        },
    }


def build_wrapper(actor_id, mesh, anim_blueprint):
    folder = f"{CHARACTER_ROOT}/{actor_id}"
    name = f"BP_DM_{actor_id}_FirstBatchExpressionReview_v001"
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if TARGET != "canonical" or not unreal.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError(f"Refusing to overwrite existing wrapper: {path}")

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.Blueprint, factory
    )
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"Unable to create wrapper: {path}")

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
        raise RuntimeError("Wrapper Blueprint has no scene root")
    handle, failure_reason = subsystem.add_new_subobject(
        unreal.AddNewSubobjectParams(
            parent_handle=root_handle,
            new_class=unreal.SkeletalMeshComponent,
            blueprint_context=blueprint,
        )
    )
    if not failure_reason.is_empty():
        raise RuntimeError(f"Unable to add Body component: {failure_reason}")
    if not subsystem.rename_subobject(handle=handle, new_name=unreal.Text("Body")):
        raise RuntimeError("Unable to rename Body component")
    body = get_component(handle)
    if not isinstance(body, unreal.SkeletalMeshComponent):
        raise RuntimeError(f"Unexpected Body component: {body}")
    body.set_skeletal_mesh_asset(mesh)
    body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    body.set_update_animation_in_editor(True)
    body.set_allow_anim_curve_evaluation(True)
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    body.set_anim_instance_class(anim_blueprint.generated_class())
    body.set_editor_property("component_use_fixed_skel_bounds", False)
    body.set_editor_property("disable_post_process_blueprint", True)

    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    status = blueprint.get_editor_property("status")
    if status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError(f"Wrapper compile failed: {status}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        blueprint, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save wrapper: {path}")
    return blueprint, {
        "asset": blueprint.get_path_name(),
        "compile_status": str(status),
        "disable_post_process_blueprint": True,
    }


REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
records = []
for actor_id, actor_spec in ACTORS.items():
    mesh = unreal.load_asset(actor_spec["mesh"])
    body_animation = unreal.load_asset(actor_spec["body_animation"])
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Missing review mesh: {actor_spec['mesh']}")
    if not isinstance(body_animation, unreal.AnimSequence):
        raise RuntimeError(
            f"Missing review body animation: {actor_spec['body_animation']}"
        )
    skeleton = body_animation.get_editor_property("skeleton")
    if mesh.get_editor_property("skeleton") != skeleton:
        raise RuntimeError(f"Mesh/body Skeleton mismatch for {actor_id}")

    expression_assets = []
    expression_records = []
    for expression_id, suffix in EXPRESSIONS:
        path = f"{ANIMATION_ROOT}/{actor_id}/A_DM_{actor_id}_Face_{suffix}"
        asset = unreal.load_asset(path)
        if not isinstance(asset, unreal.AnimSequence):
            raise RuntimeError(f"Missing expression asset: {path}")
        if asset.get_editor_property("skeleton") != skeleton:
            raise RuntimeError(
                f"Expression Skeleton mismatch for {actor_id}/{expression_id}"
            )
        expression_assets.append(asset)
        expression_index = len(expression_records)
        expression_records.append(
            {
                "expression_id": expression_id,
                "index": expression_index,
                "pair_index": expression_index // 2,
                "variant_index": expression_index % 2,
                "asset": asset.get_path_name(),
            }
        )

    anim_blueprint, anim_record = build_anim_blueprint(
        actor_id, mesh, body_animation, expression_assets
    )
    wrapper, wrapper_record = build_wrapper(actor_id, mesh, anim_blueprint)
    records.append(
        {
            "actor_id": actor_id,
            "mesh": mesh.get_path_name(),
            "skeleton": skeleton.get_path_name(),
            "body_animation": body_animation.get_path_name(),
            "expressions": expression_records,
            "anim_blueprint": anim_record,
            "wrapper": wrapper_record,
        }
    )

report = {
    "schema_version": 1,
    "target": TARGET,
    "runtime_scope": (
        "first_batch_canonical_body_plus_direct_morph_expression"
        if TARGET == "canonical"
        else "full_reference_body_plus_direct_morph_expression"
    ),
    "selectors": [EXPRESSION_PAIR_VARIABLE, EXPRESSION_VARIANT_VARIABLE],
    "records": records,
    "actor_count": len(records),
    "expression_count": sum(len(item["expressions"]) for item in records),
    "success": len(records) == 2,
    "visual_review": "pending",
    "production_status": "not_approved",
}
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("DM_FIRST_BATCH_EXPRESSION_COMPOSITION=" + json.dumps(report, ensure_ascii=False))
