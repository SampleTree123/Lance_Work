#!/usr/bin/env python3
"""Execute frozen First Batch render jobs with resumable node-level state."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import uuid


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_first_batch_render_matrix as matrix  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = ROOT / "00_engine"
DEFAULT_GRAPH_ROOT = (
    ENGINE_ROOT / "outputs" / "first_batch_dataset" / "graph_20260824_v1"
)
DEFAULT_MATRIX_CONFIG = (
    ENGINE_ROOT
    / "scripts"
    / "unreal"
    / "first_batch_local_render_matrix_20260824_v1.json"
)
DEFAULT_UPROJECT = ENGINE_ROOT / "projects" / "datatry_02" / "datatry_02.uproject"
LOCK_SCHEMA = "first_batch_render_input_lock_v1"
RUN_SCHEMA = "first_batch_render_run_v1"
SIDECAR_SCHEMA = "first_batch_node_sidecar_v1"
STATE_SCHEMA = "first_batch_render_node_state_v1"
MEDIA_MANIFEST_SCHEMA = "first_batch_media_manifest_v1"


class ContractError(RuntimeError):
    """Raised when immutable graph or output contracts are invalid."""


class LeaseUnavailable(RuntimeError):
    """Raised when another process owns a live lease."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: object) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def legacy_text_sha256_candidates(path: Path) -> set[str]:
    payload = path.read_bytes()
    normalized = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    crlf = normalized.replace(b"\n", b"\r\n")
    return {sha256_bytes(payload), sha256_bytes(normalized), sha256_bytes(crlf)}


