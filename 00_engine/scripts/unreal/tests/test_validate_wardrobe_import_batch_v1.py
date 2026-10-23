import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_wardrobe_import_batch_v1 import PHASES, validate_case


def fixture():
    case = {"case_id": "M_SHIRT", "sex": "male", "bodyfit_id": "M02_Average",
            "modules": [{"module_key": "shirt", "slot": "shirts",
                         "cc_scene_objects": [{"name": "Shirt"}]}]}
    reports = {p: {"success": True, "mode": p, "case_id": "M_SHIRT"} for p in PHASES}
    garment = {"class": "SkeletalMesh", "name": "Shirt", "path": "/Game/Shirt",
               "skeleton": "/Game/BaseSkeleton", "physics_asset": None,
               "lod0_vertices": 100}
    body = {**garment, "name": "CC_Base_Body", "path": "/Game/Body"}
    reports["validate_case"].update(base_skeleton="/Game/BaseSkeleton",
                                    split_assets=[garment, body])
    return case, reports


def test_maps_only_apparel_and_does_not_approve_fit():
    result = validate_case(*fixture())
    assert result["classified_mesh_count"] == 1
    assert result["ignored_split_mesh_count"] == 1
    assert result["fit_review"] == "pending"
    assert not result["runtime_approved"]


@pytest.mark.parametrize("field,value", [("skeleton", "/Game/Wrong"),
                                         ("physics_asset", "/Game/Physics"),
                                         ("lod0_vertices", 0)])
def test_rejects_bad_garment(field, value):
    case, reports = fixture()
    reports["validate_case"]["split_assets"][0][field] = value
    with pytest.raises(ValueError):
        validate_case(case, reports)


def test_rejects_failed_or_wrong_report():
    case, reports = fixture()
    for phase in PHASES:
        bad = copy.deepcopy(reports)
        bad[phase]["success"] = False
        with pytest.raises(ValueError):
            validate_case(case, bad)
        bad[phase]["success"] = True
        bad[phase]["case_id"] = "F_OTHER"
        with pytest.raises(ValueError):
            validate_case(case, bad)
