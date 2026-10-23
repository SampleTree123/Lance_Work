"""One owned PRELASH route lease over the existing durable Bridge driver.

No other stage is replaced. Route stays owned until the same actual job ends;
only after exact restore may the original driver verify/persist/adopt the step.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

CC = Path(__file__).resolve().parent
DISPATCHER = CC / 'cc_validate_body_reconstruction.py'
ORIGINAL_SHA = '27b4c3a53897c7259a236729a3964b2a5f0c3d6aa1be96fdb961a2b670f84b2c'
RUNNER = CC / 'cc_run_character_refresh_bounded_entry_v1.py'
RUNNER_SHA = 'af5475c15eae0ee21e52d859ce2cc276dc63476642607ee8a9b4be09f1f5a297'
ANCHOR = '"character_refresh_normals": "cc_refresh_skin_normal_closure_v1"'
REPLACEMENT = '"character_refresh_normals": "cc_run_character_refresh_bounded_entry_v1"'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def verify(record):
    actual = pin(record['path'])
    if actual['sha256'] != record['sha256'] or ('bytes' in record and actual['bytes'] != record['bytes']):
        raise ValueError('Owned first-run input changed: ' + record['path'])
    return actual


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def exclusive(path, value):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ValueError('Existing first-run evidence differs; never overwrite: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')


def runner():
    if pin(RUNNER)['sha256'] != RUNNER_SHA:
        raise ValueError('Frozen first-run runner changed')
    spec = importlib.util.spec_from_file_location('_operation_private_bounded_runner', RUNNER)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class LocalApi:
    @staticmethod
    def sha256_file(path):
        return pin(path)['sha256']


def bound_library(library):
    value = copy.deepcopy(library)
    config = value['refresh_assembly']
    target = runner()
    value['prelash_bounded_entry'] = {'schema': target.SCHEMA, 'first_run': True, 'policy': target.POLICY,
        'max_reentry_per_runtime_avatar': 1, 'implementation': pin(RUNNER),
        'source_project': config['source_project'], 'makeup_asset': config['assets']['makeup_eyebrow']}
    provenance = target.validate(value, LocalApi())
    return value, provenance


def short_alias(serial, state):
    actual = (Path(state['attempt_dir']) / '01_prelash').resolve()
    runtime = Path(serial.RUNTIME).resolve()
    identifier = state['character_id']
    if not identifier.startswith('CFD40_') or not identifier.replace('_', '').isalnum() or not actual.is_relative_to(runtime):
        raise ValueError('Exact owned first-run output required')
    actual.mkdir(parents=True, exist_ok=True)
    alias = runtime / ('p' + identifier.removeprefix('CFD40_').replace('_', '').lower())
    if not alias.exists():
        script = "New-Item -ItemType Junction -Path '{}' -Target '{}' | Out-Null".format(
            str(alias).replace("'", "''"), str(actual).replace("'", "''"))
        subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script], check=True, capture_output=True)
    if not alias.is_dir() or alias.resolve(strict=True) != actual:
        raise ValueError('Short alias is not the exact owned output junction')
    return alias


class FirstRunOperation:
    def __init__(self, folder, poll_seconds=3, sleep=time.sleep):
        self.folder = Path(folder).resolve()
        self.pointer = self.folder / 'first_run_active.json'
        self.poll_seconds, self.sleep = poll_seconds, sleep

    def active(self):
        pointer = read(self.pointer) if self.pointer.exists() else {}
        if not pointer.get('intent'):
            return None
        intent_path = Path(verify(pointer['intent'])['path'])
        if not intent_path.is_relative_to(self.folder / 'first_runs'):
            raise ValueError('First-run intent escapes its controller')
        intent = read(intent_path)
        operation = intent_path.with_name('operation.json')
        return intent, operation, read(operation)

    def prepare(self, state, step, alias, provenance, bridge_root):
        if self.active():
            raise ValueError('Another owned first-run operation is unresolved')
        if pin(DISPATCHER)['sha256'] != ORIGINAL_SHA:
            raise ValueError('Dispatcher must be original before first-run dispatch')
        folder = self.folder / 'first_runs' / state['character_id']
        original = DISPATCHER.read_bytes()
        source = original.decode('utf-8-sig')
        if source.count(ANCHOR) != 1:
            raise ValueError('Exact existing Normal route anchor changed')
        patched = source.replace(ANCHOR, REPLACEMENT, 1).encode('utf-8')
        for name, data in (('dispatcher_original.py', original), ('dispatcher_owned.py', patched)):
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != data:
                raise ValueError('Owned route evidence already differs')
            if not path.exists():
                path.write_bytes(data)
        snapshot = folder / 'pending_serial_snapshot.json'
        exclusive(snapshot, state)
        intent = {'schema': 'cfd40_owned_first_prelash_intent_v1', 'character_id': state['character_id'],
            'job_id': step['job_id'], 'library': step['library'], 'output_dir': step['output_dir'],
            'short_output': str(alias), 'state_path': state['state_path'], 'pending_snapshot': pin(snapshot),
            'result_path': str(Path(bridge_root) / 'results' / (step['job_id'] + '.json')),
            'dispatcher': str(DISPATCHER.resolve()), 'original': pin(folder / 'dispatcher_original.py'),
            'patched': pin(folder / 'dispatcher_owned.py'), 'provenance': provenance}
        intent_path = folder / 'intent.json'
        exclusive(intent_path, intent)
        op_path = folder / 'operation.json'
        write(op_path, {'status': 'intent_persisted_not_dispatched', 'dispatch_attempted': False})
        write(self.pointer, {'intent': pin(intent_path)})
        return intent, op_path

    @staticmethod
    def restore(intent):
        if Path(intent['dispatcher']).resolve() != DISPATCHER.resolve():
            raise ValueError('Owned dispatcher path changed')
        original, patched = verify(intent['original']), verify(intent['patched'])
        if original['sha256'] != ORIGINAL_SHA:
            raise ValueError('Original dispatcher backup is not the frozen source')
        current = pin(DISPATCHER)['sha256']
        if current == patched['sha256']:
            DISPATCHER.write_bytes(Path(original['path']).read_bytes())
        elif current != original['sha256']:
            raise ValueError('Unknown dispatcher owner/content; never overwrite')
        if pin(DISPATCHER)['sha256'] != original['sha256']:
            raise ValueError('Dispatcher restore failed')

    def reconcile(self):
        active = self.active()
        if not active:
            return None
        intent, op_path, operation = active
        for record in (intent['library'], intent['original'], intent['patched'], intent['pending_snapshot']):
            verify(record)
        state = read(intent['state_path'])
        step = state.get('steps', {}).get('01_prelash', {})
        if (state.get('character_id') != intent['character_id'] or step.get('job_id') != intent['job_id']
                or step.get('library') != intent['library']
                or Path(step.get('output_dir', '')).resolve() != Path(intent['output_dir']).resolve()
                or Path(intent['short_output']).resolve(strict=True) != Path(intent['output_dir']).resolve(strict=True)):
            raise ValueError('Owned operation does not match its original pending step')
        result_path = Path(intent['result_path'])
        if not result_path.exists() and not operation.get('dispatch_attempted'):
            self.restore(intent)
            operation.update(status='not_dispatched_restored_manual_attention', dispatch_attempted=False)
            write(op_path, operation)
            raise ValueError('First-run intent stopped before dispatch; restored, inspect same intent, never auto-submit')
        while not result_path.exists():
            # Absence, timeout, stopfile or restart never authorizes re-dispatch.
            if pin(DISPATCHER)['sha256'] not in (intent['original']['sha256'], intent['patched']['sha256']):
                raise ValueError('Unknown dispatcher while waiting for the same job')
            self.sleep(self.poll_seconds)
        try:
            result = read(result_path)
        finally:
            self.restore(intent)  # Even malformed terminal evidence must release our exact route.
        operation.update(status='terminal_restored', result=pin(result_path), terminal_status=result.get('status'))
        write(op_path, operation)
        if result.get('job_id') != intent['job_id'] or result.get('command') != 'validate_bodyfit_library' or result.get('status') not in ('succeeded', 'failed', 'cancelled'):
            raise ValueError('Unknown/mismatched terminal result; restored dispatcher, stop without retry')
        return intent

    def dispatch(self, command, original_call, state, driver, alias, provenance):
        step = state['steps']['01_prelash']
        def argument(name):
            return command[command.index(name) + 1]
        if (argument('--job-id') != step['job_id'] or Path(argument('--library-file')).resolve() != Path(step['library']['path']).resolve()
                or Path(argument('--output-dir')).resolve() != Path(step['output_dir']).resolve()):
            raise ValueError('Original Bridge submit differs from owned first-run step')
        intent, op_path = self.prepare(state, step, alias, provenance, driver.bridge_root)
        DISPATCHER.write_bytes(Path(intent['patched']['path']).read_bytes())
        if pin(DISPATCHER)['sha256'] != intent['patched']['sha256']:
            raise ValueError('Owned route installation failed')
        operation = {'status': 'dispatch_attempted_same_job_only', 'dispatch_attempted': True}
        write(op_path, operation)  # Before CLI, including an ambiguous return.
        payload = list(command)
        payload[payload.index('--output-dir') + 1] = str(alias)
        try:
            operation['submission'] = original_call(payload)
        except Exception as error:
            operation['transport_error'] = type(error).__name__ + ': ' + str(error)
        write(op_path, operation)
        self.reconcile()
        return operation.get('submission', {'job_id': step['job_id'],
            'same_job_actual_terminal_reconciliation': pin(intent['result_path']),
            'transport_error_preserved': operation.get('transport_error')})

    @staticmethod
    def report_gate(report, library, provenance):
        runtime, entry = report.get('runtime_wrapper', {}), report.get('bounded_editor_entry', {})
        if (report.get('success') is not True or report.get('config') != library['refresh_assembly']
                or report.get('implementation_sha256') != provenance['wrapper']['sha256']
                or runtime.get('first_run') is not True or runtime.get('implementation') != provenance['wrapper']
                or runtime.get('source_pins') != provenance['sources']
                or entry.get('provenance') != provenance or entry.get('source_pins_verified_after_run') is not True):
            raise ValueError('Actual first-run wrapper/source provenance gate failed')
        audits = entry.get('entry_audits', [])
        if (len(audits) != 2 or {a['phase'] for a in audits} != {'activate_editor_for_exact_layers', 'activate_editor_after_editing_reload'}
                or not all(a.get('ready') is True for a in audits)
                or len(set(entry['reentry_attempted_avatar_ids'])) != len(entry['reentry_attempted_avatar_ids'])):
            raise ValueError('Actual bounded entry/readiness evidence incomplete')
        for audit in audits:
            receipt = audit.get('cancel_only_reentry')
            if receipt and (receipt.get('cancel_count') != 1 or receipt.get('add_count') != 0 or receipt.get('replace_count') != 0
                    or receipt.get('unknown_dialog') is not None or receipt.get('application_accepted') is not False):
                raise ValueError('Only exact own preset Cancel may enter the editor')

    def adopt(self, serial, state, report, driver):
        intent, op_path, operation = self.active()
        if state['steps']['01_prelash']['status'] != 'completed':
            raise ValueError('Original driver must complete all actual Normal/stage gates first')
        intent_pin = pin(op_path.with_name('intent.json'))
        attestation_path = op_path.with_name('adoption.json')
        attestation = {'schema': 'cfd40_owned_first_prelash_adoption_v1', 'character_id': state['character_id'],
            'intent': intent_pin, 'report': state['steps']['01_prelash']['outputs']['report'],
            'original_driver_completed': True, 'runtime_wrapper_verified': True, 'recipe_complete': False}
        exclusive(attestation_path, attestation)
        additions = {'first_run_intent': intent_pin, 'first_run_adoption': pin(attestation_path),
            'first_run_wrapper': intent['provenance']['wrapper'],
            **{'first_run_source_' + name: record for name, record in intent['provenance']['sources'].items()}}
        for name, record in additions.items():
            if name in state['inputs'] and state['inputs'][name] != record:
                raise ValueError('Existing first-run input differs')
            state['inputs'][name] = record
        history = state.setdefault('first_run_history', [])
        if pin(attestation_path) not in history:
            history.append(pin(attestation_path))
        driver.persist(state)
        operation.update(status='adopted_by_original_driver', adoption=pin(attestation_path))
        write(op_path, operation)
        write(self.pointer, {'intent': None, 'last_adoption': pin(attestation_path)})

    def finish_completed(self, serial):
        """Crash after original completion must finish attestation before tick."""
        active = self.active()
        if not active:
            return
        intent = active[0]
        state = read(intent['state_path'])
        if state['steps']['01_prelash']['status'] != 'completed':
            return
        driver = serial.BridgeStepDriver(run_root=serial.RUNTIME, stage_root=serial.STAGE)
        # Original completed_report rechecks Bridge payload, all bound outputs,
        # and the original Normal/eight-channel validator in serial v2.
        report = serial.completed_report(state, '01_prelash', 'refresh_partial_report.json', driver)
        if (report.get('status') != 'prelash_checkpoint_validated_not_final'
                or report.get('stage_validated') is not True
                or report['config']['character_id'] != state['character_id']):
            raise ValueError('Original same-case validated PRELASH status required')
        library = read(intent['library']['path'])
        self.report_gate(report, library, intent['provenance'])
        self.adopt(serial, state, report, driver)

    def install(self, serial):
        original_stage = serial.stage_tick
        def stage_tick(state, step_id, library, filename, driver, validate):
            active = self.active()
            owned = active and active[0]['character_id'] == state['character_id']
            fresh = step_id == '01_prelash' and not state.get('steps') and state.get('facts', {}).get('geometry', {}).get('result_project')
            if step_id != '01_prelash' or not (fresh or owned):
                return original_stage(state, step_id, library, filename, driver, validate)
            if owned:
                value, provenance = read(active[0]['library']['path']), active[0]['provenance']
            else:
                value, provenance = bound_library(library)
            alias = short_alias(serial, state)
            original_call = driver.client_call
            def client_call(command):
                if command and command[0] == 'validate-bodies':
                    return self.dispatch(command, original_call, state, driver, alias, provenance)
                return original_call(command)
            def validation(report):
                validate(report)
                self.report_gate(report, value, provenance)
            driver.client_call = client_call
            try:
                report = original_stage(state, step_id, value, filename, driver, validation)
            finally:
                driver.client_call = original_call
            if report is not None:
                self.report_gate(report, value, provenance)
                self.adopt(serial, state, report, driver)
            return report
        serial.stage_tick = stage_tick
        return serial
