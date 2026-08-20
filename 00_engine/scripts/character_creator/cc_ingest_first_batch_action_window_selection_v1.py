"""Validate and freeze the user-approved first-batch five-second action windows."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
ARTIFACT_ROOT = ENGINE_ROOT / "outputs" / "character_creator_bridge" / "artifacts"
DEFAULT_MANIFEST = (
    ARTIFACT_ROOT
    / "first_batch_action_full_preview"
    / "review_20260820_v3_5s"
    / "action_window_manifest.json"
)
DEFAULT_REGISTRY = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v3.json"
DEFAULT_SELECTION = (
    Path.home()
    / "Downloads"
    / "first_batch_action_windows_20260820_v3_5s_selection.json"
)
DEFAULT_OUTPUT = (
    ARTIFACT_ROOT
    / "first_batch_action_window_selection"
    / "frozen_20260820_v3"
    / "frozen_action_windows.json"
)
EXPECTED_ACTION_COUNT = 12
EXPECTED_WINDOW_SECONDS = 5.0
TIME_TOLERANCE = 0.001


class ActionWindowSelectionError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActionWindowSelectionError(f"Could not read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ActionWindowSelectionError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locked_file(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise ActionWindowSelectionError(f"Required file is missing: {path}")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def verified_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ActionWindowSelectionError(f"Invalid file record: {label}")
    actual = locked_file(Path(str(record.get("path", ""))))
    expected_bytes = record.get("bytes", record.get("size_bytes"))
    if expected_bytes is not None and actual["bytes"] != int(expected_bytes):
        raise ActionWindowSelectionError(f"File size drifted: {label}")
    if record.get("sha256") != actual["sha256"]:
        raise ActionWindowSelectionError(f"File hash drifted: {label}")
    return actual


def indexed_unique(items: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        value = str(item.get(key, ""))
        if not value or value in result:
            raise ActionWindowSelectionError(f"Invalid or duplicate {label}: {value!r}")
        result[value] = item
    return result


def number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ActionWindowSelectionError(f"Invalid number for {label}: {value!r}") from exc
    if not math.isfinite(result):
        raise ActionWindowSelectionError(f"Non-finite number for {label}")
    return result


def close(left: float, right: float) -> bool:
    return abs(left - right) <= TIME_TOLERANCE


def freeze_action_windows(
    selection_path: Path = DEFAULT_SELECTION,
    manifest_path: Path = DEFAULT_MANIFEST,
    registry_path: Path = DEFAULT_REGISTRY,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    selection_path = selection_path.resolve()
    manifest_path = manifest_path.resolve()
    registry_path = registry_path.resolve()
    output_path = output_path.resolve()

    selection = read_json(selection_path)
    manifest = read_json(manifest_path)
    registry = read_json(registry_path)

    review_id = str(manifest.get("review_id", ""))
    if not review_id or selection.get("review_id") != review_id:
        raise ActionWindowSelectionError("Selection review_id does not match manifest")
    if selection.get("complete") is not True:
        raise ActionWindowSelectionError("Selection is incomplete")
    if registry.get("status") != "frozen_pending_cc_and_ue_validation":
        raise ActionWindowSelectionError("Action registry is not frozen")

    window_seconds = number(manifest.get("window_duration_seconds"), "manifest window")
    selection_window = number(
        selection.get("production_window_duration_seconds"),
        "selection production window",
    )
    if not close(window_seconds, EXPECTED_WINDOW_SECONDS) or not close(
        selection_window, window_seconds
    ):
        raise ActionWindowSelectionError("Expected one fixed five-second window policy")

    cases = manifest.get("cases") or []
    selections = selection.get("selections") or []
    actions = registry.get("actions") or []
    if not all(isinstance(value, list) for value in (cases, selections, actions)):
        raise ActionWindowSelectionError("Manifest, selection, or registry list is invalid")
    if not all(len(value) == EXPECTED_ACTION_COUNT for value in (cases, selections, actions)):
        raise ActionWindowSelectionError("Expected exactly 12 actions in every source")

    cases_by_id = indexed_unique(cases, "case_id", "manifest case_id")
    selections_by_id = indexed_unique(selections, "case_id", "selection case_id")
    actions_by_id = indexed_unique(actions, "action_id", "registry action_id")
    if set(cases_by_id) != set(selections_by_id):
        raise ActionWindowSelectionError("Selection case set does not match manifest")
    if {str(item.get("action_id")) for item in cases} != set(actions_by_id):
        raise ActionWindowSelectionError("Manifest action set does not match registry")

    frozen_actions: list[dict[str, Any]] = []
    sex_counts = {"female": 0, "male": 0}
    padded_count = 0
    for case in cases:
        case_id = str(case["case_id"])
        action_id = str(case["action_id"])
        selected = selections_by_id[case_id]
        action = actions_by_id[action_id]
        label = f"{action_id}/{case_id}"

        if selected.get("confirmed") is not True:
            raise ActionWindowSelectionError(f"Window is not confirmed: {label}")
        if selected.get("action_id") != action_id:
            raise ActionWindowSelectionError(f"Selection action_id mismatch: {label}")
        if selected.get("sex") != case.get("sex") or action.get("sex") != case.get("sex"):
            raise ActionWindowSelectionError(f"Sex mismatch: {label}")
        if selected.get("source_filename") != case.get("source_filename"):
            raise ActionWindowSelectionError(f"Source filename mismatch: {label}")

        preview = verified_record(case.get("video") or {}, f"preview {label}")
        if selected.get("source_video_sha256") != preview["sha256"]:
            raise ActionWindowSelectionError(f"Selected preview hash mismatch: {label}")
        motion = verified_record(action.get("runtime_file") or {}, f"motion {label}")
        if Path(motion["path"]).name != case.get("source_filename"):
            raise ActionWindowSelectionError(f"Runtime motion filename mismatch: {label}")

        source_duration = number(case["video"].get("duration_seconds"), f"source duration {label}")
        selected_source_duration = number(
            selected.get("source_duration_seconds"), f"selected source duration {label}"
        )
        source_window = number(
            case.get("source_window_duration_seconds"), f"source window {label}"
        )
        selected_source_window = number(
            selected.get("source_window_duration_seconds"),
            f"selected source window {label}",
        )
        selected_production_window = number(
            selected.get("production_duration_seconds"),
            f"selected production window {label}",
        )
        start = number(selected.get("window_start_seconds"), f"window start {label}")
        end = number(selected.get("window_end_seconds"), f"window end {label}")
        padding = max(0.0, window_seconds - source_window)
        selected_padding = number(
            selected.get("padding_required_seconds"), f"padding {label}"
        )

        if not close(selected_source_duration, source_duration):
            raise ActionWindowSelectionError(f"Source duration mismatch: {label}")
        if not close(selected_source_window, source_window):
            raise ActionWindowSelectionError(f"Source window mismatch: {label}")
        if not close(selected_production_window, window_seconds):
            raise ActionWindowSelectionError(f"Production duration mismatch: {label}")
        if start < -TIME_TOLERANCE or start > source_duration - source_window + TIME_TOLERANCE:
            raise ActionWindowSelectionError(f"Window start is out of range: {label}")
        if not close(end, start + source_window) or end > source_duration + TIME_TOLERANCE:
            raise ActionWindowSelectionError(f"Window end is out of range: {label}")
        if not close(selected_padding, padding):
            raise ActionWindowSelectionError(f"Padding duration mismatch: {label}")
        expected_policy = case.get("padding_policy") or "none"
        if selected.get("padding_policy") != expected_policy:
            raise ActionWindowSelectionError(f"Padding policy mismatch: {label}")

        sex = str(case.get("sex"))
        if sex not in sex_counts:
            raise ActionWindowSelectionError(f"Unsupported sex: {label}")
        sex_counts[sex] += 1
        if padding > TIME_TOLERANCE:
            padded_count += 1

        frozen_actions.append(
            {
                "action_id": action_id,
                "case_id": case_id,
                "sex": sex,
                "semantic_family": action.get("semantic_family"),
                "source_motion": motion,
                "source_preview_video": preview,
                "window": {
                    "start_seconds": round(start, 2),
                    "source_end_seconds": round(end, 6),
                    "source_duration_seconds": round(source_window, 6),
                    "production_duration_seconds": window_seconds,
                    "padding_required_seconds": round(padding, 6),
                    "padding_policy": expected_policy,
                },
                "cc_export_status": "pending",
                "unreal_validation_status": "pending",
                "production_status": "not_approved",
            }
        )

    if sex_counts != {"female": 6, "male": 6}:
        raise ActionWindowSelectionError(f"Unexpected sex counts: {sex_counts}")

    frozen = {
        "schema_version": 1,
        "freeze_id": review_id.removesuffix("_5s"),
        "generated_at": now(),
        "status": "frozen_ready_for_cc_export",
        "production_status": "not_approved_pending_cc_and_ue_validation",
        "provenance": {
            "selection": locked_file(selection_path),
            "review_manifest": locked_file(manifest_path),
            "action_registry": locked_file(registry_path),
        },
        "contract": {
            "action_count": len(frozen_actions),
            "female_action_count": sex_counts["female"],
            "male_action_count": sex_counts["male"],
            "production_window_duration_seconds": window_seconds,
            "idle_padded_action_count": padded_count,
        },
        "actions": frozen_actions,
    }
    write_json(output_path, frozen)
    return {
        "output": str(output_path),
        "status": frozen["status"],
        **frozen["contract"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = freeze_action_windows(
        selection_path=args.selection,
        manifest_path=args.manifest,
        registry_path=args.registry,
        output_path=args.output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
