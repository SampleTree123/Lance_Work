"""Independent SkinGen editor-close/SubD0 candidate; never recipe completion.

Only a successful, layer-persistent, pixel-verified partial may enter. Load the
immutable original once to capture real original support geometry, then close
the independent partial through the inventoried Qt checkbox. No appearance
application, texture repair, tolerance allowance or shared dispatcher change.
"""
import importlib
import json
import os
import sys
import time
import traceback
from types import SimpleNamespace

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'character_refresh_20261018_v1')
PROTECTED_NAMES = frozenset(('CC_Base_Body', 'CC_Base_Eye', 'CC_Base_EyeOcclusion',
    'CC_Base_TearLine', 'CC_Base_Teeth', 'CC_Base_Tongue'))
REQUIRED_PIXEL_CHECKS = ('source_to_saved_protected_support', 'saved_to_reloaded_selected_pixels',
    'selected_eyes_to_saved_no_allowances', 'selected_eyes_to_reloaded_no_allowances')


def read_json(path):
    with open(path, encoding='utf-8-sig') as handle:
        return json.load(handle)


def mesh_key(row):
    return tuple(row[key] for key in ('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256'))


def protected_geometry(snapshot):
    """Keep every exposed low/high original native mesh, not just Body."""
    if snapshot['working_subdivision'] != 0:
        raise ValueError('Protected geometry requires actual working SubD0')
    selected = dict(snapshot)
    selected['meshes'] = [row for row in snapshot['meshes'] if row['name'] in PROTECTED_NAMES]
    if {row['name'] for row in selected['meshes']} != PROTECTED_NAMES:
        raise ValueError('Original Body and all five native support mesh kinds required')
    if len({mesh_key(row) for row in selected['meshes']}) != len(selected['meshes']):
        raise ValueError('Ambiguous exposed protected mesh level')
    owners = {row['owner'] for row in selected['meshes']}
    selected['parts'] = [row for row in snapshot['parts'] if row['name'] in PROTECTED_NAMES]
    selected['owner_transforms'] = [row for row in snapshot['owner_transforms'] if row['owner'] in owners]
    selected['owner_transform_errors'] = [row for row in snapshot.get('owner_transform_errors', []) if row['owner'] in owners]
    available = {(row['owner'], row['space']) for row in selected['owner_transforms']}
    if selected['owner_transform_errors'] or any((owner, space) not in available
        for owner in owners for space in ('local', 'world')):
        raise ValueError('Every protected owner requires real local/world transform capture')
    return selected


def capture_protected(avatar, api, geometry, body_capture):
    """Reuse real recursive capture, sampled scalars and a fresh reverse capture."""
    first = protected_geometry(geometry.capture_geometry(avatar, api))
    resolved, seen = {}, set()

    def visit(owner, path):
        identity = str(owner.GetID())
        if identity in seen:
            return
        seen.add(identity)
        for mesh in owner.GetMeshes(False) or []:
            key = (path, str(mesh.GetName()), int(mesh.GetVerticesCount()))
            if key[1] in PROTECTED_NAMES:
                if key in resolved:
                    raise ValueError('Ambiguous protected mesh scalar target')
                resolved[key] = mesh
        getter = getattr(owner, 'GetAvatarParts', None)
        for part in (getter() or []) if getter else []:
            visit(part, path + '/' + str(part.GetAvatarPartType()) + ':' + str(part.GetName()))

    visit(avatar, 'avatar')
    scalar = []
    for row in first['meshes']:
        mesh = resolved[(row['owner'], row['name'], row['vertex_count'])]
        samples = body_capture._scalar_cross_check(mesh, row['vertices'])
        scalar.append({'key': list(mesh_key(row)), 'samples': samples})
    repeated = protected_geometry(geometry.capture_geometry(avatar, api))
    crosscheck = geometry.compare_geometry(first, repeated)
    if not crosscheck['passed'] or crosscheck['maximum_local_delta_mm'] > .001:
        raise ValueError('Repeated original support geometry readback inconsistent')
    first['readback'] = {'scalar_queries': scalar, 'repeated_capture': crosscheck,
        'scene_update_performed': False, 'readback_tolerance_mm': .001}
    return first


