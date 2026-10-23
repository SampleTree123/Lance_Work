"""Remove temporary P0 runtime validation actors from the editor level."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_cleanup_p0_runtime_validation.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


import json

import unreal


LABELS = {
    "DM_P0_F02_Walk",
    "DM_P0_F02_Idle",
    "DM_P0_M02_Walk",
    "DM_P0_M02_Understood",
}

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed = []
for actor in actor_subsystem.get_all_level_actors():
    if actor.get_actor_label() in LABELS:
        removed.append(actor.get_path_name())
        actor_subsystem.destroy_actor(actor)
actor_subsystem.set_selected_level_actors([])

print(
    "DM_P0_RUNTIME_CLEANUP="
    + json.dumps(
        {
            "removed": removed,
            "removed_count": len(removed),
            "success": len(removed) == len(LABELS),
        },
        sort_keys=True,
    )
)
