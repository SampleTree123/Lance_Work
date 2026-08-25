"""Audit the frozen First Batch render assets in the running Unreal Editor."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work")
REQUIRED_EXPORTS = (
    ROOT
    / "00_engine"
    / "scripts"
    / "dataset"
    / "first_batch_required_exports_20260824_v3.json"
)
OUTPUT = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_render_audit_20260824_v1"
    / "render_asset_audit.json"
)
FEMALE_CANONICAL_SKELETON = (
    "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/F_ID01_O01/"
    "CC_FB_F_ID01_O01_Skeleton"
)
MALE_CANONICAL_SKELETON = (
    "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/M_ID01_O01/"
    "CC_FB_M_ID01_O01_Skeleton"
)


def object_path(package_path: str) -> str:
    return f"{package_path}.{package_path.rsplit('/', 1)[-1]}"


def asset_class(asset) -> str | None:
    return asset.get_class().get_name() if asset is not None else None


def skeleton_path(asset) -> str | None:
    if asset is None:
        return None
    skeleton = asset.get_editor_property("skeleton")
    return skeleton.get_path_name().split(".", 1)[0] if skeleton is not None else None


source = json.loads(REQUIRED_EXPORTS.read_text(encoding="utf-8-sig"))
look_rows = []
for record in source["full_reference_looks"]:
    look_id = record["look_id"]
    folder = record["expected_unreal_folder"]
    stem = f"CC_FB_{look_id}"
    mesh_package = f"{folder}/{stem}"
    skeleton_package = f"{folder}/{stem}_Skeleton"
    blueprint_package = f"{folder}/{stem}_Blueprint_LiveLink"
    mesh = unreal.load_asset(mesh_package)
    skeleton = unreal.load_asset(skeleton_package)
    blueprint = unreal.load_asset(blueprint_package)
    observed_skeleton = skeleton_path(mesh)
    canonical = (
        FEMALE_CANONICAL_SKELETON
        if record["sex"] == "female"
        else MALE_CANONICAL_SKELETON
    )
    look_rows.append(
        {
            "look_id": look_id,
            "sex": record["sex"],
            "folder": folder,
            "mesh": mesh_package,
            "mesh_class": asset_class(mesh),
            "skeleton": skeleton_package,
            "skeleton_class": asset_class(skeleton),
            "mesh_skeleton": observed_skeleton,
            "blueprint": blueprint_package,
            "blueprint_class": asset_class(blueprint),
            "generated_class": object_path(blueprint_package) + "_C",
            "canonical_animation_skeleton": canonical,
            "uses_canonical_skeleton": observed_skeleton == canonical,
            # Later Looks intentionally reuse the first imported Skeleton for
            # their sex, so an individual sibling Skeleton asset is optional.
            "assets_present": (
                mesh is not None
                and blueprint is not None
                and observed_skeleton == canonical
            ),
        }
    )

active_pool = json.loads(
    (
        ROOT
        / "00_engine"
        / "scripts"
        / "character_creator"
        / "cc_first_batch_action_pool_20260824_v1.json"
    ).read_text(encoding="utf-8-sig")
)
motion_rows = []
for sex in ("female", "male"):
    sex_folder = "Female" if sex == "female" else "Male"
    canonical = (
        FEMALE_CANONICAL_SKELETON if sex == "female" else MALE_CANONICAL_SKELETON
    )
    for action_id in active_pool["active_actions"][sex]:
        slug = action_id.removeprefix("ACT_")
        actor_id = slug.split("_", 1)[0]
        body = (
            f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
            f"BodyOnly/A_DM_{slug}_BodyOnly_v001"
        )
        if action_id == "ACT_F02_CATCH_BREATH":
            body = (
                "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/"
                "InPlaceCandidates/A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001"
            )
        body_asset = unreal.load_asset(body)
        composites = {}
        for expression in ("happy", "angry", "sad"):
            path = (
                f"/Game/DataMake/Animations/CC5/FirstDataBatch/{sex_folder}/"
                f"Composites/{actor_id}/A_DM_{slug}_{expression.title()}_Composite_v001"
            )
            asset = unreal.load_asset(path)
            composites[expression] = {
                "asset": path,
                "present": isinstance(asset, unreal.AnimSequence),
                "skeleton": skeleton_path(asset),
            }
        motion_rows.append(
            {
                "action_id": action_id,
                "sex": sex,
                "body_asset": body,
                "body_present": isinstance(body_asset, unreal.AnimSequence),
                "body_skeleton": skeleton_path(body_asset),
                "canonical_animation_skeleton": canonical,
                "composites": composites,
            }
        )

report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed" if all(row["assets_present"] for row in look_rows) else "failed",
    "required_exports": str(REQUIRED_EXPORTS),
    "counts": {
        "looks": len(look_rows),
        "looks_present": sum(row["assets_present"] for row in look_rows),
        "unique_look_skeletons": len({row["mesh_skeleton"] for row in look_rows}),
        "actions": len(motion_rows),
        "body_assets_present": sum(row["body_present"] for row in motion_rows),
        "composites_present": sum(
            value["present"]
            for row in motion_rows
            for value in row["composites"].values()
        ),
    },
    "looks": look_rows,
    "motions": motion_rows,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    "DM_FIRST_BATCH_RENDER_ASSET_AUDIT="
    + json.dumps(
        {
            "status": report["status"],
            "report": str(OUTPUT),
            "counts": report["counts"],
        },
        ensure_ascii=False,
    )
)
