import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('motion_library_expansion_test', Path(__file__).parents[1] / 'ue_motion_library_expansion_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_shared_reference_omits_mesh_without_changing_body_evaluation(monkeypatch):
    class Options:
        def set_editor_properties(self, values):
            self.values = values
    calls = []
    def evaluate(animation, time, options):
        calls.append((animation, time, options.values))
        return 'shared_pose'
    u = SimpleNamespace(AnimPoseEvaluationOptions=Options,
        AnimDataEvalType=SimpleNamespace(SOURCE='SOURCE'), Name=str,
        AnimPoseSpaces=SimpleNamespace(LOCAL='LOCAL'),
        AnimPoseExtensions=SimpleNamespace(get_anim_pose_at_time=evaluate,
            is_valid=lambda p: True, get_bone_names=lambda p: ['upperjaw'],
            get_ref_bone_pose=lambda p, n, s: (3.386, -5.9066)))
    monkeypatch.setattr(m.CONTRACT, 'transform_values', lambda x: x)
    body = m.source_evaluation_options(u, 'reference_mesh')
    baseline = m.shared_face_reference(u, 'body_only', ['upperjaw'])
    assert body.values['optional_skeletal_mesh'] == 'reference_mesh'
    assert calls[0][2] == dict(body.values, optional_skeletal_mesh=None)
    assert calls[0][:2] == ('body_only', 0.)
    assert baseline == {'upperjaw': (3.386, -5.9066)}
    assert m.TOLERANCE == 1e-4


@pytest.mark.parametrize('missing,nonfinite', [(True, False), (False, True)])
def test_shared_reference_rejects_missing_or_nonfinite_bones(monkeypatch, missing, nonfinite):
    class Options:
        def set_editor_properties(self, values):
            pass
    u = SimpleNamespace(AnimPoseEvaluationOptions=Options,
        AnimDataEvalType=SimpleNamespace(SOURCE='SOURCE'), Name=str,
        AnimPoseSpaces=SimpleNamespace(LOCAL='LOCAL'),
        AnimPoseExtensions=SimpleNamespace(get_anim_pose_at_time=lambda *a: 'pose',
            is_valid=lambda p: True, get_bone_names=lambda p: [] if missing else ['upperjaw'],
            get_ref_bone_pose=lambda *a: (float('nan') if nonfinite else 1.,)))
    monkeypatch.setattr(m.CONTRACT, 'transform_values', lambda x: x)
    with pytest.raises(RuntimeError, match='omitted|Nonfinite'):
        m.shared_face_reference(u, 'body', ['upperjaw'])


@pytest.fixture
def task(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path / 'run')
    monkeypatch.setattr(m, 'WORKSPACE', tmp_path)
    p = tmp_path / 'motion.fbx'
    p.write_bytes(b'isolated motion fixture')
    return {'sex': 'female', 'name': 'candidate_004_v1', 'source_fbx': m.file_record(p),
            'report_path': str(tmp_path / 'run' / 'reports' / 'candidate.json')}


def test_exact_source_and_new_root(task):
    path, output, destination = m.validate_task(task)
    assert path.name == 'motion.fbx'
    assert destination == m.ROOT + '/female/candidate_004_v1'
    assert not output.exists()


@pytest.mark.parametrize('change', [{'sex': 'unknown'}, {'name': '../escape'}, {'name': 'bad-name'},
    {'asset_root': m.ROOT + 'Suffix'}, {'asset_root': m.ROOT + '/../old'}, {'asset_root': '/Game/Old'},
    {'face_rate': 1}, {'duration_seconds': 5}, {'replace_existing': True}])
def test_task_rejects_scope_and_timing_overrides(task, change):
    task.update(change)
    with pytest.raises(ValueError):
        m.validate_task(task)


def test_changed_fbx_rejected(task):
    Path(task['source_fbx']['path']).write_bytes(b'changed motion')
    with pytest.raises(ValueError, match='changed'):
        m.validate_task(task)


def test_existing_or_escaped_report_rejected(task, tmp_path):
    task['report_path'] = str(tmp_path / 'old.json')
    with pytest.raises(ValueError, match='new JSON'):
        m.validate_task(task)
    p = tmp_path / 'run' / 'saved.json'
    p.parent.mkdir()
    p.write_text('old evidence')
    task['report_path'] = str(p)
    with pytest.raises(ValueError, match='new JSON'):
        m.validate_task(task)
    assert p.read_text() == 'old evidence'


@pytest.mark.parametrize('rate,denominator,frames', [(60, 1, 255), (30, 1, 300), (30000, 1001, 1800)])
def test_complete_original_grid_not_cropped_or_rescaled(rate, denominator, frames):
    duration = frames * denominator / rate
    fps, times = m.frame_grid(rate, denominator, frames, duration)
    assert len(times) == frames + 1
    assert times[0] == 0
    assert times[-1] == pytest.approx(duration)
    assert times[1] == 1 / fps


@pytest.mark.parametrize('args', [(30, 0, 150, 5), (30, 1, 0, 0), (30, 1, 120, 5),
    (True, 1, 150, 150), (30, 1, 150.5, 5), (30, 1, 150, float('nan'))])
def test_invalid_or_falsely_extended_duration_rejected(args):
    with pytest.raises(ValueError):
        m.frame_grid(*args)


def test_remove_face_preserves_actual_head_neck_names_case_insensitively():
    removed, kept = m.classify_body_curves(
        ['ctrl_expressions_mouthcornerpulll', 'HEAD_TURN_UP', 'ctrl_expressions_NECKThroatUp'],
        ['CTRL_expressions_mouthCornerPullL', 'Head_Turn_Up', 'CTRL_expressions_neckThroatUp'])
    assert removed == ['ctrl_expressions_mouthcornerpulll']
    assert kept == ['HEAD_TURN_UP', 'ctrl_expressions_NECKThroatUp']


def test_zero_curves_body_motion_is_allowed():
    assert m.classify_body_curves([], ['CTRL_expressions_eyeBlinkL']) == ([], [])


def test_unknown_curve_and_case_collision_fail_closed():
    with pytest.raises(ValueError, match='Unclassified'):
        m.classify_body_curves(['NewFaceCurve'], ['CTRL_expressions_eyeBlinkL'])
    with pytest.raises(ValueError, match='collision'):
        m.classify_body_curves(['EyeBlink', 'eyeblink'], ['EyeBlink'])


def hierarchy():
    result = {'root': 'None', 'pelvis': 'root', 'head': 'neck_02', 'neck_01': 'pelvis', 'neck_02': 'neck_01'}
    result.update({f'body_{i}': 'root' for i in range(103)})
    result.update({b: 'head' if b == 'facialbone' else 'facialbone' for b in m.CONTRACT.FACE_BONES})
    return result


def test_partition_exactly_108_body_bones_including_head_neck():
    parents = hierarchy()
    face, body, actual = m.body_partition(parents, list(parents))
    assert len(face) == 10 and len(body) == 108 and len(actual) == 118
    assert {'head', 'neck_01', 'neck_02', 'root', 'pelvis'} <= set(body)


def test_partition_does_not_silently_accept_missing_track_or_new_face_child():
    parents = hierarchy()
    with pytest.raises(ValueError, match='118 bone tracks'):
        m.body_partition(parents, [n for n in parents if n != 'head'])
    parents['body_0'] = 'facialbone'
    with pytest.raises(ValueError, match='hierarchy'):
        m.body_partition(parents, list(parents))


@pytest.mark.parametrize('state', [
    {'source_files_unchanged': False, 'dirty_protected_assets': [], 'new_dirty_packages_outside_destination': []},
    {'source_files_unchanged': True, 'dirty_protected_assets': ['/Game/Shared'], 'new_dirty_packages_outside_destination': []},
    {'source_files_unchanged': True, 'dirty_protected_assets': [], 'new_dirty_packages_outside_destination': ['/Game/Other']},
])
def test_protected_state_never_accepts_changed_or_dirty_shared_sources(state):
    with pytest.raises(RuntimeError):
        m.require_protected(state)


def test_protected_state_allows_preexisting_unrelated_dirty_package_only(tmp_path):
    p = tmp_path / 'skeleton.uasset'
    p.write_bytes(b'unchanged')
    records = [{'asset': '/Game/Shared.Shared', **m.file_record(p)}]
    package = SimpleNamespace(get_path_name=lambda: '/Game/Unrelated')
    u = SimpleNamespace(EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_content_packages=lambda: [package]))
    state = m.protected_state(u, records, {'/Game/Unrelated'}, m.ROOT + '/female/test')
    m.require_protected(state)
    p.write_bytes(b'changed')
    with pytest.raises(RuntimeError):
        m.require_protected(m.protected_state(u, records, {'/Game/Unrelated'}, m.ROOT + '/female/test'))


