"""Build the local visualization-portal run for CC clothing source discovery."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_REVIEW = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\clothing_source_inventory\inventory_20260811_v1\review\index.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")
RUN_ID = "2026-08-11-cc-clothing-source-inventory-v1"


def to_url(path_value: str) -> str:
    path = Path(path_value).resolve()
    relative = path.relative_to(LANCE_WORK_ROOT.resolve())
    return "/" + relative.as_posix()


def build_case(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["package_id"],
        "label": record["label"],
        "preset_id": record["package_id"],
        "parameters": {
            "sex_label": record["sex_label"],
            "source_type": record["source_type"],
            "content_class": record["content_class"],
            "clothing_candidate": record["clothing_candidate"],
            "wearable_count": record["wearable_count"],
            "slots": ", ".join(record["slots"]) or "unresolved",
            "style_tags": ", ".join(record["style_tags"]) or "unclassified",
            "modularity_hint": record["modularity_hint"],
            "look_policy_hint": record["look_policy_hint"],
            "preview_count": record["preview_count"],
            "source_path": record["source_path"],
        },
        "images": {"package_card": to_url(record["card"])},
    }


def build_run(review: dict[str, Any], review_path: Path) -> dict[str, Any]:
    groups = {
        group["group_id"]: {
            "label": group["label"],
            "overview": to_url(group["overview"]),
            "comparisons": {
                key: to_url(value) for key, value in group["pages"].items()
            },
            "cases": [build_case(record) for record in group["cases"]],
        }
        for group in review["groups"]
    }
    inventory_path = Path(review["inventory"]).resolve()
    return {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "CC Clothing Source Inventory v1",
        "task": "Character Creator / Clothing",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "pending_review",
        "summary": (
            "Read-only inventory of the user-sorted female and male clothing "
            "sources. Archive contents and loose CC assets are classified by "
            "actual file type before any CC installation or compatibility test."
        ),
        "decision": {
            "label": "Source discovery complete; production Looks not yet approved",
            "summary": (
                "Package names are not trusted as content truth. Clothing-only, "
                "clothing-with-character, character-only, accessory, and unresolved "
                "packages remain distinct. The next gate selects a small Pilot set "
                "for authored-Look validation in CC."
            ),
        },
        "tags": [
            "CC5",
            "Clothing",
            "RM-08",
            "Source inventory",
            "Pending review",
        ],
        "thumbnail": to_url(review["groups"][0]["overview"]),
        "metrics": [
            {"label": "Packages", "value": review["package_count"]},
            {
                "label": "Clothing candidates",
                "value": review["clothing_candidate_count"],
            },
            {
                "label": "Non-clothing / unresolved",
                "value": review["non_clothing_package_count"],
            },
            {"label": "Wearable entries", "value": review["wearable_count"]},
            {"label": "Copied previews", "value": review["preview_count"]},
            {
                "label": "Exact duplicate ZIP groups",
                "value": review["duplicate_archive_group_count"],
            },
            {"label": "Production Looks approved", "value": 0},
        ],
        "groups": groups,
        "artifacts": [
            {
                "label": "Review instructions",
                "url": to_url(str(review_path.parent / "README.md")),
            },
            {"label": "Review index", "url": to_url(str(review_path))},
            {"label": "Machine inventory", "url": to_url(str(inventory_path))},
        ],
        "source": {
            "review_index": to_url(str(review_path)),
            "machine_inventory": to_url(str(inventory_path)),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build clothing inventory portal run")
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    review_path = args.review.resolve()
    review = json.loads(review_path.read_text(encoding="utf-8"))
    run = build_run(review, review_path)
    output = args.portal_root / "runs" / run["id"] / "run.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
