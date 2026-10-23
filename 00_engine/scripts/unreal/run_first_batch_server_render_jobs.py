#!/usr/bin/env python3
"""Launch a headless server Editor and execute First Batch render jobs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = ROOT / "00_engine"
RENDER_JOBS = ENGINE_ROOT / "scripts" / "unreal" / "run_first_batch_render_jobs.py"
REMOTE_EXEC = ENGINE_ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
DEFAULT_UPROJECT = ENGINE_ROOT / "projects" / "datatry_02" / "datatry_02.uproject"
DEFAULT_GRAPH_ROOT = ENGINE_ROOT / "outputs" / "first_batch_dataset" / "graph_20260824_v1"
DEFAULT_MATRIX_CONFIG = (
    ENGINE_ROOT
    / "scripts"
    / "unreal"
    / "first_batch_local_render_matrix_20260824_v1.json"
)
DEFAULT_DDC = ENGINE_ROOT / "cache" / "ddc"
DEFAULT_RUNTIME_LIB_DIR = (
    ENGINE_ROOT / "runtime" / "ubuntu2204-libs" / "usr" / "lib" / "x86_64-linux-gnu"
)
DEFAULT_NVIDIA_ICD = Path("/etc/vulkan/icd.d/nvidia_icd.json")
TOKYO_STAGING_MAP = (
    "/Game/DataMake/Scenes/TokyoStylized/"
    "L_DM_TokyoStylized_FirstBatchRender_v001"
)
PROFILE_ID = "h200_vulkan_sm6_580_tokyo_v1"
PROFILE_SCHEMA = "first_batch_server_editor_profile_v1"
MINIMUM_DRIVER_MAJOR = 580
RUN_ROOT_TOKEN = "{RUN_ROOT}"
RUNTIME_SESSION_ROOT_TOKEN = "{RUNTIME_SESSION_ROOT}"
LOG_SESSION_ROOT_TOKEN = "{LOG_SESSION_ROOT}"


COMPATIBILITY_ARGUMENTS = (
    "-RenderOffscreen",
    "-vulkan",
    "-sm6",
    "-graphicsadapter=0",
    "-BindlessOff",
    "-gpucrashdebugging",
    "-gpubreadcrumbs",
    "-DisablePlugins=EditorToolset",
    "-ini:Engine:[/Script/Engine.RendererSettings]:r.RayTracing=False",
    "-ini:Engine:[/Script/Engine.RendererSettings]:r.RayTracing.RayTracingProxies.ProjectEnabled=False",
    "-ini:Engine:[ConsoleVariables]:r.VolumetricCloud=0",
    "-ini:Engine:[ConsoleVariables]:r.Vulkan.AllowSynchronization2=1",
    "-ini:Engine:[ConsoleVariables]:r.Vulkan.AllowDynamicRendering=1",
    "-ini:Engine:[ConsoleVariables]:r.Vulkan.AllowSplitBarriers=1",
    "-ini:Engine:[ConsoleVariables]:r.Vulkan.UseMemoryBarrierOpt=1",
    "-ini:Engine:[ConsoleVariables]:r.Vulkan.ForcePSOSingleThreaded=0",
    "-ini:Engine:[ConsoleVariables]:r.TranslucencyLightingVolume=0",
    "-ini:Engine:[ConsoleVariables]:r.PSOPrecaching=0",
    "-ini:Engine:[ConsoleVariables]:r.PostProcessing.PreferCompute=1",
    "-ini:Engine:[ConsoleVariables]:r.Tonemapper.ForceComputeIntermediate=1",
    "-ini:Engine:[ConsoleVariables]:r.Vulkan.DumpStalledGPUAfterSeconds=5",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--engine-root", type=Path, required=True)
    parser.add_argument("--uproject", type=Path, default=DEFAULT_UPROJECT)
    parser.add_argument("--project-name", default="datatry_02")
    parser.add_argument("--graph-root", type=Path, default=DEFAULT_GRAPH_ROOT)
    parser.add_argument("--matrix-config", type=Path, default=DEFAULT_MATRIX_CONFIG)
    parser.add_argument("--ddc-path", type=Path, default=DEFAULT_DDC)
    parser.add_argument("--runtime-lib-dir", type=Path, default=DEFAULT_RUNTIME_LIB_DIR)
    parser.add_argument("--nvidia-icd", type=Path, default=DEFAULT_NVIDIA_ICD)
    parser.add_argument(
        "--ffmpeg-exe",
        type=Path,
        default=(
            Path(os.environ["DM_FFMPEG_EXE"])
            if os.environ.get("DM_FFMPEG_EXE")
            else None
        ),
        help="ffmpeg executable with libx264 support; auto-discovered when omitted.",
    )
    parser.add_argument(
        "--remote-bind-address",
        default="0.0.0.0",
        help="Remote Execution UDP bind address; Linux multicast requires 0.0.0.0.",
    )
    parser.add_argument(
        "--remote-multicast-ttl",
        type=int,
        default=1,
        help="Remote Execution multicast TTL; Linux physical interfaces require 1.",
    )
    parser.add_argument("--startup-timeout-seconds", type=int, default=1800)
    parser.add_argument("--shutdown-timeout-seconds", type=int, default=60)
    parser.add_argument("--allow-unsupported-driver", action="store_true")
    parser.add_argument("--keep-editor", action="store_true")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop the batch after the first failed node instead of continuing.",
    )
    parser.add_argument("--extra-editor-arg", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-existing", action="store_true")
    args, delegated = parser.parse_known_args()
    if delegated[:1] == ["--"]:
        delegated = delegated[1:]
    return args, delegated


def editor_executable(engine_root: Path) -> Path:
    return engine_root / "Engine" / "Binaries" / "Linux" / "UnrealEditor"


def build_editor_command(args: argparse.Namespace, ue_log: Path) -> list[str]:
    return [
        str(editor_executable(args.engine_root.resolve())),
        str(args.uproject.resolve()),
        TOKYO_STAGING_MAP,
        *COMPATIBILITY_ARGUMENTS,
        "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=True",
        "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:RemoteExecutionMulticastGroupEndpoint=239.0.0.1:6766",
        f"-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:RemoteExecutionMulticastBindAddress={args.remote_bind_address}",
        f"-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:RemoteExecutionMulticastTtl={args.remote_multicast_ttl}",
        "-Unattended",
        "-NoSplash",
        "-NoSound",
        "-NoLoadingScreen",
        "-NoScreenMessages",
        "-NoSourceControl",
        "-NoCrashDialog",
        "-windowed",
        "-ResX=640",
        "-ResY=360",
        "-ForceRes",
        "-stdout",
        "-FullStdOutLogOutput",
        f"-AbsLog={ue_log.resolve()}",
        *args.extra_editor_arg,
    ]


def build_render_command(
    args: argparse.Namespace,
    delegated: list[str],
    runtime_profile_path: Path | None,
) -> list[str]:
    command = [
        sys.executable,
        str(RENDER_JOBS),
        "--graph-root",
        str(args.graph_root.resolve()),
        "--run-root",
        str(args.run_root.resolve()),
        "--matrix-config",
        str(args.matrix_config.resolve()),
        "--uproject",
        str(args.uproject.resolve()),
        "--project-name",
        args.project_name,
        "--engine-root",
        str(args.engine_root.resolve()),
    ]
    if runtime_profile_path is not None:
        command.extend(
            ["--runtime-profile-record", str(runtime_profile_path.resolve())]
        )
    if args.dry_run:
        command.append("--dry-run")
    if args.audit_existing:
        command.append("--audit-existing")
    if not args.fail_fast and "--continue-on-error" not in delegated:
        command.append("--continue-on-error")
    command.extend(delegated)
    return command


def build_editor_environment(args: argparse.Namespace, runtime_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    home = runtime_root / "home"
    temp = runtime_root / "tmp"
    ddc = args.ddc_path.resolve()
    for path in (home, temp, ddc):
        path.mkdir(parents=True, exist_ok=True)
    environment["HOME"] = str(home)
    environment["TMPDIR"] = str(temp)
    environment["UE_LocalDataCachePath"] = str(ddc)
    environment["VK_ICD_FILENAMES"] = str(args.nvidia_icd.resolve())
    environment["VK_LOADER_LAYERS_DISABLE"] = "*"
    environment["DM_UE_REMOTE_BIND_ADDRESS"] = args.remote_bind_address
    environment["DM_UE_REMOTE_MULTICAST_TTL"] = str(
        args.remote_multicast_ttl
    )
    runtime_lib_dir = args.runtime_lib_dir.resolve()
    if runtime_lib_dir.is_dir():
        current = environment.get("LD_LIBRARY_PATH", "")
        environment["LD_LIBRARY_PATH"] = (
            f"{runtime_lib_dir}:{current}" if current else str(runtime_lib_dir)
        )
    return environment


def build_render_environment(
    args: argparse.Namespace, ffmpeg_exe: Path
) -> dict[str, str]:
    environment = os.environ.copy()
    environment["DM_FFMPEG_EXE"] = str(ffmpeg_exe)
    environment["DM_UE_REMOTE_BIND_ADDRESS"] = args.remote_bind_address
    environment["DM_UE_REMOTE_MULTICAST_TTL"] = str(
        args.remote_multicast_ttl
    )
    return environment


def stable_runtime_value(
    value: str,
    run_root: Path,
    runtime_session_root: Path | None = None,
    log_session_root: Path | None = None,
) -> str:
    if runtime_session_root is not None:
        value = value.replace(
            str(runtime_session_root.resolve()), RUNTIME_SESSION_ROOT_TOKEN
        )
    if log_session_root is not None:
        value = value.replace(str(log_session_root.resolve()), LOG_SESSION_ROOT_TOKEN)
    return value.replace(str(run_root.resolve()), RUN_ROOT_TOKEN)


def recorded_editor_environment(
    environment: dict[str, str],
    run_root: Path | None = None,
    runtime_session_root: Path | None = None,
    *,
    include_scheduler_identity: bool = False,
) -> dict[str, str]:
    keys = [
        "HOME",
        "TMPDIR",
        "UE_LocalDataCachePath",
        "VK_ICD_FILENAMES",
        "VK_LOADER_LAYERS_DISABLE",
        "CUDA_VISIBLE_DEVICES",
        "DM_UE_REMOTE_BIND_ADDRESS",
        "DM_UE_REMOTE_MULTICAST_TTL",
        "DM_FFMPEG_EXE",
    ]
    if include_scheduler_identity:
        keys.append("SLURM_JOB_ID")
    record = {key: environment.get(key, "") for key in keys}
    if run_root is not None:
        record = {
            key: stable_runtime_value(
                value,
                run_root,
                runtime_session_root=runtime_session_root,
            )
            for key, value in record.items()
        }
    return record


def stable_editor_command(
    command: list[str],
    run_root: Path,
    log_session_root: Path | None = None,
) -> list[str]:
    return [
        stable_runtime_value(
            value,
            run_root,
            log_session_root=log_session_root,
        )
        for value in command
    ]


def reserve_invocation_roots(
    runtime_root: Path, log_root: Path
) -> tuple[str, Path, Path]:
    sessions_root = runtime_root / "sessions"
    for index in range(10000):
        invocation_id = f"invocation_{index:03d}"
        invocation_runtime_root = sessions_root / invocation_id
        try:
            invocation_runtime_root.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        invocation_log_root = log_root / "sessions" / invocation_id
        invocation_log_root.mkdir(parents=True, exist_ok=False)
        return invocation_id, invocation_runtime_root, invocation_log_root
    raise RuntimeError("Unable to reserve a server Editor invocation directory")


def write_session(
    archive_path: Path,
    latest_path: Path,
    session: dict,
) -> None:
    write_json(archive_path, session)
    write_json(latest_path, session)


def discovered_ffmpeg_candidates() -> list[Path]:
    candidates: list[Path] = []
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        candidates.append(Path(system_ffmpeg))

    try:
        import imageio_ffmpeg
    except ImportError:
        pass
    else:
        candidates.append(Path(imageio_ffmpeg.get_ffmpeg_exe()))

    home = Path.home()
    conda_roots = [home / ".conda" / "envs"]
    conda_roots.extend(path / ".conda" / "envs" for path in home.glob("*"))
    for root in conda_roots:
        if not root.is_dir():
            continue
        candidates.extend(
            sorted(
                root.glob(
                    "*/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*"
                )
            )
        )
        candidates.extend(sorted(root.glob("*/bin/ffmpeg")))
    return candidates


def ffmpeg_has_libx264(path: Path) -> bool:
    if not path.is_file() or not os.access(path, os.X_OK):
        return False
    try:
        completed = subprocess.run(
            [str(path), "-hide_banner", "-encoders"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and "libx264" in completed.stdout


def resolve_ffmpeg_exe(configured: Path | None) -> Path:
    candidates = [configured] if configured is not None else discovered_ffmpeg_candidates()
    checked: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in checked:
            continue
        checked.add(resolved)
        if ffmpeg_has_libx264(resolved):
            return resolved
    if configured is not None:
        raise RuntimeError(
            f"Configured ffmpeg is missing, not executable, or lacks libx264: "
            f"{configured}"
        )
    raise RuntimeError(
        "No executable ffmpeg with libx264 support was found; set "
        "DM_FFMPEG_EXE or pass --ffmpeg-exe"
    )


def query_nvidia_gpus() -> list[dict[str, str]]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,uuid,driver_version",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"nvidia-smi failed: {completed.stderr.strip()}")
    records = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) == 3:
            records.append(
                {"name": fields[0], "uuid": fields[1], "driver_version": fields[2]}
            )
    if not records:
        raise RuntimeError("nvidia-smi returned no GPUs")
    return records


def driver_major(version: str) -> int:
    try:
        return int(version.split(".", 1)[0])
    except ValueError as exc:
        raise RuntimeError(f"Unable to parse NVIDIA driver version: {version}") from exc


def validate_gpu(records: list[dict[str, str]], allow_unsupported: bool) -> None:
    h200 = [record for record in records if "H200" in record["name"].upper()]
    if not h200:
        raise RuntimeError(f"No NVIDIA H200 is visible: {records}")
    unsupported = [
        record
        for record in h200
        if driver_major(record["driver_version"]) < MINIMUM_DRIVER_MAJOR
    ]
    if unsupported and not allow_unsupported:
        raise RuntimeError(
            f"Server profile {PROFILE_ID} requires NVIDIA driver "
            f"{MINIMUM_DRIVER_MAJOR}+; "
            f"unsupported H200 devices: {unsupported}"
        )


def remote_command(
    args: argparse.Namespace,
    command: str,
    *,
    discovery_timeout: float,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            args.project_name,
            "--engine-root",
            str(args.engine_root.resolve()),
            "--discovery-timeout",
            str(discovery_timeout),
            "--command",
            command,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def wait_for_editor(
    args: argparse.Namespace,
    process: subprocess.Popen[str],
) -> dict:
    command = (
        "import unreal, json; "
        "print('DM_SERVER_EDITOR_READY=' + json.dumps({"
        f"'project':{args.project_name!r},'ready':True}}))"
    )
    deadline = time.monotonic() + args.startup_timeout_seconds
    last_error = "Remote Execution has not responded"
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(
                f"Unreal Editor exited before Remote Execution was ready: {exit_code}"
            )
        try:
            completed = remote_command(
                args,
                command,
                discovery_timeout=3,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            last_error = "Remote Execution readiness probe timed out"
        else:
            if completed.returncode == 0 and "DM_SERVER_EDITOR_READY=" in completed.stdout:
                return json.loads(completed.stdout)
            last_error = (completed.stderr or completed.stdout).strip()[-2000:]
        time.sleep(5)
    raise TimeoutError(
        f"Unreal Editor was not remotely reachable within "
        f"{args.startup_timeout_seconds} seconds: {last_error}"
    )


def stop_editor(
    args: argparse.Namespace,
    process: subprocess.Popen[str],
) -> dict:
    exit_code = process.poll()
    if exit_code is not None:
        return {"method": "already_exited", "exit_code": exit_code}
    remote_exit_code = None
    try:
        completed = remote_command(
            args,
            "import unreal; unreal.SystemLibrary.quit_editor()",
            discovery_timeout=5,
            timeout=15,
        )
        remote_exit_code = completed.returncode
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        process.wait(timeout=args.shutdown_timeout_seconds)
        return {
            "method": "graceful",
            "exit_code": process.poll(),
            "remote_exit_code": remote_exit_code,
        }
    except subprocess.TimeoutExpired:
        process.terminate()
    try:
        process.wait(timeout=15)
        return {
            "method": "terminated_after_timeout",
            "exit_code": process.poll(),
            "remote_exit_code": remote_exit_code,
        }
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=15)
        return {
            "method": "killed_after_timeout",
            "exit_code": process.poll(),
            "remote_exit_code": remote_exit_code,
        }


def main() -> int:
    args, delegated = parse_args()
    existing_profile = args.run_root.resolve() / "runtime" / "server_editor" / "profile.json"
    runtime_profile = (
        existing_profile
        if args.audit_existing and existing_profile.is_file()
        else None
    )
    render_command = build_render_command(args, delegated, runtime_profile)
    if args.dry_run or args.audit_existing:
        return subprocess.run(render_command, check=False).returncode

    engine = editor_executable(args.engine_root.resolve())
    if not engine.is_file():
        raise FileNotFoundError(f"Unreal Editor is missing: {engine}")
    if not args.uproject.is_file():
        raise FileNotFoundError(f"Unreal project is missing: {args.uproject}")
    if not args.nvidia_icd.is_file():
        raise FileNotFoundError(f"NVIDIA Vulkan ICD is missing: {args.nvidia_icd}")

    gpu_records = query_nvidia_gpus()
    validate_gpu(gpu_records, args.allow_unsupported_driver)
    ffmpeg_exe = resolve_ffmpeg_exe(args.ffmpeg_exe)
    os.environ["DM_UE_REMOTE_BIND_ADDRESS"] = args.remote_bind_address
    os.environ["DM_UE_REMOTE_MULTICAST_TTL"] = str(
        args.remote_multicast_ttl
    )

    run_root = args.run_root.resolve()
    runtime_root = run_root / "runtime" / "server_editor"
    log_root = run_root / "logs" / "server_editor"
    runtime_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    invocation_id, invocation_runtime_root, invocation_log_root = (
        reserve_invocation_roots(runtime_root, log_root)
    )
    ue_log = invocation_log_root / "unreal_editor.log"
    stdout_log = invocation_log_root / "unreal_editor_stdout.log"
    profile_path = runtime_root / "profile.json"
    session_path = invocation_runtime_root / "session.json"
    latest_session_path = runtime_root / "session.json"
    editor_command = build_editor_command(args, ue_log)
    environment = build_editor_environment(args, invocation_runtime_root)
    environment["DM_FFMPEG_EXE"] = str(ffmpeg_exe)
    render_environment = build_render_environment(args, ffmpeg_exe)
    profile = {
        "schema_version": PROFILE_SCHEMA,
        "profile_id": PROFILE_ID,
        "status": "frozen_candidate_pending_batch_acceptance",
        "minimum_nvidia_driver_major": MINIMUM_DRIVER_MAJOR,
        "launcher": str(Path(__file__).resolve()),
        "launcher_sha256": sha256_file(Path(__file__).resolve()),
        "editor_executable": str(engine.resolve()),
        "editor_executable_sha256": sha256_file(engine.resolve()),
        "ffmpeg_executable": str(ffmpeg_exe),
        "ffmpeg_executable_sha256": sha256_file(ffmpeg_exe),
        "uproject": str(args.uproject.resolve()),
        "uproject_sha256": sha256_file(args.uproject.resolve()),
        "tokyo_staging_map": TOKYO_STAGING_MAP,
        "command": stable_editor_command(
            editor_command,
            run_root,
            log_session_root=invocation_log_root,
        ),
        "environment": recorded_editor_environment(
            environment,
            run_root,
            runtime_session_root=invocation_runtime_root,
        ),
        "gpus": gpu_records,
    }
    write_json(profile_path, profile)
    render_command = build_render_command(args, delegated, profile_path)

    process: subprocess.Popen[str] | None = None
    with stdout_log.open("w", encoding="utf-8") as stdout_handle:
        try:
            process = subprocess.Popen(
                editor_command,
                env=environment,
                stdout=stdout_handle,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            session = {
                "schema_version": 1,
                "profile_id": PROFILE_ID,
                "invocation_id": invocation_id,
                "started_at_utc": utc_now(),
                "pid": process.pid,
                "status": "starting",
                "editor_process_contract": {
                    "process_count": 1,
                    "scope": "all_selected_nodes_in_this_invocation",
                    "restart_policy": "invocation_boundary_or_editor_failure_only",
                },
                "editor_command": editor_command,
                "editor_environment": recorded_editor_environment(
                    environment,
                    include_scheduler_identity=True,
                ),
                "render_command": render_command,
            }
            write_session(session_path, latest_session_path, session)
            ready = wait_for_editor(args, process)
            session.update(
                {
                    "ready_at_utc": utc_now(),
                    "status": "ready",
                    "remote_execution": ready,
                }
            )
            write_session(session_path, latest_session_path, session)
            completed = subprocess.run(
                render_command,
                check=False,
                env=render_environment,
            )
            result_path = run_root / "result.json"
            render_summary = (
                json.loads(result_path.read_text(encoding="utf-8"))
                if result_path.is_file()
                else None
            )
            session.update(
                {
                    "render_finished_at_utc": utc_now(),
                    "render_exit_code": completed.returncode,
                    "render_summary": render_summary,
                    "status": "render_finished",
                }
            )
            write_session(session_path, latest_session_path, session)
            return completed.returncode
        finally:
            shutdown = None
            if process is not None and not args.keep_editor:
                shutdown = stop_editor(args, process)
            elif process is not None:
                shutdown = {
                    "method": "retained",
                    "exit_code": process.poll(),
                }
            if process is not None:
                session = (
                    json.loads(session_path.read_text(encoding="utf-8"))
                    if session_path.is_file()
                    else {"schema_version": 1, "profile_id": PROFILE_ID}
                )
                session["editor_shutdown"] = shutdown
                session["editor_exit_code"] = process.poll()
                session["ended_at_utc"] = utc_now()
                session["status"] = (
                    "editor_retained"
                    if args.keep_editor and process.poll() is None
                    else "ended"
                )
                write_session(session_path, latest_session_path, session)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise
