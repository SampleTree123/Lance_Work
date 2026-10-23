"""One exact redness preset after explicit Skin category; always restore backup.

No opacity write, full appearance rerun, material repair or generic OK policy.
The input is a separately saved/hash-bound current partial, not an accepted
recipe. Actual layer names, generic LoadFile result and geometry are evidence.
"""
import importlib
import os
import sys
import traceback
from types import SimpleNamespace

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
NATIVE_NAMES = frozenset(('CC_Base_Body', 'CC_Base_Eye', 'CC_Base_EyeOcclusion',
    'CC_Base_TearLine', 'CC_Base_Teeth', 'CC_Base_Tongue'))


def diagnostic_native_geometry(snapshot):
    """Retain the true working level, including1; this is not final acceptance."""
    if snapshot['working_subdivision'] not in (0, 1):
        raise ValueError('Only actual working levels0/1 supported for diagnostic')
    selected = dict(snapshot)
    selected['meshes'] = [row for row in snapshot['meshes'] if row['name'] in NATIVE_NAMES]
    if {row['name'] for row in selected['meshes']} != NATIVE_NAMES:
        raise ValueError('Body/all five native support mesh kinds required')
    keys = [tuple(row[key] for key in ('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256')) for row in selected['meshes']]
    if len(keys) != len(set(keys)):
        raise ValueError('Ambiguous native diagnostic geometry')
    owners = {row['owner'] for row in selected['meshes']}
    selected['parts'] = [row for row in snapshot['parts'] if row['name'] in NATIVE_NAMES]
    selected['owner_transforms'] = [row for row in snapshot['owner_transforms'] if row['owner'] in owners]
    selected['owner_transform_errors'] = [row for row in snapshot.get('owner_transform_errors', []) if row['owner'] in owners]
    available = {(row['owner'], row['space']) for row in selected['owner_transforms']}
    if selected['owner_transform_errors'] or any((owner, space) not in available for owner in owners for space in ('local', 'world')):
        raise ValueError('Native diagnostic owner transform evidence incomplete')
    return selected


def validate(config, output_dir, api, probe, runner):
    if config.get('restore_source_on_completion') is not True or config.get('recipe_complete') is not False:
        raise ValueError('Diagnostic-only and unconditional source restoration required')
    if not probe.inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('Independent task output child required')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse existing redness probe output')
    source = probe.reference(config['source_project'], api, '.ccproject', (RUN_ROOT,))
    runner.redness_contract(config['asset'], config['sex'])
    if api.sha256_file(config['asset']['path']) != config['asset']['sha256']:
        raise ValueError('Exact redness asset SHA changed')
    if config.get('preserve_modified_materials') is not True:
        raise ValueError('Explicit exact keep-modified-materials policy required')
    return source


