"""Build a deterministic 20-second, four-camera first-batch pilot sequence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(str(globals().get("DM_WORKSPACE_ROOT", r"D:\UE\Lance_Work")))
WINDOWS_PATH = (
    ROOT
    / "00_engine"
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_window_selection"
    / "frozen_20260821_v4"
    / "frozen_action_windows.json"
)
ACTION_POOL_PATH = (
    ROOT
    / "00_engine"
    / "scripts"
    / "character_creator"
    / "cc_first_batch_action_pool_20260824_v1.json"
)
MOTION_GATE_PATH = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_motions_20260822_v1"
    / "aggregate_motion_import_gate.json"
)

SOURCE_SEQUENCE = str(
    globals().get("DM_SOURCE_SEQUENCE", "/Game/DataMake/Sequences/firstweek")
)
OUTPUT_SEQUENCE = str(
    globals().get(
        "DM_OUTPUT_SEQUENCE",
        "/Game/DataMake/Sequences/FirstBatch/"
        "LS_DM_FirstBatch_F02_20s_Pilot_v001",
    )
)
ACTION_ID = str(globals().get("DM_ACTION_ID", "ACT_F02_CATCH_BREATH"))
ACTION_CONTRACT_JSON = str(globals().get("DM_ACTION_CONTRACT_JSON", "null"))
TARGET_ACTOR_NAME = str(
    globals().get(
        "DM_TARGET_ACTOR_NAME",
        "CC_FB_F_ID02_O04_Blueprint_LiveLink_C_1",
    )
)
REPLACE_OUTPUT = bool(globals().get("DM_REPLACE_OUTPUT", True))
OPEN_OUTPUT = bool(globals().get("DM_OPEN_OUTPUT", True))
SEGMENT_EXPRESSION_STATES = tuple(
    str(value).lower()
    for value in globals().get(
        "DM_SEGMENT_EXPRESSIONS", ("happy", "angry", "sad", "happy")
    )
)
RENDER_CAMERA_ID = str(globals().get("DM_RENDER_CAMERA_ID", "")).lower()

DISPLAY_FPS = 30
SEGMENT_FRAMES = 150
SEGMENT_COUNT = 4
TOTAL_FRAMES = SEGMENT_FRAMES * SEGMENT_COUNT
SECTION_PRE_ROLL_FRAMES = 1
EXPECTED_CAMERA_CUTS = (
    (0, 150, "near"),
    (150, 300, "far"),
    (300, 450, "high"),
    (450, 600, "side"),
)
F02_INPLACE_ASSET = (
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/InPlaceCandidates/"
    "A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001"
)
NATIVE_SECTION_TEMPLATE_SEQUENCE = (
    "/Game/DataMake/Sequences/FirstBatch/Templates/"
    "LS_DM_NativeSkeletalAnimationSectionTemplate_v001"
)
REPORT_ROOT = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day3_20260823_v1"
)
REPORT_PATH = REPORT_ROOT / f"sequence_build_{ACTION_ID.lower()}_pilot.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def frame_value(value) -> int:
    return int(value.value) if hasattr(value, "value") else int(value)


def find_actor(name: str):
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = [
        actor
        for actor in subsystem.get_all_level_actors()
        if actor.get_name() == name or actor.get_actor_label() == name
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one target actor named {name}, found {len(matches)}")
    return matches[0]


def find_action(records: list[dict], action_id: str) -> dict:
    matches = [record for record in records if record.get("action_id") == action_id]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one action record for {action_id}, found {len(matches)}"
        )
    return matches[0]


def load_animation(
    action_id: str,
    motion_record: dict,
    window_record: dict,
    action_contract: dict | None,
):
    override_asset = (
        action_contract.get("root_motion_override_asset")
        if action_contract is not None
        else None
    )
    if override_asset or action_id == "ACT_F02_CATCH_BREATH":
        path = override_asset or F02_INPLACE_ASSET
        source_policy = "approved_inplace_override"
    elif float(window_record["window"]["padding_required_seconds"]) > 1.0e-6:
        slug = action_id.removeprefix("ACT_")
        sex_folder = "Female" if window_record["sex"] == "female" else "Male"
        path = (
            f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
            f"IdlePadded/A_DM_{slug}_IdlePadded5s_v001"
        )
        source_policy = "symmetric_exact_endpoint_holds_v1"
    else:
        path = (
            action_contract["happy_composite_animation"]
            if action_contract is not None
            else motion_record["body_only_animation"]["asset"]
        )
        source_policy = "approved_original_body_only"
    asset = unreal.load_asset(path)
    if not isinstance(asset, unreal.AnimSequence):
        raise RuntimeError(f"Animation is missing or invalid: {path}")
    return asset, source_policy


def load_segment_animations(
    action_id: str,
    window_record: dict,
    body_animation: unreal.AnimSequence,
    action_contract: dict | None,
) -> tuple[list[unreal.AnimSequence], list[str], str]:
    slug = action_id.removeprefix("ACT_")
    actor_id = slug.split("_", 1)[0]
    sex_folder = "Female" if window_record["sex"] == "female" else "Male"
    root = (
        f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
        f"Composites/{actor_id}"
    )
    assets = []
    states = []
    if len(SEGMENT_EXPRESSION_STATES) != SEGMENT_COUNT:
        raise RuntimeError(
            f"Expected {SEGMENT_COUNT} segment expressions, found "
            f"{SEGMENT_EXPRESSION_STATES}"
        )
    if not set(SEGMENT_EXPRESSION_STATES).issubset({"happy", "angry", "sad"}):
        raise RuntimeError(
            f"Unsupported segment expression: {SEGMENT_EXPRESSION_STATES}"
        )
    for state in SEGMENT_EXPRESSION_STATES:
        path = (
            action_contract["happy_composite_animation"]
            if action_contract is not None and state == "happy"
            else f"{root}/A_DM_{slug}_{state.title()}_Composite_v001"
        )
        asset = unreal.load_asset(path)
        if not isinstance(asset, unreal.AnimSequence):
            raise RuntimeError(f"Missing expression composite: {path}")
        if asset.get_skeleton() != body_animation.get_skeleton():
            raise RuntimeError(f"Composite skeleton mismatch: {path}")
        curves = unreal.AnimationLibrary.get_animation_curve_names(
            asset, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
        if not curves:
            raise RuntimeError(f"Composite contains no facial curves: {path}")
        assets.append(asset)
        states.append(state)
    return assets, states, "embedded_morph_curves"


def validate_camera_contract(sequence: unreal.LevelSequence) -> list[dict]:
    cuts = []
    camera_tracks = [
        track
        for track in sequence.get_tracks()
        if isinstance(track, unreal.MovieSceneCameraCutTrack)
    ]
    if len(camera_tracks) != 1:
        raise RuntimeError(
            f"Expected one camera-cut track, found {len(camera_tracks)}"
        )
    for section in camera_tracks[0].get_sections():
        binding = sequence.resolve_binding_id(section.get_camera_binding_id())
        cuts.append(
            {
                "start_frame": frame_value(section.get_start_frame()),
                "end_frame": frame_value(section.get_end_frame()),
                "camera_binding": binding.get_name() if binding.is_valid() else None,
            }
        )
    observed = [
        (cut["start_frame"], cut["end_frame"], cut["camera_binding"])
        for cut in cuts
    ]
    if observed != list(EXPECTED_CAMERA_CUTS):
        raise RuntimeError(
            f"Camera-cut contract mismatch: expected={EXPECTED_CAMERA_CUTS}, "
            f"observed={observed}"
        )
    return cuts


def configure_render_camera(sequence: unreal.LevelSequence, camera_id: str) -> dict:
    if camera_id not in {cut[2] for cut in EXPECTED_CAMERA_CUTS}:
        raise RuntimeError(f"Unsupported render camera: {camera_id!r}")
    camera_tracks = [
        track
        for track in sequence.get_tracks()
        if isinstance(track, unreal.MovieSceneCameraCutTrack)
    ]
    if len(camera_tracks) != 1:
        raise RuntimeError(
            f"Expected one camera-cut track, found {len(camera_tracks)}"
        )
    expected_by_name = {
        name: (start_frame, end_frame)
        for start_frame, end_frame, name in EXPECTED_CAMERA_CUTS
    }
    sections_by_name = {}
    for section in camera_tracks[0].get_sections():
        binding = sequence.resolve_binding_id(section.get_camera_binding_id())
        name = binding.get_name() if binding.is_valid() else None
        if name not in expected_by_name or name in sections_by_name:
            raise RuntimeError(f"Unexpected camera-cut binding: {name!r}")
        sections_by_name[name] = section
    if set(sections_by_name) != set(expected_by_name):
        raise RuntimeError(
            f"Camera-cut bindings are incomplete: {sorted(sections_by_name)}"
        )

    # The workspace asset is reused between jobs. Restore its canonical ranges
    # before applying this job's camera isolation so no previous job can leak.
    for name, section in sections_by_name.items():
        start_frame, end_frame = expected_by_name[name]
        section.set_range(start_frame, end_frame)
        section.set_is_active(True)
    source_cuts = validate_camera_contract(sequence)

    for name, section in sections_by_name.items():
        selected = name == camera_id
        section.set_is_active(selected)
        if selected:
            section.set_range(0, TOTAL_FRAMES)

    active_sections = [
        {
            "camera_binding": name,
            "start_frame": frame_value(section.get_start_frame()),
            "end_frame": frame_value(section.get_end_frame()),
        }
        for name, section in sections_by_name.items()
        if section.is_active()
    ]
    expected_active = [
        {
            "camera_binding": camera_id,
            "start_frame": 0,
            "end_frame": TOTAL_FRAMES,
        }
    ]
    return {
        "requested_camera": camera_id,
        "source_camera_cuts": source_cuts,
        "active_camera_cuts": active_sections,
        "passed": active_sections == expected_active,
    }


def duplicate_sequence(source_path: str, output_path: str):
    source = unreal.load_asset(source_path)
    if not isinstance(source, unreal.LevelSequence):
        raise RuntimeError(f"Source sequence is missing: {source_path}")
    if unreal.EditorAssetLibrary.does_asset_exist(output_path):
        if not REPLACE_OUTPUT:
            raise RuntimeError(f"Output already exists: {output_path}")
        current = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
        if current and current.get_path_name() == output_path:
            unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
        output = unreal.load_asset(output_path)
        if not isinstance(output, unreal.LevelSequence):
            raise RuntimeError(f"Existing output is not a LevelSequence: {output_path}")
        generated_roots = [
            binding
            for binding in output.get_bindings()
            if str(binding.get_display_name()) == "DM First Batch Character"
            and not binding.get_parent().is_valid()
        ]
        for binding in generated_roots:
            binding.remove()
        generated_orphans = [
            binding
            for binding in output.get_bindings()
            if str(binding.get_display_name()) == "DM Animated Skeletal Mesh"
        ]
        for binding in generated_orphans:
            binding.remove()
        return output
    folder = output_path.rsplit("/", 1)[0]
    unreal.EditorAssetLibrary.make_directory(folder)
    if not unreal.EditorAssetLibrary.duplicate_asset(source_path, output_path):
        raise RuntimeError(f"Unable to duplicate {source_path} to {output_path}")
    output = unreal.load_asset(output_path)
    if not isinstance(output, unreal.LevelSequence):
        raise RuntimeError(f"Duplicated output is not a LevelSequence: {output_path}")
    return output


def matching_component(actor, animation: unreal.AnimSequence):
    skeleton = animation.get_skeleton()
    matches = []
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh = component.get_skeletal_mesh_asset()
        if mesh and mesh.get_editor_property("skeleton") == skeleton:
            matches.append(component)
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one skeletal component compatible with "
            f"{skeleton.get_path_name()}, found {[item.get_name() for item in matches]}"
        )
    return matches[0]


def copy_native_section_template() -> str:
    template = unreal.load_asset(NATIVE_SECTION_TEMPLATE_SEQUENCE)
    if not isinstance(template, unreal.LevelSequence):
        raise RuntimeError(
            "Native skeletal-animation section template is missing: "
            f"{NATIVE_SECTION_TEMPLATE_SEQUENCE}"
        )
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(template)
    tracks = [
        track
        for binding in template.get_bindings()
        for track in binding.get_tracks()
        if isinstance(track, unreal.MovieSceneSkeletalAnimationTrack)
        and len(track.get_sections()) > 0
    ]
    if len(tracks) != 1 or len(tracks[0].get_sections()) != 1:
        raise RuntimeError(
            "Native section template must contain exactly one populated "
            "skeletal-animation track and one section"
        )
    subsystem = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    exported_text = subsystem.copy_sections([tracks[0].get_sections()[0]])
    if not exported_text:
        raise RuntimeError("Unable to copy the native skeletal-animation section")
    return exported_text


def add_repeated_action_track(
    sequence: unreal.LevelSequence,
    actor,
    animations: list[unreal.AnimSequence],
    expression_states: list[str],
    start_seconds: float,
    force_custom_mode: bool,
) -> tuple[object, list[dict]]:
    if len(animations) != SEGMENT_COUNT:
        raise RuntimeError(f"Expected {SEGMENT_COUNT} segment animations")
    if len(expression_states) != SEGMENT_COUNT:
        raise RuntimeError(f"Expected {SEGMENT_COUNT} expression states")
    exported_section = copy_native_section_template()
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    editor_subsystem = unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    )
    created_bindings = editor_subsystem.add_actors([actor])
    if len(created_bindings) != 1:
        raise RuntimeError(
            f"Expected one native actor binding, found {len(created_bindings)}"
        )
    actor_binding = created_bindings[0]
    actor_binding.set_display_name("DM First Batch Character")
    skeletal_tracks = [
        track
        for track in actor_binding.get_tracks()
        if isinstance(track, unreal.MovieSceneSkeletalAnimationTrack)
    ]
    if len(skeletal_tracks) > 1:
        raise RuntimeError(
            f"Native actor binding created {len(skeletal_tracks)} animation tracks"
        )
    track = (
        skeletal_tracks[0]
        if skeletal_tracks
        else actor_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    )
    track.set_display_name("DM Body Action Window x4")

    tick_resolution = sequence.get_tick_resolution()
    tick_fps = float(tick_resolution.numerator) / float(tick_resolution.denominator)
    offset_ticks = int(round(start_seconds * tick_fps))
    sections = []
    for index, (animation, expression_state) in enumerate(
        zip(animations, expression_states)
    ):
        start_frame = index * SEGMENT_FRAMES
        end_frame = start_frame + SEGMENT_FRAMES
        paste_params = unreal.MovieScenePasteSectionsParams(
            tracks=[track],
            track_row_indices=[0],
            time=unreal.FrameTime(unreal.FrameNumber(start_frame)),
        )
        pasted = editor_subsystem.paste_sections(exported_section, paste_params)
        if pasted is None or len(pasted) != 1:
            raise RuntimeError(
                f"Expected one native section at frame {start_frame}, found {pasted}"
            )
        section = pasted[0]
        section.set_range(start_frame, end_frame)
        section.set_pre_roll_frames(SECTION_PRE_ROLL_FRAMES)
        params = section.get_editor_property("params")
        params.set_editor_property("animation", animation)
        params.set_editor_property("reverse", False)
        # Every staged CC5 Blueprint must enter Sequencer's custom animation
        # mode explicitly. Relying on the Blueprint's current animation mode
        # worked for the first staged Look only; later Looks rendered in T-pose.
        params.set_editor_property("force_custom_mode", force_custom_mode)
        params.set_editor_property("start_frame_offset", unreal.FrameNumber(0))
        params.set_editor_property("end_frame_offset", unreal.FrameNumber(0))
        params.set_editor_property(
            "first_loop_start_frame_offset", unreal.FrameNumber(offset_ticks)
        )
        section.set_editor_property("params", params)
        sections.append(
            {
                "index": index,
                "start_frame": frame_value(section.get_start_frame()),
                "end_frame": frame_value(section.get_end_frame()),
                "pre_roll_frames": int(section.get_pre_roll_frames()),
                "source_start_seconds": start_seconds,
                "expression_state": expression_state,
                "first_loop_start_offset_ticks": offset_ticks,
                "force_custom_mode": bool(
                    params.get_editor_property("force_custom_mode")
                ),
                "animation": animation.get_path_name(),
            }
        )
    return actor_binding, sections


action_contract = json.loads(ACTION_CONTRACT_JSON)
if action_contract is not None:
    if not isinstance(action_contract, dict):
        raise RuntimeError("Frozen action contract must be an object")
    if action_contract.get("action_id") != ACTION_ID:
        raise RuntimeError(
            f"Action contract mismatch: {action_contract.get('action_id')} != {ACTION_ID}"
        )
    if action_contract.get("sex") not in {"female", "male"}:
        raise RuntimeError(f"Invalid action sex: {action_contract.get('sex')}")
    if not isinstance(action_contract.get("window"), dict):
        raise RuntimeError("Frozen action contract lacks window")
    if not action_contract.get("happy_composite_animation"):
        raise RuntimeError("Frozen action contract lacks Happy composite")
    window_record = {
        "action_id": ACTION_ID,
        "sex": action_contract["sex"],
        "window": action_contract["window"],
    }
    motion_record = {}
    action_contract_source = "frozen_source_manifest"
else:
    windows = read_json(WINDOWS_PATH)
    action_pool = read_json(ACTION_POOL_PATH)
    motion_gate = read_json(MOTION_GATE_PATH)
    active_action_ids = {
        action_id
        for sex in ("female", "male")
        for action_id in action_pool["active_actions"][sex]
    }
    if ACTION_ID not in active_action_ids:
        raise RuntimeError(
            f"Action is not active in the frozen production pool: {ACTION_ID}"
        )
    window_record = find_action(windows["actions"], ACTION_ID)
    motion_record = find_action(motion_gate["records"], ACTION_ID)
    action_contract_source = "legacy_runtime_reports"
animation, source_policy = load_animation(
    ACTION_ID, motion_record, window_record, action_contract
)
segment_animations, expression_states, expression_policy = load_segment_animations(
    ACTION_ID, window_record, animation, action_contract
)
bind_pose_guard_frames = 1 if ACTION_ID == "ACT_F02_CATCH_BREATH" else 0
source_start_seconds = (
    0.0
    if source_policy == "symmetric_exact_endpoint_holds_v1"
    else float(window_record["window"]["start_seconds"])
) + bind_pose_guard_frames / DISPLAY_FPS
# This is required for both sexes. Imported Blueprint defaults are not uniform,
# and MRQ starts from the saved map rather than the editor preview state.
force_custom_mode = True
actor = find_actor(TARGET_ACTOR_NAME)
component = matching_component(actor, animation)
component.set_editor_property("disable_post_process_blueprint", True)

sequence = duplicate_sequence(SOURCE_SEQUENCE, OUTPUT_SEQUENCE)
sequence.set_display_rate(unreal.FrameRate(DISPLAY_FPS, 1))
sequence.set_playback_start(0)
sequence.set_playback_end(TOTAL_FRAMES)
camera_contract = configure_render_camera(sequence, RENDER_CAMERA_ID)
camera_cuts = camera_contract["source_camera_cuts"]
actor_binding, sections = add_repeated_action_track(
    sequence,
    actor,
    segment_animations,
    expression_states,
    source_start_seconds,
    force_custom_mode,
)

if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save generated sequence: {OUTPUT_SEQUENCE}")
if OPEN_OUTPUT:
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)

report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "build_first_batch_four_camera_render_workspace",
    "source_sequence": SOURCE_SEQUENCE,
    "output_sequence": sequence.get_path_name(),
    "target_actor": actor.get_path_name(),
    "target_component": component.get_path_name(),
    "action_id": ACTION_ID,
    "action_sex": window_record["sex"],
    "action_contract_source": action_contract_source,
    "animation": animation.get_path_name(),
    "animation_source_policy": source_policy,
    "expression_policy": expression_policy,
    "expression_states": expression_states,
    "native_section_template": NATIVE_SECTION_TEMPLATE_SEQUENCE,
    "disable_post_process_blueprint": bool(
        component.get_editor_property("disable_post_process_blueprint")
    ),
    "window": window_record["window"],
    "source_start_seconds_after_guards": source_start_seconds,
    "bind_pose_guard_frames": bind_pose_guard_frames,
    "force_custom_mode_required": force_custom_mode,
    "display_fps": DISPLAY_FPS,
    "segment_frames": SEGMENT_FRAMES,
    "segment_count": SEGMENT_COUNT,
    "total_frames": TOTAL_FRAMES,
    "camera_cuts": camera_cuts,
    "render_camera_contract": camera_contract,
    "animation_binding": actor_binding.get_name(),
    "animation_binding_type": "native_actor_binding",
    "animation_sections": sections,
    "checks": {
        "camera_cut_contract": camera_cuts
        == [
            {
                "start_frame": start,
                "end_frame": end,
                "camera_binding": camera,
            }
            for start, end, camera in EXPECTED_CAMERA_CUTS
        ],
        "render_camera_isolated": camera_contract["passed"],
        "four_animation_sections": len(sections) == SEGMENT_COUNT,
        "all_sections_are_150_frames": all(
            item["end_frame"] - item["start_frame"] == SEGMENT_FRAMES
            for item in sections
        ),
        "all_sections_use_expected_evaluation_mode": all(
            item["force_custom_mode"] == force_custom_mode for item in sections
        ),
        "all_cc5_looks_force_custom_mode": force_custom_mode
        and all(item["force_custom_mode"] for item in sections),
        "all_sections_have_one_frame_preroll": all(
            item["pre_roll_frames"] == SECTION_PRE_ROLL_FRAMES
            for item in sections
        ),
        "approved_f02_inplace_override": ACTION_ID != "ACT_F02_CATCH_BREATH"
        or source_policy == "approved_inplace_override",
        "native_section_template_used": len(sections) == SEGMENT_COUNT,
        "expression_composites": (
            expression_policy == "embedded_morph_curves"
            and expression_states == list(SEGMENT_EXPRESSION_STATES)
        ),
        "post_process_disabled_for_direct_morph_curves": bool(
            component.get_editor_property("disable_post_process_blueprint")
        ),
    },
}
report["success"] = all(report["checks"].values())
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("DM_FIRST_BATCH_20S_SEQUENCE=" + json.dumps(report, ensure_ascii=False))
