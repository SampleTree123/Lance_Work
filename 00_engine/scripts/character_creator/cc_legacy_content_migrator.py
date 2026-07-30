"""Audit legacy CC templates and re-save supported items as Custom content.

Load this file from Character Creator 5 with Script > Load Python.  The tool
never modifies files below Reallusion Templates.  It first validates one shirt,
then unlocks resumable clothing and accessory migration batches.
"""

import datetime
import hashlib
import json
import os
import shutil
import traceback

import RLPy
from PySide2 import QtCore, QtWidgets


TEMPLATE_ROOT = r"D:\CharacterCreator_sucai\Reallusion Templates"
CUSTOM_ROOT = r"D:\CharacterCreator_sucai\Reallusion Custom"
OUTPUT_ROOT = (
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_content_migration"
)
PILOT_SOURCE = os.path.join(
    TEMPLATE_ROOT,
    "Cloth",
    "Shirts",
    "Rolled sleeves shirt_A3.ccCloth",
)

BASE_CANDIDATES = (
    os.path.join(
        TEMPLATE_ROOT,
        "Actor",
        "Character",
        "_Mixer Ready",
        "Base",
        "_HD Neutral M.ccAvatar",
    ),
    os.path.join(
        TEMPLATE_ROOT,
        "Actor",
        "Character",
        "_Mixer Ready",
        "Base",
        "HD Neutral M.ccAvatar",
    ),
)

CATEGORY_ENUMS = {
    "Underwear": "ETemplateRootFolder_Underwear",
    "Shirts": "ETemplateRootFolder_Shirts",
    "Pants": "ETemplateRootFolder_Pants",
    "Skirts": "ETemplateRootFolder_Skirts",
    "Coats": "ETemplateRootFolder_Coats",
    "Full-body": "ETemplateRootFolder_FullBody",
    "Others": "ETemplateRootFolder_ClothOthers",
    "Gloves": "ETemplateRootFolder_Gloves",
    "Shoes": "ETemplateRootFolder_Shoes",
    "Head": "ETemplateRootFolder_Head",
    "Torso": "ETemplateRootFolder_Torso",
    "Arm": "ETemplateRootFolder_Arm",
    "Leg": "ETemplateRootFolder_Leg",
    "Accessory Others": "ETemplateRootFolder_AccessoryOthers",
}

CUSTOM_FALLBACKS = {
    "Underwear": os.path.join("Cloth", "Underwear"),
    "Shirts": os.path.join("Cloth", "Shirts"),
    "Pants": os.path.join("Cloth", "Pants"),
    "Skirts": os.path.join("Cloth", "Skirts"),
    "Coats": os.path.join("Cloth", "Coats"),
    "Full-body": os.path.join("Cloth", "Full-body"),
    "Others": os.path.join("Cloth", "Others"),
    "Gloves": os.path.join("Cloth", "Gloves"),
    "Shoes": os.path.join("Cloth", "Shoes"),
    "Head": os.path.join("Accessory", "Head"),
    "Torso": os.path.join("Accessory", "Torso"),
    "Arm": os.path.join("Accessory", "Arm"),
    "Leg": os.path.join("Accessory", "Leg"),
    "Accessory Others": os.path.join("Accessory", "Others"),
}

SUPPORTED_EXTENSIONS = {".cccloth", ".ccshoes", ".ccgloves", ".ccacc"}
AUDIT_EXTENSIONS = {
    ".ccacc",
    ".ccavatar",
    ".ccavatarpreset",
    ".cccam",
    ".cccloth",
    ".cceye",
    ".ccfacialprofile",
    ".ccgloves",
    ".cclightroom",
    ".ccmixerpackage",
    ".ccmixerpreset",
    ".ccproject",
    ".ccshoes",
    ".ccskin",
    ".ccskingenpreset",
    ".ccslider",
    ".ccteeth",
    ".imotionplus",
    ".italk",
    ".rlhairelement",
    ".rlhairstyle",
    ".rlhair",
    ".rlmotion",
    ".rlpose",
    ".rlwrinkle",
}


class MigrationError(RuntimeError):
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
        raise MigrationError("{} failed: {}".format(label, info))
    return info


def object_id(obj):
    try:
        return str(obj.GetID())
    except Exception:
        return None


def object_name(obj):
    try:
        return str(obj.GetName())
    except Exception:
        return "<unnamed>"


