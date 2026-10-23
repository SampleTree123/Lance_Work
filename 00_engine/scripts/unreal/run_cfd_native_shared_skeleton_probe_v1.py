"""Two accepted CFD identities imported against isolated canonical Skeleton copies.

prepare is offline. setup/import/audit are root-only explicit editor operations.
The accepted per-identity HQ witnesses are reused read-only; only split geometry
is imported. Mesh-specific facial reference transforms are allowed to differ.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

import cfd_native_batch40_contract_v1 as common
import run_cfd_native_pair_transfer_v1 as pair

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[2]
RUN = REPO / '00_engine/outputs/unreal_character_import/cfd_native_shared_skeleton_probe_20261006_v1'
UE_ROOT = '/Game/DataMake/Validation/CFDNativeSharedSkeletonProbe20261006'
CONFIG = RUN / 'shared_probe_config.json'
BASELINE = RUN / 'shared_skeleton_baseline.json'
FACE_TRANSLATION_BONES = frozenset(('facialbone','jawroot','upperjaw','teeth01','teeth02',
                                   'tongue01','tongue02','tongue03','l_eye','r_eye'))


def shared_path(sex):
    return UE_ROOT + '/SharedSkeletons/SKEL_CFDShared_' + sex.title() + '_v1'


def prepare(canonical_registry, pair_manifest=pair.MANIFEST, pair_registry=pair.RUN / 'standard_candidate_registry.json'):
    canonical = {c['sex']:c for c in common.read(canonical_registry)['cases']}
    accepted = {c['sex']:c for c in common.read(pair_registry)['cases']}
    source_cases = common.read(pair_manifest)['cases']
    if len(source_cases) != 2 or set(canonical) != {'female','male'} or set(accepted) != set(canonical):
        raise ValueError('Exactly two canonical and accepted identity references are required')
    cases = []
    for source_case in source_cases:
        sex = source_case['sex']
        audit = common.read(accepted[sex]['audit'])
        if (not audit.get('success') or not audit.get('standard_candidate_ready')
                or audit['source']['sha256'] != source_case['fbx']['sha256']):
            raise ValueError('Identity witness is not an accepted import of this exact FBX')
        witness_root = audit.get('witness_root')
        if not witness_root or not all(m['material'].startswith(witness_root + '/')
                for mesh in audit['meshes'] for m in mesh['materials']):
            raise ValueError('Accepted materials are not contained by one recorded witness')
        identifier = 'CFD_SHARED_PROBE_' + sex.upper() + '_001'
        root = RUN / 'imports' / sex
        manifest = root / 'import_manifest.json'
        row = {**source_case, 'character_id': identifier, 'source_character_id': source_case['character_id']}
        pair.write_once(manifest, {'schema_version':1, 'cases':[row]})
        cases.append({'sex':sex, 'character_id':identifier, 'manifest':pair.source(manifest),
                      'canonical_skeleton':canonical[sex]['skeleton'], 'shared_skeleton':shared_path(sex),
                      'readonly_witness_root':witness_root, 'accepted_audit':pair.source(accepted[sex]['audit'])})
    config = {'schema_version':1, 'cases':cases, 'canonical_registry':pair.source(canonical_registry),
              'pair_registry':pair.source(pair_registry), 'pair_manifest':pair.source(pair_manifest),
              'scope':'Shared Skeleton copies only. Identity mesh facial reference differences are preserved and permitted.'}
    pair.write_once(CONFIG, config)
    return {'config':str(CONFIG), 'cases':[{k:c[k] for k in ('sex','canonical_skeleton','shared_skeleton')} for c in cases]}


def package_record(asset_path):
    import unreal
    package = asset_path.split('.', 1)[0]
    if not package.startswith('/Game/'):
        raise ValueError('Expected a project package')
    return pair.source(Path(unreal.Paths.project_content_dir()) / (package[6:] + '.uasset'))


def core():
    worker = common.module('ue_import_complete_character_skeleton_pilot_v1')
    worker.UE_ROOT = UE_ROOT
    return worker


def translation_modes(skeleton, require_face_skeleton=False):
    """Read only; BoneTree mutation is unavailable in this UE build."""
    import unreal
    pose = unreal.AnimPoseExtensions.get_reference_pose(skeleton)
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)]
    nodes = skeleton.get_editor_property('bone_tree')
    if len(names) != len(nodes) or len(set(names)) != len(names):
        raise RuntimeError('Reference bone order/BoneTree size mismatch')
    modes = {n:node.get_editor_property('translation_retargeting_mode') for n,node in zip(names,nodes)}
    if require_face_skeleton and (FACE_TRANSLATION_BONES - modes.keys() or
            any(modes[n] != unreal.BoneTranslationRetargetingMode.SKELETON for n in FACE_TRANSLATION_BONES)):
        raise RuntimeError('Copy source requires all ten face translation modes set to Skeleton')
    return {name:str(mode) for name,mode in modes.items()}


def checked_config():
    config = common.read(CONFIG)
    for key in ('canonical_registry','pair_registry','pair_manifest'):
        if pair.source(config[key]['path'])['sha256'] != config[key]['sha256']:
            raise ValueError('Probe input source changed: ' + key)
    for case in config['cases']:
        for key in ('manifest','accepted_audit'):
            if pair.source(case[key]['path'])['sha256'] != case[key]['sha256']:
                raise ValueError('Probe case evidence changed: ' + key)
        if bool(case.get('copy_source_skeleton')) != bool(case.get('copy_source_package')):
            raise ValueError('Optional copy source requires both Skeleton and pinned package')
        for key in ('copy_source_package','canonical_package'):
            if case.get(key) and pair.source(case[key]['path']) != case[key]:
                raise ValueError('Protected Skeleton package changed: ' + key)
    return config


def editor_setup():
    import unreal
    worker = core()
    config = checked_config()
    if BASELINE.exists():
        return verify_baseline()
    baseline = {'schema_version':1, 'success':False, 'cases':[]}
    for case in config['cases']:
        canonical = unreal.load_asset(case['canonical_skeleton'])
        if not isinstance(canonical, unreal.Skeleton):
            raise RuntimeError('Canonical Skeleton missing')
        protected = package_record(case['canonical_skeleton'])
        if case.get('canonical_package') and protected != case['canonical_package']:
            raise RuntimeError('Protected original canonical package changed')
        reference = worker.skeleton_reference_inventory(canonical)
        source = canonical
        copy_evidence = {}
        if case.get('copy_source_skeleton'):
            copy_path = case['copy_source_skeleton']
            if package_record(copy_path) != case['copy_source_package']:
                raise RuntimeError('Pinned copy source package changed')
            source = unreal.load_asset(copy_path)
            if not isinstance(source,unreal.Skeleton) or worker.skeleton_reference_inventory(source) != reference:
                raise RuntimeError('Copy source must preserve the canonical reference pose')
            modes = translation_modes(source,require_face_skeleton=True)
            copy_evidence = {'copy_source_skeleton':copy_path,'copy_source_package':case['copy_source_package'],
                             'translation_retargeting_modes':modes}
        destination = case['shared_skeleton']
        worker.guard(destination)
        if unreal.EditorAssetLibrary.does_asset_exist(destination):
            raise RuntimeError('Unowned shared Skeleton destination exists without committed baseline')
        folder,name = destination.rsplit('/', 1)
        copied = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,folder,source)
        if not isinstance(copied,unreal.Skeleton):
            raise RuntimeError('Cannot duplicate canonical Skeleton')
        worker.save(copied)
        copied_reference = worker.skeleton_reference_inventory(copied)
        if copied_reference != reference or package_record(case['canonical_skeleton']) != protected:
            raise RuntimeError('Skeleton copy changed reference facts or canonical source')
        if copy_evidence and (translation_modes(copied,require_face_skeleton=True) != modes
                or package_record(copy_path) != case['copy_source_package']):
            raise RuntimeError('Skeleton copy changed source package or translation retarget modes')
        baseline['cases'].append({'sex':case['sex'], 'canonical_skeleton':case['canonical_skeleton'],
            'canonical_package':protected, 'shared_skeleton':destination, 'reference':reference,
            'initial_copy_package':package_record(destination), **copy_evidence})
    baseline['success'] = True
    pair.write_once(BASELINE,baseline)
    return {'success':True,'baseline':str(BASELINE)}


def verify_baseline():
    import unreal
    worker = core()
    checked_config()
    baseline = common.read(BASELINE)
    if not baseline.get('success'):
        raise RuntimeError('Shared Skeleton setup is not committed')
    for case in baseline['cases']:
        if package_record(case['canonical_skeleton']) != case['canonical_package']:
            raise RuntimeError('Protected canonical Skeleton package changed')
        for path in (case['canonical_skeleton'],case['shared_skeleton']):
            if worker.skeleton_reference_inventory(unreal.load_asset(path)) != case['reference']:
                raise RuntimeError('Skeleton own reference changed: ' + path)
        if case.get('copy_source_skeleton'):
            if package_record(case['copy_source_skeleton']) != case['copy_source_package']:
                raise RuntimeError('Validated copy source package changed')
            for path in (case['copy_source_skeleton'],case['shared_skeleton']):
                skeleton = unreal.load_asset(path)
                if (worker.skeleton_reference_inventory(skeleton) != case['reference']
                        or translation_modes(skeleton,require_face_skeleton=True) != case['translation_retargeting_modes']):
                    raise RuntimeError('Validated copy reference or retarget modes changed: ' + path)
    return {'success':True,'canonical_packages_unchanged':True,'shared_reference_poses_unchanged':True,
            'copy_sources_and_translation_modes_unchanged':True}


def editor_import(sex, audit_only=False):
    import unreal
    config = checked_config()
    selected = [c for c in config['cases'] if c['sex'] == sex]
    if len(selected) != 1:
        raise ValueError('Unknown probe sex')
    case = selected[0]
    verify_baseline()
    worker = core()
    worker.REPORT_ROOT = Path(case['manifest']['path']).parent
    worker.REQUIRED_CASE_SEXES = (sex,)
    worker.SHARED_SKELETON_PATH = case['shared_skeleton']
    worker.READONLY_WITNESS_ROOT = case['readonly_witness_root']
    result = worker.main(case['manifest']['path'], audit_only=audit_only)
    integrity = verify_baseline()
    # The identity's mesh reference pose should survive sharing. This is a
    # same-FBX comparison against its accepted independent import, never a
    # demand that identity-specific facial bones equal the canonical face.
    from compare_complete_character_bone_standard_v1 import compare_bones
    accepted_audit = common.read(case['accepted_audit']['path'])
    imported_audit = common.read(result['cases'][0]['audit'])
    accepted_meshes = {mesh['role']:mesh for mesh in accepted_audit['meshes']}
    comparisons = []
    for mesh in imported_audit['meshes']:
        previous = accepted_meshes[mesh['role']]
        compared = compare_bones(previous['bones'], mesh['bones'])
        preserved = (not compared['missing_bones'] and not compared['extra_bones']
            and not compared['parent_differences'] and compared['max_translation_difference_cm'] <= 1e-6
            and compared['max_quaternion_sign_equivalent_difference'] <= 1e-6
            and compared['max_scale_component_difference'] <= 1e-6)
        comparisons.append({'role':mesh['role'], 'mesh':mesh['path'], 'preserved':preserved, **compared})
    integrity.update(identity_mesh_reference_comparison=comparisons,
                     identity_mesh_reference_preserved=all(row['preserved'] for row in comparisons))
    common.write(RUN / (sex + '_shared_integrity.json'),integrity)
    if not integrity['identity_mesh_reference_preserved']:
        raise RuntimeError('Shared import changed the identity mesh reference pose; inspect integrity report')
    if not audit_only:
        worker.save(unreal.load_asset(case['shared_skeleton']))
    integrity.update(character_id=case['character_id'],sex=sex,
                     actual_shared_package=package_record(case['shared_skeleton']),
                     mesh_reference_pose_equality_to_canonical_required=False)
    common.write(RUN / (sex + '_shared_integrity.json'),integrity)
    rows = []
    for other in config['cases']:
        path = Path(other['manifest']['path']).parent / 'standard_candidate_registry.json'
        if path.exists():
            rows.extend(common.read(path)['cases'])
    common.write(RUN / 'standard_candidate_registry.json',{'schema_version':1,'cases':rows,
                  'shared_by_sex':True,'common_male_female_skeleton':False,'human_acceptance':'pending'})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action',required=True,choices=('prepare','setup','import','audit','verify'))
    parser.add_argument('--canonical-registry')
    parser.add_argument('--pair-manifest',default=str(pair.MANIFEST))
    parser.add_argument('--pair-registry',default=str(pair.RUN/'standard_candidate_registry.json'))
    parser.add_argument('--sex',choices=('male','female','both'),default='both')
    parser.add_argument('--node-id')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not args.canonical_registry:
            parser.error('prepare requires explicit --canonical-registry')
        print(json.dumps(prepare(args.canonical_registry,args.pair_manifest,args.pair_registry),ensure_ascii=False))
        return
    helper = common.module('cfd_native_pair_ue_target_v1')
    helper.RUN,helper.TARGET_FILE = RUN,RUN/'ue_target.json'
    expressions = (['editor_setup()'] if args.action == 'setup' else ['verify_baseline()'] if args.action == 'verify'
                   else ['editor_import('+repr(sex)+',audit_only='+repr(args.action == 'audit')+')'
                         for sex in (('female','male') if args.sex == 'both' else (args.sex,))])
    for expression in expressions:
        run = RUN/'runner'/(args.action+'_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        command = ('import sys;sys.path.insert(0,'+repr(str(SCRIPTS))+');import run_cfd_native_shared_skeleton_probe_v1 as p;'
                   'print(p.'+expression+')')
        helper.remote(command,run,args.action,node_id=args.node_id,timeout=1200,unattended=True)


if __name__ == '__main__':
    main()
