"""Serial v11 editor render driver; connects to an already running editor only.

DM_WORKSPACE, DM_UE_PROJECT_ROOT, DM_UE_ENGINE_ROOT, DM_RENDER_RUN_ROOT and
DM_UE_PATH_MAP (JSON object mapping local prefixes to editor prefixes) allow
the same command to run on Windows/Linux. A timeout stops the queue because
an editor render may still be running. Never automatically retries a command.
"""
from __future__ import annotations

import argparse
import binascii
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import struct
import sys
import time
import uuid
import zlib

SCRIPT_ROOT = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_ROOT.parents[2]
MARKER = "DM_DATASET_DRIVER_V11="
TERMINAL_OK = {"success", "completed", "complete", "finished", "succeeded"}
TERMINAL_BAD = {"failed", "error", "cancelled", "canceled", "setup_failed"}
ACTIVE = {"rendering", "running", "queued", "pending", "starting", "busy", "submitted"}
REFERENCE_WORKER = "ue_dataset_reference_v11"
PNG_POLICY = {"format": "PNG", "frames": 1, "bits_per_channel": 8,
              "channels": ["RGB", "RGBA"], "alpha_policy": "preserve original PNG without conversion",
              "verification": "all_chunk_crc_and_full_idat_zlib_decode"}


class WorkerError(ValueError):
    """Editor returned a concrete exception; query MRQ before continuing."""


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def emit(phase, **value):
    print(json.dumps({"at": now(), "phase": phase, **value}, ensure_ascii=False), flush=True)


@contextmanager
def queue_lock(run_root):
    """A process lock prevents two drivers from interleaving world mutations."""
    path = Path(run_root) / "driver.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def editor_path(path, mappings):
    value = str(Path(path).resolve()).replace("\\", "/")
    for source, target in sorted(mappings.items(), key=lambda item: len(item[0]), reverse=True):
        source = str(source).replace("\\", "/").rstrip("/")
        if value.casefold() == source.casefold() or value.casefold().startswith(source.casefold() + "/"):
            return str(target).replace("\\", "/").rstrip("/") + value[len(source):]
    return value


