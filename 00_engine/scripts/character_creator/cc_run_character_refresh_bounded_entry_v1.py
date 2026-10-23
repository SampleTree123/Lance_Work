"""Opt-in normal PRELASH with the proven bounded entry before activation.

Only a private runner is transformed. Original save/reload, wait, geometry,
layers, pixels and four-Normal closure remain unchanged. Not a recovery driver.
"""
import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parent
POLICY = 'normal_mouse_click_then_own_preset_exact_cancel_once_per_reload'
SCHEMA = 'cfd40_prelash_bounded_entry_v1'
FROZEN = {
    'cc_run_character_refresh_v1': '80c6c4c479dbdbb158a24dd830f76859b4e3d6727b13e7125c848ea2bfb02a72',
    'cc_refresh_skin_normal_closure_v1': 'bdcb52b4485e1b85bc75e52c0de44d51c16f2438f0c8c0e60577a1cde32be322',
    'cc_repair_refresh_editing_checkpoint_v3': 'eea834e4e1c7bc4e5546e4c6be056ebcc06ef4864ded58104a951340a76008e0',
}


def file_record(path, api):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': api.sha256_file(str(path)), 'bytes': path.stat().st_size}


def private_module(name):
    path = DIRECTORY / (name + '.py')
    spec = importlib.util.spec_from_file_location('_bounded_prelash_private_' + name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def validate(library, api):
    config = library['refresh_assembly']
    control = library.get('prelash_bounded_entry', {})
    if (library.get('diagnostic_mode') != 'character_refresh_normals' or control.get('first_run') is not True
            or control.get('schema') != SCHEMA or control.get('policy') != POLICY
            or type(control.get('max_reentry_per_runtime_avatar')) is not int
            or control['max_reentry_per_runtime_avatar'] != 1
            or control.get('source_project') != config['source_project']
            or control.get('makeup_asset') != config['assets']['makeup_eyebrow']):
        raise ValueError('Explicit same-source/same-Makeup bounded PRELASH binding required')
    if any(key in library for key in ('saved_editing_resume', 'bounded_editor_entry')):
        raise ValueError('First-run bounded PRELASH cannot bind a failed checkpoint recovery')
    if (config.get('redness_policy') != 'excluded_by_user' or config.get('include_redness_layers') is not False
            or any(config.get(key) is not True for key in (
                'verify_layer_persistence', 'capture_pixel_evidence', 'finalize_editor_closed',
                'restore_four_skin_normals_after_editor_close'))):
        raise ValueError('Original no-redness layers/pixels/editor-close/Normal gates required')
    wrapper = file_record(__file__, api)
    expected = control.get('implementation', {})
    if (Path(expected.get('path', '')).resolve() != Path(wrapper['path'])
            or expected.get('sha256') != wrapper['sha256']
            or ('bytes' in expected and expected['bytes'] != wrapper['bytes'])):
        raise ValueError('Exact actual bounded runner implementation pin required')
    sources = {}
    for name, digest in FROZEN.items():
        record = file_record(DIRECTORY / (name + '.py'), api)
        if record['sha256'] != digest:
            raise ValueError('Frozen bounded PRELASH source changed: ' + name)
        sources[name] = record
    return {'wrapper': wrapper, 'sources': sources, 'source_project': config['source_project'],
            'makeup_asset': config['assets']['makeup_eyebrow']}


def transform(source):
    # Exact two insertions; never replace/remove the original operation or wait.
    anchor = '    def checkpoint(phase=None):\n'
    activation = "        report.setdefault('editor_activation_audits', []).append(audit)\n"
    if source.count(anchor) != 1 or source.count(activation) != 1:
        raise ValueError('Frozen report/activation injection anchors changed')
    source = source.replace(anchor, '    _initialize_bounded_report(report)\n\n' + anchor, 1)
    return source.replace(activation, activation +
        '        _before_bounded_activation(api, ui, report, checkpoint, avatar_id, label)\n', 1)


def initialize_report(report, provenance):
    report['base_runner_implementation_sha256'] = report['implementation_sha256']
    report['implementation_sha256'] = provenance['wrapper']['sha256']
    report['execution_variant'] = 'preemptive_bounded_editor_entry_not_checkpoint_recovery'
    report['runtime_wrapper'] = {'schema': SCHEMA, 'first_run': True, 'implementation': provenance['wrapper'],
        'source_pins': provenance['sources'],
        'private_runner_injections': ['initialize_report', 'before_activate_target_editor_operation']}
    report['bounded_editor_entry'] = {
        'schema': SCHEMA, 'policy': POLICY, 'max_reentry_per_runtime_avatar': 1,
        'entry_audits': [], 'reentry_attempted_avatar_ids': [],
        'provenance': provenance, 'original_sources_unchanged_on_disk': True,
        'runner_executed_with_private_injections': True,
        'source_pins_verified_after_run': False,
        'scope': 'Preemptive normal entry only; original wait and all downstream gates retained. No recipe/visual acceptance.'}


def before_activation(core, api, ui, report, checkpoint, avatar_id, label):
    # The proven helper's legacy field name stays in this shallow view only.
    # Its audit and loads objects are shared with the real honest report.
    view = dict(report)
    view['checkpoint_repair'] = report['bounded_editor_entry']
    return core.bounded_entry(api, ui, view, checkpoint, avatar_id, label)


def run(library, output_dir, log, api):
    provenance = validate(library, api)
    core = private_module('cc_repair_refresh_editing_checkpoint_v3')
    normal = private_module('cc_refresh_skin_normal_closure_v1')
    runner_path = DIRECTORY / 'cc_run_character_refresh_v1.py'
    namespace = dict(__file__=str(runner_path), __name__='_bounded_prelash_private_runner',
        _initialize_bounded_report=lambda report: initialize_report(report, provenance),
        _before_bounded_activation=lambda *args: before_activation(core, *args))
    exec(compile(transform(runner_path.read_text(encoding='utf-8-sig')), str(runner_path), 'exec'), namespace)
    class Imports:
        def __getattr__(self, name):
            return getattr(importlib, name)
        def import_module(self, name):
            if name == 'cc_refresh_closed_assembly_v1':
                return SimpleNamespace(finish=normal.finish, __file__=normal.__file__)
            return importlib.import_module(name)
    namespace['importlib'] = Imports()
    report = namespace['run'](library, output_dir, log, api)
    # No additional reload/save or application operation is introduced.
    try:
        after = validate(library, api)
        if after != provenance:
            raise ValueError('Bounded PRELASH provenance changed during execution')
    except Exception as error:
        report['success'] = False
        report['status'] = 'failed_bounded_entry_source_validation'
        report['runtime_wrapper_validation_error'] = str(error)
        report.setdefault('error', {'message': str(error)})
        report['bounded_editor_entry']['original_sources_unchanged_on_disk'] = False
    else:
        report['bounded_editor_entry']['source_pins_verified_after_run'] = True
    api.write_json(report, report['summary_path'])
    return report
