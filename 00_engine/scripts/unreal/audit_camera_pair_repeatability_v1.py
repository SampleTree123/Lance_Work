"""Offline pair/repeatability audit. Owner: SCENE_CAMERA_SEQUENCE.md section 7.

No UE/browser/server calls. Strictly compare all 300 repeat PNGs; never use a
fitted tolerance to call differing renders identical. Pillow/numpy are loaded
only for pixel statistics. Hair-color visual acceptance remains separate.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path

RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
BASE='cam_05_dolly_in'
PAIR='cam_31_dolly_in_pink_edit'
REPEAT='cam_34_dolly_in_repeatability'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def pin(path):
 path=Path(path)
 return {'path':str(path),'sha256':sha_bytes(path.read_bytes())}
def check(record):
 if pin(record['path'])['sha256']!=record['sha256']:raise ValueError('Pinned input changed: '+record['path'])
def package(asset):return asset.split('.')[0]


def _unique(rows,key,label):
 result={row[key]:row for row in rows}
 if len(result)!=len(rows):raise ValueError('Duplicate '+label)
 return result


def _asset_identity(record):
 if record is None:return None
 return {'asset':record['asset'],'sha256':record['package']['sha256']}


def _materials(component):
 slots=_unique(component['materials'],'slot','material slot')
 return {str(slot):[_asset_identity(record) for record in slots[slot]['chain']] for slot in sorted(slots)}


def _bindings(row):
 result=[];world=row['map']['asset'];actor=row['actor']
 for binding in row['bindings']:
  if len(binding['objects'])!=1:raise ValueError('Nonunique binding in scene audit')
  path=binding['objects'][0]
  if 'TRASH' in path or not path.startswith(world+':'):raise ValueError('Binding does not belong to audited world')
  if path==actor:relative='$character'
  elif path.startswith(actor+'.'):relative='$character.'+path[len(actor)+1:]
  else:relative='$world:'+path[len(world)+1:]
  result.append({'name':binding['name'],'object_role':relative,
      'is_exact_current_body':bool(binding['is_exact_current_body'])})
 if len(result)!=9 or sum(r['is_exact_current_body'] for r in result)!=1:
  raise ValueError('Expected nine bindings and exactly one Body')
 return sorted(result,key=lambda r:(r['name'],r['object_role']))


def pair_structure(run,scene_audit,prepared):
 if scene_audit.get('success') is not True or scene_audit.get('all_jobs_passed') is not True or len(scene_audit.get('jobs',[]))!=34:
  raise ValueError('Complete successful 34-scene binding audit required')
 rows=_unique(scene_audit['jobs'],'shot_id','scene shot')
 left,right=rows[BASE],rows[PAIR]
 if not left.get('success') or not right.get('success'):raise ValueError('Paired scene rows not successful')
 components_a=_unique(left['components'],'name','component')
 components_b=_unique(right['components'],'name','component')
 differences=[];allowed=[]
 if set(components_a)!=set(components_b):differences.append({'field':'component_names','base':sorted(components_a),'pair':sorted(components_b)})
 for name in sorted(set(components_a)&set(components_b)):
  a,b=components_a[name],components_b[name]
  for field in ('mesh','skeleton'):
   if _asset_identity(a.get(field))!=_asset_identity(b.get(field)):
    differences.append({'component':name,'field':field,'base':_asset_identity(a.get(field)),'pair':_asset_identity(b.get(field))})
  am,bm=_materials(a),_materials(b)
  if am!=bm:
   change={'component':name,'field':'materials','base':am,'pair':bm}
   (allowed if name.startswith('HairPart') else differences).append(change)
 for field in ('sex','actor_transform','body_relative_transform','actor_copy_route_tags'):
  if left.get(field)!=right.get(field):differences.append({'field':field,'base':left.get(field),'pair':right.get(field)})
 if _bindings(left)!=_bindings(right):differences.append({'field':'binding_roles','base':_bindings(left),'pair':_bindings(right)})
 check(prepared['plan']);plan=read(prepared['plan']['path'])
 shot=next(s for s in plan['shots'] if s['shot_id']==BASE)
 trajectory=sha_bytes(json.dumps(shot['frames']+[shot['endpoint_validation_frame']],sort_keys=True,separators=(',',':'),allow_nan=False).encode())
 if trajectory!=shot['trajectory_sha256']:raise ValueError('Frozen cam05 trajectory hash cannot be reproduced')
 receipt_refs={Path(p['path']).stem:p for p in prepared['sequence_receipts']}
 receipts={}
 for sid,row in ((BASE,left),(PAIR,right)):
  reference=receipt_refs[sid];check(reference);receipt=read(reference['path']);receipts[sid]=receipt
  if receipt.get('success') is not True or receipt['plan']!=prepared['plan']:raise ValueError('Prepared pair receipt is stale or incomplete')
  for field in ('map','sequence'):
   if receipt['job'][field]!=row[field]['asset']:raise ValueError('Scene audit does not match prepared pair '+field)
   check(row[field]['package'])
   pins={str(Path(p['path'])).casefold():p['sha256'] for p in receipt['asset_files']}
   if pins.get(str(Path(row[field]['package']['path'])).casefold())!=row[field]['package']['sha256']:
    raise ValueError('Prepared asset hash differs from scene audit')
  if receipt['spec']['trajectory_sha256']!=trajectory or receipt['sequence_report']['source_trajectory_sha256']!=trajectory:
   differences.append({'field':'camera_trajectory_sha256','shot_id':sid,'expected':trajectory})
 for field in ('animation_path','source_start_seconds','fps','duration_seconds','render_frames',
               'start_frame_inclusive','end_frame_exclusive','endpoint_key_frame','transform_and_fov_key_counts',
               'rotation_channel_order','interpolation','force_custom_mode'):
  a,b=receipts[BASE]['sequence_report'][field],receipts[PAIR]['sequence_report'][field]
  if a!=b:differences.append({'field':'sequence_report.'+field,'base':a,'pair':b})
 return {'success':not differences and bool(allowed),'base_shot':BASE,'edited_shot':PAIR,
  'component_count':len(components_a),'allowed_hair_material_differences':allowed,'forbidden_differences':differences,
  'hair_material_edit_present':bool(allowed),'camera_trajectory_sha256':trajectory,
  'bindings_roles_equal':_bindings(left)==_bindings(right),'source_receipts':[receipt_refs[BASE],receipt_refs[PAIR]],
  'scope':'visible component mesh/skeleton/material chains, actor transforms, bindings roles, recorded animation/window/camera invariants',
  'hair_color_visual_acceptance':'not assessed; image appearance remains a separate review',
  'not_covered':'all scene light/environment actors and recursive material textures are outside the scene audit component scope'}


def compare_frame(path_a,path_b):
 """Compare immutable byte snapshots; report native 8-bit RGB/RGBA differences."""
 import io
 import numpy as np
 from PIL import Image
 data_a,data_b=Path(path_a).read_bytes(),Path(path_b).read_bytes()
 arrays=[];info=[]
 for data in (data_a,data_b):
  if len(data)<25 or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[24]!=8:
   raise ValueError('Require intact 8-bit PNG without implicit precision conversion')
  with Image.open(io.BytesIO(data)) as im:
   im.load()
   if im.mode not in ('RGB','RGBA'):raise ValueError('Require native RGB/RGBA PNG; no silent palette/channel conversion')
   arrays.append(np.asarray(im,dtype=np.uint8).copy());info.append({'size':list(im.size),'mode':im.mode})
 if info[0]!=info[1]:raise ValueError('Repeat frame geometry or native channel mode differs')
 delta=arrays[0].astype(np.int16)-arrays[1].astype(np.int16)
 absolute=np.abs(delta);squared=delta.astype(np.int32)**2
 scalar_count=int(delta.size);sse=int(squared.sum(dtype=np.int64));mse=sse/scalar_count
 pixels=int(delta.shape[0]*delta.shape[1]);changed=int(np.any(delta!=0,axis=2).sum())
 return {'base_sha256':sha_bytes(data_a),'repeat_sha256':sha_bytes(data_b),
  'png_bytes_exact':data_a==data_b,'decoded_pixels_exact':changed==0,'image':info[0],
  'pixel_count':pixels,'changed_pixels':changed,'changed_pixel_fraction':changed/pixels,
  'scalar_count':scalar_count,'absolute_error_sum':int(absolute.sum(dtype=np.int64)),
  'squared_error_sum':sse,'max_absolute_channel_error':int(absolute.max()),
  'mae':float(absolute.mean()),'mse':mse,'psnr_db':None if mse==0 else 10*math.log10(255**2/mse),
  'psnr_is_infinite':mse==0}


def repeatability(run,render_receipt,prepared,attempt):
 if render_receipt.get('status')!='completed' or render_receipt.get('success') is not True:
  raise ValueError('Require successful terminal render receipt before comparing frames')
 jobs=_unique(render_receipt['jobs'],'shot_id','render job');base,repeat=jobs[BASE],jobs[REPEAT]
 if (base['map'],base['sequence'])!=(repeat['map'],repeat['sequence']):
  raise ValueError('Repeat job does not reuse exactly cam05 map and sequence')
 prepared_job=next(j for j in prepared['jobs'] if j['shot_id']==BASE)
 if base!=prepared_job:raise ValueError('Render cam05 differs from prepared final job')
 if jobs[PAIR]!=next(j for j in prepared['jobs'] if j['shot_id']==PAIR):
  raise ValueError('Render cam31 differs from prepared final job')
 render_pins={str(Path(p['path'])).casefold():p for p in render_receipt['inputs']}
 receipt_refs={Path(p['path']).stem:p for p in prepared['sequence_receipts']}
 for sid in (BASE,PAIR):
  reference=receipt_refs[sid];check(reference)
  for asset in read(reference['path'])['asset_files']:
   render_pin=render_pins.get(str(Path(asset['path'])).casefold())
   if render_pin!=asset:raise ValueError('Rendered input pin differs from prepared '+sid+' asset')
   check(render_pin)
 callbacks=_unique(render_receipt.get('job_results',[]),'shot_id','terminal callback')
 if not all(callbacks.get(s,{}).get('success') is True for s in (BASE,PAIR,REPEAT)):
  raise ValueError('Missing successful callback for base/pair/repeat render')
 contract=render_receipt['render_contract']
 if contract.get('frame_count')!=300 or contract.get('fps')!=30 or contract.get('duration_seconds')!=10:
  raise ValueError('Expected strict 300-frame ten-second render contract')
 root=run/'renders'/attempt
 if Path(render_receipt['output_root']).resolve()!=root.resolve():raise ValueError('Render receipt output root differs')
 expected={f'frame_{i:04d}.png' for i in range(300)}
 inventories={}
 for sid in (BASE,PAIR,REPEAT):
  folder=root/sid;found={p.name for p in folder.glob('*.png')}
  inventories[sid]={'png_count':len(found),'missing':sorted(expected-found),'unexpected':sorted(found-expected)}
  if found!=expected:raise ValueError('Incomplete/nonexact 300 PNG set for '+sid+': '+str(inventories[sid]))
 frames=[]
 for i in range(300):
  filename=f'frame_{i:04d}.png'
  metrics=compare_frame(root/BASE/filename,root/REPEAT/filename)
  frames.append(dict(metrics,frame=i,filename=filename))
 total_scalars=sum(r['scalar_count'] for r in frames);sse=sum(r['squared_error_sum'] for r in frames)
 total_pixels=sum(r['pixel_count'] for r in frames);changed=sum(r['changed_pixels'] for r in frames)
 mse=sse/total_scalars
 return {'audit_complete':True,'base_shot':BASE,'repeat_shot':REPEAT,'same_map_and_sequence':True,
  'render_contract':contract,'frame_inventory':inventories,'compared_frame_count':300,
  'png_byte_exact_frame_count':sum(r['png_bytes_exact'] for r in frames),
  'decoded_pixel_exact_frame_count':sum(r['decoded_pixels_exact'] for r in frames),
  'all_png_bytes_exact':all(r['png_bytes_exact'] for r in frames),
  'all_decoded_pixels_exact':all(r['decoded_pixels_exact'] for r in frames),
  'global_pixel_count':total_pixels,'global_changed_pixels':changed,'global_changed_pixel_fraction':changed/total_pixels,
  'global_mae':sum(r['absolute_error_sum'] for r in frames)/total_scalars,'global_mse':mse,
  'global_psnr_db':None if mse==0 else 10*math.log10(255**2/mse),'global_psnr_is_infinite':mse==0,
  'maximum_absolute_channel_error':max(r['max_absolute_channel_error'] for r in frames),
  'worst_frame_by_mse':max(frames,key=lambda r:r['mse'])['frame'],
  'different_pixel_frames':[r['frame'] for r in frames if not r['decoded_pixels_exact']],
  'frames':frames,'threshold_policy':'exact equality only; no relaxed PSNR/MAE threshold or human acceptance inferred',
  'pixel_metric_scope':'all native 8-bit RGB/RGBA channels, including alpha when present',
  'png_metadata_note':'PNG byte equality and decoded pixel equality reported separately'}


def audit(run=RUN,attempt='matrix_v1'):
 run=Path(run)
 if not attempt or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in attempt):
  raise ValueError('Unsafe render attempt id')
 paths={'scene_audit':run/'scene_binding_audit_v2.json','prepared_jobs':run/'prepared_jobs_v2.json',
        'render_receipt':run/'render_receipts'/(attempt+'.json')}
 result={'schema':'camera_pair_repeatability_audit_v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
   'success':False,'audit_complete':False,'errors':[],
   'scope':'offline saved-scene pair invariants and strict 300-frame repeat comparison; no UE connection or visual acceptance'}
 try:
  source_pins={k:pin(p) for k,p in paths.items()};result['inputs']=source_pins
  prepared=read(paths['prepared_jobs'])
  if prepared.get('success') is not True or len(prepared.get('jobs',[]))!=34:raise ValueError('Require final 34 prepared jobs')
  result['pair_structure']=pair_structure(run,read(paths['scene_audit']),prepared)
  result['repeatability']=repeatability(run,read(paths['render_receipt']),prepared,attempt)
  for record in source_pins.values():check(record)
  result['audit_complete']=True
  result['success']=bool(result['pair_structure']['success'] and result['repeatability']['all_png_bytes_exact'] and result['repeatability']['all_decoded_pixels_exact'])
  result['status']='strict_exact_pass' if result['success'] else 'differences_observed_for_review'
 except (OSError,ValueError,KeyError,ImportError) as exc:
  result['errors'].append(str(exc));result['status']='audit_incomplete'
 return result


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--run-root',type=Path,default=RUN);parser.add_argument('--attempt',default='matrix_v1')
 parser.add_argument('--output',type=Path)
 args=parser.parse_args();output=args.output or args.run_root/'pair_repeatability_audit_v1.json'
 if not output.resolve().is_relative_to(args.run_root.resolve()) or output.suffix!='.json' or output.exists():
  raise ValueError('Use a new owned JSON audit output path')
 result=audit(args.run_root,args.attempt);output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
 print(json.dumps({k:result[k] for k in ('status','success','audit_complete','errors')},ensure_ascii=False))
