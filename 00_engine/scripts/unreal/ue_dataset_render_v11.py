"""Serial v11 renderer. Uses current 40-person slot assembly on owned map copies."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import time
import uuid

S = Path(__file__).resolve().parent
WORKSPACE = S.parents[2]
ASSETS = '/Game/DataMake/Render/Main'
LIVE = '_dm_dataset_render_v11'
VERSION = 3
RENDER_CVARS = {'r.AntiAliasingMethod':4,'r.ScreenPercentage':100,'r.DynamicRes.OperationMode':0,
               'r.DynamicGlobalIlluminationMethod':1,'r.ReflectionMethod':1,'r.Shadow.Virtual.Enable':1,
               **{'sg.'+name+'Quality':3 for name in ('ViewDistance','AntiAliasing','Shadow','GlobalIllumination','Reflection','PostProcess','Texture','Effects','Foliage')}}

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    temp.replace(path)

def module(name):
    spec = importlib.util.spec_from_file_location('_dataset_' + name, S / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value

def presentation_policy():
    smile = module('dataset_smile_runtime_v1')
    return {'version': VERSION, 'smile_runtime_version': smile.VERSION,
            'smile_catalog_sha256': smile.manifest_digest()}

def signature(job):
    return hashlib.sha256(json.dumps({'policy': presentation_policy(), 'job': job}, sort_keys=True).encode()).hexdigest()

def apply_appearance(u, current, actor, selected, t, motion, *, body_action_id=None):
    return module('dataset_smile_runtime_v1').apply(
        u, current, actor, selected, t, motion, body_action_id=body_action_id)

def selection(job, current):
    state = job['state']; contract = current['graph'].load('scene_site_appearance_v1')
    value = contract.default_selection(current['data'], state['sex'])
    value.update(character_id=state['identity'], hair_color=state['hair_color'], face_id='smile')
    value['choice'] = copy.deepcopy(state['wardrobe']); value['choice']['hair_id'] = state['hair']
    return contract.validate_selection(value, current['data'], body_action_id=state['action'])

def spawn_slot_actor(u, sex):
    """Instantiate the production slot blueprint directly, without a trial map."""
    if sex not in ('female', 'male'):
        raise ValueError('Unknown character sex: '+str(sex))
    path='/Game/DataMake/Validation/CFDNativeBatch4020261006/ModularReview/FixedSlotRuntime/BP_DM_Complete_'+sex.title()+'_FixedSlots_v001'
    blueprint=u.load_asset(path)
    if blueprint is None:
        raise RuntimeError('Missing production slot blueprint: '+path)
    actor=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(blueprint.generated_class(),u.Vector(),u.Rotator())
    if actor is None:raise RuntimeError('Cannot spawn production slot actor')
    return actor

def persistent_lashes(u, current, actor):
    """Review lash actors are transient; save equivalent real followers for PIE."""
    assembly = current['assembly']; state = assembly._pair_revision_runtime
    binding = state['bindings'][actor.get_path_name()]; body = binding['body']
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    replacements = []
    for old in binding['actors']:
        old_comp = old.get_editor_property('skeletal_mesh_component')
        follower = actors.spawn_actor_from_class(u.SkeletalMeshActor, actor.get_actor_location(), actor.get_actor_rotation())
        follower.set_actor_label('DM_Dataset_' + old.get_actor_label())
        follower.set_owner(actor)
        follower.attach_to_component(body, '', u.AttachmentRule.SNAP_TO_TARGET, u.AttachmentRule.SNAP_TO_TARGET, u.AttachmentRule.SNAP_TO_TARGET, False)
        comp = follower.get_editor_property('skeletal_mesh_component')
        comp.set_skeletal_mesh_asset(old_comp.get_skeletal_mesh_asset())
        comp.set_leader_pose_component(body, True, False)
        comp.set_editor_property('use_attach_parent_bound', True)
        comp.set_allow_anim_curve_evaluation(True)
        comp.add_tick_prerequisite_component(body)
        replacements.append(follower)
        actors.destroy_actor(old)
    binding['actors'] = replacements
    return current['revision'].readback(assembly, actor)

def release_bindings(u,current):
    """Map replacement can leave Python wrappers whose native objects are gone."""
    state=current['assembly']._pair_revision_runtime
    for key,binding in list(state['bindings'].items()):
        try:
            valid=u.SystemLibrary.is_valid(binding['owner'])
        except (TypeError,RuntimeError): valid=False
        if not valid:
            state['bindings'].pop(key,None)
            continue
        live=[]
        for actor in binding['actors']:
            try:
                if u.SystemLibrary.is_valid(actor):live.append(actor)
            except (TypeError,RuntimeError): pass
        binding['actors']=live
    return current['revision'].clear(current['assembly'])

def settings(u):
    keys = ['r.AntiAliasingMethod', 'r.ScreenPercentage', 'r.DynamicRes.OperationMode',
            'r.Streaming.PoolSize', 'r.DynamicGlobalIlluminationMethod', 'r.ReflectionMethod',
            'r.Shadow.Virtual.Enable', 'sg.ViewDistanceQuality', 'sg.AntiAliasingQuality',
            'sg.ShadowQuality', 'sg.GlobalIlluminationQuality', 'sg.ReflectionQuality',
            'sg.PostProcessQuality', 'sg.TextureQuality', 'sg.EffectsQuality', 'sg.FoliageQuality']
    return {key: u.SystemLibrary.get_console_variable_float_value(key) for key in keys}

def prepare(u, run, job):
    path = run / 'jobs' / job['job_id'] / 'prepared.json'
    sig = signature(job)
    if path.exists():
        previous = read(path)
        if previous.get('signature') == sig and all(u.EditorAssetLibrary.does_asset_exist(previous['job'][key]) for key in ('map','sequence')):
            return dict(previous, reused=True)
    if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
        raise RuntimeError('MRQ active; cannot change world')
    started = time.monotonic(); times = {}; tick = started
    import pair_scene_review_20261019_v1 as pair
    current = pair.worker(u)
    times['assembly_initialization'] = time.monotonic()-tick; tick=time.monotonic()
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem); actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    release_bindings(u,current)
    site=job['site']; dest=ASSETS+'/Maps/L_'+job['job_id']+'_'+uuid.uuid4().hex[:8]
    sequence_path=ASSETS+'/Sequences/LS_'+job['job_id']+'_'+uuid.uuid4().hex[:8]
    # Reuse a loaded source scene when preparing adjacent jobs; map saves are owned copies.
    cached=getattr(u, LIVE+'_scene', {})
    reuse=cached.get('source')==site['map'] and cached.get('world')==u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not reuse:
        if not levels.load_level(site['map']): raise RuntimeError('Cannot load source scene '+site['map'])
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    times['scene_load']=time.monotonic()-tick; tick=time.monotonic()
    # All mutations occur only after saving a dedicated copy, never over the source.
    if not u.EditorLoadingAndSavingUtils.save_map(world,dest): raise RuntimeError('Cannot create owned map')
    # SaveMap creates a duplicate asset but does not switch the editor world.
    if not levels.load_level(dest): raise RuntimeError('Cannot load owned map')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    for existing in list(actors.get_all_level_actors()):
        if isinstance(existing,u.LevelSequenceActor) or existing.get_actor_label().startswith(('DM_Dataset_','DM_SiteReview_')):
            actors.destroy_actor(existing)
    times['scene_copy_cleanup']=time.monotonic()-tick; tick=time.monotonic()
    trial=module('ue_production_trial_render_v1')
    actor=spawn_slot_actor(u,job['state']['sex'])
    actor.set_actor_label('DM_SiteReview_Dataset_Character')
    actor.set_actor_location(u.Vector(*[site['position'][k] for k in ('x','y','z')]),False,False)
    actor.set_actor_rotation(u.Rotator(pitch=0,yaw=site['yaw'],roll=0),False)
    selected=selection(job,current)
    motion=u.load_asset(job['motion']['animation'])
    if motion is None: raise RuntimeError('Missing production10 motion')
    applied=apply_appearance(u,current,actor,selected,0.,motion,body_action_id=job['state']['action'])
    lashes=persistent_lashes(u,current,actor)
    persistent_materials=module('dataset_persistent_materials_v1').freeze_actor(u,actor,ASSETS+'/Materials/PersistentV1')
    animation=u.load_asset(applied['animation_path'])
    times['character_wardrobe_hair_motion']=time.monotonic()-tick; tick=time.monotonic()
    import scene_site_review_geometry_v1 as geo
    plan_path=Path(job['camera_binding']['plan_path'])
    if not plan_path.is_absolute(): plan_path=WORKSPACE/plan_path
    plan_stamp=(str(plan_path),plan_path.stat().st_mtime_ns)
    plan_cache=getattr(u,LIVE+'_camera_plan',None)
    if not plan_cache or plan_cache['stamp']!=plan_stamp:
        plan_cache={'stamp':plan_stamp,'shots':{s['shot_id']:s for s in read(plan_path)['shots']}}
        setattr(u,LIVE+'_camera_plan',plan_cache)
    shot=copy.deepcopy(plan_cache['shots'][job['camera_binding']['shot_id']])
    offset=[site['position'][k] for k in ('x','y','z')]
    for row in shot['frames']+[shot['endpoint_validation_frame']]:
        row['position']=geo.transform_point(row['position'],offset,site['yaw'])
        row['look_at']=geo.transform_point(row['look_at'],offset,site['yaw'])
        row['rotation_pitch_yaw_roll'][1]+=site['yaw']
    shot.update(shot_id=job['job_id'],width=job['width'],height=job['height'],sex=job['state']['sex'],source_animation=job['motion']['animation'],window_start_seconds=0.,source_start_seconds=0.,source_body_play_rate=1.)
    first=shot['frames'][0]; r=first['rotation_pitch_yaw_roll']
    camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*first['position']),u.Rotator(pitch=r[0],yaw=r[1],roll=r[2]))
    camera.set_actor_label('DM_Dataset_Camera')
    comp=camera.get_component_by_class(u.CameraComponent)
    comp.set_editor_property('aspect_ratio',job['width']/job['height']); comp.set_editor_property('constrain_aspect_ratio',True)
    comp.set_field_of_view(first['horizontal_fov_degrees'])
    from level_exposure_policy_v1 import apply as exposure
    exposure_readback=exposure(comp)
    times['camera']=time.monotonic()-tick; tick=time.monotonic()
    ground=trial.sample_ground_height(u,actor,camera,animation,shot,site=site)
    times['ground_follow']=time.monotonic()-tick; tick=time.monotonic()
    builder=module('ue_motion_scene_sequence_v1'); builder.ALLOWED_PREFIX=ASSETS+'/'
    builder.NATIVE_TEMPLATE=trial.resolve(builder.NATIVE_TEMPLATE)
    built=builder.build_sequence(u,shot,actor,camera,animation,sequence_path,ground_height_keys=ground['frames'])
    if not u.EditorAssetLibrary.save_loaded_asset(built['sequence'],False): raise RuntimeError('Cannot save sequence')
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not u.EditorLoadingAndSavingUtils.save_map(world,dest): raise RuntimeError('Cannot save owned map')
    times['sequence_and_save']=time.monotonic()-tick
    setattr(u,LIVE+'_scene',{'source':site['map'],'world':world})
    result={'success':True,'signature':sig,'job_id':job['job_id'],'job':{'shot_id':job['job_id'],'map':dest+'.'+dest.rsplit('/',1)[1],'sequence':sequence_path+'.'+sequence_path.rsplit('/',1)[1]},
            'stage_seconds':times,'preparation_seconds':time.monotonic()-started,'scene_reused':reuse,'appearance':applied,'persistent_lashes':lashes,'persistent_materials':persistent_materials,'ground_height_follow':ground,'sequence_report':built['report'],
            'resolved_project_settings':settings(u),'exposure':exposure_readback,'source_scene_saved':False,'state':job['state'],'camera_first_frame':first,'width':job['width'],'height':job['height']}
    write(path,result)
    return result

def renderer(u,run,job=None,pool_mb=10240):
    m=module('ue_motion_scene_render_v1'); m.RUN=run; m.PROJECT=Path(u.Paths.project_dir()).resolve();m.ASSET_ROOT=ASSETS;m.LIVE_ATTRIBUTE=LIVE
    # Saved map/sequence metadata is enough for this pilot; avoid whole-map hashing per clip.
    def pin(path):
        p=Path(path);s=p.stat();return {'path':str(p),'size':s.st_size,'mtime_ns':s.st_mtime_ns}
    m.file_pin=pin
    original=m.persist
    def persist(state):
        if state['receipt']['status']=='submitted' and not state.get('configured'):
            from ue_primary_scene_samples_v1 import sample_scene_resources
            from mrq_streaming_warmup_v1 import apply as warmup
            state['receipt']['render_contract']['scene_resources']=sample_scene_resources(u,state['queue'])
            state['receipt']['render_contract']['streaming_warmup']=warmup(u,state['queue'],pool_size_mb=pool_mb)
            state['receipt']['render_contract'].update(engine_warmup_count=120,render_warmup_count=32,profile_scope='v11_local_pilot')
            state['receipt']['render_contract']['baseline_cvars']=dict(RENDER_CVARS)
            destination=run/'jobs'/job['job_id']/'frames';destination.mkdir(parents=True,exist_ok=True)
            for qjob in state['queue'].get_jobs():
                game=qjob.get_configuration().find_or_add_setting_by_class(u.MoviePipelineGameOverrideSetting)
                game.set_editor_property('texture_streaming',u.MoviePipelineTextureStreamingMethod.FULLY_LOAD)
                state['receipt']['render_contract']['texture_readiness']={
                    'policy':'fully_load_used_textures_v2',
                    'texture_streaming':str(game.get_editor_property('texture_streaming')),
                    'scope':'Load used textures at full available resolution before output; keep original camera and LOD settings',
                    'evidence':'dataset_texture_quality_20261023_v1 cold-cache A/B: face diffuse 64x64 -> 2048x2048'}
                state['receipt']['render_contract']['scene_resources']['effective_texture_override']='FULLY_LOAD (supersedes inherited NONE)'
                state['receipt']['render_contract']['streaming_warmup']['streaming_policy']='fully_load_used_textures_with_rendered_warmup'
                variables=qjob.get_configuration().find_or_add_setting_by_class(u.MoviePipelineConsoleVariableSetting)
                for name,value in RENDER_CVARS.items():
                    if not variables.add_or_update_console_variable(name,float(value)):raise RuntimeError('Cannot bind render baseline '+name)
                output=qjob.get_configuration().find_or_add_setting_by_class(u.MoviePipelineOutputSetting)
                output.output_directory=u.DirectoryPath(str(destination))
                output.override_existing_output=True
            state['receipt']['frames_directory']=str(destination)
            state['receipt']['job_signature']=signature(job)
            state['configured']=True
        original(state)
    m.persist=persist
    return m

def dispatch(request):
    import unreal as u
    run=Path(request['run_root']).resolve(); action=request['action']
    if action=='status':
        result=renderer(u,run).status(u)
        receipt=result.get('receipt') or {}
        if result.get('subsystem_rendering') and receipt.get('jobs'):
            jid=receipt['jobs'][0]['shot_id']; snapshot=run/'jobs'/jid/'runtime_snapshot.json'
            if not snapshot.exists():
                world=u.EditorLevelLibrary.get_game_world()
                if world:
                    found=[]
                    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
                        if 'DM_SiteReview_Dataset_Character'==actor.get_actor_label() or actor.get_actor_label().startswith('DM_Dataset_DM_SiteReview_'):
                            components=[]
                            for comp in actor.get_components_by_class(u.SkeletalMeshComponent):
                                mesh=comp.get_skeletal_mesh_asset();leader=comp.get_editor_property('leader_pose_component')
                                if mesh: components.append({'component':comp.get_name(),'mesh':mesh.get_path_name(),'leader':leader.get_path_name() if leader else None,'visible':comp.is_visible()})
                            found.append({'actor':actor.get_path_name(),'components':components})
                    if found: write(snapshot,{'world':world.get_path_name(),'actors':found,'settings':settings(u),'stage':'PIE_render_in_progress','attempt_id':receipt['attempt_id']})
        return result
    job=next(j for j in read(request['jobs_path'])['jobs'] if j['job_id']==request['job_id'])
    if action=='prepare': return prepare(u,run,job)
    if action=='render':
        prepared=read(run/'jobs'/job['job_id']/'prepared.json')
        if prepared['signature']!=signature(job): raise ValueError('Prepared job changed')
        return renderer(u,run,job,request.get('pool_mb',10240)).start_render(u,[prepared['job']],job['job_id']+'_'+uuid.uuid4().hex[:8],width=job['width'],height=job['height'])
    raise ValueError('Unknown action '+str(action))
