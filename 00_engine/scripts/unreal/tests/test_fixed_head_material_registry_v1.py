"""Bounded material publication checks: exact edits and independent hash gate."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formal_wardrobe_registry_v1 as formal
from build_fixed_head_material_registry_v1 import EXPECTED_IDS, TARGET_PREFIX, build_registry


def test_material_publication_edits_only_reported_slots():
    source = formal.read_registry(formal.DUAL_FIT_REGISTRY)
    original = deepcopy(source)
    groups = []
    for hair in source["hair_assets"]:
        if hair["hair_id"] not in EXPECTED_IDS:
            continue
        rows = []
        for sex, fit in hair["fit_variants"].items():
            for mesh in fit["meshes"]:
                for index, before in enumerate(mesh["materials"]):
                    rows.append({"mesh": mesh["path"], "slot_index": index,
                                 "hair_id": hair["hair_id"], "sex": sex, "before": before,
                                 "material": TARGET_PREFIX + hair["hair_id"] + f"_{sex}_{len(rows)}.MI_Repair"})
        groups.append(rows)
    # Synthetic successful report exercises the contract, without altering UE.
    rows = [group.pop(0) for group in groups]
    rows += [row for group in groups for row in group][:19]
    hair_report = {"success": True, "mode": "apply", "records": rows}
    skin_report = {"success": True, "mode": "apply", "changed_slots": [
        {"sex": "female", "mesh": "/Game/Female"}, {"sex": "male", "mesh": "/Game/Male"}]}
    result = build_registry(source, hair_report, skin_report)
    for hair in result["hair_assets"]:
        for fit in hair["fit_variants"].values():
            for mesh in fit["meshes"]:
                for row in rows:
                    if mesh["path"] == row["mesh"]:
                        assert mesh["materials"][row["slot_index"]] == row["material"]
                        mesh["materials"][row["slot_index"]] = row["before"]
    assert result == original == source
    hair_report["records"][-1] = deepcopy(rows[0])
    with pytest.raises(ValueError, match="Duplicate"):
        build_registry(source, hair_report, skin_report)


def test_material_hash_gate_never_falls_back_to_single_fit_on_bad_repair(tmp_path, monkeypatch):
    source = formal.DUAL_FIT_REGISTRY
    assert formal.historical_registry_path() in {source, formal.MATERIAL_REPAIR_REGISTRY}
    candidate = tmp_path / "materials.json"
    receipt_path = tmp_path / "publication.json"
    monkeypatch.setattr(formal, "MATERIAL_REPAIR_REGISTRY", candidate)
    monkeypatch.setattr(formal, "MATERIAL_REPAIR_PUBLICATION", receipt_path)
    candidate.write_bytes(source.read_bytes())
    assert formal.historical_registry_path() == source
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = {"batch_id": "fixed_head_material_repair_20261005_v1", "success": True,
               "source_registry": str(source), "source_registry_sha256": digest(source),
               "output_registry": str(candidate), "output_registry_sha256": digest(candidate),
               "counts": {"hairstyles": 40, "fits": 80, "hair_material_slots": 24},
               "families_meshes_and_usage_permissions_preserved": True}
    for key in ("hair_apply_report", "skin_apply_report"):
        p = tmp_path / (key + ".json")
        p.write_text(json.dumps({"success": True, "mode": "apply"}), encoding="utf-8")
        receipt[key] = str(p)
        receipt[key + "_sha256"] = digest(p)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert formal.historical_registry_path() == candidate
    Path(receipt["skin_apply_report"]).write_text('{"success":false}', encoding="utf-8")
    assert formal.historical_registry_path() == source
