"""CLI client for the local Character Creator file-queue bridge."""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import uuid


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(SCRIPT_DIR, "bridge_config.json")
CLIENT_VERSION = "0.2.0"
JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$")


class ClientError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(data, path):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    temporary = os.path.join(
        directory, ".{}.{}.tmp".format(os.path.basename(path), uuid.uuid4().hex)
    )
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def runtime_paths(config):
    root = os.path.abspath(config["runtime_root"])
    return {
        "root": root,
        "inbox": os.path.join(root, "inbox"),
        "results": os.path.join(root, "results"),
        "heartbeat": os.path.join(root, "state", "heartbeat.json"),
    }


def ensure_runtime(paths):
    for key in ("inbox", "results"):
        os.makedirs(paths[key], exist_ok=True)
    os.makedirs(os.path.dirname(paths["heartbeat"]), exist_ok=True)


def make_job_id():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return "{}_{}".format(stamp, uuid.uuid4().hex[:12])


def parse_time(value):
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def bridge_health(config, paths):
    result = {
        "healthy": False,
        "reason": None,
        "heartbeat_path": paths["heartbeat"],
        "heartbeat": None,
        "age_seconds": None,
    }
    if not os.path.isfile(paths["heartbeat"]):
        result["reason"] = "heartbeat_missing"
        return result
    try:
        heartbeat = read_json(paths["heartbeat"])
        result["heartbeat"] = heartbeat
        if int(heartbeat.get("protocol_version", -1)) != int(
            config["protocol_version"]
        ):
            result["reason"] = "protocol_mismatch"
            return result
        updated = parse_time(heartbeat["updated_at"])
        age = (datetime.datetime.now(datetime.timezone.utc) - updated.astimezone(datetime.timezone.utc)).total_seconds()
        result["age_seconds"] = max(0.0, age)
        if age > float(config["active_lease_seconds"]):
            result["reason"] = "heartbeat_stale"
            return result
        if heartbeat.get("state") not in ("idle", "busy"):
            result["reason"] = "bridge_not_running"
            return result
        result["healthy"] = True
        result["reason"] = "ok"
        return result
    except Exception as exc:
        result["reason"] = "heartbeat_invalid"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        return result


def submit(config, paths, command, payload, job_id=None):
    job_id = job_id or make_job_id()
    if not JOB_ID_PATTERN.match(job_id):
        raise ClientError("Invalid job ID: {}".format(job_id))
    request_path = os.path.join(paths["inbox"], job_id + ".json")
    result_path = os.path.join(paths["results"], job_id + ".json")
    if os.path.exists(request_path) or os.path.exists(result_path):
        raise ClientError("Job ID already exists: {}".format(job_id))
    request = {
        "protocol_version": int(config["protocol_version"]),
        "job_id": job_id,
        "created_at": now(),
        "command": command,
        "payload": payload,
        "client": {"name": "cc_bridge_client", "version": CLIENT_VERSION},
    }
    atomic_write_json(request, request_path)
    return {
        "submitted": True,
        "job_id": job_id,
        "request_path": request_path,
        "result_path": result_path,
    }


def wait_for_result(paths, job_id, timeout_seconds):
    result_path = os.path.join(paths["results"], job_id + ".json")
    deadline = time.monotonic() + float(timeout_seconds)
    while True:
        if os.path.isfile(result_path):
            try:
                return read_json(result_path)
            except (PermissionError, json.JSONDecodeError, OSError):
                # The CC process writes result files directly. Existence can
                # become visible briefly before its handle is released.
                pass
        if time.monotonic() >= deadline:
            raise ClientError(
                "Timed out after {} seconds waiting for {}".format(
                    timeout_seconds, job_id
                )
            )
        time.sleep(0.25)


def build_dialog_guard_command(
    guard_path,
    target_process_id,
    result_path,
    log_path,
    progress_root,
    timeout_seconds,
):
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        guard_path,
        "-TargetProcessId",
        str(int(target_process_id)),
        "-ResultPath",
        result_path,
        "-LogPath",
        log_path,
        "-TimeoutSeconds",
        str(max(1, int(float(timeout_seconds)))),
    ]
    if progress_root:
        command.extend(["-ProgressRoot", progress_root])
    return command


def launch_dialog_guard(config, paths, submission, progress_root, timeout_seconds):
    guard_path = os.path.abspath(
        config.get(
            "undo_dialog_guard_path",
            os.path.join(SCRIPT_DIR, "cc_undo_dialog_guard.ps1"),
        )
    )
    if not os.path.isfile(guard_path):
        raise ClientError("Undo dialog guard is missing: {}".format(guard_path))
    health = bridge_health(config, paths)
    if not health["healthy"]:
        raise ClientError(
            "Bridge must be healthy before starting dialog guard: {}".format(
                health["reason"]
            )
        )
    target_process_id = health["heartbeat"].get("pid")
    if not isinstance(target_process_id, int) or target_process_id <= 0:
        raise ClientError("Bridge heartbeat has no valid CC process ID")
    log_path = os.path.join(
        paths["root"],
        "dialog_guard",
        submission["job_id"] + ".jsonl",
    )
    command = build_dialog_guard_command(
        guard_path,
        target_process_id,
        submission["result_path"],
        log_path,
        progress_root,
        timeout_seconds,
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creation_flags,
    )
    return {
        "enabled": True,
        "process_id": process.pid,
        "target_process_id": target_process_id,
        "log_path": log_path,
        "guard_path": guard_path,
    }