def deactivate_editor(api, ui, audit):
    """Click the exact live checkbox once; no default-button or enabled hack."""
    checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
    audit['before'] = ui.widget_record(checkbox)
    if not checkbox.isVisible():
        ui.reveal_editor(api, audit.setdefault('reveal_editor', {}))
        checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
    audit['before_close'] = ui.widget_record(checkbox)
    if str(checkbox.text()) != 'Activate Editor' or not checkbox.isVisible():
        raise ValueError('Exact editor checkbox is not visible: {!r}'.format(audit))
    clicked = bool(checkbox.isChecked())
    if clicked:
        if not checkbox.isEnabled():
            raise ValueError('Checked editor is disabled; refusing forced close: {!r}'.format(audit))
        checkbox.click()
    api.QtWidgets.QApplication.processEvents()
    checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
    audit['after'] = ui.widget_record(checkbox)
    audit['clicked'] = clicked
    audit['verified_off'] = not bool(checkbox.isChecked())
    if not audit['verified_off']:
        raise ValueError('Editor close did not read back unchecked: {!r}'.format(audit))
    return audit


def wait_editor_ready(api, ui, expected_avatar_id, audit, modal_state, checkpoint, timeout_seconds=10.):
    """Bounded real-condition Qt wait; never sleeps, reselects or enables UI."""
    if not 0 < timeout_seconds <= 10:
        raise ValueError('Editor readiness wait is bounded to10seconds')
    started = time.monotonic()
    audit.update(timeout_seconds=timeout_seconds, poll_interval_ms=50, poll_count=0,
        samples=[], ready=False, loop_started=False)
    outcome = {}
    loop = None

    def poll():
        nonlocal loop
        try:
            if modal_state.get('modal_guard', {}).get('unknown') is not None:
                raise ValueError('Unknown modal refused while waiting for actual editor readiness')
            avatars = list(api.RLPy.RScene.GetAvatars() or [])
            selected = [str(item.GetID()) for item in (api.RLPy.RScene.GetSelectedObjects() or [])]
            if len(avatars) != 1 or str(avatars[0].GetID()) != str(expected_avatar_id) or selected != [str(expected_avatar_id)]:
                raise ValueError('Avatar identity/selection changed during bounded editor readiness wait')
            widgets = list(api.QtWidgets.QApplication.allWidgets())
            checkbox = ui.unique_widget(widgets, *ui.SELECTORS['editor'])
            page = ui.unique_widget(widgets, *ui.APPEARANCE_PAGE_SELECTOR)
            active_getter = getattr(api.QtWidgets.QApplication, 'activeModalWidget', None)
            active = active_getter() if callable(active_getter) else None
            state = {'editor': ui.widget_record(checkbox), 'appearance_page': ui.widget_record(page),
                'selected_ids': selected, 'avatar_id': str(avatars[0].GetID()),
                'avatar_python_type': type(avatars[0]).__name__, 'active_modal_present': active is not None}
            audit['poll_count'] += 1
            if not audit['samples'] or state != audit['samples'][-1]:
                audit['samples'].append(state)
                checkpoint()
            ready = (active is None and checkbox.isVisible() and checkbox.isEnabled()
                and page.isVisible() and page.isEnabled())
            elapsed = time.monotonic() - started
            if ready:
                audit.update(ready=True, elapsed_seconds=elapsed, final=state)
                outcome['done'] = True
            elif elapsed >= timeout_seconds:
                audit.update(elapsed_seconds=elapsed, final=state, timed_out=True)
                raise ValueError('Actual Appearance/editor did not become ready within bounded10seconds')
        except Exception as exc:
            outcome['error'] = exc
            audit['error'] = str(exc)
            audit['elapsed_seconds'] = time.monotonic() - started
        if loop is not None and ('done' in outcome or 'error' in outcome):
            loop.quit()

    poll()
    if not outcome:
        loop = api.QtCore.QEventLoop()
        timer = api.QtCore.QTimer()
        timer.setInterval(50)
        timer.timeout.connect(poll)
        audit['loop_started'] = True
        timer.start()
        try:
            loop.exec_()
        finally:
            timer.stop()
    checkpoint()
    if 'error' in outcome:
        raise outcome['error']
    if not audit['ready']:
        raise ValueError('Editor readiness event loop ended without verified ready state')
    return audit


