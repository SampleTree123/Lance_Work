"""Bounded CC Makeup load probe. No guessed layer APIs or opacity writes.

Run through the BodyFit dispatch API namespace. inspect_current reads widgets;
backup_current saves a new project; load_makeup requires that backup and loads
one independent project plus one hash-bound Makeup eyebrow preset.
"""
import importlib
import os
import sys
import traceback

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'character_refresh_20261018_v1')
MAKEUP_ROOT = r'D:\CharacterCreator_sucai\Reallusion Custom\Makeup\Eyebrow\Makeup & SFX'
KEEP_MODIFIED_TEXT = 'You have changed material or texture settings in Modify panel, do you want to keep the modified result?'


def inside(path, root):
    try:
        path, root = [os.path.normcase(os.path.realpath(p)) for p in (path, root)]
        return os.path.commonpath([path, root]) == root
    except (TypeError, ValueError):
        return False


def reference(ref, api, extension, roots):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
        raise ValueError('Expected path and SHA256 reference')
    path = ref['path']
    if os.path.splitext(path)[1].lower() != extension or not any(inside(path, r) for r in roots):
        raise ValueError('Reference outside allowed roots or wrong extension: ' + path)
    if api.sha256_file(path) != ref.get('sha256'):
        raise ValueError('Reference SHA256 changed: ' + path)
    return path


def validate(config, output_dir, api):
    mode = config.get('mode')
    if mode not in ('inspect_current', 'backup_current', 'load_makeup'):
        raise ValueError('Unsupported Makeup probe mode')
    if not isinstance(config.get('preserve_modified_materials', False), bool):
        raise ValueError('preserve_modified_materials must be an explicit boolean')
    if not inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('Probe requires a new independent child output directory')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse to overwrite or reuse a populated probe output')
    if mode == 'load_makeup':
        reference(config['current_scene_backup'], api, '.ccproject', (RUN_ROOT,))
        source = reference(config['source_project'], api, '.ccproject', (RUN_ROOT, STAGE_ROOT))
        reference(config['makeup_asset'], api, '.ccskingenpreset',
                  (os.path.join(MAKEUP_ROOT, 'Male'), os.path.join(MAKEUP_ROOT, 'Trimmed')))
        reference(config['regions'], api, '.json', (os.path.dirname(__file__),))
        if os.path.normcase(os.path.realpath(source)) == os.path.normcase(os.path.realpath(config['current_scene_backup']['path'])):
            raise ValueError('Independent source must differ from current-scene backup')
    return mode


def status_record(status):
    result = {'returned': status is not None, 'python_type': type(status).__name__, 'repr': str(status)}
    for name in ('IsError', 'GetStatusCode'):
        getter = getattr(status, name, None)
        if callable(getter):
            try:
                value = getter()
                result[name] = bool(value) if name == 'IsError' else str(value)
            except Exception as exc:
                result[name + '_error'] = str(exc)
    return result


def widget_metadata(api):
    """Read Qt getters only; retain parent paths to identify real layer controls."""
    app = api.QtWidgets.QApplication
    records = []
    for widget in app.allWidgets():
        try:
            chain, parent = [], widget
            for _ in range(20):
                if parent is None:
                    break
                chain.append(type(parent).__name__ + ':' + str(parent.objectName()))
                parent = parent.parentWidget()
            row = {'class': type(widget).__name__, 'object_name': str(widget.objectName()),
                   'visible': bool(widget.isVisible()), 'enabled': bool(widget.isEnabled()),
                   'parent_path': '/'.join(reversed(chain))}
            for getter in ('text', 'windowTitle', 'toolTip', 'accessibleName', 'accessibleDescription',
                           'value', 'minimum', 'maximum', 'singleStep', 'decimals', 'currentText', 'isChecked', 'isCheckable'):
                method = getattr(widget, getter, None)
                if callable(method):
                    try:
                        value = method()
                        if isinstance(value, (str, int, float, bool)):
                            row[getter] = value
                    except Exception:
                        pass
            if row['visible'] or any(token in str(row).lower() for token in ('skingen', 'makeup', 'opacity', 'eyebrow')):
                records.append(row)
        except RuntimeError:
            continue  # A transient progress widget may have been destroyed.
    return {'widgets': records, 'count': len(records),
            'policy': 'Qt getters only; no clicking, expanding, selection or value writes'}


