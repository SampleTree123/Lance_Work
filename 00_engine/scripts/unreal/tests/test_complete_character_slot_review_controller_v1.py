"""Controller protocol/closing tests; no UE calls, sockets, or visible UI."""
from __future__ import annotations

from contextlib import nullcontext
import copy
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_complete_character_slot_review_v1 as controller


@pytest.fixture(scope="module")
def data():
    return controller.load_catalog()


@pytest.fixture
def run_root(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    (root / "replies").mkdir(parents=True)
    monkeypatch.setattr(controller, "ROOT", root)
    monkeypatch.setattr(controller, "command_lock", lambda: nullcontext())
    return root


@pytest.fixture
def request_value(data):
    return controller.initial_request(data)


def result_for(request, data):
    return {"success": True, "request": copy.deepcopy(request), "level": controller.LEVEL,
            "sources": copy.deepcopy(data["sources"]), "plan_sha256": "plan123",
            "bindings": {"success": True, "errors": [], "plan_sha256": "plan123",
                         "characters": {s: {"components": [{"component_name": "Body", "mesh_path": f"/Game/{s}.Body", "errors": []}]}
                                        for s in ("female", "male")}}}


def envelope(path):
    return {"success": True, "output": [{"output": controller.MARKER + json.dumps({"success": True, "result_file": str(path)})}]}


def save_result(path, result):
    controller.write(path, result)
    return envelope(path)


def test_reopen_is_static_hair_two_even_when_saved_case_was_playing(data):
    saved = controller.initial_request(data)
    saved.update(action_index=3, playing=True, view="back")
    saved["choices"]["female"]["hair_id"] = "HAIR_HB1_16"
    actual = controller.initial_request(data, {"request": saved})
    assert actual["action_index"] == 0 and actual["playing"] is False and actual["view"] == "front"
    assert all(c["hair_id"] == "HAIR_HB1_02" for c in actual["choices"].values())
    assert saved["playing"] is True  # Input is not rewritten.


def test_reopen_preserves_valid_choices_from_bound_predecessor(data):
    saved = controller.initial_request(data)
    saved["registry_sha256"] = data["sources"]["source_registry"]["sha256"]
    for sex in ("female", "male"):
        saved["choices"][sex] = copy.deepcopy(data["presets_by_sex"][sex][-1]["choice"])
    actual = controller.initial_request(data, {"request": saved})
    assert all(actual["choices"][s]["family_id"] == saved["choices"][s]["family_id"]
               for s in ("female", "male"))
    invalid = copy.deepcopy(saved)
    invalid["choices"]["male"]["family_id"] = "male.removed_family"
    actual = controller.initial_request(data, {"request": invalid})
    assert actual["choices"]["female"]["family_id"] == saved["choices"]["female"]["family_id"]
    assert actual["choices"]["male"]["family_id"] != "male.removed_family"


@pytest.mark.parametrize("focus", ["female", "male", "both"])
def test_legs_cli_request_and_actual_reply_keep_requested_framing(run_root, data, focus):
    args = controller.build_parser().parse_args(["--action", "view", "--framing", "legs", "--focus", focus])
    request = controller.cli_request(args, data)
    assert request["framing"] == "legs" and request["focus"] == focus
    path = run_root / "replies/legs.json"
    result = result_for(request, data)
    assert controller.parse_reply(save_result(path, result), request)["request"]["framing"] == "legs"
    result["request"]["framing"] = "torso"
    with pytest.raises(RuntimeError, match="不一致"):
        controller.parse_reply(save_result(path, result), request)


def test_cli_uses_original_gapped_preset_numbers_and_sex_specific_hair(data):
    parser = controller.build_parser()
    args = parser.parse_args(["--action", "show", "--female-preset", "95", "--male-preset", "78",
                              "--female-hair", "38", "--male-hair", "39", "--framing", "feet"])
    request = controller.cli_request(args, data)
    expected = next(p for p in data["presets_by_sex"]["female"] if p["index"] == 95)
    assert request["choices"]["female"]["family_id"] == expected["choice"]["family_id"]
    assert request["choices"]["male"]["hair_id"] == next(h["hair_id"] for h in data["hairs_by_sex"]["male"] if h["index"] == 39)
    assert request["framing"] == "feet"
    for flags in (["--female-preset", "71"], ["--male-preset", "31"], ["--male-hair", "8"], ["--male-hair", "40"], ["--female-hair", "6"]):
        with pytest.raises(ValueError, match="编号"):
            controller.cli_request(parser.parse_args(["--action", "show", *flags]), data)


@pytest.mark.parametrize("field,value", [("action_index", True), ("action_index", 6), ("playing", 1),
                                          ("save", 1), ("focus", "none"), ("view", "top"), ("registry_sha256", "old")])
def test_invalid_request_fails_before_transport(data, request_value, field, value):
    request_value[field] = value
    with pytest.raises(ValueError):
        controller.validate_request(request_value, data)


def test_restore_does_not_depend_on_catalog_and_static_cannot_play(monkeypatch, data, request_value):
    monkeypatch.setattr(controller, "load_catalog", lambda: pytest.fail("restore must not load changed catalog"))
    assert controller.validate_request({"action": "restore"}) == {"action": "restore"}
    request_value["playing"] = True
    with pytest.raises(ValueError, match="静态"):
        controller.validate_request(request_value, data)


def test_large_receipt_is_read_from_bound_file_not_remote_output(run_root, data, request_value):
    result = result_for(request_value, data)
    result["extra_readback"] = "x" * 100000
    reply = save_result(run_root / "replies/result.json", result)
    assert len(json.dumps(reply)) < 1000
    parsed = controller.parse_reply(reply, request_value)
    assert parsed["bindings"] == result["bindings"] and parsed["controller_result_sha256"]


@pytest.mark.parametrize("path", ["outside.json", "replies/../outside.json", "replies_other/result.json"])
def test_receipt_escape_is_rejected(run_root, data, request_value, path):
    reply = save_result(run_root / path, result_for(request_value, data))
    with pytest.raises(RuntimeError, match="replies"):
        controller.parse_reply(reply, request_value)


@pytest.mark.parametrize("kind", ["relative", "missing", "text", "directory"])
def test_receipt_must_be_existing_absolute_json(run_root, request_value, kind):
    path = run_root / "replies/result.json"
    if kind == "relative":
        path = Path("replies/result.json")
    elif kind == "text":
        path = path.with_suffix(".txt")
        path.write_text("{}", encoding="utf-8")
    elif kind == "directory":
        path.mkdir()
    with pytest.raises(RuntimeError):
        controller.parse_reply(envelope(path), request_value)


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(success=False), lambda r: r.update(request={}),
    lambda r: r["request"].update(view="back"), lambda r: r.update(level="/Game/Wrong"),
    lambda r: r["bindings"].update(success=False), lambda r: r["bindings"].update(errors=["bad"]),
    lambda r: r["bindings"]["characters"].pop("male"), lambda r: r["bindings"].update(plan_sha256="wrong"),
    lambda r: r["sources"]["registry"].update(sha256="wrong"),
])
def test_stale_failed_or_unbound_actual_state_cannot_be_loaded(run_root, data, request_value, mutation):
    result = result_for(request_value, data)
    mutation(result)
    with pytest.raises(RuntimeError):
        controller.parse_reply(save_result(run_root / "replies/result.json", result), request_value)


