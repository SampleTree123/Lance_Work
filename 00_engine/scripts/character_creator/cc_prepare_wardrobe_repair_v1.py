"""Prepare explicit failed-case retries and aggregate independently verified evidence.

This tool never runs CC, moves exports, or starts another batch. Archive the
listed failed outputs explicitly before invoking the ordinary CC bridge client.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def record(path):
    path = Path(path).resolve(strict=True)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def unchanged(item):
    if record(item["path"]) != item:
        raise ValueError("Evidence changed: " + item["path"])


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write("\n")


def indexed(items, key):
    result = {item[key]: item for item in items}
    if len(result) != len(items):
        raise ValueError("Duplicate case IDs")
    return result


def prepare(source, previous_result, output, export_boundary):
    source, previous_result = Path(source).resolve(), Path(previous_result).resolve()
    output, boundary = Path(output).resolve(), Path(export_boundary).resolve(strict=True)
    if output.exists():
        raise FileExistsError(output)
    manifest, previous = read(source), read(previous_result)
    cases = indexed(manifest["presets"], "preset_id")
    results = indexed(previous["results"], "case_id")
    if set(cases) != set(results) or not previous.get("finished_at"):
        raise ValueError("Require a finished report covering the frozen batch exactly")
    failed = [uid for uid in cases if results[uid].get("success") is False]
    if not failed or any(item.get("success") not in (True, False) for item in results.values()):
        raise ValueError("Require explicitly failed cases")
    snapshots, preserve = [], []
    for uid, item in results.items():
        evidence = record(item["result_path"])
        value = read(evidence["path"])
        if value.get("case_id") != uid or value.get("success") is not item["success"]:
            raise ValueError("Case evidence disagrees with summary: " + uid)
        snapshots.append(evidence)
    for uid in failed:
        production = cases[uid]["production_output"]
        for key in ("project_path", "export_root"):
            path = Path(production[key]).resolve()
            if path == boundary or boundary not in path.parents:
                raise ValueError("Failed output escapes export boundary: " + str(path))
            preserve.append({"case_id": uid, "kind": key, "path": str(path), "exists": path.exists()})
    manifest = copy.deepcopy(manifest)
    manifest["presets"] = [manifest_case for manifest_case in manifest["presets"] if manifest_case["preset_id"] in failed]
    manifest["counts"] = {"case_count": len(failed)}
    manifest["repair_provenance"] = {
        "source_manifest": record(source), "original_summary": record(previous_result),
        "original_case_results": snapshots, "retry_case_ids": failed,
        "preserve_failed_outputs_before_retry": preserve,
        "successful_case_ids_not_reexported": [uid for uid in cases if uid not in failed],
        "output_paths_unchanged": True,
    }
    write_new(output, manifest)
    return manifest["repair_provenance"]


def aggregate(repair_manifest, retry_result, output):
    repair = read(repair_manifest)
    provenance = repair["repair_provenance"]
    for item in [provenance["source_manifest"], provenance["original_summary"], *provenance["original_case_results"]]:
        unchanged(item)
    original_manifest = read(provenance["source_manifest"]["path"])
    cases = indexed(original_manifest["presets"], "preset_id")
    retry_cases = indexed(repair["presets"], "preset_id")
    expected = set(provenance["retry_case_ids"])
    if set(retry_cases) != expected or any(retry_cases[uid] != cases[uid] for uid in expected):
        raise ValueError("Retry altered a frozen case or changed retry coverage")
    previous = read(provenance["original_summary"]["path"])
    retry = read(retry_result)
    retried = indexed(retry["results"], "case_id")
    if (set(retried) != expected or retry.get("success") is not True
            or retry.get("failure_count") != 0 or retry.get("success_count") != len(expected)
            or not retry.get("finished_at")):
        raise ValueError("Retry did not fully succeed with exact case coverage")
    for uid, item in retried.items():
        value = read(item["result_path"])
        if item.get("success") is not True or value.get("success") is not True or value.get("case_id") != uid:
            raise ValueError("Invalid retry case evidence: " + uid)
    result = copy.deepcopy(previous)
    result["results"] = [retried.get(item["case_id"], item) for item in previous["results"]]
    if any(item.get("success") is not True for item in result["results"]):
        raise ValueError("Aggregate still contains failed cases")
    result.update(success=True, success_count=len(cases), failure_count=0, finished_at=retry["finished_at"],
                  completed_count=len(cases), requested_count=len(cases), library_case_count=len(cases),
                  blocked=False, phase="complete", run_id=Path(output).parent.name,
                  summary_path=str(Path(output).resolve()),
                  started_from_library=provenance["source_manifest"]["path"])
    result.pop("undo_warning_guard", None)
    result["evidence_kind"] = "aggregate_of_original_successes_and_explicit_failed_case_retry"
    result["repair_provenance"] = {
        "original_summary": provenance["original_summary"],
        "repair_manifest": record(repair_manifest), "retry_summary": record(retry_result),
        "original_report_not_modified": True,
    }
    write_new(output, result)
    return {"case_count": len(cases), "retry_case_count": len(expected), "output": str(Path(output).resolve())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    for name in ("source", "previous-result", "output", "export-boundary"):
        prepare_parser.add_argument("--" + name, type=Path, required=True)
    aggregate_parser = commands.add_parser("aggregate")
    for name in ("repair-manifest", "retry-result", "output"):
        aggregate_parser.add_argument("--" + name, type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    print(json.dumps((prepare if command == "prepare" else aggregate)(**args), ensure_ascii=True, indent=2))
