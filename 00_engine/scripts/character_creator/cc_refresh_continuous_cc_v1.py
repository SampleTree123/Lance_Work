"""Continuous CC assembly/export over frozen per-case serial v2.

Missing native704 registration queues a captured source and continues assembly.
Only actual required failures stop; a stop file prevents submissions, never kills
an active job. No UE calls or automated claim of human image acceptance.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import subprocess

CC = Path(__file__).resolve().parent
REPO = CC.parents[2]
RUN = REPO / '00_engine/outputs/character_refresh_20261018_v1'
sys.path[:0] = [str(CC), str(RUN)]
import build_numeric_cc_receipt_v2 as numeric

SCHEMA = 'cfd40_refresh_cc_continuous_progress_v1'


def transport_uncertainty(error):
    return isinstance(error, (TimeoutError, ConnectionError, subprocess.TimeoutExpired))


def prepare(order_path, policy_path, directory):
    builder, serial, policy = numeric.private_builder(policy_path)
    order = serial.checked(order_path)
    directory = Path(directory).resolve()
    if not directory.is_relative_to(RUN) or directory == RUN or directory.exists():
        raise ValueError('New exclusive progress directory below this refresh run required')
    value = dict(schema=SCHEMA, status='prepared_not_started', order=serial.bind(order_path),
        batch_processing_authorization=policy, implementation_pins=[serial.bind(__file__), serial.bind(numeric.__file__),
            serial.bind(numeric.FROZEN_BUILDER)], items={}, pending_native704_authorizations=[], ready_for_ue=[],
        execution_started=False, visual_review='pending_batch_review', batch40_accepted=False,
        stop_file=str(directory / 'stop_requested.json'), active_character_id=None)
    # Read existing durable evidence only. Completed original cases are seeded,
    # not reassembled; a captured AF003 can enter the numeric queue immediately.
    for row in order['cases']:
        path = Path(row['state_path'])
        if not path.exists():
            continue
        state = serial.read(path)
        identifier = row['character_id']
        if state.get('status') == 'completed':
            append_unique(value['ready_for_ue'], ready_row(identifier, row, state, serial))
            value['items'][identifier] = dict(state_path=str(path), status='complete_CC_export_not_UE_accepted')
        elif 'review_ready_staged_final' in state.get('facts', {}) and 'visual_report' in state['facts']:
            facts = builder.load_facts(order_path, identifier)
            measurement = numeric.measurement_record(facts[3], facts[7])
            append_unique(value['pending_native704_authorizations'], measurement)
            value['items'][identifier] = dict(state_path=str(path),
                status='four_images_captured_pending_numeric_registration', measurement=measurement)
    directory.mkdir(parents=True, exist_ok=False)
    serial.write(directory / 'progress.json', value)
    return value


def checked(progress_path):
    initial = numeric.frozen().adapter.controller()
    value = initial.read(progress_path)
    if value.get('schema') != SCHEMA:
        raise ValueError('Expected this continuous progress schema')
    for record in [value['order'], value['batch_processing_authorization'], *value['implementation_pins']]:
        initial.verify(record, 'continuous pinned input')
    builder, serial, policy = numeric.private_builder(value['batch_processing_authorization']['path'])
    order = serial.checked(value['order']['path'])
    if len({r['character_id'] for r in value['ready_for_ue']}) != len(value['ready_for_ue']):
        raise ValueError('Duplicate ready queue identity')
    return builder, serial, order, policy, value


def append_unique(rows, row):
    old = [r for r in rows if r['character_id'] == row['character_id']]
    if old:
        if old[0] != row:
            raise ValueError('Previously recorded source/queue pins changed; never overwrite')
    else:
        rows.append(row)


def pending_jobs(state, row, serial):
    result = [s['job_id'] for s in state.get('steps', {}).values() if s.get('status') == 'pending']
    geometry_path = Path(row['geometry_state'])
    if geometry_path.exists():
        geometry = serial.read(geometry_path)
        result += [s['job_id'] for s in geometry.get('steps', {}).values() if s.get('status') == 'pending']
    preparation = state.get('facts', {}).get('export_preparation')
    if preparation and state['facts'].get('export_submission_recorded') and not state['facts'].get('export_inventory'):
        prep = serial.read(preparation['path'])
        result.append(prep['job_id'])  # Existing export only; never recreate it.
    return sorted(set(result))


def cc_idle(serial):
    driver = serial.BridgeStepDriver(run_root=serial.RUNTIME, stage_root=serial.STAGE)
    health = driver.client_call(['health'])
    return (health.get('healthy') and not (health.get('heartbeat') or {}).get('active_job_id')
            and not any(list((driver.bridge_root / area).glob('*.json')) for area in ('inbox', 'processing')))


def ready_row(identifier, row, state, serial):
    facts = state['facts']
    preparation = facts.get('export_preparation')
    if not preparation or not facts.get('export_inventory'):
        raise ValueError('Completed export must have actual preparation and inventory')
    serial.verify(preparation, 'complete export preparation')
    actual = serial.exporter.status(preparation['path'])
    if actual.get('complete_export_verified') is not True or actual.get('export_inventory') != facts['export_inventory']:
        raise ValueError('Actual same export inventory verification required before UE queue')
    receipt = facts['completed_CC_receipt']
    manifest = facts['completed_transfer_manifest']
    for record in (receipt, manifest, facts['export_inventory']):
        serial.verify(record, 'actual ready-for-UE evidence')
    payload = serial.read(receipt['path'])
    return dict(character_id=identifier, sex=row['sex'], revision_id='v2', numeric_export_receipt=receipt,
        transfer_manifest=manifest, export_inventory=facts['export_inventory'],
        visual_review=payload.get('visual_review', 'explicit_prior_review_preserved'),
        existing_explicit_review_preserved='root_visual_approval' in payload)


def tick(progress_path, gate_path, phase='all', registry_path=None):
    builder, serial, order, policy, progress = checked(progress_path)
    if progress['status'] == 'failed':
        raise ValueError('Failed progress retained; inspect error, never auto-reset')
    if Path(progress['stop_file']).exists():
        progress.update(status='stopped_no_new_submissions', execution_started=True)
        # Leave pending states/jobs alone. On resume the frozen serial reads the
        # same persisted job; no kill, cancellation or resubmission is issued.
        serial.write(progress_path, progress)
        return progress
    serial.representative_evidence(order['batch_plan']['path'], gate_path)
    if registry_path:
        registry_pin = serial.bind(registry_path)
        if registry_pin not in progress.setdefault('numeric_registries_used', []):
            progress['numeric_registries_used'].append(registry_pin)
    progress['execution_started'] = True
    pending_rows = []
    for row in order['cases']:
        state = serial.read(row['state_path']) if Path(row['state_path']).exists() else {}
        if pending_jobs(state, row, serial):
            pending_rows.append(row)
    if len(pending_rows) > 1:
        progress.update(status='failed', error='Multiple subjects have persisted pending jobs; inspect owners before continuing')
        serial.write(progress_path, progress)
        return progress
    priority = [r for r in order['cases'] if r not in pending_rows]
    for row in pending_rows + priority:
        identifier = row['character_id']
        if any(r['character_id'] == identifier for r in progress['ready_for_ue']):
            continue
        state = serial.read(row['state_path']) if Path(row['state_path']).exists() else {}
        if state.get('status') == 'failed':
            progress.update(status='failed', active_character_id=identifier, error='Actual existing case failed; attempt preserved')
            serial.write(progress_path, progress)
            return progress
        progress['active_character_id'] = identifier
        item = progress['items'].setdefault(identifier, dict(state_path=row['state_path'], status='not_started'))
        try:
            if state.get('status') == 'completed':
                append_unique(progress['ready_for_ue'], ready_row(identifier, row, state, serial))
                item['status'] = 'complete_CC_export_not_UE_accepted'
                serial.write(progress_path, progress)
                continue
            captured = 'review_ready_staged_final' in state.get('facts', {}) and 'visual_report' in state.get('facts', {})
            if not captured:
                if phase == 'export' and not pending_jobs(state, row, serial):
                    continue
                if not pending_jobs(state, row, serial) and not cc_idle(serial):
                    progress['status'] = 'waiting_CC_idle_no_submission'
                    serial.write(progress_path, progress)
                    return progress
                answer = serial.advance(progress['order']['path'], identifier, gate_path, True)
                item.update(status=answer.get('status', 'same_case_pending'), last_result=answer)
                progress['status'] = 'assembling'
                serial.write(progress_path, progress)
                return progress
            if 'measurement' not in item:
                facts = builder.load_facts(progress['order']['path'], identifier)
                item['measurement'] = numeric.measurement_record(facts[3], facts[7])
                append_unique(progress['pending_native704_authorizations'], item['measurement'])
                item['status'] = 'four_images_captured_pending_numeric_registration'
                serial.write(progress_path, progress)
            if phase == 'assemble':
                continue
            existing = state['facts'].get('completed_transfer_manifest')
            if existing:
                serial.verify(existing, 'existing completed export source')
                manifest_path = existing['path']
            else:
                cap = numeric.registered_cap(registry_path, item['measurement'], policy, serial)
                if cap is None:
                    # Registration is batched numeric work, not an error or a
                    # request for per-person human image approval. Continue CC.
                    continue
                output = RUN / 'batch_cases' / identifier / 'numeric_cc_v2'
                built = numeric.build(progress['order']['path'], identifier, policy['path'], registry_path, output)
                item['numeric_export_receipt'] = built['receipt']
                item['numeric_transfer_manifest'] = built['transfer_manifest']
                manifest_path = built['transfer_manifest']['path']
            if not pending_jobs(state, row, serial) and not cc_idle(serial):
                progress['status'] = 'waiting_CC_idle_no_submission'
                serial.write(progress_path, progress)
                return progress
            answer = serial.advance(progress['order']['path'], identifier, gate_path, True, manifest_path)
            item.update(status='exporting_same_job', last_result=answer)
            progress['status'] = 'exporting'
            serial.write(progress_path, progress)
            return progress
        except Exception as error:
            current = serial.read(row['state_path']) if Path(row['state_path']).exists() else {}
            pending = pending_jobs(current, row, serial)
            progress.update(status='same_job_pending_transport_attention' if transport_uncertainty(error)
                            and pending and current.get('status') != 'failed' else 'failed',
                            error=str(error), pending_job_ids=pending)
            serial.write(progress_path, progress)
            return progress
    count = len(progress['ready_for_ue'])
    progress.update(status='all_CC_exports_complete_visual_batch_review_pending' if count == len(order['cases'])
                    else 'assembly_capture_complete_pending_batch_numeric_registration' if phase != 'export'
                    else 'pending_batch_numeric_registration_or_assembly', active_character_id=None)
    serial.write(progress_path, progress)
    return progress


def run(progress_path, gate_path, phase='all', registry_path=None, poll_seconds=5, once=False):
    _, serial, _, _, _ = checked(progress_path)
    # One global new-controller owner even if somebody selects another progress
    # directory. Original per-case/geometry/export locks remain in force too.
    with serial.controller_lock(serial.RUNTIME / 'continuous_cc_v1_owner'):
        previous = None
        while True:
            progress = tick(progress_path, gate_path, phase, registry_path)
            observed = (progress.get('active_character_id'), progress['status'], len(progress['ready_for_ue']))
            if observed != previous:
                print(json.dumps(dict(current=observed[0], status=observed[1], ready=observed[2]), ensure_ascii=False), flush=True)
                previous = observed
            if once or progress['status'] not in ('assembling', 'exporting', 'waiting_CC_idle_no_submission', 'same_job_pending_transport_attention'):
                return progress
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
    if args.action == 'prepare':
        if not all((args.order, args.policy, args.directory)) or args.execute:
            parser.error('Offline prepare needs order/policy/exclusive directory; never execute')
        result = prepare(args.order, args.policy, args.directory)
    elif not args.execute:
        if not args.progress:
            parser.error('Existing progress required')
        result = checked(args.progress)[4]
    else:
        if not args.progress or not args.gate:
            parser.error('Execution needs progress and actual representative gate')
        result = run(args.progress, args.gate, args.phase, args.caps_registry, args.poll_seconds, args.once)
    print(json.dumps({'status': result['status'], 'active_character_id': result.get('active_character_id'),
                      'ready_for_ue': len(result['ready_for_ue']),
                      'pending_native704': len(result['pending_native704_authorizations'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
