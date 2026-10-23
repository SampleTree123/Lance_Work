"""Read-only source-pin audit for the camera pilot; no Unreal connection.

Owner: SCENE_CAMERA_SEQUENCE.md section 7. Writes only an owned audit snapshot.
"""
from datetime import datetime,timezone
from pathlib import Path
import argparse,hashlib,json,re

RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def pins(value):
 if isinstance(value,dict):
  if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):yield value
  for child in value.values():yield from pins(child)
 elif isinstance(value,list):
  for child in value:yield from pins(child)

def _audit_base(run=RUN):
 run=Path(run);checks=[];pending=[];observed={};cache_count=0;composition_count=0
 def check(record,context):
  path=record['path'];expected=record['sha256'];key=(path,expected)
  if key not in observed:
   try:actual=sha(path);error=None
   except (OSError,ValueError) as exc:actual=None;error=str(exc)
   observed[key]={'path':path,'expected_sha256':expected,'actual_sha256':actual,'matches':actual==expected,'error':error,'contexts':[]}
  observed[key]['contexts'].append(context)
 inventory=read(run/'offline_motion_inventory_v2.json')
 for entry in inventory['entries']:
  for sex,variant in entry['variants'].items():check(variant['body_only_package'],f'inventory:{entry["review_index"]}:{sex}')
 inventory_count=sum(len(entry['variants']) for entry in inventory['entries'])
 for path in sorted((run/'cache').glob('*.json')):
  try:value=read(path)
  except (OSError,ValueError) as exc:pending.append({'path':str(path),'reason':'incomplete/unreadable cache: '+str(exc)});continue
  if value.get('success') is not True:pending.append({'path':str(path),'reason':'cache not successful'});continue
  cache_count+=1
  for record in pins(value):check(record,'cache:'+path.name)
 for path in sorted((run/'compositions').glob('*.json')):
  try:value=read(path)
  except (OSError,ValueError) as exc:pending.append({'path':str(path),'reason':'incomplete/unreadable composition: '+str(exc)});continue
  if value.get('success') is not True:pending.append({'path':str(path),'reason':'composition not successful'});continue
  composition_count+=1
  for record in pins(value.get('sources',{})):check(record,'composition:'+path.name)
 recovery=read(run/'stage_recovery_v1.json')
 check(recovery['original_restored_package'],'original_review_map:post_recovery_baseline')
 for record in recovery.get('backups',[]):check(record,'recovery_backup')
 sequence_receipts=list((run/'sequences').glob('*.json'))
 for path in sequence_receipts:
  try:value=read(path)
  except (OSError,ValueError) as exc:pending.append({'path':str(path),'reason':'incomplete/unreadable sequence: '+str(exc)});continue
  for record in value.get('asset_files',[]):check(record,'sequence:'+path.name)
 checked=list(observed.values());failed=[r for r in checked if not r['matches']]
 complete=len(sequence_receipts)==30 and cache_count==12 and composition_count==12 and not pending
 inventory_checks=[r for r in checked if any(c.startswith('inventory:') for c in r['contexts'])]
 report={'schema':'camera_source_protection_audit_v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
         'status':'failed' if failed else ('completed_preparation_sources_verified' if complete else 'in_progress_sources_verified_so_far'),
         'success':not failed and complete,'all_observed_pins_match':not failed,'preparation_complete':complete,
         'inventory_asset_count':inventory_count,'inventory_unique_packages':len(inventory_checks),
         'inventory_50_assets_unchanged':inventory_count==50 and len(inventory_checks)==50 and all(r['matches'] for r in inventory_checks),
         'completed_cache_count':cache_count,'completed_composition_count':composition_count,'prepared_sequence_count':len(sequence_receipts),
         'checked_unique_path_sha_pairs':len(checked),'mismatches':failed,'pending':pending,'checks':checked,
         'review_scene_recovery':{'baseline':'stage_recovery_v1.original_restored_package',
          'original_scene_restored_from_complete_preserved_snapshot':recovery.get('original_scene_restored_from_complete_preserved_snapshot'),
          'original_file_bitwise_identical_to_old_disk':recovery.get('original_file_bitwise_identical_to_old_disk'),
          'scope':'Checks post-recovery saved map; does not claim original pre-incident bytes stayed unchanged or prove current live UE state'},
         'limitations':['Read-only disk snapshot; not current UE dirty-package/live-scene inspection','Checks recorded body/face/skeleton/reference mesh/cache/sequence/map dependencies; not every material or texture in the project','Render and human visual acceptance remain separate']}
 return report