def validate(config, output_dir, api, probe):
    if config.get('recipe_complete') is not False:
        raise ValueError('Final state probe must keep recipe_complete=false')
    if not probe.inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('New independent finalization output child required')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse existing finalization output')
    report_path = probe.reference(config['partial_report'], api, '.json', (RUN_ROOT,))
    prior = read_json(report_path)
    if (prior.get('diagnostic_mode') != 'character_refresh' or prior.get('success') is not True
        or prior.get('recipe_complete') is not False or prior.get('layer_persistence_passed') is not True
        or prior.get('source_unchanged') is not True or prior.get('pixel_capture_enabled') is not True
        or prior.get('layers_before_save') != prior.get('layers_after_reload')
        or not prior.get('layers_after_reload')):
        raise ValueError('Successful pixel-verified layer-persistent partial required; failed v7 is ineligible')
    if any(prior.get('pixel_checks', {}).get(name, {}).get('passed') is not True for name in REQUIRED_PIXEL_CHECKS):
        raise ValueError('Partial pixel protection gates have not all passed')
    if not prior.get('steps') or any(step.get('geometry_against_source', {}).get('passed') is not True
        or step.get('geometry_against_previous_phase', {}).get('passed') is not True
        or step.get('measured_working_subdivision_level') != 0 for step in prior['steps']):
        raise ValueError('Partial real active-base geometry gates have not all passed')
    for step in prior['steps']:
        for key in ('geometry_against_source', 'geometry_against_previous_phase'):
            check = step[key]
            if check.get('threshold_mm') != .002 or check.get('vertex_count') != 14164 or check.get('allowances') != []:
                raise ValueError('Partial geometry gates must use strict all14164 .002mm with no allowances')
    for asset in prior['config'].get('assets', {}).values():
        if api.sha256_file(asset['path']) != asset['sha256']:
            raise ValueError('Partial selected source asset SHA changed')
    parent = os.path.dirname(report_path)
    source = probe.reference(prior['config']['source_project'], api, '.ccproject', (RUN_ROOT, STAGE_ROOT))
    partial = probe.reference(prior['saved_candidate'], api, '.ccproject', (parent,))
    if prior.get('candidate') != prior['saved_candidate'] or os.path.normcase(os.path.realpath(partial)) == os.path.normcase(os.path.realpath(source)):
        raise ValueError('Independent partial project reference mismatch')
    body_path = probe.reference(config['source_body_snapshot'], api, '.json', (parent,))
    if os.path.normcase(os.path.realpath(body_path)) != os.path.normcase(os.path.realpath(os.path.join(parent, 'source_geometry.json'))):
        raise ValueError('Body baseline must be the successful partial run original source snapshot')
    manifests = {}
    for label in ('source', 'after_eyes', 'reloaded'):
        entry = prior['pixel_stages'][label]
        path = probe.reference(entry, api, '.json', (parent,))
        observed = read_json(path)
        if entry.get('pixel_capture_complete') is not True or observed.get('pixel_capture_complete') is not True or observed.get('checkpoint') != label:
            raise ValueError('Incomplete real pixel manifest: ' + label)
        for row in observed['materials']:
            evidence = list(row['textures'].values()) + [value['evidence'] for value in row.get('missing_textures', {}).values() if value.get('evidence')]
            for record in evidence:
                probe.reference(record, api, '.png', (parent,))
        manifests[label] = observed
    return prior, source, partial, read_json(body_path), manifests


