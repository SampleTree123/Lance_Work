"""Isolated CFD native pair transfer. Prepare is offline; editor calls are explicit.

Owner: Transfer13. No existing pilot source, level, or registry is rewritten.
Input spec: {"cases": [{"sex": "female", "character_id": "...",
"fbx": "...fbx", "source_project": "...ccProject"}, {...male...}]}.
Optional input_photo and creation_receipt paths are recorded with SHA256.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[2]
RUN = REPO / '00_engine/outputs/unreal_character_import/cfd_native_pair_20261006_v1'
UE_ROOT = '/Game/DataMake/Validation/CFDNativePair20261006'
MANIFEST = RUN / 'complete_character_import_manifest_v1.json'
LEVEL = UE_ROOT + '/L_DM_CFDNativePair_Review_v001'
ROLES = {'CC_Base_Body': 'body', 'CC_Base_Tongue': 'tongue',
         'CC_Base_Eye': 'eyes', 'CC_Base_Teeth': 'teeth',
         'CC_Base_TearLine': 'tearline', 'CC_Base_EyeOcclusion': 'eye_occlusion'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def source(path):
    path = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return {'path': str(path), 'sha256': h.hexdigest(), 'bytes': path.stat().st_size}


def write_once(path, value):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ValueError('Existing preparation differs; preserve evidence: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def expectation(extracted):
    rows = []
    names = [m['source_name'] for m in extracted['expected_meshes']]
    if len(names) != 6 or set(names) != set(ROLES):
        raise ValueError('Actual FBX is not the six-part native character: ' + repr(names))
    for mesh in extracted['expected_meshes']:
        row = {key: mesh[key] for key in ('source_name', 'model_name', 'expected_materials',
                                         'expected_nonzero_morph_names', 'position_delta_audit')}
        row.update(role=ROLES[mesh['source_name']], expected_morph_names=mesh['fbx_morph_names'],
                   fbx_morph_names=mesh['fbx_morph_names'])
        rows.append(row)
    return rows


def prepare(spec_path):
    spec = read(spec_path)
    cases = spec.get('cases', [])
    if len(cases) != 2 or {c.get('sex') for c in cases} != {'female', 'male'}:
        raise ValueError('Exactly one female and one male source are required')
    ids = [c['character_id'] for c in cases]
    if len(set(ids)) != 2 or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_]{0,63}', i) for i in ids):
        raise ValueError('Invalid or duplicate character IDs')
    sys.path.insert(0, str(REPO / '00_engine/scripts/character_creator'))
    from cc_extract_complete_fbx_source_v1 import extract
    manifest = {'schema_version': 1, 'pilot_id': RUN.name, 'cases': [],
                'scope': 'New native Headshot pair; complete static source transfer, isolated per-character Skeletons; prototype-only; human and motion acceptance pending.'}
    for case in sorted(cases, key=lambda c: c['sex']):
        fbx = Path(case['fbx']).resolve(strict=True)
        extracted = extract(fbx)
        # Preserve source evidence even when an unexpected component blocks the six-slot route.
        extract_path = RUN / ('fbx_source_extract_' + case['sex'] + '_v1.json')
        write_once(extract_path, extracted)
        row = {'character_id': case['character_id'], 'sex': case['sex'],
               'fbx': source(fbx), 'json': source(fbx.with_suffix('.json')),
               'source_project': source(case['source_project']), 'source_extract': source(extract_path),
               'expected_meshes': expectation(extracted), 'source_bone_count': extracted['bone_count'],
               'eyebrows_scope': 'Native Headshot skin appearance; no independent HD eyebrow assembly.',
               'source_limitations': ['No assumption that new identities share an accepted reference skeleton.',
                                      'Clothes/hair fit and body/facial motion require this pair review.']}
        for key in ('input_photo', 'creation_receipt'):
            if case.get(key):
                row[key] = source(case[key])
        manifest['cases'].append(row)
    write_once(MANIFEST, manifest)
    return {'manifest': str(MANIFEST), 'ue_root': UE_ROOT,
            'cases': [{'id': c['character_id'], 'parts': len(c['expected_meshes']),
                       'bones': c['source_bone_count'],
                       'morph_channels': sum(len(m['expected_morph_names']) for m in c['expected_meshes'])}
                      for c in manifest['cases']]}


def editor_import(audit_only=False):
    # A unique module avoids retargeting any already loaded legacy worker.
    path = SCRIPTS / 'ue_import_complete_character_skeleton_pilot_v1.py'
    spec = importlib.util.spec_from_file_location('_dm_cfd_native_pair_import_v1', path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    worker.REPORT_ROOT, worker.UE_ROOT = RUN, UE_ROOT
    worker.WITNESS_SUBDIR = 'MaterialWitnessInteractive'
    worker.WITNESS_AUTOMATED = False
    return worker.main(MANIFEST, audit_only=audit_only)


def remote_unattended(action):
    # CC AutoSetup's native options window must be allowed during the witness
    # import. Canceling it in unattended mode silently leaves generic materials.
    return action != 'import'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('prepare', 'status', 'import', 'audit', 'stage', 'open'), required=True)
    parser.add_argument('--spec')
    parser.add_argument('--request-file', help='Optional fixed-slot UI request for stage')
    parser.add_argument('--node-id', help='Must match this run ue_target.json')
    parser.add_argument('--launch', action='store_true', help='Unsupported for the explicitly bound running editor')
    parser.add_argument('--nullrhi', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not args.spec:
            parser.error('prepare requires --spec')
        print(json.dumps(prepare(args.spec), ensure_ascii=False))
        return
    if args.action == 'status':
        p = RUN / 'standard_candidate_registry.json'
        print(p.read_text(encoding='utf-8') if p.exists() else 'Not imported')
        return
    if args.action == 'open' and args.nullrhi:
        parser.error('Visual review requires a rendering editor')
    if args.launch:
        parser.error('This run binds an existing editor through ue_target.json; launch is disabled')
    from cfd_native_pair_ue_target_v1 import remote
    runner = RUN / 'runner' / (args.action + '_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    runner.mkdir(parents=True, exist_ok=True)
    if args.action in ('import', 'audit'):
        command = ('import runpy; m=runpy.run_path(' + repr(str(Path(__file__).resolve()))
                   + '); m["editor_import"](audit_only=' + repr(args.action == 'audit') + ')')
    elif args.action == 'stage':
        import run_complete_character_slot_review_v1 as panel
        if args.request_file:
            request = read(args.request_file)
        else:
            stage_args = panel.build_parser().parse_args(['--action', 'show', '--female-preset', '1',
                    '--male-preset', '1', '--female-hair', '2', '--male-hair', '2'])
            request = panel.cli_request(stage_args, panel.load_catalog())
        command = ('import sys,runpy; sys.path.insert(0,' + repr(str(SCRIPTS)) + '); runpy.run_path('
                   + repr(str(SCRIPTS / 'ue_cfd_native_pair_review_v1.py'))
                   + ',run_name="__main__",init_globals=' + repr({'DM_CFD_PAIR_STAGE': True,
                                                                       'DM_SLOT_REVIEW_REQUEST': request}) + ')')
    else:
        command = ('import unreal; levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); '
                   'assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Save current level changes first"; '
                   'assert levels.load_level(' + repr(LEVEL) + ')')
    result = remote(command, runner, args.action, timeout=1200, node_id=args.node_id,
                    unattended=remote_unattended(args.action))
    print(json.dumps({'success': result['command_result']['success'], 'action': args.action,
                      'runner': str(runner)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
