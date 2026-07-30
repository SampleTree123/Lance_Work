"""Inspect eight saved CC5 body-preset projects without modifying them."""

import datetime
import hashlib
import json
import os
import traceback

import RLPy
from PySide2 import QtCore, QtWidgets


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "cc_validate_body_presets_config.json")
OUTPUT_ROOT = (
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_body_preset_validation"
)

FACE_TERMS = (
    "head",
    "face",
    "eye",
    "brow",
    "nose",
    "mouth",
    "lip",
    "jaw",
    "chin",
    "cheek",
    "ear",
    "forehead",
    "teeth",
    "tongue",
    "expression",
    "viseme",
)
BODY_TERMS = (
    "body",
    "torso",
    "chest",
    "breast",
    "shoulder",
    "arm",
    "elbow",
    "hand",
    "waist",
    "abdomen",
    "belly",
    "stomach",
    "hip",
    "pelvis",
    "butt",
    "glute",
    "leg",
    "thigh",
    "calf",
    "foot",
    "feet",
    "muscle",
    "fat",
    "height",
    "scale",
    "proportion",
    "ratio",
)
JUNCTION_TERMS = ("neck", "clavicle", "collar")


class ValidationError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def status_info(status):
    result = {"returned": status is not None, "is_error": False}
    if status is None:
        return result
    try:
        result["is_error"] = bool(status.IsError())
    except Exception as exc:
        result["is_error_read_error"] = str(exc)
    try:
        result["status_code"] = str(status.GetStatusCode())
    except Exception as exc:
        result["status_code_read_error"] = str(exc)
    return result


def checked(label, status):
    info = status_info(status)
    if info["is_error"]:
        raise ValidationError("{} failed: {}".format(label, info))
    return info


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def resolve_avatar():
    avatars = list(RLPy.RScene.GetAvatars() or [])
    return (avatars[0] if avatars else None), avatars


def classify_morph(display, morph_id, categories):
    text = " ".join([display, morph_id] + categories).lower()
    if any(term in text for term in JUNCTION_TERMS):
        return "junction"
    if any(term in text for term in FACE_TERMS):
        return "face"
    if any(term in text for term in BODY_TERMS):
        return "body"
    return "other"


