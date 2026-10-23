"""Persist scalp-hair visual review alignment inside the existing Body Blueprint.

The first review level used separate SkeletalMeshActor followers.  Their
cross-actor Leader Pose links are not serialized when the level is reloaded.
This repair uses the Blueprint's empty BundlePart components, which already
have persistent Body Leader Pose bindings, without changing the Blueprint
asset or its formal outfit contract.
"""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_repair_scalp_hair_review_alignment_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


from datetime import datetime, timezone
import json
from pathlib import Path

import unreal


LEVEL_PATH = "/Game/DataMake/Validation/ScalpHairPilot/L_DM_ScalpHairPilot_Review_v001"
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\scalp_hair_pilot_20260923_111307_interchange\hair_visual_review_alignment_repair_v1.json"
)
HAIR_MESHES = [
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/hair_base",
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/side_bangs",
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/curly_long_hair",
    "/Game/Vendor/Reallusion/CC5/ScalpHairPilot/F02_Average/HB1_01_Interchange/Modules/curly_ponytail_back",
]


def write_report(payload):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def run():
    result = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "level": LEVEL_PATH,
        "formal_blueprint_modified": False,
        "success": False,
    }
    try:
        level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if not level_subsystem.load_level(LEVEL_PATH):
            raise RuntimeError(f"Unable to load review level: {LEVEL_PATH}")
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = actor_subsystem.get_all_level_actors()
        # Remove the non-persistent hair followers from the first review pass.
        removed = []
        for actor in list(actors):
            if actor.get_actor_label().startswith("DM_ScalpHairReview_") and "_HB1_01_" in actor.get_actor_label():
                removed.append(actor.get_actor_label())
                actor_subsystem.destroy_actor(actor)

        staged = []
        for bodyfit_id in ("M02_Average", "F02_Average"):
            body_actor = next(
                actor for actor in actor_subsystem.get_all_level_actors()
                if actor.get_actor_label() == f"DM_ScalpHairReview_{bodyfit_id}"
            )
            components = {
                component.get_name(): component
                for component in body_actor.get_components_by_class(unreal.SkeletalMeshComponent)
            }
            body = components["Body"]
            item_records = []
            for index, mesh_path in enumerate(HAIR_MESHES, start=1):
                slot_name = f"BundlePart{index:02d}"
                component = components[slot_name]
                mesh = unreal.load_asset(mesh_path)
                if mesh is None:
                    raise RuntimeError(f"Hair mesh is unavailable: {mesh_path}")
                component.set_skeletal_mesh_asset(mesh)
                component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                component.set_visibility(True, False)
                try:
                    component.set_hidden_in_game(False)
                except Exception:
                    pass
                item_records.append(
                    {
                        "slot": slot_name,
                        "mesh": mesh_path,
                        "leader": component.get_editor_property("leader_pose_component").get_name()
                        if component.get_editor_property("leader_pose_component")
                        else None,
                        "leader_is_body": component.get_editor_property("leader_pose_component") == body,
                        "visible": component.is_visible(),
                    }
                )
            staged.append({"bodyfit_id": bodyfit_id, "actor": body_actor.get_path_name(), "hair": item_records})

        level_subsystem.editor_set_viewport_realtime(True)
        if not level_subsystem.save_current_level():
            raise RuntimeError(f"Unable to save review level: {LEVEL_PATH}")
        # Reopen to verify that the Body-bound links and mesh assignments persist.
        if not level_subsystem.load_level(LEVEL_PATH):
            raise RuntimeError("Unable to reload repaired review level")
        reloaded = []
        for bodyfit_id in ("M02_Average", "F02_Average"):
            body_actor = next(
                actor for actor in actor_subsystem.get_all_level_actors()
                if actor.get_actor_label() == f"DM_ScalpHairReview_{bodyfit_id}"
            )
            components = {
                component.get_name(): component
                for component in body_actor.get_components_by_class(unreal.SkeletalMeshComponent)
            }
            body = components["Body"]
            reloaded.append(
                {
                    "bodyfit_id": bodyfit_id,
                    "hair": [
                        {
                            "slot": f"BundlePart{index:02d}",
                            "mesh": components[f"BundlePart{index:02d}"].get_skeletal_mesh_asset().get_path_name()
                            if components[f"BundlePart{index:02d}"].get_skeletal_mesh_asset()
                            else None,
                            "leader_is_body": components[f"BundlePart{index:02d}"].get_editor_property("leader_pose_component") == body,
                            "visible": components[f"BundlePart{index:02d}"].is_visible(),
                        }
                        for index in range(1, 5)
                    ],
                }
            )
        result.update({"removed_separate_followers": removed, "staged": staged, "reloaded": reloaded, "success": True})
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        write_report(result)
    unreal.log("DataMake scalp hair alignment repair: " + json.dumps(result, ensure_ascii=False, default=str))
    if not result["success"]:
        unreal.log_error("Scalp hair alignment repair failed")


run()
