"""Offline transport checks; never discovers or modifies a real UE editor."""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def transport(monkeypatch, tmp_path):
    scripts = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(scripts))
    import pair_review_transport_fast_v1 as fast
    spec = importlib.util.spec_from_file_location("offline_pair_transport_panel", scripts / "scene_site_review_panel_v1.py")
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    app.RUN, app.WORKER = tmp_path, scripts / "pair_scene_review_20261019_v1.py"
    node = {"node_id": "editor-a", "project_name": "datatry_02", "user": "Macheniek"}
    state = SimpleNamespace(sessions=[], lock_depth=0, locks=0, loads=0, installs=0,
                            fail_next=False, wrong_reply=False, sleeps=[])

    @contextmanager
    def command_lock():
        state.locks += 1
        state.lock_depth += 1
        try:
            yield
        finally:
            state.lock_depth -= 1

    class FakeSession:
        def __init__(self):
            self.remote_nodes = [node]
            self.starts, self.opens, self.stops, self.commands = 0, [], 0, []
            self.timeouts = []
            self._command_connection = SimpleNamespace(_command_channel_socket=SimpleNamespace(settimeout=self.timeouts.append))
            state.sessions.append(self)

        def start(self):
            self.starts += 1

        def open_command_connection(self, node_id):
            assert state.lock_depth == 1
            self.opens.append(node_id)

        def run_command(self, sent, **kwargs):
            assert state.lock_depth == 1
            assert kwargs == {"unattended": True, "exec_mode": "file", "raise_on_failure": False}
            self.commands.append(sent.copy())
            if state.fail_next:
                state.fail_next = False
                raise ConnectionResetError("reply interrupted")
            result = {**sent, "success": True, "message": "人物切换完成"}
            if state.wrong_reply:
                result["request_id"] = "old-request"
            return {"success": True, "output": [{"output": app.MARKER + json.dumps(result, ensure_ascii=False)}]}

        def stop(self):
            self.stops += 1

    module = SimpleNamespace(RemoteExecution=FakeSession, MODE_EXEC_FILE="file")

    def load(_root):
        state.loads += 1
        return module

    def select(nodes, node_id, pinned):
        assert nodes == [node]
        assert node_id in (None, node["node_id"])
        if pinned:
            assert pinned["node_id"] == node["node_id"]
        return node.copy()

    app.bridge = SimpleNamespace(command_lock=command_lock, load_remote_execution=load,
                                 select_node=select, DEFAULT_ENGINE_ROOT=tmp_path)
    app.command_payload = lambda sent: sent
    app.install_complete_reply_receiver = lambda module: setattr(state, "installs", state.installs + 1)
    monkeypatch.setattr(fast.time, "sleep", state.sleeps.append)
    monkeypatch.setattr(fast.atexit, "register", lambda callback: None)
    executor = fast.install(app)
    yield fast, app, executor, state
    executor.close()


def test_complete_success_reuses_session_without_fixed_discovery_wait(transport):
    fast, app, executor, state = transport
    first = {"request_id": "first", "action": "preview"}
    second = {"request_id": "second", "action": "set_appearance"}
    assert app.execute(first)["request_id"] == "first"
    assert app.execute(second)["request_id"] == "second"
    assert len(state.sessions) == state.loads == state.installs == 1
    session = state.sessions[0]
    assert session.starts == 1 and session.opens == ["editor-a"]
    assert session.stops == 0 and session.commands == [first, second]
    assert session.timeouts == [120] and state.sleeps == []
    assert state.locks == 2
    assert fast.install(app) is executor
    assert json.loads((app.RUN / "remote/second.json").read_text(encoding="utf-8"))["success"]
    executor.close()
    executor.close()
    assert session.stops == 1


def test_disconnect_is_not_replayed_and_next_request_recovers(transport):
    _, app, executor, state = transport
    first = {"request_id": "lost", "action": "save_site"}
    state.fail_next = True
    with pytest.raises(ConnectionResetError, match="interrupted"):
        app.execute(first)
    assert len(state.sessions) == 1
    assert state.sessions[0].commands == [first]
    assert state.sessions[0].stops == 1
    assert executor.session is None
    failed = json.loads((app.RUN / "remote/lost.json").read_text(encoding="utf-8"))
    assert not failed["success"] and "interrupted" in failed["error"]["message"]
    next_request = {"request_id": "recover", "action": "status"}
    assert app.execute(next_request)["request_id"] == "recover"
    assert len(state.sessions) == 2
    assert state.sessions[1].commands == [next_request]
    assert state.sleeps == []


def test_mismatched_reply_closes_connection_without_replay(transport):
    _, app, executor, state = transport
    state.wrong_reply = True
    with pytest.raises(RuntimeError, match="不匹配"):
        app.execute({"request_id": "current", "action": "preview"})
    assert len(state.sessions) == 1
    assert len(state.sessions[0].commands) == 1
    assert state.sessions[0].stops == 1 and executor.session is None


def test_install_replaces_captured_panel_and_queue_defaults_and_preserves_injection(transport):
    fast, app, _, _ = transport
    old_executor = lambda *_: "old"

    class CapturedPanel:
        def __init__(self, root, node_id=None, executor=old_executor):
            self.root, self.node_id, self.executor = root, node_id, executor

    class CapturedQueue:
        def __init__(self, executor=old_executor, node_id=None):
            self.node_id, self.executor = node_id, executor

    private = SimpleNamespace(Panel=CapturedPanel, CommandQueue=CapturedQueue)
    executor = fast.install(private)
    assert private.Panel("root", "node").executor is executor
    assert private.CommandQueue(node_id="node").executor is executor
    override = lambda *_: "offline"
    assert private.Panel("root", executor=override).executor is override
    assert private.CommandQueue(override).executor is override
    assert CapturedPanel("root").executor is old_executor
    assert CapturedQueue().executor is old_executor


def test_complete_receiver_preserves_fragmented_utf8_and_filters_identity(monkeypatch):
    scripts = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(scripts))
    import scene_site_review_panel_v1 as shared

    class Message:
        def __init__(self, *_):
            pass

        def from_json_bytes(self, value):
            self.value = json.loads(value.decode("utf-8"))
            self.type_ = self.value["type"]
            return True

        def passes_receive_filter(self, node_id):
            return self.value["dest"] == node_id

    class Connection:
        pass

    module = SimpleNamespace(_RemoteExecutionCommandConnection=Connection,
                             _RemoteExecutionMessage=Message, DEFAULT_RECEIVE_BUFFER_SIZE=4096)
    shared.install_complete_reply_receiver(module)
    value = {"type": "command_result", "dest": "client", "text": "切换完成"}
    raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
    split = raw.index("切".encode("utf-8")) + 1
    fragments = iter([raw[:split], raw[split:split + 1], raw[split + 1:]])
    connection = Connection()
    connection._node_id = "client"
    connection._command_channel_socket = SimpleNamespace(recv=lambda _: next(fragments))
    assert connection._receive_message("command_result").value == value
    connection._command_channel_socket = SimpleNamespace(recv=lambda _: b"")
    with pytest.raises(RuntimeError, match="中断"):
        connection._receive_message("command_result")
    wrong = json.dumps({**value, "dest": "other"}).encode("utf-8")
    connection._command_channel_socket = SimpleNamespace(recv=lambda _: wrong)
    with pytest.raises(RuntimeError, match="不匹配"):
        connection._receive_message("command_result")