def audit(run=RUN):
 """Audit the actual input chains, independently of saved render-map hashes."""
 run=Path(run);report=_audit_base(run);issues=[];chains=[];skipped=[];derived=[];historical_code=[]
 checks=[]
 for old in report['checks']:
  if Path(old['path']).suffix.lower()=='.py':
   historical_code.append({'path':old['path'],'recorded_sha256':old['expected_sha256'],
     'current_sha256':old['actual_sha256'],'same_version':old['matches'],'contexts':old['contexts'],
     'scope':'historical implementation version; not an asset-immutability claim'})
  else:checks.append(old)
 report['checks']=checks
 lookup={(str(Path(r['path'])).casefold(),r['expected_sha256']):r for r in checks}
 actual={str(Path(r['path'])).casefold():(r['actual_sha256'],r['error']) for r in checks}
 def check(record,context):
  path=record['path'];expected=record['sha256'];canonical=str(Path(path)).casefold()
  if Path(path).suffix.lower()=='.fbx':
   skipped.append({'path':path,'reason':'Large FBX not rehashed; actual BodyOnly/import evidence checked'});return
  if Path(path).suffix.lower()=='.py':
   # Generation 2 is intentionally preserved after the generation 3 source
   # revision. Its old script hash is historical, not a source-asset mismatch.
   try:digest=sha(path);error=None
   except (OSError,ValueError) as exc:digest=None;error=str(exc)
   historical_code.append({'path':path,'recorded_sha256':expected,'current_sha256':digest,
     'same_version':digest==expected,'context':context,'error':error,
     'scope':'historical preparation code version; excluded from asset-immutability verdict'})
   return
  key=(canonical,expected)
  if key not in lookup:
   if canonical not in actual:
    try:actual[canonical]=(sha(path),None)
    except (OSError,ValueError) as exc:actual[canonical]=(None,str(exc))
   digest,error=actual[canonical]
   row={'path':path,'expected_sha256':expected,'actual_sha256':digest,'matches':digest==expected,'error':error,'contexts':[]}
   lookup[key]=row;checks.append(row)
  if context not in lookup[key]['contexts']:lookup[key]['contexts'].append(context)
 def inspect(value,context):
  for record in pins(value):check(record,context)
 def issue(context,exc):issues.append({'context':context,'error':str(exc)})
 def compose(record,animation,context):
  check(record,context+':composition_report')
  value=read(record['path'])
  if value.get('success') is not True or value.get('sources_unchanged') is not True:
   raise ValueError('Composition lacks verified input preservation')
  if value['destination'].split('.')[0]!=animation.split('.')[0]:
   raise ValueError('Sequence animation differs from composition destination')
  if len(value.get('sources',[]))<4:raise ValueError('Missing actual composition sources')
  inspect(value['sources'],context+':actual_composition_inputs')
  inspect(value.get('task',{}),context+':composition_task_provenance')
  return value
 inventory=read(run/'offline_motion_inventory_v2.json')
 for entry in inventory['entries']:
  for sex,v in entry['variants'].items():
   context=f'inventory_import:{entry["review_index"]}:{sex}'
   try:
    check(v['import_report'],context)
    source=read(v['import_report']['path'])
    if source.get('success') is not True:raise ValueError('BodyOnly import did not succeed')
    inspect(source.get('protected_sources',[]),context+':reference_body_and_shared_skeleton')
   except (OSError,ValueError,KeyError) as exc:issue(context,exc)
 retime=[]
 for path in sorted((run/'retime').glob('*.json')):
  try:
   value=read(path)
   if value.get('success') is not True or value.get('sources_unchanged') is not True:
    raise ValueError('Retime source preservation did not succeed')
   inspect(value,'retime:'+path.name)
   retime.append({'path':str(path),'kind':'body_window' if value.get('schema')=='camera_body_window_v1' else 'face_composition'})
  except (OSError,ValueError,KeyError) as exc:issue(str(path),exc)
 main,pair,extra=[read(run/name) for name in ('prepared_jobs_v1.json','paired_edit_prepared_v1.json','retime_prepared_jobs_v1.json')]
 jobs=main['jobs']+[pair['job']]+extra['jobs'];mainids={j['shot_id'] for j in main['jobs']}
 if [len(main['jobs']),len(extra['jobs']),len(jobs)]!=[30,3,34] or len({j['shot_id'] for j in jobs})!=34:
  issue('job_inventory','Expected exactly 30 primary, one paired edit and three supplemental jobs')
 inspect(main,'main_manifest');inspect(extra,'extra_manifest')
 for path,expected in pair['color_report'].get('protected_package_hashes',{}).items():
  check({'path':path,'sha256':expected},'pair_edit:protected_mesh_material_shader')
 for job in jobs:
  sid=job['shot_id'];context='shot:'+sid
  try:
   is_pair=sid==pair['job']['shot_id']
   receipt=pair if is_pair else read(run/('sequences' if sid in mainids else 'retime_sequences')/(sid+'.json'))
   if receipt['job']!=job:raise ValueError('Shot receipt differs from manifest')
   inspect(receipt.get('asset_files',[]),context+':derived_scene_sequence_only')
   animation=receipt['sequence_report']['animation_path'];actual_receipt=receipt
   if is_pair:
    actual_receipt=read(run/'sequences'/(pair['source_shot_id']+'.json'))
    if actual_receipt['sequence_report']['animation_path'].split('.')[0]!=animation.split('.')[0]:
     raise ValueError('Pair edit changed body/face animation')
   if 'composition' in actual_receipt:
    ref=actual_receipt['composition']['cache_receipt'];check(ref,context+':cache_receipt');cache=read(ref['path'])
    if cache.get('success') is not True or cache['animation_path'].split('.')[0]!=animation.split('.')[0]:
     raise ValueError('Cache does not bind this shot animation')
    inspect(cache,context+':cache_inputs_and_output')
    comp_ref=cache['composition_report'];comp=compose(comp_ref,animation,context)
   else:
    comp_ref=actual_receipt['composition_report'];comp=compose(comp_ref,animation,context)
    body_ref=actual_receipt.get('body_source_evidence')
    if body_ref:
     check(body_ref,context+':body_source_evidence')
     if Path(body_ref['path']).suffix.lower()=='.json':
      body=read(body_ref['path'])
      if body.get('success') is not True or body.get('sources_unchanged') is not True:
       raise ValueError('Retime body lacks verified source preservation')
      inspect(body,context+':actual_retime_body_inputs')
      if body['destination'].split('.')[0]!=comp['task']['body_animation'].split('.')[0]:
       raise ValueError('Composed body does not match retime report')
    # No old output hash was recorded for the two retimed face composites.
    # Observe derived outputs now, without claiming historical immutability.
    if sid in ('cam_32_retime_c018_female','cam_33_retime_c018_male'):
     file=Path('D:/UE/projects/datatry_02/Content')/(animation.split('.')[0].removeprefix('/Game/')+'.uasset')
     derived.append({'shot_id':sid,'path':str(file),'sha256_observed_now':sha(file),
       'scope':'current derived-output observation; no original historical output hash existed'})
   chains.append({'shot_id':sid,'animation':animation,'composition_report':comp_ref,
     'body_input':comp['task']['body_animation'],'actual_input_asset_count':len(comp['sources']),
     'source_input_chain_resolved':True})
  except (OSError,ValueError,KeyError) as exc:issue(context,exc)
 v2=[];v3=[]
 studio_paths=[(generation,path) for generation in (2,3) for path in sorted((run/('sequences_v'+str(generation))).glob('*.json'))]
 for generation,path in studio_paths:
  try:
   value=read(path)
   if value.get('success') is not True or value['job']['shot_id'] not in {j['shot_id'] for j in jobs}:
    raise ValueError('Unsuccessful or unknown StudioV2 receipt')
   # Includes original composite, source-map, shared hair mesh and probe pins;
   # these are additional to the body/face/skeleton chains resolved above.
   inspect(value,'studio_v'+str(generation)+':'+path.name)
   (v2 if generation==2 else v3).append(value['job']['shot_id'])
  except (OSError,ValueError,KeyError) as exc:issue(str(path),exc)
 missing=sorted({j['shot_id'] for j in jobs}-set(v3))
 skeleton=[r for r in checks if '/sharedskeletons/skel_cfdshared_' in r['path'].replace('\\','/').casefold()]
 failed=[r for r in checks if not r['matches']]
 skeleton_ok=len(skeleton)==2 and all(r['matches'] for r in skeleton)
 source_complete=report['inventory_50_assets_unchanged'] and skeleton_ok and len(chains)==34 and len(retime)==4 and not failed and not issues
 report.update({'schema':'camera_source_protection_audit_v2','status':'failed' if failed or issues else
   ('source_inputs_verified_studio_preparation_in_progress' if missing else 'all_34_source_inputs_and_studio_receipts_verified'),
   'success':source_complete,'source_protection_complete':source_complete,'all_observed_pins_match':not failed,
   'all_checked_asset_and_document_pins_match':not failed,
   'all_historical_code_pins_match':all(r['same_version'] for r in historical_code),
   'preparation_complete':len(v3)==34,'current_studio_generation':3,'current_generation_full_34_receipts_complete':len(v3)==34,
   'shared_two_skeletons_unchanged':skeleton_ok,'shared_skeleton_checks':skeleton,
   'covered_original_shot_input_chains':len(chains),'shot_input_chains':chains,'retime_input_reports':retime,
   'available_v2_receipt_count':len(v2),'available_v2_shot_ids':v2,
   'available_v3_receipt_count':len(v3),'available_v3_shot_ids':v3,'missing_current_generation_receipts':missing,
   'checked_unique_path_sha_pairs':len(checks),'mismatches':failed,'structural_issues':issues,
   'derived_output_observations_without_prior_hash':derived,'large_fbx_hashing':'not performed',
   'skipped_large_fbx_records':skipped,
   'historical_preparation_code_versions':historical_code,
   'limitations':['Disk snapshot only; no Unreal dirty-package/live-state inspection',
     'All 34 actual body/face composition chains and retime inputs audited separately from map/sequence outputs',
     'Only recorded reference meshes, shared skeletons, body/face inputs, targeted paired-edit materials and hair meshes are checked; not every material/texture in the project',
     'Two derived retimed face-composite outputs lacked a historical package hash; current observations are not substituted for an old source-preservation proof',
     'Planner and preparation code pins can describe earlier authorized versions; all implementation-code observations are separate from asset/document immutability verdicts',
     'Studio receipts created after snapshot require later audit; preparation completion differs from source-protection completion',
     'No large FBX rehash, license validation, render quality or human visual acceptance claim']})
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=RUN/('source_protection_audit_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'));a=p.parse_args()
 output=a.output.resolve()
 if not output.is_relative_to(RUN.resolve()) or output.suffix!='.json' or output.exists():raise ValueError('Audit output must be new JSON within this run')
 result=audit();output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
 print(json.dumps({k:result[k] for k in ['status','success','all_observed_pins_match','inventory_50_assets_unchanged','shared_two_skeletons_unchanged','covered_original_shot_input_chains','available_v2_receipt_count','checked_unique_path_sha_pairs']}))