def normalized_locked_input(path: Path) -> tuple[bytes, str]:
    suffix = path.suffix.lower()
    if suffix in {".json", ".uproject"}:
        payload = canonical_json(read_json(path)).encode("utf-8")
        return payload, "canonical_json_v1"
    if suffix == ".jsonl":
        records = read_jsonl(path)
        payload = ("\n".join(canonical_json(record) for record in records) + "\n").encode(
            "utf-8"
        )
        return payload, "canonical_jsonl_v1"
    payload = path.read_bytes()
    if suffix in {".py", ".ps1", ".sh", ".cmd"}:
        payload = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return payload, "text_lf_v1"
    return payload, "raw_bytes_v1"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_write_json(path: Path, payload: object) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Unable to read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Expected a JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ContractError(
                        f"Expected an object at {path}:{line_number}"
                    )
                records.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Unable to read JSONL {path}: {exc}") from exc
    return records


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(payload) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def repo_uri(path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(ROOT)
    except ValueError:
        return f"file://{resolved.as_posix()}"
    return f"repo://{relative.as_posix()}"


def git_state() -> dict:
    revision = "unknown"
    dirty = None
    try:
        revision_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if revision_result.returncode == 0:
            revision = revision_result.stdout.strip()
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if status_result.returncode == 0:
            dirty = bool(status_result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {"revision": revision, "dirty": dirty}


class FileLease(AbstractContextManager["FileLease"]):
    def __init__(
        self,
        path: Path,
        *,
        owner: str,
        stale_after_seconds: int,
        wait_seconds: float = 0.0,
    ) -> None:
        self.path = path
        self.owner = owner
        self.stale_after_seconds = stale_after_seconds
        self.wait_seconds = wait_seconds
        self.lease_id = uuid.uuid4().hex
        self.acquired = False

    def _payload(self) -> dict:
        return {
            "schema_version": 1,
            "lease_id": self.lease_id,
            "owner": self.owner,
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
            "created_at_utc": utc_now(),
        }

    def _archive(self, reason: str) -> bool:
        archived = self.path.with_name(
            f"{self.path.name}.{reason}.{int(time.time())}.{uuid.uuid4().hex[:8]}"
        )
        try:
            os.replace(self.path, archived)
        except FileNotFoundError:
            pass
        return True

    def _owner_process_is_dead(self) -> bool:
        try:
            payload = read_json(self.path)
        except (ContractError, FileNotFoundError):
            return False
        if payload.get("hostname") != socket.gethostname():
            return False
        pid = payload.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except (PermissionError, OSError):
            return False
        return False

    def _archive_stale(self) -> bool:
        try:
            age = time.time() - self.path.stat().st_mtime
        except FileNotFoundError:
            return True
        if self._owner_process_is_dead():
            return self._archive("orphaned")
        if age <= self.stale_after_seconds:
            return False
        return self._archive("stale")

    def acquire(self) -> "FileLease":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.wait_seconds
        while True:
            try:
                descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                if self._archive_stale():
                    continue
                if time.monotonic() >= deadline:
                    raise LeaseUnavailable(f"Live lease exists: {self.path}")
                time.sleep(0.2)
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(self._payload(), ensure_ascii=False, indent=2))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            self.acquired = True
            return self

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            try:
                payload = read_json(self.path)
            except ContractError:
                payload = {}
            if payload.get("lease_id") == self.lease_id:
                self.path.unlink(missing_ok=True)
        finally:
            self.acquired = False

    def __enter__(self) -> "FileLease":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


@dataclass
class RenderContext:
    graph_root: Path
    run_root: Path
    matrix_config_path: Path
    source_manifest: dict
    required_exports: dict
    matrix_config: dict
    nodes: list[dict]
    jobs: list[dict]
    nodes_by_id: dict[str, dict]
    looks_by_id: dict[str, dict]
    actions_by_id: dict[str, dict]
    cameras_by_id: dict[str, dict]
    uproject: Path
    project_name: str
    engine_root: Path | None
    runtime_profile_path: Path | None = None
    runtime_profile: dict | None = None
    input_fingerprint: str = ""
    input_lock_sha256: str = ""


def camera_contract(matrix_config: dict) -> dict[str, dict]:
    cameras: dict[str, dict] = {}
    for sample in matrix_config.get("samples", []):
        camera_id = str(sample.get("camera_id", "")).lower()
        if not camera_id:
            continue
        value = {
            "camera_section_index": int(sample["camera_section_index"]),
            "start_frame_inclusive": int(sample["start_frame_inclusive"]),
            "end_frame_exclusive": int(sample["end_frame_exclusive"]),
        }
        existing = cameras.get(camera_id)
        if existing is not None and existing != value:
            raise ContractError(f"Conflicting camera contract for {camera_id}")
        cameras[camera_id] = value
    if set(cameras) != {"near", "far", "high", "side"}:
        raise ContractError(f"Incomplete camera contract: {sorted(cameras)}")
    return cameras


def load_context(args: argparse.Namespace) -> RenderContext:
    graph_root = args.graph_root.resolve()
    run_root = args.run_root.resolve()
    matrix_config_path = args.matrix_config.resolve()
    source_manifest = read_json(graph_root / "source_manifest.json")
    required_exports = read_json(graph_root / "required_exports.json")
    matrix_config = read_json(matrix_config_path)
    nodes = read_jsonl(graph_root / "nodes.jsonl")
    jobs = read_jsonl(graph_root / "render_jobs.jsonl")

    if source_manifest.get("status") != "frozen":
        raise ContractError("Source manifest is not frozen")
    if matrix_config.get("status") != "frozen_for_local_render":
        raise ContractError("Matrix configuration is not frozen")
    if len(nodes) != int(source_manifest.get("expected_nodes", -1)):
        raise ContractError("Node count does not match source manifest")
    if len(jobs) != int(source_manifest.get("expected_render_jobs", -1)):
        raise ContractError("Render Job count does not match source manifest")

    nodes_by_id: dict[str, dict] = {}
    for node in nodes:
        node_id = str(node.get("node_id", ""))
        if not node_id or node_id in nodes_by_id:
            raise ContractError(f"Invalid or duplicate node_id: {node_id!r}")
        if sha256_json(node.get("config")) != node.get("config_sha256"):
            raise ContractError(f"Node config hash mismatch: {node_id}")
        nodes_by_id[node_id] = node

    render_job_ids: set[str] = set()
    job_nodes: set[str] = set()
    for job in jobs:
        render_job_id = str(job.get("render_job_id", ""))
        node_id = str(job.get("node_id", ""))
        if not render_job_id or render_job_id in render_job_ids:
            raise ContractError(f"Invalid or duplicate render_job_id: {render_job_id!r}")
        if node_id in job_nodes or node_id not in nodes_by_id:
            raise ContractError(f"Invalid or duplicate job node_id: {node_id!r}")
        if job.get("status") not in {"pending", "retryable_failed"}:
            raise ContractError(f"Unsupported source job status for {node_id}")
        if job.get("expected_media_uri") != nodes_by_id[node_id].get(
            "expected_media_uri"
        ):
            raise ContractError(f"Media URI mismatch for {node_id}")
        render_job_ids.add(render_job_id)
        job_nodes.add(node_id)
    if job_nodes != set(nodes_by_id):
        raise ContractError("Render Jobs do not cover every graph node exactly once")

    looks_by_id = {
        str(look["look_id"]).lower(): look
        for look in source_manifest.get("looks", [])
    }
    actions_by_id = {
        str(asset["asset_id"]).lower(): asset
        for asset in source_manifest.get("assets", [])
        if asset.get("asset_type") == "action"
    }
    if len(looks_by_id) != int(required_exports.get("counts", {}).get("full_reference_looks", -1)):
        raise ContractError("Look registry count mismatch")
    if len(actions_by_id) != int(required_exports.get("counts", {}).get("action_assets", -1)):
        raise ContractError("Action registry count mismatch")

    matrix_lock = source_manifest.get("input_manifests", {}).get(
        "local_render_matrix", {}
    )
    expected_matrix_hash = matrix_lock.get("sha256")
    matrix_hash_mode = matrix_lock.get("hash_mode", "raw_bytes_v1")
    if matrix_hash_mode == "canonical_json_v1":
        matrix_hash_matches = sha256_json(matrix_config) == expected_matrix_hash
    elif matrix_hash_mode == "raw_bytes_v1":
        matrix_hash_matches = expected_matrix_hash in legacy_text_sha256_candidates(
            matrix_config_path
        )
    else:
        raise ContractError(f"Unsupported matrix hash mode: {matrix_hash_mode}")
    if expected_matrix_hash and not matrix_hash_matches:
        raise ContractError("Local render matrix hash differs from the frozen source")

    uproject = args.uproject.resolve()
    if not args.dry_run and not args.audit_existing and not uproject.is_file():
        raise ContractError(f"Unreal project is missing: {uproject}")

    runtime_profile_path = getattr(args, "runtime_profile_record", None)
    runtime_profile = None
    if runtime_profile_path is not None:
        runtime_profile_path = runtime_profile_path.resolve()
        runtime_profile = read_json(runtime_profile_path)
        if (
            runtime_profile.get("schema_version")
            != "first_batch_server_editor_profile_v1"
            or not runtime_profile.get("profile_id")
        ):
            raise ContractError(
                f"Invalid server runtime profile: {runtime_profile_path}"
            )

    return RenderContext(
        graph_root=graph_root,
        run_root=run_root,
        matrix_config_path=matrix_config_path,
        source_manifest=source_manifest,
        required_exports=required_exports,
        matrix_config=matrix_config,
        nodes=nodes,
        jobs=jobs,
        nodes_by_id=nodes_by_id,
        looks_by_id=looks_by_id,
        actions_by_id=actions_by_id,
        cameras_by_id=camera_contract(matrix_config),
        uproject=uproject,
        project_name=args.project_name,
        engine_root=args.engine_root.resolve() if args.engine_root else None,
        runtime_profile_path=runtime_profile_path,
        runtime_profile=runtime_profile,
    )


def node_to_matrix_row(context: RenderContext, job: dict) -> dict:
    node = context.nodes_by_id[job["node_id"]]
    config = node["config"]
    look_id = str(node["look_id"]).lower()
    action_id = str(config["action_id"]).lower()
    camera_id = str(config["camera_id"]).lower()
    try:
        look = context.looks_by_id[look_id]
        action = context.actions_by_id[action_id]
        camera = context.cameras_by_id[camera_id]
    except KeyError as exc:
        raise ContractError(
            f"Unable to bind {job['node_id']} to a frozen production asset: {exc}"
        ) from exc
    constraints = action.get("constraints", {})
    source_action_id = constraints.get("source_action_id")
    if not source_action_id:
        raise ContractError(f"Action lacks source_action_id: {action_id}")
    window = constraints.get("window")
    happy_composite = constraints.get("happy_composite_animation")
    if not isinstance(window, dict) or not happy_composite:
        raise ContractError(f"Action lacks frozen runtime bindings: {action_id}")
    if config.get("expression_id") != "happy":
        raise ContractError(f"First Batch node is not fixed to Happy: {job['node_id']}")
    expected_frames = int(config["duration_frames"])
    if camera["end_frame_exclusive"] - camera["start_frame_inclusive"] != expected_frames:
        raise ContractError(f"Camera duration mismatch for {job['node_id']}")
    return {
        "sample_id": f"NODE_{job['node_id']}",
        "node_id": job["node_id"],
        "render_job_id": job["render_job_id"],
        "look_id": look.get("source_look_id", look_id.upper()),
        "sex": config["sex"],
        "bodyfit_id": config["bodyfit_id"],
        "identity_id": config["identity_id"],
        "outfit_id": config["outfit_id"],
        "character_blueprint": look["character_blueprint"],
        "character_blueprint_class": look["character_blueprint_class"],
        "action_id": source_action_id,
        "action_contract": {
            "action_id": source_action_id,
            "sex": config["sex"],
            "window": window,
            "root_motion_policy": constraints.get("root_motion_policy"),
            "root_motion_override_asset": constraints.get(
                "root_motion_override_asset"
            ),
            "happy_composite_animation": happy_composite,
        },
        "expression_id": config["expression_id"],
        "camera_id": camera_id,
        **camera,
        "output_relative_directory": f"media/nodes/{job['node_id']}",
        "expected_media_uri": job["expected_media_uri"],
        "config_sha256": node["config_sha256"],
    }


def input_entries(context: RenderContext) -> list[dict]:
    paths = [
        context.graph_root / "source_manifest.json",
        context.graph_root / "nodes.jsonl",
        context.graph_root / "render_jobs.jsonl",
        context.graph_root / "required_exports.json",
        context.matrix_config_path,
        Path(__file__).resolve(),
        Path(matrix.__file__).resolve(),
        matrix.REMOTE_EXEC.resolve(),
        matrix.STAGE_SCRIPT.resolve(),
        matrix.SEQUENCE_RUNNER.resolve(),
        matrix.PROFILE_RUNNER.resolve(),
        matrix.RENDER_RUNNER.resolve(),
        ENGINE_ROOT / "scripts" / "unreal" / "ue_build_first_batch_20s_sequence.py",
        ENGINE_ROOT / "scripts" / "unreal" / "ue_build_first_batch_render_profile.py",
        ENGINE_ROOT / "scripts" / "unreal" / "ue_start_first_batch_local_sample_render.py",
    ]
    project_path = context.uproject if context.uproject.is_file() else None
    if project_path is not None:
        paths.append(project_path)
    if context.runtime_profile_path is not None:
        paths.append(context.runtime_profile_path)
    entries = []
    for path in paths:
        if not path.is_file():
            raise ContractError(f"Locked input is missing: {path}")
        if (
            context.runtime_profile_path is not None
            and path == context.runtime_profile_path
        ):
            uri = f"runtime-profile://{context.runtime_profile['profile_id']}"
        elif project_path is not None and path == project_path:
            uri = f"project://{context.project_name}/{path.name}"
        else:
            uri = repo_uri(path)
        normalized_payload, hash_mode = normalized_locked_input(path)
        entries.append(
            {
                "uri": uri,
                "bytes": len(normalized_payload),
                "sha256": sha256_bytes(normalized_payload),
                "hash_mode": hash_mode,
            }
        )
    return sorted(entries, key=lambda value: value["uri"])


def ensure_input_lock(context: RenderContext) -> None:
    entries = input_entries(context)
    fingerprint = sha256_json(entries)
    lock_path = context.run_root / "inputs.lock.json"
    if lock_path.is_file():
        existing = read_json(lock_path)
        if (
            existing.get("schema_version") != LOCK_SCHEMA
            or existing.get("input_fingerprint") != fingerprint
        ):
            raise ContractError(
                "Run Root is bound to different immutable inputs; use a new Run Root"
            )
    else:
        atomic_write_json(
            lock_path,
            {
                "schema_version": LOCK_SCHEMA,
                "created_at_utc": utc_now(),
                "batch_id": context.source_manifest["batch_id"],
                "source_manifest_id": context.source_manifest["source_manifest_id"],
                "input_fingerprint": fingerprint,
                "inputs": entries,
            },
        )
    context.input_fingerprint = fingerprint
    context.input_lock_sha256 = sha256_file(lock_path)


def ensure_run_manifest(context: RenderContext) -> None:
    manifest_path = context.run_root / "manifest.json"
    payload = {
        "schema_version": RUN_SCHEMA,
        "run_id": context.run_root.name,
        "status": "running",
        "batch_id": context.source_manifest["batch_id"],
        "source_manifest_id": context.source_manifest["source_manifest_id"],
        "input_fingerprint": context.input_fingerprint,
        "input_lock_sha256": context.input_lock_sha256,
        "planned_node_count": len(context.jobs),
        "render_profile": context.source_manifest["render_profile"],
        "runtime_profile": context.runtime_profile,
        "paths": {
            "input_lock": "inputs.lock.json",
            "status": "status.json",
            "result": "result.json",
            "media_manifest": "media_manifest.json",
            "media_manifest_jsonl": "media_manifest.jsonl",
            "node_media": "media/nodes/<node_id>/video.mp4",
            "node_sidecar": "media/nodes/<node_id>/sidecar.json",
        },
        "created_at_utc": utc_now(),
    }
    if manifest_path.is_file():
        existing = read_json(manifest_path)
        if existing.get("input_fingerprint") != context.input_fingerprint:
            raise ContractError("Run manifest input fingerprint mismatch")
        payload["created_at_utc"] = existing.get(
            "created_at_utc", payload["created_at_utc"]
        )
    atomic_write_json(manifest_path, payload)


def select_jobs(args: argparse.Namespace, jobs: list[dict]) -> list[dict]:
    if args.node_id:
        if args.start_index != 1 or args.limit is not None:
            raise ContractError("--node-id cannot be combined with --start-index/--limit")
        by_id = {job["node_id"]: job for job in jobs}
        missing = [node_id for node_id in args.node_id if node_id not in by_id]
        if missing:
            raise ContractError(f"Unknown node IDs: {missing}")
        selected = [by_id[node_id] for node_id in args.node_id]
    else:
        if args.start_index < 1 or args.start_index > len(jobs):
            raise ContractError(f"--start-index must be in 1..{len(jobs)}")
        selected = jobs[args.start_index - 1 :]
        if args.limit is not None:
            if args.limit < 1:
                raise ContractError("--limit must be positive")
            selected = selected[: args.limit]
    if (
        len(selected) == len(jobs)
        and not args.dry_run
        and not args.audit_existing
        and not args.confirm_full_run
    ):
        raise ContractError("Refusing a 640-node run without --confirm-full-run")
    return selected


def node_state_path(context: RenderContext, node_id: str) -> Path:
    return context.run_root / "state" / "nodes" / f"{node_id}.json"


def read_node_state(context: RenderContext, job: dict) -> dict:
    path = node_state_path(context, job["node_id"])
    if path.is_file():
        state = read_json(path)
        if state.get("render_job_id") != job["render_job_id"]:
            raise ContractError(f"Node state job mismatch: {job['node_id']}")
        return state
    return {
        "schema_version": STATE_SCHEMA,
        "node_id": job["node_id"],
        "render_job_id": job["render_job_id"],
        "status": "pending",
        "attempts": [],
    }


def write_node_state(context: RenderContext, state: dict) -> None:
    state["updated_at_utc"] = utc_now()
    atomic_write_json(node_state_path(context, state["node_id"]), state)


def accepted_paths(context: RenderContext, job: dict) -> tuple[Path, Path]:
    video = context.run_root / Path(job["expected_media_uri"])
    return video, video.with_name("sidecar.json")


def validate_accepted_node(
    context: RenderContext,
    job: dict,
    *,
    verify_hash: bool,
) -> dict | None:
    video, sidecar_path = accepted_paths(context, job)
    if not video.is_file() or not sidecar_path.is_file():
        return None
    try:
        sidecar = read_json(sidecar_path)
    except ContractError:
        return None
    node = context.nodes_by_id[job["node_id"]]
    media = sidecar.get("media", {})
    ground_truth = sidecar.get("ground_truth", {})
    qa = sidecar.get("qa", {})
    checks = [
        sidecar.get("schema_version") == SIDECAR_SCHEMA,
        sidecar.get("status") == "accepted",
        sidecar.get("node_id") == job["node_id"],
        sidecar.get("render_job_id") == job["render_job_id"],
        sidecar.get("input_lock_sha256") == context.input_lock_sha256,
        ground_truth.get("config_sha256") == node["config_sha256"],
        ground_truth.get("config") == node["config"],
        media.get("path") == job["expected_media_uri"],
        media.get("bytes") == video.stat().st_size,
        bool(media.get("sha256")),
        qa.get("pose_driver", {}).get("passed") is True,
        qa.get("evaluation_preroll", {}).get("passed") is True,
        qa.get("temporal_motion", {}).get("passed") is True,
    ]
    if not all(checks):
        return None
    if verify_hash and sha256_file(video) != media["sha256"]:
        return None
    return sidecar


def build_sidecar(
    context: RenderContext,
    job: dict,
    row: dict,
    attempt_number: int,
    render_report: dict,
    stage_report: dict,
    sequence_report: dict,
    video_path: Path,
) -> dict:
    node = context.nodes_by_id[job["node_id"]]
    automation = render_report["automation_contract"]
    return {
        "schema_version": SIDECAR_SCHEMA,
        "status": "accepted",
        "node_id": job["node_id"],
        "render_job_id": job["render_job_id"],
        "input_lock_sha256": context.input_lock_sha256,
        "ground_truth": {
            "config": node["config"],
            "config_sha256": node["config_sha256"],
            "look_id": node["look_id"],
            "character_blueprint": node["character_blueprint"],
            "render_profile_id": node["render_profile_id"],
        },
        "actual_binding": {
            "character_blueprint_class": row["character_blueprint_class"],
            "actor_name": stage_report.get("actor_name"),
            "action_id": row["action_id"],
            "expression_id": row["expression_id"],
            "camera_id": row["camera_id"],
            "camera_section_index": row["camera_section_index"],
            "map": render_report.get("map"),
            "sequence": render_report.get("sequence"),
            "sequence_output": sequence_report.get("output_sequence"),
        },
        "media": {
            "path": job["expected_media_uri"],
            "container": "mp4",
            "codec": "h264",
            "bytes": video_path.stat().st_size,
            "sha256": sha256_file(video_path),
            "width": render_report["resolution"][0],
            "height": render_report["resolution"][1],
            "fps": render_report["fps"],
            "frames": render_report["frame_count"],
            "duration_seconds": render_report["duration_seconds"],
        },
        "attempt": {
            "number": attempt_number,
            "policy": job["attempt_policy"],
            "max_attempts": job["max_attempts"],
        },
        "qa": {
            "render_status": render_report["status"],
            "pose_driver": automation["pose_driver_contract"],
            "evaluation_preroll": automation["evaluation_preroll_contract"],
            "temporal_motion": automation["temporal_motion_contract"],
        },
        "runtime": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "project_name": context.project_name,
            "uproject_sha256": (
                sha256_file(context.uproject) if context.uproject.is_file() else None
            ),
            "git": git_state(),
            "editor_profile": context.runtime_profile,
        },
        "accepted_at_utc": utc_now(),
    }


