"""Bounded Headshot base assembly in CC; owner ASSEMBLY_AND_ACCEPTANCE.md.

Geometry is gated after every step against the input, including final save.
No identity, body recipe, subdivision switching, hair, wardrobe or export.
On failure the in-memory scene is restored from the immutable input; failed
receipts are retained and cannot be mistaken for a completed character.
"""
import importlib
import os
import sys
import traceback

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_base_assembly_20261005_v1'
CREATION_RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_character_creation_20261005_v1'


def inside(path, root):
    path, root = (os.path.normcase(os.path.realpath(p)) for p in (path, root))
    return os.path.commonpath([path, root]) == root


def geometry_modules():
    directory = os.path.dirname(__file__)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    return (importlib.import_module('cc_capture_assembly_geometry_v1'),
            importlib.import_module('cc_assembly_geometry_invariants_v1'))


def run(library, output_dir, log, api):
    config = library['base_assembly']
    output_dir = os.path.realpath(output_dir)
    if not any(inside(output_dir, root) for root in (RUN_ROOT, CREATION_RUN_ROOT)):
        raise ValueError('Base assembly run outside authorized root')
    source = config['source_project']
    target = config['output_project']
    if not inside(target, output_dir) or os.path.exists(target):
        raise ValueError('Output project must be new and inside this run')
    if os.path.realpath(source) == os.path.realpath(target):
        raise ValueError('Input cannot be overwritten')
    if api.sha256_file(source) != config['source_sha256']:
        raise ValueError('Input SHA changed')
    if api.sha256_file(config['regions_path']) != config['regions_sha256']:
        raise ValueError('Region partition SHA changed')
    assets = config['assets']
    if [a['slot'] for a in assets] != ['skin', 'eyebrows', 'eyelashes', 'eyes']:
        raise ValueError('Only skin/brows/lashes/eyes in fixed order are allowed')
    for asset in assets:
        if api.sha256_file(asset['path']) != asset['sha256']:
            raise ValueError('Asset SHA changed: ' + asset['asset_id'])
    settings = config['geometry_invariants']
    capture, invariants = geometry_modules()
    # First run is exemption-free. Subsequent allowances must match an exact,
    # source-evidenced and asset-specific registration; no arbitrary masks.
    approved_allowances = []
    policy_ref = config.get('geometry_policy')
    if policy_ref:
        registered_paths = [os.path.join(os.path.dirname(__file__), name) for name in (
            'cc_base_assembly_geometry_policy_v1.json', 'cc_base_assembly_geometry_policy_v2.json')]
        policy_path = os.path.realpath(policy_ref['path'])
        if os.path.normcase(policy_path) not in {os.path.normcase(os.path.realpath(path)) for path in registered_paths}:
            raise ValueError('Geometry policy must be the registered assembly policy')
        if api.sha256_file(policy_path) != policy_ref['sha256']:
            raise ValueError('Geometry policy SHA changed')
        policy = api.read_json(policy_path)
        # The offline compiler may already be cached in a long-lived CC session;
        # reload it so the SHA-bound policy is interpreted by current code.
        compiler = importlib.reload(importlib.import_module('cc_compile_headshot_base_assembly_v1'))
        try:
            approved_allowances = compiler.registered_allowance_for_sex(
                policy, config['eyelash_asset_id'], config.get('sex'))
        except compiler.CompileError as error:
            raise ValueError('Registered geometry allowance rejected: ' + str(error)) from error
    if settings != {'space': 'local', 'thresholds_mm': invariants.DEFAULT_TOLERANCE_MM,
                    'allowances': approved_allowances}:
        raise ValueError('Assembly policy requires0.002mm outside registered asset-specific allowances')
    regions = invariants.load_regions(config['regions_path'])
    report_path = os.path.join(output_dir, 'assembly_report.json')
    geometry_path = os.path.join(output_dir, 'assembly_geometry_invariants.json')
    report = {'schema_version': 1, 'success': False, 'character_id': config['character_id'],
              'started_at': api.now(), 'config': config, 'steps': [],
              'implementation_sha256': api.sha256_file(__file__),
              'visual_acceptance': 'pending', 'source_unchanged': None,
              'geometry_invariants_path': geometry_path,
              'summary_path': report_path, 'recovery': None}
    geometry = {'schema_version': 1, 'passed': False, 'space': 'local',
                'thresholds_mm': settings['thresholds_mm'], 'allowances': approved_allowances, 'steps': []}

    def phase(name, detail=None):
        report.update(phase=name, updated_at=api.now())
        if detail is not None:
            report['progress_detail'] = detail
        api.write_json(report, report_path)
        log('Headshot base assembly: ' + name)
        api.QtWidgets.QApplication.processEvents()

    def get_avatar():
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected one source avatar')
        return avatars[0]

    def check_geometry(name):
        after = capture.capture_body_snapshot(avatar, api=api, include_world=False,
                    output_path=os.path.join(output_dir, name + '_geometry.json'))
        comparison = invariants.compare_assembly_snapshots(before, after, regions,
                        space='local', tolerance_mm=settings['thresholds_mm'], allowances=approved_allowances)
        comparison['step'] = name
        geometry['steps'].append(comparison)
        geometry['passed'] = all(item['passed'] for item in geometry['steps'])
        api.write_json(geometry, geometry_path)
        if not comparison['passed']:
            raise ValueError('Protected geometry moved at ' + name + ': ' + ','.join(comparison['failed_regions']))
        return comparison

    try:
        phase('loading_independent_input')
        status, dialogs = api.load_file_with_optional_undo_warning(source, 'Load independent base-assembly input')
        report['load'] = {'status': status, 'dialogs': dialogs}
        avatar = get_avatar()
        api.RLPy.RScene.SelectObject(avatar)
        if list(avatar.GetHairs() or []) or api.avatar_asset_inventory(avatar)['object_count']:
            raise ValueError('Input must be bare, with no attached hair, wardrobe or props')
        before = capture.capture_body_snapshot(avatar, api=api, include_world=False,
                    output_path=os.path.join(output_dir, 'before_geometry.json'))
        report['working_subdivision_level'] = before['working_subdivision_level']
        for asset in assets:
            name = 'apply_' + asset['slot']
            phase(name)
            avatar, result = api.apply_appearance_assets(avatar, [asset], cleanup_names=[],
                    allow_missing_cleanup=True,
                    allow_verified_material_noop=True,
                    progress_callback=lambda p, d=None: phase(name + ':' + p, d))
            report['steps'].append({'step': name, 'application': result})
            check_geometry(name)
        phase('eyebrow_pigmentation')
        pigmentation = api.apply_shared_hair_pigmentation(avatar, config['hair_color'],
                            config['visible_gray_fraction'], target_domains=('eyebrows',))
        report['steps'].append({'step': 'eyebrow_pigmentation', 'result': pigmentation})
        check_geometry('eyebrow_pigmentation')
        profile = config.get('face_material_quality_profile')
        if profile:
            phase('face_material_quality')
            result = api.apply_face_material_quality_profile(avatar, profile)
            report['steps'].append({'step': 'face_material_quality', 'result': result})
            check_geometry('face_material_quality')
        phase('pre_save')
        if int(avatar.GetSubdivMeshLevel()) != before['working_subdivision_level']:
            raise ValueError('Assembly changed working subdivision')
        if list(avatar.GetHairs() or []):
            raise ValueError('Assembly unexpectedly added scalp hair')
        check_geometry('pre_save')
        if api.sha256_file(source) != config['source_sha256']:
            raise ValueError('Source changed during assembly')
        os.makedirs(os.path.dirname(target), exist_ok=True)
        phase('saving_independent_project')
        api.checked('Save independent assembled base character', api.RLPy.RFileIO.SaveProject(target))
        phase('post_save')
        check_geometry('post_save')
        report['saved_project'] = {'path': target, 'sha256': api.sha256_file(target),
                                    'bytes': os.path.getsize(target)}
        report['source_unchanged'] = api.sha256_file(source) == config['source_sha256']
        if not report['source_unchanged']:
            raise ValueError('Immutable input SHA changed after save')
        report['success'] = True
        phase('completed_awaiting_representative_visual_review')
    except Exception as exc:
        report['failed_phase'] = report.get('phase')
        report['error'] = {'type': type(exc).__name__, 'message': str(exc),
                           'traceback': traceback.format_exc()}
        report['success'] = False
        try:
            if api.sha256_file(source) != config['source_sha256']:
                raise ValueError('Cannot restore changed source')
            api.load_file_with_optional_undo_warning(source, 'Restore immutable input after failed assembly')
            report['recovery'] = {'status': 'restored_input', 'policy': 'Retry only this failed character in a new run; do not reprocess completed characters'}
        except Exception as restore_exc:
            report['recovery'] = {'status': 'restore_failed', 'error': str(restore_exc)}
        report['source_unchanged'] = api.sha256_file(source) == config['source_sha256']
        phase('failed')
    report['finished_at'] = api.now()
    api.write_json(report, report_path)
    return report
