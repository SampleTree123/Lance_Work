"""Independent static head/hair review using the current formal identities and hair.

Source meshes/materials and saved appearance/site files are never edited.
"""
import copy,json,math,uuid,importlib
from pathlib import Path
import unreal as u
import scene_site_appearance_v1 as contract
import ue_scene_site_appearance_v1 as assembly
import ue_complete_character_fixed_slot_runtime_v1 as fixed

RUN=Path(__file__).resolve().parents[2]/'outputs/hair_only_review_20261017_v1'
ROOT='/Game/DataMake/Review/HairOnly20261017'
LEVEL=ROOT+'/L_HairOnlyReview'
PREFIX='DM_HairOnly_'
SUBJECT='DM_SiteReview_HairOnly_Character'
LIVE='_dm_hair_only_review_v1'
CACHE='_dm_hair_only_catalog_v1'
VIEWS={'front':0.,'side':90.,'back':180.,'threequarter':45.}

def write(name,value):
 RUN.mkdir(parents=True,exist_ok=True)
 (RUN/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')

def world_path():return u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]
def actors():return u.get_editor_subsystem(u.EditorActorSubsystem)
def find(label):return next((a for a in actors().get_all_level_actors() if a.get_actor_label()==label),None)
def actor(name,cls,location=None,rotation=None):
 value=find(PREFIX+name)
 if value is None:
  value=actors().spawn_actor_from_class(cls,location or u.Vector(),rotation or u.Rotator(),transient=False)
  value.set_actor_label(PREFIX+name)
 return value

def data():
 # Inspection session: validate/load once, rather than resetting the formal
 # catalog's asset-hash cache on every click. Restart UE to refresh the catalog.
 cached=getattr(u,CACHE,None)
 if cached is None:
  cached=contract.catalog();setattr(u,CACHE,cached)
 return cached

def public_catalog(full):
 return {'identities':copy.deepcopy(full['identities']),
         'hairs_by_sex':{sex:[{'hair_id':h['hair_id'],'index':h['index'],
                              'label':h.get('label') or h.get('name') or h['hair_id']} for h in full['hairs_by_sex'][sex]] for sex in ('female','male')}}

def state():
 value=getattr(u,LIVE,None)
 if value is None:
  value={}
  path=RUN/'last_selection.json'
  if path.exists():value=json.loads(path.read_text(encoding='utf8'))
  setattr(u,LIVE,value)
 return value

def ensure_level():
 levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
 if world_path()==LEVEL:return levels
 # Stop only the current site's preview/check before its world is unloaded.
 import ue_primary_saved_site_review_v1 as adapter
 cached=getattr(u,adapter.CACHE,None)
 if cached:
  cached.pause_playback();cached.cancel()
 original=world_path();dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
 entry={'source_map':original,'dirty_maps':dirty,'backup_map':None}
 if original in dirty:
  backup=ROOT+'/Recovery/L_PreHairReview_'+uuid.uuid4().hex[:12]
  world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  if not u.EditorLoadingAndSavingUtils.save_map(world,backup):raise RuntimeError('当前关卡备份失败，已保留现场。')
  entry['backup_map']=backup
 write('entry_context.json',entry)
 if cached:cached.restore()
 assembly.invalidate_cache(u)
 levels.eject_pilot_level_actor()
 opened=levels.load_level(LEVEL) if u.EditorAssetLibrary.does_asset_exist(LEVEL) else levels.new_level(LEVEL)
 if not opened:raise RuntimeError('无法打开独立头发审查关卡。')
 return levels

