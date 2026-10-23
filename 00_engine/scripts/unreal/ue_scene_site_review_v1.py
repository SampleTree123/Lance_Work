"""UE point review runtime. Temporary actors only; scene assets never saved here."""
from pathlib import Path
from collections import deque
import copy, json, math, hashlib, uuid, time, traceback
import unreal as u
import scene_site_review_geometry_v1 as geo
S=Path(__file__).resolve().parent
RUN=S.parents[1]/'outputs/scene_site_review_20261014_v1'
LIVE='_dm_site_review_v1'
PREFIX='DM_SiteReview_'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def xyz(v): return [float(v.x),float(v.y),float(v.z)]
def vec(v):return u.Vector(*v)
def world():return u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
def actors():return u.get_editor_subsystem(u.EditorActorSubsystem)
def live():
 if not hasattr(u,LIVE):
  local=read(RUN/'site_review_local_geometry_v1.json');geo.verify_sources(local['sources'])
  setattr(u,LIVE,{'local':local,'site':None,'marker':None,'character':None,'camera':None,'job':None,'report':None,'ranges':False,'preview':{},'original_view':u.get_editor_subsystem(u.UnrealEditorSubsystem).get_level_viewport_camera_info()})
 d=getattr(u,LIVE)
 if 'original_fov' not in d:
  v=u.get_editor_subsystem(u.LevelEditorSubsystem);d['original_fov']=v.get_level_viewport_fov(v.get_active_viewport_config_key())
 if d.get('runtime_version')!=8:
  import importlib
  importlib.reload(geo)
  if d.get('playback_handle'):u.unregister_slate_post_tick_callback(d.pop('playback_handle'))
  d['local']=read(RUN/'site_review_local_geometry_v1.json');geo.verify_sources(d['local']['sources'])
  import camera_standard_v3 as standard
  d.update(runtime_version=8,frozen_shots={},loaded_plan_roots=set(),motions={},shot_index={s['shot_id']:s for s in d['local']['shots']},camera_standard=standard.load_config(geo.CAMERA_STANDARD))
  d['runtime_inputs']=[*d['local']['sources'],geo.pin(RUN/'site_review_local_geometry_v1.json'),geo.pin(RUN/'site_review_catalog_v1.json'),geo.pin(__file__)]
  d['input_stats']={};d['input_result']=None
 return d
def owned():return [a for a in u.GameplayStatics.get_all_actors_of_class(world(),u.Actor) if a.get_actor_label().startswith(PREFIX)]
def current_map():return world().get_path_name().split('.')[0]
def synchronize():
 d=live();m=d.get('marker')
 if m and u.SystemLibrary.is_valid(m) and d['site'] and d['site']['map']==current_map():
  d['site']['position']=dict(zip(('x','y','z'),xyz(m.get_actor_location())));d['site']['yaw']=float(m.get_actor_rotation().yaw)
 return d

def _safe(call):
 try:return _plain(call())
 except Exception:return {'unavailable':True}

def _plain(value):
 if value is None or isinstance(value,(str,int,float,bool)):return value
 if isinstance(value,(list,tuple)):return [_plain(v) for v in value]
 if hasattr(value,'get_path_name'):return value.get_path_name()
 if all(hasattr(value,k) for k in ('pitch','yaw','roll')):return [float(value.pitch),float(value.yaw),float(value.roll)]
 if all(hasattr(value,k) for k in ('x','y','z')):return xyz(value)
 return str(value)

def _component_state(c):
 record={'path':_safe(c.get_path_name)}
 for prop in ('relative_location','relative_rotation','relative_scale3d','visible','hidden_in_game',
              'static_mesh','skeletal_mesh_asset','box_extent','sphere_radius','capsule_radius','capsule_half_height'):
  record[prop]=_safe(lambda prop=prop:c.get_editor_property(prop))
 for method in ('get_collision_enabled','get_collision_profile_name','get_materials','get_local_bounds'):
  record[method]=_safe(lambda method=method:getattr(c,method)())
 record['visibility_response']=_safe(lambda:c.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY))
 return record

