#!/usr/bin/env python3
"""Build a deterministic CC outfit compatibility gate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


TARGET_BODYFITS = {
    "female": ["F01_Lean", "F04_Heavy", "F05_Short_Average"],
    "male": ["M01_Lean", "M04_Heavy", "M05_Short_Average"],
}
BASE_AVATAR_BY_SEX = {
    "female": r"D:\CharacterCreator_sucai\Reallusion Templates\Actor\Character\_Mixer Ready\Base\_HD Neutral F.ccAvatar",
    "male": r"D:\CharacterCreator_sucai\Reallusion Templates\Actor\Character\_Mixer Ready\Base\_HD Neutral M.ccAvatar",
}
FULL_BODY_CAMERA = (
    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera\Headshot Ref\Ref Cam Male L.ccCam"
)
PREVIEW_LIGHTROOM = (
    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Light Room\Default\Default_CC5.ccLightroom"
)
CAPTURE_VIEWS = [
    {"view_id": "front", "yaw_degrees": 0.0},
    {"view_id": "front_three_quarter", "yaw_degrees": 45.0},
    {"view_id": "left_profile", "yaw_degrees": 90.0},
    {"view_id": "rear", "yaw_degrees": 180.0},
    {"view_id": "right_profile", "yaw_degrees": -90.0},
]
SLOT_LOAD_ORDER = {
    "full_body": 10,
    "pants": 20,
    "skirts": 20,
    "shirts": 30,
    "coats": 40,
    "family_accessory": 50,
    "shoes": 60,
}
DEFAULT_COMPATIBILITY_ALIAS_REGISTRY = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "character_creator"
    / "outfit_compatibility_aliases"
    / "compatibility_alias_registry.json"
)


class OutfitGateError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OutfitGateError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_compatibility_alias_registry(
    registry_path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    registry_path = registry_path.resolve()
    registry = read_json(registry_path)
    if registry.get("schema_version") != 1:
        raise OutfitGateError(
            f"Unsupported compatibility alias registry: {registry_path}"
        )
    policy = registry.get("policy") or {}
    if (
        policy.get("byte_identity_required") is not True
        or policy.get("source_assets_remain_immutable") is not True
        or policy.get("allowed_transform")
        != "extension_dispatch_alias_only"
    ):
        raise OutfitGateError(
            f"Unsafe compatibility alias policy: {registry_path}"
        )

    aliases_by_source_sha: dict[str, dict[str, Any]] = {}
    for entry in registry.get("aliases", []):
        if not isinstance(entry, dict):
            raise OutfitGateError(
                f"Compatibility alias entry is not an object: {registry_path}"
            )
        source = entry.get("source") or {}
        alias = entry.get("alias") or {}
        source_path = Path(source.get("path", "")).resolve()
        alias_path = Path(alias.get("path", "")).resolve()
        if not source_path.is_file() or not alias_path.is_file():
            raise OutfitGateError(
                f"Compatibility alias file is missing: {entry.get('alias_id')}"
            )
        source_sha = str(source.get("sha256", "")).lower()
        alias_sha = str(alias.get("sha256", "")).lower()
        if not source_sha or source_sha != alias_sha:
            raise OutfitGateError(
                f"Compatibility alias hashes differ: {entry.get('alias_id')}"
            )
        source_size = source_path.stat().st_size
        alias_size = alias_path.stat().st_size
        if (
            source_size != source.get("size_bytes")
            or alias_size != alias.get("size_bytes")
            or source_size != alias_size
        ):
            raise OutfitGateError(
                f"Compatibility alias sizes differ: {entry.get('alias_id')}"
            )
        if sha256_file(source_path) != source_sha:
            raise OutfitGateError(
                f"Compatibility alias source hash changed: {source_path}"
            )
        if sha256_file(alias_path) != alias_sha:
            raise OutfitGateError(
                f"Compatibility alias target hash changed: {alias_path}"
            )
        if source_sha in aliases_by_source_sha:
            raise OutfitGateError(
                f"Duplicate compatibility alias source hash: {source_sha}"
            )
        aliases_by_source_sha[source_sha] = {
            **entry,
            "source_path": source_path,
            "alias_path": alias_path,
        }

    return aliases_by_source_sha, {
        "path": str(registry_path),
        "registry_id": registry.get("registry_id"),
        "sha256": sha256_file(registry_path),
        "alias_count": len(aliases_by_source_sha),
    }


def resolve_compatibility_alias(
    source_path: Path,
    record: dict[str, Any],
    aliases_by_source_sha: dict[str, dict[str, Any]] | None,
) -> tuple[Path, dict[str, Any] | None]:
    if source_path.suffix.casefold() != ".ccgloves":
        return source_path, None
    if aliases_by_source_sha is None:
        return source_path, None

    source_sha = str(record.get("sha256", "")).lower()
    entry = aliases_by_source_sha.get(source_sha)
    if entry is None:
        raise OutfitGateError(
            f"ccGloves asset has no validated loader alias: {source_path}"
        )
    if entry["source_path"] != source_path.resolve():
        raise OutfitGateError(
            f"Compatibility alias source path mismatch: {source_path}"
        )
    if source_path.stat().st_size != record.get("size_bytes"):
        raise OutfitGateError(
            f"Compatibility alias source size changed: {source_path}"
        )
    if sha256_file(source_path) != source_sha:
        raise OutfitGateError(
            f"Compatibility alias source hash changed: {source_path}"
        )

    alias_path = entry["alias_path"]
    return alias_path, {
        "alias_id": entry["alias_id"],
        "transform": "extension_dispatch_alias_only",
        "source_path": str(source_path),
        "source_extension": source_path.suffix,
        "loader_extension": alias_path.suffix,
        "byte_identity_verified": True,
    }


def stable_choice(values: list[str], seed: int, key: str) -> str:
    if not values:
        raise OutfitGateError(f"Cannot choose from an empty pool: {key}")
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    return values[int.from_bytes(digest[:8], "big") % len(values)]


def collect_subjects(
    summary_path: Path, project_staging_root: Path | None = None
) -> list[dict[str, Any]]:
    summary = read_json(summary_path)
    if summary.get("status") != "passed":
        raise OutfitGateError("The source character showcase is not accepted")
    by_bodyfit = {
        character.get("bodyfit_id"): character
        for character in summary.get("characters", [])
    }
    subjects: list[dict[str, Any]] = []
    face_ids: set[str] = set()
    for sex in ("female", "male"):
        for bodyfit_id in TARGET_BODYFITS[sex]:
            character = by_bodyfit.get(bodyfit_id)
            if not isinstance(character, dict):
                raise OutfitGateError(f"Accepted subject is missing: {bodyfit_id}")
            if character.get("sex") != sex or character.get("age_label") != "young":
                raise OutfitGateError(f"Subject metadata mismatch: {bodyfit_id}")
            face_id = character.get("face_recipe_id")
            if not isinstance(face_id, str) or face_id in face_ids:
                raise OutfitGateError(f"Face V3 recipe is missing or reused: {bodyfit_id}")
            face_ids.add(face_id)
            project = character.get("project") or {}
            project_path = Path(project.get("review_path", ""))
            if project_staging_root is not None:
                project_path = project_staging_root / project_path.name
            if not project_path.is_file():
                raise OutfitGateError(f"Accepted project is missing: {project_path}")
            size_bytes = project_path.stat().st_size
            expected_size = project.get("bytes")
            expected_sha = project.get("sha256")
            if size_bytes != expected_size:
                raise OutfitGateError(f"Accepted project size changed: {project_path}")
            actual_sha = sha256_file(project_path)
            if actual_sha != expected_sha:
                raise OutfitGateError(f"Accepted project hash changed: {project_path}")
            subjects.append(
                {
                    "subject_id": f"OUTFIT_{bodyfit_id.upper()}",
                    "source_character_id": character["character_id"],
                    "sex": sex,
                    "bodyfit_id": bodyfit_id,
                    "body_class": character.get("body_class"),
                    "age_label": character["age_label"],
                    "face_recipe_id": face_id,
                    "scalp_hair_display_name": character.get(
                        "scalp_hair_display_name"
                    ),
                    "source_project": {
                        "path": str(project_path),
                        "size_bytes": size_bytes,
                        "sha256": actual_sha,
                    },
                    "source_review": {
                        "summary_path": str(summary_path),
                        "summary_status": summary["status"],
                        "result_flags": character.get("result_flags"),
                    },
                }
            )
    return subjects


def load_family_manifests(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    paths = sorted(
        root.glob("*/*/outfit_family.json"),
        key=lambda value: str(value).casefold(),
    )
    if len(paths) != 41:
        raise OutfitGateError(f"Expected 41 outfit families, found {len(paths)}")
    manifests: list[tuple[Path, dict[str, Any]]] = []
    family_ids: set[str] = set()
    for path in paths:
        document = read_json(path)
        family_id = document.get("family_id")
        if not isinstance(family_id, str) or family_id in family_ids:
            raise OutfitGateError(f"Invalid or duplicate family ID: {path}")
        if document.get("rules_status") != "confirmed":
            raise OutfitGateError(f"Family is not confirmed: {path}")
        family_ids.add(family_id)
        manifests.append((path, document))
    return manifests


def inventory_index(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], Path]:
    path = root / "both" / "shoes" / "shoe_inventory.json"
    inventory = read_json(path)
    by_id: dict[str, dict[str, Any]] = {}
    for asset in inventory.get("assets", []):
        identifier = asset.get("shoe_id")
        if not isinstance(identifier, str) or identifier in by_id:
            raise OutfitGateError(f"Invalid shared shoe inventory: {path}")
        by_id[identifier] = asset
    if not by_id:
        raise OutfitGateError(f"Shared shoe inventory is empty: {path}")
    return inventory, by_id, path


def resolve_shared_shoe_path(asset: dict[str, Any]) -> Path:
    candidates = [Path(value) for value in asset.get("source_paths", [])]
    candidates = [path for path in candidates if path.is_file()]
    if len(candidates) != 1:
        raise OutfitGateError(
            f"Shared shoe must resolve to one file: {asset.get('shoe_id')}"
        )
    path = candidates[0]
    if path.stat().st_size != asset.get("size_bytes"):
        raise OutfitGateError(f"Shared shoe size changed: {path}")
    if sha256_file(path) != asset.get("sha256"):
        raise OutfitGateError(f"Shared shoe hash changed: {path}")
    return path


def asset_record_by_id(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = document.get("assets")
    if not isinstance(records, list) or not records:
        raise OutfitGateError(f"Family has no assets: {document.get('family_id')}")
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        identifier = record.get("asset_id")
        if not isinstance(identifier, str) or identifier in result:
            raise OutfitGateError(
                f"Family has invalid asset IDs: {document.get('family_id')}"
            )
        result[identifier] = record
    return result


def selected_asset_ids_for_group(
    document: dict[str, Any], group: dict[str, Any], seed: int
) -> list[str]:
    family_id = document["family_id"]
    group_id = group["group_id"]
    selected: list[str] = []
    for slot in group["required_slots"] + group["optional_slots"]:
        pool = group["slot_pools"][slot]
        selected.append(
            stable_choice(pool, seed, f"{family_id}:{group_id}:{slot}")
        )
    selected.extend(group.get("required_assets", []))
    optional_assets = group.get("optional_assets", [])
    if optional_assets:
        selected.append(
            stable_choice(
                optional_assets,
                seed,
                f"{family_id}:{group_id}:family_accessory",
            )
        )
    if len(selected) != len(set(selected)):
        raise OutfitGateError(f"Representative Look has duplicate assets: {family_id}/{group_id}")
    return selected


def representative_looks(
    family_path: Path,
    document: dict[str, Any],
    inventory: dict[str, Any],
    shoes_by_id: dict[str, dict[str, Any]],
    seed: int,
    compatibility_aliases: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records = asset_record_by_id(document)
    mode = document["assembly_mode"]
    if mode == "slot_groups":
        source_groups = document["assembly"]["groups"]
        groups = [
            (
                group["group_id"],
                selected_asset_ids_for_group(document, group, seed),
            )
            for group in source_groups
        ]
    elif mode == "locked_bundle":
        bundle = document["assembly"]["bundle"]
        groups = [(bundle["bundle_id"], list(bundle["required_assets"]))]
    else:
        raise OutfitGateError(
            f"Production gate does not accept {mode}: {document['family_id']}"
        )

    output: list[dict[str, Any]] = []
    for group_id, selected_ids in groups:
        assets: list[dict[str, Any]] = []
        for identifier in selected_ids:
            record = records.get(identifier)
            if record is None:
                raise OutfitGateError(
                    f"Representative Look references an unknown asset: {identifier}"
                )
            absolute_path = family_path.parent / Path(record["path"])
            if not absolute_path.is_file():
                raise OutfitGateError(f"Garment asset is missing: {absolute_path}")
            resolved_path, compatibility_transform = (
                resolve_compatibility_alias(
                    absolute_path,
                    record,
                    compatibility_aliases,
                )
            )
            asset = {
                "asset_id": identifier,
                "display_name": record["display_name"],
                "slot": record["slot"],
                "source": "family",
                "path": str(resolved_path),
                "size_bytes": resolved_path.stat().st_size,
                "sha256": sha256_file(resolved_path),
            }
            if compatibility_transform is not None:
                asset["compatibility_transform"] = compatibility_transform
            assets.append(asset)

        footwear = document["footwear_policy"]
        footwear_mode = footwear["mode"]
        shoe_selection: dict[str, Any]
        if footwear_mode == "native_pool":
            native = [asset for asset in assets if asset["slot"] == "shoes"]
            if len(native) != 1:
                raise OutfitGateError(
                    f"Native representative Look must select one shoe: {document['family_id']}/{group_id}"
                )
            shoe_selection = {
                "mode": "native_pool",
                "asset_id": native[0]["asset_id"],
                "allow_barefoot": False,
            }
        elif footwear_mode == "shared_pool":
            allowed = footwear["allowed_shared_shoe_ids"]
            identifier = footwear.get("default_shared_shoe_id") or stable_choice(
                allowed,
                seed,
                f"{document['family_id']}:{group_id}:shared_shoe",
            )
            shared = shoes_by_id.get(identifier)
            if shared is None or shared.get("sex") != document["sex"]:
                raise OutfitGateError(f"Invalid shared shoe selection: {identifier}")
            shared_path = resolve_shared_shoe_path(shared)
            assets.append(
                {
                    "asset_id": identifier,
                    "display_name": shared.get("display_name"),
                    "slot": "shoes",
                    "source": "shared_inventory",
                    "path": str(shared_path),
                    "size_bytes": shared["size_bytes"],
                    "sha256": shared["sha256"],
                }
            )
            shoe_selection = {
                "mode": "shared_pool",
                "asset_id": identifier,
                "allow_barefoot": footwear["allow_barefoot"],
                "inventory_ref": {
                    "library_id": inventory["library_id"],
                    "revision_id": inventory["revision_id"],
                },
            }
        elif footwear_mode == "integrated_footwear":
            if not any(
                asset["path"].lower().endswith(".ccshoes")
                and asset["slot"] == "full_body"
                for asset in assets
            ):
                raise OutfitGateError(
                    f"Integrated footwear asset is absent: {document['family_id']}/{group_id}"
                )
            shoe_selection = {
                "mode": "integrated_footwear",
                "asset_id": None,
                "allow_barefoot": False,
            }
        else:
            shoe_selection = {
                "mode": "barefoot_only",
                "asset_id": None,
                "allow_barefoot": True,
            }

        # A locked bundle records an author-approved application sequence.  Some
        # legacy components are order-sensitive, so only synthesized slot-group
        # looks use the generic inner-to-outer slot ordering.
        if mode != "locked_bundle":
            assets.sort(
                key=lambda item: (
                    SLOT_LOAD_ORDER[item["slot"]],
                    item["asset_id"],
                )
            )
        for asset in assets:
            asset["cloth_options_policy"] = (
                "keep_cloth_shape"
                if asset["slot"] == "coats"
                else "fit_body_shape"
            )
        output.append(
            {
                "look_id": f"{document['family_id']}::{group_id}",
                "family_id": document["family_id"],
                "family_display_name": document["display_name"],
                "sex": document["sex"],
                "group_id": group_id,
                "assembly_mode": document["assembly_mode"],
                "selected_assets": assets,
                "footwear_selection": shoe_selection,
            }
        )
    return output


def build_gate(
    clothing_root: Path,
    showcase_summary: Path,
    seed: int,
    output_root: Path,
    project_staging_root: Path | None = None,
    library_id: str = "cc_outfit_compatibility_gate_20260815_v1",
    compatibility_alias_registry: Path = DEFAULT_COMPATIBILITY_ALIAS_REGISTRY,
) -> dict[str, Any]:
    clothing_root = clothing_root.resolve()
    showcase_summary = showcase_summary.resolve()
    project_staging_root = (
        project_staging_root.resolve() if project_staging_root is not None else None
    )
    subjects = collect_subjects(showcase_summary, project_staging_root)
    subjects_by_sex = {
        sex: [subject for subject in subjects if subject["sex"] == sex]
        for sex in ("female", "male")
    }
    inventory, shoes_by_id, inventory_path = inventory_index(clothing_root)
    compatibility_aliases, compatibility_alias_registry_record = (
        load_compatibility_alias_registry(compatibility_alias_registry)
    )

    families: list[dict[str, Any]] = []
    looks: list[dict[str, Any]] = []
    for manifest_path, document in load_family_manifests(clothing_root):
        family_path = manifest_path.parent
        family_looks = representative_looks(
            manifest_path,
            document,
            inventory,
            shoes_by_id,
            seed,
            compatibility_aliases,
        )
        looks.extend(family_looks)
        families.append(
            {
                "family_id": document["family_id"],
                "display_name": document["display_name"],
                "sex": document["sex"],
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "logical_group_count": len(family_looks),
                "footwear_mode": document["footwear_policy"]["mode"],
            }
        )

    if not looks:
        raise OutfitGateError("No logical outfit groups were discovered")

    presets: list[dict[str, Any]] = []
    for look in looks:
        for subject in subjects_by_sex[look["sex"]]:
            case_id = f"{look['look_id']}::{subject['bodyfit_id']}"
            safe_case_id = (
                case_id.replace("::", "__")
                .replace(".", "_")
                .replace(" ", "_")
            )
            base_avatar = Path(BASE_AVATAR_BY_SEX[look["sex"]])
            if not base_avatar.is_file():
                raise OutfitGateError(f"Neutral base avatar is missing: {base_avatar}")
            presets.append(
                {
                    "preset_id": safe_case_id,
                    "case_id": case_id,
                    "output_directory_name": safe_case_id,
                    "look_id": look["look_id"],
                    "subject_id": subject["subject_id"],
                    "sex": look["sex"],
                    "bodyfit_id": subject["bodyfit_id"],
                    "base_avatar": {"path": str(base_avatar)},
                    "source_project": subject["source_project"],
                    "selected_assets": look["selected_assets"],
                    "footwear_selection": look["footwear_selection"],
                    "capture_views": CAPTURE_VIEWS,
                    "expected_image_count": len(CAPTURE_VIEWS),
                    "planned_output_directory": str(
                        output_root / "cases" / safe_case_id
                    ),
                }
            )

    expected_case_count = sum(
        len(subjects_by_sex[look["sex"]]) for look in looks
    )
    if len(presets) != expected_case_count:
        raise OutfitGateError(
            f"Expected {expected_case_count} test cases, found {len(presets)}"
        )
    if len({case["case_id"] for case in presets}) != len(presets):
        raise OutfitGateError("Duplicate test case IDs")

    return {
        "schema_version": 1,
        "library_id": library_id,
        "diagnostic_mode": "outfit_compatibility_gate",
        "gate_id": library_id,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "planned",
        "seed": seed,
        "clothing_root": str(clothing_root),
        "shared_shoe_inventory": {
            "path": str(inventory_path),
            "library_id": inventory["library_id"],
            "revision_id": inventory["revision_id"],
            "sha256": sha256_file(inventory_path),
        },
        "compatibility_alias_registry": compatibility_alias_registry_record,
        "source_showcase_summary": str(showcase_summary),
        "project_staging_root": (
            str(project_staging_root) if project_staging_root is not None else None
        ),
        "preview_capture_mode": "render_image",
        "preview_resolution": [1024, 1024],
        "preview_lightroom": PREVIEW_LIGHTROOM,
        "full_body_camera": FULL_BODY_CAMERA,
        "subjects": subjects,
        "families": families,
        "representative_looks": looks,
        "presets": presets,
        "capture_policy": {
            "resolution": [1024, 1024],
            "views": CAPTURE_VIEWS,
            "framing": "full_body_centered_with_fixed_margin",
            "neutral_pose_required": True,
            "transparent_background": False,
        },
        "execution_policy": {
            "reload_source_project_before_each_case": True,
            "remove_existing_clothing_before_apply": True,
            "preserve_identity_hair_and_face_components": True,
            "apply_assets_in_slot_order": list(SLOT_LOAD_ORDER),
            "stop_on_blocking_dialog": True,
            "continue_after_visual_or_load_failure": True,
            "checkpoint_after_each_case": True,
            "project_load_settle_seconds": 20.0,
            "asset_load_before_seconds": 1.5,
            "asset_load_after_seconds": 4.0,
            "coats_load_after_seconds": 6.0,
        },
        "counts": {
            "subject_count": len(subjects),
            "family_count": len(families),
            "logical_group_count": len(looks),
            "test_case_count": len(presets),
            "views_per_case": len(CAPTURE_VIEWS),
            "expected_image_count": len(presets) * len(CAPTURE_VIEWS),
            "families_by_sex": dict(Counter(item["sex"] for item in families)),
            "logical_groups_by_sex": dict(Counter(item["sex"] for item in looks)),
            "cases_by_sex": dict(Counter(item["sex"] for item in presets)),
            "footwear_modes": dict(Counter(item["footwear_mode"] for item in families)),
            "compatibility_alias_asset_count": sum(
                1
                for look in looks
                for asset in look["selected_assets"]
                if "compatibility_transform" in asset
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clothing-root", type=Path, required=True)
    parser.add_argument("--showcase-summary", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-staging-root", type=Path)
    parser.add_argument(
        "--compatibility-alias-registry",
        type=Path,
        default=DEFAULT_COMPATIBILITY_ALIAS_REGISTRY,
    )
    parser.add_argument("--seed", type=int, default=20260815)
    parser.add_argument(
        "--library-id",
        default="cc_outfit_compatibility_gate_20260815_v1",
    )
    args = parser.parse_args()

    gate = build_gate(
        args.clothing_root,
        args.showcase_summary,
        args.seed,
        args.output_root.resolve(),
        args.project_staging_root,
        args.library_id,
        args.compatibility_alias_registry,
    )
    write_json(args.output.resolve(), gate)
    print(json.dumps({"success": True, **gate["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
