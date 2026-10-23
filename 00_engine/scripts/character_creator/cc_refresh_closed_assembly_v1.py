"""Final closure for a live, layer-reloaded assembly; no standalone CC route.

The caller has just reloaded its own independent editing checkpoint and proved
the actual layer signature. Original source geometry/pixels remain immutable.
"""
import importlib
import os
from types import SimpleNamespace


def finish(context):
    c = context
    report, api, ui, pixels = c.report, c.api, c.ui, c.pixels
    finalizer = importlib.import_module('cc_finalize_refresh_partial_v1')
    support = importlib.import_module('cc_repair_headshot_support_materials_v1')
    if report.get('layer_persistence_passed') is not True or report['layers_before_save'] != report['layers_after_reload']:
        raise ValueError('Live assembly closure requires actual editing-checkpoint layer persistence')
    if report['config'].get('redness_policy') != 'excluded_by_user' or report['config'].get('include_redness_layers') is not False:
        raise ValueError('Closure currently implements only the user-updated redness-excluded recipe')
    if not report.get('pixel_capture_enabled') or not c.original_support:
        raise ValueError('Original full native geometry and real texture evidence are required')
    target = os.path.join(c.output_dir, 'PRELASH_skin_makeup_eye_editor_closed_subd0.ccProject')
    if os.path.exists(target):
        raise ValueError('Refuse existing closed assembly candidate')
    read_api = SimpleNamespace(_transform_data=api._transform_data)

    def current():
        avatar = c.avatar()
        if str(avatar.GetID()) != str(c.avatar_id):
            raise ValueError('Assembly avatar identity changed during closure')
        return avatar

    def editor_off():
        widget = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
        state = ui.widget_record(widget)
        if str(widget.text()) != 'Activate Editor' or widget.isChecked():
            raise ValueError('Assembly final editor is not actually off: {!r}'.format(state))
        return state

    def geometry(label):
        c.checkpoint('closed_assembly_geometry_' + label)
        avatar = current()
        if int(avatar.GetSubdivMeshLevel()) != 0:
            raise ValueError('Closed assembly geometry requires actual SubD0')
        body_path = os.path.join(c.output_dir, label + '_closed_body_geometry.json')
        body = c.capture.capture_body_snapshot(avatar, api=read_api, include_world=True, output_path=body_path)
        native = finalizer.capture_protected(avatar, api, support, c.capture)
        native_path = os.path.join(c.output_dir, label + '_closed_native_geometry.json')
        api.write_json(native, native_path)
        check = {'phase': label, 'body_against_original': c.all_vertex_gate(c.baseline, body),
            'all_native_support_against_original': support.compare_geometry(c.original_support, native),
            'body_snapshot': {'path': body_path, 'sha256': api.sha256_file(body_path)},
            'native_snapshot': {'path': native_path, 'sha256': api.sha256_file(native_path)}}
        report.setdefault('closed_geometry_checks', []).append(check)
        c.checkpoint()
        if not check['body_against_original']['passed'] or not check['all_native_support_against_original']['passed']:
            raise ValueError('Original Body/support geometry changed during assembly closure: ' + label)

    def check_pixels(label, observed):
        checks = {'source_to_' + label + '_protected_support': pixels.compare_pixels(c.pixel_snapshots['source'], observed, api,
            allow_skin_changes=True, allow_eye_changes=True),
            'selected_eyes_to_' + label + '_no_allowances': pixels.compare_eye_pixels(c.pixel_snapshots['after_eyes'], observed, api)}
        report['pixel_checks'].update(checks)
        c.checkpoint()
        return checks

    def non_lash(snapshot):
        scoped = dict(snapshot)
        scoped['materials'] = [row for row in snapshot.get('materials', []) if
            (row.get('owner'), row.get('mesh'), row.get('material')) != ('avatar', 'CC_Base_Body', 'Std_Eyelash')]
        return scoped

    def non_lash_check(label, before, after, **allowances):
        result = pixels.compare_pixels(non_lash(before), non_lash(after), api, **allowances)
        report['pixel_checks'][label] = result
        c.checkpoint()
        if not result['passed']:
            raise ValueError('Non-lash protected pixels changed during assembly checkpoint: ' + label)
        return result

    def require_pixels(checks):
        if any(value['passed'] is not True for value in checks.values()):
            raise ValueError('Original support or selected eye pixels changed during assembly closure')

    close = report.setdefault('editor_close', {})
    c.checkpoint('close_verified_persistent_assembly_editor')
    ui.guarded_action(lambda: finalizer.deactivate_editor(api, ui, close), api, close, c.checkpoint)
    report['editor_off_after_close'] = editor_off()
    transition = report.setdefault('final_subdivision_transition', {'before': int(current().GetSubdivMeshLevel()), 'requested': 0, 'called': False})
    if transition['before'] not in (0, 1):
        raise ValueError('Only actual assembly working levels0/1 are supported')
    if transition['before'] == 1:
        def switch():
            transition['called'] = True
            c.checkpoint('switch_closed_assembly_to_actual_subd0')
            raw = current().SwitchSubdivMeshLevel(0)
            transition['raw_status'] = c.probe.status_record(raw)
            transition['actual_after'] = int(current().GetSubdivMeshLevel())
            c.checkpoint()
            if raw is None or not callable(getattr(raw, 'IsError', None)):
                raise ValueError('Missing inspectable assembly subdivision RStatus')
            api.checked('Switch closed assembly to actual SubD0', raw)
        ui.guarded_action(switch, api, transition, c.checkpoint)
    transition['actual_after'] = int(current().GetSubdivMeshLevel())
    report['editor_off_after_switch'] = editor_off()
    geometry('closed_subd0')
    c.pixel_stage('saved')
    observed = c.pixel_snapshots['saved']
    checks = check_pixels('saved', observed)
    require_pixels({'selected_eyes': checks['selected_eyes_to_saved_no_allowances']})
    non_lash_check('source_to_saved_non_lash_support', c.pixel_snapshots['source'], observed,
        allow_skin_changes=True, allow_eye_changes=True)
    c.checkpoint('save_independent_closed_assembly')
    def save():
        if os.path.exists(target):
            raise ValueError('Refuse overwrite closed assembly candidate')
        raw = api.RLPy.RFileIO.SaveProject(target)
        report['save_status'] = c.probe.status_record(raw)
        c.checkpoint()
        if raw is None or not callable(getattr(raw, 'IsError', None)):
            raise ValueError('Missing inspectable assembly SaveProject RStatus')
        api.checked('Save closed assembly candidate', raw)
    ui.guarded_action(save, api, report.setdefault('closed_save_guard', {}), c.checkpoint)
    report['saved_candidate'] = {'path': target, 'sha256': api.sha256_file(target)}
    report['editor_off_after_save'] = editor_off()
    geometry('post_save')
    c.probe.guarded_load(target, 'Reload editor-closed assembly candidate', api, report['loads'], c.checkpoint)
    c.avatar_id = str(c.avatar().GetID())
    report['editor_off_after_reload'] = editor_off()
    geometry('reloaded_subd0')
    c.pixel_stage('reloaded')
    checks = check_pixels('reloaded', c.pixel_snapshots['reloaded'])
    require_pixels({'selected_eyes': checks['selected_eyes_to_reloaded_no_allowances']})
    non_lash_check('source_to_reloaded_non_lash_support', c.pixel_snapshots['source'], c.pixel_snapshots['reloaded'],
        allow_skin_changes=True, allow_eye_changes=True)
    report['pixel_checks']['saved_to_reloaded_selected_pixels'] = pixels.compare_pixels(c.pixel_snapshots['saved'], c.pixel_snapshots['reloaded'], api)
    report['pre_serialization_to_first_reload_selected_pixels'] = report['pixel_checks']['saved_to_reloaded_selected_pixels']
    # Newly applied SkinGen skins can change during their first serialization.
    # Keep that complete difference receipt; never call it pixel-preserved.
    # Non-skin/non-lash support remains exact, and the product itself must be
    # exactly stable when the same immutable saved SHA is loaded again.
    non_lash_check('saved_to_first_reload_non_skin_support', c.pixel_snapshots['saved'], c.pixel_snapshots['reloaded'], allow_skin_changes=True)
    first_serialized = c.pixel_snapshots['reloaded']
    report['pixel_stages']['first_serialized_reload'] = dict(report['pixel_stages']['reloaded'])
    report['skin_serialization_scope'] = 'Raw pre-save versus first-reload selected pixels are recorded in full, including intended skin bake/serialization differences; no unchanged claim or numeric tolerance. Product stability is tested by a second load of exactly the same saved SHA without saving again.'
    if api.sha256_file(target) != report['saved_candidate']['sha256']:
        raise ValueError('Closed assembly candidate changed before same-SHA stability reload')
    c.probe.guarded_load(target, 'Reload same SHA closed assembly for product stability', api, report['loads'], c.checkpoint)
    c.avatar_id = str(c.avatar().GetID())
    report['editor_off_before_stability_preview'] = editor_off()
    if int(current().GetSubdivMeshLevel()) != 0:
        raise ValueError('Same-SHA assembly product did not load actual0')
    c.checkpoint('render_actual_saved_assembly_view')
    image_path = os.path.join(c.output_dir, 'prelash_current_view.png')
    if os.path.exists(image_path):
        raise ValueError('Refuse existing saved assembly preview')
    api.render_preview(image_path, api.RLPy.RGlobal.GetTime())
    image = api.QtGui.QImage(image_path)
    if image.isNull() or image.width() <= 0 or image.height() <= 0:
        raise ValueError('Actual serialized assembly preview is not decodable')
    report['current_view_preview'] = {'path': image_path, 'sha256': api.sha256_file(image_path),
        'width': int(image.width()), 'height': int(image.height()),
        'scope': 'Actual saved camera/light/current-time view, no changes; root visual review required.'}
    geometry('same_sha_reloaded_after_preview')
    stable_root = os.path.join(c.output_dir, 'same_sha_stability')
    stable = pixels.capture_stage(current(), stable_root, 'reloaded', api)
    report['pixel_checks']['serialized_to_same_sha_reload_no_allowances'] = pixels.compare_pixels(first_serialized, stable, api)
    if stable['pixel_capture_complete'] is not True or not report['pixel_checks']['serialized_to_same_sha_reload_no_allowances']['passed']:
        raise ValueError('Same immutable serialized assembly pixels changed on another load')
    stable_path = os.path.join(stable_root, 'pixels_reloaded', 'materials.json')
    report['pixel_stages']['reloaded'] = {'path': stable_path, 'sha256': api.sha256_file(stable_path), 'pixel_capture_complete': True}
    c.pixel_snapshots['reloaded'] = stable
    report['editor_off_after_stability_reload'] = editor_off()
    if api.sha256_file(target) != report['saved_candidate']['sha256']:
        raise ValueError('Immutable serialized assembly changed')
    report['native_lash_pixel_observations'] = {name: [difference for difference in value.get('differences', [])
        if difference.get('key') == ['avatar', 'CC_Base_Body', 'Std_Eyelash']]
        for name, value in report['pixel_checks'].items() if name in (
            'source_to_saved_protected_support', 'source_to_reloaded_protected_support', 'saved_to_reloaded_selected_pixels')}
    report['stage_validated'] = True
    report['accepted_final'] = False
    report['native_lash_replacement_required_before_completion'] = True
    report['native_lash_pixel_scope'] = 'Exact original avatar/CC_Base_Body/Std_Eyelash is captured and compared without tolerance, but is pending authorized selected-lash replacement. No changed native-lash pixels are accepted as final; selected-lash baseline and strict save/reload must follow.'
    report['candidate'] = dict(report['saved_candidate'])
    report['final_working_subdivision_level'] = int(current().GetSubdivMeshLevel())
    report['closed_project_layer_reedit_verified'] = False
    report['layer_persistence_scope'] = 'Actual independent editing checkpoint reload; closed final project is verified by rendered pixels, not reactivated for editing.'
    report['final_subdivision_scope'] = 'Editor actually closed and actual working SubD0 persisted on independent save/reload.'
    return target
