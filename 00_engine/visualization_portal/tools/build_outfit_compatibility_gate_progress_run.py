from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from build_outfit_compatibility_gate_run import (
    BODYFIT_ORDER,
    DEFAULT_GATE,
    DEFAULT_PORTAL,
    LANCE_WORK_ROOT,
    VIEW_ORDER,
    OutfitPortalError,
    build_sheet,
    collect_cases,
    read_json,
    safe_id,
    to_url,
    write_json,
)


DEFAULT_INITIAL_VALIDATION = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_compatibility_gate\run_20260815_execution_v1"
    r"\validation_result.json"
)
DEFAULT_RESUME_PLAN = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_outfit_compatibility_resume_plan_20260816_v6.json"
)
DEFAULT_CHUNK_PARENT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_compatibility_gate"
)
DEFAULT_REVIEW_ROOT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_compatibility_gate\cumulative_review_20260815_v1"
)
DEFAULT_RUN_ID = "2026-08-15-outfit-compatibility-gate-progress-v1"
DEFAULT_REVIEW_DECISION = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_outfit_visual_review_20260816_v1.json"
)


def discover_validations(chunk_roots: list[Path] | None = None) -> list[Path]:
    paths: list[Path] = []
    if DEFAULT_RESUME_PLAN.is_file():
        resume_plan = read_json(DEFAULT_RESUME_PLAN)
        paths.extend(
            path.resolve()
            for value in resume_plan.get("checkpoint_validations", [])
            if (path := Path(value)).is_file()
        )
    elif DEFAULT_INITIAL_VALIDATION.is_file():
        paths.append(DEFAULT_INITIAL_VALIDATION.resolve())
    roots = chunk_roots or sorted(
        path
        for path in DEFAULT_CHUNK_PARENT.glob("run_202608*_chunks_v*")
        if path.is_dir()
    )
    for chunk_root in roots:
        paths.extend(
            path.resolve()
            for path in sorted(chunk_root.glob("chunk_*/validation_result.json"))
            if path.is_file()
        )
    return list(dict.fromkeys(paths))


def collect_unique_cases(
    validation_paths: list[Path],
) -> tuple[list[dict[str, Any]], list[Path]]:
    cases_by_id: OrderedDict[str, dict[str, Any]] = OrderedDict()
    loaded_paths = []
    for validation_path in validation_paths:
        validation = read_json(validation_path)
        loaded_paths.append(validation_path)
        for case in collect_cases(validation):
            case_id = case["case_id"]
            existing = cases_by_id.get(case_id)
            if existing is not None:
                if existing["result_path"] != case["result_path"]:
                    raise OutfitPortalError(
                        f"Conflicting duplicate case {case_id}: "
                        f"{existing['result_path']} vs {case['result_path']}"
                    )
                continue
            cases_by_id[case_id] = case
    return list(cases_by_id.values()), loaded_paths


def remove_stale_sheets(sheets_root: Path, generated_sheet_paths: set[Path]) -> None:
    generated = {path.resolve() for path in generated_sheet_paths}
    for stale_sheet in sheets_root.glob("g*.png"):
        if stale_sheet.resolve() not in generated:
            stale_sheet.unlink()


