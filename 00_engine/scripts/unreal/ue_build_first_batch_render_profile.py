"""Create or audit the first-batch 1440p30 Movie Render Queue preset."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work")
PRESET_FOLDER = "/Game/DataMake/Render/Presets"
PRESET_NAME = "MRQ_DM_FirstBatch_1440p30_PNG_v001"
PRESET_PATH = f"{PRESET_FOLDER}/{PRESET_NAME}"
DEFAULT_OUTPUT = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_render"
    / "_profile_default"
)
REPORT_PATH = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day3_20260823_v1"
    / "render_profile_build.json"
)


def load_or_create_profile() -> tuple[unreal.MoviePipelinePrimaryConfig, str]:
    if unreal.EditorAssetLibrary.does_asset_exist(PRESET_PATH):
        asset = unreal.load_asset(PRESET_PATH)
        if not isinstance(asset, unreal.MoviePipelinePrimaryConfig):
            raise RuntimeError(f"Preset path has wrong asset type: {PRESET_PATH}")
        return asset, "updated_existing"
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset = asset_tools.create_asset(
        PRESET_NAME,
        PRESET_FOLDER,
        unreal.MoviePipelinePrimaryConfig,
        unreal.MoviePipelinePrimaryConfigFactory(),
    )
    if not isinstance(asset, unreal.MoviePipelinePrimaryConfig):
        raise RuntimeError(f"Unable to create MRQ preset: {PRESET_PATH}")
    return asset, "created"


profile, operation = load_or_create_profile()
output = profile.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
output.output_directory.set_editor_property("path", DEFAULT_OUTPUT.as_posix())
output.output_resolution = unreal.IntPoint(2560, 1440)
output.use_custom_frame_rate = True
output.output_frame_rate = unreal.FrameRate(30, 1)
output.use_custom_playback_range = True
output.custom_start_frame = 0
output.custom_end_frame = 150
output.output_frame_step = 1
output.handle_frame_count = 0
output.file_name_format = "frame_{frame_number_rel}"
output.zero_pad_frame_numbers = 4
output.override_existing_output = True
output.flush_disk_writes_per_shot = True

deferred = profile.find_or_add_setting_by_class(
    unreal.MoviePipelineDeferredPassBase
)
deferred.set_is_enabled(True)
png = profile.find_or_add_setting_by_class(
    unreal.MoviePipelineImageSequenceOutput_PNG
)
png.set_is_enabled(True)
png.write_alpha = False
aa = profile.find_or_add_setting_by_class(
    unreal.MoviePipelineAntiAliasingSetting
)
aa.spatial_sample_count = 1
aa.temporal_sample_count = 1
aa.engine_warm_up_count = 16
aa.render_warm_up_count = 8
aa.render_warm_up_frames = True
aa.use_camera_cut_for_warm_up = True
profile.initialize_transient_settings()

if not unreal.EditorAssetLibrary.save_loaded_asset(profile, only_if_is_dirty=False):
    raise RuntimeError(f"Unable to save MRQ preset: {PRESET_PATH}")

user_settings = profile.get_user_settings()
setting_classes = sorted(item.get_class().get_name() for item in user_settings)
checks = {
    "resolution_2560x1440": output.output_resolution
    == unreal.IntPoint(2560, 1440),
    "frame_rate_30": output.output_frame_rate.numerator == 30
    and output.output_frame_rate.denominator == 1,
    "custom_range_150": bool(output.use_custom_playback_range)
    and int(output.custom_start_frame) == 0
    and int(output.custom_end_frame) == 150,
    "png_enabled": bool(png.is_enabled()),
    "deferred_pass_enabled": bool(deferred.is_enabled()),
    "single_sample_aa": int(aa.spatial_sample_count) == 1
    and int(aa.temporal_sample_count) == 1,
}
report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed" if all(checks.values()) else "failed",
    "operation": operation,
    "preset": profile.get_path_name(),
    "render_contract": {
        "width": 2560,
        "height": 1440,
        "fps": 30,
        "start_frame_inclusive": 0,
        "end_frame_exclusive": 150,
        "expected_frame_count": 150,
        "expected_duration_seconds": 5.0,
        "master_format": "png_sequence",
        "delivery_format": "h264_mp4",
        "spatial_samples": 1,
        "temporal_samples": 1,
    },
    "settings": setting_classes,
    "checks": checks,
}
if report["status"] != "passed":
    raise RuntimeError(f"MRQ profile verification failed: {checks}")
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("DM_RENDER_PROFILE=" + json.dumps(report, ensure_ascii=False))
