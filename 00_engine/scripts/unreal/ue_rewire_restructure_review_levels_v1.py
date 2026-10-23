"""Switch existing validation levels from old module meshes to curated copies."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1")
LEVELS = [
    "/Game/DataMake/Validation/AssetRestructurePilot/L_DM_AssetRestructure_Compare_v001",
    "/Game/DataMake/Validation/ScalpHairCompatibility/L_DM_ScalpHairCompatibility_Review_v001",
    "/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Batch003",
    "/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Coverage",
    "/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Review",
]


def run():
    plan = json.loads((ROOT / "migration_plan.json").read_text(encoding="utf-8"))
    mesh_map = {item["old"]: item["new"] for case in plan["cases"] for item in case["assets"]
                if item["class"] == "SkeletalMesh"}
    pilot_path = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_pilot_20260928_v1\ue_copy_report.json")
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    for case in pilot["cases"]:
        for item in case["meshes"]:
            mesh_map[item["new"]] = mesh_map[item["old"]]
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    result = {"schema_version": 1, "levels": [], "success": False}
    try:
        for level in LEVELS:
            if not levels.load_level(level):
                raise RuntimeError(f"cannot load level: {level}")
            edits = []
            for actor in actors.get_all_level_actors():
                for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                    current = component.get_skeletal_mesh_asset()
                    old = current.get_path_name() if current is not None else None
                    if old not in mesh_map:
                        continue
                    new = unreal.load_asset(mesh_map[old])
                    if not isinstance(new, unreal.SkeletalMesh):
                        raise RuntimeError(f"mapped mesh missing: {mesh_map[old]}")
                    component.set_skeletal_mesh_asset(new)
                    edits.append({"actor": actor.get_actor_label(), "old": old, "new": mesh_map[old]})
                if level.endswith("L_DM_AssetRestructure_Compare_v001"):
                    label = actor.get_actor_label()
                    if label.startswith("DM_RestructureCompare_Original_"):
                        actor.set_actor_label(label.replace("_Original_", "_Migrated_", 1))
                    elif label.startswith("DM_RestructureCompare_Copied_"):
                        actor.set_actor_label(label.replace("_Copied_", "_Current_", 1))
            if edits and not levels.save_current_level():
                raise RuntimeError(f"cannot save rewired level: {level}")
            result["levels"].append({"level": level, "replaced_components": len(edits), "edits": edits})
            (ROOT / "level_rewire_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            unreal.log(f"DataMake rewired level {level}: {len(edits)} components")
        result["success"] = True
    finally:
        (ROOT / "level_rewire_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


run()
