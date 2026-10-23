"""Bounded Unreal import worker for the CC5 modular outfit pilot.

Run through remote execution. Set DM_MODULAR_MODE to one of preflight,
cleanup_case, import_reference, import_split, apply_materials, or validate_case.
All modes except preflight also require DM_MODULAR_CASE_ID.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import re

import unreal


LEGACY_PILOT_MANIFEST_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\unreal"
    r"\ue_modular_outfit_pilot_manifest_20260829_v1.json"
)
MANIFEST_PATH = Path(globals().get("DM_MODULAR_MANIFEST_PATH", LEGACY_PILOT_MANIFEST_PATH))
REPORT_ROOT = Path(globals().get("DM_MODULAR_REPORT_ROOT",
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\modular_outfit_pilot_20260829_v1"
))
PROJECT_ROOT = "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot"
DEFAULT_INTERCHANGE_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
PIPELINE_ASSET_NAME = "DM_Interchange_Split_Pipeline_v1"
EXPECTED_CASE_COUNT = 14
EXPECTED_BASE_CASE_IDS = {"male": "M_BASE", "female": "F_BASE"}
VALID_MODES = {
    "preflight",
    "cleanup_case",
    "import_reference",
    "import_split",
    "apply_materials",
    "validate_case",
}
RIG_ASSET_CLASSES = (
    "PhysicsAsset",
    "AnimBlueprint",
    "Blueprint",
    "IKRigDefinition",
    "IKRetargeter",
)
HQ_SKIN_MATERIAL_MARKERS = (
    "std_skin_head_pbr_hq_inst",
    "std_skin_body_pbr_hq_inst",
)
SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_file(path: Path, label: str) -> dict:
    exists = False
    size_bytes = None
    actual_sha256 = None
    error = None
    try:
        exists = path.is_file()
        size_bytes = path.stat().st_size if exists else None
        actual_sha256 = sha256_file(path) if exists else None
    except OSError as exc:
        error = str(exc)
    return {
        "label": label,
        "path": str(path),
        "exists": exists,
        "size_bytes": size_bytes,
        "sha256": actual_sha256,
        "expected_sha256": None,
        "error": error,
        "passed": bool(exists and size_bytes and actual_sha256),
    }


def validate_manifest(manifest: dict) -> dict:
    """Validate the frozen pilot shape without consulting Unreal."""
    errors = []
    if not isinstance(manifest, dict):
        raise ValueError("Invalid modular outfit manifest: root must be an object")
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Invalid modular outfit manifest: cases must be a list")
    expected_count = expected_case_count(manifest)
    if len(cases) != expected_count:
        errors.append(
            f"expected {expected_count} cases, found {len(cases)}"
        )
    declared_count = manifest.get("counts", {}).get("case_count")
    if declared_count != expected_count:
        errors.append(
            f"counts.case_count must be {expected_count}, found {declared_count}"
        )

    bodyfit_by_id = {}
    bodyfits = manifest.get("bodyfits")
    if not isinstance(bodyfits, list):
        errors.append("bodyfits must be a list")
        bodyfits = []
    for index, bodyfit in enumerate(bodyfits):
        if not isinstance(bodyfit, dict):
            errors.append(f"bodyfits[{index}] must be an object")
            continue
        bodyfit_id = bodyfit.get("bodyfit_id")
        sex = bodyfit.get("sex")
        if not isinstance(bodyfit_id, str) or not SEGMENT_PATTERN.fullmatch(bodyfit_id):
            errors.append(f"bodyfits[{index}].bodyfit_id is not a safe asset segment")
            continue
        if bodyfit_id in bodyfit_by_id:
            errors.append(f"duplicate bodyfit_id {bodyfit_id}")
        bodyfit_by_id[bodyfit_id] = sex

    case_ids = []
    base_cases = []
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("case_id")
        bodyfit_id = case.get("bodyfit_id")
        sex = case.get("sex")
        if not isinstance(case_id, str) or not SEGMENT_PATTERN.fullmatch(case_id):
            errors.append(f"{prefix}.case_id is not a safe asset segment")
        else:
            case_ids.append(case_id)
        if not isinstance(bodyfit_id, str) or not SEGMENT_PATTERN.fullmatch(bodyfit_id):
            errors.append(f"{prefix}.bodyfit_id is not a safe asset segment")
        elif bodyfit_id not in bodyfit_by_id:
            errors.append(f"{prefix}.bodyfit_id {bodyfit_id} is not declared")
        elif bodyfit_by_id[bodyfit_id] != sex:
            errors.append(
                f"{prefix} sex {sex} does not match bodyfit {bodyfit_id}"
            )
        if sex not in EXPECTED_BASE_CASE_IDS:
            errors.append(f"{prefix}.sex must be male or female")
        if manifest.get("import_scope") == "wardrobe_average_v1":
            try:
                destinations_for_case(case)
                root = case.get("ue_case_root", "")
                if case.get("case_role") == "base_body":
                    expected_root = case_destinations(bodyfit_id, case_id)["case_root"]
                    if root != expected_root or not case.get("reuse_existing_base"):
                        raise ValueError("Wardrobe must reuse the exact validated base")
                elif not root.startswith(
                    f"/Game/Vendor/Reallusion/CC5/Wardrobe/{sex.title()}/Average/"
                ):
                    raise ValueError("Wardrobe case root is outside its sex/Average scope")
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f"{prefix}: {exc}")
        if case.get("case_role") == "base_body":
            base_cases.append(case)

        planned_export = case.get("planned_export")
        if not isinstance(planned_export, dict):
            errors.append(f"{prefix}.planned_export must be an object")
            continue
        for key, suffix in (
            ("fbx", ".fbx"),
            ("json", ".json"),
            ("project", ".ccproject"),
        ):
            value = planned_export.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.planned_export.{key} is required")
            elif Path(value).suffix.lower() != suffix:
                errors.append(
                    f"{prefix}.planned_export.{key} must end with {suffix}"
                )
        fbx = planned_export.get("fbx")
        sidecar = planned_export.get("json")
        if isinstance(fbx, str) and isinstance(sidecar, str):
            if Path(fbx).stem.casefold() != Path(sidecar).stem.casefold():
                errors.append(f"{prefix} FBX and JSON basenames must match")

    duplicates = sorted(
        case_id for case_id, count in Counter(case_ids).items() if count != 1
    )
    if duplicates:
        errors.append("duplicate case_id values: " + ", ".join(duplicates))

    actual_base_ids = {
        case.get("case_id") for case in base_cases if isinstance(case, dict)
    }
    expected_base_ids = set(EXPECTED_BASE_CASE_IDS.values())
    if actual_base_ids != expected_base_ids or len(base_cases) != 2:
        errors.append(
            "base cases must be exactly M_BASE and F_BASE"
        )
    for sex, expected_case_id in EXPECTED_BASE_CASE_IDS.items():
        matches = [
            case
            for case in base_cases
            if case.get("sex") == sex and case.get("case_id") == expected_case_id
        ]
        if len(matches) != 1:
            errors.append(
                f"expected exactly one {sex} base case named {expected_case_id}"
            )

    if errors:
        raise ValueError("Invalid modular outfit manifest: " + "; ".join(errors))
    return {
        "case_count": len(cases),
        "case_ids": list(case_ids),
        "base_case_ids": dict(EXPECTED_BASE_CASE_IDS),
        "bodyfit_ids": sorted(bodyfit_by_id),
    }


def case_for_id(manifest: dict, case_id: str) -> dict:
    matches = [case for case in manifest["cases"] if case.get("case_id") == case_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one manifest case {case_id}, found {len(matches)}")
    return matches[0]


def base_case_for_sex(manifest: dict, sex: str) -> dict:
    expected_case_id = EXPECTED_BASE_CASE_IDS.get(sex)
    if expected_case_id is None:
        raise ValueError(f"Unsupported sex: {sex}")
    matches = [
        case
        for case in manifest["cases"]
        if case.get("case_role") == "base_body"
        and case.get("sex") == sex
        and case.get("case_id") == expected_case_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one base case {expected_case_id} for {sex}, found {len(matches)}"
        )
    return matches[0]


def case_destinations(bodyfit_id: str, case_id: str) -> dict:
    """Build all project asset paths for one bounded case."""
    if not SEGMENT_PATTERN.fullmatch(bodyfit_id):
        raise ValueError(f"Unsafe bodyfit_id asset segment: {bodyfit_id}")
    if not SEGMENT_PATTERN.fullmatch(case_id):
        raise ValueError(f"Unsafe case_id asset segment: {case_id}")
    case_root = f"{PROJECT_ROOT}/{bodyfit_id}/Cases/{case_id}"
    modules = case_root + "/Modules"
    return {
        "case_root": case_root,
        "full_reference": case_root + "/FullReference",
        "modules": modules,
        "pipeline": modules + "/" + PIPELINE_ASSET_NAME,
    }


def destinations_for_case(case: dict) -> dict:
    root = case.get("ue_case_root")
    if root is not None:
        segments = root.split("/") if isinstance(root, str) else []
        if (not segments or segments[0] != "" or
                not all(SEGMENT_PATTERN.fullmatch(s) for s in segments[1:]) or
                not root.startswith((PROJECT_ROOT + "/", "/Game/Vendor/Reallusion/CC5/Wardrobe/"))):
            raise ValueError(f"Unsafe explicit case root: {root}")
        return {"case_root": root, "full_reference": root + "/FullReference",
                "modules": root + "/Modules",
                "pipeline": root + "/Modules/" + PIPELINE_ASSET_NAME}
    return case_destinations(case["bodyfit_id"], case["case_id"])


def expected_case_count(manifest: dict) -> int:
    if manifest.get("import_scope") == "wardrobe_average_v1":
        count = manifest.get("counts", {}).get("case_count")
        if type(count) is not int or not 3 <= count <= 1000:
            raise ValueError("Wardrobe import requires 2 bases and 1..998 units")
        return count
    return EXPECTED_CASE_COUNT


def planned_export_paths(case: dict) -> dict[str, Path]:
    planned = case["planned_export"]
    return {key: Path(planned[key]) for key in ("fbx", "json", "project")}


def report_path(mode: str, case_id: str | None = None) -> Path:
    token = "preflight" if case_id is None else f"{case_id}_{mode}"
    return REPORT_ROOT / f"{token}.json"


def write_report(path: Path, payload: dict) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    payload["report_path"] = str(path)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def object_path(obj) -> str | None:
    return obj.get_path_name() if obj is not None else None


def object_class_name(obj) -> str:
    return obj.get_class().get_name()


def list_asset_paths(root: str) -> list[str]:
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return []
    return sorted(
        unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        )
    )


def load_assets(root: str) -> list:
    assets = []
    for asset_path in list_asset_paths(root):
        asset = unreal.load_asset(asset_path)
        if asset is None:
            raise RuntimeError(f"Unable to load asset: {asset_path}")
        assets.append(asset)
    return assets


def material_slot_keys(slot) -> list[str]:
    keys = []
    for property_name in ("material_slot_name", "imported_material_slot_name"):
        value = str(slot.get_editor_property(property_name))
        if value and value != "None" and value not in keys:
            keys.append(value)
    return keys


def material_slot_record(slot) -> dict:
    material = slot.get_editor_property("material_interface")
    return {
        "material_slot_name": str(slot.get_editor_property("material_slot_name")),
        "imported_material_slot_name": str(
            slot.get_editor_property("imported_material_slot_name")
        ),
        "material_interface": object_path(material),
        "material_class": object_class_name(material) if material else None,
    }


def skeletal_mesh_record(mesh, mesh_subsystem=None) -> dict:
    if mesh_subsystem is None:
        mesh_subsystem = unreal.get_editor_subsystem(
            unreal.SkeletalMeshEditorSubsystem
        )
    lod_error = None
    try:
        lod_count = int(mesh_subsystem.get_lod_count(mesh))
        lod0_vertices = int(mesh_subsystem.get_num_verts(mesh, 0)) if lod_count else 0
    except Exception as exc:
        lod_count = 0
        lod0_vertices = 0
        lod_error = str(exc)
    try:
        morph_names = [str(name) for name in mesh.get_all_morph_target_names()]
    except Exception:
        morph_names = [
            str(morph.get_name())
            for morph in mesh.get_editor_property("morph_targets")
        ]
    materials = [
        material_slot_record(slot)
        for slot in mesh.get_editor_property("materials")
    ]
    return {
        "name": mesh.get_name(),
        "path": mesh.get_path_name(),
        "class": object_class_name(mesh),
        "skeleton": object_path(mesh.get_editor_property("skeleton")),
        "physics_asset": object_path(mesh.get_editor_property("physics_asset")),
        "lod_count": lod_count,
        "lod0_vertices": lod0_vertices,
        "lod_error": lod_error,
        "material_slot_names": [item["material_slot_name"] for item in materials],
        "imported_material_slot_names": [
            item["imported_material_slot_name"] for item in materials
        ],
        "materials": materials,
        "morph_count": len(morph_names),
    }


def asset_record(asset, mesh_subsystem=None) -> dict:
    if isinstance(asset, unreal.SkeletalMesh):
        return skeletal_mesh_record(asset, mesh_subsystem)
    return {
        "name": asset.get_name(),
        "path": asset.get_path_name(),
        "class": object_class_name(asset),
    }


def asset_records(root: str, detailed_meshes: bool = True) -> list[dict]:
    mesh_subsystem = None
    if detailed_meshes:
        mesh_subsystem = unreal.get_editor_subsystem(
            unreal.SkeletalMeshEditorSubsystem
        )
    records = [asset_record(asset, mesh_subsystem) for asset in load_assets(root)]
    return sorted(records, key=lambda item: (item["class"], item["path"]))


def class_counts(records: list[dict]) -> dict:
    return dict(sorted(Counter(item["class"] for item in records).items()))


def skeletal_meshes_under(root: str) -> list:
    return [asset for asset in load_assets(root) if isinstance(asset, unreal.SkeletalMesh)]


def skeletons_under(root: str) -> list:
    return [asset for asset in load_assets(root) if object_class_name(asset) == "Skeleton"]


def require_source_files(case: dict, kinds: tuple[str, ...]) -> list[dict]:
    paths = planned_export_paths(case)
    checks = [
        inspect_file(paths[kind], f"{case['case_id']}.{kind}") for kind in kinds
    ]
    failed = [check for check in checks if not check["passed"]]
    if failed:
        raise RuntimeError(
            "Required export files are missing or empty: "
            + ", ".join(check["path"] for check in failed)
        )
    return checks


def refuse_overwrite(destination: str) -> None:
    existing = list_asset_paths(destination)
    if existing:
        raise RuntimeError(
            f"Refusing to overwrite non-empty destination {destination}: "
            + ", ".join(existing)
        )


def factory_probe(fbx_paths: list[Path]) -> tuple[object | None, dict]:
    result = {
        "available": False,
        "class": None,
        "formats": [],
        "can_import": {},
        "error": None,
    }
    try:
        factory = unreal.CCFbxFactory()
        result["available"] = True
        result["class"] = factory.get_class().get_path_name()
        result["formats"] = list(factory.get_editor_property("formats"))
        for path in fbx_paths:
            try:
                result["can_import"][str(path)] = bool(
                    factory.script_factory_can_import(str(path))
                )
            except Exception as exc:
                result["can_import"][str(path)] = False
                result.setdefault("probe_errors", {})[str(path)] = str(exc)
        return factory, result
    except Exception as exc:
        result["error"] = str(exc)
        return None, result


def factory_probe_ready(probe: dict) -> bool:
    """CCFbxFactory's can-import probe is advisory; actual import is authoritative."""
    formats = [str(value).casefold() for value in probe.get("formats") or []]
    return bool(
        probe.get("available")
        and probe.get("class") == "/Script/RLPlugin.CCFbxFactory"
        and any(value.startswith("fbx;") for value in formats)
    )


