"""Persistent command transport installed only on the pair panel's private app.

Call ``install(app)`` after loading/configuring the private panel module and before
subclassing/creating its Panel. Restart the panel process to pick up code changes.
No command is replayed after failure; a later user request opens a new session.
"""
from __future__ import annotations

import atexit
import os
import threading
import time
import traceback


class PersistentExecutor:
    def __init__(self, app):
        self.app = app
        self.session = None
        self.module = None
        self.node = None
        self.pid = os.getpid()
        self._lock = threading.RLock()

    def _discard(self):
        session, self.session = self.session, None
        self.module, self.node = None, None
        if session is not None:
            try:
                session.stop()
            except Exception:
                # Preserve the original command failure, including lost replies.
                pass

    def close(self):
        with self._lock:
            self._discard()

    def _connect(self, node_id):
        app = self.app
        module = app.bridge.load_remote_execution(app.bridge.DEFAULT_ENGINE_ROOT.resolve())
        app.install_complete_reply_receiver(module)
        self.module = module
        self.session = module.RemoteExecution()
        self.session.start()
        pin_path = app.RUN / "session.json"
        pinned = app.read(pin_path) if pin_path.is_file() else None
        deadline, last_error = time.monotonic() + 12, None
        while True:
            try:
                node = app.bridge.select_node(list(self.session.remote_nodes), node_id, pinned)
                break
            except RuntimeError as exc:
                last_error = exc
            if time.monotonic() >= deadline:
                raise last_error
            time.sleep(.2)
        app.write(pin_path, {"node_id": node["node_id"], "node": node, "pinned_at": app.now()})
        self.session.open_command_connection(node["node_id"])
        self.session._command_connection._command_channel_socket.settimeout(120)
        self.node = node

    def __call__(self, sent, node_id=None):
        app = self.app
        with self._lock, app.bridge.command_lock():
            record = {"started_at": app.now(), "request": sent, "success": False}
            try:
                if not app.WORKER.is_file():
                    raise FileNotFoundError("拍摄点执行脚本尚未就绪。")
                if self.pid != os.getpid():
                    self._discard()
                    self.pid = os.getpid()
                if self.session is not None and node_id and node_id != self.node["node_id"]:
                    self._discard()
                if self.session is None:
                    self._connect(node_id)
                record["node"] = self.node
                reply = self.session.run_command(
                    app.command_payload(sent), unattended=True,
                    exec_mode=self.module.MODE_EXEC_FILE, raise_on_failure=False)
                record["command_result"] = reply
                result = app.parse_reply(reply, sent)
                # Persistent connections must never accept a delayed prior reply.
                if (result.get("request_id") != sent["request_id"]
                        or result.get("action") != sent["action"]):
                    raise RuntimeError("UE 回执与本次操作不匹配；本次操作不会自动重试。")
                record.update(success=True, result=result)
                return result
            except Exception as exc:
                record["error"] = {"message": str(exc), "traceback": traceback.format_exc()}
                self._discard()
                raise
            finally:
                record["finished_at"] = app.now()
                app.write(app.RUN / "remote" / (sent["request_id"] + ".json"), record)


def install(app):
    """Bind a persistent executor to this privately loaded module, idempotently.

    Explicit executor injection remains available for offline tests. Both classes
    are wrapped because their original default arguments captured old execute.
    The shared scene_site_review_panel_v1 module and other panels stay untouched.
    """
    existing = getattr(app, "_pair_fast_transport", None)
    if existing is not None:
        return existing
    executor = PersistentExecutor(app)
    original_panel, original_queue = app.Panel, app.CommandQueue

    class FastPanel(original_panel):
        def __init__(self, root, node_id=None, executor=None):
            super().__init__(root, node_id, executor=executor if executor is not None else app.execute)

    class FastCommandQueue(original_queue):
        def __init__(self, executor=None, node_id=None):
            super().__init__(executor=executor if executor is not None else app.execute, node_id=node_id)

    app.execute = executor
    app.Panel, app.CommandQueue = FastPanel, FastCommandQueue
    app._pair_fast_transport = executor
    atexit.register(executor.close)
    return executor
