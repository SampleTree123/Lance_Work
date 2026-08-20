#!/usr/bin/env python3
"""Stage machine-passed RM-05C Headshot prototypes and update the registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_BATCH = SCRIPT_ROOT / "cc_headshot_rm05c_source_batch_v1.json"
DEFAULT_REGISTRY = SCRIPT_ROOT / "cc_headshot_face_prototype_registry_v1.json"
DEFAULT_ASSET_ROOT = (
    ENGINE_ROOT / "assets" / "character_creator" / "face_prototypes" / "v1"
)
DEFAULT_OUTPUT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "headshot_rm05c_prototype_staging_20260810_v1.json"
)
EVIDENCE_FILES = (
    "blink_bilateral_front.png",
    "jaw_open_front.png",
    "neutral_three_quarter.png",
    "post_pose_neutral_front.png",
    "smile_broad_front.png",
    "smile_medium_front.png",
    "smile_subtle_front.png",
)
ASSEMBLY_ORDER = (
    "load_identity_project",
    "verify_identity_project_sha256",
    "apply_same_sex_bodyfit_body_and_junction_morphs",
    "reconcile_eye_and_teeth_actor_parts",
    "load_canonical_facial_profile",
    "apply_safe_local_face_morphs",
    "apply_bodyfit_head_scale_and_neck_height",
    "apply_skin_and_appearance_assets",
    "run_dynamic_face_and_full_character_validation",
)


class StagingError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_file(path_value: str, label: str) -> Path:
    path = Path(path_value).resolve()
    if not path.is_file():
        raise StagingError(f"{label} is missing: {path}")
    return path


def file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def require_truth(value: Any, label: str) -> None:
    if value is not True:
        raise StagingError(f"{label} did not pass")


def validate_candidate(entry: dict[str, Any]) -> dict[str, Any]:
    prototype_id = str(entry.get("prototype_id") or "")
    sex = entry.get("sex")
    expected_prefix = "F_HS_" if sex == "female" else "M_HS_"
    if sex not in ("female", "male") or not prototype_id.startswith(expected_prefix):
        raise StagingError(f"Invalid prototype identity: {prototype_id}/{sex}")

    source = require_file(entry["source_project"], f"{prototype_id} source project")
    expected_source_hash = str(entry.get("source_project_sha256") or "").lower()
    actual_source_hash = sha256_file(source)
    if actual_source_hash != expected_source_hash:
        raise StagingError(f"{prototype_id} source project SHA-256 changed")

    inspection_result_path = require_file(
        entry["inspection_result"], f"{prototype_id} inspection result"
    )
    inspection_report_path = require_file(
        entry["inspection_report"], f"{prototype_id} inspection report"
    )
    inspection_result = read_json(inspection_result_path)
    inspection = read_json(inspection_report_path)
    require_truth(inspection_result.get("success"), f"{prototype_id} inspection")
    if (
        int(inspection_result.get("success_count", -1)) != 8
        or int(inspection_result.get("failure_count", -1)) != 0
    ):
        raise StagingError(f"{prototype_id} inspection is incomplete")
    inspected_source = inspection.get("source_project") or {}
    if str(inspected_source.get("sha256") or "").lower() != actual_source_hash:
        raise StagingError(f"{prototype_id} inspection source hash differs")
    source_profile = ((inspection.get("subject") or {}).get("facial_profile") or {})
    if (
        source_profile.get("expression_set_uid") != "CC4 Extended"
        or int(source_profile.get("expression_count", -1)) != 160
    ):
        raise StagingError(f"{prototype_id} source Profile is not CC4 Extended/160")
    pose_validation = inspection.get("facial_pose_validation") or {}
    require_truth(
        (pose_validation.get("neutral_eye_integrity") or {}).get("matches"),
        f"{prototype_id} source neutral eye integrity",
    )
    if (pose_validation.get("evidence_liveness") or {}).get("status") != "passed":
        raise StagingError(f"{prototype_id} source pose evidence is not live")

    upgrade_path = require_file(entry["upgrade_report"], f"{prototype_id} upgrade")
    upgrade = read_json(upgrade_path)
    require_truth(upgrade.get("success"), f"{prototype_id} upgrade")
    upgraded_source = upgrade.get("source_project") or {}
    if str(upgraded_source.get("sha256") or "").lower() != actual_source_hash:
        raise StagingError(f"{prototype_id} upgrade source hash differs")
    if upgrade.get("source_project") != upgrade.get("source_project_after"):
        raise StagingError(f"{prototype_id} source project changed during upgrade")
    before = upgrade.get("before") or {}
    after = upgrade.get("after") or {}
    if (
        before.get("expression_set_uid") != "CC4 Extended"
        or int(before.get("expression_count", -1)) != 160
        or after.get("expression_set_uid") != "CC5 MetaHuman"
        or int(after.get("expression_count", -1)) != 379
    ):
        raise StagingError(f"{prototype_id} Profile transition differs")
    require_truth((upgrade.get("profile_gate") or {}).get("matches"), f"{prototype_id} Profile gate")
    identity = upgrade.get("identity_preservation") or {}
    for key in (
        "morphs_unchanged",
        "material_unchanged",
        "eye_structure_unchanged",
        "bounds_unchanged",
    ):
        require_truth(identity.get(key), f"{prototype_id} {key}")
    pose_gate = upgrade.get("pose_gate") or {}
    require_truth(pose_gate.get("matches"), f"{prototype_id} pose gate")
    require_truth(
        (pose_gate.get("neutral_eye_integrity") or {}).get("matches"),
        f"{prototype_id} upgraded neutral eye integrity",
    )

    derived_project = require_file(
        upgrade["derived_project"]["path"], f"{prototype_id} derived project"
    )
    derived_profile = require_file(
        upgrade["derived_facial_profile"]["path"],
        f"{prototype_id} derived Profile",
    )
    rollback_profile = require_file(
        upgrade["source_facial_profile_sidecar"]["path"],
        f"{prototype_id} rollback Profile",
    )
    evidence_root = derived_project.parent
    evidence = {
        name: require_file(str(evidence_root / name), f"{prototype_id} evidence {name}")
        for name in EVIDENCE_FILES
    }
    return {
        "prototype_id": prototype_id,
        "sex": sex,
        "source": source,
        "source_sha256": actual_source_hash,
        "inspection_result": inspection_result_path,
        "inspection_report": inspection_report_path,
        "upgrade_report": upgrade_path,
        "upgrade": upgrade,
        "derived_project": derived_project,
        "derived_profile": derived_profile,
        "rollback_profile": rollback_profile,
        "evidence": evidence,
        "source_reference": entry.get("source_reference"),
    }


def build_manifest(candidate: dict[str, Any], destination: Path) -> dict[str, Any]:
    upgrade = candidate["upgrade"]
    identity = upgrade["identity_preservation"]
    source_reference = candidate.get("source_reference")
    canonical_assets = {
        "identity_project": file_record(destination / "identity_cc5_hd.ccProject"),
        "facial_profile": file_record(destination / "facial_profile_cc5_hd.ccFacialProfile"),
        "rollback_facial_profile": file_record(
            destination / "source_cc4_extended.ccFacialProfile"
        ),
    }
    if source_reference:
        canonical_assets["source_reference"] = file_record(
            destination / "source_reference.jpg"
        )
        reference_status = "pending_user_confirmation"
        original_reference = str(Path(source_reference).resolve())
    else:
        reference_status = "pending_user_mapping"
        original_reference = None
    return {
        "schema_version": 1,
        "prototype_id": candidate["prototype_id"],
        "sex": candidate["sex"],
        "status": "candidate_cc5_hd_rm05c_machine_pass_source_reference_pending_visual_pending",
        "identity_representation": {
            "mode": "baked_geometry_project",
            "nonzero_shaping_morph_count": None,
            "measurement_status": "not_recorded_in_rm05c_batch",
            "slider_vector_reconstruction_authoritative": False,
            "reason": (
                "The Headshot identity is baked into character geometry and cannot "
                "be reconstructed from the shaping slider vector alone. The exact "
                "nonzero slider count was not persisted by the RM-05C inspection."
            ),
        },
        "canonical_assets": canonical_assets,
        "source_reference_match": {
            "original_path": original_reference,
            "confirmation_status": reference_status,
            "required_before_visual_acceptance": True,
        },
        "frozen_source": {
            "project_path": str(candidate["source"]),
            "project_bytes": candidate["source"].stat().st_size,
            "project_sha256": candidate["source_sha256"],
        },
        "profile_upgrade": {
            "mode": upgrade["upgrade_mode"],
            "source_uid": upgrade["before"]["expression_set_uid"],
            "source_expression_count": upgrade["before"]["expression_count"],
            "derived_uid": upgrade["after"]["expression_set_uid"],
            "derived_expression_count": upgrade["after"]["expression_count"],
            "target_path": upgrade["target_facial_profile"]["path"],
            "target_sha256": upgrade["target_facial_profile"]["sha256"],
        },
        "validation": {
            "machine_status": "passed",
            "visual_status": "pending_user_review",
            "static_morphs_unchanged": identity["morphs_unchanged"],
            "material_assignments_unchanged": identity["material_unchanged"],
            "eye_structure_unchanged": identity["eye_structure_unchanged"],
            "neutral_eye_integrity": upgrade["pose_gate"]["neutral_eye_integrity"]["matches"],
            "profile_persisted_after_reload": upgrade["profile_gate"]["matches"],
            "source_project_unchanged": upgrade["source_project_unchanged"],
            "bounds_max_abs_delta": identity["bounds_max_abs_delta"],
            "inspection_result_path": str(candidate["inspection_result"]),
            "inspection_result_sha256": sha256_file(candidate["inspection_result"]),
            "report_path": str(candidate["upgrade_report"]),
            "report_sha256": sha256_file(candidate["upgrade_report"]),
        },
        "assembly_contract": {
            "pipeline": "headshot_project_seed_then_bodyfit_v1",
            "implemented": False,
            "pilot_runtime_available": True,
            "prototype_bodyfit_pilot_validated": False,
            "required_order": list(ASSEMBLY_ORDER),
            "production_blockers": [
                "source_reference_mapping_pending",
                "user_visual_review_pending",
                "prototype_specific_bodyfit_pilot_not_run",
                "production_recipe_integration_pending",
                "rm05c_identity_pool_scale_comparison_pending",
                "rm06_face_recipe_validation_pending",
            ],
        },
    }


def stage_candidate(candidate: dict[str, Any], asset_root: Path) -> Path:
    destination = asset_root / candidate["prototype_id"]
    if destination.exists():
        raise StagingError(f"Prototype destination already exists: {destination}")
    asset_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{candidate['prototype_id']}-", dir=asset_root)
    )
    try:
        shutil.copy2(candidate["derived_project"], temporary / "identity_cc5_hd.ccProject")
        shutil.copy2(
            candidate["derived_profile"], temporary / "facial_profile_cc5_hd.ccFacialProfile"
        )
        shutil.copy2(
            candidate["rollback_profile"], temporary / "source_cc4_extended.ccFacialProfile"
        )
        if candidate.get("source_reference"):
            shutil.copy2(
                require_file(candidate["source_reference"], "source reference"),
                temporary / "source_reference.jpg",
            )
        evidence_dir = temporary / "evidence"
        evidence_dir.mkdir()
        for name, source in candidate["evidence"].items():
            shutil.copy2(source, evidence_dir / name)
        manifest = build_manifest(candidate, temporary)
        # Manifest paths must point at the final immutable package, not its temp path.
        for record in manifest["canonical_assets"].values():
            record["path"] = str(destination / Path(record["path"]).name)
        write_json(manifest, temporary / "prototype.json")
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination / "prototype.json"


def update_registry(
    registry_path: Path, manifest_paths: list[Path]
) -> dict[str, Any]:
    registry = read_json(registry_path)
    if (registry.get("selection_policy") or {}).get("enabled_for_production") is not False:
        raise StagingError("Headshot production selection must remain disabled")
    records = list(registry.get("prototypes") or [])
    existing_ids = {record.get("prototype_id") for record in records}
    for manifest_path in manifest_paths:
        manifest = read_json(manifest_path)
        prototype_id = manifest["prototype_id"]
        if prototype_id in existing_ids:
            raise StagingError(f"Registry already contains {prototype_id}")
        records.append(
            {
                "prototype_id": prototype_id,
                "sex": manifest["sex"],
                "status": manifest["status"],
                "manifest": file_record(manifest_path),
            }
        )
        existing_ids.add(prototype_id)
    records.sort(key=lambda record: (record["sex"], record["prototype_id"]))
    registry["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    registry["status"] = "rm05c_10_candidate_registry_6_source_reference_and_visual_pending"
    policy = registry.setdefault("selection_policy", {})
    policy["enabled_for_production"] = False
    policy["visual_acceptance_status"] = "passed_4_pending_6"
    policy["candidate_count"] = len(records)
    policy["source_reference_mapping_pending_count"] = len(manifest_paths)
    registry["prototypes"] = records
    write_json(registry, registry_path)
    return registry


def stage_batch(
    batch_path: Path,
    registry_path: Path,
    asset_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    batch = read_json(batch_path)
    if int(batch.get("schema_version", -1)) != 1:
        raise StagingError("Unsupported RM-05C batch schema")
    candidates = [validate_candidate(entry) for entry in batch.get("candidates") or []]
    expected = int((batch.get("policy") or {}).get("expected_new_count", -1))
    if len(candidates) != expected or expected <= 0:
        raise StagingError("RM-05C candidate count differs from policy")
    ids = [item["prototype_id"] for item in candidates]
    if len(ids) != len(set(ids)):
        raise StagingError("RM-05C batch contains duplicate prototype IDs")
    destinations = [asset_root / prototype_id for prototype_id in ids]
    existing = [str(path) for path in destinations if path.exists()]
    if existing:
        raise StagingError(
            "RM-05C destination preflight failed: {}".format(", ".join(existing))
        )
    manifests = [stage_candidate(candidate, asset_root) for candidate in candidates]
    registry = update_registry(registry_path, manifests)
    target_total = int((batch.get("policy") or {}).get("target_total_count", -1))
    if len(registry["prototypes"]) != target_total:
        raise StagingError("RM-05C registry total differs from policy")
    result = {
        "schema_version": 1,
        "batch_id": batch["batch_id"],
        "status": "staged_machine_pass_source_reference_and_visual_pending",
        "new_prototype_count": len(manifests),
        "registry_prototype_count": len(registry["prototypes"]),
        "production_enabled": registry["selection_policy"]["enabled_for_production"],
        "manifests": [file_record(path) for path in manifests],
        "registry": file_record(registry_path),
    }
    write_json(result, output_path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = stage_batch(
            args.batch.resolve(),
            args.registry.resolve(),
            args.asset_root.resolve(),
            args.output.resolve(),
        )
    except (OSError, ValueError, KeyError, StagingError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
