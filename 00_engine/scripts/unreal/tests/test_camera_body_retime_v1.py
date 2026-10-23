"""Pure-Python temporal invariants; no UE import or application connection."""
import importlib.util
import math
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / 'ue_camera_body_retime_v1.py'
spec = importlib.util.spec_from_file_location('camera_body_retime_test', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_c018_reaches_complete_source_endpoint_without_wrap_or_hold():
    result = m.body_mapping(60, 1, 485, 8.083333015441895)
    assert len(result['times']) == 601
    assert result['times'][0] == 0 and result['times'][-1] == 10
    assert result['body_play_rate'] == pytest.approx(485/600)
    assert result['source_times'][-1] == pytest.approx(485/60)
    differences = [b-a for a, b in zip(result['source_times'], result['source_times'][1:])]
    assert min(differences) > 0
    assert max(differences)-min(differences) < 1e-12
    assert not result['body_looped'] and result['seams_seconds'] == []


def test_root_trajectory_spatial_extent_is_preserved_while_clock_slows():
    result = m.body_mapping(60, 1, 485, 485/60)
    # Analytic source trajectory, including nonzero initial displacement.
    root = lambda t: (100+35*t, -7+2*t*t, math.sin(t))
    samples = [root(t) for t in result['source_times']]
    assert samples[0] == root(0)
    assert samples[-1] == root(485/60)
    assert samples[300] == pytest.approx(root((485/60)/2))
    assert samples[-1][0] - samples[0][0] == pytest.approx(35*485/60)
    assert samples[0][0] != 0  # no implicit root reset or in-place conversion


def test_face_clock_does_not_inherit_slow_body_clock():
    result = m.body_mapping(60, 1, 485, 485/60)
    composer = m.private_module('ue_compose_native_face_body_v1')
    assert result['source_times'][300] == pytest.approx(4.041666666666667)
    assert composer.face_time(result['times'][300], 0, 5, result['face_play_rate'], 'loop') == 0
    assert composer.face_time(7.5, 0, 5, result['face_play_rate'], 'loop') == 2.5
    assert result['face_period_seconds'] == 5 and result['face_play_rate'] == 1


@pytest.mark.parametrize('frames,rate', [(420,.7), (599,599/600), (600,1.), (900,1.)])
def test_inclusive_seven_exclusive_ten_slowdown_boundary(frames, rate):
    result = m.body_mapping(60, 1, frames, frames/60)
    assert result['body_play_rate'] == pytest.approx(rate)
    assert result['body_retimed'] is (frames < 600)


@pytest.mark.parametrize('frames', [1, 310, 383, 419])
def test_under_seven_including_actual_run_and_jump_rejected(frames):
    with pytest.raises(ValueError, match='below seven'):
        m.body_mapping(60, 1, frames, frames/60)


def test_long_window_uses_original_speed_and_records_later_start():
    result = m.body_mapping(60, 1, 2041, 34.016666412353516, 14.)
    assert result['body_play_rate'] == 1
    assert result['source_times'][0] == 14 and result['source_times'][-1] == 24
    assert result['source_times'][123] == pytest.approx(14+123/60)
    assert result['mode'] == 'trim_original_rate'


@pytest.mark.parametrize('args', [(60,1,485,485/60,1), (60,1,683,683/60,2),
    (60,1,600,10,-1), (60,1,600,10,True), (60,1,600,10,float('nan'))])
def test_invalid_window_does_not_silently_wrap_or_clamp(args):
    with pytest.raises(ValueError):
        m.body_mapping(*args)


@pytest.mark.parametrize('args', [(0,1,485,485/60), (60,0,485,485/60),
    (60,1,485.5,485.5/60), (60,1,485,10), (True,1,485,485/60),
    (30000,1001,300,300*1001/30000), (60,1,485,float('inf'))])
def test_bad_grid_or_timing_mismatch_fails_closed(args):
    with pytest.raises(ValueError):
        m.body_mapping(*args)


def test_task_rejects_face_rate_and_outside_report(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path)
    task = {'sex':'female','action_id':'ACT_EXP_F_018','window_id':'c018_f_ten_v1',
            'source_start_seconds':0,'report_path':str(tmp_path/'receipt.json')}
    assert m.validate_task(task) == task
    with pytest.raises(ValueError):
        m.validate_task(dict(task, face_rate=.8))
    with pytest.raises(ValueError):
        m.validate_task(dict(task, report_path=str(tmp_path.parent/'old.json')))
