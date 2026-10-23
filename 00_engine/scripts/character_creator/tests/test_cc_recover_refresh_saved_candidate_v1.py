"""Exact v9 warning-only saved-candidate recovery; original failure stays false."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_cc_finalize_refresh_partial_v1 import environment, load, reference, write, sha, MODULE as CORE

MODULE = load('cc_recover_refresh_saved_candidate_v1')


@pytest.fixture
def recovery(environment, monkeypatch):
    root, old_config, prior, prior_path, api, probe, state, calls = environment
    monkeypatch.setattr(MODULE, 'RUN_ROOT', str(root))
    monkeypatch.setattr(MODULE, 'STAGE_ROOT', str(root))
    prior.update(success=False, phase='failed_partial_candidate', layer_persistence_passed=False,
        layers_after_reload=None, error={'message': MODULE.FAILURE_TEXT})
    prior['config'].update(redness_policy='excluded_by_user', include_redness_layers=False)
    prior['pixel_checks']['source_to_restored_protected_support'] = {'passed': True}
    prior['layers_before_save'] = {'makeup': {'eyebrow': {'opacity': 90, 'slider_opacity': 90,
        'row_enable_flags_uninterpreted': [{'object_name': 'qtEnableToolButton', 'isChecked': False}]}}}
    prior['steps'][0]['phase'] = 'post_save'
    partial_dir = prior_path.parent
    warning = partial_dir / 'warning.png'
    warning.write_bytes(b'exact fixture warning')
    monkeypatch.setattr(MODULE, 'WARNING_SHA', sha(warning))
    bad = {'checkpoint': 'saved', 'pixel_capture_complete': False, 'skin_diffuse_coverage': [],
        'texture_observation_errors': [], 'decode_errors': [], 'materials': []}
    for material in ['Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg', 'Std_Eyelash']:
        bad['materials'].append({'owner': 'avatar', 'mesh': 'CC_Base_Body', 'material': material, 'textures': {},
            'missing_textures': {name: {'reason': 'sdk_known_warning_image', 'evidence': reference(warning)}
                for name in ('diffuse', 'bump', 'roughness', 'opacity', 'metallic', 'ambient_occlusion')}})
    bad_ref = write(partial_dir / 'pixels_saved' / 'materials.json', bad)
    prior['pixel_stages']['saved'] = dict(bad_ref, pixel_capture_complete=False)
    config = {'recipe_complete': False, 'recovery_kind': 'recover_v9_saved_candidate',
        'failed_report': write(prior_path, prior), 'candidate': copy.deepcopy(prior['saved_candidate']),
        'source_body_snapshot': old_config['source_body_snapshot']}
    monkeypatch.setitem(sys.modules, 'cc_finalize_refresh_partial_v1', CORE)
    ui = sys.modules['cc_skingen_controls_v1']
    page = SimpleNamespace(isEnabled=lambda: state.get('post_select_ui_refreshed', False)
        and not state.get('ui_stays_disabled', False))
    original_unique = ui.unique_widget
    ui.APPEARANCE_PAGE_SELECTOR = ('page',)
    ui.unique_widget = lambda widgets, *selector: page if selector == ('page',) else original_unique(widgets, *selector)
    ui.widget_record = lambda widget: {'isEnabled': page.isEnabled(), 'isVisible': True,
        **({'isChecked': widget.isChecked()} if hasattr(widget, 'isChecked') else {})}
    def refresh():
        state['post_select_ui_refreshed'] = True
    api.QtWidgets.QApplication.processEvents = refresh
    page.isVisible = lambda: True
    old_unique = ui.unique_widget
    checkbox = old_unique([], *ui.SELECTORS['editor'])
    checkbox.isEnabled = lambda: page.isEnabled()
    timers = []
    state['qt_tick_seconds'] = 0.
    class Timer:
        def __init__(self):
            self.active = False
            self.timeout = SimpleNamespace(connect=lambda callback: setattr(self, 'callback', callback))
            timers.append(self)
        def setInterval(self, interval): assert interval == 50
        def start(self): self.active = True
        def stop(self): self.active = False
    class EventLoop:
        def __init__(self): self.stopped = False
        def quit(self): self.stopped = True
        def exec_(self):
            for tick in range(250):
                state['qt_tick_seconds'] += .05
                refresh()
                for timer in timers:
                    if timer.active: timer.callback()
                if self.stopped: return
            raise AssertionError('Wait must stop at its real-condition deadline')
    api.QtCore = SimpleNamespace(QTimer=Timer, QEventLoop=EventLoop)
    monkeypatch.setattr(CORE.time, 'monotonic', lambda: state['qt_tick_seconds'])
    def reveal(api, audit):
        if not page.isEnabled(): raise ValueError('Appearance page still disabled')
        audit.update(verified=True)
    ui.reveal_editor = reveal
    ui.activate_editor = lambda checkbox: {'checked': True}
    ui.select_category = lambda api, category: {'category': category}
    ui.read_layer_opacity = lambda api, name: {'layer_name': name, 'opacity': 90 if state.get('recovery_layer_mismatch') is not True else 100,
        'slider_opacity': 90 if state.get('recovery_layer_mismatch') is not True else 100,
        'row_enable_flags_uninterpreted': [{'object_name': 'qtEnableToolButton', 'isChecked': False}]}
    ui.layer_persistence_signature = load('cc_skingen_controls_v1').layer_persistence_signature
    def render(path, time):
        assert time == 'same_time'
        Path(path).write_bytes(b'real fixture render')
        calls.append('render_current_view')
    api.render_preview = render
    api.RLPy.RGlobal = SimpleNamespace(GetTime=lambda: 'same_time')
    api.QtGui = SimpleNamespace(QImage=lambda path: SimpleNamespace(isNull=lambda: False, width=lambda: 640, height=lambda: 640))
    return root, config, prior, prior_path, bad, bad_ref, api, probe, state, calls


@pytest.mark.parametrize('mode', ['different_failure', 'no_signature', 'changed_candidate', 'unknown_warning'])
def test_recovery_refuses_other_failures_before_cc_calls(recovery, mode):
    root, config, prior, path, bad, bad_ref, api, probe, state, calls = recovery
    if mode == 'different_failure':
        prior['error']['message'] = 'No character picked.'
    elif mode == 'no_signature':
        prior['layers_before_save'] = {}
    elif mode == 'changed_candidate':
        config['candidate']['sha256'] = '0' * 64
    else:
        bad['materials'][0]['missing_textures']['diffuse']['reason'] = 'unknown_placeholder'
        prior['pixel_stages']['saved'] = dict(write(Path(bad_ref['path']), bad), pixel_capture_complete=False)
    config['failed_report'] = write(path, prior)
    with pytest.raises(ValueError):
        MODULE.run({'recover_saved_candidate': config}, str(root / 'recover'), lambda text: None, api)
    assert not calls and not state['saves']


@pytest.mark.parametrize('layer_mismatch,eye_damage,success', [(False, False, True), (True, False, False), (False, True, False)])
def test_recovery_reads_real_signature_then_closes_with_all_protections(recovery, layer_mismatch, eye_damage, success):
    root, config, prior, path, bad, bad_ref, api, probe, state, calls = recovery
    state['recovery_layer_mismatch'] = layer_mismatch
    if eye_damage: state['mode'] = 'eye_pixels_changed'
    original_failure_sha = sha(path)
    result = MODULE.run({'recover_saved_candidate': config}, str(root / 'recover'), lambda text: None, api)
    assert result['success'] is success, result.get('error')
    assert result['diagnostic_mode'] == 'recover_saved_candidate'
    assert not result['recipe_complete'] and result['recovery']['original_success'] is False
    assert sha(path) == original_failure_sha
    assert not prior['success'] and prior['layer_persistence_passed'] is False
    if layer_mismatch:
        assert not state['saves'] and not state['switches'] and 'close' not in calls
    if success:
        assert result['recovered_prior_save_layer_persistence_passed']
        assert result['recovered_layer_readback']['row_enable_flags_uninterpreted'][0]['isChecked'] is False
        assert result['final_working_subdivision_level'] == 0
        assert result['current_view_preview']['width'] == 640 and 'render_current_view' in calls
        assert result['pixel_checks']['closed_to_reloaded_no_allowances']['passed']
        wait = result['editor_readiness_wait']
        assert not wait['samples'][0]['appearance_page']['isEnabled']
        assert wait['final']['appearance_page']['isEnabled']
        assert wait['final']['selected_ids'] == ['1'] and wait['ready']


def test_still_disabled_at_real_condition_deadline_stops_without_forced_enable(recovery):
    root, config, prior, path, bad, bad_ref, api, probe, state, calls = recovery
    state['ui_stays_disabled'] = True
    result = MODULE.run({'recover_saved_candidate': config}, str(root / 'recover'), lambda text: None, api)
    assert not result['success']
    wait = result['editor_readiness_wait']
    assert wait['loop_started'] and wait['timed_out']
    assert not wait['samples'][0]['appearance_page']['isEnabled']
    assert not wait['final']['appearance_page']['isEnabled']
    assert wait['samples'][0]['selected_ids'] == wait['final']['selected_ids'] == ['1']
    assert 'bounded10seconds' in result['error']['message']
    assert not state['saves'] and not state['switches'] and 'close' not in calls
