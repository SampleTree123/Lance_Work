"""Remove transient first-batch expression review actors."""

from __future__ import annotations

import json

import unreal


labels = {
    f"DM_FBEXP_{actor_id}_{expression_id.title()}"
    for actor_id in ("F02", "M02")
    for expression_id in ("happy", "angry", "sad")
}
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed = []
for actor in actor_subsystem.get_all_level_actors():
    if actor.get_actor_label() in labels:
        removed.append(actor.get_path_name())
        actor_subsystem.destroy_actor(actor)
actor_subsystem.set_selected_level_actors([])
print(
    "DM_FIRST_BATCH_EXPRESSION_CLEANUP="
    + json.dumps({"removed": removed, "success": True}, sort_keys=True)
)
