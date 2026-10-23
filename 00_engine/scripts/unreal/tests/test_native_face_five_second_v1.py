import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('ue_native_face_five_second_v1')
c = load('ue_capture_native_face_five_second_v1')


@pytest.fixture
def task(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path)
    return {'sex': 'female', 'composite_id': 'gentle_test', 'body_animation': '/Game/Test/Body',
            'face_animation': '/Game/Test/Face', 'reference_mesh': '/Game/Test/Mesh',
            'allowed_face_curve_names': ['CTRL_expressions_eyeBlinkL', 'CTRL_expressions_jawOpen'],
            'face_start_seconds': 5.35, 'face_end_seconds': 10.35, 'face_rate': 1,
            'face_playback': 'hold', 'body_mode': 'static', 'static_use_reference_pose': True,
            'report_path': str(tmp_path / 'result.json')}


@pytest.mark.parametrize('change', [
    {'face_rate': .5}, {'face_rate': 2}, {'face_rate': True}, {'face_rate': float('nan')},
    {'face_playback': 'loop'}, {'face_end_seconds': 8}, {'face_end_seconds': 11},
    {'face_start_seconds': -1, 'face_end_seconds': 4}, {'face_end_seconds': float('inf')},
    {'body_mode': 'animation'}, {'static_use_reference_pose': False},
    {'face_envelope': None}, {'face_envelope': {'intensity': 1}},
    {'allow_face_truncation': True}, {'allowed_face_curve_names': []},
])
def test_rejects_retiming_freeze_loops_and_envelopes_before_unreal(task, change):
    task.update(change)
    with pytest.raises(ValueError):
        m.run(task)


def test_sample_mapping_is_continuous_native_time_and_composer_is_isolated(task):
    old = load('ue_compose_native_face_body_v1')
    old_run, old_assets = old.RUN, old.ASSET_ROOT
    m.validate_task(task)
    module = m.composer_module()
    assert module.RUN == m.RUN and module.ASSET_ROOT == m.ASSET_ROOT
    assert (old.RUN, old.ASSET_ROOT) == (old_run, old_assets)
    values = [module.face_time(i/30, 5.35, 10.35, 1, 'hold') for i in range(151)]
    assert values == pytest.approx([5.35+i/30 for i in range(151)])
    assert all(b > a for a, b in zip(values, values[1:]))
    assert len(module.FACE_BONES) == 10


def test_rejects_report_escape(task, tmp_path):
    task['report_path'] = str(tmp_path / '..' / 'old_run' / 'result.json')
    with pytest.raises(ValueError, match='inside'):
        m.validate_task(task)


def test_preparation_does_not_replace_existing_task(tmp_path):
    path = tmp_path / 'task.json'
    m.write_new_or_identical(path, {'original': True})
    before = path.read_bytes()
    m.write_new_or_identical(path, {'original': True})
    with pytest.raises(ValueError, match='overwrite'):
        m.write_new_or_identical(path, {'original': False})
    assert path.read_bytes() == before


@pytest.fixture
def capture(task, tmp_path, monkeypatch):
    monkeypatch.setattr(c.contract, 'RUN', tmp_path)
    monkeypatch.setattr(c, 'RUN', tmp_path)
    return {'sex': 'female', 'animation': m.ASSET_ROOT + '/female/A_gentle_test',
            'composition_report': task['report_path'], 'times': [i/30 for i in range(151)],
            'output_dir': str(tmp_path / 'capture')}


@pytest.mark.parametrize('times', [[0, 5], [i/30 for i in range(150)],
    [i/30 for i in reversed(range(151))], [i/30 for i in range(150)]+[5.01],
    [False]+[i/30 for i in range(1,151)], [float('nan')]+[i/30 for i in range(1,151)]])
def test_capture_requires_complete_ordered_native_30fps_sample(capture, times):
    capture['times'] = times
    with pytest.raises(ValueError, match='151'):
        c.validate_task(capture)


def test_capture_gate_requires_success_and_full_frame_comparison(task, capture, monkeypatch):
    report = {'task': task, 'success': False, 'sources_unchanged': True,
              'destination': capture['animation'], 'face_bones': sorted(m.EXPECTED_FACE_BONES),
              'verification': {'duration_seconds': 5, 'fps': 60, 'all_frame_count': 301}}
    path = Path(task['report_path'])
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='successful'):
        c.run(capture)
    report['success'] = True
    report['verification']['all_frame_count'] = 151
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='all-frame'):
        c.run(capture)
    report['verification']['all_frame_count'] = 301
    path.write_text(json.dumps(report))
    fake = SimpleNamespace(RUN='old', MAX_CAPTURE_FRAMES=50, run=lambda value: value)
    monkeypatch.setattr(c.contract, 'load_isolated', lambda *_: fake)
    assert c.run(capture) == capture
    assert fake.RUN == c.RUN and fake.MAX_CAPTURE_FRAMES == 151


def test_capture_keeps_existing_settle_and_global_default():
    source = (Path(__file__).parents[1] / 'ue_capture_native_face_review_v1.py').read_text()
    assert 'MAX_CAPTURE_FRAMES=50' in source
    assert "if state['frames']<16:return" in source
    assert "CACHE='_dm_native_face_capture_v1'" in source
