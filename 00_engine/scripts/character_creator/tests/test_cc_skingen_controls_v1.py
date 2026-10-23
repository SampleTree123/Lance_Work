import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('skingen_controls', Path(__file__).parents[1] / 'cc_skingen_controls_v1.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Node:
    def __init__(self, name, parent=None):
        self.name, self.parent = name, parent

    def objectName(self):
        return self.name

    def parentWidget(self):
        return self.parent


class QCheckBox(Node):
    def __init__(self, parent=None, checked=False):
        super().__init__('qtModeSwitchPushButton', parent)
        self.checked, self.clicks = checked, 0

    def text(self):
        return 'Activate Editor'

    def isVisible(self):
        return True

    def isEnabled(self):
        return True

    def isChecked(self):
        return self.checked

    def click(self):
        self.clicks += 1
        self.checked = not self.checked


def chain(names):
    parent = None
    for name in names:
        parent = Node(name, parent)
    return parent


def test_selector_uses_exact_ancestor_scope_not_first_name_match():
    unrelated = QCheckBox(chain(('OtherPanel', 'qtTopWidget')))
    correct = QCheckBox(chain(MODULE.TOP))
    assert MODULE.unique_widget([unrelated, correct], *MODULE.SELECTORS['editor']) is correct


def test_selector_refuses_collision_even_with_identical_visible_widgets():
    first = QCheckBox(chain(MODULE.TOP))
    second = QCheckBox(chain(MODULE.TOP))
    with pytest.raises(ValueError, match='found 2'):
        MODULE.unique_widget([first, second], *MODULE.SELECTORS['editor'])


def test_selector_refuses_missing_control():
    with pytest.raises(ValueError, match='found 0'):
        MODULE.unique_widget([], *MODULE.SELECTORS['editor'])


def test_readonly_ancestry_inventory_reports_actual_tab_and_stack_pages():
    class QTabWidget(Node):
        def count(self): return len(self.pages)
        def widget(self, index): return self.pages[index]
        def currentIndex(self): return 0
        def tabText(self, index): return ['Morph', 'Appearance'][index]
        def setCurrentIndex(self, index): pytest.fail('Inventory must not select a tab')

    class QStackedWidget(Node):
        def count(self): return len(self.pages)
        def widget(self, index): return self.pages[index]
        def currentIndex(self): return 0
        def setCurrentIndex(self, index): pytest.fail('Inventory must not switch a stack')

    tab = QTabWidget('qtAttributeRootTab')
    stack = QStackedWidget('qt_tabwidget_stackedwidget', tab)
    other, target = Node('qtMorphTab', stack), Node('qtAppearanceTab', stack)
    target.isVisible, target.isHidden = lambda: False, lambda: True
    stack.pages = tab.pages = [other, target]
    editor = QCheckBox(target, checked=True)
    editor.isVisible = lambda: False
    api = SimpleNamespace(QtWidgets=SimpleNamespace(QTabWidget=QTabWidget, QStackedWidget=QStackedWidget))
    report = MODULE.ancestry_inventory(editor, api)
    assert report['read_only']
    parents = [row for row in report['ancestors'] if 'page_inventory' in row]
    assert len(parents) == 2
    for row in parents:
        pages = row['page_inventory']
        assert pages['current_index'] == 0 and pages['editor_page_indices'] == [1]
        assert pages['unique_editor_page']
        assert pages['pages'][1]['widget']['isVisible'] is False
    assert parents[1]['page_inventory']['pages'][1]['tab_text'] == 'Appearance'


def test_public_inspect_records_ancestry_without_scene_or_ui_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, 'RUN_ROOT', str(tmp_path))
    editor = QCheckBox(checked=True)
    monkeypatch.setattr(MODULE, 'capture', lambda *args: ({'observed': True}, {'editor': editor}))
    api = SimpleNamespace(QtWidgets=SimpleNamespace(), now=lambda: 'test',
        write_json=lambda value, path: None)
    result = MODULE.run({'skingen_controls': {'action': 'inspect'}}, str(tmp_path / 'inspect'), lambda text: None, api)
    assert result['success']
    assert result['editor_ancestry']['read_only']
    assert not result['opacity_written'] and not result['layer_selected'] and editor.clicks == 0


