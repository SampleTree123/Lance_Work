"""Offline safety checks for a probe that must never guess SkinGen APIs."""
import hashlib
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('makeup_probe', Path(__file__).parents[1] / 'cc_makeup_probe_v1.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Status:
    def __init__(self, error=False):
        self.error = error

    def IsError(self):
        return self.error

    def GetStatusCode(self):
        return 'ERROR' if self.error else 'OK'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / 'runs'
    root.mkdir()
    monkeypatch.setattr(MODULE, 'RUN_ROOT', str(root))
    calls = []

    def forbidden(*args):
        calls.append(args)
        raise AssertionError('Read-only mode attempted CC mutation')

    api = SimpleNamespace(now=lambda: 'test', sha256_file=sha,
        write_json=lambda value, path: Path(path).write_text(json.dumps(value), encoding='utf-8'),
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(allWidgets=lambda: [])),
        RLPy=SimpleNamespace(RScene=SimpleNamespace(GetAvatars=lambda: []),
                            RFileIO=SimpleNamespace(LoadFile=forbidden, SaveProject=forbidden)))
    return root, api, calls


def test_inspection_does_not_call_load_save_or_scene_selection(env):
    root, api, calls = env
    result = MODULE.run({'makeup_probe': {'mode': 'inspect_current'}}, str(root / 'inspect'), lambda text: None, api)
    assert result['success'] and result['opacity_written'] is False
    assert calls == []


def test_rejects_populated_output_before_any_cc_call(env):
    root, api, calls = env
    output = root / 'existing'
    output.mkdir()
    (output / 'keep.txt').write_text('keep')
    with pytest.raises(ValueError, match='overwrite'):
        MODULE.run({'makeup_probe': {'mode': 'backup_current'}}, str(output), lambda text: None, api)
    assert calls == []


def test_rejects_changed_backup_before_source_or_asset_load(env):
    root, api, calls = env
    backup = root / 'backup.ccProject'
    backup.write_bytes(b'changed')
    config = {'mode': 'load_makeup', 'current_scene_backup': {'path': str(backup), 'sha256': '0' * 64}}
    with pytest.raises(ValueError, match='SHA256'):
        MODULE.validate(config, str(root / 'new'), api)
    assert calls == []


def test_unknown_modal_is_rejected_without_default_button_acceptance():
    events = []
    timer = SimpleNamespace(setInterval=lambda value: None, start=lambda: None, stop=lambda: None)
    timer.timeout = SimpleNamespace(connect=lambda callback: events.append(callback))

    class Dialog:
        def isVisible(self):
            return True

        def reject(self):
            events.append('rejected')

    dialog = Dialog()

    def load(path):
        events[0]()
        return Status()

    api = SimpleNamespace(QtCore=SimpleNamespace(QTimer=lambda: timer),
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(activeModalWidget=lambda: dialog), QDialog=Dialog),
        cc_dialog_snapshot=lambda widget: {'window_title': 'Unexpected palette'},
        exact_undo_warning_button=lambda widget: None, is_known_cc_progress_dialog=lambda widget: False,
        exact_dialog_buttons=lambda *args, **kwargs: [],
        RLPy=SimpleNamespace(RFileIO=SimpleNamespace(LoadFile=load)),
        checked=lambda *args: pytest.fail('Unknown modal must not pass checked'))
    receipt = []
    with pytest.raises(ValueError, match='Unknown modal'):
        MODULE.guarded_load('preset', 'test', api, receipt, lambda: None)
    assert events[-1] == 'rejected'
    assert receipt[0]['raw_status']['GetStatusCode'] == 'OK'
    assert receipt[0]['unknown_dialog']['window_title'] == 'Unexpected palette'


