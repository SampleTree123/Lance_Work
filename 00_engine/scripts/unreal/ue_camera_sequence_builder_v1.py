"""Build only new camera-pilot LevelSequences; Unreal is injected by caller.

This module does not connect to or launch Unreal. The caller owns the level,
actors, follower setup, render queue and cleanup. build_sequence returns
{'sequence': unreal.LevelSequence, 'report': JSON-serializable audit}.
"""
from __future__ import annotations

import math
import re

ALLOWED_PREFIX='/Game/DataMake/Validation/CameraMotionPilot20261009/'
NATIVE_TEMPLATE='/Game/DataMake/Sequences/FirstBatch/Templates/LS_DM_NativeSkeletalAnimationSectionTemplate_v001'
CHANNEL_NAMES=('Location.X','Location.Y','Location.Z','Rotation.X','Rotation.Y','Rotation.Z','Scale.X','Scale.Y','Scale.Z')

def unwrap_degrees(values):
    output=[]
    for value in values:
        value=float(value)
        if not math.isfinite(value): raise ValueError('Nonfinite camera rotation')
        if output: value=output[-1]+((value-output[-1]+180)%360-180)
        output.append(value)
    return output

def key_rows(shot):
    if shot.get('status')!='geometry_pass': raise ValueError('Only geometry-passed candidates may build')
    if shot.get('fps')!=30 or shot.get('duration_seconds')!=10 or shot.get('frame_count')!=300:
        raise ValueError('Pilot requires uniformly 10 seconds / 30 fps / 300 frames')
    rows=shot['frames']+[shot['endpoint_validation_frame']]
    if len(rows)!=301: raise ValueError('Need 300 display frames plus endpoint key')
    for i,row in enumerate(rows):
        if abs(float(row['t'])-i/30)>1e-7: raise ValueError('Nonuniform key time')
        if len(row['position'])!=3 or len(row['rotation_pitch_yaw_roll'])!=3: raise ValueError('Bad camera vector')
        if not all(math.isfinite(float(x)) for x in row['position']): raise ValueError('Nonfinite location')
        if not 1<float(row['horizontal_fov_degrees'])<170: raise ValueError('Bad horizontal FOV')
    pitch=unwrap_degrees([r['rotation_pitch_yaw_roll'][0] for r in rows])
    yaw=unwrap_degrees([r['rotation_pitch_yaw_roll'][1] for r in rows])
    roll=unwrap_degrees([r['rotation_pitch_yaw_roll'][2] for r in rows])
    # Unreal transform channels are Rotation.X=Roll, Y=Pitch, Z=Yaw.
    return [{'frame':i,'transform':list(r['position'])+[roll[i],pitch[i],yaw[i],1.,1.,1.],
             'fov':float(r['horizontal_fov_degrees'])} for i,r in enumerate(rows)]

def validate_new_path(unreal,path):
    if not path.startswith(ALLOWED_PREFIX) or not re.fullmatch(r'/[A-Za-z0-9_/]+',path):
        raise ValueError('Asset must be a clean package path below CameraMotionPilot20261009')
    if '..' in path or unreal.EditorAssetLibrary.does_asset_exist(path):
        raise ValueError('Refusing to overwrite an existing asset')
    return path.rsplit('/',1)

def body_component(unreal,actor):
    components=list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    exact=[c for c in components if str(c.get_name()).lower()=='body']
    if len(exact)==1: return exact[0]
    if len(components)==1: return components[0]
    raise ValueError('Cannot identify one Body component; caller must supply an unambiguous actor')

def _native_section_text(unreal):
    template=unreal.load_asset(NATIVE_TEMPLATE)
    if not isinstance(template,unreal.LevelSequence): raise RuntimeError('Native animation-section template is unavailable')
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(template)
    sections=[section for binding in template.get_bindings() for track in binding.get_tracks()
              if isinstance(track,unreal.MovieSceneSkeletalAnimationTrack) for section in track.get_sections()]
    if len(sections)!=1: raise RuntimeError('Native template requires exactly one skeletal section')
    editor=unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    text=editor.copy_sections(sections)
    if not text: raise RuntimeError('Native section copy failed')
    return text

def _channels(section):
    channels=list(section.get_all_channels())
    return channels

def _linear_key(unreal,channel,frame,value):
    return channel.add_key(unreal.FrameNumber(frame),float(value),sub_frame=0.,
                           time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE,
                           interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)

def add_animation_component_track(unreal,sequence,actor_binding,component,animation,*,source_start_seconds=0,native_text=None):
    """Optional helper for caller-owned visible face components on the same rig.

    Caller must disconnect an incompatible leader-pose relationship before using
    a separate animation track. This function does not change follower setup.
    """
    if source_start_seconds<0: raise ValueError('Negative source offset')
    binding=sequence.add_possessable(component); binding.set_parent(actor_binding)
    binding.set_display_name(str(component.get_name()))
    track=binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    track.set_display_name('Camera pilot body / native animation')
    if native_text is None: native_text=_native_section_text(unreal)
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    editor=unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    pasted=editor.paste_sections(native_text,unreal.MovieScenePasteSectionsParams(
        tracks=[track],track_row_indices=[0],time=unreal.FrameTime(unreal.FrameNumber(0))))
    if pasted is None or len(pasted)!=1: raise RuntimeError('Native skeletal section paste failed')
    section=pasted[0]; section.set_range(0,300)
    # Native template preserves UE 5.8 time-warp parameter initialization.
    params=section.get_editor_property('params')
    for key,value in [('animation',animation),('reverse',False),('force_custom_mode',True),
                      ('play_rate',unreal.MovieSceneTimeWarpExtensions.make_time_warp(1.)),
                      ('start_frame_offset',unreal.FrameNumber(0)),('end_frame_offset',unreal.FrameNumber(0))]:
        params.set_editor_property(key,value)
    tick=sequence.get_tick_resolution()
    offset=round(source_start_seconds*tick.numerator/tick.denominator)
    params.set_editor_property('first_loop_start_frame_offset',unreal.FrameNumber(offset))
    section.set_editor_property('params',params)
    section.set_range(0,300)
    if abs(unreal.MovieSceneTimeWarpExtensions.to_fixed_play_rate(params.get_editor_property('play_rate'))-1.)>1e-8:
        raise RuntimeError('Animation must play at 1x after composition')
    if params.get_editor_property('animation')!=animation or not params.get_editor_property('force_custom_mode'):
        raise RuntimeError('Animation parameter readback mismatch')
    return {'binding':binding,'track':track,'section':section,'component':component.get_path_name(),
            'animation':animation.get_path_name(),'source_start_seconds':source_start_seconds}