def resolve_base_avatar_path():
    for path in BASE_CANDIDATES:
        if os.path.isfile(path):
            return path
    actor_root = os.path.join(TEMPLATE_ROOT, "Actor")
    for root, _dirs, files in os.walk(actor_root):
        for filename in files:
            key = filename.casefold().replace("_", " ")
            if key == " hd neutral m.ccavatar":
                return os.path.join(root, filename)
    raise MigrationError("Unable to find the CC5 HD Neutral M base avatar")


def path_category(path):
    relative = os.path.relpath(path, TEMPLATE_ROOT)
    parts = relative.split(os.sep)
    extension = os.path.splitext(path)[1].casefold()
    if parts[0].casefold() == "cloth":
        if extension == ".ccshoes":
            return "Shoes"
        if extension == ".ccgloves":
            return "Gloves"
        return parts[1] if len(parts) > 2 and parts[1] in CATEGORY_ENUMS else "Others"
    if parts[0].casefold() == "accessory":
        category = parts[1] if len(parts) > 2 else "Accessory Others"
        return category if category in {"Head", "Torso", "Arm", "Leg"} else "Accessory Others"
    return parts[0]


def discover_assets():
    assets = []
    for root, _dirs, files in os.walk(TEMPLATE_ROOT):
        for filename in files:
            path = os.path.join(root, filename)
            extension = os.path.splitext(filename)[1].casefold()
            if extension not in AUDIT_EXTENSIONS:
                continue
            relative = os.path.relpath(path, TEMPLATE_ROOT)
            assets.append(
                {
                    "source": path,
                    "relative_source": relative,
                    "extension": extension,
                    "category": path_category(path),
                    "bytes": os.path.getsize(path),
                    "supported": extension in SUPPORTED_EXTENSIONS,
                }
            )
    assets.sort(key=lambda item: item["relative_source"].casefold())
    return assets


def content_id(path):
    try:
        value = RLPy.RApplication.GetContentId(path)
        rendered = str(value).strip()
        zeroish = rendered.casefold() in {"", "0", "-1", "none", "null"}
        zeroish = zeroish or rendered.replace("0", "").strip("{}-() ") == ""
        return {"queried": True, "registered": not zeroish, "value": rendered}
    except Exception as exc:
        return {"queried": False, "registered": None, "error": str(exc)}


def normalized_path(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(str(path))))


def content_database_files():
    """Return physical files registered in Smart Content Manager's database."""
    virtual_roots = set()
    root_errors = []
    for name in dir(RLPy):
        if not name.startswith("ETemplateRootFolder_"):
            continue
        if name.endswith(("_Invalid", "_Quantity")):
            continue
        try:
            virtual = str(RLPy.RApplication.GetDefaultContentFolder(getattr(RLPy, name)))
            if virtual and virtual.casefold() not in {"none", "null"}:
                virtual_roots.add(virtual)
        except Exception as exc:
            root_errors.append({"enum": name, "error": str(exc)})

    pending = list(virtual_roots)
    visited = set()
    files = set()
    walk_errors = []
    while pending:
        folder = pending.pop()
        if folder in visited:
            continue
        visited.add(folder)
        try:
            for path in list(RLPy.RApplication.GetContentFilesInFolder(folder) or []):
                files.add(normalized_path(path))
        except Exception as exc:
            walk_errors.append({"folder": folder, "operation": "files", "error": str(exc)})
        try:
            for child in list(RLPy.RApplication.GetContentFoldersInFolder(folder) or []):
                child = str(child)
                if child not in visited:
                    pending.append(child)
        except Exception as exc:
            walk_errors.append({"folder": folder, "operation": "folders", "error": str(exc)})
    return files, {
        "virtual_root_count": len(virtual_roots),
        "visited_folder_count": len(visited),
        "registered_file_count": len(files),
        "root_errors": root_errors,
        "walk_errors": walk_errors,
    }


