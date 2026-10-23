"""Offline final-state safety; never imports RLPy or starts an application."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load('cc_finalize_refresh_partial_v1')
RUNNER = load('cc_run_character_refresh_v1')
GEOMETRY = load('cc_repair_headshot_support_materials_v1')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(path):
    return {'path': str(path), 'sha256': sha(path)}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return reference(path)


def support_snapshot(shift=0.):
    transform = {'translation': dict(x=0., y=0., z=0.), 'rotation': dict(x=0., y=0., z=0., w=1.)}
    return {'working_subdivision': 0, 'expression_count': 379, 'parts': [],
        'meshes': [{'owner': 'avatar', 'name': name, 'vertex_count': 1,
            'face_count': 1, 'faces_sha256': 'same_faces', 'vertices': [[shift if name == 'CC_Base_TearLine' else 0., 0., 0.]]}
            for name in sorted(MODULE.PROTECTED_NAMES)],
        'owner_transforms': [{'owner': 'avatar', 'space': space, 'value': copy.deepcopy(transform)} for space in ('local', 'world')],
        'owner_transform_errors': []}


def test_full_native_geometry_requires_all_original_support_low_and_high_and_transforms():
    before = support_snapshot()
    high = copy.deepcopy(before['meshes'][2])
    high['vertex_count'], high['vertices'] = 2, [[0., 0., 0.], [0., 0., 0.]]
    before['meshes'].append(high)
    assert len(MODULE.protected_geometry(before)['meshes']) == 7
    missing = copy.deepcopy(before)
    missing['meshes'] = [row for row in missing['meshes'] if row['name'] != 'CC_Base_Tongue']
    with pytest.raises(ValueError, match='all five'):
        MODULE.protected_geometry(missing)
    missing = copy.deepcopy(before)
    missing['owner_transforms'].pop()
    with pytest.raises(ValueError, match='local/world'):
        MODULE.protected_geometry(missing)
    moved = copy.deepcopy(before)
    moved['meshes'][-1]['vertices'][-1][0] = .00021
    assert not GEOMETRY.compare_geometry(before, moved)['passed']
    transformed = copy.deepcopy(before)
    transformed['owner_transforms'][0]['value']['translation']['x'] = .00021
    assert not GEOMETRY.compare_geometry(before, transformed)['passed']


def test_live_capture_adapter_really_reads_all_native_meshes_scalars_and_repeat():
    calls = {'batch': 0, 'scalar': 0}
    def vector(value): return SimpleNamespace(x=value[0], y=value[1], z=value[2])
    class Mesh:
        def __init__(self, name): self.name = name
        def GetName(self): return self.name
        def GetVerticesCount(self): return 3
        def GetVertices(self, world):
            assert world is False
            calls['batch'] += 1
            return [vector([0., 0., 0.])] * 3
        def GetVertex(self, index, world):
            assert world is False
            calls['scalar'] += 1
            return vector([0., 0., 0.])
        def GetFacesCount(self): return 1
        def GetFace(self, index): return [0, 1, 2]
    transform = {'translation': dict(x=0., y=0., z=0.), 'rotation': dict(x=0., y=0., z=0., w=1.)}
    meshes = [Mesh(name) for name in sorted(MODULE.PROTECTED_NAMES)]
    avatar = SimpleNamespace(GetID=lambda: 1, GetSubdivMeshLevel=lambda: 0,
        GetMeshes=lambda children: meshes, GetAvatarParts=lambda: [],
        LocalTransform=lambda: transform, WorldTransform=lambda: transform,
        GetFaceComponent=lambda: SimpleNamespace(GetExpressionNames=lambda pattern: []))
    def scalar(mesh, rows):
        for index in range(len(rows)):
            value = mesh.GetVertex(index, False)
            assert [value.x, value.y, value.z] == rows[index]
        return [{'index': 0, 'delta_mm': 0.}]
    observed = MODULE.capture_protected(avatar, SimpleNamespace(_transform_data=lambda value: value),
        GEOMETRY, SimpleNamespace(_scalar_cross_check=scalar))
    assert calls == {'batch': 12, 'scalar': 18}
    assert len(observed['readback']['scalar_queries']) == 6
    assert observed['readback']['repeated_capture']['passed']
    assert not observed['readback']['scene_update_performed']


@pytest.mark.parametrize('checked,enabled,expect_click,success', [
    (True, True, True, True), (False, False, False, True), (True, False, False, False)])
def test_close_editor_only_clicks_available_exact_checkbox(checked, enabled, expect_click, success):
    state = {'checked': checked, 'clicks': 0}
    def click():
        state.update(checked=False, clicks=state['clicks'] + 1)
    checkbox = SimpleNamespace(text=lambda: 'Activate Editor', isVisible=lambda: True,
        isEnabled=lambda: enabled, isChecked=lambda: state['checked'], click=click)
    ui = SimpleNamespace(SELECTORS={'editor': ()}, unique_widget=lambda *args: checkbox,
        widget_record=lambda widget: {'isChecked': widget.isChecked(), 'isEnabled': widget.isEnabled()})
    api = SimpleNamespace(QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(allWidgets=lambda: [checkbox], processEvents=lambda: None)))
    audit = {}
    if success:
        assert MODULE.deactivate_editor(api, ui, audit)['verified_off']
    else:
        with pytest.raises(ValueError, match='disabled'):
            MODULE.deactivate_editor(api, ui, audit)
    assert state['clicks'] == int(expect_click)


@pytest.mark.parametrize('scenario', ['already_ready', 'delayed_ready', 'unknown_modal', 'identity_changed', 'active_known_progress'])
def test_editor_wait_is_condition_bound_and_protects_identity_and_modals(monkeypatch, scenario):
    state = {'tick': 0, 'time': 0., 'quit': False}
    modal = {}
    def ready(): return scenario == 'already_ready' or state['tick'] >= 3
    page = SimpleNamespace(isVisible=lambda: True, isEnabled=ready)
    checkbox = SimpleNamespace(isVisible=lambda: True, isEnabled=ready)
    avatar = SimpleNamespace(GetID=lambda: 2 if scenario == 'identity_changed' and state['tick'] else 1)
    ui = SimpleNamespace(SELECTORS={'editor': ('editor',)}, APPEARANCE_PAGE_SELECTOR=('page',),
        unique_widget=lambda widgets, name: checkbox if name == 'editor' else page,
        widget_record=lambda widget: {'isVisible': widget.isVisible(), 'isEnabled': widget.isEnabled()})
    timers = []
    class Timer:
        def __init__(self):
            self.timeout = SimpleNamespace(connect=lambda callback: setattr(self, 'callback', callback))
            self.active = False
            timers.append(self)
        def setInterval(self, interval): assert interval == 50
        def start(self): self.active = True
        def stop(self): self.active = False
    class EventLoop:
        def quit(self): state['quit'] = True
        def exec_(self):
            while not state['quit']:
                state['tick'] += 1
                state['time'] += .05
                if scenario == 'unknown_modal': modal['modal_guard'] = {'unknown': {'text': 'Unexpected'}}
                for timer in timers:
                    if timer.active: timer.callback()
                assert state['tick'] < 10
    api = SimpleNamespace(QtCore=SimpleNamespace(QTimer=Timer, QEventLoop=EventLoop),
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(allWidgets=lambda: [],
            activeModalWidget=lambda: object() if scenario == 'active_known_progress' and state['tick'] < 4 else None)),
        RLPy=SimpleNamespace(RScene=SimpleNamespace(GetAvatars=lambda: [avatar], GetSelectedObjects=lambda: [avatar])))
    monkeypatch.setattr(MODULE.time, 'monotonic', lambda: state['time'])
    audit = {}
    if scenario in ('unknown_modal', 'identity_changed'):
        with pytest.raises(ValueError, match='Unknown modal|identity/selection'):
            MODULE.wait_editor_ready(api, ui, '1', audit, modal, lambda: None)
        assert not audit['ready']
    else:
        assert MODULE.wait_editor_ready(api, ui, '1', audit, modal, lambda: None)['ready']
        assert audit['loop_started'] is (scenario != 'already_ready')
        if scenario == 'active_known_progress': assert state['tick'] == 4
    assert not any(timer.active for timer in timers)


@pytest.fixture
def environment(tmp_path, monkeypatch):
    root = tmp_path / 'runs'
    root.mkdir()
    monkeypatch.setattr(MODULE, 'RUN_ROOT', str(root))
    monkeypatch.setattr(MODULE, 'STAGE_ROOT', str(root))
    partial_dir = root / 'successful_partial'
    partial_dir.mkdir()
    source, partial = root / 'original.ccProject', partial_dir / 'partial.ccProject'
    source.write_bytes(b'immutable original')
    partial.write_bytes(b'successful partial')
    body = {'working_subdivision_level': 0, 'local': [[0., 0., 0.]] * 14164}
    body_ref = write(partial_dir / 'source_geometry.json', body)
    stages = {}
    for label in ('source', 'after_eyes', 'reloaded'):
        ref = write(partial_dir / ('pixels_' + label) / 'materials.json',
            {'checkpoint': label, 'pixel_capture_complete': True, 'materials': []})
        stages[label] = dict(ref, pixel_capture_complete=True)
    gate = {'passed': True, 'threshold_mm': .002, 'vertex_count': 14164, 'allowances': []}
    prior = {'diagnostic_mode': 'character_refresh', 'success': True, 'recipe_complete': False,
        'layer_persistence_passed': True, 'source_unchanged': True, 'pixel_capture_enabled': True,
        'layers_before_save': {'makeup': ['Eyebrow']}, 'layers_after_reload': {'makeup': ['Eyebrow']},
        'pixel_checks': {name: {'passed': True} for name in MODULE.REQUIRED_PIXEL_CHECKS},
        'steps': [{'geometry_against_source': gate, 'geometry_against_previous_phase': gate, 'measured_working_subdivision_level': 0}],
        'config': {'source_project': reference(source)}, 'candidate': reference(partial), 'saved_candidate': reference(partial),
        'pixel_stages': stages, 'pending_phases': ['eyelashes'], 'pending_validation': ['visual_acceptance']}
    prior_path = partial_dir / 'refresh_partial_report.json'
    config = {'recipe_complete': False, 'partial_report': write(prior_path, prior), 'source_body_snapshot': body_ref}
    state = {'project': 'source', 'level': 0, 'checked': False, 'selected': [], 'mode': None, 'switches': [], 'saves': []}
    calls = []
    def switch(level):
        state['switches'].append(level)
        if state['mode'] != 'switch_failed': state['level'] = level
        return SimpleNamespace(IsError=lambda: False)
    avatar = SimpleNamespace(GetID=lambda: 1, GetSubdivMeshLevel=lambda: state['level'], SwitchSubdivMeshLevel=switch)
    def click():
        calls.append('close')
        state['checked'] = False
    checkbox = SimpleNamespace(text=lambda: 'Activate Editor', isVisible=lambda: True,
        isEnabled=lambda: True, isChecked=lambda: state['checked'], click=click)
    def load_project(path, label, api, receipts, checkpoint):
        calls.append('load:' + Path(path).name)
        if str(path) == str(source):
            state.update(project='source', level=0, checked=False)
        elif str(path) == str(partial):
            state.update(project='partial', level=1, checked=True)
        else:
            state.update(project='reloaded', level=1 if state['mode'] == 'reload_level1' else 0,
                checked=state['mode'] == 'reload_editor_on')
        return {}
    def inside(path, parent):
        return Path(path).resolve().is_relative_to(Path(parent).resolve())
    def ref(ref, api, extension, parents):
        if not any(inside(ref['path'], parent) for parent in parents) or Path(ref['path']).suffix.lower() != extension:
            raise ValueError('Reference outside scope')
        if sha(ref['path']) != ref['sha256']: raise ValueError('SHA changed')
        return ref['path']
    probe = SimpleNamespace(inside=inside, reference=ref, guarded_load=load_project,
        status_record=lambda raw: {'IsError': raw.IsError(), 'returned': True})
    def guarded(operation, api, receipt, checkpoint):
        if state['mode'] == 'unknown_modal' and state['checked']:
            raise ValueError('Unknown modal refused')
        return operation()
    ui = SimpleNamespace(guarded_action=guarded, SELECTORS={'editor': ()},
        unique_widget=lambda *args: checkbox, widget_record=lambda widget: {'isChecked': widget.isChecked()})
    def body_capture(avatar, api, include_world, output_path):
        assert not hasattr(api, 'force_avatar_scene_evaluation'), 'No morph notification during raw capture'
        result = copy.deepcopy(body)
        result['working_subdivision_level'] = state['level']
        if state['mode'] == 'body_drift' and state['project'] != 'source': result['local'][-1][0] = .00021
        write(Path(output_path), result)
        return result
    capture = SimpleNamespace(capture_body_snapshot=body_capture)
    monkeypatch.setattr(MODULE, 'capture_protected', lambda *args:
        support_snapshot(.00021 if state['mode'] == 'support_drift' and state['project'] != 'source' else 0.))
    def pixels_capture(avatar, output, label, api):
        result = {'pixel_capture_complete': True, 'checkpoint': label}
        write(Path(output) / ('pixels_' + label) / 'materials.json', result)
        return result
    pixels = SimpleNamespace(capture_stage=pixels_capture,
        compare_eye_pixels=lambda *args: {'passed': state['mode'] != 'eye_pixels_changed'},
        compare_pixels=lambda before, after, api, **kwargs: {'passed': not (
            state['mode'] == 'reload_pixels_changed' and after['checkpoint'] == 'reloaded' and not kwargs)})
    def save(path):
        state['saves'].append(path)
        Path(path).write_bytes(b'independent final state')
        return SimpleNamespace(IsError=lambda: False)
    api = SimpleNamespace(sha256_file=sha, now=lambda: 'test', write_json=lambda value, path: write(Path(path), value),
        checked=lambda label, raw: None, _transform_data=lambda transform: {},
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(allWidgets=lambda: [checkbox], processEvents=lambda: None)),
        RLPy=SimpleNamespace(RScene=SimpleNamespace(GetAvatars=lambda: [avatar],
            GetSelectedObjects=lambda: state['selected'], SelectObject=lambda avatar: state.update(selected=[avatar])),
            RFileIO=SimpleNamespace(SaveProject=save)))
    for name, module in [('cc_makeup_probe_v1', probe), ('cc_skingen_controls_v1', ui),
        ('cc_refresh_material_pixels_v1', pixels), ('cc_capture_assembly_geometry_v1', capture),
        ('cc_run_character_refresh_v1', RUNNER), ('cc_repair_headshot_support_materials_v1', GEOMETRY)]:
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(MODULE.importlib, 'reload', lambda module: module)
    return root, config, prior, prior_path, api, probe, state, calls


@pytest.mark.parametrize('field,value', [('success', False), ('layer_persistence_passed', False),
    ('pixel_capture_enabled', False), ('source_unchanged', False), ('recipe_complete', True)])
def test_failed_or_unverified_partial_is_rejected_before_cc_calls(environment, field, value):
    root, config, prior, path, api, probe, state, calls = environment
    prior[field] = value
    config['partial_report'] = write(path, prior)
    with pytest.raises(ValueError, match='Successful'):
        MODULE.run({'finalize_partial': config}, str(root / 'final'), lambda text: None, api)
    assert not calls and not state['saves'] and not state['switches']


def test_changed_sha_and_existing_output_are_rejected_before_cc_calls(environment):
    root, config, prior, path, api, probe, state, calls = environment
    output = root / 'final'
    output.mkdir()
    (output / 'keep').write_bytes(b'keep')
    with pytest.raises(ValueError, match='Refuse existing'):
        MODULE.run({'finalize_partial': config}, str(output), lambda text: None, api)
    config['partial_report']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='SHA changed'):
        MODULE.run({'finalize_partial': config}, str(root / 'new'), lambda text: None, api)
    assert not calls


@pytest.mark.parametrize('mode,success,saves,switches', [
    (None, True, 1, 1), ('unknown_modal', False, 0, 0), ('switch_failed', False, 0, 1),
    ('body_drift', False, 0, 1), ('support_drift', False, 0, 1), ('eye_pixels_changed', False, 0, 1),
    ('reload_level1', False, 1, 1), ('reload_editor_on', False, 1, 1), ('reload_pixels_changed', False, 1, 1)])
def test_finalizer_retains_strict_geometry_pixels_and_no_recipe_completion(environment, mode, success, saves, switches):
    root, config, prior, path, api, probe, state, calls = environment
    state['mode'] = mode
    result = MODULE.run({'finalize_partial': config}, str(root / 'final'), lambda text: None, api)
    assert result['success'] is success, result.get('error')
    assert result['recipe_complete'] is False and result['pending_phases'] == ['eyelashes']
    assert len(state['saves']) == saves and len(state['switches']) == switches
    assert all(level == 0 for level in state['switches']), 'Never restore editing level1'
    assert calls[:2] == ['load:original.ccProject', 'load:partial.ccProject']
    assert sha(prior['candidate']['path']) == prior['candidate']['sha256']
    if success:
        assert result['final_working_subdivision_level'] == 0
        assert all(row['all_native_support_against_original']['passed'] for row in result['geometry_checks'])
        assert result['prior_layer_persistence_passed'] and not result['closed_project_layer_reedit_verified']


@pytest.mark.parametrize('failure', [None, 'immediate_readback', 'skin_changed', 'eyes_changed'])
def test_post_close_repair_keeps_raw_receipt_and_recaptures_all_gates_before_save(environment, failure):
    root, config, prior, path, api, probe, state, calls = environment
    pixels = sys.modules['cc_refresh_material_pixels_v1']
    original_compare = pixels.compare_pixels
    def compare(before, after, api, **kwargs):
        if after['checkpoint'] == 'saved' and kwargs:
            return {'passed': False, 'differences': [{'key': ['avatar', 'CC_Base_Body', 'Std_Eyelash'],
                'channel': 'bump', 'reason': 'protected_channel_availability_changed'}]}
        return original_compare(before, after, api, **kwargs)
    def restore(*args):
        calls.append('restore_three_lash_channels')
        return {'passed': failure != 'immediate_readback'}
    pixels.compare_pixels = compare
    pixels.restore_closed_lash_support = restore
    pixels.compare_skin_pixels = lambda *args: {'passed': failure != 'skin_changed'}
    pixels.compare_eye_pixels = lambda before, after, api: {'passed': not (
        failure == 'eyes_changed' and after['checkpoint'] == 'after_closed_support_restore')}
    result = MODULE.run({'finalize_partial': config}, str(root / 'closed_repair'), lambda text: None, api)
    assert result['success'] is (failure is None), result.get('error')
    assert calls.count('restore_three_lash_channels') == 1
    assert len(state['saves']) == int(failure is None)
    assert result['pre_closed_support_restore_checks']['source_to_saved']['passed'] is False
    assert result['pixel_stages']['before_closed_support_restore']['path'].endswith('pixels_saved/materials.json') or result['pixel_stages']['before_closed_support_restore']['path'].endswith('pixels_saved\\materials.json')
    if failure is None:
        assert result['pixel_stages']['saved']['path'].endswith('pixels_after_closed_support_restore/materials.json') or result['pixel_stages']['saved']['path'].endswith('pixels_after_closed_support_restore\\materials.json')
        assert result['pixel_checks']['source_to_saved']['passed']
        assert result['pixel_checks']['skin_unchanged_by_closed_support_restore']['passed']
        assert any(row['phase'] == 'after_closed_support_restore' for row in result['geometry_checks'])
