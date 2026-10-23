"""Bounded checks for dual-fit publication and real wardrobe selection."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_fixed_head_hair_registry_v1 import BATCH_ID, build_registry
import formal_wardrobe_registry_v1 as formal
from formal_wardrobe_registry_v1 import LEGACY_REGISTRY, RegistryError, hair_fit, read_registry, resolve_selection


@pytest.fixture
def source_and_report():
    source = read_registry(LEGACY_REGISTRY)
    root = "/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1"
    report = {"batch_id": BATCH_ID, "ue_root": root,
              "success": True, "complete": True, "records": []}
    for hair in source["hair_assets"]:
        for sex in ("female", "male"):
            name = f"{hair['hair_id']}_{sex}"
            report["records"].append({
                "hair_id": hair["hair_id"], "sex": sex, "success": True,
                "skeleton_path": f"{root}/Shared/{sex}/SK_{sex}.SK_{sex}",
                "meshes": [{"name": name, "path": f"{root}/{sex}/{name}.{name}",
                            "materials": [f"{root}/MI_Hair.MI_Hair"]}],
            })
    return source, report


def test_publication_preserves_clothing_and_separates_geometry_from_permissions(source_and_report):
    source, report = source_and_report
    original = deepcopy(source)
    registry = build_registry(source, report)
    assert source == original
    assert registry["families"] == source["families"]
    assert registry["shared_shoe_assets"] == source["shared_shoe_assets"]
    assert [h["sex"] for h in registry["hair_assets"]] == [h["sex"] for h in source["hair_assets"]]
    hair = next(h for h in registry["hair_assets"] if h["hair_id"] == "HAIR_HB1_01")
    assert hair_fit(hair, "male")["meshes"] != hair_fit(hair, "female")["meshes"]
    for sex, family_id in (("female", "female.elise"), ("male", "male.redsoul")):
        selection = resolve_selection(registry, character_sex=sex, family_id=family_id,
                                      group_id="default", hair_id="HAIR_HB1_01")
        if selection["hair_reason"] == "deny_all":
            assert not selection["hair_assignments"]
        else:
            assert selection["hair_fit_sex"] == sex
            assert selection["hair_assignments"][0]["mesh_path"] == hair_fit(hair, sex)["meshes"][0]["path"]
    for sex in ("male", "female"):
        family = next(f for f in registry["families"]
                      if f["sex"] == sex and not f["hair_interface"]["deny_all"]
                      and f["assembly_mode"] == "slot_groups"
                      and not any(a.get("hair_interface", {}).get("deny_all") for a in f["assets"]))
        group = family["assembly"]["groups"][0]
        asset_ids = [group["slot_pools"][slot][0] for slot in group["required_slots"]]
        asset_ids += group.get("required_assets", [])
        selection = resolve_selection(registry, character_sex=sex, family_id=family["family_id"],
                                      group_id=group["group_id"], family_asset_ids=asset_ids,
                                      hair_id="HAIR_HB1_01")
        assert selection["hair_reason"] == "allowed"
        assert selection["hair_skeleton_path"] == hair_fit(hair, sex)["skeleton_path"]
        assert selection["hair_assignments"][0]["mesh_path"] == hair_fit(hair, sex)["meshes"][0]["path"]
    # A female-only style has a male geometry export but is still disallowed.
    with pytest.raises(RegistryError, match="hair not available"):
        resolve_selection(registry, character_sex="male", family_id="male.redsoul",
                          group_id="default", hair_id="HAIR_HB2_01")


def test_publication_rejects_incomplete_and_duplicate_pairs(source_and_report):
    source, report = source_and_report
    report["complete"] = False
    with pytest.raises(ValueError, match="completed successful"):
        build_registry(source, report)
    report["complete"] = True
    report["records"][-1] = deepcopy(report["records"][0])
    with pytest.raises(ValueError, match="exactly once"):
        build_registry(source, report)


def test_all_80_fits_resolve_with_existing_usage_and_outfit_denial(source_and_report):
    source, report = source_and_report
    registry = build_registry(source, report)
    accepted = rejected = 0
    for sex in ("male", "female"):
        family = next(f for f in registry["families"]
                      if f["sex"] == sex and not f["hair_interface"]["deny_all"]
                      and f["assembly_mode"] == "slot_groups"
                      and not any(a.get("hair_interface", {}).get("deny_all") for a in f["assets"]))
        group = family["assembly"]["groups"][0]
        ids = [group["slot_pools"][slot][0] for slot in group["required_slots"]]
        ids += group.get("required_assets", [])
        kwargs = {"character_sex": sex, "family_id": family["family_id"],
                  "group_id": group["group_id"], "family_asset_ids": ids}
        for hair in registry["hair_assets"]:
            fit = hair_fit(hair, sex)
            assert fit["meshes"] and fit["skeleton_path"]
            if hair["sex"] in {sex, "both"}:
                selection = resolve_selection(registry, hair_id=hair["hair_id"], **kwargs)
                assert [a["mesh_path"] for a in selection["hair_assignments"]] == [m["path"] for m in fit["meshes"]]
                assert selection["hair_skeleton_path"] == fit["skeleton_path"]
                accepted += 1
            else:
                with pytest.raises(RegistryError, match="hair not available"):
                    resolve_selection(registry, hair_id=hair["hair_id"], **kwargs)
                rejected += 1
        for family in registry["families"]:
            if family["sex"] != sex:
                continue
            if family["assembly_mode"] == "locked_bundle":
                requests = [(family["assembly"]["bundle"]["bundle_id"], [])]
            else:
                requests = []
                for group in family["assembly"]["groups"]:
                    ids = [group["slot_pools"][slot][0] for slot in group["required_slots"]]
                    ids += group.get("required_assets", [])
                    requests.append((group["group_id"], ids))
            for group_id, ids in requests:
                selection = resolve_selection(registry, character_sex=sex, family_id=family["family_id"],
                                              group_id=group_id, family_asset_ids=ids, hair_id="HAIR_HB1_01")
                by_id = {a["asset_id"]: a for a in family["assets"]}
                deny = family["hair_interface"]["deny_all"] or any(
                    by_id[aid].get("hair_interface", {}).get("deny_all", False)
                    for aid in selection["selected_family_asset_ids"])
                assert bool(selection["hair_assignments"]) is not deny
    assert (accepted, rejected) == (51, 29)


def test_historical_switch_waits_for_successful_hash_bound_publication(tmp_path, monkeypatch, source_and_report):
    source, report = source_and_report
    legacy = tmp_path / "legacy.json"
    candidate = tmp_path / "dual.json"
    receipt = tmp_path / "publication.json"
    imported = tmp_path / "import.json"
    monkeypatch.setattr(formal, "LEGACY_REGISTRY", legacy)
    monkeypatch.setattr(formal, "DUAL_FIT_REGISTRY", candidate)
    monkeypatch.setattr(formal, "DUAL_FIT_PUBLICATION", receipt)
    legacy.write_text(json.dumps(source), encoding="utf-8")
    candidate.write_text(json.dumps(build_registry(source, report)), encoding="utf-8")
    assert formal.historical_registry_path() == legacy  # A candidate alone is not publication.
    imported.write_text(json.dumps(report), encoding="utf-8")
    publication = {"batch_id": BATCH_ID, "success": True,
        "counts": {"hairstyles": 40, "fits": 80}, "output_registry": str(candidate),
        "output_registry_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "import_report": str(imported), "import_report_sha256": hashlib.sha256(imported.read_bytes()).hexdigest()}
    receipt.write_text(json.dumps(publication), encoding="utf-8")
    assert formal.historical_registry_path() == candidate
    assert "fit_variants" in formal.read_registry(formal.historical_registry_path())["hair_assets"][0]
    report["complete"] = False
    imported.write_text(json.dumps(report), encoding="utf-8")
    publication["import_report_sha256"] = hashlib.sha256(imported.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(publication), encoding="utf-8")
    assert formal.historical_registry_path() == legacy
    report["complete"] = True
    imported.write_text(json.dumps(report), encoding="utf-8")
    publication["import_report_sha256"] = hashlib.sha256(imported.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(publication), encoding="utf-8")
    candidate.write_text(candidate.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert formal.historical_registry_path() == legacy  # Modified index does not inherit acceptance.
