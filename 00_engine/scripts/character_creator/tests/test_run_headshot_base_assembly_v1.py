"""Controller recovery and immutable-source protections without touching CC."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import run_headshot_base_assembly_v1 as controller


@pytest.fixture
def work(tmp_path, monkeypatch):
    source = tmp_path / "ORIGINAL.ccProject"
    source.write_bytes(b"fixed identity and scalp")
    regions = tmp_path / "regions.json"
    regions.write_text("{}")
    asset = tmp_path / "asset.ccEye"
    asset.write_bytes(b"approved material")
    registry = tmp_path / "registry.json"
    registry.write_text("{}")
    quality = tmp_path / "quality.json"
    quality.write_text("{}")
    request = {"character_id": "PHOTO_01", "sex": "female", "seed": 42,
               "source_project": str(source), "source_sha256": controller.sha(source),
               "regions_path": str(regions)}

    def compiler(request):
        return {"character_id": request["character_id"], "seed": request["seed"],
                "source_project": request["source_project"],
                "source_sha256": controller.sha(request["source_project"]),
                "output_project": request["output_project"],
                "regions_path": str(regions), "regions_sha256": controller.sha(regions),
                "assets": [{"asset_id": "EYES01", **controller.bind(asset)}],
                "registry": controller.bind(registry),
                "face_material_quality_profile": controller.bind(quality)}

    monkeypatch.setattr(controller, "compile_base_assembly", compiler)
    return {"request": request, "source": source, "root": tmp_path / "run",
            "stage": tmp_path / "staging", "bridge": tmp_path / "bridge"}


def prepare(work):
    return controller.prepare(work["request"], run_root=work["root"], stage_root=work["stage"])


def terminal_success(work, state):
    manifest = controller.read(state["manifest"]["path"])
    output = Path(manifest["output_project"])
    output.write_bytes(b"assembled independent character")
    report = {"success": True, "source_unchanged": True, "config": manifest,
              "saved_project": controller.bind(output)}
    controller.write(Path(state["output_dir"]) / "assembly_report.json", report)
    controller.write(Path(state["output_dir"]) / "assembly_geometry_invariants.json",
                     {"passed": True, "steps": [{"passed": True}]})
    result_path = work["bridge"] / "results" / (state["job_id"] + ".json")
    controller.write(result_path, {"job_id": state["job_id"], "status": "succeeded"})
    return result_path


def test_prepare_copies_original_without_changing_or_overwriting_it(work):
    original_bytes = work["source"].read_bytes()
    state = prepare(work)
    assert state["status"] == "prepared"
    assert work["source"].read_bytes() == original_bytes
    assert Path(state["working_copy"]["path"]).read_bytes() == original_bytes
    assert Path(state["working_copy"]["path"]).is_relative_to(work["stage"])
    manifest = controller.read(state["manifest"]["path"])
    assert Path(manifest["output_project"]).is_relative_to(work["root"])
    assert not Path(manifest["output_project"]).exists()
    assert manifest["input_lineage"]["original_sha256"] == state["working_copy"]["sha256"]
    assert prepare(work)["job_id"] == state["job_id"]


def test_pending_unknown_never_calls_bridge_or_duplicates_submission(work):
    state = prepare(work)
    state["status"] = "pending"
    controller.write(state["state_path"], state)
    calls = []
    result = controller.execute(prepare(work), bridge_root=work["bridge"],
                                client_call=lambda args: calls.append(args), wait_seconds=0)
    assert result["status"] == "pending"
    assert result["job_id"] == state["job_id"]
    assert calls == []


def test_preexisting_queue_of_same_job_is_observed_not_resubmitted(work):
    state = prepare(work)
    controller.write(work["bridge"] / "inbox" / (state["job_id"] + ".json"), {})
    calls = []
    result = controller.execute(state, bridge_root=work["bridge"],
                                client_call=lambda args: calls.append(args), wait_seconds=0)
    assert result["status"] == "pending"
    assert calls == []


def test_submit_once_persists_pending_before_cli_and_then_resumes_same_job(work):
    state = prepare(work)
    calls = []

    def client(args):
        calls.append(args)
        if args == ["health"]:
            return {"healthy": True, "heartbeat": {"active_job_id": None}}
        assert controller.read(state["state_path"])["status"] == "pending"
        return {"job_id": state["job_id"]}

    first = controller.execute(state, bridge_root=work["bridge"], client_call=client, wait_seconds=0)
    second = controller.execute(prepare(work), bridge_root=work["bridge"], client_call=client, wait_seconds=0)
    assert first["job_id"] == second["job_id"]
    assert len(calls) == 2
    assert "--no-wait" in calls[1]
    assert "--confirm-scene-replace" in calls[1]


def test_pending_existing_result_is_read_before_any_bridge_call(work):
    state = prepare(work)
    state["status"] = "pending"
    controller.write(state["state_path"], state)
    terminal_success(work, state)
    completed = controller.execute(state, bridge_root=work["bridge"],
                                    client_call=lambda args: pytest.fail("must only read result"), wait_seconds=0)
    assert completed["status"] == "completed"
    assert prepare(work)["status"] == "completed"


@pytest.mark.parametrize("field", ["original", "working_copy", "manifest", "library", "saved_project", "geometry_report", "assembly_report", "bridge_result"])
def test_completed_hash_drift_cannot_be_skipped(work, field):
    state = prepare(work)
    terminal_success(work, state)
    completed = controller.execute(state, bridge_root=work["bridge"], wait_seconds=0)
    changed = Path(completed[field]["path"])
    changed.write_bytes(changed.read_bytes() + b"drift")
    with pytest.raises(controller.ControllerError, match="SHA"):
        prepare(work)


def test_false_geometry_receipt_prevents_completion(work):
    state = prepare(work)
    terminal_success(work, state)
    controller.write(Path(state["output_dir"]) / "assembly_geometry_invariants.json",
                     {"passed": False, "steps": [{"passed": False}]})
    with pytest.raises(controller.ControllerError, match="receipts"):
        controller.execute(state, bridge_root=work["bridge"], wait_seconds=0)
    assert controller.read(state["state_path"])["status"] == "prepared"


def test_failed_attempt_gets_new_job_and_fresh_source_without_overwriting_failure(work):
    state = prepare(work)
    result_path = work["bridge"] / "results" / (state["job_id"] + ".json")
    controller.write(result_path, {"job_id": state["job_id"], "status": "failed", "error": {"message": "load failed"}})
    failed = controller.execute(state, bridge_root=work["bridge"], wait_seconds=0)
    old_state = Path(failed["state_path"]).read_bytes()
    new = prepare(work)
    assert failed["status"] == "failed"
    assert new["attempt_id"] == "attempt_002"
    assert new["job_id"] != failed["job_id"]
    assert new["working_copy"]["path"] != failed["working_copy"]["path"]
    assert Path(new["working_copy"]["path"]).read_bytes() == work["source"].read_bytes()
    assert Path(failed["state_path"]).read_bytes() == old_state


def test_uncertain_submission_remains_pending_and_is_not_resent(work):
    state = prepare(work)

    def client(args):
        if args == ["health"]:
            return {"healthy": True, "heartbeat": {}}
        raise TimeoutError("could have queued already")

    with pytest.raises(controller.ControllerError, match="uncertain"):
        controller.execute(state, bridge_root=work["bridge"], client_call=client, wait_seconds=0)
    resumed = prepare(work)
    assert resumed["status"] == "pending"
    controller.execute(resumed, bridge_root=work["bridge"],
                       client_call=lambda args: pytest.fail("must not resubmit"), wait_seconds=0)


def test_other_active_or_queued_job_blocks_submission(work):
    state = prepare(work)
    with pytest.raises(controller.ControllerError, match="active"):
        controller.execute(state, bridge_root=work["bridge"],
            client_call=lambda args: {"healthy": True, "heartbeat": {"active_job_id": "other_job"}}, wait_seconds=0)
    controller.write(work["bridge"] / "inbox" / "other_job.json", {})
    with pytest.raises(controller.ControllerError, match="queued"):
        controller.execute(state, bridge_root=work["bridge"],
            client_call=lambda args: {"healthy": True, "heartbeat": {}}, wait_seconds=0)


def test_changed_request_requires_distinct_character_identifier(work):
    prepare(work)
    work["request"]["seed"] += 1
    with pytest.raises(controller.ControllerError, match="request differs"):
        prepare(work)


@pytest.mark.parametrize("character_id", ["../escape", "a/b", "", "x" * 65])
def test_invalid_character_id_cannot_escape_run(work, character_id):
    work["request"]["character_id"] = character_id
    with pytest.raises(controller.ControllerError):
        prepare(work)


def test_declared_external_output_is_rejected(work):
    work["request"]["output_project"] = str(work["source"].parent / "unsafe.ccProject")
    with pytest.raises(controller.ControllerError, match="pinned"):
        prepare(work)


def test_prepare_default_cli_never_operates_cc(work, monkeypatch, tmp_path):
    monkeypatch.setattr(controller, "RUN_ROOT", work["root"])
    original_prepare = controller.prepare
    monkeypatch.setattr(controller, "prepare", lambda r: original_prepare(r, run_root=work["root"], stage_root=work["stage"]))
    monkeypatch.setattr(controller, "execute", lambda *a, **k: pytest.fail("default must not execute"))
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(work["request"]))
    assert controller.main(["--request", str(request_path)]) == 0
    assert not (work["root"] / "controller.lock").exists()


def test_compile_failure_is_retained_and_retry_uses_new_attempt(work, monkeypatch):
    actual = controller.compile_base_assembly
    monkeypatch.setattr(controller, "compile_base_assembly", lambda request: (_ for _ in ()).throw(ValueError("registry failure")))
    with pytest.raises(ValueError, match="registry failure"):
        prepare(work)
    failed_path = work["root"] / "PHOTO_01" / "attempt_001" / "controller_state.json"
    failed_bytes = failed_path.read_bytes()
    assert controller.read(failed_path)["status"] == "failed"
    monkeypatch.setattr(controller, "compile_base_assembly", actual)
    new = prepare(work)
    assert new["attempt_id"] == "attempt_002"
    assert failed_path.read_bytes() == failed_bytes


def test_batch_execution_stops_at_pending_instead_of_submitting_next_character(work, monkeypatch, tmp_path):
    monkeypatch.setattr(controller, "RUN_ROOT", work["root"])
    requests = [dict(work["request"], character_id="ONE"), dict(work["request"], character_id="TWO")]
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(requests))
    calls = []
    def prepare_only(request):
        calls.append(request["character_id"])
        return {"character_id": request["character_id"], "attempt_id": "attempt_001",
                "job_id": "same_pending_job", "status": "prepared", "output_dir": "isolated"}
    monkeypatch.setattr(controller, "prepare", prepare_only)
    monkeypatch.setattr(controller, "execute", lambda state, **kwargs: dict(state, status="pending"))
    assert controller.main(["--batch", str(path), "--execute", "--wait-seconds", "0"]) == 2
    assert calls == ["ONE"]