def keep_modified_result_matches(snapshot):
    """Only the QMessageBox observed in load_makeup_female_v1; no fuzzy text."""
    if snapshot.get('class_name') != 'QMessageBox' or snapshot.get('window_title') != 'Character Creator 5':
        return False
    for field in ('labels', 'direct_text'):
        texts = {str(text).strip() for text in snapshot.get(field, []) if str(text).strip()}
        if texts != {KEEP_MODIFIED_TEXT}:
            return False
    buttons = snapshot.get('buttons', [])
    return (len(buttons) == 3
        and sorted(str(button.get('text')) for button in buttons) == ['&No', '&Yes', 'Cancel']
        and all(button.get('class_name') == 'QPushButton' and button.get('visible') is True
                and button.get('enabled') is True and button.get('checkable') is False for button in buttons))


UNDO_WARNING_TEXT = 'Failed to record undo/redo step. Undo manager will restart.'


def undo_warning_matches(snapshot):
    """Deduplicate the same QMessageBox text exposed by QLabel and text()."""
    normalize = lambda text: ' '.join(str(text).split())
    if snapshot.get('class_name') != 'QMessageBox' or snapshot.get('window_title') != 'Character Creator 5':
        return False
    texts = {normalize(text) for field in ('labels', 'direct_text')
             for text in snapshot.get(field, []) if normalize(text)}
    if texts != {UNDO_WARNING_TEXT}:
        return False
    buttons = snapshot.get('buttons', [])
    return (len(buttons) == 1 and buttons[0].get('class_name') == 'QPushButton'
        and buttons[0].get('text') == 'OK' and buttons[0].get('visible') is True
        and buttons[0].get('enabled') is True and buttons[0].get('checkable') is False)


def exact_undo_warning_button(widget, api, snapshot):
    if not undo_warning_matches(snapshot):
        return None
    buttons = api.exact_dialog_buttons(widget, 'OK', checkable=False)
    return buttons[0] if len(buttons) == 1 and str(buttons[0].text()) == 'OK' else None


def guarded_load(path, label, api, receipt, checkpoint, preserve_modified_materials=False, stage=None):
    """Generic LoadFile; reuse exact Undo/progress recognizers, reject other modals."""
    keep_allowed = (preserve_modified_materials is True and stage == 'makeup_preset'
                    and label == 'Load one Makeup preset' and os.path.splitext(path)[1].lower() == '.ccskingenpreset')
    guard = {'path': path, 'label': label, 'observed_dialogs': [], 'undo_count': 0,
             'keep_modified_materials': {'allowed': keep_allowed, 'clicked_count': 0},
             'unknown_dialog': None, 'policy': 'Exact Undo; explicitly opted-in exact keep-modified Yes only at Makeup preset stage; unknown modal cancelled'}
    receipt.append(guard)
    timer = api.QtCore.QTimer()
    timer.setInterval(100)
    handled = set()

    def inspect():
        widget = api.QtWidgets.QApplication.activeModalWidget()
        if widget is None or not widget.isVisible():
            return
        snapshot = api.cc_dialog_snapshot(widget)
        snapshot.pop('normalized_text', None)
        if snapshot not in guard['observed_dialogs']:
            guard['observed_dialogs'].append(snapshot)
            checkpoint()
        if id(widget) in handled:
            return
        if api.is_known_cc_progress_dialog(widget):
            return
        button = exact_undo_warning_button(widget, api, snapshot)
        if button is not None:
            handled.add(id(widget))
            guard['undo_count'] += 1
            button.click()
            return
        if keep_allowed and keep_modified_result_matches(snapshot):
            yes_buttons = api.exact_dialog_buttons(widget, 'Yes', checkable=False)
            if len(yes_buttons) == 1 and str(yes_buttons[0].text()) == '&Yes':
                handled.add(id(widget))
                guard['keep_modified_materials']['clicked_count'] += 1
                guard['keep_modified_materials']['matched_snapshot'] = snapshot
                checkpoint()
                yes_buttons[0].click()
                return
        handled.add(id(widget))
        guard['unknown_dialog'] = snapshot
        checkpoint()
        buttons = api.exact_dialog_buttons(widget, 'Cancel', checkable=False)
        if len(buttons) == 1:
            buttons[0].click()
        elif isinstance(widget, api.QtWidgets.QDialog):
            widget.reject()
        else:
            # Closing a modal is a refusal, never pressing its default action.
            widget.close()

    timer.timeout.connect(inspect)
    timer.start()
    try:
        raw = api.RLPy.RFileIO.LoadFile(path)
        guard['raw_status'] = status_record(raw)
        checkpoint()
    finally:
        timer.stop()
    if guard['unknown_dialog'] is not None:
        raise ValueError('Unknown modal refused; inspect recorded dialog metadata')
    if raw is None or not callable(getattr(raw, 'IsError', None)):
        raise ValueError('LoadFile did not return an inspectable RStatus')
    guard['checked_status'] = api.checked(label, raw)
    return guard


