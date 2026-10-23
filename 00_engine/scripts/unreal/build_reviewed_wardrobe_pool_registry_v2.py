"""Publish the bounded post-slot review exclusion without modifying UE assets."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path

import formal_wardrobe_registry_v1 as formal
from build_reviewed_wardrobe_pool_registry_v1 import digest, read, write_new, HAIR_COUNTS, SCOPE

OUTPUT_ROOT = formal.REVIEWED_POOL_V2_PUBLICATION.parent
PARENT_SHA = "c7b10609fb5d2de83917e17b3cde5c8258fe8e1aa94043287dc6efaa8dd89bea"
COUNTS = formal.REVIEWED_POOL_V2_COUNTS


def revise_mapping(parent_mapping: dict, registry: dict) -> tuple[dict, dict]:
    """Keep historical numbers and all surviving choices exactly intact."""
    mapping = copy.deepcopy(parent_mapping)
    for key in ("success", "publication_id", "output_registry_sha256"):
        mapping.pop(key, None)
    counts = {"female": 0, "male": 0}
    removed = []
    for row in mapping["outfits"]:
        sex = row["character_sex"]
        if row["family_id"] == "male.lift_haul":
            if row["status"] != "retained":
                raise ValueError("Lift & Haul witness was not previously retained")
            row.update({"status": "excluded", "reason": "post_slot_user_review_excluded_male_lift_haul"})
            removed.append(row["historical_sex_index"])
            for key in ("retained_witness_index", "request", "resolved_variant_id", "assignments"):
                row.pop(key, None)
        elif row["status"] == "retained":
            resolved = formal.resolve_selection(registry, **row["request"])
            if resolved["assignments"] != row["assignments"] or resolved["qualified_variant_id"] != row["resolved_variant_id"]:
                raise ValueError("Surviving witness changed during revision")
            counts[sex] += 1
            row["retained_witness_index"] = counts[sex]
    if removed != [33, 34, 35, 36] or counts != {"female": 79, "male": 73} or len(mapping["outfits"]) != 173:
        raise ValueError("Unexpected revised historical witness coverage")
    # A rejected removed family must remain unreachable even with its old choices.
    rejected = 0
    for row in parent_mapping["outfits"]:
        if row["family_id"] != "male.lift_haul":
            continue
        try:
            formal.resolve_selection(registry, **row["request"])
        except formal.RegistryError:
            rejected += 1
        else:
            raise ValueError("Excluded male Lift & Haul remains selectable")
    validation = {"counts": COUNTS, "hair_selection_counts": HAIR_COUNTS,
                  "historical_witnesses": 173, "retained_witnesses": 152, "excluded_witnesses": 21,
                  "retained_by_sex": counts, "removed_historical_male_indices": removed,
                  "removed_family_rejection_cases": rejected,
                  "all_other_families_assets_hair_and_shared_shoes_preserved": True,
                  "all_combinations_tested": False, "new_body_visual_acceptance": False, "scope": SCOPE}
    return mapping, validation


def publish() -> dict:
    parent_path = formal.reviewed_pool_v1_registry_path()
    if digest(parent_path) != PARENT_SHA:
        raise ValueError("Reviewed v1 source bytes differ from the approved parent")
    parent_receipt = read(formal.REVIEWED_POOL_PUBLICATION)
    protected = [parent_path, formal.REVIEWED_POOL_PUBLICATION,
                 formal.MATERIAL_REPAIR_REGISTRY, formal.MATERIAL_REPAIR_PUBLICATION]
    protected += [Path(parent_receipt[k]) for k in ("mapping_report", "selection_validation", "protected_sources_report", "feedback")]
    before = {str(p): digest(p) for p in protected}
    source = read(parent_path)
    registry = formal.reviewed_pool_v2_expected(source, PARENT_SHA)
    mapping, validation = revise_mapping(read(Path(parent_receipt["mapping_report"])), registry)
    write_new(formal.REVIEWED_POOL_V2_REGISTRY, registry)
    output_sha = digest(formal.REVIEWED_POOL_V2_REGISTRY)
    common = {"success": True, "publication_id": formal.REVIEWED_POOL_V2_ID, "output_registry_sha256": output_sha}
    feedback_path = OUTPUT_ROOT / "human_review_feedback_v2.json"
    feedback = {**common,
                "source": "direct_user_feedback_after_reviewing_new_slot_system",
                "user_statement": "除了要再把男性的lift&haul服装去除，其他所有的服装发型动作都基本正确合理；高跟鞋处理方式待讨论。",
                "excluded_family_ids": ["male.lift_haul"],
                "high_heels": "retained_pending_pose_and_fit_decision",
                "human_acceptance": "user_reports_reviewed_clothing_hair_and_actions_basically_reasonable_except_exclusions_and_shoes",
                "acceptance_scope": "only_user_observed_review_scene_choices; no_exhaustive_combinations_or_all_motion_frames_claimed",
                "shoe_pose_or_body_occlusion_fix_accepted": False,
                "female_shared_lift_and_haul_shoes_preserved": True}
    write_new(feedback_path, feedback)
    mapping_path = OUTPUT_ROOT / "selection_mapping_v2.json"
    validation_path = OUTPUT_ROOT / "selection_validation_v2.json"
    protection_path = OUTPUT_ROOT / "protected_sources_v2.json"
    write_new(mapping_path, {**mapping, **common})
    write_new(validation_path, {**validation, **common})
    after = {str(p): digest(p) for p in protected}
    if before != after:
        raise ValueError("Protected sources changed; current receipt not published")
    write_new(protection_path, {**common, "scope": "listed JSON sources only; no UE asset mutation or full UE audit",
                               "records": [{"path": p, "before_sha256": sha, "after_sha256": after[p], "unchanged": True}
                                           for p, sha in before.items()]})
    manifest = {**common, "scope": SCOPE, "counts": COUNTS, "hair_selection_counts": HAIR_COUNTS,
                "removed_family_ids": ["male.lift_haul"], "status": "published_post_slot_bounded_user_review_revision",
                "new_body_visual_acceptance": False,
                "published_at": (read(formal.REVIEWED_POOL_V2_PUBLICATION)["published_at"]
                                 if formal.REVIEWED_POOL_V2_PUBLICATION.exists() else datetime.now(timezone.utc).isoformat())}
    for key, path in (("source_registry", parent_path), ("source_publication", formal.REVIEWED_POOL_PUBLICATION),
                      ("output_registry", formal.REVIEWED_POOL_V2_REGISTRY), ("mapping_report", mapping_path),
                      ("selection_validation", validation_path), ("protected_sources_report", protection_path), ("feedback", feedback_path)):
        manifest[key], manifest[key + "_sha256"] = str(path), digest(path)
    write_new(formal.REVIEWED_POOL_V2_PUBLICATION, manifest)
    if formal.reviewed_pool_v2_registry_path() != formal.REVIEWED_POOL_V2_REGISTRY:
        raise ValueError("Current revision default did not resolve")
    return manifest


if __name__ == "__main__":
    result = publish()
    print(json.dumps({"success": True, "registry": result["output_registry"], "sha256": result["output_registry_sha256"],
                      "manifest": str(formal.REVIEWED_POOL_V2_PUBLICATION), "counts": COUNTS}, indent=2))
