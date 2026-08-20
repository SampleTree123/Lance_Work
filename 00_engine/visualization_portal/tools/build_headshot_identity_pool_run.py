from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INDEX = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_identity_pool_10\review_20260810_v2\index.json"
)
DEFAULT_STAGING = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_rm05c_prototype_staging_20260810_v1.json"
)
DEFAULT_MAPPING = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_rm05c_source_mapping_20260810_v1.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")
RUN_ID = "2026-08-10-headshot-identity-pool-10-v2"


def to_url(path_value: str) -> str:
    path = Path(path_value).resolve()
    relative = path.relative_to(LANCE_WORK_ROOT.resolve())
    return "/" + relative.as_posix()


def build_group(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": record["sex"].title(),
        "overview": to_url(record["overview"]),
        "comparisons": {
            key: to_url(value) for key, value in record["comparisons"].items()
        },
        "cases": [
            {
                "id": case["prototype_id"],
                "label": case["prototype_id"],
                "preset_id": case["prototype_id"],
                "parameters": {
                    "profile": "CC5 MetaHuman / 379",
                    "visual_status": case["visual_status"],
                    "source_reference_status": case["source_reference_status"]
                    or "mapped_legacy_record",
                    "bodyfit_integration": "pending",
                },
                "images": {
                    **{key: to_url(value) for key, value in case["views"].items()},
                    **(
                        {"source_reference": to_url(case["source_reference"])}
                        if case["source_reference"]
                        else {}
                    ),
                },
            }
            for case in record["cases"]
        ],
    }


def build_run(
    index: dict[str, Any],
    index_path: Path,
    staging_path: Path,
    mapping_path: Path,
) -> dict[str, Any]:
    groups = {record["sex"]: build_group(record) for record in index["groups"]}
    return {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "Headshot Identity Pool 10",
        "task": "Character Creator / Face Identity",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "pending_review",
        "summary": (
            "Ten CC5 HD Headshot identity candidates: five female and five male. "
            "All passed machine inspection and all source photographs are mapped. "
            "Four are previously accepted and six await human visual review."
        ),
        "decision": {
            "label": "Machine gate passed; RM-05C human review remains open",
            "summary": (
                "The six new projects preserve baked identity, eye structure, "
                "materials, and neutral geometry through CC4 Extended to CC5 "
                "MetaHuman Profile upgrades. Their source mappings are hash-locked; "
                "production selection stays disabled while Face V3 remains active."
            ),
        },
        "tags": [
            "CC5 HD",
            "Headshot",
            "Identity pool",
            "RM-05C",
            "Pending review",
        ],
        "thumbnail": groups["female"]["overview"],
        "metrics": [
            {"label": "Candidates", "value": index["prototype_count"]},
            {"label": "Female", "value": index["female_count"]},
            {"label": "Male", "value": index["male_count"]},
            {"label": "Machine passed", "value": index["machine_passed_count"]},
            {"label": "Visual accepted", "value": index["visual_accepted_count"]},
            {"label": "Source mapped", "value": index["source_reference_mapped_count"]},
            {"label": "Visual review pending", "value": index["visual_pending_count"]},
            {"label": "Morph count pending", "value": 6},
            {"label": "Production enabled", "value": 0},
        ],
        "groups": groups,
        "artifacts": [
            {
                "label": "Visual review instructions",
                "url": to_url(str(index_path.parent / "README.md")),
            },
            {"label": "Review index", "url": to_url(str(index_path))},
            {"label": "Prototype registry", "url": to_url(index["registry"])},
            {
                "label": "Registry machine validation",
                "url": to_url(index["machine_validation"]),
            },
            {"label": "RM-05C staging report", "url": to_url(str(staging_path))},
            {"label": "Source mapping report", "url": to_url(str(mapping_path))},
        ],
        "source": {
            "review_index": to_url(str(index_path)),
            "prototype_registry": to_url(index["registry"]),
            "machine_validation": to_url(index["machine_validation"]),
            "staging_report": to_url(str(staging_path)),
            "source_mapping_report": to_url(str(mapping_path)),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Headshot identity pool portal run")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    args = parser.parse_args()
    index_path = args.index.resolve()
    staging_path = args.staging.resolve()
    mapping_path = args.mapping.resolve()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    run = build_run(index, index_path, staging_path, mapping_path)
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
