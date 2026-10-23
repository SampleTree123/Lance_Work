"""Small offline scheduler/authorization tests; no Bridge or app calls."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

CC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('continuous_cc', CC / 'cc_refresh_continuous_cc_v1.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
numeric = controller.numeric


def test_missing_registration_is_pending_not_an_invented_limit():
    assert numeric.registered_cap(None, {}, {}, None) is None


def test_registration_cannot_use_other_asset_or_infinite_limit():
    measurement = {key: None for key in ('source_project', 'geometry_project', 'result_project', 'basis_report')}
    measurement.update(character_id='CASE_A', eyelash_asset={'asset_id': 'A'},
        measurement_selector='steps[phase=reloaded_native_export].body.lash_measurement', indices=list(range(704)),
        native_lash_count=704, mesh='CC_Base_Body', space_units='millimeters',
        measured_local_max_mm=4., measured_world_max_mm=5., protected_nonlash_body_count=13460, protected_nonlash_maximum_mm=.002)
    cap = dict(measurement, name='explicit_case_A', bounded_upper_limit_mm=6., magnitude_bound_registered=True)
    registry = dict(schema=numeric.CAP_SCHEMA, status='registered', reviewer='root_agent',
                    batch_processing_authorization={}, cases=[cap])
    serial = SimpleNamespace(read=lambda _: registry, bind=lambda _: {'path': 'registry'})
    cap['eyelash_asset'] = {'asset_id': 'B'}
    with pytest.raises(ValueError, match='eyelash_asset'):
        numeric.registered_cap('registry', measurement, {}, serial)
    cap['eyelash_asset'] = measurement['eyelash_asset']
    cap['bounded_upper_limit_mm'] = float('inf')
    with pytest.raises(ValueError, match='finite'):
        numeric.registered_cap('registry', measurement, {}, serial)


def test_numeric_receipt_never_persists_a_fake_root_visual_approval():
    rows = []
    compiler = SimpleNamespace(ASSEMBLY_SCHEMA='assembly', write_new=lambda path, value: rows.append(value))
    proxy = numeric.CompilerProxy(compiler, {'path': 'real_policy'})
    original = dict(schema='assembly', status='completed', recipe_complete=True, assembly_accepted=True,
                    root_visual_approval={'path': 'must_not_persist'}, user_final_acceptance=False)
    proxy.write_new('test_only', original)
    assert 'root_visual_approval' not in rows[0]
    assert rows[0]['visual_accepted'] is False and rows[0]['visual_review'] == 'pending_batch_review'
    assert rows[0]['batch_processing_authorization'] == {'path': 'real_policy'}
    assert 'root_visual_approval' in original  # Private adapter does not mutate caller/source.


def test_validation_failure_is_fatal_even_if_job_is_pending():
    assert not controller.transport_uncertainty(ValueError('wrong source hash'))
    assert not controller.transport_uncertainty(PermissionError('local access denied'))
    assert controller.transport_uncertainty(TimeoutError('transport timeout'))
    assert controller.transport_uncertainty(ConnectionError('transport disconnected'))


def test_stop_signal_performs_no_advance_or_application_call(tmp_path, monkeypatch):
    signal = tmp_path / 'stop_requested.json'
    signal.write_text('{}')
    progress = dict(status='assembling', stop_file=str(signal), execution_started=True)
    writes = []
    serial = SimpleNamespace(write=lambda path, value: writes.append(copy.deepcopy(value)))
    monkeypatch.setattr(controller, 'checked', lambda _: (None, serial, None, None, progress))
    result = controller.tick(tmp_path / 'progress.json', 'unused_gate')
    assert result['status'] == 'stopped_no_new_submissions'
    assert len(writes) == 1  # No gate/health/submit/wait/cancel API even exists on this fake.


def test_missing_cap_continues_to_next_assembly_without_export(tmp_path, monkeypatch):
    paths = [tmp_path / 'captured.json', tmp_path / 'next.json']
    for path in paths:
        path.write_text('{}')
    rows = [dict(character_id=name, state_path=str(path), geometry_state=str(tmp_path / ('g_' + name)))
            for name, path in zip(('AF003', 'AF004'), paths)]
    states = {str(paths[0]): {'facts': {'visual_report': {}, 'review_ready_staged_final': {}}}, str(paths[1]): {}}
    progress = dict(status='assembling', stop_file=str(tmp_path / 'absent_stop'), order={'path': 'frozen_order'},
                    items={'AF003': {'measurement': {'character_id': 'AF003'}}},
                    ready_for_ue=[], pending_native704_authorizations=[])
    calls = []
    serial = SimpleNamespace(read=lambda path: states[str(path)], write=lambda *args: None,
        representative_evidence=lambda *args: None,
        advance=lambda order, identifier, *args: calls.append(identifier) or {'status': 'geometry_same_state_pending'})
    monkeypatch.setattr(controller, 'checked', lambda _: (None, serial, {'cases': rows, 'batch_plan': {'path': 'plan'}}, {}, progress))
    monkeypatch.setattr(controller, 'pending_jobs', lambda *args: [])
    monkeypatch.setattr(controller, 'cc_idle', lambda _: True)
    result = controller.tick(tmp_path / 'progress.json', 'gate')
    assert calls == ['AF004'] and result['status'] == 'assembling'
    assert not result['ready_for_ue']  # Missing-cap source was not exported or accepted.


def test_ready_queue_old_pins_cannot_be_overwritten():
    rows = [dict(character_id='CASE_A', export_inventory={'sha256': 'original'})]
    with pytest.raises(ValueError, match='never overwrite'):
        controller.append_unique(rows, dict(character_id='CASE_A', export_inventory={'sha256': 'changed'}))
    assert rows[0]['export_inventory']['sha256'] == 'original'
