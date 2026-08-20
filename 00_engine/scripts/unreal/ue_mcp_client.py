#!/usr/bin/env python3
"""Call the Unreal Editor streamable-HTTP MCP endpoint."""

from __future__ import annotations

import argparse
import base64
import json
from typing import Any
from urllib import request


DEFAULT_URL = "http://127.0.0.1:8010/mcp"
PROTOCOL_VERSION = "2025-06-18"


class UnrealMcpError(RuntimeError):
    pass


def decode_response(payload: bytes, content_type: str) -> dict[str, Any] | None:
    if not payload:
        return None
    text = payload.decode("utf-8")
    if "text/event-stream" in content_type:
        messages = [
            line[5:].strip()
            for line in text.splitlines()
            if line.startswith("data:") and line[5:].strip()
        ]
        if not messages:
            raise UnrealMcpError("MCP event stream did not contain a data message")
        text = messages[-1]
    value = json.loads(text)
    if not isinstance(value, dict):
        raise UnrealMcpError("MCP response must be a JSON object")
    return value


class UnrealMcpClient:
    def __init__(self, url: str, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout
        self.session_id: str | None = None
        self.next_id = 1

    def _post(self, message: dict[str, Any]) -> dict[str, Any] | None:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = request.Request(
            self.url,
            data=json.dumps(message, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout) as response:
            session_id = response.headers.get("Mcp-Session-Id")
            if session_id:
                self.session_id = session_id
            return decode_response(
                response.read(), response.headers.get("Content-Type", "")
            )

    def request(self, method: str, params: dict[str, Any]) -> Any:
        request_id = self.next_id
        self.next_id += 1
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        if response is None:
            raise UnrealMcpError(f"MCP request {method} returned no response")
        if response.get("id") != request_id:
            raise UnrealMcpError(f"Unexpected MCP response id for {method}")
        if "error" in response:
            raise UnrealMcpError(json.dumps(response["error"], ensure_ascii=False))
        return response.get("result")

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._post(message)

    def initialize(self) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "lance-unreal-mcp-client", "version": "1.0"},
            },
        )
        self.notify("notifications/initialized")
        return result

    def list_tools(self) -> dict[str, Any]:
        return self.request("tools/list", {})

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})


def parse_json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("Arguments must decode to a JSON object")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=30.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("list-tools")
    subparsers.add_parser("list-toolsets")
    describe = subparsers.add_parser("describe-toolset")
    describe.add_argument("toolset_name")
    call = subparsers.add_parser("call")
    call.add_argument("tool_name")
    arguments = call.add_mutually_exclusive_group()
    arguments.add_argument("--arguments", type=parse_json_object)
    arguments.add_argument("--arguments-base64")
    args = parser.parse_args()
    if getattr(args, "arguments_base64", None):
        decoded = base64.b64decode(args.arguments_base64).decode("utf-8")
        args.arguments = parse_json_object(decoded)
    if getattr(args, "arguments", None) is None:
        args.arguments = {}
    return args


def main() -> int:
    args = parse_args()
    client = UnrealMcpClient(args.url, args.timeout)
    initialized = client.initialize()
    if args.command == "health":
        value = {
            "url": args.url,
            "session_id": client.session_id,
            "server": initialized.get("serverInfo"),
            "capabilities": initialized.get("capabilities"),
        }
    elif args.command == "list-tools":
        value = client.list_tools()
    elif args.command == "list-toolsets":
        value = client.call("list_toolsets", {})
    elif args.command == "describe-toolset":
        value = client.call(
            "describe_toolset", {"toolset_name": args.toolset_name}
        )
    else:
        value = client.call(args.tool_name, args.arguments)
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
