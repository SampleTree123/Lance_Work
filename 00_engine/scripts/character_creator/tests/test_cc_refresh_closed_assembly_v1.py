"""Offline gates for reusable live assembly closure; no CC calls."""
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_cc_finalize_refresh_partial_v1 import environment, load, MODULE as FINALIZER, RUNNER, support_snapshot, sha


MODULE = load('cc_refresh_closed_assembly_v1')


@pytest.fixture
def live(environment, monkeypatch):
    root, config, prior, path, api, probe, state, calls = environment
    monkeypatch.setitem(sys.modules, 'cc_finalize_refresh_partial_v1', FINALIZER)
    ui, pixels = sys.modules['cc_skingen_controls_v1'], sys.modules['cc_refresh_material_pixels_v1']
    report = dict(prior, loads=[], pixel_checks={}, pixel_stages={}, pixel_capture_enabled=True)
    report['config'] = dict(prior['config'], redness_policy='excluded_by_user', include_redness_layers=False)
    output = root / 'normal_closure'
    output.mkdir()
    state.update(project='partial', checked=True, level=1)
    snapshots = {'source': {'checkpoint': 'source'}, 'after_eyes': {'checkpoint': 'after_eyes'}}
    avatar = api.RLPy.RScene.GetAvatars()[0]
    api.render_preview = lambda path, time: Path(path).write_bytes(b'real saved view mock')
    api.RLPy.RGlobal = SimpleNamespace(GetTime=lambda: 0)
    api.QtGui = SimpleNamespace(QImage=lambda path: SimpleNamespace(isNull=lambda: False, width=lambda: 64, height=lambda: 64))
    def pixel_stage(label):
        snapshots[label] = pixels.capture_stage(avatar, str(output), label, api)
        if not snapshots[label]['pixel_capture_complete']:
            raise ValueError('Actual pixel capture incomplete')
        path = output / ('pixels_' + label) / 'materials.json'
        report['pixel_stages'][label] = {'path': str(path), 'sha256': sha(path), 'pixel_capture_complete': True}
    context = SimpleNamespace(report=report, api=api, ui=ui, pixels=pixels,
        output_dir=str(output), avatar=lambda: api.RLPy.RScene.GetAvatars()[0], avatar_id='1',
        original_support=support_snapshot(), baseline={'working_subdivision_level': 0, 'local': [[0., 0., 0.]] * 14164},
        capture=sys.modules['cc_capture_assembly_geometry_v1'], all_vertex_gate=RUNNER.all_vertex_gate,
        checkpoint=lambda *args: None, probe=probe, pixel_stage=pixel_stage, pixel_snapshots=snapshots)
    return context, state, calls


@pytest.mark.parametrize('mode', [None, 'unknown_modal', 'switch_failed', 'body_drift', 'support_drift',
    'eye_pixels_changed', 'reload_level1', 'reload_editor_on', 'reload_pixels_changed'])
def test_live_closure_checks_actual_levels_all_native_geometry_and_pixels(live, mode):
    context, state, calls = live
    state['mode'] = mode
    if mode:
        with pytest.raises(ValueError):
            MODULE.finish(context)
    else:
        path = MODULE.finish(context)
        assert Path(path).is_file()
        assert context.report['final_working_subdivision_level'] == 0
        assert not context.report['recipe_complete']
        assert context.report['layer_persistence_passed']
        assert context.report['closed_project_layer_reedit_verified'] is False
        assert len(context.report['closed_geometry_checks']) == 4
        assert context.report['pixel_checks']['serialized_to_same_sha_reload_no_allowances']['passed']
    assert state['switches'] == ([] if mode == 'unknown_modal' else [0]), 'Never restore editor working1 after closure'
    assert len(state['saves']) == int(mode in (None, 'reload_level1', 'reload_editor_on', 'reload_pixels_changed'))


def test_closure_rejects_unverified_layers_and_overwrite_before_scene_calls(live):
    context, state, calls = live
    context.report['layer_persistence_passed'] = False
    with pytest.raises(ValueError, match='layer persistence'):
        MODULE.finish(context)
    context.report['layer_persistence_passed'] = True
    target = Path(context.output_dir) / 'PRELASH_skin_makeup_eye_editor_closed_subd0.ccProject'
    target.write_bytes(b'keep')
    with pytest.raises(ValueError, match='Refuse existing'):
        MODULE.finish(context)
    assert not calls and not state['switches'] and not state['saves']


@pytest.mark.parametrize('failure', [None, 'non_lash_support'])
def test_native_lash_differences_are_recorded_only_for_pending_replacement_checkpoint(live, failure):
    context, state, calls = live
    rows = [{'owner': 'avatar', 'mesh': 'CC_Base_Body', 'material': 'Std_Eyelash'},
        {'owner': 'avatar', 'mesh': 'CC_Base_Tongue', 'material': 'Std_Tongue'}]
    context.pixel_snapshots['source']['materials'] = rows
    original_capture = context.pixels.capture_stage
    def capture(*args):
        result = original_capture(*args)
        result['materials'] = rows
        return result
    context.pixels.capture_stage = capture
    def compare(before, after, api, **kwargs):
        has_native = any(row['material'] == 'Std_Eyelash' for row in after.get('materials', []))
        changed = (has_native and before['checkpoint'] in ('source', 'saved')) or failure == 'non_lash_support'
        key = ['avatar', 'CC_Base_Tongue', 'Std_Tongue'] if failure else ['avatar', 'CC_Base_Body', 'Std_Eyelash']
        return {'passed': not changed, 'differences': [{'key': key, 'channel': 'opacity',
            'reason': 'protected_rgba_pixels_changed'}] if changed else []}
    context.pixels.compare_pixels = compare
    if failure:
        with pytest.raises(ValueError): MODULE.finish(context)
        assert not state['saves']
    else:
        MODULE.finish(context)
        assert not context.report['pixel_checks']['source_to_saved_protected_support']['passed']
        assert context.report['pixel_checks']['source_to_saved_non_lash_support']['passed']
        assert context.report['pixel_checks']['saved_to_first_reload_non_skin_support']['passed']
        assert context.report['pixel_checks']['serialized_to_same_sha_reload_no_allowances']['passed']
        assert context.report['native_lash_pixel_observations']['saved_to_reloaded_selected_pixels']
        assert context.report['stage_validated'] and not context.report['accepted_final']
        assert context.report['native_lash_replacement_required_before_completion']
        assert not context.report['recipe_complete']
