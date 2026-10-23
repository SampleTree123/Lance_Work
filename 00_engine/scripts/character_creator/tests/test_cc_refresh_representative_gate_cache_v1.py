"""Offline file-boundary tests; no real representative/application acceptance."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

CC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('_tested_rep_cache', CC / 'cc_refresh_representative_gate_cache_v1.py')
cache_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache_module)

# The production helper clones this real function's code and only redirects
# its batch global to the private unmodified owner's I/O. No cache mirror.
calls = []
mutation = []


def original_gate(plan_path, gate_path):
    calls.append(str(gate_path))
    plan = batch.read(plan_path)
    gate = batch.read(gate_path)
    batch.verified(plan['leaf'], 'fixture pinned data')
    registry = batch.transfer.read(gate['implicit_registry'])
    state = batch.transfer.status(gate['request'])
    if mutation:
        mutation.pop()()
    if registry.get('fail') or state.get('status') != 'completed':
        raise ValueError('Real fixture validation failed')
    return {'passed': True, 'gate': batch.pin(gate_path)}


def put(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


@pytest.fixture
def setup(tmp_path):
    calls.clear()
    mutation.clear()
    leaf = put(tmp_path / 'leaf.json', {'fixture': 1})
    registry = put(tmp_path / 'registry.json', {'fail': False})
    request = put(tmp_path / 'request.json', {})
    put(tmp_path / 'controller_status.json', {'status': 'completed'})
    plan = put(tmp_path / 'plan.json', {'leaf': pin(leaf)})
    gate = put(tmp_path / 'gate.json', {'implicit_registry': str(registry), 'request': str(request)})
    order = put(tmp_path / 'order.json', {'fixture_order': 1})
    cache = cache_module.RepresentativeGateCache([pin(CC / 'cc_refresh_representative_gate_cache_v1.py')])
    serial = SimpleNamespace(representative_evidence=original_gate)
    cache.bind(serial, pin(order))
    return SimpleNamespace(cache=cache, serial=serial, leaf=leaf, registry=registry,
                           request=request, plan=plan, gate=gate, order=order, folder=tmp_path)


def test_success_reuse_exact_closure_and_key_change(setup):
    s = setup
    assert s.serial.representative_evidence(s.plan, s.gate)['passed']
    assert s.serial.representative_evidence(s.plan, s.gate)['passed']
    assert len(calls) == 1
    # Implicit registry and both status candidates, including absence, observed.
    assert str(s.registry.absolute()) in s.cache.entry['files']
    assert s.cache.entry['files'][str((s.folder / 'worker_status.json').absolute())][1] == 'missing'
    # Equal bytes but a replacement file identity invalidates success.
    replacement = s.folder / 'replacement.json'
    replacement.write_bytes(s.leaf.read_bytes())
    replacement.replace(s.leaf)
    assert s.serial.representative_evidence(s.plan, s.gate)['passed']
    assert len(calls) == 2
    other_order = put(s.folder / 'order2.json', {'fixture_order': 2})
    serial = SimpleNamespace(representative_evidence=original_gate)
    s.cache.bind(serial, pin(other_order))
    assert serial.representative_evidence(s.plan, s.gate)['passed']
    assert len(calls) == 3
    gate2 = put(s.folder / 'gate2.json', json.loads(s.gate.read_text()))
    assert serial.representative_evidence(s.plan, gate2)['passed']
    assert len(calls) == 4


def test_implicit_status_change_missing_and_exception_never_cached(setup):
    s = setup
    s.serial.representative_evidence(s.plan, s.gate)
    worker = put(s.folder / 'worker_status.json', {'status': 'failed'})
    with pytest.raises(ValueError, match='fixture validation failed'):
        s.serial.representative_evidence(s.plan, s.gate)
    assert s.cache.entry is None
    with pytest.raises(ValueError, match='fixture validation failed'):
        s.serial.representative_evidence(s.plan, s.gate)
    assert len(calls) == 3
    worker.unlink()
    s.serial.representative_evidence(s.plan, s.gate)
    s.registry.unlink()
    with pytest.raises(FileNotFoundError):
        s.serial.representative_evidence(s.plan, s.gate)
    assert s.cache.entry is None and len(calls) == 5


def test_mid_validation_change_cannot_cache_and_wrapper_refuses_old_progress(setup):
    s = setup
    mutation.append(lambda: put(s.registry, {'fail': False, 'changed_during_validation': True}))
    with pytest.raises(ValueError, match='changed across full validation'):
        s.serial.representative_evidence(s.plan, s.gate)
    assert s.cache.entry is None
    s.serial.representative_evidence(s.plan, s.gate)
    assert len(calls) == 2
    wrapper_spec = importlib.util.spec_from_file_location('_tested_rep_wrapper', CC / 'cc_refresh_continuous_cc_v4.py')
    wrapper = importlib.util.module_from_spec(wrapper_spec)
    wrapper_spec.loader.exec_module(wrapper)
    base, _, _ = wrapper.controller()
    old = put(s.folder / 'old_progress.json', {'schema': base.SCHEMA})
    with pytest.raises(ValueError, match='New v4 progress'):
        base.checked(old)
