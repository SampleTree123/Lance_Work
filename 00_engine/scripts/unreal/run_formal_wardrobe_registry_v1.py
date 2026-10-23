"""Inspect or apply a wardrobe selection directly from the formal UE registry.

Examples:
  python run_formal_wardrobe_registry_v1.py --phase inspect --family-id female.pretty_dresses
  python run_formal_wardrobe_registry_v1.py --phase build
  python run_formal_wardrobe_registry_v1.py --phase stage --bodyfit-id F02_Average \
    --family-id female.pretty_dresses --group-id pants --asset-id <shirt> \
    --asset-id <pants> --asset-id <shoes> --hair-id HAIR_HB1_01
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from formal_wardrobe_registry_v1 import (
    MATERIAL_REPAIR_REGISTRY, current_registry_path, read_registry, resolve_selection, validate_registry,
)


ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parents[1]
REMOTE_EXEC = ROOT / "ue_remote_exec.py"
UE_WORKER = ROOT / "ue_formal_wardrobe_runtime_v1.py"
UE_CMD = Path(r"D:\UE\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe")
UE_PROJECT = Path(r"D:\UE\projects\datatry_02\datatry_02.uproject")
REVIEW_PLAN = ENGINE / "outputs/unreal_character_import/asset_restructure_full_20260929_v1/review_plans/wardrobe_coverage/review_plan.json"
REPORT_ROOT = ENGINE / "outputs/unreal_character_import/formal_registry_runtime_v1"
BODYFIT_SEX = {"M02_Average": "male", "F02_Average": "female"}


def parity_check(registry: dict, registry_path: Path | None = None) -> dict:
    # This command reproduces the frozen, unfiltered 173-outfit acceptance.
    # Reviewed-pool survivor/mask mapping has its own publication validation.
    registry_path = registry_path or MATERIAL_REPAIR_REGISTRY
    witness = json.loads(REVIEW_PLAN.read_text(encoding="utf-8"))
    variants = {variant["qualified_variant_id"]: variant
                for bodyfit in witness["bodyfits"]
                for variant in bodyfit["runtime_variants"]}
    rows = witness["review_selection"]["outfits"]
    failures = []
    for row in rows:
        try:
            current = resolve_selection(
                registry, character_sex=row["family_id"].split(".", 1)[0],
                family_id=row["family_id"], group_id=row["group_id"],
                family_asset_ids=row["family_asset_ids"],
                shared_shoe_id=next(iter(row["shared_shoe_ids"]), None),
            )
            expected = variants[row["qualified_variant_id"]]
            new_assignments = {(a["target_component"], a["mesh_path"]) for a in current["assignments"]}
            old_assignments = {(a["target_component"], a["mesh_path"]) for a in expected["assignments"]}
            if new_assignments != old_assignments:
                failures.append({"variant": row["qualified_variant_id"], "reason": "assignment mismatch"})
        except Exception as exc:
            failures.append({"variant": row["qualified_variant_id"], "reason": str(exc)})
    return {"registry_path": str(registry_path), "scope": "historical_unfiltered_173_outfit_parity",
            "registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
            "reviewed_outfits": len(rows), "exact_matches": len(rows) - len(failures),
            "failures": failures, "success": len(rows) == 173 and not failures}


def inspect(registry: dict, family_id: str | None) -> dict:
    if family_id is None:
        return {"summary": validate_registry(registry),
                "families": [{"family_id": f["family_id"], "sex": f["sex"],
                              "groups": ([g["group_id"] for g in f["assembly"]["groups"]]
                                         if f["assembly_mode"] == "slot_groups" else [f["assembly"]["bundle"]["bundle_id"]])}
                             for f in registry["families"]]}
    family = next((f for f in registry["families"] if f["family_id"] == family_id), None)
    if family is None:
        raise ValueError(f"unknown family: {family_id}")
    return family


def registry_for_phase(phase: str, explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        return explicit_path
    return MATERIAL_REPAIR_REGISTRY if phase == "parity" else current_registry_path()


def ue_command(mode: str, bodyfit_id: str, selection: dict | None, registry_path: Path | None = None) -> str:
    registry_path = registry_path or current_registry_path()
    worker = str(UE_WORKER.resolve())
    assignments = [f"DM_FORMAL_MODE={mode!r}", f"DM_FORMAL_BODYFIT_ID={bodyfit_id!r}",
                   f"DM_FORMAL_SELECTION={selection!r}",
                   f"DM_FORMAL_REGISTRY_PATH={str(registry_path.resolve())!r}", f"__file__={worker!r}"]
    assignments.append("exec(compile(open(r%r, 'r', encoding='utf-8').read(), r%r, 'exec'), globals())" % (worker, worker))
    return "; ".join(assignments)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("inspect", "parity", "build", "stage", "verify", "cleanup"), required=True)
    parser.add_argument("--project", default="datatry_02")
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--transport", choices=("auto", "remote", "cmd"), default="auto")
    parser.add_argument("--bodyfit-id", choices=tuple(BODYFIT_SEX))
    parser.add_argument("--family-id")
    parser.add_argument("--group-id")
    parser.add_argument("--asset-id", action="append", default=[])
    parser.add_argument("--shared-shoe-id")
    parser.add_argument("--hair-id")
    return parser.parse_args()


def run_cmd(mode: str, bodyfit_id: str, selection: dict | None, registry_path: Path | None = None) -> dict:
    registry_path = registry_path or current_registry_path()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    commands = REPORT_ROOT / "commands"
    commands.mkdir(exist_ok=True)
    bootstrap = commands / f"{bodyfit_id}_{mode}.py"
    bootstrap.write_text(
        f"import sys\nsys.path.insert(0, {str(ROOT)!r})\n"
        "import ue_formal_wardrobe_runtime_v1 as worker\n"
        f"worker.DM_FORMAL_MODE = {mode!r}\n"
        f"worker.DM_FORMAL_BODYFIT_ID = {bodyfit_id!r}\n"
        f"worker.DM_FORMAL_SELECTION = {selection!r}\n"
        f"worker.DM_FORMAL_REGISTRY_PATH = {str(registry_path.resolve())!r}\n"
        "worker.main()\n", encoding="utf-8",
    )
    log_path = REPORT_ROOT / f"{bodyfit_id}_{mode}_cmd.log"
    command = [str(UE_CMD), str(UE_PROJECT), "-run=pythonscript",
               f"-script={bootstrap}", "-unattended", "-nop4", "-nullrhi",
               "-nosplash", "-DDC-ForceMemoryCache", "-ddc=NoZenLocalFallback"]
    started_at = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, cwd=str(ENGINE.parent),
                                   stdout=log, stderr=subprocess.STDOUT, check=False)
    candidates = sorted((path for path in REPORT_ROOT.glob(f"{bodyfit_id}_{mode}_*.json")
                         if path.stat().st_mtime >= started_at),
                        key=lambda path: path.stat().st_mtime, reverse=True)
    report = json.loads(candidates[0].read_text(encoding="utf-8")) if candidates else None
    return {"exit_code": completed.returncode, "report_path": str(candidates[0]) if candidates else None,
            "log_path": str(log_path), "success": completed.returncode == 0 and bool(report and report["success"])}


def main() -> int:
    args = parse_args()
    args.registry = registry_for_phase(args.phase, args.registry)
    registry = read_registry(args.registry)
    if args.phase == "inspect":
        print(json.dumps(inspect(registry, args.family_id), ensure_ascii=False, indent=2))
        return 0
    if args.phase == "parity":
        result = parity_check(registry, args.registry)
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        (REPORT_ROOT / "reviewed_173_parity.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["success"] else 1
    if args.phase in {"stage", "verify"}:
        if not args.bodyfit_id or not args.family_id or not args.group_id:
            raise ValueError("stage/verify requires bodyfit, family and group IDs")
        selection = {"family_id": args.family_id, "group_id": args.group_id,
                     "family_asset_ids": args.asset_id, "shared_shoe_id": args.shared_shoe_id,
                     "hair_id": args.hair_id}
        resolve_selection(registry, character_sex=BODYFIT_SEX[args.bodyfit_id], **selection)
        bodyfits = [args.bodyfit_id]
    else:
        selection = None
        bodyfits = [args.bodyfit_id] if args.bodyfit_id else list(BODYFIT_SEX)
    transport = args.transport
    if transport == "auto":
        transport = "remote" if args.phase in {"build", "stage", "cleanup"} else "cmd"
    if transport == "cmd" and args.phase in {"build", "stage", "cleanup"}:
        raise ValueError("Blueprint build and persistent stage/cleanup require a live Unreal Editor")
    if args.project != "datatry_02" and transport == "cmd":
        raise ValueError("commandlet transport is configured for datatry_02 only")
    for bodyfit_id in bodyfits:
        if transport == "cmd":
            result = run_cmd(args.phase, bodyfit_id, selection, args.registry)
            print(json.dumps(result, ensure_ascii=False))
            if not result["success"]:
                return 1
            continue
        command = [sys.executable, str(REMOTE_EXEC), "--project", args.project,
                   "--command", ue_command(args.phase, bodyfit_id, selection, args.registry),
                   "--discovery-timeout", "30"]
        completed = subprocess.run(command, cwd=str(ENGINE.parent), capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", check=False)
        if completed.returncode:
            print(completed.stdout[-5000:], file=sys.stderr)
            print(completed.stderr[-5000:], file=sys.stderr)
            return completed.returncode
        envelope = json.loads(completed.stdout)
        markers = [item["output"] for item in envelope["command_result"].get("output", [])
                   if item.get("type") == "Info" and item.get("output", "").startswith("DM_FORMAL_REGISTRY_RESULT=")]
        if len(markers) != 1:
            raise RuntimeError("UE operation returned no unique formal-registry result")
        print(markers[0].strip().split("=", 1)[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
