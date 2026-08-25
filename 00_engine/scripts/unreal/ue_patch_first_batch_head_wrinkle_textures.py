"""Audit, patch, or restore missing wrinkle textures on first-batch head materials."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

import unreal


LOOK_ROOT = "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks"
LOOK_PATTERN = re.compile(r"/CC_FB_[FM]_ID\d{2}_O\d{2}$")
TEXTURE_ROOT = (
    "/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/Materials/"
    "CC_M02_Average_Pilot_UE58/textures/"
)
FIX_TEXTURES = {
    "CM1": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Diffuse1",
    "CM2": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Diffuse2",
    "CM3": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Diffuse3",
    "WM1": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Normal1",
    "WM2": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Normal2",
    "WM3": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Normal3",
    "RM1": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Roughness1",
    "RM2": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Roughness2",
    "RM3": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Roughness3",
    "HM1_Flow": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Flow1",
    "HM2_Flow": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Flow2",
    "HM3_Flow": TEXTURE_ROOT + "Std_Skin_Head_Wrinkle_Flow3",
    "NormalMap_Blend": TEXTURE_ROOT + "Std_Skin_Head_NBMap",
}
OUTPUT_DIR = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\diagnostics"
)
BACKUP_PATH = OUTPUT_DIR / "first_batch_head_wrinkle_texture_backup.json"
REPORT_PATH = OUTPUT_DIR / "first_batch_head_wrinkle_texture_patch.json"
MODE = str(globals().get("DM_MODE", "audit")).lower()
if MODE not in {"audit", "apply", "restore"}:
    raise RuntimeError(f"Unsupported DM_MODE: {MODE}")


def object_path(value):
    return value.get_path_name() if value is not None else None


def read_parameters(material):
    return {
        name: object_path(
            unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
                material, name
            )
        )
        for name in FIX_TEXTURES
    }


def find_head_material(mesh):
    for index, slot in enumerate(mesh.get_editor_property("materials")):
        slot_name = str(slot.get_editor_property("material_slot_name"))
        if "std_skin_head" not in slot_name.lower():
            continue
        material = slot.get_editor_property("material_interface")
        if not isinstance(material, unreal.MaterialInstanceConstant):
            raise RuntimeError(
                f"Head material is not a MIC: {mesh.get_path_name()} slot {index}"
            )
        return index, slot_name, material
    raise RuntimeError(f"Head material not found: {mesh.get_path_name()}")


assets = sorted(
    path
    for path in unreal.EditorAssetLibrary.list_assets(
        LOOK_ROOT, recursive=True, include_folder=False
    )
    if LOOK_PATTERN.search(path.split(".", 1)[0])
)
if len(assets) != 32:
    raise RuntimeError(f"Expected 32 first-batch look meshes, found {len(assets)}")

targets = {}
for parameter, texture_path in FIX_TEXTURES.items():
    texture = unreal.load_asset(texture_path)
    if texture is None:
        raise RuntimeError(f"Missing fix texture: {texture_path}")
    targets[parameter] = texture

backup = None
if MODE == "restore":
    if not BACKUP_PATH.is_file():
        raise RuntimeError(f"Missing backup: {BACKUP_PATH}")
    backup = json.loads(BACKUP_PATH.read_text(encoding="utf-8"))
    backup = {record["mesh"]: record for record in backup["records"]}

records = []
for asset_path in assets:
    mesh = unreal.load_asset(asset_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"Invalid skeletal mesh: {asset_path}")
    slot_index, slot_name, material = find_head_material(mesh)
    before = read_parameters(material)

    if MODE == "apply":
        requested = {name: texture for name, texture in targets.items()}
    elif MODE == "restore":
        source = backup.get(mesh.get_path_name())
        if source is None:
            raise RuntimeError(f"Mesh missing from backup: {mesh.get_path_name()}")
        requested = {}
        for name, texture_path in source["before"].items():
            texture = unreal.load_asset(texture_path) if texture_path else None
            if texture_path and texture is None:
                raise RuntimeError(f"Missing backup texture: {texture_path}")
            requested[name] = texture
    else:
        requested = {}

    if requested:
        for name, texture in requested.items():
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                material, name, texture
            )
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            material, only_if_is_dirty=False
        ):
            raise RuntimeError(f"Unable to save material: {material.get_path_name()}")

    after = read_parameters(material)
    expected = (
        {name: texture.get_path_name() for name, texture in requested.items()}
        if requested
        else before
    )
    checks = {
        "all_parameters_present": all(after.get(name) for name in FIX_TEXTURES),
        "requested_values_match": all(
            after.get(name) == expected.get(name) for name in expected
        ),
        "uses_placeholder_after": any(
            path and "/CC_Shaders/SkinShader/Textures/Share/" in path
            for path in after.values()
        ),
    }
    records.append(
        {
            "mesh": mesh.get_path_name(),
            "head_slot": slot_index,
            "head_slot_name": slot_name,
            "material": material.get_path_name(),
            "before": before,
            "after": after,
            "checks": checks,
        }
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if MODE == "apply" and not BACKUP_PATH.exists():
    BACKUP_PATH.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

success = all(record["checks"]["requested_values_match"] for record in records)
if MODE == "apply":
    success = success and not any(
        record["checks"]["uses_placeholder_after"] for record in records
    )
report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "mode": MODE,
    "look_count": len(records),
    "texture_parameter_count": len(FIX_TEXTURES),
    "backup": str(BACKUP_PATH),
    "records": records,
    "success": success,
}
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
if not success:
    raise RuntimeError(f"First-batch wrinkle texture {MODE} failed: {REPORT_PATH}")
print(
    "DM_FIRST_BATCH_WRINKLE_TEXTURE_PATCH="
    + json.dumps(
        {
            "mode": MODE,
            "look_count": len(records),
            "texture_parameter_count": len(FIX_TEXTURES),
            "report": str(REPORT_PATH),
            "backup": str(BACKUP_PATH),
            "success": success,
        },
        ensure_ascii=False,
    )
)
