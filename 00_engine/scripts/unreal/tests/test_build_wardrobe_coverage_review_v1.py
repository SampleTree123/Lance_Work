import pytest

from test_build_wardrobe_review_plan_v1 import fixture
from build_wardrobe_coverage_review_v1 import compile_coverage


def data():
    registry, template, _, reports = fixture()
    for record in registry["families"]:
        record["document"]["rules_status"] = "confirmed"
    return registry, template, reports


def test_covers_every_mesh_and_keeps_visual_pending():
    plan = compile_coverage(*data(), "test")
    assert plan["coverage"]["planned_mesh_count"] == 6
    assert plan["coverage"]["outfit_count"] == 2
    assert not plan["coverage"]["uncovered_mesh_paths"]
    assert plan["coverage"]["visual_acceptance"] == "pending"
    assert plan["runtime_approved"] is False


def test_pool_variants_cover_assets_without_cartesian_product():
    registry, template, reports = data()
    doc = registry["families"][0]["document"]
    for slot in ("shirts", "pants"):
        old = next(a for a in doc["assets"] if a["slot"] == slot)["asset_id"]
        aid = old + "2"
        doc["assets"].append({"asset_id": aid, "slot": slot})
        doc["assembly"]["groups"][0]["slot_pools"][slot].append(aid)
        registry["units"].append({"unit_id": aid, "bodyfit_id": "M02_Average"})
        registry["asset_bindings"].append({"family_id": doc["family_id"], "asset_id": aid,
                                           "unit_id": aid, "module_key": aid})
        reports[0]["cases"].append({"case_id": aid, "transfer_passed": True, "modules": [
            {"module_key": aid, "slot": slot, "mesh_paths": [f"/Game/{aid}"], "mesh_names": [aid]}]})
    plan = compile_coverage(registry, template, reports, "test")
    assert plan["coverage"]["outfit_count"] == 3
    body = plan["bodyfits"][0]
    assert len(body["candidate_mesh_registry"]) == 5
    assert len({c["component_name"] for c in body["candidate_mesh_registry"]}) == 5
    assert plan["coverage"]["planned_mesh_count"] == 8


def test_unreachable_asset_fails_instead_of_disappearing():
    registry, template, reports = data()
    registry["families"][0]["document"]["assets"].append({"asset_id": "orphan", "slot": "coats"})
    with pytest.raises(ValueError, match="outside approved groups"):
        compile_coverage(registry, template, reports, "test")


def test_missing_transfer_or_failed_report_blocks_planning():
    registry, template, reports = data()
    reports[0]["success"] = False
    with pytest.raises(ValueError, match="successful transfer"):
        compile_coverage(registry, template, reports, "test")


def test_locked_bundle_keeps_all_parts():
    registry, template, reports = data()
    doc = registry["families"][0]["document"]
    doc["assembly_mode"] = "locked_bundle"
    doc["assembly"] = {"bundle": {"bundle_id": "locked", "required_assets": [a["asset_id"] for a in doc["assets"]]}}
    plan = compile_coverage(registry, template, reports, "test")
    assert len(plan["review_selection"]["outfits"][1]["family_asset_ids"]) == 3


def test_unknown_accessory_policy_is_not_assumed_compatible():
    registry, template, reports = data()
    group = registry["families"][0]["document"]["assembly"]["groups"][0]
    group["optional_assets"] = ["male_shirt"]
    group["optional_asset_policy"] = "unknown"
    with pytest.raises(ValueError, match="Unknown optional"):
        compile_coverage(registry, template, reports, "test")


def test_shared_shoe_pool_gets_witnesses_without_native_shoe_mix():
    registry, template, reports = data()
    doc = registry["families"][0]["document"]
    doc["assets"] = [a for a in doc["assets"] if a["slot"] != "shoes"]
    group = doc["assembly"]["groups"][0]
    group["required_slots"].remove("shoes")
    group["slot_pools"].pop("shoes")
    registry["asset_bindings"] = [b for b in registry["asset_bindings"] if b["asset_id"] != "male_shoes"]
    reports[0]["cases"] = [c for c in reports[0]["cases"] if c["case_id"] != "male_shoes"]
    doc["footwear_policy"] = {"mode": "shared_pool", "allowed_shared_shoe_ids": ["M001", "M002"], "allow_barefoot": True}
    for aid in ("M001", "M002"):
        registry["units"].append({"unit_id": aid, "bodyfit_id": "M02_Average"})
        registry["asset_bindings"].append({"family_id": "male.SharedFootwear", "asset_id": aid, "unit_id": aid, "module_key": aid})
        reports[0]["cases"].append({"case_id": aid, "transfer_passed": True, "modules": [
            {"module_key": aid, "slot": "shoes", "mesh_paths": [f"/Game/{aid}"], "mesh_names": [aid]}]})
    plan = compile_coverage(registry, template, reports, "test")
    male = [c for c in plan["review_selection"]["outfits"] if c["bodyfit_id"] == "M02_Average"]
    assert len(male) == 2
    assert {c["shared_shoe_ids"][0] for c in male} == {"M001", "M002"}
    assert all("male_shoes" not in c["family_asset_ids"] for c in male)


def test_assembly_summary_rejects_stale_and_missing_evidence(tmp_path):
    from run_wardrobe_coverage_review_v1 import summarize
    from modular_outfit_runtime_plan_v2 import write_json
    plan = compile_coverage(*data(), "test")
    path = tmp_path / "review_plan.json"
    write_json(path, plan)
    result = summarize(path)
    assert not result["assembly_checks_complete"]
    assert result["covered_meshes"] == 0
    write_json(tmp_path / "assembly/checks_001_002.json", {"plan_sha256": "stale", "rows": []})
    with pytest.raises(ValueError, match="Stale assembly"):
        summarize(path)
