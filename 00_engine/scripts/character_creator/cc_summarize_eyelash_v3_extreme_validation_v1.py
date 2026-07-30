"""Summarize completed CC5 V3 extreme-face eyelash validation chunks."""

import argparse
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(
    SCRIPT_DIR, "cc_eyelash_v3_extreme_batch_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_eyelash_v3_extreme_automation_summary_v1.json"
)
REQUIRED_ARTIFACTS = (
    "face_front_preview",
    "face_three_quarter_preview",
    "face_profile_preview",
    "eyelash_blink_preview",
    "eyelash_asymmetric_preview",
    "eyelash_wide_preview",
)


class SummaryError(RuntimeError):
    pass


def now():
    return (
        datetime.datetime.now()
        .astimezone()
        .replace(microsecond=0)
        .isoformat()
    )


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        handle.write("\n")
    os.replace(temporary, path)


def discover_validation_results(artifact_root):
    paths = []
    for root, unused_directories, files in os.walk(artifact_root):
        if "validation_result.json" in files:
            paths.append(os.path.join(root, "validation_result.json"))
    return sorted(paths)


def eyelash_step(case_result):
    steps = (
        (case_result.get("appearance_application") or {}).get("steps")
        or []
    )
    matches = [item for item in steps if item.get("slot") == "eyelashes"]
    if len(matches) != 1:
        return None
    return matches[0]


def summarize_case(case_result, preset):
    artifacts = case_result.get("artifacts") or {}
    artifact_paths = {
        key: artifacts.get(key) for key in REQUIRED_ARTIFACTS
    }
    images_complete = all(
        isinstance(path, str)
        and os.path.isfile(path)
        and os.path.getsize(path) > 0
        for path in artifact_paths.values()
    )
    step = eyelash_step(case_result)
    structural_checks = {
        "case_success": case_result.get("success") is True,
        "character_preset_verified": bool(
            step and step.get("character_preset_verified") is True
        ),
        "eye_geometry_preserved": bool(
            step and step.get("eye_geometry_preserved") is True
        ),
        "eye_support_preserved": bool(
            step and step.get("eye_support_preserved") is True
        ),
        "images_complete": images_complete,
        "pose_profile_verified": (
            (case_result.get("facial_pose_validation") or {}).get(
                "profile"
            )
            == "eyelash_visibility_v1"
        ),
    }
    structural_pass = all(structural_checks.values())
    metadata = preset.get("eyelash_v3_extreme") or {}
    return {
        "artifact_paths": artifact_paths,
        "asset_id": preset["appearance_asset_ids"][0],
        "automation_status": (
            "structural_pass_visual_pending"
            if structural_pass
            else "failed"
        ),
        "display_name": preset["appearance_recipe"]["assets"][0][
            "display_name"
        ],
        "face_index": metadata.get("face_index"),
        "images_complete": images_complete,
        "preset_id": preset["preset_id"],
        "primary_seed_id": metadata.get("primary_seed_id"),
        "sex": preset["sex"],
        "structural_checks": structural_checks,
        "structural_pass": structural_pass,
        "visual_review_status": "pending",
    }


def build_summary(artifact_root, batch_path=DEFAULT_BATCH):
    artifact_root = os.path.realpath(os.path.abspath(artifact_root))
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    if not os.path.isdir(artifact_root):
        raise SummaryError(
            "Artifact root is missing: {}".format(artifact_root)
        )
    if not os.path.isfile(batch_path):
        raise SummaryError(
            "Eyelash batch is missing: {}".format(batch_path)
        )
    batch = read_json(batch_path)
    presets = {
        item["preset_id"]: item
        for item in batch.get("presets") or []
    }
    cases = []
    seen = set()
    for result_path in discover_validation_results(artifact_root):
        document = read_json(result_path)
        for case_result in document.get("results") or []:
            preset_id = case_result.get("preset_id")
            if preset_id not in presets:
                raise SummaryError(
                    "Unknown eyelash preset result: {}".format(
                        preset_id
                    )
                )
            if preset_id in seen:
                raise SummaryError(
                    "Duplicate eyelash result: {}".format(preset_id)
                )
            seen.add(preset_id)
            cases.append(
                summarize_case(case_result, presets[preset_id])
            )
    cases.sort(
        key=lambda item: (
            item["asset_id"],
            item["face_index"],
            item["preset_id"],
        )
    )
    status_counts = {}
    for item in cases:
        status = item["automation_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    pending_ids = sorted(set(presets) - seen)
    return {
        "artifact_root": artifact_root,
        "batch_path": batch_path,
        "cases": cases,
        "completed_case_count": len(cases),
        "generated_at": now(),
        "pending_case_count": len(pending_ids),
        "pending_preset_ids": pending_ids,
        "schema_version": 1,
        "status": (
            "automation-complete-visual-review-pending"
            if len(cases) == len(presets)
            else "automation-partial"
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "summary_id": "cc_eyelash_v3_extreme_automation_v1",
        "total_case_count": len(presets),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Summarize CC5 V3 extreme eyelash validation."
    )
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build_summary(args.artifact_root, args.batch)
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output_path)
    print(
        "Summarized {}/{} eyelash cases -> {}".format(
            document["completed_case_count"],
            document["total_case_count"],
            output_path,
        )
    )


if __name__ == "__main__":
    main()
