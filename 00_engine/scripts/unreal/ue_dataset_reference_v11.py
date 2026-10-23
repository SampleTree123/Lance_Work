"""Approved v11 reference presentation: static PNGs and neutral motion clips.

Only explicit dispatch mutates owned capture assets. Adopted graph stays read-only.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import re
import time
import uuid

S=Path(__file__).resolve().parent
WORKSPACE=S.parents[2]
ROOT='/Game/DataMake/Render/References'
LIVE='_dm_dataset_reference_v11'
VERSION=3

def module(name):
    spec=importlib.util.spec_from_file_location('_reference_production_'+name,S/(name+'.py'))
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8');tmp.replace(path)

def signature(job):
    value={'reference_version':VERSION,'main_policy':module('ue_dataset_render_v11').presentation_policy(),'job':job}
    if job.get('reference_kind')=='garment' and job.get('slot')=='shoes':value['shoe_framing_version']=1
    if job.get('reference_kind') in ('identity','hair') and job.get('garments_present') is False:value['portrait_presentation_version']=1
    if job.get('framing_policy')=='tight_face_no_neck_or_shoulders':value['identity_framing_version']=2
    if job.get('framing_policy')=='shared_head_shoulders':value['shared_hair_framing_version']=1
    if job.get('framing_policy')=='adaptive_complete_hair':value['adaptive_hair_framing_version']=1
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def adaptive_hair_framing(head_position,hair_bounds,view,width,height):
    if not hair_bounds or view not in ('front','back'):raise ValueError('Adaptive hair framing requires actual hair bounds and front/back view')
    head={'center':[head_position[0],head_position[1],head_position[2]+8.], 'extent':[12.,10.,14.]}
    bounds=[head]+hair_bounds
    low=[min(b['center'][k]-b['extent'][k] for b in bounds) for k in range(3)]
    high=[max(b['center'][k]+b['extent'][k] for b in bounds) for k in range(3)]
    center=[(a+b)/2 for a,b in zip(low,high)]; extent=[(b-a)/2 for a,b in zip(low,high)]
    tan_h=math.tan(math.radians(14.)); tan_v=tan_h/(width/height)
    distance=max(40.,extent[1]+1.12*max(extent[0]/tan_h,extent[2]/tan_v))
    sign=1. if view=='front' else -1.
    return {'position':[center[0],center[1]+sign*distance,center[2]],
            'rotation_pitch_yaw_roll':[0.,-90. if view=='front' else 90.,0.],
            'horizontal_fov_degrees':28.,'bounds_center':center,'bounds_extent':extent,
            'view':view,'focus_kind':'hair','head_socket':head_position,
            'head_proxy_extent_cm':head['extent'],'camera_distance_cm':distance,'fit_margin':1.12,
            'framing_scope':'complete actual hairstyle plus compact head; adaptive distance; body/clothes excluded from fit',
            'presentation_status':'adaptive_framing_sample_review'}

def shared_hair_framing(head_position,view,width,height):
    if view not in ('front','back') or width!=height:raise ValueError('Shared hair framing requires square front/back view')
    center=[head_position[0],head_position[1],head_position[2]+3.0]
    sign=1. if view=='front' else -1.
    return {'position':[center[0],center[1]+sign*110.,center[2]],
            'rotation_pitch_yaw_roll':[0.,-90. if view=='front' else 90.,0.],
            'horizontal_fov_degrees':28.,'bounds_center':center,'bounds_extent':[25.,15.,25.],
            'view':view,'focus_kind':'hair','head_socket':head_position,
            'framing_scope':'shared male/female head-relative camera; most hair; longest tips may crop',
            'camera_distance_cm':110.,'head_relative_center_z_cm':3.,
            'presentation_status':'shared_parameters_sample_review'}

def identity_face_framing(head_position,width,height):
    # Fixed CC head anchor: keep facial outline, allow peripheral hair to crop.
    center=[head_position[0],head_position[1],head_position[2]+9.7]
    return {'position':[center[0],center[1]+64.0,center[2]],
            'rotation_pitch_yaw_roll':[0.,-90.,0.],'horizontal_fov_degrees':28.,
            'bounds_center':center,'bounds_extent':[12.,10.,12.], 'view':'front',
            'focus_kind':'identity','head_socket':head_position,
            'framing_scope':'tight face; peripheral hair may crop; no shoulders; chin retained',
            'presentation_status':'approved_design_new_framing_review'}

def source(run,job):
    path=Path(job.get('source_jobs_path',job.get('main_jobs_path','carrier_jobs.json')))
    if not path.is_absolute():path=run/path
    value=next(x for x in read(path)['jobs'] if x['job_id']==job['source_job_id'])
    expected=job.get('source_job_sha256')
    actual=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    if expected and expected!=actual:raise ValueError('Reference carrier definition changed; rebuild reference plan')
    return value,path

def shared_main():
    main=module('ue_dataset_render_v11')
    return main

def renderer(u,run,job=None,pool_mb=10240):
    main=shared_main();main.signature=signature
    value=main.renderer(u,run,job,pool_mb);value.LIVE_ATTRIBUTE=LIVE;value.ASSET_ROOT=ROOT
    return value

def static_prepare(u,run,job):
    main=shared_main();pilot=module('ue_dataset_reference_pilot_v11');pilot.ROOT=ROOT
    src,src_path=source(run,job)
    # Static canonical references do not need to load/render their source scene.
    def resolved_source(u,run,j,_main):
        prepared=main.prepare(u,run,src) if j['reference_kind']=='scene' else {}
        pin={'path':str(src_path),'sha256':pilot.digest(src_path)}
        return src,prepared,pin,[]
    pilot.source_job=resolved_source
    def garment_target(source,asset_id):
        rows=[a for a in source['appearance']['wardrobe_assets'] if a['asset_id']==asset_id]
        if len(rows)!=1 or not rows[0].get('mesh_paths'):raise ValueError('Missing single target item '+asset_id)
        return copy.deepcopy(rows[0])
    pilot.garment_target=garment_target
    if job.get('reference_kind')=='identity' and job.get('framing_policy')=='tight_face_no_neck_or_shoulders':
        pilot.head_framing=lambda head,bounds,kind,view,width,height: identity_face_framing(head,width,height)
    if job.get('reference_kind')=='hair' and job.get('framing_policy')=='shared_head_shoulders':
        pilot.head_framing=lambda head,bounds,kind,view,width,height: shared_hair_framing(head,view,width,height)
    if job.get('reference_kind')=='hair' and job.get('framing_policy')=='adaptive_complete_hair':
        pilot.head_framing=lambda head,bounds,kind,view,width,height: adaptive_hair_framing(head,bounds,view,width,height)
    if job.get('slot')=='shoes':
        original_framing=pilot.garment_framing
        def footwear_framing(bounds,width,height,fov=32.0,view='front'):
            pose=original_framing(bounds,width,height,fov,view)
            center,extent=pose['bounds_center'],pose['bounds_extent']
            elevation=math.radians(25.0)
            projected_height=extent[2]*math.cos(elevation)+extent[1]*math.sin(elevation)
            projected_depth=extent[1]*math.cos(elevation)+extent[2]*math.sin(elevation)
            tan_h=math.tan(math.radians(fov/2));tan_v=tan_h/(width/height)
            distance=max(25.,projected_depth+1.18*max(extent[0]/tan_h,projected_height/tan_v))
            sign=1 if view=='front' else -1
            pose.update(position=[center[0],center[1]+sign*distance*math.cos(elevation),center[2]+distance*math.sin(elevation)],
                        rotation_pitch_yaw_roll=[-25.,-90. if view=='front' else 90.,0.],
                        shoe_view_elevation_degrees=25.,framing_scope='complete pair; front/back azimuth with visible shoe uppers')
            return pose
        pilot.garment_framing=footwear_framing
    render_job=dict(job,view=job.get('render_view',job.get('view')))
    result=pilot.prepare(u,run,render_job)
    result.update(signature=signature(job),schema='dataset_reference_prepared_v11_v1',presentation_status='design_confirmed_sample_review',source_jobs_path=str(src_path))
    result['details']['presentation_status']='design_confirmed'
    write(run/'jobs'/job['job_id']/'prepared.json',result)
    return result

def ground_plane(u,actors,unique):
    folder,name=(ROOT+'/Materials/M_Ground_'+unique).rsplit('/',1)
    mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    color=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant',u.LinearColor(0.18,0.18,0.18,1))
    u.MaterialEditingLibrary.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    # Low ambient floor contribution avoids a black distant strip without
    # removing the lit surface's contact shadows near the subject.
    ambient=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
    ambient.set_editor_property('constant',u.LinearColor(0.08,0.08,0.08,1))
    u.MaterialEditingLibrary.connect_material_property(ambient,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    rough=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant)
    rough.set_editor_property('r',1.0)
    u.MaterialEditingLibrary.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    u.MaterialEditingLibrary.recompile_material(mat)
    u.EditorAssetLibrary.save_loaded_asset(mat,False)
    plane=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-1),u.Rotator())
    plane.set_actor_label('DM_Reference_Ground')
    comp=plane.get_component_by_class(u.StaticMeshComponent)
    comp.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));comp.set_material(0,mat)
    comp.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
    plane.set_actor_scale3d(u.Vector(60,60,0.02))
    return {'surface_z_cm':0,'extent_cm':3000,'material':'neutral_gray_rough','collision':True}

def motion_prepare(u,run,job):
    main=shared_main();pilot=module('ue_dataset_reference_pilot_v11');pilot.ROOT=ROOT
    src,src_path=source(run,job)
    if (job['frames'],job['fps'])!=(300,30):raise ValueError('Motion reference must be 10 seconds at 30fps')
    import pair_scene_review_20261019_v1 as pair
    current=pair.worker(u);main.release_bindings(u,current)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    unique=uuid.uuid4().hex[:10];dest=ROOT+'/Maps/L_'+job['job_id']+'_'+unique;seqpath=ROOT+'/Sequences/LS_'+job['job_id']+'_'+unique
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not levels.new_level(dest):raise RuntimeError('Cannot create neutral motion stage')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    trial=main.module('ue_production_trial_render_v1')
    actor=main.spawn_slot_actor(u,src['state']['sex'])
    actor.set_actor_label('DM_SiteReview_Reference_Character')
    actor.set_actor_location(u.Vector(),False,False);actor.set_actor_rotation(u.Rotator(),False)
    selected=main.selection(src,current);animation=u.load_asset(src['motion']['animation'])
    if animation is None:raise ValueError('Missing production10 animation')
    appearance=main.apply_appearance(u,current,actor,selected,0.,animation,body_action_id=src['state']['action'])
    animation=u.load_asset(appearance['animation_path'])
    lashes=main.persistent_lashes(u,current,actor)
    materials=main.module('dataset_persistent_materials_v1').freeze_actor(u,actor,main.ASSETS+'/Materials/PersistentV1')
    environment=pilot.neutral_environment(u,actors,[0.,0.,90.],unique)
    environment['status']='design_confirmed';environment['ground']=ground_plane(u,actors,unique)
    path=Path(src['camera_binding']['plan_path']);path=path if path.is_absolute() else WORKSPACE/path
    shot=copy.deepcopy(next(s for s in read(path)['shots'] if s['shot_id']==src['camera_binding']['shot_id']))
    shot.update(shot_id=job['job_id'],width=job['width'],height=job['height'],sex=src['state']['sex'],source_animation=src['motion']['animation'],window_start_seconds=0.,source_start_seconds=0.,source_body_play_rate=1.)
    first=shot['frames'][0];r=first['rotation_pitch_yaw_roll']
    camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*first['position']),u.Rotator(pitch=r[0],yaw=r[1],roll=r[2]))
    camera.set_actor_label('DM_Reference_Camera');pilot.apply_camera(u,camera,first,job['width'],job['height'])
    from level_exposure_policy_v1 import apply as exposure
    exposure(camera.get_component_by_class(u.CameraComponent))
    builder=main.module('ue_motion_scene_sequence_v1');builder.ALLOWED_PREFIX=main.ASSETS+'/'
    builder.NATIVE_TEMPLATE=trial.resolve(builder.NATIVE_TEMPLATE)
    built=builder.build_sequence(u,shot,actor,camera,animation,seqpath)
    if not u.EditorAssetLibrary.save_loaded_asset(built['sequence'],False):raise RuntimeError('Cannot save motion sequence')
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not u.EditorLoadingAndSavingUtils.save_map(world,dest):raise RuntimeError('Cannot save motion map')
    result={'success':True,'schema':'dataset_reference_prepared_v11_v1','signature':signature(job),'job_id':job['job_id'],'reference_kind':'motion',
            'job':{'shot_id':job['job_id'],'map':pilot.object_path(dest),'sequence':built['sequence'].get_path_name()},
            'source_job_id':src['job_id'],'source_jobs_path':str(src_path),'selection':selected,'state':src['state'],
            'appearance':appearance,'persistent_lashes':lashes,'persistent_materials':materials,
            'camera_first_frame':first,'sequence_report':built['report'],'environment':environment,
            'motion_clock':{'mode':'production10','start_seconds':0,'play_rate':1,'fps':30,'frames':300},
            'camera_space':'original canonical trajectory at origin; no source scene transform',
            'ground_policy':'fixed neutral ground at zero; retain authored vertical body motion',
            'width':job['width'],'height':job['height'],'frames':300,'fps':30,'presentation_status':'design_confirmed_sample_review'}
    write(run/'jobs'/job['job_id']/'prepared.json',result);return result

def prepare(u,run,job):
    if not re.fullmatch(r'ref_[A-Za-z0-9_]{1,100}',job['job_id']):raise ValueError('Unsafe reference ID')
    if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():raise RuntimeError('MRQ active')
    source(run,job)
    main=shared_main()
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages() if not p.get_path_name().startswith((main.ASSETS+'/',ROOT+'/'))]
    if dirty:raise RuntimeError('Unsaved user map: '+str(dirty))
    path=run/'jobs'/job['job_id']/'prepared.json'
    if path.exists():
        previous=read(path)
        if previous.get('signature')==signature(job) and all(u.EditorAssetLibrary.does_asset_exist(previous['job'][k]) for k in ('map','sequence')):return dict(previous,reused=True)
    start=time.monotonic()
    result=motion_prepare(u,run,job) if job['reference_kind']=='motion' else static_prepare(u,run,job)
    result['preparation_seconds']=time.monotonic()-start
    write(path,result);return result

def dispatch(request):
    import unreal as u
    run=Path(request['run_root']).resolve()
    if request['action']=='status':return renderer(u,run).status(u)
    path=Path(request.get('jobs_path',run/'reference_jobs.json'))
    if not path.is_absolute():path=run/path
    job=next(x for x in read(path)['jobs'] if x['job_id']==request['job_id'])
    if request['action']=='prepare':return prepare(u,run,job)
    if request['action']=='render':
        source(run,job)
        prepared=read(run/'jobs'/job['job_id']/'prepared.json')
        if prepared['signature']!=signature(job):raise ValueError('Reference job changed; prepare again')
        return renderer(u,run,job,request.get('pool_mb',10240)).start_render(u,[prepared['job']],job['job_id']+'_'+uuid.uuid4().hex[:8],width=job['width'],height=job['height'])
    raise ValueError('Unknown reference action')