def scene_signature():
 # Best effort observable state; unsupported component fields never abort review.
 rows=[]
 for a in actors().get_all_level_actors():
  if a.get_actor_label().startswith(PREFIX):continue
  # Do not serialize component handles: inspect their individual current fields.
  try:components=sorted((_component_state(c) for c in a.get_components_by_class(u.PrimitiveComponent)),key=lambda r:str(r['path']))
  except Exception:components=[{'unavailable':True}]
  rows.append({'path':_safe(a.get_path_name),'location':_safe(a.get_actor_location),
               'rotation':_safe(a.get_actor_rotation),'scale':_safe(a.get_actor_scale3d),
               'hidden':_safe(lambda:a.get_editor_property('hidden')),'components':components})
 dirty=_safe(lambda:[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
             +[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
 return geo.canonical_sha({'actors':sorted(rows,key=lambda r:str(r['path'])),'dirty_packages':sorted(dirty) if isinstance(dirty,list) else dirty})

def _file_stat(path):
 st=Path(path).stat();return [st.st_size,st.st_mtime_ns,st.st_ctime_ns]

def input_status(force=False):
 """Hash on first use or metadata change; ordinary polling only stats files."""
 d=live();changed=[];stats={};errors=[]
 for record in d['runtime_inputs']:
  path=record['path']
  try:
   stats[path]=_file_stat(path)
   if force or d['input_stats'].get(path)!=stats[path]:
    if geo.pin(path)['sha256']!=record['sha256']:errors.append(path)
  except Exception:stats[path]=None;errors.append(path)
  if d['input_stats'].get(path)!=stats[path]:changed.append(path)
 if not force and not changed and d.get('input_result') is not None:return d['input_result']
 # A previously mismatched file remains invalid until actually restored.
 previous=d.get('input_result') or {}
 errors=list(set(errors+[p for p in previous.get('changed_files',[]) if p not in changed and not force]))
 result={'valid':not errors,'changed_files':sorted(errors),
         'signature':geo.canonical_sha({'expected':d['runtime_inputs'],'stats':stats,'invalid':sorted(errors)})}
 d['input_stats']=stats;d['input_result']=result
 if errors:
  d['frozen_shots'].clear();d['motions'].clear();d['loaded_plan_roots']=set()
 return result
def stamp():
 d=synchronize();site=d['site'];site={k:site.get(k) for k in ('site_id','map','position','yaw')} if site else None
 return geo.canonical_sha({'site':site,'input':d['local']['input_fingerprint'],
  'runtime_inputs':input_status()['signature'],'scene':scene_signature()})
def state():
 d=synchronize();s=dict(d['site'] or {});j=d.get('job')
 s['current_map']=current_map()
 report=d.get('report') or {};valid=input_status()['valid'];current_stamp=stamp();same=report.get('stamp')==current_stamp
 summary=report.get('summary',{});scope=report.get('scope',{})
 fresh=valid and same and report.get('status')=='complete' and summary.get('checked_items',-1)==summary.get('total_items',-2)
 full=fresh and scope.get('kind')=='all' and scope.get('combinations')==len(d['local']['shots']) and report.get('coverage',{}).get('full_matrix_checked',False)
 s['current_result_fresh']=fresh;s['full_matrix_fresh']=full;s['needs_recheck']=not full
 s['recheck_reason']=('输入已改变，请重新准备并检查。' if not valid else
   '尚未完成检查。' if not report else '检查已取消、失败或过期，请重新检查。' if report.get('status')!='complete' else
   '点位或场景已改变，请重新检查。' if not same else '剩余组合已检查；已排除组合未检查。' if fresh and scope.get('kind')=='remaining' else '仅检查了当前组合，全量仍待检查。' if not full else '')
 s['check']={'status':j.get('status') if j else 'idle','completed':j.get('completed',0) if j else 0,'total':j.get('total',0) if j else 0}
 s['check']['scope']=j.get('scope') if j else report.get('scope')
 if report:s['check']['report']=report
 s['decisions_fresh']=valid and s.get('decisions_stamp')==current_stamp
 s['review_stamp']=current_stamp
 if not s['decisions_fresh']:s['allowed_combinations']=[];s['issue_reviews']={}
 s['preview']=d['preview'];s['show_ranges']=d['ranges']
 s['playback']=dict(d.get('playback',{'playing':False,'time_seconds':0.,'duration_seconds':0.,'loop':False}))
 return s

def catalog():
 c=read(RUN/'site_review_catalog_v1.json')
 import scene_site_catalog_v1 as directory
 scenes=directory.build_catalog()
 return {'motions':[{'id':a.get('motion_id',a.get('id')),'label':a.get('label',a.get('motion_label')),'duration_seconds':a.get('duration_seconds',a.get('clock',{}).get('duration_seconds',0))} for a in c['actions']], 'cameras':[{'id':a.get('camera_id',a.get('id')),'label':a.get('label',a.get('camera_label',a.get('camera_id',a.get('id'))))} for a in c['cameras']], 'aspects':['landscape','portrait'],'sites':scenes['sites'],'scenes':scenes['scenes'],'scene_counts':scenes['counts']}

def open_scene(p):
 import scene_site_catalog_v1 as directory
 target=p.get('map_path')
 if target not in {s['map_path'] for s in directory.build_catalog()['scenes']}:raise ValueError('目标不在场景目录中。')
 if target==current_map():return
 if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():raise ValueError('当前正在渲染，请结束后打开场景。')
 dirty=[a.get_path_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
 if dirty:raise ValueError('当前关卡有未保存变更，请先在 UE 保存或处理后再打开其他场景：'+', '.join(dirty))
 restore()
 if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(target):raise ValueError('场景打开失败：'+target)
 d=live();d['original_view']=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_level_viewport_camera_info()
 v=u.get_editor_subsystem(u.LevelEditorSubsystem);d['original_fov']=v.get_level_viewport_fov(v.get_active_viewport_config_key())
def require_site():
 d=synchronize()
 if not d['site']:raise ValueError('请先创建或载入点位。')
 if d['site']['map']!=current_map():raise ValueError('当前关卡与点位不一致，请在当前关卡新建点位或打开原关卡。')
 return d

def create(p):
 restore()
 selected=actors().get_selected_level_actors();location=xyz(selected[0].get_actor_location()) if selected else [0,0,0]
 if 'position' in p:location=[p['position'][k] for k in ('x','y','z')]
 d=live();sid=p.get('site_id') or 'site_'+uuid.uuid4().hex[:10]
 if not sid.replace('_','').isalnum():raise ValueError('点位ID不合法')
 m=actors().spawn_actor_from_class(u.TargetPoint,vec(location),u.Rotator(pitch=0,yaw=float(p.get('yaw',0)),roll=0),transient=True);m.set_actor_label(PREFIX+sid)
 d['marker']=m;d['site']={'site_id':sid,'name':p.get('name') or sid,'map':current_map(),'position':dict(zip(('x','y','z'),location)),'yaw':float(p.get('yaw',0))}
 actors().set_selected_level_actors([m]);return d

def update(p):
 d=require_site();m=d['marker'];pos=p.get('position',d['site']['position']);v=[float(pos[k]) for k in ('x','y','z')];yaw=float(p.get('yaw',d['site']['yaw']))
 if not all(math.isfinite(x) for x in v+[yaw]):raise ValueError('坐标或角度无效')
 m.set_actor_location(vec(v),False,False);m.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),False)
 if p.get('name'):d['site']['name']=str(p['name'])
 synchronize();return d

def hit_data(h):
 if not h:return None
 r=h.to_tuple()
 if not r[0]:return None
 return {'point':xyz(r[5]),'normal':xyz(r[7]),'distance':float(r[3]),'actor':r[9].get_actor_label() if r[9] else None}
def trace_ignored():
 j=live().get('job')
 return j['ignored'] if j and j.get('status')=='running' and 'ignored' in j else owned()
def ray(a,b):return hit_data(u.SystemLibrary.line_trace_single(world(),vec(a),vec(b),u.TraceTypeQuery.ECC_VISIBILITY,True,trace_ignored(),u.DrawDebugTrace.NONE))
def sphere(a,b,r):return hit_data(u.SystemLibrary.sphere_trace_single(world(),vec(a),vec(b),r,u.TraceTypeQuery.ECC_VISIBILITY,True,trace_ignored(),u.DrawDebugTrace.NONE))
def snap():
 d=require_site();p=[d['site']['position'][k] for k in ('x','y','z')];h=ray([p[0],p[1],p[2]+100],[p[0],p[1],p[2]-1000])
 if not h:raise ValueError('起点上下范围内没有找到可碰撞地面，请先把点位移动到地面附近。')
 if h['normal'][2]<.7:raise ValueError('命中表面过陡，不作为起点地面。')
 update({'position':dict(zip(('x','y','z'),h['point']))});return h

def placed(selection=None):
 d=require_site();local=d['local']
 if selection is not None:
  mid=selection.get('action_id','MOTION_CAND_003');cid=selection.get('camera_id','front_full');o=selection.get('aspect','portrait')
  shots=[s for s in local['shots'] if s['motion_id']==mid and s['camera_id']==cid and s['orientation']==o]
  local={**local,'shots':shots,'actions':[a for a in local['actions'] if a['motion_id']==mid]}
 return geo.place_geometry(local,[d['site']['position'][k] for k in ('x','y','z')],d['site']['yaw'])
def select(p,g=None):
 g=g if g is not None else placed(p);mid=p.get('action_id','MOTION_CAND_003');cid=p.get('camera_id','front_full');o=p.get('aspect','portrait')
 found=[s for s in g['shots'] if s['motion_id']==mid and s['camera_id']==cid and s['orientation']==o]
 if len(found)!=1:raise ValueError('未知的动作/镜头/画幅组合')
 return found[0],next(a for a in g['actions'] if a['motion_id']==mid)
def frozen_shot(shot_id):
 d=live()
 from camera_standard_v3 import apply_standard
 if not input_status()['valid']:raise ValueError('输入已经改变，请重新准备检查数据。')
 if shot_id in d['frozen_shots']:return d['frozen_shots'][shot_id]
 if str(geo.FOLLOW_CORRECTION) not in d.setdefault('loaded_plan_roots',set()) and geo.FOLLOW_CORRECTION.is_file():
  d['frozen_shots'].update({s['shot_id']:apply_standard(s,d['camera_standard']) for s in read(geo.FOLLOW_CORRECTION)['corrected_shots']})
  d['loaded_plan_roots'].add(str(geo.FOLLOW_CORRECTION))
  if shot_id in d['frozen_shots']:return d['frozen_shots'][shot_id]
 for root in (geo.NONFACE,geo.FACE):
  if str(root) not in d.setdefault('loaded_plan_roots',set()):
   for s in read(root/'camera_trial_plan_v1.json')['shots']:d['frozen_shots'].setdefault(s['shot_id'],apply_standard(s,d['camera_standard']))
   d['loaded_plan_roots'].add(str(root))
  if shot_id in d['frozen_shots']:return d['frozen_shots'][shot_id]
 raise ValueError('原镜头不存在')
def enable_live_view():
 d=live();settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
 if 'background_throttle_original' not in d:d['background_throttle_original']=settings.get_editor_property('bThrottleCPUWhenNotForeground')
 settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
 u.EditorLevelLibrary.editor_invalidate_viewports()

def preview(p):
 d=require_site()
 if p.get('_playback_tick'):
  shot=d['playback_shot']
 else:
  shot,_=select(p);enable_live_view()
 t=max(0,min(float(p.get('time_seconds',0)),shot['clock']['duration_seconds']))
 original=frozen_shot(shot['shot_id']);row=min(original['frames']+[original['endpoint_validation_frame']],key=lambda x:abs(x['t']-t));t=row['t'];position=[d['site']['position'][k] for k in ('x','y','z')];yaw=d['site']['yaw']
 import ue_camera_alignment_review_v1 as alignment
 import ue_camera_prepare_studio_v2 as helper
 import ue_motion_portrait_scene_pilot_v1 as base
 ch=d.get('character')
 if not ch or not u.SystemLibrary.is_valid(ch) or d.get('sex')!=original['sex']:
  if ch and u.SystemLibrary.is_valid(ch):actors().destroy_actor(ch)
  template=u.load_asset(base.SOURCES[original['sex']]);candidates=[a for a in u.GameplayStatics.get_all_actors_of_class(template,u.Actor) if a.get_actor_label()=='DM_CCWH_'+original['sex']+'_Character']
  if len(candidates)!=1:raise ValueError('未找到模块化人物模板')
  ch=actors().duplicate_actor(candidates[0],world(),u.Vector(0,0,0));ch.set_actor_label(PREFIX+'Character');d['character']=ch;d['sex']=original['sex']
 ch.set_actor_location(vec(position),False,False);ch.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),False)
 motion_key=(original['motion_id'],original['sex'])
 if motion_key not in d['motions']:d['motions'][motion_key]=alignment.existing_composite(u,original)[0]
 motion=d['motions'][motion_key]
 for c in ch.get_components_by_class(u.SkeletalMeshComponent):
  if c.get_name() in helper.FACE_COMPONENTS:
   c.set_leader_pose_component(None,True,False)
   # OverrideAnimationData alone only updates saved data when mode is already
   # SingleNode. Explicitly update the live instance before forced evaluation.
   c.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
   c.set_animation(motion)
   c.set_position(float(original['window_start_seconds'])+t,False)
   c.override_animation_data(motion,False,False,float(original['window_start_seconds'])+t,1.);c.set_update_animation_in_editor(True)
 camera=d.get('camera')
 if not camera or not u.SystemLibrary.is_valid(camera):camera=actors().spawn_actor_from_class(u.CameraActor,u.Vector(),u.Rotator(),transient=True);camera.set_actor_label(PREFIX+'Camera');d['camera']=camera
 loc=geo.transform_point(row['position'],position,yaw);rot=list(row['rotation_pitch_yaw_roll']);rot[1]+=yaw
 camera.set_actor_location(vec(loc),False,False);camera.set_actor_rotation(u.Rotator(pitch=rot[0],yaw=rot[1],roll=rot[2]),False)
 c=camera.get_component_by_class(u.CameraComponent);c.set_field_of_view(row['horizontal_fov_degrees']);c.set_editor_property('aspect_ratio',original['aspect_ratio']);c.set_editor_property('constrain_aspect_ratio',True)
 if not p.get('_playback_tick'):u.EditorLevelLibrary.pilot_level_actor(camera)
 d['preview']={'action_id':shot['motion_id'],'camera_id':shot['camera_id'],'aspect':shot['orientation'],'time_seconds':t}
 if d['ranges'] and not p.get('_playback_tick'):show_ranges(True)
 return d['preview']

