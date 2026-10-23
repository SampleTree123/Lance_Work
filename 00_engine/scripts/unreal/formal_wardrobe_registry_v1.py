"""Validate and resolve outfits directly from the formal UE wardrobe registry.

This module has no Unreal dependency. It is the selection contract shared by
the command-line checks and the editor runtime; historical review plans are
only parity witnesses, never selection inputs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ENGINE = Path(__file__).resolve().parents[2]
LEGACY_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json"
DUAL_FIT_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json"
DUAL_FIT_PUBLICATION = ENGINE / "outputs/unreal_character_import/fixed_head_hair_20261004_v1/registry_publication_report.json"
MATERIAL_REPAIR_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_fixed_head_materials_20261005_v1.json"
MATERIAL_REPAIR_PUBLICATION = ENGINE / "outputs/unreal_character_import/fixed_head_material_repair_20261005_v1/registry_publication_report.json"
REVIEWED_POOL_ID = "reviewed_pool_20261006_v1"
REVIEWED_POOL_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261006_v1.json"
REVIEWED_POOL_PUBLICATION = ENGINE / "outputs/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1/tonight_20261006_v1/registry_publication/publication_manifest_v1.json"
REVIEWED_POOL_V2_ID = "reviewed_pool_20261006_v2"
REVIEWED_POOL_V2_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261006_v2.json"
REVIEWED_POOL_V2_PUBLICATION = REVIEWED_POOL_PUBLICATION.parent.parent / "post_slot_user_review_20261006_v1/publication_manifest_v2.json"
REVIEWED_POOL_V2_COUNTS = {"families": 38, "family_assets": 309, "shared_shoes": 43, "hair": 32}


def _material_repair_is_published() -> bool:
    """An independently saved repair cannot silently inherit old acceptance."""
    try:
        receipt = json.loads(MATERIAL_REPAIR_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (receipt.get("batch_id") != "fixed_head_material_repair_20261005_v1"
                or receipt.get("success") is not True
                or receipt.get("counts") != {"hairstyles": 40, "fits": 80, "hair_material_slots": 24}
                or Path(receipt["source_registry"]).resolve() != DUAL_FIT_REGISTRY.resolve()
                or receipt["source_registry_sha256"] != hashlib.sha256(DUAL_FIT_REGISTRY.read_bytes()).hexdigest()
                or Path(receipt["output_registry"]).resolve() != MATERIAL_REPAIR_REGISTRY.resolve()
                or receipt["output_registry_sha256"] != hashlib.sha256(MATERIAL_REPAIR_REGISTRY.read_bytes()).hexdigest()
                or receipt.get("families_meshes_and_usage_permissions_preserved") is not True):
            return False
        for key in ("hair_apply_report", "skin_apply_report"):
            report_path = Path(receipt[key])
            if receipt[key + "_sha256"] != hashlib.sha256(report_path.read_bytes()).hexdigest():
                return False
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            if report.get("success") is not True or report.get("mode") != "apply":
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def historical_registry_path() -> Path:
    """Resolve the historical unfiltered publication chain explicitly.

    Retained for reproduction of old evidence; never a current-pool fallback.
    """
    try:
        publication = json.loads(DUAL_FIT_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (publication.get("batch_id") != "fixed_head_hair_20261004_v1"
                or publication.get("success") is not True
                or publication.get("counts") != {"hairstyles": 40, "fits": 80}
                or Path(publication["output_registry"]).resolve() != DUAL_FIT_REGISTRY.resolve()
                or hashlib.sha256(DUAL_FIT_REGISTRY.read_bytes()).hexdigest() != publication["output_registry_sha256"]):
            return LEGACY_REGISTRY
        import_path = Path(publication["import_report"])
        if hashlib.sha256(import_path.read_bytes()).hexdigest() != publication["import_report_sha256"]:
            return LEGACY_REGISTRY
        report = json.loads(import_path.read_text(encoding="utf-8-sig"))
        records = report.get("records", [])
        pairs = {(row.get("hair_id"), row.get("sex")) for row in records}
        if (report.get("success") is not True or report.get("complete") is not True
                or len(records) != 80 or len(pairs) != 80
                or any(row.get("success") is not True for row in records)):
            return LEGACY_REGISTRY
        return MATERIAL_REPAIR_REGISTRY if _material_repair_is_published() else DUAL_FIT_REGISTRY
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return LEGACY_REGISTRY


def reviewed_pool_v1_registry_path() -> Path:
    """Require the reviewed pool's bound publication, with no old-pool fallback.

    A missing/corrupt receipt or changed source/output is an actionable error,
    including if both reviewed files disappear. Explicit historical reads are
    still supported through read_registry(path) and historical_registry_path().
    """
    try:
        receipt = json.loads(REVIEWED_POOL_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (receipt.get("publication_id") != REVIEWED_POOL_ID
                or receipt.get("success") is not True
                or receipt.get("counts") != {"families": 39, "family_assets": 320, "shared_shoes": 43, "hair": 32}
                or receipt.get("hair_selection_counts") != {"male": 15, "female": 23, "union": 32, "overlap": 6}
                or receipt.get("scope") != "reviewed_selection_rules_not_new_body_visual_acceptance"):
            raise ValueError("wrong reviewed-pool publication contract")
        for key, expected in (("source_registry", MATERIAL_REPAIR_REGISTRY),
                              ("source_publication", MATERIAL_REPAIR_PUBLICATION),
                              ("output_registry", REVIEWED_POOL_REGISTRY)):
            path = Path(receipt[key])
            if (path.resolve() != expected.resolve()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]):
                raise ValueError(f"changed or wrong {key}")
        source_receipt = json.loads(MATERIAL_REPAIR_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (source_receipt.get("success") is not True
                or source_receipt.get("batch_id") != "fixed_head_material_repair_20261005_v1"
                or Path(source_receipt["output_registry"]).resolve() != MATERIAL_REPAIR_REGISTRY.resolve()
                or source_receipt["output_registry_sha256"] != receipt["source_registry_sha256"]):
            raise ValueError("invalid source material publication")
        for key in ("selection_validation", "mapping_report", "protected_sources_report"):
            path = Path(receipt[key])
            if (path.parent.resolve() != REVIEWED_POOL_PUBLICATION.parent.resolve()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]):
                raise ValueError(f"changed or misplaced {key}")
            evidence = json.loads(path.read_text(encoding="utf-8-sig"))
            if (evidence.get("success") is not True
                    or evidence.get("output_registry_sha256") != receipt["output_registry_sha256"]):
                raise ValueError(f"unsuccessful or stale {key}")
        return REVIEWED_POOL_REGISTRY
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RegistryError(f"Reviewed pool publication unavailable or invalid; refusing unfiltered fallback: {exc}") from exc


# A provenance path, not an unvalidated alternate route. Default reads above
# validate at call time; importing this module does not require local outputs.
def reviewed_pool_v2_expected(source: dict, source_sha256: str) -> dict:
    """The only approved revision is removal of the male Lift & Haul family."""
    import copy
    result = copy.deepcopy(source)
    removed = [f for f in result["families"] if f["family_id"] == "male.lift_haul"]
    if len(removed) != 1 or removed[0]["sex"] != "male" or len(removed[0]["assets"]) != 11:
        raise RegistryError("Expected exactly the male Lift & Haul family with 11 assets")
    result["families"] = [f for f in result["families"] if f["family_id"] != "male.lift_haul"]
    result["reviewed_pool"].update({"publication_id": REVIEWED_POOL_V2_ID,
                                   "parent_registry_sha256": source_sha256,
                                   "revision_excluded_families": ["male.lift_haul"]})
    if validate_registry(result) != REVIEWED_POOL_V2_COUNTS:
        raise RegistryError("Unexpected current reviewed-pool counts")
    return result


def reviewed_pool_v2_publication_path() -> Path:
    """Return the current receipt only after validating the entire chain."""
    reviewed_pool_v2_registry_path()
    return REVIEWED_POOL_V2_PUBLICATION


def reviewed_pool_v2_registry_path() -> Path:
    """Require the latest review revision; never fall back to an older pool."""
    try:
        parent = reviewed_pool_v1_registry_path()
        receipt = json.loads(REVIEWED_POOL_V2_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (receipt.get("publication_id") != REVIEWED_POOL_V2_ID
                or receipt.get("success") is not True
                or receipt.get("counts") != REVIEWED_POOL_V2_COUNTS
                or receipt.get("hair_selection_counts") != {"male": 15, "female": 23, "union": 32, "overlap": 6}
                or receipt.get("scope") != "reviewed_selection_rules_not_new_body_visual_acceptance"
                or receipt.get("removed_family_ids") != ["male.lift_haul"]):
            raise ValueError("wrong current reviewed-pool revision contract")
        for key, expected in (("source_registry", parent), ("source_publication", REVIEWED_POOL_PUBLICATION),
                              ("output_registry", REVIEWED_POOL_V2_REGISTRY)):
            path = Path(receipt[key])
            if path.resolve() != expected.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or wrong {key}")
        source = json.loads(parent.read_text(encoding="utf-8-sig"))
        result = json.loads(REVIEWED_POOL_V2_REGISTRY.read_text(encoding="utf-8-sig"))
        if result != reviewed_pool_v2_expected(source, receipt["source_registry_sha256"]):
            raise ValueError("current registry differs from the approved revision delta")
        evidence = {}
        for key in ("selection_validation", "mapping_report", "protected_sources_report", "feedback"):
            path = Path(receipt[key])
            if path.parent.resolve() != REVIEWED_POOL_V2_PUBLICATION.parent.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or misplaced {key}")
            evidence[key] = json.loads(path.read_text(encoding="utf-8-sig"))
            if evidence[key].get("success") is not True or evidence[key].get("output_registry_sha256") != receipt["output_registry_sha256"]:
                raise ValueError(f"unsuccessful or stale {key}")
        feedback = evidence["feedback"]
        if feedback.get("excluded_family_ids") != ["male.lift_haul"] or feedback.get("high_heels") != "retained_pending_pose_and_fit_decision":
            raise ValueError("revision feedback does not match the approved exclusion")
        validation = evidence["selection_validation"]
        if validation.get("retained_by_sex") != {"female": 79, "male": 73} or validation.get("retained_witnesses") != 152:
            raise ValueError("wrong revised witness coverage")
        return REVIEWED_POOL_V2_REGISTRY
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RegistryError(f"Current reviewed pool unavailable or invalid; refusing unfiltered fallback: {exc}") from exc


REVIEWED_POOL_V3_ID = "reviewed_pool_20261007_v3"
REVIEWED_POOL_V3_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261007_v3.json"
REVIEWED_POOL_V3_PUBLICATION = ENGINE / "outputs/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/shoe_publication/publication_manifest_v3.json"
REVIEWED_POOL_V3_COUNTS = {"families": 38, "family_assets": 299, "shared_shoes": 31, "hair": 32}
FEMALE_SHARED_SHOE_IDS = [f"F{i:03d}" for i in [1, 2, 3, 4, 5, 22, 23, 24, 25]]
FEMALE_EXCLUDED_SHOE_IDS = [f"F{i:03d}" for i in range(6, 22)]


def reviewed_pool_v3_expected(source: dict, source_sha256: str) -> dict:
    """Remove female native shoes and use the one user-approved shared pool."""
    import copy
    result = copy.deepcopy(source)
    result["shared_shoe_assets"] = [a for a in result["shared_shoe_assets"]
                                     if not (a["sex"] == "female" and a["asset_id"] in FEMALE_EXCLUDED_SHOE_IDS)]
    if [a["asset_id"] for a in result["shared_shoe_assets"] if a["sex"] == "female"] != FEMALE_SHARED_SHOE_IDS:
        raise RegistryError("Unexpected female shared footwear source")
    for family in result["families"]:
        if family["sex"] != "female":
            continue
        removed = {a["asset_id"] for a in family["assets"] if a["slot"] == "shoes"}
        family["assets"] = [a for a in family["assets"] if a["asset_id"] not in removed]
        if family["assembly_mode"] == "locked_bundle":
            bundle = family["assembly"]["bundle"]
            bundle["required_assets"] = [a for a in bundle["required_assets"] if a not in removed]
        else:
            for group in family["assembly"]["groups"]:
                group["slot_pools"].pop("shoes", None)
                for key in ("required_slots", "optional_slots"):
                    group[key] = [s for s in group[key] if s != "shoes"]
                for key in ("required_assets", "optional_assets"):
                    if key in group:
                        group[key] = [a for a in group[key] if a not in removed]
        family["shared_footwear_policy"] = {"mode": "required_universal_female_pool", "default_asset_id": "F001"}
    result["reviewed_pool"].update({"publication_id": REVIEWED_POOL_V3_ID,
        "parent_registry_sha256": source_sha256, "high_heels": "female_shared_F006_F021_and_all_female_native_shoes_excluded_male_unchanged",
        "female_shared_shoe_ids": FEMALE_SHARED_SHOE_IDS,
        "female_excluded_shared_shoe_ids": FEMALE_EXCLUDED_SHOE_IDS})
    if validate_registry(result) != REVIEWED_POOL_V3_COUNTS:
        raise RegistryError("Unexpected v3 reviewed-pool counts")
    return result


def reviewed_pool_v3_publication_path() -> Path:
    reviewed_pool_v3_registry_path()
    return REVIEWED_POOL_V3_PUBLICATION


def reviewed_pool_v3_registry_path() -> Path:
    """Fail closed on v3 and verify its exact bounded delta from preserved v2."""
    try:
        parent = reviewed_pool_v2_registry_path()
        receipt = json.loads(REVIEWED_POOL_V3_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (receipt.get("publication_id") != REVIEWED_POOL_V3_ID or receipt.get("success") is not True
                or receipt.get("counts") != REVIEWED_POOL_V3_COUNTS
                or receipt.get("female_shared_shoe_ids") != FEMALE_SHARED_SHOE_IDS
                or receipt.get("male_preserved") is not True):
            raise ValueError("wrong current reviewed-pool revision contract")
        for key, expected in (("source_registry", parent), ("source_publication", REVIEWED_POOL_V2_PUBLICATION),
                              ("output_registry", REVIEWED_POOL_V3_REGISTRY)):
            path = Path(receipt[key])
            if path.resolve() != expected.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or wrong {key}")
        source = json.loads(parent.read_text(encoding="utf-8-sig"))
        result = json.loads(REVIEWED_POOL_V3_REGISTRY.read_text(encoding="utf-8-sig"))
        if result != reviewed_pool_v3_expected(source, receipt["source_registry_sha256"]):
            raise ValueError("current registry differs from the approved revision delta")
        for key in ("selection_validation", "mapping_report", "protected_sources_report", "feedback"):
            path = Path(receipt[key])
            if path.parent.resolve() != REVIEWED_POOL_V3_PUBLICATION.parent.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or misplaced {key}")
            evidence = json.loads(path.read_text(encoding="utf-8-sig"))
            if evidence.get("success") is not True or evidence.get("output_registry_sha256") != receipt["output_registry_sha256"]:
                raise ValueError(f"unsuccessful or stale {key}")
        return REVIEWED_POOL_V3_REGISTRY
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RegistryError(f"Current reviewed pool unavailable or invalid; refusing unfiltered fallback: {exc}") from exc


REVIEWED_POOL_V4_ID = "reviewed_pool_20261007_v4"
REVIEWED_POOL_V4_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261007_v4.json"
REVIEWED_POOL_V4_PUBLICATION = REVIEWED_POOL_V3_PUBLICATION.parent / "publication_manifest_v4.json"
REVIEWED_POOL_V4_COUNTS = REVIEWED_POOL_V3_COUNTS.copy()


def female_shoe_optional(family: dict, group_id: str) -> bool:
    policy = family.get("shared_footwear_policy", {})
    return policy.get("mode") == "universal_female_pool_by_group" and group_id in policy["barefoot_allowed_groups"]


def reviewed_pool_v4_expected(source: dict, source_sha256: str, original: dict) -> dict:
    """Restore original v2 barefoot permission, leaving the nine-shoe pool intact."""
    import copy
    result = copy.deepcopy(source)
    original_families = {f["family_id"]: f for f in original["families"]}
    for family in result["families"]:
        if family["sex"] != "female":
            continue
        old = original_families[family["family_id"]]
        assets = {a["asset_id"]: a for a in old["assets"]}
        if old["assembly_mode"] == "locked_bundle":
            bundle = old["assembly"]["bundle"]
            groups = [{"group_id": bundle["bundle_id"], "required_assets": bundle["required_assets"]}]
        else:
            groups = old["assembly"]["groups"]
        allowed = [g["group_id"] for g in groups if "shoes" not in g.get("required_slots", [])
                   and not any(assets[a]["slot"] == "shoes" for a in g.get("required_assets", []))]
        family["shared_footwear_policy"] = {"mode": "universal_female_pool_by_group",
            "default_asset_id": "F001", "barefoot_allowed_groups": allowed,
            "barefoot_permission_source": "reviewed_pool_20261006_v2_required_shoe_rules"}
    result["reviewed_pool"].update({"publication_id": REVIEWED_POOL_V4_ID,
        "parent_registry_sha256": source_sha256, "barefoot_policy": "preserve_v2_optional_shoe_groups"})
    return result


def reviewed_pool_v4_publication_path() -> Path:
    reviewed_pool_v4_registry_path()
    return REVIEWED_POOL_V4_PUBLICATION


def reviewed_pool_v4_registry_path() -> Path:
    try:
        parent = reviewed_pool_v3_registry_path()
        receipt = json.loads(REVIEWED_POOL_V4_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (receipt.get("publication_id") != REVIEWED_POOL_V4_ID or receipt.get("success") is not True
                or receipt.get("counts") != REVIEWED_POOL_V4_COUNTS
                or receipt.get("female_shared_shoe_ids") != FEMALE_SHARED_SHOE_IDS
                or receipt.get("barefoot_policy") != "preserve_v2_optional_shoe_groups"
                or receipt.get("male_preserved") is not True):
            raise ValueError("wrong current reviewed-pool revision contract")
        for key, expected in (("source_registry", parent), ("source_publication", REVIEWED_POOL_V3_PUBLICATION),
                              ("barefoot_source_registry", REVIEWED_POOL_V2_REGISTRY),
                              ("output_registry", REVIEWED_POOL_V4_REGISTRY)):
            path = Path(receipt[key])
            if path.resolve() != expected.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or wrong {key}")
        source = json.loads(parent.read_text(encoding="utf-8-sig"))
        original = json.loads(REVIEWED_POOL_V2_REGISTRY.read_text(encoding="utf-8-sig"))
        result = json.loads(REVIEWED_POOL_V4_REGISTRY.read_text(encoding="utf-8-sig"))
        if result != reviewed_pool_v4_expected(source, receipt["source_registry_sha256"], original):
            raise ValueError("current registry differs from the approved revision delta")
        for key in ("selection_validation", "mapping_report", "protected_sources_report", "feedback"):
            path = Path(receipt[key])
            if path.parent.resolve() != REVIEWED_POOL_V4_PUBLICATION.parent.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or misplaced {key}")
            evidence = json.loads(path.read_text(encoding="utf-8-sig"))
            if evidence.get("success") is not True or evidence.get("output_registry_sha256") != receipt["output_registry_sha256"]:
                raise ValueError(f"unsuccessful or stale {key}")
        return REVIEWED_POOL_V4_REGISTRY
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RegistryError(f"Current reviewed pool unavailable or invalid; refusing unfiltered fallback: {exc}") from exc


CURRENT_REVIEWED_POOL_ID = "reviewed_pool_20261007_v5"
CURRENT_REVIEWED_POOL_REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261007_v5.json"
CURRENT_REVIEWED_POOL_PUBLICATION = ENGINE / "outputs/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/hair_palette_v2_20261007/publication/publication_manifest_v5.json"
CURRENT_REVIEWED_POOL_COUNTS = {**REVIEWED_POOL_V4_COUNTS, "hair": 28}
CURRENT_HAIR_EXCLUSIONS = {"male": {36: "HAIR_HB3_15", 40: "HAIR_HB3_20"},
                           "female": {6: "HAIR_HB1_13", 10: "HAIR_HB1_18", 15: "HAIR_HB2_05"}}


def hair_review_indices_by_sex(registry: dict) -> dict:
    """Return the formal sex-specific original panel numbers, with no renumbering."""
    return {sex: list(registry["reviewed_pool"]["hair_review_indices_by_sex"][sex]) for sex in ("male", "female")}


def hair_selection_counts(registry: dict) -> dict:
    indices = hair_review_indices_by_sex(registry)
    male, female = set(indices["male"]), set(indices["female"])
    return {"male": len(male), "female": len(female), "union": len(male | female), "overlap": len(male & female)}


def reviewed_pool_v5_expected(source: dict, source_sha256: str) -> dict:
    """Apply only the five sex-specific removals and cancel shape grouping."""
    import copy
    result = copy.deepcopy(source)
    for sex, exclusions in CURRENT_HAIR_EXCLUSIONS.items():
        for index, hair_id in exclusions.items():
            if index not in source["reviewed_pool"]["hair_review_indices_by_sex"][sex]:
                raise RegistryError("Expected retained original hair index for exclusion")
            hair = next(h for h in result["hair_assets"] if h["hair_id"] == hair_id)
            if sex not in hair["reviewed_sexes"]:
                raise RegistryError("Expected retained sex permission for exclusion")
            hair["reviewed_sexes"].remove(sex)
        result["reviewed_pool"]["hair_review_indices_by_sex"][sex] = [i for i in source["reviewed_pool"]["hair_review_indices_by_sex"][sex] if i not in exclusions]
    result["hair_assets"] = [h for h in result["hair_assets"] if h["reviewed_sexes"]]
    result["reviewed_pool"].update({"publication_id": CURRENT_REVIEWED_POOL_ID,
        "parent_registry_sha256": source_sha256,
        "hair_shape_groups": "cancelled_by_user; random_choice_within_approved_sex_pool",
        "hair_selection_mode": "random_within_approved_sex_pool",
        "revision_hair_excluded_indices_by_sex": {s: list(rows) for s, rows in CURRENT_HAIR_EXCLUSIONS.items()}})
    if validate_registry(result) != CURRENT_REVIEWED_POOL_COUNTS or hair_selection_counts(result) != {"male": 13, "female": 20, "union": 28, "overlap": 5}:
        raise RegistryError("Unexpected v5 hair pool counts")
    return result


def current_registry_publication_path() -> Path:
    current_registry_path()
    return CURRENT_REVIEWED_POOL_PUBLICATION


def current_registry_path() -> Path:
    try:
        parent = reviewed_pool_v4_registry_path()
        receipt = json.loads(CURRENT_REVIEWED_POOL_PUBLICATION.read_text(encoding="utf-8-sig"))
        if (receipt.get("publication_id") != CURRENT_REVIEWED_POOL_ID or receipt.get("success") is not True
                or receipt.get("counts") != CURRENT_REVIEWED_POOL_COUNTS
                or receipt.get("hair_selection_counts") != {"male": 13, "female": 20, "union": 28, "overlap": 5}
                or receipt.get("clothing_and_shoes_preserved") is not True):
            raise ValueError("wrong current reviewed-pool revision contract")
        for key, expected in (("source_registry", parent), ("source_publication", REVIEWED_POOL_V4_PUBLICATION),
                              ("output_registry", CURRENT_REVIEWED_POOL_REGISTRY)):
            path = Path(receipt[key])
            if path.resolve() != expected.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or wrong {key}")
        source = json.loads(parent.read_text(encoding="utf-8-sig"))
        result = json.loads(CURRENT_REVIEWED_POOL_REGISTRY.read_text(encoding="utf-8-sig"))
        if result != reviewed_pool_v5_expected(source, receipt["source_registry_sha256"]):
            raise ValueError("current registry differs from the approved revision delta")
        for key in ("selection_validation", "mapping_report", "protected_sources_report", "feedback"):
            path = Path(receipt[key])
            if path.parent.resolve() != CURRENT_REVIEWED_POOL_PUBLICATION.parent.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != receipt[key + "_sha256"]:
                raise ValueError(f"changed or misplaced {key}")
            evidence = json.loads(path.read_text(encoding="utf-8-sig"))
            if evidence.get("success") is not True or evidence.get("output_registry_sha256") != receipt["output_registry_sha256"]:
                raise ValueError(f"unsuccessful or stale {key}")
        return CURRENT_REVIEWED_POOL_REGISTRY
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
        raise RegistryError(f"Current reviewed pool unavailable or invalid; refusing unfiltered fallback: {exc}") from exc


DEFAULT_REGISTRY = CURRENT_REVIEWED_POOL_REGISTRY
FIXED_SLOT = {
    "shirts": "UpperInner", "coats": "UpperOuter", "pants": "Bottom",
    "skirts": "Bottom", "full_body": "FullBody", "shoes": "Footwear",
}
VALID_SLOTS = set(FIXED_SLOT) | {"family_accessory"}
BUNDLE_CAPACITY = 10
VALID_SEX = {"male", "female", "both"}


class RegistryError(ValueError):
    pass


def read_registry(path: Path | None = None) -> dict[str, Any]:
    path = Path(path) if path is not None else current_registry_path()
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_registry(value)
    return value


def _unique(rows: list[dict], key: str, context: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise RegistryError(f"missing or duplicate {key} in {context}: {value!r}")
        result[value] = row
    return result


def _mesh_paths(row: dict, field: str, context: str) -> list[str]:
    paths = row.get(field)
    if not isinstance(paths, list) or not paths or any(not isinstance(path, str) for path in paths):
        raise RegistryError(f"invalid {field}: {context}")
    if not paths or len(paths) != len(set(paths)):
        raise RegistryError(f"invalid {field}: {context}")
    if any(not isinstance(path, str) or not path.startswith("/Game/") or "." not in path.rsplit("/", 1)[-1] for path in paths):
        raise RegistryError(f"invalid UE object path in {context}")
    return paths


def _hair_policy(row: dict, context: str) -> None:
    policy = row.get("hair_interface")
    if policy is None:
        return
    if not isinstance(policy, dict) or set(policy) != {"allow_all", "deny_all"}:
        raise RegistryError(f"invalid hair policy: {context}")
    if policy["allow_all"] is policy["deny_all"] or not all(isinstance(v, bool) for v in policy.values()):
        raise RegistryError(f"contradictory hair policy: {context}")


def hair_fit(hair: dict, character_sex: str) -> dict:
    """Choose geometry fit independently of a hairstyle's usage permission."""
    if character_sex not in {"male", "female"}:
        raise RegistryError(f"invalid character sex: {character_sex}")
    variants = hair.get("fit_variants")
    if variants is None:
        # Existing single-F02 imports keep their original consumer contract.
        return {"meshes": hair["meshes"], "skeleton_path": hair.get("skeleton_path")}
    if character_sex not in variants:
        raise RegistryError(f"hair has no {character_sex} fit: {hair['hair_id']}")
    return variants[character_sex]


