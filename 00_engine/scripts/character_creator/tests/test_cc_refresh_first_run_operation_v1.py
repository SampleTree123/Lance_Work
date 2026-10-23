"""Owned route lifecycle with the real Bridge driver; no app calls."""
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_refresh_first_run_operation_v1 as op
import cc_character_creation_job_state_v1 as jobs


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    dispatcher = tmp_path / 'dispatcher.py'
    dispatcher.write_text('routes = {' + op.ANCHOR + '}\n', encoding='utf-8')
    monkeypatch.setattr(op, 'DISPATCHER', dispatcher)
    monkeypatch.setattr(op, 'ORIGINAL_SHA', op.pin(dispatcher)['sha256'])
    run, stage, bridge = (tmp_path / x for x in ('run', 'stage', 'bridge'))
    attempt, staged = run / 'CFD40_TEST_001' / 'attempt_001', stage / 'CFD40_TEST_001'
    attempt.mkdir(parents=True)
    staged.mkdir(parents=True)
    request = {'character_id': 'CFD40_TEST_001'}
    state = dict(character_id=request['character_id'], attempt_dir=str(attempt), stage_dir=str(staged),
        state_path=str(attempt / 'state.json'), request=request, request_fingerprint=jobs.fingerprint(request),
        inputs={'dispatcher': jobs.bind(dispatcher)}, status='prepared', steps={})
    driver = jobs.BridgeStepDriver(run_root=run, stage_root=stage, bridge_root=bridge)
    driver.persist(state)
    owner = op.FirstRunOperation(tmp_path / 'controller', sleep=lambda _: pytest.fail('Unexpected wait'))
    return state, driver, owner, dispatcher


def result(driver, state, status='succeeded'):
    step = state['steps']['01_prelash']
    path = driver.bridge_root / 'results' / (step['job_id'] + '.json')
    op.write(path, dict(job_id=step['job_id'], command='validate_bodyfit_library', status=status,
        result=dict(library_file=step['library']['path'], output_dir=step['output_dir'])))
    return path


def pending(fixture):
    state, driver, owner, _ = fixture
    driver.client_call = lambda args: {'healthy': True} if args == ['health'] else {'queued': True}
    step = driver.submit_step(state, '01_prelash', {'fixture': True}, Path(state['attempt_dir']) / '01_prelash')
    return step


def test_original_driver_pending_before_single_dispatch_and_restore_before_persist(fixture):
    state, driver, owner, dispatcher = fixture
    calls = []
    output = Path(state['attempt_dir']) / '01_prelash'
    def client(args):
        if args == ['health']:
            return {'healthy': True}
        calls.append(args)
        persisted = op.read(state['state_path'])
        assert persisted['steps']['01_prelash']['status'] == 'pending'
        assert persisted['steps']['01_prelash']['job_id'] == args[args.index('--job-id') + 1]
        assert op.pin(dispatcher)['sha256'] != op.ORIGINAL_SHA
        result(driver, state)
        raise TimeoutError('Simulated lost acknowledgement after actual submit')
    def wrapped(args):
        if args == ['health']:
            return client(args)
        return owner.dispatch(args, client, state, driver, output, {})
    driver.client_call = wrapped
    step = driver.submit_step(state, '01_prelash', {'fixture': True}, output)
    assert len(calls) == 1 and op.pin(dispatcher)['sha256'] == op.ORIGINAL_SHA
    assert step['submission']['transport_error_preserved'].startswith('TimeoutError')
    driver.wait_step(state, '01_prelash', 0)
    assert step['status'] == 'succeeded'
    driver.verify_state_inputs(state)  # Original dispatcher pin is intact.


