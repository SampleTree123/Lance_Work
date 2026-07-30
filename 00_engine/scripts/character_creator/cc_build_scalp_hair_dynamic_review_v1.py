"""Build the final scalp-hair dynamic and static-pressure review."""

import argparse
import collections
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_COMPATIBILITY_REVIEW = os.path.join(
    SCRIPT_DIR,
    "cc_scalp_hair_compatibility_visual_review_v1.json",
)
DEFAULT_DYNAMIC_SUMMARY = os.path.join(
    SCRIPT_DIR,
    "cc_scalp_hair_dynamic_automation_summary_v1.json",
)
DEFAULT_STATIC_SUMMARY = os.path.join(
    SCRIPT_DIR,
    "cc_scalp_hair_static_pressure_summary_v1.json",
)
DEFAULT_DECISIONS = os.path.join(
    SCRIPT_DIR,
    "cc_scalp_hair_dynamic_review_decisions_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_scalp_hair_dynamic_review_v1.json",
)
APPROVED_COMPATIBILITY_STATUS = "approved_static_dynamic_pending"
DYNAMIC_STATUS_MAP = {
    "dynamic_candidate": "dynamic_approved",
    "rigid_short_candidate": "rigid_short_approved",
}


class ReviewError(RuntimeError):
    pass


def now():
    return (
        datetime.datetime.now()
        .astimezone()
        .replace(microsecond=0)
        .isoformat()
    )


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        handle.write("\n")
    os.replace(temporary, path)


def resolved_file(path, label):
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise ReviewError("{} is missing: {}".format(label, path))
    return path


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ReviewError(
                "{} IDs are invalid or duplicated".format(label)
            )
        result[value] = item
    return result


def validate_complete_summary(
    document,
    expected_count,
    label,
    success_key="success",
):
    if (
        int(document.get("total_case_count", -1)) != expected_count
        or int(document.get("completed_case_count", -1))
        != expected_count
        or int(document.get("pending_case_count", -1)) != 0
    ):
        raise ReviewError(
            "{} does not prove {}/{} completion".format(
                label,
                expected_count,
                expected_count,
            )
        )
    cases = document.get("cases") or []
    if len(cases) != expected_count:
        raise ReviewError(
            "{} case count differs from its summary".format(label)
        )
    if any(
        item.get(success_key) is not True
        or item.get("images_complete") is not True
        for item in cases
    ):
        raise ReviewError(
            "{} contains an unsuccessful or incomplete case".format(
                label
            )
        )
    return cases


def compact_dynamic_case(item):
    displacement = item.get("displacement") or {}
    physics = item.get("physics") or {}
    return {
        "active_part_max_center_displacement": displacement.get(
            "active_part_max_center_displacement"
        ),
        "all_part_max_center_displacement": displacement.get(
            "all_part_max_center_displacement"
        ),
        "automation_status": item.get("automation_status"),
        "motion_id": item.get("motion_id"),
        "physics_active_count": physics.get("physics_active_count"),
        "physics_component_count": physics.get(
            "physics_component_count"
        ),
        "preset_id": item.get("preset_id"),
        "sex": item.get("sex"),
    }


def compact_static_case(item):
    return {
        "preset_id": item.get("preset_id"),
        "primary_seed_id": item.get("primary_seed_id"),
        "sex": item.get("sex"),
        "structural_pass": item.get("structural_pass"),
    }


