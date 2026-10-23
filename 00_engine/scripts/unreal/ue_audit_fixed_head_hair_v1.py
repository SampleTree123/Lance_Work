"""Read-only final audit: load all 80 fits through the published UE index.

No rendering, animation, full-library visual review, or source asset edits.
Run after all imports and build_fixed_head_hair_registry_v1.py succeed.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timezone
import unreal

REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "00_engine/outputs/unreal_character_import/fixed_head_hair_20261004_v1"
UE_ROOT = "/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1"
REGISTRY = Path(globals().get("DM_FIXED_HAIR_REGISTRY", REPO /
    "00_engine/assets/character_creator/wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json"))


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def package(path):
    return path.split(".", 1)[0]


def path(asset):
    return asset.get_path_name() if asset is not None else None


def final_audit():
    worker = REPO / "00_engine/scripts/unreal/formal_wardrobe_registry_v1.py"
    spec = importlib.util.spec_from_file_location("dm_fixed_hair_index_contract", worker)
    formal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(formal)
    index = formal.read_registry(REGISTRY)
    report = read(ROOT / "import_report.json")
    if report.get("success") is not True or report.get("complete") is not True:
        raise RuntimeError("Full successful import report required")
    if len(index["hair_assets"]) != 40:
        raise RuntimeError("Expected the retained 40 hairstyles")
    rows = report["records"]
    expected = {(h["hair_id"], sex) for h in index["hair_assets"] for sex in ("female", "male")}
    by_pair = {(r["hair_id"], r["sex"]): r for r in rows}
    if len(rows) != 80 or set(by_pair) != expected:
        raise RuntimeError("Import coverage must be exactly 40 x 2")
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    asset_data = registry.get_assets_by_path(UE_ROOT, recursive=True)
    asset_classes = {}
    for data in asset_data:
        object_name = str(data.package_name) + "." + str(data.asset_name)
        asset_classes.setdefault(str(data.asset_class_path.asset_name), set()).add(object_name)
    expected_skeletons = {r["skeleton_path"] for r in rows}
    if len(expected_skeletons) != 2 or asset_classes.get("Skeleton", set()) != expected_skeletons:
        raise RuntimeError("New batch must contain exactly two shared Skeleton assets")
    for skeleton in expected_skeletons:
        if not isinstance(unreal.load_asset(skeleton), unreal.Skeleton):
            raise RuntimeError("Shared Skeleton does not load: " + skeleton)
    expected_meshes = {m["path"] for r in rows for m in r["meshes"]}
    expected_meshes.update(m["path"] for r in report["bases"].values() for m in r["meshes"])
    if asset_classes.get("SkeletalMesh", set()) != expected_meshes:
        raise RuntimeError("Unexpected/missing SkeletalMesh: duplicate complete-avatar modules may remain")
    if any(str(data.package_name).startswith(UE_ROOT + "/_Staging/") for data in asset_data):
        raise RuntimeError("Staging packages remain in the Asset Registry")
    physical = Path(unreal.Paths.project_content_dir()) / UE_ROOT.removeprefix("/Game/") / "_Staging"
    if physical.exists() and any(physical.rglob("*.uasset")):
        raise RuntimeError("Staging asset files remain on disk")
    zero_path = UE_ROOT + "/Shared/Materials/M_Coverage_ZeroMask.M_Coverage_ZeroMask"
    zero = unreal.load_asset(zero_path)
    if not isinstance(zero, unreal.Material) or zero.get_editor_property("blend_mode") != unreal.BlendMode.BLEND_MASKED:
        raise RuntimeError("Persisted zero-mask coverage material is missing")
    expression = unreal.MaterialEditingLibrary.get_material_property_input_node(zero, unreal.MaterialProperty.MP_OPACITY_MASK)
    if not isinstance(expression, unreal.MaterialExpressionConstant) or expression.get_editor_property("r") != 0.:
        raise RuntimeError("Coverage material must connect a constant zero to Opacity Mask")
    checked = []
    material_paths, texture_paths = set(), set()
    hidden_count = 0
    for hair in index["hair_assets"]:
        for sex in ("female", "male"):
            fit = formal.hair_fit(hair, sex)
            imported = by_pair[(hair["hair_id"], sex)]
            if fit["skeleton_path"] != imported["skeleton_path"]:
                raise RuntimeError("Index chose wrong fit Skeleton")
            hidden = {(r["mesh"].split(".", 1)[0], r["slot_index"]) for r in imported["coverage_hidden_slots"]}
            seen_hidden = set()
            for item in fit["meshes"]:
                mesh = unreal.load_asset(item["path"])
                if not isinstance(mesh, unreal.SkeletalMesh):
                    raise RuntimeError("Indexed hair does not load " + item["path"])
                if path(mesh.get_editor_property("skeleton")) != fit["skeleton_path"]:
                    raise RuntimeError("Indexed hair uses wrong shared Skeleton")
                slots = list(mesh.get_editor_property("materials"))
                actual = [path(s.get_editor_property("material_interface")) for s in slots]
                if actual != item["materials"]:
                    raise RuntimeError("Index material binding differs from saved mesh")
                for number, slot in enumerate(slots):
                    material = slot.get_editor_property("material_interface")
                    if material is None or package(path(material)).startswith(UE_ROOT + "/_Staging/"):
                        raise RuntimeError("Hair material is missing or references staging")
                    key = (package(item["path"]), number)
                    if key in hidden:
                        if path(material) != zero_path:
                            raise RuntimeError("Approved coverage slot did not retain zero-mask binding")
                        seen_hidden.add(key)
                    material_paths.add(path(material))
                    if isinstance(material, unreal.MaterialInstanceConstant):
                        parent = material.get_editor_property("parent")
                        if parent is None or package(path(parent)).startswith(UE_ROOT + "/_Staging/"):
                            raise RuntimeError("Hair instance retains a bad parent")
                        for parameter in material.get_editor_property("texture_parameter_values") or []:
                            texture = parameter.get_editor_property("parameter_value")
                            if texture is None:
                                continue
                            if package(path(texture)).startswith(UE_ROOT + "/_Staging/"):
                                raise RuntimeError("Hair texture retains a staging reference")
                            texture_paths.add(path(texture))
            if seen_hidden != hidden:
                raise RuntimeError("Coverage slot mapping missing from indexed meshes")
            hidden_count += len(hidden)
            checked.append({"hair_id": hair["hair_id"], "sex": sex,
                "mesh_count": len(fit["meshes"]), "hidden_coverage_slots": len(hidden), "loaded": True})
    if hidden_count != 142:
        raise RuntimeError("Expected 71 approved coverage slots per fit source")
    return {"schema_version": 1, "success": True, "batch_id": report["batch_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "registry": str(REGISTRY),
        "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "cases_loaded": len(checked), "hair_meshes_loaded": len(expected_meshes) - 2,
        "shared_skeletons": sorted(expected_skeletons), "shared_base_meshes": 2,
        "hidden_coverage_slots": hidden_count, "staging_packages": 0,
        "unique_materials": len(material_paths), "unique_textures": len(texture_paths), "cases": checked,
        "scope": "All 80 variants load through the published index; minimal structural/runtime support check only"}


try:
    result = final_audit()
except Exception as exc:
    result = {"success": False, "error": str(exc), "created_at_utc": datetime.now(timezone.utc).isoformat()}
    (ROOT / "final_runtime_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise
else:
    (ROOT / "final_runtime_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log("Fixed head hair final runtime audit passed: 80 variants / 2 shared Skeletons / no staging")