def test_error_status_is_recorded_before_checker_raises():
    timer = SimpleNamespace(timeout=SimpleNamespace(connect=lambda callback: None),
        setInterval=lambda value: None, start=lambda: None, stop=lambda: None)

    def checked(label, status):
        assert status.IsError()
        raise ValueError('SDK rejected preset')

    api = SimpleNamespace(QtCore=SimpleNamespace(QTimer=lambda: timer),
        RLPy=SimpleNamespace(RFileIO=SimpleNamespace(LoadFile=lambda path: Status(True))), checked=checked)
    receipt = []
    with pytest.raises(ValueError, match='SDK rejected'):
        MODULE.guarded_load('preset', 'test', api, receipt, lambda: None)
    assert receipt[0]['raw_status']['IsError'] is True
    assert receipt[0]['raw_status']['GetStatusCode'] == 'ERROR'


def keep_dialog_snapshot():
    return {'class_name': 'QMessageBox', 'window_title': 'Character Creator 5',
        'labels': [MODULE.KEEP_MODIFIED_TEXT, ' '], 'direct_text': [MODULE.KEEP_MODIFIED_TEXT, ' '],
        'buttons': [{'class_name': 'QPushButton', 'text': text, 'visible': True,
            'enabled': True, 'checkable': False} for text in ('&Yes', '&No', 'Cancel')]}


def undo_dialog_snapshot():
    return {'class_name': 'QMessageBox', 'window_title': 'Character Creator 5',
        'labels': [MODULE.UNDO_WARNING_TEXT, ' '], 'direct_text': [MODULE.UNDO_WARNING_TEXT, ' '],
        'buttons': [{'class_name': 'QPushButton', 'text': 'OK', 'visible': True,
            'enabled': True, 'checkable': False}]}


def test_undo_warning_deduplicates_real_qmessagebox_text_and_ignores_blank_whitespace():
    snapshot = undo_dialog_snapshot()
    # This real v4 shape yields two matches in the former combined-list counter.
    assert sum(text.strip() == MODULE.UNDO_WARNING_TEXT for field in ('labels', 'direct_text')
        for text in snapshot[field]) == 2
    assert MODULE.undo_warning_matches(snapshot)
    snapshot['direct_text'] = [' \n' + MODULE.UNDO_WARNING_TEXT.replace(' ', '\n') + '\t', ' \t ']
    assert MODULE.undo_warning_matches(snapshot)


@pytest.mark.parametrize('field,value', [
    ('class_name', 'QDialog'), ('window_title', 'Other application'),
    ('direct_text', ['Failed to record undo/redo step. Undo manager will restart!', ' ']),
    ('labels', [MODULE.UNDO_WARNING_TEXT, 'Additional warning']),
    ('direct_text', ['No character picked.']), ('labels', []),
])
def test_undo_warning_refuses_other_or_extra_text(field, value):
    snapshot = undo_dialog_snapshot()
    snapshot[field] = value
    if field == 'labels' and value == []:
        snapshot['direct_text'] = []
    assert not MODULE.undo_warning_matches(snapshot)


@pytest.mark.parametrize('change', ['duplicate', 'disabled', 'hidden', 'checkable', 'other_text', 'other_class'])
def test_undo_warning_requires_one_exact_available_ok(change):
    snapshot = undo_dialog_snapshot()
    if change == 'duplicate':
        snapshot['buttons'].append(copy.deepcopy(snapshot['buttons'][0]))
    else:
        key, value = {'disabled': ('enabled', False), 'hidden': ('visible', False),
            'checkable': ('checkable', True), 'other_text': ('text', 'Continue'),
            'other_class': ('class_name', 'QToolButton')}[change]
        snapshot['buttons'][0][key] = value
    assert not MODULE.undo_warning_matches(snapshot)


