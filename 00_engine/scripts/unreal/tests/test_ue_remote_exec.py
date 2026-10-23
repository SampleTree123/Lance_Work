from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "ue_remote_exec.py"
SPEC = importlib.util.spec_from_file_location("ue_remote_exec", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DefaultEngineRootTests(unittest.TestCase):
    def test_environment_override_has_priority(self) -> None:
        with mock.patch.dict(
            MODULE.os.environ,
            {"DM_UE_ENGINE_ROOT": "/custom/UE_5.8"},
            clear=False,
        ):
            self.assertEqual(
                MODULE.default_engine_root(),
                Path("/custom/UE_5.8"),
            )

    def test_multicast_bind_address_defaults_from_environment(self) -> None:
        with mock.patch.dict(
            MODULE.os.environ,
            {
                "DM_UE_REMOTE_BIND_ADDRESS": "0.0.0.0",
                "DM_UE_REMOTE_MULTICAST_TTL": "1",
            },
            clear=False,
        ), mock.patch.object(
            MODULE.sys,
            "argv",
            ["ue_remote_exec.py", "--project", "datatry_02", "--command", "pass"],
        ):
            args = MODULE.parse_args()

        self.assertEqual(args.multicast_bind_address, "0.0.0.0")
        self.assertEqual(args.multicast_ttl, 1)


if __name__ == "__main__":
    unittest.main()