def test_ambiguous_markers_and_remote_failure_do_not_print_payload(run_root, data, request_value):
    reply = save_result(run_root / "replies/result.json", result_for(request_value, data))
    reply["output"] *= 2
    with pytest.raises(RuntimeError, match="唯一"):
        controller.parse_reply(reply, request_value)
    reply["success"] = False
    reply["output"].append({"output": "base64-blob" * 100000})
    with pytest.raises(RuntimeError) as exc:
        controller.parse_reply(reply, request_value)
    assert "base64" not in str(exc.value) and len(str(exc.value)) < 200


def test_manual_record_requires_human_button_fresh_status_and_unmodified_evidence(run_root, data, request_value, monkeypatch):
    request_value["action"] = "status"
    path = run_root / "replies/status.json"
    reply = controller.parse_reply(save_result(path, result_for(request_value, data)), request_value)
    monkeypatch.setattr(controller, "load_catalog", lambda: data)
    with pytest.raises(ValueError, match="使用者"):
        controller.record_observation("female", "accepted", "", request_value, reply, data)
    assert not (run_root / "manual_review.json").exists()
    observation = controller.record_observation("female", "issue", "裤子检查", request_value, reply, data, human_button=True)
    assert observation["bindings"] == reply["bindings"] and observation["plan_sha256"] == "plan123"
    assert observation["request"]["action"] == "status" and observation["origin"] == "human_panel_button"
    assert len(controller.read(run_root / "manual_review.json")["observations"]) == 1
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="回执文件"):
        controller.record_observation("female", "accepted", "", request_value, reply, data, human_button=True)
    assert len(controller.read(run_root / "manual_review.json")["observations"]) == 1


def test_manual_record_does_not_accept_a_changed_draft_or_changed_sources(run_root, data, request_value, monkeypatch):
    request_value["action"] = "status"
    reply = controller.parse_reply(save_result(run_root / "replies/status.json", result_for(request_value, data)), request_value)
    changed = copy.deepcopy(request_value)
    changed["choices"]["female"]["hair_id"] = None
    with pytest.raises(RuntimeError, match="不一致"):
        controller.record_observation("female", "accepted", "", changed, reply, data, human_button=True)
    new_data = copy.deepcopy(data)
    new_data["sources"]["registry"]["sha256"] = "changed"
    monkeypatch.setattr(controller, "load_catalog", lambda: new_data)
    with pytest.raises(ValueError, match="来源已变化"):
        controller.record_observation("female", "accepted", "", request_value, reply, data, human_button=True)
    assert not (run_root / "manual_review.json").exists()


