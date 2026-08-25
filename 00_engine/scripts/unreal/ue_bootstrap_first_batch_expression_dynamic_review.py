"""Inject dynamic capture before PIE temporarily hides Remote Execution."""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


TARGET = str(globals().get("DM_FIRST_BATCH_EXPRESSION_TARGET", "legacy"))
CAPTURE_SCRIPT = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\unreal"
    r"\ue_capture_first_batch_expression_dynamic_review.py"
)

previous = globals().get("_dm_first_batch_expression_bootstrap_callback")
if previous is not None:
    try:
        unreal.unregister_slate_post_tick_callback(previous)
    except Exception:
        pass
globals()["_dm_first_batch_expression_bootstrap_callback"] = None


def bootstrap_tick(_delta_seconds):
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None:
        return
    handle = globals().get("_dm_first_batch_expression_bootstrap_callback")
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
    globals()["_dm_first_batch_expression_bootstrap_callback"] = None
    try:
        globals()["DM_FIRST_BATCH_EXPRESSION_TARGET"] = TARGET
        source = CAPTURE_SCRIPT.read_text(encoding="utf-8")
        exec(compile(source, str(CAPTURE_SCRIPT), "exec"), globals())
    except Exception:
        unreal.log_error(traceback.format_exc())
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if subsystem.is_in_play_in_editor():
            subsystem.editor_request_end_play()


globals()["_dm_first_batch_expression_bootstrap_callback"] = (
    unreal.register_slate_post_tick_callback(bootstrap_tick)
)
subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not subsystem.is_in_play_in_editor():
    subsystem.editor_play_simulate()
print(
    "DM_FIRST_BATCH_EXPRESSION_BOOTSTRAP="
    + json.dumps({"target": TARGET, "success": True}, sort_keys=True)
)
