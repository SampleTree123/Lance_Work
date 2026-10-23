"""Regression checks for the UE registry's actual selection contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))
from formal_wardrobe_registry_v1 import (  # noqa: E402
    MATERIAL_REPAIR_REGISTRY, RegistryError, read_registry, resolve_selection,
)


ENGINE = SCRIPT_ROOT.parents[1]
REVIEW_PLAN = (ENGINE / "outputs/unreal_character_import/asset_restructure_full_20260929_v1"
               / "review_plans/wardrobe_coverage/review_plan.json")


@pytest.fixture(scope="module")
def registry():
    # These are the unfiltered 173-outfit historical acceptance witnesses.
    return read_registry(MATERIAL_REPAIR_REGISTRY)


def test_accepted_173_outfits_resolve_to_same_components(registry):
    historical = json.loads(REVIEW_PLAN.read_text(encoding="utf-8"))
    old_variants = {variant["qualified_variant_id"]: variant
                    for bodyfit in historical["bodyfits"]
                    for variant in bodyfit["runtime_variants"]}
    rows = historical["review_selection"]["outfits"]
    assert len(rows) == 173
    for row in rows:
        new = resolve_selection(
            registry, character_sex=row["family_id"].split(".", 1)[0],
            family_id=row["family_id"], group_id=row["group_id"],
            family_asset_ids=row["family_asset_ids"],
            shared_shoe_id=next(iter(row["shared_shoe_ids"]), None),
        )
        old = old_variants[row["qualified_variant_id"]]
        actual = {(item["target_component"], item["mesh_path"]) for item in new["assignments"]}
        expected = {(item["target_component"], item["mesh_path"]) for item in old["assignments"]}
        assert actual == expected, row["qualified_variant_id"]


def test_hair_sex_and_outfit_denial(registry):
    family = next(f for f in registry["families"] if f["family_id"] == "female.streetwear_collection")
    group = next(g for g in family["assembly"]["groups"] if g["group_id"] == "pants_with_warrior_cloak")
    ids = [group["slot_pools"]["pants"][0], group["slot_pools"]["coats"][0]]
    denied = resolve_selection(registry, character_sex="female", family_id=family["family_id"],
                               group_id=group["group_id"], family_asset_ids=ids,
                               hair_id="HAIR_HB1_01")
    assert denied["hair_reason"] == "deny_all"
    assert denied["hair_assignments"] == []
    assert len(denied["assignments"]) == 2
    allowed_group = next(g for g in family["assembly"]["groups"] if g["group_id"] == "pants_with_casual_jacket")
    allowed = resolve_selection(registry, character_sex="female", family_id=family["family_id"],
                                group_id=allowed_group["group_id"],
                                family_asset_ids=[allowed_group["slot_pools"]["pants"][0],
                                                  allowed_group["slot_pools"]["coats"][0]],
                                hair_id="HAIR_HB1_01")
    assert allowed["hair_reason"] == "allowed"
    assert allowed["resolved_hair_id"] == "HAIR_HB1_01"
    assert allowed["hair_assignments"]
    with pytest.raises(RegistryError, match="hair not available"):
        resolve_selection(registry, character_sex="male", family_id="male.redsoul",
                          group_id="default", hair_id="HAIR_HB2_01")


def test_locked_bundle_is_inseparable_and_shared_shoe_keeps_footwear(registry):
    family = next(f for f in registry["families"] if f["family_id"] == "female.elise")
    full = resolve_selection(registry, character_sex="female", family_id=family["family_id"],
                             group_id="default", shared_shoe_id="F022")
    assert len(full["selected_family_asset_ids"]) == len(family["assets"])
    assert any(a["target_component"] == "Footwear" for a in full["assignments"])
    with pytest.raises(RegistryError, match="whole"):
        resolve_selection(registry, character_sex="female", family_id=family["family_id"],
                          group_id="default", family_asset_ids=[family["assets"][0]["asset_id"]])