def promote_attempt(
    context: RenderContext,
    job: dict,
    sidecar: dict,
    source_video: Path,
) -> Path:
    final_video, _ = accepted_paths(context, job)
    final_folder = final_video.parent
    temporary = final_folder.with_name(
        f".{final_folder.name}.promoting.{uuid.uuid4().hex}"
    )
    temporary.mkdir(parents=True, exist_ok=False)
    promoted_video = temporary / "video.mp4"
    shutil.copy2(source_video, promoted_video)
    promoted_hash = sha256_file(promoted_video)
    if promoted_hash != sidecar["media"]["sha256"]:
        raise ContractError(f"Promotion copy hash mismatch: {job['node_id']}")
    sidecar = json.loads(json.dumps(sidecar))
    sidecar["media"]["bytes"] = promoted_video.stat().st_size
    atomic_write_json(temporary / "sidecar.json", sidecar)
    if final_folder.exists():
        quarantine = (
            context.run_root
            / "staging"
            / "quarantine"
            / f"{job['node_id']}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        )
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        os.replace(final_folder, quarantine)
    final_folder.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary, final_folder)
    return final_video


def cleanup_attempt(attempt_dir: Path, *, keep_artifacts: bool) -> None:
    if keep_artifacts:
        return
    for frame in attempt_dir.glob("frame_*.png"):
        frame.unlink(missing_ok=True)
    for video in attempt_dir.glob("*.mp4"):
        video.unlink(missing_ok=True)