def run(library, output_dir, log, api):
    config = library['makeup_probe']
    mode = validate(config, output_dir, api)
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'makeup_probe_report.json')
    report = {'schema_version': 1, 'diagnostic_mode': 'makeup_probe', 'mode': mode,
              'success': False, 'config': config, 'started_at': api.now(),
              'loads': [], 'summary_path': report_path, 'opacity_written': False}

    def checkpoint(phase=None):
        if phase:
            report['phase'] = phase
            log('Makeup probe: ' + phase)
        report['updated_at'] = api.now()
        api.write_json(report, report_path)

    def avatar():
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected exactly one avatar')
        return avatars[0]

    def save_new(name):
        target = os.path.join(output_dir, name + '.ccProject')
        if os.path.exists(target):
            raise ValueError('Refuse to overwrite project')
        raw = api.RLPy.RFileIO.SaveProject(target)
        report[name + '_save_status'] = status_record(raw)
        checkpoint()
        if raw is None or not callable(getattr(raw, 'IsError', None)):
            raise ValueError('SaveProject did not return an inspectable RStatus')
        api.checked('Save independent ' + name, raw)
        report[name] = {'path': target, 'sha256': api.sha256_file(target), 'bytes': os.path.getsize(target)}
        checkpoint()

    try:
        checkpoint('inspect_current')
        report['widgets_before'] = widget_metadata(api)
        report['avatar_names_before'] = [str(a.GetName()) for a in (api.RLPy.RScene.GetAvatars() or [])]
        if mode == 'backup_current':
            checkpoint('backup_current_scene')
            save_new('current_scene_backup')
        elif mode == 'load_makeup':
            checkpoint('load_independent_source')
            guarded_load(config['source_project']['path'], 'Load independent Makeup source', api, report['loads'], checkpoint)
            current = avatar()
            source_avatar_id = str(current.GetID())
            report['source_avatar_id'] = source_avatar_id
            directory = os.path.dirname(__file__)
            if directory not in sys.path:
                sys.path.insert(0, directory)
            capture = importlib.import_module('cc_capture_assembly_geometry_v1')
            invariants = importlib.import_module('cc_assembly_geometry_invariants_v1')
            regions = invariants.load_regions(config['regions']['path'])
            before = capture.capture_body_snapshot(current, api=api, include_world=False,
                        output_path=os.path.join(output_dir, 'before_geometry.json'))
            report['material_before'] = api.avatar_material_fingerprint(current)
            checkpoint('load_one_makeup_preset')
            api.RLPy.RScene.SelectObject(current)
            guarded_load(config['makeup_asset']['path'], 'Load one Makeup preset', api, report['loads'], checkpoint,
                         preserve_modified_materials=config.get('preserve_modified_materials', False), stage='makeup_preset')
            current = avatar()
            report['avatar_identity_preserved'] = str(current.GetID()) == source_avatar_id
            after = capture.capture_body_snapshot(current, api=api, include_world=False,
                        output_path=os.path.join(output_dir, 'after_geometry.json'))
            report['material_after'] = api.avatar_material_fingerprint(current)
            report['geometry'] = invariants.compare_assembly_snapshots(before, after, regions,
                space='local', tolerance_mm=invariants.DEFAULT_TOLERANCE_MM, allowances=[])
            report['widgets_after'] = widget_metadata(api)
            # Read the real table without changing category, selection or values.
            try:
                controls = importlib.import_module('cc_skingen_controls_v1')
                table = controls.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *controls.SELECTORS['table'])
                report['skingen_table_after'] = {'success': True, 'table': controls.table_record(table, api)}
            except Exception as table_exc:
                report['skingen_table_after'] = {'success': False, 'error': str(table_exc)}
            report['source_unchanged'] = api.sha256_file(config['source_project']['path']) == config['source_project']['sha256']
            checkpoint('captured_after_load')
            if not report['geometry']['passed'] or not report['source_unchanged'] or not report['avatar_identity_preserved']:
                raise ValueError('Geometry or immutable source guard failed; candidate not saved')
            save_new('makeup_candidate')
        report['success'] = True
        checkpoint('completed')
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        checkpoint('failed')
    return report