def _execute(library, output_dir, log, api, validated_recovery=None):
    directory = os.path.dirname(__file__)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    probe = importlib.reload(importlib.import_module('cc_makeup_probe_v1'))
    ui = importlib.reload(importlib.import_module('cc_skingen_controls_v1'))
    pixels = importlib.reload(importlib.import_module('cc_refresh_material_pixels_v1'))
    runner = importlib.import_module('cc_run_character_refresh_v1')
    geometry = importlib.import_module('cc_repair_headshot_support_materials_v1')
    body_capture = importlib.import_module('cc_capture_assembly_geometry_v1')
    recovering = validated_recovery is not None
    config = library['recover_saved_candidate' if recovering else 'finalize_partial']
    prior, source, partial, historical_body, pixel_reference = (validated_recovery if recovering else
        validate(config, output_dir, api, probe))
    runner.all_vertex_gate(historical_body, historical_body)
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, 'RECOVERED_v9_editor_closed_subd0.ccProject' if recovering else 'PARTIAL_editor_closed_subd0.ccProject')
    report = {'diagnostic_mode': 'recover_saved_candidate' if recovering else 'finalize_partial', 'success': False, 'recipe_complete': False,
        'status': 'experimental_final_state_candidate', 'config': config,
        'partial_project': prior['saved_candidate'], 'source_project': prior['config']['source_project'],
        'prior_layer_persistence_passed': prior.get('layer_persistence_passed') is True,
        'closed_project_layer_reedit_verified': False,
        'excluded_components': ['redness'] if prior['config'].get('redness_policy') == 'excluded_by_user' else [],
        'pending_phases': list(prior.get('pending_phases', [])), 'pending_validation': list(prior.get('pending_validation', [])),
        'loads': [], 'geometry_checks': [], 'pixel_checks': {}, 'pixel_stages': {},
        'implementation_sha256': api.sha256_file(__file__),
        'summary_path': os.path.join(output_dir, 'recover_saved_candidate_report.json' if recovering else 'finalize_partial_report.json'),
        'scope': 'Close exact SkinGen editor, actual SubD0, all original native low/high support geometry and selected standard pixels; only measured post-close lash AO/Normal/roughness restoration, no recipe completion.'}
    if recovering:
        report['recovery'] = {'kind': 'recover_v9_saved_candidate', 'original_failed_report': config['failed_report'],
            'original_success': prior.get('success'), 'original_error': prior.get('error'),
            'scope': 'New downstream evidence; historical failed partial is never rewritten or declared successful.'}
    report['dependencies'] = {module.__name__: api.sha256_file(module.__file__)
        for module in (probe, ui, pixels, runner, geometry, body_capture) if getattr(module, '__file__', None)}

    def checkpoint(phase=None):
        if phase:
            report['phase'] = phase
            log('Independent final state: ' + phase)
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])

    def avatar():
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected exactly one current avatar')
        return avatars[0]

    def editor_off():
        checkbox = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
        state = ui.widget_record(checkbox)
        if str(checkbox.text()) != 'Activate Editor' or bool(checkbox.isChecked()):
            raise ValueError('Final state editor is not actually off: {!r}'.format(state))
        return state

    # Capturing geometry must not inject MorphWeight notifications. Readbacks
    # prove the actual arrays; no bake or hidden geometry repair is permitted.
    read_api = SimpleNamespace(_transform_data=api._transform_data)

    def capture(label):
        checkpoint('capture_geometry_' + label)
        current = avatar()
        if int(current.GetSubdivMeshLevel()) != 0:
            raise ValueError('Final/source capture requires actual SubD0')
        body = body_capture.capture_body_snapshot(current, api=read_api, include_world=True,
            output_path=os.path.join(output_dir, label + '_body_geometry.json'))
        supports = capture_protected(current, api, geometry, body_capture)
        path = os.path.join(output_dir, label + '_protected_geometry.json')
        api.write_json(supports, path)
        report.setdefault('geometry_snapshots', {})[label] = {
            'body': {'path': os.path.join(output_dir, label + '_body_geometry.json'),
                'sha256': api.sha256_file(os.path.join(output_dir, label + '_body_geometry.json'))},
            'protected': {'path': path, 'sha256': api.sha256_file(path)}}
        checkpoint()
        return body, supports

    def geometry_gate(label):
        body, supports = capture(label)
        check = {'phase': label, 'body_against_original': runner.all_vertex_gate(original_body, body),
            'all_native_support_against_original': geometry.compare_geometry(original_support, supports)}
        report['geometry_checks'].append(check)
        checkpoint()
        if not check['body_against_original']['passed'] or not check['all_native_support_against_original']['passed']:
            raise ValueError('Original Body/support geometry or transforms changed: ' + label)

    def pixels_at(label, restore_closed_support=False):
        checkpoint('capture_pixels_' + label)
        observed = pixels.capture_stage(avatar(), output_dir, label, api)
        path = os.path.join(output_dir, 'pixels_' + label, 'materials.json')
        report['pixel_stages'][label] = {'path': path, 'sha256': api.sha256_file(path),
            'pixel_capture_complete': observed['pixel_capture_complete']}
        checks = {'source_to_' + label: pixels.compare_pixels(pixel_reference['source'], observed, api,
            allow_skin_changes=True, allow_eye_changes=True),
            'after_eyes_to_' + label: pixels.compare_eye_pixels(pixel_reference['after_eyes'], observed, api)}
        report['pixel_checks'].update(checks)
        checkpoint()
        if (restore_closed_support and observed['pixel_capture_complete']
                and checks['after_eyes_to_' + label]['passed'] is True
                and checks['source_to_' + label]['passed'] is not True
                and checks['source_to_' + label].get('differences')):
            # Keep the raw failed observation. Never relabel or permit a changed
            # support map: restore only three measured lash channels, then read
            # all protected pixels and geometry again before any save.
            report['pre_closed_support_restore_checks'] = checks
            report['pixel_stages']['before_closed_support_restore'] = dict(report['pixel_stages'][label])
            repair = report.setdefault('closed_support_restore', {})
            def restore():
                result = pixels.restore_closed_lash_support(avatar(), pixel_reference['source'], observed,
                    checks['source_to_' + label], api, os.path.join(output_dir, 'closed_support_restore'))
                repair.update(result)
                checkpoint()
                if not result['passed']:
                    raise ValueError('Post-close lash support immediate readback failed')
                return result
            ui.guarded_action(restore, api, repair, checkpoint)
            repaired = pixels.capture_stage(avatar(), output_dir, 'after_closed_support_restore', api)
            repaired_path = os.path.join(output_dir, 'pixels_after_closed_support_restore', 'materials.json')
            report['pixel_stages'][label] = {'path': repaired_path, 'sha256': api.sha256_file(repaired_path),
                'pixel_capture_complete': repaired['pixel_capture_complete']}
            checks = {'source_to_' + label: pixels.compare_pixels(pixel_reference['source'], repaired, api,
                allow_skin_changes=True, allow_eye_changes=True),
                'after_eyes_to_' + label: pixels.compare_eye_pixels(pixel_reference['after_eyes'], repaired, api),
                'skin_unchanged_by_closed_support_restore': pixels.compare_skin_pixels(observed, repaired, api)}
            report['pixel_checks'].update(checks)
            observed = repaired
            report['editor_off_after_support_restore'] = editor_off()
            geometry_gate('after_closed_support_restore')
            checkpoint()
        if not observed['pixel_capture_complete'] or any(check['passed'] is not True for check in checks.values()):
            raise ValueError('Original support or selected eye pixels changed: ' + label)
        return observed

    try:
        checkpoint('load_original_for_real_support_baseline')
        probe.guarded_load(source, 'Load original support geometry baseline', api, report['loads'], checkpoint)
        original_body, original_support = capture('original_source')
        report['historical_body_source_check'] = runner.all_vertex_gate(historical_body, original_body)
        if not report['historical_body_source_check']['passed']:
            raise ValueError('Fresh original source Body differs from successful partial source')
        checkpoint('load_successful_partial')
        probe.guarded_load(partial, 'Load successful partial for final state', api, report['loads'], checkpoint)
        avatar_id = str(avatar().GetID())
        report['selection'] = {}
        runner.select_preset_avatar(api, avatar_id, report['selection'])
        if recovering:
            checkpoint('verify_actual_saved_candidate_makeup_layers')
            def verify_loaded_layers():
                wait_editor_ready(api, ui, avatar_id, report.setdefault('editor_readiness_wait', {}),
                    report['recovery_layer_guard'], checkpoint)
                ui.reveal_editor(api, report.setdefault('recovery_reveal_editor', {}))
                ui.activate_editor(ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor']))
                ui.select_category(api, 'makeup')
                value = ui.read_layer_opacity(api, 'Eyebrow')
                report['recovered_layer_readback'] = value
                report['recovered_layers_after_load'] = {'makeup': ui.layer_persistence_signature([value])}
                report['recovered_prior_save_layer_persistence_passed'] = report['recovered_layers_after_load'] == prior['layers_before_save']
                checkpoint()
                if not report['recovered_prior_save_layer_persistence_passed']:
                    raise ValueError('Saved candidate Eyebrow signature differs from real before-save evidence')
                report['pending_validation'] = [name for name in report['pending_validation']
                    if name != 'Makeup_actual_layer_identity_and_persistence_after_first_real_load']
                return report['recovered_layers_after_load']
            ui.guarded_action(verify_loaded_layers, api, report.setdefault('recovery_layer_guard', {}), checkpoint)
        checkpoint('closing_exact_editor')
        close = report.setdefault('editor_close', {})
        ui.guarded_action(lambda: deactivate_editor(api, ui, close), api, close, checkpoint)
        report['editor_off_after_close'] = editor_off()
        before = int(avatar().GetSubdivMeshLevel())
        transition = report.setdefault('subdivision_transition', {'before': before, 'requested': 0, 'called': False})
        if before not in (0, 1):
            raise ValueError('Only actual working levels0/1 supported')
        if before == 1:
            def switch():
                transition['called'] = True
                checkpoint('before_native_switch_to_subd0')
                raw = avatar().SwitchSubdivMeshLevel(0)
                transition['raw_status'] = probe.status_record(raw)
                transition['actual_after'] = int(avatar().GetSubdivMeshLevel())
                checkpoint('returned_native_switch_to_subd0')
                if raw is None or not callable(getattr(raw, 'IsError', None)):
                    raise ValueError('Missing inspectable subdivision RStatus')
                api.checked('Actual final working SubD0', raw)
            ui.guarded_action(switch, api, transition, checkpoint)
        transition['actual_after'] = int(avatar().GetSubdivMeshLevel())
        if transition['actual_after'] != 0:
            raise ValueError('Actual final subdivision readback is not0')
        report['editor_off_after_switch'] = editor_off()
        if str(avatar().GetID()) != avatar_id:
            raise ValueError('Avatar identity changed while closing editor')
        geometry_gate('closed_subd0')
        saved_pixels = pixels_at('saved', restore_closed_support=True)
        if pixel_reference.get('reloaded'):
            report['partial_to_closed_pixel_diagnostic'] = pixels.compare_pixels(pixel_reference['reloaded'], saved_pixels, api)
        elif recovering:
            report['partial_to_closed_pixel_diagnostic'] = {'available': False,
                'reason': 'Prior active SkinGen capture contained warning placeholders; not valid pixels for equality.'}
        checkpoint('saving_independent_subd0_candidate')
        if os.path.exists(target):
            raise ValueError('Refuse candidate overwrite')
        def save():
            raw = api.RLPy.RFileIO.SaveProject(target)
            report['save_status'] = probe.status_record(raw)
            checkpoint()
            if raw is None or not callable(getattr(raw, 'IsError', None)):
                raise ValueError('Missing inspectable SaveProject RStatus')
            api.checked('Save independent editor-closed candidate', raw)
        ui.guarded_action(save, api, report.setdefault('save_guard', {}), checkpoint)
        report['saved_candidate'] = {'path': target, 'sha256': api.sha256_file(target)}
        report['editor_off_after_save'] = editor_off()
        geometry_gate('post_save')
        checkpoint('reload_independent_subd0_candidate')
        probe.guarded_load(target, 'Reload editor-closed candidate', api, report['loads'], checkpoint)
        report['editor_off_after_reload'] = editor_off()
        geometry_gate('reloaded_subd0')
        reloaded_pixels = pixels_at('reloaded')
        report['pixel_checks']['closed_to_reloaded_no_allowances'] = pixels.compare_pixels(saved_pixels, reloaded_pixels, api)
        if not report['pixel_checks']['closed_to_reloaded_no_allowances']['passed']:
            raise ValueError('Closed candidate pixels changed on reload')
        if recovering:
            report['pending_validation'] = [name for name in report['pending_validation']
                if name != 'protected_eye_support_texture_pixels_via_real_SaveFile_exports_where_required']
        report['source_unchanged'] = api.sha256_file(source) == prior['config']['source_project']['sha256']
        report['partial_unchanged'] = api.sha256_file(partial) == prior['saved_candidate']['sha256']
        if not report['source_unchanged'] or not report['partial_unchanged']:
            raise ValueError('Immutable source/partial changed')
        if recovering:
            checkpoint('render_recovered_current_real_view')
            image_path = os.path.join(output_dir, 'recovered_current_view.png')
            if os.path.exists(image_path):
                raise ValueError('Refuse existing recovery preview')
            api.render_preview(image_path, api.RLPy.RGlobal.GetTime())
            image = api.QtGui.QImage(image_path)
            if image.isNull() or image.width() <= 0 or image.height() <= 0:
                raise ValueError('Recovery real preview is not decodable')
            report['current_view_preview'] = {'path': image_path, 'sha256': api.sha256_file(image_path),
                'width': int(image.width()), 'height': int(image.height()),
                'scope': 'Actual current camera view; no avatar, material, lighting or camera changes. Face closeup/visual eyebrow effect remains root review.'}
            report['editor_off_after_preview'] = editor_off()
            geometry_gate('after_real_preview')
        report['final_working_subdivision_level'] = int(avatar().GetSubdivMeshLevel())
        report['success'] = True
        report['status'] = 'final_state_candidate_verified_recipe_pending'
        checkpoint('independent_final_state_saved_recipe_pending')
    except Exception as exc:
        report['error'] = {'message': str(exc), 'traceback': traceback.format_exc()}
        checkpoint('failed_final_state_candidate')
    return report


def run(library, output_dir, log, api):
    """Public normal route always keeps the successful-partial precondition."""
    return _execute(library, output_dir, log, api)
