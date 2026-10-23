"""AF005 bounded normal UI entry after each actual editing reload.

Experimental Assembly Technical. Reuses the immutable runner and Normal/full
closure. A real Qt mouse click navigates Appearance; one own preset invocation
per runtime avatar may only cancel the evidenced Add/Replace question. No layer,
material, geometry, opacity or enable-flag exception is introduced.
"""
import importlib
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parent
REPAIR_SHA = '209cbae9ea21a539498edc5c9c6ea81aef7fc71a50081b86d6d34503bc31c37c'
QUESTION = 'Would you like to add a new layer or replace the current layer?'


def cancel_question(snapshot):
    texts = {str(t).strip() for key in ('labels', 'direct_text') for t in snapshot.get(key, []) if str(t).strip()}
    buttons = snapshot.get('buttons', [])
    return (snapshot.get('class_name') == 'QMessageBox'
            and snapshot.get('window_title') == 'Character Creator 5' and texts == {QUESTION}
            and len(buttons) == 3 and {b.get('text') for b in buttons} == {'Add', 'Replace', 'Cancel'}
            and all(b.get('class_name') == 'QPushButton' and b.get('visible') is True
                    and b.get('enabled') is True and b.get('checkable') is False for b in buttons))


def click_appearance(api, ui, audit):
    """Deliver a normal Qt mouse event; never emit a tab signal or enable UI."""
    tab = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.APPEARANCE_TAB_SELECTOR)
    page = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.APPEARANCE_PAGE_SELECTOR)
    index = int(tab.indexOf(page))
    if index < 0 or tab.widget(index) is not page:
        raise ValueError('Exact Appearance tab membership changed')
    bar = tab.tabBar()
    audit.update(index=index, current_before=int(tab.currentIndex()), entry_enabled=bool(tab.isTabEnabled(index)))
    if not (tab.isVisible() and tab.isEnabled() and bar.isVisible() and bar.isEnabled() and tab.isTabEnabled(index)):
        raise ValueError('Normal Appearance tab is unavailable; no forced navigation')
    qt_test = importlib.import_module('PySide2.QtTest')
    point = bar.tabRect(index).center()
    qt_test.QTest.mouseClick(bar, api.QtCore.Qt.LeftButton, api.QtCore.Qt.NoModifier, point)
    api.QtWidgets.QApplication.processEvents()
    audit.update(action='QTest.mouseClick actual QTabBar rectangle', point=[point.x(), point.y()],
                 current_after=int(tab.currentIndex()))
    if int(tab.currentIndex()) != index:
        raise ValueError('Normal Appearance mouse click did not navigate')
    makeup = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['makeup'])
    audit['makeup_before'] = ui.widget_record(makeup)
    if makeup.isVisible() and makeup.isEnabled():
        audit['makeup_click'] = ui.select_makeup(makeup)
        api.QtWidgets.QApplication.processEvents()


def ready(api, ui):
    widgets = list(api.QtWidgets.QApplication.allWidgets())
    editor = ui.unique_widget(widgets, *ui.SELECTORS['editor'])
    page = ui.unique_widget(widgets, *ui.APPEARANCE_PAGE_SELECTOR)
    return bool(editor.isVisible() and editor.isEnabled() and page.isVisible() and page.isEnabled()), {
        'editor': ui.widget_record(editor), 'page': ui.widget_record(page)}


