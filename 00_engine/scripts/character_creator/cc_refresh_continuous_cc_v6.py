"""Private v5 plus first-run bounded PRELASH over the original Bridge driver."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

CC = Path(__file__).resolve().parent
FROZEN = CC / 'cc_refresh_continuous_cc_v5.py'
FROZEN_SHA = '69310832a02ef152264e62701531eecbd403f250f5c2f2eab85407d2fa59e00c'
VERSION = 'cfd40_refresh_continuous_cc_v6_bounded_first_run'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def controller_module():
    if hashlib.sha256(FROZEN.read_bytes()).hexdigest() != FROZEN_SHA:
        raise ValueError('Frozen continuous v5 changed')
    wrapper = load(FROZEN, '_first_run_private_frozen_v5').controller_module()
    wrapper.VERSION = VERSION
    original_pins = wrapper.implementation_pins
    def implementation_pins():
        rows = original_pins()
        for path in (Path(__file__), CC / 'cc_refresh_first_run_operation_v1.py', CC / 'cc_run_character_refresh_bounded_entry_v1.py'):
            rows.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
        return rows
    wrapper.implementation_pins = implementation_pins
    original_controller = wrapper.controller
    def controller():
        base, cache, expected = original_controller()
        operation = load(CC / 'cc_refresh_first_run_operation_v1.py', '_first_run_private_operation')
        original_checked = base.checked
        def checked(path):
            builder, serial, order, policy, progress = original_checked(path)
            owner = operation.FirstRunOperation(Path(path).parent)
            owner.finish_completed(serial)
            owner.install(serial)
            return builder, serial, order, policy, progress
        base.checked = checked
        return base, cache, expected
    wrapper.controller = controller
    return wrapper


def run(path, gate, phase='all', registry=None, poll_seconds=5, once=False):
    wrapper = controller_module()
    base, _, expected = wrapper.controller()
    operation = load(CC / 'cc_refresh_first_run_operation_v1.py', '_first_run_owner_operation')
    progress = operation.read(path)
    if progress.get('runtime_wrapper') != VERSION or progress.get('runtime_wrapper_inputs') != expected:
        raise ValueError('New exclusive v6 progress with exact implementation pins required')
    serial = base.numeric.frozen().adapter.controller()  # No order/input verification while route is owned.
    with serial.controller_lock(serial.RUNTIME / 'continuous_cc_v1_owner'):
        previous = None
        while True:
            try:
                # On restart this always precedes every frozen checked/tick.
                operation.FirstRunOperation(Path(path).parent).reconcile()
                result = base.tick(path, gate, phase, registry)
            except Exception as error:
                result = operation.read(path)
                result.update(status='failed', error=str(error), last_exception=base.exception_evidence(error))
                operation.write(path, result)
            short = (result.get('active_character_id'), result['status'], len(result['ready_for_ue']))
            if short != previous:
                print(json.dumps({'current': short[0], 'status': short[1], 'ready': short[2]}), flush=True)
                previous = short
            if once or result['status'] not in ('assembling', 'exporting', 'waiting_CC_idle_no_submission', 'same_job_pending_transport_attention'):
                return result
            time.sleep(max(1., min(float(poll_seconds), 30.)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('prepare', 'run'), required=True)
    for key in ('order', 'policy', 'directory', 'progress', 'gate', 'caps-registry'):
        parser.add_argument('--' + key)
    parser.add_argument('--phase', choices=('assemble', 'export', 'all'), default='all')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--poll-seconds', type=float, default=5)
    args = parser.parse_args()
    wrapper = controller_module()
    if args.action == 'prepare':
        if not all((args.order, args.policy, args.directory)) or args.execute:
            parser.error('Offline preparation requires original order/policy and a new exclusive directory')
        result = wrapper.prepare(args.order, args.policy, args.directory)
    elif args.execute:
        if not args.progress or not args.gate:
            parser.error('Existing v6 progress and accepted gate required')
        result = run(args.progress, args.gate, args.phase, args.caps_registry, args.poll_seconds, args.once)
    else:
        if not args.progress:
            parser.error('Existing v6 progress required')
        operation = load(CC / 'cc_refresh_first_run_operation_v1.py', '_readonly_first_run_operation')
        if operation.FirstRunOperation(Path(args.progress).parent).active():
            result = operation.read(args.progress)  # Never frozen checked against an owned route.
        else:
            result = wrapper.controller()[0].checked(args.progress)[4]
    print(json.dumps({'status': result['status'], 'active_character_id': result.get('active_character_id'),
        'ready_for_ue': len(result['ready_for_ue']), 'pending_native704': len(result['pending_native704_authorizations'])}))


if __name__ == '__main__':
    main()
