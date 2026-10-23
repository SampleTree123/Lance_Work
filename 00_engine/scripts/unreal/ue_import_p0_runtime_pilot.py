"""Preflight and import the P0 CC5 Unreal runtime pilot bundle.

Run through ue_remote_exec.py. Set DM_P0_RUNTIME_MODE in the remote payload to
one of: preflight, female_reference, male_reference.
"""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_import_p0_runtime_pilot.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import unreal


MANIFEST_PATH = Path(
    r"D:\UE\exports\character_creator\p0_ue_runtime_pilot_20260818_v1"
    r"\export_bundle_manifest.json"
)
REPORT_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\p0_runtime_pilot_20260819_v1"
)

REFERENCE_TARGETS = {
    "female_reference": {
        "binding_id": "p0_female_clothed",
        "destination": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/F02/FullReference"
        ),
        "report_name": "female_reference_import.json",
        "validation_report_name": "female_reference_validation.json",
    },
    "male_reference": {
        "binding_id": "p0_male_clothed",
        "destination": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/M02/FullReference"
        ),
        "report_name": "male_reference_import.json",
        "validation_report_name": "male_reference_validation.json",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_entries(manifest: dict) -> list[tuple[str, dict]]:
    entries = [
        ("work_order", manifest["work_order"]),
        ("cc_export_report", manifest["cc_export_report"]),
    ]
    for actor in manifest["actors"]:
        prefix = actor["actor_binding_id"]
        entries.extend(
            [
                (f"{prefix}.reference_fbx", actor["reference_fbx"]),
                (f"{prefix}.auto_setup_json", actor["auto_setup_json"]),
            ]
        )
    for motion in manifest["motions"]:
        prefix = motion["case_id"]
        entries.extend(
            [
                (f"{prefix}.source_motion", motion["source_motion"]),
                (f"{prefix}.raw_ascii_fbx", motion["raw_ascii_fbx"]),
                (f"{prefix}.patched_fbx", motion["patched_fbx"]),
                (f"{prefix}.bone_patch_report", motion["bone_patch_report"]),
            ]
        )
    return entries


def verify_entry(label: str, entry: dict) -> dict:
    path = Path(entry["path"])
    exists = path.is_file()
    actual_bytes = path.stat().st_size if exists else None
    actual_sha256 = sha256(path) if exists else None
    expected_bytes = entry["bytes"]
    expected_sha256 = entry["sha256"].lower()
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


def list_assets(root: str) -> list[str]:
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return []
    return sorted(
        unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        )
    )


def write_report(name: str, payload: dict) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def actor_for_binding(manifest: dict, binding_id: str) -> dict:
    matches = [
        actor
        for actor in manifest["actors"]
        if actor["actor_binding_id"] == binding_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one actor for binding {binding_id}, found {len(matches)}"
        )
    return matches[0]


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
        material_class_counts = Counter(
            interface.get_class().get_name() if interface else "None"
            for interface in material_interfaces
        )
        record.update(
            {
                "skeleton": skeleton.get_path_name() if skeleton else None,
                "material_slot_count": len(material_interfaces),
                "material_slot_class_counts": dict(
                    sorted(material_class_counts.items())
                ),
                "material_slot_paths": [
                    interface.get_path_name() if interface else None
                    for interface in material_interfaces
                ],
                "morph_target_count": len(
                    asset.get_editor_property("morph_targets")
                ),
            }
        )
    return record


