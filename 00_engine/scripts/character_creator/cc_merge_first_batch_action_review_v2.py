"""Merge three revised action previews with nine hash-verified V1 videos."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
OLD_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v1.json"
NEW_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v2.json"
OLD_MANIFEST = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "first_batch_action_full_preview"
    / "capture_20260820_v1"
    / "encoded_review"
    / "action_window_manifest.json"
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def apply_window_policy(item: dict, duration: float) -> dict:
    item = copy.deepcopy(item)
    source_duration = float(item["video"]["duration_seconds"])
    source_window = min(duration, source_duration)
    item["recommended_start_seconds"] = round(
        max(0.0, (source_duration - source_window) / 2.0), 2
    )
    item["source_window_duration_seconds"] = round(source_window, 6)
    item["padding_required_seconds"] = round(
        max(0.0, duration - source_duration), 6
    )
    item["padding_policy"] = (
        "blend_to_subtle_idle_at_both_ends"
        if item["padding_required_seconds"] > 0.0
        else "none"
    )
    return item


def build(
    old_registry: dict,
    new_registry: dict,
    old_manifest: dict,
    delta_manifest: dict,
    duration: float,
) -> dict:
    old_actions = {
        item["filename"]: item for item in old_registry.get("actions") or []
    }
    old_cases = {
        item["action_id"]: item for item in old_manifest.get("cases") or []
    }
    delta_cases = {
        item["action_id"]: item for item in delta_manifest.get("cases") or []
    }
    cases = []
    reused = []
    captured = []
    for action in new_registry.get("actions") or []:
        action_id = action["action_id"]
        if action_id in delta_cases:
            case = copy.deepcopy(delta_cases[action_id])
            captured.append(action_id)
        else:
            old_action = old_actions.get(action["filename"])
            if old_action is None:
                raise ValueError(f"missing delta preview: {action_id}")
            if (
                old_action["runtime_file"]["sha256"]
                != action["runtime_file"]["sha256"]
            ):
                raise ValueError(f"reused action hash drifted: {action_id}")
            case = copy.deepcopy(old_cases[old_action["action_id"]])
            case["action_id"] = action_id
            case["case_id"] = action_id.lower()
            reused.append(action_id)
        case["source_filename"] = Path(action["runtime_file"]["path"]).name
        cases.append(apply_window_policy(case, duration))
    if len(cases) != 12 or len(reused) != 9 or len(captured) != 3:
        raise ValueError(
            f"expected 12 cases (9 reused, 3 captured); got "
            f"{len(cases)}, {len(reused)}, {len(captured)}"
        )
    return {
        "schema_version": 2,
        "review_id": "first_batch_action_windows_20260820_v2_5s",
        "window_duration_seconds": duration,
        "short_clip_policy": "blend_to_subtle_idle_at_both_ends",
        "case_count": len(cases),
        "reuse_provenance": {
            "hash_verified_v1_action_ids": reused,
            "newly_captured_action_ids": captured,
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-registry", type=Path, default=OLD_REGISTRY)
    parser.add_argument("--new-registry", type=Path, default=NEW_REGISTRY)
    parser.add_argument("--old-manifest", type=Path, default=OLD_MANIFEST)
    parser.add_argument("--delta-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--window-duration-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.window_duration_seconds <= 0.0:
        parser.error("--window-duration-seconds must be positive")
    manifest = build(
        read_json(args.old_registry),
        read_json(args.new_registry),
        read_json(args.old_manifest),
        read_json(args.delta_manifest),
        float(args.window_duration_seconds),
    )
    write_json(args.output, manifest)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
