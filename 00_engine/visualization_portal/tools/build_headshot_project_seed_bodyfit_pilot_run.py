from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INDEX = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_project_seed_bodyfit_pilot\review_20260810_v1\index.json"
)
DEFAULT_VALIDATION = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_headshot_project_seed_bodyfit_pilot_validation_v1.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")
RUN_ID = "2026-08-10-headshot-project-seed-bodyfit-pilot-v1"


def to_url(path_value: str) -> str:
    path = Path(path_value).resolve()
    relative = path.relative_to(LANCE_WORK_ROOT.resolve())
    return "/" + relative.as_posix()


def build_group(record: dict[str, Any]) -> dict[str, Any]:
    sex = record["sex"]
    sheets = record["sheets"]
    views = record["views"]
    return {
        "label": sex.title(),
        "overview": to_url(sheets["assembly"]),
        "comparisons": {
            "dynamic_gate": to_url(sheets["dynamic"]),
            "reload_and_neutral": to_url(sheets["reload"]),
        },
        "cases": [
            {
                "id": record["preset_id"],
                "label": "{} H00 + average BodyFit".format(sex.title()),
                "preset_id": record["preset_id"],
                "parameters": {
                    "head_profile": "H00_BASELINE",
                    "bodyfit": "F02_Average" if sex == "female" else "M02_Average",
                    "expression_set": "CC5 MetaHuman",
                    "expression_count": 379,
                    "dynamic_pose_count": 5,
                },
                "images": {key: to_url(path) for key, path in views.items()},
            }
        ],
    }


def build_run(
    index: dict[str, Any],
    index_path: Path,
    validation: dict[str, Any],
    validation_path: Path,
) -> dict[str, Any]:
    review = validation.get("user_visual_review") or {}
    accepted = review.get("status") == "accepted"
    groups = {record["sex"]: build_group(record) for record in index["groups"]}
    return {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "Headshot Project Seed + BodyFit Pilot",
        "task": "Character Creator / Character Assembly",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "approved" if accepted else "pending_review",
        "summary": (
            "The complete two-case machine gate passed. Review body proportions, "
            "identity continuity, facial motion, eye geometry, and save/reload "
            "consistency before production approval."
        ),
        "decision": {
            "label": (
                "Machine and human review passed"
                if accepted
                else "Machine gate passed; human visual review pending"
            ),
            "summary": (
                "Headshot identity projects were used as baked seeds, canonical "
                "average BodyFits were applied in a fixed order, CC5 HD facial "
                "profiles stayed at 379 expressions, and saved projects reloaded "
                "without Morph or neutral-eye drift."
            ),
        },
        "tags": [
            "CC5 HD",
            "Headshot",
            "BodyFit",
            "Project seed",
            "Pending visual review" if not accepted else "Approved",
        ],
        "thumbnail": groups["female"]["overview"],
        "metrics": [
            {"label": "Machine cases", "value": 2},
            {"label": "Passed cases", "value": 2},
            {"label": "Expressions", "value": 379},
            {"label": "Dynamic poses", "value": 10},
            {"label": "Reload checks", "value": 2},
        ],
        "groups": groups,
        "artifacts": [
            {
                "label": "Visual review instructions",
                "url": to_url(str(index_path.parent / "README.md")),
            },
            {"label": "Review index", "url": to_url(str(index_path))},
            {
                "label": "Machine authority",
                "url": to_url(index["machine_validation"]),
            },
            {
                "label": "Validation authority record",
                "url": to_url(str(validation_path)),
            },
            *[
                {
                    "label": "{} lit capture result".format(group["sex"].title()),
                    "url": to_url(group["lit_capture"]["result"]),
                }
                for group in index["groups"]
            ],
        ],
        "source": {
            "review_index": to_url(str(index_path)),
            "machine_validation": to_url(index["machine_validation"]),
            "validation": to_url(str(validation_path)),
            "visual_source_policy": index["visual_source_policy"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build portal run for Headshot project-seed + BodyFit pilot"
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    args = parser.parse_args()
    index_path = args.index.resolve()
    validation_path = args.validation.resolve()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    run = build_run(index, index_path, validation, validation_path)
    output = args.portal_root / "runs" / run["id"] / "run.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(run, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