def test_activation_is_idempotent_and_does_not_toggle_editor_off():
    checkbox = QCheckBox(checked=False)
    first = MODULE.activate_editor(checkbox)
    second = MODULE.activate_editor(checkbox)
    assert first == {'checked_before': False, 'checked_after': True, 'clicked': True}
    assert second == {'checked_before': True, 'checked_after': True, 'clicked': False}
    assert checkbox.clicks == 1


def test_activation_requires_actual_text_not_only_object_name():
    checkbox = QCheckBox()
    checkbox.text = lambda: 'Something else'
    with pytest.raises(ValueError, match='no longer matches'):
        MODULE.activate_editor(checkbox)
    assert checkbox.clicks == 0


def reveal_environment():
    class QWidget(Node):
        def isEnabled(self): return True

    class QTabWidget(Node):
        def isVisible(self): return True
        def isEnabled(self): return True
        def count(self): return 2
        def currentIndex(self): return self.index
        def indexOf(self, item): return self.pages.index(item) if item in self.pages else -1
        def widget(self, index): return self.pages[index]
        def setCurrentIndex(self, index):
            self.writes.append(index)
            self.index = index

    tab = QTabWidget('qtAttributeRootTab', chain(('MainWindow', ':/AttributeModify.ui', 'AttributeModify')))
    tab.index, tab.writes = 0, []
    stack = Node('qt_tabwidget_stackedwidget', tab)
    page, other = QWidget('qtAppearanceTab', stack), QWidget('qtEditAttributeTab', stack)
    tab.pages = [other, page]  # Runtime index1 intentionally differs from observed live index3.
    parent = page
    for name in MODULE.TOP:
        parent = Node(name, parent)
    editor = QCheckBox(parent, checked=True)
    editor.isVisible = lambda: tab.index == 1
    api = SimpleNamespace(QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(
        allWidgets=lambda: [tab, page, editor], processEvents=lambda: None)))
    return api, tab, page, editor


def test_reveal_uses_exact_page_indexof_and_is_idempotent_without_stack_writes():
    api, tab, page, editor = reveal_environment()
    first = MODULE.reveal_editor(api)
    second = MODULE.reveal_editor(api)
    assert first['verified'] and first['target_index'] == 1
    assert first['before']['editor']['isVisible'] is False
    assert first['after']['editor']['isVisible'] is True
    assert tab.writes == [1] and not second['set_current_index_called']
    assert editor.clicks == 0 and editor.isChecked()


def test_reveal_refuses_page_collision_before_navigation():
    api, tab, page, editor = reveal_environment()
    api.QtWidgets.QApplication.allWidgets = lambda: [tab, page, page, editor]
    with pytest.raises(ValueError, match='found 2'):
        MODULE.reveal_editor(api)
    assert tab.writes == []


def test_reveal_refuses_missing_page_membership_or_disabled_tab():
    api, tab, page, editor = reveal_environment()
    tab.indexOf = lambda page: -1
    with pytest.raises(ValueError, match='not a member'):
        MODULE.reveal_editor(api)
    assert tab.writes == []
    api, tab, page, editor = reveal_environment()
    tab.isEnabled = lambda: False
    with pytest.raises(ValueError, match='availability'):
        MODULE.reveal_editor(api)
    assert tab.writes == []


def test_reveal_failure_keeps_real_navigation_and_visibility_audit():
    api, tab, page, editor = reveal_environment()
    editor.isVisible = lambda: False
    audit = {}
    with pytest.raises(ValueError, match='did not reveal'):
        MODULE.reveal_editor(api, audit)
    assert tab.writes == [1] and not audit['verified']
    assert audit['after']['editor']['isVisible'] is False


def test_disabled_editor_is_recorded_and_refused_without_forcing_enable():
    checkbox = QCheckBox(checked=True)
    checkbox.isEnabled = lambda: False
    audit = {}
    with pytest.raises(ValueError, match="'isEnabled': False") as failure:
        MODULE.activate_editor(checkbox, audit=audit)
    assert "'isChecked': True" in str(failure.value)
    assert audit['checkbox_before_activation']['object_name'] == 'qtModeSwitchPushButton'
    assert not audit['checkbox_before_activation']['isEnabled']
    assert checkbox.clicks == 0


