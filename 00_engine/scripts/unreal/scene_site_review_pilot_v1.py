"""Explicit pilot plans/preparation for site review. No automatic UE connection.
Owner SCENE_CAMERA_SEQUENCE section17; run only after exclusive UE access.
"""
from pathlib import Path
import copy, hashlib, importlib.util, json
import scene_site_review_geometry_v1 as geo
S=Path(__file__).resolve().parent
RUN=geo.RUN
ASSETS='/Game/DataMake/Validation/SceneSiteReview20261014'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def module(name):
 spec=importlib.util.spec_from_file_location('_site_pilot_'+name,S/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def make_plan(site_file,scene_id,selections,revision='v1'):
 """Only a saved, actually surveyed site may create a render plan."""
 record=read(site_file);site=record['site'];library=geo.load_library()
 original=library['shots']
 position=[site['position'][k] for k in ('x','y','z')];yaw=site['yaw'];shots=[]
 for mid,cid,orientation in selections:
  matches=[s for s in original if s['motion_id']==mid and s['camera_id']==cid and s['orientation']==orientation]
  if len(matches)!=1:raise ValueError('Unknown selection')
  shot=copy.deepcopy(matches[0]);shot['source_frozen_shot_id']=shot['shot_id'];shot['shot_id']='site_'+site['site_id']+'_'+str(len(shots)+1)+'_'+revision
  shot.update(group='scenes',scene_id=scene_id,scene_anchor_cm=position,scene_yaw_degrees=yaw,actor_offset_cm=position)
  for row in shot['frames']+[shot['endpoint_validation_frame']]:
   row['position']=geo.transform_point(row['position'],position,yaw);row['look_at']=geo.transform_point(row['look_at'],position,yaw);row['rotation_pitch_yaw_roll'][1]+=yaw
  shot['trajectory_sha256']=hashlib.sha256(json.dumps(shot['frames']+[shot['endpoint_validation_frame']],sort_keys=True,separators=(',',':')).encode()).hexdigest();shots.append(shot)
 plan={'schema':'scene_site_review_pilot_plan_v1','scene_id':scene_id,'revision':revision,'site':site,'site_pin':pin(site_file),'shots':shots,'human_acceptance':'pending'}
 path=RUN/'pilot_plans'/('scene_'+site['site_id']+'_'+revision+'.json')
 if path.exists() and read(path)!=plan:raise ValueError('Existing pilot plan differs; select new revision')
 save(path,plan);return path

def prepare(u,plan_path,ids=None):
 plan=read(plan_path)
 if pin(plan['site_pin']['path'])!=plan['site_pin']:raise ValueError('Saved point changed; rebuild explicit plan')
 base=module('ue_motion_portrait_scene_pilot_v1');alignment=module('ue_camera_alignment_review_v1');scene=module('ue_scene_character_pilot_v1')
 base.RUN,base.A=RUN,ASSETS;base.ensure_motion=alignment.existing_composite
 original_module=base.module
 def configured(name):
  m=original_module(name)
  if name=='ue_motion_scene_sequence_v1':m.ALLOWED_PREFIX=ASSETS+'/'
  return m
 base.module=configured;scene.base=base;scene.RUN,scene.A=RUN,ASSETS
 # Explicit current map from saved point, rather than old historical alias.
 scene.locations=type('SiteMap',(),{'current_map':staticmethod(lambda scene_id:plan['site']['map'])})
 return scene.prepare(u,plan_path,ids)

def render(u,plan_path,attempt,ids):
 plan=read(plan_path);shots={s['shot_id']:s for s in plan['shots']};selected=[shots[x] for x in ids]
 if len({(s['width'],s['height']) for s in selected})!=1:raise ValueError('Render one aspect per batch')
 jobs=[]
 for s in selected:
  receipt=read(RUN/'scene_sequences'/(s['shot_id']+'.json'))
  if not receipt['success'] or receipt['plan']!=pin(plan_path):raise ValueError('Preparation missing or changed')
  for p in receipt['asset_files']+receipt['source_pins']:
   if pin(p['path'])!=p:raise ValueError('Prepared assets changed')
  jobs.append(receipt['job'])
 m=module('ue_motion_scene_render_v1');m.RUN,m.ASSET_ROOT,m.LIVE_ATTRIBUTE=RUN,ASSETS,'_dm_scene_site_review_render_v1'
 return m.start_render(u,jobs,attempt,width=selected[0]['width'],height=selected[0]['height'])

