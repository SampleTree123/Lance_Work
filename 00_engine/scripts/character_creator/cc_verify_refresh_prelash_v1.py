"""Narrow same-SHA reload of the real WF003 v5 serialized pre-lash project.

No save, material application, editor activation, subdivision switch or repair.
The failed v5 receipt remains failed. This establishes product reload stability,
not equality to pre-serialization SkinGen textures and not final lash acceptance.
"""
import importlib
import json
import os
import traceback
from types import SimpleNamespace

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'


def read(path):
    with open(path, encoding='utf-8-sig') as handle:
        return json.load(handle)


def validate(config, output_dir, api, probe, runner, finalizer):
    if config.get('kind') != 'WF003_v5_same_sha_reload' or config.get('recipe_complete') is not False:
        raise ValueError('Only the explicit WF003 v5 pre-lash stability observation is implemented')
    if not probe.inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('Independent task output child required')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse existing stability output')
    prior_path = probe.reference(config['recovery_report'], api, '.json', (RUN_ROOT,))
    prior = read(prior_path)
    if prior.get('success') is not False or prior.get('error', {}).get('message') != 'Original support or selected eye pixels changed: reloaded':
        raise ValueError('Expected the unchanged real v5 terminal condition')
    if prior.get('recovered_prior_save_layer_persistence_passed') is not True:
        raise ValueError('Actual Eyebrow editing-checkpoint persistence proof required')
    candidate = probe.reference(config['candidate'], api, '.ccproject', (RUN_ROOT,))
    if config['candidate'] != prior.get('saved_candidate'):
        raise ValueError('Candidate is not the exact real v5 saved project')
    eyebrow = prior.get('recovered_layers_after_load', {}).get('makeup', {}).get('eyebrow', {})
    if eyebrow.get('opacity') != 90 or eyebrow.get('slider_opacity') != 90:
        raise ValueError('Known actual Eyebrow90 readback missing')
    old_path = probe.reference(prior['recovery']['original_failed_report'], api, '.json', (RUN_ROOT,))
    old = read(old_path)
    if old['config'].get('redness_policy') != 'excluded_by_user' or old['config'].get('include_redness_layers') is not False:
        raise ValueError('User-excluded redness scope is required')
    if old.get('layers_before_save') != prior['recovered_layers_after_load']:
        raise ValueError('Actual pre-save and reload layer signature binding differs')
    if prior['pixel_checks']['source_to_saved']['passed'] is not True or prior['pixel_checks']['after_eyes_to_reloaded']['passed'] is not True:
        raise ValueError('Real pre-save support and chosen-eye protection proofs required')
    diffs = prior['pixel_checks']['source_to_reloaded']['differences']
    if len(diffs) != 1 or diffs[0].get('key') != ['avatar', 'CC_Base_Body', 'Std_Eyelash'] or diffs[0].get('channel') != 'opacity':
        raise ValueError('Unexpected v5 protected support difference; separate diagnosis required')
    if not prior.get('geometry_checks') or any(row['body_against_original']['passed'] is not True
            or row['all_native_support_against_original']['passed'] is not True for row in prior['geometry_checks']):
        raise ValueError('Original full native geometry proof missing')
    refs = prior['geometry_snapshots']['original_source']
    body = read(probe.reference(refs['body'], api, '.json', (RUN_ROOT,)))
    native = read(probe.reference(refs['protected'], api, '.json', (RUN_ROOT,)))
    runner.all_vertex_gate(body, body)
    finalizer.protected_geometry(native)
    manifest_ref = prior['pixel_stages']['reloaded']
    pixels = read(probe.reference(manifest_ref, api, '.json', (RUN_ROOT,)))
    if not pixels.get('pixel_capture_complete') or set(pixels.get('skin_diffuse_coverage', [])) != {
            'Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg'}:
        raise ValueError('Actual serialized four-skin/support PNG baseline required')
    for row in pixels['materials']:
        records = list(row['textures'].values()) + [record['evidence'] for record in row.get('missing_textures', {}).values() if record.get('evidence')]
        for record in records:
            probe.reference(record, api, '.png', (RUN_ROOT,))
    return prior, candidate, body, native, pixels


