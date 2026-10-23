"""Read native selection through model indexes, avoiding deleted item wrappers.

Experimental Assembly Technical; normal enabled-tab checks stay identical.
"""
from pathlib import Path


def run(library, output_dir, log, api):
    path = Path(__file__).with_name('cc_refresh_normal_appearance_navigation_v1.py')
    if api.sha256_file(str(path)) != 'a1e705b24a93dfb67249de600b666ae2b00b0617b26b49f4bb0d7f7499fa714d':
        raise ValueError('Frozen normal-navigation core changed')
    source = path.read_text(encoding='utf-8-sig')
    start = source.index('        trees = [x for x in docks[0].findChildren')
    end = source.index('        widgets = list(api.QtWidgets.QApplication.allWidgets())', start)
    source = source[:start] + '''        trees = []
        report['destroyed_native_tree_wrappers_skipped'] = 0
        for candidate in docks[0].findChildren(api.QtWidgets.QTreeWidget):
            try:
                parent = candidate.parentWidget()
                if parent is not None and str(parent.objectName()) == 'qtSceneManagerTreeFrm':
                    trees.append(candidate)
            except RuntimeError:
                report['destroyed_native_tree_wrappers_skipped'] += 1
        if len(trees) != 1:
            raise ValueError('Unique actual live native tree required')
        tree = trees[0]
        model = tree.model()
        indexes = list(tree.selectionModel().selectedRows(0))
        if len(indexes) != 1:
            raise ValueError('One native actor row must be selected')
        index = indexes[0]
        parent = index.parent()
        role = api.QtCore.Qt.DisplayRole
        report['native_selection'] = dict(name=str(model.data(index, role)),
            parent_name=str(model.data(parent, role)) if parent.isValid() else None,
            current=tree.currentIndex().sibling(tree.currentIndex().row(), 0) == index,
            hidden=bool(tree.isRowHidden(index.row(), parent)),
            disabled=not bool(int(model.flags(index)) & int(api.QtCore.Qt.ItemIsEnabled)),
            interface='QAbstractItemModel/QModelIndex; no QTreeWidgetItem wrapper')
        row = report['native_selection']
        if row['name'] != str(avatars[0].GetName()) or row['parent_name'] != 'Character' or row['hidden'] or row['disabled']:
            raise ValueError('Native model selection is not the same active root actor')
''' + source[end:]
    namespace = dict(__file__=str(path), __name__='_model_index_normal_navigation_private')
    exec(compile(source, str(path), 'exec'), namespace)
    return namespace['run'](library, output_dir, log, api)
