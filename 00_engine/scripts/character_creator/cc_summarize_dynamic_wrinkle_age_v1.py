"""Summarize the completed CC5 dynamic-wrinkle age matrix."""

import argparse
import datetime
import json
import os

from PIL import Image, ImageChops, ImageStat


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(
    SCRIPT_DIR, "cc_dynamic_wrinkle_age_batch_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_dynamic_wrinkle_age_automation_summary_v1.json"
)
EXPECTED_POSE_IDS = (
    "neutral_front",
    "blink_bilateral_front",
    "brow_raise_front",
    "brow_down_front",
    "squint_bilateral_front",
    "smile_front",
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


def strength_application_valid(application, expected_strength):
    if not isinstance(application, dict):
        return False
    if float(application.get("strength", -1.0)) != float(
        expected_strength
    ):
        return False
    results = application.get("strength_results") or []
    return (
        len(results) == 13
        and all(
            (item.get("status") or {}).get("is_error") is False
            for item in results
        )
        and not any(
            application.get("morph_deltas", {}).get(group)
            for group in ("body", "junction", "face", "other")
        )
    )


def image_difference(baseline_path, target_path):
    for path in (baseline_path, target_path):
        if (
            not isinstance(path, str)
            or not os.path.isfile(path)
            or os.path.getsize(path) <= 0
        ):
            raise SummaryError(
                "Dynamic wrinkle image is missing: {}".format(path)
            )
    with Image.open(baseline_path) as source:
        baseline = source.convert("RGB")
    with Image.open(target_path) as source:
        target = source.convert("RGB")
    if baseline.size != target.size:
        raise SummaryError("Dynamic wrinkle image sizes differ")
    difference = ImageChops.difference(baseline, target)
    statistics = ImageStat.Stat(difference)
    extrema = difference.getextrema()
    histogram = difference.convert("L").histogram()
    changed_pixels = sum(histogram[1:])
    total_pixels = baseline.width * baseline.height
    return {
        "changed_pixel_fraction": (
            float(changed_pixels) / float(total_pixels)
        ),
        "maximum_channel_difference": max(
            item[1] for item in extrema
        ),
        "mean_absolute_channel_difference": (
            sum(statistics.mean) / 3.0
        ),
    }


def summarize_case(case_result, preset):
    validation = case_result.get("dynamic_wrinkle_validation") or {}
    pairs = validation.get("pairs") or []
    pair_ids = [item.get("pose_id") for item in pairs]
    if pair_ids != list(EXPECTED_POSE_IDS):
        raise SummaryError(
            "Dynamic wrinkle pose order is invalid: {}".format(
                case_result.get("preset_id")
            )
        )
    pair_records = []
    for item in pairs:
        baseline_path = item.get("baseline_image")
        target_path = item.get("target_image")
        difference = image_difference(baseline_path, target_path)
        pair_records.append(
            {
                "baseline_image": baseline_path,
                "difference": difference,
                "pose_id": item["pose_id"],
                "target_image": target_path,
            }
        )
    target = validation.get("target") or {}
    baseline = validation.get("baseline") or {}
    restore = validation.get("target_restore") or {}
    structural_checks = {
        "case_success": case_result.get("success") is True,
        "pair_count": len(pair_records) == len(EXPECTED_POSE_IDS),
        "pair_images_differ": all(
            item["difference"]["maximum_channel_difference"] > 0
            for item in pair_records
        ),
        "target_strength_applied": strength_application_valid(
            target.get("application"), 1.0
        ),
        "baseline_strength_applied": strength_application_valid(
            baseline.get("application"), 0.0
        ),
        "target_strength_restored": strength_application_valid(
            restore, 1.0
        ),
    }
    structural_pass = all(structural_checks.values())
    age_metadata = preset.get("dynamic_wrinkle_age_validation") or {}
    assembly = case_result.get("facial_assembly") or {}
    return {
        "age_label": preset.get("age_label"),
        "age_morph": assembly.get("age_morph"),
        "automation_status": (
            "structural_pass_visual_pending"
            if structural_pass
            else "failed"
        ),
        "pairs": pair_records,
        "preset_id": preset["preset_id"],
        "profile_id": age_metadata.get("profile_id"),
        "sex": preset["sex"],
        "skin_asset_id": age_metadata.get("skin_asset_id"),
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
            "Dynamic wrinkle batch is missing: {}".format(batch_path)
        )
    batch = read_json(batch_path)
    presets = {
        item["preset_id"]: item
        for item in batch.get("presets") or []
    }
    if len(presets) != 6:
        raise SummaryError("Expected six dynamic wrinkle presets")
    cases = []
    seen = set()
    for result_path in discover_validation_results(artifact_root):
        document = read_json(result_path)
        for case_result in document.get("results") or []:
            preset_id = case_result.get("preset_id")
            if preset_id not in presets:
                raise SummaryError(
                    "Unknown dynamic wrinkle result: {}".format(
                        preset_id
                    )
                )
            if preset_id in seen:
                raise SummaryError(
                    "Duplicate dynamic wrinkle result: {}".format(
                        preset_id
                    )
                )
            seen.add(preset_id)
            cases.append(
                summarize_case(case_result, presets[preset_id])
            )
    age_order = {"young": 0, "middle": 1, "older": 2}
    sex_order = {"male": 0, "female": 1}
    cases.sort(
        key=lambda item: (
            sex_order[item["sex"]],
            age_order[item["age_label"]],
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
        "summary_id": "cc_dynamic_wrinkle_age_automation_v1",
        "total_case_count": len(presets),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Summarize CC5 dynamic wrinkle age validation."
    )
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build_summary(args.artifact_root, args.batch)
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output_path)
    print(
        "Summarized {}/{} dynamic wrinkle cases -> {}".format(
            document["completed_case_count"],
            document["total_case_count"],
            output_path,
        )
    )


if __name__ == "__main__":
    main()
