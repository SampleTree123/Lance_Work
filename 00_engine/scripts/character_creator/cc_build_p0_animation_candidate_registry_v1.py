"""Build the hash-locked RM-09 P0 animation candidate registry."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_PILOT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_pilot"
    / "pilot_20260817_v1"
    / "pilot_manifest.json"
)
DEFAULT_EVIDENCE = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_dynamic_gate"
    / "cumulative_review_20260818_v2_lit"
    / "consolidated_validation.json"
)
DEFAULT_VISUAL_DECISION = SCRIPT_ROOT / "cc_p0_animation_visual_review_20260818_v1.json"
DEFAULT_POLICY = SCRIPT_ROOT / "cc_p0_animation_candidate_policy_20260818_v1.json"
DEFAULT_OUTPUT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_candidate_registry"
    / "registry_20260818_v1"
    / "candidate_registry.json"
)

ALLOWED_SEX_PREFERENCES = {"female_preferred", "male_preferred", "unisex"}
ALLOWED_TEMPORAL_USAGE = {"loop_candidate", "one_shot"}
ALLOWED_ROOT_POLICIES = {"in_place", "preserve_source_root_motion"}
ALLOWED_REUSE_POLICIES = {"replaceable", "paired", "locked"}


class CandidateRegistryError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateRegistryError(f"Could not read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CandidateRegistryError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locked_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise CandidateRegistryError(f"Required file is missing: {resolved}")
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def unique_by_case(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise CandidateRegistryError(f"{label} contains a missing case_id")
        if case_id in result:
            raise CandidateRegistryError(f"{label} contains duplicate case_id: {case_id}")
        result[case_id] = item
    return result


def verify_visual_decision(decision: dict[str, Any]) -> set[str]:
    user_review = decision.get("user_visual_review") or {}
    if user_review.get("overall_status") != "all_16_visual_quality_accepted":
        raise CandidateRegistryError("P0 visual decision is not the accepted full-set decision")
    boundary = decision.get("scope_boundary") or {}
    if not boundary.get("allows_candidate_registry_work_to_start"):
        raise CandidateRegistryError("Visual decision does not allow registry work")
    if boundary.get("approves_motions_as_production_assets"):
        raise CandidateRegistryError("Visual decision leaks production approval")
    accepted = user_review.get("accepted_case_ids") or []
    if len(accepted) != 16 or len(set(accepted)) != 16:
        raise CandidateRegistryError("Visual decision must accept exactly 16 unique cases")

    review_scope = decision.get("review_scope") or {}
    locked_records = [review_scope.get("gate_manifest") or {}]
    locked_records.extend(review_scope.get("source_validations") or [])
    for record in locked_records:
        path = Path(record.get("path", ""))
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise CandidateRegistryError(f"Visual decision source drifted: {path}")
    return set(accepted)


def validate_policy(
    policy: dict[str, Any], expected_ids: set[str]
) -> dict[str, dict[str, Any]]:
    if policy.get("source_pilot_id") != "cc_p0_animation_dynamic_pilot_20260817_v1":
        raise CandidateRegistryError("Policy references an unexpected Pilot")
    policies = unique_by_case(policy.get("cases") or [], "Policy")
    if set(policies) != expected_ids:
        raise CandidateRegistryError("Policy case set differs from the Pilot")
    for case_id, item in policies.items():
        if item.get("sex_preference") not in ALLOWED_SEX_PREFERENCES:
            raise CandidateRegistryError(f"Invalid sex preference: {case_id}")
        if item.get("temporal_usage") not in ALLOWED_TEMPORAL_USAGE:
            raise CandidateRegistryError(f"Invalid temporal usage: {case_id}")
        if item.get("root_motion_policy") not in ALLOWED_ROOT_POLICIES:
            raise CandidateRegistryError(f"Invalid root policy: {case_id}")
        if item.get("facial_reuse_policy") not in ALLOWED_REUSE_POLICIES:
            raise CandidateRegistryError(f"Invalid facial reuse policy: {case_id}")
        if not isinstance(item.get("motion_role"), str) or not item["motion_role"]:
            raise CandidateRegistryError(f"Missing motion role: {case_id}")
        if not isinstance(item.get("known_limits"), list):
            raise CandidateRegistryError(f"known_limits must be a list: {case_id}")
    return policies


def build_registry(
    pilot_path: Path = DEFAULT_PILOT,
    evidence_path: Path = DEFAULT_EVIDENCE,
    decision_path: Path = DEFAULT_VISUAL_DECISION,
    policy_path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:
    pilot_path = pilot_path.resolve()
    evidence_path = evidence_path.resolve()
    decision_path = decision_path.resolve()
    policy_path = policy_path.resolve()
    pilot = read_json(pilot_path)
    evidence = read_json(evidence_path)
    decision = read_json(decision_path)
    policy = read_json(policy_path)

    pilot_id = pilot.get("pilot_id")
    if pilot_id != "cc_p0_animation_dynamic_pilot_20260817_v1":
        raise CandidateRegistryError("Unexpected Pilot ID")
    pilot_cases = unique_by_case(pilot.get("cases") or [], "Pilot")
    if len(pilot_cases) != 16:
        raise CandidateRegistryError("Candidate registry requires the frozen 16-case Pilot")

    if not evidence.get("success") or evidence.get("failure_count") != 0:
        raise CandidateRegistryError("Consolidated dynamic evidence did not pass")
    if evidence.get("production_approved_count") != 0:
        raise CandidateRegistryError("Dynamic evidence leaks production approval")
    if evidence.get("visual_review_status") != "accepted":
        raise CandidateRegistryError("Dynamic evidence has no accepted visual review")
    evidence_cases = unique_by_case(evidence.get("cases") or [], "Evidence")
    if set(evidence_cases) != set(pilot_cases):
        raise CandidateRegistryError("Evidence case set differs from the Pilot")

    accepted_ids = verify_visual_decision(decision)
    if accepted_ids != set(pilot_cases):
        raise CandidateRegistryError("Visual decision case set differs from the Pilot")
    policies = validate_policy(policy, set(pilot_cases))

    entries: list[dict[str, Any]] = []
    for case_id, pilot_case in pilot_cases.items():
        dynamic = evidence_cases[case_id]
        assigned = policies[case_id]
        extracted = pilot_case.get("extracted_file") or {}
        motion_path = Path(extracted.get("path", ""))
        if not motion_path.is_file():
            raise CandidateRegistryError(f"Extracted motion is missing: {case_id}")
        if motion_path.stat().st_size != extracted.get("size_bytes"):
            raise CandidateRegistryError(f"Extracted motion size drifted: {case_id}")
        if sha256_file(motion_path) != extracted.get("sha256"):
            raise CandidateRegistryError(f"Extracted motion hash drifted: {case_id}")

        facial_class = dynamic.get("facial_channel_class")
        if facial_class != "none_detected":
            raise CandidateRegistryError(f"Unexpected facial channels: {case_id}")
        if assigned["facial_reuse_policy"] != "replaceable":
            raise CandidateRegistryError(
                f"No-face Pilot motion must remain replaceable: {case_id}"
            )

        root = dynamic.get("recomputed_root_evidence") or {}
        root_class = root.get("classification")
        expected_root_policy = {
            "moving_candidate": "preserve_source_root_motion",
            "in_place_candidate": "in_place",
        }.get(root_class)
        if expected_root_policy is None:
            raise CandidateRegistryError(f"Unknown Root classification: {case_id}")
        if assigned["root_motion_policy"] != expected_root_policy:
            raise CandidateRegistryError(f"Root policy conflicts with evidence: {case_id}")

        temporal = assigned["temporal_usage"]
        loop_status = (
            "pending_ue_seam_validation"
            if temporal == "loop_candidate"
            else "not_required_for_one_shot"
        )
        frames = int(dynamic.get("motion_length_frames", 0))
        if frames <= 0:
            raise CandidateRegistryError(f"Invalid frame length: {case_id}")
        entries.append(
            {
                "case_id": case_id,
                "motion_id": pilot_case.get("motion_id"),
                "filename": pilot_case.get("filename"),
                "source_format": pilot_case.get("source_format"),
                "source_motion": {
                    "path": str(motion_path.resolve()),
                    "bytes": motion_path.stat().st_size,
                    "sha256": extracted.get("sha256"),
                },
                "motion_role": assigned["motion_role"],
                "sex_preference": assigned["sex_preference"],
                "pilot_actor_preset_id": pilot_case.get("pilot_actor_preset_id"),
                "duration": {
                    "frames": frames,
                    "fps": 60.0,
                    "seconds": round(frames / 60.0, 4),
                },
                "root_motion": {
                    "classification": root_class,
                    "policy": assigned["root_motion_policy"],
                    "horizontal_displacement_cm": round(
                        float(root.get("first_to_last_horizontal_distance_cm", 0.0)), 6
                    ),
                    "ue_validation_status": "pending",
                },
                "facial_channels": "none",
                "facial_reuse_policy": assigned["facial_reuse_policy"],
                "approved_face_pool_binding": "cc5_reusable_face_pool_pending_runtime_gate",
                "hidden_prop_dependency": "none_detected",
                "temporal_usage": temporal,
                "loop_seam_status": loop_status,
                "visual_quality_status": "accepted",
                "known_limits": assigned["known_limits"],
                "candidate_status": "registered_pending_ue_runtime_validation",
                "production_status": "not_approved",
            }
        )

    counts = {
        "candidate_count": len(entries),
        "visual_quality_accepted_count": sum(
            item["visual_quality_status"] == "accepted" for item in entries
        ),
        "loop_candidate_count": sum(
            item["temporal_usage"] == "loop_candidate" for item in entries
        ),
        "one_shot_count": sum(item["temporal_usage"] == "one_shot" for item in entries),
        "moving_count": sum(
            item["root_motion"]["classification"] == "moving_candidate"
            for item in entries
        ),
        "in_place_count": sum(
            item["root_motion"]["classification"] == "in_place_candidate"
            for item in entries
        ),
        "replaceable_face_count": sum(
            item["facial_reuse_policy"] == "replaceable" for item in entries
        ),
        "production_approved_count": 0,
        "by_sex_preference": dict(
            sorted(Counter(item["sex_preference"] for item in entries).items())
        ),
    }
    return {
        "schema_version": 1,
        "registry_id": "cc_p0_animation_candidate_registry_20260818_v1",
        "generated_at": now(),
        "status": "registered_pending_ue_runtime_validation",
        "source_pilot_id": pilot_id,
        "provenance": {
            "pilot_manifest": locked_file(pilot_path),
            "dynamic_evidence": locked_file(evidence_path),
            "visual_decision": locked_file(decision_path),
            "policy_assignment": locked_file(policy_path),
        },
        "policy_summary": {
            "facial_channel_result": "all_none",
            "facial_reuse_result": "all_replaceable",
            "loop_rule": "Only explicit loop candidates proceed to UE seam validation.",
            "one_shot_rule": "One-shot clips are not evaluated as seamless loops.",
            "sex_rule": "Preference guides selection but does not hard-lock retargeting.",
        },
        "counts": counts,
        "candidates": entries,
        "next_gate": {
            "gate_id": "p0_representative_ue_runtime_pilot",
            "required_case_roles": [
                "female_root_motion_walk",
                "male_root_motion_walk",
                "in_place_loop",
                "one_shot_gesture",
            ],
            "requires_generated_clothed_characters": True,
            "production_approval_before_gate": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--visual-decision", type=Path, default=DEFAULT_VISUAL_DECISION)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = build_registry(
        args.pilot,
        args.evidence,
        args.visual_decision,
        args.policy,
    )
    write_json(args.output.resolve(), registry)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
