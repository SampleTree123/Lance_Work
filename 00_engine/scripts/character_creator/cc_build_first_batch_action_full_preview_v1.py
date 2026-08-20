"""Build the immutable CC gate used for full-length action preview capture."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = SCRIPT_ROOT / "cc_first_batch_action_gate_20260820_v1.json"
DEFAULT_OUTPUT = SCRIPT_ROOT / "cc_first_batch_action_full_preview_20260820_v1.json"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build(source: dict, interval_frames: int = 6) -> dict:
    if source.get("diagnostic_mode") != "animation_p0_dynamic_gate":
        raise ValueError("source is not an animation_p0_dynamic_gate library")
    if interval_frames <= 0:
        raise ValueError("interval_frames must be positive")
    result = copy.deepcopy(source)
    result["library_id"] = "cc_first_batch_action_full_preview_20260820_v1"
    result["generated_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    result["status"] = "full_preview_capture_planned"
    result["preview_resolution"] = [640, 640]
    policy = result.setdefault("capture_policy", {})
    policy.pop("sample_normalized_positions", None)
    policy.pop("sample_frames", None)
    policy["sample_interval_frames"] = int(interval_frames)
    policy["preview_fps"] = 60.0 / float(interval_frames)
    policy["segment_timeout_seconds"] = 60.0
    counts = result.setdefault("counts", {})
    counts["sample_count_per_motion"] = None
    counts["expected_image_count"] = None
    counts["preview_fps"] = policy["preview_fps"]
    result["selection_override"]["dynamic_gate_still_required"] = False
    result["selection_override"]["production_approval_granted"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--interval-frames", type=int, default=6)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    output = build(source, args.interval_frames)
    write_json(args.output, output)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
