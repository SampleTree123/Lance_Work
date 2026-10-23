"""Build the scoped female hair x outfit visual-review matrix.

The matrix deliberately works at garment-model level.  Shoe/color variants and
families explicitly excluded by the user are not expanded because they cannot
change the head/hair intersection being reviewed.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
REGISTRY = Path(
    r"D:/UE/exports/character_creator/wardrobe_average_20260906_v1/manifests/v3/wardrobe_registry.json"
)
WARDROBE_REPORTS = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "wardrobe_average_20260906_v1"
)
HAIR_REPORT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "scalp_hair_batch_20260924_v1"
    / "batch_import_report.json"
)
OUTPUT = (
    LANCE_ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "hair_outfit_compatibility_20260926_v1"
    / "compatibility_plan.json"
)

TARGET_FAMILY_ASSETS = {
    "female.dress_collection": {
        "group_id": "full_body",
        "slots": {"full_body"},
        "display_order": 1,
    },
    "female.streetwear_collection": {
        "group_id": "selected_head_risk_coats",
        "asset_ids": {
            "female.streetwear_collection.asset.9ac2b52ae980",  # WarriorCloak_A
            "female.streetwear_collection.asset.0fa43a7cfabb",  # Windbreaker_A
        },
        "display_order": 2,
    },
}

BODYFIT = "F02_Average"
BLUEPRINT = "/Game/DataMake/Characters/ModularOutfitPilot/F02_Average/BP_DM_F02_Average_ModularOutfitPilot_v002"
SKELETON = "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/F02_Average/Cases/F_BASE/FullReference/CC_MOD_F_BASE_UE58_Skeleton"
LEVEL = "/Game/DataMake/Validation/ScalpHairCompatibility/L_DM_ScalpHairCompatibility_Review_v001"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: str) -> str:
    return str(value).replace("\\", "/").casefold()


def main() -> None:
    registry = read(REGISTRY)
    if not HAIR_REPORT.is_file():
        raise FileNotFoundError(HAIR_REPORT)
    hair_report = read(HAIR_REPORT)
    if hair_report.get("success") is not True or len(hair_report.get("records", [])) != 40:
        raise ValueError("Expected the validated 40-style scalp hair import report")

    modules = {}
    for report_path in sorted(WARDROBE_REPORTS.glob("batch_*/wardrobe_modules.json")):
        report = read(report_path)
        if report.get("success") is not True:
            continue
        for case in report.get("cases", []):
            for module in case.get("modules", []):
                key = norm(module.get("source_path", ""))
                if key:
                    modules[key] = module

    families = {item["document"]["family_id"]: item["document"] for item in registry["families"]}
    targets = []
    for family_id, rule in TARGET_FAMILY_ASSETS.items():
        family = families[family_id]
        for asset in family["assets"]:
            if "asset_ids" in rule and asset["asset_id"] not in rule["asset_ids"]:
                continue
            if "slots" in rule and asset.get("slot") not in rule["slots"]:
                continue
            binding = next(
                binding
                for binding in registry["asset_bindings"]
                if binding["family_id"] == family_id
                and binding["asset_id"] == asset["asset_id"]
            )
            source_path = binding["source_path"]
            module = modules.get(norm(source_path))
            if not module:
                raise ValueError(f"No transferred UE module found for {source_path}")
            targets.append(
                {
                    "family_id": family_id,
                    "family_display_name": family.get("display_name", family_id),
                    "group_id": rule["group_id"],
                    "asset_id": asset["asset_id"],
                    "display_name": asset.get("display_name", asset["asset_id"]),
                    "slot": asset.get("slot"),
                    "source_path": source_path,
                    "unit_id": binding["unit_id"],
                    "module_key": module["module_key"],
                    "mesh_paths": module["mesh_paths"],
                    "mesh_names": module.get("mesh_names", []),
                    "ue_case_root": next(
                        unit["ue_case_root"]
                        for unit in registry["units"]
                        if unit["unit_id"] == binding["unit_id"]
                    ),
                    "review_scope": "head_hair_intersection_garment_model_only",
                }
            )
    targets.sort(key=lambda row: (TARGET_FAMILY_ASSETS[row["family_id"]]["display_order"], row["display_name"]))
    for index, target in enumerate(targets, 1):
        target["outfit_index"] = index

    hair_styles = []
    excluded = {"cc_base_body", "cc_base_eye", "cc_base_eyeocclusion", "cc_base_tearline", "cc_base_teeth", "cc_base_tongue"}
    for record in hair_report["records"]:
        meshes = [mesh for mesh in record["runtime_hair_meshes"] if mesh["name"] not in excluded]
        if not meshes:
            raise ValueError(f"No hair meshes for {record['preset_id']}")
        hair_id = record["preset_id"].replace("_F_BATCH20260924", "")
        hair_styles.append(
            {
                "hair_index": len(hair_styles) + 1,
                "hair_id": hair_id,
                "preset_id": record["preset_id"],
                "display_name": record["display_name"],
                "meshes": [
                    {
                        "name": mesh["name"],
                        "path": mesh["path"],
                        "materials": mesh.get("materials", []),
                    }
                    for mesh in meshes
                ],
            }
        )

    cases = []
    index = 1
    for outfit in targets:
        for hair in hair_styles:
            cases.append(
                {
                    "review_index": index,
                    "outfit_index": outfit["outfit_index"],
                    "hair_index": hair["hair_index"],
                    "outfit_id": outfit["asset_id"],
                    "hair_id": hair["hair_id"],
                    "label": f"{outfit['display_name']} × {hair['display_name']}",
                    "visual_decision": "pending",
                }
            )
            index += 1

    result = {
        "schema_version": 1,
        "plan_id": "hair_outfit_compatibility_20260926_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "level": LEVEL,
        "bodyfit_id": BODYFIT,
        "blueprint_path": BLUEPRINT,
        "skeleton_path": SKELETON,
        "outfit_targets": targets,
        "hair_styles": hair_styles,
        "cases": cases,
        "counts": {
            "outfit_targets": len(targets),
            "hair_styles": len(hair_styles),
            "review_cases": len(cases),
        },
        "scope": {
            "female_dress_collection": "all Full-body assets only",
            "female_streetwear_collection": ["WarriorCloak_A", "Windbreaker_A"],
            "excluded": [
                "female.rugged_trendy",
                "male.redsoul",
                "male.rugged_trendy",
                "color-only B/C variants",
                "unselected clothing families",
            ],
            "shoe_and_unrelated_slot_policy": "not expanded; this review targets hair-head intersection",
        },
        "status": "ready_for_ue_review",
        "visual_acceptance": "pending",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **result["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
