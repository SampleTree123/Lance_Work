import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cc_prepare_wardrobe_repair_v1 import aggregate, prepare


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.fixture
def batch(tmp_path):
    boundary = tmp_path / "exports"
    boundary.mkdir()
    presets, results = [], []
    for uid, success in (("good", True), ("bad", False)):
        folder = boundary / uid
        folder.mkdir()
        project = folder / "avatar.ccProject"
        project.write_bytes(b"preserve")
        presets.append({"preset_id": uid, "selected_assets": [{"sha256": "frozen"}],
                        "production_output": {"project_path": str(project),
                                              "export_root": str(folder / "fbx")}})
        result = save(tmp_path / (uid + ".json"), {"case_id": uid, "success": success})
        results.append({"case_id": uid, "success": success, "result_path": str(result)})
    source = save(tmp_path / "source.json", {"presets": presets, "counts": {"case_count": 2}})
    summary = save(tmp_path / "old.json", {"results": results, "success": False,
                                           "success_count": 1, "failure_count": 1,
                                           "started_at": "old-start", "finished_at": "old-end"})
    repair = tmp_path / "repair.json"
    return source, summary, repair, boundary


def test_prepare_only_failed_keeps_paths_and_originals(batch):
    source, summary, repair, boundary = batch
    original_source, original_result = source.read_bytes(), summary.read_bytes()
    plan = prepare(source, summary, repair, boundary)
    value = json.loads(repair.read_text())
    assert value["presets"] == [json.loads(original_source)["presets"][1]]
    assert plan["successful_case_ids_not_reexported"] == ["good"]
    assert plan["retry_case_ids"] == ["bad"]
    assert source.read_bytes() == original_source and summary.read_bytes() == original_result
    assert (boundary / "bad/avatar.ccProject").read_bytes() == b"preserve"
    assert not (boundary / "bad/fbx").exists()
    with pytest.raises(FileExistsError):
        prepare(source, summary, repair, boundary)


def retry_report(tmp_path):
    case = save(tmp_path / "retry-case.json", {"case_id": "bad", "success": True})
    return save(tmp_path / "retry.json", {"results": [{"case_id": "bad", "success": True, "result_path": str(case)}],
                                          "success": True, "success_count": 1, "failure_count": 0,
                                          "finished_at": "new-end"})


def test_aggregate_preserves_old_success_and_identifies_aggregate(batch, tmp_path):
    source, summary, repair, boundary = batch
    prepare(source, summary, repair, boundary)
    original = summary.read_bytes()
    output = tmp_path / "aggregate.json"
    aggregate(repair, retry_report(tmp_path), output)
    result = json.loads(output.read_text())
    assert result["success_count"] == 2 and result["failure_count"] == 0
    assert result["results"][0] == json.loads(original)["results"][0]
    assert "aggregate" in result["evidence_kind"]
    assert result["summary_path"] == str(output.resolve())
    assert summary.read_bytes() == original
    with pytest.raises(FileExistsError):
        aggregate(repair, tmp_path / "retry.json", output)


@pytest.mark.parametrize("target", ["source", "summary", "case", "repair"])
def test_aggregate_rejects_changed_evidence_or_frozen_cases(batch, tmp_path, target):
    source, summary, repair, boundary = batch
    prepare(source, summary, repair, boundary)
    if target == "repair":
        value = json.loads(repair.read_text())
        value["presets"][0]["selected_assets"][0]["sha256"] = "different"
        save(repair, value)
    else:
        path = {"source": source, "summary": summary, "case": tmp_path / "good.json"}[target]
        path.write_text(path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        aggregate(repair, retry_report(tmp_path), tmp_path / "aggregate.json")


def test_rejects_escaping_export_path(batch, tmp_path):
    source, summary, repair, boundary = batch
    value = json.loads(source.read_text())
    value["presets"][1]["production_output"]["export_root"] = str(tmp_path / "elsewhere")
    save(source, value)
    with pytest.raises(ValueError, match="boundary"):
        prepare(source, summary, repair, boundary)


@pytest.mark.parametrize("mode", ["extra", "failure", "unfinished"])
def test_rejects_incomplete_or_extraneous_retry(batch, tmp_path, mode):
    source, summary, repair, boundary = batch
    prepare(source, summary, repair, boundary)
    retry = retry_report(tmp_path)
    value = json.loads(retry.read_text())
    if mode == "extra":
        value["results"].append({"case_id": "good", "success": True})
    elif mode == "failure":
        value["success"] = False
    else:
        value["finished_at"] = None
    save(retry, value)
    with pytest.raises(ValueError):
        aggregate(repair, retry, tmp_path / "aggregate.json")