def environment():
 material=u.load_asset(ROOT+'/M_NeutralBackground')
 if material is None:
  material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_NeutralBackground',ROOT,u.Material,u.MaterialFactoryNew())
  material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
  material.set_editor_property('two_sided',True)
  color=u.MaterialEditingLibrary.create_material_expression(material,u.MaterialExpressionConstant3Vector)
  color.set_editor_property('constant',u.LinearColor(.055,.055,.055,1))
  u.MaterialEditingLibrary.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
  u.MaterialEditingLibrary.recompile_material(material);u.EditorAssetLibrary.save_loaded_asset(material,False)
 background=actor('Background',u.StaticMeshActor,u.Vector(0,0,160))
 background.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'))
 background.static_mesh_component.set_material(0,material);background.static_mesh_component.set_cast_shadow(False)
 background.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
 background.set_actor_scale3d(u.Vector(20,20,20))
 key=actor('Key',u.DirectionalLight,u.Vector(0,0,300),u.Rotator(pitch=-35,yaw=-145))
 key.get_component_by_class(u.DirectionalLightComponent).set_editor_property('intensity',.7)
 for name,x,y,yaw,intensity in [('Fill',180,70,180,100.),('Rim',-150,-80,0,70.)]:
  light=actor(name,u.RectLight,u.Vector(x,y,190),u.Rotator(yaw=yaw))
  light.get_component_by_class(u.RectLightComponent).set_editor_properties({'intensity':intensity,'source_width':180.,'source_height':180.})
 volume=actor('Exposure',u.PostProcessVolume)
 volume.set_editor_property('unbound',True)
 settings=volume.get_editor_property('settings')
 settings.set_editor_properties({'override_auto_exposure_method':True,'auto_exposure_method':u.AutoExposureMethod.AEM_MANUAL,
  'override_auto_exposure_apply_physical_camera_exposure':True,'auto_exposure_apply_physical_camera_exposure':False,
  'override_auto_exposure_bias':True,'auto_exposure_bias':-1.8})
 volume.set_editor_property('settings',settings)
 cam=actor('Camera',u.CameraActor)
 cam.get_component_by_class(u.CameraComponent).set_editor_properties({'field_of_view':28.,'constrain_aspect_ratio':True,'aspect_ratio':1.})
 return cam

def inspection_record(components):
 import hair_eye_color_runtime_v1 as colors
 out=[];lib=u.MaterialEditingLibrary
 for name,c in components.items():
  if not name.startswith('HairPart'):continue
  mesh=c.get_skeletal_mesh_asset()
  if mesh is None:continue
  for i,slot in enumerate(mesh.get_editor_property('materials')):
   source=slot.material_interface;actual=c.get_material(i)
   row={'component':name,'slot':i,'source':colors._path(source),'actual':colors._path(actual),
        'source_material_retained':actual==source,'cast_shadow':c.get_editor_property('cast_shadow')}
   if isinstance(actual,u.MaterialInstanceConstant):
    props=actual.get_editor_property('base_property_overrides')
    row['base_overrides']={}
    for field in ('override_blend_mode','blend_mode','override_shading_model','shading_model','override_two_sided','two_sided','override_opacity_mask_clip_value','opacity_mask_clip_value'):
     try:row['base_overrides'][field]=str(props.get_editor_property(field))
     except Exception:pass
    row['parent_chain']=[colors._path(m) for m in colors._chain(actual)]
    parameters={str(n) for n in lib.get_scalar_parameter_names(actual)}
    row['alpha_parameters']={n:lib.get_material_instance_scalar_parameter_value(actual,n) for n in ('Alpha Power','Alpha Multiplier','Opacity Strength','Increase Opacity Mask Min Value','PixelDepthOffset') if n in parameters}
   out.append(row)
 return out

def set_view(view):
 if view not in VIEWS:raise ValueError('不支持的观察角度。')
 if world_path()!=LEVEL:raise RuntimeError('请先显示人物以打开头发审查关卡。')
 body_actor=find(SUBJECT);camera=find(PREFIX+'Camera')
 if not body_actor or not camera:raise RuntimeError('请先显示人物。')
 body=fixed.actor_components(body_actor)['Body']
 target=body.get_socket_location('head')+u.Vector(0,0,7)
 angle=math.radians(VIEWS[view]);location=target+u.Vector(120*math.cos(angle),120*math.sin(angle),0)
 camera.set_actor_location_and_rotation(location,u.MathLibrary.find_look_at_rotation(location,target),False,True)
 levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
 levels.editor_set_viewport_realtime(True);levels.editor_set_game_view(True);levels.pilot_level_actor(camera);levels.editor_invalidate_viewports()
 state()['view']=view

