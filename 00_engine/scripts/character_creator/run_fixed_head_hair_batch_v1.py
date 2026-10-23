"""Resumable fixed-head hair controller. Owner: CC_TO_UE_MODULAR_OUTFIT_PILOT.md."""
from pathlib import Path
import argparse, datetime, hashlib, json, subprocess, sys, time

REPO = Path(__file__).resolve().parents[3]
BRIDGE = REPO / '00_engine/outputs/character_creator_bridge'
RUN = BRIDGE / 'artifacts/fixed_head_hair_20261004_v1'
STAGE = REPO / '00_engine/scripts/character_creator/runtime_staging/fixed_head_hair_20261004_v1'
OLD = BRIDGE / 'artifacts/headshot_route_compare_20261002_v1'
OLD_STAGE = STAGE.parent / 'headshot_route_compare_20261002_v1'
EXPORT = Path(r'D:\UE\exports\character_creator\fixed_head_hair_20261004_v1')
CLIENT = REPO / '00_engine/character_creator_bridge/cc_bridge_client.py'
MANIFEST = EXPORT / 'manifests/batch.json'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)

def record(path):
    path = Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def now():
    return datetime.datetime.now().astimezone().isoformat()

def template(sex):
    doc = read(OLD_STAGE / (('female01' if sex == 'female' else 'male01') + '_final_visual_prepare_v1.json'))
    for key in ['headshot_route_validation', 'headshot_photo_probe', 'headshot_mesh_replace']:
        doc.pop(key, None)
    doc.update(diagnostic_mode='fixed_head_hair_batch', eye_snapshot_mode='transforms_only')
    return doc

def health():
    p = subprocess.run([sys.executable, str(CLIENT), 'health'], capture_output=True,
                       text=True, encoding='utf-8', check=True)
    return json.loads(p.stdout)

def job(name, doc):
    name = 'fixed_head_hair_' + name
    result_path = BRIDGE / 'results' / (name + '.json')
    config_path = STAGE / (name + '.json')
    output_dir = RUN / 'jobs' / name
    if config_path.exists():
        if read(config_path) != doc:
            raise ValueError('Existing job config differs: ' + name)
    else:
        write(config_path, doc)
    if not result_path.exists():
        h = health(); active = h['heartbeat'].get('active_job_id')
        queued = any((BRIDGE / area / (name + '.json')).exists() for area in ['inbox', 'processing'])
        if active and active != name:
            raise RuntimeError('Other CC job active: ' + active)
        if not queued and active != name:
            if not h['healthy']:
                raise RuntimeError('CC bridge unhealthy')
            cmd = [sys.executable, str(CLIENT), 'validate-bodies', '--library-file', str(config_path),
                   '--output-dir', str(output_dir), '--confirm-scene-replace',
                   '--auto-dismiss-undo-warning', '--job-id', name, '--no-wait']
            p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if p.returncode:
                raise RuntimeError(p.stdout + p.stderr)
        write(RUN / 'live.json', {'updated_at': now(), 'job_id': name,
                                'result_path': str(result_path), 'phase': 'waiting'})
        print('Waiting ' + name, flush=True)
        while not result_path.exists():
            time.sleep(2)
    result = read(result_path)
    if result['status'] != 'succeeded':
        # The legacy exporter can finish all files and fail only at publishing
        # the staging directory if its target parent does not yet exist.
        c = doc['fixed_head_hair_batch']
        attempt_file = output_dir / (c.get('export_basename', '') + '_export_attempt.json')
        if c['action'] == 'export' and result.get('error', {}).get('type') == 'FileNotFoundError' and attempt_file.exists():
            a = read(attempt_file); staging = Path(a['attempt_root']).resolve(); target = Path(c['export_root']).resolve()
            staging_root = Path(r'D:\UE\exports\character_creator\.fbx_stage').resolve()
            if not staging.is_relative_to(staging_root) or not target.is_relative_to(EXPORT.resolve()):
                raise ValueError('Recovery path escaped expected roots')
            recovery = output_dir / 'export_recovery.json'
            if not recovery.exists():
                checked = exported(c['export_basename'], staging)
                if target.exists():
                    raise ValueError('Recovery target already exists without a recovery record')
                target.parent.mkdir(parents=True, exist_ok=True)
                staging.rename(target)
                write(recovery, {'success': True, 'reason': 'Completed export; missing target parent at directory publication',
                    'original_failed_result': str(result_path), 'restored_at': now(), 'bundle': exported(c['export_basename'], target)})
            elif record(target/(c['export_basename']+'.fbx'))['sha256'] != read(recovery)['bundle']['fbx_record']['sha256']:
                raise ValueError('Recovered export changed')
            print('Recovered completed export ' + name, flush=True)
            return {'success': True, 'recovery': str(recovery)}
        raise RuntimeError(name + ' ' + str(result.get('error')))
    report = read(output_dir / 'fixed_head_hair_report.json')
    if not report['success']:
        raise RuntimeError('CC report failed: ' + name)
    print('Completed ' + name, flush=True)
    return report

