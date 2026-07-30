"""Merge successful per-character results from interrupted or chunked CC runs."""

import argparse
import datetime
import json
import os


class MergeError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def discover_results(root):
    discovered = []
    for current_root, unused_dirs, files in os.walk(root):
        if "result.json" not in files:
            continue
        path = os.path.join(current_root, "result.json")
        item = read_json(path)
        item["_source_result_path"] = path
        discovered.append(item)
    return discovered


def merge(batch_path, source_roots, output_root):
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    output_root = os.path.realpath(os.path.abspath(output_root))
    source_roots = [os.path.realpath(os.path.abspath(item)) for item in source_roots]
    if not os.path.isfile(batch_path):
        raise MergeError("Batch file is missing: {}".format(batch_path))
    for root in source_roots:
        if not os.path.isdir(root):
            raise MergeError("Source root is missing: {}".format(root))
    if os.path.isdir(output_root) and os.listdir(output_root):
        raise MergeError("Output root exists and is not empty: {}".format(output_root))

    batch = read_json(batch_path)
    expected = [item["preset_id"] for item in batch.get("presets") or []]
    expected_by_id = dict(
        (item["preset_id"], item) for item in batch.get("presets") or []
    )
    if not expected or len(expected) != len(set(expected)):
        raise MergeError("Batch preset IDs must be non-empty and unique")

    candidates = {}
    for root in source_roots:
        for item in discover_results(root):
            preset_id = item.get("preset_id")
            if preset_id in expected:
                candidates.setdefault(preset_id, []).append(item)

    selected = []
    missing = []
    failed_only = []
    for preset_id in expected:
        items = candidates.get(preset_id) or []
        successful = [item for item in items if item.get("success") is True]
        if successful:
            successful.sort(key=lambda item: item["_source_result_path"])
            chosen = successful[-1]
            chosen["source_result_path"] = chosen.pop("_source_result_path")
            manifest_item = expected_by_id[preset_id]
            for key in (
                "appearance_recipe_id",
                "appearance_asset_ids",
                "appearance_recipe",
            ):
                if chosen.get(key) is None and manifest_item.get(key) is not None:
                    chosen[key] = manifest_item[key]
            selected.append(chosen)
        elif items:
            failed_only.append(preset_id)
        else:
            missing.append(preset_id)
    if missing or failed_only:
        raise MergeError(
            "Incomplete merge; missing={}, failed_only={}".format(missing, failed_only)
        )

    os.makedirs(output_root, exist_ok=True)
    errors = [float(item.get("face_max_abs_error") or 0.0) for item in selected]
    result = {
        "schema_version": 1,
        "run_id": os.path.basename(output_root),
        "started_at": None,
        "finished_at": now(),
        "started_from_library": batch_path,
        "library_id": batch.get("library_id"),
        "requested_count": len(expected),
        "success_count": len(selected),
        "failure_count": 0,
        "success": len(selected) == len(expected),
        "merged_from_chunked_runs": True,
        "source_roots": source_roots,
        "maximum_face_abs_error": max(errors),
        "results": selected,
    }
    output_path = os.path.join(output_root, "validation_result.json")
    write_json(result, output_path)
    return {
        "success": result["success"],
        "output": output_path,
        "result_count": len(selected),
        "maximum_face_abs_error": max(errors),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--source-root", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            merge(args.batch, args.source_root, args.output_root),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