def build_progress_run(
    gate: dict[str, Any],
    gate_path: Path,
    validation_paths: list[Path],
    review_root: Path,
    run_id: str,
    review_decision: dict[str, Any] | None = None,
    review_decision_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cases, loaded_validations = collect_unique_cases(validation_paths)
    cases_by_look: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        cases_by_look.setdefault(case["look_id"], []).append(case)

    look_metadata = OrderedDict(
        (item["look_id"], item) for item in gate["representative_looks"]
    )
    unknown_looks = sorted(set(cases_by_look) - set(look_metadata))
    ignored_cases_outside_gate = sum(
        len(cases_by_look[look_id]) for look_id in unknown_looks
    )
    for look_id in unknown_looks:
        cases_by_look.pop(look_id)

    portal_groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    review_groups = []
    incomplete_looks = []
    published_case_count = 0
    sheets_root = review_root / "sheets"
    generated_sheet_paths: set[Path] = set()

    for look_id, metadata in look_metadata.items():
        records = cases_by_look.get(look_id, [])
        if not records:
            continue
        records.sort(key=lambda item: BODYFIT_ORDER[item["bodyfit_id"]])
        expected_bodyfits = {
            "F01_Lean",
            "F04_Heavy",
            "F05_Short_Average",
        } if records[0]["sex"] == "female" else {
            "M01_Lean",
            "M04_Heavy",
            "M05_Short_Average",
        }
        present_bodyfits = {item["bodyfit_id"] for item in records}
        if present_bodyfits != expected_bodyfits:
            incomplete_looks.append(
                {
                    "look_id": look_id,
                    "expected_bodyfits": sorted(expected_bodyfits),
                    "present_bodyfits": sorted(present_bodyfits),
                }
            )
            continue

        display_label = f"{metadata['family_display_name']} / {metadata['group_id']}"
        group_id = f"g{len(portal_groups) + 1:02d}-{safe_id(look_id)}"
        sheet_path = sheets_root / f"{group_id}.png"
        build_sheet(display_label, records, sheet_path)
        generated_sheet_paths.add(sheet_path.resolve())
        portal_cases = [
            {
                "id": case["preset_id"],
                "label": f"{case['bodyfit_id']} / {display_label}",
                "preset_id": case["preset_id"],
                "parameters": {"asset_count": case["asset_count"]},
                "images": {
                    view_id: to_url(Path(case["images"][view_id]))
                    for view_id in VIEW_ORDER
                },
            }
            for case in records
        ]
        portal_groups[group_id] = {
            "label": display_label,
            "overview": to_url(sheet_path),
            "comparisons": {},
            "cases": portal_cases,
        }
        review_groups.append(
            {
                "group_id": group_id,
                "look_id": look_id,
                "label": display_label,
                "sheet": str(sheet_path),
                "cases": records,
            }
        )
        published_case_count += len(records)

    if not portal_groups:
        raise OutfitPortalError("No complete Look is available for publication")

    # The review root is rebuilt in place as new Looks finish. Remove summary
    # sheets whose old sequence number or Look no longer belongs to this build.
    remove_stale_sheets(sheets_root, generated_sheet_paths)

    expected_total = int(gate["counts"]["test_case_count"])
    machine_success_count = sum(len(items) for items in cases_by_look.values())
    image_count = published_case_count * len(VIEW_ORDER)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    review_index = {
        "schema_version": 1,
        "created_at": now,
        "status": "machine_complete" if published_case_count == expected_total else "in_progress",
        "completed_case_count": published_case_count,
        "machine_success_case_count": machine_success_count,
        "expected_case_count": expected_total,
        "image_count": image_count,
        "complete_look_count": len(portal_groups),
        "ignored_cases_outside_gate": ignored_cases_outside_gate,
        "ignored_looks_outside_gate": unknown_looks,
        "incomplete_looks_not_published": incomplete_looks,
        "groups": review_groups,
        "validation_sources": [str(path) for path in loaded_validations],
        "user_visual_review": (
            review_decision.get("user_visual_review")
            if review_decision is not None
            else None
        ),
        "known_deferred_issues": [
            {
                "id": "hair_headwear_intersection",
                "description": (
                    "Scalp hair can intersect hoods, head wraps, tall collars, or "
                    "other clothing geometry around the head. Record visually and "
                    "resolve later with compatibility rules or alternate hair variants."
                ),
            }
        ],
    }
    index_path = review_root / "index.json"
    write_json(index_path, review_index)
    readme_path = review_root / "README.md"
    readme_path.write_text(
        "# Outfit Compatibility Gate - Cumulative Review\n\n"
        f"- Published complete cases: {published_case_count}/{expected_total}\n"
        f"- Complete Looks: {len(portal_groups)}/{len(look_metadata)}\n"
        f"- Review images: {image_count}\n"
        f"- Ignored historical cases outside this gate: {ignored_cases_outside_gate}\n"
        "- Machine failures in published cases: 0\n\n"
        "Each sheet contains one complete Look with three extreme BodyFits and five "
        "fixed views. Machine success confirms loading, inventory changes, framing, "
        "and capture; it is not a human visual pass.\n\n"
        "Known deferred issue: hair may intersect hoods, head wraps, tall collars, "
        "or other head-adjacent clothing. Do not reject the clothing family solely "
        "for that expected conflict until the hair/clothing compatibility policy is "
        "implemented.\n",
        encoding="utf-8",
    )

    progress_complete = published_case_count == expected_total
    visual_status = (
        (review_decision or {}).get("user_visual_review") or {}
    ).get("overall_status")
    static_visual_accepted = (
        progress_complete
        and visual_status == "static_visual_accepted_dynamic_pending"
    )
    run = {
        "schema_version": 1,
        "id": run_id,
        "title": "CC Outfit Compatibility Gate - Cumulative Progress",
        "task": "Character Creator / Clothing Compatibility",
        "created_at": now,
        "status": (
            "static_visual_accepted_dynamic_pending"
            if static_visual_accepted
            else "pending_review"
        ),
        "summary": (
            f"{published_case_count}/{expected_total} cases across "
            f"{len(portal_groups)}/{len(look_metadata)} complete Looks are available "
            "for human review, with zero machine failures in published rows."
        ),
        "decision": {
            "label": (
                "Static garment review accepted; motion stress is pending"
                if static_visual_accepted
                else (
                    "Machine gate complete; awaiting human review"
                    if progress_complete
                    else "Current machine checkpoint passed; more chunks remain"
                )
            ),
            "summary": (
                "Published rows passed project loading, clothing cleanup, asset "
                "application, inventory verification, hair preservation, framing, "
                "and five-view capture. Hair versus hood/head-wrap intersections are "
                "recorded as a deferred compatibility-rule problem."
            ),
        },
        "tags": [
            "CC5",
            "Outfits",
            "Extreme BodyFits",
            "Five views",
            "Cumulative",
        ],
        "thumbnail": next(iter(portal_groups.values()))["overview"],
        "metrics": [
            {"label": "Completed cases", "value": f"{published_case_count}/{expected_total}"},
            {"label": "Machine passed", "value": published_case_count},
            {"label": "Machine failed", "value": 0},
            {"label": "Review images", "value": image_count},
            {"label": "Completed Looks", "value": len(portal_groups)},
        ],
        "groups": portal_groups,
        "artifacts": [
            {"label": "Review instructions", "url": to_url(readme_path)},
            {"label": "Cumulative review index", "url": to_url(index_path)},
            {"label": "Gate manifest", "url": to_url(gate_path)},
        ] + (
            [
                {
                    "label": "User static review decision",
                    "url": to_url(review_decision_path),
                }
            ]
            if review_decision_path is not None
            else []
        ),
        "source": {
            "gate_manifest": to_url(gate_path),
            "validation_sources": [to_url(path) for path in loaded_validations],
            "review_index": to_url(index_path),
            "review_scope": "complete_looks_only",
        },
    }
    return run, review_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the cumulative outfit compatibility portal run"
    )
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--validation", type=Path, action="append")
    parser.add_argument(
        "--chunk-root",
        type=Path,
        action="append",
        help="Repeat to limit discovery to specific restart-bounded run roots",
    )
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--review-decision",
        type=Path,
        default=DEFAULT_REVIEW_DECISION,
    )
    args = parser.parse_args()

    validation_paths = (
        [path.resolve() for path in args.validation]
        if args.validation
        else discover_validations(
            [path.resolve() for path in args.chunk_root]
            if args.chunk_root
            else None
        )
    )
    if not validation_paths:
        raise OutfitPortalError("No validation checkpoints were found")
    missing = [str(path) for path in validation_paths if not path.is_file()]
    if missing:
        raise OutfitPortalError(f"Validation checkpoints are missing: {missing}")

    gate = read_json(args.gate.resolve())
    review_decision_path = args.review_decision.resolve()
    review_decision = (
        read_json(review_decision_path)
        if review_decision_path.is_file()
        else None
    )
    run, review_index = build_progress_run(
        gate,
        args.gate.resolve(),
        validation_paths,
        args.review_root.resolve(),
        args.run_id,
        review_decision,
        review_decision_path if review_decision is not None else None,
    )
    output = args.portal_root.resolve() / "runs" / args.run_id / "run.json"
    write_json(output, run)
    print(output)
    print(
        "Published {}/{} cases across {} complete Looks from {} checkpoints".format(
            review_index["completed_case_count"],
            review_index["expected_case_count"],
            review_index["complete_look_count"],
            len(review_index["validation_sources"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