def hair_mesh_capacity(hair: dict) -> int:
    variants = hair.get("fit_variants")
    return max(len(fit["meshes"]) for fit in variants.values()) if variants else len(hair["meshes"])


def hair_available_to(hair: dict, character_sex: str) -> bool:
    """Intersect original usage permission with the reviewed selection."""
    return (character_sex in {"male", "female"}
            and hair.get("sex") in {character_sex, "both"}
            and character_sex in hair.get("reviewed_sexes", ["male", "female"]))


def validate_registry(registry: dict[str, Any]) -> dict[str, int]:
    if registry.get("schema_version") != 4:
        raise RegistryError("formal UE registry schema_version must be 4")
    families = registry.get("families")
    hairs = registry.get("hair_assets")
    shoes = registry.get("shared_shoe_assets")
    if not all(isinstance(rows, list) and rows for rows in (families, hairs, shoes)):
        raise RegistryError("formal UE registry requires families, hair and shared shoes")
    family_by_id = _unique(families, "family_id", "families")
    hair_by_id = _unique(hairs, "hair_id", "hair_assets")
    shoe_by_id = _unique(shoes, "asset_id", "shared_shoe_assets")
    for shoe_id, shoe in shoe_by_id.items():
        if shoe.get("sex") not in VALID_SEX:
            raise RegistryError(f"invalid shared shoe sex: {shoe_id}")
        _mesh_paths(shoe, "ue_asset_paths", shoe_id)
    for hair_id, hair in hair_by_id.items():
        if hair.get("sex") not in VALID_SEX:
            raise RegistryError(f"invalid hairstyle sex: {hair_id}")
        reviewed = hair.get("reviewed_sexes")
        if reviewed is not None or "reviewed_pool" in registry:
            permitted = {"male", "female"} if hair["sex"] == "both" else {hair["sex"]}
            if (not isinstance(reviewed, list) or not reviewed
                    or any(not isinstance(sex, str) for sex in reviewed)
                    or len(reviewed) != len(set(reviewed)) or not set(reviewed) <= permitted):
                raise RegistryError(f"invalid reviewed hairstyle selection: {hair_id}")
        variants = hair.get("fit_variants")
        if variants is not None:
            if not isinstance(variants, dict) or set(variants) != {"male", "female"}:
                raise RegistryError(f"hairstyle requires male and female fits: {hair_id}")
            fits = list(variants.items())
        else:
            fits = [("legacy", hair)]
        for fit_sex, fit in fits:
            if not isinstance(fit, dict):
                raise RegistryError(f"invalid hair fit: {hair_id}/{fit_sex}")
            meshes = fit.get("meshes")
            if not isinstance(meshes, list) or not meshes or any(not isinstance(m, dict) for m in meshes):
                raise RegistryError(f"hairstyle has no meshes: {hair_id}/{fit_sex}")
            _mesh_paths({"paths": [mesh.get("path") for mesh in meshes]}, "paths", hair_id)
            if variants is not None:
                _mesh_paths({"paths": [fit.get("skeleton_path")]}, "paths", f"{hair_id}/{fit_sex}/skeleton")
    asset_count = 0
    for family_id, family in family_by_id.items():
        sex = family.get("sex")
        if sex not in {"male", "female"}:
            raise RegistryError(f"invalid family sex: {family_id}")
        _hair_policy(family, family_id)
        assets = family.get("assets")
        if not isinstance(assets, list) or not assets:
            raise RegistryError(f"family has no assets: {family_id}")
        by_id = _unique(assets, "asset_id", family_id)
        asset_count += len(by_id)
        for asset_id, asset in by_id.items():
            if asset.get("slot") not in VALID_SLOTS:
                raise RegistryError(f"invalid asset slot: {asset_id}")
            root = asset.get("ue_case_root")
            if not isinstance(root, str) or not root.startswith("/Game/DataMake/CharacterFactory/Wardrobe/"):
                raise RegistryError(f"invalid case root: {asset_id}")
            if any(not path.startswith(root + "/Meshes/") for path in _mesh_paths(asset, "ue_mesh_paths", asset_id)):
                raise RegistryError(f"asset mesh escapes case root: {asset_id}")
            _hair_policy(asset, asset_id)
        assembly = family.get("assembly") or {}
        if family.get("assembly_mode") == "locked_bundle":
            bundle = assembly.get("bundle") or {}
            required = bundle.get("required_assets")
            if not isinstance(required, list) or set(required) != set(by_id) or len(required) != len(by_id):
                raise RegistryError(f"locked bundle does not cover family: {family_id}")
            if len({asset["ue_case_root"] for asset in assets}) != 1:
                raise RegistryError(f"locked bundle spans multiple UE cases: {family_id}")
        elif family.get("assembly_mode") == "slot_groups":
            groups = assembly.get("groups")
            if not isinstance(groups, list) or not groups:
                raise RegistryError(f"slot family has no groups: {family_id}")
            _unique(groups, "group_id", family_id)
            for group in groups:
                group_id = group["group_id"]
                pools = group.get("slot_pools")
                if not isinstance(pools, dict) or not pools:
                    raise RegistryError(f"group has no slot pools: {family_id}/{group_id}")
                required_slots = group.get("required_slots") or []
                optional_slots = group.get("optional_slots") or []
                if set(required_slots) & set(optional_slots) or set(pools) != set(required_slots) | set(optional_slots):
                    raise RegistryError(f"slot declarations differ from pools: {family_id}/{group_id}")
                for slot, pool in pools.items():
                    if slot not in FIXED_SLOT or not isinstance(pool, list) or not pool or len(pool) != len(set(pool)):
                        raise RegistryError(f"invalid pool: {family_id}/{group_id}/{slot}")
                    if any(asset_id not in by_id or by_id[asset_id]["slot"] != slot for asset_id in pool):
                        raise RegistryError(f"wrong asset in pool: {family_id}/{group_id}/{slot}")
                required_assets = group.get("required_assets") or []
                optional_assets = group.get("optional_assets") or []
                if set(required_assets) & set(optional_assets) or len(required_assets) != len(set(required_assets)) or len(optional_assets) != len(set(optional_assets)):
                    raise RegistryError(f"invalid explicit assets: {family_id}/{group_id}")
                if any(asset_id not in by_id for asset_id in required_assets + optional_assets):
                    raise RegistryError(f"unknown explicit asset: {family_id}/{group_id}")
        else:
            raise RegistryError(f"unknown assembly mode: {family_id}")
    return {"families": len(families), "family_assets": asset_count,
            "shared_shoes": len(shoes), "hair": len(hairs)}


