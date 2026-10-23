"""Close the now-readable original Makeup state; no further preset/source load.

Experimental Assembly Technical. Frozen full-save/reload closure retained;
the cancelled Add/Replace attempt and original failure remain separate facts.
"""
from pathlib import Path


def run(library, output_dir, log, api):
    config = library['checkpoint_repair']
    for key in ('existing_layer_report', 'cancelled_reentry_report'):
        record = config[key]
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Actual recovered-editor evidence changed')
    layers = api.read_json(config['existing_layer_report']['path'])
    prior = api.read_json(library['saved_editing_resume']['failed_report']['path'])
    if (not layers.get('success') or layers['after']['table']['row_count'] != 1
            or {'makeup': layers['operation']['persistence_signature']} != prior['layers_before_save']):
        raise ValueError('Actual one-row original Eyebrow100 recovery proof required')
    cancelled = api.read_json(config['cancelled_reentry_report']['path'])
    if (cancelled.get('success') is not False or len(cancelled.get('loads', [])) != 1
            or not cancelled['loads'][0].get('unknown_dialog')):
        raise ValueError('Exact prior cancelled reentry attempt required')
    path = Path(__file__).with_name('cc_repair_refresh_editing_checkpoint_v1.py')
    if api.sha256_file(str(path)) != '209cbae9ea21a539498edc5c9c6ea81aef7fc71a50081b86d6d34503bc31c37c':
        raise ValueError('Frozen full-closure repair implementation changed')
    source = path.read_text(encoding='utf-8-sig')
    source = source.replace("config.get('allow_same_selected_makeup_reentry') is not True or config.get('policy') != 'normal_navigation_then_same_makeup_once'",
        "config.get('allow_same_selected_makeup_reentry') is not False or config.get('policy') != 'closure_only_no_further_asset_load'", 1)
    first = '        if not _normal_entry(api, ui, report, checkpoint):\n'
    last = "        gate('after_checkpoint_ui_or_same_makeup_reentry', baseline)"
    if source.count(first) != 1 or source.count(last) != 1:
        raise ValueError('Frozen no-second-asset-load anchors changed')
    start, end = source.index(first), source.index(last)
    source = source[:start] + '''        if not _normal_entry(api, ui, report, checkpoint):
            raise ValueError('Current recovered editor must remain ready; no second asset load permitted')
''' + source[end:]
    source = source.replace('EDITING_repaired_same_selected_makeup.ccProject', 'EDITING_recovered_original_makeup.ccProject')
    source = source.replace("    report.pop('saved_editing_recovery', None)", """    report.pop('saved_editing_recovery', None)
    report['checkpoint_repair'].update(continuation_mode='current_editor_closure_no_second_asset_load',
        existing_layer_report=config['existing_layer_report'], cancelled_reentry_report=config['cancelled_reentry_report'],
        original_failure_report_unchanged=True, no_further_asset_load_permitted=True)""", 1)
    namespace = dict(__file__=__file__, __name__='_af005_recovered_editor_closure_private')
    exec(compile(source, str(path), 'exec'), namespace)
    return namespace['run'](library, output_dir, log, api)
