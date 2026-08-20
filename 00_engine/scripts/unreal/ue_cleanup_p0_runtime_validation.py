"""Remove temporary P0 runtime validation actors from the editor level."""

from __future__ import annotations

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
