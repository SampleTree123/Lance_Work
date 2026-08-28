"""Configure and start one first-batch 5-second MRQ job in the editor."""

from __future__ import annotations

import json

import unreal


PRESET_PATH = "/Game/DataMake/Render/Presets/MRQ_DM_FirstBatch_1440p30_PNG_v001"
MAP_PATH = str(
    globals().get(
        "DM_MAP_PATH",
        "/Game/DataMake/Scenes/TokyoStylized/"
        "L_DM_TokyoStylized.L_DM_TokyoStylized",
    )
)
SEQUENCE_PATH = str(
    globals().get(
        "DM_SEQUENCE_PATH",
        "/Game/DataMake/Sequences/FirstBatch/"
        "LS_DM_FirstBatch_F02_20s_Pilot_v001."
        "LS_DM_FirstBatch_F02_20s_Pilot_v001",
    )
)
OUTPUT_DIRECTORY = str(globals()["DM_OUTPUT_DIRECTORY"])
START_FRAME = int(globals().get("DM_START_FRAME", 0))
END_FRAME = int(globals().get("DM_END_FRAME", 150))
JOB_NAME = str(globals().get("DM_JOB_NAME", "DM_FirstBatch_LocalSample_v001"))
ALLOW_PARTIAL = bool(globals().get("DM_ALLOW_PARTIAL", False))
RENDER_OFFSCREEN = bool(globals().get("DM_RENDER_OFFSCREEN", False))


preset = unreal.load_asset(PRESET_PATH)
if not isinstance(preset, unreal.MoviePipelinePrimaryConfig):
    raise RuntimeError(f"Missing MRQ preset: {PRESET_PATH}")
if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH.split(".", 1)[0]):
    raise RuntimeError(f"Missing map: {MAP_PATH}")
if not unreal.EditorAssetLibrary.does_asset_exist(SEQUENCE_PATH.split(".", 1)[0]):
    raise RuntimeError(f"Missing sequence: {SEQUENCE_PATH}")
if END_FRAME - START_FRAME <= 0:
    raise RuntimeError("Render frame range must be positive")
if END_FRAME - START_FRAME != 150 and not ALLOW_PARTIAL:
    raise RuntimeError(
        f"First-batch local sample must be exactly 150 frames: "
        f"{START_FRAME}..{END_FRAME}"
    )

subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
if subsystem.is_rendering():
    raise RuntimeError("Movie Render Queue is already rendering")
queue = subsystem.get_queue()
queue.delete_all_jobs()
job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
job.job_name = JOB_NAME
job.author = "Lance_Work automated local sample"
job.comment = "First-batch 1440p30 five-second local acceptance sample"
job.map = unreal.SoftObjectPath(MAP_PATH)
job.sequence = unreal.SoftObjectPath(SEQUENCE_PATH)
job.set_configuration(preset)

configuration = job.get_configuration()
output = configuration.find_or_add_setting_by_class(
    unreal.MoviePipelineOutputSetting
)
output.output_directory.set_editor_property("path", OUTPUT_DIRECTORY)
output.output_resolution = unreal.IntPoint(2560, 1440)
output.use_custom_frame_rate = True
output.output_frame_rate = unreal.FrameRate(30, 1)
output.use_custom_playback_range = True
output.custom_start_frame = START_FRAME
output.custom_end_frame = END_FRAME
output.file_name_format = "frame_{frame_number_rel}"
output.zero_pad_frame_numbers = 4
output.override_existing_output = True
output.flush_disk_writes_per_shot = True
configuration.find_or_add_setting_by_class(
    unreal.MoviePipelineDeferredPassBase
).set_is_enabled(True)
configuration.find_or_add_setting_by_class(
    unreal.MoviePipelineImageSequenceOutput_PNG
).set_is_enabled(True)
configuration.initialize_transient_settings()

executor = unreal.MoviePipelinePIEExecutor(subsystem)
executor.set_is_rendering_offscreen(RENDER_OFFSCREEN)
# Keep the Python wrapper alive for the duration of the asynchronous render.
setattr(unreal, "_dm_first_batch_local_executor", executor)
subsystem.render_queue_with_executor_instance(executor)

report = {
    "status": "started",
    "job_name": JOB_NAME,
    "preset": PRESET_PATH,
    "map": MAP_PATH,
    "sequence": SEQUENCE_PATH,
    "output_directory": OUTPUT_DIRECTORY,
    "start_frame_inclusive": START_FRAME,
    "end_frame_exclusive": END_FRAME,
    "expected_frame_count": END_FRAME - START_FRAME,
    "resolution": [2560, 1440],
    "fps": 30,
    "offscreen": RENDER_OFFSCREEN,
}
print("DM_SAMPLE_RENDER_STARTED=" + json.dumps(report, ensure_ascii=False))
