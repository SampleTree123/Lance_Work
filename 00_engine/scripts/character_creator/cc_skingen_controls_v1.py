"""Evidence-bound SkinGen Qt controls probe; no load, save, or numeric writes.

The widget paths come from session_backup_v2/makeup_probe_report.json.
Use inspect, activate_editor or select_makeup; row-name resolution is read-only.
"""
import os
import time
import traceback

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
RESOURCE = ':/plugin/CCAvatarShaping/MixSubstancePanel.ui'
TOP = (RESOURCE, 'AvatarShapingSectionBasePanel', 'MixSubstancePanel', 'qtTopWidget')
SELECTORS = {
    'editor': ('qtModeSwitchPushButton', 'QCheckBox', TOP),
    'makeup': ('qtMakeupPushButton', 'QPushButton', (RESOURCE, 'AvatarShapingSectionBasePanel', 'qtUpperPanel')),
    'skin': ('qtSkinPushButton', 'QPushButton', (RESOURCE, 'AvatarShapingSectionBasePanel', 'qtUpperPanel')),
    'material': ('qtMaterialComboBox', 'QComboBox', TOP),
    'table': ('qtFeatureTableWidget', 'QTableWidget', TOP + ('qtLowerPanel',)),
    'opacity_spin': ('qtSpinBox', 'QSpinBox', TOP + ('qtBlendOpacityHorizontalSliderEx',)),
    'opacity_slider': ('EditedWidget', 'QSlider', TOP + ('qtBlendOpacityHorizontalSliderEx',)),
}
APPEARANCE_TAB_SELECTOR = ('qtAttributeRootTab', 'QTabWidget',
    ('MainWindow', ':/AttributeModify.ui', 'AttributeModify'))
APPEARANCE_PAGE_SELECTOR = ('qtAppearanceTab', 'QWidget',
    ('MainWindow', ':/AttributeModify.ui', 'AttributeModify', 'qtAttributeRootTab', 'qt_tabwidget_stackedwidget'))


def ancestor_names(widget):
    names, parent = [], widget.parentWidget()
    while parent is not None and len(names) < 40:
        names.append(str(parent.objectName()))
        parent = parent.parentWidget()
    return tuple(reversed(names))


def unique_widget(widgets, object_name, class_name, ancestor_suffix):
    matches = []
    for widget in widgets:
        try:
            if str(widget.objectName()) != object_name or type(widget).__name__ != class_name:
                continue
            ancestors = ancestor_names(widget)
            if ancestors[-len(ancestor_suffix):] == tuple(ancestor_suffix):
                matches.append(widget)
        except RuntimeError:
            continue
    if len(matches) != 1:
        raise ValueError('Expected exactly one {} {} under {}; found {}'.format(
            class_name, object_name, '/'.join(ancestor_suffix), len(matches)))
    return matches[0]


def widget_record(widget):
    record = {'class': type(widget).__name__, 'object_name': str(widget.objectName()),
              'ancestor_names': list(ancestor_names(widget))}
    for name in ('text', 'toolTip', 'isVisible', 'isHidden', 'isEnabled', 'isCheckable', 'isChecked',
                 'value', 'minimum', 'maximum', 'currentText', 'currentIndex'):
        getter = getattr(widget, name, None)
        if callable(getter):
            try:
                value = getter()
                if isinstance(value, (str, int, float, bool)):
                    record[name] = value
            except Exception:
                pass
    return record


def ancestry_inventory(widget, api):
    """Qt getters only: identify the real selected and containing parent pages."""
    chain, cursor = [], widget
    while cursor is not None:
        if len(chain) >= 128 or any(cursor is ancestor for ancestor in chain):
            raise ValueError('Unexpected cyclic or overlong widget ancestry')
        chain.append(cursor)
        cursor = cursor.parentWidget()
    records = []
    for ancestor in chain:
        record = widget_record(ancestor)
        kind = next((name for name in ('QTabWidget', 'QStackedWidget')
            if isinstance(ancestor, getattr(api.QtWidgets, name, ()))), None)
        if kind is not None:
            count = int(ancestor.count())
            if count < 0 or count > 128:
                raise ValueError('Unexpected parent page count')
            pages, containing = [], []
            for index in range(count):
                page = ancestor.widget(index)
                if page is None:
                    raise ValueError('Parent page enumeration returned no widget')
                contains = any(page is item for item in chain)
                if contains:
                    containing.append(index)
                pages.append({'index': index, 'widget': widget_record(page),
                    'tab_text': str(ancestor.tabText(index)) if kind == 'QTabWidget' else None,
                    'contains_editor': contains})
            record['page_inventory'] = {'kind': kind, 'count': count,
                'current_index': int(ancestor.currentIndex()), 'editor_page_indices': containing,
                'unique_editor_page': len(containing) == 1, 'pages': pages}
        records.append(record)
    return {'read_only': True, 'order': 'editor_to_root', 'ancestors': records,
        'policy': 'Qt getters only; no setCurrentIndex, setVisible, clicks, selection or scene calls.'}


