"""Merge validated male and female CC body Morph snapshots into one catalog."""

import argparse
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_body_morph_catalog_v1.json")


class CatalogBuildError(RuntimeError):
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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(data):
    payload = json.dumps(
        data, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_snapshot(snapshot, sex, path):
    entries = snapshot.get("entries") or []
    expected = snapshot.get("body_and_junction_morph_count")
    if expected != len(entries):
        raise CatalogBuildError(
            "{} snapshot count mismatch: header={}, entries={}: {}".format(
                sex, expected, len(entries), path
            )
        )
    ids = [entry.get("id") for entry in entries]
    if any(not morph_id for morph_id in ids):
        raise CatalogBuildError("{} snapshot contains an empty Morph ID".format(sex))
    if len(ids) != len(set(ids)):
        raise CatalogBuildError("{} snapshot contains duplicate Morph IDs".format(sex))
    return dict((entry["id"], entry) for entry in entries)


def source_record(path, snapshot):
    return {
        "path": path,
        "sha256": sha256_file(path),
        "captured_at": snapshot.get("captured_at"),
        "catalog_fingerprint_sha256": snapshot.get("catalog_fingerprint_sha256"),
        "base_avatar": snapshot.get("base_avatar"),
        "product": snapshot.get("product"),
        "body_morph_count": snapshot.get("body_morph_count"),
        "junction_morph_count": snapshot.get("junction_morph_count"),
        "body_and_junction_morph_count": snapshot.get(
            "body_and_junction_morph_count"
        ),
    }


def sex_values(entry):
    if entry is None:
        return None
    return {
        "minimum": entry.get("minimum"),
        "maximum": entry.get("maximum"),
        "default_weight": entry.get("default_weight"),
    }


def build_catalog(male_path, female_path, output_path):
    male_path = os.path.realpath(os.path.abspath(male_path))
    female_path = os.path.realpath(os.path.abspath(female_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    for path, label in ((male_path, "male"), (female_path, "female")):
        if not os.path.isfile(path):
            raise CatalogBuildError("Missing {} snapshot: {}".format(label, path))

    male = read_json(male_path)
    female = read_json(female_path)
    by_sex = {
        "male": validate_snapshot(male, "male", male_path),
        "female": validate_snapshot(female, "female", female_path),
    }
    all_ids = sorted(set(by_sex["male"]) | set(by_sex["female"]))
    common_ids = set(by_sex["male"]) & set(by_sex["female"])
    morphs = []
    metadata_conflicts = []
    for morph_id in all_ids:
        male_entry = by_sex["male"].get(morph_id)
        female_entry = by_sex["female"].get(morph_id)
        reference = male_entry or female_entry
        if male_entry and female_entry:
            compared = ("display", "classification", "categories")
            differing = [
                field
                for field in compared
                if male_entry.get(field) != female_entry.get(field)
            ]
            if differing:
                metadata_conflicts.append(
                    {"id": morph_id, "differing_fields": differing}
                )
        supported = [
            sex for sex in ("male", "female") if by_sex[sex].get(morph_id)
        ]
        morphs.append(
            {
                "id": morph_id,
                "display": reference.get("display"),
                "classification": reference.get("classification"),
                "categories": reference.get("categories") or [],
                "supported_sexes": supported,
                "sex_values": {
                    "male": sex_values(male_entry),
                    "female": sex_values(female_entry),
                },
            }
        )

    counts = {
        "union": len(all_ids),
        "common": len(common_ids),
        "male": len(by_sex["male"]),
        "female": len(by_sex["female"]),
        "male_only": len(set(by_sex["male"]) - set(by_sex["female"])),
        "female_only": len(set(by_sex["female"]) - set(by_sex["male"])),
        "body": sum(item["classification"] == "body" for item in morphs),
        "junction": sum(item["classification"] == "junction" for item in morphs),
    }
    catalog = {
        "schema_version": 1,
        "catalog_id": "cc5_body_and_junction_morph_catalog_v1",
        "generated_at": now(),
        "status": "validated-runtime-catalog",
        "counts": counts,
        "metadata_conflicts": metadata_conflicts,
        "source_catalogs": {
            "male": source_record(male_path, male),
            "female": source_record(female_path, female),
        },
        "morphs": morphs,
    }
    catalog["catalog_fingerprint_sha256"] = sha256_json(
        {"counts": counts, "morphs": morphs}
    )
    write_json(catalog, output_path)
    return {
        "success": True,
        "output": output_path,
        "counts": counts,
        "metadata_conflict_count": len(metadata_conflicts),
        "catalog_fingerprint_sha256": catalog["catalog_fingerprint_sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--male", required=True, help="Male runtime catalog JSON")
    parser.add_argument("--female", required=True, help="Female runtime catalog JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_catalog(args.male, args.female, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
