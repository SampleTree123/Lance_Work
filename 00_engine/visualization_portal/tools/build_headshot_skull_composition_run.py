from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INDEX = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_skull_composition_candidates\review_20260809_v1\index.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
DEFAULT_SELECTION = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_headshot_skull_profile_selection_v1.json"
)
LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")
RUN_ID = "2026-08-09-headshot-skull-composition-candidates-v1"


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


def build_run(
    index: dict[str, Any],
    index_path: Path,
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    candidate_count = max(len(group["cases"]) for group in groups.values())
    selected = [] if selection is None else selection.get("profiles", [])
    selected_summary = ", ".join(
        "{}={}".format(
            item["canonical_profile_id"],
            item["source_candidate_id"],
        )
        for item in selected
    )
    run = {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "Headshot 头型多轴组合候选",
        "task": "Character Creator / Headshot",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "approved" if selected else "pending_review",
        "summary": (
            "在批准的七个单轴范围内，以受控联合幅度生成 C00-C08。"
            "C00 为默认参照，最终只从其余候选中选择最多三个变体。"
        ),
        "decision": (
            {
                "label": "候选选择已通过",
                "summary": (
                    "人工选择已固化：{}。"
                    "这些档案仍需通过两性动态表情门禁后才能进入生产。"
                ).format(selected_summary),
                "selected_profiles": selected,
            }
            if selected
            else {
                "label": "等待人工选择",
                "summary": (
                    "分别检查女性和男性的正面、四分之三与侧面。"
                    "最终头型池为 H00 默认加最多三个通过两性检查的变体。"
                ),
            }
        ),
        "tags": ["CC5 HD", "Headshot", "多轴 Morph", "头型候选"],
        "thumbnail": groups["female"]["overview"],
        "metrics": [
            {"label": "候选头型", "value": candidate_count},
            {"label": "最终预算", "value": 4},
            {"label": "源图", "value": source_images},
            {"label": "人物基准", "value": len(groups)},
        ],
        "groups": groups,
        "artifacts": [
            {"label": "人工审查说明", "url": to_url(str(review_root / "README.md"))},
            {"label": "结果索引", "url": to_url(str(index_path))},
            {"label": "候选清单", "url": to_url(index["manifest"])},
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
    if selection is not None:
        run["source"]["selection"] = to_url(str(DEFAULT_SELECTION))
        run["artifacts"].append(
            {"label": "规范头型选择", "url": to_url(str(DEFAULT_SELECTION))}
        )
    return run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the portal run for Headshot skull composition candidates."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    selection = (
        json.loads(args.selection.read_text(encoding="utf-8"))
        if args.selection.is_file()
        else None
    )
    run = build_run(index, args.index.resolve(), selection)
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
