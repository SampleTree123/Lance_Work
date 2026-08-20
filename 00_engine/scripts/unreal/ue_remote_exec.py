#!/usr/bin/env python3
"""Execute a Python payload in a running Unreal Editor instance."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time


DEFAULT_ENGINE_ROOT = Path(r"D:\UE\UE_5.8")


def load_remote_execution(engine_root: Path):
    module_path = (
        engine_root
        / "Engine"
        / "Plugins"
        / "Experimental"
        / "PythonScriptPlugin"
        / "Content"
        / "Python"
        / "remote_execution.py"
    )
    if not module_path.is_file():
        raise FileNotFoundError(f"Unreal remote execution module not found: {module_path}")

    spec = importlib.util.spec_from_file_location("ue_remote_execution", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Running Unreal project name")
    parser.add_argument("--script", type=Path, help="Python file to execute in Unreal")
    parser.add_argument("--command", help="Literal Python command to execute in Unreal")
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_ENGINE_ROOT)
    parser.add_argument("--discovery-timeout", type=float, default=12.0)
    args = parser.parse_args()
    if bool(args.script) == bool(args.command):
        parser.error("Specify exactly one of --script or --command")
    return args


def main() -> int:
    args = parse_args()
    payload = args.command
    if args.script:
        payload = args.script.resolve().read_text(encoding="utf-8")

    remote_execution = load_remote_execution(args.engine_root.resolve())
    session = remote_execution.RemoteExecution()
    session.start()
    try:
        deadline = time.monotonic() + args.discovery_timeout
        matches = []
        while time.monotonic() < deadline:
            matches = [
                node
                for node in session.remote_nodes
                if node.get("project_name") == args.project
            ]
            if matches:
                break
            time.sleep(0.2)

        if not matches:
            discovered = [node.get("project_name") for node in session.remote_nodes]
            raise RuntimeError(
                f"Unreal project '{args.project}' was not discovered; found {discovered}"
            )
        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple Unreal nodes matched project '{args.project}': {matches}"
            )

        node = matches[0]
        session.open_command_connection(node["node_id"])
        result = session.run_command(
            payload,
            unattended=True,
            exec_mode=remote_execution.MODE_EXEC_FILE,
            raise_on_failure=False,
        )
        envelope = {"node": node, "command_result": result}
        print(json.dumps(envelope, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get("success") else 1
    finally:
        session.stop()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise
