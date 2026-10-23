"""Selection publication, original permissions and fail-closed routing."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formal_wardrobe_registry_v1 as formal
import build_reviewed_wardrobe_pool_registry_v1 as publisher


@pytest.fixture(scope="module")
def inputs():
    return (publisher.read(formal.MATERIAL_REPAIR_REGISTRY), publisher.read(publisher.CANDIDATE),
            publisher.read(publisher.FEEDBACK))


@pytest.fixture(scope="module")
def registry(inputs):
    return publisher.build_registry(*inputs)


def test_exact_reviewed_permissions_preserve_source_and_both_fits(inputs, registry):
    source, candidate, feedback = inputs
    before = copy.deepcopy(inputs)
    assert publisher.build_registry(*inputs) == registry
    assert inputs == before
    by_id = {h["hair_id"]: h for h in source["hair_assets"]}
    for hair in registry["hair_assets"]:
        original = copy.deepcopy(hair)
        original.pop("reviewed_sexes")
        assert original == by_id[hair["hair_id"]]
        assert set(hair["fit_variants"]) == {"male", "female"}
    for sex in ("male", "female"):
        expected = {r["hair_id"] for r in feedback["hair"]["selected_by_sex"][sex]}
        actual = {h["hair_id"] for h in registry["hair_assets"] if formal.hair_available_to(h, sex)}
        assert actual == expected
    for hair_id in ("HAIR_HB1_16", "HAIR_HB1_17", "HAIR_HB1_18"):
        hair = next(h for h in registry["hair_assets"] if h["hair_id"] == hair_id)
        assert hair["sex"] == "both" and hair["reviewed_sexes"] == ["female"]
        with pytest.raises(formal.RegistryError, match="hair not available"):
            formal.resolve_selection(registry, character_sex="male", family_id="male.redsoul", group_id="default", hair_id=hair_id)


@pytest.mark.parametrize("bad_review", [None, [], ["male"], ["female", "female"], "female", [False]])
def test_reviewed_permission_cannot_expand_or_disappear(registry, bad_review):
    changed = copy.deepcopy(registry)
    hair = next(h for h in changed["hair_assets"] if h["sex"] == "female")
    hair["reviewed_sexes"] = bad_review
    with pytest.raises(formal.RegistryError, match="reviewed hairstyle"):
        formal.validate_registry(changed)


def test_exact_clothing_exclusions_and_shoes_unchanged(inputs, registry):
    source = inputs[0]
    assert formal.validate_registry(registry) == publisher.COUNTS
    assert registry["shared_shoe_assets"] == source["shared_shoe_assets"]
    old = {f["family_id"]: f for f in source["families"]}
    new = {f["family_id"]: f for f in registry["families"]}
    assert set(old) - set(new) == {"female.rugged_trendy", "male.kilt"}
    changed = {fid for fid in new if new[fid] != old[fid]}
    assert changed == {"female.streetwear_collection", "male.cyberpunk_locked"}
    street = new["female.streetwear_collection"]
    assert {g["group_id"] for g in street["assembly"]["groups"]} == {"full_body", "skirt_with_shirt"}
    removed = [a for a in old[street["family_id"]]["assets"] if a not in street["assets"]]
    assert {a["display_name"] for a in removed} == {f"YogaPants_{c}" for c in "ABCDEF"}
    assert street["hair_interface"] == old[street["family_id"]]["hair_interface"]
    cyber = new["male.cyberpunk_locked"]
    assert cyber["assembly_mode"] == "locked_bundle" and len(cyber["assets"]) == 4
    assert any("/cs_c01_shirt.cs_c01_shirt" in p for a in cyber["assets"] for p in a["ue_mesh_paths"])
    result = formal.resolve_selection(registry, character_sex="male", family_id=cyber["family_id"], group_id="default")
    assert set(result["selected_family_asset_ids"]) == set(cyber["assembly"]["bundle"]["required_assets"])
    assert publisher.MASK_ID not in result["selected_family_asset_ids"]
    with pytest.raises(formal.RegistryError, match="whole"):
        formal.resolve_selection(registry, character_sex="male", family_id=cyber["family_id"], group_id="default",
                                 family_asset_ids=result["selected_family_asset_ids"][:3])


def test_witness_number_mapping_and_preserved_denial(inputs, registry):
    validation, mapping = publisher.verify_selections(inputs[0], registry, publisher.read(publisher.REVIEW_PLAN))
    assert validation["retained_witnesses"] == 156
    assert validation["retained_by_sex"] == {"male": 77, "female": 79}
    excluded = [r for r in mapping["outfits"] if r["status"] == "excluded"]
    assert len(excluded) == 17
    assert [r["historical_sex_index"] for r in excluded if r["reason"] == "YogaPants_A_to_F"] == list(range(71, 86))
    assert mapping["cyberpunk_removed_mask"]["target_component"] == "BundlePart01"
    assert any(row["deny_all"] for row in validation["canonical_group_checks"])
    assert validation["new_body_visual_acceptance"] is False


def test_candidate_cannot_smuggle_unapproved_clothing_or_geometry(inputs):
    source, candidate, feedback = copy.deepcopy(inputs)
    candidate["shared_shoe_assets"].pop()
    with pytest.raises(ValueError, match="approved selection delta"):
        publisher.build_registry(source, candidate, feedback)
    source, candidate, feedback = copy.deepcopy(inputs)
    candidate["hair_assets"][0]["fit_variants"]["male"]["meshes"][0]["path"] += "_changed"
    with pytest.raises(ValueError, match="approved selection delta"):
        publisher.build_registry(source, candidate, feedback)


@pytest.fixture
def publication(tmp_path, monkeypatch, registry):
    """A complete isolated publication; all gate links bind real file bytes."""
    output = tmp_path / "reviewed.json"
    source = tmp_path / "source.json"
    source_receipt = tmp_path / "source_receipt.json"
    receipt_path = tmp_path / "publication_manifest.json"
    for name, path in (("REVIEWED_POOL_REGISTRY", output), ("MATERIAL_REPAIR_REGISTRY", source),
                       ("MATERIAL_REPAIR_PUBLICATION", source_receipt), ("REVIEWED_POOL_PUBLICATION", receipt_path)):
        monkeypatch.setattr(formal, name, path)
    publisher.write_new(source, {"source": True})
    publisher.write_new(output, registry)
    publisher.write_new(source_receipt, {"success": True, "batch_id": "fixed_head_material_repair_20261005_v1",
                                       "output_registry": str(source), "output_registry_sha256": publisher.digest(source)})
    receipt = {"success": True, "publication_id": formal.REVIEWED_POOL_ID, "scope": publisher.SCOPE,
               "counts": publisher.COUNTS, "hair_selection_counts": publisher.HAIR_COUNTS}
    for key, path in (("source_registry", source), ("source_publication", source_receipt), ("output_registry", output)):
        receipt[key], receipt[key + "_sha256"] = str(path), publisher.digest(path)
    for key in ("selection_validation", "mapping_report", "protected_sources_report"):
        path = tmp_path / (key + ".json")
        publisher.write_new(path, {"success": True, "output_registry_sha256": publisher.digest(output)})
        receipt[key], receipt[key + "_sha256"] = str(path), publisher.digest(path)
    publisher.write_new(receipt_path, receipt)
    return receipt_path, receipt


def test_explicit_v1_validates_receipt_but_other_history_still_readable(publication, inputs):
    receipt_path, receipt = publication
    assert formal.reviewed_pool_v1_registry_path() == formal.REVIEWED_POOL_REGISTRY
    assert formal.read_registry(formal.reviewed_pool_v1_registry_path())["reviewed_pool"]["publication_id"] == formal.REVIEWED_POOL_ID
    historical = receipt_path.parent / "explicit_history.json"
    publisher.write_new(historical, inputs[0])
    receipt_path.unlink()
    with pytest.raises(formal.RegistryError, match="refusing unfiltered fallback"):
        formal.reviewed_pool_v1_registry_path()
    assert len(formal.read_registry(historical)["hair_assets"]) == 40


@pytest.mark.parametrize("target", ["receipt", "source_registry", "source_publication", "output_registry",
                                     "selection_validation", "mapping_report", "protected_sources_report", "both_current_files"])
def test_explicit_v1_never_silently_falls_back_on_missing_or_changed_bound_file(publication, target):
    receipt_path, receipt = publication
    if target in {"receipt", "both_current_files"}:
        receipt_path.unlink()
        if target == "both_current_files":
            Path(receipt["output_registry"]).unlink()
    else:
        with Path(receipt[target]).open("ab") as handle:
            handle.write(b"\n")
    with pytest.raises(formal.RegistryError, match="refusing unfiltered fallback"):
        formal.reviewed_pool_v1_registry_path()


@pytest.mark.parametrize("target", ["selection_validation", "mapping_report", "protected_sources_report", "source_publication"])
def test_rehashed_failure_report_does_not_publish(publication, target):
    receipt_path, receipt = publication
    path = Path(receipt[target])
    data = publisher.read(path)
    data["success"] = False
    path.write_bytes(publisher.encoded(data))
    receipt[target + "_sha256"] = publisher.digest(path)
    receipt_path.write_bytes(publisher.encoded(receipt))
    with pytest.raises(formal.RegistryError, match="refusing unfiltered fallback"):
        formal.reviewed_pool_v1_registry_path()


def test_versioned_write_never_replaces_an_existing_output(tmp_path):
    path = tmp_path / "version.json"
    publisher.write_new(path, {"a": 1})
    before = path.read_bytes()
    publisher.write_new(path, {"a": 1})
    with pytest.raises(ValueError, match="Refusing to replace"):
        publisher.write_new(path, {"a": 2})
    assert path.read_bytes() == before


def test_live_publication_matches_reproducible_registry(registry):
    assert formal.reviewed_pool_v1_registry_path() == formal.REVIEWED_POOL_REGISTRY
    assert formal.read_registry(formal.reviewed_pool_v1_registry_path()) == registry
    receipt = publisher.read(formal.REVIEWED_POOL_PUBLICATION)
    protected = publisher.read(Path(receipt["protected_sources_report"]))
    for row in protected["records"]:
        assert publisher.digest(Path(row["path"])) == row["before_sha256"] == row["after_sha256"]


def test_historical_parity_is_explicit_while_inspect_uses_current_pool():
    import run_formal_wardrobe_registry_v1 as runner
    assert runner.registry_for_phase("parity") == formal.MATERIAL_REPAIR_REGISTRY
    assert runner.registry_for_phase("inspect") == formal.CURRENT_REVIEWED_POOL_REGISTRY
    assert runner.registry_for_phase("stage") == formal.CURRENT_REVIEWED_POOL_REGISTRY
    assert runner.registry_for_phase("parity", formal.LEGACY_REGISTRY) == formal.LEGACY_REGISTRY
    report = runner.parity_check(formal.read_registry(formal.MATERIAL_REPAIR_REGISTRY))
    assert report["success"] is True and report["exact_matches"] == 173
    assert report["scope"] == "historical_unfiltered_173_outfit_parity"
