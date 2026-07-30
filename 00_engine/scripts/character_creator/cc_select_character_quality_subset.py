"""Create a deterministic subset of a Character Creator quality batch."""

import argparse
import copy
import datetime
import json
import os


class SelectionError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def select_subset(batch_path, output_path, preset_ids, library_id=None):
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    if not os.path.isfile(batch_path):
        raise SelectionError("Batch file is missing: {}".format(batch_path))
    if os.path.exists(output_path):
        raise SelectionError("Output already exists: {}".format(output_path))
    if not preset_ids or len(preset_ids) != len(set(preset_ids)):
        raise SelectionError("Requested preset IDs must be non-empty and unique")

    source = read_json(batch_path)
    source_presets = source.get("presets") or []
    by_id = {item.get("preset_id"): item for item in source_presets}
    missing = [preset_id for preset_id in preset_ids if preset_id not in by_id]
    if missing:
        raise SelectionError("Preset IDs are missing from the batch: {}".format(missing))

    result = copy.deepcopy(source)
    result["character_count"] = len(preset_ids)
    result["generated_at"] = now()
    result["library_id"] = library_id or "{}_subset_{}".format(
        source.get("library_id") or "character_quality_batch", len(preset_ids)
    )
    result["presets"] = [copy.deepcopy(by_id[preset_id]) for preset_id in preset_ids]
    result["subset_selection"] = {
        "source_library_file": batch_path,
        "source_library_id": source.get("library_id"),
        "preset_ids": list(preset_ids),
    }
    write_json(result, output_path)
    return {
        "success": True,
        "output": output_path,
        "library_id": result["library_id"],
        "character_count": len(preset_ids),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preset-id", action="append", required=True)
    parser.add_argument("--library-id")
    args = parser.parse_args()
    print(
        json.dumps(
            select_subset(
                args.batch,
                args.output,
                args.preset_id,
                library_id=args.library_id,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
