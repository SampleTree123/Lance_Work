"""Apply an explicit locked-bundle exclusion in a new library, then reuse evidence.

No CC execution, asset deletion, source edits, or successful re-exports occur here.
Ordinary same-input retries remain owned by cc_prepare_wardrobe_repair_v1.py.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil

import cc_build_modular_outfit_pilot_v1 as common
from cc_build_wardrobe_library_v1 import unit_key
from cc_prepare_wardrobe_repair_v1 import indexed, read, record, unchanged, write_new


def revise_documents(registry, cc, ue, approval):
    registry, cc, ue = copy.deepcopy((registry, cc, ue))
    old, excluded = approval["old_unit_id"], approval["exclude_asset_id"]
    if approval.get("approved_by") != "user" or not approval.get("approval"):
        raise ValueError("Explicit user approval required")
    unit = indexed(registry["units"], "unit_id")[old]
    family = next(f for f in registry["families"] if f["document"]["family_id"] == approval["family_id"])
    doc = family["document"]
    modules = indexed(unit["modules"], "asset_id")
    if not unit["locked_bundle"] or doc["assembly_mode"] != "locked_bundle":
        raise ValueError("Only locked-bundle revisions are supported")
    if (approval["retain_asset_id"] == excluded
            or modules[excluded]["sha256"] != approval["exclude_sha256"]
            or modules[approval["retain_asset_id"]]["sha256"] != approval["retain_sha256"]):
        raise ValueError("Approval does not match the source alternatives")
    if (set(modules) != set(doc["assembly"]["bundle"]["required_assets"])
            or set(modules) != set(indexed(doc["assets"], "asset_id"))):
        raise ValueError("Bundle and family contract differ")
    preset = indexed(cc["presets"], "preset_id")[old]
    case = indexed(ue["cases"], "case_id")[old]
    if preset["selected_assets"] != unit["modules"] or case["modules"] != unit["modules"]:
        raise ValueError("Frozen master manifests disagree")
    selected = [m for m in unit["modules"] if m["asset_id"] != excluded]
    new = unit_key(unit["sex"], selected, True)
    if new in {u["unit_id"] for u in registry["units"]}:
        raise ValueError("Revised unit already exists")
    unit.update(unit_id=new, modules=selected)
    for key in ("relative_directory", "ue_case_root"):
        unit[key] = unit[key].replace(old, new)
    for key in ("preset_id", "case_id", "output_directory_name", "look_id"):
        preset[key] = new
    preset["selected_assets"] = copy.deepcopy(selected)
    for key in ("project_path", "export_root", "export_basename"):
        preset["production_output"][key] = preset["production_output"][key].replace(old, new)
    case.update(case_id=new, modules=copy.deepcopy(selected), ue_case_root=unit["ue_case_root"])
    case["planned_export"] = {k: v.replace(old, new) for k, v in case["planned_export"].items()}
    doc["assets"] = [a for a in doc["assets"] if a["asset_id"] != excluded]
    doc["assembly"]["bundle"]["required_assets"] = [m["asset_id"] for m in selected]
    # The revised contract lives separately from the external source directory.
    for asset in doc["assets"]:
        asset["source_relative_path"] = asset["path"]
        asset["path"] = modules[asset["asset_id"]]["source_path"]
    doc["traceability"]["approved_revision"] = copy.deepcopy(approval)
    family["original_manifest"] = copy.deepcopy(family["manifest"])
    registry["asset_bindings"] = [b for b in registry["asset_bindings"]
                                  if not (b["unit_id"] == old and b["asset_id"] == excluded)]
    for binding in registry["asset_bindings"]:
        if binding["unit_id"] == old:
            binding["unit_id"] = new
    registry["counts"]["source_bindings"] = len(registry["asset_bindings"])
    registry["counts"]["unique_modules"] = sum(len(u["modules"]) for u in registry["units"])
    for target in (registry, cc, ue):
        target["revision_id"] = approval["revision_id"]
    cc["counts"] = {**registry["counts"], "case_count": len(cc["presets"])}
    ue["counts"] = {**registry["counts"], "case_count": len(ue["cases"])}
    ue["families"] = copy.deepcopy(registry["families"])
    return registry, cc, ue, new


def prepare(source, destination, approval, previous_result, retry_output):
    source, destination, retry_output = map(lambda p: Path(p).resolve(), (source, destination, retry_output))
    if destination.exists() or retry_output.exists():
        raise FileExistsError("Revision and retry paths must be new")
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("Use independent sibling library directories")
    decision = read(approval)
    batch_name, old = decision["batch"], decision["old_unit_id"]
    if Path(batch_name).name != batch_name or not batch_name.startswith("batch_"):
        raise ValueError("Invalid batch directory")
    originals = {name: read(source / name) for name in ("wardrobe_registry.json", "cc_export.json", "ue_import.json")}
    registry, cc, ue, new = revise_documents(*originals.values(), decision)
    previous = read(previous_result)
    rows = indexed(previous["results"], "case_id")
    batch_cc = read(source / batch_name / "cc_export.json")
    old_presets = indexed(batch_cc["presets"], "preset_id")
    if (set(rows) != set(old_presets) or not previous.get("finished_at")
            or {uid for uid, row in rows.items() if row.get("success") is not True} != {old}
            or rows[old].get("success") is not False):
        raise ValueError("Require exactly the approved failed case in a completed batch")
    master_presets = indexed(originals["cc_export.json"]["presets"], "preset_id")
    if any(preset != master_presets[uid] for uid, preset in old_presets.items()):
        raise ValueError("Batch presets differ from frozen master")
    new_preset = indexed(cc["presets"], "preset_id")[new]
    boundary = Path(cc["output_root"]).resolve(strict=True)
    for key in ("project_path", "export_root"):
        path = Path(new_preset["production_output"][key]).resolve()
        if boundary not in path.parents:
            raise ValueError("Revised output escapes export root")
        if path.exists():
            raise FileExistsError(path)
    records = [record(approval), record(previous_result)]
    for uid, row in rows.items():
        evidence = record(row["result_path"])
        value = read(evidence["path"])
        if value.get("case_id") != uid or value.get("success") is not row["success"]:
            raise ValueError("Original case evidence differs")
        records.append(evidence)
    family = next(f for f in registry["families"] if f["document"]["family_id"] == decision["family_id"])
    common.verify_file(family["original_manifest"], "Original family contract")
    for asset in family["document"]["assets"]:
        common.verify_file(asset, "Approved bundle member")
    source_files = [source / name for name in originals]
    source_files += sorted(source.glob("batch_*/*.json"))
    records += [record(path) for path in source_files]
    if (source / batch_name / "ue_import.json").exists():
        raise ValueError("Cannot replace an already finalized bundle")
    # Preserve all successful batch documents byte-for-byte; binaries stay in place.
    reused = {}
    for path in source_files:
        if path.parent == source or path.parent.name == batch_name:
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        if path.name == "ue_import.json":
            reused[path.parent.name] = record(path)
    contract_path = destination / "family_contracts" / (decision["family_id"] + ".json")
    write_new(contract_path, family["document"])
    family["manifest"] = common.verify_file({"path": str(contract_path)}, "Revised family contract")
    ue["families"] = copy.deepcopy(registry["families"])
    for name, doc in zip(originals, (registry, cc, ue)):
        write_new(destination / name, doc)
    batch_cc["revision_id"] = decision["revision_id"]
    batch_cc["presets"] = [copy.deepcopy(new_preset) if p["preset_id"] == old else p for p in batch_cc["presets"]]
    batch_ue = copy.deepcopy(ue)
    selected_ids = {p["preset_id"] for p in batch_cc["presets"]}
    batch_ue["cases"] = [c for c in ue["cases"] if c["case_id"] in selected_ids]
    batch_ue["counts"] = {"case_count": len(selected_ids)}
    write_new(destination / batch_name / "cc_export.json", batch_cc)
    write_new(destination / batch_name / "ue_pending.json", batch_ue)
    retry = copy.deepcopy(batch_cc)
    retry.update(presets=[copy.deepcopy(new_preset)], counts={"case_count": 1})
    write_new(retry_output, retry)
    new_files = [destination / name for name in originals] + [
        contract_path, destination / batch_name / "cc_export.json",
        destination / batch_name / "ue_pending.json", retry_output]
    revision = {
        "schema_version": 1, "revision_id": decision["revision_id"], "approval": record(approval),
        "source_library": str(source), "source_records": records,
        "revised_records": [record(path) for path in new_files],
        "reused_finalized_manifests": reused, "batch": batch_name,
        "superseded_case_id": old, "revised_case_id": new,
        "original_summary": record(previous_result), "retry_manifest": record(retry_output),
        "successful_case_ids_not_reexported": [uid for uid in rows if uid != old],
        "source_files_unchanged": True, "ue_import_authorized": False,
    }
    write_new(destination / "revision.json", revision)
    return {"new_case_id": new, "retry_manifest": str(retry_output), "library": str(destination)}


def aggregate(revision, retry_result, output):
    plan = read(revision)
    for item in [*plan["source_records"], *plan["revised_records"]]:
        unchanged(item)
    old, new = plan["superseded_case_id"], plan["revised_case_id"]
    previous, retry = read(plan["original_summary"]["path"]), read(retry_result)
    rows = indexed(retry["results"], "case_id")
    if (set(rows) != {new} or retry.get("success") is not True or retry.get("success_count") != 1
            or retry.get("failure_count") != 0 or not retry.get("finished_at")):
        raise ValueError("Revised export has not succeeded with exact coverage")
    actual = read(rows[new]["result_path"])
    if rows[new].get("success") is not True or actual.get("success") is not True or actual.get("case_id") != new:
        raise ValueError("Invalid revised case evidence")
    result = copy.deepcopy(previous)
    result["results"] = [rows[new] if row["case_id"] == old else row for row in previous["results"]]
    if any(row.get("success") is not True for row in result["results"]):
        raise ValueError("Unresolved aggregate failure")
    count = len(result["results"])
    result.update(success=True, failure_count=0, success_count=count, completed_count=count,
                  requested_count=count, library_case_count=count, blocked=False, phase="complete",
                  finished_at=retry["finished_at"], run_id=Path(output).parent.name,
                  summary_path=str(Path(output).resolve()),
                  started_from_library=str(Path(revision).parent / plan["batch"] / "cc_export.json"))
    result.pop("undo_warning_guard", None)
    result["evidence_kind"] = "aggregate_of_unchanged_successes_and_user_approved_bundle_revision"
    result["revision_provenance"] = {"revision": record(revision), "retry_summary": record(retry_result),
                                     "revised_case_result": record(rows[new]["result_path"]),
                                     "original_summary": plan["original_summary"]}
    write_new(output, result)
    return {"success_count": count, "reexported_cases": [new], "output": str(output)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    for name in ("source", "destination", "approval", "previous-result", "retry-output"):
        prepare_parser.add_argument("--" + name, type=Path, required=True)
    aggregate_parser = commands.add_parser("aggregate")
    for name in ("revision", "retry-result", "output"):
        aggregate_parser.add_argument("--" + name, type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    print(json.dumps((prepare if command == "prepare" else aggregate)(**args), indent=2))
