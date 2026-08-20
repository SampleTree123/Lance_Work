"""Build the accepted 10-preset adult BodyFit production library."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DEFAULT_BASE_LIBRARY = os.path.join(
    SCRIPT_DIR,
    "cc_body_preset_library_v1.json",
)
DEFAULT_SHORT_LIBRARY = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_candidates_v1.json",
)
DEFAULT_DECISIONS = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_decisions_v1.json",
)
DEFAULT_HEIGHT_MATRIX = os.path.join(
    ENGINE_ROOT,
    "outputs",
    "character_creator_bridge",
    "artifacts",
    "bodyfit_height_matrix_final_v1_20260802_03",
    "bodyfit_height_matrix.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_body_preset_library_v2.json",
)

BASE_IDS = (
    "M01_Lean",
    "M02_Average",
    "M03_Athletic",
    "M04_Heavy",
    "F01_Lean",
    "F02_Average",
    "F03_Athletic",
    "F04_Heavy",
)
SHORT_IDS = (
    "M05_Short_Average",
    "F05_Short_Average",
)
PRODUCTION_ORDER = (
    "M01_Lean",
    "M02_Average",
    "M03_Athletic",
    "M04_Heavy",
    "M05_Short_Average",
    "F01_Lean",
    "F02_Average",
    "F03_Athletic",
    "F04_Heavy",
    "F05_Short_Average",
)


class BodyLibraryBuildError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def canonical_path(path):
    return os.path.realpath(os.path.abspath(path))


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


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise BodyLibraryBuildError(
                "{} has an invalid or duplicate {}".format(label, key)
            )
        result[value] = item
    return result


def source_record(path, library_id):
    resolved = canonical_path(path)
    if not os.path.isfile(resolved):
        raise BodyLibraryBuildError(
            "Source document is missing: {}".format(resolved)
        )
    return {
        "library_id": library_id,
        "path": resolved,
        "sha256": sha256_file(resolved),
    }


def validate_project(preset):
    project = preset.get("source_project") or {}
    path = project.get("path")
    if not isinstance(path, str) or not os.path.isfile(path):
        raise BodyLibraryBuildError(
            "BodyFit source project is missing: {}".format(path)
        )
    actual_bytes = os.path.getsize(path)
    actual_hash = sha256_file(path)
    if (
        actual_bytes != int(project.get("bytes", -1))
        or actual_hash != project.get("sha256")
    ):
        raise BodyLibraryBuildError(
            "BodyFit source project changed: {}".format(
                preset.get("preset_id")
            )
        )


def validate_component_libraries(base, short):
    base_by_id = indexed(base.get("presets") or [], "preset_id", "Base library")
    short_by_id = indexed(
        short.get("presets") or [],
        "preset_id",
        "Short BodyFit library",
    )
    if set(base_by_id) != set(BASE_IDS):
        raise BodyLibraryBuildError(
            "Base library must contain the accepted eight BodyFits"
        )
    if set(short_by_id) != set(SHORT_IDS):
        raise BodyLibraryBuildError(
            "Short library must contain M05 and F05"
        )
    if short.get("status") != "accepted":
        raise BodyLibraryBuildError("Short BodyFit library is not accepted")
    for label, document in (("base", base), ("short", short)):
        if document.get("body_application_mode") != "source_project":
            raise BodyLibraryBuildError(
                "{} BodyFit library is not source-project based".format(label)
            )
    if base.get("expected_eyeball_move_weight") != short.get(
        "expected_eyeball_move_weight"
    ):
        raise BodyLibraryBuildError(
            "BodyFit libraries disagree on eyeball move weight"
        )
    if base.get("preview_lightroom") != short.get("preview_lightroom"):
        raise BodyLibraryBuildError(
            "BodyFit libraries disagree on preview Lightroom"
        )
    combined = dict(base_by_id)
    combined.update(short_by_id)
    for preset in combined.values():
        if preset.get("review_status") != "accepted":
            raise BodyLibraryBuildError(
                "BodyFit is not accepted: {}".format(preset["preset_id"])
            )
        validate_project(preset)
    return combined


def validate_decisions(decisions, expected_ids):
    if decisions.get("status") != (
        "head_and_neck_bodyfit_adjustments_selected"
    ):
        raise BodyLibraryBuildError(
            "Head and neck BodyFit decisions are not final"
        )
    selections = indexed(
        decisions.get("selections") or [],
        "bodyfit_id",
        "Head and neck decisions",
    )
    if set(selections) != set(expected_ids):
        raise BodyLibraryBuildError(
            "Head and neck decisions do not cover all 10 BodyFits"
        )
    unfinished = [
        bodyfit_id
        for bodyfit_id, item in selections.items()
        if item.get("status") != "selected"
    ]
    if unfinished:
        raise BodyLibraryBuildError(
            "Unselected BodyFit decisions: {}".format(", ".join(unfinished))
        )


def validate_height_matrix(matrix, expected_ids):
    if (
        matrix.get("success") is not True
        or int(matrix.get("success_count", -1)) != len(expected_ids)
        or int(matrix.get("failure_count", -1)) != 0
    ):
        raise BodyLibraryBuildError(
            "The final 10-BodyFit height matrix did not pass"
        )
    results = indexed(
        matrix.get("results") or [],
        "preset_id",
        "Height matrix",
    )
    if set(results) != set(expected_ids):
        raise BodyLibraryBuildError(
            "Height matrix does not cover all 10 BodyFits"
        )
    failed = [
        bodyfit_id
        for bodyfit_id, item in results.items()
        if item.get("success") is not True
        or item.get("restored_exactly") is not True
    ]
    if failed:
        raise BodyLibraryBuildError(
            "Height matrix has failed or unrestored BodyFits: {}".format(
                ", ".join(failed)
            )
        )


def build(
    base_library_path=DEFAULT_BASE_LIBRARY,
    short_library_path=DEFAULT_SHORT_LIBRARY,
    decisions_path=DEFAULT_DECISIONS,
    height_matrix_path=DEFAULT_HEIGHT_MATRIX,
):
    base_path = canonical_path(base_library_path)
    short_path = canonical_path(short_library_path)
    decision_path = canonical_path(decisions_path)
    matrix_path = canonical_path(height_matrix_path)
    base = read_json(base_path)
    short = read_json(short_path)
    decisions = read_json(decision_path)
    matrix = read_json(matrix_path)

    combined = validate_component_libraries(base, short)
    validate_decisions(decisions, PRODUCTION_ORDER)
    validate_height_matrix(matrix, PRODUCTION_ORDER)

    presets = [copy.deepcopy(combined[item]) for item in PRODUCTION_ORDER]
    document = copy.deepcopy(base)
    document.update(
        {
            "schema_version": 1,
            "library_id": "adult_body_fits_v2",
            "generated_at": now(),
            "status": "accepted",
            "bodyfit_count": len(presets),
            "presets": presets,
            "source_libraries": {
                "base": source_record(base_path, base.get("library_id")),
                "short_extension": source_record(
                    short_path,
                    short.get("library_id"),
                ),
                "proportion_decisions": source_record(
                    decision_path,
                    decisions.get("decision_set_id"),
                ),
            },
            "source_validation": {
                "base_library": copy.deepcopy(
                    base.get("source_validation")
                ),
                "runtime_height_matrix": {
                    "path": matrix_path,
                    "sha256": sha256_file(matrix_path),
                    "success_count": matrix["success_count"],
                    "failure_count": matrix["failure_count"],
                },
            },
            "technical_validation": {
                "canonical_source_project_bytes": sum(
                    int(item["source_project"]["bytes"])
                    for item in presets
                ),
                "canonical_source_project_count": len(presets),
                "canonical_source_projects_hash_locked": True,
                "female_count": sum(
                    1 for item in presets if item.get("sex") == "female"
                ),
                "male_count": sum(
                    1 for item in presets if item.get("sex") == "male"
                ),
                "preset_count": len(presets),
                "runtime_height_matrix_success_count": matrix[
                    "success_count"
                ],
                "success": True,
                "unique_body_fingerprint_count": len(
                    {
                        item.get("body_and_junction_fingerprint")
                        for item in presets
                    }
                ),
            },
        }
    )
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-library", default=DEFAULT_BASE_LIBRARY)
    parser.add_argument("--short-library", default=DEFAULT_SHORT_LIBRARY)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--height-matrix", default=DEFAULT_HEIGHT_MATRIX)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_path = canonical_path(args.output)
    document = build(
        base_library_path=args.base_library,
        short_library_path=args.short_library,
        decisions_path=args.decisions,
        height_matrix_path=args.height_matrix,
    )
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "bodyfit_count": document["bodyfit_count"],
                "library_id": document["library_id"],
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
