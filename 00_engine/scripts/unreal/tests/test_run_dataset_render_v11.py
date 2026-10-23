"""Focused driver tests; no editor connection or real media encoding."""
import importlib.util
import hashlib
import json
import os
import binascii
from pathlib import Path
import subprocess
import struct
import sys
import time
import zlib
import pytest
from contextlib import contextmanager
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "run_dataset_render_v11.py"
spec = importlib.util.spec_from_file_location("dataset_driver_v11", SOURCE)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def arguments(tmp_path, *extra):
    manifest = tmp_path / "pilot_jobs.json"
    manifest.write_text(json.dumps({"jobs": [{"job_id": f"train_node_{i:06d}"} for i in range(3)]}))
    return driver.parse_args(["--run-root", str(tmp_path), "--poll-interval", ".001", *extra])


def encoder_ok(command, **kwargs):
    run_root = Path(command[command.index("--run-root") + 1])
    job_id = command[command.index("--job-id") + 1]
    directory = run_root / "jobs" / job_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "video.mp4").write_bytes(b"fake-encoded-video")
    driver.write(directory / "media_receipt.json", {"status": "success", "job_id": job_id})
    return subprocess.CompletedProcess(command, 0, "encoded", "")


def test_serial_queue_continues_after_terminal_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "bind_media_render_provenance", lambda args, job: {"signature": "fake"})
    args = arguments(tmp_path)
    events, polls = [], {}

    def transport(request):
        action, job = request["action"], request["job_id"]
        events.append((action, job))
        if action == "status":
            polls[job] = polls.get(job, 0) + 1
            if polls[job] == 1:
                return {"status": "idle"}
            if polls[job] == 2:
                return {"status": "rendering"}
            return {"status": "failed" if job.endswith("000000") else "completed"}
        return {"status": "prepared" if action == "prepare" else "rendering"}

    assert driver.run(args, transport, encoder_ok) == 1
    summary = driver.read(tmp_path / "driver_summary.json")
    assert [r["status"] for r in summary["jobs"]] == ["failed", "success", "success"]
    assert not summary["queue_stopped"]
    assert events.index(("prepare", "train_node_000001")) > events.index(("render", "train_node_000000")) + 2


def test_timeout_stops_remaining_queue(tmp_path):
    args = arguments(tmp_path, "--render-timeout", ".005")
    events = []

    def transport(request):
        events.append((request["action"], request["job_id"]))
        return {"status": "idle" if len(events) == 1 else "rendering"}

    assert driver.run(args, transport, encoder_ok) == 1
    assert {job for _, job in events} == {"train_node_000000"}
    assert driver.read(tmp_path / "driver_summary.json")["queue_stopped"]


def test_unknown_poll_result_stops_queue(tmp_path):
    args = arguments(tmp_path)
    count = 0

    def transport(request):
        nonlocal count
        count += 1
        return {"status": "idle" if count == 1 else "prepared" if count == 2 else "rendering" if count == 3 else "unknown"}

    assert driver.run(args, transport, encoder_ok) == 1
    assert len(driver.read(tmp_path / "driver_summary.json")["jobs"]) == 1


def test_job_selection_and_command_only(tmp_path):
    args = arguments(tmp_path, "--job-id", "train_node_000001", "--command-only", "prepare")
    events = []
    assert driver.run(args, lambda request: events.append(request) or {"status": "prepared"}) == 0
    assert len(events) == 1
    assert events[0]["job_id"] == "train_node_000001"
    args = arguments(tmp_path, "--shard-count", "2", "--shard-index", "1")
    assert [j["job_id"] for j in driver.select_jobs(args)] == ["train_node_000001"]


def test_discovery_ignores_old_user_and_path_mapping(tmp_path):
    args = arguments(tmp_path, "--project-root", str(tmp_path / "MyProject.uproject"))
    transport = driver.Transport.__new__(driver.Transport)
    transport.args, transport.node_id = args, None
    node = {"project_name": "MyProject", "node_id": "new-editor", "user": "server-user"}
    assert transport.select_node([node])["node_id"] == "new-editor"
    assert driver.editor_path(tmp_path / "jobs/a", {str(tmp_path): "/server/work"}) == "/server/work/jobs/a"


def test_worker_receipt_waits_for_executor_teardown():
    responses = iter([
        {"subsystem_rendering": True, "owned_executor_active": True, "owned_attempt_id": "new",
         "receipt": {"status": "completed", "attempt_id": "new", "success": True}},
        {"subsystem_rendering": False, "owned_executor_active": False, "owned_attempt_id": "new",
         "receipt": {"status": "completed", "attempt_id": "new", "success": True}},
    ])
    result = driver.wait_render(lambda request: next(responses), {}, time.monotonic(), 1, .001,
                                {"owned_attempt_id": "new"})
    assert result["subsystem_rendering"] is False


