"""Freeze the final 12-action batch after replacing F02 and M04."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cc_build_first_batch_action_gate_v2 as base


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
ARTIFACT_ROOT = ENGINE_ROOT / "outputs" / "character_creator_bridge" / "artifacts"

DEFAULT_SOURCE = Path(r"D:\BaiduNetdiskDownload\iclone动作\P0_Core_Everyday\1")
DEFAULT_INVENTORY = (
    ARTIFACT_ROOT
    / "animation_source_inventory"
    / "p0_20260817_v3"
    / "inventory.json"
)
DEFAULT_RUNTIME_ROOT = SCRIPT_ROOT / "runtime_assets" / "first_batch_actions_20260820_v3"
DEFAULT_OUTPUT = (
    ARTIFACT_ROOT
    / "first_batch_action_selection"
    / "selection_20260820_v3"
)
DEFAULT_GATE_OUTPUT = SCRIPT_ROOT / "cc_first_batch_action_gate_20260820_v3.json"
DEFAULT_REGISTRY_OUTPUT = SCRIPT_ROOT / "cc_first_batch_action_registry_20260820_v3.json"

PILOT_ID = "cc_first_batch_actions_12_20260820_v3"
REGISTRY_ID = "first_batch_action_registry_20260820_v3"
ACTOR_LIBRARY_ID = "cc_first_batch_clothed_review_actors_20260820_v3"

ACTION_SPECS = (
    {
        "action_id": "ACT_F01_ARGUMENT_BOSSY",
        "filename": "Argument_Bossy_F.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "argument_gesture",
    },
    {
        "action_id": "ACT_F02_CATCH_BREATH",
        "filename": "CatchBreath.iMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "self_recovery",
    },
    {
        "action_id": "ACT_F03_AUDIENCE_01",
        "filename": "Audience F 01.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_F04_AUDIENCE_09",
        "filename": "Audience F 09.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_F05_TIE_SHOES",
        "filename": "TieShoes.iMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "self_interaction",
    },
    {
        "action_id": "ACT_F06_ELEVATOR_GREETING",
        "filename": "Elevator_Greeting_F.rlMotion",
        "sex": "female",
        "actor_id": "F02_Average",
        "semantic_family": "greeting_gesture",
    },
    {
        "action_id": "ACT_M01_ARGUMENT_SURRENDER",
        "filename": "Argument_Surrender_M.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "argument_gesture",
    },
    {
        "action_id": "ACT_M02_AUDIENCE_01",
        "filename": "Audience M 01.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_M03_AUDIENCE_12",
        "filename": "Audience M 12.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "audience_reaction",
    },
    {
        "action_id": "ACT_M04_LIVING_ROOM_SWING",
        "filename": "LivingRoom_Swing_M.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "dance_gesture",
    },
    {
        "action_id": "ACT_M05_ELEVATOR_GREETING",
        "filename": "Elevator_Greeting_M.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "greeting_gesture",
    },
    {
        "action_id": "ACT_M06_MOVING_ARGUMENT_DECLINE",
        "filename": "MovingArgument_Decline_M.rlMotion",
        "sex": "male",
        "actor_id": "M02_Average",
        "semantic_family": "argument_gesture",
    },
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    base.write_json(path, value)


def build(args: argparse.Namespace) -> dict[str, Any]:
    original_specs = base.ACTION_SPECS
    original_pilot_id = base.PILOT_ID
    original_actor_builder = base.build_actor_library

    def build_actor_library_v3(*values: Any, **kwargs: Any) -> dict[str, Any]:
        library = original_actor_builder(*values, **kwargs)
        library["library_id"] = ACTOR_LIBRARY_ID
        return library

    base.ACTION_SPECS = ACTION_SPECS
    base.PILOT_ID = PILOT_ID
    base.build_actor_library = build_actor_library_v3
    try:
        result = base.build_first_batch_action_gate(
            args.source,
            args.inventory,
            args.body_library,
            args.work_order,
            args.runtime_root,
            args.actor_runtime_root,
            args.output,
            args.gate_output,
            args.registry_output,
            args.camera,
            args.lightroom,
        )
    finally:
        base.ACTION_SPECS = original_specs
        base.PILOT_ID = original_pilot_id
        base.build_actor_library = original_actor_builder

    registry = base.read_json(args.registry_output.resolve())
    registry["registry_id"] = REGISTRY_ID
    write_json(args.registry_output.resolve(), registry)
    write_json(args.output.resolve() / "action_registry.json", registry)
    result["cc_output_dir"] = str(
        args.output.resolve().parent / "dynamic_run_20260820_v3"
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--body-library", type=Path, default=base.DEFAULT_BODY_LIBRARY)
    parser.add_argument("--work-order", type=Path, default=base.DEFAULT_WORK_ORDER)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument(
        "--actor-runtime-root", type=Path, default=base.DEFAULT_ACTOR_RUNTIME_ROOT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gate-output", type=Path, default=DEFAULT_GATE_OUTPUT)
    parser.add_argument("--registry-output", type=Path, default=DEFAULT_REGISTRY_OUTPUT)
    parser.add_argument("--camera", type=Path, default=base.DEFAULT_CAMERA)
    parser.add_argument("--lightroom", type=Path, default=base.DEFAULT_LIGHTROOM)
    return parser.parse_args()


def main() -> int:
    result = build(parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
