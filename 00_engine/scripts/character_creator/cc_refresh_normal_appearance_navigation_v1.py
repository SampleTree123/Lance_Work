"""Normal enabled-tab Appearance navigation in AF005's newly loaded scene.

Experimental Assembly Technical. Never force-enable/show, load, save, select an
object or write scene data. A disabled page alone is not a disabled tab entry.
"""
import importlib
import os
import traceback


def run(library, output_dir, log, api):
    config = library['normal_appearance_navigation']
    if config['character_id'] != 'CFD40_AF_005' or os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Exact AF005 independent normal-navigation receipt required')
    for record in (config['load_report'], config['editing_checkpoint']):
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Loaded-checkpoint evidence changed')
    os.makedirs(output_dir, exist_ok=True)
    ui = importlib.import_module('cc_skingen_controls_v1')
    report = dict(success=False, config=config, navigation_performed=False, scene_writes=False,
                  summary_path=os.path.join(output_dir, 'normal_appearance_navigation_report.json'))
    def checkpoint():
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])
    try:
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        selected = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
        if len(avatars) != 1 or str(avatars[0].GetID()) != config['expected_avatar_id'] or selected != [config['expected_avatar_id']]:
            raise ValueError('Exact loaded-checkpoint avatar selection required')
        report['sdk_selection'] = dict(id=selected[0], name=str(avatars[0].GetName()), python_type=type(avatars[0]).__name__)
        docks = [x for x in api.QtWidgets.QApplication.allWidgets() if isinstance(x, api.QtWidgets.QDockWidget)
                 and str(x.objectName()) == ':/plugin/ICListManager/ICListManager.ui']
        if len(docks) != 1:
            raise ValueError('Unique native Scene dock required')
        trees = [x for x in docks[0].findChildren(api.QtWidgets.QTreeWidget)
                 if x.parentWidget() is not None and str(x.parentWidget().objectName()) == 'qtSceneManagerTreeFrm']
        if len(trees) != 1 or len(trees[0].selectedItems()) != 1:
            raise ValueError('Unique selected native scene row required')
        item = trees[0].selectedItems()[0]
        report['native_selection'] = dict(name=str(item.text(0)), parent_name=str(item.parent().text(0)) if item.parent() else None,
                                          current=item is trees[0].currentItem(), hidden=item.isHidden(), disabled=item.isDisabled())
        if (str(item.text(0)) != str(avatars[0].GetName()) or item.parent() is None
                or str(item.parent().text(0)) != 'Character' or item.isHidden() or item.isDisabled()):
            raise ValueError('Native row is not the same active root character')
        widgets = list(api.QtWidgets.QApplication.allWidgets())
        tab = ui.unique_widget(widgets, *ui.APPEARANCE_TAB_SELECTOR)
        page = ui.unique_widget(widgets, *ui.APPEARANCE_PAGE_SELECTOR)
        index = int(tab.indexOf(page))
        if index < 0 or tab.widget(index) is not page:
            raise ValueError('Appearance page membership changed')
        bar = tab.tabBar()
        report['entry_before'] = dict(tab=ui.widget_record(tab), page=ui.widget_record(page),
            target_index=index, current_index=int(tab.currentIndex()), target_tab_enabled=bool(tab.isTabEnabled(index)),
            tab_bar_enabled=bool(bar.isEnabled()), tab_bar_visible=bool(bar.isVisible()))
        checkpoint()
        permitted = (tab.isVisible() and tab.isEnabled() and bar.isVisible() and bar.isEnabled() and tab.isTabEnabled(index))
        report['normal_entry_permitted'] = bool(permitted)
        if permitted and int(tab.currentIndex()) != index:
            def navigate():
                raw = tab.setCurrentIndex(index)
                report['navigation_return'] = dict(python_type=type(raw).__name__, repr=repr(raw))
                report['navigation_performed'] = True
                api.QtWidgets.QApplication.processEvents()
            ui.guarded_action(navigate, api, report.setdefault('navigation_guard', {}), checkpoint)
        report['entry_after'] = dict(page=ui.widget_record(page), current_index=int(tab.currentIndex()),
                                      target_tab_enabled=bool(tab.isTabEnabled(index)))
        report['appearance'], _ = ui.capture(api, ['Eyebrow'])
        report['selected_after'] = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
        if report['selected_after'] != selected:
            raise ValueError('Normal page navigation changed SDK selection')
        report['success'] = True
    except Exception as error:
        report['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    checkpoint()
    return report