def build_reference_import_options(skeleton: object | None) -> object:
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
    return options


def copy_reference_import_options(source: object, target: object) -> None:
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


def configure_cc_factory_import_ui(factory: object, options: object) -> str:
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
    copy_reference_import_options(options, matches[0])
    return matches[0].get_path_name()


def register_factory_ui_enforcer(
    factory: object, options: object
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
                current_path = (
                    current_skeleton.get_path_name() if current_skeleton else None
                )
                if current_path != desired_skeleton_path:
                    copy_reference_import_options(options, candidate)
                    state["rewrite_count"] += 1
        except Exception as exc:
            state["last_error"] = str(exc)

    handle = unreal.register_slate_pre_tick_callback(enforce_factory_ui)
    return handle, state


def run_preflight(manifest: dict, manifest_summary: dict) -> dict:
    cases = []
    all_checks = []
    fbx_paths = []
    for case in manifest["cases"]:
        paths = planned_export_paths(case)
        checks = [
            inspect_file(paths[kind], f"{case['case_id']}.{kind}")
            for kind in ("fbx", "json", "project")
        ]
        all_checks.extend(checks)
        fbx_paths.append(paths["fbx"])
        cases.append(
            {
                "case_id": case["case_id"],
                "case_role": case["case_role"],
                "sex": case["sex"],
                "bodyfit_id": case["bodyfit_id"],
                "destinations": destinations_for_case(case),
                "files": checks,
                "passed": all(check["passed"] for check in checks),
            }
        )

    _, probe = factory_probe(fbx_paths)
    factory_ready = factory_probe_ready(probe)
    fbx_json_checks = [
        check
        for check in all_checks
        if check["label"].endswith((".fbx", ".json"))
    ]
    success = (
        all(case["passed"] for case in cases)
        and len(fbx_json_checks) == expected_case_count(manifest) * 2
        and all(check["sha256"] for check in fbx_json_checks)
        and factory_ready
    )
    report = {
        "schema_version": 1,
        "mode": "preflight",
        "created_at_utc": utc_now(),
        "manifest_path": str(MANIFEST_PATH),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "manifest_status": manifest.get("status"),
        "manifest_validation": manifest_summary,
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "project_root": PROJECT_ROOT,
        "expected_case_count": expected_case_count(manifest),
        "actual_case_count": len(manifest["cases"]),
        "required_base_case_ids": dict(EXPECTED_BASE_CASE_IDS),
        "actual_base_case_ids": sorted(
            case["case_id"]
            for case in manifest["cases"]
            if case["case_role"] == "base_body"
        ),
        "hash_policy": "capture_actual_sha256_no_expected_export_hashes",
        "fbx_json_hash_check_count": len(fbx_json_checks),
        "all_file_check_count": len(all_checks),
        "file_failure_count": sum(not check["passed"] for check in all_checks),
        "cc_factory_probe": probe,
        "cc_factory_ready": factory_ready,
        "can_import_probe_policy": (
            "advisory_known_false_for_reallusion_cc_fbx; "
            "post_import_structure_is_authoritative"
        ),
        "cases": cases,
        "asset_mutation_performed": False,
        "success": success,
    }
    path = write_report(report_path("preflight"), report)
    if not success:
        raise RuntimeError(f"Modular outfit preflight failed; see {path}")
    unreal.log(f"DataMake modular outfit preflight passed: {path}")
    return report


def reference_quality(records: list[dict], counts: dict) -> dict:
    meshes = [record for record in records if record["class"] == "SkeletalMesh"]
    slots = [slot for mesh in meshes for slot in mesh.get("materials", [])]
    material_paths = [
        slot["material_interface"] for slot in slots if slot["material_interface"]
    ]
    all_slots_non_null = bool(slots) and len(material_paths) == len(slots)
    all_slots_are_instances = bool(slots) and all(
        slot["material_class"] == "MaterialInstanceConstant" for slot in slots
    )
    lowered_paths = [path.casefold() for path in material_paths]
    required_hq_skin_materials = {
        marker: any(marker in path for path in lowered_paths)
        for marker in HQ_SKIN_MATERIAL_MARKERS
    }
    material_quality_passed = (
        all_slots_non_null
        and all_slots_are_instances
        and counts.get("Texture2D", 0) > 0
        and all(required_hq_skin_materials.values())
    )
    rig_asset_checks = {
        class_name: counts.get(class_name, 0) > 0
        for class_name in RIG_ASSET_CLASSES
    }
    rig_assets_passed = all(rig_asset_checks.values())
    return {
        "material_slot_count": len(slots),
        "all_material_slots_non_null": all_slots_non_null,
        "all_material_slots_are_instances": all_slots_are_instances,
        "required_hq_skin_materials": required_hq_skin_materials,
        "material_quality_passed": material_quality_passed,
        "rig_asset_checks": rig_asset_checks,
        "rig_assets_passed": rig_assets_passed,
        "requires_auto_setup": not (material_quality_passed and rig_assets_passed),
    }


def run_cleanup_case(manifest: dict, case: dict) -> dict:
    del manifest
    destination = destinations_for_case(case)["case_root"]
    if not destination.startswith(PROJECT_ROOT + "/"):
        raise RuntimeError(f"Refusing cleanup outside modular pilot root: {destination}")
    existed = unreal.EditorAssetLibrary.does_directory_exist(destination)
    assets_before = list_asset_paths(destination)
    delete_result = True
    if existed:
        delete_result = bool(
            unreal.EditorAssetLibrary.delete_directory(destination)
        )
    exists_after = unreal.EditorAssetLibrary.does_directory_exist(destination)
    report = {
        "schema_version": 1,
        "mode": "cleanup_case",
        "case_id": case["case_id"],
        "created_at_utc": utc_now(),
        "destination": destination,
        "existed_before": existed,
        "asset_count_before": len(assets_before),
        "delete_result": delete_result,
        "exists_after": exists_after,
        "success": bool(delete_result and not exists_after),
    }
    path = write_report(report_path("cleanup_case", case["case_id"]), report)
    unreal.SystemLibrary.collect_garbage()
    if not report["success"]:
        raise RuntimeError(f"Case cleanup failed; see {path}")
    return report


def run_import_reference(manifest: dict, case: dict) -> dict:
    destinations = destinations_for_case(case)
    destination = destinations["full_reference"]
    sources = planned_export_paths(case)
    source_checks = require_source_files(case, ("fbx", "json"))
    if sources["fbx"].stem.casefold() != sources["json"].stem.casefold():
        raise RuntimeError("FBX and Auto Setup JSON basenames do not match")
    refuse_overwrite(destination)

    factory, probe = factory_probe([sources["fbx"]])
    if factory is None or not factory_probe_ready(probe):
        raise RuntimeError("CCFbxFactory is unavailable or does not declare FBX support")

    requested_skeleton = None
    skeleton = None
    if case["case_role"] != "base_body":
        _base_case, skeleton, _base_destination = discover_base_skeleton(
            manifest, case["sex"]
        )
        requested_skeleton = skeleton.get_path_name()
    options = build_reference_import_options(skeleton)
    factory_import_ui_path = configure_cc_factory_import_ui(factory, options)
    enforcer_handle, enforcer_state = register_factory_ui_enforcer(
        factory, options
    )
    interactive = bool(globals().get("DM_MODULAR_INTERACTIVE", False))

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(sources["fbx"]))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", not interactive)
    task.set_editor_property("save", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("factory", factory)
    task.set_editor_property("options", options)

    unreal.log(
        f"DataMake modular outfit: importing {case['case_id']} FullReference"
    )
    import_exception = None
    try:
        try:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        except RuntimeError as exc:
            # Auto Setup can report a transient post-process skeleton error after
            # creating the complete character bundle. Structural checks below
            # remain authoritative.
            import_exception = str(exc)
    finally:
        unreal.unregister_slate_pre_tick_callback(enforcer_handle)
    unreal.EditorAssetLibrary.save_directory(
        destination, only_if_is_dirty=False, recursive=True
    )

    records = asset_records(destination)
    counts = class_counts(records)
    skeleton_paths = sorted(
        record["path"] for record in records if record["class"] == "Skeleton"
    )
    mesh_skeleton_paths = sorted(
        {
            record["skeleton"]
            for record in records
            if record["class"] == "SkeletalMesh" and record.get("skeleton")
        }
    )
    raw_import_passed = (
        counts.get("SkeletalMesh", 0) > 0 and counts.get("Skeleton", 0) > 0
    )
    quality = reference_quality(records, counts)
    imported_object_paths = list(
        task.get_editor_property("imported_object_paths") or []
    )
    report = {
        "schema_version": 1,
        "mode": "import_reference",
        "case_id": case["case_id"],
        "bodyfit_id": case["bodyfit_id"],
        "sex": case["sex"],
        "created_at_utc": utc_now(),
        "source_fbx": str(sources["fbx"]),
        "source_json": str(sources["json"]),
        "source_checks": source_checks,
        "destination": destination,
        "factory": probe,
        "interactive_import": interactive,
        "automated_import_task": not interactive,
        "requested_skeleton": requested_skeleton,
        "import_options_applied": True,
        "factory_import_ui_path": factory_import_ui_path,
        "factory_ui_enforcer_state": enforcer_state,
        "import_exception": import_exception,
        "task_imported_object_paths": [str(path) for path in imported_object_paths],
        "asset_count": len(records),
        "asset_class_counts": counts,
        "skeleton_paths": skeleton_paths,
        "skeletal_mesh_skeleton_paths": mesh_skeleton_paths,
        "assets": records,
        "raw_import_passed": raw_import_passed,
        **quality,
        "production_status": "not_approved",
        "success": raw_import_passed and not quality["requires_auto_setup"],
    }
    path = write_report(report_path("import_reference", case["case_id"]), report)
    if not report["success"]:
        raise RuntimeError(
            "FullReference import failed the Auto Setup contract; "
            f"see {path}"
        )
    unreal.log(f"DataMake FullReference import passed: {path}")
    return report


def discover_base_skeleton(manifest: dict, sex: str) -> tuple[dict, object, str]:
    base_case = base_case_for_sex(manifest, sex)
    destination = destinations_for_case(base_case)["full_reference"]
    skeletons = skeletons_under(destination)
    if len(skeletons) != 1:
        raise RuntimeError(
            f"Expected exactly one Skeleton under {destination}, found {len(skeletons)}"
        )
    return base_case, skeletons[0], destination


def configure_split_pipeline(pipeline, skeleton) -> None:
    mesh_pipeline = pipeline.get_editor_property("mesh_pipeline")
    common_skeletal = pipeline.get_editor_property(
        "common_skeletal_meshes_and_animations_properties"
    )
    animation_pipeline = pipeline.get_editor_property("animation_pipeline")
    material_pipeline = pipeline.get_editor_property("material_pipeline")
    texture_pipeline = material_pipeline.get_editor_property("texture_pipeline")

    mesh_pipeline.set_editor_property("import_skeletal_meshes", True)
    mesh_pipeline.set_editor_property("import_static_meshes", False)
    mesh_pipeline.set_editor_property(
        "combine_skeletal_meshes_behavior",
        unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE,
    )
    mesh_pipeline.set_editor_property("import_morph_targets", True)
    mesh_pipeline.set_editor_property("create_physics_asset", False)
    mesh_pipeline.set_editor_property("physics_asset", None)
    mesh_pipeline.set_editor_property(
        "skeletal_mesh_import_content_type",
        unreal.InterchangeSkeletalMeshContentType.ALL,
    )
    common_skeletal.set_editor_property("skeleton", skeleton)
    common_skeletal.set_editor_property("try_auto_select_skeleton", False)
    common_skeletal.set_editor_property("import_only_animations", False)
    animation_pipeline.set_editor_property("import_animations", False)
    material_pipeline.set_editor_property("import_materials", False)
    texture_pipeline.set_editor_property("import_textures", False)


def is_forbidden_split_asset_class(class_name: str) -> bool:
    return (
        class_name == "Skeleton"
        or class_name == "PhysicsAsset"
        or class_name.startswith("Material")
        or class_name.startswith("Texture")
        or class_name.startswith("Anim")
    )


def run_import_split(manifest: dict, case: dict) -> dict:
    destinations = destinations_for_case(case)
    destination = destinations["modules"]
    source = planned_export_paths(case)["fbx"]
    source_checks = require_source_files(case, ("fbx",))
    base_case, base_skeleton, base_destination = discover_base_skeleton(
        manifest, case["sex"]
    )
    base_skeleton_path = base_skeleton.get_path_name()
    refuse_overwrite(destination)

    pipeline = unreal.EditorAssetLibrary.duplicate_asset(
        DEFAULT_INTERCHANGE_PIPELINE, destinations["pipeline"]
    )
    if pipeline is None:
        raise RuntimeError("Unable to create the per-case Interchange pipeline asset")
    configure_split_pipeline(pipeline, base_skeleton)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        pipeline, only_if_is_dirty=False
    ):
        raise RuntimeError(
            f"Unable to save Interchange pipeline: {destinations['pipeline']}"
        )

    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
    previous_fbx_flag = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
    editor_world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    if previous_fbx_flag != 1:
        unreal.SystemLibrary.execute_console_command(editor_world, f"{fbx_cvar} 1")
    if unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar) != 1:
        raise RuntimeError(f"Unable to enable {fbx_cvar}")

    imported_objects = []
    try:
        source_data = manager.create_source_data(str(source))
        if source_data is None:
            raise RuntimeError(f"Unable to create Interchange source data: {source}")
        parameters = unreal.ImportAssetParameters()
        parameters.set_editor_property("is_automated", True)
        parameters.set_editor_property("force_show_dialog", False)
        parameters.set_editor_property("replace_existing", False)
        parameters.set_editor_property(
            "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
        )
        unreal.log(
            f"DataMake modular outfit: importing {case['case_id']} split modules"
        )
        imported_objects = manager.import_asset(
            destination, source_data, parameters
        ) or []
    finally:
        if previous_fbx_flag != 1:
            unreal.SystemLibrary.execute_console_command(
                editor_world, f"{fbx_cvar} {previous_fbx_flag}"
            )

    unreal.EditorAssetLibrary.save_directory(
        destination, only_if_is_dirty=False, recursive=True
    )
    records = asset_records(destination)
    counts = class_counts(records)
    meshes = [record for record in records if record["class"] == "SkeletalMesh"]
    empty_meshes = [
        record["path"] for record in meshes if record["lod0_vertices"] <= 0
    ]
    skeleton_mismatches = [
        {
            "mesh": record["path"],
            "actual_skeleton": record["skeleton"],
            "expected_skeleton": base_skeleton_path,
        }
        for record in meshes
        if record["skeleton"] != base_skeleton_path
    ]
    physics_asset_violations = [
        record["path"] for record in meshes if record["physics_asset"] is not None
    ]
    forbidden_assets = [
        record
        for record in records
        if is_forbidden_split_asset_class(record["class"])
    ]
    success = (
        bool(meshes)
        and not empty_meshes
        and not skeleton_mismatches
        and not physics_asset_violations
        and not forbidden_assets
    )
    report = {
        "schema_version": 1,
        "mode": "import_split",
        "case_id": case["case_id"],
        "bodyfit_id": case["bodyfit_id"],
        "sex": case["sex"],
        "created_at_utc": utc_now(),
        "source_fbx": str(source),
        "source_checks": source_checks,
        "destination": destination,
        "pipeline": pipeline.get_path_name(),
        "base_case_id": base_case["case_id"],
        "base_full_reference_destination": base_destination,
        "base_skeleton": base_skeleton_path,
        "settings": {
            "combine_skeletal_meshes": "DO_NOT_COMBINE",
            "import_morph_targets": True,
            "import_materials": False,
            "import_textures": False,
            "import_animations": False,
            "create_physics_asset": False,
        },
        "import_return_objects": [
            asset_record(obj) for obj in imported_objects if obj is not None
        ],
        "asset_class_counts": counts,
        "mesh_count": len(meshes),
        "meshes": meshes,
        "empty_meshes": empty_meshes,
        "skeleton_mismatches": skeleton_mismatches,
        "physics_asset_violations": physics_asset_violations,
        "forbidden_destination_assets": forbidden_assets,
        "destination_assets": records,
        "success": success,
    }
    path = write_report(report_path("import_split", case["case_id"]), report)
    if not success:
        raise RuntimeError(f"Split import failed validation; see {path}")
    unreal.log(f"DataMake split import passed: {path}")
    return report


