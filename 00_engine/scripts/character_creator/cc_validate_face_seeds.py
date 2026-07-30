"""Validate reusable CC5 face seeds on clean neutral male/female bases."""

import datetime
import hashlib
import json
import math
import os
import traceback

import RLPy
from PySide2 import QtCore, QtWidgets


OUTPUT_ROOT = r"D:\UE\Lance_Work\00_engine\outputs\character_creator_face_seed_validation"
TEMPLATE_ROOT = r"D:\CharacterCreator_sucai\Reallusion Templates"
LIGHTROOM = os.path.join(
    TEMPLATE_ROOT, "Stage", "Light Room", "Default", "Default_CC5.ccLightroom"
)
HEAD_ROOT = os.path.join(TEMPLATE_ROOT, "Avatar Preset", "Head Morph")
BASES = {
    "male": os.path.join(
        TEMPLATE_ROOT, "Actor", "Character", "_Mixer Ready", "Base", "_HD Neutral M.ccAvatar"
    ),
    "female": os.path.join(
        TEMPLATE_ROOT, "Actor", "Character", "_Mixer Ready", "Base", "_HD Neutral F.ccAvatar"
    ),
}
CAMERAS = {
    "male": [
        ("L", os.path.join(TEMPLATE_ROOT, "Stage", "Camera", "Headshot Ref", "Ref Cam Male L.ccCam")),
        ("R", os.path.join(TEMPLATE_ROOT, "Stage", "Camera", "Headshot Ref", "Ref Cam Male R.ccCam")),
    ],
    "female": [
        ("L", os.path.join(TEMPLATE_ROOT, "Stage", "Camera", "Headshot Ref", "Ref Cam Female L.ccCam")),
        ("R", os.path.join(TEMPLATE_ROOT, "Stage", "Camera", "Headshot Ref", "Ref Cam Female R.ccCam")),
    ],
}


def seed(seed_id, sex, *preset_parts):
    return {
        "seed_id": seed_id,
        "sex": sex,
        "base": BASES[sex],
        "preset": os.path.join(HEAD_ROOT, *preset_parts) if preset_parts else None,
        "cameras": CAMERAS[sex],
    }


CONFIG = [
    seed("M00_Neutral", "male"),
    seed("M01_Aaron", "male", "HD Aaron.ccAvatarPreset"),
    seed("M02_Kevin", "male", "CC4 Kevin.ccAvatarPreset"),
    seed("M03_Caleb", "male", "CC3+", "CC3+_Caleb.ccAvatarPreset"),
    seed("M04_Male_A", "male", "CC3+", "Male_A.ccAvatarPreset"),
    seed("M05_Male_B", "male", "CC3+", "Male_B.ccAvatarPreset"),
    seed("M06_Male_C", "male", "CC3+", "Male_C.ccAvatarPreset"),
    seed("M07_Male_D", "male", "CC3+", "Male_D.ccAvatarPreset"),
    seed("M08_Male_E", "male", "CC3+", "Male_E.ccAvatarPreset"),
    seed("M09_Male_F", "male", "CC3+", "Male_F.ccAvatarPreset"),
    seed("F00_Neutral", "female"),
    seed("F01_Ariana", "female", "HD Ariana.ccAvatarPreset"),
    seed("F02_Camila", "female", "CC4 Camila.ccAvatarPreset"),
    seed("F03_Katherine", "female", "CC3+", "CC3+_Katherine.ccAvatarPreset"),
    seed("F04_Female_A", "female", "CC3+", "Female_A.ccAvatarPreset"),
    seed("F05_Female_B", "female", "CC3+", "Female_B.ccAvatarPreset"),
    seed("F06_Female_C", "female", "CC3+", "Female_C.ccAvatarPreset"),
    seed("F07_Female_D", "female", "CC3+", "Female_D.ccAvatarPreset"),
    seed("F08_Female_E", "female", "CC3+", "Female_E.ccAvatarPreset"),
    seed("F09_Female_F", "female", "CC3+", "Female_F.ccAvatarPreset"),
]

