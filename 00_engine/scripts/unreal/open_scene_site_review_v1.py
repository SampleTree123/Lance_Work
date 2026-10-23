"""Open the independent scene-site panel without launching a second UE editor."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scene_site_review_panel_v1 import RUN, SCRIPT_ROOT, read, write, now


def launch(node_id=None):
    RUN.mkdir(parents=True, exist_ok=True)
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    if os.name == "nt" and pythonw.is_file():
        python = pythonw
    command = [str(python), str(SCRIPT_ROOT / "scene_site_review_panel_v1.py")]
    if node_id:
        command += ["--node-id", node_id]
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with (RUN / "panel_stdout.log").open("ab") as out, (RUN / "panel_stderr.log").open("ab") as err:
        process = subprocess.Popen(command, cwd=SCRIPT_ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   creationflags=flags, start_new_session=os.name != "nt")
    deadline = time.monotonic() + 10
    lifecycle = {}
    while time.monotonic() < deadline:
        path = RUN / "panel_lifecycle.json"
        if path.is_file():
            lifecycle = read(path)
            if lifecycle.get("pid") == process.pid and lifecycle.get("stage") in {"ready", "failed"}:
                break
        if process.poll() is not None:
            break
        time.sleep(.15)
    ready = lifecycle.get("pid") == process.pid and lifecycle.get("stage") == "ready"
    result = {"schema": "scene_site_panel_launch_v1", "pid": process.pid, "ready": ready,
              "started_at": now(), "run_root": str(RUN), "lifecycle": lifecycle}
    write(RUN / "launcher_status.json", result)
    if not ready:
        raise RuntimeError("审查面板未能启动。请查看 " + str(RUN / "panel_stderr.log"))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-id")
    args = parser.parse_args()
    print(json.dumps(launch(args.node_id), ensure_ascii=False))
