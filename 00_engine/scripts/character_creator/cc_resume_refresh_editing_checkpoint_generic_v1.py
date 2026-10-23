"""Own-case adapter for the proven bounded editor-entry/short-root recovery.

Experimental Assembly Technical. Only an actual saved-editing readiness failure
may continue. Case, recipe, checkpoint and original layer signature come from
that case's failed durable job. No source rebuild, numeric or pixel allowance.
"""
from pathlib import Path
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parent
CORE_SHA = 'eea834e4e1c7bc4e5546e4c6be056ebcc06ef4864ded58104a951340a76008e0'
RESUME_SHA = '72c7c7d0bb9f90616d83b40eaf28791f24cdae82a4af515282313f67b224ae68'


def own_resume(library, api):
    config = library['bounded_editor_entry']
    reference = config['failed_serial_state']
    if api.sha256_file(reference['path']) != reference['sha256']:
        raise ValueError('Own failed serial state changed')
    state = api.read_json(reference['path'])
    recipe = library['refresh_assembly']
    identifier = recipe['character_id']
    step = state.get('steps', {}).get('01_prelash', {})
    if (state.get('status') != 'failed' or state.get('character_id') != identifier
            or step.get('status') != 'failed' or set(state.get('steps', {})) != {'01_prelash'}
            or config.get('character_id') != identifier):
        raise ValueError('Only this own failed PRELASH job may resume')
    for record in (step['library'], step['bridge_result'], library['saved_editing_resume']['failed_report']):
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Own failed job evidence changed')
    prior_library = api.read_json(step['library']['path'])
    terminal = api.read_json(step['bridge_result']['path'])
    prior = api.read_json(library['saved_editing_resume']['failed_report']['path'])
    if (prior_library['refresh_assembly'] != recipe or terminal.get('status') != 'failed'
            or terminal.get('job_id') != step['job_id']
            or Path(library['saved_editing_resume']['failed_report']['path']).resolve()
            != (Path(step['output_dir']) / 'refresh_partial_report.json').resolve()
            or prior['config'] != recipe
            or state['facts']['geometry']['result_project']['sha256'] != recipe['source_project']['sha256']):
        raise ValueError('Recovery must bind the actual own recipe, geometry and failed Bridge output')
    expected = config['expected_layers']
    if expected != prior['layers_before_save'] or set(expected) != {'makeup'} or set(expected['makeup']) != {'eyebrow'}:
        raise ValueError('Exact own original single Eyebrow layer signature required')
    row = expected['makeup']['eyebrow']
    if (type(row['opacity']) not in (int, float) or not 0 <= row['opacity'] <= 100
            or row['slider_opacity'] != row['opacity']
            or not isinstance(row['row_enable_flags_uninterpreted'], list)):
        raise ValueError('Own actual opacity/slider/flags signature is invalid')
    path = DIRECTORY / 'cc_resume_refresh_editing_checkpoint_v1.py'
    if api.sha256_file(str(path)) != RESUME_SHA:
        raise ValueError('Frozen saved-checkpoint validation changed')
    source = path.read_text(encoding='utf-8-sig')
    anchor = "recipe.get('character_id') != 'CFD40_AF_005'"
    if source.count(anchor) != 1:
        raise ValueError('Own-case provenance anchor changed')
    namespace = dict(__file__=str(path), __name__='_own_case_saved_checkpoint_private', _own_identifier=identifier)
    exec(compile(source.replace(anchor, "recipe.get('character_id') != _own_identifier", 1), str(path), 'exec'), namespace)
    return SimpleNamespace(**namespace)


def run(library, output_dir, log, api):
    core = DIRECTORY / 'cc_repair_refresh_editing_checkpoint_v3.py'
    if api.sha256_file(str(core)) != CORE_SHA:
        raise ValueError('Frozen actual normal-click/exact-Cancel recovery changed')
    source = core.read_text(encoding='utf-8-sig')
    anchor = '    resume = repair.private_resume(api)'
    if source.count(anchor) != 1:
        raise ValueError('Own-case resume binding anchor changed')
    source = source.replace(anchor, '    resume = _own_resume(library, api)', 1)
    anchor = "        if expected != {'makeup': {'eyebrow': {'opacity': 100, 'slider_opacity': 100, 'row_enable_flags_uninterpreted': False}}}:"
    if source.count(anchor) != 1:
        raise ValueError('Original own-layer signature anchor changed')
    source = source.replace(anchor, "        if expected != library['bounded_editor_entry']['expected_layers']:", 1)
    namespace = dict(__file__=__file__, __name__='_own_case_bounded_normal_entry_private', _own_resume=own_resume)
    exec(compile(source, str(core), 'exec'), namespace)
    return namespace['run'](library, output_dir, log, api)
