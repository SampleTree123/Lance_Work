"""Root-owned isolated motion/portrait stage preparation. SCENE_CAMERA_SEQUENCE §11."""
from pathlib import Path
import hashlib, json, importlib.util, datetime, traceback

S=Path(__file__).resolve().parent
RUN=S.parents[1]/'outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1'
PLAN_NAME='camera_trial_plan_v1.json'
A='/Game/DataMake/Validation/MotionPortraitScenePilot20261011'
CONTENT=Path('D:/UE/projects/datatry_02/Content')
SOURCES={
    'female':'/Game/DataMake/Validation/CameraMotionPilot20261009/MapsV2/L_cam_01_static_front_v003',
    'male':'/Game/DataMake/Validation/CameraMotionPilot20261009/MapsV2/L_cam_12_static_side_v003'}

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):
    p=Path(p).resolve(strict=True)
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,value,exclusive=True):
    p=Path(p);assert p.resolve().is_relative_to(RUN.resolve());p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x' if exclusive else 'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def module(name):
    spec=importlib.util.spec_from_file_location('_motion_scene_'+name,S/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def package(p,ext='.uasset'):return CONTENT/(p.split('.')[0].removeprefix('/Game/')+ext)
def clean(u):
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty:raise RuntimeError('Unsaved packages: '+str([p.get_name() for p in dirty]))
    assert not u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering()
def character(u,sex):
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    selected=[a for a in actors if a.get_actor_label()=='DM_CCWH_'+sex+'_Character']
    cams=[a for a in actors if a.get_actor_label()=='DM_CCWH_Camera']
    assert len(selected)==len(cams)==1
    return selected[0],cams[0]

def ensure_motion(u,shot):
    loop=module('ue_cfd40_full_motion_loop_v1');loop.RUN=RUN;loop.ASSET_ROOT=A
    choices,selection=loop.accepted_faces();choice,proof=choices[(shot['sex'],'smile')]
    source=shot['source_animation']
    if shot['motion_id']=='MOTION_CAND_008':
        report_path=RUN/'body_windows'/('walk_'+shot['sex']+'_v1.json')
        report=read(report_path)
        if not report['success'] and shot['sex']=='male':
            physical=read(RUN/'body_windows/walk_male_physical_validation_v1.json')
            assert physical['success'] and physical['sources_unchanged'] and physical['target_unchanged']
            assert physical['original_failed_report']==pin(report_path)
            assert physical['destination']==report['destination']
            for record in physical['source_target_records']:
                assert pin(record['path'])['sha256']==record['sha256']
        else:assert report['success'] and report['sources_unchanged']
        source=report['destination']
    elif shot['motion_id'].startswith('ACT_'):
        reuse_proof=read(RUN/'legacy_shared_motion_reuse_v2.json')
        assert reuse_proof['success'] and reuse_proof['sources_unchanged']
        assert reuse_proof['camera_plan_unchanged']==pin(RUN/'camera_trial_plan_v1.json')
        selected=[r for r in reuse_proof['actions'] if r['motion_id']==shot['motion_id'] and r['sex']==shot['sex']]
        assert len(selected)==1 and selected[0]['success']
        selected=selected[0]
        assert selected['source']['asset'].split('.')[0]==source.split('.')[0]
        for key in ('source','target','prior_full_frame_proof'):
            record=selected[key];assert pin(record['path'])['sha256']==record['sha256']
        source=selected['target']['asset']
    animation,detail=loop.ensure_composite(u,shot['sex'],{'path':source,'action_id':shot['motion_id']},choice,proof,selection)
    if shot['motion_id'].startswith('ACT_'):
        detail=dict(detail,shared_body_reuse_proof=pin(RUN/'legacy_shared_motion_reuse_v2.json'))
    return animation,detail

def prepare(u,selected_ids=None):
    assert Path(u.Paths.project_dir()).resolve()==CONTENT.parent.resolve()
    clean(u);plan_path=RUN/PLAN_NAME;plan=read(plan_path)
    shots=plan['shots'];wanted=set(selected_ids) if selected_ids is not None else {s['shot_id'] for s in shots}
    assert wanted and wanted<={s['shot_id'] for s in shots}
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    entry=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name()
    builder=module('ue_motion_scene_sequence_v1');helper=module('ue_camera_prepare_studio_v2')
    motion_cache={};jobs=[];native_text=None
    source_pins=[pin(package(p,'.umap')) for p in SOURCES.values()]
    source_pins.append(pin(package(builder.NATIVE_TEMPLATE)))
    for shot in shots:
        if shot['shot_id'] not in wanted:continue
        sid=shot['shot_id'];receipt_path=RUN/'sequences'/(sid+'.json')
        if receipt_path.exists():
            prior=read(receipt_path);assert prior['success'] and prior['plan']==pin(plan_path)
            for record in prior['asset_files']:assert pin(record['path'])==record
            jobs.append(prior['job']);continue
        clean(u)
        mkey=(shot['motion_id'],shot['sex'])
        if mkey not in motion_cache:motion_cache[mkey]=ensure_motion(u,shot)
        motion,detail=motion_cache[mkey]
        map_path=A+'/Maps/L_'+sid;seq_path=A+'/Sequences/LS_'+sid
        assert not u.EditorAssetLibrary.does_asset_exist(map_path) and not u.EditorAssetLibrary.does_asset_exist(seq_path),'Partial assets require inspection'
        report={'success':False,'shot_id':sid,'plan':pin(plan_path)}
        try:
            u.LevelSequenceEditorBlueprintLibrary.close_level_sequence();clean(u)
            assert levels.load_level(SOURCES[shot['sex']])
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            assert u.EditorLoadingAndSavingUtils.save_map(world,map_path)
            assert levels.load_level(map_path)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            actor,camera=character(u,shot['sex'])
            followers=[]
            for c in actor.get_components_by_class(u.SkeletalMeshComponent):
                c.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
                if c.get_name() in helper.FACE_COMPONENTS:
                    c.set_leader_pose_component(None,True,False);c.override_animation_data(motion,False,False,float(shot['window_start_seconds']),1.)
                    if c.get_name()!='Body':followers.append(c)
            comp=camera.get_component_by_class(u.CameraComponent)
            comp.set_editor_property('aspect_ratio',shot['aspect_ratio']);comp.set_editor_property('constrain_aspect_ratio',True)
            first=shot['frames'][0];camera.set_actor_location(u.Vector(*first['position']),False,False)
            camera.set_actor_rotation(u.Rotator(*first['rotation_pitch_yaw_roll']),False);comp.set_field_of_view(first['horizontal_fov_degrees'])
            # Cache only immutable native section text, never a pasted section or params.
            # Each track still gets a fresh section and its own animation/time settings.
            if native_text is None:
                native_text=builder._native_section_text(u)
                u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
            built=builder.build_sequence(u,shot,actor,camera,motion,seq_path,native_text=native_text)
            for c in followers:builder.add_animation_component_track(u,built['sequence'],built['actor_binding'],c,motion,source_start_seconds=shot['window_start_seconds'],frame_count=shot['frame_count'],native_text=native_text)
            assert u.EditorAssetLibrary.save_loaded_asset(built['sequence'],False)
            # This map was created above in the task's namespace; avoid the
            # interactive source-control checkout used by save_current_level.
            u.LevelSequenceEditorBlueprintLibrary.close_level_sequence();assert u.EditorLoadingAndSavingUtils.save_map(world,map_path);clean(u)
            assert levels.load_level(map_path)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();sequence=u.load_asset(seq_path)
            bindings=helper.binding_readback(u,sequence,world)
            job={'shot_id':sid,'map':world.get_path_name(),'sequence':sequence.get_path_name()}
            report.update(success=True,job=job,composition=detail,sequence_report=built['report'],bindings=bindings,
                          asset_files=[pin(package(map_path,'.umap')),pin(package(seq_path))],source_pins=source_pins,human_acceptance='pending')
            for record in source_pins:assert pin(record['path'])==record
            save(receipt_path,report);jobs.append(job)
            save(RUN/'preparation_progress_v1.json',{'last_shot':sid,'prepared_in_call':len(jobs),'selected':len(wanted)},False)
        except Exception:
            report['error']=traceback.format_exc();save(RUN/'prepare_failures'/(sid+'_'+datetime.datetime.now().strftime('%H%M%S')+'.json'),report);raise
    for record in source_pins:assert pin(record['path'])==record
    clean(u);u.LevelSequenceEditorBlueprintLibrary.close_level_sequence();assert levels.load_level(entry)
    complete=[]
    for s in shots:
        p=RUN/'sequences'/(s['shot_id']+'.json')
        if p.exists() and read(p).get('success'):complete.append(read(p)['job'])
    save(RUN/'prepared_jobs_v1.json',{'success':len(complete)==len(shots),'plan':pin(plan_path),'jobs':complete,'prepared':len(complete),'total':len(shots)},False)
    return {'prepared_this_call':len(jobs),'total_prepared':len(complete),'total':len(shots),'entry_restored':entry}

def render(u,attempt,ids,width=1280,height=720):
    manifest=read(RUN/'prepared_jobs_v1.json');assert manifest['plan']==pin(RUN/PLAN_NAME)
    wanted=set(ids);jobs=[j for j in manifest['jobs'] if j['shot_id'] in wanted];assert len(jobs)==len(wanted)
    for job in jobs:
        receipt=read(RUN/'sequences'/(job['shot_id']+'.json'));assert receipt['success']
        for record in receipt['asset_files']:assert pin(record['path'])==record
    return module('ue_motion_scene_render_v1').start_render(u,jobs,attempt,width=width,height=height)
