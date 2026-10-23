"""Plan a reversible masked-hair material repair from the UE material-slot audit."""

from __future__ import annotations

import json
from pathlib import Path


ENGINE = Path(__file__).resolve().parents[2]
ROOT = ENGINE / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
AUDIT = ROOT / "material_slot_audit.json"
PLAN = ROOT / "masked_repair_plan.json"
TEMPLATE = "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/Materials/CC_M02_Average_Pilot_UE58/Hair1_Transparency_LWHQ_Inst"
FALLBACK = {
    ("HAIR_HB1_01", "Hair134_Transparency_Pbr"):
    "/Game/DataMake/CharacterFactory/Hair/HB1_01/Textures/Hair135_Transparency_Pbr_Diffuse.Hair135_Transparency_Pbr_Diffuse",
}


def is_hair_card(row: dict) -> bool:
    name = row["slot_name"].lower()
    return (name.startswith(("hair", "scalp", "babyhair"))
            and "transparency" in name
            and not any(token in name for token in ("clip", "ring", "band")))


def build_plan(audit: dict) -> dict:
    rows = []
    targets = {}
    fallback_used = []
    for row in audit["rows"]:
        if not is_hair_card(row):
            continue
        textures = row["textures"]
        diffuse = textures.get("DiffuseColorMap") or FALLBACK.get((row["hair_id"], row["slot_name"]))
        opacity = textures.get("OpacityMaskMap") or textures.get("OpacityMap")
        if not diffuse or not opacity:
            raise ValueError(f"Hair card has no complete texture pair: {row['hair_id']} {row['slot_name']}")
        root, marker, _ = row["mesh"].partition("/Meshes/")
        if not marker or not root.startswith("/Game/DataMake/CharacterFactory/Hair/"):
            raise ValueError(f"Unexpected hair mesh path: {row['mesh']}")
        if row["parent"] != "/InterchangeAssets/Materials/FBXLegacyPhongSurfaceMaterial.FBXLegacyPhongSurfaceMaterial":
            raise ValueError(f"Unexpected hair material parent: {row['material']}")
        material_name = row["material"].rsplit("/", 1)[-1].split(".", 1)[0]
        target = root + "/RuntimeMaterials/MI_" + material_name + "_Masked"
        prior = targets.get(target)
        if prior and prior != (diffuse, opacity):
            raise ValueError(f"Conflicting texture pairs for {target}")
        targets[target] = (diffuse, opacity)
        if (row["hair_id"], row["slot_name"]) in FALLBACK:
            fallback_used.append(row["material"])
        rows.append({
            "hair_id": row["hair_id"], "mesh": row["mesh"], "slot_index": row["slot_index"],
            "slot_name": row["slot_name"], "old_material": row["material"],
            "new_material": target, "diffuse": diffuse, "opacity": opacity,
        })
    if len(rows) != 220 or len({r["hair_id"] for r in rows}) != 40 or len(fallback_used) != 1:
        raise ValueError("Material repair scope differs from the frozen 40-hair audit")
    return {"schema_version": 1, "source_audit": str(AUDIT), "template": TEMPLATE,
            "hair_count": 40, "slot_count": len(rows), "new_material_count": len(targets),
            "explicit_diffuse_fallbacks": fallback_used, "rows": rows,
            "non_hair_or_accessory_slots_unchanged": audit["slot_count"] - len(rows)}


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    plan = build_plan(audit)
    if PLAN.exists() and json.loads(PLAN.read_text(encoding="utf-8")) != plan:
        raise FileExistsError(f"Material plan changed; use a new version: {PLAN}")
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"plan": str(PLAN), "hairs": plan["hair_count"],
                      "slots": plan["slot_count"], "material_instances": plan["new_material_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