def test_restart_same_job_and_pre_dispatch_crash_stop_without_retry(fixture):
    state, driver, owner, dispatcher = fixture
    step = pending(fixture)
    intent, path = owner.prepare(state, step, Path(step['output_dir']), {}, driver.bridge_root)
    dispatcher.write_bytes(Path(intent['patched']['path']).read_bytes())
    with pytest.raises(ValueError, match='stopped before dispatch'):
        owner.reconcile()
    assert op.pin(dispatcher)['sha256'] == op.ORIGINAL_SHA
    assert owner.active() and op.read(path)['dispatch_attempted'] is False
    # Simulate a persisted dispatch followed by controller restart, not retry.
    op.write(path, {'dispatch_attempted': True})
    dispatcher.write_bytes(Path(intent['patched']['path']).read_bytes())
    waits = []
    def complete(_):
        waits.append(True)
        result(driver, state, 'failed')
    restarted = op.FirstRunOperation(owner.folder, sleep=complete)
    restarted.reconcile()
    assert len(waits) == 1 and op.pin(dispatcher)['sha256'] == op.ORIGINAL_SHA
    driver.wait_step(state, '01_prelash', 0)
    assert state['status'] == 'failed' and step['status'] == 'failed'


def test_malformed_terminal_restores_and_completed_crash_finishes_original_validation(fixture, monkeypatch):
    state, driver, owner, dispatcher = fixture
    step = pending(fixture)
    intent, path = owner.prepare(state, step, Path(step['output_dir']),
        {'wrapper': op.pin(dispatcher), 'sources': {}}, driver.bridge_root)
    op.write(path, {'dispatch_attempted': True})
    dispatcher.write_bytes(Path(intent['patched']['path']).read_bytes())
    terminal = result(driver, state)
    terminal.write_text('{broken', encoding='utf-8')
    with pytest.raises(ValueError):
        owner.reconcile()
    assert op.pin(dispatcher)['sha256'] == op.ORIGINAL_SHA
    result(driver, state)
    owner.reconcile()
    driver.wait_step(state, '01_prelash', 0)
    report_path = Path(step['output_dir']) / 'refresh_partial_report.json'
    report = dict(status='prelash_checkpoint_validated_not_final', stage_validated=True,
        config={'character_id': state['character_id']})
    op.write(report_path, report)
    driver.mark_step_complete(state, '01_prelash', {'report': report_path})
    validations = []
    def completed(current, key, filename, original_driver):
        original_driver.verify_completed_step(current, key)
        validations.append('original_completed_and_normal_validator')
        return op.read(current['steps'][key]['outputs']['report']['path'])
    monkeypatch.setattr(owner, 'report_gate', lambda *args: validations.append('wrapper_gate'))
    serial = SimpleNamespace(RUNTIME=driver.run_root, STAGE=driver.stage_root,
        BridgeStepDriver=lambda **_: driver, completed_report=completed)
    owner.finish_completed(serial)
    assert validations == ['original_completed_and_normal_validator', 'wrapper_gate']
    assert not owner.active()
    adopted = op.read(state['state_path'])
    assert len(adopted['first_run_history']) == 1
    driver.verify_state_inputs(adopted)


def test_old_pending_and_other_stages_unchanged_and_real_BM005_report_gate(monkeypatch, tmp_path):
    calls = []
    serial = SimpleNamespace(stage_tick=lambda *args: calls.append(args) or None)
    monkeypatch.setattr(op, 'short_alias', lambda *_: pytest.fail('Old path must not prepare alias'))
    owner = op.FirstRunOperation(tmp_path)
    owner.install(serial)
    for step in ('01_prelash', '02_lash'):
        state = {'character_id': 'CFD40_TEST_001', 'steps': {'01_prelash': {'status': 'pending'}}}
        serial.stage_tick(state, step, {'old': True}, 'report.json', SimpleNamespace(), lambda _: None)
    assert len(calls) == 2 and all(row[2] == {'old': True} for row in calls)
    run = Path(__file__).resolve().parents[3] / 'outputs/character_refresh_20261018_v1'
    manifest = op.read(run / 'BM005_first_run_prelash_v1/first_run_manifest_v1.json')
    adoption = op.read(run / 'BM005_first_run_prelash_v1/actual_first_run_adoption_v1.json')
    op.verify(manifest['library'])
    op.verify(adoption['report'])
    op.FirstRunOperation.report_gate(op.read(adoption['report']['path']),
        op.read(manifest['library']['path']), manifest['provenance'])
