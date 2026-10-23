"""Experimental skin/Makeup/eye candidate, with opt-in exact redness layers.

Every phase gates all14164 Body vertices at0.002mm, without an allowance mask.
Successful execution means a partial independent candidate, never recipe completion.
"""
import importlib
import math
import os
import sys
import traceback
from types import SimpleNamespace

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'character_refresh_20261018_v1')
PHASES = ['skin', 'remove_legacy_brow_parts', 'eyes', 'makeup_eyebrow']
REDNESS_ROOT = r'D:\CharacterCreator_sucai\Reallusion Templates\Skin\Skin Details\3_Coloration'
GEOMETRY = {'mesh': 'CC_Base_Body', 'space': 'local', 'vertices': 14164,
            'working_subdivision_level': 0, 'maximum_displacement_mm': 0.002, 'allowances': []}


def all_vertex_gate(before, after, threshold_mm=0.002):
    if threshold_mm != 0.002 or before['working_subdivision_level'] != 0 or after['working_subdivision_level'] != 0:
        raise ValueError('Strict0.002mm and working SubD0 required')
    first, second = before['local'], after['local']
    if len(first) != 14164 or len(second) != 14164 or any(len(v) != 3 for v in first + second):
        raise ValueError('Expected all14164 Body vertices')
    distances = [math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(x, y))) * 10 for x, y in zip(first, second)]
    if not all(math.isfinite(v) for v in distances):
        raise ValueError('Nonfinite geometry')
    bad = [index for index, value in enumerate(distances) if value > threshold_mm + 1e-12]
    return {'passed': not bad, 'vertex_count': len(distances), 'maximum_displacement_mm': max(distances),
            'threshold_mm': threshold_mm, 'failed_vertex_indices': bad, 'allowances': []}


def local_cage_diagnostic(before, after):
    """Inactive-cage observation only; never a substitute for active SubD0 gate."""
    first, second = before['local'], after['local']
    if len(first) != 14164 or len(second) != 14164:
        raise ValueError('Expected14164 local cage points for diagnostic')
    values = [math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(x, y))) * 10 for x, y in zip(first, second)]
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Nonfinite local cage diagnostic')
    return {'maximum_displacement_mm': max(values), 'vertex_count': len(values),
            'observed_working_level': after['working_subdivision_level'],
            'scope': 'Diagnostic local cage only, not active-base geometry acceptance'}


def redness_contract(asset, sex):
    if sex not in ('male', 'female') or asset.get('choice') not in ('hemoglobin', 'redness', 'mature_redness'):
        raise ValueError('Explicit redness type and sex required')
    if isinstance(asset.get('opacity'), bool) or asset.get('opacity') not in (50, 100):
        raise ValueError('Redness top-layer Opacity must be50/100')
    choice = asset['choice']
    relative = {'hemoglobin': 'Hemoglobin {}.ccSkinGenPreset'.format('M' if sex == 'male' else 'F'),
        'redness': os.path.join('Redness', sex.title() + '.ccSkinGenPreset'),
        'mature_redness': os.path.join('Redness', 'Mature ' + sex.title() + '.ccSkinGenPreset')}[choice]
    expected = os.path.normcase(os.path.realpath(os.path.join(REDNESS_ROOT, relative)))
    if os.path.normcase(os.path.realpath(asset['path'])) != expected:
        raise ValueError('Redness file is not the exact requested sex/type preset')
    names = ['Hemoglobin'] if choice == 'hemoglobin' else ['upper face', 'mid face', 'lower face']
    if asset.get('requested_layers') != names:
        raise ValueError('Unexpected configured redness layer names')
    return names