def build_source_material_index(source_meshes: list) -> tuple[dict, list[dict]]:
    index = {}
    source_slots = []
    for mesh in source_meshes:
        for slot_index, slot in enumerate(mesh.get_editor_property("materials")):
            material = slot.get_editor_property("material_interface")
            record = {
                "mesh": mesh.get_path_name(),
                "slot_index": slot_index,
                "keys": material_slot_keys(slot),
                "material": object_path(material),
            }
            source_slots.append(record)
            if material is None:
                continue
            candidate = {**record, "material_object": material}
            for key in record["keys"]:
                index.setdefault(key, []).append(candidate)
    return index, source_slots


def run_apply_materials(manifest: dict, case: dict) -> dict:
    destinations = destinations_for_case(case)
    source_meshes = skeletal_meshes_under(destinations["full_reference"])
    target_meshes = skeletal_meshes_under(destinations["modules"])
    base_case, base_skeleton, base_destination = discover_base_skeleton(
        manifest, case["sex"]
    )
    expected_skeleton = base_skeleton.get_path_name()
    source_index, source_slots = build_source_material_index(source_meshes)

    unmatched = []
    ambiguous = []
    skeleton_mismatches = []
    planned_assignments = []
    for mesh in target_meshes:
        actual_skeleton = object_path(mesh.get_editor_property("skeleton"))
        if actual_skeleton != expected_skeleton:
            skeleton_mismatches.append(
                {
                    "mesh": mesh.get_path_name(),
                    "actual_skeleton": actual_skeleton,
                    "expected_skeleton": expected_skeleton,
                }
            )
        slots = list(mesh.get_editor_property("materials"))
        if not slots:
            unmatched.append(
                {"mesh": mesh.get_path_name(), "reason": "no_material_slots"}
            )
            continue
        mesh_assignments = []
        for slot_index, slot in enumerate(slots):
            keys = material_slot_keys(slot)
            candidates_by_path = {}
            for key in keys:
                for candidate in source_index.get(key, []):
                    candidates_by_path[candidate["material"]] = candidate
            candidates = list(candidates_by_path.values())
            if not candidates:
                unmatched.append(
                    {
                        "mesh": mesh.get_path_name(),
                        "slot_index": slot_index,
                        "keys": keys,
                    }
                )
                continue
            if len(candidates) != 1:
                ambiguous.append(
                    {
                        "mesh": mesh.get_path_name(),
                        "slot_index": slot_index,
                        "keys": keys,
                        "candidate_materials": sorted(candidates_by_path),
                    }
                )
                continue
            candidate = candidates[0]
            mesh_assignments.append(
                {
                    "slot_index": slot_index,
                    "target_keys": keys,
                    "material": candidate["material"],
                    "material_object": candidate["material_object"],
                    "source_mesh": candidate["mesh"],
                    "source_slot_index": candidate["slot_index"],
                    "matched_keys": sorted(set(keys) & set(candidate["keys"])),
                }
            )
        planned_assignments.append((mesh, slots, mesh_assignments))

    preconditions_passed = (
        bool(source_meshes)
        and bool(target_meshes)
        and not unmatched
        and not ambiguous
        and not skeleton_mismatches
    )
    report = {
        "schema_version": 1,
        "mode": "apply_materials",
        "case_id": case["case_id"],
        "bodyfit_id": case["bodyfit_id"],
        "sex": case["sex"],
        "created_at_utc": utc_now(),
        "full_reference_destination": destinations["full_reference"],
        "modules_destination": destinations["modules"],
        "base_case_id": base_case["case_id"],
        "base_full_reference_destination": base_destination,
        "base_skeleton": expected_skeleton,
        "source_mesh_count": len(source_meshes),
        "source_material_slots": source_slots,
        "source_material_key_count": len(source_index),
        "target_mesh_count": len(target_meshes),
        "unmatched_slots": unmatched,
        "ambiguous_slots": ambiguous,
        "skeleton_mismatches": skeleton_mismatches,
        "assignments": [],
        "success": False,
    }
    path = report_path("apply_materials", case["case_id"])
    if not preconditions_passed:
        write_report(path, report)
        raise RuntimeError(f"Material assignment preconditions failed; see {path}")

    assignment_records = []
    for mesh, slots, assignments in planned_assignments:
        serialized_assignments = []
        for assignment in assignments:
            slots[assignment["slot_index"]].set_editor_property(
                "material_interface", assignment["material_object"]
            )
            serialized_assignments.append(
                {
                    key: value
                    for key, value in assignment.items()
                    if key != "material_object"
                }
            )
        mesh.set_editor_property("materials", slots)
        mesh.set_editor_property("physics_asset", None)
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            mesh, only_if_is_dirty=False
        ):
            raise RuntimeError(f"Unable to save split mesh: {mesh.get_path_name()}")
        assignment_records.append(
            {
                "mesh": mesh.get_path_name(),
                "physics_asset": None,
                "slots": serialized_assignments,
            }
        )

    report["assignments"] = assignment_records
    report["assigned_slot_count"] = sum(
        len(record["slots"]) for record in assignment_records
    )
    report["success"] = True
    write_report(path, report)
    unreal.log(f"DataMake split material assignment passed: {path}")
    return report


