"""Isolated camera pilot staging. Owner: SCENE_CAMERA_SEQUENCE.md section 7."""
import json,hashlib,traceback
from pathlib import Path
import unreal as u
RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
ASSET_ROOT='/Game/DataMake/Validation/CameraMotionPilot20261009'
MAP=ASSET_ROOT+'/L_DM_CameraMotionPilot_v001'
def record(p):
 p=Path(p);return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
 levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 original=world.get_path_name().split('.')[0]
 expected='/Game/DataMake/Validation/CFDNativeBatch4020261006/L_DM_CFDNativeBatch40_ModularReview_v001'
 if original!=expected or u.EditorAssetLibrary.does_asset_exist(MAP):raise RuntimeError('Unexpected scene or existing pilot map; inspect before retry')
 if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():raise RuntimeError('Render is active')
 src=Path('D:/UE/projects/datatry_02/Content')/(original.removeprefix('/Game/')+'.umap')
 before=record(src)
 snapshot={'original_map':original,'original_package':before,'dirty_maps_before':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
 u.EditorAssetLibrary.make_directory(ASSET_ROOT)
 if not u.EditorLoadingAndSavingUtils.save_map(world, MAP):raise RuntimeError('Independent Save As failed')
 if not levels.load_level(MAP):raise RuntimeError('Cannot load copied pilot map')
 if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]!=MAP:raise RuntimeError('Pilot map did not become current')
 actors=u.get_editor_subsystem(u.EditorActorSubsystem)
 details=[]
 for a in actors.get_all_level_actors():
  label=a.get_actor_label()
  if label=='DM_CCWH_Background':
   actors.destroy_actor(a);continue
  if label.endswith('_Character'):
   a.set_actor_location(u.Vector(0,0,0),False,False);a.set_actor_rotation(u.Rotator(0,0,0),False)
   a.set_actor_hidden_in_game('male_Character' in label and 'female' not in label)
   comps=[]
   for c in a.get_components_by_class(u.SkeletalMeshComponent):
    c.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    comps.append({'name':c.get_name(),'visible':c.is_visible(),'leader':str(c.get_editor_property('leader_pose_component')),'materials':[m.get_path_name() if m else None for m in c.get_materials()]})
   details.append({'actor':label,'components':comps})
  elif label=='DM_CCWH_Floor':
   a.set_actor_scale3d(u.Vector(100,100,0.1))
 if not levels.save_current_level():raise RuntimeError('Cannot save pilot')
 if record(src)!=before:raise RuntimeError('Original map file changed')
 snapshot.update(success=True,pilot_map=MAP,characters=details,source_map_unchanged=True)
 (RUN/'stage_v1.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Independent camera map staged; original map file unchanged')
if __name__=='__main__':main()

