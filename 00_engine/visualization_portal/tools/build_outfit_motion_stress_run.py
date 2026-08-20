from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
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
    r"\cc_outfit_motion_stress_gate_20260816_v3.json"
)
DEFAULT_RESULTS_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_motion_stress_gate\run_20260816_v1"
)
DEFAULT_REVIEW_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_motion_stress_gate\cumulative_review_20260816_v1"
)
DEFAULT_REVIEW_DECISION = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_outfit_motion_visual_review_20260817_v1.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
RUN_ID = "2026-08-16-outfit-motion-stress-gate-v1"
PROFILE_LABELS = {
    "locomotion_walk": "Walk",
    "full_body_calibration": "Full-body calibration",
}


def discover_validations(results_root: Path) -> list[Path]:
    if not results_root.is_dir():
        return []
    return sorted(
        (path.resolve() for path in results_root.glob("**/validation_result.json")),
        key=lambda path: (path.stat().st_mtime_ns, str(path).casefold()),
    )


def _sample_key(profile_id: str, normalized_position: float) -> str:
    return f"{profile_id}_{round(float(normalized_position) * 100):02d}"


def _case_from_result(
    result_path: Path,
    preset: dict[str, Any],
) -> dict[str, Any]:
    result = read_json(result_path)
    if result.get("success") is not True:
        raise OutfitPortalError(f"Case result is not successful: {result_path}")
    if result.get("case_id") != preset["case_id"]:
        raise OutfitPortalError(f"Case id mismatch: {result_path}")

    captures = result.get("captures") or []
    if len(captures) != 1:
        raise OutfitPortalError(f"Expected one static reference: {result_path}")
    reference = Path(captures[0]["image"]["path"]).resolve()

    expected_profiles = preset.get("motion_stress_profiles") or []
    actual_profiles = result.get("motion_stress_validations") or []
    actual_by_id = {item.get("profile_id"): item for item in actual_profiles}
    if set(actual_by_id) != {item["profile_id"] for item in expected_profiles}:
        raise OutfitPortalError(f"Motion profile mismatch: {result_path}")

    images: OrderedDict[str, Path] = OrderedDict()
    images["reference"] = reference
    profile_rows: list[dict[str, Any]] = []
    for profile in expected_profiles:
        profile_id = profile["profile_id"]
        normalized = profile.get("sample_normalized_positions") or []
        samples = actual_by_id[profile_id].get("samples") or []
        if len(samples) != len(normalized):
            raise OutfitPortalError(
                f"Motion sample count mismatch for {profile_id}: {result_path}"
            )
        row_images = []
        for position, sample in zip(normalized, samples, strict=True):
            image_path = Path(sample["image"]).resolve()
            key = _sample_key(profile_id, float(position))
            images[key] = image_path
            row_images.append(
                {
                    "frame": int(sample["frame"]),
                    "key": key,
                    "normalized_position": float(position),
                    "path": str(image_path),
                }
            )
        profile_rows.append(
            {
                "profile_id": profile_id,
                "purpose": profile.get("purpose", ""),
                "samples": row_images,
            }
        )

    missing = [str(path) for path in images.values() if not path.is_file()]
    empty = [str(path) for path in images.values() if path.is_file() and path.stat().st_size == 0]
    if missing or empty:
        raise OutfitPortalError(
            f"Case images are missing or empty: missing={missing}, empty={empty}"
        )

    return {
        "bodyfit_id": result["bodyfit_id"],
        "case_id": result["case_id"],
        "images": {key: str(path) for key, path in images.items()},
        "look_id": result["look_id"],
        "motion_profiles": profile_rows,
        "preset_id": result["preset_id"],
        "result_path": str(result_path),
        "sex": result["sex"],
        "subject_id": result["subject_id"],
    }


