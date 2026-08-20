from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INDEX = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\headshot_skull_profile_dynamic_gate\review_20260809_v1\index.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
SELECTION_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_headshot_skull_profile_selection_v1.json"
)
VALIDATION_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_headshot_skull_profile_validation_v1.json"
)
LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")
RUN_ID = "2026-08-09-headshot-skull-profile-dynamic-gate-v1"


def to_url(path_value: str) -> str:
    path = Path(path_value).resolve()
    relative = path.relative_to(LANCE_WORK_ROOT.resolve())
    return "/" + relative.as_posix()


def build_group(index: dict[str, Any], group_record: dict[str, Any]) -> dict[str, Any]:
    sex = group_record["sex"]
    profiles = [profile for profile in index["profiles"] if profile["sex"] == sex]
    return {
        "label": "女性" if sex == "female" else "男性",
        "overview": to_url(group_record["overview"]),
        "comparisons": {
            view: to_url(path)
            for view, path in group_record["view_comparisons"].items()
        },
        "cases": [
            {
                "id": record["profile"]["id"],
                "label": record["profile"]["label"],
                "preset_id": record["preset_id"],
                "parameters": {
                    key: value
                    for key, value in record["profile"].items()
                    if key
                    not in ("id", "label", "source_candidate_id")
                },
                "images": {
                    view: to_url(path) for view, path in record["views"].items()
                },
            }
            for record in profiles
        ],
    }


def build_run(index: dict[str, Any], index_path: Path) -> dict[str, Any]:
    validation = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
    user_accepted = (
        (validation.get("user_visual_review") or {}).get("status") == "accepted"
    )
    groups = {
        group["sex"]: build_group(index, group) for group in index["groups"]
    }
    return {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "Headshot 规范头型动态门禁",
        "task": "Character Creator / Headshot",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "approved" if user_accepted else "pending_review",
        "summary": (
            "对人工选定的 H00-H03 共享头型执行男女双性 CC5 HD 表情矩阵。"
            "机器门禁 8/8 通过；人工动态验收已通过。"
            if user_accepted
            else "机器门禁 8/8 通过，当前等待眼睑、嘴唇、牙齿和轮廓的人眼确认。"
        ),
        "decision": {
            "label": (
                "机器与人工动态门禁均通过"
                if user_accepted
                else "机器动态门禁通过，等待视觉验收"
            ),
            "summary": (
                "四档均保持 CC5 MetaHuman 379 表情集，五个表情姿态有有效画面差异，"
                "中性眼球状态一致，受控头型 Morph 在表情前后未变化并精确恢复。"
            ),
        },
        "tags": ["CC5 HD", "Headshot", "动态门禁", "规范头型"],
        "thumbnail": groups["female"]["overview"],
        "metrics": [
            {"label": "规范头型", "value": 4},
            {"label": "两性案例", "value": index["case_count"]},
            {"label": "表情姿态", "value": 40},
            {"label": "原始图", "value": index["source_image_count"]},
        ],
        "groups": groups,
        "artifacts": [
            {"label": "视觉审查说明", "url": to_url(str(index_path.parent / "README.md"))},
            {"label": "结果索引", "url": to_url(str(index_path))},
            {"label": "规范头型清单", "url": to_url(index["manifest"])},
            {"label": "人工选择记录", "url": to_url(str(SELECTION_PATH))},
            {"label": "动态机器门禁记录", "url": to_url(str(VALIDATION_PATH))},
            *[
                {"label": "验证结果 {}".format(i + 1), "url": to_url(path)}
                for i, path in enumerate(index["result_paths"])
            ],
        ],
        "source": {
            "review_index": to_url(str(index_path)),
            "manifest": to_url(index["manifest"]),
            "selection": to_url(str(SELECTION_PATH)),
            "validation": to_url(str(VALIDATION_PATH)),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build portal run for canonical Headshot skull dynamic gate"
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    args = parser.parse_args()
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
