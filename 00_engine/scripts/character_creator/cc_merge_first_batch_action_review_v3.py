"""Merge two final replacement previews with ten frozen V2 review decisions."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime
import json
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
ARTIFACT_ROOT = SCRIPT_ROOT.parents[1] / "outputs" / "character_creator_bridge" / "artifacts"
DEFAULT_PREVIOUS_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v2.json"
DEFAULT_NEW_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v3.json"
DEFAULT_PREVIOUS_MANIFEST = (
    ARTIFACT_ROOT
    / "first_batch_action_full_preview"
    / "review_20260820_v2_5s"
    / "action_window_manifest.json"
)
DEFAULT_PREVIOUS_SELECTION = Path(
    r"C:\Users\Macheniek\Downloads\first_batch_action_windows_20260820_v2_5s_selection.json"
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
    previous_registry: dict,
    new_registry: dict,
    previous_manifest: dict,
    delta_manifest: dict,
    previous_selection: dict,
    duration: float,
    expected_reused: int = 10,
    expected_captured: int = 2,
    review_id: str = "first_batch_action_windows_20260820_v3_5s",
) -> tuple[dict, dict]:
    previous_actions = {
        item["filename"]: item for item in previous_registry.get("actions") or []
    }
    previous_cases = {
        item["action_id"]: item for item in previous_manifest.get("cases") or []
    }
    delta_cases = {
        item["action_id"]: item for item in delta_manifest.get("cases") or []
    }
    previous_decisions = {
        item["action_id"]: item for item in previous_selection.get("selections") or []
    }

    cases: list[dict] = []
    seed_selections: list[dict] = []
    reused: list[str] = []
    captured: list[str] = []
    for action in new_registry.get("actions") or []:
        action_id = action["action_id"]
        if action_id in delta_cases:
            case = copy.deepcopy(delta_cases[action_id])
            captured.append(action_id)
        else:
            old_action = previous_actions.get(action["filename"])
            if old_action is None:
                raise ValueError(f"missing delta preview: {action_id}")
            if old_action["runtime_file"]["sha256"] != action["runtime_file"]["sha256"]:
                raise ValueError(f"reused action hash drifted: {action_id}")
            old_action_id = old_action["action_id"]
            case = copy.deepcopy(previous_cases[old_action_id])
            decision = copy.deepcopy(previous_decisions.get(old_action_id))
            if not decision or not decision.get("confirmed"):
                raise ValueError(f"reused action lacks a confirmed decision: {action_id}")
            if decision.get("source_video_sha256") != case["video"]["sha256"]:
                raise ValueError(f"reused video hash drifted: {action_id}")
            if decision.get("source_filename") != case.get("source_filename"):
                raise ValueError(f"reused source filename drifted: {action_id}")
            case["action_id"] = action_id
            case["case_id"] = action_id.lower()
            decision["action_id"] = action_id
            decision["case_id"] = case["case_id"]
            seed_selections.append(decision)
            reused.append(action_id)
        case["source_filename"] = Path(action["runtime_file"]["path"]).name
        cases.append(apply_window_policy(case, duration))

    if (
        len(cases) != expected_reused + expected_captured
        or len(reused) != expected_reused
        or len(captured) != expected_captured
    ):
        raise ValueError(
            f"expected {expected_reused + expected_captured} cases "
            f"({expected_reused} reused, {expected_captured} captured); "
            f"got total={len(cases)}, reused={len(reused)}, captured={len(captured)}"
        )

    manifest = {
        "schema_version": 2,
        "review_id": review_id,
        "window_duration_seconds": duration,
        "short_clip_policy": "blend_to_subtle_idle_at_both_ends",
        "case_count": len(cases),
        "reuse_provenance": {
            "hash_verified_v2_action_ids": reused,
            "newly_captured_action_ids": captured,
        },
        "cases": cases,
    }
    seed = {
        "schema_version": 2,
        "review_id": review_id,
        "seeded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "production_window_duration_seconds": duration,
        "complete": False,
        "confirmed_count": len(seed_selections),
        "selection_count": len(seed_selections),
        "seed_policy": "lock_hash_verified_confirmed_v2_decisions",
        "selections": seed_selections,
    }
    return manifest, seed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-registry", type=Path, default=DEFAULT_PREVIOUS_REGISTRY)
    parser.add_argument("--new-registry", type=Path, default=DEFAULT_NEW_REGISTRY)
    parser.add_argument("--previous-manifest", type=Path, default=DEFAULT_PREVIOUS_MANIFEST)
    parser.add_argument("--delta-manifest", type=Path, required=True)
    parser.add_argument("--previous-selection", type=Path, default=DEFAULT_PREVIOUS_SELECTION)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed-output", type=Path, required=True)
    parser.add_argument("--window-duration-seconds", type=float, default=5.0)
    parser.add_argument("--expected-reused", type=int, default=10)
    parser.add_argument("--expected-captured", type=int, default=2)
    parser.add_argument(
        "--review-id",
        default="first_batch_action_windows_20260820_v3_5s",
    )
    args = parser.parse_args()
    if args.window_duration_seconds <= 0.0:
        parser.error("--window-duration-seconds must be positive")
    manifest, seed = build(
        read_json(args.previous_registry),
        read_json(args.new_registry),
        read_json(args.previous_manifest),
        read_json(args.delta_manifest),
        read_json(args.previous_selection),
        float(args.window_duration_seconds),
        args.expected_reused,
        args.expected_captured,
        args.review_id,
    )
    write_json(args.output, manifest)
    write_json(args.seed_output, seed)
    print(args.output.resolve())
    print(args.seed_output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
