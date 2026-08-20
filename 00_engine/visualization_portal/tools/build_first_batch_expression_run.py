#!/usr/bin/env python3
"""Build and register the first-batch UE expression review portal run."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys


ENGINE_ROOT = Path(r"D:\UE\Lance_Work\00_engine")
PORTAL_ROOT = ENGINE_ROOT / "visualization_portal"
DEFAULT_REPORT = (
    ENGINE_ROOT
    / "outputs"
    / "unreal_character_import"
    / "first_batch_expressions_20260820_v1"
    / "runtime_review"
    / "pie_expression_review.json"
)
RUN_ID = "2026-08-20-ue-first-batch-expressions-v1"


def portal_url(path: Path) -> str:
    relative = path.resolve().relative_to(ENGINE_ROOT.parent.resolve())
    return "/" + relative.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if not report.get("automatic_success"):
        raise RuntimeError("Refusing to register an unsuccessful expression review")

    output_dir = args.report.parent
    contact_sheet = output_dir / "first_batch_expression_contact_sheet.png"
    groups = {}
    for actor_id in ("F02", "M02"):
        for expression_id in ("happy", "angry", "sad"):
            records = [
                item
                for item in report["records"]
                if item["actor_id"] == actor_id
                and item["expression_id"] == expression_id
            ]
            records.sort(key=lambda item: item["target_seconds"])
            groups[f"{actor_id.lower()}-{expression_id}"] = {
                "label": f"{actor_id} / {expression_id.title()}",
                "overview": portal_url(contact_sheet),
                "comparisons": {},
                "cases": [
                    {
                        "id": f"{actor_id.lower()}_{expression_id}_runtime",
                        "label": f"{actor_id} {expression_id} dynamic samples",
                        "preset_id": actor_id,
                        "parameters": {
                            "expression": expression_id,
                            "facial_runtime_mode": "direct_morph_curves",
                            "body_animation": "enabled",
                            "post_process_blueprint": "disabled",
                        },
                        "images": {
                            item["sample_id"]: portal_url(Path(item["image"]["path"]))
                            for item in records
                        },
                    }
                ],
            }

    run = {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "UE First Batch Expressions",
        "task": "Unreal Engine / first-batch facial diversity",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "review",
        "summary": (
            "F02 and M02 passed the automated Happy, Angry, and Sad runtime "
            "composition gate. Visual approval remains pending."
        ),
        "tags": [
            "UE 5.8",
            "CC5",
            "Happy",
            "Angry",
            "Sad",
            "Body + face",
            "Pending visual review",
        ],
        "thumbnail": portal_url(contact_sheet),
        "metrics": [
            {"label": "Expressions", "value": 3},
            {"label": "Actors", "value": 2},
            {"label": "Runtime samples", "value": "18/18"},
            {"label": "Automatic gate", "value": "Passed"},
            {"label": "Visual gate", "value": "Pending"},
        ],
        "groups": groups,
        "artifacts": [
            {"label": "Runtime report", "url": portal_url(args.report)},
            {
                "label": "Expression asset build report",
                "url": portal_url(output_dir.parent / "build_report.json"),
            },
            {
                "label": "Runtime composition build report",
                "url": portal_url(output_dir.parent / "runtime_composition_build.json"),
            },
        ],
        "decision": {
            "label": "Visual review required",
            "summary": (
                "The runtime and curve gates passed. Approve expression strength "
                "and naturalness in the portal before production status changes."
            ),
        },
    }
    run_dir = PORTAL_ROOT / "runs" / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    run_path = run_dir / "run.json"
    run_path.write_text(
        json.dumps(run, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    register = PORTAL_ROOT / "tools" / "register_run.py"
    command = [sys.executable, str(register), str(run_path)]
    if args.replace:
        command.append("--replace")
    subprocess.run(command, check=True)
    print(json.dumps({"run": str(run_path), "success": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
