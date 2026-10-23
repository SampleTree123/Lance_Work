"""AF005 continuation v2: real deselect/reselect event before readiness check.

Assembly Technical experimental owner; separate output, original v1 untouched.
"""
import importlib.util
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
V1_SHA = '72c7c7d0bb9f90616d83b40eaf28791f24cdae82a4af515282313f67b224ae68'


def run(library, output_dir, log, api):
    path = DIRECTORY / 'cc_resume_refresh_editing_checkpoint_v1.py'
    if api.sha256_file(str(path)) != V1_SHA:
        raise ValueError('Frozen continuation v1 changed')
    spec = importlib.util.spec_from_file_location('_selection_event_private_resume', path)
    resume = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resume)
    original = resume.transformed_runner
    def transformed(source):
        text = original(source)
        anchor = "            select_preset_avatar(api, avatar_id, audit['target_selection'])"
        if text.count(anchor) != 1:
            raise ValueError('Frozen target selection anchor changed')
        return text.replace(anchor, '''            audit['selection_reset'] = {'before': [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]}
            raw = api.RLPy.RScene.ClearSelectObjects()
            audit['selection_reset']['clear_status'] = probe.status_record(raw)
            api.checked('Clear stale selected target before checkpoint editor binding', raw)
            api.QtWidgets.QApplication.processEvents()
            audit['selection_reset']['after_clear'] = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
            checkpoint()
            if audit['selection_reset']['after_clear']:
                raise ValueError('Selection reset did not read back empty')
''' + anchor, 1)
    resume.transformed_runner = transformed
    return resume.run(library, output_dir, log, api)