def collect_case_states(
    gate: dict[str, Any],
    validation_paths: list[Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    presets = {item["case_id"]: item for item in gate.get("presets") or []}
    successful: dict[str, dict[str, Any]] = {}
    failures: dict[str, dict[str, Any]] = {}
    for validation_path in validation_paths:
        validation = read_json(validation_path)
        for compact in validation.get("results") or []:
            case_id = compact.get("case_id")
            if case_id not in presets:
                continue
            if compact.get("success") is True:
                result_path = Path(compact["result_path"]).resolve()
                successful[case_id] = _case_from_result(result_path, presets[case_id])
                failures.pop(case_id, None)
            else:
                failures[case_id] = {
                    "case_id": case_id,
                    "error": compact.get("error"),
                    "validation": str(validation_path),
                }
                successful.pop(case_id, None)
    return successful, failures


def build_sheet(label: str, case: dict[str, Any], output_path: Path) -> None:
    image_size = 300
    gap = 14
    row_label_width = 230
    header_height = 110
    row_height = image_size + 58
    columns = 6
    width = row_label_width + columns * (image_size + gap) + gap
    height = header_height + 2 * row_height + gap
    canvas = Image.new("RGB", (width, height), "#10151d")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(28, bold=True)
    heading_font = load_font(17, bold=True)
    detail_font = load_font(14)
    draw.text((24, 18), label, fill="#f3f5f7", font=title_font)
    draw.text(
        (24, 58),
        f"Diagnostic motion stress / {case['bodyfit_id']} / 11 fixed captures",
        fill="#9ca8b8",
        font=detail_font,
    )
    headers = ["Reference", "0%", "20%", "40%", "60%", "80%"]
    for column, heading in enumerate(headers):
        x = row_label_width + column * (image_size + gap)
        draw.text((x + 6, 82), heading, fill="#cfd6df", font=heading_font)

    reference = Path(case["images"]["reference"])
    rows = case["motion_profiles"]
    for row_index, profile in enumerate(rows):
        y = header_height + row_index * row_height
        draw.rounded_rectangle(
            (gap, y, width - gap, y + row_height - gap),
            radius=6,
            fill="#171e28",
            outline="#2a3544",
            width=1,
        )
        profile_id = profile["profile_id"]
        draw.text(
            (26, y + 32),
            PROFILE_LABELS.get(profile_id, profile_id),
            fill="#f3f5f7",
            font=heading_font,
        )
        draw.text(
            (26, y + 66),
            profile.get("purpose", ""),
            fill="#9ca8b8",
            font=detail_font,
        )
        if row_index == 0:
            with Image.open(reference) as opened:
                thumbnail = opened.convert("RGB").resize(
                    (image_size, image_size), Image.Resampling.LANCZOS
                )
            canvas.paste(thumbnail, (row_label_width, y + 10))
        for column, sample in enumerate(profile["samples"], 1):
            with Image.open(sample["path"]) as opened:
                thumbnail = opened.convert("RGB").resize(
                    (image_size, image_size), Image.Resampling.LANCZOS
                )
            x = row_label_width + column * (image_size + gap)
            canvas.paste(thumbnail, (x, y + 10))
            draw.text(
                (x + 8, y + image_size + 18),
                f"frame {sample['frame']}",
                fill="#9ca8b8",
                font=detail_font,
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=True)


def build_run(
    gate: dict[str, Any],
    validation_paths: list[Path],
    review_root: Path,
    review_decision: dict[str, Any] | None = None,
    review_decision_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    successful, failures = collect_case_states(gate, validation_paths)
    if not successful:
        raise OutfitPortalError("No complete successful motion-stress cases were found")

    look_metadata = {
        item["look_id"]: item for item in gate.get("representative_looks") or []
    }
    preset_order = [item["case_id"] for item in gate.get("presets") or []]
    ordered_cases = [successful[case_id] for case_id in preset_order if case_id in successful]
    sheets_root = review_root / "sheets"
    portal_groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    review_cases = []
    for index, case in enumerate(ordered_cases, 1):
        metadata = look_metadata[case["look_id"]]
        label = f"{metadata['family_display_name']} / {metadata['group_id']}"
        group_id = f"g{index:02d}-{safe_id(case['look_id'])}"
        sheet_path = sheets_root / f"{group_id}.png"
        build_sheet(label, case, sheet_path)
        portal_groups[group_id] = {
            "label": label,
            "overview": to_url(sheet_path),
            "comparisons": {},
            "cases": [
                {
                    "id": case["preset_id"],
                    "label": f"{case['bodyfit_id']} / {label}",
                    "preset_id": case["preset_id"],
                    "parameters": {
                        "bodyfit_id": case["bodyfit_id"],
                        "motion_profiles": [
                            profile["profile_id"] for profile in case["motion_profiles"]
                        ],
                    },
                    "images": {
                        key: to_url(Path(path)) for key, path in case["images"].items()
                    },
                }
            ],
        }
        review_cases.append(
            {
                "group_id": group_id,
                "label": label,
                "sheet": str(sheet_path),
                **case,
            }
        )

    expected = int(gate["counts"]["test_case_count"])
    completed = len(successful)
    motion_images = sum(
        len(profile["samples"])
        for case in ordered_cases
        for profile in case["motion_profiles"]
    )
    machine_state = (
        "pending_review" if completed == expected and not failures else "in_progress"
    )
    visual_review = (review_decision or {}).get("user_visual_review") or {}
    visual_status = visual_review.get("overall_status")
    spot_check_accepted = (
        machine_state == "pending_review"
        and visual_status == "motion_stress_accepted_by_spot_check"
    )
    state = "approved" if spot_check_accepted else machine_state
    review_index = {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": state,
        "machine_status": machine_state,
        "visual_review_status": visual_status,
        "visual_review_method": (
            (review_decision or {}).get("review_scope") or {}
        ).get("review_method"),
        "completed_case_count": completed,
        "expected_case_count": expected,
        "failure_count": len(failures),
        "reference_image_count": completed,
        "motion_image_count": motion_images,
        "validation_paths": [str(path) for path in validation_paths],
        "failures": list(failures.values()),
        "cases": review_cases,
        "scope_note": (
            "These motions are diagnostic probes for clothing deformation only; "
            "they are not the production animation pool."
        ),
    }
    index_path = review_root / "index.json"
    write_json(index_path, review_index)
    readme_path = review_root / "README.md"
    readme_path.write_text(
        "# Outfit Motion Stress Review\n\n"
        f"- Completed: {completed}/{expected} Looks\n"
        f"- Machine failures: {len(failures)}\n"
        f"- Static references: {completed}\n"
        f"- Motion captures: {motion_images}\n"
        "- Review state: " + state + "\n\n"
        + (
            "The user accepted this gate by spot-check and reported no issue. "
            "This is sampled acceptance, not a recorded per-Look signoff for all "
            "53 Looks.\n\n"
            if spot_check_accepted
            else ""
        )
        + "Each sheet contains one static reference, five same-sex walk samples, "
        "and five full-body calibration samples. Inspect garment/body penetration, "
        "layer separation, hem collapse, shoe/foot alignment, and detached parts. "
        "Hair against hoods, headwraps, and high collars is a separately recorded "
        "deferred issue and does not fail this clothing-motion gate.\n\n"
        "The two motions are diagnostic probes. They do not form or approve the "
        "production animation pool.\n",
        encoding="utf-8",
    )
    run = {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "CC Outfit Motion Stress Gate",
        "task": "Character Creator / Clothing Dynamic Compatibility",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": state,
        "summary": (
            f"{completed}/{expected} representative Looks completed on the "
            "same-sex heavy BodyFit with two diagnostic motions."
        ),
        "decision": {
            "label": (
                "User spot-check accepted; no issue reported"
                if spot_check_accepted
                else (
                    "Machine capture complete; visual review pending"
                    if state == "pending_review"
                    else "Diagnostic motion batch in progress"
                )
            ),
            "summary": (
                "The recorded decision is sampled acceptance, not 53 individual "
                "Look signoffs. Hair/headwear overlap remains deferred. Production "
                "animation-pool work is ready but has not started."
                if spot_check_accepted
                else (
                    "Review the 11-image sheet for each Look. Hair/headwear overlap is "
                    "tracked separately. Production animation-pool work has not started."
                )
            ),
        },
        "tags": ["CC5", "Outfits", "Motion stress", "Heavy BodyFit", "Diagnostic"],
        "thumbnail": next(iter(portal_groups.values()))["overview"],
        "metrics": [
            {"label": "Completed Looks", "value": f"{completed}/{expected}"},
            {"label": "Machine failed", "value": len(failures)},
            {"label": "Static references", "value": completed},
            {"label": "Motion images", "value": motion_images},
        ],
        "groups": portal_groups,
        "artifacts": [
            {"label": "Review instructions", "url": to_url(readme_path)},
            {"label": "Review index", "url": to_url(index_path)},
            {"label": "Gate manifest", "url": to_url(DEFAULT_GATE)},
        ] + (
            [
                {
                    "label": "User motion review decision",
                    "url": to_url(review_decision_path),
                }
            ]
            if review_decision_path is not None
            else []
        ),
        "source": {
            "gate_manifest": to_url(DEFAULT_GATE),
            "review_index": to_url(index_path),
            "validation_paths": [to_url(path) for path in validation_paths],
            "motions_are_diagnostic_not_production_pool": True,
            "review_decision": (
                to_url(review_decision_path)
                if review_decision_path is not None
                else None
            ),
        },
    }
    return run, review_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the cumulative outfit motion-stress portal run"
    )
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    parser.add_argument(
        "--review-decision",
        type=Path,
        default=DEFAULT_REVIEW_DECISION,
    )
    args = parser.parse_args()
    gate = read_json(args.gate.resolve())
    validation_paths = discover_validations(args.results_root.resolve())
    if not validation_paths:
        raise OutfitPortalError(
            f"No validation checkpoints found under: {args.results_root.resolve()}"
        )
    review_root = args.review_root.resolve()
    review_decision_path = args.review_decision.resolve()
    review_decision = (
        read_json(review_decision_path) if review_decision_path.is_file() else None
    )
    run, unused_review_index = build_run(
        gate,
        validation_paths,
        review_root,
        review_decision,
        review_decision_path if review_decision is not None else None,
    )
    output = args.portal_root.resolve() / "runs" / RUN_ID / "run.json"
    write_json(output, run)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