def test_layer_name_requires_exact_match_and_reports_duplicate_rows():
    rows = [{'row': 0, 'names': ['upper face']}, {'row': 1, 'names': ['Upper Face']},
            {'row': 2, 'names': ['upper face extra']}, {'row': 3, 'names': ['mid face']}]
    assert MODULE.layer_name_matches(rows, 'upper face') == [0, 1]
    with pytest.raises(ValueError, match='2 rows'):
        MODULE.require_unique_layer(rows, 'upper face')
    assert MODULE.require_unique_layer(rows, 'mid face') == 3
    with pytest.raises(ValueError, match='0 rows'):
        MODULE.require_unique_layer(rows, 'lower face')


def test_unknown_modal_blocks_action_and_is_never_accepted(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    state = {'active': True, 'operation_calls': 0, 'rejected': False}

    class Dialog:
        def isVisible(self):
            return True

        def reject(self):
            state.update(active=False, rejected=True)

    dialog = Dialog()
    timer = SimpleNamespace(timeout=SimpleNamespace(connect=lambda callback: None),
        setInterval=lambda value: None, start=lambda: None, stop=lambda: None)
    api = SimpleNamespace(QtCore=SimpleNamespace(QTimer=lambda: timer),
        QtWidgets=SimpleNamespace(QDialog=Dialog, QApplication=SimpleNamespace(
            activeModalWidget=lambda: dialog if state['active'] else None)),
        cc_dialog_snapshot=lambda widget: {'title': 'Unexpected palette'},
        is_known_cc_progress_dialog=lambda widget: False,
        exact_undo_warning_button=lambda widget: None, exact_dialog_buttons=lambda *args, **kwargs: [])

    def operation():
        state['operation_calls'] += 1

    report = {}
    with pytest.raises(ValueError, match='action not executed'):
        MODULE.guarded_action(operation, api, report, lambda: None)
    assert state['rejected'] and state['operation_calls'] == 0
    assert report['modal_guard']['unknown'] == {'title': 'Unexpected palette'}


def test_controls_reuse_exact_deduplicated_undo_warning(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    import cc_makeup_probe_v1 as probe
    state, callbacks = {'active': False, 'clicks': 0}, []
    dialog = SimpleNamespace(isVisible=lambda: True)

    def click():
        state.update(active=False, clicks=state['clicks'] + 1)

    ok = SimpleNamespace(text=lambda: 'OK', click=click)
    snapshot = {'class_name': 'QMessageBox', 'window_title': 'Character Creator 5',
        'labels': [probe.UNDO_WARNING_TEXT, ' '], 'direct_text': [probe.UNDO_WARNING_TEXT, ' '],
        'buttons': [{'class_name': 'QPushButton', 'text': 'OK', 'visible': True,
            'enabled': True, 'checkable': False}]}
    timer = SimpleNamespace(timeout=SimpleNamespace(connect=lambda callback: callbacks.append(callback)),
        setInterval=lambda value: None, start=lambda: None, stop=lambda: None)
    api = SimpleNamespace(QtCore=SimpleNamespace(QTimer=lambda: timer),
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(
            activeModalWidget=lambda: dialog if state['active'] else None, processEvents=lambda: None)),
        cc_dialog_snapshot=lambda widget: snapshot, is_known_cc_progress_dialog=lambda widget: False,
        exact_dialog_buttons=lambda widget, text, **kwargs: [ok] if text == 'OK' else [])

    def operation():
        state['active'] = True
        callbacks[0]()
        return 'done'

    report = {}
    assert MODULE.guarded_action(operation, api, report, lambda: None) == 'done'
    assert state['clicks'] == 1
    assert report['modal_guard']['undo_count'] == 1 and report['modal_guard']['unknown'] is None


def layer_environment(monkeypatch, duplicate=False, enabled=True, linked=True):
    state = {'row': -1, 'selected': [], 'spin': 100, 'slider': 100, 'writes': [], 'selections': []}
    names = [{'row': 0, 'names': ['Eyebrow'], 'cells': []}]
    if duplicate:
        names.append({'row': 1, 'names': ['Eyebrow'], 'cells': []})

    def spin_write(value):
        state['writes'].append(value)
        state['spin'] = value
        if linked:
            state['slider'] = value

    spin = type('QSpinBox', (Node,), {} )('qtSpinBox', chain(MODULE.TOP + ('qtBlendOpacityHorizontalSliderEx',)))
    slider = type('QSlider', (Node,), {} )('EditedWidget', chain(MODULE.TOP + ('qtBlendOpacityHorizontalSliderEx',)))
    for widget, key in ((spin, 'spin'), (slider, 'slider')):
        widget.isVisible = lambda: True
        widget.isEnabled = lambda: enabled
        widget.minimum, widget.maximum = lambda: 0, lambda: 100
        widget.value = lambda key=key: state[key]
    spin.setValue = spin_write

    def select(row, column):
        state['selections'].append(row)
        state.update(row=row, selected=[[row, column]])

    controls = {'material': SimpleNamespace(currentText=lambda: 'Head'),
        'table': SimpleNamespace(isVisible=lambda: True, isEnabled=lambda: True, setCurrentCell=select),
        'editor': SimpleNamespace(isChecked=lambda: True), 'opacity_spin': spin, 'opacity_slider': slider}

    def capture(api, requested_names):
        return {'table': {'rows': names, 'current_row': state['row'], 'selected_indexes': state['selected']}}, controls

    monkeypatch.setattr(MODULE, 'capture', capture)
    api = SimpleNamespace(QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(
        processEvents=lambda: None, allWidgets=lambda: [spin, slider])))
    return state, api


