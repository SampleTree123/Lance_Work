from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "ue_mcp_client.py"
SPEC = importlib.util.spec_from_file_location("ue_mcp_client", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class StreamingRequestTests(unittest.TestCase):
    @mock.patch.object(MODULE.subprocess, "run")
    def test_tool_call_reads_unreal_sse_response(self, run: mock.Mock) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                b'event: message\r\n'
                b'data: {"jsonrpc":"2.0","id":1,'
                b'"result":{"content":[]}}\r\n\r\n'
            ),
            stderr=b"",
        )
        client = MODULE.UnrealMcpClient("http://127.0.0.1:8010/mcp")
        client.session_id = "test-session"

        result = client.request("tools/call", {"name": "list_toolsets"})

        self.assertEqual(result, {"content": []})
        command = run.call_args.args[0]
        self.assertIn("--no-buffer", command)
        self.assertIn("Mcp-Session-Id: test-session", command)

    def test_non_tool_request_uses_regular_transport(self) -> None:
        client = MODULE.UnrealMcpClient("http://127.0.0.1:8010/mcp")
        response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        with mock.patch.object(client, "_post", return_value=response) as post:
            with mock.patch.object(client, "_post_streaming") as streaming:
                result = client.request("tools/list", {})

        self.assertEqual(result, {"tools": []})
        post.assert_called_once()
        streaming.assert_not_called()


if __name__ == "__main__":
    unittest.main()