def run(library, output_dir, log, api):
    directory = os.path.dirname(__file__)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    probe = importlib.reload(importlib.import_module('cc_makeup_probe_v1'))
    ui = importlib.reload(importlib.import_module('cc_skingen_controls_v1'))
    runner = importlib.import_module('cc_run_character_refresh_v1')
    body_capture = importlib.import_module('cc_capture_assembly_geometry_v1')
    geometry = importlib.import_module('cc_repair_headshot_support_materials_v1')
    config = library['redness_probe']
    source = validate(config, output_dir, api, probe, runner)
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, 'DIAGNOSTIC_skin_category_redness.ccProject')
    report = {'diagnostic_mode': 'redness_probe', 'success': False, 'recipe_complete': False,
        'diagnostic_only': True, 'source_project': config['source_project'], 'asset': config['asset'],
        'loads': [], 'control_steps': [], 'geometry_snapshots': {}, 'geometry_checks': [],
        'opacity_written': False, 'source_restored': False,
        'final_geometry_accepted': False, 'subdivision_switch_performed': False,
        'summary_path': os.path.join(output_dir, 'redness_probe_report.json'),
        'implementation_sha256': api.sha256_file(__file__),
        'scope': 'One SHA-bound redness LoadFile after explicit Skin category; same-actual-level Body14164 local and all native support diagnostics, no subdivision switch/force evaluation, independent diagnostic save and unconditional backup reload. Not final SubD0 acceptance.'}
    read_api = SimpleNamespace(_transform_data=api._transform_data)
    baseline_body, baseline_support, original_level = None, None, None
    source_load_attempted = False

    def checkpoint(phase=None):
        if phase:
            report['phase'] = phase
            log('Redness category probe: ' + phase)
        report['updated_at'] = api.now()
        api.write_json(report, report['summary_path'])

    def avatar():
        items = list(api.RLPy.RScene.GetAvatars() or [])
        if len(items) != 1:
            raise ValueError('Exactly one current avatar required')
        return items[0]

    def control(label, operation, **options):
        receipt = {'phase': label}
        report['control_steps'].append(receipt)
        checkpoint(label)
        receipt['result'] = ui.guarded_action(operation, api, receipt, checkpoint, **options)
        checkpoint()
        return receipt['result']

    def inspect(label):
        state, _ = ui.capture(api)
        path = os.path.join(output_dir, label + '_skingen.json')
        api.write_json(state, path)
        report[label] = {'path': path, 'sha256': api.sha256_file(path), 'state': state}
        checkpoint()
        return state

    def measure(label):
        level = int(avatar().GetSubdivMeshLevel())
        if level not in (0, 1):
            raise ValueError('Only observed working levels0/1 supported')
        body = body_capture.capture_body_snapshot(avatar(), api=read_api, include_world=False,
            output_path=os.path.join(output_dir, label + '_body.json'))
        supports = diagnostic_native_geometry(geometry.capture_geometry(avatar(), api))
        repeated = diagnostic_native_geometry(geometry.capture_geometry(avatar(), api))
        readback = geometry.compare_geometry(supports, repeated)
        if not readback['passed'] or readback['maximum_local_delta_mm'] > .001:
            raise ValueError('Same-level native geometry readback inconsistent')
        supports['repeated_readback'] = readback
        support_path = os.path.join(output_dir, label + '_support.json')
        api.write_json(supports, support_path)
        report['geometry_snapshots'][label] = {'actual_working_level': level,
            'body': {'path': os.path.join(output_dir, label + '_body.json'),
            'sha256': api.sha256_file(os.path.join(output_dir, label + '_body.json'))},
            'support': {'path': support_path, 'sha256': api.sha256_file(support_path)}}
        if baseline_body is not None:
            if body['working_subdivision_level'] != baseline_body['working_subdivision_level']:
                raise ValueError('Load changed actual working level; same-level diagnostic refused')
            local = runner.local_cage_diagnostic(baseline_body, body)
            native = geometry.compare_geometry(baseline_support, supports)
            check = {'phase': label, 'body_local_diagnostic': local, 'all_native_support': native,
                'diagnostic_equal': local['maximum_displacement_mm'] <= .002 and native['passed'],
                'final_geometry_accepted': False, 'same_actual_working_level': level}
            report['geometry_checks'].append(check)
            checkpoint()
            if not check['diagnostic_equal']:
                raise ValueError('Same-level Body/native support diagnostic changed: ' + label)
        else:
            runner.local_cage_diagnostic(body, body)
        return body, supports

    try:
        checkpoint('load_hash_bound_partial_backup')
        source_load_attempted = True
        probe.guarded_load(source, 'Load independent current partial backup', api, report['loads'], checkpoint)
        original_level = int(avatar().GetSubdivMeshLevel())
        inspect('backup_loaded_before_any_category_change')
        baseline_body, baseline_support = measure('backup_baseline')
        target_id = str(avatar().GetID())
        selection = report.setdefault('selection_before_skin_navigation', {})
        def select_backup_avatar():
            runner.select_preset_avatar(api, target_id, selection)
            return selection
        control('select_backup_avatar', select_backup_avatar)
        control('reveal_exact_editor', lambda: ui.reveal_editor(api))
        control('activate_exact_editor', lambda: ui.activate_editor(
            ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *ui.SELECTORS['editor'])))
        control('select_makeup_verify_backup_layer', lambda: ui.select_category(api, 'makeup'))
        report['backup_eyebrow_readback'] = control('verify_saved_backup_eyebrow', lambda: ui.read_layer_opacity(api, 'Eyebrow'))
        control('select_skin_before_redness', lambda: ui.select_category(api, 'skin'))
        state = inspect('skin_context_before_load')
        if state['controls']['material'].get('currentText') != 'Head':
            raise ValueError('Skin context must already target Head; refusing guessed material selection')
        if state['controls']['skin'].get('isChecked') is not True:
            raise ValueError('Skin category did not read back checked')

        def load_one():
            runner.select_preset_avatar(api, target_id, report.setdefault('selection_immediately_before_asset', {}))
            checkpoint('load_one_redness_after_skin_category')
            raw = api.RLPy.RFileIO.LoadFile(config['asset']['path'])
            report['asset_raw_status'] = probe.status_record(raw)
            checkpoint()
            if raw is None or not callable(getattr(raw, 'IsError', None)):
                raise ValueError('Missing inspectable redness LoadFile RStatus')
            api.checked('Load exactly one redness preset after Skin category', raw)
            return report['asset_raw_status']

        control('load_one_redness_after_skin_category', load_one,
            preserve_modified_materials=True, stage='redness_preset')
        inspect('after_redness_load_actual_layers')
        measure('after_redness_load')

        def save_candidate():
            if os.path.exists(target):
                raise ValueError('Refuse diagnostic candidate overwrite')
            raw = api.RLPy.RFileIO.SaveProject(target)
            report['save_status'] = probe.status_record(raw)
            checkpoint()
            if raw is None or not callable(getattr(raw, 'IsError', None)):
                raise ValueError('Missing inspectable SaveProject RStatus')
            api.checked('Save independent redness diagnostic only', raw)

        control('save_diagnostic_candidate', save_candidate)
        report['candidate'] = {'path': target, 'sha256': api.sha256_file(target)}
        report['load_and_geometry_passed'] = True
    except Exception as exc:
        report['error'] = {'message': str(exc), 'traceback': traceback.format_exc()}
        checkpoint('redness_probe_failed_before_restore')
    finally:
        if source_load_attempted:
            try:
                checkpoint('restore_hash_bound_partial_backup')
                probe.guarded_load(source, 'Restore independent current partial backup', api, report['loads'], checkpoint)
                inspect('restored_backup_actual_layers')
                if baseline_body is not None:
                    measure('restored_backup')
                report['source_restored'] = (api.sha256_file(source) == config['source_project']['sha256']
                    and int(avatar().GetSubdivMeshLevel()) == original_level and baseline_body is not None)
                if not report['source_restored']:
                    raise ValueError('Restored source hash/working-level/geometry evidence incomplete')
            except Exception as exc:
                report['restore_error'] = {'message': str(exc), 'traceback': traceback.format_exc()}
        report['success'] = report.get('load_and_geometry_passed') is True and report['source_restored'] is True and 'error' not in report and 'restore_error' not in report
        checkpoint('redness_probe_completed_restored' if report['success'] else 'redness_probe_failed_restoration_recorded')
    return report
