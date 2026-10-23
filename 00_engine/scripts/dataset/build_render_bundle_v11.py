"""Freeze current render settings, immutable jobs and reference bindings for upload.

Offline only; owns dataset_server_bundle_* outputs. Does not render or upload.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import render_plan_v11
import schedule_render_v11

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / '00_engine/outputs/dataset_return_control_20261022_v11/render_preparation/VIDEO_PROFILE.json'
REFERENCES = ROOT / '00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4'
CORRECTED = ROOT / '00_engine/outputs/dataset_texture_quality_20261023_v1/corrected'


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest(source, jobs):
    return {**{k:v for k,v in source.items() if k not in ('jobs', 'job_count')},
            'job_count': len(jobs), 'jobs': jobs}


def build(out):
    if out.exists():
        raise ValueError('Choose a new output directory; existing bundles are not overwritten')
    out.mkdir(parents=True)
    shutil.copyfile(Path(__file__).with_name('render_bundle_v11_README.md'), out / 'README.md')
    (out / 'config').mkdir()
    shutil.copyfile(PROFILE, out / 'config/VIDEO_PROFILE.json')
    render_plan_v11.main(['--profile', str(PROFILE), '--out', str(out / 'queues/main')])
    main = read(out / 'queues/main/main_jobs.json')
    old = read(CORRECTED / 'main_jobs.json')
    if main['jobs'] != old['jobs']:
        raise ValueError('Main job content changed; investigate before publishing bundle')
    ordered, _, schedule = schedule_render_v11.build(main, 1)
    write(out / 'queues/main/ordered_jobs.json', manifest(main, ordered))
    write(out / 'config/SCHEDULE.json', schedule)
    (out / 'queues/references').mkdir(parents=True)
    for name in ('reference_jobs.json', 'carrier_jobs.json', 'reference_bindings.json',
                 'identity_reference_pools.json', 'motion_carriers.json', 'hair_carrier_clothing.json'):
        shutil.copyfile(REFERENCES / name, out / 'queues/references' / name)
    reference = read(REFERENCES / 'reference_jobs.json')
    ref_jobs = reference['jobs']
    carriers = {j['job_id']:j for j in read(REFERENCES / 'carrier_jobs.json')['jobs']}
    for job in ref_jobs:
        carrier = carriers[job['source_job_id']]
        assert hashlib.sha256(json.dumps(carrier, sort_keys=True).encode()).hexdigest() == job['source_job_sha256']
    def reference_key(job):
        src = carriers[job['source_job_id']]
        return (src['site']['map'] if job['reference_kind']=='scene' else '',
                src['state']['sex'], src['state']['identity'], src['state']['hair'], job['job_id'])
    queues = {'smoke_main': {'jobs':'queues/main/pilot_jobs.json', 'worker_module':'ue_dataset_render_v11', 'output_subdir':'main'},
              'main': {'jobs':'queues/main/ordered_jobs.json', 'worker_module':'ue_dataset_render_v11', 'output_subdir':'main'}}
    for kind in ('scene', 'identity', 'hair', 'garment', 'motion'):
        jobs = sorted([j for j in ref_jobs if j['reference_kind']==kind], key=reference_key)
        relative = 'queues/references/' + kind + '_jobs.json'
        write(out / relative, manifest(reference, jobs))
        queues[kind] = {'jobs': relative, 'worker_module':'ue_dataset_reference_v11',
                        'output_subdir':'references', 'seed_files': {'carrier_jobs.json':'queues/references/carrier_jobs.json'}}
    pilot_ids = set()
    for path in (REFERENCES/'hair_framing_pilot_jobs.json', REFERENCES/'motion_pilot_jobs.json',
                 REFERENCES/'portrait_pilot_jobs.json',
                 ROOT/'00_engine/outputs/dataset_reference_production_20261023_v1/static_pilot_jobs.json'):
        for j in read(path)['jobs']:
            if path.name=='static_pilot_jobs.json' and j['reference_kind'] not in ('scene','garment'):
                continue
            if path.name=='portrait_pilot_jobs.json' and j['reference_kind']!='identity':
                continue
            pilot_ids.add(j['job_id'])
    pilots = [j for j in ref_jobs if j['job_id'] in pilot_ids]
    assert len(pilots)==len(pilot_ids)
    write(out/'queues/references/smoke_jobs.json', manifest(reference,pilots))
    queues['smoke_references'] = {**queues['hair'], 'jobs':'queues/references/smoke_jobs.json'}
    profile = read(PROFILE)
    config = {'schema':'dataset_render_bundle_v1','engine_version':'5.8.1',
        'character_expression':profile['character_expression'],
        'profile_snapshot':'config/VIDEO_PROFILE.json', 'content_inventory':'config/CONTENT_CONFIG.json',
        'runtime':{'portable_runtime':True,'command_timeout':600,'render_timeout':3600,'discovery_timeout':120},
        'queues':queues, 'execution_order':['smoke_main','smoke_references','main','scene','identity','hair','garment','motion'],
        'single_editor_serial':True, 'resume':'same output root; successful matching jobs skipped by existing driver',
        'retry':'no automatic retry; fix error then explicitly rerun same queue',
        'profile_semantics':'Frozen documented contract with current worker implementation; job dimensions and timings consumed directly. Editing profile alone does not override worker CVar/AA/encoding constants; regenerate and test affected code/plan.'}
    write(out/'RENDER_CONFIG.json', config)
    local = read(PROFILE.parent/'MACHINE_LOCAL.json')
    machine = {'schema':'dataset_render_bundle_machine_v1','workspace_root':str(ROOT).replace('\\','/'),
        'project_root':local['project_root'],'engine_root':local['engine_root'],
        'output_root':str(ROOT/'00_engine/outputs/dataset_bundle_local_execution_20261023_v1').replace('\\','/'),
        'texture_pool_mb':local['texture_pool_mb'],'python_executable':None,'ffmpeg':None,'node_id':None}
    write(out/'config/MACHINE_LOCAL.json', machine)
    server = {**machine, **{k:None for k in ('workspace_root','project_root','engine_root','output_root','texture_pool_mb')}}
    server['instructions']='Fill absolute Linux paths and measured GPU texture budget; one UE editor per worker. Python3 + FFmpeg/libx264 required. No Windows machine budget default.'
    write(out/'config/MACHINE_SERVER.template.json', server)
    counts = Counter(j['reference_kind'] for j in ref_jobs)
    dimensions = {key:dict(sorted(Counter(j['state'][key] for j in main['jobs']).items()))
                  for key in ('sex','identity','hair','hair_color','site','aspect','action','camera')}
    garments = Counter(a['asset_id'] for j in main['jobs'] for a in j['appearance']['wardrobe_assets'])
    sites = {j['site']['site_id']:j['site'] for j in main['jobs']}
    content = {'schema':'dataset_render_content_inventory_v1',
        'character_expression':profile['character_expression'],
        'main_videos':len(main['jobs']),'main_by_split':dict(Counter(j['split'] for j in main['jobs'])),
        'reference_counts':dict(counts),'total_videos':len(main['jobs'])+counts['motion'],
        'total_static_images':len(ref_jobs)-counts['motion'],'main_scene_maps':len({j['site']['map'] for j in main['jobs']}),
        'smoke_main':len(read(out/'queues/main/pilot_jobs.json')['jobs']),'smoke_references':len(pilots),
        'value_occurrences_in_main':dimensions,'garment_asset_occurrences_in_main':dict(sorted(garments.items())),
        'sites':list(sites.values()),'reference_presentation':profile['static_reference_presentation'],
        'exact_content':'queues/main/main_jobs.json and queues/references/reference_jobs.json; reference carrier details in carrier_jobs.json',
        'training_reference_binding':'queues/references/reference_bindings.json -> effective_reference_links',
        'exposure':'Saved source level postprocess volumes in project/Content; camera exposure overrides cleared by worker. Map binary upload is required, JSON alone does not carry lighting.'}
    write(out/'config/CONTENT_CONFIG.json',content)
    sources = [PROFILE, CORRECTED/'main_jobs.json', REFERENCES/'reference_jobs.json', REFERENCES/'carrier_jobs.json', REFERENCES/'reference_bindings.json']
    for name in ('run_dataset_render_v11','ue_dataset_render_v11','ue_dataset_reference_v11','dataset_runtime_paths_v11','ue_dataset_reference_pilot_v11','dataset_persistent_materials_v1','dataset_smile_runtime_v1'):
        sources.append(ROOT/'00_engine/scripts/unreal'/f'{name}.py')
    sources.append(ROOT/'00_engine/assets/character_creator/dataset_smile_v1.json')
    formal=ROOT/'00_engine/outputs/production_workflow_20261017_v1'
    active=formal/'asset_inventory_formal_runtime_active_v1.json'
    sources += [formal/'asset_inventory_formal_runtime_v1.py',active,Path(read(active)['catalog']['path'])]
    sources += [Path(__file__),Path(__file__).with_name('run_render_bundle_v11.py'),Path(__file__).with_name('encode_render_v11.py'),Path(__file__).with_name('render_bundle_v11_README.md')]
    write(out/'SOURCE_SNAPSHOT.json',{'source_files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p)} for p in sources],
        'main_job_definitions_unchanged':True,'reference_job_definitions_unchanged':True,
        'server_tested':False,'render_or_upload_started':False})
    write(out/'PACKAGE_FILES.json',{'files':[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
          for p in sorted(out.rglob('*')) if p.is_file()]})
    print(json.dumps({'bundle':str(out),'main':len(main['jobs']),'references':dict(counts),'smoke_references':len(pilots)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    build(parser.parse_args().out.resolve())
