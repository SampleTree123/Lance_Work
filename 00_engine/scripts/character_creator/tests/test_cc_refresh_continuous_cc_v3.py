"""Offline scheduler branches only; fixtures are not real CC/approval evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

CC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('_test_continuous_v3', CC / 'cc_refresh_continuous_cc_v3.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def fixture(tmp_path, monkeypatch):
    def read(path):
        return json.loads(Path(path).read_text())
    def bind(path):
        return {'path': str(Path(path).resolve()), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    def verify(record, _label):
        if bind(record['path'])['sha256'] != record['sha256']:
            raise ValueError('Fixture pin changed')
    def write(path, value):
        Path(path).write_text(json.dumps(value))
    state_path = tmp_path / 'AF005_state.json'
    write(state_path, {'character_id': 'CFD40_AF_005', 'status': 'failed', 'steps': {}, 'facts': {}})
    order_path = tmp_path / 'order.json'
    order = {'cases': [dict(character_id='CFD40_AF_005', state_path=str(state_path), geometry_state=str(tmp_path / 'missing_geo')),
                       dict(character_id='CFD40_BM_001', state_path=str(tmp_path / 'next.json'), geometry_state=str(tmp_path / 'next_geo'))],
             'batch_plan': {'path': 'unchanged-test-plan'}}
    write(order_path, order)
    history = tmp_path / 'prior_failed.json'
    write(history, {'schema': controller.SCHEMA, 'status': 'failed', 'order': bind(order_path),
                    'active_character_id': 'CFD40_AF_005'})
    decision = tmp_path / 'root_decision.md'
    decision.write_text('Offline scheduling fixture CFD40_AF_005 ' + bind(state_path)['sha256'])
    monkeypatch.setattr(controller, 'ROOT_DECISION', decision)
    registry = tmp_path / 'registry.json'
    write(registry, {'schema': controller.DEFER_SCHEMA, 'status': 'authorized', 'reviewer': 'root_agent',
        'cases': [{'character_id': 'CFD40_AF_005', 'failed_state': bind(state_path), 'failed_progress': bind(history),
            'root_authorization': bind(decision), 'decision': 'defer_failed_AF005_only_until_local_editor_recovery',
            'acceptance_granted': False}]})
    calls = []
    serial = SimpleNamespace(read=read, bind=bind, verify=verify, write=write,
        representative_evidence=lambda *_: None,
        advance=lambda _order, identifier, *_: calls.append(identifier) or {'status': 'offline_fixture_no_application'})
    return SimpleNamespace(read=read, bind=bind, write=write, state_path=state_path, order=order,
        order_path=order_path, history=history, registry=registry, calls=calls, serial=serial)


def progress_for(f, deferred):
    return {'status': 'prepared_not_started', 'stop_file': str(f.state_path.parent / 'stop.json'),
        'order': f.bind(f.order_path), 'ready_for_ue': [], 'items': {}, 'deferred_cases': deferred,
        'pending_native704_authorizations': [], 'original_order_case_count': len(f.order['cases'])}


def test_exact_af005_defer_continues_next_without_state_change(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    before = f.bind(f.state_path)
    deferred = controller.deferrals(f.registry, f.bind(f.history), f.serial, dict(f.order, _path=f.order_path))
    progress = progress_for(f, deferred)
    monkeypatch.setattr(controller, 'checked', lambda _: (None, f.serial, f.order, {}, progress))
    monkeypatch.setattr(controller, 'cc_idle', lambda _: True)
    result = controller.tick(tmp_path / 'new_progress.json', 'unchanged-gate')
    assert f.calls == ['CFD40_BM_001']
    assert result['status'] == 'assembling'
    assert result['items']['CFD40_AF_005']['status'] == 'deferred_unresolved_not_ready'
    assert result['ready_for_ue'] == [] and f.bind(f.state_path) == before


def test_unregistered_failed_case_still_stops_before_next(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    progress = progress_for(f, {})
    monkeypatch.setattr(controller, 'checked', lambda _: (None, f.serial, f.order, {}, progress))
    result = controller.tick(tmp_path / 'new_progress.json', 'unchanged-gate')
    assert result['status'] == 'failed' and result['active_character_id'] == 'CFD40_AF_005'
    assert f.calls == []
    # Authorizing AF005 must not hide a different person's subsequent failure.
    deferred = controller.deferrals(f.registry, f.bind(f.history), f.serial, dict(f.order, _path=f.order_path))
    f.write(tmp_path / 'next.json', {'character_id': 'CFD40_BM_001', 'status': 'failed', 'steps': {}})
    progress = progress_for(f, deferred)
    monkeypatch.setattr(controller, 'checked', lambda _: (None, f.serial, f.order, {}, progress))
    result = controller.tick(tmp_path / 'other_failure_progress.json', 'unchanged-gate')
    assert result['status'] == 'failed' and result['active_character_id'] == 'CFD40_BM_001'
    assert f.calls == []


def test_pending_af005_cannot_be_deferred_even_with_exact_authorization(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    state = f.read(f.state_path)
    state['steps'] = {'01_prelash': {'status': 'pending', 'job_id': 'same_pending_job'}}
    f.write(f.state_path, state)
    registry = f.read(f.registry)
    registry['cases'][0]['failed_state'] = f.bind(f.state_path)
    controller.ROOT_DECISION.write_text('Offline scheduling fixture CFD40_AF_005 ' + f.bind(f.state_path)['sha256'])
    registry['cases'][0]['root_authorization'] = f.bind(controller.ROOT_DECISION)
    f.write(f.registry, registry)
    with pytest.raises(ValueError, match='Pending job cannot be deferred'):
        controller.deferrals(f.registry, f.bind(f.history), f.serial, dict(f.order, _path=f.order_path))
    assert f.calls == []


def test_deferred_case_cannot_produce_allcomplete_or_shrink_original_order(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    deferred = controller.deferrals(f.registry, f.bind(f.history), f.serial, dict(f.order, _path=f.order_path))
    progress = progress_for(f, deferred)
    progress['ready_for_ue'] = [{'character_id': 'CFD40_BM_001'}]  # Branch model only, not an actual export receipt.
    original = copy.deepcopy(f.order)
    monkeypatch.setattr(controller, 'checked', lambda _: (None, f.serial, f.order, {}, progress))
    result = controller.tick(tmp_path / 'new_progress.json', 'unchanged-gate', phase='export')
    assert result['status'] == 'deferred_unresolved'
    assert result['original_order_case_count'] == 2 and f.order == original
    assert result['ready_for_ue'] == [{'character_id': 'CFD40_BM_001'}] and f.calls == []