def table_record(table, api):
    rows = []
    roles = ('DisplayRole', 'ToolTipRole', 'CheckStateRole', 'UserRole')
    for row in range(table.rowCount()):
        entry = {'row': row, 'cells': [], 'names': []}
        for column in range(table.columnCount()):
            cell = {'column': column}
            item = table.item(row, column)
            if item is not None:
                cell['item_text'] = str(item.text())
                cell['item_selected'] = bool(item.isSelected())
                cell['roles'] = {}
                for name in roles:
                    value = item.data(getattr(api.QtCore.Qt, name))
                    cell['roles'][name] = value if value is None or isinstance(value, (str, int, float, bool)) else str(value)
                if item.text():
                    entry['names'].append(str(item.text()).strip())
            widget = table.cellWidget(row, column)
            if widget is not None:
                children = [widget] + list(widget.findChildren(api.QtWidgets.QWidget))
                cell['widgets'] = [widget_record(child) for child in children]
                # qtTextLabel is the actual SkinGen layer-name label in the receipt.
                entry['names'].extend(str(child.text()).strip() for child in children
                    if str(child.objectName()) == 'qtTextLabel' and callable(getattr(child, 'text', None)) and child.text())
            entry['cells'].append(cell)
        entry['names'] = sorted(set(entry['names']))
        rows.append(entry)
    return {'row_count': table.rowCount(), 'column_count': table.columnCount(),
            'current_row': table.currentRow(), 'current_column': table.currentColumn(),
            'selected_indexes': [[index.row(), index.column()] for index in table.selectedIndexes()], 'rows': rows}


