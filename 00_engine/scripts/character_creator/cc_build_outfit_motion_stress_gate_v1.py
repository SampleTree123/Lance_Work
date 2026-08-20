#!/usr/bin/env python3
"""Build the first deterministic outfit motion-stress gate.

This gate deliberately uses existing CC motions as diagnostic loads. It does
not select or approve assets for the later production animation pool.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_STATIC_GATE = SCRIPT_DIR / "cc_outfit_compatibility_gate_20260816_v3.json"
DEFAULT_STATIC_REVIEW_INDEX = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_compatibility_gate\cumulative_review_20260815_v1"
    r"\reviewed_index_20260816_v1.json"
)
DEFAULT_OUTPUT = SCRIPT_DIR / "cc_outfit_motion_stress_gate_20260816_v3.json"
DEFAULT_CHUNK_DIR = SCRIPT_DIR / "outfit_motion_stress_chunks_20260816_v3"
DEFAULT_OUTPUT_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_motion_stress_gate\run_20260816_v1"
)
HEAVY_BODYFIT = {"female": "F04_Heavy", "male": "M04_Heavy"}
REFERENCE_VIEW = {"view_id": "front_three_quarter", "yaw_degrees": 45.0}
SAMPLE_POSITIONS = [0.0, 0.2, 0.4, 0.6, 0.8]
MOTION_ROOT = Path(
    r"D:\CharacterCreator_sucai\Reallusion Templates\Animation\Motion Plus\1.Acting"
)
CALIBRATION_MOTION = Path(
    r"D:\CharacterCreator_sucai\Reallusion Templates\Animation\Motion Plus\Animated"
    r"\2.Calibration\01_Body Rig\Full Body.iMotionPlus"
)
MOTIONS = {
    "female": [
        (
            "locomotion_walk",
            MOTION_ROOT / "02_Female" / "CC5 HD" / "HD Walk_F.iMotionPlus",
        ),
        (
            "full_body_calibration",
            CALIBRATION_MOTION,
        ),
    ],
    "male": [
        (
            "locomotion_walk",
            MOTION_ROOT / "01_Male" / "CC5 HD" / "HD Walk_M.iMotionPlus",
        ),
        (
            "full_body_calibration",
            CALIBRATION_MOTION,
        ),
    ],
}


class MotionStressBuildError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MotionStressBuildError(f"Expected JSON object: {path}")
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


def file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise MotionStressBuildError(f"Required motion is missing: {resolved}")
    return {
        "path": str(resolved),
        "size_bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def build_motion_profiles(sex: str) -> list[dict[str, Any]]:
    profiles = []
    for profile_id, path in MOTIONS[sex]:
        profiles.append(
            {
                "profile_id": profile_id,
                "purpose": (
                    "stride_hip_knee_ankle_and_hem_stress"
                    if profile_id == "locomotion_walk"
                    else "shoulder_elbow_torso_and_layering_stress"
                ),
                "motion": file_record(path),
                "replace_existing_motion_clips": True,
                "sample_normalized_positions": list(SAMPLE_POSITIONS),
                "yaw_degrees": 135.0,
                "segment_timeout_seconds": 30.0,
                "image_prefix": profile_id,
            }
        )
    return profiles


def load_static_application_orders(
    review_index_path: Path,
) -> dict[str, dict[str, Any]]:
    review_index_path = review_index_path.resolve()
    review_index = read_json(review_index_path)
    orders: dict[str, dict[str, Any]] = {}
    for group in review_index.get("groups") or []:
        for case in group.get("cases") or []:
            sex = case.get("sex")
            if sex not in HEAVY_BODYFIT:
                continue
            if case.get("bodyfit_id") != HEAVY_BODYFIT[sex]:
                continue
            look_id = case.get("look_id")
            if not isinstance(look_id, str) or not look_id:
                raise MotionStressBuildError(
                    "Static review contains a heavy case without look_id"
                )
            if look_id in orders:
                raise MotionStressBuildError(
                    f"Static review contains duplicate heavy evidence: {look_id}"
                )
            result_path = Path(case["result_path"]).resolve()
            result = read_json(result_path)
            if result.get("success") is not True:
                raise MotionStressBuildError(
                    f"Static application-order evidence is not successful: {result_path}"
                )
            asset_ids = [
                item.get("asset_id") for item in result.get("asset_applications") or []
            ]
            if (
                not asset_ids
                or any(not isinstance(item, str) or not item for item in asset_ids)
                or len(asset_ids) != len(set(asset_ids))
            ):
                raise MotionStressBuildError(
                    f"Static application order is empty or ambiguous: {result_path}"
                )
            object_owners: dict[str, dict[str, str]] = {}
            allowed_replacements = []
            for application in result.get("asset_applications") or []:
                asset_id = application.get("asset_id")
                slot = application.get("slot")
                changes = application.get("inventory_changes") or {}
                for removed in changes.get("removed") or []:
                    owner = object_owners.pop(removed.get("id"), None)
                    if owner is not None:
                        allowed_replacements.append(
                            {
                                "removing_asset_id": asset_id,
                                "removed_owner_asset_id": owner["asset_id"],
                                "removed_owner_slot": owner["slot"],
                                "object_collection": removed.get("collection"),
                                "object_name": removed.get("name"),
                            }
                        )
                for added in changes.get("added") or []:
                    object_owners[added["id"]] = {
                        "asset_id": asset_id,
                        "slot": slot,
                    }
            assembled_objects = (result.get("assembled_inventory") or {}).get(
                "objects"
            ) or []
            if not assembled_objects:
                raise MotionStressBuildError(
                    f"Static application evidence has no final inventory: {result_path}"
                )
            expected_inventory = sorted(
                [
                    {
                        "collection": item.get("collection"),
                        "name": item.get("name"),
                        "python_type": item.get("python_type"),
                    }
                    for item in assembled_objects
                ],
                key=lambda item: (
                    str(item["collection"]),
                    str(item["name"]),
                    str(item["python_type"]),
                ),
            )
            orders[look_id] = {
                "allowed_required_asset_replacements": allowed_replacements,
                "case_id": result.get("case_id"),
                "expected_assembled_inventory": expected_inventory,
                "ordered_asset_ids": asset_ids,
                "result_path": str(result_path),
                "result_sha256": sha256_file(result_path),
            }
    return orders


def reorder_assets_from_static_evidence(
    selected_assets: list[dict[str, Any]],
    evidence: dict[str, Any],
    look_id: str,
) -> list[dict[str, Any]]:
    assets_by_id = {item.get("asset_id"): item for item in selected_assets}
    if len(assets_by_id) != len(selected_assets) or None in assets_by_id:
        raise MotionStressBuildError(
            f"Motion source assets are missing unique asset IDs: {look_id}"
        )
    ordered_ids = evidence["ordered_asset_ids"]
    if set(ordered_ids) != set(assets_by_id) or len(ordered_ids) != len(selected_assets):
        raise MotionStressBuildError(
            f"Static application evidence asset set differs for Look {look_id}"
        )
    return [copy.deepcopy(assets_by_id[asset_id]) for asset_id in ordered_ids]


def build_gate(
    static_gate_path: Path,
    output_root: Path,
    library_id: str,
    static_review_index_path: Path | None = None,
) -> dict[str, Any]:
    static_gate_path = static_gate_path.resolve()
    static_gate = read_json(static_gate_path)
    if static_gate.get("diagnostic_mode") != "outfit_compatibility_gate":
        raise MotionStressBuildError("Source manifest is not an outfit static gate")

    static_presets = static_gate.get("presets") or []
    look_ids = [item.get("look_id") for item in static_gate.get("representative_looks", [])]
    if not look_ids or len(look_ids) != len(set(look_ids)):
        raise MotionStressBuildError("Source Look IDs are missing or not unique")

    presets_by_key = {
        (item.get("look_id"), item.get("bodyfit_id")): item
        for item in static_presets
    }
    application_orders = (
        load_static_application_orders(static_review_index_path)
        if static_review_index_path is not None
        else {}
    )
    if application_orders and set(application_orders) != set(look_ids):
        missing = sorted(set(look_ids) - set(application_orders))
        extra = sorted(set(application_orders) - set(look_ids))
        raise MotionStressBuildError(
            f"Static application evidence coverage mismatch: missing={missing}, extra={extra}"
        )
    dynamic_presets = []
    for look_index, look_id in enumerate(look_ids, 1):
        look_cases = [item for item in static_presets if item.get("look_id") == look_id]
        if not look_cases:
            raise MotionStressBuildError(f"Source Look has no cases: {look_id}")
        sex = look_cases[0].get("sex")
        if sex not in HEAVY_BODYFIT:
            raise MotionStressBuildError(f"Unsupported sex for Look {look_id}: {sex}")
        bodyfit_id = HEAVY_BODYFIT[sex]
        source = presets_by_key.get((look_id, bodyfit_id))
        if source is None:
            raise MotionStressBuildError(
                f"Look {look_id} has no required heavy BodyFit {bodyfit_id}"
            )
        preset = copy.deepcopy(source)
        order_evidence = application_orders.get(look_id)
        if order_evidence is not None:
            preset["selected_assets"] = reorder_assets_from_static_evidence(
                preset["selected_assets"],
                order_evidence,
                look_id,
            )
            preset["source_static_application_order"] = copy.deepcopy(order_evidence)
        preset_id = f"{source['preset_id']}__motion_stress_v1"
        directory_name = "d{:03d}_{}".format(
            look_index,
            hashlib.sha1(look_id.encode("utf-8")).hexdigest()[:8],
        )
        preset.update(
            {
                "preset_id": preset_id,
                "case_id": f"{source['case_id']}::motion_stress_v1",
                "output_directory_name": directory_name,
                "capture_views": [dict(REFERENCE_VIEW)],
                "expected_image_count": 1,
                "motion_stress_profiles": build_motion_profiles(sex),
                "motion_stress_expected_image_count": (
                    len(MOTIONS[sex]) * len(SAMPLE_POSITIONS)
                ),
                "planned_output_directory": str(
                    output_root.resolve() / "cases" / directory_name
                ),
            }
        )
        dynamic_presets.append(preset)

    motion_image_count = sum(
        item["motion_stress_expected_image_count"] for item in dynamic_presets
    )
    reference_image_count = len(dynamic_presets)
    document = {
        "schema_version": 1,
        "library_id": library_id,
        "generated_at": now(),
        "status": "motion_stress_pending",
        "diagnostic_mode": "outfit_motion_stress_gate",
        "source_static_gate": {
            "path": str(static_gate_path),
            "sha256": sha256_file(static_gate_path),
            "library_id": static_gate.get("library_id"),
        },
        "source_static_review_index": (
            {
                "path": str(static_review_index_path.resolve()),
                "sha256": sha256_file(static_review_index_path.resolve()),
                "application_order_look_count": len(application_orders),
            }
            if static_review_index_path is not None
            else None
        ),
        "preview_capture_mode": static_gate.get("preview_capture_mode", "render_image"),
        "preview_resolution": static_gate.get("preview_resolution", [1024, 1024]),
        "preview_lightroom": static_gate["preview_lightroom"],
        "full_body_camera": static_gate["full_body_camera"],
        "representative_looks": copy.deepcopy(static_gate["representative_looks"]),
        "presets": dynamic_presets,
        "capture_policy": {
            "reference_view": dict(REFERENCE_VIEW),
            "motion_view": "front_three_quarter",
            "sample_normalized_positions": list(SAMPLE_POSITIONS),
            "motion_profiles": ["locomotion_walk", "full_body_calibration"],
            "framing": "full_body_centered_before_each_motion",
            "physics_simulation": True,
        },
        "execution_policy": {
            **copy.deepcopy(static_gate.get("execution_policy") or {}),
            "checkpoint_after_each_case": True,
            "stop_on_blocking_dialog": True,
        },
        "scope_policy": {
            "bodyfit_per_look": "same_sex_heavy_only",
            "female_bodyfit": HEAVY_BODYFIT["female"],
            "male_bodyfit": HEAVY_BODYFIT["male"],
            "motions_are_diagnostic_not_production_pool": True,
            "hair_headwear_intersection_is_recorded_but_deferred": True,
            "dynamic_visual_review_required": True,
            "application_order_source": (
                "frozen_static_success_evidence"
                if application_orders
                else "source_manifest_order"
            ),
        },
        "counts": {
            "logical_group_count": len(look_ids),
            "test_case_count": len(dynamic_presets),
            "cases_by_sex": dict(Counter(item["sex"] for item in dynamic_presets)),
            "motion_profile_count_per_case": 2,
            "sample_positions_per_profile": len(SAMPLE_POSITIONS),
            "reference_image_count": reference_image_count,
            "motion_image_count": motion_image_count,
            "expected_image_count": reference_image_count + motion_image_count,
        },
    }
    return document


def write_chunks(document: dict[str, Any], chunk_dir: Path, looks_per_chunk: int) -> int:
    if looks_per_chunk < 1:
        raise MotionStressBuildError("looks_per_chunk must be positive")
    presets = document["presets"]
    chunk_dir.mkdir(parents=True, exist_ok=True)
    stale = list(chunk_dir.glob("chunk_*.json"))
    for path in stale:
        path.unlink()
    chunk_count = 0
    for start in range(0, len(presets), looks_per_chunk):
        chunk_count += 1
        selected = presets[start : start + looks_per_chunk]
        chunk = copy.deepcopy(document)
        chunk["library_id"] = f"{document['library_id']}__chunk_{chunk_count:02d}"
        chunk["parent_library_id"] = document["library_id"]
        chunk["presets"] = selected
        chunk["counts"] = {
            **document["counts"],
            "logical_group_count": len(selected),
            "test_case_count": len(selected),
            "cases_by_sex": dict(Counter(item["sex"] for item in selected)),
            "reference_image_count": len(selected),
            "motion_image_count": sum(
                item["motion_stress_expected_image_count"] for item in selected
            ),
            "expected_image_count": sum(
                1 + item["motion_stress_expected_image_count"] for item in selected
            ),
        }
        write_json(chunk_dir / f"chunk_{chunk_count:02d}.json", chunk)
    return chunk_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-gate", type=Path, default=DEFAULT_STATIC_GATE)
    parser.add_argument(
        "--static-review-index",
        type=Path,
        default=DEFAULT_STATIC_REVIEW_INDEX,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--chunk-dir", type=Path, default=DEFAULT_CHUNK_DIR)
    parser.add_argument("--looks-per-chunk", type=int, default=2)
    parser.add_argument(
        "--library-id",
        default="cc_outfit_motion_stress_gate_20260816_v3",
    )
    args = parser.parse_args()

    document = build_gate(
        args.static_gate,
        args.output_root,
        args.library_id,
        args.static_review_index,
    )
    write_json(args.output.resolve(), document)
    chunk_count = write_chunks(
        document,
        args.chunk_dir.resolve(),
        args.looks_per_chunk,
    )
    print(
        json.dumps(
            {"success": True, **document["counts"], "chunk_count": chunk_count},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
