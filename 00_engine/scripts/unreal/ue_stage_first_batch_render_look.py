"""Replace the character in the isolated First Batch render staging map."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import unreal


STAGE_MAP = str(globals()["DM_STAGE_MAP"])
LOOK_ID = str(globals()["DM_LOOK_ID"])
BLUEPRINT_CLASS = str(globals()["DM_BLUEPRINT_CLASS"])
ACTOR_LABEL = "DM First Batch Render Character"


if not unreal.EditorAssetLibrary.does_asset_exist(STAGE_MAP):
    raise RuntimeError(f"Missing staging map: {STAGE_MAP}")
if not unreal.EditorLevelLibrary.load_level(STAGE_MAP):
    raise RuntimeError(f"Unable to load staging map: {STAGE_MAP}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = list(actor_subsystem.get_all_level_actors())
labelled = [actor for actor in actors if actor.get_actor_label() == ACTOR_LABEL]
cc_actors = [actor for actor in actors if actor.get_name().startswith("CC_FB_")]
candidates = labelled or cc_actors
if not candidates:
    raise RuntimeError("Staging map contains no character transform anchor")
anchor = candidates[0]
location = anchor.get_actor_location()
rotation = anchor.get_actor_rotation()
scale = anchor.get_actor_scale3d()
removed = []
for actor in sorted(set(labelled + cc_actors), key=lambda item: item.get_name()):
    removed.append(actor.get_path_name())
    actor_subsystem.destroy_actor(actor)
actor_subsystem.set_selected_level_actors([])
unreal.SystemLibrary.collect_garbage()

blueprint_class = unreal.load_object(None, BLUEPRINT_CLASS)
if blueprint_class is None:
    raise RuntimeError(f"Missing generated Blueprint class: {BLUEPRINT_CLASS}")
spawned = actor_subsystem.spawn_actor_from_class(blueprint_class, location, rotation)
if spawned is None:
    raise RuntimeError(f"Unable to spawn Look {LOOK_ID}")
spawned.set_actor_scale3d(scale)
spawned.set_actor_label(ACTOR_LABEL, mark_dirty=True)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError(f"Unable to save staging map: {STAGE_MAP}")

report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed",
    "map": STAGE_MAP,
    "look_id": LOOK_ID,
    "blueprint_class": BLUEPRINT_CLASS,
    "actor_name": spawned.get_name(),
    "actor_label": spawned.get_actor_label(),
    "removed_actor_count": len(removed),
    "transform": {
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.roll, rotation.pitch, rotation.yaw],
        "scale": [scale.x, scale.y, scale.z],
    },
}
print("DM_FIRST_BATCH_LOOK_STAGED=" + json.dumps(report, ensure_ascii=False))
