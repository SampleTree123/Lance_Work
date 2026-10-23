"""Load the immutable AF005 editing checkpoint once, then return to CC idle.

Experimental Assembly Technical owner. Layer/UI inspection is a separate job;
no assets, layer writes, subdivision transitions, geometry evaluation or save.
"""
import importlib
import os
import traceback


def run(library, output_dir, log, api):
    config = library['load_editing_checkpoint']
    if config['character_id'] != 'CFD40_AF_005' or config['checkpoint']['sha256'] != 'c9841c2094b13ee0854b0f6bdc9320e1cbbc133c3f4b4f7bc3e825c0e4520f5f':
        raise ValueError('Exact original AF005 editing checkpoint required')
    record = config['checkpoint']
    if api.sha256_file(record['path']) != record['sha256']:
        raise ValueError('Immutable checkpoint changed')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('New load receipt output required')
    os.makedirs(output_dir, exist_ok=True)
    probe = importlib.import_module('cc_makeup_probe_v1')
    report = dict(success=False, diagnostic_mode='load_editing_checkpoint_once', config=config, loads=[],
                  source_unchanged=False, summary_path=os.path.join(output_dir, 'load_editing_checkpoint_report.json'))
    def checkpoint():
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])
    try:
        probe.guarded_load(record['path'], 'Load original AF005 editing checkpoint once in user-restarted CC', api, report['loads'], checkpoint)
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('One actual checkpoint avatar required')
        avatar = avatars[0]
        report['avatar'] = dict(id=str(avatar.GetID()), name=str(avatar.GetName()), python_type=type(avatar).__name__,
                                working_subdivision=int(avatar.GetSubdivMeshLevel()), avatar_type=int(avatar.GetAvatarType()))
        report['selected'] = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
        report['source_unchanged'] = api.sha256_file(record['path']) == record['sha256']
        if not report['source_unchanged']:
            raise ValueError('Source checkpoint changed during load')
        report['success'] = True
    except Exception as error:
        report['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    checkpoint()
    return report