RUN_PREFIX = "face_seeds"
WINDOW_TITLE = "CC5 Face Seed Validation"
START_LABEL = "Starting {}-seed face validation."
FINISH_TITLE = "Face Seed Validation Finished"
PROMPT_TITLE = "Validate Face Seeds"
PROMPT_DESCRIPTION = "face seeds"

FACE_TERMS = (
    "head", "face", "eye", "brow", "nose", "mouth", "lip", "jaw",
    "chin", "cheek", "ear", "forehead", "teeth", "tongue",
)
BODY_TERMS = (
    "body", "torso", "chest", "breast", "shoulder", "arm", "elbow",
    "hand", "waist", "abdomen", "belly", "stomach", "hip", "pelvis",
    "butt", "glute", "leg", "thigh", "calf", "foot", "feet", "muscle",
    "fat", "height", "scale", "proportion", "ratio",
)
JUNCTION_TERMS = ("neck", "clavicle", "collar")


class PilotError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temp, path)


def checked(label, status):
    if status is None:
        return {"returned": False, "is_error": False}
    try:
        is_error = bool(status.IsError())
    except Exception:
        is_error = False
    info = {"returned": True, "is_error": is_error}
    try:
        info["status_code"] = str(status.GetStatusCode())
    except Exception:
        pass
    if is_error:
        raise PilotError("{} failed: {}".format(label, info))
    return info


def set_avatar_yaw(avatar, degrees):
    control = avatar.GetControl("Transform")
    if control is None:
        raise PilotError("Avatar has no Transform control")
    data_block = control.GetDataBlock()
    if data_block is None:
        raise PilotError("Avatar Transform control has no data block")
    time = RLPy.RGlobal.GetStartTime()
    checked(
        "Set avatar yaw {}".format(degrees),
        data_block.SetData(
            "Rotation/RotationZ", time, RLPy.RVariant(math.radians(degrees))
        ),
    )
    checked("Refresh avatar yaw", RLPy.RGlobal.SetTime(time))


def classify(display, morph_id, categories):
    text = " ".join([display, morph_id] + categories).lower()
    if any(term in text for term in JUNCTION_TERMS):
        return "junction"
    if any(term in text for term in FACE_TERMS):
        return "face"
    if any(term in text for term in BODY_TERMS):
        return "body"
    return "other"


def fingerprint(entries):
    canonical = json.dumps(
        [(item["id"], round(item["weight"], 8)) for item in entries],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def capture_vectors(avatar):
    component = avatar.GetAvatarShapingComponent()
    if component is None:
        raise PilotError("Avatar has no shaping component")
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
                morph_id, {"id": morph_id, "display": display, "categories": []}
            )
            if category not in entry["categories"]:
                entry["categories"].append(category)

    groups = dict((name, []) for name in ("face", "body", "junction", "other"))
    for morph_id in sorted(catalog):
        source = catalog[morph_id]
        try:
            weight = float(component.GetShapingMorphWeight(morph_id))
        except Exception:
            continue
        if abs(weight) <= 1e-8:
            continue
        group = classify(source["display"], morph_id, source["categories"])
        groups[group].append(
            {
                "id": morph_id,
                "display": source["display"],
                "categories": source["categories"],
                "weight": weight,
            }
        )
    return {
        "catalog_morph_count": len(catalog),
        "groups": dict(
            (
                name,
                {
                    "nonzero_count": len(entries),
                    "fingerprint_sha256": fingerprint(entries),
                    "entries": entries,
                },
            )
            for name, entries in groups.items()
        ),
    }


