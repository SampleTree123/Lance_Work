"""No engine imports: reject candidates, changed evidence and unsafe looping."""
import copy
import json
import os
from collections import OrderedDict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_face_library_contract_v1 as contract


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return contract.source(path)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    content = tmp_path / 'Content'
    monkeypatch.setattr(contract, 'PROJECT_CONTENT', content)
    native = contract.ASSET_ROOT + '/female/gentle/A_Native.A_Native'
    animation = contract.ASSET_ROOT + '/Composed/Female/A_Gentle_Walk.A_Gentle_Walk'
    package_file = content / (animation.split('.', 1)[0].removeprefix('/Game/') + '.uasset')
    package_file.parent.mkdir(parents=True, exist_ok=True)
    package_file.write_bytes(b'new derived animation')
    source_file = tmp_path / 'source.fbx'; source_file.write_bytes(b'performance')
    skeleton_file = tmp_path / 'shared_skeleton.uasset'; skeleton_file.write_bytes(b'unchanged skeleton')
    imported = {'success': True, 'task': {'sex': 'female'}, 'source_unchanged': True,
        'skeleton_file_unchanged': True, 'new_dirty_packages_outside_destination': [],
        'source': contract.source(source_file), 'skeleton_after': contract.source(skeleton_file),
        'animations': [{'path': native, 'skeleton': contract.SKELETONS['female'], 'active_curve_names': ['jawOpen', 'blinkL']}]}
    composed = {'success': True, 'sex': 'female', 'body_action_id': 'ACT_F03_AUDIENCE_01',
        'animation_path': animation, 'native_animation_path': native,
        'skeleton_path': contract.SKELETONS['female'], 'package': contract.source(package_file),
        'checks': {name: True for name in contract.CHECKS},
        'non_face_validation': {'coverage': 'all_frames', 'checked_frame_count': 137, 'frame_count': 137}}
    visual = {'reviewer': 'root_agent', 'status': 'reviewed_for_panel', 'animation_paths': [animation],
              'observations': 'Test fixture representing a separately observed reference performance.', 'user_acceptance': 'pending'}
    paths = {key: tmp_path / (key + '.json') for key in ('imported', 'composed', 'visual')}
    entry = {'sex': 'female', 'face_id': 'gentle', 'label': 'Gentle', 'body_action_id': 'ACT_F03_AUDIENCE_01',
             'animation_path': animation, 'native_animation_path': native, 'skeleton_path': contract.SKELETONS['female'],
             'package': contract.source(package_file), 'playback': {'mode': 'oneshot', 'end_behavior': 'return_body'},
             'evidence': {'native_import': write(paths['imported'], imported),
                          'composition': write(paths['composed'], composed), 'root_visual': write(paths['visual'], visual)}}
    document = {'schema': contract.SCHEMA, 'status': 'validated_review',
                'sources': {'native_fbx': contract.source(source_file)}, 'entries': [entry]}
    return {'document': document, 'paths': paths, 'imported': imported, 'composed': composed,
            'visual': visual, 'package_file': package_file, 'source_file': source_file}


def test_review_catalog_does_not_claim_user_acceptance_and_resolves_exact_key(fixture, tmp_path):
    path = tmp_path / 'registry.json'; write(path, fixture['document'])
    library = contract.catalog(path)
    assert library['status'] == 'validated_review'
    choices = contract.available_faces(library, 'female', 'ACT_F03_AUDIENCE_01')
    assert [row['face_id'] for row in choices] == ['none', 'gentle']
    assert choices[1]['user_acceptance'] == 'pending'
    assert contract.resolve(library, 'female', 'gentle', 'ACT_F03_AUDIENCE_01')['animation_path'] == fixture['document']['entries'][0]['animation_path']
    with pytest.raises(ValueError, match='No verified'):
        contract.resolve(library, 'male', 'gentle', 'ACT_F03_AUDIENCE_01')
    with pytest.raises(ValueError, match='not a published'):
        contract.catalog(path, published_only=True)


def test_none_restores_caller_body_without_requiring_face_registry():
    assert contract.resolve(None, 'female', 'none', 'static')['animation_path'] is None
    body = '/Game/Body/A_Walk.A_Walk'
    result = contract.resolve(None, 'male', 'none', 'ACT_M03_WALK', body_animation_path=body)
    assert result['restore_body_only'] and result['clear_face_curves'] and result['animation_path'] == body
    with pytest.raises(ValueError):
        contract.resolve(None, 'female', 'none', 'static', body_animation_path=body)


@pytest.mark.parametrize('mutation', ['candidate', 'duplicate', 'wrong_skeleton', 'import_as_derived', 'missing_visual'])
def test_unverified_or_ambiguous_entries_rejected(fixture, mutation):
    value = fixture['document']; row = value['entries'][0]
    if mutation == 'candidate':
        value['status'] = 'candidate'
    elif mutation == 'duplicate':
        value['entries'].append(copy.deepcopy(row))
    elif mutation == 'wrong_skeleton':
        row['skeleton_path'] = contract.SKELETONS['male']
    elif mutation == 'import_as_derived':
        row['animation_path'] = row['native_animation_path']
    else:
        del row['evidence']['root_visual']
    with pytest.raises(ValueError):
        contract.validate_registry(value)


@pytest.mark.parametrize('target', ['package_file', 'source_file'])
def test_modified_saved_asset_or_source_rejected(fixture, target):
    fixture[target].write_bytes(b'changed after validation')
    with pytest.raises(ValueError, match='SHA changed'):
        contract.validate_registry(fixture['document'])