def cancel_only_reentry(asset, api, report, checkpoint, audit):
    """Unknown dialogs are refused; the exact observed question gets Cancel only."""
    if api.sha256_file(asset['path']) != asset['sha256']:
        raise ValueError('Own selected Makeup asset changed')
    receipt = dict(path=asset['path'], sha256=asset['sha256'], label='Own Makeup entry; exact Add/Replace Cancel only',
                   observed_dialogs=[], cancel_count=0, add_count=0, replace_count=0, unknown_dialog=None)
    report['loads'].append(receipt)
    audit['cancel_only_reentry'] = receipt
    timer = api.QtCore.QTimer()
    timer.setInterval(100)
    handled = set()

    def inspect():
        widget = api.QtWidgets.QApplication.activeModalWidget()
        if widget is None or not widget.isVisible():
            return
        snapshot = api.cc_dialog_snapshot(widget)
        snapshot.pop('normalized_text', None)
        if snapshot not in receipt['observed_dialogs']:
            receipt['observed_dialogs'].append(snapshot)
            checkpoint()
        if api.is_known_cc_progress_dialog(widget) or id(widget) in handled:
            return
        handled.add(id(widget))
        buttons = api.exact_dialog_buttons(widget, 'Cancel', checkable=False)
        if cancel_question(snapshot) and len(buttons) == 1 and str(buttons[0].text()) == 'Cancel' and receipt['cancel_count'] == 0:
            receipt['cancel_count'] += 1
            checkpoint()
            buttons[0].click()
            return
        receipt['unknown_dialog'] = snapshot
        checkpoint()
        if len(buttons) == 1:
            buttons[0].click()
        elif isinstance(widget, api.QtWidgets.QDialog):
            widget.reject()
        else:
            widget.close()

    timer.timeout.connect(inspect)
    timer.start()
    try:
        raw = api.RLPy.RFileIO.LoadFile(asset['path'])
        import cc_makeup_probe_v1 as probe
        receipt['raw_status'] = probe.status_record(raw)
        checkpoint()
    finally:
        timer.stop()
    if receipt['unknown_dialog'] is not None or receipt['cancel_count'] != 1:
        raise ValueError('Reentry must cancel exactly one evidenced Add/Replace question; no other confirmation')
    receipt['checked_status'] = api.checked('Own Makeup exact-Cancel entry', raw)
    receipt['application_accepted'] = False


def bounded_entry(api, ui, report, checkpoint, avatar_id, label):
    avatars = list(api.RLPy.RScene.GetAvatars() or [])
    if len(avatars) != 1 or str(avatars[0].GetID()) != str(avatar_id):
        raise ValueError('Own runtime avatar changed before normal editor entry')
    recovery = report['checkpoint_repair']
    audit = dict(phase=label, avatar_id=str(avatar_id), normal_click={})
    recovery['entry_audits'].append(audit)
    checkpoint('bounded_normal_editor_entry_' + label)
    click_appearance(api, ui, audit['normal_click'])
    is_ready, audit['after_normal_click'] = ready(api, ui)
    if not is_ready:
        key = str(avatar_id)
        if key in recovery['reentry_attempted_avatar_ids']:
            raise ValueError('Only one own exact-Cancel reentry per actual reload allowed')
        recovery['reentry_attempted_avatar_ids'].append(key)
        checkpoint()
        cancel_only_reentry(report['config']['assets']['makeup_eyebrow'], api, report, checkpoint, audit)
        click_appearance(api, ui, audit.setdefault('normal_click_after_cancel', {}))
        is_ready, audit['after_exact_cancel'] = ready(api, ui)
    audit['ready'] = is_ready
    checkpoint()
    if not is_ready:
        raise ValueError('Editor still unavailable after one bounded normal entry; no retry')


def exact_layers(report, ui, api, label, checkpoint):
    capture, _ = ui.capture(api, ['Eyebrow'])
    report['checkpoint_repair'].setdefault('layer_inventories', {})[label] = capture['table']
    signature = report['layers_before_save'] if label == 'before_save' else report['layers_after_reload']
    expected = report['checkpoint_repair']['expected_layers']
    checkpoint()
    if capture['table']['row_count'] != 1 or signature != expected:
        raise ValueError('Exactly one original Eyebrow100 with original flags required; no layer deletion')


