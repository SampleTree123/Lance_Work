"""Fresh subject orchestration retains its calibration and explicit review."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_cc_explicit_corner_fresh_geometry_repair_v3 as explicit


def state():
    return {'status': 'prepared', 'steps': {}, 'completed_offline_steps': []}


def test_new_subject_starts_with_own_capture_then_four_probes():
    s = state()
    names = [name for name, operation in explicit.fresh.STEP_PLAN]
    assert names[:6] == ['01_capture', '02_calibrate_zero', '02_calibrate_x',
                        '02_calibrate_y', '02_calibrate_z', '03_identity_roundtrip']
    assert explicit.next_step(s) == '01_capture'
    s['steps']['01_capture'] = {'status': 'completed'}
    assert explicit.next_step(s) == '02_calibrate_zero'


def test_pending_job_stops_loop_without_starting_another_subject_step(monkeypatch):
    s = state()
    calls = []
    class Driver:
        def verify_state_inputs(self, s): pass
    def pending(s, driver, **kwargs):
        calls.append(kwargs)
        s['steps']['01_capture'] = {'status': 'pending'}
    monkeypatch.setattr(explicit.fresh, 'advance', pending)
    explicit.advance(s, Driver(), max_steps=20)
    assert len(calls) == 1
    assert s['steps'] == {'01_capture': {'status': 'pending'}}


def test_final_review_uses_explicit_pixel_scope_without_original_review(monkeypatch):
    s = state()
    for name, operation in explicit.fresh.STEP_PLAN:
        if name == '10_review': break
        if operation == 'offline': s['completed_offline_steps'].append(name)
        else: s['steps'][name] = {'status': 'completed'}
    called = []
    class Driver:
        def verify_state_inputs(self, s): pass
        def persist(self, s): called.append('persist')
    def review(s, driver):
        called.append('explicit_pixel_review')
        s['status'] = 'completed'
    monkeypatch.setattr(explicit, 'explicit_pixel_review', review)
    monkeypatch.setattr(explicit.fresh, 'advance', lambda *args, **kw: pytest.fail('Original review must not run'))
    explicit.advance(s, Driver())
    assert called == ['explicit_pixel_review', 'persist']
    assert '10_review' in s['completed_offline_steps']
