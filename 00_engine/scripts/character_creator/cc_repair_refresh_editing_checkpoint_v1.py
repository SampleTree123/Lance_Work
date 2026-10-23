"""Resume loaded AF005, with optional one identical selected-Makeup reentry.

Experimental Assembly Technical. No original project load or role rebuild.
Reuse frozen runner and Normal closure; new editing save/reload proves the
repaired checkpoint, never retrospectively accepts the original failed one.
"""
import importlib
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parent


def private_resume(api):
    path = DIRECTORY / 'cc_resume_refresh_editing_checkpoint_v1.py'
    if api.sha256_file(str(path)) != '72c7c7d0bb9f90616d83b40eaf28791f24cdae82a4af515282313f67b224ae68':
        raise ValueError('Frozen original-checkpoint provenance helper changed')
    spec = importlib.util.spec_from_file_location('_af005_repair_provenance', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normal_entry(api, ui, report, checkpoint):
    widgets = list(api.QtWidgets.QApplication.allWidgets())
    tab = ui.unique_widget(widgets, *ui.APPEARANCE_TAB_SELECTOR)
    page = ui.unique_widget(widgets, *ui.APPEARANCE_PAGE_SELECTOR)
    index = int(tab.indexOf(page))
    if index < 0 or tab.widget(index) is not page:
        raise ValueError('Actual Appearance page membership changed')
    bar = tab.tabBar()
    audit = dict(target_index=index, current_before=int(tab.currentIndex()),
                 entry_enabled=bool(tab.isTabEnabled(index)), page_before=ui.widget_record(page),
                 navigation_performed=False)
    report['checkpoint_repair'].setdefault('normal_entry_checks', []).append(audit)
    checkpoint()
    if tab.isVisible() and tab.isEnabled() and bar.isVisible() and bar.isEnabled() and tab.isTabEnabled(index):
        if int(tab.currentIndex()) != index:
            raw = tab.setCurrentIndex(index)
            audit.update(navigation_performed=True, navigation_return=repr(raw))
            api.QtWidgets.QApplication.processEvents()
    editor = ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])
    audit.update(current_after=int(tab.currentIndex()), page_after=ui.widget_record(page), editor_after=ui.widget_record(editor))
    audit['ready'] = bool(page.isVisible() and page.isEnabled() and editor.isVisible() and editor.isEnabled())
    checkpoint()
    return audit['ready']


def initial(library, output_dir, api):
    resume = private_resume(api)
    report, baseline, native, pixels, _ = resume.initial(library, output_dir, api)
    config = library['checkpoint_repair']
    if config.get('allow_same_selected_makeup_reentry') is not True or config.get('policy') != 'normal_navigation_then_same_makeup_once':
        raise ValueError('Explicit one identical selected-Makeup reentry authorization required')
    for key in ('actual_load_report', 'actual_load_result'):
        resume.verify(config[key], api)
    loaded = api.read_json(config['actual_load_report']['path'])
    terminal = api.read_json(config['actual_load_result']['path'])
    if (terminal['status'] != 'succeeded' or terminal['instance_id'] != config['expected_instance']
            or not loaded.get('success') or loaded['config']['checkpoint']['sha256'] != library['saved_editing_resume']['editing_checkpoint']['sha256']
            or len(loaded['loads']) != 1):
        raise ValueError('One actual original-checkpoint load in new instance required')
    avatars = list(api.RLPy.RScene.GetAvatars() or [])
    selected = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
    if len(avatars) != 1 or str(avatars[0].GetID()) != loaded['avatar']['id'] or selected != [loaded['avatar']['id']]:
        raise ValueError('Still-loaded own AF005 checkpoint identity changed')
    report['checkpoint_repair'] = dict(actual_load_report=config['actual_load_report'], actual_load_result=config['actual_load_result'],
        original_failed_report=library['saved_editing_resume']['failed_report'],
        original_editing_checkpoint=library['saved_editing_resume']['editing_checkpoint'],
        original_checkpoint_layer_persistence_verified=False, makeup_reapplied=False,
        selected_makeup=report['config']['assets']['makeup_eyebrow'], expected_layers=report['layers_before_save'],
        implementation_sha256=api.sha256_file(__file__), source_project_loads_performed=0)
    report.pop('saved_editing_recovery', None)
    return report, baseline, native, pixels, loaded['avatar']['id']