def test_layer_selection_is_exact_and_collision_prevents_any_selection(monkeypatch):
    state, api = layer_environment(monkeypatch, duplicate=True)
    with pytest.raises(ValueError, match='2 rows'):
        MODULE.selected_layer(api, 'Eyebrow')
    assert not state['selections'] and not state['writes']


def test_known_top_opacity_write_requires_selected_row_and_linked_readback(monkeypatch):
    state, api = layer_environment(monkeypatch)
    result = MODULE.set_layer_opacity(api, 'Eyebrow', 50)
    assert result['verified'] and result['after']['opacity'] == 50
    assert state['writes'] == [50] and state['row'] == 0
    assert state['slider'] == 50
    stronger = MODULE.set_layer_opacity(api, 'Eyebrow', 100)
    assert stronger['verified'] and stronger['after']['opacity'] == 100
    assert state['writes'] == [50, 100]


def test_disabled_control_blocks_numeric_write_even_when_row_is_selected(monkeypatch):
    state, api = layer_environment(monkeypatch, enabled=False)
    with pytest.raises(ValueError, match='does not enable'):
        MODULE.set_layer_opacity(api, 'Eyebrow', 50)
    assert not state['writes']


def test_unlinked_slider_causes_failed_readback_with_partial_write_audit(monkeypatch):
    state, api = layer_environment(monkeypatch, linked=False)
    audit = {}
    with pytest.raises(ValueError, match='disagree'):
        MODULE.set_layer_opacity(api, 'Eyebrow', 50, audit)
    assert state['writes'] == [50] and audit['spin_write_performed']
    assert not audit.get('verified', False)


def test_persistence_signature_ignores_order_but_detects_changed_opacity():
    def record(name, opacity):
        return {'layer_name': name, 'opacity': opacity, 'slider_opacity': opacity,
                'row_enable_flags_uninterpreted': [{'object_name': 'qtEnableToolButton', 'isChecked': False}]}
    before = [record('upper face', 50), record('mid face', 50), record('lower face', 50)]
    assert MODULE.layer_persistence_signature(before) == MODULE.layer_persistence_signature(list(reversed(before)))
    after = [record('upper face', 50), record('mid face', 100), record('lower face', 50)]
    assert MODULE.layer_persistence_signature(before) != MODULE.layer_persistence_signature(after)