def refresh_run_indexes(context: RenderContext, stale_after_seconds: int) -> dict:
    aggregate_lease = FileLease(
        context.run_root / "leases" / "_aggregate.lock",
        owner="aggregate",
        stale_after_seconds=stale_after_seconds,
        wait_seconds=60,
    )
    with aggregate_lease:
        media_records = []
        state_counts: Counter[str] = Counter()
        for job in context.jobs:
            state = read_node_state(context, job)
            accepted = validate_accepted_node(context, job, verify_hash=False)
            status = "accepted" if accepted is not None else state.get("status", "pending")
            state_counts[status] += 1
            if accepted is not None:
                media_records.append(
                    {
                        "node_id": job["node_id"],
                        "render_job_id": job["render_job_id"],
                        "config_sha256": accepted["ground_truth"]["config_sha256"],
                        **accepted["media"],
                        "sidecar": str(
                            Path(job["expected_media_uri"]).with_name("sidecar.json")
                        ).replace("\\", "/"),
                    }
                )
        media_records.sort(key=lambda value: value["node_id"])
        media_jsonl = "".join(canonical_json(record) + "\n" for record in media_records)
        atomic_write_text(context.run_root / "media_manifest.jsonl", media_jsonl)
        media_manifest = {
            "schema_version": MEDIA_MANIFEST_SCHEMA,
            "updated_at_utc": utc_now(),
            "input_lock_sha256": context.input_lock_sha256,
            "planned_node_count": len(context.jobs),
            "accepted_node_count": len(media_records),
            "status": "complete" if len(media_records) == len(context.jobs) else "partial",
            "records": media_records,
        }
        atomic_write_json(context.run_root / "media_manifest.json", media_manifest)
        status = {
            "schema_version": RUN_SCHEMA,
            "updated_at_utc": utc_now(),
            "input_lock_sha256": context.input_lock_sha256,
            "planned_node_count": len(context.jobs),
            "counts": dict(sorted(state_counts.items())),
            "accepted_node_count": len(media_records),
            "status": "complete" if len(media_records) == len(context.jobs) else "running",
        }
        atomic_write_json(context.run_root / "status.json", status)
        return status


