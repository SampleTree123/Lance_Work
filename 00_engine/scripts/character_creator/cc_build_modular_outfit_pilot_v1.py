#!/usr/bin/env python3
"""Compile the frozen Average-BodyFit modular outfit pilot manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
LANCE_ROOT = SCRIPT_ROOT.parents[2]
DEFAULT_SOURCE = SCRIPT_ROOT / "cc_modular_outfit_pilot_source_v1.json"
DEFAULT_CC_OUTPUT = SCRIPT_ROOT / "cc_modular_outfit_pilot_20260829_v1.json"
DEFAULT_UE_OUTPUT = (
    LANCE_ROOT
    / "00_engine"
    / "scripts"
    / "unreal"
    / "ue_modular_outfit_pilot_manifest_20260829_v1.json"
)
DEFAULT_ALIAS_REGISTRY = (
    LANCE_ROOT
    / "00_engine"
    / "assets"
    / "character_creator"
    / "outfit_compatibility_aliases"
    / "compatibility_alias_registry.json"
)
LOAD_ORDER = {
    "full_body": 10,
    "pants": 20,
    "skirts": 20,
    "shirts": 30,
    "coats": 40,
    "family_accessory": 50,
    "shoes": 60,
}
AVERAGE_BODYFITS = {"female": "F02_Average", "male": "M02_Average"}
CAPTURE_VIEWS = [{"view_id": "front", "yaw_degrees": 0.0}]
PREVIEW_LIGHTROOM = (
    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Light Room"
    r"\Default\Default_CC5.ccLightroom"
)
FULL_BODY_CAMERA = (
    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera"
    r"\Headshot Ref\Ref Cam Male L.ccCam"
)


class ModularPilotError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ModularPilotError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(record: dict[str, Any], label: str) -> dict[str, Any]:
    path = Path(record.get("path", "")).resolve()
    if not path.is_file():
        raise ModularPilotError(f"{label} is missing: {path}")
    size_bytes = path.stat().st_size
    actual_sha = sha256_file(path)
    expected_size = record.get("size_bytes")
    expected_sha = str(record.get("sha256", "")).lower()
    if expected_size is not None and size_bytes != expected_size:
        raise ModularPilotError(f"{label} size changed: {path}")
    if expected_sha and actual_sha != expected_sha:
        raise ModularPilotError(f"{label} hash changed: {path}")
    return {"path": str(path), "size_bytes": size_bytes, "sha256": actual_sha}


def asset_index(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for asset in document.get("assets") or []:
        asset_id = asset.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in result:
            raise ModularPilotError(
                f"Family has invalid asset IDs: {document.get('family_id')}"
            )
        result[asset_id] = asset
    if not result:
        raise ModularPilotError(f"Family has no assets: {document.get('family_id')}")
    return result


def load_aliases(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    record = verify_file(
        {"path": str(path)},
        "Compatibility alias registry",
    )
    document = read_json(path)
    policy = document.get("policy") or {}
    if (
        document.get("schema_version") != 1
        or policy.get("byte_identity_required") is not True
        or policy.get("source_assets_remain_immutable") is not True
        or policy.get("allowed_transform") != "extension_dispatch_alias_only"
    ):
        raise ModularPilotError("Compatibility alias policy is not safe")
    result: dict[str, dict[str, Any]] = {}
    for entry in document.get("aliases") or []:
        source = verify_file(entry.get("source") or {}, "Alias source")
        alias = verify_file(entry.get("alias") or {}, "Alias target")
        if source["sha256"] != alias["sha256"] or source["size_bytes"] != alias["size_bytes"]:
            raise ModularPilotError(
                f"Compatibility alias is not byte-identical: {entry.get('alias_id')}"
            )
        result[source["sha256"]] = {
            "alias_id": entry.get("alias_id"),
            "alias": alias,
            "source": source,
        }
    return result, {**record, "alias_count": len(result)}


def resolve_family_asset(
    family_root: Path,
    asset: dict[str, Any],
    aliases: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_record = verify_file(
        {
            "path": str(family_root / asset["path"]),
            "size_bytes": asset.get("size_bytes"),
            "sha256": asset.get("sha256"),
        },
        f"Family asset {asset.get('asset_id')}",
    )
    load_record = source_record
    compatibility_transform = None
    if Path(source_record["path"]).suffix.casefold() == ".ccgloves":
        alias = aliases.get(source_record["sha256"])
        if alias is None:
            raise ModularPilotError(
                f"ccGloves asset lacks a validated loader alias: {source_record['path']}"
            )
        if alias["source"]["path"] != source_record["path"]:
            raise ModularPilotError("Compatibility alias source path changed")
        load_record = alias["alias"]
        compatibility_transform = {
            "alias_id": alias["alias_id"],
            "byte_identity_verified": True,
            "source_path": source_record["path"],
            "load_path": load_record["path"],
            "transform": "extension_dispatch_alias_only",
        }
    record = {
        "asset_id": asset["asset_id"],
        "display_name": asset.get("display_name"),
        "slot": asset["slot"],
        "source": "family",
        "source_path": source_record["path"],
        "path": load_record["path"],
        "size_bytes": load_record["size_bytes"],
        "sha256": load_record["sha256"],
        "family_relative_path": asset["path"],
        "module_key": asset["path"],
        "cloth_options_policy": (
            "keep_cloth_shape" if asset["slot"] == "coats" else "fit_body_shape"
        ),
    }
    if compatibility_transform is not None:
        record["compatibility_transform"] = compatibility_transform
    return record


def shoe_inventory_index(
    inventory_record: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    verified = verify_file(inventory_record, "Shared shoe inventory")
    document = read_json(Path(verified["path"]))
    result: dict[str, dict[str, Any]] = {}
    for asset in document.get("assets") or []:
        shoe_id = asset.get("shoe_id")
        if not isinstance(shoe_id, str) or not shoe_id or shoe_id in result:
            raise ModularPilotError("Shared shoe inventory has invalid IDs")
        result[shoe_id] = {
            **asset,
            "_inventory_root": str(Path(verified["path"]).parent),
        }
    if not result:
        raise ModularPilotError("Shared shoe inventory is empty")
    return result, {
        **verified,
        "library_id": document.get("library_id"),
        "revision_id": document.get("revision_id"),
    }


def resolve_shared_shoe(asset: dict[str, Any], expected_sex: str) -> dict[str, Any]:
    if asset.get("sex") != expected_sex:
        raise ModularPilotError(
            f"Shared shoe sex mismatch: {asset.get('shoe_id')}"
        )
    path = Path(asset["_inventory_root"]) / asset["new_relative_path"]
    verified = verify_file(
        {
            "path": str(path),
            "size_bytes": asset.get("size_bytes"),
            "sha256": asset.get("sha256"),
        },
        f"Shared shoe {asset.get('shoe_id')}",
    )
    return {
        "asset_id": asset["shoe_id"],
        "display_name": asset.get("display_name"),
        "slot": "shoes",
        "source": "shared_inventory",
        "source_path": verified["path"],
        "path": verified["path"],
        "size_bytes": verified["size_bytes"],
        "sha256": verified["sha256"],
        "module_key": f"shared:{asset['shoe_id']}",
        "cloth_options_policy": "fit_body_shape",
        "validation_status": asset.get("validation_status"),
    }


def group_for(document: dict[str, Any], group_id: str) -> dict[str, Any]:
    if document.get("assembly_mode") == "locked_bundle":
        bundle = document.get("assembly", {}).get("bundle") or {}
        if bundle.get("bundle_id") != group_id:
            raise ModularPilotError(
                f"Unknown locked bundle: {document.get('family_id')}/{group_id}"
            )
        return bundle
    for group in document.get("assembly", {}).get("groups") or []:
        if group.get("group_id") == group_id:
            return group
    raise ModularPilotError(
        f"Unknown slot group: {document.get('family_id')}/{group_id}"
    )


def validate_slot_group(
    document: dict[str, Any],
    group: dict[str, Any],
    enabled_family_ids: set[str],
    enabled_shared_shoes: set[str],
) -> None:
    records = asset_index(document)
    pools = group.get("slot_pools") or {}
    required_slots = group.get("required_slots") or []
    optional_slots = group.get("optional_slots") or []
    allowed_ids: set[str] = set(group.get("required_assets") or [])
    allowed_ids.update(group.get("optional_assets") or [])
    for slot in required_slots + optional_slots:
        pool = set(pools.get(slot) or [])
        selected = enabled_family_ids & pool
        if slot in required_slots and len(selected) != 1:
            raise ModularPilotError(
                f"Runtime variant requires exactly one {slot}: {document['family_id']}"
            )
        if slot in optional_slots and len(selected) > 1:
            raise ModularPilotError(
                f"Runtime variant enables multiple optional {slot}: {document['family_id']}"
            )
        allowed_ids.update(pool)
    if not set(group.get("required_assets") or []).issubset(enabled_family_ids):
        raise ModularPilotError(
            f"Runtime variant omits a required family asset: {document['family_id']}"
        )
    if not enabled_family_ids.issubset(allowed_ids):
        extra = sorted(enabled_family_ids - allowed_ids)
        raise ModularPilotError(
            f"Runtime variant uses assets outside the group: {extra}"
        )
    for asset_id in enabled_family_ids:
        if asset_id not in records:
            raise ModularPilotError(f"Unknown enabled family asset: {asset_id}")
    validate_footwear(document, enabled_family_ids, enabled_shared_shoes)


def validate_footwear(
    document: dict[str, Any],
    enabled_family_ids: set[str],
    enabled_shared_shoes: set[str],
) -> None:
    records = asset_index(document)
    footwear = document.get("footwear_policy") or {}
    mode = footwear.get("mode")
    native_shoes = {
        asset_id
        for asset_id in enabled_family_ids
        if records[asset_id].get("slot") == "shoes"
    }
    if mode == "native_pool":
        if len(native_shoes) != 1 or enabled_shared_shoes:
            raise ModularPilotError(
                f"Native footwear variant must enable one native shoe: {document['family_id']}"
            )
    elif mode == "shared_pool":
        allowed = set(footwear.get("allowed_shared_shoe_ids") or [])
        if not enabled_shared_shoes.issubset(allowed):
            raise ModularPilotError(
                f"Runtime variant uses a disallowed shared shoe: {document['family_id']}"
            )
        if len(enabled_shared_shoes) > 1:
            raise ModularPilotError("Runtime variant enables multiple shared shoes")
        if not enabled_shared_shoes and footwear.get("allow_barefoot") is not True:
            raise ModularPilotError(
                f"Runtime variant is barefoot where prohibited: {document['family_id']}"
            )
        if native_shoes:
            raise ModularPilotError("Shared-pool variant enables a native shoe")
    elif mode == "integrated_footwear":
        if native_shoes or enabled_shared_shoes:
            raise ModularPilotError("Integrated-footwear variant enables extra shoes")
    elif mode == "barefoot_only":
        if native_shoes or enabled_shared_shoes:
            raise ModularPilotError("Barefoot-only variant enables shoes")
    else:
        raise ModularPilotError(f"Unsupported footwear mode: {mode}")


def validate_runtime_variant(
    document: dict[str, Any],
    group: dict[str, Any],
    enabled_assets: list[dict[str, Any]],
) -> None:
    family_ids = {
        asset["asset_id"] for asset in enabled_assets if asset["source"] == "family"
    }
    shared_ids = {
        asset["asset_id"]
        for asset in enabled_assets
        if asset["source"] == "shared_inventory"
    }
    if document.get("assembly_mode") == "locked_bundle":
        required = set(group.get("required_assets") or [])
        if family_ids != required:
            raise ModularPilotError(
                f"Locked bundle must remain intact: {document['family_id']}"
            )
        validate_footwear(document, family_ids, shared_ids)
    else:
        validate_slot_group(document, group, family_ids, shared_ids)


def compile_case(
    case: dict[str, Any],
    bodyfits: dict[str, dict[str, Any]],
    shoes: dict[str, dict[str, Any]],
    aliases: dict[str, dict[str, Any]],
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    case_id = case.get("case_id")
    sex = case.get("sex")
    bodyfit_id = case.get("bodyfit_id")
    if not isinstance(case_id, str) or not case_id or Path(case_id).name != case_id:
        raise ModularPilotError(f"Invalid case ID: {case_id}")
    if sex not in AVERAGE_BODYFITS or bodyfit_id != AVERAGE_BODYFITS[sex]:
        raise ModularPilotError(f"Case is outside the Average-BodyFit scope: {case_id}")
    bodyfit = bodyfits.get(bodyfit_id)
    if bodyfit is None or bodyfit.get("sex") != sex:
        raise ModularPilotError(f"Unknown BodyFit: {case_id}/{bodyfit_id}")

    selected_assets: list[dict[str, Any]] = []
    family_summary = None
    group = None
    family_document = None
    family_manifest = case.get("family_manifest")
    is_base = case.get("case_role") == "base_body"
    if is_base:
        if family_manifest is not None or case.get("selection"):
            raise ModularPilotError(f"Base case cannot select outfit assets: {case_id}")
    else:
        manifest_record = verify_file(
            family_manifest or {}, f"Family manifest for {case_id}"
        )
        family_path = Path(manifest_record["path"])
        family_document = read_json(family_path)
        if family_document.get("rules_status") != "confirmed":
            raise ModularPilotError(f"Family is not confirmed: {family_path}")
        if family_document.get("sex") != sex:
            raise ModularPilotError(f"Family sex mismatch: {case_id}")
        records = asset_index(family_document)
        records_by_path = {asset["path"]: asset for asset in records.values()}
        selection = case.get("selection") or {}
        group = group_for(family_document, case.get("group_id"))
        if selection.get("include_locked_bundle") is True:
            if family_document.get("assembly_mode") != "locked_bundle":
                raise ModularPilotError(f"Case requests a non-locked bundle: {case_id}")
            selected_ids = list(group.get("required_assets") or [])
        else:
            requested_paths = selection.get("family_asset_paths") or []
            if not requested_paths or len(requested_paths) != len(set(requested_paths)):
                raise ModularPilotError(f"Case has invalid family asset paths: {case_id}")
            missing = sorted(set(requested_paths) - set(records_by_path))
            if missing:
                raise ModularPilotError(
                    f"Case references assets outside its family: {case_id}: {missing}"
                )
            selected_ids = [records_by_path[path]["asset_id"] for path in requested_paths]
        for asset_id in selected_ids:
            selected_assets.append(
                resolve_family_asset(family_path.parent, records[asset_id], aliases)
            )
        shared_shoe_id = selection.get("shared_shoe_id")
        if shared_shoe_id is not None:
            shared = shoes.get(shared_shoe_id)
            if shared is None:
                raise ModularPilotError(f"Unknown shared shoe: {shared_shoe_id}")
            selected_assets.append(resolve_shared_shoe(shared, sex))
        validate_runtime_variant(family_document, group, selected_assets)
        family_summary = {
            "family_id": family_document["family_id"],
            "assembly_mode": family_document["assembly_mode"],
            "group_id": case.get("group_id"),
            "manifest": manifest_record,
            "footwear_policy": family_document.get("footwear_policy"),
        }

    if family_document is None or family_document.get("assembly_mode") != "locked_bundle":
        selected_assets.sort(
            key=lambda asset: (LOAD_ORDER[asset["slot"]], asset["asset_id"])
        )
    by_key = {asset["module_key"]: asset for asset in selected_assets}
    if len(by_key) != len(selected_assets):
        raise ModularPilotError(f"Duplicate module keys: {case_id}")
    variants = []
    raw_variants = case.get("runtime_variants") or []
    if not raw_variants:
        raise ModularPilotError(f"Case has no runtime variants: {case_id}")
    seen_variant_ids: set[str] = set()
    for variant in raw_variants:
        variant_id = variant.get("variant_id")
        if (
            not isinstance(variant_id, str)
            or not variant_id
            or variant_id in seen_variant_ids
        ):
            raise ModularPilotError(f"Invalid runtime variant ID: {case_id}")
        seen_variant_ids.add(variant_id)
        disabled = variant.get("disabled_modules") or []
        if len(disabled) != len(set(disabled)) or not set(disabled).issubset(by_key):
            raise ModularPilotError(
                f"Runtime variant disables unknown modules: {case_id}/{variant_id}"
            )
        enabled = [asset for asset in selected_assets if asset["module_key"] not in disabled]
        if family_document is not None and group is not None:
            validate_runtime_variant(family_document, group, enabled)
        variants.append(
            {
                "variant_id": variant_id,
                "enabled_modules": [asset["module_key"] for asset in enabled],
                "disabled_modules": list(disabled),
                "purpose": variant.get("purpose"),
            }
        )

    export_basename = f"CC_MOD_{case_id}_UE58"
    export_root = output_root / "full_reference" / case_id
    project_path = output_root / "projects" / f"{case_id}.ccProject"
    preset = {
        "preset_id": case_id,
        "case_id": case_id,
        "case_role": case.get("case_role"),
        "output_directory_name": case_id,
        "look_id": case_id,
        "subject_id": bodyfit_id,
        "sex": sex,
        "bodyfit_id": bodyfit_id,
        "source_project": bodyfit["source_project"],
        "selected_assets": [
            {key: value for key, value in asset.items() if key != "module_key"}
            for asset in selected_assets
        ],
        "allow_empty_selected_assets": is_base,
        "capture_views": list(CAPTURE_VIEWS),
        "expected_image_count": 0,
        "production_output": {
            "project_path": str(project_path),
            "export_root": str(export_root),
            "export_basename": export_basename,
            "export_timeout_seconds": 1200.0,
            "skip_preview_capture": True,
        },
        "coverage_tags": list(case.get("coverage_tags") or []),
    }
    runtime_case = {
        "case_id": case_id,
        "case_role": case.get("case_role"),
        "sex": sex,
        "bodyfit_id": bodyfit_id,
        "family": family_summary,
        "source_project": bodyfit["source_project"],
        "planned_export": {
            "root": str(export_root),
            "fbx": str(export_root / f"{export_basename}.fbx"),
            "json": str(export_root / f"{export_basename}.json"),
            "project": str(project_path),
        },
        "modules": selected_assets,
        "runtime_variants": variants,
        "coverage_tags": list(case.get("coverage_tags") or []),
        "validation_status": "export_pending",
    }
    return preset, runtime_case, family_summary


def compile_manifests(source_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source_path = source_path.resolve()
    source = read_json(source_path)
    if source.get("schema_version") != 1:
        raise ModularPilotError("Unsupported modular pilot source schema")
    bodyfits: dict[str, dict[str, Any]] = {}
    for bodyfit in source.get("bodyfits") or []:
        bodyfit_id = bodyfit.get("bodyfit_id")
        if bodyfit_id in bodyfits:
            raise ModularPilotError(f"Duplicate BodyFit: {bodyfit_id}")
        if bodyfit_id != AVERAGE_BODYFITS.get(bodyfit.get("sex")):
            raise ModularPilotError(f"Non-Average BodyFit in pilot: {bodyfit_id}")
        bodyfits[bodyfit_id] = {
            **bodyfit,
            "source_project": verify_file(
                bodyfit.get("source_project") or {},
                f"Source project {bodyfit_id}",
            ),
        }
    if set(bodyfits) != set(AVERAGE_BODYFITS.values()):
        raise ModularPilotError("Pilot must contain exactly M02_Average and F02_Average")
    shoes, inventory_summary = shoe_inventory_index(
        source.get("shared_shoe_inventory") or {}
    )
    aliases, alias_summary = load_aliases(DEFAULT_ALIAS_REGISTRY)
    output_root = Path(source.get("output_root", "")).resolve()
    if not output_root.is_absolute():
        raise ModularPilotError("Pilot output_root must be absolute")

    presets = []
    runtime_cases = []
    families: dict[str, dict[str, Any]] = {}
    case_ids: set[str] = set()
    for case in source.get("cases") or []:
        if case.get("case_id") in case_ids:
            raise ModularPilotError(f"Duplicate case ID: {case.get('case_id')}")
        case_ids.add(case.get("case_id"))
        preset, runtime_case, family = compile_case(
            case, bodyfits, shoes, aliases, output_root
        )
        presets.append(preset)
        runtime_cases.append(runtime_case)
        if family is not None:
            families[family["family_id"]] = family
    expected_count = source.get("expected_case_count")
    if len(presets) != expected_count:
        raise ModularPilotError(
            f"Expected {expected_count} pilot cases, found {len(presets)}"
        )
    coverage = Counter(
        tag for case in runtime_cases for tag in case.get("coverage_tags") or []
    )
    missing_coverage = sorted(
        set(source.get("required_coverage_tags") or []) - set(coverage)
    )
    if missing_coverage:
        raise ModularPilotError(f"Pilot coverage is incomplete: {missing_coverage}")

    common = {
        "schema_version": 1,
        "pilot_id": source["pilot_id"],
        "revision_id": source["revision_id"],
        "frozen_at": source["frozen_at"],
        "source_spec": {
            "path": str(source_path),
            "sha256": sha256_file(source_path),
        },
        "scope": source["scope"],
        "manual_followup_requirements": source.get(
            "manual_followup_requirements"
        ) or [],
        "counts": {
            "case_count": len(runtime_cases),
            "cases_by_sex": dict(Counter(case["sex"] for case in runtime_cases)),
            "base_case_count": sum(
                case["case_role"] == "base_body" for case in runtime_cases
            ),
            "outfit_case_count": sum(
                case["case_role"] != "base_body" for case in runtime_cases
            ),
            "source_module_count": sum(len(case["modules"]) for case in runtime_cases),
            "runtime_variant_count": sum(
                len(case["runtime_variants"]) for case in runtime_cases
            ),
            "families": len(families),
            "coverage_tags": dict(sorted(coverage.items())),
        },
    }
    cc_manifest = {
        **common,
        "library_id": f"{source['pilot_id']}_cc_export",
        "diagnostic_mode": "outfit_compatibility_gate",
        "status": "export_pending",
        "output_root": str(output_root),
        # Production cases opt out individually. Keep the global mode valid so
        # the shared reconstruction runner can still enforce its contract.
        "preview_capture_mode": "render_image",
        "preview_resolution": [1024, 1024],
        "preview_lightroom": PREVIEW_LIGHTROOM,
        "full_body_camera": FULL_BODY_CAMERA,
        "bodyfits": list(bodyfits.values()),
        "shared_shoe_inventory": inventory_summary,
        "compatibility_alias_registry": alias_summary,
        "presets": presets,
        "execution_policy": {
            "reload_source_project_before_each_case": True,
            "remove_existing_clothing_before_apply": True,
            "remove_source_accessories": True,
            "preserve_identity_hair_and_face_components": True,
            "allow_empty_selected_assets": True,
            "apply_assets_in_slot_order": list(LOAD_ORDER),
            "stop_on_blocking_dialog": True,
            "continue_after_visual_or_load_failure": False,
            "checkpoint_after_each_case": True,
            "record_asset_load_undo": False,
            "project_load_settle_seconds": 12.0,
            "asset_load_before_seconds": 0.5,
            "asset_load_after_seconds": 2.5,
            "coats_load_after_seconds": 4.0,
        },
    }
    ue_manifest = {
        **common,
        "manifest_id": f"{source['pilot_id']}_ue_runtime",
        "status": "source_export_pending",
        "output_root": str(output_root),
        "bodyfits": list(bodyfits.values()),
        "families": sorted(families.values(), key=lambda item: item["family_id"]),
        "cases": runtime_cases,
        "runtime_contract": source["runtime_contract"],
    }
    return cc_manifest, ue_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--cc-output", type=Path, default=DEFAULT_CC_OUTPUT)
    parser.add_argument("--ue-output", type=Path, default=DEFAULT_UE_OUTPUT)
    args = parser.parse_args()
    cc_manifest, ue_manifest = compile_manifests(args.source)
    write_json(args.cc_output.resolve(), cc_manifest)
    write_json(args.ue_output.resolve(), ue_manifest)
    print(json.dumps({"success": True, **cc_manifest["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
