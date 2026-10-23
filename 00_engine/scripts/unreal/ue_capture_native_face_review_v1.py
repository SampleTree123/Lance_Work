"""Capture bounded native face preview frames on the current modular pair.

Root-only review probe. Restores actor animation and removes the transient camera;
does not save the level or alter any source asset. Native full clips may contain
body poses: this probe is for facial selection, not composition acceptance.
"""
import json
from pathlib import Path
import traceback
import unreal as u

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/character_runtime_face_library_20261007_v1')
LEVEL='/Game/DataMake/Validation/CFDNativeBatch4020261006/L_DM_CFDNativeBatch40_ModularReview_v001'
CACHE='_dm_native_face_capture_v1'
MAX_CAPTURE_FRAMES=50


def apply_animation_state(body, asset, loop, playing, position, rate):
    """Set exact sample time, then evaluate it without advancing animation time.

    OverrideAnimationData ticks/evaluates the current single-node instance;
    SetPosition alone does not evaluate it. Refresh again after setting the
    instance, or the captured pose/curves remain at the preceding sample.
    """
    body.override_animation_data(asset,loop,playing,position,rate)
    instance=body.get_anim_instance()
    if instance and hasattr(instance,'set_animation_asset'):
        instance.set_animation_asset(asset,loop,rate);instance.set_playing(playing)
    body.set_position(position,False)
    # Public reflected API: internally TickAnimation(0,false), then synchronous
    # RefreshBoneTransforms. Same SingleNode mode preserves the configured time.
    body.override_animation_data(asset,loop,playing,position,rate)


def run(task):
    if hasattr(u,CACHE):
        raise RuntimeError('A face capture is already active')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0]!=LEVEL:
        raise ValueError('Open the current modular review level first')
    root=Path(task['output_dir']).resolve()
    if not root.is_relative_to(RUN) or root.exists():
        raise ValueError('Capture output must be new in the current run')
    sex=task['sex']
    if sex not in ('female','male'):raise ValueError('Invalid sex')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    pair=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='DM_CCWH_'+sex+'_Character']
    if len(pair)!=1:raise RuntimeError('Expected one modular actor')
    actor=pair[0]
    parts={c.get_name():c for c in actor.get_components_by_class(u.SkeletalMeshComponent)}
    body=parts['Body']; motion=u.load_asset(task['animation'])
    if not isinstance(motion,u.AnimSequence) or motion.get_skeleton()!=body.get_skeletal_mesh_asset().get_editor_property('skeleton'):
        raise ValueError('Preview clip does not match current shared Skeleton')
    times=task['times']
    if not times or len(times)>MAX_CAPTURE_FRAMES or any(not isinstance(t,(int,float)) or t<0 or t>motion.get_play_length() for t in times):
        raise ValueError('Invalid capture times')
    data=body.get_editor_property('animation_data')
    old={'asset':data.anim_to_play,'loop':data.saved_looping,'playing':bool(body.get_anim_instance() and body.is_playing()),'position':body.get_position(),'rate':data.saved_play_rate}
    root.mkdir(parents=True)
    report={'success':False,'scope':'native clip facial selection preview','task':task,'captures':[]}
    camera=actors.spawn_actor_from_class(u.SceneCapture2D,u.Vector(100,actor.get_actor_location().y,170),u.Rotator(yaw=180),transient=True)
    cap=camera.get_component_by_class(u.SceneCaptureComponent2D)
    cap.set_editor_properties({'capture_every_frame':False,'capture_on_movement':False,'always_persist_rendering_state':True,
        'capture_source':u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,'fov_angle':30.0})
    texture=u.RenderingLibrary.create_render_target2d(world,720,720,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(.18,.18,.18,1))
    cap.set_editor_property('texture_target',texture)
    settings=u.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings')
    throttle=settings.get_editor_property('bThrottleCPUWhenNotForeground')
    settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
    state={'step':0,'frames':0,'handle':None,'camera':camera,'texture':texture}
    def finish(error=None):
        if state['handle'] is not None:u.unregister_slate_post_tick_callback(state['handle'])
        try:apply_animation_state(body,old['asset'],old['loop'],old['playing'],old['position'],old['rate'])
        except Exception: error=(error or '')+' restore: '+traceback.format_exc()
        actors.destroy_actor(camera)
        settings.set_editor_property('bThrottleCPUWhenNotForeground',throttle)
        report.update(success=error is None,error=error,original_animation_restored=True)
        (root/'capture_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        if hasattr(u,CACHE):delattr(u,CACHE)
    def tick(delta):
        try:
            if state['frames']==0:apply_animation_state(body,motion,False,False,times[state['step']],1.)
            state['frames']+=1
            head=body.get_socket_location('head')
            camera.set_actor_location(u.Vector(head.x+90,head.y,head.z+7),False,False)
            cap.capture_scene()
            if state['frames']<16:return
            name='frame_%02d_%06.2fs.png'%(state['step'],times[state['step']])
            u.RenderingLibrary.export_render_target(world,texture,str(root),name)
            instance=body.get_anim_instance()
            curve_names=['CTRL_expressions_eyeBlinkL','CTRL_expressions_jawOpen','CTRL_expressions_mouthCornerPullL']
            report['captures'].append({'path':str(root/name),'time_seconds':times[state['step']],
                'position':body.get_position(),'body_curves':{n:float(instance.get_curve_value(n)) for n in curve_names},
                'support_leaders':{n:(c.get_editor_property('leader_pose_component').get_path_name() if c.get_editor_property('leader_pose_component') else None) for n,c in parts.items() if n in ('Eyes','Teeth','Tongue','Tearline','EyeOcclusion')}})
            state['step']+=1;state['frames']=0
            if state['step']==len(times):finish()
        except Exception:finish(traceback.format_exc())
    state['handle']=u.register_slate_post_tick_callback(tick)
    setattr(u,CACHE,state)
    print('Native face capture scheduled: '+str(root))


if __name__=='__main__':
    run(json.loads(Path(globals()['DM_NATIVE_FACE_CAPTURE_TASK']).read_text(encoding='utf-8')))