def show(request,full):
 person=next((p for p in full['identities'] if p['id']==request.get('character_id')),None)
 if person is None:raise ValueError('请选择当前目录中的人物。')
 hair=next((h for h in full['hairs_by_sex'][person['sex']] if h['hair_id']==request.get('hair_id')),None)
 if hair is None:raise ValueError('请选择当前性别保留的发型。')
 selection=contract.default_selection(full,person['sex'])
 selection.update(character_id=person['id'],hair_color='original',face_id='none')
 selection['choice']={'family_id':None,'group_id':None,'slot_choices':{},'optional_asset_ids':[],'shared_shoe_id':None,'hair_id':hair['hair_id']}
 # Use precisely the same saved template and assembler as production preview.
 import ue_motion_portrait_scene_pilot_v1 as stage
 formal=contract.formal_runtime()
 if not formal:raise RuntimeError('正式资产目录尚未启用。')
 overlay=formal[1].formal_path_overlay
 template_path=overlay.get(stage.SOURCES[person['sex']],stage.SOURCES[person['sex']])
 levels=ensure_level()
 if any(find(PREFIX+name) is None for name in ('Background','Key','Fill','Rim','Exposure','Camera')):environment()
 body_actor=find(SUBJECT)
 previous=next((p for p in full['identities'] if p['id']==state().get('character_id')),None)
 reused=bool(body_actor and previous and previous['sex']==person['sex'])
 if not reused:
  template=u.load_asset(template_path)
  candidates=[a for a in u.GameplayStatics.get_all_actors_of_class(template,u.Actor)
              if a.get_actor_label()=='DM_CCWH_'+person['sex']+'_Character']
  if len(candidates)!=1:raise RuntimeError('未找到唯一的正式槽位人物模板。')
  if body_actor:
   assembly.invalidate_cache(u,body_actor);actors().destroy_actor(body_actor)
  body_actor=actors().duplicate_actor(candidates[0],u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),u.Vector())
  body_actor.set_actor_label(SUBJECT)
  body_actor.set_actor_location(u.Vector(),False,False)
  # Orient the whole template; leave all slot/component transforms intact.
  body_actor.set_actor_rotation(u.Rotator(yaw=-90),False)
 actual=assembly.apply_actor(u,body_actor,selection,0.,None,data=full,path_overlay=overlay)
 components=fixed.actor_components(body_actor)
 # Keep all template component flags, LOD policy and body materials unchanged.
 # The close camera excludes the body; unused clothing slots are emptied by
 # the production assembler itself, not by a separate visibility workaround.
 state().update(character_id=person['id'],hair_id=hair['hair_id'],view=request.get('view','front'))
 set_view(state()['view']);actors().set_selected_level_actors([])
 # Selection is persisted below; do not save/validate the map on every switch.
 write('last_selection.json',state())
 rows=inspection_record(components)
 report={'success':True,'level':LEVEL,'state':copy.deepcopy(state()),'hair_materials':rows,
         'source_material_bindings_unchanged':all(r['source_material_retained'] for r in rows),
         'hair_coverage':actual.get('hair_coverage'),'source_assets_modified':False,
         'clothing_components':0,'body_animation':None,'hair_color':'original','hair_shadows_disabled':False,
         'assembly_mode':'production_template_and_apply_actor','template_map':template_path,
         'actor_reused':reused,'level_saved_on_switch':False,
         'actor_class':body_actor.get_class().get_path_name(),'component_count':len(components),
         'formal_assembly_readback':actual}
 try:report['anti_aliasing_method']=u.SystemLibrary.get_console_variable_int_value('r.AntiAliasingMethod')
 except Exception:pass
 write('latest_review_receipt.json',report)
 return report

def dispatch(request):
 action=request.get('action')
 if action=='view':
  set_view(request.get('view'));write('last_selection.json',state())
  return {'success':True,'request_id':request.get('request_id'),'state':copy.deepcopy(state()),'level':LEVEL}
 full=data()
 if action in {'catalog','status'}:result={'success':True}
 elif action=='show':result=show(request,full)
 elif action=='view':set_view(request.get('view'));write('last_selection.json',state());result={'success':True}
 else:raise ValueError('未知头发审查操作。')
 return {**result,'request_id':request.get('request_id'),'catalog':public_catalog(full),'state':copy.deepcopy(state()),'level':LEVEL}
