"""Prepare and resume bounded complete-character imports one identity at a time.

The 40-row source spec adds group A/B/L/W and group_index 1..5 to pair source
fields. prepare --character-id supports exports becoming ready incrementally.
Each witness import needs the native CC AutoSetup/FBX UI confirmation.
"""
import argparse
from datetime import datetime
import hashlib
import re
from pathlib import Path
import sys

import cfd_native_batch40_contract_v1 as contract
import run_cfd_native_pair_transfer_v1 as pair


def case_root(identifier):
    return contract.RUN / 'imports' / identifier


def split_subdir(identifier, expected):
    """One explicit, source-bound recovery; all other identities keep their paths."""
    path = case_root(identifier) / 'split_recovery_config.json'
    if not path.exists():
        return 'Meshes'
    config = contract.read(path)
    signature = hashlib.sha256(__import__('json').dumps(expected, sort_keys=True).encode()).hexdigest()
    value = config.get('split_subdir')
    if (identifier != 'CFD40_BM_001' or config.get('character_id') != identifier
            or config.get('schema_version') != 1 or config.get('input_fingerprint') != signature):
        raise ValueError('Split recovery must bind the interrupted BM001 manifest')
    if (not isinstance(value, str) or not re.fullmatch(r'MeshesRecovery[A-Za-z0-9_]{1,48}', value)):
        raise ValueError('Split recovery requires a safe new single directory name')
    return value


def prepare(spec_path, identifier=None):
    spec = contract.read(spec_path)
    cases = contract.validate_spec(spec)
    pair.write_once(contract.SPEC, spec)
    selected = [c for c in cases if identifier is None or c['character_id'] == identifier]
    if not selected:
        raise ValueError('Unknown character ID')
    sys.path.insert(0, str(contract.REPO / '00_engine/scripts/character_creator'))
    from cc_extract_complete_fbx_source_v1 import extract
    prepared = []
    for case in selected:
        root = case_root(case['character_id'])
        fbx = Path(case['fbx']).resolve(strict=True)
        extracted = extract(fbx)
        extract_path = root / 'fbx_source_extract_v1.json'
        pair.write_once(extract_path, extracted)
        row = {'character_id': case['character_id'], 'sex': case['sex'],
               'fbx': pair.source(fbx), 'json': pair.source(fbx.with_suffix('.json')),
               'source_project': pair.source(case['source_project']),
               'source_extract': pair.source(extract_path), 'expected_meshes': pair.expectation(extracted),
               'source_bone_count': extracted['bone_count'], 'group': case['group'], 'group_index': case['group_index'],
               'source_limitations': ['Prototype-only; per-identity fit and human review pending.'],
               'eyebrows_scope': 'Native Headshot skin brows; no independent HD eyebrow assembly.'}
        for key in ('input_photo', 'creation_receipt'):
            if case.get(key):
                row[key] = pair.source(case[key])
        pair.write_once(root / 'import_manifest.json', {'schema_version': 1, 'cases': [row]})
        prepared.append(case['character_id'])
    return {'prepared': prepared}


def refresh_registry():
    cases = contract.validate_spec(contract.read(contract.SPEC))
    shared_path = contract.RUN / 'shared_skeleton_config.json'
    shared = {c['sex']:c['shared_skeleton'] for c in common_shared_config()['cases']} if shared_path.exists() else {}
    committed, pending = [], []
    for case in cases:
        root = case_root(case['character_id'])
        registry_path = root / 'standard_candidate_registry.json'
        if not registry_path.exists():
            pending.append(case['character_id'])
            continue
        registry = contract.read(registry_path)
        manifest = root / 'import_manifest.json'
        if registry.get('manifest_sha256') != pair.source(manifest)['sha256']:
            raise ValueError('Imported manifest changed: ' + case['character_id'])
        rows = registry.get('cases', [])
        if len(rows) != 1 or rows[0]['character_id'] != case['character_id'] or not rows[0].get('standard_candidate_ready'):
            pending.append(case['character_id'])
            continue
        row = rows[0]
        audit = contract.read(row['audit'])
        if not audit.get('success') or not audit.get('all_source_morph_names_preserved'):
            pending.append(case['character_id'])
            continue
        reference = audit.get('shared_skeleton_reference_audit', {})
        if (row['skeleton'].split('.',1)[0] != shared.get(case['sex'])
                or reference.get('path') != shared.get(case['sex']) or reference.get('unchanged') is not True
                or audit.get('source_mesh_hierarchy_audit',{}).get('passed') is not True):
            raise ValueError('Completed identity does not pass the batch shared Skeleton contract: ' + case['character_id'])
        committed.append({**row, 'group': case['group'], 'group_index': case['group_index'],
                          'audit_source': pair.source(row['audit'])})
    result = {'schema_version': 1, 'cases': committed, 'pending': pending,
              'complete': len(committed) == 40, 'visual_acceptance': 'pending',
              'common_skeleton_adopted': bool(committed), 'shared_skeletons': shared}
    contract.write(contract.REGISTRY, result)
    return result


