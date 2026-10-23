"""Frozen v4 with private geometry direct-gate reuse; never auto-enables."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

CC = Path(__file__).resolve().parent
FROZEN = CC / 'cc_refresh_continuous_cc_v4.py'
FROZEN_SHA = '3a05e4ad284605a8adc63c36e2bc295b024ddc174f04837c06ce4b7796a19f48'
VERSION = 'cfd40_refresh_continuous_cc_v5_rep_geometry_cache_only'


def controller_module():
    if hashlib.sha256(FROZEN.read_bytes()).hexdigest() != FROZEN_SHA:
        raise ValueError('Frozen continuous v4 source changed')
    spec = importlib.util.spec_from_file_location('_geometry_private_frozen_v4', FROZEN)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    value.HELPER = CC / 'cc_refresh_representative_gate_cache_v2.py'
    value.VERSION = VERSION
    old_implementation_pins = value.implementation_pins
    def implementation_pins():
        rows = old_implementation_pins()
        for path in (Path(__file__), CC / 'cc_refresh_representative_gate_cache_v1.py'):
            rows.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'bytes': path.stat().st_size})
        return rows
    value.implementation_pins = implementation_pins
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
    wrapper = controller_module()
    if args.action == 'prepare':
        if not all((args.order, args.policy, args.directory)) or args.execute:
            parser.error('Offline preparation requires original order/policy and an exclusive new directory')
        result = wrapper.prepare(args.order, args.policy, args.directory)
    else:
        if not args.progress:
            parser.error('Explicit new v5 progress required')
        base, _, _ = wrapper.controller()
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