def build_sequence(unreal,shot,actor,camera,animation,path):
    keys=key_rows(shot)
    folder,name=validate_new_path(unreal,path)
    body=body_component(unreal,actor)
    camera_component=camera.get_component_by_class(unreal.CameraComponent)
    if camera_component is None: raise ValueError('Camera has no CameraComponent')
    cine=getattr(unreal,'CineCameraComponent',None)
    if cine is not None and isinstance(camera_component,cine):
        raise ValueError('Use ordinary CameraActor: CineCamera requires focal-length tracks, not FieldOfView')
    if not isinstance(animation,unreal.AnimSequence): raise ValueError('Expected an AnimSequence')
    start=float(shot.get('window_start_seconds',0))
    length=float(animation.get_editor_property('sequence_length'))
    if start+10>length+1e-5: raise ValueError('Animation is shorter than the 10-second source window')
    library=unreal.LevelSequenceEditorBlueprintLibrary
    previous=library.get_current_level_sequence()
    sequence=None
    try:
        native_text=_native_section_text(unreal)
        sequence=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.LevelSequence,unreal.LevelSequenceFactoryNew())
        if not isinstance(sequence,unreal.LevelSequence): raise RuntimeError('Sequence asset creation failed')
        sequence.set_display_rate(unreal.FrameRate(30,1))
        sequence.set_tick_resolution_directly(unreal.FrameRate(24000,1))
        sequence.set_playback_start(0); sequence.set_playback_end(300)
        actor_binding=sequence.add_possessable(actor); actor_binding.set_display_name('Camera pilot character')
        body_report=add_animation_component_track(unreal,sequence,actor_binding,body,animation,source_start_seconds=start,native_text=native_text)
        camera_binding=sequence.add_possessable(camera); camera_binding.set_display_name('Camera pilot baked trajectory')
        transform_track=camera_binding.add_track(unreal.MovieScene3DTransformTrack)
        transform_section=transform_track.add_section(); transform_section.set_range(0,301)
        channels=_channels(transform_section)
        if len(channels)<9: raise RuntimeError('Expected nine transform channels')
        # Names may expose Location or Translation; confirm rotation semantics.
        names=[str(c.get_editor_property('channel_name')) for c in channels[:9]]
        if names[3:6]!=['Rotation.X','Rotation.Y','Rotation.Z']:
            raise RuntimeError('Unexpected transform-channel rotation order: '+repr(names))
        for row in keys:
            for channel,value in zip(channels[:9],row['transform']): _linear_key(unreal,channel,row['frame'],value)
        component_binding=sequence.add_possessable(camera_component); component_binding.set_parent(camera_binding)
        fov_track=component_binding.add_track(unreal.MovieSceneFloatTrack)
        fov_track.set_property_name_and_path('FieldOfView','FieldOfView')
        fov_section=fov_track.add_section(); fov_section.set_range(0,301)
        fov_channels=_channels(fov_section)
        if len(fov_channels)!=1: raise RuntimeError('Expected one FOV channel')
        for row in keys: _linear_key(unreal,fov_channels[0],row['frame'],row['fov'])
        cut_track=sequence.add_track(unreal.MovieSceneCameraCutTrack)
        cut=cut_track.add_section(); cut.set_range(0,300)
        cut.set_camera_binding_id(sequence.get_binding_id(camera_binding))
        counts=[len(c.get_keys()) for c in channels[:9]]+[len(fov_channels[0].get_keys())]
        if counts!=[301]*10: raise RuntimeError('Camera keys did not read back completely')
        if not unreal.EditorAssetLibrary.save_loaded_asset(sequence,only_if_is_dirty=False):
            raise RuntimeError('Sequence save failed')
        report={'schema':'camera_pilot_sequence_build_v1','status':'built_pending_runtime_validation',
                'sequence_path':sequence.get_path_name(),'shot_id':shot['shot_id'],'source_trajectory_sha256':shot['trajectory_sha256'],
                'body_component':body_report['component'],'animation_path':animation.get_path_name(),
                'source_start_seconds':start,'fps':30,'duration_seconds':10,'render_frames':300,
                'start_frame_inclusive':0,'end_frame_exclusive':300,'endpoint_key_frame':300,
                'transform_and_fov_key_counts':counts,'rotation_channel_order':'roll,pitch,yaw; unwrapped',
                'interpolation':'LINEAR','force_custom_mode':True,'native_template':NATIVE_TEMPLATE,
                'followers':'caller responsibility; only Body bound by build_sequence'}
        return {'sequence':sequence,'actor_binding':actor_binding,'report':report}
    finally:
        if previous is not None: library.open_level_sequence(previous)
        else: library.close_level_sequence()
