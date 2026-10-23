import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('motion_face_pilot_tests', Path(__file__).parents[1] / 'ue_motion_library_face_pilot_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def record(path, content=b'fixture'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {'path': str(path), 'sha256': hashlib.sha256(content).hexdigest()}


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path / 'm3')
    monkeypatch.setattr(m, 'CONTENT', tmp_path / 'content')
    destination = m.ROOT + '/female/new_motion_v1'
    face = sorted(m.load('ue_compose_native_face_body_v1.py').FACE_BONES)
    protected = ['body_' + str(i) for i in range(108)]
    info = {'frame_rate': {'numerator': 60, 'denominator': 1}, 'number_of_frames': 620,
            'duration_seconds': 620/60, 'fps': 60., 'bone_track_names': protected}
    data = {'task': {'sex': 'female', 'name': 'new_motion_v1'}, 'success': True,
        'eligible_for_native_five_seconds': True, 'destination': destination, 'source_files_unchanged': True,
        'changed_source_files': [], 'dirty_protected_assets': [], 'new_dirty_packages_outside_destination': [],
        'retimed': False, 'cropped': False, 'looped_or_padded': False,
        'imported': dict(info, bone_track_names=protected + face), 'body_only': info,
        'removed_face_tracks': face, 'verification': {'all_frame_count': 621, 'source_bone_count': 118,
            'protected_body_bone_count': 108, 'removed_face_track_count': 10, 'face_tracks_absent': True,
            'face_local_pose_is_reference': True, 'preserved_curve_keys_identical': True,
            'max_absolute_errors': {'protected_bones': 0., 'preserved_curves': 0., 'face_reference_bones': 0.}},
        'source_fbx': record(tmp_path/'source.fbx'), 'protected_sources': [record(tmp_path/'skeleton.uasset')]}
    for prefix, suffix, key in [('source', 'Source', 'source_animation'), ('body_only', 'BodyOnly', 'body_only_animation')]:
        asset = destination + '/A_new_motion_v1_' + suffix
        data[key] = asset
        file = m.CONTENT / (asset.removeprefix('/Game/') + '.uasset')
        data[prefix + '_asset_record'] = dict(record(file), asset=asset + '.' + asset.rsplit('/',1)[1], bytes=7)
    path = m.RUN / 'imports/approved.json'
    def save():
        return record(path, json.dumps(data).encode())
    return data, path, save


def test_source_binding_and_old_composer_record_shape(source):
    data, path, save = source
    proof = save()
    _, row = m.import_source(proof, 'female')
    assert row['duration_seconds'] > 5
    assert set(row['original_body']) == {'asset', 'path', 'sha256'}
    Path(data['body_only_asset_record']['path']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        m.import_source(proof)


def test_changed_report_and_wrong_sex_fail(source):
    _, path, save = source
    proof = save()
    with pytest.raises(ValueError, match='sex/name'):
        m.import_source(proof, 'male')
    path.write_text('{}')
    with pytest.raises(ValueError, match='changed'):
        m.import_source(proof)


@pytest.mark.parametrize('eligible', [False, True])
def test_short_source_rejected_even_with_false_eligibility_claim(source, eligible):
    data, _, save = source
    data['eligible_for_native_five_seconds'] = eligible
    for key in ('imported', 'body_only'):
        data[key].update(number_of_frames=256, duration_seconds=256/60)
    data['verification']['all_frame_count'] = 257
    with pytest.raises(ValueError, match='short|Short'):
        m.import_source(save())


def test_escaped_asset_root_and_output_fail_before_write(source):
    data, _, save = source
    data['destination'] = '/Game/Old'
    with pytest.raises(ValueError, match='root'):
        m.import_source(save())
    with pytest.raises(ValueError, match='inside'):
        m.panel().output_path(m.RUN.parent / 'old.json')
    assert not (m.RUN.parent / 'old.json').exists()


def test_no_shared_module_or_old_output_mutation(source):
    data, _, save = source
    proof = save()
    old = m.load('ue_native_face_panel_five_second_v1.py')
    old_run, old_root = old.RUN, old.ASSET_ROOT
    private = m.panel()
    assert private.RUN == m.RUN and private.ASSET_ROOT == m.ROOT
    assert old.RUN == old_run and old.ASSET_ROOT == old_root
    old_report = m.RUN.parent / 'n3_saved_report.json'
    old_report.write_text('unchanged')
    task = {'operation': 'body_window', 'sex': 'female', 'action_id': 'ACT_PILOT',
            'window_id': 'test_v1', 'source_report': proof['path'], 'reference_mesh': '/Game/Reference',
            'report_path': str(old_report)}
    with pytest.raises(ValueError, match='inside'):
        m.validate_task({'schema': m.SCHEMA, 'import_report': proof, 'task': task})
    assert old_report.read_text() == 'unchanged'


def test_task_source_substitution_and_existing_output_fail(source):
    _, _, save = source
    proof = save()
    task = {'operation': 'body_window', 'sex': 'female', 'action_id': 'ACT_PILOT',
            'window_id': 'test_v1', 'source_report': str(m.RUN/'imports/other.json'),
            'reference_mesh': '/Game/Reference', 'report_path': str(m.RUN/'pilot/report.json')}
    value = {'schema': m.SCHEMA, 'import_report': proof, 'task': task}
    with pytest.raises(ValueError, match='differs'):
        m.validate_task(value)
    task['source_report'] = proof['path']
    record(Path(task['report_path']), b'old report')
    with pytest.raises(ValueError, match='existing output'):
        m.validate_task(value)
    assert Path(task['report_path']).read_bytes() == b'old report'
