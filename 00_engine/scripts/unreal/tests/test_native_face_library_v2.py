"""Five-second evidence boundaries and native single-node playback, without UE."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_face_library_contract_v1 as c
from test_cfd_native_batch40_modular_worker_v1 import functions


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(c, 'PROJECT_CONTENT', tmp_path / 'Content')
    monkeypatch.setattr(c, 'ACCEPTED_SELECTION', tmp_path / 'accepted.json')
    def save(name, data):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding='utf8')
        return c.source(p)
    def asset(path):
        p = c.PROJECT_CONTENT / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(path.encode())
        return {'asset': path, **c.source(p)}
    def composed(sex, path, native, start, end):
        return {'success': True, 'sources_unchanged': True, 'new_dirty_packages_outside_target': [],
            'destination': path.split('.')[0], 'sources': [asset(native)], 'face_bones': list(range(10)),
            'task': {'sex': sex, 'face_animation': native, 'face_start_seconds': start, 'face_end_seconds': end,
                'face_rate': 1, 'face_playback': 'hold', 'allowed_face_curve_names': ['blink'],
                'body_mode': 'static', 'static_use_reference_pose': True},
            'verification': {'duration_seconds': 5, 'fps': 30, 'all_frame_count': 151,
                'unrelated_curve_keys_identical': True, 'max_absolute_errors': {'protected_bones': 0, 'face_curves': 0},
                'face_bone_metric_maxima': {'translation_cm': 0, 'rotation_degrees': 0, 'scale_abs': 0}}}
    legacy = save('old.json', {'historical': True})
    selection = {'selection_accepted': True, 'runtime_registry_unchanged': legacy, 'entries': []}
    choices = {}
    for sex in c.SKELETONS:
        for face in c.FACE_IDS:
            path = '/Game/Accepted/' + sex + '_' + face
            path += '.' + path.rsplit('/', 1)[-1]
            native = path.replace('/Accepted/', '/Native/')
            report = composed(sex, path, native, 10, 15)
            imported = {'success': True, 'task': {'sex': sex}, 'source_unchanged': True, 'skeleton_file_unchanged': True,
                'new_dirty_packages_outside_destination': [], 'source': asset(native), 'skeleton_after': asset(c.SKELETONS[sex]),
                'animations': [{'path': native, 'skeleton': c.SKELETONS[sex], 'active_curve_names': ['blink']}]}
            choice = {'sex': sex, 'face_id': face, 'label_zh': face, 'selection_accepted': True, 'asset': path,
                'source_animation': native, 'source_asset': asset(native), 'asset_file_at_selection': asset(path),
                'source_window': {'start_seconds': 10, 'end_seconds': 15},
                'evidence': {'composition_report': save(sex+face+'static.json', report), 'source_report': save(sex+face+'import.json', imported)}}
            choices[(sex, face)] = choice
            selection['entries'].append(choice)
    accepted = save('accepted.json', selection)
    rows, planned = [], []
    for (sex, face), choice in choices.items():
        for body in ['static'] + ['ACT_' + str(i) for i in range(5)]:
            path = choice['asset']
            report = choice['evidence']['composition_report']
            original = None
            if body != 'static':
                path = c.PANEL_ASSET_ROOT + '/Composites/' + sex + '/A_' + face + '_' + body
                path += '.' + path.rsplit('/', 1)[-1]
                original = '/Game/Body/' + sex + body
                original += '.' + original.rsplit('/', 1)[-1]
                window = c.PANEL_ASSET_ROOT + '/BodyWindows/' + sex + '/A_' + body
                window += '.' + window.rsplit('/', 1)[-1]
                br = {'success': True, 'sources_unchanged': True, 'new_dirty_packages_outside_target': [], 'dirty_sources': [],
                    'mapping': {'mode': 'repeat_body_original_speed', 'face_clock_wraps': False, 'body_retimed': False, 'seams_blended': False, 'fps': 30},
                    'task': {'sex': sex, 'action_id': body}, 'destination': window.split('.')[0], 'original_body': asset(original),
                    'asset_record': asset(window), 'sources': [asset(original)],
                    'verification': {'bone_count': 118, 'duration_seconds': 5, 'fps': 30, 'all_frame_count': 151,
                        'max_absolute_errors': {'bones': 0, 'curves': 0}}}
                comp = composed(sex, path, choice['asset'], 0, 5)
                comp['task'].update(body_mode='animation', body_animation=window.split('.')[0], original_body=br['original_body'],
                    accepted_face_selection=accepted, accepted_static_report=choice['evidence']['composition_report'],
                    panel_integration_task={'body_action_id': body, 'face_id': face},
                    body_window_report=save(sex+face+body+'body.json', br))
                report = save(sex+face+body+'comp.json', comp)
            planned.append({'sex': sex, 'face_id': face, 'body_action_id': body, 'asset': path,
                'report': report['path'], 'original_body_animation': original})
            rows.append({'sex': sex, 'face_id': face, 'label': face, 'body_action_id': body,
                'animation_path': path, 'native_animation_path': choice['source_animation'], 'skeleton_path': c.SKELETONS[sex],
                'package': asset(path), 'playback': {'mode': 'oneshot', 'end_behavior': 'hold_last', 'rate': 1, 'duration_seconds': 5},
                'evidence': {'composition': report, 'native_import': choice['evidence']['source_report']}})
    visual = save('visual.json', {'reviewer': 'root_agent', 'status': 'reviewed_for_panel',
        'scope': 'representative_combinations_only', 'observations': 'Synthetic test fixture, not actual visual acceptance.',
        'animation_paths': [rows[1]['animation_path']], 'evidence': [legacy]})
    return {'schema': c.SCHEMA_V2, 'status': 'validated_review', 'sources': {'contract': c.source(c.__file__),
        'accepted_selection': accepted, 'legacy_registry': legacy, 'root_visual': visual,
        'preparation_manifest': save('manifest.json', {'selection': accepted, 'entries': planned})}, 'entries': rows}


def test_valid_complete_registry_and_static_allowlist(registry):
    value = c.validate_registry(registry)
    assert len(value['entries']) == 48
    assert all(r['playback']['mode'] == 'oneshot' for r in value['entries'])


@pytest.mark.parametrize('change', ['loop', 'rate', 'missing', 'duplicate', 'foreign_static', 'foreign_dynamic', 'wrong_import'])
def test_v2_rejects_timing_inventory_and_source_substitution(registry, change):
    row = registry['entries'][0]
    if change == 'loop': row['playback']['mode'] = 'loop'
    elif change == 'rate': row['playback']['rate'] = .5
    elif change == 'missing': registry['entries'].pop()
    elif change == 'duplicate': registry['entries'][1] = copy.deepcopy(row)
    elif change == 'foreign_static': row['animation_path'] = registry['entries'][6]['animation_path']
    elif change == 'foreign_dynamic': registry['entries'][1]['animation_path'] = '/Game/Foreign/A.A'
    else: row['evidence']['native_import'] = registry['entries'][6]['evidence']['native_import']
    with pytest.raises(ValueError): c.validate_registry(registry)


@pytest.mark.parametrize('change', ['retime', 'envelope', 'partial_frames', 'body_error', 'face_error', 'visual_unreviewed', 'mutated_asset'])
def test_v2_rejects_incomplete_actual_evidence_even_with_refreshed_report_hash(registry, change):
    row = registry['entries'][1]
    if change == 'mutated_asset':
        Path(row['package']['path']).write_bytes(b'changed')
    else:
        record = registry['sources']['root_visual'] if change == 'visual_unreviewed' else row['evidence']['composition']
        p = Path(record['path']); data = c.read(p)
        if change == 'retime': data['task']['face_rate'] = .5
        elif change == 'envelope': data['task']['face_envelope'] = {}
        elif change == 'partial_frames': data['verification']['all_frame_count'] = 13
        elif change == 'body_error': data['verification']['max_absolute_errors']['protected_bones'] = .01
        elif change == 'face_error': data['verification']['face_bone_metric_maxima']['rotation_degrees'] = .21
        else: data['status'] = 'pending'
        p.write_text(json.dumps(data), encoding='utf8'); record.update(c.source(p))
    with pytest.raises(ValueError): c.validate_registry(registry)


def test_explicit_old_mapping_rejects_unsupported_and_unknown_source(registry):
    registry['registry_source'] = {'sha256': 'new'}
    appearance = {'female': {'face_id': 'gentle_smile'}, 'male': {'face_id': 'dramatic_sad'}}
    result, changes = c.migrate_legacy_appearance(appearance, registry['sources']['legacy_registry']['sha256'], registry)
    assert result['female']['face_id'] == 'smile' and result['male']['face_id'] == 'sad' and len(changes) == 2
    assert appearance['female']['face_id'] == 'gentle_smile'
    with pytest.raises(ValueError): c.migrate_legacy_appearance(appearance, 'wrong', registry)
    appearance['female']['face_id'] = 'gentle_surprise'
    with pytest.raises(ValueError, match='重新选择'): c.migrate_legacy_appearance(appearance, registry['sources']['legacy_registry']['sha256'], registry)


@pytest.mark.parametrize('action,playing,position,expected_position,expected_playing', [
    ('playback', False, 2.5, 2.5, False), ('playback', True, 2.5, 2.5, True),
    ('playback', True, 5., 0., True), ('view', True, 5., 5., False)])
def test_oneshot_pause_resume_replay_and_hold(action, playing, position, expected_position, expected_playing):
    values = {}
    motion = SimpleNamespace(get_play_length=lambda: 5.)
    instance = SimpleNamespace(set_animation_asset=lambda *a: values.update(instance=a), set_playing=lambda p: values.update(playing=p))
    body = SimpleNamespace(override_animation_data=lambda *a: values.update(override=a), get_anim_instance=lambda: instance,
        set_position=lambda p, _: values.update(position=p))
    ns = functions('set_animation', _animation=lambda *a: None, fixed=SimpleNamespace(body_for=lambda s: body, object_path=lambda m: 'clip'))
    ns['set_animation']({'action': action, 'action_index': 0, 'playing': playing}, {'female': {
        'review_motion': motion, '_previous_motion': 'clip', '_previous_position': position,
        'face_selection': {'playback': {'mode': 'oneshot', 'end_behavior': 'hold_last'}}}})
    assert values['position'] == expected_position and values['playing'] is expected_playing
    assert values['override'][1] is False and values['override'][4] == 1.


def test_configuration_migrates_only_face_source_lock(registry, tmp_path):
    import cfd_native_batch40_configuration_v1 as config
    registry['registry_source'] = {'path': str(tmp_path / 'new.json'), 'sha256': 'new'}
    old = registry['sources']['legacy_registry']
    request = {'appearance': {'female': {'face_id': 'gentle_smile'}, 'male': {'face_id': 'dramatic_sad'}},
        'face_registry_sha256': old['sha256'], 'action': 'show', 'save': False, 'playing': True}
    data = {'sources': {'native_face_library': registry['registry_source'], 'wardrobe': {'sha256': 'unchanged'}},
        'appearance': {'palette': 'unchanged'}, 'face_library': registry}
    content = {'request': request, 'level': config.identity.LEVEL, 'palette': data['appearance'],
        'sources': {**data['sources'], 'native_face_library': old}}
    path = tmp_path / 'config.json'
    path.write_text(json.dumps({'schema': config.SCHEMA, 'content': content, 'content_sha256': config.digest(content)}), encoding='utf8')
    result = config.load_configuration(path, data, lambda request, data: request)
    assert result['appearance']['female']['face_id'] == 'smile' and result['playing']
    assert result['face_registry_sha256'] == 'new'
    data['sources']['wardrobe']['sha256'] = 'changed'
    with pytest.raises(ValueError, match='版本'): config.load_configuration(path, data, lambda request, data: request)


def test_invalid_activation_never_falls_back(tmp_path, monkeypatch):
    pointer = tmp_path / 'pointer.json'
    monkeypatch.setattr(c, 'ACTIVE_POINTER', pointer)
    assert c.active_registry_path() == c.REGISTRY
    pointer.write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='activation'): c.active_registry_path()


@pytest.mark.parametrize('position,looping,expected', [(5., False, True), (2., False, False), (5., True, False)])
def test_completed_hold_is_valid_but_unexpected_stop_or_loop_is_not(position, looping, expected):
    import cfd_native_batch40_modular_contract_v1 as identities
    clip = SimpleNamespace(get_play_length=lambda: 5.)
    body = SimpleNamespace(get_editor_property=lambda _: SimpleNamespace(get_editor_property=lambda _: looping),
        get_skeletal_mesh_asset=lambda: SimpleNamespace(get_editor_property=lambda _: c.SKELETONS['female']))
    base = {'success': False, 'sources': {}, 'bindings': {'success': True, 'errors': [], 'appearance_readback': {},
        'characters': {'female': {}}}, 'animation': {'female': {'animation': 'clip', 'position': position, 'playing': False}},
        'animation_errors': ['female/playback_state_mismatch']}
    plan = {'sources': {'character_registry': {}, 'appearance_palette': {}},
        'faces': {'female': {'face_id': 'smile', 'animation_path': 'clip', 'playback': {'mode': 'oneshot', 'end_behavior': 'hold_last'}}},
        'characters': {'female': {'case': {'character_id': 'test', 'skeleton': c.SKELETONS['female']}}}}
    ns = functions('state', _state=lambda *a: copy.deepcopy(base), identities=identities,
        fixed=SimpleNamespace(body_for=lambda _: body, object_path=lambda x: x, BASES=('Body',)))
    result = ns['state']({'action_index': 0, 'playing': True}, {}, plan, {'female': {'review_motion': clip}})
    assert result['success'] is expected


def test_new_human_observations_use_new_ledger_and_require_exact_reply(tmp_path, monkeypatch):
    import contextlib
    import run_cfd_native_batch40_modular_review_v1 as controller
    root, new = tmp_path / 'old', tmp_path / 'new'
    (root / 'replies').mkdir(parents=True)
    new.mkdir()
    old = root / 'manual_review.json'; old.write_text('historical', encoding='utf8')
    monkeypatch.setattr(controller.identities, 'ROOT', root)
    monkeypatch.setattr(c, 'PANEL_RUN', new)
    monkeypatch.setattr(controller, 'verify_result', lambda *a: None)
    monkeypatch.setattr(controller.panel, 'command_lock', contextlib.nullcontext)
    data = {'sources': {'native_face_library': {'sha256': 'new'}}, 'face_library': {'schema': c.SCHEMA_V2}}
    monkeypatch.setattr(controller, 'load_catalog', lambda: data)
    raw = {'request': {}, 'sources': data['sources'], 'bindings': {}, 'animation': {}, 'plan_sha256': 'plan'}
    evidence = root / 'replies/result.json'; evidence.write_text(json.dumps(raw), encoding='utf8')
    reply = {**raw, 'controller_result_file': str(evidence), 'controller_result_sha256': c.source(evidence)['sha256']}
    with pytest.raises(ValueError, match='使用者'): controller.record_observation('female', 'accepted', '', {}, reply, data)
    result = controller.record_observation('female', 'accepted', 'observed', {}, reply, data, human_button=True)
    assert result['note'] == 'observed' and len(c.read(new / 'manual_review.json')['observations']) == 1
    assert old.read_text(encoding='utf8') == 'historical'
    evidence.write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='回执'): controller.record_observation('female', 'accepted', '', {}, reply, data, human_button=True)