def _selected_assets(family: dict, group_id: str, selected: list[str]) -> list[dict]:
    family_id = family["family_id"]
    by_id = {asset["asset_id"]: asset for asset in family["assets"]}
    if len(selected) != len(set(selected)) or any(asset_id not in by_id for asset_id in selected):
        raise RegistryError(f"repeated or foreign asset in {family_id}")
    if family["assembly_mode"] == "locked_bundle":
        bundle = family["assembly"]["bundle"]
        if group_id != bundle["bundle_id"]:
            raise RegistryError(f"unknown locked bundle: {family_id}/{group_id}")
        required = bundle["required_assets"]
        if selected and set(selected) != set(required):
            raise RegistryError(f"locked bundle must be selected as a whole: {family_id}")
        return [by_id[asset_id] for asset_id in required]
    groups = {group["group_id"]: group for group in family["assembly"]["groups"]}
    if group_id not in groups:
        raise RegistryError(f"unknown outfit group: {family_id}/{group_id}")
    group = groups[group_id]
    chosen = set(selected)
    ordered = []
    for slot, pool in group["slot_pools"].items():
        matches = [asset_id for asset_id in pool if asset_id in chosen]
        if (slot in group["required_slots"] and len(matches) != 1) or len(matches) > 1:
            raise RegistryError(f"select exactly one required and at most one optional {slot}: {family_id}/{group_id}")
        ordered.extend(matches)
    required = group.get("required_assets") or []
    optional = group.get("optional_assets") or []
    if not set(required) <= chosen:
        raise RegistryError(f"required accessory missing: {family_id}/{group_id}")
    ordered.extend(required)
    ordered.extend(asset_id for asset_id in optional if asset_id in chosen)
    if set(ordered) != chosen or len(ordered) != len(set(ordered)):
        raise RegistryError(f"selection violates outfit group: {family_id}/{group_id}")
    return [by_id[asset_id] for asset_id in ordered]