def test_true_missing_evaluator_curve_is_never_zero_fallback():
    assert m.CONTRACT.curve_names_present(['Head_Turn_Up'], ['head_turn_up'])
    assert not m.CONTRACT.curve_names_present(['Head_Turn_Up'], [])


@pytest.mark.parametrize('transform_curves', [[], ['head_transform']])
def test_inspect_uses_only_ue58_public_curve_types(transform_curves):
    # Match UE5.8's Python enum: RCT_Vector is Hidden and not an attribute.
    types = SimpleNamespace(RCT_FLOAT=0, RCT_TRANSFORM=2)
    queried = []
    def curve_names(asset, kind):
        queried.append(kind)
        return transform_curves if kind == 2 else []
    u = SimpleNamespace(RawCurveTrackTypes=types,
        AnimationLibrary=SimpleNamespace(get_animation_curve_names=curve_names))
    model = SimpleNamespace(get_frame_rate=lambda: SimpleNamespace(numerator=60, denominator=1),
        get_number_of_frames=lambda: 255, get_bone_track_names=lambda: ['head'])
    animation = SimpleNamespace(data_model_interface=model, get_play_length=lambda: 4.25,
        get_path_name=lambda: '/Game/Test.Test')
    if transform_curves:
        with pytest.raises(ValueError, match='Unexpected transform'):
            m.inspect(u, animation)
    else:
        info, times = m.inspect(u, animation)
        assert info['other_curve_types'] == {'transform': []}
        assert info['duration_seconds'] == times[-1] == 4.25
    assert queried == [0, 2]
