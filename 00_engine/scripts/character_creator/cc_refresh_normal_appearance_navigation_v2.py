"""Ignore destroyed Qt wrappers left by project-load UI recreation.

Experimental Assembly Technical; preserve the v1 no-navigation failure receipt.
"""
from pathlib import Path


def run(library, output_dir, log, api):
    path = Path(__file__).with_name('cc_refresh_normal_appearance_navigation_v1.py')
    if api.sha256_file(str(path)) != 'a1e705b24a93dfb67249de600b666ae2b00b0617b26b49f4bb0d7f7499fa714d':
        raise ValueError('Frozen normal navigation v1 changed')
    source = path.read_text(encoding='utf-8-sig')
    anchor = "        trees = [x for x in docks[0].findChildren(api.QtWidgets.QTreeWidget)\n                 if x.parentWidget() is not None and str(x.parentWidget().objectName()) == 'qtSceneManagerTreeFrm']"
    if source.count(anchor) != 1:
        raise ValueError('Frozen scene-tree enumeration anchor changed')
    source = source.replace(anchor, '''        trees = []
        report['destroyed_native_tree_wrappers_skipped'] = 0
        for candidate in docks[0].findChildren(api.QtWidgets.QTreeWidget):
            try:
                parent = candidate.parentWidget()
                if parent is not None and str(parent.objectName()) == 'qtSceneManagerTreeFrm':
                    trees.append(candidate)
            except RuntimeError:
                report['destroyed_native_tree_wrappers_skipped'] += 1''', 1)
    namespace = dict(__file__=str(path), __name__='_live_qt_normal_navigation_private')
    exec(compile(source, str(path), 'exec'), namespace)
    return namespace['run'](library, output_dir, log, api)
