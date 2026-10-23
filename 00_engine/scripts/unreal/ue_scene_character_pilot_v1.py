"""Isolated scene character trials; owner SCENE_CAMERA_SEQUENCE section 11.

Imports/edits are confined to the active pilot. Original environment and actor
template packages are pinned and checked. No implicit editor connection.
"""
import copy, hashlib, json, math
from pathlib import Path
import ue_motion_portrait_scene_pilot_v1 as base
import ue_scene_location_pilot_v1 as locations

RUN=base.RUN; A=base.A

def transform_point(point,offset,yaw):
    a=math.radians(yaw);c=math.cos(a);s=math.sin(a);x,y,z=point
    return [c*x-s*y+offset[0],s*x+c*y+offset[1],z+offset[2]]

def scene_plan(scene_id,anchor,yaw=0.,revision='v1',scene_source_map=None):
    """Translate each action's initial root to one common performance anchor."""
    source=base.read(RUN/'camera_trial_plan_v1.json')
    clips={c['clip_id']:c for c in base.read(RUN/'all_motion_samples_v1.json')['clips']}
    selected=[]
    wanted={'front_full','orbit_360','high_full','dolly_in_side'}
    for original in source['shots']:
        if original['group']!='portrait':continue
        if original['orientation']=='landscape' and original['camera_id'] not in wanted:continue
        if original['orientation']=='portrait' and original['camera_id']!='front_full':continue
        shot=copy.deepcopy(original);clip=clips[shot['source_clip_id']]
        t=shot['source_start_seconds'];frames=clip['frames']
        before=max((r for r in frames if r['t']<=t),key=lambda r:r['t'])
        after=min((r for r in frames if r['t']>=t),key=lambda r:r['t'])
        alpha=(t-before['t'])/(after['t']-before['t']) if after['t']>before['t'] else 0.
        root=[(1-alpha)*a+alpha*b for a,b in zip(before['bones']['root'],after['bones']['root'])]
        rotated=transform_point(root,[0,0,0],yaw)
        # Root Z can encode a vertical action: only normalize horizontal origin.
        offset=[anchor[0]-rotated[0],anchor[1]-rotated[1],anchor[2]]
        shot['shot_id']='scene_'+scene_id+'_'+revision+'_'+original['shot_id'].removeprefix('portrait_')
        shot.update(group='scenes',scene_id=scene_id,scene_anchor_cm=anchor,scene_yaw_degrees=yaw,actor_offset_cm=offset)
        for row in shot['frames']+[shot['endpoint_validation_frame']]:
            row['position']=transform_point(row['position'],offset,yaw)
            row['look_at']=transform_point(row['look_at'],offset,yaw)
            row['rotation_pitch_yaw_roll'][1]+=yaw
        shot['trajectory_sha256']=hashlib.sha256(json.dumps(shot['frames']+[shot['endpoint_validation_frame']],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        selected.append(shot)
    assert len(selected)==15
    out={'schema':'motion_portrait_camera_trial_v1','scene_id':scene_id,'revision':revision,'anchor_cm':anchor,'yaw_degrees':yaw,'source_plan':base.pin(RUN/'camera_trial_plan_v1.json'),'shots':selected,'human_acceptance':'pending'}
    if scene_source_map is not None:
        assert scene_source_map.startswith(A+'/SceneBases/'), 'Only an owned pilot point base may replace the original scene'
        out['scene_source_map']=scene_source_map
        out['scene_source_pin']=base.pin(base.package(scene_source_map,'.umap'))
    path=RUN/('scene_trial_plan_'+scene_id+'_'+revision+'.json');base.save(path,out)
    return path

def prepare(u,plan_path,selected_ids=None):
    base.clean(u);plan_path=Path(plan_path);plan=base.read(plan_path)
    scene_id=plan['scene_id'];levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    builder=base.module('ue_motion_scene_sequence_v1');helper=base.module('ue_camera_prepare_studio_v2')
    current_source=locations.current_map(scene_id)
    source_scene=plan.get('scene_source_map',current_source)
    if 'scene_source_map' in plan:
        assert source_scene.startswith(A+'/SceneBases/')
        assert base.pin(base.package(source_scene,'.umap'))==plan['scene_source_pin']
    pins=[base.pin(base.package(v,'.umap')) for v in dict.fromkeys([current_source,source_scene,*base.SOURCES.values()])]
    jobs=[];cache={}
    for shot in plan['shots']:
        if selected_ids is not None and shot['shot_id'] not in selected_ids:continue
        sid=shot['shot_id'];receipt=RUN/'scene_sequences'/(sid+'.json')
        if receipt.exists():
            prior=base.read(receipt);assert prior['success'] and prior['plan']==base.pin(plan_path)
            for p in prior['asset_files']:assert base.pin(p['path'])==p
            assert prior['source_pins']==pins, 'Scene or character sources changed since preparation'
            for p in prior['source_pins']:assert base.pin(p['path'])==p
            jobs.append(prior['job']);continue
        base.clean(u);sex=shot['sex'];key=(shot['motion_id'],sex)
        if key not in cache:cache[key]=base.ensure_motion(u,shot)
        motion,detail=cache[key]
        dest=A+'/SceneTrials/L_'+sid;seqpath=A+'/SceneTrials/LS_'+sid
        assert not u.EditorAssetLibrary.does_asset_exist(dest) and not u.EditorAssetLibrary.does_asset_exist(seqpath)
        u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
        assert levels.load_level(source_scene)
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert u.EditorLoadingAndSavingUtils.save_map(world,dest);assert levels.load_level(dest)
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        removed=[]
        for a in list(actors.get_all_level_actors()):
            if isinstance(a,u.LevelSequenceActor):removed.append(a.get_actor_label());assert actors.destroy_actor(a)
        template_world=u.load_asset(base.SOURCES[sex])
        candidates=[a for a in u.GameplayStatics.get_all_actors_of_class(template_world,u.Actor) if a.get_actor_label()=='DM_CCWH_'+sex+'_Character']
        assert len(candidates)==1,'Cannot locate one source modular character'
        expected_followers=helper._parent_bound_names(u,candidates[0])
        source_scale=candidates[0].get_actor_scale3d()
        assert max(abs(v-1.) for v in (source_scale.x,source_scale.y,source_scale.z))<1e-6
        source_body=helper.fresh_component(u,candidates[0],'Body')
        relative_location=source_body.get_editor_property('relative_location');relative_rotation=source_body.get_editor_property('relative_rotation');relative_scale=source_body.get_editor_property('relative_scale3d')
        assert max(abs(v) for v in (relative_location.x,relative_location.y,relative_location.z,relative_rotation.pitch,relative_rotation.yaw,relative_rotation.roll))<1e-5
        assert max(abs(v-1.) for v in (relative_scale.x,relative_scale.y,relative_scale.z))<1e-6
        actor=actors.duplicate_actor(candidates[0],world,u.Vector(0,0,0));assert actor
        actor.set_actor_label('DM_Scene_'+sex+'_Character')
        actor.set_actor_location(u.Vector(*shot['actor_offset_cm']),False,False)
        actor.set_actor_rotation(u.Rotator(pitch=0,yaw=shot['scene_yaw_degrees'],roll=0),False)
        followers=[]
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            c.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            if c.get_name() in helper.FACE_COMPONENTS:
                c.set_leader_pose_component(None,True,False);c.override_animation_data(motion,False,False,float(shot['window_start_seconds']),1.)
                if c.get_name()!='Body':followers.append(c)
        first=shot['frames'][0]
        camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*first['position']),u.Rotator(*first['rotation_pitch_yaw_roll']))
        camera.set_actor_label('DM_Scene_Trial_Camera')
        # Set the initial PIE view before Sequencer evaluates its first camera cut.
        camera.set_editor_property('auto_activate_for_player',u.AutoReceiveInput.PLAYER0)
        component=camera.get_component_by_class(u.CameraComponent)
        component.set_editor_property('aspect_ratio',shot['aspect_ratio']);component.set_editor_property('constrain_aspect_ratio',True);component.set_field_of_view(first['horizontal_fov_degrees'])
        built=builder.build_sequence(u,shot,actor,camera,motion,seqpath)
        for c in followers:builder.add_animation_component_track(u,built['sequence'],built['actor_binding'],c,motion,source_start_seconds=shot['window_start_seconds'],frame_count=shot['frame_count'])
        assert u.EditorAssetLibrary.save_loaded_asset(built['sequence'],False)
        u.LevelSequenceEditorBlueprintLibrary.close_level_sequence();assert levels.save_current_level();base.clean(u)
        assert levels.load_level(dest)
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        reloaded=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='DM_Scene_'+sex+'_Character'];assert len(reloaded)==1
        actor=reloaded[0];sequence=u.load_asset(seqpath)
        trial_cameras=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='DM_Scene_Trial_Camera']
        assert len(trial_cameras)==1
        assert trial_cameras[0].get_editor_property('auto_activate_for_player')==u.AutoReceiveInput.PLAYER0
        bindings=helper.binding_readback(u,sequence,world)
        assert actor.get_path_name().startswith(dest+'.')
        actual_followers=helper._parent_bound_names(u,actor)
        assert actual_followers==expected_followers,'Cross-world copy changed populated follower inventory'
        follower_rows=[]
        for name in actual_followers:
            state=helper._component_source_state(u,actor,name)
            c=helper.fresh_component(u,actor,name)
            assert c.get_editor_property('use_attach_parent_bound') is True
            follower_rows.append(dict(state,use_attach_parent_bound=True))
        follower_audit={'success':True,'components':follower_rows,'expected_names':expected_followers}
        face_audit=helper.audit_face_animation(u,actor,motion.get_path_name())
        assert abs(float(motion.get_editor_property('rate_scale'))-1.)<1e-8
        job={'shot_id':sid,'map':world.get_path_name(),'sequence':sequence.get_path_name()}
        for p in pins:assert base.pin(p['path'])==p
        base.save(receipt,{'success':True,'plan':base.pin(plan_path),'job':job,'composition':detail,'bindings':bindings,'follower_audit':follower_audit,'face_audit':face_audit,'animation_rate_scale':1.,'removed_demo_sequence_actors':removed,'source_pins':pins,'source_packages_unchanged':True,'asset_files':[base.pin(base.package(dest,'.umap')),base.pin(base.package(seqpath))],'human_acceptance':'pending'})
        jobs.append(job)
    complete=[]
    for shot in plan['shots']:
        receipt=RUN/'scene_sequences'/(shot['shot_id']+'.json')
        if receipt.exists():complete.append(base.read(receipt)['job'])
    base.save(RUN/('scene_prepared_'+scene_id+'_'+plan['revision']+'.json'),{'success':len(complete)==len(plan['shots']),'plan':base.pin(plan_path),'jobs':complete},False)
    return {'scene_id':scene_id,'jobs':len(jobs),'total_prepared':len(complete),'total':len(plan['shots'])}