def editor_import(identifier, audit_only=False):
    hold_path = contract.RUN / 'operator_import_hold.json'
    if not audit_only and hold_path.exists() and contract.read(hold_path).get('active') is True:
        raise RuntimeError('Batch import held before starting next character: ' + str(hold_path))
    shared = shared_runtime()
    shared.verify_baseline()
    result = _import_character(identifier, audit_only)
    shared.verify_baseline()
    if not audit_only:
        try:
            result['package_release'] = release_saved_case_packages(identifier)
        finally:
            shared.verify_baseline()
    return result


def release_saved_case_packages(identifier):
    """Unload only this completed identity's already-loaded, saved packages."""
    cases = contract.validate_spec(contract.read(contract.SPEC))
    if len([c for c in cases if c['character_id'] == identifier]) != 1:
        raise ValueError('Unknown batch character')
    root = case_root(identifier)
    state = contract.read(root / identifier / 'import_state.json')
    audit = contract.read(root / identifier / 'import_audit.json')
    if (state.get('status') != 'audited' or audit.get('success') is not True
            or audit.get('standard_candidate_ready') is not True):
        raise RuntimeError('Package release requires a completed successful character audit')
    import gc
    import unreal
    prefix = contract.UE_ROOT + '/' + identifier + '/'
    receipt = root / ('package_release_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    record = {'schema_version':1,'character_id':identifier,'case_prefix':prefix,
              'success':False,'packages':[],'dirty_packages':[],'any_packages_unloaded':False,
              'skipped_empty':False,'error':''}
    packages = []
    try:
        packages = [p for p in unreal.ObjectIterator(unreal.Package)
                    if p.get_path_name().startswith(prefix)]
        record['packages'] = sorted(p.get_path_name() for p in packages)
        dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        record['dirty_packages'] = sorted(dirty.intersection(record['packages']))
        if record['dirty_packages']:
            raise RuntimeError('Refuse to unload unsaved current character packages')
        if packages:
            unloaded, error = unreal.EditorLoadingAndSavingUtils.unload_packages(packages)
            record['any_packages_unloaded'], record['error'] = bool(unloaded), str(error)
            if not unloaded or record['error']:
                raise RuntimeError('Current character package unload failed: ' + record['error'])
        else:
            record['skipped_empty'] = True
        packages.clear()
        gc.collect()
        unreal.SystemLibrary.collect_garbage()
        # Package objects can remain after a successful unload; this is evidence,
        # not a requirement that every package object disappears.
        record['remaining_loaded_packages'] = sorted(p.get_path_name() for p in unreal.ObjectIterator(unreal.Package)
                                                     if p.get_path_name().startswith(prefix))
        record['success'] = True
    except Exception as error:
        record['failure'] = str(error)
        raise
    finally:
        packages.clear()
        contract.write(receipt, record)
    return {'receipt':str(receipt),'success':True,'skipped_empty':record['skipped_empty'],
            'selected_count':len(record['packages']),'any_packages_unloaded':record['any_packages_unloaded']}