def config(sex, name, source, **extra):
    d = template(sex)
    d['fixed_head_hair_batch'] = {'case_id': name, 'sex': sex, 'source_project': source, **extra}
    return d

def prepare():
    references = {
        'female': OLD / 'female01_baked_final_capture_v1/morph_bake_checkpoint.ccProject',
        'male': OLD / 'male01_average_inverse_roundtrip_v1/roundtrip_subd0.ccProject'}
    info = {'batch_id': 'fixed_head_hair_20261004_v1',
            'user_reference_approval': 'User accepted female01/male01 reference head shapes in this thread',
            'sources': {}}
    for sex, original in references.items():
        name = 'prepare_' + sex + ('_v3' if sex == 'female' else '_v1')
        target = RUN / 'sources' / ('SOURCE_' + sex + '_FixedHead_Average_SubD0.ccProject')
        report = job(name, config(sex, name, record(original), action='prepare_source', prepared_project_path=str(target)))
        source = report['prepared_project']
        if record(source['path'])['sha256'] != source['sha256']:
            raise ValueError('Prepared source changed')
        info['sources'][sex] = {'reference_project': record(original), 'prepared_project': source,
             'body_state': report['body_after'], 'report': str(RUN/'jobs'/('fixed_head_hair_'+name)/'fixed_head_hair_report.json'),
             'geometry': str(RUN/'jobs'/('fixed_head_hair_'+name)/'reference_body_geometry.json')}
    write(RUN / 'sources/source_manifest.json', info)
    return info

def build_manifest(info):
    registry = read(REPO / '00_engine/assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json')
    old = read(Path(r'D:\UE\exports\character_creator\scalp_hair_batch_20260924_v1\manifests\cc_export.json'))
    catalog = read(REPO / '00_engine/scripts/character_creator/cc_scalp_hair_asset_catalog_v1.json')
    by_id = {a['asset_id']: a for a in catalog['assets']}
    by_hair = {p['preset_id'].split('_F_BATCH')[0]: p['scalp_hair_asset_id'] for p in old['presets']}
    previous = read(MANIFEST) if MANIFEST.exists() else {}
    prior = {c['case_id']: c for c in previous.get('cases', [])}
    manifest = {'schema_version': 1, 'batch_id': 'fixed_head_hair_20261004_v1',
                'expected_count': 80, 'source_manifest': str(RUN/'sources/source_manifest.json'),
                'bases': previous.get('bases', {}), 'cases': [],
                'legacy_registry': str(REPO/'00_engine/assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json')}
    for row in registry['hair_assets']:
        asset = by_id[by_hair[row['hair_id']]]
        file = asset['selected_source']; actual = record(file['path'])
        if actual['sha256'] != file['sha256']:
            raise ValueError('Hair catalog source changed: ' + row['hair_id'])
        resolved = {'asset_id': asset['asset_id'], 'display_name': asset['display_name'],
             'asset_type': asset['asset_type'], 'slot': 'scalp_hair', 'asset_form': asset['asset_form'],
             'extension': asset['extension'], 'verification_mode': 'scene_inventory',
             'path': actual['path'], 'resolved_path': actual['path'], 'sha256': actual['sha256']}
        for sex in ['female', 'male']:
            case_id = row['hair_id'] + '_' + sex
            manifest['cases'].append(prior.get(case_id, {'case_id': case_id, 'hair_id': row['hair_id'],
               'sex': sex, 'usage_sex': row['sex'], 'source_reference_id': 'FIXED_HEAD_' + sex.upper() + '_V1',
               'source_project': info['sources'][sex]['prepared_project'], 'hair_asset': resolved,
               'display_name': row['display_name'], 'status': 'pending'}))
    if len(manifest['cases']) != 80:
        raise ValueError('Expected exactly 80 cases')
    write(MANIFEST, manifest)
    return manifest

