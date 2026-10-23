"""Evidence-level checks for the isolated complete-character review catalog."""

import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import complete_character_review_contract_v1 as contract
import formal_wardrobe_registry_v1 as formal


@pytest.fixture(scope="module")
def data():
    return contract.catalog()


def test_all_accepted_outfits_preserve_coverage_and_sex(data):
    registry = formal.read_registry(formal.MATERIAL_REPAIR_REGISTRY)
    plan = json.loads(contract.SOURCE_PLAN.read_text(encoding="utf-8-sig"))
    all_meshes = set()
    for sex, count in (("female", 95), ("male", 78)):
        outfits = data[f"{sex}_outfits"]
        assert [row["index"] for row in outfits] == list(range(1, count + 1))
        for outfit in outfits:
            result = formal.resolve_selection(registry, character_sex=sex, **outfit["choice"])
            assert result == outfit["resolved"]
            assert result["character_sex"] == sex
            paths = [row["mesh_path"] for row in result["assignments"]]
            assert len(paths) == len(set(paths))
            all_meshes.update(paths)
            assert outfit["label"].isascii()
    assert all_meshes == set(plan["coverage"]["mesh_witnesses"])
    assert len(all_meshes) == 346


def test_hair_blocking_uses_formal_selection_policy(data):
    registry = formal.read_registry(formal.MATERIAL_REPAIR_REGISTRY)
    for sex in ("female", "male"):
        allowed_hair = next(hair for hair in data["hairs"] if hair["sex"] in (sex, "both"))
        states = set()
        for row in data[f"{sex}_outfits"]:
            result = formal.resolve_selection(registry, character_sex=sex,
                                              hair_id=allowed_hair["hair_id"], **row["choice"])
            assert row["hair_deny"] == (result["hair_reason"] == "deny_all")
            states.add(row["hair_deny"])
        assert states == {True, False}
    assert len(data["hairs"]) == 40
    assert all(set(hair["fit_variants"]) == {"female", "male"} for hair in data["hairs"])


def test_provenance_hashes_and_actions_are_bound_to_reports(data):
    sources = data["sources"]
    evidence = [sources[key] for key in ("registry", "source_plan", "standard_candidate_registry", "current_action_registry",
                                       "current_action_graph", "current_action_pool")]
    evidence += list(sources["action_reports"].values())
    for source in evidence:
        assert hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() == source["sha256"]
    for sex in ("female", "male"):
        actions = data["actions_by_sex"][sex]
        assert [row["index"] for row in actions] == [1, 2, 3, 4, 5]
        assert len({row["path"] for row in actions}) == 5
        for row, action_id in zip(actions, contract.ACTION_IDS[sex]):
            report = json.loads(Path(sources["action_reports"][action_id]["path"]).read_text(encoding="utf-8-sig"))
            assert row["path"] == report["source"]
            assert row["source_skeleton"] == report["source_skeleton"]
            assert Path(row["asset_file_path"]).is_file()
            assert Path(row["import_fbx_path"]).stem == row["expected_basename"]
            assert hashlib.sha256(Path(row["import_fbx_path"]).read_bytes()).hexdigest() == row["import_fbx_sha256"]


def test_actions_match_current_authority_and_exclude_retired_packages(data):
    graph = json.loads(contract.CURRENT_ACTION_GRAPH.read_text(encoding="utf-8-sig"))
    pool = json.loads(contract.CURRENT_ACTION_POOL.read_text(encoding="utf-8-sig"))
    retired = {row["action_id"] for row in pool["excluded_actions"]}
    assert retired == {"ACT_F04_AUDIENCE_09", "ACT_M03_AUDIENCE_12"}
    for sex in ("female", "male"):
        ids = {row["action_id"] for row in data["actions_by_sex"][sex]}
        assert ids == {value.upper() for value in graph["actions_by_sex"][sex]}
        assert ids == set(pool["active_actions"][sex])
        assert not ids & retired
    current = json.loads(contract.CURRENT_ACTION_REGISTRY.read_text(encoding="utf-8-sig"))
    assert current["historical_import_receipts_recovered"] is False
    assert not {row["action_id"] for row in current["records"]} & retired


def test_each_catalog_call_rereads_preserved_historical_registry(monkeypatch):
    called = []
    original_read = formal.read_registry
    def read(path=None):
        called.append(path)
        return original_read(path)
    monkeypatch.setattr(formal, "read_registry", read)
    contract.catalog()
    contract.catalog()
    assert called == [formal.MATERIAL_REPAIR_REGISTRY, formal.MATERIAL_REPAIR_REGISTRY]


def test_migrated_registry_rejects_tampered_package_hash(monkeypatch, tmp_path):
    registry = json.loads(contract.CURRENT_ACTION_REGISTRY.read_text(encoding="utf-8-sig"))
    registry["records"][0]["asset_sha256"] = "0" * 64
    replacement = tmp_path / "catalog.json"
    replacement.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(contract, "CURRENT_ACTION_REGISTRY", replacement)
    with pytest.raises(ValueError, match="differs from retained source"):
        contract.current_actions({})
