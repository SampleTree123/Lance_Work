"""One normal Close on the actually inventoried AF005 Facial Profile Editor.

Experimental Assembly Technical owner; UI-only independent recovery receipt.
No load/save, expression/texture writes, subdivision or geometry evaluation.
"""
import importlib
import os
import traceback


def run(library, output_dir, log, api):
    config = library['close_profile_editor']
    if config['character_id'] != 'CFD40_AF_005':
        raise ValueError('Exact AF005 recovery only')
    for key in ('editing_checkpoint', 'mode_inventory'):
        record = config[key]
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Recovery evidence changed')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('New close receipt output required')
    os.makedirs(output_dir, exist_ok=True)
    ui = importlib.import_module('cc_skingen_controls_v1')
    report = dict(success=False, diagnostic_mode='close_profile_editor_ui_only', config=config,
                  summary_path=os.path.join(output_dir, 'close_profile_editor_report.json'),
                  scope='One normal Close only; no geometry/material/expression acceptance', loads_performed=False)
    def checkpoint():
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])
    def identity():
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        selected = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
        state = dict(avatars=[dict(id=str(x.GetID()), name=str(x.GetName())) for x in avatars], selected=selected)
        if len(avatars) != 1 or str(avatars[0].GetID()) != config['expected_avatar_id'] or selected != [config['expected_avatar_id']]:
            raise ValueError('Exact same AF005 scene identity/selection changed')
        return state
    try:
        report['identity_before'] = identity()
        report['before'], _ = ui.capture(api, ['Eyebrow'])
        docks = [x for x in api.QtWidgets.QApplication.allWidgets() if isinstance(x, api.QtWidgets.QDockWidget)
                 and str(x.objectName()) == ':/plugin/CCAvatarShaping/ExpressionSliderSection.ui'
                 and str(x.windowTitle()) == 'Facial Profile Editor']
        if len(docks) != 1:
            raise ValueError('Unique inventoried Facial Profile Editor dock required')
        dock = docks[0]
        report['dock_before'] = ui.widget_record(dock)
        buttons = [x for x in dock.findChildren(api.QtWidgets.QToolButton)
                   if str(x.objectName()) == 'qtDockCloseWindowToolButton' and str(x.toolTip()) == 'Close']
        if len(buttons) != 1 or not dock.isVisible() or not dock.isEnabled() or not buttons[0].isVisible() or not buttons[0].isEnabled():
            raise ValueError('Exact visible enabled Close target required')
        button = buttons[0]
        report['button_before'] = ui.widget_record(button)
        audit = report.setdefault('close_guard', {})
        checkpoint()
        def close():
            raw = button.click()
            report['close_return'] = dict(python_type=type(raw).__name__, repr=repr(raw))
            report['close_clicked_once'] = True
            api.QtWidgets.QApplication.processEvents()
        ui.guarded_action(close, api, audit, checkpoint)
        report['identity_after'] = identity()
        report['dock_after'] = ui.widget_record(dock)
        report['after'], _ = ui.capture(api, ['Eyebrow'])
        if dock.isVisible():
            raise ValueError('Normal Close did not hide the inventoried editor dock')
        report['success'] = True
    except Exception as error:
        report['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    report['editing_checkpoint_unchanged'] = api.sha256_file(config['editing_checkpoint']['path']) == config['editing_checkpoint']['sha256']
    checkpoint()
    return report