def test_transport_uses_command_lock_and_fresh_discovery(tmp_path, monkeypatch):
    args = arguments(tmp_path, "--project-root", str(tmp_path / "ServerProject.uproject"))
    calls = []
    locked = False

    @contextmanager
    def lock():
        nonlocal locked
        locked = True
        try:
            yield
        finally:
            locked = False

    class Session:
        remote_nodes = [{"node_id": "new-node", "project_name": "ServerProject", "user": "server"}]
        _command_connection = SimpleNamespace(_command_channel_socket=SimpleNamespace(settimeout=lambda value: None))

        def start(self):
            calls.append("start")

        def stop(self):
            calls.append("stop")

        def open_command_connection(self, node):
            assert locked and node == "new-node"

        def run_command(self, command, **kwargs):
            assert locked and "ue_dataset_render_v11" in command and ".dispatch(" in command
            return {"success": True, "output": [{"output": driver.MARKER + '{"subsystem_rendering":false}'}]}

    module = SimpleNamespace(RemoteExecution=Session, MODE_EXEC_FILE="ExecuteFile")
    panel = SimpleNamespace(bridge=SimpleNamespace(command_lock=lock, load_remote_execution=lambda path: module),
                            install_complete_reply_receiver=lambda value: None)
    monkeypatch.setitem(sys.modules, "scene_site_review_panel_v1", panel)
    result = driver.Transport(args)({"action": "status", "run_root": str(tmp_path)})
    assert result == {"subsystem_rendering": False}
    assert calls == ["start", "stop"]
    assert len(list((tmp_path / "remote").glob("*.json"))) == 1