def apply_target_face(avatar, target_morphs):
    component = avatar.GetAvatarShapingComponent()
    if component is None:
        raise PilotError("Avatar has no shaping component")
    catalog = {}
    for raw_category in component.GetShapingMorphCatergoryNames() or []:
        category = str(raw_category)
        ids = list(component.GetShapingMorphIDs(category) or [])
        names = list(component.GetShapingMorphDisplayNames(category) or [])
        for index, raw_id in enumerate(ids):
            morph_id = str(raw_id)
            display = str(names[index] if index < len(names) else morph_id)
            entry = catalog.setdefault(
                morph_id, {"id": morph_id, "display": display, "categories": []}
            )
            if category not in entry["categories"]:
                entry["categories"].append(category)

    targets = dict((item["id"], float(item["weight"])) for item in target_morphs)
    missing = sorted(set(targets) - set(catalog))
    if missing:
        raise PilotError("Target face morph IDs are unavailable: {}".format(missing))

    face_ids = [
        morph_id
        for morph_id, entry in catalog.items()
        if classify(entry["display"], morph_id, entry["categories"]) == "face"
    ]
    changed = []
    for morph_id in sorted(face_ids):
        target = float(targets.get(morph_id, 0.0))
        bounds = component.GetShapingMorphMinMax(morph_id)
        minimum = float(bounds.first)
        maximum = float(bounds.second)
        reported_out_of_bounds = (
            target < minimum - 1e-7 or target > maximum + 1e-7
        )
        is_signed_embed_morph = morph_id.lower().startswith('cc embed morphs/')
        if reported_out_of_bounds and not is_signed_embed_morph:
            raise PilotError(
                "Target morph is outside its bounds: {} target={} bounds=[{}, {}]".format(
                    morph_id, target, minimum, maximum
                )
            )
        previous = float(component.GetShapingMorphWeight(morph_id))
        if abs(previous - target) <= 1e-7:
            continue
        checked(
            "Set face morph {}".format(catalog[morph_id]["display"]),
            component.SetShapingMorphWeight(morph_id, target),
        )
        changed.append(
            {"id": morph_id, "previous": previous, "target": target}
        )
    if changed:
        checked(
            "Refresh face morph weights",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
    return {"available_face_morph_count": len(face_ids), "changed": changed}


def group_delta(before, after, tolerance=1e-7):
    old = dict((item["id"], item["weight"]) for item in before["entries"])
    new = dict((item["id"], item["weight"]) for item in after["entries"])
    result = []
    for morph_id in sorted(set(old) | set(new)):
        old_value = float(old.get(morph_id, 0.0))
        new_value = float(new.get(morph_id, 0.0))
        if abs(new_value - old_value) > tolerance:
            result.append(
                {
                    "id": morph_id,
                    "before": old_value,
                    "after": new_value,
                    "delta": new_value - old_value,
                }
            )
    return result


def remove_current_avatars():
    errors = []
    for avatar in list(RLPy.RScene.GetAvatars() or []):
        try:
            RLPy.RScene.RemoveObject(avatar)
        except Exception as exc:
            errors.append("{}: {}".format(avatar.GetName(), exc))
    if errors:
        raise PilotError("Unable to clear current avatars: {}".format(errors))


def load_base(path):
    remove_current_avatars()
    attempts = []
    try:
        loaded = RLPy.RFileIO.LoadObject(path, True)
        attempts.append({"api": "LoadObject", "returned_type": type(loaded).__name__})
    except Exception as exc:
        attempts.append({"api": "LoadObject", "exception": str(exc)})
    avatars = list(RLPy.RScene.GetAvatars() or [])
    if not avatars:
        attempts.append({"api": "LoadFile", "status": checked("Load base", RLPy.RFileIO.LoadFile(path))})
        avatars = list(RLPy.RScene.GetAvatars() or [])
    if not avatars:
        raise PilotError("No avatar after base load: {}".format(attempts))
    avatar = avatars[0]
    RLPy.RScene.SelectObject(avatar)
    return avatar, attempts


def run_candidate(candidate, run_dir, log):
    seed_dir = os.path.join(run_dir, candidate["seed_id"])
    os.makedirs(seed_dir, exist_ok=False)
    result_path = os.path.join(seed_dir, "result.json")
    result = {
        "seed_id": candidate["seed_id"],
        "sex": candidate["sex"],
        "parents": candidate.get("parents"),
        "expected_face_change": bool(
            candidate.get(
                "expect_face_change",
                candidate.get("preset") is not None
                or candidate.get("target_face_morphs") is not None,
            )
        ),
        "success": False,
        "body_unchanged": None,
        "junction_unchanged": None,
        "face_changed": None,
        "face_change_count": None,
        "face_fingerprint": None,
        "target_mismatch_count": None,
        "application": None,
        "preview_paths": [],
        "error": None,
    }
    write_json(result, result_path)
    try:
        avatar, attempts = load_base(candidate["base"])
        log("Base loaded: {}".format(attempts))
        before = capture_vectors(avatar)
        write_json(before, os.path.join(seed_dir, "morph_vectors_before.json"))

        if candidate.get("target_face_morphs") is not None:
            result["application"] = apply_target_face(
                avatar, candidate["target_face_morphs"]
            )
            log(
                "Applied exact target face: {} changed weights".format(
                    len(result["application"]["changed"])
                )
            )
        elif candidate["preset"]:
            RLPy.RScene.SelectObject(avatar)
            checked("Apply head preset", RLPy.RFileIO.LoadFile(candidate["preset"]))
            avatars = list(RLPy.RScene.GetAvatars() or [])
            if not avatars:
                raise PilotError("Avatar disappeared after applying head preset")
            avatar = avatars[0]
        after = capture_vectors(avatar)
        write_json(after, os.path.join(seed_dir, "morph_vectors_after.json"))

        deltas = dict(
            (name, group_delta(before["groups"][name], after["groups"][name]))
            for name in ("face", "body", "junction", "other")
        )
        target_morphs = candidate.get("target_face_morphs")
        if target_morphs is not None:
            deltas["target_mismatch"] = group_delta(
                {"entries": target_morphs}, after["groups"]["face"]
            )
            result["target_mismatch_count"] = len(deltas["target_mismatch"])
        write_json(deltas, os.path.join(seed_dir, "morph_delta.json"))
        result["body_unchanged"] = not bool(deltas["body"])
        result["junction_unchanged"] = not bool(deltas["junction"])
        result["face_changed"] = bool(deltas["face"])
        result["face_change_count"] = len(deltas["face"])
        result["face_fingerprint"] = after["groups"]["face"]["fingerprint_sha256"]
        log(
            "Morph delta: face={}, body={}, junction={}, other={}".format(
                len(deltas["face"]), len(deltas["body"]),
                len(deltas["junction"]), len(deltas["other"])
            )
        )
        if not result["body_unchanged"]:
            raise PilotError("Head preset changed body morphs")
        if result["target_mismatch_count"]:
            raise PilotError(
                "Applied face differs from target recipe in {} morphs".format(
                    result["target_mismatch_count"]
                )
            )
        if result["face_changed"] != result["expected_face_change"]:
            raise PilotError(
                "Face-change expectation mismatch: expected={}, actual={}".format(
                    result["expected_face_change"], result["face_changed"]
                )
            )

        checked("Load Lightroom", RLPy.RFileIO.LoadFile(LIGHTROOM))
        checked("Set start time", RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime()))
        for view_id, camera_path in candidate["cameras"]:
            checked("Load camera {}".format(view_id), RLPy.RFileIO.LoadFile(camera_path))
            preview = os.path.join(seed_dir, "preview_{}.png".format(view_id))
            checked("Render preview {}".format(view_id), RLPy.RGlobal.RenderImage(preview))
            if not os.path.isfile(preview) or os.path.getsize(preview) <= 0:
                raise PilotError("Preview missing or empty: {}".format(preview))
            result["preview_paths"].append(preview)

        profile_camera = candidate["cameras"][0][1]
        checked("Reload profile camera", RLPy.RFileIO.LoadFile(profile_camera))
        set_avatar_yaw(avatar, 90.0)
        preview = os.path.join(seed_dir, "preview_front.png")
        checked("Render preview front", RLPy.RGlobal.RenderImage(preview))
        if not os.path.isfile(preview) or os.path.getsize(preview) <= 0:
            raise PilotError("Preview missing or empty: {}".format(preview))
        result["preview_paths"].append(preview)
        set_avatar_yaw(avatar, 0.0)
        result["success"] = True
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        log("FAILED {}: {}".format(candidate["seed_id"], exc))
    write_json(result, result_path)
    return result