def test_real_undo_warning_during_load_clicks_only_exact_ok():
    callbacks, clicks = [], []
    timer = SimpleNamespace(timeout=SimpleNamespace(connect=lambda callback: callbacks.append(callback)),
        setInterval=lambda value: None, start=lambda: None, stop=lambda: None)
    dialog = SimpleNamespace(isVisible=lambda: True)
    ok = SimpleNamespace(text=lambda: 'OK', click=lambda: clicks.append('exact_ok'))

    def load(path):
        callbacks[0]()
        return Status()

    api = SimpleNamespace(QtCore=SimpleNamespace(QTimer=lambda: timer),
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(activeModalWidget=lambda: dialog)),
        cc_dialog_snapshot=lambda widget: undo_dialog_snapshot(), is_known_cc_progress_dialog=lambda widget: False,
        exact_dialog_buttons=lambda widget, text, **kwargs: [ok] if text == 'OK' else [],
        RLPy=SimpleNamespace(RFileIO=SimpleNamespace(LoadFile=load)), checked=lambda *args: {'is_error': False})
    receipt = []
    MODULE.guarded_load('source.ccProject', 'Load independent refresh source', api, receipt, lambda: None)
    assert clicks == ['exact_ok']
    assert receipt[0]['undo_count'] == 1 and receipt[0]['unknown_dialog'] is None


def test_keep_modified_matcher_accepts_only_recorded_dialog():
    snapshot = keep_dialog_snapshot()
    assert MODULE.keep_modified_result_matches(snapshot)
    mutations = [
        ('window_title', 'Other application'), ('class_name', 'QDialog'),
        ('direct_text', ['Keep modified result?']), ('labels', [MODULE.KEEP_MODIFIED_TEXT, 'Additional warning']),
        ('buttons', snapshot['buttons'][:2]),
    ]
    for key, value in mutations:
        changed = copy.deepcopy(snapshot)
        changed[key] = value
        assert not MODULE.keep_modified_result_matches(changed)
    changed = copy.deepcopy(snapshot)
    changed['buttons'][0]['enabled'] = False
    assert not MODULE.keep_modified_result_matches(changed)


@pytest.mark.parametrize('opt_in,stage,label,accepted', [
    (True, 'makeup_preset', 'Load one Makeup preset', True),
    (False, 'makeup_preset', 'Load one Makeup preset', False),
    (True, 'source_project', 'Load independent Makeup source', False),
    (True, None, 'Load one Makeup preset', False),
    ('true', 'makeup_preset', 'Load one Makeup preset', False),
])
def test_keep_modified_yes_requires_opt_in_and_exact_preset_stage(opt_in, stage, label, accepted):
    events, callbacks = [], []
    timer = SimpleNamespace(timeout=SimpleNamespace(connect=lambda callback: callbacks.append(callback)),
        setInterval=lambda value: None, start=lambda: None, stop=lambda: None)

    class Dialog:
        def isVisible(self):
            return True

    dialog = Dialog()
    yes = SimpleNamespace(text=lambda: '&Yes', click=lambda: events.append('yes'))
    cancel = SimpleNamespace(click=lambda: events.append('cancel'))

    def load(path):
        callbacks[0]()
        return Status()

    api = SimpleNamespace(QtCore=SimpleNamespace(QTimer=lambda: timer),
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(activeModalWidget=lambda: dialog), QDialog=Dialog),
        cc_dialog_snapshot=lambda widget: keep_dialog_snapshot(),
        exact_undo_warning_button=lambda widget: None, is_known_cc_progress_dialog=lambda widget: False,
        exact_dialog_buttons=lambda widget, text, **kwargs: [yes] if text == 'Yes' else [cancel],
        RLPy=SimpleNamespace(RFileIO=SimpleNamespace(LoadFile=load)), checked=lambda *args: {'is_error': False})
    receipt = []
    if accepted:
        MODULE.guarded_load('one.ccSkinGenPreset', label, api, receipt, lambda: None,
            preserve_modified_materials=opt_in, stage=stage)
        assert events == ['yes']
        assert receipt[0]['keep_modified_materials']['clicked_count'] == 1
    else:
        with pytest.raises(ValueError, match='Unknown modal'):
            MODULE.guarded_load('one.ccSkinGenPreset', label, api, receipt, lambda: None,
                preserve_modified_materials=opt_in, stage=stage)
        assert events == ['cancel']