def run(library, output_dir, log, api):
    probe = importlib.reload(importlib.import_module('cc_makeup_probe_v1'))
    ui = importlib.import_module('cc_skingen_controls_v1')
    pixels = importlib.import_module('cc_refresh_material_pixels_v1')
    finalizer = importlib.import_module('cc_finalize_refresh_partial_v1')
    runner = importlib.import_module('cc_run_character_refresh_v1')
    geometry = importlib.import_module('cc_repair_headshot_support_materials_v1')
    capture = importlib.import_module('cc_capture_assembly_geometry_v1')
    config = library['verify_prelash']
    prior, candidate, body, native, reference_pixels = validate(config, output_dir, api, probe, runner, finalizer)
    os.makedirs(output_dir, exist_ok=True)
    report = {'diagnostic_mode': 'verify_prelash', 'success': False, 'stage_validated': False,
        'accepted_final': False, 'recipe_complete': False, 'config': config, 'candidate': config['candidate'],
        'original_runtime_report_success': False, 'runtime_report_unchanged': True,
        'layer_persistence_binding': {'recovery_report': config['recovery_report'],
            'original_before_save_report': prior['recovery']['original_failed_report'],
            'actual_signature': prior['recovered_layers_after_load'], 'actual_readback_matched': True,
            'closed_project_layer_reedit_verified': False},
        'pixel_reference': prior['pixel_stages']['reloaded'], 'loads': [],
        'pending_phases': ['selected_eyelash_application_and_its_strict_final_geometry_pixel_save_reload'],
        'pending_validation': ['same_light_visual_appearance_review'],
        'skin_serialization_scope': 'Four skins were intentionally applied. Pre-save SkinGen pixels changed on first serialization/reload; those differences are recorded, never called unchanged. This probe compares the actual first-reload product pixels with the same immutable saved project reloaded again.',
        'implementation_sha256': api.sha256_file(__file__),
        'summary_path': os.path.join(output_dir, 'verify_prelash_report.json')}
    def checkpoint(phase=None):
        if phase:
            report['phase'] = phase
            log('Pre-lash same-file observation: ' + phase)
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])
    def avatar():
        values = list(api.RLPy.RScene.GetAvatars() or [])
        if len(values) != 1:
            raise ValueError('Exactly one current avatar required')
        return values[0]
    def actual_state():
        current = avatar()
        widget = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
        state = {'avatar_id': str(current.GetID()), 'working_subdivision_level': int(current.GetSubdivMeshLevel()),
            'editor': ui.widget_record(widget)}
        if current.GetSubdivMeshLevel() != 0 or str(widget.text()) != 'Activate Editor' or widget.isChecked():
            raise ValueError('Saved product must load actual0 with editor off; no correction is performed')
        return state
    try:
        checkpoint('load_exact_already_serialized_project_no_save')
        probe.guarded_load(candidate, 'Reload same SHA serialized pre-lash candidate', api, report['loads'], checkpoint)
        report['loaded_state'] = actual_state()
        checkpoint('render_current_real_saved_view')
        image_path = os.path.join(output_dir, 'prelash_current_view.png')
        api.render_preview(image_path, api.RLPy.RGlobal.GetTime())
        image = api.QtGui.QImage(image_path)
        if image.isNull() or image.width() <= 0 or image.height() <= 0:
            raise ValueError('Actual saved-view preview is not decodable')
        report['current_view_preview'] = {'path': image_path, 'sha256': api.sha256_file(image_path),
            'width': int(image.width()), 'height': int(image.height()),
            'scope': 'Actual saved scene camera/light/current-time view; no camera/light/material change. Root visual review still required.'}
        checkpoint('read_actual0_all_native_geometry_after_preview')
        current = avatar()
        observed_body = capture.capture_body_snapshot(current, api=SimpleNamespace(_transform_data=api._transform_data), include_world=True,
            output_path=os.path.join(output_dir, 'same_sha_body_geometry.json'))
        observed_native = finalizer.capture_protected(current, api, geometry, capture)
        api.write_json(observed_native, os.path.join(output_dir, 'same_sha_native_geometry.json'))
        report['geometry_checks'] = {'body_against_original': runner.all_vertex_gate(body, observed_body),
            'all_native_support_against_original': geometry.compare_geometry(native, observed_native)}
        if any(check['passed'] is not True for check in report['geometry_checks'].values()):
            raise ValueError('Same-file product body/support geometry differs from original')
        checkpoint('compare_all_actual_serialized_pixels_zero_allowance')
        observed = pixels.capture_stage(current, output_dir, 'reloaded', api)
        report['pixel_check'] = pixels.compare_pixels(reference_pixels, observed, api)
        if observed['pixel_capture_complete'] is not True or report['pixel_check']['passed'] is not True:
            raise ValueError('Same immutable serialized project pixels are not stable on reload')
        report['final_state'] = actual_state()
        report['candidate_unchanged'] = api.sha256_file(candidate) == config['candidate']['sha256']
        if not report['candidate_unchanged']:
            raise ValueError('Immutable product candidate changed')
        report['success'] = report['stage_validated'] = True
        checkpoint('same_sha_prelash_stable_selected_lash_pending')
    except Exception as exc:
        report['error'] = {'message': str(exc), 'traceback': traceback.format_exc()}
        checkpoint('failed_same_sha_prelash_observation')
    return report
