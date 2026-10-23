from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "run_first_batch_server_render_jobs.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_first_batch_server_render_jobs", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def arguments(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_root=root / "run",
        engine_root=root / "UnrealEngine",
        uproject=root / "datatry_02.uproject",
        project_name="datatry_02",
        graph_root=root / "graph",
        matrix_config=root / "matrix.json",
        ddc_path=root / "ddc",
        runtime_lib_dir=root / "runtime-libs",
        nvidia_icd=root / "nvidia_icd.json",
        ffmpeg_exe=None,
        remote_bind_address="0.0.0.0",
        remote_multicast_ttl=1,
        startup_timeout_seconds=1800,
        shutdown_timeout_seconds=60,
        allow_unsupported_driver=False,
        keep_editor=False,
        fail_fast=False,
        extra_editor_arg=[],
        dry_run=False,
        audit_existing=False,
    )


class EditorCommandTests(unittest.TestCase):
    def test_server_command_uses_accepted_compatibility_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command = MODULE.build_editor_command(
                arguments(root), root / "unreal.log"
            )

        expected = {
            "-RenderOffscreen",
            "-vulkan",
            "-sm6",
            "-BindlessOff",
            "-DisablePlugins=EditorToolset",
            "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:RemoteExecutionMulticastBindAddress=0.0.0.0",
            "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:RemoteExecutionMulticastTtl=1",
            "-ini:Engine:[/Script/Engine.RendererSettings]:r.RayTracing=False",
            "-ini:Engine:[ConsoleVariables]:r.TranslucencyLightingVolume=0",
            "-ini:Engine:[ConsoleVariables]:r.PSOPrecaching=0",
            "-ini:Engine:[ConsoleVariables]:r.PostProcessing.PreferCompute=1",
            "-ini:Engine:[ConsoleVariables]:r.Tonemapper.ForceComputeIntermediate=1",
        }
        self.assertTrue(expected.issubset(command))
        self.assertIn(MODULE.TOKYO_STAGING_MAP, command)

    def test_server_command_excludes_short_lived_pixel_probe_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command = MODULE.build_editor_command(
                arguments(root), root / "unreal.log"
            )

        joined = " ".join(command)
        self.assertNotIn("-game", command)
        self.assertNotIn("-BENCHMARK", command)
        self.assertNotIn("-BENCHMARKSECONDS", joined)
        self.assertNotIn("HighResShot", joined)
        self.assertNotIn("-ExecCmds", joined)

    def test_formal_executor_receives_runtime_profile_and_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = arguments(root)
            profile = root / "profile.json"
            command = MODULE.build_render_command(
                args,
                ["--node-id", "n_test"],
                profile,
            )

        self.assertIn("--runtime-profile-record", command)
        self.assertIn(str(profile.resolve()), command)
        self.assertIn("--continue-on-error", command)
        self.assertEqual(command[-2:], ["--node-id", "n_test"])

    def test_fail_fast_does_not_enable_continue_on_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = arguments(root)
            args.fail_fast = True
            command = MODULE.build_render_command(
                args,
                ["--node-id", "n_test"],
                root / "profile.json",
            )

        self.assertNotIn("--continue-on-error", command)

    def test_audit_can_reuse_existing_server_profile_without_editor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = arguments(root)
            profile = args.run_root / "runtime/server_editor/profile.json"
            profile.parent.mkdir(parents=True)
            profile.write_text("{}\n", encoding="utf-8")

            command = MODULE.build_render_command(args, [], profile)

        self.assertIn("--runtime-profile-record", command)
        self.assertIn(str(profile.resolve()), command)


