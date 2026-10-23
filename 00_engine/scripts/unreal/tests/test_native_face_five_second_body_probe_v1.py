import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('five_second_body_probe', Path(__file__).parents[1] / 'ue_native_face_five_second_body_probe_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


@pytest.fixture
def task(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path)
    monkeypatch.setattr(m.contract, 'RUN', tmp_path)
    return {'sex': 'female', 'probe_id': 'test_v1', 'face_report': str(tmp_path / 'face.json'),
            'crop_report_path': str(tmp_path / 'crop.json'),
            'composition_report_path': str(tmp_path / 'composition.json'), 'report_path': str(tmp_path / 'probe.json')}


def face_report(task):
    return {'success': True, 'sources_unchanged': True, 'face_bones': list(m.contract.EXPECTED_FACE_BONES),
            'destination': m.contract.ASSET_ROOT + '/female/A_test_face',
            'task': {'sex': 'female', 'composite_id': 'test_face', 'body_animation': '/Game/Test/Body',
                'face_animation': '/Game/Test/Face', 'reference_mesh': '/Game/Test/Mesh',
                'allowed_face_curve_names': ['CTRL_expressions_eyeBlinkL'], 'face_start_seconds': 5.35,
                'face_end_seconds': 10.35, 'face_rate': 1, 'face_playback': 'hold',
                'body_mode': 'static', 'static_use_reference_pose': True, 'report_path': task['face_report']},
            'verification': {'fps': 60, 'all_frame_count': 301, 'duration_seconds': 5}}


@pytest.mark.parametrize('numerator,denominator,duration', [(30, 1, 3.4), (30, 1, 4.53),
    (30000, 1001, 7), (0, 1, 7), (30, 0, 7), (True, 1, 7), (float('nan'), 1, 7)])
def test_short_or_nonrepresentable_body_rejected(numerator, denominator, duration):
    with pytest.raises(ValueError):
        m.frame_grid(numerator, denominator, duration)


def test_native_frame_grid_has_no_time_warp_or_face_restart():
    fps, frames, times = m.frame_grid(30, 1, 7.0666666)
    assert (fps, frames, len(times)) == (30, 150, 151)
    assert times[0] == 0 and times[-1] == 5
    assert all(b - a == pytest.approx(1/30) for a, b in zip(times, times[1:]))


@pytest.mark.parametrize('change', [{'face_rate': .5}, {'face_playback': 'loop'}, {'sex': 'unknown'}, {'probe_id': '../old'}])
def test_entry_rejects_timing_overrides_before_loading_unreal(task, change):
    task.update(change)
    with pytest.raises(ValueError):
        m.run(task)


def test_unique_reports_protect_existing_and_source(task):
    m.validate_task(task)
    Path(task['crop_report_path']).write_text('preserve')
    with pytest.raises(ValueError, match='new'):
        m.validate_task(task)
    assert Path(task['crop_report_path']).read_text() == 'preserve'
    task['crop_report_path'] = task['face_report']
    with pytest.raises(ValueError, match='distinct'):
        m.validate_task(task)


def test_reports_cannot_escape_run(task, tmp_path):
    task['report_path'] = str(tmp_path / '..' / 'old.json')
    with pytest.raises(ValueError, match='inside'):
        m.validate_task(task)


def test_preselected_body_reports_reference_original_long_animations():
    for sex, path in m.BODY_REPORTS.items():
        report = m.read_json(path)
        assert report['success'] is True and report['task']['sex'] == sex
        assert report['task']['body_mode'] == 'animation'
        assert report['verification']['duration_seconds'] >= 5
        assert '/ModularReview/Animations/' in report['task']['body_animation']
        assert any(row['asset'] == report['task']['body_animation'] for row in report['sources'])


def test_composition_uses_already_verified_face_zero_to_five_original_speed(task):
    face = face_report(task)
    prepared = m.compose_task(task, face, '/Game/New/BodyCrop')
    assert prepared['face_animation'] == face['destination']
    assert prepared['body_animation'] == '/Game/New/BodyCrop'
    assert prepared['body_mode'] == 'animation'
    assert (prepared['face_start_seconds'], prepared['face_end_seconds'], prepared['face_rate']) == (0, 5, 1)
    assert prepared['face_playback'] == 'hold' and 'face_envelope' not in prepared


def test_failed_or_wrong_face_report_rejected_before_unreal(task):
    face = face_report(task)
    path = Path(task['face_report'])
    path.write_text(json.dumps(face))
    original, accepted = m.verified_inputs(task)
    assert '/A_CCWH_F06_ELEVATOR_GREETING' in original['asset']
    assert accepted == face
    face['success'] = False
    path.write_text(json.dumps(face))
    with pytest.raises(ValueError, match='successful'):
        m.verified_inputs(task)
    face['success'] = True
    face['verification']['all_frame_count'] = 151
    path.write_text(json.dumps(face))
    with pytest.raises(ValueError, match='frame/ten-bone'):
        m.verified_inputs(task)
    face['verification']['all_frame_count'] = 301
    face['destination'] += '_other'
    path.write_text(json.dumps(face))
    with pytest.raises(ValueError, match='destination'):
        m.verified_inputs(task)


def test_source_preservation_checks_hash_and_unsaved_changes(monkeypatch):
    from types import SimpleNamespace
    record = {'asset': '/Game/Original.Original', 'sha256': 'a'}
    module = SimpleNamespace(asset_record=lambda _: dict(record))
    u = SimpleNamespace(EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_content_packages=lambda: []))
    assert m.ensure_preserved(module, u, [record], set(), ['/Game/New'])['sources_unchanged']
    module.asset_record = lambda _: {**record, 'sha256': 'changed'}
    with pytest.raises(RuntimeError, match='preservation'):
        m.ensure_preserved(module, u, [record], set(), ['/Game/New'])
    module.asset_record = lambda _: dict(record)
    u.EditorLoadingAndSavingUtils.get_dirty_content_packages = lambda: [SimpleNamespace(get_path_name=lambda: '/Game/Original')]
    with pytest.raises(RuntimeError, match='preservation'):
        m.ensure_preserved(module, u, [record], set(), ['/Game/New'])