def vector_fingerprint(entries):
    canonical = json.dumps(
        [(item["id"], round(item["weight"], 8)) for item in entries],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def capture_morph_vectors(avatar):
    component = avatar.GetAvatarShapingComponent()
    if component is None:
        raise ValidationError("Avatar has no shaping component")

    catalog = {}
    category_names = [
        str(item) for item in (component.GetShapingMorphCatergoryNames() or [])
    ]
    for category in category_names:
        ids = list(component.GetShapingMorphIDs(category) or [])
        names = list(component.GetShapingMorphDisplayNames(category) or [])
        for index, raw_id in enumerate(ids):
            morph_id = str(raw_id)
            display = str(names[index] if index < len(names) else morph_id)
            entry = catalog.setdefault(
                morph_id,
                {"id": morph_id, "display": display, "categories": []},
            )
            if category not in entry["categories"]:
                entry["categories"].append(category)

    entries = []
    for morph_id in sorted(catalog):
        source = catalog[morph_id]
        try:
            weight = float(component.GetShapingMorphWeight(morph_id))
        except Exception:
            continue
        if abs(weight) <= 1e-8:
            continue
        minimum = None
        maximum = None
        try:
            bounds = component.GetShapingMorphMinMax(morph_id)
            minimum = float(bounds.first)
            maximum = float(bounds.second)
        except Exception:
            pass
        classification = classify_morph(
            source["display"], morph_id, source["categories"]
        )
        entries.append(
            {
                "id": morph_id,
                "display": source["display"],
                "categories": source["categories"],
                "classification": classification,
                "weight": weight,
                "minimum": minimum,
                "maximum": maximum,
            }
        )

    groups = {}
    for name in ("body", "junction", "face", "other"):
        selected = [item for item in entries if item["classification"] == name]
        groups[name] = {
            "nonzero_count": len(selected),
            "fingerprint_sha256": vector_fingerprint(selected),
            "entries": selected,
        }
    body_and_junction = [
        item for item in entries if item["classification"] in ("body", "junction")
    ]
    return {
        "catalog_morph_count": len(catalog),
        "category_count": len(category_names),
        "categories": category_names,
        "all_nonzero_count": len(entries),
        "all_fingerprint_sha256": vector_fingerprint(entries),
        "body_and_junction_nonzero_count": len(body_and_junction),
        "body_and_junction_fingerprint_sha256": vector_fingerprint(
            body_and_junction
        ),
        "groups": groups,
    }


def inspect_preset(config, preset, run_dir, log):
    preset_id = preset["preset_id"]
    preset_dir = os.path.join(run_dir, "presets", preset_id)
    os.makedirs(preset_dir, exist_ok=False)
    vector_path = os.path.join(preset_dir, "morph_vectors.json")
    preview_path = os.path.join(preset_dir, "preview.png")
    result_path = os.path.join(preset_dir, "result.json")
    source = preset["project"]
    source_stat = os.stat(source)
    result = {
        "schema_version": 1,
        "preset_id": preset_id,
        "sex": preset["sex"],
        "body_class": preset["body_class"],
        "source_project": source,
        "source_bytes": source_stat.st_size,
        "source_modified_at": datetime.datetime.fromtimestamp(
            source_stat.st_mtime
        ).astimezone().replace(microsecond=0).isoformat(),
        "source_sha256": None,
        "started_at": now(),
        "finished_at": None,
        "success": False,
        "avatar_count": None,
        "avatar_name": None,
        "all_vector_fingerprint": None,
        "body_vector_fingerprint": None,
        "body_nonzero_count": None,
        "artifacts": {"vectors": vector_path, "preview": preview_path},
        "steps": [],
        "error": None,
    }

    def mark(name, detail=None):
        result["steps"].append({"name": name, "at": now(), "detail": detail})
        write_json(result, result_path)
        log("{}: {}".format(name, detail))

    write_json(result, result_path)
    try:
        result["source_sha256"] = sha256_file(source)
        mark("source_hashed", result["source_sha256"])
        mark("project_loaded", checked("Load project", RLPy.RFileIO.LoadFile(source)))
        avatar, avatars = resolve_avatar()
        result["avatar_count"] = len(avatars)
        if avatar is None:
            raise ValidationError("No avatar exists after loading project")
        result["avatar_name"] = str(avatar.GetName())
        RLPy.RScene.SelectObject(avatar)
        mark(
            "avatar_resolved",
            {"name": result["avatar_name"], "avatar_count": len(avatars)},
        )

        vectors = capture_morph_vectors(avatar)
        write_json(vectors, vector_path)
        result["all_vector_fingerprint"] = vectors["all_fingerprint_sha256"]
        result["body_vector_fingerprint"] = vectors[
            "body_and_junction_fingerprint_sha256"
        ]
        result["body_nonzero_count"] = vectors[
            "body_and_junction_nonzero_count"
        ]
        mark(
            "morph_vectors_captured",
            {
                "catalog_morph_count": vectors["catalog_morph_count"],
                "all_nonzero_count": vectors["all_nonzero_count"],
                "body_and_junction_nonzero_count": vectors[
                    "body_and_junction_nonzero_count"
                ],
                "body_fingerprint": result["body_vector_fingerprint"],
            },
        )

        if config.get("preview_lightroom"):
            mark(
                "preview_lightroom_loaded",
                checked(
                    "Load preview Lightroom",
                    RLPy.RFileIO.LoadFile(config["preview_lightroom"]),
                ),
            )
        mark(
            "start_time_selected",
            checked("Set start time", RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime())),
        )
        if config.get("render_preview", True):
            mark(
                "preview_rendered",
                checked("Render preview", RLPy.RGlobal.RenderImage(preview_path)),
            )
        if not os.path.isfile(vector_path) or os.path.getsize(vector_path) <= 0:
            raise ValidationError("Morph vector output is missing or empty")
        if config.get("render_preview", True) and (
            not os.path.isfile(preview_path) or os.path.getsize(preview_path) <= 0
        ):
            raise ValidationError("Preview output is missing or empty")
        result["success"] = True
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        log("FAILED: {}".format(exc))
    result["finished_at"] = now()
    write_json(result, result_path)
    return result