def exact_layers(report, ui, api, label, checkpoint):
    observed, _ = ui.capture(api, ['Eyebrow'])
    report['checkpoint_repair'].setdefault('layer_inventories', {})[label] = observed['table']
    signature = report['layers_before_save'] if label == 'before_save' else report['layers_after_reload']
    expected = report['checkpoint_repair']['expected_layers']
    if observed['table']['row_count'] != 1 or signature != expected:
        checkpoint()
        raise ValueError('Repair requires exactly one original Eyebrow100 row/signature; no delete or tolerance')
    if expected['makeup']['eyebrow']['opacity'] != 100 or expected['makeup']['eyebrow']['slider_opacity'] != 100:
        raise ValueError('Exact AF005 requested Eyebrow100 required')
    if not report['checkpoint_repair']['makeup_reapplied']:
        report['checkpoint_repair']['original_checkpoint_layer_persistence_verified'] = True
    checkpoint()


def run(library, output_dir, log, api):
    if str(DIRECTORY) not in sys.path:
        sys.path.insert(0, str(DIRECTORY))
    resume = private_resume(api)
    resume.validate(library['saved_editing_resume'], library['refresh_assembly'], api)
    normal = importlib.import_module('cc_refresh_skin_normal_closure_v1')
    path = DIRECTORY / 'cc_run_character_refresh_v1.py'
    if api.sha256_file(str(path)) != resume.RUNNER_SHA:
        raise ValueError('Frozen runner changed')
    source = path.read_text(encoding='utf-8-sig')
    first = '    previous_snapshot = None\n    try:\n'
    last = "        if verify_layers:\n            activate_target_editor('activate_editor_for_exact_layers')"
    if source.count(first) != 1 or source.count(last) != 1:
        raise ValueError('Frozen repair anchors changed')
    start, end = source.index(first), source.index(last)
    source = source[:start] + '''    previous_snapshot = None
    try:
        report, baseline, original_support, inherited_pixels, avatar_id = _repair_initial(library, output_dir, api)
        pixel_snapshots.update(inherited_pixels)
        previous_snapshot = baseline
        target = os.path.join(output_dir, 'EDITING_repaired_same_selected_makeup.ccProject')
        checkpoint('normal_appearance_entry_before_optional_makeup_reentry')
        if not _normal_entry(api, ui, report, checkpoint):
            checkpoint('reapply_same_selected_makeup_once_no_skin_or_eye_reload')
            report['checkpoint_repair']['makeup_reapplied'] = True
            report['checkpoint_repair']['makeup_load'] = probe.guarded_load(config['assets']['makeup_eyebrow']['path'],
                'Reenter own exact selected Makeup once', api, report['loads'], checkpoint,
                preserve_modified_materials=True, stage='makeup_preset')
            _normal_entry(api, ui, report, checkpoint)
        gate('after_checkpoint_ui_or_same_makeup_reentry', baseline)
''' + source[end:]
    anchor = "            report['layers_before_save'] = capture_named_layers('before_save_layers')"
    source = source.replace(anchor, anchor + "\n            _exact_layers(report, ui, api, 'before_save', checkpoint)", 1)
    anchor = "            report['layers_after_reload'] = capture_named_layers('after_editing_reload_layers')"
    source = source.replace(anchor, anchor + "\n            _exact_layers(report, ui, api, 'after_reload', checkpoint)", 1)
    namespace = dict(__file__=str(path), __name__='_af005_local_makeup_repair_private',
                     _repair_initial=initial, _normal_entry=normal_entry, _exact_layers=exact_layers)
    exec(compile(source, str(path), 'exec'), namespace)
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
    api.write_json(report, report['summary_path'])
    return report
