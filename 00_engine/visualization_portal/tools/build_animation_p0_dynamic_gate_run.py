from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from datetime import datetime
import hashlib
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from PIL import Image, ImageDraw

from build_outfit_compatibility_gate_run import (
    OutfitPortalError,
    load_font,
    read_json,
    safe_id,
    to_url,
    write_json,
)


DEFAULT_GATE = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_p0_animation_dynamic_gate_20260818_v3.json"
)
DEFAULT_VALIDATIONS = [
    Path(
        r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge"
        r"\artifacts\animation_p0_dynamic_gate\run_20260818_v8_lit_review"
        r"\validation_result.json"
    ),
    Path(
        r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge"
        r"\artifacts\animation_p0_lighting_scout"
        r"\start_aligned_20260818_v1\validation_result.json"
    ),
]
DEFAULT_REVIEW_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge"
    r"\artifacts\animation_p0_dynamic_gate\cumulative_review_20260818_v2_lit"
)
DEFAULT_DECISION = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_p0_animation_visual_review_20260818_v1.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
RUN_ID = "2026-08-17-cc-animation-p0-dynamic-gate-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_visual_decision(
    decision_path: Path | None,
    gate_path: Path,
    validation_paths: list[Path],
    expected_case_ids: list[str],
) -> dict[str, Any] | None:
    if decision_path is None or not decision_path.is_file():
        return None
    decision_path = decision_path.resolve()
    decision = read_json(decision_path)
    if decision.get("schema_version") != 1:
        raise OutfitPortalError("P0 visual decision schema_version must be 1")
    review = decision.get("user_visual_review") or {}
    if review.get("overall_status") != "all_16_visual_quality_accepted":
        raise OutfitPortalError("P0 visual decision is not an accepted decision")

    scope = decision.get("review_scope") or {}
    gate_ref = scope.get("gate_manifest") or {}
    if (
        os.path.normcase(str(Path(gate_ref.get("path", "")).resolve()))
        != os.path.normcase(str(gate_path.resolve()))
        or gate_ref.get("sha256") != sha256_file(gate_path)
    ):
        raise OutfitPortalError("P0 visual decision gate binding is stale")

    expected_sources = {
        (
            os.path.normcase(str(path.resolve())),
            sha256_file(path.resolve()),
        )
        for path in validation_paths
    }
    recorded_sources = {
        (
            os.path.normcase(str(Path(item.get("path", "")).resolve())),
            item.get("sha256"),
        )
        for item in scope.get("source_validations") or []
    }
    if recorded_sources != expected_sources:
        raise OutfitPortalError("P0 visual decision validation bindings are stale")

    accepted_ids = review.get("accepted_case_ids") or []
    if sorted(accepted_ids) != sorted(expected_case_ids):
        raise OutfitPortalError("P0 visual decision does not cover the full Pilot")
    if scope.get("reviewed_motion_count") != len(expected_case_ids):
        raise OutfitPortalError("P0 visual decision reviewed count is incorrect")
    decision["_path"] = str(decision_path)
    return decision


def landmark_priority(name: str) -> tuple[int, str]:
    lowered = str(name).lower()
    if lowered in ("root", "cc_base_root", "rl_boneroot"):
        priority = 0
    elif lowered.endswith("_boneroot") or lowered.endswith("_root"):
        priority = 1
    elif "hip" in lowered:
        priority = 2
    elif "pelvis" in lowered:
        priority = 3
    else:
        priority = 4
    return priority, lowered


def horizontal_distance(first: dict[str, Any], last: dict[str, Any]) -> float:
    return math.sqrt(
        (float(last["x"]) - float(first["x"])) ** 2
        + (float(last["y"]) - float(first["y"])) ** 2
    )