class EnvironmentAndGpuTests(unittest.TestCase):
    def test_editor_environment_uses_workspace_ddc_and_forced_icd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = arguments(root)
            args.runtime_lib_dir.mkdir()
            environment = MODULE.build_editor_environment(
                args, root / "runtime"
            )

        self.assertEqual(
            environment["UE_LocalDataCachePath"], str((root / "ddc").resolve())
        )
        self.assertEqual(
            environment["VK_ICD_FILENAMES"],
            str((root / "nvidia_icd.json").resolve()),
        )
        self.assertEqual(environment["VK_LOADER_LAYERS_DISABLE"], "*")
        self.assertEqual(
            environment["DM_UE_REMOTE_BIND_ADDRESS"], "0.0.0.0"
        )
        self.assertEqual(environment["DM_UE_REMOTE_MULTICAST_TTL"], "1")
        self.assertTrue(
            environment["LD_LIBRARY_PATH"].startswith(
                str((root / "runtime-libs").resolve())
            )
        )

    def test_render_environment_keeps_user_home_and_adds_runtime_connections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = arguments(root)
            ffmpeg = root / "ffmpeg"
            with mock.patch.dict(os.environ, {"HOME": "/user-home"}, clear=True):
                environment = MODULE.build_render_environment(args, ffmpeg)

        self.assertEqual(environment["HOME"], "/user-home")
        self.assertEqual(environment["DM_FFMPEG_EXE"], str(ffmpeg))
        self.assertEqual(environment["DM_UE_REMOTE_BIND_ADDRESS"], "0.0.0.0")
        self.assertEqual(environment["DM_UE_REMOTE_MULTICAST_TTL"], "1")

    def test_profile_runtime_paths_are_stable_across_run_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args_a = arguments(root)
            args_b = arguments(root)
            args_a.run_root = root / "run-a"
            args_b.run_root = root / "run-b"
            command_a = MODULE.build_editor_command(
                args_a, args_a.run_root / "logs" / "unreal.log"
            )
            command_b = MODULE.build_editor_command(
                args_b, args_b.run_root / "logs" / "unreal.log"
            )
            environment_a = {
                "HOME": str(args_a.run_root / "runtime" / "home"),
                "TMPDIR": str(args_a.run_root / "runtime" / "tmp"),
            }
            environment_b = {
                "HOME": str(args_b.run_root / "runtime" / "home"),
                "TMPDIR": str(args_b.run_root / "runtime" / "tmp"),
            }

            self.assertEqual(
                MODULE.stable_editor_command(command_a, args_a.run_root),
                MODULE.stable_editor_command(command_b, args_b.run_root),
            )
            self.assertEqual(
                MODULE.recorded_editor_environment(
                    environment_a, args_a.run_root
                ),
                MODULE.recorded_editor_environment(
                    environment_b, args_b.run_root
                ),
            )

    def test_profile_is_stable_across_recovery_invocations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = arguments(root)
            runtime_a = args.run_root / "runtime/server_editor/sessions/invocation_000"
            runtime_b = args.run_root / "runtime/server_editor/sessions/invocation_001"
            log_a = args.run_root / "logs/server_editor/sessions/invocation_000"
            log_b = args.run_root / "logs/server_editor/sessions/invocation_001"
            env_a = {"HOME": str(runtime_a / "home"), "TMPDIR": str(runtime_a / "tmp")}
            env_b = {"HOME": str(runtime_b / "home"), "TMPDIR": str(runtime_b / "tmp")}
            command_a = MODULE.build_editor_command(args, log_a / "unreal.log")
            command_b = MODULE.build_editor_command(args, log_b / "unreal.log")

        self.assertEqual(
            MODULE.stable_editor_command(command_a, args.run_root, log_a),
            MODULE.stable_editor_command(command_b, args.run_root, log_b),
        )
        self.assertEqual(
            MODULE.recorded_editor_environment(env_a, args.run_root, runtime_a),
            MODULE.recorded_editor_environment(env_b, args.run_root, runtime_b),
        )

    def test_scheduler_job_id_is_session_evidence_not_profile_identity(self) -> None:
        environment = {"SLURM_JOB_ID": "117924", "HOME": "/tmp/home"}

        profile_environment = MODULE.recorded_editor_environment(environment)
        session_environment = MODULE.recorded_editor_environment(
            environment,
            include_scheduler_identity=True,
        )

        self.assertNotIn("SLURM_JOB_ID", profile_environment)
        self.assertEqual(session_environment["SLURM_JOB_ID"], "117924")

    def test_invocation_roots_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = MODULE.reserve_invocation_roots(root / "runtime", root / "logs")
            second = MODULE.reserve_invocation_roots(root / "runtime", root / "logs")

        self.assertEqual(first[0], "invocation_000")
        self.assertEqual(second[0], "invocation_001")

    def test_gpu_gate_accepts_580_and_rejects_565(self) -> None:
        MODULE.validate_gpu(
            [
                {
                    "name": "NVIDIA H200",
                    "uuid": "GPU-test",
                    "driver_version": "580.126.20",
                }
            ],
            False,
        )
        with self.assertRaisesRegex(RuntimeError, "driver 580"):
            MODULE.validate_gpu(
                [
                    {
                        "name": "NVIDIA H200",
                        "uuid": "GPU-test",
                        "driver_version": "565.57.01",
                    }
                ],
                False,
            )

    def test_explicit_ffmpeg_requires_libx264(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "ffmpeg"
            executable.touch(mode=0o755)
            with mock.patch.object(
                MODULE, "ffmpeg_has_libx264", return_value=True
            ):
                self.assertEqual(
                    MODULE.resolve_ffmpeg_exe(executable), executable.resolve()
                )

            with mock.patch.object(
                MODULE, "ffmpeg_has_libx264", return_value=False
            ):
                with self.assertRaisesRegex(RuntimeError, "lacks libx264"):
                    MODULE.resolve_ffmpeg_exe(executable)


class EditorShutdownTests(unittest.TestCase):
    def test_graceful_shutdown_is_recorded(self) -> None:
        process = mock.Mock()
        process.poll.side_effect = [None, 0]
        process.wait.return_value = 0
        completed = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as temp_dir:
            args = arguments(Path(temp_dir))
            with mock.patch.object(
                MODULE, "remote_command", return_value=completed
            ):
                shutdown = MODULE.stop_editor(args, process)

        self.assertEqual(shutdown["method"], "graceful")
        self.assertEqual(shutdown["exit_code"], 0)
        self.assertEqual(shutdown["remote_exit_code"], 0)
        process.terminate.assert_not_called()

    def test_shutdown_timeout_terminates_editor(self) -> None:
        process = mock.Mock()
        process.poll.side_effect = [None, 1]
        process.wait.side_effect = [
            subprocess.TimeoutExpired("UnrealEditor", 60),
            1,
        ]
        completed = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as temp_dir:
            args = arguments(Path(temp_dir))
            with mock.patch.object(
                MODULE, "remote_command", return_value=completed
            ):
                shutdown = MODULE.stop_editor(args, process)

        self.assertEqual(shutdown["method"], "terminated_after_timeout")
        self.assertEqual(shutdown["exit_code"], 1)
        process.terminate.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
