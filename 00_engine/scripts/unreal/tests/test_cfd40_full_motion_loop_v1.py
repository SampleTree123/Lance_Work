"""Loop review preserves full duration and rejects stale/composition evidence."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('full_motion_loop_test', Path(__file__).parents[1] / 'ue_cfd40_full_motion_loop_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def proof(task):
    return {'success': True, 'task': task, 'sources_unchanged': True,
            'new_dirty_packages_outside_target': [], 'face_bones': list(range(10)),
            'verification': {'duration_seconds': 12., 'all_frame_count': 361,
                             'unrelated_curve_keys_identical': True,
                             'max_absolute_errors': {'protected_bones': 0., 'face_curves': 0.},
                             'face_bone_metric_maxima': {'translation_cm': 0., 'rotation_degrees': .1, 'scale_abs': 0.},
                             'face_bone_metric_tolerances': {'translation_cm': .001, 'rotation_degrees': .2, 'scale_abs': 1e-4}}}


def test_complete_full_duration_proof():
    task = {'face_playback': 'loop'}
    m.validate_composition(proof(task), task, 12., 360)


@pytest.mark.parametrize('change', ['duration', 'frames', 'sources', 'task', 'nan', 'threshold', 'dirty'])
def test_rejects_incomplete_or_loosened_proof(change):
    report = proof({})
    if change == 'duration': report['verification']['duration_seconds'] = 5.
    if change == 'frames': report['verification']['all_frame_count'] = 151
    if change == 'sources': report['sources_unchanged'] = False
    if change == 'task': report['task'] = {'face_rate': .5}
    if change == 'nan': report['verification']['max_absolute_errors']['protected_bones'] = float('nan')
    if change == 'threshold': report['verification']['face_bone_metric_tolerances']['rotation_degrees'] = 1.
    if change == 'dirty': report['new_dirty_packages_outside_target'] = ['/Game/SharedSkeleton']
    with pytest.raises(ValueError): m.validate_composition(report, {}, 12., 360)


def test_cache_rechecks_report_sources_and_target(tmp_path):
    def saved(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return m.record(path)
    task, spec = {}, {'sources': 'stable'}
    asset = saved('asset.bin', 'asset') | {'asset': '/Game/New/A.A'}
    source = saved('source.bin', 'source')
    report = proof(task) | {'destination': '/Game/New/A', 'sources': [source]}
    receipt = {'schema': 'full_motion_loop_cache_v1', 'success': True, 'key': m.digest(spec),
               'spec': spec, 'runtime_policy': m.runtime_policy(), 'asset': asset,
               'animation_path': asset['asset'], 'composition_report': saved('report.json', report)}
    assert m.validate_cache(receipt, spec, task, 12., 360) == receipt
    Path(source['path']).write_text('changed')
    with pytest.raises(ValueError, match='dependency changed'):
        m.validate_cache(receipt, spec, task, 12., 360)


class Motion:
    def __init__(self, path, duration): self.path, self.duration = path, duration
    def get_play_length(self): return self.duration


def fake_app(index, face_id):
    full, native5 = Motion('/Game/Full.Full', 12.), Motion('/Game/Face.Face', 5.)
    chosen = native5 if face_id != 'none' else full if index else None
    selection = {'animation_path': chosen.path if chosen else None, 'face_id': face_id,
                 'playback': {'mode': 'oneshot'}, 'evidence': {'old_5s': True},
                 'package': {'old': True}, 'user_acceptance': 'old', 'non_face_validation': {'frames': 151}}
    entry = {'review_motion': chosen, 'face_selection': selection}
    request = {'action_index': index, 'appearance': {'female': {'face_id': face_id}}}
    data = {'actions_by_sex': {'female': [{'index': 1, 'action_id': 'ACT_F', 'path': full.path}]}}
    def old_plan(*_): return {'faces': {'female': copy.deepcopy(selection)}, 'sources': {}}, {'female': dict(entry)}
    def old_state(request, data, plan, prepared):
        motion = prepared['female'].get('review_motion')
        return {'success': True, 'animation': {'female': {'animation': motion.path if motion else None}}}
    app = SimpleNamespace(load_plan=old_plan, state=old_state, review=SimpleNamespace(), unreal=None,
                          fixed=SimpleNamespace(object_path=lambda a: a.path if a else None, digest=m.digest))
    return app, request, data


@pytest.mark.parametrize('index,face_id,kind,duration', [
    (1, 'smile', 'full_body_repeated_face', 12.),
    (1, 'none', 'full_body_without_face', 12.),
    (0, 'smile', 'static_body_face_repeat', 5.),
    (0, 'none', 'static_without_animation', 0.)])
def test_all_loop_modes_use_correct_sources(monkeypatch, index, face_id, kind, duration):
    app, request, data = fake_app(index, face_id)
    choice = {'asset': '/Game/Face.Face', 'face_id': 'smile'}
    monkeypatch.setattr(m, 'accepted_faces', lambda: ({('female', 'smile'): (choice, {})}, {'sha256': 'accepted'}))
    monkeypatch.setattr(m, 'composer', lambda: SimpleNamespace(asset_record=lambda p: {'asset': p}))
    def ensure(*args):
        assert args[2]['path'] == '/Game/Full.Full'
        return Motion('/Game/Derived.Derived', 12.), {'kind': 'full_body_repeated_face', 'duration_seconds': 12., 'animation_path': '/Game/Derived.Derived'}
    monkeypatch.setattr(m, 'ensure_composite', ensure)
    m.install_worker(app)
    plan, prepared = app.load_plan(request, data)
    assert plan['full_motion_loop']['characters']['female']['kind'] == kind
    assert plan['full_motion_loop']['characters']['female']['duration_seconds'] == duration
    assert app.review.load_plan is app.load_plan
    selection = prepared['female']['face_selection']
    if duration:
        assert selection['playback']['mode'] == 'loop'
    if index and face_id != 'none':
        assert 'evidence' not in selection and 'package' not in selection
        assert selection['user_acceptance'] == 'pending_full_motion_loop_review'
    saved = SimpleNamespace(get_editor_property=lambda key: bool(duration) if key == 'saved_looping' else 1.)
    app.fixed.body_for = lambda _: SimpleNamespace(get_editor_property=lambda _: saved)
    result = app.state(request, data, plan, prepared)
    assert result['success'] is True
    assert result['full_motion_loop_readback']['success'] is True
    saved.get_editor_property = lambda key: False if key == 'saved_looping' else .5
    assert app.state(request, data, plan, prepared)['success'] is False


def test_install_does_not_allow_duplicate_hook():
    app, _, _ = fake_app(0, 'none')
    m.install_worker(app)
    with pytest.raises(ValueError, match='already installed'): m.install_worker(app)


def test_composer_mapping_repeats_face_without_stretching_body():
    composer = m.composer()
    assert composer.face_time(6.5, 0, 5, 1, 'loop') == 1.5
    assert composer.face_time(12., 0, 5, 1, 'loop') == 2.
    assert composer.RUN == m.RUN
    assert composer.ASSET_ROOT == m.ASSET_ROOT + '/Composites'