class Transport:
    def __init__(self, args):
        self.args = args
        import scene_site_review_panel_v1 as panel
        self.panel = panel
        self.node_id = args.node_id  # Fresh discovery; never reads a historical pin.
        self.mappings = json.loads(os.environ.get("DM_UE_PATH_MAP", "{}"))
        if not isinstance(self.mappings, dict):
            raise ValueError("DM_UE_PATH_MAP must be a JSON object")

    def select_node(self, nodes):
        project = self.args.project_root
        names = {project.stem} if project.suffix == ".uproject" else {project.name}
        if project.is_dir():
            names.update(p.stem for p in project.glob("*.uproject"))
        candidates = [n for n in nodes if n.get("project_name") in names]
        if self.node_id:
            candidates = [n for n in candidates if n.get("node_id") == self.node_id]
        if len(candidates) != 1:
            raise RuntimeError(f"Need one editor for {sorted(names)}; found {len(candidates)}. Use --node-id if ambiguous.")
        return candidates[0]

    def __call__(self, request):
        request = dict(request, request_id=uuid.uuid4().hex)
        for key in ("run_root", "jobs_path", "workspace", "project_root"):
            if key in request:
                request[key] = editor_path(request[key], self.mappings)
        remote_scripts = editor_path(self.args.workspace / "00_engine/scripts/unreal", self.mappings)
        # Printing the return value ourselves decouples transport from worker logs.
        worker_name=getattr(self.args,'worker_module','ue_dataset_render_v11')
        bootstrap=f"import {worker_name} as _dataset_v11\nimportlib.reload(_dataset_v11)\n"
        if getattr(self.args,'portable_runtime',False):
            project_files=list(self.args.project_root.glob('*.uproject'))
            if len(project_files)!=1:raise ValueError('Portable runtime needs exactly one project file')
            bootstrap=("import dataset_runtime_paths_v11 as _paths\n"
                       f"_path_key = ({str(self.args.workspace)!r}, {str(project_files[0])!r}, {str(self.args.engine_root)!r})\n"
                       "if not hasattr(_paths, '_driver_adapters'): _paths._driver_adapters = {}\n"
                       "if _path_key not in _paths._driver_adapters: _paths._driver_adapters[_path_key] = _paths.RuntimePaths(_path_key[0], _path_key[1], engine_root=_path_key[2])\n"
                       f"_dataset_v11 = _paths._driver_adapters[_path_key].load({worker_name!r})\n")
        command = (f"import sys, json, importlib\nsys.path.insert(0, {remote_scripts!r})\n"
                   + bootstrap +
                   f"_dataset_result = _dataset_v11.dispatch({request!r})\n"
                   f"print({MARKER!r} + json.dumps(_dataset_result, ensure_ascii=False, default=str))")
        record = {"request": request, "started_at": now()}
        started = time.monotonic()
        session = None
        try:
            with self.panel.bridge.command_lock():
                module = self.panel.bridge.load_remote_execution(self.args.engine_root.resolve())
                self.panel.install_complete_reply_receiver(module)
                session = module.RemoteExecution()
                session.start()
                deadline = time.monotonic() + self.args.discovery_timeout
                last_error = None
                while time.monotonic() < deadline:
                    try:
                        node = self.select_node(list(session.remote_nodes))
                        break
                    except RuntimeError as exc:
                        last_error = exc
                        time.sleep(.2)
                else:
                    raise last_error or RuntimeError("No running editor discovered")
                self.node_id = node["node_id"]
                record["node"] = node
                session.open_command_connection(self.node_id)
                session._command_connection._command_channel_socket.settimeout(self.args.command_timeout)
                reply = session.run_command(command, unattended=True, exec_mode=module.MODE_EXEC_FILE, raise_on_failure=False)
                record["remote_reply"] = reply
                if reply.get("success") is not True:
                    raise WorkerError("Editor command failed: " + str(reply)[-3000:])
                values = [str(row.get("output", "")).split(MARKER, 1)[1]
                          for row in reply.get("output", []) if MARKER in str(row.get("output", ""))]
                if len(values) != 1:
                    raise RuntimeError("Missing or ambiguous worker return receipt")
                result, _ = json.JSONDecoder().raw_decode(values[0].lstrip())
                if not isinstance(result, dict):
                    raise RuntimeError("Worker returned a non-object receipt")
                record["result"] = result
                return result
        except Exception as exc:
            record["error"] = str(exc)
            raise
        finally:
            if session:
                session.stop()
            record.update(finished_at=now(), seconds=time.monotonic() - started)
            write(self.args.run_root / "remote" / (request["request_id"] + ".json"), record)


def state_of(result):
    nested = result.get("renderer") or result.get("render") or result.get("receipt")
    if isinstance(nested, dict):
        return state_of(nested)
    return str(result.get("status") or result.get("state") or "").lower()


def renderer_active(result):
    return bool(result.get("subsystem_rendering") or result.get("active_executor_path")
                or result.get("owned_executor_active") or result.get("busy") or result.get("is_rendering")
                or state_of(result) in ACTIVE)


def renderer_idle(result):
    if renderer_active(result):
        return False
    if "subsystem_rendering" in result:
        return result["subsystem_rendering"] is False and state_of(result) in ({"", "idle", "prepared"} | TERMINAL_OK | TERMINAL_BAD)
    return state_of(result) in {"idle", "prepared"} | TERMINAL_OK | TERMINAL_BAD


def assert_accepted(result):
    if result.get("success") is False or state_of(result) in TERMINAL_BAD:
        raise ValueError(str(result.get("error") or result))