def run_validate_case(manifest: dict, case: dict) -> dict:
    destinations = destinations_for_case(case)
    full_records = asset_records(destinations["full_reference"])
    split_records = asset_records(destinations["modules"])
    full_counts = class_counts(full_records)
    split_counts = class_counts(split_records)
    split_meshes = [
        record for record in split_records if record["class"] == "SkeletalMesh"
    ]

    base_error = None
    base_case = None
    base_destination = None
    expected_skeleton = None
    try:
        base_case, base_skeleton, base_destination = discover_base_skeleton(
            manifest, case["sex"]
        )
        expected_skeleton = base_skeleton.get_path_name()
    except Exception as exc:
        base_error = str(exc)

    skeleton_mismatches = [
        {
            "mesh": record["path"],
            "actual_skeleton": record["skeleton"],
            "expected_skeleton": expected_skeleton,
        }
        for record in split_meshes
        if expected_skeleton is None or record["skeleton"] != expected_skeleton
    ]
    empty_meshes = [
        record["path"] for record in split_meshes if record["lod0_vertices"] <= 0
    ]
    material_failures = []
    for record in split_meshes:
        materials = record.get("materials", [])
        null_slots = [
            index
            for index, slot in enumerate(materials)
            if slot["material_interface"] is None
        ]
        if not materials or null_slots:
            material_failures.append(
                {
                    "mesh": record["path"],
                    "material_slot_count": len(materials),
                    "null_slot_indices": null_slots,
                }
            )

    assertions = {
        "full_reference_has_skeletal_mesh": full_counts.get("SkeletalMesh", 0) > 0,
        "full_reference_has_skeleton": full_counts.get("Skeleton", 0) > 0,
        "base_skeleton_is_unique": base_error is None,
        "split_has_skeletal_mesh": bool(split_meshes),
        "all_split_meshes_use_base_skeleton": not skeleton_mismatches,
        "all_split_meshes_have_nonempty_lod0": not empty_meshes,
        "all_split_material_interfaces_are_non_null": not material_failures,
    }
    success = all(assertions.values())
    report = {
        "schema_version": 1,
        "mode": "validate_case",
        "case_id": case["case_id"],
        "bodyfit_id": case["bodyfit_id"],
        "sex": case["sex"],
        "created_at_utc": utc_now(),
        "full_reference_destination": destinations["full_reference"],
        "modules_destination": destinations["modules"],
        "base_case_id": base_case["case_id"] if base_case else None,
        "base_full_reference_destination": base_destination,
        "base_skeleton": expected_skeleton,
        "base_skeleton_error": base_error,
        "full_reference_asset_class_counts": full_counts,
        "split_asset_class_counts": split_counts,
        "full_reference_assets": full_records,
        "split_assets": split_records,
        "split_mesh_count": len(split_meshes),
        "skeleton_mismatches": skeleton_mismatches,
        "empty_meshes": empty_meshes,
        "material_failures": material_failures,
        "assertions": assertions,
        "validation_scope": [
            "asset_inventory",
            "base_skeleton_binding",
            "lod0_vertex_presence",
            "material_interface_presence",
        ],
        "not_evaluated": [
            "apparel_classification",
            "runtime_switching",
        ],
        "success": success,
    }
    path = write_report(report_path("validate_case", case["case_id"]), report)
    if not success:
        raise RuntimeError(f"Case validation failed; see {path}")
    unreal.log(f"DataMake modular outfit case validation passed: {path}")
    return report