def recompute_root_evidence(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if len(samples) < 2:
        return {"classification": "insufficient_samples", "evidence_source": None}
    first_by_name = {
        item.get("name"): item
        for item in samples[0].get("landmark_bones") or []
        if item.get("name") and not item.get("error")
    }
    last_by_name = {
        item.get("name"): item
        for item in samples[-1].get("landmark_bones") or []
        if item.get("name") and not item.get("error")
    }
    common = sorted(set(first_by_name) & set(last_by_name), key=landmark_priority)
    if not common:
        return {"classification": "unavailable", "evidence_source": None}
    landmark = common[0]
    first = first_by_name[landmark]["world_transform"]["translation"]
    last = last_by_name[landmark]["world_transform"]["translation"]
    distance = horizontal_distance(first, last)
    if distance >= 15.0:
        classification = "moving_candidate"
    elif distance <= 5.0:
        classification = "in_place_candidate"
    else:
        classification = "ambiguous"
    return {
        "classification": classification,
        "evidence_source": "landmark_bone_world_translation_recomputed",
        "landmark_bone": landmark,
        "first_to_last_horizontal_distance_cm": distance,
        "thresholds_cm": {"in_place_max": 5.0, "moving_min": 15.0},
    }


def collect_successes(
    validation_paths: list[Path],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    successes: dict[str, dict[str, Any]] = {}
    source_runs = []
    for validation_path in validation_paths:
        validation_path = validation_path.resolve()
        validation = read_json(validation_path)
        source_runs.append(
            {
                "path": str(validation_path),
                "sha256": sha256_file(validation_path),
                "success_count": int(validation.get("success_count", 0)),
                "failure_count": int(validation.get("failure_count", 0)),
            }
        )
        for result in validation.get("results") or []:
            if result.get("success") is True:
                successes[result["case_id"]] = {
                    "result": result,
                    "validation_path": validation_path,
                }
    return successes, source_runs


def validate_case(
    case: dict[str, Any],
    result_record: dict[str, Any],
) -> dict[str, Any]:
    result = result_record["result"]
    report_path = Path(result["motion_report_path"]).resolve()
    report = read_json(report_path)
    samples = report.get("samples") or []
    if len(samples) != 5:
        raise OutfitPortalError(
            f"Expected five samples for {case['case_id']}: {report_path}"
        )
    images: OrderedDict[str, str] = OrderedDict()
    sample_rows = []
    for index, sample in enumerate(samples):
        image_path = Path(sample["image"]).resolve()
        image_record = sample.get("image_record") or {}
        if not image_path.is_file() or image_path.stat().st_size <= 4096:
            raise OutfitPortalError(f"Missing animation image: {image_path}")
        if image_record.get("sha256") != sha256_file(image_path):
            raise OutfitPortalError(f"Animation image hash drift: {image_path}")
        with Image.open(image_path) as opened:
            if opened.size != (1024, 1024):
                raise OutfitPortalError(
                    f"Unexpected animation image size {opened.size}: {image_path}"
                )
        normalized = float(index) / 4.0
        key = f"t{round(normalized * 100):03d}_f{int(sample['frame']):04d}"
        images[key] = to_url(image_path)
        sample_rows.append(
            {
                "frame": int(sample["frame"]),
                "image": str(image_path),
                "key": key,
                "normalized_position": normalized,
            }
        )
    hidden = report.get("hidden_dependency_evidence") or {}
    root_evidence = recompute_root_evidence(samples)
    return {
        "case_id": case["case_id"],
        "filename": case.get("filename"),
        "images": images,
        "motion_length_frames": int(report["clip"]["length_frame"]),
        "facial_channel_class": report["clip"]["facial_channel_class"],
        "hidden_dependencies": hidden.get("added_scene_props") or [],
        "pilot_actor_preset_id": case["pilot_actor_preset_id"],
        "raw_root_evidence": report.get("root_motion_evidence"),
        "recomputed_root_evidence": root_evidence,
        "report_path": str(report_path),
        "review_family": case.get("review_family"),
        "samples": sample_rows,
        "source_format": case.get("source_format"),
        "source_validation": str(result_record["validation_path"]),
    }


def build_sheet(
    case: dict[str, Any],
    output_path: Path,
    visual_accepted: bool = False,
) -> None:
    image_size = 250
    gap = 14
    margin = 20
    header_height = 118
    footer_height = 42
    width = margin * 2 + image_size * 5 + gap * 4
    height = header_height + image_size + footer_height + margin
    canvas = Image.new("RGB", (width, height), "#10151d")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(25, bold=True)
    detail_font = load_font(15)
    caption_font = load_font(14, bold=True)
    draw.text(
        (margin, 18),
        f"{case['pilot_actor_preset_id']} / {case['filename']}",
        fill="#f3f5f7",
        font=title_font,
    )
    root = case["recomputed_root_evidence"]
    detail = (
        f"{case['review_family']} | {case['source_format']} | "
        f"{case['motion_length_frames']} frames | "
        f"root: {root['classification']} ({root.get('landmark_bone')}) | "
        f"face: {case['facial_channel_class']}"
    )
    draw.text((margin, 62), detail, fill="#aab5c4", font=detail_font)
    draw.text(
        (margin, 88),
        (
            "Visual quality accepted by user; loop and reuse policy remain to be assigned."
            if visual_accepted
            else "Visual decision remains pending; inspect silhouette, foot contact, balance, and loop intent."
        ),
        fill="#7f8b9b",
        font=detail_font,
    )
    for index, sample in enumerate(case["samples"]):
        x = margin + index * (image_size + gap)
        with Image.open(sample["image"]) as opened:
            image = opened.convert("RGB").resize(
                (image_size, image_size), Image.Resampling.LANCZOS
            )
        canvas.paste(image, (x, header_height))
        draw.text(
            (x + 8, header_height + image_size + 10),
            f"{round(sample['normalized_position'] * 100)}% / frame {sample['frame']}",
            fill="#cfd6df",
            font=caption_font,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=True)


def restore_inherited_permissions(path: Path) -> None:
    if os.name != "nt":
        return
    completed = subprocess.run(
        ["icacls", str(path), "/inheritance:e", "/T", "/C", "/Q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise OutfitPortalError(
            f"Could not restore portal artifact permissions: "
            f"{(completed.stderr or completed.stdout).strip()}"
        )


def build_run(
    gate_path: Path,
    validation_paths: list[Path],
    review_root: Path,
    portal_root: Path,
    decision_path: Path | None = DEFAULT_DECISION,
    run_id: str = RUN_ID,
    title: str = "CC P0 Animation Dynamic Gate",
    task: str = "Character Creator / Animation Pool P0",
) -> dict[str, Any]:
    gate_path = gate_path.resolve()
    gate = read_json(gate_path)
    gate_cases = [
        {
            **case,
            "pilot_actor_preset_id": preset["preset_id"],
        }
        for preset in gate.get("presets") or []
        for case in preset.get("motion_cases") or []
    ]
    successes, source_runs = collect_successes(validation_paths)
    expected_ids = [case["case_id"] for case in gate_cases]
    missing = sorted(set(expected_ids) - set(successes))
    if missing:
        raise OutfitPortalError(f"P0 animation cases remain incomplete: {missing}")
    cases = [validate_case(case, successes[case["case_id"]]) for case in gate_cases]
    decision = load_visual_decision(
        decision_path,
        gate_path,
        validation_paths,
        expected_ids,
    )
    visual_accepted = decision is not None

    review_root = review_root.resolve()
    sheets_root = review_root / "sheets"
    groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    review_cases = []
    for index, case in enumerate(cases, 1):
        group_id = f"g{index:02d}-{safe_id(case['case_id'])}"
        sheet_path = sheets_root / f"{group_id}.png"
        build_sheet(case, sheet_path, visual_accepted)
        root = case["recomputed_root_evidence"]
        groups[group_id] = {
            "label": f"{case['pilot_actor_preset_id']} / {case['filename']}",
            "overview": to_url(sheet_path),
            "comparisons": {},
            "cases": [
                {
                    "id": case["case_id"],
                    "label": case["filename"],
                    "preset_id": case["pilot_actor_preset_id"],
                    "parameters": {
                        "facial_channel_class": case["facial_channel_class"],
                        "hidden_dependency_count": len(case["hidden_dependencies"]),
                        "motion_length_frames": case["motion_length_frames"],
                        "review_family": case["review_family"],
                        "root_motion_class": root["classification"],
                        "root_motion_landmark": root.get("landmark_bone"),
                        "source_format": case["source_format"],
                    },
                    "images": case["images"],
                }
            ],
        }
        review_cases.append(
            {
                "case_id": case["case_id"],
                "facial_channel_class": case["facial_channel_class"],
                "fps": 60.0,
                "hidden_dependencies": case["hidden_dependencies"],
                "load_status": "succeeded",
                "loop_class": (
                    "pending_policy_assignment"
                    if visual_accepted
                    else "pending_visual_review"
                ),
                "motion_length_frames": case["motion_length_frames"],
                "notes": [
                    "Root evidence recomputed from RL_BoneRoot-priority landmarks."
                ],
                "root_motion_class": root["classification"],
                "root_motion_evidence": root,
                "visual_decision": "accepted" if visual_accepted else "pending",
            }
        )

    root_counts = Counter(
        case["recomputed_root_evidence"]["classification"] for case in cases
    )
    face_counts = Counter(case["facial_channel_class"] for case in cases)
    hidden_count = sum(len(case["hidden_dependencies"]) for case in cases)
    image_count = sum(len(case["images"]) for case in cases)
    consolidated = {
        "schema_version": 1,
        "pilot_id": (gate.get("source_pilot_manifest") or {}).get("pilot_id"),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "success": True,
        "requested_count": len(cases),
        "success_count": len(cases),
        "failure_count": 0,
        "image_count": image_count,
        "production_approved_count": 0,
        "visual_review_status": "accepted" if visual_accepted else "pending",
        "root_motion_counts": dict(root_counts),
        "facial_channel_counts": dict(face_counts),
        "hidden_dependency_count": hidden_count,
        "source_gate": {
            "path": str(gate_path),
            "sha256": sha256_file(gate_path),
        },
        "source_runs": source_runs,
        "cases": cases,
    }
    review = {
        "schema_version": 1,
        "pilot_id": consolidated["pilot_id"],
        "status": (
            "visual_quality_accepted_candidate_registry_pending"
            if visual_accepted
            else "automation_complete_pending_visual_review"
        ),
        "production_approved_count": 0,
        "cases": review_cases,
    }
    consolidated_path = review_root / "consolidated_validation.json"
    review_path = review_root / "dynamic_review_automation_consolidated.json"
    write_json(consolidated_path, consolidated)
    write_json(review_path, review)

    run = {
        "schema_version": 1,
        "id": run_id,
        "title": title,
        "task": task,
        "created_at": consolidated["generated_at"],
        "status": "approved" if visual_accepted else "pending_review",
        "summary": (
            f"{len(cases)}/{len(cases)} motions passed automated checks and "
            "user visual quality review. Loop intent and reuse policy still "
            "require candidate-registry assignment; production approval remains 0."
            if visual_accepted
            else f"{len(cases)}/{len(cases)} motions passed automated CC load, "
            "playback, capture, channel, root-motion, and hidden-prop checks; "
            "visual decisions remain pending. Captures use the Lightroom "
            "camera, source yaw, start-root alignment, and root-follow centering."
        ),
        "tags": [
            "CC5",
            "Animation",
            "P0 Pilot",
            "Dynamic gate",
            "Lighting corrected",
            *( ["Visual accepted"] if visual_accepted else [] ),
        ],
        "thumbnail": next(iter(groups.values()))["overview"],
        "metrics": [
            {
                "label": "Automated pass",
                "value": f"{len(cases)}/{len(cases)}",
            },
            {"label": "Review images", "value": image_count},
            {"label": "Moving / in-place", "value": f"{root_counts['moving_candidate']} / {root_counts['in_place_candidate']}"},
            {"label": "Hidden props", "value": hidden_count},
            {
                "label": "Visual quality",
                "value": (
                    f"{len(cases)}/{len(cases)} accepted"
                    if visual_accepted
                    else "pending"
                ),
            },
        ],
        "groups": groups,
        "artifacts": [
            {"label": "Consolidated validation", "url": to_url(consolidated_path)},
            {"label": "Consolidated review", "url": to_url(review_path)},
            {"label": "Full Pilot gate", "url": to_url(gate_path)},
        ],
    }
    if visual_accepted:
        run["decision"] = {
            "label": "User visual review accepted",
            "summary": (
                f"The user reviewed all {len(cases)} Pilot motions and reported no "
                "unnatural behavior. This closes visual-quality review only; "
                "loop/reuse policy and production admission remain pending."
            ),
        }
        run["artifacts"].append(
            {
                "label": "User visual review decision",
                "url": to_url(Path(decision["_path"])),
            }
        )
    run_path = portal_root.resolve() / "runs" / run_id / "run.json"
    write_json(run_path, run)
    restore_inherited_permissions(review_root)
    restore_inherited_permissions(run_path.parent)
    return {
        "run": run,
        "run_path": str(run_path),
        "consolidated_path": str(consolidated_path),
        "review_path": str(review_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument(
        "--validation",
        action="append",
        type=Path,
        dest="validations",
    )
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--portal", type=Path, default=DEFAULT_PORTAL)
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--title", default="CC P0 Animation Dynamic Gate")
    parser.add_argument(
        "--task", default="Character Creator / Animation Pool P0"
    )
    args = parser.parse_args()
    result = build_run(
        args.gate,
        args.validations or DEFAULT_VALIDATIONS,
        args.review_root,
        args.portal,
        args.decision,
        args.run_id,
        args.title,
        args.task,
    )
    run = result["run"]
    print(
        f"Built {run['id']}: {len(run['groups'])} cases, "
        f"{sum(len(case['images']) for group in run['groups'].values() for case in group['cases'])} images"
    )
    print(result["run_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