def attempt_log_path(context: RenderContext, job: dict, attempt_number: int) -> Path:
    return (
        context.run_root
        / "logs"
        / "render"
        / job["node_id"]
        / f"attempt_{attempt_number:03d}.jsonl"
    )


def mark_interrupted_attempts(attempts: list[dict]) -> int:
    interrupted_at = utc_now()
    count = 0
    for attempt in attempts:
        if attempt.get("status") != "running":
            continue
        attempt["status"] = "interrupted"
        attempt["interrupted_at_utc"] = interrupted_at
        count += 1
    return count


def run_one_job(
    context: RenderContext,
    job: dict,
    args: argparse.Namespace,
) -> dict:
    existing = validate_accepted_node(context, job, verify_hash=True)
    if existing is not None:
        state = read_node_state(context, job)
        state["status"] = "accepted"
        state["resume"] = "reused_hash_valid_output"
        write_node_state(context, state)
        return {"node_id": job["node_id"], "status": "accepted", "resume": "reused"}

    lease = FileLease(
        context.run_root / "leases" / f"{job['node_id']}.lock",
        owner=job["node_id"],
        stale_after_seconds=args.lease_timeout_seconds,
    )
    with lease:
        existing = validate_accepted_node(context, job, verify_hash=True)
        if existing is not None:
            return {"node_id": job["node_id"], "status": "accepted", "resume": "reused"}
        state = read_node_state(context, job)
        attempts = state.setdefault("attempts", [])
        mark_interrupted_attempts(attempts)
        max_attempts = int(job["max_attempts"])
        if len(attempts) >= max_attempts:
            state["status"] = "permanent_failed"
            write_node_state(context, state)
            return {"node_id": job["node_id"], "status": "permanent_failed"}

        attempt_number = len(attempts)
        attempt_dir = (
            context.run_root
            / "staging"
            / "render"
            / job["node_id"]
            / f"attempt_{attempt_number:03d}"
        )
        if attempt_dir.exists():
            attempt_dir = attempt_dir.with_name(
                f"{attempt_dir.name}_retry_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            )
        log_path = attempt_log_path(context, job, attempt_number)
        attempt = {
            "attempt": attempt_number,
            "status": "running",
            "started_at_utc": utc_now(),
            "attempt_dir": str(attempt_dir.relative_to(context.run_root)).replace("\\", "/"),
            "log": str(log_path.relative_to(context.run_root)).replace("\\", "/"),
        }
        attempts.append(attempt)
        state["status"] = "running"
        write_node_state(context, state)
        append_jsonl(log_path, {"event": "attempt_started", **attempt})
        row = node_to_matrix_row(context, job)

        try:
            stage_report = matrix.stage_look(context.matrix_config, row)
            append_jsonl(log_path, {"event": "look_staged", "report": stage_report})
            sequence_report = matrix.build_sequence(
                context.matrix_config,
                row,
                stage_report["actor_name"],
            )
            if not sequence_report.get("success"):
                raise RuntimeError(f"Sequence build failed: {sequence_report}")
            pose_contract = matrix.pose_driver_contract(sequence_report)
            if not pose_contract["passed"]:
                raise ContractError(f"Anti-T-pose contract failed: {pose_contract}")
            append_jsonl(
                log_path,
                {"event": "sequence_built", "pose_driver": pose_contract},
            )
            render_report = matrix.render_case(
                context.matrix_config,
                row,
                attempt_dir,
                args.timeout_seconds,
                sequence_report,
            )
            source_video = Path(render_report["video"])
            if not source_video.is_file():
                raise RuntimeError(f"Rendered video is missing: {source_video}")
            sidecar = build_sidecar(
                context,
                job,
                row,
                attempt_number,
                render_report,
                stage_report,
                sequence_report,
                source_video,
            )
            final_video = promote_attempt(context, job, sidecar, source_video)
            accepted = validate_accepted_node(context, job, verify_hash=True)
            if accepted is None:
                raise ContractError(f"Accepted output failed final validation: {job['node_id']}")
            attempt["status"] = "accepted"
            attempt["completed_at_utc"] = utc_now()
            attempt["media_sha256"] = accepted["media"]["sha256"]
            state["status"] = "accepted"
            state["accepted_media"] = job["expected_media_uri"]
            write_node_state(context, state)
            append_jsonl(
                log_path,
                {
                    "event": "attempt_accepted",
                    "node_id": job["node_id"],
                    "video": str(final_video.relative_to(context.run_root)).replace("\\", "/"),
                    "sha256": accepted["media"]["sha256"],
                },
            )
            cleanup_attempt(attempt_dir, keep_artifacts=args.keep_attempt_artifacts)
            return {"node_id": job["node_id"], "status": "accepted", "resume": "rendered"}
        except Exception as exc:
            attempt["status"] = "permanent_failed" if isinstance(exc, ContractError) else "retryable_failed"
            attempt["completed_at_utc"] = utc_now()
            attempt["error_type"] = type(exc).__name__
            attempt["error"] = str(exc)
            if len(attempts) >= max_attempts:
                attempt["status"] = "permanent_failed"
            state["status"] = attempt["status"]
            write_node_state(context, state)
            append_jsonl(
                log_path,
                {
                    "event": "attempt_failed",
                    "status": attempt["status"],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            if not args.continue_on_error:
                raise
            return {
                "node_id": job["node_id"],
                "status": attempt["status"],
                "error": str(exc),
            }


def audit_selection(context: RenderContext, selected: list[dict]) -> dict:
    records = []
    for job in selected:
        sidecar = validate_accepted_node(context, job, verify_hash=True)
        records.append(
            {
                "node_id": job["node_id"],
                "status": "accepted" if sidecar is not None else "missing_or_invalid",
            }
        )
    return {
        "schema_version": RUN_SCHEMA,
        "created_at_utc": utc_now(),
        "status": (
            "passed"
            if all(record["status"] == "accepted" for record in records)
            else "failed"
        ),
        "selected_count": len(records),
        "accepted_count": sum(record["status"] == "accepted" for record in records),
        "records": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-root", type=Path, default=DEFAULT_GRAPH_ROOT)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--matrix-config", type=Path, default=DEFAULT_MATRIX_CONFIG)
    parser.add_argument("--uproject", type=Path, default=DEFAULT_UPROJECT)
    parser.add_argument("--project-name", default="datatry_02")
    parser.add_argument("--engine-root", type=Path)
    parser.add_argument(
        "--runtime-profile-record",
        type=Path,
        help="Immutable server Editor launch profile to include in the input lock.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--lease-timeout-seconds", type=int, default=6 * 60 * 60)
    parser.add_argument("--minimum-free-gib", type=float, default=40.0)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--node-id", action="append")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-existing", action="store_true")
    parser.add_argument("--confirm-full-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--keep-attempt-artifacts", action="store_true")
    return parser.parse_args()


def dry_run_report(context: RenderContext, selected: list[dict]) -> dict:
    rows = [node_to_matrix_row(context, job) for job in selected]
    return {
        "status": "dry_run_passed",
        "source_manifest_id": context.source_manifest["source_manifest_id"],
        "total_job_count": len(context.jobs),
        "selected_count": len(selected),
        "first_node_id": selected[0]["node_id"],
        "last_node_id": selected[-1]["node_id"],
        "look_count": len({row["look_id"] for row in rows}),
        "action_counts": dict(sorted(Counter(row["action_id"] for row in rows).items())),
        "camera_counts": dict(sorted(Counter(row["camera_id"] for row in rows).items())),
        "expression_counts": dict(
            sorted(Counter(row["expression_id"] for row in rows).items())
        ),
    }


def main() -> int:
    args = parse_args()
    context = load_context(args)
    selected = select_jobs(args, context.jobs)
    if not selected:
        raise ContractError("No Render Jobs were selected")
    if args.dry_run:
        print(json.dumps(dry_run_report(context, selected), ensure_ascii=False, indent=2))
        return 0

    context.run_root.mkdir(parents=True, exist_ok=True)
    if not args.audit_existing:
        free_bytes = shutil.disk_usage(context.run_root).free
        required_bytes = int(args.minimum_free_gib * 1024**3)
        if free_bytes < required_bytes:
            raise ContractError(
                f"At least {args.minimum_free_gib:.1f} GiB free is required; "
                f"found {free_bytes / 1024**3:.1f} GiB"
            )
    ensure_input_lock(context)
    ensure_run_manifest(context)
    refresh_run_indexes(context, args.lease_timeout_seconds)

    if args.audit_existing:
        result = audit_selection(context, selected)
        atomic_write_json(context.run_root / "result.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "passed" else 1

    pending = [
        job
        for job in selected
        if validate_accepted_node(context, job, verify_hash=True) is None
    ]
    if pending:
        matrix.configure_remote(context.project_name, context.engine_root)
        matrix.ensure_stage_map(context.matrix_config)
        profile_command = [
            sys.executable,
            str(matrix.PROFILE_RUNNER),
            "--project-name",
            context.project_name,
        ]
        if context.engine_root is not None:
            profile_command.extend(["--engine-root", str(context.engine_root)])
        matrix.run_command(profile_command, 300)

    invocation_records = []
    for ordinal, job in enumerate(selected, start=1):
        print(
            f"[{ordinal}/{len(selected)}] {job['node_id']}",
            flush=True,
        )
        invocation_records.append(run_one_job(context, job, args))
        refresh_run_indexes(context, args.lease_timeout_seconds)
        if invocation_records[-1].get("resume") == "rendered":
            try:
                matrix.remote(
                    "import unreal; unreal.SystemLibrary.collect_garbage(); "
                    "print('DM_FORMAL_RENDER_GC=done')",
                    180,
                )
            except Exception:
                pass

    status = refresh_run_indexes(context, args.lease_timeout_seconds)
    result = {
        "schema_version": RUN_SCHEMA,
        "created_at_utc": utc_now(),
        "status": (
            "passed"
            if all(record["status"] == "accepted" for record in invocation_records)
            else "partial_failed"
        ),
        "selected_count": len(selected),
        "accepted_count": sum(
            record["status"] == "accepted" for record in invocation_records
        ),
        "rendered_count": sum(
            record.get("resume") == "rendered" for record in invocation_records
        ),
        "reused_count": sum(
            record.get("resume") == "reused" for record in invocation_records
        ),
        "run_status": status,
        "records": invocation_records,
    }
    atomic_write_json(context.run_root / "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