def pause_playback():
 d=live()
 if d.get('playback_handle'):u.unregister_slate_post_tick_callback(d.pop('playback_handle'))
 if d.get('playback'):d['playback']['playing']=False

def playback_tick(delta):
 d=live();pb=d.get('playback')
 if not pb or not pb['playing']:return
 try:
  require_site()
  if any(d['site'].get(k)!=d['playback_site'].get(k) for k in ('map','position','yaw')):raise ValueError('点位改变，播放已暂停。')
  elapsed=time.monotonic()-d['playback_started'];duration=pb['duration_seconds']
  t=elapsed%duration if pb['loop'] else min(elapsed,duration)
  preview({**d['playback_selection'],'time_seconds':t,'_playback_tick':True})
  pb['time_seconds']=d['preview']['time_seconds']
  if not pb['loop'] and elapsed>=duration:pause_playback()
 except Exception as exc:
  pb['error']=str(exc);pause_playback()

def play(p):
 pause_playback();d=require_site();shot,_=select(p)
 d['playback_shot']=shot;d['playback_selection']={k:p[k] for k in ('action_id','camera_id','aspect')}
 d['playback_site']=copy.deepcopy(d['site'])
 duration=shot['clock']['duration_seconds'];start=max(0.,min(float(p.get('time_seconds',0.)),duration))
 if start>=duration:start=0.
 preview({**p,'time_seconds':start})
 d['playback']={'playing':True,'time_seconds':start,'duration_seconds':duration,'loop':bool(p.get('loop',False))}
 d['playback_started']=time.monotonic()-start;d['playback_handle']=u.register_slate_post_tick_callback(playback_tick)

