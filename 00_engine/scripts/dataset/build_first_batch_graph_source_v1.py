"""Compose the frozen first-batch graph source from validated local manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_REQUIRED_EXPORTS = SCRIPT_ROOT / "first_batch_required_exports_20260824_v3.json"
DEFAULT_LOCAL_MATRIX = (
    ENGINE_ROOT / "scripts" / "unreal" / "first_batch_local_render_matrix_20260824_v1.json"
)
DEFAULT_OUTPUT = SCRIPT_ROOT / "first_batch_graph_source_20260824_v1.json"
SOURCE_MANIFEST_ID = "first_batch_source_20260824_v1"
SAMPLING_SPEC_VERSION = "multi_round_v1_20260824"
CAMERA_IDS = ("near", "far", "high", "side")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PORTABLE_SOURCE_PREFIXES = ("bundle://", "repo://", "workspace://", "/Game/")


class GraphSourceError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GraphSourceError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GraphSourceError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def is_portable_source_ref(value: str) -> bool:
    return isinstance(value, str) and value.startswith(PORTABLE_SOURCE_PREFIXES)


def normalize_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    require(bool(normalized), f"Could not normalize ID: {value!r}")
    return normalized


def outfit_id(sex: str, source_outfit_id: str) -> str:
    return f"{sex[0]}_{normalize_id(source_outfit_id)}"


def make_asset(
    asset_id: str,
    asset_type: str,
    sex: str,
    source_ref: str,
    content_sha256: str,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    require(bool(SHA256.fullmatch(content_sha256)), f"Invalid hash for {asset_id}")
    require(is_portable_source_ref(source_ref), f"Unportable source_ref for {asset_id}")
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "sex_compatibility": sex,
        "source_ref": source_ref,
        "content_sha256": content_sha256,
        "version": "20260824_v1",
        "status": "validated",
        "constraints": constraints or {},
    }


def normalize_happy_composite(path: str) -> str:
    normalized, count = re.subn(
        r"_(Happy|Angry|Sad)_Composite_", "_Happy_Composite_", path
    )
    require(count == 1, f"Could not normalize composite path: {path}")
    return normalized


def validate_inputs(
    required: dict[str, Any], matrix: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    require(
        required.get("schema_version") == "required_exports_v1",
        "Unsupported required-exports schema",
    )
    require(
        matrix.get("schema_version") == "first_batch_local_render_matrix_v1",
        "Unsupported local-matrix schema",
    )
    looks = required.get("full_reference_looks")
    actions = required.get("actions")
    samples = matrix.get("samples")
    require(isinstance(looks, list) and len(looks) == 32, "Expected 32 looks")
    require(isinstance(actions, list) and len(actions) == 10, "Expected 10 actions")
    require(isinstance(samples, list) and len(samples) == 32, "Expected 32 matrix samples")
    require(
        all(look.get("cc_export_status") == "validated" for look in looks),
        "Every look must have validated CC export status",
    )
    require(
        all(action.get("cc_export_status") == "validated" for action in actions),
        "Every action must have validated CC export status",
    )
    samples_by_look = {sample["look_id"]: sample for sample in samples}
    require(len(samples_by_look) == 32, "Matrix look IDs must be unique")
    require(
        {look["look_id"] for look in looks} == set(samples_by_look),
        "Required-export and matrix Look IDs differ",
    )
    return looks, actions, samples_by_look


def build_happy_composites(
    samples: list[dict[str, Any]], actions: list[dict[str, Any]]
) -> dict[str, str]:
    candidates: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        candidates[sample["action_id"]].add(
            normalize_happy_composite(sample["composite_animation"])
        )
    result: dict[str, str] = {}
    for action in actions:
        action_id = action["action_id"]
        paths = candidates[action_id]
        require(len(paths) == 1, f"Happy composite is ambiguous: {action_id}")
        result[action_id] = next(iter(paths))
    return result


def build_source_manifest(
    required_exports_path: Path, local_matrix_path: Path
) -> dict[str, Any]:
    required = read_json(required_exports_path)
    matrix = read_json(local_matrix_path)
    source_looks, source_actions, samples_by_look = validate_inputs(required, matrix)
    happy_composites = build_happy_composites(
        matrix["samples"], source_actions
    )
    bundle_id = normalize_id(required["batch_id"])

    looks: list[dict[str, Any]] = []
    look_hashes_by_bodyfit: dict[tuple[str, str], list[str]] = defaultdict(list)
    look_hashes_by_identity: dict[tuple[str, str], list[str]] = defaultdict(list)
    look_hashes_by_outfit: dict[tuple[str, str], list[str]] = defaultdict(list)
    for source_look in source_looks:
        sex = source_look["sex"]
        source_look_id = source_look["look_id"]
        sample = samples_by_look[source_look_id]
        fbx = source_look["fbx"]
        content_hash = fbx["sha256"]
        require(bool(SHA256.fullmatch(content_hash)), f"Invalid Look hash: {source_look_id}")
        require(
            is_portable_source_ref(fbx["source_ref"]),
            f"Unportable Look source_ref: {source_look_id}",
        )
        bodyfit = normalize_id(source_look["bodyfit_id"])
        identity = normalize_id(source_look["identity_id"])
        outfit = outfit_id(sex, source_look["outfit_id"])
        look_hashes_by_bodyfit[(sex, bodyfit)].append(content_hash)
        look_hashes_by_identity[(sex, identity)].append(content_hash)
        look_hashes_by_outfit[(sex, outfit)].append(content_hash)
        looks.append(
            {
                "look_id": normalize_id(source_look_id),
                "source_look_id": source_look_id,
                "sex": sex,
                "bodyfit_id": bodyfit,
                "identity_id": identity,
                "outfit_id": outfit,
                "source_ref": fbx["source_ref"],
                "content_sha256": content_hash,
                "character_blueprint": sample["character_blueprint"],
                "character_blueprint_class": sample["character_blueprint_class"],
                "source_validated_look_id": source_look.get(
                    "source_validated_look_id"
                ),
            }
        )

    assets: list[dict[str, Any]] = []
    for (sex, bodyfit), hashes in sorted(look_hashes_by_bodyfit.items()):
        assets.append(
            make_asset(
                bodyfit,
                "bodyfit",
                sex,
                f"bundle://{bundle_id}/bodyfits/{bodyfit}",
                canonical_sha256(sorted(hashes)),
                {"baked_into_full_reference_looks": True},
            )
        )
    for (sex, identity), hashes in sorted(look_hashes_by_identity.items()):
        assets.append(
            make_asset(
                identity,
                "identity",
                sex,
                f"bundle://{bundle_id}/identities/{identity}",
                canonical_sha256(sorted(hashes)),
                {"baked_into_full_reference_looks": True},
            )
        )
    for (sex, outfit), hashes in sorted(look_hashes_by_outfit.items()):
        assets.append(
            make_asset(
                outfit,
                "outfit",
                sex,
                f"bundle://{bundle_id}/outfits/{outfit}",
                canonical_sha256(sorted(hashes)),
                {"baked_into_full_reference_looks": True},
            )
        )

    actions_by_sex: dict[str, list[str]] = {"female": [], "male": []}
    for source_action in source_actions:
        action_id = normalize_id(source_action["action_id"])
        sex = source_action["sex"]
        exported = source_action["expected_export"]
        actions_by_sex[sex].append(action_id)
        assets.append(
            make_asset(
                action_id,
                "action",
                sex,
                exported["source_ref"],
                exported["sha256"],
                {
                    "source_action_id": source_action["action_id"],
                    "semantic_family": source_action["semantic_family"],
                    "root_motion_policy": source_action["root_motion_policy"],
                    "root_motion_override_asset": source_action.get(
                        "root_motion_override_asset"
                    ),
                    "face_policy": source_action["face_policy"],
                    "window": source_action["window"],
                    "happy_composite_animation": happy_composites[
                        source_action["action_id"]
                    ],
                },
            )
        )

    happy = next(
        (row for row in required.get("expressions") or [] if row.get("expression_id") == "happy"),
        None,
    )
    require(isinstance(happy, dict), "Happy expression is missing")
    assets.append(
        make_asset(
            "happy",
            "expression",
            "unisex",
            f"bundle://{bundle_id}/expressions/happy",
            happy["profile_sha256"],
            {
                "unreal_assets": happy["unreal_assets"],
                "asset_suffix": happy["asset_suffix"],
                "fixed_for_first_batch": True,
            },
        )
    )

    unreal = matrix["unreal"]
    render = matrix["render"]
    scene_id = "tokyo_stylized_v1"
    lighting_id = "tokyo_stylized_lighting_v1"
    anchor_id = "first_batch_actor_anchor_v1"
    render_profile_id = "mrq_1440p30_5s_v1"
    assets.extend(
        [
            make_asset(
                scene_id,
                "scene",
                "unisex",
                unreal["staging_map_package"],
                canonical_sha256(
                    {
                        "source": unreal["source_map_package"],
                        "staging": unreal["staging_map_package"],
                    }
                ),
            ),
            make_asset(
                lighting_id,
                "lighting",
                "unisex",
                f"bundle://{bundle_id}/scene/tokyo_stylized/lighting_v1",
                canonical_sha256(
                    {"scene": unreal["staging_map_package"], "lighting": "frozen_v1"}
                ),
            ),
            make_asset(
                anchor_id,
                "anchor",
                "unisex",
                f"bundle://{bundle_id}/scene/tokyo_stylized/actor_anchor_v1",
                canonical_sha256(
                    {"scene": unreal["staging_map_package"], "anchor": "actor_v1"}
                ),
            ),
            make_asset(
                render_profile_id,
                "render_profile",
                "unisex",
                unreal["render_preset"],
                canonical_sha256(render),
                {"image_sequence": render["image_sequence"], "video_codec": render["video_codec"]},
            ),
        ]
    )
    for section_index, camera_id in enumerate(CAMERA_IDS):
        assets.append(
            make_asset(
                camera_id,
                "camera",
                "unisex",
                f"bundle://{bundle_id}/sequences/firstweek/cameras/{camera_id}",
                canonical_sha256(
                    {
                        "source_sequence": unreal["source_sequence_package"],
                        "camera_id": camera_id,
                        "section_index": section_index,
                    }
                ),
                {
                    "source_sequence": unreal["source_sequence_package"],
                    "section_index": section_index,
                },
            )
        )

    required_hash = canonical_sha256(required)
    matrix_hash = canonical_sha256(matrix)
    input_manifest_sha256 = canonical_sha256(
        {"required_exports": required_hash, "local_render_matrix": matrix_hash}
    )
    return {
        "schema_version": "config_graph_v1",
        "manifest_type": "first_batch_source_manifest",
        "sampling_spec_version": SAMPLING_SPEC_VERSION,
        "source_manifest_id": SOURCE_MANIFEST_ID,
        "batch_id": normalize_id(required["batch_id"]),
        "status": "frozen",
        "release_status": "candidate_pending_chain_render_validation",
        "production_mode": "full_pool",
        "expected_domain_count": 2,
        "expected_nodes": 640,
        "expected_chains": 4000,
        "expected_render_jobs": 640,
        "input_manifest_sha256": input_manifest_sha256,
        "input_manifests": {
            "required_exports": {
                "source_ref": f"repo://00_engine/scripts/dataset/{required_exports_path.name}",
                "sha256": required_hash,
                "hash_mode": "canonical_json_v1",
            },
            "local_render_matrix": {
                "source_ref": f"repo://00_engine/scripts/unreal/{local_matrix_path.name}",
                "sha256": matrix_hash,
                "hash_mode": "canonical_json_v1",
            },
        },
        "assets": sorted(assets, key=lambda row: row["asset_id"]),
        "looks": sorted(looks, key=lambda row: row["look_id"]),
        "actions_by_sex": actions_by_sex,
        "expression_ids": ["happy"],
        "expression_policy": {
            "fixed_expression_id": "happy",
            "editable_feature": False,
            "edit_axis": None,
        },
        "scene_binding": {
            "scene_id": scene_id,
            "lighting_id": lighting_id,
            "anchor_id": anchor_id,
            "camera_ids": {camera_id: camera_id for camera_id in CAMERA_IDS},
        },
        "render_profile": {
            "render_profile_id": render_profile_id,
            "fps": 30,
            "frame_start": 0,
            "duration_frames": 150,
            "resolution": {"width": 2560, "height": 1440},
            "sequence_asset": unreal["workspace_sequence_package"],
            "seed": 0,
        },
        "chain_plan": {
            "quota_matrix": {
                "female_v1": {
                    "progressive_shortest": {"3": 500, "4": 500, "5": 0},
                    "freeform_walk": {"3": 334, "4": 333, "5": 333},
                },
                "male_v1": {
                    "progressive_shortest": {"3": 500, "4": 500, "5": 0},
                    "freeform_walk": {"3": 333, "4": 333, "5": 334},
                },
            },
            "sampler_seed": 20260824,
            "axis_target_shares": {"E1": 0.25, "E2": 0.25, "E3": 0.25, "E7": 0.25},
            "axis_share_tolerance": 0.02,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required-exports", type=Path, default=DEFAULT_REQUIRED_EXPORTS)
    parser.add_argument("--local-matrix", type=Path, default=DEFAULT_LOCAL_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        source = build_source_manifest(
            args.required_exports.resolve(), args.local_matrix.resolve()
        )
        write_json(args.output.resolve(), source)
    except GraphSourceError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "source_manifest_id": source["source_manifest_id"],
                "assets": len(source["assets"]),
                "looks": len(source["looks"]),
                "actions": sum(len(rows) for rows in source["actions_by_sex"].values()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
