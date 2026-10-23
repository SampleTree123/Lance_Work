"""Character Creator 5 local file-queue bridge plugin."""

rl_plugin_info = {"ap": "Character Creator", "ap_version": "Any"}

import datetime
import importlib.util
import json
import os
import re
import shutil
import traceback
import uuid

import RLPy
from PySide2 import QtCore, QtWidgets


CONFIG_PATH = r"D:\UE\Lance_Work\00_engine\character_creator_bridge\bridge_config.json"
JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$")
ALLOWED_COMMANDS = {
    "ping",
    "scene_summary",
    "apply_face_recipe_preview",
    "validate_bodyfit_library",
}
SOURCE_PROJECT_ONLY_BODYFIT_MODES = frozenset(
    (
        "outfit_compatibility_gate",
        "outfit_motion_stress_gate",
    )
)


class BridgeError(RuntimeError):
    pass


class JobRejected(BridgeError):
    pass


def bodyfit_preset_input_paths(document, preset):
    """Return the preset files required by the selected execution mode."""
    if document.get("diagnostic_mode") in SOURCE_PROJECT_ONLY_BODYFIT_MODES:
        source_project = (preset.get("source_project") or {}).get("path")
        if not isinstance(source_project, str) or not source_project:
            raise ValueError("source_project.path is required")
        return (source_project,)

    try:
        base_path = preset["base_avatar"]["path"]
        source_path = preset["source_project"]["path"]
    except Exception as exc:
        raise ValueError("base_avatar.path and source_project.path are required") from exc
    if (
        not isinstance(base_path, str)
        or not base_path
        or not isinstance(source_path, str)
        or not source_path
    ):
        raise ValueError("base_avatar.path and source_project.path are required")
    return (base_path, source_path)


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def parse_time(value):
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


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


def pid_is_alive(pid):
    try:
        return int(pid) > 0
    except (TypeError, ValueError):
        return False