def _import_character(identifier, audit_only=False):
    cases = contract.validate_spec(contract.read(contract.SPEC))
    selected = [c for c in cases if c['character_id'] == identifier]
    if len(selected) != 1:
        raise ValueError('Unknown batch character')
    case = selected[0]
    root = case_root(identifier)
    manifest = root / 'import_manifest.json'
    worker = contract.module('ue_import_complete_character_skeleton_pilot_v1')
    worker.REPORT_ROOT, worker.UE_ROOT = root, contract.UE_ROOT
    worker.REQUIRED_CASE_SEXES = (case['sex'],)
    shared = shared_runtime()
    shared_config = common_shared_config()
    worker.SHARED_SKELETON_PATH = next(c['shared_skeleton'] for c in shared_config['cases'] if c['sex'] == case['sex'])
    worker.WITNESS_SUBDIR, worker.WITNESS_AUTOMATED = 'MaterialWitnessInteractive', False
    expected = contract.read(manifest)['cases'][0]
    worker.SPLIT_SUBDIR = split_subdir(identifier, expected)
    for field in ('fbx', 'json', 'source_extract', 'source_project'):
        worker.source_record(expected, field)
    state = root / identifier / 'import_state.json'
    audit_path = root / identifier / 'import_audit.json'
    if not audit_only and state.exists() and audit_path.exists():
        old_state, old_audit = contract.read(state), contract.read(audit_path)
        signature = hashlib.sha256(__import__('json').dumps(expected, sort_keys=True).encode()).hexdigest()
        if old_state.get('input_fingerprint') != signature:
            raise ValueError('Existing import input/config changed')
        if old_state.get('status') == 'audited' and old_audit.get('success') and old_audit.get('standard_candidate_ready'):
            if old_state.get('split_subdir', 'Meshes') != worker.SPLIT_SUBDIR:
                raise ValueError('Completed import split directory cannot change')
            refresh_registry()
            return {'skipped_completed': True, 'character_id': identifier}
    # Preserve each failed previous receipt before the importer writes its next result.
    if audit_path.exists() and not contract.read(audit_path).get('success'):
        old = contract.read(audit_path)
        pair.write_once(audit_path.with_name('failed_' + pair.source(audit_path)['sha256'][:12] + '.json'), old)
    result = worker.main(manifest, audit_only=audit_only)
    shared.verify_baseline()
    if not audit_only:
        worker.save(worker.unreal.load_asset(worker.SHARED_SKELETON_PATH))
    refresh_registry()
    return result


def common_shared_config():
    path = contract.RUN / 'shared_skeleton_config.json'
    if not path.exists():
        raise RuntimeError('Run prepare-shared and setup-shared after the accepted two-person representative gate')
    config = contract.read(path)
    acceptance = config.get('representative_acceptance')
    if not acceptance or pair.source(acceptance['path'])['sha256'] != acceptance['sha256']:
        raise RuntimeError('Representative dynamic/visual acceptance is missing or changed')
    validate_acceptance(contract.read(acceptance['path']))
    for record in config.get('representative_gate', []):
        if pair.source(record['path'])['sha256'] != record['sha256']:
            raise RuntimeError('Shared representative gate evidence changed')
        gate = contract.read(record['path'])
        if not gate.get('success') or not gate.get('identity_mesh_reference_preserved'):
            raise RuntimeError('Shared representative gate did not pass')
    if len(config.get('representative_gate', [])) != 2:
        raise RuntimeError('Both shared representative gates are required')
    return config


def validate_acceptance(value):
    if (set(value.get('sexes',[])) != {'female','male'}
            or any(value.get(key) is not True for key in ('success','morph_passed','skeletal_animation_passed','visual_accepted'))
            or not value.get('evidence')):
        raise RuntimeError('Both representatives must pass Morph, skeletal animation and visual acceptance with evidence')


