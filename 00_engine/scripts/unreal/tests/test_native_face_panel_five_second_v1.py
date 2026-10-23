import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('panel_five_second_test', Path(__file__).parents[1] / 'ue_native_face_panel_five_second_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


@pytest.mark.parametrize('frames,duration,seam', [(136, 4.5333333015441895, 136/30), (102, 3.4000000953674316, 3.4)])
def test_short_body_wraps_only_body_clock_at_original_rate(frames, duration, seam):
    result = m.body_mapping(30, 1, frames, duration)
    assert result['mode'] == 'repeat_body_original_speed'
    assert result['seams_seconds'] == pytest.approx([seam])
    assert result['source_times'][frames-1] == pytest.approx((frames-1)/30)
    assert result['source_times'][frames] == 0
    assert result['source_times'][frames+1] == pytest.approx(1/30)
    assert result['times'][frames] == pytest.approx(seam)
    assert result['times'][-1] == 5 and len(result['times']) == 151
    assert result['face_clock_wraps'] is False and result['body_retimed'] is False
    assert result['seams_blended'] is False


@pytest.mark.parametrize('frames', [150, 212, 585])
def test_long_body_is_first_five_seconds_without_rescaling(frames):
    result = m.body_mapping(30, 1, frames, frames/30)
    assert result['mode'] == 'crop_first_five_seconds'
    assert result['times'] == result['source_times']
    assert result['seams_seconds'] == [] and result['times'][-1] == 5


@pytest.mark.parametrize('args', [(0, 1, 136, 136/30), (30, 0, 136, 136/30), (30, 1, 0, 0),
    (30000, 1001, 100, 100*1001/30000), (30, 1, 136, 5), (30, 1, 136.5, 136.5/30),
    (True, 1, 136, 136), (float('nan'), 1, 136, 136/30)])
def test_bad_or_nonrepresentable_frame_grids_fail(args):
    with pytest.raises(ValueError):
        m.body_mapping(*args)


@pytest.fixture
def task(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path)
    return {'operation': 'compose', 'sex': 'female', 'face_id': 'smile', 'body_action_id': 'ACT_F03_AUDIENCE_01',
            'body_window_report': str(tmp_path/'body.json'), 'composite_id': 'test_v1', 'report_path': str(tmp_path/'compose.json')}


@pytest.mark.parametrize('change', [{'face_rate': .5}, {'face_envelope': None}, {'face_playback': 'loop'}, {'face_id': 'surprise'}, {'operation': 'unknown'}])
def test_task_rejects_unaccepted_faces_and_time_overrides(task, change):
    task.update(change)
    with pytest.raises(ValueError):
        m.run(task)


def test_output_escape_and_overwrite_rejected(task, tmp_path):
    task['report_path'] = str(tmp_path/'..'/'old.json')
    with pytest.raises(ValueError):
        m.validate_task(task)
    path = tmp_path/'evidence.json'
    m.write_new(path, {'saved': True})
    with pytest.raises(ValueError, match='overwrite'):
        m.write_new(path, {'saved': False})
    assert m.read(path) == {'saved': True}


def test_current_sources_have_eight_accepted_faces_and_ten_original_bodies():
    faces, bodies = m.accepted_faces(), m.body_sources()
    assert len(faces) == 8 and len(bodies) == 10
    assert set(face for sex, face in faces) == set(m.FACE_IDS)
    for sex in ('female', 'male'):
        subset = [row for (s, action), row in bodies.items() if s == sex]
        assert len(subset) == 5
        assert any(row['duration_seconds'] < 5 for row in subset)
        assert any(row['duration_seconds'] > 5 for row in subset)


def test_dynamic_composition_keeps_face_continuous_independent_of_body_seam(task, monkeypatch):
    entry = {'asset': '/Game/Accepted/Smile', 'reference_mesh': '/Game/Body', 'selection_entry_id': 'female.smile',
             'evidence': {'composition_report': {'path': 'accepted.json', 'sha256': 'accepted'}}}
    face = {'task': {'allowed_face_curve_names': ['Blink', 'Mouth']}}
    body = {'success': True, 'sources_unchanged': True,
            'task': {'sex': 'female', 'action_id': task['body_action_id']},
            'verification': {'bone_count': 118, 'all_frame_count': 151, 'fps': 30, 'duration_seconds': 5},
            'asset_record': {'asset': '/Game/Window', 'sha256': 'window'},
            'original_body': {'asset': '/Game/Original', 'sha256': 'original'}, 'destination': '/Game/Window'}
    monkeypatch.setattr(m, 'accepted_faces', lambda: {('female', 'smile'): (entry, face)})
    monkeypatch.setattr(m, 'read', lambda _: body)
    monkeypatch.setattr(m, 'file_record', lambda path: {'path': str(path), 'sha256': 'proof'})
    records = {row['asset']: row for row in (body['asset_record'], body['original_body'])}
    monkeypatch.setattr(m, 'composer', lambda: SimpleNamespace(asset_record=lambda path: records[path], run=lambda ct: ct))
    result = m.run(task)
    assert result['body_animation'] == '/Game/Window' and result['face_animation'] == '/Game/Accepted/Smile'
    assert (result['face_start_seconds'], result['face_end_seconds'], result['face_rate'], result['face_playback']) == (0, 5, 1, 'hold')
    assert 'face_envelope' not in result and result['body_mode'] == 'animation'
    body['sources_unchanged'] = False
    with pytest.raises(ValueError, match='verified body'):
        m.run(task)


def test_preparation_is_offline_and_exhaustive_without_rebuilding_statics(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path)
    result = m.prepare()
    assert len(result['body_tasks']) == 10 and len(result['composition_tasks']) == 40 and len(result['entries']) == 48
    static = [row for row in result['entries'] if row['body_action_id'] == 'static']
    assert len(static) == 8 and all(row['task'] is None and row['reuse_accepted_static'] for row in static)
    assert all(row['accepted_selection_entry_id'] == row['sex']+'.'+row['face_id'] for row in result['entries'])
    for row in result['body_tasks'] + result['composition_tasks']:
        m.validate_task(m.read(row['task']))
    assert [row['body']['source_duration_seconds'] > 5 for row in result['representatives']] == [True, False]
    assert m.prepare() == result
