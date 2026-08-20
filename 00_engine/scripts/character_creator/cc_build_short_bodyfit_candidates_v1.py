"""Build the two short-adult BodyFit candidates from reviewed projects."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_LIBRARY_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_body_preset_library_v1.json",
)
MORPH_CATALOG_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_body_morph_catalog_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_candidates_v1.json",
)
DEFAULT_CANDIDATE_RECORDS = (
    os.path.join(SCRIPT_DIR, "cc_short_stature_candidate_m05_v1.json"),
    os.path.join(SCRIPT_DIR, "cc_short_stature_candidate_f05_v1.json"),
)


class CandidateBuildError(RuntimeError):
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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def vector_fingerprint(entries):
    canonical = json.dumps(
        [
            (item["id"], round(float(item["weight"]), 8))
            for item in sorted(entries, key=lambda value: value["id"])
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def catalog_by_id(document):
    result = {}
    for item in document.get("morphs") or []:
        morph_id = item.get("id")
        if morph_id in result:
            raise CandidateBuildError(
                "Morph catalog contains duplicate ID {}".format(morph_id)
            )
        result[morph_id] = item
    return result


def build_candidate(record, base_by_id, morph_catalog):
    bodyfit_id = record.get("bodyfit_id")
    base_bodyfit_id = (record.get("recipe") or {}).get("base_bodyfit_id")
    sex = record.get("sex")
    if not bodyfit_id or base_bodyfit_id not in base_by_id:
        raise CandidateBuildError("Candidate BodyFit IDs are incomplete")
    base = base_by_id[base_bodyfit_id]
    if sex != base.get("sex"):
        raise CandidateBuildError("Candidate sex differs from its base BodyFit")

    project = record.get("project") or {}
    project_path = project.get("path")
    if not isinstance(project_path, str) or not os.path.isfile(project_path):
        raise CandidateBuildError(
            "Candidate project is missing: {}".format(project_path)
        )
    actual_hash = sha256_file(project_path)
    actual_bytes = os.path.getsize(project_path)
    if actual_hash != project.get("sha256") or actual_bytes != int(
        project.get("bytes", -1)
    ):
        raise CandidateBuildError(
            "Candidate project changed after validation: {}".format(
                bodyfit_id
            )
        )

    body_by_id = dict(
        (item["id"], copy.deepcopy(item))
        for item in base.get("target_body_morphs") or []
    )
    overlay_ids = []
    for overlay in (record.get("recipe") or {}).get("morphs") or []:
        morph_id = overlay.get("id")
        if morph_id not in morph_catalog:
            raise CandidateBuildError(
                "Candidate Morph is absent from catalog: {}".format(morph_id)
            )
        catalog_entry = morph_catalog[morph_id]
        if catalog_entry.get("classification") != "body":
            raise CandidateBuildError(
                "Candidate Morph is not body-owned: {}".format(morph_id)
            )
        sex_values = (catalog_entry.get("sex_values") or {}).get(sex) or {}
        body_by_id[morph_id] = {
            "categories": list(catalog_entry.get("categories") or []),
            "classification": "body",
            "display": catalog_entry.get("display") or morph_id,
            "id": morph_id,
            "maximum": sex_values.get("maximum"),
            "minimum": sex_values.get("minimum"),
            "weight": float(overlay["weight"]),
        }
        overlay_ids.append(morph_id)
    body = sorted(body_by_id.values(), key=lambda item: item["id"])
    junction = copy.deepcopy(base.get("target_junction_morphs") or [])
    preview_path = (record.get("validation") or {}).get("preview")
    if not isinstance(preview_path, str) or not os.path.isfile(preview_path):
        raise CandidateBuildError(
            "Candidate preview is missing: {}".format(preview_path)
        )
    body_fingerprint = vector_fingerprint(body)
    junction_fingerprint = vector_fingerprint(junction)
    combined_fingerprint = vector_fingerprint(body + junction)
    return {
        "preset_id": bodyfit_id,
        "sex": sex,
        "body_class": record.get("body_class", "short_average"),
        "review_status": record.get(
            "review_status",
            "accepted-body-pending-head-scale",
        ),
        "base_avatar": copy.deepcopy(base["base_avatar"]),
        "source_project": {
            "path": project_path,
            "sha256": actual_hash,
            "bytes": actual_bytes,
            "modified_at": datetime.datetime.fromtimestamp(
                os.path.getmtime(project_path),
                tz=datetime.timezone.utc,
            ).astimezone().replace(microsecond=0).isoformat(),
        },
        "source_preview": {
            "path": preview_path,
            "sha256": sha256_file(preview_path),
        },
        "source_bodyfit_id": base_bodyfit_id,
        "overlay_morph_ids": sorted(overlay_ids),
        "target_body_morphs": body,
        "target_junction_morphs": junction,
        "body_morph_count": len(body),
        "junction_morph_count": len(junction),
        "body_only_fingerprint": body_fingerprint,
        "junction_fingerprint": junction_fingerprint,
        "body_and_junction_fingerprint": combined_fingerprint,
        "candidate_record": os.path.realpath(
            os.path.abspath(record["_record_path"])
        ),
    }


def build(record_paths):
    base_library = read_json(BASE_LIBRARY_PATH)
    base_by_id = dict(
        (item["preset_id"], item)
        for item in base_library.get("presets") or []
    )
    morph_catalog = catalog_by_id(read_json(MORPH_CATALOG_PATH))
    records = []
    for path in record_paths:
        resolved = os.path.realpath(os.path.abspath(path))
        if not os.path.isfile(resolved):
            raise CandidateBuildError(
                "Candidate record is missing: {}".format(resolved)
            )
        record = read_json(resolved)
        record["_record_path"] = resolved
        records.append(record)
    presets = [
        build_candidate(record, base_by_id, morph_catalog)
        for record in records
    ]
    ids = [item["preset_id"] for item in presets]
    if len(ids) != len(set(ids)) or len(presets) != 2:
        raise CandidateBuildError(
            "Short BodyFit library requires two unique candidates"
        )
    library_status = (
        "accepted"
        if all(item.get("review_status") == "accepted" for item in presets)
        else "accepted-body-pending-head-scale"
    )
    return {
        "schema_version": 1,
        "library_id": "short_adult_bodyfit_candidates_v1",
        "generated_at": now(),
        "status": library_status,
        "style_scope": "realistic short adult",
        "body_application_mode": "source_project",
        "expected_eyeball_move_weight": base_library.get(
            "expected_eyeball_move_weight",
            0.0,
        ),
        "preview_lightroom": base_library.get("preview_lightroom"),
        "presets": presets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-record",
        action="append",
        dest="candidate_records",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    records = tuple(args.candidate_records or DEFAULT_CANDIDATE_RECORDS)
    output_path = os.path.realpath(os.path.abspath(args.output))
    document = build(records)
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "output": output_path,
                "preset_ids": [
                    item["preset_id"] for item in document["presets"]
                ],
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
