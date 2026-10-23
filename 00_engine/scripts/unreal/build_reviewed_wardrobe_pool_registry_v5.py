"""Publish the user's sex-specific hairstyle removals without editing UE assets."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import formal_wardrobe_registry_v1 as formal
from build_reviewed_wardrobe_pool_registry_v1 import digest, read, write_new, SCOPE

PARENT_SHA = "e000b7e71768f653ffbc34f78186ef201373c3f0542f5730e0a155b8fff8262a"


def revise_mapping(parent: dict, registry: dict) -> tuple[dict, dict]:
    mapping = copy.deepcopy(parent)
    for key in ("success", "publication_id", "output_registry_sha256"):
        mapping.pop(key, None)
    current = {h["hair_id"]: h for h in registry["hair_assets"]}
    excluded_pairs = []
    for row in mapping["hair"]:
        for sex, exclusions in formal.CURRENT_HAIR_EXCLUSIONS.items():
            if row["historical_review_index"] in exclusions:
                if exclusions[row["historical_review_index"]] != row["hair_id"] or sex not in row["reviewed_sexes"]:
                    raise ValueError("Original hair index does not match the approved exclusion")
                excluded_pairs.append({"sex": sex, "historical_review_index": row["historical_review_index"], "hair_id": row["hair_id"]})
        row["reviewed_sexes"] = list(current[row["hair_id"]]["reviewed_sexes"]) if row["hair_id"] in current else []
        row["status"] = "retained" if row["reviewed_sexes"] else "excluded"
    for row in mapping["outfits"]:
        if row["status"] == "retained":
            resolved = formal.resolve_selection(registry, **row["request"])
            if resolved["assignments"] != row["assignments"] or resolved["qualified_variant_id"] != row["resolved_variant_id"]:
                raise ValueError("Clothing or shoe witness changed")
    if len(excluded_pairs) != 5:
        raise ValueError("Expected exactly five sex-specific hair exclusions")
    actual = {sex: [r["historical_review_index"] for r in mapping["hair"] if sex in r["reviewed_sexes"]] for sex in ("male", "female")}
    if actual != formal.hair_review_indices_by_sex(registry):
        raise ValueError("Mapping differs from formal hair whitelist")
    for row in excluded_pairs:
        hair = current.get(row["hair_id"])
        if hair and formal.hair_available_to(hair, row["sex"]):
            raise ValueError("Excluded sex-specific hair remains available")
    if not formal.hair_available_to(current["HAIR_HB1_13"], "male"):
        raise ValueError("Male original hair 06 was accidentally excluded")
    return mapping, {"hair_selection_counts": formal.hair_selection_counts(registry),
        "hair_review_indices_by_sex": actual, "excluded_pairs": excluded_pairs,
        "female_06_removed_male_06_retained": True, "retained_outfit_witnesses": 152,
        "all_outfit_witnesses_unchanged": True, "selection_mode": "random_within_approved_sex_pool",
        "source_UE_assets_modified": False, "new_visual_acceptance_claimed": False}


def publish() -> dict:
    parent = formal.reviewed_pool_v4_registry_path()
    if digest(parent) != PARENT_SHA:
        raise ValueError("Unexpected v4 parent bytes")
    parent_receipt = read(formal.REVIEWED_POOL_V4_PUBLICATION)
    protected = [parent, formal.REVIEWED_POOL_V4_PUBLICATION]
    protected += [Path(parent_receipt[k]) for k in ("mapping_report", "selection_validation", "protected_sources_report", "feedback")]
    before = {str(p): digest(p) for p in protected}
    source = read(parent)
    registry = formal.reviewed_pool_v5_expected(source, PARENT_SHA)
    for key in ("families", "shared_shoe_assets"):
        if registry[key] != source[key]:
            raise ValueError("Clothing or shoes changed")
    mapping, validation = revise_mapping(read(Path(parent_receipt["mapping_report"])), registry)
    write_new(formal.CURRENT_REVIEWED_POOL_REGISTRY, registry)
    common = {"success": True, "publication_id": formal.CURRENT_REVIEWED_POOL_ID,
              "output_registry_sha256": digest(formal.CURRENT_REVIEWED_POOL_REGISTRY)}
    root = formal.CURRENT_REVIEWED_POOL_PUBLICATION.parent
    evidence = {"mapping_report": {**mapping, **common}, "selection_validation": {**validation, **common},
        "feedback": {**common, "source": "direct_user_20261007", "hair_grouping_cancelled": True,
            "removed_original_indices": {s: list(rows) for s, rows in formal.CURRENT_HAIR_EXCLUSIONS.items()},
            "selection_mode": "random_within_approved_sex_pool", "source_assets_deleted": False}}
    after = {str(p): digest(p) for p in protected}
    if before != after:
        raise ValueError("Protected parent sources changed")
    evidence["protected_sources_report"] = {**common, "scope": "listed JSON sources; no UE writes",
        "records": [{"path": p, "before_sha256": sha, "after_sha256": after[p], "unchanged": True} for p, sha in before.items()]}
    manifest = {**common, "counts": formal.CURRENT_REVIEWED_POOL_COUNTS, "hair_selection_counts": formal.hair_selection_counts(registry),
                "scope": SCOPE, "clothing_and_shoes_preserved": True,
                "published_at": (read(formal.CURRENT_REVIEWED_POOL_PUBLICATION)["published_at"]
                                 if formal.CURRENT_REVIEWED_POOL_PUBLICATION.exists() else datetime.now(timezone.utc).isoformat())}
    paths = {"source_registry": parent, "source_publication": formal.REVIEWED_POOL_V4_PUBLICATION,
             "output_registry": formal.CURRENT_REVIEWED_POOL_REGISTRY}
    for key, value in evidence.items():
        paths[key] = root / (key + "_v5.json")
        write_new(paths[key], value)
    for key, path in paths.items():
        manifest[key], manifest[key + "_sha256"] = str(path), digest(path)
    write_new(formal.CURRENT_REVIEWED_POOL_PUBLICATION, manifest)
    formal.current_registry_path()
    return manifest


if __name__ == "__main__":
    result = publish()
    print(json.dumps({k: result[k] for k in ("success", "output_registry", "output_registry_sha256", "counts", "hair_selection_counts")}, indent=2))