def test_import_success_alone_cannot_replace_composition_checks(fixture):
    fixture['composed']['checks']['component_curve_sync_verified'] = False
    fixture['document']['entries'][0]['evidence']['composition'] = write(fixture['paths']['composed'], fixture['composed'])
    with pytest.raises(ValueError, match='required bounded checks'):
        contract.validate_registry(fixture['document'])


def test_sampled_proof_is_usable_but_never_relabelled_all_frames(fixture):
    composed = fixture['composed']
    composed['non_face_validation'] = {'coverage': 'sampled_frames', 'checked_frame_count': 13, 'frame_count': 137}
    row = fixture['document']['entries'][0]
    row['evidence']['composition'] = write(fixture['paths']['composed'], composed)
    library = contract.validate_registry(fixture['document'])
    assert contract.available_faces(library, 'female', row['body_action_id'])[1]['validation_scope']['coverage'] == 'sampled_frames'
    composed['non_face_validation']['coverage'] = 'all_frames'
    row['evidence']['composition'] = write(fixture['paths']['composed'], composed)
    with pytest.raises(ValueError, match='all-frame'):
        contract.validate_registry(fixture['document'])


def test_loop_requires_extra_evidence_oneshot_end_policy_is_explicit(fixture):
    row = fixture['document']['entries'][0]
    row['playback'] = {'mode': 'loop', 'end_behavior': 'repeat'}
    with pytest.raises(ValueError, match='Loop playback'):
        contract.validate_registry(fixture['document'])
    fixture['composed']['loop_boundary_verified'] = True
    row['evidence']['composition'] = write(fixture['paths']['composed'], fixture['composed'])
    assert contract.validate_registry(fixture['document'])['entries'][0]['playback']['mode'] == 'loop'
    row['playback'] = {'mode': 'oneshot', 'end_behavior': 'automatic_guess'}
    with pytest.raises(ValueError, match='One-shot'):
        contract.validate_registry(fixture['document'])


def test_native_import_cache_still_reads_all_bytes_but_parses_once(fixture, monkeypatch):
    monkeypatch.setattr(contract, '_NATIVE_IMPORT_CACHE', OrderedDict())
    record = fixture['document']['entries'][0]['evidence']['native_import']
    original_read, original_parse = Path.read_bytes, json.loads
    reads, parses = [], []
    def counted_read(path):
        reads.append(str(path))
        return original_read(path)
    def counted_parse(raw):
        parses.append(len(raw))
        return original_parse(raw)
    monkeypatch.setattr(Path, 'read_bytes', counted_read)
    monkeypatch.setattr(json, 'loads', counted_parse)
    first = contract._evidence(record, {}, json_file=True, native_import=True)
    first['animations'][0]['active_curve_names'].clear()
    second = contract._evidence(record, {}, json_file=True, native_import=True)
    assert reads == [record['path'], record['path']]
    assert len(parses) == 1
    assert second['animations'][0]['active_curve_names'] == ['jawOpen', 'blinkL']


def test_warm_cache_rejects_changed_bytes_with_same_size_and_timestamp(fixture, monkeypatch):
    monkeypatch.setattr(contract, '_NATIVE_IMPORT_CACHE', OrderedDict())
    record = fixture['document']['entries'][0]['evidence']['native_import']
    contract.validate_registry(fixture['document'])
    path = fixture['paths']['imported']
    stat = path.stat()
    old = path.read_bytes()
    altered = old.replace(b'"success": true', b'"success": null', 1)
    assert len(altered) == len(old) and altered != old
    path.write_bytes(altered)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert path.stat().st_size == stat.st_size and path.stat().st_mtime_ns == stat.st_mtime_ns
    with pytest.raises(ValueError, match='SHA changed'):
        contract.validate_registry(fixture['document'])
    # Supplying the new correct hash must parse the new invalid result, not
    # reuse the formerly successful report held for that same path.
    fixture['document']['entries'][0]['evidence']['native_import'] = contract.source(path)
    with pytest.raises(ValueError, match='Native import'):
        contract.validate_registry(fixture['document'])


def test_native_summary_preserves_required_fields_and_cache_is_bounded(fixture, tmp_path, monkeypatch):
    monkeypatch.setattr(contract, '_NATIVE_IMPORT_CACHE', OrderedDict())
    monkeypatch.setattr(contract, 'NATIVE_IMPORT_CACHE_LIMIT', 2)
    document = copy.deepcopy(fixture['imported'])
    document['unused_large_report'] = list(range(10000))
    document['task']['unused_settings'] = 'x' * 10000
    document['animations'][0]['all_curve_samples'] = list(range(10000))
    expected = copy.deepcopy(fixture['imported'])
    records = [write(tmp_path / ('large_' + str(i) + '.json'), document) for i in range(3)]
    for record in records:
        result = contract._evidence(record, {}, json_file=True, native_import=True)
        assert result == expected
        assert len(json.dumps(result)) < len(json.dumps(document)) / 10
    assert len(contract._NATIVE_IMPORT_CACHE) == 2
    assert (str(Path(records[0]['path']).resolve()), records[0]['sha256']) not in contract._NATIVE_IMPORT_CACHE
    assert all(set(row['animations'][0]) == {'path', 'skeleton', 'active_curve_names'}
               for row in contract._NATIVE_IMPORT_CACHE.values())


def test_warm_import_cache_does_not_skip_other_source_hashes(fixture, monkeypatch):
    monkeypatch.setattr(contract, '_NATIVE_IMPORT_CACHE', OrderedDict())
    contract.validate_registry(fixture['document'])
    fixture['package_file'].write_bytes(b'changed derived package')
    with pytest.raises(ValueError, match='SHA changed'):
        contract.validate_registry(fixture['document'])
