"""Summarize completed CC5 scalp-hair dynamic validation chunks."""

import argparse
import datetime
import json
import math
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_dynamic_batch_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_dynamic_automation_summary_v1.json"
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


def center_distance(left, right):
    if (
        not isinstance(left, (list, tuple))
        or not isinstance(right, (list, tuple))
        or len(left) != 3
        or len(right) != 3
    ):
        return None
    return math.sqrt(
        sum(
            (float(left[index]) - float(right[index])) ** 2
            for index in range(3)
        )
    )


def motion_displacement(report):
    samples = report.get("samples") or []
    if not samples:
        return {
            "active_part_max_center_displacement": 0.0,
            "all_part_max_center_displacement": 0.0,
            "part_displacements": [],
        }
    baseline_parts = {
        item.get("id"): item
        for item in (
            (samples[0].get("hair_physics") or {}).get(
                "hair_parts"
            )
            or []
        )
        if item.get("id") is not None
    }
    records = []
    for part_id, baseline in baseline_parts.items():
        baseline_center = (
            (baseline.get("bounds") or {}).get("center")
        )
        maximum = 0.0
        measured = False
        for sample in samples[1:]:
            current = next(
                (
                    item
                    for item in (
                        (sample.get("hair_physics") or {}).get(
                            "hair_parts"
                        )
                        or []
                    )
                    if item.get("id") == part_id
                ),
                None,
            )
            if current is None:
                continue
            distance = center_distance(
                baseline_center,
                (current.get("bounds") or {}).get("center"),
            )
            if distance is None:
                continue
            measured = True
            maximum = max(maximum, distance)
        records.append(
            {
                "id": part_id,
                "maximum_center_displacement": (
                    maximum if measured else None
                ),
                "name": baseline.get("name"),
                "physics_active": baseline.get(
                    "physics_active"
                ),
            }
        )
    measured_values = [
        item["maximum_center_displacement"]
        for item in records
        if item["maximum_center_displacement"] is not None
    ]
    active_values = [
        item["maximum_center_displacement"]
        for item in records
        if item["physics_active"] is True
        and item["maximum_center_displacement"] is not None
    ]
    return {
        "active_part_max_center_displacement": max(
            [0.0] + active_values
        ),
        "all_part_max_center_displacement": max(
            [0.0] + measured_values
        ),
        "part_displacements": records,
    }


def discover_validation_results(artifact_root):
    paths = []
    for root, unused_directories, files in os.walk(artifact_root):
        if "validation_result.json" in files:
            paths.append(os.path.join(root, "validation_result.json"))
    return sorted(paths)


def case_artifact_paths(case_result):
    preset_id = case_result["preset_id"]
    result_path = (
        case_result.get("artifacts") or {}
    ).get("source_preview")
    if not result_path:
        raise SummaryError(
            "Case {} has no artifact paths".format(preset_id)
        )
    case_dir = os.path.dirname(result_path)
    motion_summary = case_result.get("hair_motion_validation") or {}
    motion_report_path = motion_summary.get(
        "hair_motion_probe_path"
    )
    return {
        "case_dir": case_dir,
        "face_front": os.path.join(case_dir, "face_front.png"),
        "face_profile": os.path.join(case_dir, "face_profile.png"),
        "hair_rear": os.path.join(case_dir, "hair_rear.png"),
        "motion_report": motion_report_path,
    }


