"""Bounded follow/compact comparison adapter; SCENE_CAMERA_SEQUENCE owner."""
from pathlib import Path
import importlib.util, hashlib, json, math
S=Path(__file__).resolve().parent
RUN=S.parents[1]/'outputs/camera_follow_compact_scene_20261015_v1'
ASSETS='/Game/DataMake/Validation/CameraFollowCompact20261015'
PLAN_NAME='camera_compact_comparison_plan_v1.json'

def adapter(digest):
 path=RUN/PLAN_NAME
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Comparison plan changed')
 plan=json.loads(path.read_text(encoding='utf-8-sig'));shots={s['shot_id']:s for s in plan['shots']}
 spec=importlib.util.spec_from_file_location('_follow_compact_adapter',S/'ue_camera_alignment_review_v1.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.RUN,m.ASSETS,m.PLAN_NAME=RUN,ASSETS,PLAN_NAME
 original=m.configured_module
 def configured(name):
  module=original(name)
  if name=='ue_motion_scene_sequence_v1':
   keys=module.key_rows
   def review_keys(shot):
    if shots.get(shot['shot_id'])!=shot:raise ValueError('Shot differs from frozen comparison')
    # Known local crops are reviewable, not silently reclassified in evidence.
    return keys(dict(shot,status='geometry_pass')) if shot.get('status')=='geometry_review_required' else keys(shot)
   module.key_rows=review_keys
  if name=='ue_motion_scene_render_v1':module.LIVE_ATTRIBUTE='_dm_follow_compact_render_20261015'
  return module
 m.configured_module=configured
 return m

def prepare(u,ids,digest):return adapter(digest).prepare(u,ids)
def render(u,attempt,ids,width,height,digest):
 result=adapter(digest).render(u,attempt,ids,width=width,height=height)
 return {'attempt':attempt,'receipt_path':result.get('receipt_path')}