def make_audit(assets, query_content_ids=True, indexed_files=None):
    groups = {}
    audited = []
    for asset in assets:
        item = dict(asset)
        if query_content_ids:
            item["content_id"] = content_id(item["source"])
        if indexed_files is not None:
            item["database_indexed"] = normalized_path(item["source"]) in indexed_files
        audited.append(item)
        key = "{} | {}".format(item["category"], item["extension"])
        group = groups.setdefault(
            key,
            {
                "category": item["category"],
                "extension": item["extension"],
                "physical": 0,
                "bytes": 0,
                "registered": 0,
                "unregistered": 0,
                "unknown": 0,
                "database_indexed": 0,
                "database_missing": 0,
                "supported": item["supported"],
            },
        )
        group["physical"] += 1
        group["bytes"] += item["bytes"]
        info = item.get("content_id")
        if not info or info.get("registered") is None:
            group["unknown"] += 1
        elif info["registered"]:
            group["registered"] += 1
        else:
            group["unregistered"] += 1
        if indexed_files is not None:
            if item["database_indexed"]:
                group["database_indexed"] += 1
            else:
                group["database_missing"] += 1
    return {
        "schema_version": 1,
        "created_at": now(),
        "cc_version": str(RLPy.RApplication.GetProductVersion()),
        "template_root": TEMPLATE_ROOT,
        "custom_root": str(RLPy.RApplication.GetCustomDataPath()),
        "asset_count": len(audited),
        "supported_count": sum(1 for item in audited if item["supported"]),
        "groups": sorted(groups.values(), key=lambda item: (item["category"], item["extension"])),
        "assets": audited,
    }


def avatars():
    return list(RLPy.RScene.GetAvatars() or [])


def load_clean_base():
    base_path = resolve_base_avatar_path()
    before = {object_id(avatar) for avatar in avatars()}
    avatar = None
    try:
        loaded = RLPy.RFileIO.LoadObject(base_path, True)
        if loaded is not None and hasattr(loaded, "GetClothes"):
            avatar = loaded
    except Exception:
        loaded = None
    if avatar is None:
        new_avatars = [item for item in avatars() if object_id(item) not in before]
        avatar = new_avatars[-1] if new_avatars else None
    if avatar is None:
        checked("Load base avatar", RLPy.RFileIO.LoadFile(base_path))
        new_avatars = [item for item in avatars() if object_id(item) not in before]
        avatar = new_avatars[-1] if new_avatars else (avatars()[0] if avatars() else None)
    if avatar is None:
        raise MigrationError("No avatar exists after loading the neutral base")
    keep_id = object_id(avatar)
    for other in avatars():
        if object_id(other) != keep_id:
            checked("Remove previous avatar", RLPy.RScene.RemoveObject(other))
    avatar.SetName("Legacy_Content_Migration_Base")
    RLPy.RScene.SelectObject(avatar)
    return avatar, base_path


def avatar_assets(avatar):
    result = []
    for getter_name in ("GetClothes", "GetAccessories", "GetHairs"):
        try:
            result.extend(list(getattr(avatar, getter_name)() or []))
        except Exception:
            pass
    unique = {}
    for item in result:
        unique[object_id(item) or "memory:{}".format(id(item))] = item
    return unique


def choose_loaded_object(avatar, before, source):
    after = avatar_assets(avatar)
    new_items = [item for key, item in after.items() if key not in before]
    selected = list(RLPy.RScene.GetSelectedObjects() or [])
    selected_assets = [item for item in selected if isinstance(item, (RLPy.RICloth, RLPy.RIAccessory))]
    stem = os.path.splitext(os.path.basename(source))[0].casefold()
    named = [item for item in new_items + selected_assets if stem in object_name(item).casefold()]
    if named:
        return named[-1], after
    if selected_assets:
        return selected_assets[-1], after
    if len(new_items) == 1:
        return new_items[0], after
    if new_items:
        return new_items[-1], after
    raise MigrationError(
        "Could not identify the object loaded from {} (selected={}, new={})".format(
            source,
            [object_name(item) for item in selected],
            [object_name(item) for item in new_items],
        )
    )


def custom_folder(category):
    virtual = None
    enum_name = CATEGORY_ENUMS.get(category)
    if enum_name and hasattr(RLPy, enum_name):
        try:
            virtual = str(
                RLPy.RApplication.GetCustomContentFolder(getattr(RLPy, enum_name))
            )
        except Exception:
            pass
    fallback = CUSTOM_FALLBACKS.get(category)
    if not fallback:
        raise MigrationError("No Custom folder mapping for {}".format(category))
    configured_root = str(RLPy.RApplication.GetCustomDataPath())
    if not os.path.isabs(configured_root):
        configured_root = CUSTOM_ROOT
    path = os.path.join(configured_root, fallback)
    os.makedirs(path, exist_ok=True)
    return path, {"enum": enum_name, "virtual": virtual, "physical_root": configured_root}