def exported(stem, root):
    root = Path(root); fbx = root/(stem+'.fbx'); js = root/(stem+'.json')
    textures = [p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ['.png','.jpg','.jpeg','.tga','.bmp','.dds']]
    if fbx.stat().st_size < 1000 or not textures:
        raise ValueError('Incomplete FBX/texture bundle: ' + str(root))
    document = read(js)
    references = []
    def check_paths(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == 'Texture Path' and isinstance(item, str) and item:
                    physical = (root / item).resolve()
                    if not physical.is_file() or physical.stat().st_size == 0:
                        raise ValueError('Missing referenced texture: ' + str(physical))
                    references.append(str(physical))
                else:
                    check_paths(item)
        elif isinstance(value, list):
            for item in value:
                check_paths(item)
    check_paths(document)
    return {'fbx': str(fbx), 'json': str(js), 'fbx_record': record(fbx), 'json_record': record(js),
            'texture_count': len(textures), 'verified_texture_references': len(set(references)),
            'export_root': str(root), 'status': 'exported'}

def export_bases(manifest, info):
    for sex in ['female', 'male']:
        name = 'BASE_' + sex; stem = 'CC_FIXED_HEAD_' + sex.upper(); root = EXPORT/'bases'/sex
        job(name, config(sex, name, info['sources'][sex]['prepared_project'], action='export',
                         export_root=str(root), export_basename=stem))
        manifest['bases'][sex] = {**exported(stem, root),
             'source_project': info['sources'][sex]['prepared_project'],
             'source_reference_id': 'FIXED_HEAD_' + sex.upper() + '_V1'}
        write(MANIFEST, manifest)

def export_cases(manifest, hair_id=None):
    for case in manifest['cases']:
        if hair_id and case['hair_id'] != hair_id:
            continue
        if case['status'] == 'exported':
            if record(case['fbx'])['sha256'] != case['fbx_record']['sha256']:
                raise ValueError('Completed export changed: ' + case['case_id'])
            continue
        name = case['case_id']; root = EXPORT/'cases'/case['sex']/case['hair_id']; stem='CC_'+name
        job(name, config(case['sex'], name, case['source_project'], action='export',
           hair_id=case['hair_id'], hair_asset=case['hair_asset'], export_root=str(root), export_basename=stem))
        case.update(exported(stem, root))
        case['report'] = str(RUN/'jobs'/('fixed_head_hair_'+name)/'fixed_head_hair_report.json')
        manifest.update(updated_at=now(), exported_count=sum(c['status']=='exported' for c in manifest['cases']))
        write(MANIFEST, manifest)
        print('Exported %d/80: %s' % (manifest['exported_count'], name), flush=True)
    write(RUN/'live.json', {'updated_at': now(), 'phase': 'export_phase_complete',
                          'exported_count': sum(c['status']=='exported' for c in manifest['cases']),
                          'manifest': str(MANIFEST)})

def main():
    p=argparse.ArgumentParser();p.add_argument('--action', choices=['prepare','pilot','all'],required=True)
    p.add_argument('--hair-id', default='HAIR_HB3_17'); args=p.parse_args()
    info = prepare(); manifest = build_manifest(info); export_bases(manifest, info)
    if args.action != 'prepare':
        export_cases(manifest, args.hair_id if args.action == 'pilot' else None)
    print(str(MANIFEST), flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        state = read(RUN/'live.json') if (RUN/'live.json').exists() else {}
        state.update(updated_at=now(), phase='needs_followup', error=str(exc))
        write(RUN/'live.json', state)
        raise
