"""Build a neutral hybrid clip and graph-matched v003 control AnimBlueprint."""

from __future__ import annotations

import json
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


SOURCE_FACE = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_HybridSupport_Loop_v001"
)
NEUTRAL_FACE = (
    "/Game/DataMake/Animations/CC5/Pilot/Face/"
    "A_DM_M02_Face_HybridSupport_NeutralLoop_v001"
)
SOURCE_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003"
)
CONTROL_BLUEPRINT = (
    "/Game/DataMake/Animations/CC5/Pilot/"
    "ABP_DM_M02_BodyFaceLayer_v003_ControlNeutral"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_hybrid_neutral_control_v003_build.json"
)


source_face = unreal.load_asset(SOURCE_FACE)
if not isinstance(source_face, unreal.AnimSequence):
    raise RuntimeError(f"Hybrid source unavailable: {SOURCE_FACE}")

neutral_face = unreal.load_asset(NEUTRAL_FACE)
neutral_created = False
if neutral_face is None:
    neutral_face = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_FACE, NEUTRAL_FACE)
    neutral_created = True
if not isinstance(neutral_face, unreal.AnimSequence):
    raise RuntimeError(f"Unable to create neutral hybrid clip: {NEUTRAL_FACE}")

source_model = source_face.data_model_interface
model = neutral_face.data_model_interface
controller = neutral_face.controller
if source_model is None or model is None or controller is None:
    raise RuntimeError("Neutral hybrid animation model/controller unavailable")

support_bones = [str(name) for name in source_model.get_bone_track_names()]
frame_count = int(model.get_number_of_frames())
key_count = frame_count + 1
controller.open_bracket("Build M02 neutral hybrid control clip", False)
try:
    existing_tracks = {str(name) for name in model.get_bone_track_names()}
    for track_name in sorted(existing_tracks - set(support_bones)):
        controller.remove_bone_track(unreal.Name(track_name), False)
    for bone in support_bones:
        if bone not in existing_tracks:
            controller.add_bone_track(unreal.Name(bone), False)
        neutral = unreal.AnimationLibrary.get_bone_pose_for_frame(
            source_face, unreal.Name(bone), 0, False
        )
        positions = [
            unreal.Vector(
                neutral.translation.x,
                neutral.translation.y,
                neutral.translation.z,
            )
            for _ in range(key_count)
        ]
        rotations = [
            unreal.Quat(
                neutral.rotation.x,
                neutral.rotation.y,
                neutral.rotation.z,
                neutral.rotation.w,
            )
            for _ in range(key_count)
        ]
        scales = [
            unreal.Vector(neutral.scale3d.x, neutral.scale3d.y, neutral.scale3d.z)
            for _ in range(key_count)
        ]
        if not controller.set_bone_track_keys(
            unreal.Name(bone), positions, rotations, scales, False
        ):
            raise RuntimeError(f"Unable to neutralize support track: {bone}")
    controller.remove_all_attributes(False)
finally:
    controller.close_bracket(False)

unreal.AnimationLibrary.remove_all_curve_data(neutral_face)
neutral_face.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_NONE)
unreal.AnimationLibrary.finalize_bone_animation(neutral_face)
if not unreal.EditorAssetLibrary.save_loaded_asset(neutral_face, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save neutral hybrid clip: {NEUTRAL_FACE}")

source_blueprint = unreal.load_asset(SOURCE_BLUEPRINT)
if not isinstance(source_blueprint, unreal.AnimBlueprint):
    raise RuntimeError(f"Source AnimBlueprint unavailable: {SOURCE_BLUEPRINT}")
control_blueprint = unreal.load_asset(CONTROL_BLUEPRINT)
control_created = False
if control_blueprint is None:
    control_blueprint = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_BLUEPRINT, CONTROL_BLUEPRINT
    )
    control_created = True
if not isinstance(control_blueprint, unreal.AnimBlueprint):
    raise RuntimeError(f"Unable to create control AnimBlueprint: {CONTROL_BLUEPRINT}")

graph = unreal.BlueprintEditorLibrary.find_graph(control_blueprint, "AnimGraph")
if graph is None:
    raise RuntimeError("Control AnimBlueprint has no AnimGraph")
face_players = []
sequence_paths = []
for node in BlueprintTools.find_nodes(graph):
    if not isinstance(node, unreal.AnimGraphNode_SequencePlayer):
        continue
    anim_node = node.get_editor_property("node")
    sequence = anim_node.get_editor_property("sequence")
    sequence_path = sequence.get_path_name() if sequence is not None else None
    if sequence_path in {
        source_face.get_path_name(),
        neutral_face.get_path_name(),
    }:
        anim_node.set_editor_property("sequence", neutral_face)
        node.set_editor_property("node", anim_node)
        face_players.append(node)
        sequence_path = neutral_face.get_path_name()
    sequence_paths.append(sequence_path)
if len(face_players) != 1:
    raise RuntimeError(
        f"Expected one hybrid face Sequence Player, found {len(face_players)}"
    )

BlueprintTools.compile_blueprint(control_blueprint, warnings_as_errors=True)
compile_status = control_blueprint.get_editor_property("status")
if compile_status != unreal.BlueprintStatus.BS_UP_TO_DATE:
    raise RuntimeError(f"Control AnimBlueprint compile status: {compile_status}")
if not unreal.EditorAssetLibrary.save_loaded_asset(
    control_blueprint, only_if_is_dirty=False
):
    raise RuntimeError(f"Unable to save control AnimBlueprint: {CONTROL_BLUEPRINT}")

neutral_tracks = {str(name) for name in model.get_bone_track_names()}
neutral_curves = {
    str(name)
    for name in unreal.AnimationLibrary.get_animation_curve_names(
        neutral_face, unreal.RawCurveTrackTypes.RCT_FLOAT
    )
}
success = (
    neutral_tracks == set(support_bones)
    and not neutral_curves
    and len(face_players) == 1
    and compile_status == unreal.BlueprintStatus.BS_UP_TO_DATE
)
report = {
    "schema_version": 1,
    "source_face": source_face.get_path_name(),
    "neutral_face": neutral_face.get_path_name(),
    "neutral_face_created": neutral_created,
    "play_length_seconds": float(neutral_face.get_play_length()),
    "support_bones": support_bones,
    "curve_names": sorted(neutral_curves),
    "source_anim_blueprint": source_blueprint.get_path_name(),
    "control_anim_blueprint": control_blueprint.get_path_name(),
    "control_anim_blueprint_created": control_created,
    "compile_status": str(compile_status),
    "sequence_players": sorted(path for path in sequence_paths if path),
    "success": success,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
if not success:
    raise RuntimeError("Neutral hybrid control verification failed")
print(
    "DM_HYBRID_NEUTRAL_CONTROL="
    + json.dumps(
        {
            "control_anim_blueprint": control_blueprint.get_path_name(),
            "neutral_face": neutral_face.get_path_name(),
            "report": str(REPORT_PATH),
            "success": True,
        },
        sort_keys=True,
    )
)