def poll_until(manager, predicate):
    deadline, delivered = time.monotonic() + 3, []
    while time.monotonic() < deadline:
        result = manager.poll()
        if result:
            delivered.append(result)
        if predicate():
            return delivered
        time.sleep(.005)
    pytest.fail("Background command did not complete")


@pytest.mark.parametrize("fail_first", [False, True])
def test_close_during_busy_serializes_restore_and_never_records_acceptance(run_root, fail_first):
    entered, release, calls, threads = threading.Event(), threading.Event(), [], []
    def executor(request, node):
        calls.append(request["action"])
        threads.append(threading.get_ident())
        if request["action"] == "show":
            entered.set()
            assert release.wait(2)
            if fail_first:
                raise TimeoutError("simulated 120-second command timeout")
        return {"success": True}
    manager = controller.CommandQueue(executor)
    manager.submit({"action": "show"})
    assert entered.wait(1)
    manager.close()
    manager.close()
    assert calls == ["show"]
    with pytest.raises(RuntimeError):
        manager.submit({"action": "view"})
    release.set()
    delivered = poll_until(manager, lambda: manager.closed)
    manager.thread.join(1)
    assert calls == ["show", "restore"] and len(set(threads)) == 1 and not manager.thread.is_alive()
    assert len(delivered) == 2 and delivered[-1][0] == {"action": "restore"}
    assert not (run_root / "manual_review.json").exists()
    if fail_first:
        assert controller.read(run_root / "controller_error.json")["stage"] == "background_command"


def test_restore_failure_still_finishes_queue_and_persists_error(run_root):
    def fail(request, node):
        raise RuntimeError("restore failed")
    manager = controller.CommandQueue(fail)
    manager.close()
    delivered = poll_until(manager, lambda: manager.closed)
    manager.thread.join(1)
    assert str(delivered[0][2]) == "restore failed"
    assert controller.read(run_root / "controller_error.json")["error"] == "restore failed"


@pytest.mark.parametrize("timeout", [False, True])
def test_execute_reuses_pin_and_lock_sets_timeout_and_always_stops(run_root, data, request_value, monkeypatch, timeout):
    captured = {}
    reply = save_result(run_root / "replies/result.json", result_for(request_value, data))
    node = {"node_id": "wanted", "project_name": "datatry_02", "user": "Macheniek"}
    class Session:
        remote_nodes = [node]
        def __init__(self):
            self._command_connection = SimpleNamespace(_command_channel_socket=SimpleNamespace(settimeout=lambda v: captured.update(timeout=v)))
        def start(self): captured["started"] = True
        def open_command_connection(self, value): captured["node"] = value
        def run_command(self, command, **kwargs):
            captured["payload"], captured["kwargs"] = command, kwargs
            if timeout:
                raise TimeoutError("simulated socket timeout")
            return reply
        def stop(self): captured["stopped"] = True
    clock = iter(range(100))
    monkeypatch.setattr(controller.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(controller.time, "sleep", lambda _: None)
    monkeypatch.setattr(controller.previous, "ROOT", run_root / "historical")
    monkeypatch.setattr(controller.previous, "load_remote_execution", lambda _: SimpleNamespace(RemoteExecution=Session, MODE_EXEC_FILE="file"))
    if timeout:
        with pytest.raises(TimeoutError):
            controller.execute(request_value, "wanted")
    else:
        assert controller.execute(request_value, "wanted")["success"] is True
    assert captured["timeout"] == 120 and captured["stopped"]
    assert "DM_SLOT_REVIEW_REQUEST" in captured["payload"]
    assert controller.read(run_root / "historical/session.json")["node_id"] == "wanted"
    assert len(list(run_root.glob("remote_*.json"))) == 1
    saved = controller.read(next(run_root.glob("remote_*.json")))
    assert saved["success"] is not timeout
    if timeout:
        assert saved["error"]["type"] == "TimeoutError"


def test_node_selection_never_silently_switches_editor():
    node = {"node_id": "one", "project_name": "datatry_02", "user": "Macheniek"}
    with pytest.raises(RuntimeError):
        controller.select_node([node], pinned={"node_id": "stale"})
    with pytest.raises(RuntimeError):
        controller.select_node([node, {**node, "node_id": "two"}])
    assert controller.select_node([node], node_id="one", pinned={"node_id": "stale"}) == node


def test_startup_failure_replaces_stale_ready_lifecycle_and_persists_error(run_root, monkeypatch):
    import os
    controller.write(run_root / "panel_lifecycle.json", {"pid": os.getpid(), "stage": "starting"})
    def fail():
        raise ValueError("catalog changed")
    monkeypatch.setattr(controller, "main", fail)
    with pytest.raises(ValueError, match="catalog changed"):
        controller.entrypoint()
    assert controller.read(run_root / "panel_lifecycle.json")["stage"] == "failed"
    assert controller.read(run_root / "controller_error.json")["stage"] == "entrypoint"