def target_path(asset, all_assets):
    folder, folder_source = custom_folder(asset["category"])
    filename = os.path.basename(asset["source"])
    duplicates = [
        item
        for item in all_assets
        if item["category"] == asset["category"]
        and os.path.basename(item["source"]).casefold() == filename.casefold()
    ]
    if len(duplicates) > 1:
        stem, extension = os.path.splitext(filename)
        digest = hashlib.sha1(asset["relative_source"].encode("utf-8")).hexdigest()[:8]
        filename = "{}__{}{}".format(stem, digest, extension)
    return os.path.join(folder, filename), folder_source


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def migrate_one(avatar, asset, all_assets, run_dir, verify_thumbnail=False):
    target, folder_source = target_path(asset, all_assets)
    result = {
        "source": asset["source"],
        "relative_source": asset["relative_source"],
        "category": asset["category"],
        "target": target,
        "target_folder_source": folder_source,
        "strategy": "filesystem_copy_with_content_manager_autosync",
        "started_at": now(),
        "finished_at": None,
        "success": False,
        "skipped": False,
        "error": None,
    }
    if os.path.isfile(target) and os.path.getsize(target) > 0:
        source_bytes = os.path.getsize(asset["source"])
        target_bytes = os.path.getsize(target)
        if source_bytes != target_bytes:
            result.update(
                {
                    "error": {
                        "type": "MigrationError",
                        "message": "Custom target exists with a different size; refusing to overwrite",
                    },
                    "source_bytes": source_bytes,
                    "target_bytes": target_bytes,
                    "finished_at": now(),
                }
            )
            return result
        if not verify_thumbnail:
            result.update(
                {
                    "success": True,
                    "skipped": True,
                    "reason": "non-empty Custom target already exists",
                    "target_bytes": os.path.getsize(target),
                    "target_content_id": content_id(target),
                    "finished_at": now(),
                }
            )
            return result
        result["preexisting_target_revalidated"] = True

    loaded_object = None
    try:
        if verify_thumbnail:
            if avatar is None:
                raise MigrationError("Pilot validation requires a loaded avatar")
            before = avatar_assets(avatar)
            RLPy.RScene.SelectObject(avatar)
            result["source_load_status"] = checked(
                "Load legacy source asset", RLPy.RFileIO.LoadFile(asset["source"])
            )
            current_avatars = avatars()
            if not current_avatars:
                raise MigrationError("Avatar disappeared after applying legacy asset")
            avatar = current_avatars[0]
            loaded_object, _after = choose_loaded_object(
                avatar, before, asset["source"]
            )
            result["source_loaded_object"] = {
                "name": object_name(loaded_object),
                "id": object_id(loaded_object),
                "python_type": type(loaded_object).__name__,
            }
            result["source_object_cleanup_status"] = checked(
                "Remove source-loaded object", RLPy.RScene.RemoveObject(loaded_object)
            )
            loaded_object = None

        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(asset["source"], target)
        if not os.path.isfile(target) or os.path.getsize(target) <= 0:
            raise MigrationError("Copy completed but no non-empty Custom target exists")
        result["source_bytes"] = os.path.getsize(asset["source"])
        result["target_bytes"] = os.path.getsize(target)
        if result["source_bytes"] != result["target_bytes"]:
            raise MigrationError("Source and Custom target sizes differ after copy")
        result["target_content_id"] = content_id(target)
        if verify_thumbnail:
            result["source_sha256"] = sha256_file(asset["source"])
            result["target_sha256"] = sha256_file(target)
            if result["source_sha256"] != result["target_sha256"]:
                raise MigrationError("Source and Custom target checksums differ")
            thumbnail_dir = os.path.join(run_dir, "verification")
            os.makedirs(thumbnail_dir, exist_ok=True)
            thumbnail_path = os.path.join(
                thumbnail_dir,
                hashlib.sha1(target.encode("utf-8")).hexdigest()[:12] + ".png",
            )
            result["thumbnail_status"] = status_info(
                RLPy.RFileIO.SaveThumbnailToFile(target, thumbnail_path)
            )
            result["thumbnail"] = {
                "path": thumbnail_path,
                "exists": os.path.isfile(thumbnail_path),
                "bytes": os.path.getsize(thumbnail_path)
                if os.path.isfile(thumbnail_path)
                else 0,
            }
            before_reapply = avatar_assets(avatar)
            RLPy.RScene.SelectObject(avatar)
            result["reapply_load_status"] = checked(
                "Reload saved Custom asset", RLPy.RFileIO.LoadFile(target)
            )
            loaded_object, _after_reapply = choose_loaded_object(
                avatar, before_reapply, target
            )
            result["reapplied_object"] = {
                "name": object_name(loaded_object),
                "id": object_id(loaded_object),
                "python_type": type(loaded_object).__name__,
            }
            result["reapply_cleanup_status"] = checked(
                "Remove reapplied Custom object", RLPy.RScene.RemoveObject(loaded_object)
            )
            loaded_object = None
            result["reapply_verified"] = True
        result["success"] = True
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if loaded_object is not None:
            try:
                result["cleanup_status"] = status_info(
                    RLPy.RScene.RemoveObject(loaded_object)
                )
            except Exception as exc:
                result["cleanup_error"] = str(exc)
        try:
            RLPy.RScene.SelectObject(avatar)
        except Exception:
            pass
        result["finished_at"] = now()
    return result


