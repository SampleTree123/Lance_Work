"""Prepare or execute serial photo/project-to-base-character CC creation.

Preparation is the default. CC must already be running in its existing offline
session. No export, UE operation, restart, or connection is performed here.
"""
import argparse
import importlib
import json
import math

from cc_character_creation_job_state_v1 import (
    BridgeStepDriver, ControllerError, SAFE_ID, controller_lock, read,
)


def parse_requests(args):
    if args.request:
        requests = [read(args.request)]
    elif args.batch:
        requests = read(args.batch)
    else:
        if args.sex is None or args.character_id is None or args.seed is None:
            raise ControllerError("Inline photo/project requests require --sex, --character-id, and --seed")
        requests = [{
            "photo" if args.photo else "source_project": args.photo or args.source_project,
            "sex": args.sex, "character_id": args.character_id, "seed": args.seed,
        }]
    if not isinstance(requests, list) or not requests or not all(isinstance(r, dict) for r in requests):
        raise ControllerError("Requests must be a nonempty list of objects")
    mode = getattr(args, 'appearance_mode', None)
    if mode is not None:
        for request in requests:
            if request.get('appearance_mode', mode) != mode:
                raise ControllerError('CLI appearance_mode conflicts with request; use the matching entry')
        requests = [dict(request, appearance_mode=mode) for request in requests]
    ids = []
    for request in requests:
        character_id = request.get("character_id", "")
        if not isinstance(character_id, str) or not SAFE_ID.fullmatch(character_id):
            raise ControllerError("Each request needs a safe ASCII character_id")
        if request.get("sex") not in ("male", "female"):
            raise ControllerError("Each request needs sex male or female")
        if bool(request.get("photo")) == bool(request.get("source_project")):
            raise ControllerError("Each request must select exactly one of photo or source_project")
        if type(request.get("seed")) is not int:
            raise ControllerError("Each request needs an integer seed")
        if request.get('appearance_mode', 'assembled') not in ('assembled', 'headshot_native'):
            raise ControllerError('appearance_mode must be assembled or headshot_native')
        if request.get('appearance_mode') == 'headshot_native' and 'facial_components' in request:
            raise ControllerError('Native Headshot mode cannot select facial_components')
        ids.append(character_id)
    if len(ids) != len(set(ids)):
        raise ControllerError("Batch repeats character IDs")
    return requests


def run_requests(requests, *, execute=False, wait_seconds=600, pipeline=None, driver=None, emit=print):
    if not math.isfinite(wait_seconds) or wait_seconds < 0:
        raise ControllerError("wait_seconds must be finite and nonnegative")
    pipeline = pipeline or importlib.import_module("cc_character_creation_pipeline_v1")
    driver = driver or BridgeStepDriver()
    for request in requests:
        state = pipeline.prepare_request(request)
        driver.verify_state_inputs(state)
        if execute:
            state = pipeline.advance(state, driver, wait_seconds)
        summary = {key: state.get(key) for key in (
            "character_id", "attempt_id", "status", "attempt_dir", "state_path",
        )}
        summary["steps"] = {name: {"status": step["status"], "job_id": step["job_id"]}
                            for name, step in state.get("steps", {}).items()}
        summary['appearance_mode'] = state.get('appearance_mode', state['request'].get('appearance_mode','assembled')) if 'request' in state else 'assembled'
        emit(json.dumps(summary, ensure_ascii=False))
        if execute and state["status"] in ("pending", "failed"):
            return 2
    return 0


def main(argv=None, *, fixed_appearance_mode=None, description=None):
    parser = argparse.ArgumentParser(description=description or __doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--photo", help="Face photo; Headshot uses pinned Current + Clean Soft")
    inputs.add_argument("--source-project", help="User-saved raw Headshot .ccProject")
    inputs.add_argument("--request", help="Single full request JSON")
    inputs.add_argument("--batch", help="JSON list of requests; executed serially")
    parser.add_argument("--sex", choices=("male", "female"))
    parser.add_argument("--character-id")
    parser.add_argument("--seed", type=int)
    parser.add_argument('--appearance-mode', choices=('assembled','headshot_native'),
                        default=fixed_appearance_mode,
                        help=argparse.SUPPRESS if fixed_appearance_mode else
                        'Default assembled; native preserves Headshot appearance and only corrects geometry')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true", help="Default; no Bridge submission")
    mode.add_argument("--execute", action="store_true", help="Explicitly submit to currently running CC")
    parser.add_argument("--wait-seconds", type=float, default=600,
                        help="Per-step wait; pending jobs can be resumed without resubmission")
    args = parser.parse_args(argv)
    if (args.request or args.batch) and any(value is not None for value in (args.sex, args.character_id, args.seed)):
        parser.error("--request/--batch carry their own sex, character_id, and seed")
    requests = parse_requests(args)
    with controller_lock():
        return run_requests(requests, execute=args.execute, wait_seconds=args.wait_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