def summarize_case(case_result, preset):
    paths = case_artifact_paths(case_result)
    motion_report_path = paths["motion_report"]
    motion_report = (
        read_json(motion_report_path)
        if motion_report_path
        and os.path.isfile(motion_report_path)
        else None
    )
    images = []
    if motion_report is not None:
        images = [
            sample.get("image")
            for sample in motion_report.get("samples") or []
        ]
    image_paths = [
        paths["face_front"],
        paths["face_profile"],
        paths["hair_rear"],
    ] + images
    images_complete = bool(
        image_paths
        and all(
            isinstance(path, str)
            and os.path.isfile(path)
            and os.path.getsize(path) > 0
            for path in image_paths
        )
    )
    initial_physics = (
        (motion_report or {}).get("initial_hair_physics") or {}
    )
    displacement = motion_displacement(motion_report or {})
    automation_status = "failed"
    if case_result.get("success") and motion_report is not None:
        active_count = int(
            initial_physics.get("physics_active_count", 0)
        )
        if not images_complete:
            automation_status = "missing_images"
        elif active_count == 0:
            automation_status = "rigid_short_candidate"
        elif (
            displacement[
                "active_part_max_center_displacement"
            ]
            > 0.05
        ):
            automation_status = "dynamic_candidate"
        else:
            automation_status = "active_without_motion_review"

    metadata = preset.get("scalp_hair_dynamic_validation") or {}
    return {
        "artifact_paths": {
            **paths,
            "motion_images": images,
        },
        "asset_id": preset["appearance_asset_ids"][0],
        "automation_status": automation_status,
        "case_phase": metadata.get("case_phase"),
        "displacement": displacement,
        "display_name": preset["appearance_recipe"]["assets"][0][
            "display_name"
        ],
        "female_presentation_score": metadata.get(
            "female_presentation_score"
        ),
        "images_complete": images_complete,
        "motion_id": metadata.get("motion_id"),
        "physics": {
            "global_physics_simulation_loop": initial_physics.get(
                "global_physics_simulation_loop"
            ),
            "hair_part_count": initial_physics.get(
                "hair_part_count"
            ),
            "physics_active_count": initial_physics.get(
                "physics_active_count"
            ),
            "physics_component_count": initial_physics.get(
                "physics_component_count"
            ),
            "soft_material_count": initial_physics.get(
                "soft_material_count"
            ),
        },
        "preset_id": preset["preset_id"],
        "sex": preset["sex"],
        "silhouette_family": metadata.get(
            "silhouette_family"
        ),
        "success": bool(case_result.get("success")),
        "visual_review_status": "pending",
    }


def build_summary(artifact_root, batch_path=DEFAULT_BATCH):
    artifact_roots = (
        list(artifact_root)
        if isinstance(artifact_root, (list, tuple))
        else [artifact_root]
    )
    artifact_roots = [
        os.path.realpath(os.path.abspath(path))
        for path in artifact_roots
    ]
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    for path in artifact_roots:
        if not os.path.isdir(path):
            raise SummaryError(
                "Artifact root is missing: {}".format(path)
            )
    if not os.path.isfile(batch_path):
        raise SummaryError(
            "Dynamic batch is missing: {}".format(batch_path)
        )
    batch = read_json(batch_path)
    presets = {
        item["preset_id"]: item
        for item in batch.get("presets") or []
    }
    cases = []
    seen = set()
    for artifact_root_path in artifact_roots:
        for result_path in discover_validation_results(
            artifact_root_path
        ):
            document = read_json(result_path)
            for case_result in document.get("results") or []:
                preset_id = case_result.get("preset_id")
                if preset_id not in presets:
                    raise SummaryError(
                        "Unknown dynamic preset result: {}".format(
                            preset_id
                        )
                    )
                if preset_id in seen:
                    raise SummaryError(
                        "Duplicate dynamic result: {}".format(
                            preset_id
                        )
                    )
                seen.add(preset_id)
                cases.append(
                    summarize_case(
                        case_result,
                        presets[preset_id],
                    )
                )
    cases.sort(key=lambda item: item["preset_id"])
    completed_ids = {item["preset_id"] for item in cases}
    status_counts = {}
    for item in cases:
        status = item["automation_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "artifact_root": (
            artifact_roots[0] if len(artifact_roots) == 1 else None
        ),
        "artifact_roots": artifact_roots,
        "batch_path": batch_path,
        "cases": cases,
        "completed_case_count": len(cases),
        "generated_at": now(),
        "pending_case_count": len(presets) - len(completed_ids),
        "pending_preset_ids": sorted(
            set(presets) - completed_ids
        ),
        "schema_version": 1,
        "status": (
            "automation-complete-visual-review-pending"
            if len(cases) == len(presets)
            else "automation-partial"
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "summary_id": "cc_scalp_hair_dynamic_automation_v1",
        "total_case_count": len(presets),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Summarize CC5 scalp-hair dynamic validation."
    )
    parser.add_argument(
        "--artifact-root",
        action="append",
        required=True,
        help="Repeat to merge disjoint continuation runs.",
    )
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build_summary(args.artifact_root, args.batch)
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output_path)
    print(
        "Summarized {}/{} dynamic cases -> {}".format(
            document["completed_case_count"],
            document["total_case_count"],
            output_path,
        )
    )


if __name__ == "__main__":
    main()
