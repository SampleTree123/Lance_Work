from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "run_first_batch_server_render_batches.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_first_batch_server_render_batches", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def arguments(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_root=root / "run",
        start_index=1,
        limit=20,
        batch_size=10,
        max_invocations_per_batch=2,
        retry_delay_seconds=0.0,
        confirm_full_run=False,
        dry_run=False,
        audit_existing=False,
    )


class BatchPlanningTests(unittest.TestCase):
    def test_batches_cover_selection_without_single_node_editor_batches(self) -> None:
        batches = MODULE.build_batches(5, 23, 10)

        self.assertEqual(
            batches,
            [
                {"batch_index": 0, "start_index": 5, "limit": 10},
                {"batch_index": 1, "start_index": 15, "limit": 10},
                {"batch_index": 2, "start_index": 25, "limit": 3},
            ],
        )

    def test_full_batch_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = arguments(Path(temp_dir))
            args.limit = 640
            with self.assertRaisesRegex(ValueError, "confirm-full-run"):
                MODULE.validate_arguments(args)

            args.confirm_full_run = True
            MODULE.validate_arguments(args)

    def test_batch_size_one_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = arguments(Path(temp_dir))
            args.batch_size = 1
            with self.assertRaisesRegex(ValueError, "one Editor per video"):
                MODULE.validate_arguments(args)

    def test_full_run_confirmation_is_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = arguments(Path(temp_dir))
            args.limit = 640
            args.confirm_full_run = True
            command = MODULE.build_server_command(
                args,
                ["--engine-root", "/test/UnrealEngine"],
                start_index=1,
                limit=640,
                mode="--dry-run",
            )

        self.assertIn("--confirm-full-run", command)


class SupervisorRecoveryTests(unittest.TestCase):
    def test_failed_invocation_retries_same_batch_then_advances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = arguments(root)
            completed = [
                subprocess.CompletedProcess([], 1),
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0),
            ]
            with mock.patch.object(
                MODULE.subprocess, "run", side_effect=completed
            ) as runner:
                exit_code = MODULE.run_supervised_batches(
                    args, ["--engine-root", "/test/UnrealEngine"]
                )

            record = MODULE.read_latest_result(root / "missing")
            supervisor = MODULE.json.loads(
                (args.run_root / "runtime/server_editor/supervisor.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertIsNone(record)
        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.call_count, 3)
        commands = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(
            commands[0][commands[0].index("--start-index") + 1], "1"
        )
        self.assertEqual(
            commands[1][commands[1].index("--start-index") + 1], "1"
        )
        self.assertEqual(
            commands[2][commands[2].index("--start-index") + 1], "11"
        )
        self.assertEqual(supervisor["status"], "passed")
        self.assertEqual(
            [len(batch["invocations"]) for batch in supervisor["batches"]],
            [2, 1],
        )


if __name__ == "__main__":
    unittest.main()
