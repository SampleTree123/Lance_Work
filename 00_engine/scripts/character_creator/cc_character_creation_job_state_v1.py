"""Durable serial Bridge steps for CC character creation (no CC SDK import).

Pending submissions are deliberately never retried. A Bridge success is only
a succeeded step: the pipeline must bind its expected outputs before completion.
"""

from contextlib import contextmanager
import datetime
import json
import math
import os
from pathlib import Path
import time
import uuid

# Reuse the established controller's file hashes and Bridge client rather than
# implementing a second wire protocol or a second CC process manager.
from run_headshot_base_assembly_v1 import (
    SAFE_ID, ControllerError, bind, bridge_cli, fingerprint, read, sha, verify, write,
)

REPO = Path(__file__).resolve().parents[3]
RUN_ID = "headshot_character_creation_20261005_v1"
RUN_ROOT = REPO / "00_engine/outputs/character_creator_bridge/artifacts" / RUN_ID
STAGE_ROOT = Path(__file__).parent / "runtime_staging" / RUN_ID
BRIDGE_ROOT = REPO / "00_engine/outputs/character_creator_bridge"


def now():
    return datetime.datetime.now().astimezone().isoformat()


def _inside(path, root, label):
    value, boundary = Path(path).resolve(), Path(root).resolve()
    if not value.is_relative_to(boundary):
        raise ControllerError(label + " is outside its pinned directory")
    return value


