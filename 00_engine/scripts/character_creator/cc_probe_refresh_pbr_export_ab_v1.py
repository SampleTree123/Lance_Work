"""One source, existing full export route, only the measured PBR flag differs.

Private API views leave the live SDK/module and original route unmodified.
Both branches reload the same SHA-bound source and refuse existing export roots.
"""
import copy
import importlib
import os

FLAG = 'EExportFbxOptions_ExportPbrTextureAsImageInFormatDirectory'


class View:
    def __init__(self, base, **overrides):
        self.base, self.overrides = base, overrides

    def __getattr__(self, name):
        return self.overrides[name] if name in self.overrides else getattr(self.base, name)


def settings_snapshot(setting):
    return {key: int(getattr(setting, method)()) for key, method in (
        ('option', 'GetOption'), ('option2', 'GetOption2'), ('option3', 'GetOption3'),
        ('texture_size', 'GetTextureSize'), ('texture_format', 'GetTextureFormat'))}


def export_call(sdk, api, branch, records):
    def invoke(avatar, path, setting):
        before = settings_snapshot(setting)
        bit = int(getattr(sdk, FLAG))
        if before['option'] & bit:
            raise ValueError('Baseline already has PBR format-directory flag; A/B no longer isolates its absence')
        if branch == 'B':
            api.checked('Enable only PBR format-directory export flag',
                        setting.SetOption(setting.GetOption() | getattr(sdk, FLAG)))
        after = settings_snapshot(setting)
        expected = dict(before)
        expected['option'] |= bit if branch == 'B' else 0
        if after != expected:
            raise ValueError('Native export settings differ beyond the single PBR flag')
        records.append({'branch': branch, 'path': path, 'before': before, 'actual': after,
                        'added_flag': FLAG if branch == 'B' else None,
                        'inverse_normal_y_unchanged': not ((before['option'] ^ after['option'])
                            & int(sdk.EExportFbxOptions_InverseNormalY))})
        return sdk.RFileIO.ExportFbxFile(avatar, path, setting)
    return invoke


def run(library, output_dir, log, api):
    config = library['refresh_pbr_export_ab']
    record = config['source_project']
    if api.sha256_file(record['path']) != record['sha256'] or os.path.getsize(record['path']) != record['bytes']:
        raise ValueError('A/B source pin changed')
    if config['character_id'] != 'CFD40_LM_002' or config['branches'] != ['A', 'B']:
        raise ValueError('This isolated experiment is exactly the male A/B pair')
    evidence = config['actual_material_probe']
    if api.sha256_file(evidence['path']) != evidence['sha256']:
        raise ValueError('Actual prior material probe changed')
    if api.read_json(evidence['path'])['expected_loaded_source'] != record:
        raise ValueError('A/B source differs from the actually measured final source')
    if int(getattr(api.RLPy, FLAG)) != config['measured_flag_value']:
        raise ValueError('SDK export flag differs from actual read-only probe')
    route = importlib.import_module('cc_headshot_route_validation_v1')
    results, calls = [], []
    for branch in config['branches']:
        subdir = os.path.join(output_dir, branch)
        os.makedirs(subdir, exist_ok=False)
        run_library = copy.deepcopy(library['existing_export_library'])
        route_config = run_library['headshot_route_validation']
        if route_config['source_project'] != record or route_config['export_repeat_count'] != 1:
            raise ValueError('Existing full export input changed')
        route_config['case_id'] = config['case_ids'][branch]
        io_view = View(api.RLPy.RFileIO, ExportFbxFile=export_call(api.RLPy, api, branch, calls))
        api_view = View(api, RLPy=View(api.RLPy, RFileIO=io_view))
        result = route.run(run_library, subdir, log, api_view)
        results.append({'branch': branch, 'result': result})
        api.write_json({'source_project': record, 'native_calls': calls, 'branches': results,
                       'success': False, 'diagnostic_only': True}, os.path.join(output_dir, 'pbr_export_ab_report.json'))
    if len(calls) != 2 or api.sha256_file(record['path']) != record['sha256']:
        raise ValueError('Expected exactly two exports with unchanged source file')
    report = {'success': True, 'diagnostic_only': True, 'source_project': record,
              'native_calls': calls, 'branches': results, 'accepted_final': False,
              'source_skin_normal_empty_before_export': True,
              'scope': 'A existing flags; B only PBR format-directory bit. Companion native_calls are actual GetOption readbacks; route export_settings records its unmodified baseline request.',
              'pbr_channel_completeness_verified': False, 'ue_imported': False}
    path = os.path.join(output_dir, 'pbr_export_ab_report.json')
    api.write_json(report, path)
    summary = {'success': True, 'report_path': path,
               'summary_path': os.path.join(output_dir, 'validation_result.json'), 'diagnostic_only': True}
    api.write_json(summary, summary['summary_path'])
    return summary