def prepare_shared(probe_root, acceptance_receipt):
    probe_root = Path(probe_root).resolve()
    validate_acceptance(contract.read(acceptance_receipt))
    original = contract.read(probe_root / 'shared_probe_config.json')
    baseline = contract.read(probe_root / 'shared_skeleton_baseline.json')
    if baseline.get('success') is not True:
        raise RuntimeError('Representative shared Skeleton baseline is not committed')
    baseline_cases = {c['sex']:c for c in baseline['cases']}
    gates = []
    for sex in ('female','male'):
        path = probe_root / (sex + '_shared_integrity.json')
        gate = contract.read(path)
        if not gate.get('success') or not gate.get('identity_mesh_reference_preserved'):
            raise RuntimeError('Shared probe has not passed for ' + sex)
        gates.append(pair.source(path))
    copied_cases = []
    for case in original['cases']:
        source = baseline_cases[case['sex']]
        if (source['shared_skeleton'] != case['shared_skeleton'] or source['canonical_skeleton'] != case['canonical_skeleton']
                or pair.source(source['canonical_package']['path']) != source['canonical_package']):
            raise RuntimeError('Canonical protection or representative copy identity changed')
        copied_cases.append({**case,
            'shared_skeleton':contract.UE_ROOT+'/SharedSkeletons/SKEL_CFDShared_'+case['sex'].title()+'_v1',
            'canonical_package':source['canonical_package'],
            'copy_source_skeleton':source['shared_skeleton'],
            'copy_source_package':pair.source(source['initial_copy_package']['path'])})
    config = {**original, 'representative_gate':gates, 'representative_acceptance':pair.source(acceptance_receipt),
              'cases':copied_cases}
    pair.write_once(contract.RUN / 'shared_skeleton_config.json',config)
    return {'config':str(contract.RUN / 'shared_skeleton_config.json')}


def shared_runtime():
    common_shared_config()
    shared = contract.module('run_cfd_native_shared_skeleton_probe_v1')
    shared.RUN,shared.UE_ROOT = contract.RUN,contract.UE_ROOT
    shared.CONFIG = contract.RUN / 'shared_skeleton_config.json'
    shared.BASELINE = contract.RUN / 'shared_skeleton_baseline.json'
    return shared


def editor_setup_shared():
    return shared_runtime().editor_setup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', required=True, choices=('prepare', 'prepare-shared', 'setup-shared', 'status', 'import', 'audit'))
    parser.add_argument('--spec')
    parser.add_argument('--probe-root', default=str(contract.RUN.parent/'cfd_native_shared_skeleton_probe_20261006_v1'))
    parser.add_argument('--acceptance-receipt', help='Both-sex dynamic and human visual acceptance JSON')
    parser.add_argument('--character-id')
    parser.add_argument('--all', action='store_true', help='Sequential native import windows, stops on first failure')
    parser.add_argument('--node-id')
    args = parser.parse_args()
    if args.action == 'prepare-shared':
        if not args.acceptance_receipt:
            parser.error('prepare-shared requires --acceptance-receipt after representative validation')
        print(prepare_shared(args.probe_root, args.acceptance_receipt))
        return
    if args.action == 'setup-shared':
        run = contract.RUN / 'runner' / ('setup_shared_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
        command = ('import sys;sys.path.insert(0,'+repr(str(contract.SCRIPTS))+');'
                   'import run_cfd_native_batch40_transfer_v1 as b;print(b.editor_setup_shared())')
        contract.target_remote()(command,run,'setup_shared',node_id=args.node_id)
        return
    if args.action == 'prepare':
        if not args.spec:
            parser.error('prepare requires --spec')
        print(prepare(args.spec, args.character_id))
        return
    if args.action == 'status':
        data = refresh_registry()
        print({'completed': len(data['cases']), 'pending': data['pending']})
        return
    if bool(args.character_id) == bool(args.all):
        parser.error('Select --character-id or --all')
    cases = contract.validate_spec(contract.read(contract.SPEC))
    selected = [c for c in cases if args.all or c['character_id'] == args.character_id]
    if not selected:
        parser.error('Unknown character ID')
    remote = contract.target_remote()
    for case in selected:
        run = contract.RUN / 'runner' / (datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + case['character_id'])
        command = ('import sys,runpy;sys.path.insert(0,' + repr(str(contract.SCRIPTS)) + '); m=runpy.run_path('
                   + repr(str(Path(__file__).resolve())) + ');print(m["editor_import"]('
                   + repr(case['character_id']) + ',audit_only=' + repr(args.action == 'audit') + '))')
        remote(command, run, args.action, timeout=1800, node_id=args.node_id, unattended=args.action != 'import')
        print({'completed_action': args.action, 'character_id': case['character_id']}, flush=True)


if __name__ == '__main__':
    main()
