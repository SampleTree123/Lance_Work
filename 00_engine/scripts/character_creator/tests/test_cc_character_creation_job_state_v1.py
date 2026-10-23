"""Controller recovery guarantees, using fake Bridge responses only."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_character_creation_job_state_v1 as jobs


@pytest.fixture
def fixture(tmp_path):
    run, stage, bridge = (tmp_path / key for key in ("run", "stage", "bridge"))
    attempt, staged = run / "alice" / "attempt_001", stage / "alice" / "attempt_001"
    attempt.mkdir(parents=True)
    staged.mkdir(parents=True)
    original = tmp_path / "original.ccProject"
    original.write_bytes(b"unchanged source")
    request = {"source_project": str(original), "sex": "female", "character_id": "alice", "seed": 1}
    state = {"character_id": "alice", "attempt_id": "attempt_001", "attempt_dir": str(attempt),
             "state_path": str(attempt / "controller_state.json"), "stage_dir": str(staged),
             "request": request, "request_fingerprint": jobs.fingerprint(request), "steps": {},
             "inputs": {"original": jobs.bind(original)}, "status": "prepared"}
    calls = []
    def client(args):
        calls.append(args)
        return {"healthy": True, "heartbeat": {"active_job_id": None}} if args == ["health"] else {"queued": True}
    driver = jobs.BridgeStepDriver(run_root=run, stage_root=stage, bridge_root=bridge, client_call=client)
    driver.persist(state)
    return state, driver, calls, bridge


def submit(fixture, step_id="generate"):
    state, driver, _, _ = fixture
    output = Path(state["attempt_dir"]) / step_id
    return driver.submit_step(state, step_id, {"diagnostic_mode": "fake", "value": 1}, output)


def terminal(fixture, status="succeeded", **changes):
    state, _, _, bridge = fixture
    step = state["steps"]["generate"]
    result = {"job_id": step["job_id"], "status": status, "command": "validate_bodyfit_library",
              "result": {"library_file": step["library"]["path"], "output_dir": step["output_dir"]},
              "finished_at": "2026-10-05", "error": None}
    result.update(changes)
    path = bridge / "results" / (step["job_id"] + ".json")
    jobs.write(path, result)
    return path


def complete(fixture):
    state, driver, _, _ = fixture
    submit(fixture)
    terminal(fixture)
    driver.wait_step(state, "generate", 0)
    output = Path(state["attempt_dir"]) / "generate" / "saved.ccProject"
    output.write_bytes(b"new project")
    driver.mark_step_complete(state, "generate", {"project": output})
    return output


def test_durable_pending_precedes_submission(fixture):
    state, driver, calls, _ = fixture
    def client(args):
        calls.append(args)
        if args == ["health"]:
            return {"healthy": True}
        durable = jobs.read(state["state_path"])
        assert durable["steps"]["generate"]["status"] == "pending"
        assert durable["steps"]["generate"]["job_id"] in args
        return {"queued": True}
    driver.client_call = client
    step = submit(fixture)
    assert calls[-1][-1] == "--no-wait"
    assert step["status"] == "pending"
    assert "--auto-dismiss-undo-warning" in calls[-1]


def test_pending_never_resubmits_even_without_queue_or_result(fixture):
    state, driver, calls, _ = fixture
    first = submit(fixture)
    driver.wait_step(state, "generate", 0)
    second = submit(fixture)
    assert first["job_id"] == second["job_id"]
    assert sum(args[0] == "validate-bodies" for args in calls) == 1


def test_unknown_submission_preserves_same_job(fixture):
    state, driver, _, _ = fixture
    def client(args):
        if args == ["health"]:
            return {"healthy": True}
        raise TimeoutError("uncertain")
    driver.client_call = client
    with pytest.raises(jobs.ControllerError, match="uncertain"):
        submit(fixture)
    pending = jobs.read(state["state_path"])["steps"]["generate"]
    assert pending["status"] == "pending"
    assert submit(fixture)["job_id"] == pending["job_id"]


@pytest.mark.parametrize("change", [{"job_id": "other"}, {"command": "wrong"}, {"status": "unknown"},
                                   {"result": {"library_file": "wrong", "output_dir": "wrong"}}])
def test_unrelated_or_unknown_results_do_not_complete(fixture, change):
    state, driver, _, _ = fixture
    submit(fixture)
    terminal(fixture, **change)
    with pytest.raises(jobs.ControllerError):
        driver.wait_step(state, "generate", 0)
    assert state["steps"]["generate"]["status"] == "pending"


def test_success_requires_real_bound_outputs(fixture):
    state, driver, _, _ = fixture
    submit(fixture)
    terminal(fixture)
    assert driver.wait_step(state, "generate", 0)["status"] == "succeeded"
    with pytest.raises(jobs.ControllerError):
        driver.verify_completed_step(state, "generate")
    with pytest.raises(jobs.ControllerError, match="named"):
        driver.mark_step_complete(state, "generate", {})
    with pytest.raises(FileNotFoundError):
        driver.mark_step_complete(state, "generate", {"project": Path(state["attempt_dir"]) / "missing"})


def test_completed_hash_drift_blocks_reuse(fixture):
    state, driver, calls, _ = fixture
    output = complete(fixture)
    assert driver.verify_completed_step(state, "generate")
    output.write_bytes(b"drift")
    with pytest.raises(jobs.ControllerError, match="SHA changed"):
        submit(fixture)
    assert sum(args[0] == "validate-bodies" for args in calls) == 1


def test_library_drift_blocks_resume(fixture):
    state, driver, _, _ = fixture
    step = submit(fixture)
    Path(step["library"]["path"]).write_text("{}")
    with pytest.raises(jobs.ControllerError, match="SHA changed"):
        driver.wait_step(state, "generate", 0)


def test_request_drift_blocks_work(fixture):
    state, driver, _, _ = fixture
    state["request"]["seed"] = 9
    with pytest.raises(jobs.ControllerError, match="fingerprint"):
        submit(fixture)


def test_original_drift_blocks_work(fixture):
    state, driver, _, _ = fixture
    Path(state["inputs"]["original"]["path"]).write_bytes(b"changed")
    with pytest.raises(jobs.ControllerError, match="SHA changed"):
        submit(fixture)


@pytest.mark.parametrize("status", ["failed", "cancelled"])
def test_terminal_failure_requires_new_attempt(fixture, status):
    state, driver, _, _ = fixture
    submit(fixture)
    terminal(fixture, status=status)
    assert driver.wait_step(state, "generate", 0)["status"] == "failed"
    assert state["status"] == "failed"
    with pytest.raises(jobs.ControllerError, match="new attempt"):
        submit(fixture)


def test_no_parallel_or_unbound_next_step(fixture):
    state, driver, _, _ = fixture
    submit(fixture)
    for phase in ("pending", "succeeded"):
        if phase == "succeeded":
            terminal(fixture)
            driver.wait_step(state, "generate", 0)
        with pytest.raises(jobs.ControllerError, match="previous"):
            submit(fixture, "assemble")


def test_busy_bridge_does_not_prepare_or_submit(fixture):
    state, driver, _, _ = fixture
    driver.client_call = lambda args: {"healthy": True, "heartbeat": {"active_job_id": "other"}}
    with pytest.raises(jobs.ControllerError, match="busy"):
        submit(fixture)
    assert not state["steps"]


def test_other_queued_work_blocks_submission(fixture):
    state, _, _, bridge = fixture
    jobs.write(bridge / "inbox" / "other.json", {})
    with pytest.raises(jobs.ControllerError, match="queued"):
        submit(fixture)
    assert not state["steps"]


def test_altered_pending_config_not_reused(fixture):
    state, driver, _, _ = fixture
    step = submit(fixture)
    with pytest.raises(jobs.ControllerError, match="differs"):
        driver.submit_step(state, "generate", {}, step["output_dir"])


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_wait_rejected(fixture, value):
    state, driver, _, _ = fixture
    submit(fixture)
    with pytest.raises(jobs.ControllerError, match="finite"):
        driver.wait_step(state, "generate", value)


def test_output_outside_attempt_rejected(fixture, tmp_path):
    state, driver, _, _ = fixture
    with pytest.raises(jobs.ControllerError, match="outside"):
        driver.submit_step(state, "generate", {}, tmp_path / "outside")


def test_bound_output_outside_attempt_rejected(fixture, tmp_path):
    state, driver, _, _ = fixture
    submit(fixture)
    terminal(fixture)
    driver.wait_step(state, "generate", 0)
    external = tmp_path / "external"
    external.write_bytes(b"unrelated")
    with pytest.raises(jobs.ControllerError, match="outside"):
        driver.mark_step_complete(state, "generate", {"project": external})


def test_lock_blocks_concurrent_controller_and_releases(tmp_path):
    with jobs.controller_lock(tmp_path):
        with pytest.raises(jobs.ControllerError, match="lock"):
            with jobs.controller_lock(tmp_path):
                pass
    assert not (tmp_path / "controller.lock").exists()


def test_controller_does_not_remove_replacement_lock(tmp_path):
    with jobs.controller_lock(tmp_path):
        jobs.write(tmp_path / "controller.lock", {"token": "other"})
    assert (tmp_path / "controller.lock").is_file()


@pytest.mark.parametrize("change", [{"status": "unexpected"}, {"job_id": "../outside"}])
def test_unknown_persisted_step_cannot_resume(fixture, change):
    state, driver, _, _ = fixture
    step = submit(fixture)
    step.update(change)
    with pytest.raises(jobs.ControllerError):
        driver.wait_step(state, "generate", 0)
