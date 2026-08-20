"""Build per-BodyFit sheets for a multi-case CC5 neck review matrix."""

import argparse
import os
from pathlib import Path

from cc_make_neck_morph_review_sheets_v1 import (
    read_json,
    render_sheet,
    write_json,
)


def bodyfit_id_from_result(result):
    source_project = result.get("application", {}).get("source_project")
    if not source_project:
        raise RuntimeError(
            "Review result has no source project: {}".format(
                result.get("preset_id")
            )
        )
    return Path(source_project).stem


def prepare_candidates(morph):
    candidates = sorted(
        morph.get("candidates") or [],
        key=lambda item: float(item["value"]),
        reverse=True,
    )
    baseline = next(
        (item for item in candidates if abs(float(item["value"])) <= 1e-7),
        None,
    )
    if baseline is None:
        raise RuntimeError("Neck review has no zero baseline")
    baseline_height = (
        float(baseline["avatar_bounds"]["maximum"][2])
        - float(baseline["avatar_bounds"]["minimum"][2])
    )
    for candidate in candidates:
        height = (
            float(candidate["avatar_bounds"]["maximum"][2])
            - float(candidate["avatar_bounds"]["minimum"][2])
        )
        candidate["height_cm"] = height
        candidate["height_delta_cm"] = height - baseline_height
        for image_path in candidate.get("views", {}).values():
            if not os.path.isfile(image_path):
                raise RuntimeError("Missing review image: {}".format(image_path))
    return candidates


def build_review(summary_path, output_dir):
    summary_path = os.path.realpath(os.path.abspath(summary_path))
    output_dir = Path(os.path.realpath(os.path.abspath(output_dir)))
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise RuntimeError("Neck matrix summary is not successful")
    results = summary.get("results") or []
    if not results:
        raise RuntimeError("Neck matrix has no results")

    index = {
        "case_count": len(results),
        "cases": [],
        "scene_restored_exactly": (
            summary.get("scene_restoration", {}).get("restored_exactly") is True
        ),
        "schema_version": 1,
        "source_summary": summary_path,
    }
    for result in results:
        if result.get("success") is not True:
            raise RuntimeError(
                "Failed neck matrix case: {}".format(result.get("preset_id"))
            )
        bodyfit_id = bodyfit_id_from_result(result)
        review = result.get("neck_morph_review") or {}
        morphs = review.get("morphs") or []
        if len(morphs) != 1:
            raise RuntimeError(
                "Expected one neck Morph for {}".format(bodyfit_id)
            )
        candidates = prepare_candidates(morphs[0])
        views = review.get("views") or []
        case_dir = output_dir / bodyfit_id
        full_path = case_dir / "overview_full_body.png"
        close_path = case_dir / "overview_head_shoulders.png"
        render_sheet(
            candidates,
            views,
            False,
            full_path,
            bodyfit_id=bodyfit_id,
        )
        render_sheet(
            candidates,
            views,
            True,
            close_path,
            bodyfit_id=bodyfit_id,
        )
        index["cases"].append(
            {
                "bodyfit_id": bodyfit_id,
                "head_scale": review.get("head_scale", {}).get("target"),
                "review_restored_exactly": review.get("restored_exactly") is True,
                "sheets": {
                    "full_body": full_path.relative_to(output_dir).as_posix(),
                    "head_shoulders": close_path.relative_to(output_dir).as_posix(),
                },
                "values": [
                    {
                        "height_delta_cm": item["height_delta_cm"],
                        "slider": int(round(float(item["value"]) * 100.0)),
                    }
                    for item in candidates
                ],
                "yaw_restored_exactly": (
                    review.get("yaw_restored_exactly") is True
                ),
            }
        )
    write_json(index, output_dir / "index.json")
    return output_dir / "index.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    index_path = build_review(args.summary, args.output_dir)
    print("Neck BodyFit review sheets created: {}".format(index_path.parent))
    print("Review index: {}".format(index_path))


if __name__ == "__main__":
    main()