class PilotWindow(QtWidgets.QDialog):
    def __init__(self):
        super(PilotWindow, self).__init__()
        self.index = 0
        self.results = []
        self.run_id = datetime.datetime.now().strftime(
            RUN_PREFIX + "_%Y%m%d_%H%M%S_%f"
        )
        self.run_dir = os.path.join(OUTPUT_ROOT, self.run_id)
        os.makedirs(self.run_dir, exist_ok=False)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(900, 560)
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(START_LABEL.format(len(CONFIG)))
        layout.addWidget(self.label)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, len(CONFIG))
        layout.addWidget(self.progress)
        self.log_box = QtWidgets.QPlainTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box, 1)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.setEnabled(False)
        layout.addWidget(self.close_button)
        self.close_button.clicked.connect(self.close)
        QtCore.QTimer.singleShot(0, self.process_next)

    def log(self, message):
        self.log_box.appendPlainText("[{}] {}".format(now(), message))
        QtWidgets.QApplication.processEvents()

    def process_next(self):
        if self.index >= len(CONFIG):
            self.finish()
            return
        candidate = CONFIG[self.index]
        self.label.setText(
            "Processing {}/{}: {}".format(self.index + 1, len(CONFIG), candidate["seed_id"])
        )
        self.log("START {}".format(candidate["seed_id"]))
        self.results.append(run_candidate(candidate, self.run_dir, self.log))
        self.index += 1
        self.progress.setValue(self.index)
        QtCore.QTimer.singleShot(0, self.process_next)

    def finish(self):
        failures = [item for item in self.results if not item["success"]]
        identities = [
            "{}:{}".format(item["sex"], item["face_fingerprint"])
            for item in self.results
            if item.get("face_fingerprint")
        ]
        unique_identity_count = len(set(identities))
        summary = {
            "run_id": self.run_id,
            "output_dir": self.run_dir,
            "success": bool(
                not failures
                and len(self.results) == len(CONFIG)
                and unique_identity_count == len(CONFIG)
            ),
            "processed_count": len(self.results),
            "failure_count": len(failures),
            "unique_identity_count": unique_identity_count,
            "results": self.results,
        }
        summary_path = os.path.join(self.run_dir, "pilot_result.json")
        write_json(summary, summary_path)
        self.label.setText(
            "Finished: success={}, processed={}, failures={}, unique faces={}/{}.".format(
                summary["success"], summary["processed_count"], summary["failure_count"],
                summary["unique_identity_count"], len(CONFIG)
            )
        )
        self.log("RESULT: {}".format(summary_path))
        self.close_button.setEnabled(True)
        QtWidgets.QMessageBox.information(
            self, FINISH_TITLE, self.label.text() + "\n\n" + summary_path
        )

    def closeEvent(self, event):
        if not self.close_button.isEnabled():
            event.ignore()
            return
        event.accept()


_WINDOW = None
_HAS_RUN = False


def main():
    global _WINDOW
    missing = []
    for candidate in CONFIG:
        source_paths = [candidate["base"]] + [item[1] for item in candidate["cameras"]]
        if candidate["preset"]:
            source_paths.append(candidate["preset"])
        for path in source_paths:
            if not os.path.isfile(path):
                missing.append(path)
    if not os.path.isfile(LIGHTROOM):
        missing.append(LIGHTROOM)
    if missing:
        QtWidgets.QMessageBox.critical(None, "Face Seed Pilot Inputs Missing", "\n".join(missing))
        return
    answer = QtWidgets.QMessageBox.question(
        None,
        PROMPT_TITLE,
        (
            "This replaces the current CC scene {} times to validate {}. "
            "It does not save projects or modify source assets. "
            "Save unrelated CC work before continuing.\n\nRun the validation now?"
        ).format(len(CONFIG), PROMPT_DESCRIPTION),
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        QtWidgets.QMessageBox.Cancel,
    )
    if answer != QtWidgets.QMessageBox.Yes:
        return
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    _WINDOW = PilotWindow()
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


if os.environ.get("CC_FACE_VALIDATOR_IMPORT_ONLY") != "1":
    run_script()
