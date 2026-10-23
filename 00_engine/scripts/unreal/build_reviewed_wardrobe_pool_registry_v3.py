"""Publish universal female footwear, preserving source assets and male rules."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import formal_wardrobe_registry_v1 as formal
from build_reviewed_wardrobe_pool_registry_v1 import digest, read, write_new, HAIR_COUNTS, SCOPE

PARENT_SHA = "42bea3d643cff65734efa21b7ed9282ae654cd49365346bd327ac284277d1f24"


def revise_mapping(parent: dict, source: dict, registry: dict) -> tuple[dict, dict]:
    mapping = copy.deepcopy(parent)
    female_families = {f["family_id"]: f for f in source["families"] if f["sex"] == "female"}
    removed = {a["asset_id"] for f in female_families.values() for a in f["assets"] if a["slot"] == "shoes"}
    counts = {"female": 0, "male": 0}
    replacements = []
    for row in mapping["outfits"]:
        if row["status"] != "retained":
            continue
        sex = row["character_sex"]
        counts[sex] += 1
        if sex == "female":
            request = row["request"]
            before = copy.deepcopy(request)
            request["family_asset_ids"] = [a for a in request["family_asset_ids"] if a not in removed]
            if request.get("shared_shoe_id") not in formal.FEMALE_SHARED_SHOE_IDS:
                request["shared_shoe_id"] = "F001"
            replacements.append({"historical_sex_index": row["historical_sex_index"], "before": before, "after": copy.deepcopy(request)})
            resolved = formal.resolve_selection(registry, **request)
            row["assignments"] = resolved["assignments"]
            row["resolved_variant_id"] = resolved["qualified_variant_id"]
        else:
            resolved = formal.resolve_selection(registry, **row["request"])
            if resolved["assignments"] != row["assignments"] or resolved["qualified_variant_id"] != row["resolved_variant_id"]:
                raise ValueError("Male preset changed")
    if counts != {"female": 79, "male": 73}:
        raise ValueError("Unexpected preset coverage")
    # Exercise every legal female group against every allowed shoe, not only presets.
    import complete_character_slot_review_contract_v1 as slots
    coverage = []
    for family in registry["families"]:
        if family["sex"] != "female":
            continue
        groups = ([family["assembly"]["bundle"]["bundle_id"]] if family["assembly_mode"] == "locked_bundle"
                  else [g["group_id"] for g in family["assembly"]["groups"]])
        for gid in groups:
            for shoe in formal.FEMALE_SHARED_SHOE_IDS:
                choice = slots._default(registry, family["family_id"], gid)
                choice["shared_shoe_id"] = shoe
                request, _ = slots._canonical(registry, "female", choice)
                resolved = formal.resolve_selection(registry, character_sex="female", **request)
                actual = [a["source_component_name"] for a in resolved["assignments"] if a["slot"] == "shoes"]
                if actual != [shoe]:
                    raise ValueError("Female outfit has missing or additional footwear")
                coverage.append({"family_id": family["family_id"], "group_id": gid, "shared_shoe_id": shoe})
    return mapping, {"retained_by_sex": counts, "retained_witnesses": 152,
        "female_preset_migrations": replacements, "female_group_shoe_coverage": coverage,
        "female_group_shoe_cases": len(coverage), "male_presets_and_families_preserved": True,
        "geometry_or_UE_visual_test": False, "user_reports_pool_compatible_with_all_clothing": True}


def publish() -> dict:
    parent = formal.reviewed_pool_v2_registry_path()
    if digest(parent) != PARENT_SHA:
        raise ValueError("Unexpected v2 parent bytes")
    parent_receipt = read(formal.REVIEWED_POOL_V2_PUBLICATION)
    protected = [parent, formal.REVIEWED_POOL_V2_PUBLICATION]
    protected += [Path(parent_receipt[k]) for k in ("mapping_report", "selection_validation", "protected_sources_report", "feedback")]
    before = {str(p): digest(p) for p in protected}
    source = read(parent)
    registry = formal.reviewed_pool_v3_expected(source, PARENT_SHA)
    mapping, validation = revise_mapping(read(Path(parent_receipt["mapping_report"])), source, registry)
    for key in ("hair_assets",):
        if source[key] != registry[key]:
            raise ValueError("Hair changed")
    if [f for f in source["families"] if f["sex"] == "male"] != [f for f in registry["families"] if f["sex"] == "male"]:
        raise ValueError("Male family changed")
    if [s for s in source["shared_shoe_assets"] if s["sex"] != "female"] != [s for s in registry["shared_shoe_assets"] if s["sex"] != "female"]:
        raise ValueError("Male shared footwear changed")
    write_new(formal.REVIEWED_POOL_V3_REGISTRY, registry)
    common = {"success": True, "publication_id": formal.REVIEWED_POOL_V3_ID,
              "output_registry_sha256": digest(formal.REVIEWED_POOL_V3_REGISTRY)}
    root = formal.REVIEWED_POOL_V3_PUBLICATION.parent
    evidence = {"mapping_report": {**mapping, **common}, "selection_validation": {**validation, **common},
        "feedback": {**common, "source": "direct_user_20261007", "male_unchanged": True,
            "female_all_outfits_use_one_shared_pool": True, "excluded_range": formal.FEMALE_EXCLUDED_SHOE_IDS,
            "previously_absent_ids": ["F006", "F007", "F008", "F009"],
            "retained_ids": formal.FEMALE_SHARED_SHOE_IDS,
            "source_assets_deleted": False, "scope": "selection_rules_user_approved_no_new_visual_acceptance"}}
    after = {str(p): digest(p) for p in protected}
    if before != after:
        raise ValueError("Protected parent sources changed")
    evidence["protected_sources_report"] = {**common, "scope": "listed JSON sources; no UE writes",
        "records": [{"path": p, "before_sha256": sha, "after_sha256": after[p], "unchanged": True} for p, sha in before.items()]}
    manifest = {**common, "counts": formal.REVIEWED_POOL_V3_COUNTS, "hair_selection_counts": HAIR_COUNTS,
                "scope": SCOPE, "male_preserved": True, "female_shared_shoe_ids": formal.FEMALE_SHARED_SHOE_IDS,
                "published_at": (read(formal.REVIEWED_POOL_V3_PUBLICATION)["published_at"]
                                 if formal.REVIEWED_POOL_V3_PUBLICATION.exists() else datetime.now(timezone.utc).isoformat())}
    paths = {"source_registry": parent, "source_publication": formal.REVIEWED_POOL_V2_PUBLICATION,
             "output_registry": formal.REVIEWED_POOL_V3_REGISTRY}
    for key, value in evidence.items():
        paths[key] = root / (key + "_v3.json")
        write_new(paths[key], value)
    for key, path in paths.items():
        manifest[key], manifest[key + "_sha256"] = str(path), digest(path)
    write_new(formal.REVIEWED_POOL_V3_PUBLICATION, manifest)
    formal.reviewed_pool_v3_registry_path()
    return manifest


if __name__ == "__main__":
    result = publish()
    print(json.dumps({k: result[k] for k in ("success", "output_registry", "output_registry_sha256", "counts", "female_shared_shoe_ids")}, indent=2))
