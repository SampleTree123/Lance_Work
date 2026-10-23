"""Four bounded formal-workflow trials. Root-only UE operations, serial MRQ."""
from pathlib import Path
import copy, importlib.util, json, time

S=Path(__file__).resolve().parent
RUN=S.parents[1]/'outputs/production_workflow_20261017_v1'
ASSETS='/Game/DataMake/Capture/Trials20261017'
LIVE='_dm_production_trials_20261017'
GROUND_HEIGHT_VERSION='ground_height_follow_v1'
from level_exposure_policy_v1 import POLICY as EXPOSURE_POLICY

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def module(name):
    spec=importlib.util.spec_from_file_location('_prod_'+name,S/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def resolve(path):
    import scene_site_appearance_v1 as appearance
    formal=appearance.formal_runtime()
    if formal:
        return formal[1].formal_path_overlay.get(path,path)
    overlay=RUN/'asset_relocation_overlay_v1.json'
    if not overlay.exists():return path
    data=read(overlay)
    return {**data.get('package_paths',{}),**data.get('object_paths',{})}.get(path,path)

def motion_record(motion_id,sex):
    """Use current formal hashes after relocation, original bake proof before it."""
    import scene_site_appearance_v1 as appearance
    import production_motion_contract_v1 as motion
    runtime=module('ue_production_site_runtime_v1')
    if appearance.formal_runtime():
        formal=runtime.load_formal_motion_runtime()
        if formal is None:raise ValueError('Relocated trial requires the published formal motion runtime catalog')
        variant=formal['variants'][(motion_id,sex)]
        return variant['production10'],{'formal_motion_catalog':formal['source'],'original_bake_receipt':variant['original_bake_receipt']}
    entry=next(row for row in motion.load_contract()['motions'] if row['motion_id']==motion_id)
    variant=motion.receipt_variant(entry,sex)
    if variant is None:raise ValueError('Trial motion production bake is not ready')
    return variant['production10'],{'original_bake_receipt':variant['receipt']}

def make_plan():
    import scene_site_review_geometry_v1 as geo
    import scene_site_appearance_v1 as appearance
    folder=S.parents[1]/'outputs/scene_site_review_20261014_v1/sites'
    choices=[read(p)['site'] for p in folder.glob('*.json') if read(p)['site'].get('name','').replace(' ','')=='游乐园/1']
    if len(choices)!=1:raise ValueError('Require exactly the user saved 游乐园 / 1 point')
    site=choices[0];selection=appearance.default_selection();selection['face_id']='smile'
    library=read(RUN/'camera_library/production10/camera_plan.json')
    wanted=[('MOTION_CAND_036','orbit_360','portrait'),('MOTION_CAND_036','front_full','portrait'),
            ('MOTION_CAND_019','front_head','landscape'),('MOTION_CAND_019','rear_three_quarter_upper','landscape')]
    offset=[site['position'][k] for k in ('x','y','z')];yaw=site['yaw'];shots=[]
    for i,key in enumerate(wanted):
        shot=copy.deepcopy(next(s for s in library['shots'] if (s['motion_id'],s['camera_id'],s['orientation'])==key))
        shot['shot_id']='formal_trial_'+str(i+1)+'_'+key[1];shot['width']*=2;shot['height']*=2
        for row in shot['frames']+[shot['endpoint_validation_frame']]:
            row['position']=geo.transform_point(row['position'],offset,yaw)
            row['look_at']=geo.transform_point(row['look_at'],offset,yaw)
            row['rotation_pitch_yaw_roll'][1]+=yaw
        shot['trajectory_sha256']=geo.canonical_sha(shot['frames']+[shot['endpoint_validation_frame']])
        shots.append(shot)
    result={'schema':'production_four_trials_v1','site':site,'appearance_selection':selection,'shots':shots,
            'source_plan':geo.pin(RUN/'camera_library/production10/camera_plan.json'),'duration_seconds':10.,
            'exposure_policy':EXPOSURE_POLICY,'human_acceptance':'pending'}
    write(RUN/'four_trials_plan.json',result);return {'shots':len(shots),'site':site['name']}

def prepare(u,index):
    import ue_scene_site_appearance_v1 as appearance
    try:
        return _prepare(u,index)
    finally:
        # Partial sequence/composite failures must not pin a world on retry.
        appearance.invalidate_cache(u)

def require_ground_height_follow(record,shot,site=None):
    """An old prepared sequence cannot silently bypass the new height policy."""
    trajectory=record.get('ground_height_follow',{})
    sequence=record.get('sequence_ground_height_follow',{})
    count=int(shot['frame_count'])
    if (trajectory.get('version')!=GROUND_HEIGHT_VERSION or sequence.get('version')!=GROUND_HEIGHT_VERSION
            or trajectory.get('camera_policy')!='unchanged' or sequence.get('camera_policy')!='unchanged'
            or len(trajectory.get('frames',[]))!=count+1 or sequence.get('actor_z_key_count')!=count+1):
        raise ValueError('Prepared trial lacks current ground height follow; preserve it and choose a new trial ID')
    builder=module('ue_motion_scene_sequence_v1')
    builder.ground_height_key_rows(trajectory['frames'],count,sequence['baseline_actor_z_cm'])
    module('ue_ground_height_follow_v1').require_trajectory_support(trajectory,site or record.get('site'))
    return trajectory

def sample_ground_height(u,actor,camera,animation,shot,site=None):
    """Use the exact composite animation passed to the skeletal sequence track."""
    ground=module('ue_ground_height_follow_v1')
    kwargs={} if site is None else {'site':site}
    return ground.sample_trajectory(u,actor,animation,frame_count=int(shot['frame_count']),fps=30.,
        source_start_seconds=float(shot.get('window_start_seconds',0.)),ignore_actors=[actor,camera],**kwargs)

def _prepare(u,index):
    import ue_scene_site_appearance_v1 as appearance
    import ue_primary_scene_samples_v1 as policy
    import ue_motion_portrait_scene_pilot_v1 as old
    plan=read(RUN/'four_trials_plan.json');shot=plan['shots'][index];sid=shot['shot_id']
    receipt=RUN/'prepared'/(sid+'.json')
    if receipt.exists():
        previous=read(receipt)
        from production_motion_contract_v1 import pin,verify_pin
        if previous.get('trial_plan')!=pin(RUN/'four_trials_plan.json'):
            raise ValueError('Existing trial belongs to another plan; preserve it and choose a new trial ID')
        require_ground_height_follow(previous,shot,plan['site'])
        require_level_exposure(previous)
        verify_pin(previous['body_asset'])
        for record in previous.get('prepared_assets',[]):verify_pin(record)
        return previous
    if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():raise RuntimeError('Render active')
    start=time.monotonic();site=plan['site']
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    dest=ASSETS+'/SceneTrials/L_'+sid;seqpath=ASSETS+'/SceneTrials/LS_'+sid
    if u.EditorAssetLibrary.does_asset_exist(dest) or u.EditorAssetLibrary.does_asset_exist(seqpath):raise RuntimeError('Unreceipted trial assets exist')
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    import ue_primary_saved_site_review_v1 as panel
    cached=getattr(u,panel.CACHE,None)
    if cached is not None:
        existing=getattr(u,panel.LIVE,{})
        if (existing.get('job') or {}).get('status')=='running':raise RuntimeError('Panel check active; do not change worlds')
        cached.restore()
    appearance.invalidate_cache(u)
    if not levels.load_level(site['map']):raise RuntimeError('Cannot load user main scene')
    # Source map is never saved over. Copy before adding trial actors.
    if not u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),dest):raise RuntimeError('Scene copy failed')
    if not levels.load_level(dest):raise RuntimeError('Cannot load trial copy')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    for actor in list(actors.get_all_level_actors()):
        if isinstance(actor,u.LevelSequenceActor) or actor.get_actor_label().startswith('DM_SiteReview_'):
            actors.destroy_actor(actor)
    import scene_site_appearance_v1 as selections
    selection=selections.validate_selection(plan['appearance_selection'])
    sex=selection['sex']
    template=u.load_asset(resolve(old.SOURCES[sex]))
    candidates=[a for a in u.GameplayStatics.get_all_actors_of_class(template,u.Actor) if a.get_actor_label()=='DM_CCWH_'+sex+'_Character']
    if len(candidates)!=1:raise RuntimeError('Missing modular source actor')
    actor=actors.duplicate_actor(candidates[0],world,u.Vector())
    actor.set_actor_label('DM_SiteReview_ProductionCharacter')
    actor.set_actor_location(u.Vector(*[site['position'][k] for k in ('x','y','z')]),False,False)
    actor.set_actor_rotation(u.Rotator(pitch=0,yaw=site['yaw'],roll=0),False)
    body_asset,body_provenance=motion_record(shot['motion_id'],sex)
    motion=u.load_asset(body_asset['asset'])
    applied=appearance.apply_actor(u,actor,selection,0.,motion,body_action_id=shot['motion_id'])
    animation=u.load_asset(applied['animation_path'])
    first=shot['frames'][0];rotation=first['rotation_pitch_yaw_roll']
    camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*first['position']),u.Rotator(pitch=rotation[0],yaw=rotation[1],roll=rotation[2]))
    camera.set_actor_label('DM_ProductionCamera');camera.set_editor_property('auto_activate_for_player',u.AutoReceiveInput.PLAYER0)
    component=camera.get_component_by_class(u.CameraComponent)
    component.set_editor_property('aspect_ratio',shot['aspect_ratio']);component.set_editor_property('constrain_aspect_ratio',True)
    component.set_field_of_view(first['horizontal_fov_degrees']);policy.exposure(component,site.get('exposure_compensation',0.))
    builder=module('ue_motion_scene_sequence_v1');builder.ALLOWED_PREFIX=ASSETS+'/'
    builder.NATIVE_TEMPLATE=resolve(builder.NATIVE_TEMPLATE)
    shot=copy.deepcopy(shot);shot.update(sex=sex,source_animation=body_asset['asset'],window_start_seconds=0.,source_start_seconds=0.,source_body_play_rate=1.)
    ground_height=sample_ground_height(u,actor,camera,animation,shot,site=site)
    built=builder.build_sequence(u,shot,actor,camera,animation,seqpath,ground_height_keys=ground_height['frames'])
    if not u.EditorAssetLibrary.save_loaded_asset(built['sequence'],False):raise RuntimeError('Sequence save failed')
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not u.EditorLoadingAndSavingUtils.save_map(world,dest):raise RuntimeError('Trial save failed')
    appearance.invalidate_cache(u)
    from production_motion_contract_v1 import pin
    content=Path('D:/UE/projects/datatry_02/Content')
    record={'success':True,'shot_id':sid,'trial_plan':pin(RUN/'four_trials_plan.json'),'body_asset':body_asset,
        'body_provenance':body_provenance,'prepared_assets':[pin(content/(dest.removeprefix('/Game/')+'.umap')),
                                                          pin(content/(seqpath.removeprefix('/Game/')+'.uasset'))],
        'ground_height_follow':ground_height,'sequence_ground_height_follow':built['report']['ground_height_follow'],
        'job':{'shot_id':sid,'map':dest+'.'+dest.rsplit('/',1)[-1],
        'sequence':seqpath+'.'+seqpath.rsplit('/',1)[-1]},'appearance':applied,'preparation_seconds':time.monotonic()-start,
        'width':shot['width'],'height':shot['height'],'duration_seconds':10.,'source_scene_saved':False,'site':site,
        'exposure_policy':EXPOSURE_POLICY}
    write(receipt,record);return {'success':True,'shot_id':sid,'preparation_seconds':record['preparation_seconds']}

def renderer():
    m=module('ue_motion_scene_render_v1');m.RUN=RUN;m.ASSET_ROOT=ASSETS;m.LIVE_ATTRIBUTE=LIVE
    from ue_primary_scene_samples_v1 import sample_renderer
    sample_renderer(m)
    return m

def require_level_exposure(record):
    if record.get('exposure_policy') != EXPOSURE_POLICY:
        raise ValueError('旧渲染准备未沿用关卡曝光，请为当前场景重新生成拍摄任务。')

def render(u,index,attempt):
    plan=read(RUN/'four_trials_plan.json');shot=plan['shots'][index]
    record=read(RUN/'prepared'/(shot['shot_id']+'.json'))
    from production_motion_contract_v1 import pin,verify_pin
    if record.get('trial_plan')!=pin(RUN/'four_trials_plan.json'):raise ValueError('Trial plan changed after preparation')
    require_ground_height_follow(record,shot,plan.get('site'))
    require_level_exposure(record)
    verify_pin(record['body_asset'])
    for asset in record.get('prepared_assets',[]):verify_pin(asset)
    return renderer().start_render(u,[record['job']],attempt,width=shot['width'],height=shot['height'])['receipt_path']

def status(u):return renderer().status(u)