def layer_name_matches(rows, name):
    """Exact case-insensitive names only; same-name layers are explicit collisions."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Layer name must be a nonempty string')
    normalized = str(name).strip().casefold()
    return [entry['row'] for entry in rows if any(str(value).strip().casefold() == normalized for value in entry['names'])]


def require_unique_layer(rows, name):
    matches = layer_name_matches(rows, name)
    if len(matches) != 1:
        raise ValueError('Layer name {!r} resolves to {} rows {}; no row selected'.format(name, len(matches), matches))
    return matches[0]


def capture(api, requested_names=()):
    widgets = list(api.QtWidgets.QApplication.allWidgets())
    controls = {key: unique_widget(widgets, *selector) for key, selector in SELECTORS.items()}
    table = table_record(controls['table'], api)
    result = {'controls': {key: widget_record(value) for key, value in controls.items() if key != 'table'},
              'table': table, 'layer_name_resolution': {}}
    for name in requested_names:
        matches = layer_name_matches(table['rows'], name)
        result['layer_name_resolution'][name] = {'rows': matches, 'unique': len(matches) == 1,
                                                'collision': len(matches) > 1, 'missing': not matches}
    return result, controls


def activate_editor(checkbox, audit=None):
    observed = widget_record(checkbox)
    if audit is not None:
        audit['checkbox_before_activation'] = observed
    if str(checkbox.text()) != 'Activate Editor' or not checkbox.isVisible() or not checkbox.isEnabled():
        raise ValueError('Editor checkbox no longer matches saved evidence: {!r}'.format(observed))
    before = bool(checkbox.isChecked())
    if not before:
        checkbox.click()
    after = bool(checkbox.isChecked())
    if audit is not None:
        audit['checkbox_after_activation'] = widget_record(checkbox)
    if not after:
        raise ValueError('Editor activation did not read back checked: {!r}'.format(widget_record(checkbox)))
    return {'checked_before': before, 'checked_after': after, 'clicked': not before}


def reveal_editor(api, audit=None):
    """Select only the live-inventoried Appearance page through its QTabWidget."""
    audit = audit if audit is not None else {}
    widgets = list(api.QtWidgets.QApplication.allWidgets())
    tab = unique_widget(widgets, *APPEARANCE_TAB_SELECTOR)
    page = unique_widget(widgets, *APPEARANCE_PAGE_SELECTOR)
    editor = unique_widget(widgets, *SELECTORS['editor'])
    audit['before'] = {'tab': widget_record(tab), 'page': widget_record(page), 'editor': widget_record(editor)}
    index = int(tab.indexOf(page))
    audit['target_index'] = index
    if index < 0 or index >= int(tab.count()) or tab.widget(index) is not page:
        raise ValueError('Exact Appearance page is not a member of its bound QTabWidget')
    cursor, contains = editor, False
    while cursor is not None:
        if cursor is page:
            contains = True
            break
        cursor = cursor.parentWidget()
    if not contains or not tab.isVisible() or not tab.isEnabled() or not page.isEnabled():
        raise ValueError('Appearance navigation ancestry/availability differs from live evidence: {!r}'.format(audit))
    before = int(tab.currentIndex())
    audit['current_index_before'] = before
    audit['set_current_index_called'] = before != index
    if before != index:
        tab.setCurrentIndex(index)
    api.QtWidgets.QApplication.processEvents()
    # Resolve the exact editor again after Qt handles the page change.
    editor = unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *SELECTORS['editor'])
    audit['current_index_after'] = int(tab.currentIndex())
    audit['after'] = {'tab': widget_record(tab), 'page': widget_record(page), 'editor': widget_record(editor)}
    audit['verified'] = int(tab.currentIndex()) == index and tab.widget(index) is page and bool(editor.isVisible())
    if not audit['verified']:
        raise ValueError('Appearance page navigation did not reveal the exact editor: {!r}'.format(audit))
    return audit


def select_makeup(button):
    if str(button.text()) != 'Makeup' or str(button.toolTip()) != 'SkinGen Makeup Effects' or not button.isVisible() or not button.isEnabled():
        raise ValueError('Makeup button no longer matches saved evidence')
    if button.isCheckable() and button.isChecked():
        return {'clicked': False, 'already_checked': True}
    button.click()
    return {'clicked': True, 'checked_after': bool(button.isChecked()) if button.isCheckable() else None,
            'verification': 'Inspect resulting layer table; a button click alone is not proof of Makeup state'}


def select_category(api, category):
    """Only categories with real saved Qt evidence; no menu traversal."""
    if category not in ('makeup', 'skin'):
        raise ValueError('Expected Skin or Makeup category')
    widget = unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *SELECTORS[category])
    text, tooltip = ('Makeup', 'SkinGen Makeup Effects') if category == 'makeup' else ('Skin', 'SkinGen Skin Effects')
    if str(widget.text()) != text or str(widget.toolTip()) != tooltip or not widget.isCheckable() or not widget.isVisible() or not widget.isEnabled():
        raise ValueError('Category no longer matches saved Qt evidence')
    clicked = not bool(widget.isChecked())
    if clicked:
        widget.click()
    api.QtWidgets.QApplication.processEvents()
    if not widget.isChecked():
        raise ValueError('Category did not read back checked')
    return {'category': category, 'clicked': clicked, 'checked': True}


def selected_layer(api, name):
    """Select a unique real table row with standard Qt selection, then verify it."""
    before, controls = capture(api, [name])
    if str(controls['material'].currentText()) != 'Head':
        raise ValueError('Layer operations require the evidenced Head material')
    row = require_unique_layer(before['table']['rows'], name)
    table = controls['table']
    if not table.isVisible() or not table.isEnabled():
        raise ValueError('SkinGen layer table is not editable')
    table.setCurrentCell(row, 0)
    api.QtWidgets.QApplication.processEvents()
    after, controls = capture(api, [name])
    rows = {index[0] for index in after['table']['selected_indexes']}
    actual = require_unique_layer(after['table']['rows'], name)
    if actual != row or after['table']['current_row'] != row or rows != {row}:
        raise ValueError('Standard Qt selection did not uniquely select the requested SkinGen layer')
    return after, controls, row


def read_layer_opacity(api, name):
    state, controls, row = selected_layer(api, name)
    spin, slider = controls['opacity_spin'], controls['opacity_slider']
    if not controls['editor'].isChecked() or not all(w.isVisible() and w.isEnabled() for w in (spin, slider)):
        raise ValueError('Selected layer does not enable the evidenced top Opacity controls; no fallback events sent')
    if any(int(w.minimum()) != 0 or int(w.maximum()) != 100 for w in (spin, slider)):
        raise ValueError('Top Opacity range differs from observed0..100')
    value, linked_value = int(spin.value()), int(slider.value())
    if value != linked_value:
        raise ValueError('Top Opacity spinbox/slider disagree')
    row_state = next(record for record in state['table']['rows'] if record['row'] == row)
    flags = [{'object_name': w['object_name'], 'isChecked': w.get('isChecked')}
             for cell in row_state['cells'] for w in cell.get('widgets', [])
             if w.get('object_name') == 'qtEnableToolButton']
    return {'layer_name': name, 'row': row, 'opacity': value, 'slider_opacity': linked_value,
            'row_enable_flags_uninterpreted': flags, 'names': row_state['names']}


def set_layer_opacity(api, name, opacity, audit=None):
    if isinstance(opacity, bool) or opacity not in (50, 100):
        raise ValueError('Only the authorized top-layer Opacity50/100 is allowed')
    audit = audit if audit is not None else {}
    before = read_layer_opacity(api, name)
    audit.update(layer_name=name, before=before, target=opacity, spin_write_performed=False)
    if before['opacity'] != opacity:
        spin = unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *SELECTORS['opacity_spin'])
        audit['spin_write_performed'] = True
        spin.setValue(int(opacity))
        api.QtWidgets.QApplication.processEvents()
    after = read_layer_opacity(api, name)
    audit['after'] = after
    if after['opacity'] != opacity or after['slider_opacity'] != opacity:
        raise ValueError('Opacity write did not read back on both evidenced controls')
    audit['verified'] = True
    return audit


def layer_persistence_signature(records):
    """Ignore row order; compare exact names, Opacity, and uninterpreted enable flags."""
    result = {}
    for record in records:
        name = str(record['layer_name']).strip().casefold()
        if not name or name in result:
            raise ValueError('Duplicate layer name in persistence evidence')
        result[name] = {'opacity': record['opacity'], 'slider_opacity': record['slider_opacity'],
                        'row_enable_flags_uninterpreted': record['row_enable_flags_uninterpreted']}
    return result


def guarded_action(operation, api, report, checkpoint, preserve_modified_materials=False, stage=None):
    modal = {'observed': [], 'unknown': None, 'undo_count': 0}
    report['modal_guard'] = modal
    handled = set()
    timer = api.QtCore.QTimer()
    timer.setInterval(100)

    def inspect():
        widget = api.QtWidgets.QApplication.activeModalWidget()
        if widget is None or not widget.isVisible():
            return
        snapshot = api.cc_dialog_snapshot(widget)
        snapshot.pop('normalized_text', None)
        if snapshot not in modal['observed']:
            modal['observed'].append(snapshot)
            checkpoint()
        if api.is_known_cc_progress_dialog(widget) or id(widget) in handled:
            return
        handled.add(id(widget))
        import cc_makeup_probe_v1 as probe
        button = probe.exact_undo_warning_button(widget, api, snapshot)
        if button is not None:
            modal['undo_count'] += 1
            button.click()
            return
        if preserve_modified_materials is True and stage == 'redness_preset':
            if probe.keep_modified_result_matches(snapshot):
                yes = api.exact_dialog_buttons(widget, 'Yes', checkable=False)
                if len(yes) == 1 and str(yes[0].text()) == '&Yes':
                    modal.setdefault('keep_modified_yes_count', 0)
                    modal['keep_modified_yes_count'] += 1
                    checkpoint()
                    yes[0].click()
                    return
        modal['unknown'] = snapshot
        checkpoint()
        cancel = api.exact_dialog_buttons(widget, 'Cancel', checkable=False)
        if len(cancel) == 1:
            cancel[0].click()
        elif isinstance(widget, api.QtWidgets.QDialog):
            widget.reject()
        else:
            widget.close()

    timer.timeout.connect(inspect)
    timer.start()
    try:
        inspect()
        if modal['unknown'] is not None or api.QtWidgets.QApplication.activeModalWidget() is not None:
            raise ValueError('Modal already active; SkinGen control action not executed')
        result = operation()
        # Bounded Qt settling; no menu traversal, rendering, or scene evaluation.
        until = time.monotonic() + 10
        while True:
            api.QtWidgets.QApplication.processEvents()
            inspect()
            if modal['unknown'] is not None:
                raise ValueError('Unknown modal refused during SkinGen control action')
            active = api.QtWidgets.QApplication.activeModalWidget()
            if active is None:
                break
            if time.monotonic() >= until:
                raise ValueError('SkinGen progress still active after bounded wait')
            time.sleep(0.05)
        return result
    finally:
        timer.stop()


def run(library, output_dir, log, api):
    config = library['skingen_controls']
    action = config.get('action', 'inspect')
    if action not in ('inspect', 'reveal_editor', 'activate_editor', 'select_makeup', 'select_skin', 'select_layer', 'read_layers', 'set_opacity'):
        raise ValueError('Unsupported evidence-bound SkinGen control action')
    root = os.path.normcase(os.path.realpath(RUN_ROOT))
    output = os.path.normcase(os.path.realpath(output_dir))
    if os.path.commonpath([root, output]) != root or root == output:
        raise ValueError('Expected an independent child of the task output root')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse to overwrite existing control probe output')
    if action != 'inspect':
        backup = config['current_scene_backup']
        backup_path = os.path.normcase(os.path.realpath(backup['path']))
        if os.path.commonpath([root, backup_path]) != root or not backup_path.endswith('.ccproject') or api.sha256_file(backup['path']) != backup['sha256']:
            raise ValueError('Mutating UI action requires the hash-bound task scene backup')
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1 or str(avatars[0].GetID()) != str(config['expected_avatar_id']):
            raise ValueError('Current avatar does not match the explicitly bound probe avatar')
    os.makedirs(output_dir, exist_ok=True)
    report = {'diagnostic_mode': 'skingen_controls', 'action': action, 'config': config,
              'success': False, 'opacity_written': False, 'layer_selected': False,
              'scope': 'Exact Qt category/layer/Opacity controls only; no load, save or geometry evaluation',
              'summary_path': os.path.join(output_dir, 'skingen_controls_report.json')}

    def checkpoint():
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])

    try:
        report['before'], controls = capture(api, config.get('layer_names', []))
        if action == 'inspect':
            report['editor_ancestry'] = ancestry_inventory(controls['editor'], api)
        checkpoint()
        if action != 'inspect':
            if action == 'reveal_editor':
                operation = lambda: reveal_editor(api, report.setdefault('reveal_editor_audit', {}))
            elif action == 'activate_editor':
                operation = lambda: activate_editor(controls['editor'])
            elif action in ('select_makeup', 'select_skin'):
                operation = lambda: select_category(api, action[len('select_'):])
            else:
                def operation():
                    select_category(api, config['category'])
                    if action == 'select_layer':
                        state, _, row = selected_layer(api, config['layer_name'])
                        report['layer_selected'] = True
                        return {'row': row, 'state': state}
                    if action == 'read_layers':
                        values = [read_layer_opacity(api, name) for name in config['layer_names']]
                        report['layer_selected'] = True
                        return {'layers': values, 'persistence_signature': layer_persistence_signature(values)}
                    audit = report.setdefault('opacity_write_audit', {})
                    result = set_layer_opacity(api, config['layer_name'], config['opacity'], audit)
                    report['layer_selected'] = True
                    report['opacity_written'] = bool(result['spin_write_performed'])
                    return result
            report['operation'] = guarded_action(operation, api, report, checkpoint)
            avatars_after = list(api.RLPy.RScene.GetAvatars() or [])
            report['avatar_identity_preserved'] = len(avatars_after) == 1 and str(avatars_after[0].GetID()) == str(config['expected_avatar_id'])
            if not report['avatar_identity_preserved']:
                raise ValueError('Avatar identity changed during SkinGen control action')
        report['after'], _ = capture(api, config.get('layer_names', []))
        report['success'] = True
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    checkpoint()
    log('SkinGen controls: {} success={}'.format(action, report['success']))
    return report
