"""Check the visual queue uses the intended sex-filtered formal registry pool."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("hair_fit_review", ROOT / "build_hair_sex_fit_review_v1.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_both_sexes_are_reviewed_separately_and_excluded_hair_stays_out():
    registry = {"hair_assets": [
        {"hair_id": f"HAIR_BOTH_{i}", "display_name": "Both", "sex": "both", "meshes": [{"path": f"/Game/H{i}.H{i}"}]}
        for i in range(11)
    ] + [
        {"hair_id": f"HAIR_F_{i}", "display_name": "Female", "sex": "female", "meshes": [{"path": f"/Game/F{i}.F{i}"}]}
        for i in range(19)
    ] + [
        {"hair_id": f"HAIR_M_{i}", "display_name": "Male", "sex": "male", "meshes": [{"path": f"/Game/M{i}.M{i}"}]}
        for i in range(10)
    ]}
    plan = MODULE.build_plan(registry, "digest")
    assert plan["counts"] == {"total": 51, "female": 30, "male": 21}
    assert len({(case["sex"], case["hair_id"]) for case in plan["cases"]}) == 51
    assert all(case["bodyfit_id"] == ("F02_Average" if case["sex"] == "female" else "M02_Average")
               for case in plan["cases"])
    assert all(case["visual_decision"] == "pending" for case in plan["cases"])


def test_historical_single_fit_queue_stays_bound_to_its_original_geometry():
    from formal_wardrobe_registry_v1 import LEGACY_REGISTRY, read_registry
    import hashlib
    registry = read_registry(LEGACY_REGISTRY)
    plan = MODULE.build_plan(registry, hashlib.sha256(LEGACY_REGISTRY.read_bytes()).hexdigest())
    assert plan["source_registry"] == str(LEGACY_REGISTRY)
    assert plan["counts"] == {"total": 51, "female": 30, "male": 21}
    assert all(case["mesh_paths"] for case in plan["cases"])
