from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run_first_batch_server_production.py"
SPEC = importlib.util.spec_from_file_location("run_first_batch_server_production", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def arguments(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_root=root / "run",
        delivery_root=root / "dataset_v1",
        engine_root=root / "UnrealEngine",
        uproject=root / "datatry_02.uproject",
        graph_root=root / "graph",
        prompt_root=root / "prompts",
        batch_size=50,
        max_invocations_per_batch=2,
        confirm_full_run=True,
    )


class ProductionControllerTests(unittest.TestCase):
    def test_stages_validate_one_editor_fifty_then_complete_640(self) -> None:
        self.assertEqual(
            MODULE.STAGES,
            (
                {"id": "stage_0050", "start_index": 1, "limit": 50, "audit_limit": 50},
                {"id": "stage_0640", "start_index": 51, "limit": 590, "audit_limit": 640},
            ),
        )

    def test_full_audit_command_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = arguments(Path(temp_dir))
            command = MODULE.supervisor_command(
                args,
                start_index=1,
                limit=640,
                mode="--audit-existing",
            )

        self.assertIn("--batch-size", command)
        self.assertEqual(command[command.index("--batch-size") + 1], "50")
        self.assertIn("--confirm-full-run", command)
        self.assertEqual(command[-1], "--audit-existing")

    def test_audit_pass_requires_exact_selected_and_accepted_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_root = Path(temp_dir)
            (run_root / "result.json").write_text(
                json.dumps(
                    {"status": "passed", "selected_count": 50, "accepted_count": 50}
                ),
                encoding="utf-8",
            )
            self.assertTrue(MODULE.audit_passed(run_root, 50))
            self.assertFalse(MODULE.audit_passed(run_root, 100))

    def test_rejects_unaccepted_batch_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = arguments(Path(temp_dir))
            args.batch_size = 10
            with self.assertRaisesRegex(ValueError, "batch-size 50"):
                MODULE.validate_args(args)

    def test_new_run_root_is_not_audited_before_runtime_profile_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_root = Path(temp_dir)
            self.assertFalse(MODULE.can_audit_existing(run_root))
            (run_root / "inputs.lock.json").write_text("{}", encoding="utf-8")
            self.assertFalse(MODULE.can_audit_existing(run_root))
            profile = run_root / "runtime/server_editor/profile.json"
            profile.parent.mkdir(parents=True)
            profile.write_text("{}", encoding="utf-8")
            self.assertTrue(MODULE.can_audit_existing(run_root))

    def test_package_pass_requires_simplified_chains(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            delivery_root = Path(temp_dir)
            videos = delivery_root / "videos"
            videos.mkdir()
            for index in range(1, 641):
                (videos / f"{index}.mp4").touch()
            (delivery_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "status": "package_candidate_pending_release_qa",
                        "counts": {"videos": 640, "chains": 4000, "turns": 15000},
                        "checks": {"all_required_checks": True},
                    }
                ),
                encoding="utf-8",
            )
            (delivery_root / "chains.json").write_text("[]", encoding="utf-8")

            self.assertFalse(MODULE.package_passed(delivery_root))
            (delivery_root / "chains_simple.json").write_text("[]", encoding="utf-8")
            self.assertTrue(MODULE.package_passed(delivery_root))


if __name__ == "__main__":
    unittest.main()