def transformed_runner(source):
    first = '    previous_snapshot = None\n    try:\n'
    last = "        if verify_layers:\n            activate_target_editor('activate_editor_for_exact_layers')"
    if source.count(first) != 1 or source.count(last) != 1:
        raise ValueError('Frozen resume anchors changed')
    start, end = source.index(first), source.index(last)
    source = source[:start] + '''    previous_snapshot = None
    try:
        report, baseline, original_support, inherited_pixels, editing_source = _resume_initial(library, output_dir, api)
        pixel_snapshots.update(inherited_pixels)
        previous_snapshot = baseline
        target = os.path.join(output_dir, 'EDITING_bounded_normal_entry.ccProject')
        checkpoint('load_own_original_editing_checkpoint_once')
        probe.guarded_load(editing_source, 'Load own immutable editing checkpoint for bounded entry', api, report['loads'], checkpoint)
        report['checkpoint_repair']['original_checkpoint_load_count'] = 1
        avatar_id = str(avatar().GetID())
        checkpoint()
        gate('after_own_editing_checkpoint_load', baseline)
''' + source[end:]
    anchor = "        report.setdefault('editor_activation_audits', []).append(audit)\n"
    if source.count(anchor) != 1:
        raise ValueError('Frozen readiness wrapper anchor changed')
    source = source.replace(anchor, anchor + "        _bounded_entry(api, ui, report, checkpoint, avatar_id, label)\n", 1)
    for field, label in [('layers_before_save', 'before_save'), ('layers_after_reload', 'after_reload')]:
        anchor = "            report['{}'] = capture_named_layers('{}')".format(field, 'before_save_layers' if label == 'before_save' else 'after_editing_reload_layers')
        if source.count(anchor) != 1:
            raise ValueError('Frozen actual layer-read anchor changed')
        source = source.replace(anchor, anchor + "\n            _exact_layers(report, ui, api, {!r}, checkpoint)".format(label), 1)
    return source


def run(library, output_dir, log, api):
    if str(DIRECTORY) not in sys.path:
        sys.path.insert(0, str(DIRECTORY))
    repair_path = DIRECTORY / 'cc_repair_refresh_editing_checkpoint_v1.py'
    if api.sha256_file(str(repair_path)) != REPAIR_SHA:
        raise ValueError('Frozen repair provenance changed')
    spec = importlib.util.spec_from_file_location('_af005_bounded_repair_provenance', repair_path)
    repair = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repair)
    resume = repair.private_resume(api)
    config = library['bounded_editor_entry']
    if config.get('policy') != 'normal_mouse_click_then_own_preset_exact_cancel_once_per_reload' or config.get('max_reentry_per_runtime_avatar') != 1:
        raise ValueError('Explicit bounded per-reload entry policy required')
    resume.validate(library['saved_editing_resume'], library['refresh_assembly'], api)
    for pin in config['prior_recovery_evidence']:
        resume.verify(pin, api)
    normal = importlib.import_module('cc_refresh_skin_normal_closure_v1')
    runner_path = DIRECTORY / 'cc_run_character_refresh_v1.py'
    if api.sha256_file(str(runner_path)) != resume.RUNNER_SHA:
        raise ValueError('Frozen full runner changed')

    def initial(library, output, api):
        report, baseline, native, pixels, editing = resume.initial(library, output, api)
        expected = report['layers_before_save']
        if expected != {'makeup': {'eyebrow': {'opacity': 100, 'slider_opacity': 100, 'row_enable_flags_uninterpreted': False}}}:
            raise ValueError('Exact original AF005 Eyebrow100 signature required')
        report['checkpoint_repair'] = dict(expected_layers=expected, entry_audits=[], reentry_attempted_avatar_ids=[],
            original_checkpoint_load_count=0, policy=config['policy'], implementation_sha256=api.sha256_file(__file__),
            prior_recovery_evidence=config['prior_recovery_evidence'], original_failure_retained=True,
            add_or_replace_prohibited=True, changes_accepted_only_after_full_original_gates=True)
        return report, baseline, native, pixels, editing

    namespace = dict(__file__=str(runner_path), __name__='_af005_bounded_normal_entry_private_runner',
                     _resume_initial=initial, _bounded_entry=bounded_entry, _exact_layers=exact_layers)
    exec(compile(transformed_runner(runner_path.read_text(encoding='utf-8-sig')), str(runner_path), 'exec'), namespace)
    class Imports:
        def __getattr__(self, name):
            return getattr(importlib, name)
        def import_module(self, name):
            if name == 'cc_refresh_closed_assembly_v1':
                return SimpleNamespace(finish=normal.finish, __file__=normal.__file__)
            return importlib.import_module(name)
    namespace['importlib'] = Imports()
    report = namespace['run'](library, output_dir, log, api)
    resume.verify(library['saved_editing_resume']['failed_report'], api)
    resume.verify(library['saved_editing_resume']['editing_checkpoint'], api)
    return report
