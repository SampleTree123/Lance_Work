"""Build P0 face clips, layered AnimBlueprints, and DataMake wrappers."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_build_p0_runtime_composition.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


import json
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


OUTPUT_ROOT = "/Game/DataMake/Animations/CC5/P0RuntimePilot"
CHARACTER_ROOT = "/Game/DataMake/Characters/P0RuntimePilot"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\p0_runtime_pilot_20260819_v1\runtime_composition_build.json"
)

ACTORS = {
    "F02": {
        "mesh": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/F02/FullReference/"
            "F02_Clothed"
        ),
        "body_animations": (
            {
                "id": "walk",
                "path": f"{OUTPUT_ROOT}/F02/A_CC_P0_Walk_F_Root_v001",
                "loop": False,
            },
            {
                "id": "idle",
                "path": f"{OUTPUT_ROOT}/F02/A_CC_P0_Idle_F_InPlace_v001",
                "loop": True,
            },
        ),
    },
    "M02": {
        "mesh": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/M02/FullReference/"
            "M02_Clothed"
        ),
        "body_animations": (
            {
                "id": "walk",
                "path": f"{OUTPUT_ROOT}/M02/A_CC_P0_Walk_M_Root_v001",
                "loop": False,
            },
            {
                "id": "understood",
                "path": f"{OUTPUT_ROOT}/M02/A_CC_P0_Understood_M_InPlace_v001",
                "loop": False,
            },
        ),
    },
}

BLINK_L = "CTRL_expressions_eyeBlinkL"
BLINK_R = "CTRL_expressions_eyeBlinkR"
SMILE_L = "CTRL_expressions_mouthCornerPullL"
SMILE_R = "CTRL_expressions_mouthCornerPullR"

BLINK_KEYS = (
    (
        0.0,
        0.17,
        0.20,
        0.22,
        0.31,
        0.35,
        0.60,
        0.63,
        0.65,
        0.74,
        0.78,
        1.0,
    ),
    (0.0, 0.0, 0.55, 1.0, 1.0, 0.0, 0.0, 0.50, 1.0, 1.0, 0.0, 0.0),
)

ASYMMETRIC_BLINK_KEYS = (
    (0.0, 0.14, 0.20, 0.24, 0.48, 0.54, 1.0),
    (0.0, 0.0, 0.65, 1.0, 1.0, 0.0, 0.0),
)

FACE_SPECS = (
    {"id": "neutral", "suffix": "Neutral_Loop", "curves": {}},
    {
        "id": "natural_blink",
        "suffix": "NaturalBlink_Loop",
        "curves": {BLINK_L: BLINK_KEYS, BLINK_R: BLINK_KEYS},
    },
    {
        "id": "asymmetric_blink",
        "suffix": "AsymmetricBlink_Loop",
        "curves": {BLINK_L: ASYMMETRIC_BLINK_KEYS},
    },
    {
        "id": "subtle_smile",
        "suffix": "SubtleSmile_Loop",
        "curves": {
            SMILE_L: (
                (0.0, 0.14, 0.30, 0.72, 0.88, 1.0),
                (0.0, 0.0, 0.30, 0.30, 0.0, 0.0),
            ),
            SMILE_R: (
                (0.0, 0.14, 0.30, 0.72, 0.88, 1.0),
                (0.0, 0.0, 0.27, 0.27, 0.0, 0.0),
            ),
        },
    },
)

BODY_INDEX_VARIABLE = "BodyMotionIndex"
FACE_PAIR_VARIABLE = "FacePairIndex"
FACE_VARIANT_VARIABLE = "FaceVariantIndex"


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


def connect(output_pin, input_pin):
    if not output_pin.try_create_connection(input_pin):
        raise RuntimeError(
            f"Unable to connect {output_pin.get_pin_name()} to "
            f"{input_pin.get_pin_name()}"
        )


def only_output_pin(node):
    pins = list(node.list_output_pins())
    if len(pins) != 1:
        raise RuntimeError(
            f"Expected one output on {node.get_node_title()}, found {len(pins)}"
        )
    return pins[0]


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


def create_sequence_player(graph, animation, loop_animation, position):
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
    anim_node.set_editor_property("loop_animation", bool(loop_animation))
    anim_node.set_editor_property("play_rate", 1.0)
    node.set_editor_property("node", anim_node)
    return node


def create_blend_by_int(graph, position):
    return create_node_of_class(
        graph,
        (
            "Animation|Blends|Blend Poses by int",
            "Animation|Blends|\u6309\u6574\u578b\u6df7\u5408\u59ff\u52bf",
            "Blend Poses by int",
        ),
        unreal.AnimGraphNode_BlendListByInt,
        position,
    )


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


def require_pose_count(node, expected):
    count = sum(
        str(pin.get_pin_name()).startswith("BlendPose_")
        for pin in node.list_all_pins()
    )
    if count != expected:
        raise RuntimeError(
            f"Expected {expected} poses on {node.get_node_title()}, found {count}"
        )


def build_face_clip(actor_id, source, skeleton, spec):
    folder = f"{OUTPUT_ROOT}/{actor_id}/Face"
    name = f"A_DM_{actor_id}_Face_{spec['suffix']}_v001"
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"Refusing to overwrite existing face clip: {path}")
    target = unreal.EditorAssetLibrary.duplicate_asset(
        source.get_path_name().split(".", 1)[0], path
    )
    if not isinstance(target, unreal.AnimSequence):
        raise RuntimeError(f"Unable to create face clip: {path}")

    controller = target.controller
    model = target.data_model_interface
    bone_tracks = [str(name) for name in model.get_bone_track_names()]
    controller.open_bracket("Create P0 curve-only face clip", False)
    try:
        for track_name in bone_tracks:
            if not controller.remove_bone_track(unreal.Name(track_name), False):
                raise RuntimeError(f"Unable to remove bone track: {track_name}")
        controller.remove_all_attributes(False)
    finally:
        controller.close_bracket(False)
    unreal.AnimationLibrary.remove_all_curve_data(target)

    duration = float(target.get_play_length())
    for curve_name, (fractions, values) in spec["curves"].items():
        curve = unreal.Name(curve_name)
        times = [duration * float(fraction) for fraction in fractions]
        unreal.AnimationLibrary.add_curve(
            target, curve, unreal.RawCurveTrackTypes.RCT_FLOAT, False
        )
        unreal.AnimationLibrary.add_float_curve_keys(target, curve, times, values)
        unreal.AnimationLibrary.set_curve_meta_data_morph_target(
            skeleton, curve, True
        )

    target.set_editor_property(
        "additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE
    )
    target.set_editor_property(
        "ref_pose_type", unreal.AdditiveBasePoseType.ABPT_REF_POSE
    )
    target.set_editor_property("enable_root_motion", False)
    target.set_editor_property("force_root_lock", True)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        target, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save face clip: {path}")

    tracks_after = [
        str(name) for name in target.data_model_interface.get_bone_track_names()
    ]
    curves_after = sorted(
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            target, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    )
    missing_curves = sorted(set(spec["curves"]) - set(curves_after))
    if tracks_after or missing_curves:
        raise RuntimeError(
            f"Face clip verification failed: tracks={tracks_after}, "
            f"missing_curves={missing_curves}"
        )
    return target, {
        "id": spec["id"],
        "asset": target.get_path_name(),
        "duration_seconds": duration,
        "bone_track_count": len(tracks_after),
        "curves": curves_after,
    }


def build_anim_blueprint(actor_id, mesh, body_specs, face_assets, skeleton):
    folder = f"{OUTPUT_ROOT}/{actor_id}"
    name = f"ABP_DM_{actor_id}_P0BodyFace_v001"
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"Refusing to overwrite existing AnimBlueprint: {path}")

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
        BODY_INDEX_VARIABLE,
        FACE_PAIR_VARIABLE,
        FACE_VARIANT_VARIABLE,
    ):
        BlueprintTools.add_variable(blueprint, variable_name, "int")
        BlueprintTools.set_variable_category(
            blueprint, variable_name, "DataMake|Layer Selection"
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

    body_players = [
        create_sequence_player(
            graph,
            item["asset"],
            item["loop"],
            unreal.IntPoint(-1200, -500 + index * 270),
        )
        for index, item in enumerate(body_specs)
    ]
    body_blend = create_blend_by_int(graph, unreal.IntPoint(-720, -360))
    require_pose_count(body_blend, 2)
    body_getter = create_variable_getter(
        graph, BODY_INDEX_VARIABLE, unreal.IntPoint(-1000, 120)
    )

    face_players = [
        create_sequence_player(
            graph,
            asset,
            True,
            unreal.IntPoint(-1200, 380 + index * 240),
        )
        for index, asset in enumerate(face_assets)
    ]
    face_pair_blends = [
        create_blend_by_int(
            graph, unreal.IntPoint(-720, 500 + pair_index * 620)
        )
        for pair_index in range(2)
    ]
    face_group_blend = create_blend_by_int(graph, unreal.IntPoint(-360, 790))
    for node in [*face_pair_blends, face_group_blend]:
        require_pose_count(node, 2)
    face_pair_getter = create_variable_getter(
        graph, FACE_PAIR_VARIABLE, unreal.IntPoint(-680, 1370)
    )
    face_variant_getters = [
        create_variable_getter(
            graph,
            FACE_VARIANT_VARIABLE,
            unreal.IntPoint(-1000, 760 + pair_index * 620),
        )
        for pair_index in range(2)
    ]
    apply_additive = create_apply_additive(graph, unreal.IntPoint(-220, 0))

    for index, player in enumerate(body_players):
        connect(find_pin(player, "Pose"), find_pin(body_blend, f"BlendPose_{index}"))
        find_pin(body_blend, f"BlendTime_{index}").set_pin_value("0.20")
    connect(only_output_pin(body_getter), find_pin(body_blend, "ActiveChildIndex"))

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
            only_output_pin(face_variant_getters[pair_index]),
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
        only_output_pin(face_pair_getter),
        find_pin(face_group_blend, "ActiveChildIndex"),
    )
    connect(find_pin(body_blend, "Pose"), find_pin(apply_additive, "Base"))
    connect(
        find_pin(face_group_blend, "Pose"),
        find_pin(apply_additive, "Additive"),
    )
    find_pin(apply_additive, "Alpha").set_pin_value("1.0")
    connect(find_pin(apply_additive, "Pose"), find_pin(root, "Result"))

    BlueprintTools.arrange_nodes(
        [
            *body_players,
            body_blend,
            body_getter,
            *face_players,
            *face_pair_blends,
            face_group_blend,
            face_pair_getter,
            *face_variant_getters,
            apply_additive,
            root,
        ]
    )
    BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=True)
    status = blueprint.get_editor_property("status")
    if status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError(f"AnimBlueprint compile failed: {status}")

    default_instance = unreal.get_default_object(blueprint.generated_class())
    default_instance.set_editor_property(BODY_INDEX_VARIABLE, 1)
    default_instance.set_editor_property(FACE_PAIR_VARIABLE, 0)
    default_instance.set_editor_property(FACE_VARIANT_VARIABLE, 1)
    default_instance.set_editor_property(
        "root_motion_mode", unreal.RootMotionMode.ROOT_MOTION_FROM_EVERYTHING
    )
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        blueprint, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save AnimBlueprint: {path}")
    return blueprint, {
        "asset": blueprint.get_path_name(),
        "generated_class": blueprint.generated_class().get_path_name(),
        "compile_status": str(status),
        "default_selection": {
            BODY_INDEX_VARIABLE: 1,
            FACE_PAIR_VARIABLE: 0,
            FACE_VARIANT_VARIABLE: 1,
        },
        "root_motion_mode": str(
            default_instance.get_editor_property("root_motion_mode")
        ),
    }


def build_wrapper(actor_id, mesh, anim_blueprint):
    folder = f"{CHARACTER_ROOT}/{actor_id}"
    name = f"BP_DM_{actor_id}_P0RuntimePilot_v001"
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"Refusing to overwrite existing wrapper: {path}")

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.Blueprint, factory
    )
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"Unable to create wrapper: {path}")

    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_blueprint(blueprint)
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
    handle, failure_reason = sds.add_new_subobject(
        unreal.AddNewSubobjectParams(
            parent_handle=root_handle,
            new_class=unreal.SkeletalMeshComponent,
            blueprint_context=blueprint,
        )
    )
    if not failure_reason.is_empty():
        raise RuntimeError(f"Unable to add Body component: {failure_reason}")
    if not sds.rename_subobject(handle=handle, new_name=unreal.Text("Body")):
        raise RuntimeError("Unable to rename Body component")
    body = get_component(handle)
    if not isinstance(body, unreal.SkeletalMeshComponent):
        raise RuntimeError(f"Unexpected Body template: {body}")
    body.set_skeletal_mesh_asset(mesh)
    body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    body.set_update_animation_in_editor(True)
    body.set_allow_anim_curve_evaluation(True)
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    body.set_anim_instance_class(anim_blueprint.generated_class())
    body.set_editor_property("component_use_fixed_skel_bounds", False)
    body.set_editor_property("disable_post_process_blueprint", True)

    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    if blueprint.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise RuntimeError(
            f"Wrapper compile failed: {blueprint.get_editor_property('status')}"
        )
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        blueprint, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save wrapper: {path}")

    compiled_handles = sds.k2_gather_subobject_data_for_blueprint(blueprint)
    components_by_path = {}
    for compiled_handle in compiled_handles:
        compiled_component = get_component(compiled_handle)
        if isinstance(compiled_component, unreal.SkeletalMeshComponent):
            components_by_path[compiled_component.get_path_name()] = (
                compiled_component
            )
    components = list(components_by_path.values())
    if len(components) != 1:
        raise RuntimeError(
            "Expected one unique wrapper SkeletalMeshComponent, found "
            f"{len(components)}: {sorted(components_by_path)}"
        )
    component = components[0]
    return blueprint, {
        "asset": blueprint.get_path_name(),
        "generated_class": blueprint.generated_class().get_path_name(),
        "component": component.get_name(),
        "mesh": component.get_skeletal_mesh_asset().get_path_name(),
        "anim_class": component.get_editor_property("anim_class").get_path_name(),
        "disable_post_process_blueprint": bool(
            component.get_editor_property("disable_post_process_blueprint")
        ),
        "post_process_anim_blueprint": (
            mesh.get_editor_property("post_process_anim_blueprint").get_path_name()
            if mesh.get_editor_property("post_process_anim_blueprint")
            else None
        ),
    }


records = []
for actor_id, config in ACTORS.items():
    mesh = unreal.load_asset(config["mesh"])
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Missing P0 mesh for {actor_id}: {config['mesh']}")
    body_specs = []
    for body_spec in config["body_animations"]:
        animation = unreal.load_asset(body_spec["path"])
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError(
                f"Missing body animation for {actor_id}: {body_spec['path']}"
            )
        body_specs.append({**body_spec, "asset": animation})
    skeleton = body_specs[0]["asset"].get_editor_property("skeleton")
    if mesh.get_editor_property("skeleton") != skeleton:
        raise RuntimeError(f"Mesh/animation Skeleton mismatch for {actor_id}")
    if any(
        item["asset"].get_editor_property("skeleton") != skeleton
        for item in body_specs
    ):
        raise RuntimeError(f"Body animations use mixed Skeletons for {actor_id}")

    morph_names = {str(name) for name in mesh.get_all_morph_target_names()}
    required_curves = {
        name for spec in FACE_SPECS for name in spec["curves"]
    }
    missing_morphs = sorted(required_curves - morph_names)
    if missing_morphs:
        raise RuntimeError(
            f"P0 mesh lacks required facial Morphs for {actor_id}: {missing_morphs}"
        )

    face_assets = []
    face_records = []
    source = body_specs[1]["asset"]
    for face_spec in FACE_SPECS:
        face_asset, face_record = build_face_clip(
            actor_id, source, skeleton, face_spec
        )
        face_assets.append(face_asset)
        face_records.append(face_record)
    unreal.EditorAssetLibrary.save_loaded_asset(skeleton, only_if_is_dirty=False)

    anim_blueprint, anim_record = build_anim_blueprint(
        actor_id, mesh, body_specs, face_assets, skeleton
    )
    wrapper, wrapper_record = build_wrapper(actor_id, mesh, anim_blueprint)
    records.append(
        {
            "actor_id": actor_id,
            "mesh": mesh.get_path_name(),
            "skeleton": skeleton.get_path_name(),
            "body_animations": [
                {
                    "id": item["id"],
                    "asset": item["asset"].get_path_name(),
                    "loop": item["loop"],
                }
                for item in body_specs
            ],
            "face_clips": face_records,
            "anim_blueprint": anim_record,
            "wrapper": wrapper_record,
            "required_face_morphs": sorted(required_curves),
            "missing_face_morphs": missing_morphs,
        }
    )

report = {
    "schema_version": 1,
    "runtime_scope": "full_reference_direct_morph",
    "facial_runtime_mode": "direct_morph_curves",
    "post_process_policy": "disabled_on_full_reference_component",
    "records": records,
    "actor_count": len(records),
    "face_clip_count": sum(len(item["face_clips"]) for item in records),
    "anim_blueprint_count": len(records),
    "wrapper_count": len(records),
    "success": len(records) == 2,
    "production_status": "not_approved",
}
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
unreal.log(f"DataMake P0 runtime composition built: {REPORT_PATH}")
print("DM_P0_RUNTIME_COMPOSITION=" + json.dumps(report, ensure_ascii=False))