class ValidationWindow(QtWidgets.QDialog):
    def __init__(self, config):
        super(ValidationWindow, self).__init__()
        self.config = config
        self.index = 0
        self.results = []
        self.cancel_requested = False
        self.run_id = datetime.datetime.now().strftime(
            "{}_run_%Y%m%d_%H%M%S_%f".format(config["validation_id"])
        )
        self.run_dir = os.path.join(OUTPUT_ROOT, self.run_id)
        os.makedirs(self.run_dir, exist_ok=False)
        write_json(config, os.path.join(self.run_dir, "validation_config.json"))
        self.summary_path = os.path.join(self.run_dir, "validation_result.json")
        self.setWindowTitle("CC5 Adult Body Preset Validation")
        self.resize(940, 600)
        self._build_ui()
        self.write_summary(False)
        QtCore.QTimer.singleShot(0, self.process_next)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.summary_label = QtWidgets.QLabel(
            "Inspecting eight saved body presets. Source projects will not be saved."
        )
        layout.addWidget(self.summary_label)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, len(self.config["presets"]))
        layout.addWidget(self.progress)
        self.log_widget = QtWidgets.QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumBlockCount(2500)
        layout.addWidget(self.log_widget, 1)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QtWidgets.QPushButton("Cancel After Current Preset")
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.setEnabled(False)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self.cancel_button.clicked.connect(self.request_cancel)
        self.close_button.clicked.connect(self.close)

    def log(self, message):
        self.log_widget.appendPlainText("[{}] {}".format(now(), message))
        QtWidgets.QApplication.processEvents()

    def write_summary(self, finished):
        body_fingerprints = {
            item["preset_id"]: item.get("body_vector_fingerprint")
            for item in self.results
            if item.get("success") and item.get("body_vector_fingerprint")
        }
        failures = [item for item in self.results if not item.get("success")]
        unique_body = set(body_fingerprints.values())
        requested = len(self.config["presets"])
        completed_all = len(self.results) == requested
        summary = {
            "schema_version": 1,
            "validation_id": self.config["validation_id"],
            "run_id": self.run_id,
            "output_dir": self.run_dir,
            "finished": finished,
            "cancelled": self.cancel_requested,
            "requested_count": requested,
            "processed_count": len(self.results),
            "success_count": len(self.results) - len(failures),
            "failure_count": len(failures),
            "unique_body_vector_count": len(unique_body),
            "body_vector_fingerprints": body_fingerprints,
            "success": bool(
                finished
                and completed_all
                and not failures
                and len(unique_body) == requested
            ),
            "results": [
                {
                    "preset_id": item["preset_id"],
                    "sex": item["sex"],
                    "body_class": item["body_class"],
                    "success": item["success"],
                    "avatar_name": item.get("avatar_name"),
                    "body_nonzero_count": item.get("body_nonzero_count"),
                    "all_vector_fingerprint": item.get("all_vector_fingerprint"),
                    "body_vector_fingerprint": item.get("body_vector_fingerprint"),
                    "artifacts": item["artifacts"],
                    "error": item.get("error"),
                }
                for item in self.results
            ],
        }
        write_json(summary, self.summary_path)
        return summary

    def process_next(self):
        presets = self.config["presets"]
        if self.cancel_requested or self.index >= len(presets):
            self.finish_validation()
            return
        preset = presets[self.index]
        self.summary_label.setText(
            "Inspecting {}/{}: {}".format(
                self.index + 1, len(presets), preset["preset_id"]
            )
        )
        self.log(
            "START {}/{} {}".format(
                self.index + 1, len(presets), preset["preset_id"]
            )
        )
        result = inspect_preset(self.config, preset, self.run_dir, self.log)
        self.results.append(result)
        self.index += 1
        self.progress.setValue(self.index)
        self.log("END {} success={}".format(preset["preset_id"], result["success"]))
        self.write_summary(False)
        QtCore.QTimer.singleShot(0, self.process_next)

    def request_cancel(self):
        self.cancel_requested = True
        self.cancel_button.setEnabled(False)
        self.log("Cancellation requested; no new preset will start.")

    def finish_validation(self):
        summary = self.write_summary(True)
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        self.summary_label.setText(
            "Finished: success={}, inspected={}, failures={}, unique body vectors={}/{}.".format(
                summary["success"],
                summary["processed_count"],
                summary["failure_count"],
                summary["unique_body_vector_count"],
                summary["requested_count"],
            )
        )
        self.log("VALIDATION RESULT: {}".format(self.summary_path))
        QtWidgets.QMessageBox.information(
            self,
            "Body Preset Validation Finished",
            self.summary_label.text() + "\n\n" + self.summary_path,
        )

    def closeEvent(self, event):
        if not self.close_button.isEnabled():
            event.ignore()
            self.log("Use Cancel and wait for the current preset before closing.")
            return
        event.accept()


_WINDOW = None
_HAS_RUN = False


def main():
    global _WINDOW
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    expected_ids = {
        "M01_Lean",
        "M02_Average",
        "M03_Athletic",
        "M04_Heavy",
        "F01_Lean",
        "F02_Average",
        "F03_Athletic",
        "F04_Heavy",
    }
    configured_ids = [item["preset_id"] for item in config["presets"]]
    errors = []
    if len(configured_ids) != len(set(configured_ids)):
        errors.append("Preset IDs are not unique")
    if set(configured_ids) != expected_ids:
        errors.append("Configured preset IDs do not match the expected eight IDs")
    for item in config["presets"]:
        if not os.path.isfile(item["project"]):
            errors.append("Missing project: {}".format(item["project"]))
    lightroom = config.get("preview_lightroom")
    if lightroom and not os.path.isfile(lightroom):
        errors.append("Missing preview Lightroom: {}".format(lightroom))
    if errors:
        QtWidgets.QMessageBox.critical(
            None, "Body Preset Validation Inputs Invalid", "\n".join(errors)
        )
        return
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    message = (
        "This validation will replace the current CC scene eight times. It will "
        "read the eight saved projects and write only JSON reports and PNG previews "
        "under D:\\UE\\Lance_Work. The source projects will not be saved or modified.\n\n"
        "Save any unrelated current work before continuing."
    )
    answer = QtWidgets.QMessageBox.question(
        None,
        "Validate Eight Adult Body Presets",
        message,
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        QtWidgets.QMessageBox.Cancel,
    )
    if answer != QtWidgets.QMessageBox.Yes:
        return
    _WINDOW = ValidationWindow(config)
    _WINDOW.show()
    _WINDOW.raise_()
    _WINDOW.activateWindow()


def run_script():
    global _HAS_RUN
    if _HAS_RUN:
        return
    _HAS_RUN = True
    main()


def initialize_plugin():
    run_script()


run_script()