def collect_reference_validation(
    destination: str, expected_texture_floor: int
) -> dict:
    assets = list_assets(destination)
    records = [object_record(path) for path in assets]
    classes = Counter(record.get("class", "LoadError") for record in records)
    skeletal_meshes = [
        record for record in records if record.get("class") == "SkeletalMesh"
    ]
    skeletons = sorted(
        {
            record["skeleton"]
            for record in skeletal_meshes
            if record.get("skeleton")
        }
    )
    mesh_contract_passed = bool(skeletal_meshes) and all(
        record.get("material_slot_count", 0) > 0
        and record.get("morph_target_count", 0) > 0
        for record in skeletal_meshes
    )
    material_slot_contract_passed = bool(skeletal_meshes) and all(
        record.get("material_slot_class_counts")
        == {"MaterialInstanceConstant": record.get("material_slot_count")}
        for record in skeletal_meshes
    )
    material_slot_paths = [
        path
        for record in skeletal_meshes
        for path in record.get("material_slot_paths", [])
        if path
    ]
    required_hq_material_markers = (
        "/Std_Skin_Head_Pbr_HQ_Inst.",
        "/Std_Skin_Body_Pbr_HQ_Inst.",
    )
    required_hq_materials_passed = all(
        any(marker in path for path in material_slot_paths)
        for marker in required_hq_material_markers
    )
    hq_material_slot_count = sum(
        "_HQ_Inst." in path or "_LWHQ_Inst." in path
        for path in material_slot_paths
    )
    auto_setup_hq_assets_passed = (
        classes.get("MaterialInstanceConstant", 0) > 0
        and classes.get("Texture2D", 0) > 0
        and material_slot_contract_passed
        and required_hq_materials_passed
        and hq_material_slot_count > 0
    )
    rigging_contract_passed = (
        classes.get("PhysicsAsset", 0) > 0
        and classes.get("AnimBlueprint", 0) > 0
        and classes.get("Blueprint", 0) > 0
        and classes.get("IKRigDefinition", 0) > 0
        and classes.get("IKRetargeter", 0) > 0
    )
    return {
        "asset_count": len(records),
        "asset_class_counts": dict(sorted(classes.items())),
        "skeletons": skeletons,
        "assets": records,
        "mesh_contract_passed": mesh_contract_passed,
        "source_fbm_file_count": expected_texture_floor,
        "imported_texture_count": classes.get("Texture2D", 0),
        "material_slot_contract_passed": material_slot_contract_passed,
        "required_hq_materials_passed": required_hq_materials_passed,
        "hq_material_slot_count": hq_material_slot_count,
        "subsurface_profile_count": classes.get("SubsurfaceProfile", 0),
        "auto_setup_hq_assets_passed": auto_setup_hq_assets_passed,
        "rigging_contract_passed": rigging_contract_passed,
        "success": bool(skeletons)
        and mesh_contract_passed
        and auto_setup_hq_assets_passed
        and rigging_contract_passed,
    }


def build_preflight(manifest: dict) -> dict:
    checks = [verify_entry(label, entry) for label, entry in hash_entries(manifest)]
    failed = [item for item in checks if not item["passed"]]

    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    vendor_root = manifest["unreal"]["vendor_root"]
    datamake_root = manifest["unreal"]["datamake_root"]
    factory = unreal.CCFbxFactory()
    reference_sources = [
        actor["reference_fbx"]["path"] for actor in manifest["actors"]
    ]
    factory_probe = {
        source: bool(factory.script_factory_can_import(source))
        for source in reference_sources
    }
    target_assets = {
        vendor_root: list_assets(vendor_root),
        datamake_root: list_assets(datamake_root),
    }
    success = not failed and all(not assets for assets in target_assets.values())
    return {
        "schema_version": 1,
        "mode": "preflight",
        "created_at_utc": utc_now(),
        "manifest_path": str(MANIFEST_PATH),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "manifest_status": manifest.get("status"),
        "production_status": manifest.get("production_status"),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "editor_world": world.get_path_name() if world else None,
        "cc_factory_class": factory.get_class().get_path_name(),
        "cc_factory_formats": list(factory.get_editor_property("formats")),
        "cc_factory_can_import_probe": factory_probe,
        "hash_checks": checks,
        "hash_check_count": len(checks),
        "hash_failure_count": len(failed),
        "target_assets_before_import": target_assets,
        "success": success,
    }


def run_preflight(manifest: dict) -> dict:
    report = build_preflight(manifest)
    path = write_report("preflight.json", report)
    if not report["success"]:
        raise RuntimeError(f"P0 runtime preflight failed; see {path}")
    unreal.log(f"DataMake P0 runtime preflight passed: {path}")
    return report


