import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cc_revise_wardrobe_bundle_v1 import aggregate, prepare, revise_documents
from cc_prepare_wardrobe_repair_v1 import read, record, write_new
from cc_build_wardrobe_library_v1 import unit_key


@pytest.fixture
def library(tmp_path):
    source = tmp_path / "v2"
    assets = tmp_path / "assets"
    exports = tmp_path / "exports"
    assets.mkdir()
    exports.mkdir()
    modules = []
    for name in ("2", "3", "4"):
        path = assets / (name + ".ccCloth")
        path.write_bytes(name.encode())
        modules.append({**record(path), "asset_id": name, "source_path": str(path),
                        "slot": "full_body", "module_key": name, "cloth_options_policy": "fit_body_shape"})
    old = unit_key("female", modules, True)
    unit = {"unit_id": old, "sex": "female", "locked_bundle": True, "modules": modules,
            "relative_directory": "Female/Average/Bundle/" + old, "ue_case_root": "/Game/" + old}
    contract = {"family_id": "female.elise", "sex": "female", "assembly_mode": "locked_bundle",
                "assets": [dict(m, path=Path(m["path"]).name) for m in modules],
                "assembly": {"bundle": {"required_assets": ["2", "3", "4"]}}, "traceability": {}}
    write_new(assets / "outfit_family.json", contract)
    registry = {"units": [unit], "families": [{"document": contract, "manifest": record(assets / "outfit_family.json")}],
                "asset_bindings": [{"asset_id": m["asset_id"], "unit_id": old} for m in modules],
                "counts": {"source_bindings": 3, "unique_modules": 3}}
    preset = {"preset_id": old, "case_id": old, "look_id": old, "output_directory_name": old,
              "selected_assets": modules, "production_output": {
                  "project_path": str(exports / old / (old + ".ccProject")),
                  "export_root": str(exports / old / "fbx"), "export_basename": old}}
    cc = {"presets": [{"preset_id": "good"}, preset], "output_root": str(exports), "counts": {"case_count": 2}}
    ue = {"cases": [{"case_id": old, "modules": modules, "ue_case_root": "/Game/" + old,
                     "planned_export": {"root": str(exports / old / "fbx")}}], "families": registry["families"]}
    approval = {"revision_id": "v3", "approved_by": "user", "approval": "keep4", "family_id": "female.elise",
                "batch": "batch_057", "old_unit_id": old, "exclude_asset_id": "2", "retain_asset_id": "4",
                "exclude_sha256": modules[0]["sha256"], "retain_sha256": modules[2]["sha256"]}
    for name, value in (("wardrobe_registry.json", registry), ("cc_export.json", cc), ("ue_import.json", ue)):
        write_new(source / name, value)
    write_new(source / "batch_057/cc_export.json", cc)
    write_new(source / "batch_057/ue_pending.json", ue)
    write_new(source / "batch_001/ue_import.json", {"preserve": True})
    results = []
    for uid, success in (("good", True), (old, False)):
        path = tmp_path / (uid + ".json")
        write_new(path, {"case_id": uid, "success": success})
        results.append({"case_id": uid, "success": success, "result_path": str(path)})
    write_new(tmp_path / "previous.json", {"results": results, "finished_at": "old", "success": False})
    write_new(tmp_path / "approval.json", approval)
    return {"source": source, "destination": tmp_path / "v3", "approval": tmp_path / "approval.json",
            "previous_result": tmp_path / "previous.json", "retry_output": tmp_path / "retry.json"}


def test_revision_excludes_only_approved_alternative_and_keeps_input(library):
    source = library["source"]
    before = {str(p): p.read_bytes() for p in source.rglob("*.json")}
    output = prepare(**library)
    assert all(Path(p).read_bytes() == value for p, value in before.items())
    new = output["new_case_id"]
    revised = read(library["destination"] / "wardrobe_registry.json")
    assert [m["asset_id"] for m in revised["units"][0]["modules"]] == ["3", "4"]
    assert revised["counts"]["unique_modules"] == revised["counts"]["source_bindings"] == 2
    assert new != read(library["approval"])["old_unit_id"]
    retry = read(library["retry_output"])
    assert [p["preset_id"] for p in retry["presets"]] == [new]
    assert read(library["destination"] / "cc_export.json")["presets"][0] == {"preset_id": "good"}
    assert (library["destination"] / "batch_001/ue_import.json").read_bytes() == (source / "batch_001/ue_import.json").read_bytes()
    assert all(Path(a["path"]).exists() for a in revised["families"][0]["document"]["assets"])
    assert (source.parent / "assets/2.ccCloth").exists()
    with pytest.raises(FileExistsError):
        prepare(**library)


@pytest.mark.parametrize("change", ["approval", "hash", "locked", "manifest"])
def test_rejects_unapproved_or_inconsistent_sources(library, change):
    source = library["source"]
    reg, cc, ue = [read(source / name) for name in ("wardrobe_registry.json", "cc_export.json", "ue_import.json")]
    approval = read(library["approval"])
    if change == "approval":
        approval["approved_by"] = "automatic"
    elif change == "hash":
        approval["retain_sha256"] = "wrong"
    elif change == "locked":
        reg["units"][0]["locked_bundle"] = False
    else:
        cc["presets"][1]["selected_assets"] = []
    with pytest.raises(ValueError):
        revise_documents(reg, cc, ue, approval)


def retry_summary(library, new, success=True):
    root = library["source"].parent
    path = root / "new-case.json"
    write_new(path, {"case_id": new, "success": success})
    summary = root / "retry-result.json"
    write_new(summary, {"success": success, "success_count": int(success), "failure_count": int(not success),
                        "finished_at": "new", "results": [{"case_id": new, "success": success, "result_path": str(path)}]})
    return summary


def test_aggregate_reuses_success_and_records_new_case(library):
    plan = prepare(**library)
    previous = read(library["previous_result"])
    path = library["destination"] / "aggregate.json"
    aggregate(library["destination"] / "revision.json", retry_summary(library, plan["new_case_id"]), path)
    result = read(path)
    assert result["results"][0] == previous["results"][0]
    assert result["results"][1]["case_id"] == plan["new_case_id"]
    assert result["success"] and result["success_count"] == 2
    assert "approved_bundle_revision" in result["evidence_kind"]
    assert read(library["previous_result"]) == previous


@pytest.mark.parametrize("target", ["original", "retry_workorder", "failed"])
def test_aggregate_requires_unchanged_inputs_and_success(library, target):
    plan = prepare(**library)
    retry = retry_summary(library, plan["new_case_id"], success=target != "failed")
    if target != "failed":
        path = library["previous_result"] if target == "original" else library["retry_output"]
        path.write_text(path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        aggregate(library["destination"] / "revision.json", retry, library["destination"] / "aggregate.json")
