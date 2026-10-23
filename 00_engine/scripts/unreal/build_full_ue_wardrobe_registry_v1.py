"""Compile the agreed lean UE wardrobe registry from confirmed source rules.

Run after the full migration plan is built. The output uses only UE asset paths;
source CC paths and import reports remain in separate provenance files.
"""

from __future__ import annotations

import json
from pathlib import Path


ENGINE = Path(r"D:\UE\Lance_Work\00_engine")
SOURCE = Path(r"D:\UE\exports\character_creator\wardrobe_average_20260906_v1\manifests\v3\wardrobe_registry.json")
DRAFT = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_draft_example_v2.json"
PLAN = ENGINE / "outputs/unreal_character_import/asset_restructure_full_20260929_v1/migration_plan.json"
HAIR_MATERIAL_REPAIR = ENGINE / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/masked_repair_plan.json"
HAIR_RENDERING_REPORTS = HAIR_MATERIAL_REPAIR.parent / "rendering_repair_v2/reports"
SAVED_ASSET_AUDIT = ENGINE / "outputs/unreal_character_import/wardrobe_average_20260906_v1/ue_supervised_20260909_v3/final_saved_asset_audit.json"
OUTPUT = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json"

# Usage labels for the 40 retained hairstyles. These express the intended
# character presentation pool, not a verified fit on every head shape.
HAIR_SEX_BY_ID = {
    "HAIR_HB1_01": "both", "HAIR_HB1_02": "both", "HAIR_HB1_05": "both",
    "HAIR_HB1_09": "both", "HAIR_HB1_11": "both", "HAIR_HB1_13": "both",
    "HAIR_HB1_15": "both", "HAIR_HB1_16": "both", "HAIR_HB1_17": "both",
    "HAIR_HB1_18": "both", "HAIR_HB1_20": "both",
    "HAIR_HB2_01": "female", "HAIR_HB2_02": "female", "HAIR_HB2_04": "female",
    "HAIR_HB2_05": "female", "HAIR_HB2_06": "female", "HAIR_HB2_07": "female",
    "HAIR_HB2_08": "female", "HAIR_HB2_09": "female", "HAIR_HB2_11": "female",
    "HAIR_HB2_12": "female", "HAIR_HB2_14": "female", "HAIR_HB2_15": "female",
    "HAIR_HB2_17": "female", "HAIR_HB2_19": "female", "HAIR_HB2_20": "female",
    "HAIR_HB3_01": "male", "HAIR_HB3_02": "male", "HAIR_HB3_03": "female",
    "HAIR_HB3_04": "male", "HAIR_HB3_05": "male", "HAIR_HB3_07": "male",
    "HAIR_HB3_09": "female", "HAIR_HB3_13": "male", "HAIR_HB3_14": "female",
    "HAIR_HB3_15": "male", "HAIR_HB3_16": "male", "HAIR_HB3_17": "female",
    "HAIR_HB3_19": "male", "HAIR_HB3_20": "male",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def policy(deny=False):
    return {"allow_all": not deny, "deny_all": deny}


def run():
    source, draft, plan = read(SOURCE), read(DRAFT), read(PLAN)
    repair = read(HAIR_MATERIAL_REPAIR)
    repaired_slots = {(row["mesh"], row["slot_index"]): row for row in repair["rows"]}
    rendering_slots = {}
    for report_path in sorted(HAIR_RENDERING_REPORTS.glob("HAIR_*.json")):
        report = read(report_path)
        if report.get("success") is not True or report.get("slots") != len(report.get("materials", [])):
            raise ValueError(f"incomplete hair rendering repair report: {report_path}")
        for row in report["materials"]:
            key = (row["mesh"], row["slot"])
            if key not in repaired_slots:
                raise ValueError(f"unexpected hair rendering repair slot: {key}")
            expected = repaired_slots[key]["new_material"] + "_StrandsV2"
            if row["new_material"].split(".", 1)[0] != expected:
                raise ValueError(f"unexpected hair rendering material: {row['new_material']}")
            rendering_slots[key] = row["new_material"]
    saved_audit = read(SAVED_ASSET_AUDIT)
    if saved_audit.get("success") is not True:
        raise ValueError("saved UE asset audit is not accepted")
    by_case = {case["id"]: case for case in plan["cases"]}
    path_map = {asset["old"]: asset["new"] for case in plan["cases"] for asset in case["assets"]}
    binding = {(row["family_id"], row["asset_id"]): row["unit_id"] for row in source["asset_bindings"]}
    module_key_by_asset = {(row["family_id"], row["asset_id"]): row["module_key"] for row in source["asset_bindings"]}
    saved_modules = {
        (case["case_id"], module["module_key"]): module
        for case in saved_audit["cases"] for module in case["modules"]
    }
    # The accepted per-module audit resolves locked bundles without guessing
    # ownership from asset names or depending on directory enumeration order.
    for case in plan["cases"]:
        if case["kind"] != "wardrobe":
            continue
        expected = {asset["old"] for asset in case["assets"] if asset["class"] == "SkeletalMesh"}
        actual = [path for (case_id, _), module in saved_modules.items()
                  if case_id == case["id"] for path in module["mesh_paths"]]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError(f"saved module mesh closure differs from migrated case {case['id']}")
    denied_families = {"female.rugged_trendy", "male.redsoul", "male.rugged_trendy"}
    denied_streetwear = {
        "WarriorCloak_A", "WarriorCloak_B", "WarriorCloak_C",
        "Windbreaker_A", "Windbreaker_B", "Windbreaker_C",
    }
    families = []
    for item in source["families"]:
        document = item["document"]
        family_id = document["family_id"]
        assets = []
        for asset in document["assets"]:
            asset_id = asset["asset_id"]
            case = by_case[binding[(family_id, asset_id)]]
            module_key = module_key_by_asset[(family_id, asset_id)]
            module = saved_modules[(case["id"], module_key)]
            mesh_paths = [path_map[path] for path in module["mesh_paths"]]
            if not mesh_paths or len(mesh_paths) != len(set(mesh_paths)):
                raise ValueError(f"invalid mesh mapping for {family_id}/{asset_id}")
            if any(not path.startswith(case["new_root"] + "/Meshes/") for path in mesh_paths):
                raise ValueError(f"mesh escaped its UE case root for {family_id}/{asset_id}")
            entry = {"asset_id": asset_id, "display_name": asset["display_name"],
                     "slot": asset["slot"], "ue_case_root": case["new_root"],
                     "ue_mesh_paths": mesh_paths}
            if family_id == "female.streetwear_collection" and asset["display_name"] in denied_streetwear:
                entry["hair_interface"] = policy(True)
            assets.append(entry)
        families.append({"family_id": family_id, "display_name": document["display_name"],
                         "sex": document["sex"], "assembly_mode": document["assembly_mode"],
                         "hair_interface": policy(family_id in denied_families),
                         "assets": assets, "assembly": document["assembly"]})
    hair = []
    draft_hair_ids = {item["hair_id"] for item in draft["hair_assets"]}
    if draft_hair_ids != set(HAIR_SEX_BY_ID) or len(draft["hair_assets"]) != len(draft_hair_ids):
        raise ValueError("retained hair IDs differ from reviewed sex classifications")
    for item in draft["hair_assets"]:
        entry = {key: value for key, value in item.items() if key != "meshes"}
        entry["sex"] = HAIR_SEX_BY_ID[item["hair_id"]]
        entry["meshes"] = []
        for mesh in item["meshes"]:
            mesh_path = path_map[mesh["path"]]
            materials = [path_map[value] for value in mesh["materials"]]
            for slot_index, old_material in enumerate(materials):
                row = repaired_slots.get((mesh_path, slot_index))
                if row is None:
                    continue
                if row["hair_id"] != item["hair_id"] or row["old_material"] != old_material:
                    raise ValueError(f"hair material repair mismatch: {mesh_path} slot {slot_index}")
                materials[slot_index] = row["new_material"] + "." + row["new_material"].rsplit("/", 1)[-1]
                if (mesh_path, slot_index) in rendering_slots:
                    materials[slot_index] = rendering_slots[(mesh_path, slot_index)]
            entry["meshes"].append({"name": mesh["name"], "path": mesh_path,
                                    "materials": materials})
        hair.append(entry)
    shoes = []
    for item in draft["shared_shoe_assets"]:
        shoes.append({**item, "ue_asset_paths": [path_map[value] for value in item["ue_asset_paths"]]})
    result = {"schema_version": 4, "library_id": "wardrobe_average_20260906_v1",
              "hair_assets": hair, "shared_shoe_assets": shoes, "families": families}
    assert len(families) == 41 and sum(len(f["assets"]) for f in families) == 331
    assert len(hair) == 40 and len(shoes) == 43
    assert sum(f["hair_interface"]["deny_all"] for f in families) == 3
    assert sum(a.get("hair_interface", {}).get("deny_all", False) for f in families for a in f["assets"]) == 6
    all_ids = {a["asset_id"] for f in families for a in f["assets"]} | {a["asset_id"] for a in shoes}
    for family in families:
        for group in family["assembly"].get("groups", []):
            for pool in group.get("slot_pools", {}).values():
                if not set(pool).issubset(all_ids):
                    raise ValueError(f"assembly has unknown asset in {family['family_id']}/{group['group_id']}")
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "families": len(families),
                      "family_assets": 331, "hair": len(hair), "shared_shoes": len(shoes)}, ensure_ascii=False))


if __name__ == "__main__":
    run()
