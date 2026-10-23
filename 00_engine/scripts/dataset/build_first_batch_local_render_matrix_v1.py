#!/usr/bin/env python3
"""Build the frozen 32-video local First Batch acceptance matrix."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(r"D:\UE\Lance_Work")
REQUIRED_EXPORTS = (
    ROOT
    / "00_engine"
    / "scripts"
    / "dataset"
    / "first_batch_required_exports_20260824_v3.json"
)
ACTION_POOL = (
    ROOT
    / "00_engine"
    / "scripts"
    / "character_creator"
    / "cc_first_batch_action_pool_20260824_v1.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "00_engine"
    / "scripts"
    / "unreal"
    / "first_batch_local_render_matrix_20260824_v1.json"
)
CAMERAS = (
    ("near", 0),
    ("far", 1),
    ("high", 2),
    ("side", 3),
)
EXPRESSIONS = ("happy", "angry", "sad")
SOURCE_MAP = "/Game/Scenes/TokyoStylizedEnvironment/WorkingMaps/L_DM_TokyoStylized"
STAGE_MAP = (
    "/Game/Scenes/TokyoStylizedEnvironment/WorkingMaps/"
    "L_DM_TokyoStylized_FirstBatchRender_v001"
)
SOURCE_SEQUENCE = "/Game/DataMake/Sequences/firstweek"
WORKSPACE_SEQUENCE = (
    "/Game/DataMake/Sequences/FirstBatch/Automation/"
    "LS_DM_FirstBatch_RenderWorkspace_v001"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def object_path(package: str) -> str:
    return f"{package}.{package.rsplit('/', 1)[-1]}"


def composite_asset(sex: str, action_id: str, expression: str) -> str:
    slug = action_id.removeprefix("ACT_")
    actor_id = slug.split("_", 1)[0]
    folder = "Female" if sex == "female" else "Male"
    return (
        f"/Game/DataMake/Animations/CC5/FirstDataBatch/{folder}/"
        f"Composites/{actor_id}/A_DM_{slug}_{expression.title()}_Composite_v001"
    )


def main() -> int:
    args = parse_args()
    exports = json.loads(REQUIRED_EXPORTS.read_text(encoding="utf-8-sig"))
    pool = json.loads(ACTION_POOL.read_text(encoding="utf-8-sig"))
    looks = exports["full_reference_looks"]
    if len(looks) != 32 or len({row["look_id"] for row in looks}) != 32:
        raise RuntimeError("Required exports must contain exactly 32 unique Looks")

    sex_offsets = {"female": 0, "male": 0}
    rows = []
    for index, look in enumerate(looks):
        sex = look["sex"]
        sex_index = sex_offsets[sex]
        sex_offsets[sex] += 1
        action_id = pool["active_actions"][sex][sex_index % 5]
        camera_id, section_index = CAMERAS[index % len(CAMERAS)]
        expression_id = EXPRESSIONS[index % len(EXPRESSIONS)]
        look_id = look["look_id"]
        stem = f"CC_FB_{look_id}_Blueprint_LiveLink"
        blueprint_package = f"{look['expected_unreal_folder']}/{stem}"
        sample_id = f"FB32_{index + 1:03d}_{look_id}"
        rows.append(
            {
                "sample_id": sample_id,
                "look_id": look_id,
                "sex": sex,
                "bodyfit_id": look["bodyfit_id"],
                "identity_id": look["identity_id"],
                "outfit_id": look["outfit_id"],
                "character_blueprint": blueprint_package,
                "character_blueprint_class": object_path(blueprint_package) + "_C",
                "action_id": action_id,
                "expression_id": expression_id,
                "expression_is_editable_feature": False,
                "composite_animation": composite_asset(
                    sex, action_id, expression_id
                ),
                "camera_id": camera_id,
                "camera_section_index": section_index,
                "start_frame_inclusive": section_index * 150,
                "end_frame_exclusive": (section_index + 1) * 150,
                "output_relative_directory": sample_id,
            }
        )

    action_ids = [row["action_id"] for row in rows]
    expected_actions = {
        action
        for sex in ("female", "male")
        for action in pool["active_actions"][sex]
    }
    camera_counts = Counter(row["camera_id"] for row in rows)
    expression_counts = Counter(row["expression_id"] for row in rows)
    checks = {
        "thirty_two_unique_looks": (
            len(rows) == 32 and len({row["look_id"] for row in rows}) == 32
        ),
        "all_ten_actions_covered": set(action_ids) == expected_actions,
        "five_actions_per_sex_covered": all(
            {
                row["action_id"] for row in rows if row["sex"] == sex
            }
            == set(pool["active_actions"][sex])
            for sex in ("female", "male")
        ),
        "four_cameras_covered_eight_times": camera_counts
        == Counter({camera: 8 for camera, _ in CAMERAS}),
        "three_expressions_covered": set(expression_counts) == set(EXPRESSIONS),
        "all_samples_are_150_frames": all(
            row["end_frame_exclusive"] - row["start_frame_inclusive"] == 150
            for row in rows
        ),
        "expressions_are_render_only": all(
            row["expression_is_editable_feature"] is False for row in rows
        ),
    }
    config = {
        "schema_version": "first_batch_local_render_matrix_v1",
        "matrix_id": "first_batch_32look_acceptance_20260824_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "frozen_for_local_render" if all(checks.values()) else "invalid",
        "sources": {
            "required_exports": str(REQUIRED_EXPORTS),
            "action_pool": str(ACTION_POOL),
        },
        "unreal": {
            "project_name": "datatry_02",
            "source_map_package": SOURCE_MAP,
            "staging_map_package": STAGE_MAP,
            "staging_map_object": object_path(STAGE_MAP),
            "source_sequence_package": SOURCE_SEQUENCE,
            "workspace_sequence_package": WORKSPACE_SEQUENCE,
            "workspace_sequence_object": object_path(WORKSPACE_SEQUENCE),
            "render_preset": (
                "/Game/DataMake/Render/Presets/"
                "MRQ_DM_FirstBatch_1440p30_PNG_v001"
            ),
        },
        "render": {
            "resolution": [2560, 1440],
            "fps": 30,
            "duration_seconds": 5,
            "frame_count": 150,
            "image_sequence": "png",
            "video_codec": "h264",
        },
        "coverage": {
            "look_count": len(rows),
            "action_counts": dict(sorted(Counter(action_ids).items())),
            "camera_counts": dict(sorted(camera_counts.items())),
            "expression_counts": dict(sorted(expression_counts.items())),
            "expressions_are_editable_feature": False,
            "checks": checks,
        },
        "samples": rows,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Render matrix coverage failed: {checks}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": config["status"],
                "output": str(args.output),
                "sample_count": len(rows),
                "action_count": len(expected_actions),
                "camera_counts": config["coverage"]["camera_counts"],
                "expression_counts": config["coverage"]["expression_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
