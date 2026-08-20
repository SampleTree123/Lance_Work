"""Refresh the two accepted short BodyFits from a hash-locked CC capture."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LIBRARY = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_candidates_v1.json",
)
DEFAULT_CAPTURE = os.path.join(
    os.path.dirname(os.path.dirname(SCRIPT_DIR)),
    "outputs",
    "character_creator_bridge",
    "artifacts",
    "short_bodyfit_source_capture_20260803_01",
    "bodyfit_height_matrix.json",
)
CAPTURE_IDS = {
    "M05_Short_Average_RECHECK": "M05_Short_Average",
    "F05_Short_Average_RECHECK": "F05_Short_Average",
}


class RefreshError(RuntimeError):
    pass


def canonical_path(path):
    return os.path.realpath(os.path.abspath(path))


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def file_modified_at(path):
    return datetime.datetime.fromtimestamp(
        os.path.getmtime(path),
        datetime.timezone.utc,
    ).astimezone().replace(microsecond=0).isoformat()


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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise RefreshError("{} has invalid or duplicate {}".format(label, key))
        result[value] = item
    return result


def validate_entries(entries, classification):
    if not isinstance(entries, list) or not entries:
        if classification == "junction" and entries == []:
            return
        raise RefreshError("Captured {} Morph entries are invalid".format(classification))
    ids = set()
    for entry in entries:
        morph_id = entry.get("id")
        if (
            not isinstance(morph_id, str)
            or not morph_id
            or morph_id in ids
            or entry.get("classification") != classification
        ):
            raise RefreshError("Captured {} Morph entry is invalid".format(classification))
        ids.add(morph_id)


def refresh(library_path, capture_path):
    library_path = canonical_path(library_path)
    capture_path = canonical_path(capture_path)
    library = read_json(library_path)
    capture = read_json(capture_path)
    if (
        capture.get("success") is not True
        or capture.get("success_count") != 2
        or capture.get("failure_count") != 0
        or (capture.get("scene_restoration") or {}).get("restored_exactly") is not True
    ):
        raise RefreshError("Short BodyFit source capture did not pass")

    presets = indexed(library.get("presets") or [], "preset_id", "Short library")
    if set(presets) != set(CAPTURE_IDS.values()):
        raise RefreshError("Short library must contain exactly M05 and F05")
    results = indexed(capture.get("results") or [], "preset_id", "Capture")
    if set(results) != set(CAPTURE_IDS):
        raise RefreshError("Capture does not contain the expected short BodyFits")

    refreshed = copy.deepcopy(library)
    refreshed_presets = indexed(
        refreshed.get("presets") or [],
        "preset_id",
        "Refreshed short library",
    )
    for capture_id, bodyfit_id in CAPTURE_IDS.items():
        result = results[capture_id]
        if result.get("success") is not True:
            raise RefreshError("Capture failed for {}".format(capture_id))
        preset = refreshed_presets[bodyfit_id]
        source_path = canonical_path(preset["source_project"]["path"])
        capture_source = result.get("source_project") or {}
        if canonical_path(capture_source.get("path")) != source_path:
            raise RefreshError("Capture source path differs for {}".format(bodyfit_id))
        actual_hash = sha256_file(source_path)
        actual_bytes = os.path.getsize(source_path)
        if (
            capture_source.get("sha256") != actual_hash
            or int(capture_source.get("bytes", -1)) != actual_bytes
        ):
            raise RefreshError("Capture source identity differs for {}".format(bodyfit_id))

        vectors_path = canonical_path(result.get("source_vectors_path"))
        vectors = read_json(vectors_path)
        body = copy.deepcopy(vectors["groups"]["body"]["entries"])
        junction = copy.deepcopy(vectors["groups"]["junction"]["entries"])
        validate_entries(body, "body")
        validate_entries(junction, "junction")
        preset.update(
            {
                "body_and_junction_fingerprint": vectors[
                    "body_and_junction_fingerprint_sha256"
                ],
                "body_morph_count": len(body),
                "body_only_fingerprint": vectors["groups"]["body"][
                    "fingerprint_sha256"
                ],
                "junction_fingerprint": vectors["groups"]["junction"][
                    "fingerprint_sha256"
                ],
                "junction_morph_count": len(junction),
                "overlay_morph_ids": sorted(
                    [item["id"] for item in body + junction]
                ),
                "source_project": {
                    "bytes": actual_bytes,
                    "modified_at": file_modified_at(source_path),
                    "path": source_path,
                    "sha256": actual_hash,
                },
                "target_body_morphs": body,
                "target_junction_morphs": junction,
            }
        )

    refreshed["generated_at"] = now()
    refreshed["source_refresh_evidence"] = {
        "path": capture_path,
        "sha256": sha256_file(capture_path),
        "scene_restored_exactly": True,
    }
    return refreshed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", default=DEFAULT_LIBRARY)
    parser.add_argument("--capture", default=DEFAULT_CAPTURE)
    parser.add_argument("--output", default=DEFAULT_LIBRARY)
    args = parser.parse_args()
    output_path = canonical_path(args.output)
    document = refresh(args.library, args.capture)
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "output": output_path,
                "preset_ids": [item["preset_id"] for item in document["presets"]],
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
