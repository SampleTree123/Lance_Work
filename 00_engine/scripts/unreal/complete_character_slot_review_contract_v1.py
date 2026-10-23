"""Pure-Python choices for the reviewed pool's complete-character slot review.

Presets retain historical panel numbers and are shortcuts, not the legal
combination space. Slot groups are the authority for independent choices.
Nothing here imports Unreal, writes assets, or certifies visual fit.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import formal_wardrobe_registry_v1 as formal
import complete_character_review_contract_v1 as historical

SLOT_LABELS = {"shirts": "内搭", "coats": "外套", "pants": "裤子", "skirts": "裙子",
               "full_body": "连体服装", "shoes": "鞋", "family_accessory": "配件"}
CHOICE_KEYS = {"family_id", "group_id", "slot_choices", "optional_asset_ids", "shared_shoe_id", "hair_id"}


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _source(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _label(row: dict, fallback: str) -> str:
    # Existing source labels include legacy encoding damage; stable IDs remain
    # the selection keys even when a source label needs a readable fallback.
    value = row.get("display_name", "")
    return value if value and value.isascii() else fallback.replace("_", " ").title()


def _registry() -> tuple[dict, dict]:
    path = formal.current_registry_path()
    return formal.read_registry(path), _source(path)


def _family_group(registry: dict, family_id: str, group_id: str) -> tuple[dict, dict]:
    family = next((f for f in registry["families"] if f["family_id"] == family_id), None)
    if family is None:
        raise formal.RegistryError(f"Unknown reviewed family: {family_id}")
    if family["assembly_mode"] == "locked_bundle":
        bundle = family["assembly"]["bundle"]
        if group_id != bundle["bundle_id"]:
            raise formal.RegistryError(f"Unknown locked bundle: {family_id}/{group_id}")
        group = {"group_id": group_id, "required_slots": [], "optional_slots": [], "slot_pools": {},
                 "required_assets": bundle["required_assets"], "optional_assets": []}
    else:
        group = next((g for g in family["assembly"]["groups"] if g["group_id"] == group_id), None)
        if group is None:
            raise formal.RegistryError(f"Unknown reviewed group: {family_id}/{group_id}")
    return family, group


def _empty_choice() -> dict:
    return {"family_id": None, "group_id": None, "slot_choices": {}, "optional_asset_ids": [],
            "shared_shoe_id": None, "hair_id": None}


def _default(registry: dict, family_id: str | None, group_id: str | None) -> dict:
    choice = _empty_choice()
    if family_id is None and group_id is None:
        return choice
    family, group = _family_group(registry, family_id, group_id)
    choice.update({"family_id": family["family_id"], "group_id": group["group_id"],
                   "slot_choices": {slot: (pool[0] if slot in group["required_slots"] else None)
                                    for slot, pool in group["slot_pools"].items()}})
    if family.get("shared_footwear_policy") and not formal.female_shoe_optional(family, group_id):
        choice["shared_shoe_id"] = family["shared_footwear_policy"]["default_asset_id"]
    return choice


def default_choice(family_id: str | None, group_id: str | None) -> dict[str, Any]:
    """Choose first required slot members; optional slots/accessories stay empty.

    A locked bundle always supplies all required pieces. Female shared shoes default to the approved pool; male shoes and hair
    retain their existing defaults. (None, None) is the complete unclothed choice.
    """
    registry, _ = _registry()
    return _default(registry, family_id, group_id)


def _canonical(registry: dict, sex: str, choice: dict) -> tuple[dict, dict]:
    if sex not in {"male", "female"}:
        raise formal.RegistryError(f"Invalid character sex: {sex}")
    if not isinstance(choice, dict) or set(choice) - CHOICE_KEYS:
        raise formal.RegistryError("Unknown UI choice fields; canonical asset lists are not UI slot choices")
    value = {**_empty_choice(), **copy.deepcopy(choice)}
    slots, extras = value["slot_choices"], value["optional_asset_ids"]
    if (not isinstance(slots, dict) or not isinstance(extras, list)
            or any(not isinstance(a, str) for a in extras) or len(extras) != len(set(extras))):
        raise formal.RegistryError("Invalid or duplicate slot/accessory choices")
    for key in ("family_id", "group_id", "shared_shoe_id", "hair_id"):
        if value[key] is not None and (not isinstance(value[key], str) or not value[key]):
            raise formal.RegistryError(f"Invalid {key}")
    if value["family_id"] is None:
        if value["group_id"] is not None or slots or extras or value["shared_shoe_id"] is not None:
            raise formal.RegistryError("No-outfit choice cannot contain clothing, accessories or shoes")
        hair_id = value["hair_id"]
        if hair_id is not None:
            hair = next((h for h in registry["hair_assets"] if h["hair_id"] == hair_id), None)
            if hair is None or not formal.hair_available_to(hair, sex):
                raise formal.RegistryError(f"hair not available to {sex}: {hair_id}")
        return ({"hair_id": hair_id} if hair_id else {}), value
    family, group = _family_group(registry, value["family_id"], value["group_id"])
    if family["sex"] != sex:
        raise formal.RegistryError(f"Family not available to {sex}: {family['family_id']}")
    pools = group["slot_pools"]
    if set(slots) - set(pools):
        raise formal.RegistryError("Unknown slot or attempt to split a locked bundle")
    selected = []
    normalized_slots = {}
    for slot, pool in pools.items():
        selected_id = slots.get(slot)
        if selected_id is None:
            if slot in group["required_slots"]:
                raise formal.RegistryError(f"Required slot is empty: {slot}")
        elif not isinstance(selected_id, str) or selected_id not in pool:
            raise formal.RegistryError(f"Asset does not belong to this group slot: {slot}")
        else:
            selected.append(selected_id)
        normalized_slots[slot] = selected_id
    if not set(extras) <= set(group.get("optional_assets", [])):
        raise formal.RegistryError("Accessory is not optional in this group")
    selected.extend(group.get("required_assets", []))
    # Canonical ordering makes equivalent UI selections produce one variant ID.
    ordered_extras = [a for a in group.get("optional_assets", []) if a in extras]
    selected.extend(ordered_extras)
    value["slot_choices"], value["optional_asset_ids"] = normalized_slots, ordered_extras
    return {"family_id": family["family_id"], "group_id": group["group_id"],
            "family_asset_ids": selected, "shared_shoe_id": value["shared_shoe_id"], "hair_id": value["hair_id"]}, value


def _validate(registry: dict, registry_source: dict, sex: str, choice: dict) -> dict:
    canonical, normalized = _canonical(registry, sex, choice)
    if canonical.get("family_id"):
        resolved = formal.resolve_selection(registry, character_sex=sex, **canonical)
        # Derive deny even with no selected hair, which otherwise reports only
        # not_selected. It must still be enforced by the complete resolver.
        policy_probe = formal.resolve_selection(registry, character_sex=sex,
                                               **{**canonical, "hair_id": "HAIR_HB1_01"})
        deny = policy_probe["hair_reason"] == "deny_all"
    else:
        hair_id = canonical.get("hair_id")
        hair = next((h for h in registry["hair_assets"] if h["hair_id"] == hair_id), None)
        fit = formal.hair_fit(hair, sex) if hair else None
        hair_assignments = [{"target_component": f"HairPart{i:02d}", "target_kind": "hair_pool",
                             "source_component_name": hair_id, "slot": "scalp_hair", "mesh_path": mesh["path"]}
                            for i, mesh in enumerate(fit["meshes"], 1)] if fit else []
        resolved = {"character_sex": sex, "family_id": None, "group_id": None, "selected_family_asset_ids": [],
                    "shared_shoe_id": None, "requested_hair_id": hair_id, "resolved_hair_id": hair_id,
                    "hair_reason": "allowed" if hair else "not_selected", "assignments": [],
                    "expected_target_component_names": [], "assignment_count": 0,
                    "required_bundle_component_count": 0, "hair_assignments": hair_assignments,
                    "hair_fit_sex": sex if hair else None, "hair_skeleton_path": fit.get("skeleton_path") if fit else None}
        deny = False
    return {**resolved, "hair_deny": deny, "normalized_choice": normalized,
            "canonical_choice": canonical, "registry_source": registry_source}


def validate_choice(sex: str, choice: dict[str, Any]) -> dict[str, Any]:
    """Resolve a UI choice, rejecting missing requirements and foreign assets."""
    registry, source = _registry()
    return _validate(registry, source, sex, choice)


def to_runtime_choice(sex: str, choice: dict[str, Any]) -> dict[str, Any]:
    """Return only the canonical schema accepted by the slot UE worker."""
    return validate_choice(sex, choice)["canonical_choice"]


def _from_canonical(registry: dict, request: dict) -> dict:
    choice = _default(registry, request["family_id"], request["group_id"])
    _, group = _family_group(registry, request["family_id"], request["group_id"])
    selected = set(request["family_asset_ids"])
    if len(selected) != len(request["family_asset_ids"]) or not set(group.get("required_assets", [])) <= selected:
        raise formal.RegistryError("Preset duplicates or omits required assets")
    consumed = set(group.get("required_assets", []))
    for slot, pool in group["slot_pools"].items():
        matches = [a for a in pool if a in selected]
        if len(matches) > 1:
            raise formal.RegistryError("Preset chooses multiple assets in one slot")
        choice["slot_choices"][slot] = next(iter(matches), None)
        consumed.update(matches)
    choice["optional_asset_ids"] = [a for a in group.get("optional_assets", []) if a in selected]
    consumed.update(choice["optional_asset_ids"])
    if consumed != selected:
        raise formal.RegistryError("Preset includes foreign assets")
    choice["shared_shoe_id"], choice["hair_id"] = request.get("shared_shoe_id"), request.get("hair_id")
    return choice


def _asset_option(asset: dict) -> dict:
    return {"asset_id": asset["asset_id"], "label": _label(asset, asset["asset_id"].split(".")[-1]),
            "slot": asset["slot"], "mesh_paths": list(asset["ue_mesh_paths"]),
            "hair_interface": copy.deepcopy(asset.get("hair_interface"))}


def _family_catalog(family: dict) -> dict:
    by_id = {a["asset_id"]: a for a in family["assets"]}
    gids = ([family["assembly"]["bundle"]["bundle_id"]] if family["assembly_mode"] == "locked_bundle"
            else [g["group_id"] for g in family["assembly"]["groups"]])
    groups = []
    for gid in gids:
        _, g = _family_group({"families": [family]}, family["family_id"], gid)
        required_ids = g.get("required_assets", [])
        requires_shoes = ("shoes" in g["required_slots"] or any(by_id[a]["slot"] == "shoes" for a in required_ids))
        groups.append({"group_id": gid, "label": gid.replace("_", " ").title(),
                       "required_slots": list(g["required_slots"]), "optional_slots": list(g["optional_slots"]),
                       "slot_options": {s: [_asset_option(by_id[a]) for a in pool] for s, pool in g["slot_pools"].items()},
                       "required_assets": [_asset_option(by_id[a]) for a in required_ids],
                       "optional_assets": [_asset_option(by_id[a]) for a in g.get("optional_assets", [])],
                       "optional_asset_policy": g.get("optional_asset_policy", "independent_subset"),
                       "shared_shoe_policy": ("optional_universal_female_pool" if formal.female_shoe_optional(family, gid) else
                                              "required_universal_female_pool" if family.get("shared_footwear_policy") else
                                              "forbidden_native_required" if requires_shoes else "only_without_selected_native_shoes")})
    return {"family_id": family["family_id"], "label": _label(family, family["family_id"].split(".", 1)[1]),
            "sex": family["sex"], "assembly_mode": family["assembly_mode"],
            "hair_interface": copy.deepcopy(family["hair_interface"]), "groups": groups}


def _actions(sources: dict) -> dict:
    """Reuse the durable current action catalog without its historical outfits."""
    sources["standard_candidate_registry"] = _source(historical.STANDARD_REGISTRY)
    standard = _read(historical.STANDARD_REGISTRY)
    if {r["sex"] for r in standard["cases"]} != {"male", "female"}:
        raise ValueError("Complete-character source must contain both sexes")
    return historical.current_actions(sources)


def catalog() -> dict[str, Any]:
    """Read current publication and return JSON-compatible GUI choices + hashes.

    Index zero is reserved for no outfit/hair/static animation. Nonzero preset
    and hairstyle numbers are the original panel numbers and contain gaps.
    Each call reads fresh inputs; no combinations are enumerated or cached.
    """
    registry, registry_source = _registry()
    publication_path = formal.current_registry_publication_path()
    publication = _read(publication_path)
    mapping_path = Path(publication["mapping_report"])
    mapping = _read(mapping_path)
    sources = {"registry": registry_source, "publication": _source(publication_path)}
    for key in ("mapping_report", "selection_validation", "protected_sources_report", "source_registry", "source_publication"):
        sources[key] = _source(Path(publication[key]))
    families = {f["family_id"]: f for f in registry["families"]}
    presets = {"female": [], "male": []}
    for row in mapping["outfits"]:
        if row["status"] != "retained":
            continue
        sex = row["character_sex"]
        choice = _from_canonical(registry, row["request"])
        resolved = _validate(registry, registry_source, sex, choice)
        if resolved["assignments"] != row["assignments"]:
            raise formal.RegistryError("Published preset differs from current resolution")
        family = families[row["family_id"]]
        by_id = {a["asset_id"]: a for a in family["assets"]}
        names = [_label(by_id[a], a.split(".")[-1]) for a in resolved["selected_family_asset_ids"]]
        presets[sex].append({"index": row["historical_sex_index"], "historical_review_index": row["historical_review_index"],
                              "label": f"{_label(family, family['family_id'].split('.', 1)[1])}: {' + '.join(names)}",
                              "choice": choice, "canonical_choice": resolved["canonical_choice"], "hair_deny": resolved["hair_deny"]})
    if {s: len(v) for s, v in presets.items()} != {"female": 79, "male": 73}:
        raise ValueError("Expected 152 surviving historical presets")
    hairs = {"female": [], "male": []}
    hair_numbers = {h["hair_id"]: h["historical_review_index"] for h in mapping["hair"]}
    for hair in registry["hair_assets"]:
        for sex in hairs:
            if formal.hair_available_to(hair, sex):
                hairs[sex].append({"index": hair_numbers[hair["hair_id"]], "hair_id": hair["hair_id"],
                                    "label": _label(hair, hair["hair_id"]), "sex": hair["sex"],
                                    "reviewed_sexes": list(hair["reviewed_sexes"]), "fit": copy.deepcopy(formal.hair_fit(hair, sex))})
    approved_indices = formal.hair_review_indices_by_sex(registry)
    if {s: [h["index"] for h in rows] for s, rows in hairs.items()} != approved_indices:
        raise ValueError("Expected approved sex-specific hairstyle pools")
    return {"schema_version": 1, "publication_id": formal.CURRENT_REVIEWED_POOL_ID,
            "scope": "reviewed_selection_rules_not_new_body_visual_acceptance", "new_body_visual_acceptance": False,
            "slot_labels": SLOT_LABELS, "presets_are_shortcuts_not_complete_combinations": True,
            "presets_by_sex": presets,
            "families_by_sex": {sex: [_family_catalog(f) for f in registry["families"] if f["sex"] == sex]
                                for sex in ("female", "male")},
            "hairs_by_sex": hairs, "hair_review_indices_by_sex": approved_indices,
            "shared_shoes_by_sex": {sex: [{"asset_id": a["asset_id"], "label": _label(a, a["asset_id"]),
                                           "sex": a["sex"], "mesh_paths": list(a["ue_asset_paths"])}
                                          for a in registry["shared_shoe_assets"] if a["sex"] in {sex, "both"}]
                                    for sex in ("female", "male")},
            "actions_by_sex": _actions(sources), "sources": sources}


if __name__ == "__main__":
    print(json.dumps(catalog(), ensure_ascii=False, indent=2))