class LegacyContentMigrator(QtWidgets.QDialog):
    def __init__(self):
        super(LegacyContentMigrator, self).__init__()
        self.setWindowTitle("CC5 Legacy Content Migrator")
        self.resize(980, 680)
        self.assets = []
        self.audit = None
        self.avatar = None
        self.batch = None
        self.cancel_requested = False
        self.pilot_passed = False
        self._build_ui()
        QtCore.QTimer.singleShot(0, self.refresh_audit)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.summary = QtWidgets.QLabel("Scanning legacy Template content...")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Category",
                "Extension",
                "Physical",
                "DB Indexed",
                "DB Missing",
                "Missing ID",
                "Supported",
            ]
        )
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 2)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        layout.addWidget(self.log, 2)

        buttons = QtWidgets.QHBoxLayout()
        self.audit_button = QtWidgets.QPushButton("Rescan Audit")
        self.pilot_button = QtWidgets.QPushButton("Pilot One Shirt")
        self.clothing_button = QtWidgets.QPushButton("Migrate All Clothing")
        self.accessory_button = QtWidgets.QPushButton("Migrate Accessories")
        self.cancel_button = QtWidgets.QPushButton("Cancel Batch")
        self.close_button = QtWidgets.QPushButton("Close")
        for button in (
            self.audit_button,
            self.pilot_button,
            self.clothing_button,
            self.accessory_button,
            self.cancel_button,
            self.close_button,
        ):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.audit_button.clicked.connect(self.refresh_audit)
        self.pilot_button.clicked.connect(self.run_pilot)
        self.clothing_button.clicked.connect(self.run_clothing)
        self.accessory_button.clicked.connect(self.run_accessories)
        self.cancel_button.clicked.connect(self.request_cancel)
        self.close_button.clicked.connect(self.close)
        self.clothing_button.setEnabled(False)
        self.accessory_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def append_log(self, message):
        self.log.appendPlainText("[{}] {}".format(now(), message))
        QtWidgets.QApplication.processEvents()

    def set_busy(self, busy):
        self.audit_button.setEnabled(not busy)
        self.pilot_button.setEnabled(not busy)
        self.clothing_button.setEnabled(not busy and self.pilot_passed)
        self.accessory_button.setEnabled(not busy and self.pilot_passed)
        self.cancel_button.setEnabled(busy)
        self.close_button.setEnabled(not busy)

    def refresh_audit(self):
        if self.batch:
            return
        self.set_busy(True)
        self.append_log("Scanning physical files and CC Content IDs...")
        try:
            self.assets = discover_assets()
            indexed_files, database_scan = content_database_files()
            self.progress.setRange(0, len(self.assets))
            self.progress.setValue(0)
            audited = []
            for index, asset in enumerate(self.assets):
                item = dict(asset)
                item["content_id"] = content_id(item["source"])
                item["database_indexed"] = normalized_path(item["source"]) in indexed_files
                audited.append(item)
                if index % 25 == 0:
                    self.progress.setValue(index + 1)
                    QtWidgets.QApplication.processEvents()
            self.audit = make_audit(audited, query_content_ids=False)
            self.audit["assets"] = audited
            self.audit["database_scan"] = database_scan
            groups = {}
            for item in audited:
                key = "{} | {}".format(item["category"], item["extension"])
                group = groups.setdefault(
                    key,
                    {
                        "category": item["category"],
                        "extension": item["extension"],
                        "physical": 0,
                        "registered": 0,
                        "unregistered": 0,
                        "unknown": 0,
                        "database_indexed": 0,
                        "database_missing": 0,
                        "supported": item["supported"],
                    },
                )
                group["physical"] += 1
                registered = item["content_id"].get("registered")
                if registered is True:
                    group["registered"] += 1
                elif registered is False:
                    group["unregistered"] += 1
                else:
                    group["unknown"] += 1
                if item["database_indexed"]:
                    group["database_indexed"] += 1
                else:
                    group["database_missing"] += 1
            self.audit["groups"] = sorted(
                groups.values(), key=lambda item: (item["category"], item["extension"])
            )
            run_id = datetime.datetime.now().strftime("audit_%Y%m%d_%H%M%S_%f")
            audit_path = os.path.join(OUTPUT_ROOT, run_id, "audit.json")
            write_json(self.audit, audit_path)
            self._populate_table()
            supported = [item for item in self.assets if item["supported"]]
            clothing = [item for item in supported if item["extension"] != ".ccacc"]
            accessories = [item for item in supported if item["extension"] == ".ccacc"]
            gib = sum(item["bytes"] for item in supported) / float(1024 ** 3)
            self.summary.setText(
                "Found {} CC-related template files. Supported migration: {} clothing, "
                "{} accessories ({:.2f} GiB source data). Audit: {}".format(
                    len(self.assets), len(clothing), len(accessories), gib, audit_path
                )
            )
            self.append_log("Audit written: {}".format(audit_path))
            pilot_target = None
            pilot = next((item for item in self.assets if item["source"] == PILOT_SOURCE), None)
            if pilot:
                pilot_target, _folder_source = target_path(pilot, self.assets)
            self.pilot_passed = bool(
                pilot_target
                and os.path.isfile(pilot_target)
                and os.path.getsize(pilot_target) > 0
            )
        except Exception as exc:
            self.append_log("AUDIT FAILED: {}".format(exc))
            self.append_log(traceback.format_exc())
        finally:
            self.progress.setValue(self.progress.maximum())
            self.set_busy(False)

    def _populate_table(self):
        groups = self.audit.get("groups", []) if self.audit else []
        self.table.setRowCount(len(groups))
        for row, group in enumerate(groups):
            values = (
                group["category"],
                group["extension"],
                group["physical"],
                group["database_indexed"],
                group["database_missing"],
                group["unregistered"],
                "yes" if group["supported"] else "audit only",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def ensure_base(self):
        if self.avatar is not None and object_id(self.avatar) in {
            object_id(item) for item in avatars()
        }:
            return self.avatar
        self.append_log("Loading clean CC5 HD Neutral M base...")
        self.avatar, base_path = load_clean_base()
        self.append_log("Base loaded: {}".format(base_path))
        return self.avatar

    def confirm_scene_replace(self, label, count):
        message = (
            "{} will replace the current CC scene with a neutral migration base and "
            "process {} item(s). Save current work first.\n\nContinue?"
        ).format(label, count)
        answer = QtWidgets.QMessageBox.question(
            self,
            "Confirm Legacy Content Migration",
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def confirm_copy_batch(self, label, count):
        message = (
            "{} will copy {} validated legacy file(s) into the registered Custom "
            "categories. Existing non-empty files will not be overwritten.\n\nContinue?"
        ).format(label, count)
        answer = QtWidgets.QMessageBox.question(
            self,
            "Confirm Legacy Content Copy",
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def run_pilot(self):
        pilot = next((item for item in self.assets if item["source"] == PILOT_SOURCE), None)
        if not pilot:
            QtWidgets.QMessageBox.critical(self, "Pilot Failed", "Pilot source was not found.")
            return
        if not self.confirm_scene_replace("Pilot migration", 1):
            return
        self.start_batch("pilot", [pilot], verify_thumbnail=True)

    def run_clothing(self):
        items = [
            item
            for item in self.assets
            if item["supported"] and item["extension"] != ".ccacc"
        ]
        if self.confirm_copy_batch("Clothing migration", len(items)):
            self.start_batch("clothing", items)

    def run_accessories(self):
        items = [item for item in self.assets if item["extension"] == ".ccacc"]
        if self.confirm_copy_batch("Accessory migration", len(items)):
            self.start_batch("accessories", items)

    def start_batch(self, mode, items, verify_thumbnail=False):
        if self.batch:
            return
        if verify_thumbnail:
            try:
                self.ensure_base()
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Base Load Failed", str(exc))
                self.append_log(traceback.format_exc())
                return
        run_id = datetime.datetime.now().strftime("{}_run_%Y%m%d_%H%M%S_%f".format(mode))
        run_dir = os.path.join(OUTPUT_ROOT, run_id)
        os.makedirs(run_dir, exist_ok=False)
        self.batch = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": mode,
            "run_dir": run_dir,
            "started_at": now(),
            "finished_at": None,
            "success": False,
            "cancelled": False,
            "requested_count": len(items),
            "items": list(items),
            "next_index": 0,
            "results": [],
            "verify_thumbnail": verify_thumbnail,
        }
        self.cancel_requested = False
        self.progress.setRange(0, len(items))
        self.progress.setValue(0)
        self.set_busy(True)
        self.append_log("Started {} batch with {} item(s).".format(mode, len(items)))
        self._write_batch_state()
        QtCore.QTimer.singleShot(0, self.process_next)

    def _write_batch_state(self):
        if not self.batch:
            return
        serializable = dict(self.batch)
        serializable.pop("items", None)
        serializable.pop("verify_thumbnail", None)
        write_json(serializable, os.path.join(self.batch["run_dir"], "result.json"))

    def process_next(self):
        if not self.batch:
            return
        if self.cancel_requested or self.batch["next_index"] >= len(self.batch["items"]):
            self.finish_batch()
            return
        index = self.batch["next_index"]
        asset = self.batch["items"][index]
        self.append_log(
            "[{}/{}] {}".format(index + 1, len(self.batch["items"]), asset["relative_source"])
        )
        result = migrate_one(
            self.avatar,
            asset,
            self.assets,
            self.batch["run_dir"],
            verify_thumbnail=self.batch["verify_thumbnail"],
        )
        self.batch["results"].append(result)
        self.batch["next_index"] += 1
        self.progress.setValue(self.batch["next_index"])
        if result["success"]:
            verb = "SKIPPED" if result["skipped"] else "SAVED"
            self.append_log("{}: {}".format(verb, result["target"]))
        else:
            self.append_log("FAILED: {}".format(result["error"]["message"]))
        self._write_batch_state()
        QtCore.QTimer.singleShot(0, self.process_next)

    def request_cancel(self):
        if self.batch:
            self.cancel_requested = True
            self.append_log("Cancellation requested; stopping after the current item.")

    def finish_batch(self):
        batch = self.batch
        if not batch:
            return
        batch["cancelled"] = self.cancel_requested
        batch["finished_at"] = now()
        failures = [item for item in batch["results"] if not item["success"]]
        batch["success"] = not failures and not batch["cancelled"]
        self._write_batch_state()
        result_path = os.path.join(batch["run_dir"], "result.json")
        mode = batch["mode"]
        if mode == "pilot" and batch["success"] and batch["results"]:
            pilot_result = batch["results"][0]
            self.pilot_passed = bool(
                pilot_result.get("target_bytes", 0) > 0
                and pilot_result.get("reapply_verified")
            )
        self.append_log(
            "Finished {}: success={}, saved_or_skipped={}, failed={}, cancelled={}.".format(
                mode,
                batch["success"],
                len(batch["results"]) - len(failures),
                len(failures),
                batch["cancelled"],
            )
        )
        self.batch = None
        self.cancel_requested = False
        self.set_busy(False)
        title = "Migration Complete" if not failures else "Migration Completed with Failures"
        QtWidgets.QMessageBox.information(
            self,
            title,
            "Result: {}\n\nRefresh the Custom tab after a successful run.".format(result_path),
        )

    def closeEvent(self, event):
        if self.batch:
            event.ignore()
            self.append_log("Cancel the active batch before closing.")
            return
        event.accept()


_DIALOG = None


def run_script():
    global _DIALOG
    if _DIALOG is None:
        _DIALOG = LegacyContentMigrator()
    _DIALOG.show()
    _DIALOG.raise_()
    _DIALOG.activateWindow()


def initialize_plugin():
    run_script()


run_script()