@contextmanager
def controller_lock(run_root=RUN_ROOT):
    """Exclusive controller ownership; stale locks need explicit inspection."""
    root = Path(run_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "controller.lock"
    token = uuid.uuid4().hex
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump({"token": token, "pid": os.getpid(), "created_at": now()}, handle)
    except FileExistsError as error:
        raise ControllerError("A controller lock already exists; inspect its owner before retrying") from error
    try:
        yield
    finally:
        # Do not remove a replacement lock owned by another controller.
        if path.is_file() and read(path).get("token") == token:
            path.unlink()


class BridgeStepDriver:
    def __init__(self, *, run_root=RUN_ROOT, stage_root=STAGE_ROOT,
                 bridge_root=BRIDGE_ROOT, client_call=bridge_cli,
                 clock=time.monotonic, sleep=time.sleep):
        self.run_root = Path(run_root).resolve()
        self.stage_root = Path(stage_root).resolve()
        self.bridge_root = Path(bridge_root).resolve()
        self.client_call = client_call
        self.clock = clock
        self.sleep = sleep

    def verify_state_inputs(self, state):
        if not SAFE_ID.fullmatch(state.get("character_id", "")):
            raise ControllerError("Invalid character_id")
        _inside(state["attempt_dir"], self.run_root, "attempt_dir")
        _inside(state["stage_dir"], self.stage_root, "stage_dir")
        _inside(state["state_path"], state["attempt_dir"], "state_path")
        if fingerprint(state["request"]) != state.get("request_fingerprint"):
            raise ControllerError("Request fingerprint changed")
        mode = state["request"].get("appearance_mode", "assembled")
        if mode not in ("assembled", "headshot_native") or state.get("appearance_mode", "assembled") != mode:
            raise ControllerError("Persisted appearance_mode differs from the protected request")
        references = state.get("inputs", state.get("input_bindings", []))
        references = references.values() if isinstance(references, dict) else references
        for reference in references:
            verify(reference, "Input")

    def persist(self, state):
        self.verify_state_inputs(state)
        state["updated_at"] = now()
        write(state["state_path"], state)
        return state

    def _verify_step(self, state, step):
        self.verify_state_inputs(state)
        if step.get("status") not in ("pending", "succeeded", "completed", "failed"):
            raise ControllerError("Unknown persisted step status; inspect it rather than resubmitting")
        if not isinstance(step.get("job_id"), str) or not SAFE_ID.fullmatch(step["job_id"]):
            raise ControllerError("Invalid persisted Bridge job_id")
        verify(step["library"], "Step library")
        _inside(step["library"]["path"], state["stage_dir"], "Step library")
        _inside(step["output_dir"], state["attempt_dir"], "Step output_dir")
        if step["status"] in ("succeeded", "completed", "failed"):
            expected = self.bridge_root / "results" / (step["job_id"] + ".json")
            if Path(step["bridge_result"]["path"]).resolve() != expected.resolve():
                raise ControllerError("Bridge result reference does not match the recorded job")
            verify(step["bridge_result"], "Bridge result")
            result = read(step["bridge_result"]["path"])
            self._validate_result(step, result)
            if step["status"] in ("succeeded", "completed") and result["status"] != "succeeded":
                raise ControllerError("Successful step does not have a successful Bridge result")

    @staticmethod
    def _validate_result(step, result):
        if result.get("job_id") != step["job_id"]:
            raise ControllerError("Bridge result belongs to another job")
        if result.get("command") != "validate_bodyfit_library":
            raise ControllerError("Bridge result command does not match this step")
        if result.get("status") not in ("succeeded", "failed", "cancelled"):
            raise ControllerError("Unknown Bridge terminal status")
        if result["status"] == "succeeded":
            payload = result.get("result") or {}
            for key, expected in (("library_file", step["library"]["path"]),
                                  ("output_dir", step["output_dir"])):
                if not payload.get(key) or Path(payload[key]).resolve() != Path(expected).resolve():
                    raise ControllerError("Bridge success refers to a different " + key)

    def submit_step(self, state, step_id, library, output_dir):
        self.verify_state_inputs(state)
        if not isinstance(step_id, str) or not SAFE_ID.fullmatch(step_id):
            raise ControllerError("Invalid step_id")
        steps = state.setdefault("steps", {})
        if step_id in steps:
            step = steps[step_id]
            self._verify_step(state, step)
            if read(step["library"]["path"]) != library or Path(step["output_dir"]).resolve() != Path(output_dir).resolve():
                raise ControllerError("Existing step configuration differs; do not resume altered work")
            if step["status"] == "failed":
                raise ControllerError("Failed steps require a new attempt from the original input")
            if step["status"] == "completed":
                self.verify_completed_step(state, step)
            # This covers uncertain submissions as well as ordinary pending work.
            return step
        if state.get("status") in ("failed", "completed"):
            raise ControllerError("Cannot add work to a failed or completed attempt")
        if any(step["status"] in ("pending", "succeeded") for step in steps.values()):
            raise ControllerError("A previous step is pending or has unbound outputs")
        for previous in steps.values():
            self.verify_completed_step(state, previous)
        health = self.client_call(["health"])
        if not health.get("healthy") or (health.get("heartbeat") or {}).get("active_job_id"):
            raise ControllerError("CC Bridge is unavailable or busy")
        if any(list((self.bridge_root / area).glob("*.json")) for area in ("inbox", "processing")):
            raise ControllerError("Other queued CC work exists")
        output_dir = _inside(output_dir, state["attempt_dir"], "Step output_dir")
        if output_dir == Path(state["attempt_dir"]).resolve():
            raise ControllerError("Step outputs need their own subdirectory")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise ControllerError("Step output directory is already populated")
        output_dir.mkdir(parents=True, exist_ok=True)
        library_path = Path(state["stage_dir"]) / (step_id + "_library.json")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        with library_path.open("x", encoding="utf-8") as handle:
            json.dump(library, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
        step = {
            "step_id": step_id, "status": "pending", "job_id": "cc_create_" + uuid.uuid4().hex,
            "library": bind(library_path), "output_dir": str(output_dir), "submitted_at": now(),
        }
        steps[step_id] = step
        state["status"] = "pending"
        # Persist before calling the external client: ambiguous return is pending,
        # never a signal to issue the same command again.
        self.persist(state)
        try:
            step["submission"] = self.client_call([
                "validate-bodies", "--library-file", str(library_path),
                "--output-dir", str(output_dir), "--confirm-scene-replace",
                "--auto-dismiss-undo-warning", "--job-id", step["job_id"], "--no-wait",
            ])
        except Exception as error:
            step["submission_error"] = str(error)
            self.persist(state)
            raise ControllerError("Submission outcome uncertain; query this same job_id, never resubmit") from error
        self.persist(state)
        return step

    def wait_step(self, state, step_id, wait_seconds=600):
        if not math.isfinite(wait_seconds) or wait_seconds < 0:
            raise ControllerError("wait_seconds must be finite and nonnegative")
        step = state["steps"][step_id]
        self._verify_step(state, step)
        if step["status"] != "pending":
            return step
        result_path = self.bridge_root / "results" / (step["job_id"] + ".json")
        deadline = self.clock() + wait_seconds
        while not result_path.is_file() and self.clock() < deadline:
            self.sleep(min(1, max(0, deadline - self.clock())))
        if not result_path.is_file():
            step["pending_notice"] = "No terminal result; resume by querying this job_id only."
            self.persist(state)
            return step
        result = read(result_path)
        self._validate_result(step, result)
        step["bridge_result"] = bind(result_path)
        step["status"] = "succeeded" if result["status"] == "succeeded" else "failed"
        step["finished_at"] = result.get("finished_at", now())
        if step["status"] == "failed":
            state["status"] = "failed"
            state["failure"] = {"step_id": step_id, "bridge_error": result.get("error")}
        self.persist(state)
        return step

    def mark_step_complete(self, state, step_id, outputs):
        step = state["steps"][step_id]
        self._verify_step(state, step)
        if step["status"] != "succeeded":
            raise ControllerError("Only a succeeded step may bind completion outputs")
        if not isinstance(outputs, dict) or not outputs:
            raise ControllerError("Completion requires named output receipts")
        bound = {}
        for name, reference in outputs.items():
            path = Path(reference["path"] if isinstance(reference, dict) else reference).resolve()
            if not (path.is_relative_to(Path(state["attempt_dir"]).resolve())
                    or path.is_relative_to(Path(state["stage_dir"]).resolve())):
                raise ControllerError("Completion output lies outside this attempt")
            if isinstance(reference, dict):
                verify(reference, "Output " + name)
            bound[name] = bind(path)
        step["outputs"] = bound
        step["status"] = "completed"
        self.persist(state)
        return step

    def verify_completed_step(self, state, step):
        if isinstance(step, str):
            step = state["steps"][step]
        self._verify_step(state, step)
        if step["status"] != "completed" or not step.get("outputs"):
            raise ControllerError("Step is not complete with bound outputs")
        if read(step["bridge_result"]["path"])["status"] != "succeeded":
            raise ControllerError("Completed step Bridge result is not successful")
        for name, reference in step["outputs"].items():
            path = Path(reference["path"]).resolve()
            if not (path.is_relative_to(Path(state["attempt_dir"]).resolve())
                    or path.is_relative_to(Path(state["stage_dir"]).resolve())):
                raise ControllerError("Completed output lies outside this attempt")
            verify(reference, "Output " + name)
        return True