def import_reference(mode: str, manifest: dict) -> dict:
    config = REFERENCE_TARGETS[mode]
    actor = actor_for_binding(manifest, config["binding_id"])
    source_fbx = Path(actor["reference_fbx"]["path"])
    source_json = Path(actor["auto_setup_json"]["path"])
    destination = config["destination"]

    source_checks = [
        verify_entry(f"{config['binding_id']}.reference_fbx", actor["reference_fbx"]),
        verify_entry(
            f"{config['binding_id']}.auto_setup_json", actor["auto_setup_json"]
        ),
    ]
    if not all(check["passed"] for check in source_checks):
        raise RuntimeError(f"Reference source hash check failed for {mode}")
    if source_fbx.stem != source_json.stem:
        raise RuntimeError("FBX and Auto Setup JSON basenames do not match")

    before_assets = list_assets(destination)
    if before_assets:
        raise RuntimeError(
            f"Refusing to overwrite non-empty destination {destination}: "
            + ", ".join(before_assets)
        )

    factory = unreal.CCFbxFactory()
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source_fbx))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("factory", factory)

    unreal.log(
        f"DataMake P0 runtime: importing {source_fbx} to {destination} "
        "with CCFbxFactory"
    )
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    unreal.EditorAssetLibrary.save_directory(
        destination, only_if_is_dirty=False, recursive=True
    )

    validation = collect_reference_validation(
        destination, actor["fbm"]["file_count"]
    )
    report = {
        "schema_version": 1,
        "mode": mode,
        "created_at_utc": utc_now(),
        "source_fbx": str(source_fbx),
        "source_json": str(source_json),
        "destination": destination,
        "factory": factory.get_class().get_path_name(),
        "task_imported_object_paths": list(task.get_editor_property("imported_object_paths")),
        "source_checks": source_checks,
        **validation,
        "raw_import_success": bool(validation["skeletons"])
        and validation["mesh_contract_passed"],
        "requires_manual_auto_setup": not validation["success"],
        "production_status": "not_approved",
    }
    path = write_report(config["report_name"], report)
    if not report["raw_import_success"]:
        raise RuntimeError(f"Reference raw import failed validation; see {path}")
    if report["requires_manual_auto_setup"]:
        unreal.log_warning(
            "DataMake P0 runtime raw import passed but requires manual Auto Setup: "
            + str(path)
        )
    else:
        unreal.log(f"DataMake P0 runtime reference import passed: {path}")
    return report


def validate_existing_reference(mode: str, manifest: dict) -> dict:
    reference_mode = mode.removeprefix("validate_")
    config = REFERENCE_TARGETS[reference_mode]
    actor = actor_for_binding(manifest, config["binding_id"])
    validation = collect_reference_validation(
        config["destination"], actor["fbm"]["file_count"]
    )
    report = {
        "schema_version": 1,
        "mode": mode,
        "created_at_utc": utc_now(),
        "source_fbx": actor["reference_fbx"]["path"],
        "source_json": actor["auto_setup_json"]["path"],
        "destination": config["destination"],
        "factory": "/Script/RLPlugin.CCFbxFactory",
        "validation_only": True,
        **validation,
        "production_status": "not_approved",
    }
    path = write_report(config["validation_report_name"], report)
    if not report["success"]:
        raise RuntimeError(f"Existing reference failed validation; see {path}")
    unreal.log(f"DataMake P0 runtime existing reference passed: {path}")
    return report


def main() -> dict:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(str(MANIFEST_PATH))
    manifest = read_json(MANIFEST_PATH)
    mode = globals().get("DM_P0_RUNTIME_MODE", "preflight")
    if mode == "preflight":
        result = run_preflight(manifest)
    elif mode in REFERENCE_TARGETS:
        result = import_reference(mode, manifest)
    elif mode.removeprefix("validate_") in REFERENCE_TARGETS:
        result = validate_existing_reference(mode, manifest)
    else:
        raise ValueError(f"Unsupported DM_P0_RUNTIME_MODE: {mode}")
    print("DM_P0_RUNTIME_RESULT=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


main()
