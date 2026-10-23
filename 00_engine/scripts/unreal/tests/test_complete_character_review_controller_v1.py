"""Offline failure-boundary tests: no sockets, editor calls, or GUI creation."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_complete_character_wardrobe_hair_review_v1 as controller


@pytest.fixture
def run_root(tmp_path, monkeypatch):
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    (tmp_path / "replies").mkdir()
    return tmp_path


@pytest.fixture
def review_request():
    return dict(controller.DEFAULT_CASE, action="show")


def remote_result(value):
    return {"success": True, "output": [
        {"output": "Unrelated editor log"},
        {"output": controller.MARKER + json.dumps(value) + "\n"},
    ]}


def save_result(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return remote_result({"success": True, "result_file": str(path)})


def test_large_binding_receipt_survives_small_remote_envelope(run_root, review_request):
    bindings = {"female": [{"mesh": f"/Game/Clothes/Part{i}", "bones": "x" * 512}
                           for i in range(90)], "male": []}
    full = {"success": True, "request": review_request, "bindings": bindings}
    reply = save_result(run_root / "replies" / "large.json", full)
    assert len(json.dumps(full)) > 45000
    assert len(json.dumps(reply)) < 1500
    assert controller.parse_reply(reply, review_request)["bindings"] == bindings


@pytest.mark.parametrize("location", ["outside.json", "replies/../outside.json", "replies_extra/outside.json"])
def test_receipt_cannot_escape_reply_directory(run_root, review_request, location):
    path = run_root / location
    path.parent.mkdir(exist_ok=True)
    reply = save_result(path, {"success": True, "request": review_request})
    with pytest.raises(RuntimeError, match="replies"):
        controller.parse_reply(reply, review_request)


@pytest.mark.parametrize("kind", ["missing", "relative", "wrong_extension", "directory"])
def test_only_existing_absolute_json_receipts_are_accepted(run_root, review_request, kind):
    target = run_root / "replies" / "result.json"
    if kind == "relative":
        value = "replies/result.json"
    elif kind == "wrong_extension":
        target = target.with_suffix(".txt")
        target.write_text('{"success":true}', encoding="utf-8")
        value = str(target)
    elif kind == "directory":
        target.mkdir()
        value = str(target)
    else:
        value = str(target)
    with pytest.raises(RuntimeError):
        controller.parse_reply(remote_result({"success": True, "result_file": value}), review_request)


def test_failed_marker_does_not_follow_even_a_valid_file(run_root, review_request, monkeypatch):
    target = run_root / "replies" / "unused.json"
    target.write_text('{"success":true}', encoding="utf-8")
    def unexpected_read(_path):
        pytest.fail("A failed marker must not read a success receipt")
    monkeypatch.setattr(controller, "read", unexpected_read)
    with pytest.raises(RuntimeError, match="deliberate worker failure"):
        controller.parse_reply(remote_result({"success": False, "error": "deliberate worker failure",
                                               "result_file": str(target)}), review_request)


def test_failure_inside_file_is_not_reported_as_success(run_root, review_request):
    reply = save_result(run_root / "replies" / "failed.json",
                        {"success": False, "error": "binding mismatch", "request": review_request})
    with pytest.raises(RuntimeError, match="binding mismatch"):
        controller.parse_reply(reply, review_request)


def test_receipt_from_different_selection_is_rejected(run_root, review_request):
    reply = save_result(run_root / "replies" / "stale.json",
                        {"success": True, "request": dict(review_request, male_outfit=7), "bindings": {}})
    with pytest.raises(RuntimeError, match="male_outfit"):
        controller.parse_reply(reply, review_request)


def test_remote_execution_failure_cannot_be_overridden_by_success_marker(review_request):
    reply = remote_result({"success": True, "request": review_request})
    reply["success"] = False
    with pytest.raises(RuntimeError, match="UE"):
        controller.parse_reply(reply, review_request)


@pytest.fixture
def discovered_nodes():
    return [
        {"node_id": "offline", "project_name": "datatry_02", "user": "CodexSandboxOffline"},
        {"node_id": "interactive", "project_name": "datatry_02", "user": "Macheniek"},
        {"node_id": "other_project", "project_name": "OtherProject", "user": "Macheniek"},
    ]


def test_duplicate_project_names_select_only_interactive_user(discovered_nodes):
    assert controller.select_node(discovered_nodes)["node_id"] == "interactive"
    assert controller.select_node(list(reversed(discovered_nodes)))["node_id"] == "interactive"


def test_two_matching_interactive_editors_are_ambiguous(discovered_nodes):
    discovered_nodes.append(dict(discovered_nodes[1], node_id="second_interactive"))
    with pytest.raises(RuntimeError, match="匹配数量：2"):
        controller.select_node(discovered_nodes)


def test_missing_pin_never_silently_switches_to_another_editor(discovered_nodes):
    with pytest.raises(RuntimeError, match="固定"):
        controller.select_node(discovered_nodes, pinned={"node_id": "closed_editor"})


def test_explicit_node_can_replace_stale_pin_without_project_escape(discovered_nodes):
    pin = {"node_id": "closed_editor"}
    assert controller.select_node(discovered_nodes, "interactive", pin)["node_id"] == "interactive"
    with pytest.raises(RuntimeError):
        controller.select_node(discovered_nodes, "other_project", pin)


def test_saved_moving_case_opens_panel_static_without_opening_gui(run_root, monkeypatch):
    import tkinter
    saved = dict(controller.DEFAULT_CASE, female_outfit=3, male_outfit=4,
                 action_index=5, playing=True, view="back")
    (run_root / "current_case.json").write_text(json.dumps({"request": saved}), encoding="utf-8")
    data = {"sources": {"registry": {"sha256": "test"}},
            "female_outfits": [{}] * 5, "male_outfits": [{}] * 5,
            "hairs": [{}] * 5, "actions_by_sex": {"female": [{}] * 5, "male": [{}] * 5}}
    monkeypatch.setattr(controller, "load_catalog", lambda: data)
    observed = []
    validator = controller.validate_request
    def capture_request(value, catalog):
        observed.append(dict(value))
        return validator(value, catalog)
    monkeypatch.setattr(controller, "validate_request", capture_request)
    class StopBeforeGUI(Exception):
        pass
    def no_window():
        raise StopBeforeGUI()
    monkeypatch.setattr(tkinter, "Tk", no_window)
    args = controller.build_parser().parse_args([])
    with pytest.raises(StopBeforeGUI):
        controller.panel(args)
    assert observed == [dict(saved, action="show", action_index=0, playing=False)]


def test_pythonw_style_failure_is_persisted_without_console(run_root, monkeypatch):
    def startup_failure():
        raise RuntimeError("catalog failed before window creation")
    monkeypatch.setattr(controller, "main", startup_failure)
    with monkeypatch.context() as no_console:
        no_console.setattr(sys, "stdout", None)
        no_console.setattr(sys, "stderr", None)
        with pytest.raises(RuntimeError, match="catalog failed"):
            controller.entrypoint()
    failure = json.loads((run_root / "controller_error.json").read_text(encoding="utf-8"))
    assert failure["stage"] == "entrypoint"
    assert failure["pid"] > 0
    assert "startup_failure" in failure["traceback"]
    assert failure["error"] == "catalog failed before window creation"