def stop_playback():
 pause_playback();d=live()
 if d.get('playback_selection') and d.get('site') and d['site']['map']==current_map():preview({**d['playback_selection'],'time_seconds':0.})
 if d.get('playback'):d['playback']['time_seconds']=0.

def line(a,b,color):u.SystemLibrary.draw_debug_line(world(),vec(a),vec(b),color,3600.,2.)

def range_label(position,text,color):
 # TextRender actors are visible in the editor; debug HUD strings require play.
 p=[position[0],position[1],position[2]+18.]
 view_rotation=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_level_viewport_camera_info()[1]
 rotation=u.Rotator(pitch=-view_rotation.pitch,yaw=view_rotation.yaw+180.,roll=-view_rotation.roll)
 actor=actors().spawn_actor_from_class(u.TextRenderActor,vec(p),rotation,transient=True)
 actor.set_actor_label(PREFIX+'RangeLabel')
 component=actor.get_component_by_class(u.TextRenderComponent)
 component.set_text(text);component.set_world_size(20.)
 component.set_text_render_color(u.Color(*color,255))
def show_ranges(enabled):
 d=require_site();d['ranges']=bool(enabled);u.SystemLibrary.flush_persistent_debug_lines(world())
 for actor in owned():
  if actor.get_actor_label().startswith(PREFIX+'RangeLabel'):actors().destroy_actor(actor)
 if not enabled:return
 shot,act=select(d['preview'])
 green=u.LinearColor(0,1,0,1);blue=u.LinearColor(0,.5,1,1)
 for a,b in zip(act['root_route'],act['root_route'][1:]):line(a['position'],b['position'],green)
 for a,b in zip(shot['samples'],shot['samples'][1:]):line(a['position'],b['position'],blue)
 # Sampled skeleton envelopes make actual limb reach visible.
 for sample in act['samples'][::max(1,len(act['samples'])//8)]:
  for a,b in act['body_segments']:
   if a in sample['bones'] and b in sample['bones']:line(sample['bones'][a],sample['bones'][b],green)
 box=act['activity_bounds'];lo=box['minimum_xyz_cm'];hi=box['maximum_xyz_cm']
 u.SystemLibrary.draw_debug_box(world(),vec([(a+b)/2 for a,b in zip(lo,hi)]),vec([(b-a)/2 for a,b in zip(lo,hi)]),green,duration=3600.,thickness=1.)
 for rows,name,color in ((act['root_route'],'BODY',(100,255,100)),(shot['samples'],'CAM',(255,230,70))):
  indices=sorted(set([0,len(rows)//4,len(rows)//2,3*len(rows)//4,len(rows)-1]))
  groups=[]
  for index in indices:
   row=rows[index];edge=' START' if index==0 else ' END' if index==len(rows)-1 else ''
   text=f"{edge.strip()} {row['t']:.1f}s".strip()
   group=next((g for g in groups if math.dist(g['position'],row['position'])<35.),None)
   if group:group['times'].append(text)
   else:groups.append({'position':row['position'],'times':[text]})
  for group in groups:
   position=list(group['position'])
   if name=='BODY':position[1]-=70.
   range_label(position,name+'\n'+'\n'.join(group['times']),color)

def overview(selection=None):
 d=require_site()
 if selection and all(k in selection for k in ('action_id','camera_id','aspect')):preview(selection)
 elif not d['preview']:preview({})
 shot,act=select(d['preview']);points=[r['position'] for r in shot['samples']]+[act['activity_bounds'][k] for k in ('minimum_xyz_cm','maximum_xyz_cm')]
 lo=[min(p[i] for p in points) for i in range(3)];hi=[max(p[i] for p in points) for i in range(3)]
 center=[(a+b)/2 for a,b in zip(lo,hi)];span=max(hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2],300.)
 u.EditorLevelLibrary.eject_pilot_level_actor()
 view=u.get_editor_subsystem(u.LevelEditorSubsystem);view.set_level_viewport_fov(80.,view.get_active_viewport_config_key())
 eye=[center[0]-span*.45,center[1],center[2]+span*1.25]
 u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(vec(eye),u.Rotator(pitch=-70,yaw=0,roll=0))
 show_ranges(True)
 return {'legend':{'green':'人物路线、肢体与活动包围盒','blue':'相机路线','yellow':'相机时刻，秒'},'labels':'BODY/CAM START/END and quarter-time samples'}

def issue(job,kind,message,t,shot=None,mid=None,hit=None):
 key=(mid or shot['motion_id'],shot['shot_id'] if shot else '',kind)
 if key in job['seen']:return
 job['seen'].add(key);job['issues'].append({'id':str(len(job['issues'])+1),'severity':'review','kind':kind,'message':message,'action_id':mid or shot['motion_id'],'camera_id':shot['camera_id'] if shot else 'front_full','aspect':shot['orientation'] if shot else 'portrait','time_seconds':t,'hit':hit})
def _seen(job,kind,shot=None,mid=None):
 return (mid or shot['motion_id'],shot['shot_id'] if shot else '',kind) in job['seen']

def check_action_sample(job,a,s):
 t=s['t']
 for gp in s['ground_probes']:
   p=gp['position'];z=gp['baseline_ground_z_cm'];h=ray([p[0],p[1],z+80],[p[0],p[1],z-150])
   # Foot Z is deliberately absent: ordinary jumping retains the old floor.
   if not h:issue(job,'ground_missing','动作路线下方未找到地面，检查悬空或地面碰撞设置。',t,mid=a['motion_id']);continue
   delta=h['point'][2]-z
   if abs(delta)>5:issue(job,'ground_height','地面比原动作基准'+('高' if delta>0 else '低')+f'{abs(delta):.1f}厘米，检查陷地或悬空。',t,mid=a['motion_id'],hit=h)
   if h.get('normal',[0,0,1])[2]<.7:issue(job,'ground_slope','动作路线下方表面过陡，需要检查接地。',t,mid=a['motion_id'],hit=h)
 if _seen(job,'body_collision',mid=a['motion_id']):return
 for x,y in a['body_segments']:
   if x not in s['bones'] or y not in s['bones']:continue
   p,q=s['bones'][x],s['bones'][y]
   # Skin-level floor contacts are not collisions; foot-ground tested above.
   if min(p[2],q[2])<job['site_z']+8:continue
   h=sphere(p,q,3.)
   if h:
    issue(job,'body_collision','身体代理范围疑似碰到环境：'+str(h['actor']),t,mid=a['motion_id'],hit=h);break

def check_action(job,a):
 for sample in a['samples']:check_action_sample(job,a,sample)
def visible_targets(row,shot,bones,limit=5):
 """Select center and image extrema from landmarks inside the actual frustum."""
 pitch,yaw,roll=[math.radians(x) for x in row['rotation_pitch_yaw_roll']]
 forward=[math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)]
 right0=[-math.sin(yaw),math.cos(yaw),0.];up0=[-math.sin(pitch)*math.cos(yaw),-math.sin(pitch)*math.sin(yaw),math.cos(pitch)]
 right=[math.cos(roll)*r-math.sin(roll)*v for r,v in zip(right0,up0)]
 up=[math.sin(roll)*r+math.cos(roll)*v for r,v in zip(right0,up0)]
 tan=math.tan(math.radians(row['horizontal_fov_degrees']/2));ar=shot['width']/shot['height'];candidates=[]
 for name,target in bones.items():
  if name=='root':continue
  delta=[b-a for a,b in zip(row['position'],target)];depth=sum(x*y for x,y in zip(delta,forward))
  if depth<=1e-6:continue
  x=sum(v*r for v,r in zip(delta,right))/(depth*tan);y=sum(v*r for v,r in zip(delta,up))*ar/(depth*tan)
  if abs(x)<=1 and abs(y)<=1:candidates.append({'bone':name,'position':target,'x':x,'y':y})
 if not candidates:return []
 selected=[]
 def add(item):
  if item not in selected and len(selected)<limit:selected.append(item)
 priorities=('head','neck_01','upperarm_l','upperarm_r') if shot['camera_id']=='front_head' else ('spine_02','pelvis','head')
 for name in priorities:
  match=next((c for c in candidates if c['bone']==name),None)
  if match is not None:add(match);break
 for axis,reverse in (('x',False),('x',True),('y',False),('y',True)):
  add(sorted(candidates,key=lambda c:(c[axis],c['bone']),reverse=reverse)[0])
 for c in sorted(candidates,key=lambda c:c['x']**2+c['y']**2):add(c)
 return selected

def check_shot_sample(job,s,row,index):
 t=row['t'];p=row['position']
 if not _seen(job,'camera_collision',shot=s):
  previous=s['samples'][index-1]['position'] if index else p
  h=sphere(previous,[p[0]+.01,p[1],p[2]],8.)
  if h:issue(job,'camera_collision','相机附近或移动路径疑似碰到：'+str(h['actor']),t,shot=s,hit=h)
 if _seen(job,'occlusion',shot=s):return
 body=job['action_samples'][s['motion_id']][row['frame_index']]['bones']
 targets=visible_targets(row,s,body)
 if not targets:
  job['unmeasured_visibility_samples']+=1
  issue(job,'visibility_unmeasured','这个时间没有落在画内的骨点可测，遮挡需要视觉检查。',t,shot=s);return
 for candidate in targets:
  h=ray(p,candidate['position'])
  # A foot ray ending on its supporting floor is contact, not occlusion.
  if h and candidate['bone'] in ('foot_l','foot_r','ball_l','ball_r') and h['normal'][2]>.7 and abs(h['point'][2]-job['site_z'])<=5. and abs(candidate['position'][2]-job['site_z'])<=5.:continue
  if h:
   issue(job,'occlusion','人物疑似被环境遮挡：'+str(h['actor']),t,shot=s,hit=h);break

def check_shot(job,s):
 for index,row in enumerate(s['samples']):check_shot_sample(job,s,row,index)

def finish(job,status='complete',error=None):
 d=live()
 if status=='complete' and job['completed']!=job['total']:status='partial'
 job['status']=status;complete=status=='complete' and job['completed']==job['total']
 scope=job.get('scope',{'kind':'legacy','combinations':len(job['shots']),'selection':None})
 full=complete and scope['kind']=='all' and len(job['shots'])==len(d['local']['shots'])
 report={'schema':'scene_site_review_report_v1','status':status,'scope':scope,'stamp':job['stamp'],'site':job['site'],'input_fingerprint':d['local']['input_fingerprint'],'sampling':'0.5秒和终点；骨段/相机8cm球代理/碰撞可见性通道，非网格级保证','issues':job['issues'],'summary':{'combinations':len(job['shots']),'issues':len(job['issues']),'checked_items':job['completed'],'total_items':job['total']},
  'coverage':{'full_matrix_checked':full,'completed_scope':complete,'sample_items_completed':job['completed'],'total_sample_items':job['total'],'unmeasured_visibility_samples':job.get('unmeasured_visibility_samples',0)},
  'limitations':['检测基于稀疏骨点与Visibility碰撞通道；不能证明网格、发型、服装或无碰撞物体无遮挡。',
   '场景指纹覆盖演员及可读取组件属性、碰撞/资产引用和脏包；不保证发现同路径资产在已脏状态下的内部几何或材质改动。',
   '不支持读取的组件属性只记录不可用，不中断检查；相机视锥只选最多五个分散可见骨点。',
   '完整矩阵已检查只表示采样完成，所有疑似问题及视觉效果仍需人工判断。'],'human_acceptance':'pending','error':error}
 path=RUN/'reports'/(job['id']+'.json');write(path,report);d['report']=report;job['report_path']=str(path)
 if job.get('handle'):u.unregister_slate_post_tick_callback(job['handle']);job['handle']=None

def tick(delta):
 d=live();j=d.get('job')
 if not j or j['status']!='running':return
 try:
  reason=job_stale_reason(j)
  if reason:finish(j,'stale',reason);return
  start=time.monotonic()
  while j['queue'] and time.monotonic()-start<.018:
   kind,obj,sample,index=j['queue'].popleft()
   if kind=='action':check_action_sample(j,obj,sample)
   else:check_shot_sample(j,obj,sample,index)
   j['completed']+=1
  if not j['queue']:
   reason=job_stale_reason(j,force=True)
   finish(j,'stale' if reason else 'complete',reason)
 except Exception as e:finish(j,'failed',str(e))
def start_check(p,all_shots=False):
 d=require_site();cancel()
 if not input_status(force=True)['valid']:raise ValueError('输入已经改变，请重新准备检查数据。')
 g=placed(None if all_shots else p)
 if all_shots:ss=g['shots'];aa=g['actions']
 else:
  s,a=select(p,g);ss=[s];aa=[a]
 excluded={tuple(r.get(k) for k in ('action_id','camera_id','aspect')) for r in p.get('excluded_combinations',[])}
 ss=[s for s in ss if (s['motion_id'],s['camera_id'],s['orientation']) not in excluded]
 if not ss:raise ValueError('所选组合已全部排除，请恢复至少一个组合后检查。')
 mids={s['motion_id'] for s in ss};aa=[a for a in aa if a['motion_id'] in mids]
 scope={'kind':'all' if all_shots else 'current','combinations':len(ss),'selection':None if all_shots else {k:v for k,v in zip(('action_id','camera_id','aspect'),(ss[0]['motion_id'],ss[0]['camera_id'],ss[0]['orientation']))}}
 if all_shots and len(ss)!=len(g['shots']):scope['kind']='remaining';scope['excluded_combinations']=[dict(zip(('action_id','camera_id','aspect'),key)) for key in sorted(excluded)]
 queue=deque([('action',a,sample,index) for a in aa for index,sample in enumerate(a['samples'])]
             +[('shot',s,row,index) for s in ss for index,row in enumerate(s['samples'])])
 j={'id':'check_'+uuid.uuid4().hex[:12],'status':'running','scope':scope,'completed':0,'total':len(queue),'queue':queue,'shots':ss,'actions':{a['motion_id']:a for a in aa},
    'action_samples':{a['motion_id']:{r['frame_index']:r for r in a['samples']} for a in aa},
    'site':copy.deepcopy(d['site']),'site_z':d['site']['position']['z'],'stamp':stamp(),'issues':[],'seen':set(),'ignored':owned(),
    'input_signature':input_status()['signature'],'scene_signature':scene_signature(),'last_validity_check':time.monotonic(),'unmeasured_visibility_samples':0}
 d['job']=j;j['handle']=u.register_slate_post_tick_callback(tick)

def job_stale_reason(job,force=False):
 d=synchronize()
 if 'scope' not in job:return '工具已更新，旧检查需要重新启动。'
 if current_map()!=job['site']['map']:return '检查期间关卡已改变，请重新检查。'
 if not d.get('marker') or not u.SystemLibrary.is_valid(d['marker']):return '检查期间点位标记已删除，请重新检查。'
 if any(d['site'].get(k)!=job['site'].get(k) for k in ('site_id','map','position','yaw')):return '检查期间点位位置或朝向已改变，请重新检查。'
 now=time.monotonic()
 if force or now-job['last_validity_check']>=3.:
  job['last_validity_check']=now;inputs=input_status(force=force)
  if not inputs['valid'] or inputs['signature']!=job['input_signature']:return '检查期间输入已改变，请重新准备并检查。'
  if scene_signature()!=job['scene_signature']:return '检查期间场景演员或组件已改变，请重新检查。'
 return None
def cancel():
 j=live().get('job')
 if j and j['status']=='running':finish(j,'cancelled')
def save_site(p):
 d=require_site();site=copy.deepcopy(d['site'])
 if 'allowed_combinations' in p or 'issue_reviews' in p:
  current=stamp()
  if p.get('decisions_stamp')!=current:raise ValueError('人工决定对应的点位或场景已改变，请刷新后重新确认。')
  if not input_status()['valid']:raise ValueError('输入已经改变，不能保存为当前人工决定。')
  site['allowed_combinations']=p.get('allowed_combinations',site.get('allowed_combinations',[]));site['decisions_stamp']=current
  reviews=p.get('issue_reviews',site.get('issue_reviews',{}))
  if not isinstance(reviews,dict) or any(not isinstance(v,dict) or v.get('status') not in ('confirmed_problem','acceptable','unreviewed') or not isinstance(v.get('note',''),str) for v in reviews.values()):raise ValueError('问题审查标记格式无效。')
  site['issue_reviews']=reviews
 elif site.get('decisions_stamp')!=stamp():site['allowed_combinations']=[];site['issue_reviews']={}
 d['site']=site
 write(RUN/'sites'/(site['site_id']+'.json'),{'site':site,'input_fingerprint':d['local']['input_fingerprint'],'scene_signature':scene_signature(),'report':d['report'],'human_acceptance':'pending'})
 return str(RUN/'sites'/(site['site_id']+'.json'))
def load_site(p):
 sid=p['site_id'];path=(RUN/'sites'/(sid+'.json')).resolve()
 if path.parent!=(RUN/'sites').resolve():raise ValueError('无效点位路径')
 record=read(path);site=record['site']
 if site['map']!=current_map():raise ValueError('请先在UE打开点位所属关卡：'+site['map'])
 create(site);live()['site']=site;live()['report']=record.get('report')
def restore():
 if not hasattr(u,LIVE):return
 pause_playback();cancel();d=live();u.EditorLevelLibrary.eject_pilot_level_actor()
 for a in owned():actors().destroy_actor(a)
 u.SystemLibrary.flush_persistent_debug_lines(world())
 try:u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(*d['original_view'])
 except Exception:pass
 if d.get('original_fov') is not None:
  v=u.get_editor_subsystem(u.LevelEditorSubsystem);v.set_level_viewport_fov(d['original_fov'],v.get_active_viewport_config_key())
 if 'background_throttle_original' in d:
  settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
  settings.set_editor_property('bThrottleCPUWhenNotForeground',d.pop('background_throttle_original'))
 d.update(site=None,marker=None,character=None,camera=None,job=None,report=None,ranges=False,preview={})
def dispatch(p):
 if Path(u.Paths.project_dir()).resolve()!=Path('D:/UE/projects/datatry_02'):raise ValueError('UE项目不符')
 p={**p,**p.get('payload',{})};act=p['action'];d=live()
 if d.get('job') and d['job']['status']=='running' and act not in ('status','poll_check','cancel_check','restore'):raise ValueError('检查进行中，请等待或取消。')
 extra={}
 if act not in ('status','catalog','playback_status','save_site','poll_check','play','pause_playback','stop_playback'):pause_playback()
 if act!='restore':enable_live_view()
 if act=='create_site':create(p)
 elif act=='open_scene':open_scene(p)
 elif act=='update_site':update(p)
 elif act=='capture_site':require_site();synchronize()
 elif act=='snap_ground':extra['ground']=snap()
 elif act=='preview':extra['preview']=preview(p)
 elif act=='play':play(p)
 elif act=='pause_playback':pause_playback()
 elif act=='stop_playback':stop_playback()
 elif act=='show_ranges':show_ranges(p.get('enabled',True))
 elif act=='overview':extra['overview']=overview(p)
 elif act in ('check_start','check_all'):start_check(p,act=='check_all')
 elif act=='cancel_check':cancel()
 elif act=='save_site':extra['saved_path']=save_site(p)
 elif act=='load_site':load_site(p)
 elif act=='restore':restore()
 elif act not in ('status','catalog','poll_check','playback_status'):raise ValueError('未知操作')
 result={'success':True,'action':act,'request_id':p.get('request_id'),'state':state(),**extra}
 if act in ('status','catalog','create_site','save_site','load_site','restore','open_scene'):result['catalog']=catalog()
 if act in ('status','load_site','poll_check') and d.get('report') and (not d.get('job') or d['job']['status']!='running'):
  result['report']=d['report']
 return result
if __name__=='__main__':
 p=globals().get('DM_SCENE_SITE_REVIEW_REQUEST',{'action':'status'})
 try:r=dispatch(p)
 except Exception as e:r={'success':False,'action':p.get('action'),'request_id':p.get('request_id'),'error':str(e),'traceback':traceback.format_exc()}
 path=RUN/'replies'/((p.get('request_id') or uuid.uuid4().hex)+'.json');write(path,r)
 print('DM_SCENE_SITE_REVIEW='+json.dumps({'success':True,'result_file':str(path)}))






