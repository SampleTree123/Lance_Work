from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_INDEX = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_skull_axis_sweep_v2\review_20260809_v1\index.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
DEFAULT_SAFE_RANGES = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_headshot_skull_safe_ranges_v1.json"
)
LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")
RUN_ID = "2026-08-09-headshot-skull-axis-sweep-v2"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def to_url(path_value: str) -> str:
    path = Path(path_value).resolve()
    relative = path.relative_to(LANCE_WORK_ROOT.resolve())
    return "/" + relative.as_posix()


def build_group(index: dict[str, Any], group_record: dict[str, Any]) -> dict[str, Any]:
    sex = str(group_record["sex"])
    profiles = [profile for profile in index["profiles"] if profile["sex"] == sex]
    cases = []
    for record in profiles:
        profile = record["profile"]
        cases.append(
            {
                "id": profile["id"],
                "label": profile["label"],
                "preset_id": record["preset_id"],
                "axis_id": profile["axis_id"],
                "axis_label": profile["axis_label"],
                "value": profile["value"],
                "parameters": dict(profile["parameters"]),
                "images": {
                    view: to_url(path)
                    for view, path in record["views"].items()
                },
            }
        )
    return {
        "label": "女性" if sex == "female" else "男性",
        "overview": to_url(group_record["overview"]),
        "comparisons": {
            view: to_url(path)
            for view, path in group_record["view_comparisons"].items()
        },
        "cases": cases,
    }


def earliest_started_at(index: dict[str, Any]) -> str:
    timestamps = []
    for result_path in index["result_paths"]:
        result = load_json(Path(result_path))
        if result.get("started_at"):
            timestamps.append(str(result["started_at"]))
    if not timestamps:
        raise ValueError("No started_at timestamp found in validation results")
    return min(timestamps)


def build_run(
    index: dict[str, Any],
    index_path: Path,
    safe_ranges: dict[str, Any],
    safe_ranges_path: Path,
) -> dict[str, Any]:
    if index.get("schema_version") != 2:
        raise ValueError("Headshot skull axis sweep requires review index schema 2")

    review_root = index_path.parent
    groups = {
        group["sex"]: build_group(index, group)
        for group in index["groups"]
    }
    axis_count = len(
        {
            record["profile"]["axis_id"]
            for record in index["profiles"]
            if record["profile"]["axis_id"] != "BASELINE"
        }
    )
    approved_ranges = {
        axis["parameter_key"]: [axis["minimum"], axis["maximum"]]
        for axis in safe_ranges["axes"]
    }
    return {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "Headshot 头型 Morph 扩大范围单轴扫描",
        "task": "Character Creator / Headshot",
        "created_at": earliest_started_at(index),
        "status": "approved",
        "summary": (
            "以 F_HS_002 与 M_HS_002 为基准，分别扩大 7 个头部与颅骨 Morph 的正负范围。"
            "每次只改变一个轴，用于定位可辨识度、失真边界和后续组合的安全区间。"
        ),
        "decision": {
            "label": "人工单轴审查通过",
            "summary": (
                "Head Width、Head Depth、Skull Height、Skull Width、Skull Depth 与 Skull Peak "
                "沿用扫描范围；Skull Back Depth 从 [-0.70, +0.70] 收紧为 [-0.50, +0.50]。"
                "这些结论只批准单轴区间，多轴极值组合仍需单独验证。"
            ),
            "safe_range_policy_id": safe_ranges["policy_id"],
            "approved_single_axis_ranges": approved_ranges,
            "multi_axis_composition": safe_ranges["scope"]["multi_axis_composition"],
        },
        "tags": ["CC5 HD", "Headshot", "Morph", "单轴扫描", "头型"],
        "thumbnail": groups["female"]["overview"],
        "metrics": [
            {"label": "案例", "value": index["case_count"]},
            {"label": "源图", "value": index["image_count"]},
            {"label": "人物基准", "value": len(groups)},
            {"label": "扫描轴", "value": axis_count},
        ],
        "groups": groups,
        "artifacts": [
            {"label": "人工审查说明", "url": to_url(str(review_root / "README.md"))},
            {"label": "结果索引", "url": to_url(str(index_path))},
            {"label": "实验清单", "url": to_url(index["manifest"])},
            {"label": "人工批准安全区间", "url": to_url(str(safe_ranges_path))},
            *[
                {"label": f"验证结果 {position + 1}", "url": to_url(path)}
                for position, path in enumerate(index["result_paths"])
            ],
        ],
        "source": {
            "review_index": to_url(str(index_path)),
            "manifest": to_url(index["manifest"]),
            "safe_ranges": to_url(str(safe_ranges_path)),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the visualization portal run for Headshot skull axis sweep v2."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    parser.add_argument("--safe-ranges", type=Path, default=DEFAULT_SAFE_RANGES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index_path = args.index.resolve()
    index = load_json(index_path)
    safe_ranges_path = args.safe_ranges.resolve()
    safe_ranges = load_json(safe_ranges_path)
    run = build_run(index, index_path, safe_ranges, safe_ranges_path)
    output = args.portal_root / "runs" / run["id"] / "run.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(run, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
