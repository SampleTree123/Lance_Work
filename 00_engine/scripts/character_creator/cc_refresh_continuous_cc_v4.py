"""Frozen continuous v2 with process-local representative gate reuse only.

New exclusive progress is required. Root may enable only at a real job boundary.
The current v2 controller, progress, character stages and pending jobs stay intact.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

CC = Path(__file__).resolve().parent
FROZEN = CC / 'cc_refresh_continuous_cc_v2.py'
FROZEN_SHA = 'b8634bd12b17be7890a3faf34c2a7b325a6884421fca1ae8b025d678cb0cdc29'
HELPER = CC / 'cc_refresh_representative_gate_cache_v1.py'
VERSION = 'cfd40_refresh_continuous_cc_v4_rep_cache_only'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def implementation_pins():
    if hashlib.sha256(FROZEN.read_bytes()).hexdigest() != FROZEN_SHA:
        raise ValueError('Frozen continuous v2 source changed')
    return [{'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
             'bytes': path.stat().st_size} for path in (Path(__file__), HELPER, FROZEN)]


def controller():
    expected = implementation_pins()
    base = load(FROZEN, '_cached_private_continuous_v2')
    cache = load(HELPER, '_cached_private_gate_helper').RepresentativeGateCache(expected)
    original_checked = base.checked
    def checked(path):
        value = base.numeric.frozen().adapter.controller().read(path)
        if value.get('runtime_wrapper') != VERSION or value.get('runtime_wrapper_inputs') != expected:
            raise ValueError('New v4 progress with exact wrapper inputs required; never adopt running v2 progress')
        if implementation_pins() != expected:
            raise ValueError('Runtime wrapper implementation changed')
        builder, serial, order, policy, progress = original_checked(path)
        cache.bind(serial, progress['order'], order['implementation_pins'])
        return builder, serial, order, policy, progress
    base.checked = checked
    return base, cache, expected


def prepare(order, policy, directory):
    base, _, expected = controller()
    value = base.prepare(order, policy, directory)
    value['runtime_wrapper'] = VERSION
    value['runtime_wrapper_inputs'] = expected
    value['representative_cache_scope'] = 'process-local; full original gate on any closure/key change; no current-person cache'
    base.numeric.frozen().adapter.controller().write(Path(directory) / 'progress.json', value)
    return value


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
    if args.action == 'prepare':
        if not all((args.order, args.policy, args.directory)) or args.execute:
            parser.error('Offline preparation requires original order/policy and an exclusive new directory')
        result = prepare(args.order, args.policy, args.directory)
    else:
        if not args.progress:
            parser.error('Explicit new v4 progress required')
        base, _, _ = controller()
        if args.execute:
            if not args.gate:
                parser.error('Real original accepted representative gate required')
            result = base.run(args.progress, args.gate, args.phase, args.caps_registry,
                              args.poll_seconds, args.once)
        else:
            result = base.checked(args.progress)[4]
    print(json.dumps({'status': result['status'], 'active_character_id': result.get('active_character_id'),
                      'ready_for_ue': len(result['ready_for_ue']),
                      'pending_native704': len(result['pending_native704_authorizations'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
