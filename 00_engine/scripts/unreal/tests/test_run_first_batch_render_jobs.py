from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "run_first_batch_render_jobs.py"
SPEC = importlib.util.spec_from_file_location("run_first_batch_render_jobs", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

GRAPH_FIXTURE = None
GRAPH_FIXTURE_TEMP = None


def setUpModule() -> None:
    global GRAPH_FIXTURE, GRAPH_FIXTURE_TEMP
    if MODULE.DEFAULT_GRAPH_ROOT.is_dir():
        GRAPH_FIXTURE = MODULE.DEFAULT_GRAPH_ROOT
        return
    GRAPH_FIXTURE_TEMP = tempfile.TemporaryDirectory()
    GRAPH_FIXTURE = Path(GRAPH_FIXTURE_TEMP.name) / "graph"
    builder = MODULE.ROOT / "00_engine/scripts/dataset/build_first_batch_config_graph_v1.py"
    source = MODULE.ROOT / "00_engine/scripts/dataset/first_batch_graph_source_20260824_v1.json"
    subprocess.run(
        [
            sys.executable,
            str(builder),
            "--source",
            str(source),
            "--output-dir",
            str(GRAPH_FIXTURE),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def tearDownModule() -> None:
    if GRAPH_FIXTURE_TEMP is not None:
        GRAPH_FIXTURE_TEMP.cleanup()


def context_args(run_root: Path, *, dry_run: bool = True) -> argparse.Namespace:
    run_root.mkdir(parents=True, exist_ok=True)
    uproject = run_root / "datatry_02.uproject"
    uproject.write_text("{}\n", encoding="utf-8")
    return argparse.Namespace(
        graph_root=GRAPH_FIXTURE or MODULE.DEFAULT_GRAPH_ROOT,
        run_root=run_root,
        matrix_config=MODULE.DEFAULT_MATRIX_CONFIG,
        uproject=uproject,
        project_name="datatry_02",
        engine_root=None,
        dry_run=dry_run,
        audit_existing=False,
    )


class FrozenGraphContractTests(unittest.TestCase):
    def test_all_640_jobs_bind_to_frozen_assets_and_camera_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = MODULE.load_context(context_args(Path(temp_dir)))
            rows = [MODULE.node_to_matrix_row(context, job) for job in context.jobs]

        self.assertEqual(len(rows), 640)
        self.assertEqual(len({row["node_id"] for row in rows}), 640)
        self.assertEqual(
            {
                camera_id: (
                    value["camera_section_index"],
                    value["start_frame_inclusive"],
                    value["end_frame_exclusive"],
                )
                for camera_id, value in context.cameras_by_id.items()
            },
            {
                "near": (0, 0, 150),
                "far": (1, 150, 300),
                "high": (2, 300, 450),
                "side": (3, 450, 600),
            },
        )
        self.assertEqual({row["expression_id"] for row in rows}, {"happy"})

    def test_full_non_dry_run_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = MODULE.load_context(context_args(Path(temp_dir)))
        args = argparse.Namespace(
            node_id=None,
            start_index=1,
            limit=None,
            dry_run=False,
            audit_existing=False,
            confirm_full_run=False,
        )

        with self.assertRaisesRegex(MODULE.ContractError, "confirm-full-run"):
            MODULE.select_jobs(args, context.jobs)


class InputLockTests(unittest.TestCase):
    def test_legacy_text_hash_accepts_lf_and_crlf_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lf = root / "lf.json"
            crlf = root / "crlf.json"
            lf.write_bytes(b'{"value": 1}\n')
            crlf.write_bytes(b'{"value": 1}\r\n')

            expected = MODULE.sha256_file(crlf)
            candidates = MODULE.legacy_text_sha256_candidates(lf)

        self.assertIn(expected, candidates)

    def test_locked_json_hash_is_independent_of_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lf = root / "lf.json"
            crlf = root / "crlf.json"
            lf.write_bytes(b'{"value": 1}\n')
            crlf.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')

            lf_payload, lf_mode = MODULE.normalized_locked_input(lf)
            crlf_payload, crlf_mode = MODULE.normalized_locked_input(crlf)

        self.assertEqual(lf_mode, "canonical_json_v1")
        self.assertEqual(crlf_mode, "canonical_json_v1")
        self.assertEqual(lf_payload, crlf_payload)

    def test_input_lock_is_reusable_and_contains_no_windows_file_uri(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = MODULE.load_context(
                context_args(Path(temp_dir), dry_run=False)
            )
            context.run_root.mkdir(parents=True, exist_ok=True)
            MODULE.ensure_input_lock(context)
            first_hash = context.input_lock_sha256
            lock = MODULE.read_json(context.run_root / "inputs.lock.json")

            MODULE.ensure_input_lock(context)

        self.assertEqual(context.input_lock_sha256, first_hash)
        uris = [entry["uri"] for entry in lock["inputs"]]
        self.assertIn("project://datatry_02/datatry_02.uproject", uris)
        self.assertIn(
            "repo://00_engine/scripts/unreal/ue_build_first_batch_20s_sequence.py",
            uris,
        )
        self.assertIn(
            "repo://00_engine/scripts/unreal/ue_build_first_batch_render_profile.py",
            uris,
        )
        self.assertIn(
            "repo://00_engine/scripts/unreal/ue_start_first_batch_local_sample_render.py",
            uris,
        )
        self.assertFalse(any(uri.startswith("file://") for uri in uris))

    def test_run_root_rejects_changed_immutable_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = MODULE.load_context(
                context_args(Path(temp_dir), dry_run=False)
            )
            context.run_root.mkdir(parents=True, exist_ok=True)
            MODULE.ensure_input_lock(context)
            context.project_name = "different_project"

            with self.assertRaisesRegex(MODULE.ContractError, "different immutable"):
                MODULE.ensure_input_lock(context)


class LeaseTests(unittest.TestCase):
    def test_live_lease_blocks_and_stale_lease_is_archived(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "node.lock"
            first = MODULE.FileLease(
                path,
                owner="first",
                stale_after_seconds=3600,
            ).acquire()
            try:
                with self.assertRaises(MODULE.LeaseUnavailable):
                    MODULE.FileLease(
                        path,
                        owner="second",
                        stale_after_seconds=3600,
                    ).acquire()
                old = time.time() - 7200
                os.utime(path, (old, old))
                replacement = MODULE.FileLease(
                    path,
                    owner="replacement",
                    stale_after_seconds=60,
                ).acquire()
                replacement.release()
                self.assertTrue(list(Path(temp_dir).glob("node.lock.stale.*")))
            finally:
                first.release()

    def test_release_tolerates_external_lock_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "node.lock"
            lease = MODULE.FileLease(
                path,
                owner="test",
                stale_after_seconds=60,
            ).acquire()
            path.unlink()
            lease.release()
            self.assertFalse(lease.acquired)


class SidecarResumeTests(unittest.TestCase):
    def test_promoted_output_is_hash_valid_then_rejected_after_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = MODULE.load_context(
                context_args(Path(temp_dir), dry_run=False)
            )
            context.run_root.mkdir(parents=True, exist_ok=True)
            MODULE.ensure_input_lock(context)
            job = context.jobs[0]
            row = MODULE.node_to_matrix_row(context, job)
            source = context.run_root / "attempt.mp4"
            source.write_bytes(b"deterministic-test-video")
            render_report = {
                "status": "passed",
                "resolution": [2560, 1440],
                "fps": 30,
                "frame_count": 150,
                "duration_seconds": 5.0,
                "map": "/Game/TestMap",
                "sequence": "/Game/TestSequence",
                "automation_contract": {
                    "pose_driver_contract": {"passed": True},
                    "temporal_motion_contract": {"passed": True},
                },
            }
            sidecar = MODULE.build_sidecar(
                context,
                job,
                row,
                0,
                render_report,
                {"actor_name": "TestActor"},
                {"output_sequence": "/Game/TestSequence"},
                source,
            )
            video = MODULE.promote_attempt(context, job, sidecar, source)

            accepted = MODULE.validate_accepted_node(
                context, job, verify_hash=True
            )
            self.assertIsNotNone(accepted)
            video.write_bytes(b"tampered")
            self.assertIsNone(
                MODULE.validate_accepted_node(context, job, verify_hash=True)
            )

    def test_hash_valid_output_resumes_without_calling_unreal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = MODULE.load_context(
                context_args(Path(temp_dir), dry_run=False)
            )
            context.run_root.mkdir(parents=True, exist_ok=True)
            MODULE.ensure_input_lock(context)
            job = context.jobs[0]
            row = MODULE.node_to_matrix_row(context, job)
            source = context.run_root / "attempt.mp4"
            source.write_bytes(b"resume-test-video")
            render_report = {
                "status": "passed",
                "resolution": [2560, 1440],
                "fps": 30,
                "frame_count": 150,
                "duration_seconds": 5.0,
                "map": "/Game/TestMap",
                "sequence": "/Game/TestSequence",
                "automation_contract": {
                    "pose_driver_contract": {"passed": True},
                    "temporal_motion_contract": {"passed": True},
                },
            }
            sidecar = MODULE.build_sidecar(
                context,
                job,
                row,
                0,
                render_report,
                {"actor_name": "TestActor"},
                {"output_sequence": "/Game/TestSequence"},
                source,
            )
            MODULE.promote_attempt(context, job, sidecar, source)
            args = argparse.Namespace(
                lease_timeout_seconds=60,
                timeout_seconds=60,
                keep_attempt_artifacts=False,
                continue_on_error=False,
            )

            with mock.patch.object(
                MODULE.matrix,
                "stage_look",
                side_effect=AssertionError("Unreal must not be called on resume"),
            ):
                result = MODULE.run_one_job(context, job, args)

        self.assertEqual(result["resume"], "reused")
        self.assertEqual(result["status"], "accepted")


class ChildProcessRoutingTests(unittest.TestCase):
    def test_matrix_passes_project_and_engine_to_sequence_runner(self) -> None:
        module = MODULE.matrix
        module.configure_remote("server_project", Path("C:/UE/UE_5.8"))
        completed = mock.Mock(stdout=json.dumps({"success": True}))
        with mock.patch.object(module, "run_command", return_value=completed) as run:
            report = module.build_sequence(
                {
                    "unreal": {
                        "source_sequence_package": "/Game/Source",
                        "workspace_sequence_package": "/Game/Output",
                    }
                },
                {"action_id": "ACT_TEST", "expression_id": "happy"},
                "Actor",
            )

        command = run.call_args.args[0]
        self.assertTrue(report["success"])
        self.assertIn("--project-name", command)
        self.assertIn("server_project", command)
        self.assertIn("--engine-root", command)


if __name__ == "__main__":
    unittest.main()
