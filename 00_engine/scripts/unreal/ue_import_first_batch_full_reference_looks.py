"""Import and validate one audited first-batch FullReference Look in UE 5.8.

Run through ``ue_remote_exec.py``. Set ``DM_FIRST_BATCH_LOOK_MODE`` to
``preflight``, ``import``, or ``validate``. Import/validate modes also require
``DM_FIRST_BATCH_LOOK_ID``.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import unreal


REQUIRED_EXPORTS_PATH = Path(
    str(
        globals().get(
            "DM_FIRST_BATCH_REQUIRED_EXPORTS_PATH",
            r"D:\UE\Lance_Work\00_engine\scripts\dataset"
            r"\first_batch_required_exports_20260820_v1.json",
        )
    )
)
REPORT_ROOT = Path(
    str(
        globals().get(
            "DM_FIRST_BATCH_LOOK_REPORT_ROOT",
            r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
            r"\first_batch_full_reference_20260821_v1",
        )
    )
)
EXPECTED_VENDOR_ROOT = "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks"
CANONICAL_SKELETONS = {
    "female": (
        f"{EXPECTED_VENDOR_ROOT}/F_ID01_O01/"
        "CC_FB_F_ID01_O01_Skeleton.CC_FB_F_ID01_O01_Skeleton"
    ),
    "male": (
        f"{EXPECTED_VENDOR_ROOT}/M_ID01_O01/"
        "CC_FB_M_ID01_O01_Skeleton.CC_FB_M_ID01_O01_Skeleton"
    ),
}
CANONICAL_SKELETON_LOOKS = {"F_ID01_O01", "M_ID01_O01"}
ACCEPTED_REQUIRED_EXPORT_STATUSES = {
    "frozen_sources_pending_motion_export_and_unreal_validation",
    "frozen_sources_ready_for_unreal_import",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(record: dict, label: str) -> dict:
    path = Path(str(record.get("local_path", ""))).resolve()
    exists = path.is_file()
    actual_bytes = path.stat().st_size if exists else None
    actual_sha256 = sha256(path) if exists else None
    expected_bytes = int(record.get("bytes", -1))
    expected_sha256 = str(record.get("sha256", "")).lower()
    return {
        "label": label,
        "path": str(path),
        "exists": exists,
        "expected_bytes": expected_bytes,
        "actual_bytes": actual_bytes,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "passed": (
            exists
            and actual_bytes == expected_bytes
            and actual_sha256 == expected_sha256
        ),
    }


def verify_fbm(record: dict, label: str) -> dict:
    root = Path(str(record.get("local_path", ""))).resolve()
    files = sorted(path for path in root.rglob("*") if path.is_file()) if root.is_dir() else []
    actual_bytes = sum(path.stat().st_size for path in files)
    expected_count = int(record.get("file_count", -1))
    expected_bytes = int(record.get("bytes", -1))
    return {
        "label": label,
        "path": str(root),
        "exists": root.is_dir(),
        "expected_file_count": expected_count,
        "actual_file_count": len(files),
        "expected_bytes": expected_bytes,
        "actual_bytes": actual_bytes,
        "passed": (
            root.is_dir()
            and len(files) == expected_count
            and actual_bytes == expected_bytes
        ),
    }


def write_report(name: str, value: dict) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / name
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def list_assets(root: str) -> list[str]:
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return []
    return sorted(
        unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        )
    )


def look_by_id(manifest: dict, look_id: str) -> dict:
    matches = [
        row
        for row in manifest.get("full_reference_looks") or []
        if row.get("look_id") == look_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one Look {look_id}, found {len(matches)}")
    return matches[0]


def destination_for(look: dict) -> str:
    destination = str(look.get("expected_unreal_folder", ""))
    expected = f"{EXPECTED_VENDOR_ROOT}/{look['look_id']}"
    if destination != expected:
        raise RuntimeError(
            f"Unexpected destination contract for {look['look_id']}: "
            f"{destination} != {expected}"
        )
    return destination


def build_fbx_import_options(look: dict) -> tuple[unreal.FbxImportUI, str | None]:
    """Build deterministic skeletal import options for CC FullReference Looks."""
    sex = str(look.get("sex", "")).lower()
    skeleton_path = CANONICAL_SKELETONS.get(sex)
    if skeleton_path is None:
        raise RuntimeError(f"Unsupported Look sex for {look['look_id']}: {sex!r}")

    skeleton = unreal.load_asset(skeleton_path)
    if skeleton is None and look["look_id"] not in CANONICAL_SKELETON_LOOKS:
        raise RuntimeError(
            f"Canonical {sex} Skeleton is missing before importing "
            f"{look['look_id']}: {skeleton_path}"
        )

    options = unreal.FbxImportUI()
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_mesh", True)
    options.set_editor_property(
        "mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH
    )
    options.set_editor_property("import_animations", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", True)
    options.set_editor_property("create_physics_asset", True)
    if skeleton is not None:
        options.set_editor_property("skeleton", skeleton)

    skeletal_data = options.get_editor_property("skeletal_mesh_import_data")
    skeletal_data.set_editor_property("import_morph_targets", True)
    skeletal_data.set_editor_property("update_skeleton_reference_pose", False)
    skeletal_data.set_editor_property("use_t0_as_ref_pose", False)
    skeletal_data.set_editor_property(
        "normal_import_method",
        unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS,
    )
    return options, skeleton_path if skeleton is not None else None


def copy_fbx_import_options(
    source: unreal.FbxImportUI, target: unreal.FbxImportUI
) -> None:
    for property_name in (
        "automated_import_should_detect_type",
        "import_as_skeletal",
        "import_mesh",
        "mesh_type_to_import",
        "import_animations",
        "import_materials",
        "import_textures",
        "create_physics_asset",
        "skeleton",
    ):
        target.set_editor_property(
            property_name, source.get_editor_property(property_name)
        )

    source_data = source.get_editor_property("skeletal_mesh_import_data")
    target_data = target.get_editor_property("skeletal_mesh_import_data")
    for property_name in (
        "import_morph_targets",
        "update_skeleton_reference_pose",
        "use_t0_as_ref_pose",
        "normal_import_method",
    ):
        target_data.set_editor_property(
            property_name, source_data.get_editor_property(property_name)
        )


def configure_cc_factory_import_ui(
    factory: unreal.CCFbxFactory, options: unreal.FbxImportUI
) -> str:
    factory_path = factory.get_path_name()
    matches = [
        candidate
        for candidate in unreal.ObjectIterator(unreal.FbxImportUI)
        if candidate.get_outer().get_path_name() == factory_path
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one FbxImportUI under {factory_path}, found {len(matches)}"
        )
    copy_fbx_import_options(options, matches[0])
    return matches[0].get_path_name()


def register_factory_ui_enforcer(
    factory: unreal.CCFbxFactory, options: unreal.FbxImportUI
) -> tuple[object, dict]:
    factory_path = factory.get_path_name()
    desired_skeleton = options.get_editor_property("skeleton")
    desired_skeleton_path = (
        desired_skeleton.get_path_name() if desired_skeleton else None
    )
    state = {"tick_count": 0, "rewrite_count": 0, "last_error": None}

    def enforce_factory_ui(_delta_time: float) -> None:
        state["tick_count"] += 1
        try:
            for candidate in unreal.ObjectIterator(unreal.FbxImportUI):
                if candidate.get_outer().get_path_name() != factory_path:
                    continue
                current_skeleton = candidate.get_editor_property("skeleton")
                current_skeleton_path = (
                    current_skeleton.get_path_name() if current_skeleton else None
                )
                if current_skeleton_path != desired_skeleton_path:
                    copy_fbx_import_options(options, candidate)
                    state["rewrite_count"] += 1
        except Exception as exc:
            state["last_error"] = str(exc)

    handle = unreal.register_slate_pre_tick_callback(enforce_factory_ui)
    return handle, state


def object_record(asset_path: str) -> dict:
    asset = unreal.load_asset(asset_path)
    if asset is None:
        return {"path": asset_path, "load_error": True}
    record = {
        "path": asset_path,
        "name": asset.get_name(),
        "class": asset.get_class().get_name(),
    }
    if isinstance(asset, unreal.SkeletalMesh):
        skeleton = asset.get_editor_property("skeleton")
        material_interfaces = [
            slot.get_editor_property("material_interface")
            for slot in asset.get_editor_property("materials")
        ]
        material_classes = Counter(
            interface.get_class().get_name() if interface else "None"
            for interface in material_interfaces
        )
        record.update(
            {
                "skeleton": skeleton.get_path_name() if skeleton else None,
                "material_slot_count": len(material_interfaces),
                "material_slot_class_counts": dict(sorted(material_classes.items())),
                "material_slot_paths": [
                    interface.get_path_name() if interface else None
                    for interface in material_interfaces
                ],
                "morph_target_count": len(asset.get_editor_property("morph_targets")),
            }
        )
    return record


def collect_validation(look: dict, destination: str) -> dict:
    assets = list_assets(destination)
    records = [object_record(path) for path in assets]
    classes = Counter(record.get("class", "LoadError") for record in records)
    meshes = [record for record in records if record.get("class") == "SkeletalMesh"]
    skeletons = sorted(
        {record["skeleton"] for record in meshes if record.get("skeleton")}
    )
    expected_skeleton = CANONICAL_SKELETONS.get(str(look.get("sex", "")).lower())
    skeleton_reuse_contract_passed = bool(expected_skeleton) and skeletons == [
        expected_skeleton
    ]
    material_paths = [
        path
        for record in meshes
        for path in record.get("material_slot_paths", [])
        if path
    ]
    mesh_contract_passed = bool(meshes) and all(
        record.get("skeleton")
        and record.get("material_slot_count", 0) > 0
        and record.get("morph_target_count", 0) >= 400
        for record in meshes
    )
    material_contract_passed = bool(meshes) and all(
        record.get("material_slot_class_counts")
        == {"MaterialInstanceConstant": record.get("material_slot_count")}
        for record in meshes
    )
    required_hq_materials_passed = all(
        any(marker in path for path in material_paths)
        for marker in ("/Std_Skin_Head_Pbr_HQ_Inst.", "/Std_Skin_Body_Pbr_HQ_Inst.")
    )
    auto_setup_materials_passed = (
        classes.get("MaterialInstanceConstant", 0) > 0
        and classes.get("Texture2D", 0) > 0
        and material_contract_passed
        and required_hq_materials_passed
    )
    rigging_contract_passed = (
        classes.get("PhysicsAsset", 0) > 0
        and classes.get("AnimBlueprint", 0) > 0
        and classes.get("Blueprint", 0) > 0
        and classes.get("IKRigDefinition", 0) > 0
        and classes.get("IKRetargeter", 0) > 0
    )
    return {
        "look_id": look["look_id"],
        "destination": destination,
        "asset_count": len(records),
        "asset_class_counts": dict(sorted(classes.items())),
        "skeletal_mesh_count": len(meshes),
        "skeletons": skeletons,
        "expected_skeleton": expected_skeleton,
        "skeleton_reuse_contract_passed": skeleton_reuse_contract_passed,
        "morph_target_counts": [record.get("morph_target_count") for record in meshes],
        "source_fbm_file_count": look["fbm"]["file_count"],
        "imported_texture_count": classes.get("Texture2D", 0),
        "mesh_contract_passed": mesh_contract_passed,
        "material_contract_passed": material_contract_passed,
        "required_hq_materials_passed": required_hq_materials_passed,
        "auto_setup_materials_passed": auto_setup_materials_passed,
        "rigging_contract_passed": rigging_contract_passed,
        "assets": records,
        "success": (
            bool(skeletons)
            and skeleton_reuse_contract_passed
            and mesh_contract_passed
            and auto_setup_materials_passed
            and rigging_contract_passed
        ),
    }


def normalize_skeleton_references(look: dict, destination: str) -> dict:
    """Consolidate a transient per-Look skeleton into the canonical sex skeleton."""
    expected_skeleton = CANONICAL_SKELETONS.get(str(look.get("sex", "")).lower())
    result = {
        "expected_skeleton": expected_skeleton,
        "mesh_skeletons_before": [],
        "source_skeletons": [],
        "consolidated": False,
        "consolidate_result": None,
        "mesh_skeletons_after": [],
        "passed": False,
        "error": None,
    }
    try:
        if not expected_skeleton:
            raise RuntimeError(f"No canonical skeleton configured for {look['look_id']}")
        target = unreal.load_asset(expected_skeleton)
        if not target:
            raise RuntimeError(f"Canonical skeleton does not exist: {expected_skeleton}")

        mesh_assets = []
        for path in list_assets(destination):
            asset = unreal.load_asset(path)
            if asset and asset.get_class().get_name() == "SkeletalMesh":
                mesh_assets.append(asset)

        before = sorted(
            {
                mesh.get_editor_property("skeleton").get_path_name()
                for mesh in mesh_assets
                if mesh.get_editor_property("skeleton")
            }
        )
        result["mesh_skeletons_before"] = before
        source_paths = [path for path in before if path != expected_skeleton]
        result["source_skeletons"] = source_paths

        sources = []
        for source_path in source_paths:
            if not source_path.startswith(f"{destination}/"):
                raise RuntimeError(
                    f"Refusing to consolidate skeleton outside Look destination: {source_path}"
                )
            source = unreal.load_asset(source_path)
            if not source or source.get_class().get_name() != "Skeleton":
                raise RuntimeError(f"Unable to load transient skeleton: {source_path}")
            sources.append(source)

        if sources:
            result["consolidated"] = True
            result["consolidate_result"] = bool(
                unreal.EditorAssetLibrary.consolidate_assets(target, sources)
            )
        else:
            result["consolidate_result"] = True

        unreal.EditorAssetLibrary.save_directory(
            destination, only_if_is_dirty=False, recursive=True
        )
        after = sorted(
            {
                mesh.get_editor_property("skeleton").get_path_name()
                for mesh in mesh_assets
                if mesh.get_editor_property("skeleton")
            }
        )
        result["mesh_skeletons_after"] = after
        result["passed"] = bool(result["consolidate_result"]) and after == [
            expected_skeleton
        ]
    except Exception as exc:  # Keep the failure in the validation artifact.
        result["error"] = str(exc)
    return result


def source_checks(look: dict) -> list[dict]:
    return [
        verify_file(look["fbx"], f"{look['look_id']}.fbx"),
        verify_file(look["auto_setup_json"], f"{look['look_id']}.auto_setup_json"),
        verify_fbm(look["fbm"], f"{look['look_id']}.fbm"),
    ]


def run_preflight(manifest: dict) -> dict:
    looks = manifest.get("full_reference_looks") or []
    if manifest.get("status") not in ACCEPTED_REQUIRED_EXPORT_STATUSES:
        raise RuntimeError("Required-exports manifest is not at the expected frozen state")
    expected_count = int(
        (manifest.get("counts") or {}).get("full_reference_looks", -1)
    )
    if expected_count <= 0 or len(looks) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} FullReference Looks, found {len(looks)}"
        )
    rows = []
    for look in looks:
        destination = destination_for(look)
        checks = source_checks(look)
        rows.append(
            {
                "look_id": look["look_id"],
                "destination": destination,
                "source_checks": checks,
                "source_passed": all(item["passed"] for item in checks),
                "destination_asset_count": len(list_assets(destination)),
            }
        )
    report = {
        "schema_version": 1,
        "mode": "preflight",
        "created_at_utc": utc_now(),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "required_exports_path": str(REQUIRED_EXPORTS_PATH),
        "required_exports_sha256": sha256(REQUIRED_EXPORTS_PATH),
        "expected_look_count": expected_count,
        "look_count": len(rows),
        "source_passed_count": sum(row["source_passed"] for row in rows),
        "existing_destination_count": sum(row["destination_asset_count"] > 0 for row in rows),
        "rows": rows,
    }
    report["success"] = report["source_passed_count"] == expected_count
    path = write_report("preflight.json", report)
    if not report["success"]:
        raise RuntimeError(f"First-batch Look preflight failed; see {path}")
    return report


def validate_or_import(manifest: dict, look_id: str, import_if_missing: bool) -> dict:
    look = look_by_id(manifest, look_id)
    destination = destination_for(look)
    checks = source_checks(look)
    if not all(item["passed"] for item in checks):
        raise RuntimeError(f"Source validation failed for {look_id}")

    before_assets = list_assets(destination)
    imported_paths = []
    import_exception = None
    requested_skeleton = None
    import_options_applied = False
    factory_import_ui_path = None
    factory_ui_enforcer_state = None
    skeleton_normalization = None
    reused_existing = bool(before_assets)
    interactive = bool(globals().get("DM_FIRST_BATCH_LOOK_INTERACTIVE", False))
    automated_task = bool(
        globals().get("DM_FIRST_BATCH_LOOK_AUTOMATED_TASK", not interactive)
    )
    if not before_assets:
        if not import_if_missing:
            raise RuntimeError(f"No imported assets exist for {look_id}")
        source_fbx = Path(look["fbx"]["local_path"])
        source_json = Path(look["auto_setup_json"]["local_path"])
        if source_fbx.stem != source_json.stem:
            raise RuntimeError(f"FBX/Auto Setup JSON basename mismatch for {look_id}")
        factory = unreal.CCFbxFactory()
        # RL's factory reports False for script_factory_can_import on the same
        # CC FBXs that it imports successfully; retain that value as evidence,
        # but the actual import plus post-import contract is authoritative.
        factory_can_import_probe = bool(
            factory.script_factory_can_import(str(source_fbx))
        )
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(source_fbx))
        task.set_editor_property("destination_path", destination)
        task.set_editor_property("automated", automated_task)
        task.set_editor_property("save", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("factory", factory)
        import_options, requested_skeleton = build_fbx_import_options(look)
        task.set_editor_property("options", import_options)
        factory_import_ui_path = configure_cc_factory_import_ui(
            factory, import_options
        )
        import_options_applied = True
        enforcer_handle, factory_ui_enforcer_state = register_factory_ui_enforcer(
            factory, import_options
        )
        try:
            try:
                unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            except RuntimeError as exc:
                # Auto Setup can report a transient post-process skeleton error after
                # it has already created the complete character bundle. Preserve the
                # diagnostic and let the structural validation below decide whether
                # the import is usable.
                import_exception = str(exc)
        finally:
            unreal.unregister_slate_pre_tick_callback(enforcer_handle)
        imported_paths = list(task.get_editor_property("imported_object_paths"))
        unreal.EditorAssetLibrary.save_directory(
            destination, only_if_is_dirty=False, recursive=True
        )

    if import_if_missing:
        skeleton_normalization = normalize_skeleton_references(look, destination)

    validation = collect_validation(look, destination)
    report = {
        "schema_version": 1,
        "mode": "import" if import_if_missing else "validate",
        "created_at_utc": utc_now(),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "required_exports_path": str(REQUIRED_EXPORTS_PATH),
        "required_exports_sha256": sha256(REQUIRED_EXPORTS_PATH),
        "source_checks": checks,
        "assets_before_import": len(before_assets),
        "reused_existing": reused_existing,
        "interactive_import": interactive,
        "automated_import_task": automated_task,
        "task_imported_object_paths": imported_paths,
        "import_exception": import_exception,
        "cc_factory_can_import_probe": (
            factory_can_import_probe if not before_assets else None
        ),
        "requested_skeleton": requested_skeleton,
        "import_options_applied": import_options_applied,
        "factory_import_ui_path": factory_import_ui_path,
        "factory_ui_enforcer_state": factory_ui_enforcer_state,
        "skeleton_normalization": skeleton_normalization,
        "production_status": "not_approved",
        **validation,
    }
    path = write_report(f"{look_id}_import_validation.json", report)
    unreal.SystemLibrary.collect_garbage()
    if not report["success"]:
        raise RuntimeError(f"Imported Look failed UE validation; see {path}")
    return report


def main() -> dict:
    if not REQUIRED_EXPORTS_PATH.is_file():
        raise FileNotFoundError(str(REQUIRED_EXPORTS_PATH))
    manifest = read_json(REQUIRED_EXPORTS_PATH)
    mode = globals().get("DM_FIRST_BATCH_LOOK_MODE", "preflight")
    look_id = globals().get("DM_FIRST_BATCH_LOOK_ID")
    if mode == "preflight":
        result = run_preflight(manifest)
    elif mode == "import" and look_id:
        result = validate_or_import(manifest, look_id, True)
    elif mode == "validate" and look_id:
        result = validate_or_import(manifest, look_id, False)
    else:
        raise ValueError(f"Unsupported mode/look pair: {mode}/{look_id}")
    summary = {
        "mode": mode,
        "look_id": result.get("look_id"),
        "success": result.get("success"),
        "look_count": result.get("look_count"),
        "source_passed_count": result.get("source_passed_count"),
        "existing_destination_count": result.get("existing_destination_count"),
        "asset_count": result.get("asset_count"),
        "skeletal_mesh_count": result.get("skeletal_mesh_count"),
        "skeletons": result.get("skeletons"),
    }
    print(
        "DM_FIRST_BATCH_LOOK_RESULT="
        + json.dumps(summary, ensure_ascii=False, sort_keys=True)
    )
    return result


main()
