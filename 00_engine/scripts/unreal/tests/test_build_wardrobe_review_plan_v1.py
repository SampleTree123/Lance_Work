import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_wardrobe_review_plan_v1 import compile_review


def fixture():
    registry = {"library_id": "test", "families": [], "units": [], "asset_bindings": []}
    template = {"bodyfits": []}
    selection = {"review_id": "test", "outfits": []}
    report = {"success": True, "cases": []}
    for sex, bodyfit in [("male", "M02_Average"), ("female", "F02_Average")]:
        family_id = f"{sex}.test"
        ids = [f"{sex}_shirt", f"{sex}_pants", f"{sex}_shoes"]
        slots = ["shirts", "pants", "shoes"]
        doc = {"family_id": family_id, "sex": sex, "assembly_mode": "slot_groups",
               "assets": [{"asset_id": aid, "slot": s} for aid, s in zip(ids, slots)],
               "assembly": {"groups": [{"group_id": "default", "required_slots": slots,
                            "slot_pools": {s: [aid] for s, aid in zip(slots, ids)}}]},
               "footwear_policy": {"mode": "native_pool"}}
        registry["families"].append({"document": doc})
        template["bodyfits"].append({"bodyfit_id": bodyfit, "sex": sex})
        selection["outfits"].append({"bodyfit_id": bodyfit, "family_id": family_id,
                                     "family_asset_ids": ids, "group_id": "default",
                                     "variant_id": "first", "shared_shoe_ids": []})
        for aid, slot in zip(ids, slots):
            registry["units"].append({"unit_id": aid, "bodyfit_id": bodyfit})
            registry["asset_bindings"].append({"family_id": family_id, "asset_id": aid,
                                               "unit_id": aid, "module_key": aid})
            report["cases"].append({"case_id": aid, "transfer_passed": True, "modules": [
                {"module_key": aid, "slot": slot, "mesh_paths": [f"/Game/{aid}"],
                 "mesh_names": [aid]}]})
    return registry, template, selection, [report]


def test_assigns_existing_fixed_slots_without_promoting_fit():
    plan = compile_review(*fixture())
    assert plan["candidate_mesh_count"] == 6
    assert plan["runtime_variant_count"] == 2
    assert not plan["runtime_approved"]
    assert plan["bodyfits"][0]["runtime_variants"][0]["expected_target_component_names"] == [
        "UpperInner", "Bottom", "Footwear"]


@pytest.mark.parametrize("failure", ["missing_pants", "unapproved_shoe", "wrong_bodyfit",
                                    "failed_transfer", "duplicate_report", "missing_module"])
def test_rejects_invalid_or_incomplete_combinations(failure):
    registry, template, selection, reports = copy.deepcopy(fixture())
    if failure == "missing_pants":
        selection["outfits"][0]["family_asset_ids"].remove("male_pants")
    elif failure == "unapproved_shoe":
        selection["outfits"][0]["shared_shoe_ids"] = ["M999"]
    elif failure == "wrong_bodyfit":
        registry["units"][0]["bodyfit_id"] = "F02_Average"
    elif failure == "failed_transfer":
        reports[0]["cases"][0]["transfer_passed"] = False
    elif failure == "duplicate_report":
        reports.append(copy.deepcopy(reports[0]))
    else:
        reports[0]["cases"].pop(0)
    with pytest.raises((ValueError, RuntimeError, KeyError)):
        compile_review(registry, template, selection, reports)
