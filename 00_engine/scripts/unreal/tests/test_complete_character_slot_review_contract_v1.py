"""Legal slot choices are independent of the frozen preset coverage."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import complete_character_slot_review_contract_v1 as contract
import formal_wardrobe_registry_v1 as formal


@pytest.fixture(scope="module")
def catalog():
    return contract.catalog()


def test_catalog_keeps_historical_numbers_without_restoring_excluded_choices(catalog):
    assert {s: len(v) for s, v in catalog["presets_by_sex"].items()} == {"female": 79, "male": 73}
    assert {s: len(v) for s, v in catalog["hairs_by_sex"].items()} == {"female": 20, "male": 13}
    female = {p["index"] for p in catalog["presets_by_sex"]["female"]}
    male = {p["index"] for p in catalog["presets_by_sex"]["male"]}
    assert set(range(1, 96)) - female == {45, *range(71, 86)}
    assert set(range(1, 79)) - male == {31, 33, 34, 35, 36}
    assert max(female) == 95 and max(male) == 78
    assert [h["index"] for h in catalog["hairs_by_sex"]["male"]] == [1, 2, 3, 5, 6, 11, 27, 28, 30, 31, 32, 37, 39]
    assert all(h["index"] not in {4, 7, 12, 13, 18, 20, 21, 34} for rows in catalog["hairs_by_sex"].values() for h in rows)
    assert catalog["presets_are_shortcuts_not_complete_combinations"] is True
    assert catalog["new_body_visual_acceptance"] is False
    json.dumps(catalog)  # The GUI catalog can be serialized without UE objects.


def test_all_presets_have_one_ui_schema_and_equivalent_runtime_resolution(catalog):
    registry = formal.read_registry()
    for sex, rows in catalog["presets_by_sex"].items():
        for preset in rows:
            assert set(preset["choice"]) == contract.CHOICE_KEYS
            runtime = contract.to_runtime_choice(sex, preset["choice"])
            assert runtime == preset["canonical_choice"]
            expected = formal.resolve_selection(registry, character_sex=sex, **runtime)
            resolved = contract.validate_choice(sex, preset["choice"])
            for key, value in expected.items():
                assert resolved[key] == value


def test_every_group_has_a_valid_default_and_preserves_required_components(catalog):
    for sex, families in catalog["families_by_sex"].items():
        for family in families:
            for group in family["groups"]:
                choice = contract.default_choice(family["family_id"], group["group_id"])
                resolved = contract.validate_choice(sex, choice)
                assert {a["asset_id"] for a in group["required_assets"]} <= set(resolved["selected_family_asset_ids"])
                assert choice["optional_asset_ids"] == []
                for slot in group["optional_slots"]:
                    assert choice["slot_choices"][slot] is None
                for slot in group["required_slots"]:
                    assert choice["slot_choices"][slot] in {a["asset_id"] for a in group["slot_options"][slot]}


def test_nonpreset_legal_separates_can_be_selected_without_enumeration(catalog):
    family = next(f for f in catalog["families_by_sex"]["female"] if f["family_id"] == "female.bikini_ruana")
    group = family["groups"][0]
    choice = contract.default_choice(family["family_id"], group["group_id"])
    choice["slot_choices"].update({"pants": group["slot_options"]["pants"][3]["asset_id"],
                                    "shirts": group["slot_options"]["shirts"][2]["asset_id"],
                                    "coats": group["slot_options"]["coats"][4]["asset_id"]})
    runtime = contract.to_runtime_choice("female", choice)
    assert not any(set(p["canonical_choice"]["family_asset_ids"]) == set(runtime["family_asset_ids"])
                   for p in catalog["presets_by_sex"]["female"])
    result = contract.validate_choice("female", choice)
    assert {a["target_component"] for a in result["assignments"]} == {"Bottom", "UpperInner", "UpperOuter"}
    choice["slot_choices"]["coats"] = None
    assert "UpperOuter" not in contract.validate_choice("female", choice)["expected_target_component_names"]


@pytest.mark.parametrize("change,match", [
    (lambda c: c["slot_choices"].pop("pants"), "Required slot"),
    (lambda c: c["slot_choices"].update(pants="male.white_tie.asset.3264922c4290"), "does not belong"),
    (lambda c: c["slot_choices"].update(full_body="anything"), "Unknown slot"),
    (lambda c: c.update(optional_asset_ids=["foreign.accessory"]), "not optional"),
    (lambda c: c.update(family_asset_ids=[]), "Unknown UI choice"),
])
def test_invalid_required_and_foreign_inputs_are_not_silently_ignored(change, match):
    choice = contract.default_choice("female.bikini_ruana", "default")
    change(choice)
    with pytest.raises(formal.RegistryError, match=match):
        contract.to_runtime_choice("female", choice)


def test_locked_bundle_and_required_accessories_cannot_be_removed(catalog):
    locked = contract.default_choice("male.cyberpunk_locked", "default")
    result = contract.to_runtime_choice("male", locked)
    assert len(result["family_asset_ids"]) == 4
    locked["slot_choices"]["coats"] = result["family_asset_ids"][0]
    with pytest.raises(formal.RegistryError, match="locked bundle"):
        contract.validate_choice("male", locked)
    owen = contract.default_choice("male.owen", "default")
    group = next(f for f in catalog["families_by_sex"]["male"] if f["family_id"] == "male.owen")["groups"][0]
    required = group["required_assets"][0]["asset_id"]
    runtime = contract.to_runtime_choice("male", owen)
    assert required in runtime["family_asset_ids"]
    runtime["family_asset_ids"].remove(required)
    with pytest.raises(formal.RegistryError, match="omits required"):
        contract._from_canonical(formal.read_registry(), runtime)
    owen["optional_asset_ids"] = [required]
    with pytest.raises(formal.RegistryError, match="not optional"):
        contract.validate_choice("male", owen)


def test_optional_accessory_order_is_canonical_and_duplicates_rejected(catalog):
    family = next(f for f in catalog["families_by_sex"]["female"] if f["family_id"] == "female.jumpsuits_accessories")
    group = family["groups"][0]
    accessories = [a["asset_id"] for a in group["optional_assets"]]
    choice = contract.default_choice(family["family_id"], group["group_id"])
    choice["optional_asset_ids"] = accessories[::-1]
    first = contract.validate_choice("female", choice)
    assert first["normalized_choice"]["optional_asset_ids"] == accessories
    choice["optional_asset_ids"] = accessories
    assert contract.validate_choice("female", choice)["variant_id"] == first["variant_id"]
    choice["optional_asset_ids"] = [accessories[0], accessories[0]]
    with pytest.raises(formal.RegistryError, match="duplicate"):
        contract.validate_choice("female", choice)


def test_female_clothing_always_uses_universal_shared_pool(catalog):
    choice = contract.default_choice("female.dress_collection", "full_body")
    assert "shoes" not in choice["slot_choices"]
    assert choice["shared_shoe_id"] == "F001"
    for shoe in formal.FEMALE_SHARED_SHOE_IDS:
        choice["shared_shoe_id"] = shoe
        assert "Footwear" in contract.validate_choice("female", choice)["expected_target_component_names"]
    for shoe in [None, "F015", "not-a-shoe"]:
        choice["shared_shoe_id"] = shoe
        with pytest.raises(formal.RegistryError, match="approved universal shared shoe"):
            contract.validate_choice("female", choice)


def test_reviewed_hair_permissions_apply_with_and_without_clothing_and_deny_is_resolved():
    with pytest.raises(formal.RegistryError, match="hair not available"):
        contract.to_runtime_choice("male", {"hair_id": "HAIR_HB1_16"})
    naked = contract.validate_choice("female", {"hair_id": "HAIR_HB1_16"})
    assert naked["canonical_choice"] == {"hair_id": "HAIR_HB1_16"}
    assert naked["assignments"] == [] and naked["hair_assignments"]
    assert contract.to_runtime_choice("male", {}) == {}
    with pytest.raises(formal.RegistryError, match="No-outfit"):
        contract.to_runtime_choice("female", {"shared_shoe_id": "F022"})
    choice = contract.default_choice("male.redsoul", "default")
    assert contract.validate_choice("male", choice)["hair_deny"] is True
    choice["hair_id"] = "HAIR_HB1_01"
    resolved = contract.validate_choice("male", choice)
    assert resolved["hair_reason"] == "deny_all" and resolved["hair_assignments"] == []
    choice["hair_id"] = "HAIR_HB1_16"
    with pytest.raises(formal.RegistryError, match="hair not available"):
        contract.validate_choice("male", choice)


def test_source_hashes_and_action_availability_are_complete_without_old_outfit_catalog(monkeypatch):
    monkeypatch.setattr(contract.historical, "catalog", lambda: (_ for _ in ()).throw(AssertionError("old outfit catalog called")))
    data = contract.catalog()
    for key, source in data["sources"].items():
        rows = source.values() if key in {"action_reports", "action_packages"} else [source]
        for row in rows:
            assert hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() == row["sha256"]
    assert {s: len(v) for s, v in data["actions_by_sex"].items()} == {"male": 5, "female": 5}
    assert len(data["sources"]["action_reports"]) == len(data["sources"]["action_packages"]) == 10


def test_missing_current_action_package_prevents_available_action_claim(tmp_path, monkeypatch):
    monkeypatch.setattr(contract.historical, "PROJECT_CONTENT", tmp_path)
    with pytest.raises(ValueError, match="body-only package is absent"):
        contract.catalog()


def test_catalog_and_choice_fail_closed_when_publication_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(formal, "CURRENT_REVIEWED_POOL_PUBLICATION", tmp_path / "missing.json")
    for call in (contract.catalog, lambda: contract.default_choice("male.redsoul", "default"),
                 lambda: contract.to_runtime_choice("female", {})):
        with pytest.raises(formal.RegistryError, match="refusing unfiltered fallback"):
            call()
