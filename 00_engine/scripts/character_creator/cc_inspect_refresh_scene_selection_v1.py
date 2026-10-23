"""AF005 native Scene Manager versus SDK selection, read-only.

Experimental Assembly Technical owner. Only getters; no selection, expansion,
load/save, geometry evaluation, visibility, locking or other value changes.
"""
import importlib
import os
import traceback


def simple(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return dict(python_type=type(value).__name__, repr=repr(value))


def run(library, output_dir, log, api):
    config = library['scene_selection_inspect']
    if config['character_id'] != 'CFD40_AF_005' or os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Exact AF005 independent read-only output required')
    for record in (config['editing_checkpoint'], config['last_same_scene_report']):
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Own AF005 evidence changed')
    os.makedirs(output_dir, exist_ok=True)
    ui = importlib.import_module('cc_skingen_controls_v1')
    report = dict(success=False, read_only=True, config=config,
                  summary_path=os.path.join(output_dir, 'scene_selection_report.json'))
    def checkpoint():
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])
    def object_record(obj):
        row = dict(name=str(obj.GetName()), id=str(obj.GetID()), python_type=type(obj).__name__)
        getter = getattr(obj, 'GetAvatarPartType', None)
        if callable(getter):
            row['avatar_part_type'] = str(getter())
        row['state_getter_inventory'] = [name for name in dir(obj) if name.startswith(('Get', 'Is'))
                                         and any(token in name.lower() for token in ('visib', 'lock', 'render', 'type', 'parent'))]
        for name in ('GetVisible', 'IsVisible', 'IsLocked', 'GetLock'):
            getter = getattr(obj, name, None)
            if callable(getter):
                try:
                    row[name] = simple(getter())
                except Exception as error:
                    row[name] = dict(error=str(error))
        return row
    try:
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        selected = list(api.RLPy.RScene.GetSelectedObjects() or [])
        report['sdk'] = dict(avatars=[object_record(x) for x in avatars], selected=[object_record(x) for x in selected])
        if len(avatars) != 1 or str(avatars[0].GetID()) != config['expected_avatar_id']:
            raise ValueError('Current same-scene avatar identity changed')
        report['sdk']['avatar_parts'] = [object_record(x) for x in (avatars[0].GetAvatarParts() or [])]
        docks = [x for x in api.QtWidgets.QApplication.allWidgets() if isinstance(x, api.QtWidgets.QDockWidget)
                 and str(x.objectName()) == ':/plugin/ICListManager/ICListManager.ui' and str(x.windowTitle()) == 'Scene']
        if len(docks) != 1:
            raise ValueError('Unique actual Scene dock required')
        trees = [x for x in docks[0].findChildren(api.QtWidgets.QTreeWidget)
                 if x.parentWidget() is not None and str(x.parentWidget().objectName()) == 'qtSceneManagerTreeFrm']
        if len(trees) != 1:
            raise ValueError('Unique inventoried native scene tree required')
        tree = trees[0]
        report['tree'] = dict(widget=ui.widget_record(tree), columns=tree.columnCount(), rows=[],
                              selected_count=len(tree.selectedItems()), current_column=tree.currentColumn())
        header = tree.headerItem()
        report['tree']['headers'] = [dict(text=str(header.text(c)), tooltip=str(header.toolTip(c))) for c in range(tree.columnCount())]
        def visit(item, path):
            if len(report['tree']['rows']) >= 1000 or len(path) >= 32:
                raise ValueError('Unexpected scene inventory size')
            record = dict(path=path, selected=bool(item.isSelected()), current=item is tree.currentItem(),
                          hidden=bool(item.isHidden()), disabled=bool(item.isDisabled()), expanded=bool(item.isExpanded()),
                          flags=int(item.flags()), item_type=int(item.type()), cells=[])
            for column in range(tree.columnCount()):
                cell = dict(column=column, text=str(item.text(column)), tooltip=str(item.toolTip(column)),
                            status_tip=str(item.statusTip(column)), check_state=int(item.checkState(column)),
                            icon_present=not item.icon(column).isNull(), user_roles={})
                for role in range(int(api.QtCore.Qt.UserRole), int(api.QtCore.Qt.UserRole) + 8):
                    value = item.data(column, role)
                    if value is not None:
                        cell['user_roles'][str(role)] = simple(value)
                widget = tree.itemWidget(item, column)
                if widget is not None:
                    cell['widget'] = ui.widget_record(widget)
                    cell['child_controls'] = [ui.widget_record(x) for x in widget.findChildren(api.QtWidgets.QAbstractButton)]
                record['cells'].append(cell)
            report['tree']['rows'].append(record)
            for index in range(item.childCount()):
                visit(item.child(index), path + [index])
        for index in range(tree.topLevelItemCount()):
            visit(tree.topLevelItem(index), [index])
        report['appearance'], _ = ui.capture(api, ['Eyebrow'])
        report['sdk_selected_after'] = [object_record(x) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
        report['success'] = True
    except Exception as error:
        report['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    checkpoint()
    return report
