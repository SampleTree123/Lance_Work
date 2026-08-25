#!/usr/bin/env python3
"""Verify that a generated first-batch sequence actually drives a skeletal pose."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(r"D:\UE\Lance_Work")
REMOTE_EXEC = ROOT / "00_engine" / "scripts" / "unreal" / "ue_remote_exec.py"
REPORT_PATH = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_day3_20260822_v2"
    / "sequence_runtime_pose_probe.json"
)
PROJECT = "datatry_02"
DEFAULT_SEQUENCE = (
    "/Game/DataMake/Sequences/FirstBatch/LS_DM_FirstBatch_F02_20s_Pilot_v001"
)
DEFAULT_ACTOR = "CC_FB_F_ID02_O04_Blueprint_LiveLink_C_1"
DEFAULT_BONE = "upperarm_l"
SAMPLE_DELAYS_SECONDS = (0.75, 0.75, 0.75, 3.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", default=DEFAULT_SEQUENCE)
    parser.add_argument("--actor", default=DEFAULT_ACTOR)
    parser.add_argument("--bone", default=DEFAULT_BONE)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    return parser.parse_args()


ARGS = parse_args()


def remote(command: str) -> list[dict]:
    completed = subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            PROJECT,
            "--discovery-timeout",
            "15",
            "--command",
            command,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout + completed.stderr)
    envelope = json.loads(completed.stdout)
    result = envelope.get("command_result", {})
    if not result.get("success"):
        raise RuntimeError(str(result.get("result")))
    return result.get("output", [])


def start_playback() -> None:
    remote(
        "import unreal; "
        "unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence(); "
        f"s=unreal.load_asset({ARGS.sequence!r}); "
        "unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(s); "
        "unreal.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence(); "
        "unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0); "
        "unreal.LevelSequenceEditorBlueprintLibrary.play(); "
        "print('DM_RUNTIME_PLAYBACK_STARTED')"
    )


def stop_playback() -> None:
    remote(
        "import unreal; "
        "unreal.LevelSequenceEditorBlueprintLibrary.pause(); "
        "unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0); "
        "print('DM_RUNTIME_PLAYBACK_STOPPED')"
    )


def sample_runtime(index: int) -> dict:
    command = (
        "import unreal,json; "
        "ss=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); "
        f"a=[x for x in ss.get_all_level_actors() if x.get_name()=={ARGS.actor!r}][0]; "
        "c=a.get_components_by_class(unreal.SkeletalMeshComponent)[0]; "
        f"q=c.get_bone_transform({ARGS.bone!r},unreal.RelativeTransformSpace.RTS_COMPONENT).rotation; "
        "print('DM_RUNTIME_SAMPLE='+json.dumps({"
        f"'sample_index':{index},"
        "'frame':unreal.LevelSequenceEditorBlueprintLibrary.get_current_time(),"
        "'is_playing':unreal.LevelSequenceEditorBlueprintLibrary.is_playing(),"
        "'quat':[q.x,q.y,q.z,q.w],"
        "'animation_mode':str(c.get_animation_mode()),"
        "'anim_instance':c.get_anim_instance().get_class().get_name() "
        "if c.get_anim_instance() else None}))"
    )
    outputs = remote(command)
    records = [
        str(item.get("output", "")).strip()
        for item in outputs
        if str(item.get("output", "")).startswith("DM_RUNTIME_SAMPLE=")
    ]
    if len(records) != 1:
        raise RuntimeError(f"Expected one runtime sample for index {index}")
    return json.loads(records[0].split("=", 1)[1])


def quaternion_distance(left: list[float], right: list[float]) -> float:
    dot = abs(sum(a * b for a, b in zip(left, right)))
    return 1.0 - min(1.0, max(0.0, dot))


samples = []
start_playback()
try:
    for sample_index, delay in enumerate(SAMPLE_DELAYS_SECONDS):
        time.sleep(delay)
        samples.append(sample_runtime(sample_index))
finally:
    stop_playback()

frames = [sample["frame"] for sample in samples]
pose_deltas = [
    quaternion_distance(left["quat"], right["quat"])
    for left, right in zip(samples, samples[1:])
]
checks = {
    "sequencer_time_advances": all(
        later > earlier for earlier, later in zip(frames, frames[1:])
    ),
    "pose_changes_during_playback": max(pose_deltas, default=0.0) > 1.0e-4,
    "probe_crosses_second_segment": min(frames) < 150 <= max(frames),
    "playback_remains_active": all(sample["is_playing"] for sample in samples),
    "sequencer_anim_instance_active": all(
        sample["anim_instance"] == "AnimSequencerInstance" for sample in samples
    ),
}
report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "sequence": ARGS.sequence,
    "actor": ARGS.actor,
    "bone": ARGS.bone,
    "samples": samples,
    "metrics": {
        "sample_frames": frames,
        "consecutive_quaternion_distances": pose_deltas,
        "maximum_quaternion_distance": max(pose_deltas, default=0.0),
    },
    "checks": checks,
    "success": all(checks.values()),
}
ARGS.report_path.parent.mkdir(parents=True, exist_ok=True)
ARGS.report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
