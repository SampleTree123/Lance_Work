"""Offline same-file validation; never starts CC or writes a project."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_cc_finalize_refresh_partial_v1 import environment, load, reference, write, support_snapshot, MODULE as CORE, sha


MODULE = load('cc_verify_refresh_prelash_v1')


@pytest.fixture
def known(environment, monkeypatch):
    root, config, old, old_path, api, probe, state, calls = environment
    monkeypatch.setattr(MODULE, 'RUN_ROOT', str(root))
    monkeypatch.setitem(sys.modules, 'cc_finalize_refresh_partial_v1', CORE)
    signature = {'makeup': {'eyebrow': {'opacity': 90, 'slider_opacity': 90,
        'row_enable_flags_uninterpreted': [{'object_name': 'qtEnableToolButton', 'isChecked': False}]}}}
    old['layers_before_save'] = signature
    old['config'].update(redness_policy='excluded_by_user', include_redness_layers=False)
    old_ref = write(old_path, old)
    candidate = root / 'real_serialized.ccProject'
    candidate.write_bytes(b'real first serialized product')
    pixel_ref = write(root / 'first_reload_materials.json', {'pixel_capture_complete': True, 'materials': [],
        'skin_diffuse_coverage': ['Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg']})
    receipt = {'success': False, 'error': {'message': 'Original support or selected eye pixels changed: reloaded'},
        'recovered_prior_save_layer_persistence_passed': True, 'saved_candidate': reference(candidate),
        'recovered_layers_after_load': signature, 'recovery': {'original_failed_report': old_ref},
        'geometry_checks': [{'body_against_original': {'passed': True}, 'all_native_support_against_original': {'passed': True}}],
        'geometry_snapshots': {'original_source': {'body': config['source_body_snapshot'],
            'protected': write(root / 'original_native.json', support_snapshot())}},
        'pixel_stages': {'reloaded': pixel_ref}, 'pixel_checks': {'source_to_saved': {'passed': True},
            'after_eyes_to_reloaded': {'passed': True}, 'source_to_reloaded': {'passed': False, 'differences': [{
            'key': ['avatar', 'CC_Base_Body', 'Std_Eyelash'], 'channel': 'opacity'}]}}}
    report_path = root / 'v5_report.json'
    request = {'kind': 'WF003_v5_same_sha_reload', 'recipe_complete': False,
        'candidate': reference(candidate), 'recovery_report': write(report_path, receipt)}
    api.render_preview = lambda path, time: Path(path).write_bytes(b'real preview mock')
    api.RLPy.RGlobal = SimpleNamespace(GetTime=lambda: 0)
    api.QtGui = SimpleNamespace(QImage=lambda path: SimpleNamespace(isNull=lambda: False, width=lambda: 64, height=lambda: 64))
    return root, request, receipt, report_path, api, state, calls


@pytest.mark.parametrize('mode', [None, 'body_drift', 'support_drift', 'eye_pixels_changed', 'reload_pixels_changed', 'reload_level1', 'reload_editor_on'])
def test_same_sha_reload_uses_all_pixels_geometry_and_never_saves_or_corrects(known, mode):
    root, request, receipt, path, api, state, calls = known
    original_sha = sha(path)
    state['mode'] = mode
    pixels = sys.modules['cc_refresh_material_pixels_v1']
    compare = pixels.compare_pixels
    if mode == 'eye_pixels_changed': pixels.compare_pixels = lambda *args, **kwargs: {'passed': False}
    result = MODULE.run({'verify_prelash': request}, str(root / 'verify'), lambda text: None, api)
    assert result['success'] is (mode is None), result.get('error')
    assert not result['accepted_final'] and not result['recipe_complete']
    assert result['layer_persistence_binding']['actual_readback_matched']
    assert not state['saves'] and not state['switches']
    assert len([call for call in calls if call.startswith('load:')]) == 1
    assert sha(path) == original_sha and sha(request['candidate']['path']) == request['candidate']['sha256']
    if mode is None:
        assert result['stage_validated'] and result['candidate_unchanged']
        assert result['current_view_preview']['width'] == 64


@pytest.mark.parametrize('bad', ['layer_proof', 'candidate_sha', 'unexpected_support', 'geometry_proof', 'skin_coverage'])
def test_unbound_or_unproven_v5_refused_before_load(known, bad):
    root, request, receipt, path, api, state, calls = known
    if bad == 'layer_proof': receipt['recovered_prior_save_layer_persistence_passed'] = False
    elif bad == 'candidate_sha': request['candidate']['sha256'] = '0' * 64
    elif bad == 'unexpected_support': receipt['pixel_checks']['source_to_reloaded']['differences'][0]['key'][-1] = 'Std_Tongue'
    elif bad == 'geometry_proof': receipt['geometry_checks'][0]['all_native_support_against_original']['passed'] = False
    else:
        ref = receipt['pixel_stages']['reloaded']
        value = {'pixel_capture_complete': True, 'materials': [], 'skin_diffuse_coverage': []}
        receipt['pixel_stages']['reloaded'] = write(Path(ref['path']), value)
    request['recovery_report'] = write(path, receipt)
    with pytest.raises(ValueError):
        MODULE.run({'verify_prelash': request}, str(root / 'verify'), lambda text: None, api)
    assert not calls and not state['saves'] and not state['switches']
