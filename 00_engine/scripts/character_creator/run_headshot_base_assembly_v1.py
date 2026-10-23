"""Prepare or serially submit bounded Headshot base assembly jobs.

Default is preparation only. Failed attempts remain intact; pending jobs are
never resubmitted; completed characters are skipped only after hash/readback
checks. This controller never exports, imports into UE, restarts or connects CC.
"""

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

from cc_compile_headshot_base_assembly_v1 import compile_base_assembly


REPO = Path(__file__).resolve().parents[3]
RUN_ID = "headshot_base_assembly_20261005_v1"
RUN_ROOT = REPO / "00_engine/outputs/character_creator_bridge/artifacts" / RUN_ID
STAGE_ROOT = Path(__file__).parent / "runtime_staging" / RUN_ID
BRIDGE_ROOT = REPO / "00_engine/outputs/character_creator_bridge"
CLIENT = REPO / "00_engine/character_creator_bridge/cc_bridge_client.py"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class ControllerError(RuntimeError):
    pass


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def now():
    return datetime.datetime.now().astimezone().isoformat()


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def fingerprint(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def bind(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def verify(reference, label):
    try:
        actual = sha(reference["path"])
    except (KeyError, OSError) as error:
        raise ControllerError(label + " missing") from error
    if actual != reference.get("sha256"):
        raise ControllerError(label + " SHA changed; cannot skip or reuse")


def checked_manifest(state):
    for name in ("original", "working_copy", "manifest", "library"):
        verify(state[name], name)
    manifest = read(state["manifest"]["path"])
    if manifest["source_sha256"] != state["working_copy"]["sha256"]:
        raise ControllerError("Manifest input lineage differs")
    for asset in manifest["assets"]:
        verify(asset, "asset " + asset["asset_id"])
    verify({"path": manifest["regions_path"], "sha256": manifest["regions_sha256"]}, "regions")
    verify(manifest["registry"], "registry")
    verify(manifest["face_material_quality_profile"], "quality profile")
    policy_reference = manifest.get("geometry_policy")
    if policy_reference:
        verify(policy_reference, "geometry policy")
        policy = read(policy_reference["path"])
        for record in policy["policies"].values():
            verify({"path": record["evidence"], "sha256": record["evidence_sha256"]}, "geometry policy evidence")
    if read(state["library"]["path"]).get("base_assembly") != manifest:
        raise ControllerError("Library and manifest disagree")
    return manifest


def completed_valid(state):
    """Fail closed on drift; never turn changed completed work into a retry."""
    manifest = checked_manifest(state)
    for name in ("bridge_result", "assembly_report", "geometry_report", "saved_project"):
        verify(state[name], name)
    report = read(state["assembly_report"]["path"])
    geometry = read(state["geometry_report"]["path"])
    if (report.get("success") is not True or report.get("source_unchanged") is not True
            or report.get("config") != manifest or geometry.get("passed") is not True
            or not geometry.get("steps")
            or not all(step.get("passed") is True for step in geometry["steps"])
            or report.get("saved_project", {}).get("sha256") != state["saved_project"]["sha256"]
            or Path(state["saved_project"]["path"]).resolve() != Path(manifest["output_project"]).resolve()):
        raise ControllerError("Completed receipts do not match the protected manifest")
    return True


def prepare(request, *, run_root=RUN_ROOT, stage_root=STAGE_ROOT):
    """Prepare a new attempt or reuse the exact protected previous attempt."""
    request = dict(request)
    character_id = request.get("character_id", "")
    if not isinstance(character_id, str) or not SAFE_ID.fullmatch(character_id):
        raise ControllerError("character_id must be a simple ASCII identifier, up to64 characters")
    original = Path(request["source_project"]).resolve()
    request["source_project"] = str(original)
    request_hash = fingerprint(request)
    source_hash = sha(original)
    if request.get("source_sha256") not in (None, source_hash):
        raise ControllerError("Original source SHA differs from request")
    run_root, stage_root = Path(run_root).resolve(), Path(stage_root).resolve()
    if request.get("output_project") is not None:
        declared = Path(request["output_project"]).resolve()
        if not declared.is_relative_to(run_root) or declared == original:
            raise ControllerError("Declared output must be independent and inside the pinned run")
    character_root = run_root / character_id
    attempts = sorted(character_root.glob("attempt_[0-9][0-9][0-9]"))
    if attempts:
        state_path = attempts[-1] / "controller_state.json"
        if not state_path.is_file():
            raise ControllerError("Incomplete preparation exists; inspect it before retrying")
        previous = read(state_path)
        if previous["status"] != "failed":
            if previous["request_sha256"] != request_hash:
                raise ControllerError("Existing character request differs; use a new character_id")
            checked_manifest(previous)
            if previous["status"] == "completed":
                completed_valid(previous)
            elif previous["status"] not in ("prepared", "pending"):
                raise ControllerError("Unknown previous status; do not resubmit")
            return previous
        # A failed attempt is immutable. Fresh copy and new job/output are mandatory.
    attempt_id = "attempt_{:03d}".format(len(attempts) + 1)
    output_dir = character_root / attempt_id
    stage_dir = stage_root / character_id / attempt_id
    if output_dir.exists() or stage_dir.exists():
        raise ControllerError("Attempt path already exists")
    output_dir.mkdir(parents=True)
    stage_dir.mkdir(parents=True)
    copied = stage_dir / "INPUT.ccProject"
    shutil.copyfile(original, copied)
    if sha(original) != source_hash or sha(copied) != source_hash:
        raise ControllerError("Original or working copy changed during preparation")
    compile_request = dict(request)
    compile_request.update(source_project=str(copied), source_sha256=source_hash,
        output_project=str(output_dir / ("ASSEMBLED_" + character_id + ".ccProject")))
    try:
        manifest = compile_base_assembly(compile_request)
    except Exception as error:
        # Preparation failures also receive an immutable attempt record. The
        # next invocation may start a new attempt without erasing this evidence.
        write(output_dir / "controller_state.json", {
            "schema_version": 1, "status": "failed", "created_at": now(),
            "character_id": character_id, "attempt_id": attempt_id,
            "request_sha256": request_hash, "original": bind(original),
            "working_copy": bind(copied),
            "failure": {"phase": "compile_manifest", "message": str(error)},
        })
        raise
    manifest["input_lineage"] = {
        "original_project": str(original), "original_sha256": source_hash,
        "working_copy": str(copied), "copy_sha256": source_hash,
    }
    library = {"schema_version": 1, "diagnostic_mode": "headshot_base_assembly",
        "base_assembly": manifest,
        "presets": [{"preset_id": character_id, "base_avatar": {"path": str(copied)},
                     "source_project": {"path": str(copied)}}]}
    manifest_path = output_dir / "assembly_manifest.json"
    library_path = stage_dir / "assembly_library.json"
    write(output_dir / "request.json", request)
    write(manifest_path, manifest)
    write(library_path, library)
    state = {
        "schema_version": 1, "status": "prepared", "created_at": now(),
        "character_id": character_id, "attempt_id": attempt_id,
        "job_id": "hs_base_" + uuid.uuid4().hex,
        "request_sha256": request_hash, "original": bind(original),
        "working_copy": bind(copied), "manifest": bind(manifest_path),
        "library": bind(library_path), "output_dir": str(output_dir),
        "state_path": str(output_dir / "controller_state.json"),
        "recovery": "Failed: prepare a new attempt from original. Pending: read same job result; never resubmit. Completed: verify hashes and skip.",
    }
    if sha(original) != source_hash:
        raise ControllerError("Original changed after compilation")
    write(state["state_path"], state)
    return state


def bridge_cli(arguments):
    process = subprocess.run([sys.executable, str(CLIENT), *arguments],
        capture_output=True, text=True, encoding="utf-8", timeout=30)
    if process.returncode:
        raise ControllerError(process.stdout + process.stderr)
    return json.loads(process.stdout)


def settle_result(state, result_path):
    result = read(result_path)
    if result.get("job_id") != state["job_id"]:
        raise ControllerError("Bridge result belongs to another job")
    if result.get("status") not in ("succeeded", "failed", "cancelled"):
        raise ControllerError("Unknown bridge result status; do not resubmit")
    state["bridge_result"] = bind(result_path)
    output_dir = Path(state["output_dir"])
    report_path = output_dir / "assembly_report.json"
    geometry_path = output_dir / "assembly_geometry_invariants.json"
    state["updated_at"] = now()
    if result["status"] == "succeeded" and report_path.is_file() and geometry_path.is_file():
        report = read(report_path)
        if report.get("success") is True:
            state.update(assembly_report=bind(report_path), geometry_report=bind(geometry_path),
                         saved_project=report["saved_project"])
            # Do not publish completed if any hash/readback disagrees.
            completed_valid(state)
            state["status"] = "completed"
            write(state["state_path"], state)
            return state
    state["status"] = "failed"
    state["failure"] = result.get("error") or (read(report_path).get("error") if report_path.is_file() else {"message": "Bridge succeeded without a complete successful assembly receipt"})
    write(state["state_path"], state)
    return state


def execute(state, *, bridge_root=BRIDGE_ROOT, client_call=bridge_cli, wait_seconds=60):
    """Serial submission; ambiguous pending work is never automatically retried."""
    if not math.isfinite(wait_seconds) or wait_seconds < 0:
        raise ControllerError("wait_seconds must be finite and nonnegative")
    checked_manifest(state)
    if state["status"] == "completed":
        completed_valid(state)
        return state
    if state["status"] == "failed":
        raise ControllerError("Prepare a new attempt after a terminal failed result")
    bridge_root = Path(bridge_root)
    job_id = state["job_id"]
    result_path = bridge_root / "results" / (job_id + ".json")
    if result_path.is_file():
        return settle_result(state, result_path)
    queued = any((bridge_root / area / (job_id + ".json")).exists() for area in ("inbox", "processing"))
    if state["status"] == "prepared" and not queued:
        health = client_call(["health"])
        active = (health.get("heartbeat") or {}).get("active_job_id")
        if active == job_id:
            queued = True
        elif active or not health.get("healthy"):
            raise ControllerError("CC bridge is unavailable or another job is active")
        elif any(list((bridge_root / area).glob("*.json")) for area in ("inbox", "processing")):
            raise ControllerError("Other queued CC work exists")
        if not queued:
            # Durable pending before submission closes the uncertain-return gap.
            state.update(status="pending", submitted_at=now())
            write(state["state_path"], state)
            try:
                state["submission"] = client_call([
                    "validate-bodies", "--library-file", state["library"]["path"],
                    "--output-dir", state["output_dir"], "--confirm-scene-replace",
                    "--auto-dismiss-undo-warning", "--job-id", job_id, "--no-wait",
                ])
            except Exception as error:
                state["submission_error"] = str(error)
                write(state["state_path"], state)
                raise ControllerError("Submission outcome uncertain; inspect the same job, do not resubmit") from error
    state.update(status="pending", updated_at=now())
    write(state["state_path"], state)
    deadline = time.monotonic() + wait_seconds
    while not result_path.is_file() and time.monotonic() < deadline:
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    if result_path.is_file():
        return settle_result(state, result_path)
    state["pending_notice"] = "No terminal result yet. Observe this job_id; pending work is not resubmitted. Batch stopped."
    write(state["state_path"], state)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--request", help="One request object JSON")
    inputs.add_argument("--batch", help="JSON list of request objects (serial CC only)")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-only", action="store_true", help="Default: no CC submission")
    modes.add_argument("--execute", action="store_true", help="Explicitly submit prepared jobs to currently running CC")
    parser.add_argument("--wait-seconds", type=float, default=60,
                        help="Bounded wait per job; use600/1800 for longer serial runs")
    args = parser.parse_args(argv)
    requests = [read(args.request)] if args.request else read(args.batch)
    if not isinstance(requests, list) or not requests or not all(isinstance(r, dict) for r in requests):
        raise ControllerError("Batch must be a nonempty list of request objects")
    ids = [r.get("character_id") for r in requests]
    if len(ids) != len(set(ids)):
        raise ControllerError("Batch repeats character IDs")
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = RUN_ROOT / "controller.lock"
    try:
        lock = lock_path.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise ControllerError("Another controller may be active; inspect its lock before running") from error
    try:
        with lock:
            lock.write(now())
        for request in requests:
            state = prepare(request)
            if args.execute:
                state = execute(state, wait_seconds=args.wait_seconds)
            print(json.dumps({key: state[key] for key in ("character_id", "attempt_id", "job_id", "status", "output_dir")}), flush=True)
            if args.execute and state["status"] in ("pending", "failed"):
                return 2
    finally:
        lock_path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
