"""Prepare isolated 30-shot camera pilot from frozen trajectories and modular scene.
Technical owner: SCENE_CAMERA_SEQUENCE.md section 7. Explicit root-only UE use.
"""
import json,sys,hashlib
from pathlib import Path
import unreal as u
S=Path(__file__).resolve().parent
sys.path.insert(0,str(S))
import ue_camera_sequence_builder_v1 as builder
import ue_cfd40_full_motion_loop_v1 as loop
R=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
A='/Game/DataMake/Validation/CameraMotionPilot20261009'
BASE=A+'/L_DM_CameraMotionPilot_v001'
loop.RUN=R;loop.ASSET_ROOT=A

def pin(p):
 p=Path(p);return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def main():
 subsystem=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
 if subsystem.is_rendering() or subsystem.get_active_executor():raise RuntimeError('Rendering is still active')
 planpath=R/'camera_motion_pilot_plan_v1.json';plan=json.loads(planpath.read_text(encoding='utf-8-sig'))
 faces,selection=loop.accepted_faces()
 levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
 actorsub=u.get_editor_subsystem(u.EditorActorSubsystem)
 jobs=[]
 for shot in plan['shots']:
  receipt=R/'sequences'/(shot['shot_id']+'.json')
  if receipt.exists():
   done=json.loads(receipt.read_text(encoding='utf-8-sig'));assert done['plan']==pin(planpath)
   for x in done['asset_files']:assert pin(x['path'])==x
   jobs.append(done['job']);continue
  choice,proof=faces[(shot['sex'],'smile')]
  motion,detail=loop.ensure_composite(u,shot['sex'],{'path':shot['animation_path'],'action_id':shot['clip_id']},choice,proof,selection)
  map_path=A+'/Maps/L_'+shot['shot_id']+'_v001'
  seq_path=A+'/Sequences/LS_'+shot['shot_id']+'_final_v001'
  if u.EditorAssetLibrary.does_asset_exist(map_path) or u.EditorAssetLibrary.does_asset_exist(seq_path):raise RuntimeError('Incomplete shot exists; inspect before retry '+shot['shot_id'])
  u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
  if not levels.load_level(BASE):raise RuntimeError('Cannot load baseline scene')
  world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  if not u.EditorLoadingAndSavingUtils.save_map(world,map_path):raise RuntimeError('Copy scene failed')
  if not levels.load_level(map_path):raise RuntimeError('Cannot explicitly load copied scene')
  world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  assert world.get_path_name().split('.')[0]==map_path
  actors=actorsub.get_all_level_actors()
  actor=next(a for a in actors if a.get_actor_label()=='DM_CCWH_'+shot['sex']+'_Character')
  for a in actors:
   if a.get_actor_label().endswith('_Character'):
    a.set_actor_hidden_in_game(a!=actor)
    a.set_actor_location(u.Vector(0,0,0),False,False);a.set_actor_rotation(u.Rotator(0,0,0),False)
  camera=next(a for a in actors if a.get_actor_label()=='DM_CCWH_Camera')
  followers=[]
  for c in actor.get_components_by_class(u.SkeletalMeshComponent):
   c.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
   if c.get_name() in ['Body','Eyes','Teeth','Tongue','Tearline','EyeOcclusion']:
    c.set_leader_pose_component(None,True,False);c.override_animation_data(motion,False,False,0.,1.)
    if c.get_name()!='Body':followers.append(c)
  comp=camera.get_component_by_class(u.CameraComponent)
  comp.set_editor_property('aspect_ratio',16/9);comp.set_editor_property('constrain_aspect_ratio',True)
  first=shot['frames'][0]
  camera.set_actor_location(u.Vector(*first['position']),False,False)
  camera.set_actor_rotation(u.Rotator(*first['rotation_pitch_yaw_roll']),False)
  comp.set_field_of_view(first['horizontal_fov_degrees'])
  result=builder.build_sequence(u,shot,actor,camera,motion,seq_path)
  for c in followers:builder.add_animation_component_track(u,result['sequence'],result['actor_binding'],c,motion)
  if not u.EditorAssetLibrary.save_loaded_asset(result['sequence'],False):raise RuntimeError('Sequence save failed')
  u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
  if not levels.save_current_level():raise RuntimeError('Scene save failed')
  job={'shot_id':shot['shot_id'],'map':world.get_path_name(),'sequence':result['sequence'].get_path_name()}
  files=[pin(Path('D:/UE/projects/datatry_02/Content')/(p.removeprefix('/Game/')+s)) for p,s in [(map_path,'.umap'),(seq_path,'.uasset')]]
  save(receipt,{'plan':pin(planpath),'job':job,'sequence_report':result['report'],'face_component_tracks':[c.get_name() for c in followers],'composition':detail,'asset_files':files,'status':'prepared_pending_render'})
  jobs.append(job)
  (R/'preparation_progress_v1.json').write_text(json.dumps({'prepared':len(jobs),'total':len(plan['shots']),'last_shot':shot['shot_id']}),encoding='utf-8')
  print('Prepared camera shot '+shot['shot_id'])
 save(R/'prepared_jobs_v1.json',{'schema':'camera_pilot_prepared_jobs_v1','plan':pin(planpath),'jobs':jobs,'status':'prepared_pending_render'})
if __name__=='__main__':main()