def test_verified_resume_rejects_changed_media(tmp_path, monkeypatch):
    args = arguments(tmp_path, "--limit", "1")
    job = driver.select_jobs(args)[0]
    directory = tmp_path / "jobs" / job["job_id"]
    directory.mkdir(parents=True)
    video = directory / "video.mp4"
    video.write_bytes(b"verified-output")
    encoder = SimpleNamespace(ENCODING={"profile": "test"},
                              digest=lambda path: hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(driver, "load_encoder", lambda workspace: encoder)
    monkeypatch.setattr(driver, "renderer_signature", lambda args, job: "render-v2")
    signature = hashlib.sha256(json.dumps({"job": job, "encoding": encoder.ENCODING}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt = {"status": "success", "job_id": job["job_id"], "spec_sha256": signature,
               "video_sha256": encoder.digest(video), "input_sha256": "verified-input"}
    driver.write(directory / "media_receipt.json", receipt)
    assert not driver.verified_resume(args, job)  # Pre-policy receipts lack a binding.
    driver.write(directory / "media_receipt.json", dict(receipt, render_signature="render-v1"))
    assert not driver.verified_resume(args, job)  # Same job/encoder/video, old renderer.
    driver.write(directory / "media_receipt.json", dict(receipt, render_signature="render-v2"))
    assert not (directory / "frames").exists()  # Valid current media survives raw cleanup.
    assert driver.verified_resume(args, job)
    assert driver.run(args, lambda request: (_ for _ in ()).throw(AssertionError("Must skip editor"))) == 0
    video.write_bytes(b"changed")
    assert not driver.verified_resume(args, job)


def test_worker_exception_continues_only_after_idle_reconciliation(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "bind_media_render_provenance", lambda args, job: {"signature": "fake"})
    args = arguments(tmp_path, "--limit", "2")
    rendered = set()

    def transport(request):
        action, job = request["action"], request["job_id"]
        if action == "prepare" and job.endswith("000000"):
            raise driver.WorkerError("Missing source asset")
        if action == "render":
            rendered.add(job)
            return {"status": "submitted"}
        return {"status": "completed" if job in rendered else "idle"}

    assert driver.run(args, transport, encoder_ok) == 1
    result = driver.read(tmp_path / "driver_summary.json")
    assert not result["queue_stopped"]
    assert [row["status"] for row in result["jobs"]] == ["failed", "success"]


def test_completed_render_resumes_encode_and_rejects_new_failed_attempt(tmp_path):
    workspace = tmp_path / "workspace"
    worker = workspace / "00_engine/scripts/unreal/ue_dataset_render_v11.py"
    worker.parent.mkdir(parents=True)
    worker.write_text('def signature(job):\n    return "current-signature"\n')
    args = arguments(tmp_path, "--limit", "1", "--workspace", str(workspace))
    job = driver.select_jobs(args)[0]
    directory = tmp_path / "jobs" / job["job_id"]
    (directory / "frames").mkdir(parents=True)
    driver.write(directory / "prepared.json", {"signature": "current-signature"})
    receipt = {"jobs": [{"shot_id": job["job_id"]}], "status": "completed", "success": True,
               "job_signature": "current-signature", "frames_directory": str(directory / "frames")}
    path = tmp_path / "render_receipts/old.json"
    driver.write(path, receipt)
    events = []
    assert driver.run(args, lambda request: events.append(request["action"]) or {"status": "idle"}, encoder_ok) == 0
    assert events == ["status"]
    assert driver.read(directory / "driver_attempt.json")["reused_render"]["signature"] == "current-signature"
    media = driver.read(directory / "media_receipt.json")
    assert media["render_signature"] == "current-signature"
    assert media["render_provenance"]["receipt_relative_path"] == "render_receipts/old.json"
    assert media["render_provenance"]["receipt_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    newer = tmp_path / "render_receipts/new.json"
    driver.write(newer, dict(receipt, status="failed", success=False))
    timestamp = path.stat().st_mtime + 1
    os.utime(newer, (timestamp, timestamp))
    assert driver.completed_render_receipt(args, job) is None
    newer.unlink()
    driver.write(directory / "prepared.json", {"signature": "changed-job"})
    assert driver.completed_render_receipt(args, job) is None


def test_renderer_signature_reads_changed_source_even_with_same_size_and_mtime(tmp_path):
    workspace = tmp_path / "workspace"
    worker = workspace / "00_engine/scripts/unreal/ue_dataset_render_v11.py"
    worker.parent.mkdir(parents=True)
    worker.write_text('VERSION = 1\ndef signature(job):\n    return str(VERSION)\n')
    args = arguments(tmp_path, "--limit", "1", "--workspace", str(workspace))
    job = driver.select_jobs(args)[0]
    old_stat = worker.stat()
    assert driver.renderer_signature(args, job) == "1"
    worker.write_text('VERSION = 2\ndef signature(job):\n    return str(VERSION)\n')
    os.utime(worker, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    assert driver.renderer_signature(args, job) == "2"


def reference_arguments(tmp_path, jobs):
    workspace = tmp_path / "workspace"
    scripts = workspace / "00_engine/scripts/unreal"
    scripts.mkdir(parents=True)
    (scripts / "ue_dataset_reference_v11.py").write_text(
        'VERSION = 1\ndef signature(job):\n    return "ref-%s-%s" % (VERSION, job["job_id"])\n')
    (scripts / "ue_dataset_render_v11.py").write_text('def signature(job):\n    return "wrong-main-worker"\n')
    manifest = tmp_path / "reference_jobs.json"
    driver.write(manifest, {"jobs": jobs})
    return driver.parse_args(["--workspace", str(workspace), "--run-root", str(tmp_path),
                              "--worker-module", "ue_dataset_reference_v11", "--poll-interval", ".001"])


def png_fixture(width=2, height=3, channels=4):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    header = struct.pack(">IIBBBBB", width, height, 8, 6 if channels == 4 else 2, 0, 0, 0)
    pixels = (b"\0" + bytes([90] * width * channels)) * height
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def fake_reference_transport(args, jobs, events):
    completed = {}
    by_id = {job["job_id"]: job for job in jobs}

    def transport(request):
        job_id, action = request["job_id"], request["action"]
        events.append((action, job_id))
        job, directory = by_id[job_id], args.run_root / "jobs" / job_id
        signature = driver.renderer_signature(args, job)
        if action == "prepare":
            driver.write(directory / "prepared.json", {"signature": signature})
            return {"success": True}
        if action == "render":
            frames = directory / "frames"
            frames.mkdir(parents=True)
            if job["reference_kind"] != "motion":
                (frames / "frame_0000.png").write_bytes(png_fixture(job["width"], job["height"]))
            path = args.run_root / "render_receipts" / (job_id + "_attempt.json")
            receipt = {"jobs": [{"shot_id": job_id}], "status": "completed", "success": True,
                       "attempt_id": job_id + "_attempt", "job_signature": signature, "frames_directory": str(frames)}
            driver.write(path, receipt)
            completed[job_id] = {"subsystem_rendering": False, "owned_executor_active": False,
                                 "owned_attempt_id": receipt["attempt_id"], "receipt_path": str(path), "receipt": receipt}
            return {"owned_attempt_id": receipt["attempt_id"], "status": "submitted"}
        return completed.get(job_id, {"status": "idle"})
    return transport


def test_static_reference_queue_preserves_png_and_resumes_without_encoder(tmp_path):
    job = {"job_id": "ref_identity_A_front", "reference_kind": "identity", "source_job_id": "train_node_000000",
           "width": 2, "height": 3, "frames": 1}  # No state/site/appearance needed.
    args = reference_arguments(tmp_path, [job])
    events = []
    transport = fake_reference_transport(args, [job], events)
    def no_encoder(*args, **kwargs):
        raise AssertionError("Static PNG must never reach FFmpeg")
    assert driver.run(args, transport, no_encoder) == 0
    directory = tmp_path / "jobs" / job["job_id"]
    receipt = driver.read(directory / "media_receipt.json")
    assert receipt["media_kind"] == "png"
    assert receipt["media"]["channels"] == "RGBA" and receipt["media"]["frames"] == 1
    assert receipt["render_signature"] == "ref-1-ref_identity_A_front"
    assert receipt["render_provenance"]["worker_module"] == "ue_dataset_reference_v11"
    assert (directory / "frames/frame_0000.png").read_bytes() == png_fixture()
    assert not (directory / "video.mp4").exists()
    assert driver.verified_resume(args, job)
    assert driver.run(args, lambda request: (_ for _ in ()).throw(AssertionError("Must reuse PNG")), no_encoder) == 0
    (directory / "frames/frame_0000.png").write_bytes(png_fixture(channels=3))
    assert not driver.verified_resume(args, job)
    (directory / "frames/frame_0000.png").write_bytes(png_fixture())
    worker = args.workspace / "00_engine/scripts/unreal/ue_dataset_reference_v11.py"
    worker.write_text(worker.read_text().replace("VERSION = 1", "VERSION = 2"))
    assert not driver.verified_resume(args, job)


def test_mixed_static_motion_queue_encodes_only_300_frame_reference(tmp_path):
    jobs = [{"job_id": "ref_scene_A", "reference_kind": "scene", "source_job_id": "train_node_000000", "width": 2, "height": 3},
            {"job_id": "ref_motion_A", "reference_kind": "motion", "source_job_id": "train_node_000000",
             "width": 2, "height": 4, "frames": 300, "fps": 30}]
    args = reference_arguments(tmp_path, jobs)
    events, encodes = [], []
    def encode(command, **kwargs):
        encodes.append(command)
        return encoder_ok(command, **kwargs)
    assert driver.run(args, fake_reference_transport(args, jobs, events), encode) == 0
    assert len(encodes) == 1 and encodes[0][encodes[0].index("--job-id") + 1] == "ref_motion_A"
    assert "--jobs" in encodes[0]
    assert driver.read(tmp_path / "jobs/ref_motion_A/media_receipt.json")["render_signature"] == "ref-1-ref_motion_A"
    assert events.index(("prepare", "ref_motion_A")) > events.index(("render", "ref_scene_A")) + 1


@pytest.mark.parametrize("channels", [3, 4])
def test_png_validation_checks_whole_image_crc_dimensions_and_extra_frames(tmp_path, channels):
    frames = tmp_path / "frames"
    frames.mkdir()
    path = frames / "frame_0000.png"
    original = png_fixture(channels=channels)
    path.write_bytes(original)
    job = {"width": 2, "height": 3}
    assert driver.inspect_static_png(tmp_path, job)["media"]["channels"] == ("RGB" if channels == 3 else "RGBA")
    path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(ValueError, match="CRC"):
        driver.inspect_static_png(tmp_path, job)
    path.write_bytes(original)
    with pytest.raises(ValueError, match="dimensions"):
        driver.inspect_static_png(tmp_path, {"width": 3, "height": 3})
    (frames / "frame_0001.png").write_bytes(original)
    with pytest.raises(ValueError, match="exactly"):
        driver.inspect_static_png(tmp_path, job)


def test_reference_defaults_and_frame_contracts(tmp_path, monkeypatch):
    monkeypatch.delenv("DM_RENDER_RUN_ROOT", raising=False)
    args = driver.parse_args(["--workspace", str(tmp_path), "--worker-module", "ue_dataset_reference_v11"])
    assert args.run_root.name == "dataset_reference_hair_adaptive_20261023_v4"
    assert args.jobs.name == "reference_jobs.json"
    with pytest.raises(ValueError, match="300"):
        driver.media_kind(args, {"reference_kind": "motion", "frames": 1, "fps": 30})
    with pytest.raises(ValueError, match="one PNG"):
        driver.media_kind(args, {"reference_kind": "hair", "frames": 300})