def resolve_selection(
    registry: dict[str, Any], *, character_sex: str, family_id: str,
    group_id: str, family_asset_ids: list[str] | None = None,
    shared_shoe_id: str | None = None, hair_id: str | None = None,
) -> dict[str, Any]:
    if character_sex not in {"male", "female"}:
        raise RegistryError(f"invalid character sex: {character_sex}")
    family = next((row for row in registry["families"] if row["family_id"] == family_id), None)
    if family is None or family["sex"] != character_sex:
        raise RegistryError(f"family not available to {character_sex}: {family_id}")
    chosen = _selected_assets(family, group_id, list(family_asset_ids or []))
    if family.get("shared_footwear_policy"):
        optional_barefoot = shared_shoe_id is None and female_shoe_optional(family, group_id)
        if character_sex != "female" or (not optional_barefoot and shared_shoe_id not in FEMALE_SHARED_SHOE_IDS):
            raise RegistryError("Female outfit requires an approved universal shared shoe")
    if shared_shoe_id is not None:
        shoe = next((row for row in registry["shared_shoe_assets"] if row["asset_id"] == shared_shoe_id), None)
        if shoe is None or shoe["sex"] not in {character_sex, "both"}:
            raise RegistryError(f"shared shoe not available to {character_sex}: {shared_shoe_id}")
        if any(asset["slot"] == "shoes" for asset in chosen):
            raise RegistryError("native and shared shoes cannot be selected together")
    else:
        shoe = None
    slots = {asset["slot"] for asset in chosen}
    if shoe:
        slots.add("shoes")
    if "pants" in slots and "skirts" in slots:
        raise RegistryError("pants and skirts cannot share Bottom")
    if family["assembly_mode"] != "locked_bundle" and "full_body" in slots and slots & {"coats", "shirts", "pants", "skirts"}:
        raise RegistryError("full body and separate clothing cannot be mixed")

    outfit_rows = [(asset["asset_id"], asset["slot"], path)
                   for asset in chosen for path in asset["ue_mesh_paths"]]
    if shoe:
        outfit_rows.extend((shoe["asset_id"], "shoes", path) for path in shoe["ue_asset_paths"])
    targets, used_fixed, bundle_count = [], set(), 0
    for asset_id, slot, path in outfit_rows:
        fixed = FIXED_SLOT.get(slot)
        if fixed and fixed not in used_fixed:
            target = fixed
            used_fixed.add(fixed)
        else:
            bundle_count += 1
            if bundle_count > BUNDLE_CAPACITY:
                raise RegistryError(f"outfit exceeds {BUNDLE_CAPACITY} BundlePart slots")
            target = f"BundlePart{bundle_count:02d}"
        targets.append({"target_component": target, "target_kind": "fixed_semantic_slot" if fixed == target else "reusable_bundle_pool",
                        "source_component_name": asset_id, "slot": slot, "mesh_path": path})

    deny = family["hair_interface"]["deny_all"] or any(
        asset.get("hair_interface", {}).get("deny_all", False) for asset in chosen
    )
    hair = None
    hair_reason = "not_selected"
    if hair_id is not None:
        hair = next((row for row in registry["hair_assets"] if row["hair_id"] == hair_id), None)
        if hair is None or not hair_available_to(hair, character_sex):
            raise RegistryError(f"hair not available to {character_sex}: {hair_id}")
        if deny:
            hair = None
            hair_reason = "deny_all"
        else:
            hair_reason = "allowed"
    fit = hair_fit(hair, character_sex) if hair else None
    hair_assignments = ([{"target_component": f"HairPart{index:02d}",
                          "target_kind": "hair_pool", "source_component_name": hair_id,
                          "slot": "scalp_hair", "mesh_path": mesh["path"]}
                         for index, mesh in enumerate(fit["meshes"], 1)] if hair else [])
    selection_key = json.dumps([family_id, group_id, [a["asset_id"] for a in chosen],
                                shared_shoe_id, hair_id], ensure_ascii=False, separators=(",", ":"))
    variant_id = hashlib.sha256(selection_key.encode("utf-8")).hexdigest()[:12]
    return {
        "family_id": family_id, "group_id": group_id, "character_sex": character_sex,
        "selected_family_asset_ids": [a["asset_id"] for a in chosen],
        "shared_shoe_id": shared_shoe_id, "requested_hair_id": hair_id,
        "resolved_hair_id": hair["hair_id"] if hair else None,
        "hair_reason": hair_reason, "variant_id": variant_id,
        "qualified_variant_id": f"{family_id}::{group_id}::{variant_id}",
        "assignments": targets, "expected_target_component_names": [a["target_component"] for a in targets],
        "assignment_count": len(targets), "required_bundle_component_count": bundle_count,
        "hair_assignments": hair_assignments,
        "hair_fit_sex": character_sex if hair and hair.get("fit_variants") else None,
        "hair_skeleton_path": fit.get("skeleton_path") if fit else None,
    }