def build(
    compatibility_review_path=DEFAULT_COMPATIBILITY_REVIEW,
    dynamic_summary_path=DEFAULT_DYNAMIC_SUMMARY,
    static_summary_path=DEFAULT_STATIC_SUMMARY,
    decisions_path=DEFAULT_DECISIONS,
    output_path=DEFAULT_OUTPUT,
):
    compatibility_review_path = resolved_file(
        compatibility_review_path,
        "Compatibility visual review",
    )
    dynamic_summary_path = resolved_file(
        dynamic_summary_path,
        "Dynamic automation summary",
    )
    static_summary_path = resolved_file(
        static_summary_path,
        "Static pressure summary",
    )
    decisions_path = resolved_file(
        decisions_path,
        "Dynamic review decisions",
    )
    output_path = os.path.realpath(os.path.abspath(output_path))

    compatibility = read_json(compatibility_review_path)
    dynamic = read_json(dynamic_summary_path)
    static = read_json(static_summary_path)
    decisions = read_json(decisions_path)
    if decisions.get("review_complete") is not True:
        raise ReviewError("Dynamic review decisions are incomplete")

    compatibility_reviews = compatibility.get(
        "presentation_reviews"
    ) or []
    approved = {
        item["asset_id"]: item
        for item in compatibility_reviews
        if item.get("production_status")
        == APPROVED_COMPATIBILITY_STATUS
    }
    if len(compatibility_reviews) != 60 or len(approved) != 58:
        raise ReviewError(
            "Compatibility review must contain 58 approved of 60 assets"
        )

    dynamic_cases = validate_complete_summary(
        dynamic, 74, "Dynamic summary"
    )
    base_cases = indexed(
        [
            item
            for item in dynamic_cases
            if item.get("case_phase") == "base"
        ],
        "asset_id",
        "Dynamic base case",
    )
    cross_cases = [
        item
        for item in dynamic_cases
        if item.get("case_phase") == "cross_presentation"
    ]
    if set(base_cases) != set(approved) or len(cross_cases) != 16:
        raise ReviewError(
            "Dynamic base/cross matrix does not match approved assets"
        )
    cross_by_asset = collections.defaultdict(list)
    for item in cross_cases:
        if item.get("asset_id") not in approved:
            raise ReviewError(
                "Cross-presentation case references an excluded asset"
            )
        cross_by_asset[item["asset_id"]].append(item)

    static_cases = validate_complete_summary(
        static,
        64,
        "Static pressure summary",
        success_key="structural_pass",
    )
    static_by_asset = collections.defaultdict(list)
    for item in static_cases:
        if item.get("asset_id") not in approved:
            raise ReviewError(
                "Static pressure case references an excluded asset"
            )
        if item.get("structural_pass") is not True:
            raise ReviewError(
                "Static pressure case did not structurally pass"
            )
        static_by_asset[item["asset_id"]].append(item)
    if (
        len(static_by_asset) != 16
        or any(len(items) != 4 for items in static_by_asset.values())
    ):
        raise ReviewError(
            "Static pressure evidence must cover 16 assets x 4 faces"
        )

    overrides = decisions.get("asset_overrides") or {}
    unknown_overrides = sorted(set(overrides) - set(approved))
    if unknown_overrides:
        raise ReviewError(
            "Decision overrides reference unknown assets: {}".format(
                unknown_overrides
            )
        )

    assets = []
    for asset_id in sorted(approved):
        compatibility_item = approved[asset_id]
        base = base_cases[asset_id]
        automation_status = base.get("automation_status")
        production_status = DYNAMIC_STATUS_MAP.get(
            automation_status
        )
        if production_status is None:
            raise ReviewError(
                "Unsupported dynamic status for {}: {}".format(
                    asset_id,
                    automation_status,
                )
            )
        override = overrides.get(asset_id) or {}
        risk_tags = sorted(set(override.get("risk_tags") or []))
        notes = list(override.get("notes") or [])
        pressure_cases = static_by_asset.get(asset_id) or []
        if pressure_cases:
            pressure_status = (
                "accepted_with_documented_risk"
                if risk_tags
                else "accepted"
            )
        else:
            pressure_status = "not_selected"
        assets.append(
            {
                "asset_id": asset_id,
                "base_dynamic_case": compact_dynamic_case(base),
                "cross_presentation_cases": [
                    compact_dynamic_case(item)
                    for item in sorted(
                        cross_by_asset.get(asset_id) or [],
                        key=lambda value: value["preset_id"],
                    )
                ],
                "display_name": compatibility_item.get(
                    "display_name"
                ),
                "dynamic_status": production_status,
                "notes": notes,
                "production_status": production_status,
                "risk_tags": risk_tags,
                "static_pressure": {
                    "cases": [
                        compact_static_case(item)
                        for item in sorted(
                            pressure_cases,
                            key=lambda value: value["preset_id"],
                        )
                    ],
                    "status": pressure_status,
                },
                "visual_review_status": "accepted",
            }
        )

    status_counts = collections.Counter(
        item["production_status"] for item in assets
    )
    document = {
        "assets": assets,
        "generated_at": now(),
        "review_basis": list(decisions.get("review_basis") or []),
        "review_id": "cc_scalp_hair_dynamic_review_v1",
        "schema_version": 1,
        "sources": {
            "compatibility_visual_review": compatibility_review_path,
            "decisions": decisions_path,
            "dynamic_automation_summary": dynamic_summary_path,
            "static_pressure_summary": static_summary_path,
        },
        "summary": {
            "approved_asset_count": len(assets),
            "cross_presentation_case_count": len(cross_cases),
            "documented_risk_asset_count": sum(
                bool(item["risk_tags"]) for item in assets
            ),
            "dynamic_base_case_count": len(base_cases),
            "production_status_counts": dict(
                sorted(status_counts.items())
            ),
            "static_pressure_asset_count": len(static_by_asset),
            "static_pressure_case_count": len(static_cases),
            "visual_review_complete": True,
        },
    }
    write_json(document, output_path)
    return document


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build the final CC5 scalp-hair dynamic and "
            "static-pressure review."
        )
    )
    parser.add_argument(
        "--compatibility-review",
        default=DEFAULT_COMPATIBILITY_REVIEW,
    )
    parser.add_argument(
        "--dynamic-summary",
        default=DEFAULT_DYNAMIC_SUMMARY,
    )
    parser.add_argument(
        "--static-summary",
        default=DEFAULT_STATIC_SUMMARY,
    )
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    document = build(
        compatibility_review_path=args.compatibility_review,
        dynamic_summary_path=args.dynamic_summary,
        static_summary_path=args.static_summary,
        decisions_path=args.decisions,
        output_path=args.output,
    )
    print(
        "Built {} scalp-hair production reviews -> {}".format(
            len(document["assets"]),
            os.path.realpath(os.path.abspath(args.output)),
        )
    )


if __name__ == "__main__":
    main()