def print_json(data):
    print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True))


def add_submit_options(parser, default_timeout):
    parser.add_argument("--job-id")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--timeout", type=float, default=default_timeout)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("health", help="Read and validate the bridge heartbeat")

    ping = subparsers.add_parser("ping", help="Submit a bridge liveness job")
    add_submit_options(ping, 30.0)

    scene = subparsers.add_parser(
        "scene-summary", help="Read avatar information through RLPy"
    )
    add_submit_options(scene, 60.0)

    apply_face = subparsers.add_parser(
        "apply-face", help="Apply and preview one generated face recipe"
    )
    apply_face.add_argument("--recipe-file", required=True)
    apply_face.add_argument("--recipe-id", required=True)
    apply_face.add_argument("--output-dir", required=True)
    apply_face.add_argument("--confirm-scene-replace", action="store_true")
    add_submit_options(apply_face, 900.0)

    validate_bodies = subparsers.add_parser(
        "validate-bodies", help="Rebuild and validate canonical BodyFit presets"
    )
    validate_bodies.add_argument("--library-file", required=True)
    validate_bodies.add_argument("--output-dir", required=True)
    validate_bodies.add_argument("--preset-id", action="append", dest="preset_ids")
    validate_bodies.add_argument("--confirm-scene-replace", action="store_true")
    validate_bodies.add_argument(
        "--auto-dismiss-undo-warning",
        action="store_true",
        help="Dismiss only the exact known CC Undo Manager warning",
    )
    add_submit_options(validate_bodies, 1800.0)

    wait = subparsers.add_parser("wait", help="Wait for an existing job result")
    wait.add_argument("job_id")
    wait.add_argument("--timeout", type=float, default=900.0)

    result = subparsers.add_parser("result", help="Read an existing job result")
    result.add_argument("job_id")
    return parser


def run_submit_action(config, paths, args):
    if args.action == "ping":
        command = "ping"
        payload = {}
    elif args.action == "scene-summary":
        command = "scene_summary"
        payload = {}
    elif args.action == "apply-face":
        if not args.confirm_scene_replace:
            raise ClientError("--confirm-scene-replace is required")
        command = "apply_face_recipe_preview"
        payload = {
            "recipe_file": os.path.abspath(args.recipe_file),
            "recipe_id": args.recipe_id,
            "output_dir": os.path.abspath(args.output_dir),
            "confirm_scene_replace": True,
        }
    elif args.action == "validate-bodies":
        if not args.confirm_scene_replace:
            raise ClientError("--confirm-scene-replace is required")
        command = "validate_bodyfit_library"
        payload = {
            "library_file": os.path.abspath(args.library_file),
            "output_dir": os.path.abspath(args.output_dir),
            "confirm_scene_replace": True,
        }
        if args.preset_ids:
            payload["preset_ids"] = args.preset_ids
    else:
        raise ClientError("Unsupported submit action: {}".format(args.action))

    submission = submit(config, paths, command, payload, args.job_id)
    dialog_guard = None
    if getattr(args, "auto_dismiss_undo_warning", False):
        dialog_guard = launch_dialog_guard(
            config,
            paths,
            submission,
            payload.get("output_dir"),
            args.timeout,
        )
        submission["dialog_guard"] = dialog_guard
    if args.no_wait:
        print_json(submission)
        return 0
    result = wait_for_result(paths, submission["job_id"], args.timeout)
    if dialog_guard:
        result["client_dialog_guard"] = dialog_guard
    print_json(result)
    return 0 if result.get("status") == "succeeded" else 3


def main():
    parser = build_parser()
    args = parser.parse_args()
    config = read_json(os.path.abspath(args.config))
    paths = runtime_paths(config)
    ensure_runtime(paths)
    try:
        if args.action == "health":
            health = bridge_health(config, paths)
            print_json(health)
            return 0 if health["healthy"] else 2
        if args.action == "wait":
            result = wait_for_result(paths, args.job_id, args.timeout)
            print_json(result)
            return 0 if result.get("status") == "succeeded" else 3
        if args.action == "result":
            result_path = os.path.join(paths["results"], args.job_id + ".json")
            if not os.path.isfile(result_path):
                raise ClientError("Result does not exist: {}".format(result_path))
            result = read_json(result_path)
            print_json(result)
            return 0 if result.get("status") == "succeeded" else 3
        return run_submit_action(config, paths, args)
    except ClientError as exc:
        print_json(
            {
                "success": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
