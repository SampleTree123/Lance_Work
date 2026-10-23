"""Repair formally indexed hair cards using the verified masked shader template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parents[1]
REVIEW_ROOT = ENGINE / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
WORKER = ROOT / "ue_repair_hair_masked_materials_v1.py"
REMOTE = ROOT / "ue_remote_exec.py"


def run_one(hair_id: str) -> dict:
    worker = str(WORKER.resolve())
    command = "; ".join([
        f"DM_HAIR_REPAIR_ID={hair_id!r}", f"__file__={worker!r}",
        "exec(compile(open(r%r, 'r', encoding='utf-8').read(), r%r, 'exec'), globals())" % (worker, worker),
    ])
    result = subprocess.run(
        [sys.executable, str(REMOTE), "--project", "datatry_02", "--command", command,
         "--discovery-timeout", "30"], cwd=str(ENGINE.parent),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
    )
    report_path = REVIEW_ROOT / "material_repair_reports" / (hair_id + ".json")
    if not report_path.is_file():
        raise RuntimeError(f"UE did not write a repair report for {hair_id}: {result.stdout[-1000:]} {result.stderr[-1000:]}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if result.returncode or not report["success"]:
        raise RuntimeError(f"Repair failed for {hair_id}: {report.get('error', result.stderr[-1000:])}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    select = parser.add_mutually_exclusive_group(required=True)
    select.add_argument("--hair-id")
    select.add_argument("--all", action="store_true")
    select.add_argument("--remaining", action="store_true")
    args = parser.parse_args()
    plan = json.loads((REVIEW_ROOT / "masked_repair_plan.json").read_text(encoding="utf-8"))
    hair_ids = list(dict.fromkeys(row["hair_id"] for row in plan["rows"]))
    if args.hair_id and args.hair_id not in hair_ids:
        raise ValueError(f"Hairstyle absent from repair plan: {args.hair_id}")
    if args.remaining:
        selected = []
        for hair_id in hair_ids:
            path = REVIEW_ROOT / "material_repair_reports" / (hair_id + ".json")
            if not path.is_file() or not json.loads(path.read_text(encoding="utf-8")).get("success"):
                selected.append(hair_id)
    else:
        selected = hair_ids if args.all else [args.hair_id]
    for index, hair_id in enumerate(selected, 1):
        report = run_one(hair_id)
        print(json.dumps({"completed": index, "total": len(selected), "hair_id": hair_id,
                          "slots": report["expected_slots"], "success": True}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
