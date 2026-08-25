"""Create or open the isolated male action-matrix staging level."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import unreal


BASE_MAP = "/Game/DataMake/Scenes/TokyoStylized/L_DM_TokyoStylized"
MALE_MAP = (
    "/Game/DataMake/Scenes/TokyoStylized/"
    "L_DM_TokyoStylized_MalePilot_v001"
)
MALE_BLUEPRINT_CLASS = (
    "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/M_ID02_O04/"
    "CC_FB_M_ID02_O04_Blueprint_LiveLink."
    "CC_FB_M_ID02_O04_Blueprint_LiveLink_C"
)
MODE = str(globals().get("DM_STAGE_MODE", "male")).lower()
MALE_LABEL = "DM First Batch Male Representative"


def all_actors():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return subsystem, list(subsystem.get_all_level_actors())


def load_level(package_path: str) -> None:
    if not unreal.EditorAssetLibrary.does_asset_exist(package_path):
        raise RuntimeError(f"Missing map asset: {package_path}")
    if not unreal.EditorLevelLibrary.load_level(package_path):
        raise RuntimeError(f"Unable to load map: {package_path}")


if MODE == "base":
    load_level(BASE_MAP)
    subsystem, actors = all_actors()
    females = [actor for actor in actors if "CC_FB_F_" in actor.get_name()]
    if len(females) != 1:
        raise RuntimeError(
            f"Expected one female representative in base map, found "
            f"{[actor.get_name() for actor in females]}"
        )
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": MODE,
        "map_package": BASE_MAP,
        "map_object": f"{BASE_MAP}.{BASE_MAP.rsplit('/', 1)[-1]}",
        "target_actor": females[0].get_name(),
        "target_actor_label": females[0].get_actor_label(),
    }
else:
    if MODE != "male":
        raise RuntimeError(f"Unsupported staging mode: {MODE}")
    if not unreal.EditorAssetLibrary.does_asset_exist(MALE_MAP):
        raise RuntimeError(
            "Male staging map has not been created in its isolated Remote "
            f"Execution pass: {MALE_MAP}"
        )
    load_level(MALE_MAP)
    subsystem, actors = all_actors()
    females = [actor for actor in actors if "CC_FB_F_" in actor.get_name()]
    males = [actor for actor in actors if "CC_FB_M_ID02_O04" in actor.get_name()]

    if len(males) > 1:
        raise RuntimeError(
            f"Expected at most one male representative, found "
            f"{[actor.get_name() for actor in males]}"
        )
    if males:
        male = males[0]
        for female in females:
            subsystem.destroy_actor(female)
    else:
        if len(females) != 1:
            raise RuntimeError(
                "A new male staging map requires exactly one female transform "
                f"source, found {[actor.get_name() for actor in females]}"
            )
        source = females[0]
        location = source.get_actor_location()
        rotation = source.get_actor_rotation()
        scale = source.get_actor_scale3d()
        male_class = unreal.load_object(None, MALE_BLUEPRINT_CLASS)
        if male_class is None:
            raise RuntimeError(f"Missing male Blueprint class: {MALE_BLUEPRINT_CLASS}")
        male = subsystem.spawn_actor_from_class(male_class, location, rotation)
        if male is None:
            raise RuntimeError("Unable to spawn the male representative")
        male.set_actor_scale3d(scale)
        male.set_actor_label(MALE_LABEL, mark_dirty=True)
        subsystem.destroy_actor(source)

    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError(f"Unable to save male staging map: {MALE_MAP}")
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": MODE,
        "map_package": MALE_MAP,
        "map_object": f"{MALE_MAP}.{MALE_MAP.rsplit('/', 1)[-1]}",
        "target_actor": male.get_name(),
        "target_actor_label": male.get_actor_label(),
        "blueprint_class": MALE_BLUEPRINT_CLASS,
        "female_actor_count_after_prepare": len(
            [actor for actor in all_actors()[1] if "CC_FB_F_" in actor.get_name()]
        ),
    }

print("DM_ACTION_MATRIX_STAGE=" + json.dumps(report, ensure_ascii=False))
