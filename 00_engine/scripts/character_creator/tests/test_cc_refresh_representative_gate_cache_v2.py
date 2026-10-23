"""Private dispatch-boundary fixtures; never real geometry.advance or locks."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

CC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('_geometry_cache_under_test', CC / 'cc_refresh_representative_gate_cache_v2.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
gate_calls = []


def put(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def full_gate(plan_path, gate_path):
    gate_calls.append(str(gate_path))
    plan = batch.read(plan_path)
    batch.verified(plan['leaf'], 'fixture current source')
    return {'passed': True, 'gate': batch.pin(gate_path)}


@pytest.fixture
def fixture(tmp_path):
    gate_calls.clear()
    leaf = put(tmp_path / 'leaf.json', {'source': 1})
    plan = put(tmp_path / 'plan.json', {'leaf': pin(leaf)})
    gate = put(tmp_path / 'gate.json', {'fixture': True})
    order = put(tmp_path / 'order.json', {'fixture_order': True})
    counts = dict(owner=0, checked_plan=0, verify_subject=0, run=0, original_gate=0)
    read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
    def owner():
        counts['owner'] += 1
        def checked_plan(path):
            counts['checked_plan'] += 1
            return read(path)
        def verify_subject():
            counts['verify_subject'] += 1
        def representative_gate(*args):
            counts['original_gate'] += 1
            return {'passed': True, 'explicit_original_semantics': True}
        return SimpleNamespace(read=read, checked_plan=checked_plan,
            verify_subject=verify_subject, representative_gate=representative_gate)
    def advance(order_path, identifier, gate_path, *, batch=None, execute=False, run=None):
        # Exercise the existing dependency-injection boundary, without loading
        # the real geometry advance, locks, subprocesses or CC.
        batch = batch or geometry.owner()
        checked = batch.checked_plan(plan)
        result = batch.representative_gate(plan, checked, gate_path)
        batch.verify_subject()
        if execute:
            run(identifier)
        return result
    def run(identifier):
        counts['run'] += 1
    geometry = SimpleNamespace(owner=owner, advance=advance, untouched=object())
    serial = SimpleNamespace(representative_evidence=full_gate, geometry=geometry)
    cache = helper.RepresentativeGateCache([pin(CC / 'cc_refresh_representative_gate_cache_v2.py')])
    cache.bind(serial, pin(order))
    return SimpleNamespace(serial=serial, cache=cache, geometry=geometry, owner=owner,
                           advance=advance, counts=counts, plan=plan, gate=gate,
                           leaf=leaf, order=order, run=run)


def test_direct_geometry_entry_reuses_and_current_person_runs_every_time(fixture):
    f = fixture
    first = f.serial.representative_evidence(f.plan, f.gate)
    entry = f.cache.entry
    for _ in range(2):
        assert f.serial.geometry.advance(f.order, 'fixture_person', f.gate, execute=True, run=f.run) == first
    assert f.cache.entry is entry and len(gate_calls) == 1
    assert f.counts['checked_plan'] == f.counts['verify_subject'] == f.counts['run'] == 2
    assert f.counts['owner'] == 2 and f.counts['original_gate'] == 0
    assert f.geometry.owner is f.owner and f.geometry.advance is f.advance
    assert f.serial.geometry is not f.geometry
    assert f.serial.geometry.untouched is f.geometry.untouched


def test_changed_file_still_runs_full_validator_and_fails(fixture):
    f = fixture
    f.serial.representative_evidence(f.plan, f.gate)
    put(f.leaf, {'changed': True})
    with pytest.raises(ValueError, match='File pin changed'):
        f.serial.geometry.advance(f.order, 'fixture_person', f.gate, execute=True, run=f.run)
    assert len(gate_calls) == 2 and f.cache.entry is None
    assert f.counts['checked_plan'] == 1
    assert f.counts['verify_subject'] == f.counts['run'] == 0
    assert f.geometry.owner is f.owner and f.geometry.advance is f.advance


def test_explicit_batch_and_explicit_none_preserve_original_semantics(fixture):
    f = fixture
    explicit = f.owner()
    for injected in (explicit, None):
        result = f.serial.geometry.advance(f.order, 'fixture_person', f.gate,
            batch=injected, execute=True, run=f.run)
        assert result['explicit_original_semantics'] is True
    assert gate_calls == [] and f.cache.entry is None
    assert f.counts['original_gate'] == 2
    assert f.counts['checked_plan'] == f.counts['verify_subject'] == f.counts['run'] == 2