def require_case_id(mode: str) -> str:
    value = globals().get("DM_MODULAR_CASE_ID")
    if not isinstance(value, str) or not value:
        raise ValueError(f"DM_MODULAR_CASE_ID is required for mode {mode}")
    if not SEGMENT_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe DM_MODULAR_CASE_ID: {value}")
    return value


def error_report_name(mode: str, case_id: str | None) -> Path:
    safe_mode = re.sub(r"[^A-Za-z0-9_]+", "_", str(mode)).strip("_") or "unknown"
    safe_case = (
        re.sub(r"[^A-Za-z0-9_]+", "_", str(case_id)).strip("_")
        if case_id
        else "global"
    )
    return REPORT_ROOT / f"{safe_case}_{safe_mode}_error.json"


def collect_after_wardrobe_import(manifest: dict, mode: str) -> bool:
    if (manifest.get("import_scope") != "wardrobe_average_v1"
            or mode not in {"import_reference", "import_split"}):
        return False
    gc.collect()
    unreal.SystemLibrary.collect_garbage()
    return True


def main() -> dict:
    mode = globals().get("DM_MODULAR_MODE", "preflight")
    case_id = globals().get("DM_MODULAR_CASE_ID")
    try:
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported DM_MODULAR_MODE: {mode}")
        # Main also runs directly through UE Remote Execution, so enforce the
        # retired fixed input here as well as in the host selector. Imports
        # and shared validation/classification helpers remain unchanged.
        if MANIFEST_PATH.resolve() == LEGACY_PILOT_MANIFEST_PATH.resolve():
            if mode == "preflight" or case_id not in {"M_BASE", "F_BASE"}:
                raise RuntimeError(
                    "Retired 14-case modular outfit pilot execution. Set an "
                    "explicit current DM_MODULAR_MANIFEST_PATH; legacy recovery "
                    "requires DM_MODULAR_CASE_ID=M_BASE/F_BASE and cannot run "
                    "global preflight."
                )
        if not MANIFEST_PATH.is_file():
            raise FileNotFoundError(str(MANIFEST_PATH))
        manifest = read_json(MANIFEST_PATH)
        manifest_summary = validate_manifest(manifest)
        if mode == "preflight":
            result = run_preflight(manifest, manifest_summary)
        else:
            case_id = require_case_id(mode)
            case = case_for_id(manifest, case_id)
            if mode == "cleanup_case":
                result = run_cleanup_case(manifest, case)
            elif mode == "import_reference":
                result = run_import_reference(manifest, case)
            elif mode == "import_split":
                result = run_import_split(manifest, case)
            elif mode == "apply_materials":
                result = run_apply_materials(manifest, case)
            else:
                result = run_validate_case(manifest, case)
        if collect_after_wardrobe_import(manifest, mode):
            result["post_import_gc_requested"] = True
            write_report(Path(result["report_path"]), result)
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "mode": mode,
            "case_id": case_id,
            "created_at_utc": utc_now(),
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        failure_path = write_report(error_report_name(mode, case_id), failure)
        unreal.log_error(
            f"DataMake modular outfit operation failed; see {failure_path}: {exc}"
        )
        print(
            "DM_MODULAR_RESULT="
            + json.dumps(failure, ensure_ascii=False, sort_keys=True)
        )
        raise

    summary = {
        "mode": mode,
        "case_id": case_id,
        "success": result["success"],
        "report_path": result["report_path"],
    }
    print("DM_MODULAR_RESULT=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return result


if globals().get("__name__") == "__main__" or "DM_MODULAR_MODE" in globals():
    main()