def wait_render(transport, request, started, timeout, interval, submitted=None):
    submitted = submitted or {}
    expected_attempt = submitted.get("owned_attempt_id") or (submitted.get("receipt") or {}).get("attempt_id")
    while True:
        if time.monotonic() - started >= timeout:
            raise TimeoutError("Render timeout: queue stopped; editor may still be rendering")
        result = transport(dict(request, action="status"))
        state = state_of(result)
        attempt = result.get("owned_attempt_id") or (result.get("receipt") or {}).get("attempt_id")
        if expected_attempt and attempt != expected_attempt:
            raise RuntimeError("Renderer attempt changed; queue stopped")
        # Finished callback may precede executor teardown. Do not start another
        # world operation until both the receipt and subsystem are terminal.
        if state in TERMINAL_BAD | TERMINAL_OK and not renderer_active(result):
            return result
        if not renderer_active(result):
            raise RuntimeError(f"Unrecognized renderer status; queue stopped: {result}")
        time.sleep(min(interval, max(0, timeout - (time.monotonic() - started))))


def load_encoder(workspace):
    path = workspace / "00_engine/scripts/dataset/encode_render_v11.py"
    spec = importlib.util.spec_from_file_location("_dataset_encoder_v11", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def renderer_signature(args, job):
    """Read the current policy source rather than a potentially stale pyc."""
    worker_path = args.workspace / "00_engine/scripts/unreal" / (getattr(args, "worker_module", "ue_dataset_render_v11") + ".py")
    namespace = {"__name__": "_dataset_worker_signature_v11", "__file__": str(worker_path)}
    exec(compile(worker_path.read_text(encoding="utf-8-sig"), str(worker_path), "exec"), namespace)
    return namespace["signature"](job)


def media_kind(args, job):
    if getattr(args, "worker_module", "ue_dataset_render_v11") != REFERENCE_WORKER:
        return "video"
    kind = job.get("reference_kind")
    if kind == "motion":
        if job.get("frames") != 300 or job.get("fps") != 30:
            raise ValueError("Motion references require exactly 300 frames at 30fps")
        return "video"
    if kind not in {"scene", "garment", "identity", "hair"}:
        raise ValueError(f"Unknown reference kind: {kind}")
    if job.get("frames", 1) != 1:
        raise ValueError("Static references require exactly one PNG frame")
    return "png"


def png_spec_signature(job):
    return hashlib.sha256(json.dumps({"job": job, "output": PNG_POLICY}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def inspect_static_png(directory, job):
    """Validate a whole non-interlaced RGB/RGBA8 PNG with only stdlib."""
    frames = directory / "frames"
    path = frames / "frame_0000.png"
    if set(frames.glob("*.png")) != {path}:
        raise ValueError("Static reference must contain exactly frame_0000.png")
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")
    offset, header, compressed, ended = 8, None, bytearray(), False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("Truncated PNG chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("Truncated PNG chunk data")
        payload = data[offset + 8:end - 4]
        crc = struct.unpack(">I", data[end - 4:end])[0]
        if binascii.crc32(chunk_type + payload) & 0xFFFFFFFF != crc:
            raise ValueError("PNG chunk CRC mismatch")
        if header is None and chunk_type != b"IHDR":
            raise ValueError("PNG must start with IHDR")
        if chunk_type == b"IHDR":
            if header is not None or length != 13:
                raise ValueError("Invalid PNG IHDR")
            header = struct.unpack(">IIBBBBB", payload)
        elif chunk_type == b"IDAT":
            compressed.extend(payload)
        elif chunk_type == b"acTL":
            raise ValueError("Animated PNG is not a static reference")
        elif chunk_type == b"IEND":
            if length or end != len(data):
                raise ValueError("Invalid PNG end/trailing bytes")
            ended = True
            break
        offset = end
    if not header or not compressed or not ended:
        raise ValueError("Incomplete PNG")
    width, height, bits, color, compression, filtering, interlace = header
    if (width, height) != (job.get("width"), job.get("height")) or width < 1 or height < 1:
        raise ValueError(f"PNG dimensions {width}x{height} do not match reference job")
    if bits != 8 or color not in {2, 6} or (compression, filtering, interlace) != (0, 0, 0):
        raise ValueError("Expected non-interlaced RGB/RGBA8 PNG")
    channels = 3 if color == 2 else 4
    stride = 1 + width * channels
    expected_bytes = height * stride
    decoder = zlib.decompressobj()
    try:
        pixels = decoder.decompress(bytes(compressed), expected_bytes + 1)
    except zlib.error as exc:
        raise ValueError("PNG image data cannot be decompressed") from exc
    if len(pixels) != expected_bytes or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("PNG decoded pixel length/stream mismatch")
    if any(pixels[index] > 4 for index in range(0, expected_bytes, stride)):
        raise ValueError("Invalid PNG row filter")
    return {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "media": {"format": "PNG", "width": width, "height": height, "frames": 1,
                      "bits_per_channel": bits, "channels": "RGB" if channels == 3 else "RGBA",
                      "verification": PNG_POLICY["verification"]}}


def verified_resume(args, job):
    directory = args.run_root / "jobs" / job["job_id"]
    receipt_path, video = directory / "media_receipt.json", directory / "video.mp4"
    if not receipt_path.is_file():
        return False
    try:
        receipt = read(receipt_path)
        if receipt.get("render_signature") != renderer_signature(args, job):
            return False
        if media_kind(args, job) == "png":
            image = inspect_static_png(directory, job)
            return (receipt.get("status") == "success" and receipt.get("job_id") == job["job_id"]
                    and receipt.get("media_kind") == "png" and receipt.get("spec_sha256") == png_spec_signature(job)
                    and receipt.get("image_sha256") == image["sha256"] and receipt.get("media") == image["media"])
        if not video.is_file():
            return False
        encoder = load_encoder(args.workspace)
        spec_hash = hashlib.sha256(json.dumps({"job": job, "encoding": encoder.ENCODING}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if (receipt.get("status") != "success" or receipt.get("job_id") != job["job_id"]
                or receipt.get("spec_sha256") != spec_hash or receipt.get("video_sha256") != encoder.digest(video)):
            return False
        # Retained raw is checked against the successful encoder signature.
        frames = directory / "frames"
        if frames.is_dir():
            signature, _ = encoder.frame_signature(frames, job)
            return receipt.get("input_sha256") == signature
        return bool(receipt.get("input_sha256"))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def completed_render_receipt(args, job):
    """Resume an interrupted driver between MRQ completion and media encoding.

    The newest attempt for this job owns its shared frame directory. An older
    success must never hide a newer failed/partial attempt that touched it.
    """
    directory = args.run_root / "jobs" / job["job_id"]
    try:
        prepared = read(directory / "prepared.json")
        signature = renderer_signature(args, job)
        if prepared.get("signature") != signature:
            return None
        receipts = []
        receipt_root = args.run_root / "render_receipts"
        paths = list(receipt_root.glob(job["job_id"] + "_*.json"))
        # Native attempts are job-prefixed. Avoid rereading every reference's
        # receipt for each of thousands of jobs; retain old renamed receipts.
        if not paths:
            paths = receipt_root.glob("*.json")
        for path in paths:
            try:
                receipt = read(path)
                jobs = receipt.get("jobs", [])
                if len(jobs) == 1 and jobs[0].get("shot_id") == job["job_id"]:
                    receipts.append((path.stat().st_mtime_ns, path, receipt))
            except (OSError, ValueError, TypeError, AttributeError):
                continue
        if not receipts:
            return None
        _, path, receipt = max(receipts, key=lambda item: (item[0], str(item[1])))
        if receipt.get("status") != "completed" or receipt.get("success") is not True or receipt.get("job_signature") != signature:
            return None
        mappings = json.loads(os.environ.get("DM_UE_PATH_MAP", "{}"))
        actual = str(receipt.get("frames_directory", "")).replace("\\", "/").rstrip("/")
        expected = {str((directory / "frames").resolve()).replace("\\", "/"), editor_path(directory / "frames", mappings)}
        if actual not in expected or not (directory / "frames").is_dir():
            return None
        # Full count/header/input-hash checks are the independent encoder's job.
        return {"receipt_path": str(path), "signature": signature, "frames_directory": str(directory / "frames")}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def completed_render_provenance(args, job):
    """Require actual completed MRQ + prepared signatures under this worker."""
    completed = completed_render_receipt(args, job)
    if not completed:
        raise ValueError("Cannot bind media: latest completed render does not match current renderer policy")
    render_path = Path(completed["receipt_path"])
    render_bytes = render_path.read_bytes()
    render = json.loads(render_bytes.decode("utf-8-sig"))
    provenance = {"schema": "dataset_media_render_binding_v11_v1", "signature": completed["signature"],
                  "worker_module": getattr(args, "worker_module", "ue_dataset_render_v11"),
                  "receipt_path": str(render_path), "receipt_relative_path": render_path.relative_to(args.run_root).as_posix(),
                  "receipt_sha256": hashlib.sha256(render_bytes).hexdigest(), "attempt_id": render.get("attempt_id"),
                  "job_signature": render.get("job_signature"), "submitted_at": render.get("submitted_at"),
                  "finished_at": render.get("finished_at"), "status": render.get("status"), "success": render.get("success"),
                  "render_contract": render.get("render_contract"), "bound_at": now()}
    return provenance


def bind_media_render_provenance(args, job):
    """Bind encoder success only after independently checking renderer policy."""
    provenance = completed_render_provenance(args, job)
    receipt_path = args.run_root / "jobs" / job["job_id"] / "media_receipt.json"
    media = read(receipt_path)
    final_path = receipt_path.parent / ("frames/frame_0000.png" if media_kind(args, job) == "png" else "video.mp4")
    if (media.get("status") != "success" or media.get("job_id") != job["job_id"] or not final_path.is_file()):
        raise ValueError("Cannot bind media: encoder did not produce a matching success receipt")
    media.update(render_signature=provenance["signature"], render_provenance=provenance)
    write(receipt_path, media)
    return provenance


def finalize_static_png(args, job):
    started = time.monotonic()
    image = inspect_static_png(args.run_root / "jobs" / job["job_id"], job)
    provenance = completed_render_provenance(args, job)
    receipt = {"schema": "dataset_static_media_receipt_v11_v1", "status": "success", "media_kind": "png",
               "job_id": job["job_id"], "reference_kind": job["reference_kind"], "finished_at": now(),
               "spec_sha256": png_spec_signature(job), "image": f"jobs/{job['job_id']}/frames/frame_0000.png",
               "image_sha256": image["sha256"], "image_bytes": image["bytes"], "media": image["media"],
               "render_signature": provenance["signature"], "render_provenance": provenance,
               "output_policy": PNG_POLICY, "timing": {"verification_seconds": time.monotonic() - started},
               "visual_acceptance": "pending", "source_png_modified": False}
    write(args.run_root / "jobs" / job["job_id"] / "media_receipt.json", receipt)
    return provenance


def select_jobs(args):
    jobs = read(args.jobs)["jobs"]
    ids = [job["job_id"] for job in jobs]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate job IDs in manifest")
    for job_id in ids:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", job_id) or job_id in {".", ".."}:
            raise ValueError(f"Unsafe job ID: {job_id}")
    if args.job_id:
        missing = set(args.job_id) - set(ids)
        if missing:
            raise ValueError(f"Unknown jobs: {sorted(missing)}")
        jobs = [job for job in jobs if job["job_id"] in args.job_id]
    jobs = [job for index, job in enumerate(jobs) if index % args.shard_count == args.shard_index]
    return jobs[:args.limit] if args.limit is not None else jobs


def run(args, transport=None, encoder_runner=subprocess.run):
    jobs = select_jobs(args)
    if args.command_only and args.command_only != "status" and len(jobs) != 1:
        raise ValueError("Command-only prepare/render requires exactly one selected job")
    transport = transport or Transport(args)
    base = {"run_root": str(args.run_root), "jobs_path": str(args.jobs),
            "workspace": str(args.workspace), "project_root": str(args.project_root),"pool_mb":getattr(args,'pool_mb',10240)}
    if args.command_only:
        request = dict(base, action=args.command_only)
        if len(jobs) == 1:
            request["job_id"] = jobs[0]["job_id"]
        started = time.monotonic()
        result = transport(request)
        emit(args.command_only, seconds=time.monotonic() - started, result=result)
        assert_accepted(result)
        return 0
    summary = {"started_at": now(), "jobs": []}
    stopped = False
    try:
        for job in jobs:
            job_id, phase = job["job_id"], "resume"
            started = time.monotonic()
            row = {"job_id": job_id, "timing": {}}
            summary["jobs"].append(row)
            request = dict(base, job_id=job_id)
            try:
                output_kind = media_kind(args, job)
                if not args.force and verified_resume(args, job):
                    row["status"] = "reused_verified_receipt"
                    emit("resume", job_id=job_id, status=row["status"], seconds=time.monotonic() - started)
                    continue
                # This guard also catches unfinished work from a prior interrupted run.
                phase = "preflight_status"
                status = transport(dict(request, action="status"))
                if not renderer_idle(status):
                    raise RuntimeError(f"Editor is active or status is unknown; queue stopped before prepare: {status}")
                reusable_render = None if args.force else completed_render_receipt(args, job)
                if reusable_render:
                    row["reused_render"] = reusable_render
                    emit("resume_render", job_id=job_id, result=reusable_render)
                else:
                    for phase in ("prepare", "render"):
                        stage_start = time.monotonic()
                        result = transport(dict(request, action=phase))
                        if phase == "render":
                            phase = "render_wait"
                            result = wait_render(transport, request, stage_start, args.render_timeout, args.poll_interval, result)
                        assert_accepted(result)
                        key = "render" if phase == "render_wait" else phase
                        row["timing"][key + "_seconds"] = time.monotonic() - stage_start
                        emit(key, job_id=job_id, seconds=row["timing"][key + "_seconds"], result=result)
                if output_kind == "png":
                    phase = "verify_png"
                    stage_start = time.monotonic()
                    row["render_provenance"] = finalize_static_png(args, job)
                    row["timing"]["png_verification_seconds"] = time.monotonic() - stage_start
                    row.update(status="success", media_kind="png")
                    emit("verify_png", job_id=job_id, seconds=row["timing"]["png_verification_seconds"], status="success")
                    continue
                phase = "encode"
                stage_start = time.monotonic()
                command = [sys.executable, str(args.workspace / "00_engine/scripts/dataset/encode_render_v11.py"),
                           "--run-root", str(args.run_root), "--jobs", str(args.jobs), "--job-id", job_id]
                if args.ffmpeg:
                    command += ["--ffmpeg", args.ffmpeg]
                if args.force:
                    command.append("--force")
                completed = encoder_runner(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
                row["encoder_output"] = {"stdout": completed.stdout[-6000:], "stderr": completed.stderr[-6000:]}
                if completed.returncode:
                    raise ValueError(f"Encoder exited {completed.returncode}: {completed.stderr[-2000:]}")
                row["render_provenance"] = bind_media_render_provenance(args, job)
                row["timing"]["encode_seconds"] = time.monotonic() - stage_start
                row["status"] = "success"
                emit("encode", job_id=job_id, seconds=row["timing"]["encode_seconds"], status="success")
            except Exception as exc:
                row.update(status="failed", phase=phase, error=str(exc))
                # Returned explicit worker failures and media errors are safe to
                # continue. Transport/unknown status/timeouts can leave UE active.
                stopped = not isinstance(exc, ValueError)
                if isinstance(exc, WorkerError):
                    try:
                        reconciled = transport(dict(request, action="status"))
                        row["reconciled_status"] = reconciled
                        stopped = not renderer_idle(reconciled)
                    except Exception as reconciliation_error:
                        row["reconciliation_error"] = str(reconciliation_error)
                        stopped = True
                emit("failed", job_id=job_id, failed_phase=phase, error=str(exc), queue_stopped=stopped)
            finally:
                row["timing"]["total_seconds"] = time.monotonic() - started
                write(args.run_root / "jobs" / job_id / "driver_attempt.json", row)
                if stopped:
                    break
    finally:
        summary.update(finished_at=now(), queue_stopped=stopped)
        summary["status"] = "failed" if any(r["status"] == "failed" for r in summary["jobs"]) else "success"
        write(args.run_root / "driver_summary.json", summary)
    return 1 if summary["status"] == "failed" else 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(os.environ.get("DM_WORKSPACE", WORKSPACE)))
    default_engine = WORKSPACE.parent / "UE_5.8" if os.name == "nt" else WORKSPACE / "00_engine/unreal/UE_5.8"
    parser.add_argument("--engine-root", type=Path, default=Path(os.environ.get("DM_UE_ENGINE_ROOT", default_engine)))
    parser.add_argument("--project-root", type=Path, default=Path(os.environ.get("DM_UE_PROJECT_ROOT", WORKSPACE.parent / "projects/datatry_02")))
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--job-id", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--command-only", choices=("prepare", "render", "status"))
    parser.add_argument("--worker-module", choices=('ue_dataset_render_v11','ue_dataset_reference_pilot_v11',REFERENCE_WORKER),default='ue_dataset_render_v11')
    parser.add_argument("--portable-runtime",action='store_true',help='Use isolated path mapping for relocated workspaces/projects')
    parser.add_argument("--pool-mb",type=int,default=10240,help='Machine-specific MRQ texture pool')
    parser.add_argument("--node-id")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--force", action="store_true")
    # Full-resolution texture warmup can temporarily block editor discovery.
    parser.add_argument("--discovery-timeout", type=float, default=120)
    parser.add_argument("--command-timeout", type=float, default=180)
    parser.add_argument("--render-timeout", type=float, default=3600)
    parser.add_argument("--poll-interval", type=float, default=3)
    args = parser.parse_args(argv)
    if args.worker_module=='ue_dataset_reference_pilot_v11' and not args.command_only:parser.error('Legacy reference pilot supports command-only; use ue_dataset_reference_v11 for verified queues')
    if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
        parser.error("Require 0 <= shard-index < shard-count")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if min(args.discovery_timeout, args.command_timeout, args.render_timeout, args.poll_interval) <= 0:
        parser.error("Timeouts and poll interval must be positive")
    if args.run_root is None:
        default_run = "dataset_reference_hair_adaptive_20261023_v4" if args.worker_module == REFERENCE_WORKER else "dataset_render_pilot_20261023_v1"
        args.run_root = Path(os.environ.get("DM_RENDER_RUN_ROOT", args.workspace / "00_engine/outputs" / default_run))
    for key in ("workspace", "engine_root", "project_root", "run_root"):
        setattr(args, key, getattr(args, key).resolve())
    default_jobs = "reference_jobs.json" if args.worker_module == REFERENCE_WORKER else "pilot_jobs.json"
    args.jobs = (args.jobs or args.run_root / default_jobs).resolve()
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        with queue_lock(args.run_root):
            return run(args)
    except Exception as exc:
        emit("fatal", error=str(exc), queue_stopped=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
