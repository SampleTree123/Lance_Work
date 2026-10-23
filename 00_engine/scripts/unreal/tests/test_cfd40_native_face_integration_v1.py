"""Offline face integration; no editor connection or source asset changes."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_cfd_native_batch40_modular_review_v1 as controller
import cfd_native_batch40_modular_contract_v1 as identity
import cfd_native_batch40_configuration_v1 as config
from test_cfd_native_batch40_modular_worker_v1 import functions, Body


@pytest.fixture(scope='module')
def base_data():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(controller.identities, 'face_catalog', lambda: {'entries': []})
        return controller.load_catalog()


@pytest.fixture
def data(base_data):
    value = copy.deepcopy(base_data)
    source = {'path': 'test-only-registry.json', 'sha256': 'test-registry-sha'}
    rows = []
    for sex in identity.SEXES:
        for action in ['static'] + [r['action_id'] for r in value['actions_by_sex'][sex]]:
            rows.append({'sex': sex, 'face_id': 'gentle_smile', 'label': '轻笑', 'body_action_id': action,
                'animation_path': '/Game/Derived/' + sex + '_' + action + '.Clip',
                'playback': {'mode': 'loop', 'end_behavior': 'repeat'},
                'non_face_validation': {'coverage': 'all_frames', 'checked_frame_count': 10, 'frame_count': 10},
                'user_acceptance': 'pending'})
    value['face_library'] = {'entries': rows, 'registry_source': source}
    value['sources']['native_face_library'] = source
    return value


def face_request(data, index=0):
    request = controller.initial_request(data)
    request.update(action_index=index, playing=True)
    request['appearance']['female'].update(face_id='gentle_smile', hair_color='purple')
    return controller.pin_face_registry(request, data)


def test_static_face_playing_allowed_but_static_none_still_rejected(data):
    request = face_request(data)
    assert controller.validate_request(request, data) == request
    request['appearance']['female']['face_id'] = 'none'
    controller.pin_face_registry(request, data)
    with pytest.raises(ValueError):
        controller.validate_request(request, data)
    request['playing'] = False
    assert controller.validate_request(request, data) == request


def test_action_resolution_uses_stable_id_not_display_index(data):
    request = face_request(data, 1)
    action_id = identity.body_action_id(data, 'female', 1)
    row = next(r for r in data['face_library']['entries'] if r['sex'] == 'female' and r['body_action_id'] == action_id)
    data['face_library']['entries'] = [row]
    data['actions_by_sex']['female'][0], data['actions_by_sex']['female'][1] = data['actions_by_sex']['female'][1], data['actions_by_sex']['female'][0]
    with pytest.raises(ValueError, match='当前身体动作'):
        controller.validate_request(request, data)
    request['action_index'] = 2
    assert controller.validate_request(request, data) == request


def test_unready_missing_mismatched_library_and_oneshot_never_available(data):
    request = face_request(data)
    request['face_registry_sha256'] = 'old'
    with pytest.raises(ValueError, match='版本'):
        controller.validate_request(request, data)
    data['face_library']['entries'] = []
    assert [r['face_id'] for r in identity.faces_for_action(data, 'female', 0)] == ['none']
    with pytest.raises(ValueError, match='face_id'):
        controller.validate_request(request, data)


def test_face_config_retains_identity_outfit_color_and_playing(data, tmp_path):
    request = face_request(data, 3)
    path = tmp_path / 'face-preset.json'
    config.save_configuration(path, {'success': True, 'sources': data['sources'], 'request': request}, data, controller.validate_request)
    restored = config.load_configuration(path, data, controller.validate_request)
    assert restored == request
    switched = identity.switch_identity(restored, 'female', 'CFD40_AF_002', data['identities'])
    assert switched['appearance'] == request['appearance']
    assert switched['choices'] == request['choices'] and switched['playing']
    changed = copy.deepcopy(data)
    changed['sources']['native_face_library']['sha256'] = 'changed'
    with pytest.raises(ValueError, match='版本'):
        config.load_configuration(path, changed, controller.validate_request)


def test_old_body_only_configuration_survives_adding_face_library(data, tmp_path):
    old = copy.deepcopy(data)
    old['sources'].pop('native_face_library')
    old['face_library'] = {'entries': []}
    request = controller.initial_request(old)
    path = tmp_path / 'old-none.json'
    config.save_configuration(path, {'success': True, 'sources': old['sources'], 'request': request}, old, controller.validate_request)
    assert config.load_configuration(path, data, controller.validate_request) == request


def test_cli_static_face_and_explicit_pause(data):
    args = controller.build_parser().parse_args(['--action', 'show', '--action-index', '0', '--female-face-id', 'gentle_smile', '--playing'])
    result = controller.cli_request(args, data)
    assert result['playing'] and result['action_index'] == 0
    assert result['face_registry_sha256'] == data['face_library']['registry_source']['sha256']
    args.playing = False
    assert not controller.cli_request(args, data)['playing']


def test_static_face_motion_uses_existing_native_playback_and_retains_position():
    body = Body('mesh', 'face', 1.3)
    calls = []
    ns = functions('set_animation', _animation=lambda r, p: calls.append(copy.deepcopy(r)),
        fixed=SimpleNamespace(object_path=lambda v: v, body_for=lambda s: body))
    request = {'action_index': 0, 'playing': True}
    ns['set_animation'](request, {'female': {'review_motion': 'face', '_previous_motion': 'face', '_previous_position': 2.4}, 'male': {}})
    assert calls[0] == {'action_index': 1, 'playing': True}
    assert request == {'action_index': 0, 'playing': True} and body.position == 2.4
    ns['set_animation']({'action_index': 0, 'playing': False}, {'female': {}, 'male': {}})
    assert calls[-1] == {'action_index': 0, 'playing': False}


@pytest.mark.parametrize('extra_playback_metadata', [False, True])
def test_load_plan_resolves_native_clip_and_none_restores_exact_body(data, monkeypatch, extra_playback_metadata):
    class Anim:
        def __init__(self, path, skeleton): self.path, self.skeleton = path, skeleton
        def get_editor_property(self, key):
            assert key == 'skeleton'
            return self.skeleton
    monkeypatch.setattr(identity, 'face_catalog', lambda: data['face_library'])
    if extra_playback_metadata:
        for row in data['face_library']['entries']:
            row['playback']['body_loop_scope'] = 'body action continuation within the verified loop window'
    palette = identity.appearance_catalog()['source']
    base = {s: Anim('/Game/Base/' + s + '.' + s, data['identities']['skeletons'][s]) for s in identity.SEXES}
    def load_original(request, data):
        return {'sources': {}}, {s: ({'review_motion': base[s]} if request['action_index'] else {}) for s in identity.SEXES}
    def load_asset(path):
        sex = 'female' if '/female_' in path else 'male'
        return Anim(path, data['identities']['skeletons'][sex])
    ns = functions('load_plan', copy=copy, identities=identity,
        selected_source=lambda r: data['identities'], _load_plan=load_original,
        fixed=SimpleNamespace(object_path=lambda obj: obj.path if isinstance(obj, Anim) else obj, digest=lambda v: 'digest'),
        unreal=SimpleNamespace(load_asset=load_asset, AnimSequence=Anim))
    request = face_request(data, 0)
    plan, prepared = ns['load_plan'](request, data)
    assert 'female_static' in prepared['female']['review_motion'].path
    assert prepared['male'].get('review_motion') is None
    assert plan['faces']['female']['registry_source'] == data['face_library']['registry_source']
    request.update(action_index=2)
    request['appearance']['female']['face_id'] = 'none'
    controller.pin_face_registry(request, data)
    plan, prepared = ns['load_plan'](request, data)
    assert all(prepared[s]['review_motion'] is base[s] and plan['faces'][s]['restore_body_only'] for s in identity.SEXES)


def test_ui_static_face_preserves_play_flag_for_view_and_pause(data, monkeypatch):
    request = face_request(data)
    monkeypatch.setattr(controller, '_active_request', request)
    monkeypatch.setattr(controller, '_active_editors', {s: SimpleNamespace(read_choice=lambda sex=s: request['choices'][sex]) for s in identity.SEXES})
    monkeypatch.setattr(controller, 'action_box', lambda: SimpleNamespace(current=lambda: 0))
    assert controller.ui_request(data, 'view', view='side')['playing']
    assert not controller.ui_request(data, 'playback', playing=False)['playing']
    assert controller.ui_request(data, 'show')['appearance'] == request['appearance']


@pytest.mark.parametrize('looping', [True, False])
def test_state_reads_static_face_clip_and_loop_without_changing_requested_body(data, looping):
    request = face_request(data)
    motion = data['face_library']['entries'][0]['animation_path']
    selections = {'female': {'face_id': 'gentle_smile', 'animation_path': motion},
                  'male': {'face_id': 'none', 'animation_path': None}}
    plan = {'sources': {'character_registry': data['identities']['source'],
        'appearance_palette': data['appearance']['source'], 'native_face_library': data['face_library']['registry_source']},
        'faces': selections, 'characters': {s: {'case': data['identities']['by_id'][request['character_ids'][s]]} for s in identity.SEXES}}
    def state(effective, *args):
        assert effective['action_index'] == 1 and effective['playing']
        return {'success': True, 'sources': {}, 'bindings': {'success': True, 'errors': [], 'appearance_readback': {},
            'characters': {s: {} for s in identity.SEXES}}, 'animation': {
            s: {'animation': selections[s]['animation_path']} for s in identity.SEXES}, 'animation_errors': []}
    def body(sex):
        return SimpleNamespace(get_editor_property=lambda key: SimpleNamespace(get_editor_property=lambda key: looping),
            get_skeletal_mesh_asset=lambda: SimpleNamespace(get_editor_property=lambda key: data['identities']['skeletons'][sex]))
    ns = functions('state', _state=state, identities=identity,
        fixed=SimpleNamespace(body_for=body, object_path=lambda v: v, BASES=('Body', 'Eyes')))
    result = ns['state'](request, data, plan, {'female': {'review_motion': motion}, 'male': {}})
    assert result['request']['action_index'] == 0 and result['request']['playing']
    assert result['success'] == looping
    assert result['face_readback']['female']['success'] == looping
    assert result['face_readback']['male']['success']


def test_hidden_panel_face_row_and_static_play_button(data, monkeypatch):
    import tkinter as tk
    roots, sent, errors = [], [], []
    original_tk = tk.Tk
    def hidden_root(*args, **kwargs):
        root = original_tk(*args, **kwargs)
        root.withdraw()
        roots.append(root)
        return root
    class Queue:
        def __init__(self, *args):
            self.busy = self.closing = False
            self.closed = True  # no worker or restoration dispatch in this test
            self.loaded_request = self.loaded_reply = None
            controller._active_manager = self
        def submit(self, request): sent.append(copy.deepcopy(request))
        def poll(self): return None
    def mainloop(root):
        root.update_idletasks()
        assert not errors
        assert len(controller._active_editors) == 2
        for editor in controller._active_editors.values():
            assert int(editor.face.grid_info()['row']) == 9
            assert editor.face.current() == 0
            assert len(editor.identity['values']) == 20
        female = controller._active_editors['female']
        female.face.current(1)
        female._face_changed()
        request = controller.ui_request(data)
        controller._active_manager.loaded_request = request
        def find(widget, label):
            for child in widget.winfo_children():
                if child.winfo_class() == 'TButton' and str(child['text']) == label:
                    return child
                result = find(child, label)
                if result is not None: return result
        find(root, '播放动作').invoke()
        assert sent[-1]['playing'] and sent[-1]['action_index'] == 0
        assert sent[-1]['appearance']['female']['face_id'] == 'gentle_smile'
        # The actual layout must fit the default 880px window at the current
        # system scaling; all rows remain distinct and the controls visible.
        frame = root.winfo_children()[0]
        assert frame.winfo_reqheight() <= 880
        root.destroy()
    monkeypatch.setattr(tk, 'Tk', hidden_root)
    monkeypatch.setattr(original_tk, 'mainloop', mainloop)
    monkeypatch.setattr(controller.panel, 'CommandQueue', Queue)
    monkeypatch.setattr(controller.panel, 'load_catalog', lambda: data)
    monkeypatch.setattr(controller.panel, 'write', lambda *args: None)
    monkeypatch.setattr(controller.panel, 'read', lambda *args: {})
    monkeypatch.setattr(controller.panel, 'record_error', lambda *args: errors.append(args))
    monkeypatch.setattr(controller, '_active_editors', {})
    try:
        controller.panel.panel(SimpleNamespace(node_id=None))
    finally:
        for root in roots:
            try: root.destroy()
            except tk.TclError: pass