def normalized_path(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def path_is_within(path, roots):
    candidate = normalized_path(path)
    for root in roots:
        normalized_root = normalized_path(root)
        try:
            if os.path.commonpath([candidate, normalized_root]) == normalized_root:
                return True
        except ValueError:
            continue
    return False


def safe_archive(source, directory, suffix=None):
    os.makedirs(directory, exist_ok=True)
    basename = os.path.basename(source)
    if suffix:
        stem, extension = os.path.splitext(basename)
        basename = "{}.{}{}".format(stem, suffix, extension)
    destination = os.path.join(directory, basename)
    if os.path.exists(destination):
        stem, extension = os.path.splitext(basename)
        destination = os.path.join(
            directory, "{}.{}{}".format(stem, uuid.uuid4().hex[:8], extension)
        )
    os.replace(source, destination)
    return destination


class BridgeService(QtCore.QObject):
    def __init__(self):
        super(BridgeService, self).__init__()
        self.config = read_json(CONFIG_PATH)
        self._validate_config()
        self.paths = self._runtime_paths()
        self.instance_id = uuid.uuid4().hex
        self.started_at = now()
        self.state = "stopped"
        self.busy = False
        self.active_job_id = None
        self.last_error = None
        self.last_heartbeat_monotonic = None
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(int(self.config["poll_interval_ms"]))
        self.timer.timeout.connect(self._tick)
        self._ensure_runtime()

    def _validate_config(self):
        if int(self.config.get("protocol_version", -1)) != 1:
            raise BridgeError("Only bridge protocol version 1 is supported")
        if int(self.config.get("poll_interval_ms", 0)) < 100:
            raise BridgeError("poll_interval_ms must be at least 100")
        if int(self.config.get("heartbeat_interval_ms", 0)) < 250:
            raise BridgeError("heartbeat_interval_ms must be at least 250")
        if not self.config.get("allowed_input_roots"):
            raise BridgeError("allowed_input_roots must not be empty")

    def _runtime_paths(self):
        root = os.path.abspath(self.config["runtime_root"])
        return {
            "root": root,
            "inbox": os.path.join(root, "inbox"),
            "processing": os.path.join(root, "processing"),
            "completed": os.path.join(root, "completed_requests"),
            "failed": os.path.join(root, "failed_requests"),
            "results": os.path.join(root, "results"),
            "state": os.path.join(root, "state"),
            "logs": os.path.join(root, "logs"),
            "heartbeat": os.path.join(root, "state", "heartbeat.json"),
            "log": os.path.join(root, "logs", "bridge.jsonl"),
        }

    def _ensure_runtime(self):
        for key in (
            "inbox",
            "processing",
            "completed",
            "failed",
            "results",
            "state",
            "logs",
        ):
            os.makedirs(self.paths[key], exist_ok=True)
        os.makedirs(self.config["allowed_output_root"], exist_ok=True)

    def _append_log(self, event, detail=None, level="info"):
        record = {
            "at": now(),
            "level": level,
            "event": event,
            "instance_id": self.instance_id,
            "state": self.state,
            "active_job_id": self.active_job_id,
            "detail": detail,
        }
        try:
            with open(self.paths["log"], "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
                handle.flush()
        except Exception:
            pass

    def _queue_depth(self):
        try:
            return len(
                [
                    name
                    for name in os.listdir(self.paths["inbox"])
                    if name.endswith(".json") and not name.startswith(".")
                ]
            )
        except Exception:
            return None

    def _write_heartbeat(self):
        heartbeat = {
            "protocol_version": int(self.config["protocol_version"]),
            "bridge_id": self.config["bridge_id"],
            "plugin_version": self.config["plugin_version"],
            "instance_id": self.instance_id,
            "pid": os.getpid(),
            "state": self.state,
            "busy": self.busy,
            "active_job_id": self.active_job_id,
            "queue_depth": self._queue_depth(),
            "started_at": self.started_at,
            "updated_at": now(),
            "last_error": self.last_error,
        }
        atomic_write_json(heartbeat, self.paths["heartbeat"])
        self.last_heartbeat_monotonic = QtCore.QElapsedTimer()
        self.last_heartbeat_monotonic.start()

    def _fresh_foreign_lease(self):
        if not os.path.isfile(self.paths["heartbeat"]):
            return None
        try:
            heartbeat = read_json(self.paths["heartbeat"])
            if heartbeat.get("state") not in ("idle", "busy"):
                return None
            updated = parse_time(heartbeat["updated_at"])
            age = (
                datetime.datetime.now(datetime.timezone.utc)
                - updated.astimezone(datetime.timezone.utc)
            ).total_seconds()
            if age > float(self.config["active_lease_seconds"]):
                return None
            if not pid_is_alive(heartbeat.get("pid")):
                return None
            if heartbeat.get("instance_id") == self.instance_id:
                return None
            return heartbeat
        except Exception:
            return None

    def _recover_orphans(self):
        for filename in sorted(os.listdir(self.paths["processing"])):
            if not filename.endswith(".json") or filename.startswith("."):
                continue
            source = os.path.join(self.paths["processing"], filename)
            job_id = os.path.splitext(filename)[0]
            command = None
            try:
                request = read_json(source)
                job_id = str(request.get("job_id") or job_id)
                command = request.get("command")
            except Exception:
                request = None
            result_path = os.path.join(self.paths["results"], job_id + ".json")
            if not os.path.exists(result_path):
                atomic_write_json(
                    {
                        "protocol_version": int(self.config["protocol_version"]),
                        "job_id": job_id,
                        "command": command,
                        "status": "failed",
                        "plugin_version": self.config["plugin_version"],
                        "instance_id": self.instance_id,
                        "started_at": None,
                        "finished_at": now(),
                        "result": None,
                        "error": {
                            "type": "InterruptedJob",
                            "message": "Request was left in processing by a previous plugin instance",
                        },
                    },
                    result_path,
                )
            safe_archive(source, self.paths["failed"], "recovered")
            self._append_log("orphan_recovered", {"job_id": job_id}, "warning")

    def start(self):
        if self.timer.isActive():
            return True
        lease = self._fresh_foreign_lease()
        if lease is not None:
            self.state = "conflict"
            self.last_error = {
                "type": "ActiveLeaseConflict",
                "message": "Another live bridge instance owns the runtime queue",
                "lease": lease,
            }
            self._append_log("start_refused", self.last_error, "error")
            return False
        self._recover_orphans()
        self.state = "idle"
        self.last_error = None
        self.timer.start()
        self._write_heartbeat()
        self._append_log("bridge_started")
        return True

    def stop(self):
        self.timer.stop()
        self.state = "stopped"
        self.busy = False
        self.active_job_id = None
        self._write_heartbeat()
        self._append_log("bridge_stopped")

    def status(self):
        return {
            "bridge_id": self.config["bridge_id"],
            "plugin_version": self.config["plugin_version"],
            "instance_id": self.instance_id,
            "state": self.state,
            "busy": self.busy,
            "active_job_id": self.active_job_id,
            "queue_depth": self._queue_depth(),
            "runtime_root": self.paths["root"],
            "last_error": self.last_error,
        }

    def _heartbeat_due(self):
        if self.last_heartbeat_monotonic is None:
            return True
        return self.last_heartbeat_monotonic.elapsed() >= int(
            self.config["heartbeat_interval_ms"]
        )

    @QtCore.Slot()
    def _tick(self):
        try:
            if self.state not in ("idle", "busy"):
                return
            if self._heartbeat_due():
                self._write_heartbeat()
            if self.busy:
                return
            request_path = self._claim_next_request()
            if request_path:
                self._process_request(request_path)
        except Exception as exc:
            self.last_error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            self._append_log("tick_failed", self.last_error, "error")
            try:
                self._write_heartbeat()
            except Exception:
                pass

    def _claim_next_request(self):
        filenames = sorted(
            name
            for name in os.listdir(self.paths["inbox"])
            if name.endswith(".json") and not name.startswith(".")
        )
        for filename in filenames:
            source = os.path.join(self.paths["inbox"], filename)
            destination = os.path.join(self.paths["processing"], filename)
            try:
                os.replace(source, destination)
                return destination
            except FileNotFoundError:
                continue
            except Exception as exc:
                self._append_log(
                    "claim_failed", {"path": source, "error": str(exc)}, "warning"
                )
        return None

    def _validate_request(self, request, request_path):
        if not isinstance(request, dict):
            raise JobRejected("Request must be a JSON object")
        if int(request.get("protocol_version", -1)) != int(
            self.config["protocol_version"]
        ):
            raise JobRejected("Protocol version mismatch")
        job_id = request.get("job_id")
        if not isinstance(job_id, str) or not JOB_ID_PATTERN.match(job_id):
            raise JobRejected("Invalid job_id")
        filename_id = os.path.splitext(os.path.basename(request_path))[0]
        if filename_id != job_id:
            raise JobRejected("Filename and request job_id differ")
        command = request.get("command")
        if command not in ALLOWED_COMMANDS:
            raise JobRejected("Unsupported command: {}".format(command))
        if not isinstance(request.get("payload"), dict):
            raise JobRejected("payload must be a JSON object")
        if not isinstance(request.get("created_at"), str):
            raise JobRejected("created_at is required")
        parse_time(request["created_at"])
        return job_id, command

    def _terminal_result(self, job_id, command, status, started_at, result, error):
        return {
            "protocol_version": int(self.config["protocol_version"]),
            "job_id": job_id,
            "command": command,
            "status": status,
            "plugin_version": self.config["plugin_version"],
            "instance_id": self.instance_id,
            "started_at": started_at,
            "finished_at": now(),
            "result": result,
            "error": error,
        }

    def _process_request(self, request_path):
        filename_id = os.path.splitext(os.path.basename(request_path))[0]
        existing_result_path = os.path.join(
            self.paths['results'], filename_id + '.json'
        )
        if os.path.exists(existing_result_path):
            safe_archive(request_path, self.paths['completed'], 'duplicate')
            self._append_log(
                'duplicate_skipped', {'job_id': filename_id}, 'warning'
            )
            return
        self.busy = True
        self.state = "busy"
        self.active_job_id = filename_id
        started_at = now()
        self._write_heartbeat()
        request = None
        command = None
        job_id = filename_id
        terminal = None
        archive_dir = self.paths["failed"]
        try:
            if os.path.getsize(request_path) > int(self.config["max_request_bytes"]):
                raise JobRejected("Request exceeds max_request_bytes")
            try:
                request = read_json(request_path)
            except Exception as exc:
                raise JobRejected("Malformed request JSON: {}".format(exc))
            job_id, command = self._validate_request(request, request_path)
            self.active_job_id = job_id
            result_path = os.path.join(self.paths["results"], job_id + ".json")
            if os.path.exists(result_path):
                safe_archive(request_path, self.paths["completed"], "duplicate")
                self._append_log("duplicate_skipped", {"job_id": job_id}, "warning")
                return
            self._append_log("job_started", {"job_id": job_id, "command": command})
            result = self._dispatch(command, request["payload"], job_id)
            terminal = self._terminal_result(
                job_id, command, "succeeded", started_at, result, None
            )
            archive_dir = self.paths["completed"]
        except JobRejected as exc:
            terminal = self._terminal_result(
                job_id,
                command,
                "rejected",
                started_at,
                None,
                {"type": type(exc).__name__, "message": str(exc)},
            )
        except Exception as exc:
            terminal = self._terminal_result(
                job_id,
                command,
                "failed",
                started_at,
                None,
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
        finally:
            if terminal is not None:
                result_path = os.path.join(self.paths["results"], job_id + ".json")
                atomic_write_json(terminal, result_path)
                if os.path.exists(request_path):
                    safe_archive(request_path, archive_dir)
                self._append_log(
                    "job_finished",
                    {"job_id": job_id, "status": terminal["status"]},
                    "info" if terminal["status"] == "succeeded" else "error",
                )
            self.busy = False
            self.active_job_id = None
            self.state = "idle"
            self._write_heartbeat()

    def _dispatch(self, command, payload, job_id):
        if command == "ping":
            if payload:
                raise JobRejected("ping payload must be empty")
            return {
                "pong": True,
                "bridge_id": self.config["bridge_id"],
                "plugin_version": self.config["plugin_version"],
                "instance_id": self.instance_id,
                "pid": os.getpid(),
                "at": now(),
            }
        if command == "scene_summary":
            if payload:
                raise JobRejected("scene_summary payload must be empty")
            avatars = list(RLPy.RScene.GetAvatars() or [])
            return {
                "avatar_count": len(avatars),
                "avatars": [
                    {"name": str(item.GetName()), "id": str(item.GetID())}
                    for item in avatars
                ],
            }
        if command == "apply_face_recipe_preview":
            return self._apply_face_recipe(payload, job_id)
        if command == "validate_bodyfit_library":
            return self._validate_bodyfit_library(payload, job_id)
        raise JobRejected("Unsupported command: {}".format(command))

    def _checked_input_path(self, path, require_file=True):
        if not isinstance(path, str) or not path:
            raise JobRejected("Input path must be a non-empty string")
        resolved = os.path.realpath(os.path.abspath(path))
        if not path_is_within(resolved, self.config["allowed_input_roots"]):
            raise JobRejected("Input path is outside allowed roots: {}".format(path))
        if require_file and not os.path.isfile(resolved):
            raise JobRejected("Input file does not exist: {}".format(path))
        return resolved

    def _checked_output_path(self, path):
        if not isinstance(path, str) or not path:
            raise JobRejected("Output path must be a non-empty string")
        resolved = os.path.realpath(os.path.abspath(path))
        if not path_is_within(resolved, [self.config["allowed_output_root"]]):
            raise JobRejected("Output path is outside allowed_output_root")
        return resolved

    def _load_face_validator(self):
        validator_path = self._checked_input_path(self.config["face_validator_path"])
        previous = os.environ.get("CC_FACE_VALIDATOR_IMPORT_ONLY")
        os.environ["CC_FACE_VALIDATOR_IMPORT_ONLY"] = "1"
        try:
            module_name = "cc_face_validator_bridge_{}".format(uuid.uuid4().hex)
            specification = importlib.util.spec_from_file_location(
                module_name, validator_path
            )
            if specification is None or specification.loader is None:
                raise BridgeError("Unable to load face validator module")
            module = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)
            return module
        finally:
            if previous is None:
                os.environ.pop("CC_FACE_VALIDATOR_IMPORT_ONLY", None)
            else:
                os.environ["CC_FACE_VALIDATOR_IMPORT_ONLY"] = previous

    def _load_body_reconstructor(self):
        module_path = self._checked_input_path(
            self.config["body_reconstructor_path"]
        )
        previous = os.environ.get("CC_BODY_RECONSTRUCTOR_IMPORT_ONLY")
        os.environ["CC_BODY_RECONSTRUCTOR_IMPORT_ONLY"] = "1"
        try:
            module_name = "cc_body_reconstructor_bridge_{}".format(uuid.uuid4().hex)
            specification = importlib.util.spec_from_file_location(
                module_name, module_path
            )
            if specification is None or specification.loader is None:
                raise BridgeError("Unable to load body reconstructor module")
            module = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)
            return module
        finally:
            if previous is None:
                os.environ.pop("CC_BODY_RECONSTRUCTOR_IMPORT_ONLY", None)
            else:
                os.environ["CC_BODY_RECONSTRUCTOR_IMPORT_ONLY"] = previous

    def _apply_face_recipe(self, payload, job_id):
        required = {
            "recipe_file",
            "recipe_id",
            "output_dir",
            "confirm_scene_replace",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise JobRejected("Missing payload fields: {}".format(missing))
        if payload["confirm_scene_replace"] is not True:
            raise JobRejected("confirm_scene_replace must be true")
        recipe_file = self._checked_input_path(payload["recipe_file"])
        output_dir = self._checked_output_path(payload["output_dir"])
        recipe_id = payload["recipe_id"]
        if not isinstance(recipe_id, str) or not recipe_id:
            raise JobRejected("recipe_id must be a non-empty string")
        if os.path.isdir(output_dir) and os.listdir(output_dir):
            raise JobRejected("output_dir already exists and is not empty")

        document = read_json(recipe_file)
        recipes = document.get("recipes")
        if not isinstance(recipes, list):
            raise JobRejected("recipe_file has no recipes list")
        matches = [item for item in recipes if item.get("recipe_id") == recipe_id]
        if len(matches) != 1:
            raise JobRejected(
                "Expected exactly one recipe {}, found {}".format(
                    recipe_id, len(matches)
                )
            )
        recipe = matches[0]
        sex = recipe.get("sex")
        if sex not in ("male", "female"):
            raise JobRejected("Recipe sex must be male or female")
        target = recipe.get("target_face_morphs")
        if not isinstance(target, list) or not target:
            raise JobRejected("Recipe target_face_morphs must not be empty")

        validator = self._load_face_validator()
        candidate = {
            "seed_id": recipe_id,
            "sex": sex,
            "base": validator.BASES[sex],
            "preset": None,
            "cameras": validator.CAMERAS[sex],
            "target_face_morphs": target,
            "expect_face_change": True,
            "parents": recipe.get("parents"),
        }
        os.makedirs(output_dir, exist_ok=True)

        def command_log(message):
            self._append_log(
                "command_progress", {"job_id": job_id, "message": message}
            )
            QtWidgets.QApplication.processEvents()

        validation = validator.run_candidate(
            candidate, output_dir, command_log
        )
        if not validation.get("success"):
            error = validation.get("error") or {}
            raise BridgeError(
                "Face recipe validation failed: {}".format(
                    error.get("message") or "unknown error"
                )
            )
        if validation.get("target_mismatch_count") != 0:
            raise BridgeError("Face recipe target weights did not round-trip exactly")
        return {
            "recipe_file": recipe_file,
            "recipe_id": recipe_id,
            "output_dir": output_dir,
            "validation": validation,
        }

    def _validate_bodyfit_library(self, payload, job_id):
        required = {"library_file", "output_dir", "confirm_scene_replace"}
        missing = sorted(required - set(payload))
        if missing:
            raise JobRejected("Missing payload fields: {}".format(missing))
        if payload["confirm_scene_replace"] is not True:
            raise JobRejected("confirm_scene_replace must be true")
        library_file = self._checked_input_path(payload["library_file"])
        output_dir = self._checked_output_path(payload["output_dir"])
        if os.path.isdir(output_dir) and os.listdir(output_dir):
            raise JobRejected("output_dir already exists and is not empty")
        preset_ids = payload.get("preset_ids")
        if preset_ids is not None and (
            not isinstance(preset_ids, list)
            or not preset_ids
            or any(not isinstance(item, str) or not item for item in preset_ids)
        ):
            raise JobRejected("preset_ids must be a non-empty string list")

        document = read_json(library_file)
        presets = document.get("presets")
        if not isinstance(presets, list) or not presets:
            raise JobRejected("BodyFit library has no presets list")
        by_id = dict((item.get("preset_id"), item) for item in presets)
        selected_ids = preset_ids or [item.get("preset_id") for item in presets]
        unknown = sorted(set(selected_ids) - set(by_id))
        if unknown:
            raise JobRejected("Unknown BodyFit preset IDs: {}".format(unknown))
        for preset_id in selected_ids:
            preset = by_id[preset_id]
            try:
                input_paths = bodyfit_preset_input_paths(document, preset)
            except ValueError:
                raise JobRejected(
                    "BodyFit preset {} has invalid source paths".format(preset_id)
                )
            for input_path in input_paths:
                self._checked_input_path(input_path)
        if document.get("preview_lightroom"):
            self._checked_input_path(document["preview_lightroom"])

        reconstructor = self._load_body_reconstructor()

        def command_log(message):
            self._append_log(
                "command_progress", {"job_id": job_id, "message": message}
            )
            QtWidgets.QApplication.processEvents()

        validation = reconstructor.run_library(
            library_file, output_dir, command_log, preset_ids
        )
        if not validation.get("success"):
            raise BridgeError(
                "BodyFit reconstruction failed; inspect {}".format(
                    validation.get("summary_path") or output_dir
                )
            )
        return {
            "library_file": library_file,
            "output_dir": output_dir,
            "preset_ids": selected_ids,
            "validation": validation,
        }


_SERVICE = None
_MENU = None
_ACTIONS = []


def show_status():
    if _SERVICE is None:
        message = "Bridge service is not initialized."
    else:
        message = json.dumps(_SERVICE.status(), indent=2, sort_keys=True)
    RLPy.RUi.ShowMessageBox(
        "Lance CC Bridge Status", message, RLPy.EMsgButton_Ok
    )


def start_bridge():
    if _SERVICE is not None:
        started = _SERVICE.start()
        if not started:
            show_status()


def stop_bridge():
    if _SERVICE is not None:
        _SERVICE.stop()


def install_menu():
    global _MENU, _ACTIONS
    main_window = wrapInstance(
        int(RLPy.RUi.GetMainWindow()), QtWidgets.QMainWindow
    )
    menu = main_window.menuBar().findChild(QtWidgets.QMenu, "lance_cc_bridge_menu")
    if menu is None:
        menu = wrapInstance(
            int(RLPy.RUi.AddMenu("Lance CC Bridge", RLPy.EMenu_Plugins)),
            QtWidgets.QMenu,
        )
        menu.setObjectName("lance_cc_bridge_menu")
    for action in list(menu.actions()):
        menu.removeAction(action)
    status_action = menu.addAction("Status")
    start_action = menu.addAction("Start")
    stop_action = menu.addAction("Stop")
    status_action.triggered.connect(show_status)
    start_action.triggered.connect(start_bridge)
    stop_action.triggered.connect(stop_bridge)
    _MENU = menu
    _ACTIONS = [status_action, start_action, stop_action]


def initialize_plugin():
    global _SERVICE
    if _SERVICE is None:
        try:
            _SERVICE = BridgeService()
            _SERVICE.start()
        except Exception as exc:
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            try:
                runtime_root = read_json(CONFIG_PATH)["runtime_root"]
                os.makedirs(os.path.join(runtime_root, "state"), exist_ok=True)
                atomic_write_json(
                    {
                        "protocol_version": 1,
                        "bridge_id": "lance_cc_bridge",
                        "plugin_version": "0.2.0",
                        "instance_id": None,
                        "pid": os.getpid(),
                        "state": "failed",
                        "busy": False,
                        "active_job_id": None,
                        "started_at": now(),
                        "updated_at": now(),
                        "last_error": error,
                    },
                    os.path.join(runtime_root, "state", "heartbeat.json"),
                )
            except Exception:
                pass


def run_script():
    initialize_plugin()


run_script()


if __name__ == "__main__":
    run_script()
