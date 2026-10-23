"""Audit finalized wardrobe batches; export and UE completion are separate counts."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from validate_wardrobe_import_batch_v1 import PHASES, file_hash, validate_case


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_record(record):
    path = Path(record["path"])
    if file_hash(path) != record["sha256"]:
        raise ValueError(f"Evidence or source changed: {path}")
    return path


def mapping_manifest_matches(library, batch, mapping_record):
    current = batch / "ue_import.json"
    if mapping_record["sha256"] != file_hash(current):
        return False
    original = Path(mapping_record["path"]).resolve()
    if original == current.resolve():
        return True
    revision_path = library / "revision.json"
    if not revision_path.exists():
        return False
    inherited = read(revision_path).get("reused_finalized_manifests", {}).get(batch.name)
    if not inherited or inherited["sha256"] != mapping_record["sha256"]:
        return False
    return verify_record(inherited).resolve() == original


def audit(library, reports):
    master = read(library / "cc_export.json")
    known = {p["preset_id"] for p in master["presets"]}
    if len(known) != len(master["presets"]):
        raise ValueError("Duplicate library unit IDs")
    exported, transferred, requested, rows = set(), set(), set(), []
    for batch in sorted(library.glob("batch_*")):
        if not batch.is_dir():
            continue
        cc = read(batch / "cc_export.json")
        unit_ids = {p["preset_id"] for p in cc["presets"]}
        if len(unit_ids) != len(cc["presets"]) or unit_ids & requested or not unit_ids <= known:
            raise ValueError(f"Duplicate or unknown batch unit: {batch.name}")
        requested.update(unit_ids)
        row = {"batch": batch.name, "requested_units": len(unit_ids), "exported_units": 0,
               "transferred_units": 0, "phase_pass_counts": dict.fromkeys(PHASES, 0),
               "unit_ids": sorted(unit_ids)}
        manifest_path = batch / "ue_import.json"
        if manifest_path.exists():
            manifest = read(manifest_path)
            if manifest.get("status") != "cc_export_passed":
                raise ValueError(f"Manifest is not finalized: {batch.name}")
            evidence_path = verify_record(manifest["cc_export_evidence"]["validation_result"])
            if read(evidence_path).get("success") is not True:
                raise ValueError(f"CC result not successful: {batch.name}")
            cases = [c for c in manifest["cases"] if not c.get("reuse_existing_base")]
            if {c["case_id"] for c in cases} != unit_ids or len(cases) != len(unit_ids):
                raise ValueError(f"Finalized case set differs: {batch.name}")
            evidence = []
            for case in cases:
                verify_record(case["cc_result_evidence"])
                for key in ("fbx", "auto_setup_json", "project"):
                    verify_record(case["export"][key])
                exported.add(case["case_id"])
                phases = {}
                for phase in PHASES:
                    path = reports / batch.name / f"{case['case_id']}_{phase}.json"
                    if path.exists():
                        value = read(path)
                        if value.get("success") is True and value.get("case_id") == case["case_id"] and value.get("mode") == phase:
                            row["phase_pass_counts"][phase] += 1
                            phases[phase] = value
                evidence.append((case, phases))
            row["exported_units"] = len(cases)
            row["finalized_manifest"] = {"path": str(manifest_path.resolve()), "sha256": file_hash(manifest_path)}
            mapping_path = reports / batch.name / "wardrobe_modules.json"
            if mapping_path.exists():
                mapping = read(mapping_path)
                if (mapping.get("success") is not True
                        or not mapping_manifest_matches(library, batch, mapping["manifest"])
                        or {c["case_id"] for c in mapping["cases"]} != unit_ids
                        or len(mapping["cases"]) != len(unit_ids)):
                    raise ValueError(f"UE mapping differs from finalized manifest: {batch.name}")
                for record in mapping["evidence"]:
                    verify_record(record)
                for case, phases in evidence:
                    if set(phases) != set(PHASES):
                        raise ValueError(f"Published mapping lacks successful stages: {case['case_id']}")
                    validate_case(case, phases)
                    transferred.add(case["case_id"])
                row["transferred_units"] = len(cases)
                row["ue_mapping"] = {"path": str(mapping_path.resolve()), "sha256": file_hash(mapping_path)}
        rows.append(row)
    return {"schema_version": 1, "audited_at_utc": datetime.now(timezone.utc).isoformat(),
            "success": True, "library": str(library.resolve()), "total_units": len(known),
            "cc_exported_units": len(exported), "ue_transferred_units": len(transferred),
            "exported_pending_ue": sorted(exported-transferred), "not_exported_units": len(known-exported),
            "batches": rows, "fit_or_runtime_approval": "not_inferred_from_transfer"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-dir", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = audit(args.library_dir, args.report_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("total_units", "cc_exported_units", "ue_transferred_units", "not_exported_units")}))


if __name__ == "__main__":
    main()
