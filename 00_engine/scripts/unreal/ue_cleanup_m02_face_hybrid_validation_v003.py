"""Remove temporary editor actors used by the M02 hybrid-face review."""

import json

import unreal


LABELS = {
    "DM_M02_FaceHybridTest_Audience_v003",
    "DM_M02_FaceHybridControl_Audience_v003",
    "DM_M02_FaceHybridTest_Walk_v003",
    "DM_M02_FaceHybridControl_Walk_v003",
}

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed = []
for actor in actor_subsystem.get_all_level_actors():
    if actor.get_actor_label() in LABELS:
        removed.append(actor.get_path_name())
        actor_subsystem.destroy_actor(actor)
actor_subsystem.set_selected_level_actors([])
print(
    "DM_FACE_HYBRID_CLEANUP="
    + json.dumps({"removed": removed, "success": True}, sort_keys=True)
)
