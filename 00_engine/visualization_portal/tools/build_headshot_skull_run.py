from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_INDEX = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_skull_profile_review\review_20260809_v1\index.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")


def to_url(path_value: str) -> str:
    path = Path(path_value).resolve()
    relative = path.relative_to(LANCE_WORK_ROOT.resolve())
    return "/" + relative.as_posix()


def build_group(index: dict[str, Any], group_record: dict[str, Any]) -> dict[str, Any]:
    sex = group_record["sex"]
    profiles = [profile for profile in index["profiles"] if profile["sex"] == sex]
    cases = []
    for profile_record in profiles:
        profile = dict(profile_record["profile"])
        profile_id = profile.pop("id")
        label = profile.pop("label")
        cases.append(
            {
                "id": profile_id,
                "label": label,
                "preset_id": profile_record["preset_id"],
                "parameters": profile,
                "images": {
                    view: to_url(path)
                    for view, path in profile_record["views"].items()
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


def build_run(index: dict[str, Any], index_path: Path) -> dict[str, Any]:
    review_root = index_path.parent
    groups = {
        group["sex"]: build_group(index, group)
        for group in index["groups"]
    }
    source_images = sum(
        len(case["images"])
        for group in groups.values()
        for case in group["cases"]
    )
    return {
        "schema_version": 1,
        "id": "2026-08-09-headshot-skull-profile-review-v1",
        "title": "Headshot 头型 Morph 初始范围审查",
        "task": "Character Creator / Headshot",
        "created_at": "2026-08-09T10:20:41+08:00",
        "status": "iteration_needed",
        "summary": (
            "以 F_HS_002 与 M_HS_002 为基准，检查六组头宽、头深和颅骨组合。"
            "结果稳定，但方案间视觉差异整体偏小。"
        ),
        "decision": {
            "label": "人工审查结论",
            "summary": (
                "当前组合没有明显几何故障，但不足以提供目标中的显著头型多样性。"
                "下一轮改用单轴大范围扫描，再据结果确定安全生产区间。"
            ),
        },
        "tags": ["CC5 HD", "Headshot", "Morph", "头型"],
        "thumbnail": groups["female"]["overview"],
        "metrics": [
            {"label": "方案", "value": 12},
            {"label": "源图", "value": source_images},
            {"label": "人物基准", "value": 2},
            {"label": "受控 Morph", "value": 7},
        ],
        "groups": groups,
        "artifacts": [
            {"label": "人工审查说明", "url": to_url(str(review_root / "README.md"))},
            {"label": "结果索引", "url": to_url(str(index_path))},
            {"label": "实验矩阵清单", "url": to_url(index["manifest"])},
            *[
                {"label": f"验证结果 {position + 1}", "url": to_url(path)}
                for position, path in enumerate(index["result_paths"])
            ],
        ],
        "source": {
            "review_index": to_url(str(index_path)),
            "manifest": to_url(index["manifest"]),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the portal run record for the Headshot skull review."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    run = build_run(index, args.index.resolve())
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