def select_preset_avatar(api, expected_avatar_id, audit):
    """Rebind a preset target and prove the selection immediately before LoadFile."""
    scene = api.RLPy.RScene
    avatars = list(scene.GetAvatars() or [])
    audit['scene_avatar_ids'] = [str(item.GetID()) for item in avatars]
    audit['expected_avatar_id'] = str(expected_avatar_id)
    if len(avatars) != 1 or str(avatars[0].GetID()) != str(expected_avatar_id):
        raise ValueError('Preset target is not the unique expected current avatar')
    audit['selected_ids_before'] = [str(item.GetID()) for item in (scene.GetSelectedObjects() or [])]
    raw = scene.SelectObject(avatars[0])
    audit['select_return'] = {'python_type': type(raw).__name__, 'repr': repr(raw)}
    audit['selected_ids_after'] = [str(item.GetID()) for item in (scene.GetSelectedObjects() or [])]
    audit['verified'] = audit['selected_ids_after'] == [str(expected_avatar_id)]
    if not audit['verified']:
        raise ValueError('Preset target selection readback is not exactly the expected avatar')
    return avatars[0]


def run(library, output_dir, log, api):
    directory = os.path.dirname(__file__)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    # CC remains alive across attempts; refresh the narrowly matched dialog policy.
    probe = importlib.reload(importlib.import_module('cc_makeup_probe_v1'))
    capture = importlib.import_module('cc_capture_assembly_geometry_v1')
    config = library['refresh_assembly']
    if config.get('phases') != PHASES or config.get('geometry') != GEOMETRY or config.get('recipe_complete') is not False:
        raise ValueError('Only the bounded partial candidate recipe is implemented')
    if not probe.inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('Expected independent task output child')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse existing output')
    source = probe.reference(config['source_project'], api, '.ccproject', (RUN_ROOT, STAGE_ROOT))
    probe.reference(config['current_scene_backup'], api, '.ccproject', (RUN_ROOT,))
    if os.path.normcase(os.path.realpath(source)) == os.path.normcase(os.path.realpath(config['current_scene_backup']['path'])):
        raise ValueError('Immutable independent source must differ from session backup')
    for asset in config['assets'].values():
        if api.sha256_file(asset['path']) != asset['sha256']:
            raise ValueError('Asset SHA changed')
    probe.reference(config['assets']['makeup_eyebrow'], api, '.ccskingenpreset',
                    (os.path.join(probe.MAKEUP_ROOT, 'Male'), os.path.join(probe.MAKEUP_ROOT, 'Trimmed')))
    include_redness = config.get('include_redness_layers', False)
    if config.get('redness_policy') == 'excluded_by_user' and include_redness is not False:
        raise ValueError('User-excluded redness cannot be loaded')
    verify_layers = config.get('verify_layer_persistence', False)
    if not isinstance(include_redness, bool) or not isinstance(verify_layers, bool) or (include_redness and not verify_layers):
        raise ValueError('Redness requires explicit layer persistence verification')
    redness_names = redness_contract(config['assets']['redness'], config['sex']) if include_redness else []
    # The earlier Makeup probe imported this canonical name into long-lived CC.
    # Reload before any scene mutation so newly added exact controls are used.
    ui = importlib.reload(importlib.import_module('cc_skingen_controls_v1')) if verify_layers else None
    transition_ui = ui or importlib.reload(importlib.import_module('cc_skingen_controls_v1'))
    capture_pixels = config.get('capture_pixel_evidence', True)
    if not isinstance(capture_pixels, bool):
        raise ValueError('capture_pixel_evidence must be boolean')
    restore_support = config.get('restore_non_skin_materials', False)
    if not isinstance(restore_support, bool) or (restore_support and not capture_pixels):
        raise ValueError('Measured support restoration requires pixel evidence')
    close_editor = config.get('finalize_editor_closed', False)
    if not isinstance(close_editor, bool) or (close_editor and (not verify_layers or not capture_pixels
            or config.get('redness_policy') != 'excluded_by_user' or include_redness)):
        raise ValueError('Editor-closed finalization requires excluded redness, actual layers and real pixels')
    finalizer = importlib.import_module('cc_finalize_refresh_partial_v1') if close_editor else None
    closure = importlib.import_module('cc_refresh_closed_assembly_v1') if close_editor else None
    native_geometry = importlib.import_module('cc_repair_headshot_support_materials_v1') if close_editor else None
    pixels = importlib.reload(importlib.import_module('cc_refresh_material_pixels_v1')) if capture_pixels else None
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, 'PARTIAL_skin_makeup_eye_redness.ccProject' if include_redness else 'PARTIAL_skin_makeup_eye.ccProject')
    if close_editor:
        target = os.path.join(output_dir, 'EDITING_skin_makeup_eye.ccProject')
    report = {'diagnostic_mode': 'character_refresh', 'success': False, 'recipe_complete': False, 'status': 'experimental_partial_candidate',
              'config': config, 'loads': [], 'steps': [], 'pending_phases': config['pending_phases'],
              'pending_validation': config['pending_validation'],
              'layer_persistence_passed': False,
              'implementation_sha256': api.sha256_file(__file__),
              'makeup_probe_implementation_sha256': api.sha256_file(probe.__file__) if getattr(probe, '__file__', None) else None,
              'controls_implementation_sha256': api.sha256_file(ui.__file__) if ui is not None and getattr(ui, '__file__', None) else None,
              'pixel_implementation_sha256': api.sha256_file(pixels.__file__) if pixels is not None and getattr(pixels, '__file__', None) else None,
              'closure_implementation_sha256': api.sha256_file(closure.__file__) if closure is not None and getattr(closure, '__file__', None) else None,
              'material_evidence_scope': 'Metadata fingerprints only. Native GetQImage errors may hide texture changes; equal digests never prove preserved pixels.',
              'pixel_capture_enabled': capture_pixels, 'pixel_stages': {}, 'pixel_checks': {},
              'pixel_support_repair_policy': 'Explicit opt-in only: measured eight lash/tongue channels, source pixels or proved missing-channel clears; no warning loads or widened preservation exceptions.',
              'summary_path': os.path.join(output_dir, 'refresh_partial_report.json')}

    def checkpoint(phase=None):
        if phase:
            report['phase'] = phase
            log('Experimental refresh: ' + phase)
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])

    def avatar():
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected exactly one avatar')
        return avatars[0]

    def snapshot(label):
        return capture.capture_body_snapshot(avatar(), api=api, include_world=False,
            output_path=os.path.join(output_dir, label + '_geometry.json'))

    def gate(label, baseline):
        nonlocal previous_snapshot
        if str(avatar().GetID()) != avatar_id:
            raise ValueError('Avatar identity changed')
        raw = snapshot(label)
        original_level = raw['working_subdivision_level']
        if original_level not in (0, 1):
            raise ValueError('Only observed working levels0/1 are supported')
        entry = {'phase': label, 'raw_working_subdivision_level': original_level,
                 'raw_snapshot': os.path.join(output_dir, label + '_geometry.json'),
                 'local_cage_diagnostic': local_cage_diagnostic(baseline, raw), 'subdivision_transitions': []}
        def editor_state():
            try:
                widget = transition_ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *transition_ui.SELECTORS['editor'])
                return {'isChecked': bool(widget.isChecked()), 'isEnabled': bool(widget.isEnabled())}
            except Exception as exc:
                return {'observation_error': str(exc)}
        entry['editor_before_measurement'] = editor_state()
        report['steps'].append(entry)
        checkpoint()

        def switch(requested, purpose):
            transition = {'purpose': purpose, 'before': int(avatar().GetSubdivMeshLevel()), 'requested': requested}
            entry['subdivision_transitions'].append(transition)
            checkpoint()
            def operation():
                result = avatar().SwitchSubdivMeshLevel(requested)
                transition['raw_status'] = probe.status_record(result)
                api.checked('Switch working subdivision without baking', result)
                evaluator = getattr(api, 'force_avatar_scene_evaluation', None)
                if callable(evaluator):
                    evaluator(avatar())
                transition['actual'] = int(avatar().GetSubdivMeshLevel())
                checkpoint()
                if transition['actual'] != requested:
                    raise ValueError('Actual working subdivision differs from requested level')
                return {'actual': transition['actual']}
            transition_ui.guarded_action(operation, api, transition, checkpoint)

        try:
            if original_level == 1:
                switch(0, 'actual_active_base_measurement_no_bake')
                after = snapshot(label + '_measured_subd0')
                entry['measurement_snapshot'] = os.path.join(output_dir, label + '_measured_subd0_geometry.json')
            else:
                after = raw
                entry['measurement_snapshot'] = entry['raw_snapshot']
            check = all_vertex_gate(baseline, after)
            step_check = all_vertex_gate(previous_snapshot, after)
            entry.update(measured_working_subdivision_level=after['working_subdivision_level'],
                geometry_against_source=check, geometry_against_previous_phase=step_check,
                material=api.avatar_material_fingerprint(avatar()))
            checkpoint()
            if not check['passed'] or not step_check['passed']:
                raise ValueError('All-vertex0.002mm active-base material-phase gate failed: ' + label)
            previous_snapshot = after
        finally:
            if original_level == 1 and int(avatar().GetSubdivMeshLevel()) != 1:
                switch(1, 'restore_original_SkinGen_working_level_no_bake')
            entry['working_subdivision_level_after_gate'] = int(avatar().GetSubdivMeshLevel())
            entry['editor_after_gate'] = editor_state()
            checkpoint()

    def control_step(label, operation, **guard_options):
        receipt = {'phase': label}
        report.setdefault('control_steps', []).append(receipt)
        checkpoint(label)
        receipt['result'] = ui.guarded_action(operation, api, receipt, checkpoint, **guard_options)
        checkpoint()
        return receipt['result']

    def capture_named_layers(label):
        records = {}
        for category, names in [('makeup', ['Eyebrow'])] + ([('skin', redness_names)] if include_redness else []):
            def operation(category=category, names=names):
                ui.select_category(api, category)
                return [ui.read_layer_opacity(api, name) for name in names]
            values = control_step(label + '_' + category, operation)
            records[category] = ui.layer_persistence_signature(values)
        return records

    def activate_target_editor(label, wait_ready=False):
        audit = {'phase': label, 'target_selection': {}}
        report.setdefault('editor_activation_audits', []).append(audit)

        def operation():
            checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
            audit['checkbox_before_target_selection'] = ui.widget_record(checkbox)
            checkpoint()
            select_preset_avatar(api, avatar_id, audit['target_selection'])
            api.QtWidgets.QApplication.processEvents()
            checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
            audit['checkbox_after_target_selection'] = ui.widget_record(checkbox)
            checkpoint()
            if not checkbox.isVisible():
                ui.reveal_editor(api, audit.setdefault('reveal_editor', {}))
                checkpoint()
                checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
            if wait_ready:
                finalizer.wait_editor_ready(api, ui, avatar_id, audit.setdefault('readiness_wait', {}),
                    report['control_steps'][-1], checkpoint)
                checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
            return ui.activate_editor(checkbox, audit=audit)

        return control_step(label, operation)

    pixel_snapshots = {}

    def pixel_stage(label):
        checkpoint('capture_pixels_' + label)
        observed = pixels.capture_stage(avatar(), output_dir, label, api)
        pixel_snapshots[label] = observed
        path = os.path.join(output_dir, 'pixels_' + label, 'materials.json')
        report['pixel_stages'][label] = {'path': path, 'sha256': api.sha256_file(path),
            'pixel_capture_complete': observed['pixel_capture_complete'],
            'skin_diffuse_coverage': observed.get('skin_diffuse_coverage'),
            'support_mesh_coverage': observed.get('support_mesh_coverage'),
            'texture_observation_errors': observed.get('texture_observation_errors'),
            'metadata_observation_errors': observed.get('metadata_observation_errors'),
            'decode_errors': observed.get('decode_errors'), 'capture_exception': observed.get('capture_exception')}
        checkpoint()
        if not observed['pixel_capture_complete']:
            raise ValueError('Scoped real texture pixel capture incomplete: ' + label)

    def pixel_check(label, first, second, enforce=True, **allowances):
        report['pixel_checks'][label] = pixels.compare_pixels(pixel_snapshots[first], pixel_snapshots[second], api, **allowances)
        checkpoint()
        if enforce and not report['pixel_checks'][label]['passed']:
            raise ValueError('Protected support or saved/reloaded texture pixels changed; inspect ' + label)
        return report['pixel_checks'][label]

    def eye_pixel_check(label, second):
        report['pixel_checks'][label] = pixels.compare_eye_pixels(pixel_snapshots['after_eyes'], pixel_snapshots[second], api)
        checkpoint()
        if not report['pixel_checks'][label]['passed']:
            raise ValueError('Selected eye/support pixels changed after eye preset; inspect ' + label)

    previous_snapshot = None
    try:
        checkpoint('loading_independent_source')
        probe.guarded_load(source, 'Load independent refresh source', api, report['loads'], checkpoint)
        current = avatar()
        avatar_id = str(current.GetID())
        baseline = snapshot('source')
        previous_snapshot = baseline
        all_vertex_gate(baseline, baseline)
        original_support = None
        if close_editor:
            original_support = finalizer.capture_protected(current, api, native_geometry, capture)
            native_path = os.path.join(output_dir, 'source_native_geometry.json')
            api.write_json(original_support, native_path)
            report['source_native_geometry'] = {'path': native_path, 'sha256': api.sha256_file(native_path)}
        report['material_before'] = api.avatar_material_fingerprint(current)
        if capture_pixels:
            pixel_stage('source')
        for phase in PHASES:
            checkpoint(phase)
            current = avatar()
            if phase == 'remove_legacy_brow_parts':
                _, result = api.remove_existing_avatar_part(current, 'eyebrows')
            elif phase == 'makeup_eyebrow':
                api.RLPy.RScene.SelectObject(current)
                result = probe.guarded_load(config['assets'][phase]['path'], 'Load one Makeup preset', api,
                    report['loads'], checkpoint, preserve_modified_materials=True, stage='makeup_preset')
            elif phase == 'skin':
                api.RLPy.RScene.SelectObject(current)
                status, dialogs = api.load_file_with_optional_skin_material_dialog(
                    config['assets']['skin']['path'], 'Load explicit full skin')
                result = {'load_status': status, 'dialog_policy': dialogs,
                    'verification': 'Exact existing skin loader plus subsequent real SaveFile pixel evidence; no GetQImage fingerprint change requirement.'}
            else:
                _, result = api.apply_appearance_assets(current, [config['assets'][phase]], cleanup_names=[],
                    allow_missing_cleanup=True, allow_verified_material_noop=True)
            report.setdefault('applications', []).append({'phase': phase, 'result': result})
            gate(phase, baseline)
            if phase == 'eyes' and capture_pixels:
                pixel_stage('after_eyes')
            if phase == 'skin' and capture_pixels:
                pixel_stage('after_skin')
                initial = pixel_check('source_to_skin_protected_support', 'source', 'after_skin', enforce=False, allow_skin_changes=True)
                report['support_preservation_status'] = 'unchanged' if initial['passed'] else 'raw_skin_load_changed_support'
                if not initial['passed']:
                    if not restore_support:
                        raise ValueError('Protected support texture pixels changed; measured restoration not enabled')
                    checkpoint('restore_evidenced_non_skin_materials')
                    report['support_restore'] = pixels.restore_evidenced_support(avatar(), pixel_snapshots['source'],
                        pixel_snapshots['after_skin'], initial, api, os.path.join(output_dir, 'support_restore'))
                    if not report['support_restore']['passed']:
                        raise ValueError('Support restore immediate readback failed')
                    gate('after_support_restore', baseline)
                    pixel_stage('after_support_restore')
                    pixel_check('source_to_restored_protected_support', 'source', 'after_support_restore', allow_skin_changes=True)
                    report['pixel_checks']['skin_pixels_unchanged_during_support_restore'] = pixels.compare_skin_pixels(
                        pixel_snapshots['after_skin'], pixel_snapshots['after_support_restore'], api)
                    checkpoint()
                    if not report['pixel_checks']['skin_pixels_unchanged_during_support_restore']['passed']:
                        raise ValueError('Authorized skin pixels changed during support-only restoration')
                    report['support_preservation_status'] = 'restored_and_reverified'
                observation = pixels.compare_pixels(pixel_snapshots['source'], pixel_snapshots['after_skin'], api)
                report['authorized_skin_pixel_changes_observed'] = [difference for difference in observation.get('differences', [])
                    if len(difference.get('key', [])) == 3 and difference['key'][1] == 'CC_Base_Body'
                    and difference['key'][2] in pixels.SKINS]
                checkpoint()
        if verify_layers:
            activate_target_editor('activate_editor_for_exact_layers')
            gate('after_editor_activation', baseline)
        if include_redness:
            asset = config['assets']['redness']
            def load_redness():
                selection = {}
                report['redness_target_selection'] = selection
                checkpoint('select_avatar_for_redness_preset')
                select_preset_avatar(api, avatar_id, selection)
                checkpoint('load_one_redness_preset')
                raw_status = api.RLPy.RFileIO.LoadFile(asset['path'])
                report['redness_raw_status'] = probe.status_record(raw_status)
                checkpoint()
                if raw_status is None or not callable(getattr(raw_status, 'IsError', None)):
                    raise ValueError('Missing inspectable redness LoadFile RStatus')
                api.checked('Load one exact redness preset', raw_status)
                return report['redness_raw_status']
            control_step('load_one_redness_preset', load_redness,
                preserve_modified_materials=config.get('preserve_modified_materials', False), stage='redness_preset')
            gate('after_redness_load', baseline)
            control_step('select_skin_for_redness', lambda: ui.select_category(api, 'skin'))
            # Persist the real table before matching expected names. Unknown names stop safely.
            report['redness_table_before_writes'], _ = ui.capture(api, redness_names)
            checkpoint()
            for index, name in enumerate(redness_names):
                audit = {}
                report.setdefault('redness_opacity_writes', []).append(audit)
                control_step('redness_opacity_' + str(index), lambda name=name, audit=audit:
                    ui.set_layer_opacity(api, name, asset['opacity'], audit))
                gate('after_redness_opacity_' + str(index), baseline)
        if verify_layers:
            report['layers_before_save'] = capture_named_layers('before_save_layers')
            gate('after_presave_layer_reads', baseline)
        if close_editor:
            checkpoint('save_independent_editing_checkpoint')
            if os.path.exists(target):
                raise ValueError('Refuse editing checkpoint overwrite')
            report['editing_working_subdivision_level'] = int(avatar().GetSubdivMeshLevel())
            def save_editing():
                raw = api.RLPy.RFileIO.SaveProject(target)
                report['editing_save_status'] = probe.status_record(raw)
                checkpoint()
                if raw is None or not callable(getattr(raw, 'IsError', None)):
                    raise ValueError('Missing inspectable editing checkpoint SaveProject RStatus')
                api.checked('Save independent editing checkpoint', raw)
            control_step('save_editing_checkpoint_guard', save_editing)
            report['editing_checkpoint'] = {'path': target, 'sha256': api.sha256_file(target)}
            checkpoint('reload_editing_checkpoint_for_actual_layer_persistence')
            probe.guarded_load(target, 'Reload independent editing checkpoint', api, report['loads'], checkpoint)
            avatar_id = str(avatar().GetID())
            activate_target_editor('activate_editor_after_editing_reload', wait_ready=True)
            report['layers_after_reload'] = capture_named_layers('after_editing_reload_layers')
            report['layer_persistence_passed'] = report['layers_before_save'] == report['layers_after_reload']
            checkpoint()
            if not report['layer_persistence_passed']:
                raise ValueError('Saved/reloaded layer names, Opacity or enable flags differ')
            # No inactive SkinGen texture acceptance. Close immediately after
            # the actual layer read, then measure real SubD0 and native support.
            target = closure.finish(SimpleNamespace(report=report, api=api, ui=ui, pixels=pixels,
                output_dir=output_dir, avatar=avatar, avatar_id=avatar_id, original_support=original_support,
                baseline=baseline, capture=capture, all_vertex_gate=all_vertex_gate,
                checkpoint=checkpoint, probe=probe, pixel_stage=pixel_stage, pixel_snapshots=pixel_snapshots))
            report['pending_validation'] = [name for name in report['pending_validation'] if name not in (
                'Makeup_actual_layer_identity_and_persistence_after_first_real_load',
                'protected_eye_support_texture_pixels_via_real_SaveFile_exports_where_required')]
            report['source_unchanged'] = api.sha256_file(source) == config['source_project']['sha256']
            report['editing_checkpoint_unchanged'] = api.sha256_file(report['editing_checkpoint']['path']) == report['editing_checkpoint']['sha256']
            if not report['source_unchanged'] or not report['editing_checkpoint_unchanged']:
                raise ValueError('Immutable source or independent editing checkpoint changed')
            report['success'] = True
            report['status'] = 'prelash_checkpoint_validated_not_final'
            report['excluded_components'] = ['redness']
            checkpoint('prelash_checkpoint_saved_selected_lashes_required')
            return report
        checkpoint('saving_partial_candidate')
        report['saved_working_subdivision_level'] = int(avatar().GetSubdivMeshLevel())
        if os.path.exists(target):
            raise ValueError('Refuse overwrite candidate')
        raw = api.RLPy.RFileIO.SaveProject(target)
        report['save_status'] = probe.status_record(raw)
        checkpoint()
        if raw is None or not callable(getattr(raw, 'IsError', None)):
            raise ValueError('Missing inspectable SaveProject RStatus')
        api.checked('Save independent partial refresh candidate', raw)
        report['saved_candidate'] = {'path': target, 'sha256': api.sha256_file(target)}
        gate('post_save', baseline)
        if capture_pixels:
            pixel_stage('saved')
            pixel_check('source_to_saved_protected_support', 'source', 'saved', allow_skin_changes=True, allow_eye_changes=True)
            eye_pixel_check('selected_eyes_to_saved_no_allowances', 'saved')
        checkpoint('reload_partial_candidate')
        probe.guarded_load(target, 'Reload independent partial refresh candidate', api, report['loads'], checkpoint)
        # Reload gives a new runtime avatar ID; geometry remains bound to source.
        avatar_id = str(avatar().GetID())
        gate('post_reload', baseline)
        if verify_layers:
            activate_target_editor('activate_editor_after_reload')
            report['layers_after_reload'] = capture_named_layers('after_reload_layers')
            report['layer_persistence_passed'] = report['layers_before_save'] == report['layers_after_reload']
            if not report['layer_persistence_passed']:
                raise ValueError('Saved/reloaded layer names, Opacity or enable flags differ')
            gate('after_reload_layer_reads', baseline)
            report['pending_validation'] = [name for name in report['pending_validation']
                if name != 'Makeup_actual_layer_identity_and_persistence_after_first_real_load']
            if include_redness:
                report['pending_phases'] = [name for name in report['pending_phases']
                    if name != 'redness_exact_layer_opacity_and_reload']
        if capture_pixels:
            pixel_stage('reloaded')
            pixel_check('saved_to_reloaded_selected_pixels', 'saved', 'reloaded')
            eye_pixel_check('selected_eyes_to_reloaded_no_allowances', 'reloaded')
            report['pending_validation'] = [name for name in report['pending_validation']
                if name != 'protected_eye_support_texture_pixels_via_real_SaveFile_exports_where_required']
        report['source_unchanged'] = api.sha256_file(source) == config['source_project']['sha256']
        if not report['source_unchanged']:
            raise ValueError('Immutable source SHA changed')
        report['candidate'] = {'path': target, 'sha256': api.sha256_file(target)}
        report['final_working_subdivision_level'] = int(avatar().GetSubdivMeshLevel())
        report['final_subdivision_scope'] = 'Partial SkinGen editing state only; product/editor-close SubD0 save remains separate work.'
        try:
            controls = importlib.import_module('cc_skingen_controls_v1')
            table = controls.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *controls.SELECTORS['table'])
            report['skingen_table'] = controls.table_record(table, api)
        except Exception as exc:
            report['skingen_table_error'] = str(exc)
        report['success'] = True
        checkpoint('partial_candidate_saved_lash_policy_pending' if include_redness else 'partial_candidate_saved_lashes_and_redness_pending')
    except Exception as exc:
        report['error'] = {'message': str(exc), 'traceback': traceback.format_exc()}
        checkpoint('failed_partial_candidate')
    return report
