"""Publish the approved 2026-10-06 selection without editing any UE assets.

Source permissions and geometry stay intact. reviewed_sexes is a separate,
restrictive selection policy. Historical receipts are inputs, never rewritten.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import formal_wardrobe_registry_v1 as formal

RUN_ROOT = formal.ENGINE / "outputs/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1"
CANDIDATE = RUN_ROOT / "diagnostics_v1/modular_assembly_candidate_registry_v1.json"
FEEDBACK = RUN_ROOT / "human_review_feedback_v1.json"
REVIEW_PLAN = formal.ENGINE / "outputs/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage/review_plan.json"
OUTPUT_ROOT = formal.REVIEWED_POOL_PUBLICATION.parent
SCOPE = "reviewed_selection_rules_not_new_body_visual_acceptance"
INDICES = {
    "male": [1, 2, 3, 5, 6, 11, 27, 28, 30, 31, 32, 36, 37, 39, 40],
    "female": [1, 2, 3, 5, 6, 8, 9, 10, 11, 14, 15, 16, 17, 19, 22, 23, 24, 25, 26, 29, 33, 35, 38],
}
EXCLUDED_FAMILIES = {"female.rugged_trendy", "male.kilt"}
EXCLUDED_GROUPS = {"pants_with_shirt", "pants_with_casual_jacket",
                   "pants_with_warrior_cloak", "pants_with_windbreaker"}
MASK_ID = "male.cyberpunk_locked.asset.dfdf5cd81df8"
COUNTS = {"families": 39, "family_assets": 320, "shared_shoes": 43, "hair": 32}
HAIR_COUNTS = {"male": 15, "female": 23, "union": 32, "overlap": 6}
SOURCE_SHA = "15d83025446fc472a2275f1b39aa483f99f644aad60cd32052ee21afaedeb5a6"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_new(path: Path, value: dict) -> None:
    """Versioned outputs are immutable; identical reruns are safe."""
    data = encoded(value)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Refusing to replace existing version: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def build_registry(source: dict, candidate: dict, feedback: dict) -> dict:
    """Reconstruct the approved delta and require proposal agreement."""
    formal.validate_registry(source)
    expected = copy.deepcopy(source)
    indexed = dict(enumerate(sorted(source["hair_assets"], key=lambda h: h["hair_id"]), 1))
    for sex, indices in INDICES.items():
        rows = feedback["hair"]["selected_by_sex"][sex]
        if [r["review_index"] for r in rows] != indices:
            raise ValueError(f"Feedback whitelist differs for {sex}")
        for row in rows:
            original = indexed[row["review_index"]]
            if (row["hair_id"] != original["hair_id"]
                    or row["original_sex_permission"] != original["sex"]
                    or original["sex"] not in {sex, "both"}):
                raise ValueError("Feedback numbering or original permission differs")
    selected = set(INDICES["male"]) | set(INDICES["female"])
    expected["hair_assets"] = [copy.deepcopy(h) for i, h in indexed.items() if i in selected]
    expected["families"] = [f for f in expected["families"] if f["family_id"] not in EXCLUDED_FAMILIES]
    for family in expected["families"]:
        if family["family_id"] == "female.streetwear_collection":
            yoga = [a for a in family["assets"] if a["display_name"] in {f"YogaPants_{c}" for c in "ABCDEF"}]
            if len(yoga) != 6 or any(a["slot"] != "pants" for a in yoga):
                raise ValueError("Expected exactly YogaPants A-F")
            ids = {a["asset_id"] for a in yoga}
            groups = family["assembly"]["groups"]
            if {g["group_id"] for g in groups if set(g["slot_pools"].get("pants", [])) == ids} != EXCLUDED_GROUPS:
                raise ValueError("Unexpected streetwear group coverage")
            family["assets"] = [a for a in family["assets"] if a["asset_id"] not in ids]
            family["assembly"]["groups"] = [g for g in groups if g["group_id"] not in EXCLUDED_GROUPS]
        elif family["family_id"] == "male.cyberpunk_locked":
            mask = next(a for a in family["assets"] if a["asset_id"] == MASK_ID)
            if len(mask["ue_mesh_paths"]) != 1 or not mask["ue_mesh_paths"][0].endswith("/cybmask.cybmask"):
                raise ValueError("Cyberpunk mask identity changed")
            family["assets"] = [a for a in family["assets"] if a["asset_id"] != MASK_ID]
            required = family["assembly"]["bundle"]["required_assets"]
            family["assembly"]["bundle"]["required_assets"] = [a for a in required if a != MASK_ID]
    # Proposal was restrictive but conflated original permission with selection
    # for three original-both hairstyles. Normalize only that known field.
    normalized = copy.deepcopy(candidate)
    normalized.pop("review_proposal", None)
    original_by_id = {h["hair_id"]: h for h in source["hair_assets"]}
    for hair in normalized["hair_assets"]:
        hair["sex"] = original_by_id[hair["hair_id"]]["sex"]
    if normalized != expected:
        raise ValueError("Candidate differs from the explicitly approved selection delta")
    by_id = {h["hair_id"]: i for i, h in indexed.items()}
    for hair in expected["hair_assets"]:
        hair["reviewed_sexes"] = [sex for sex in ("male", "female") if by_id[hair["hair_id"]] in INDICES[sex]]
    expected["reviewed_pool"] = {
        "publication_id": formal.REVIEWED_POOL_ID, "scope": SCOPE,
        "source_registry_sha256": SOURCE_SHA,
        "permission_rule": "original sex intersect reviewed_sexes; both geometry fits do not grant use",
        "hair_review_indices_by_sex": INDICES,
        "hair_shape_groups": "pending_visible_silhouette_review; content_pack_is_not_shape_group",
        "high_heels": "retained; new_body_fit_and_pose_pending",
        "new_body_visual_acceptance": False,
    }
    if formal.validate_registry(expected) != COUNTS:
        raise ValueError("Unexpected publication counts")
    return expected


def verify_selections(source: dict, registry: dict, plan: dict) -> tuple[dict, dict]:
    """Exercise historical survivors, every reviewed permission and group deny."""
    mapping, sex_indices, retained = [], {"male": 0, "female": 0}, {"male": 0, "female": 0}
    for row in plan["review_selection"]["outfits"]:
        sex = row["family_id"].split(".")[0]
        sex_indices[sex] += 1
        excluded = (row["family_id"] in EXCLUDED_FAMILIES or
                    (row["family_id"] == "female.streetwear_collection" and row["group_id"] in EXCLUDED_GROUPS))
        item = {"historical_review_index": row["review_index"], "historical_sex_index": sex_indices[sex],
                "character_sex": sex, "family_id": row["family_id"], "group_id": row["group_id"],
                "historical_qualified_variant_id": row["qualified_variant_id"],
                "status": "excluded" if excluded else "retained"}
        if excluded:
            item["reason"] = "excluded_family" if row["family_id"] in EXCLUDED_FAMILIES else "YogaPants_A_to_F"
        else:
            ids = [a for a in row["family_asset_ids"] if a != MASK_ID]
            request = {"character_sex": sex, "family_id": row["family_id"], "group_id": row["group_id"],
                       "family_asset_ids": ids, "shared_shoe_id": next(iter(row["shared_shoe_ids"]), None)}
            resolved = formal.resolve_selection(registry, **request)
            retained[sex] += 1
            item.update({"retained_witness_index": retained[sex], "request": request,
                         "resolved_variant_id": resolved["qualified_variant_id"], "assignments": resolved["assignments"]})
        mapping.append(item)
    if sum(sex_indices.values()) != 173 or sum(retained.values()) != 156:
        raise ValueError("Expected 173 historical witnesses, 156 retained, 17 excluded")
    hair_rows = []
    for index, hair in enumerate(sorted(source["hair_assets"], key=lambda h: h["hair_id"]), 1):
        selected = [sex for sex in ("male", "female") if index in INDICES[sex]]
        hair_rows.append({"historical_review_index": index, "hair_id": hair["hair_id"],
                          "original_sex_permission": hair["sex"], "reviewed_sexes": selected,
                          "status": "retained" if selected else "excluded"})
        for sex in ("male", "female"):
            request = next(r["request"] for r in mapping if r["character_sex"] == sex and r["status"] == "retained")
            try:
                resolved = formal.resolve_selection(registry, **request, hair_id=hair["hair_id"])
                if sex not in selected or resolved["resolved_hair_id"] != hair["hair_id"]:
                    raise AssertionError("Whitelist permission mismatch")
            except formal.RegistryError:
                if sex in selected:
                    raise
    group_checks = []
    for family in registry["families"]:
        groups = ([{"group_id": family["assembly"]["bundle"]["bundle_id"],
                    "required_assets": family["assembly"]["bundle"]["required_assets"], "slot_pools": {}, "required_slots": []}]
                  if family["assembly_mode"] == "locked_bundle" else family["assembly"]["groups"])
        for group in groups:
            ids = list(group.get("required_assets", [])) + [group["slot_pools"][slot][0] for slot in group["required_slots"]]
            result = formal.resolve_selection(registry, character_sex=family["sex"], family_id=family["family_id"],
                                              group_id=group["group_id"], family_asset_ids=ids, hair_id="HAIR_HB1_01")
            chosen = [a for a in family["assets"] if a["asset_id"] in result["selected_family_asset_ids"]]
            deny = family["hair_interface"]["deny_all"] or any(a.get("hair_interface", {}).get("deny_all", False) for a in chosen)
            if (result["hair_reason"] == "deny_all") != deny:
                raise ValueError("Hair deny policy was not enforced")
            group_checks.append({"family_id": family["family_id"], "group_id": group["group_id"], "deny_all": deny})
    old_cyber = formal.resolve_selection(source, character_sex="male", family_id="male.cyberpunk_locked", group_id="default")
    mask = next(a for a in old_cyber["assignments"] if a["source_component_name"] == MASK_ID)
    if mask["target_component"] != "BundlePart01":
        raise ValueError("Historical mask component differs")
    validation = {"counts": COUNTS, "hair_selection_counts": HAIR_COUNTS,
                  "historical_witnesses": 173, "retained_witnesses": 156, "excluded_witnesses": 17,
                  "retained_by_sex": retained, "hair_permission_cases": 80, "canonical_group_checks": group_checks,
                  "all_combinations_tested": False, "new_body_visual_acceptance": False, "scope": SCOPE}
    report = {"hair": hair_rows, "outfits": mapping, "cyberpunk_removed_mask": mask,
              "cyberpunk_remaining_locked_count": 4, "numbering": "historical identifiers retained; witness index is not a complete combination catalog"}
    return validation, report


def publish() -> dict:
    if digest(formal.MATERIAL_REPAIR_REGISTRY) != SOURCE_SHA or not formal._material_repair_is_published():
        raise ValueError("Source is not the hash-bound material repair publication")
    protected = [formal.LEGACY_REGISTRY, formal.DUAL_FIT_REGISTRY, formal.DUAL_FIT_PUBLICATION,
                 formal.MATERIAL_REPAIR_REGISTRY, formal.MATERIAL_REPAIR_PUBLICATION, CANDIDATE, FEEDBACK, REVIEW_PLAN]
    before = {str(path): digest(path) for path in protected}
    source, candidate, feedback = read(formal.MATERIAL_REPAIR_REGISTRY), read(CANDIDATE), read(FEEDBACK)
    for key, path in (("registry", formal.MATERIAL_REPAIR_REGISTRY), ("source_plan", REVIEW_PLAN)):
        if feedback["numbering_source"][key]["sha256"] != digest(path):
            raise ValueError(f"Feedback source changed: {key}")
    registry = build_registry(source, candidate, feedback)
    validation, mapping = verify_selections(source, registry, read(REVIEW_PLAN))
    write_new(formal.REVIEWED_POOL_REGISTRY, registry)
    output_sha = digest(formal.REVIEWED_POOL_REGISTRY)
    common = {"success": True, "publication_id": formal.REVIEWED_POOL_ID, "output_registry_sha256": output_sha}
    validation_path, mapping_path = OUTPUT_ROOT / "selection_validation_v1.json", OUTPUT_ROOT / "selection_mapping_v1.json"
    write_new(validation_path, {**common, **validation})
    write_new(mapping_path, {**common, **mapping})
    after = {str(path): digest(path) for path in protected}
    if before != after:
        raise ValueError("Protected source changed during publication; receipt not published")
    protection_path = OUTPUT_ROOT / "protected_sources_v1.json"
    write_new(protection_path, {**common, "scope": "exactly the eight listed local JSON files; no UE asset audit claimed",
                               "records": [{"path": p, "before_sha256": sha, "after_sha256": after[p], "unchanged": True}
                                           for p, sha in before.items()]})
    manifest = {**common, "scope": SCOPE, "counts": COUNTS, "hair_selection_counts": HAIR_COUNTS,
                "status": "published_selection_rules_visual_fit_pending", "new_body_visual_acceptance": False,
                "candidate_registry": str(CANDIDATE), "candidate_registry_sha256": digest(CANDIDATE),
                "feedback": str(FEEDBACK), "feedback_sha256": digest(FEEDBACK)}
    for key, path in (("source_registry", formal.MATERIAL_REPAIR_REGISTRY), ("source_publication", formal.MATERIAL_REPAIR_PUBLICATION),
                      ("output_registry", formal.REVIEWED_POOL_REGISTRY), ("selection_validation", validation_path),
                      ("mapping_report", mapping_path), ("protected_sources_report", protection_path)):
        manifest[key], manifest[key + "_sha256"] = str(path), digest(path)
    manifest["published_at"] = (read(formal.REVIEWED_POOL_PUBLICATION)["published_at"] if formal.REVIEWED_POOL_PUBLICATION.exists()
                                else datetime.now(timezone.utc).isoformat())
    write_new(formal.REVIEWED_POOL_PUBLICATION, manifest)  # The default route unlocks only after all bound evidence exists.
    if formal.reviewed_pool_v1_registry_path() != formal.REVIEWED_POOL_REGISTRY:
        raise ValueError("Published default did not resolve")
    return manifest


if __name__ == "__main__":
    result = publish()
    print(json.dumps({"success": True, "registry": result["output_registry"], "sha256": result["output_registry_sha256"],
                      "manifest": str(formal.REVIEWED_POOL_PUBLICATION)}, ensure_ascii=False, indent=2))
