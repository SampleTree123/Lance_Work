"""Variable duration must propagate through endpoint keys and contracts."""
import copy
import sys
from pathlib import Path
import pytest
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ue_motion_scene_sequence_v1 as sequence


def shot(count):
    rows=[{'t':i/30,'position':[10,20,30],'rotation_pitch_yaw_roll':[5,179+i*.2,3],'horizontal_fov_degrees':35} for i in range(count+1)]
    return {'status':'geometry_pass','fps':30,'frame_count':count,'duration_seconds':count/30,'frames':rows[:-1],'endpoint_validation_frame':rows[-1]}


@pytest.mark.parametrize('count',[105,210,300,639,1131])
def test_variable_counts_have_exact_endpoint_without_extra_display_frame(count):
    candidate=shot(count);original=copy.deepcopy(candidate)
    rows=sequence.key_rows(candidate)
    assert len(rows)==count+1 and rows[-1]['frame']==count
    assert rows[0]['transform']==[10,20,30,3,5,179,1.,1.,1.]
    assert candidate==original


def test_truncated_camera_window_does_not_pass_as_complete():
    candidate=shot(639);candidate['frames']=candidate['frames'][:300]
    with pytest.raises(ValueError,match='endpoint'):sequence.key_rows(candidate)


def test_reused_native_text_creates_independent_animation_tracks(monkeypatch):
    class Props:
        def __init__(self): self.values={}
        def set_editor_property(self,key,value): self.values[key]=value
        def get_editor_property(self,key): return self.values[key]
    class Section(Props):
        def __init__(self):
            super().__init__();self.values['params']=Props()
        def set_range(self,start,end): self.range=(start,end)
    sections=[]
    def paste(text,params):
        assert text=='immutable native text'
        section=Section();sections.append(section);return [section]
    editor=SimpleNamespace(paste_sections=paste)
    unreal=SimpleNamespace(
        MovieSceneSkeletalAnimationTrack=object,LevelSequenceEditorSubsystem=object,
        LevelSequenceEditorBlueprintLibrary=SimpleNamespace(open_level_sequence=Mock()),
        get_editor_subsystem=lambda cls:editor,
        MovieScenePasteSectionsParams=lambda **kwargs:SimpleNamespace(**kwargs),
        FrameTime=lambda x:x,FrameNumber=lambda x:x,
        MovieSceneTimeWarpExtensions=SimpleNamespace(make_time_warp=lambda x:x,to_fixed_play_rate=lambda x:x))
    track=SimpleNamespace(set_display_name=Mock())
    def binding(component):
        return SimpleNamespace(set_parent=Mock(),set_display_name=Mock(),add_track=lambda cls:track)
    seq=SimpleNamespace(add_possessable=binding,get_tick_resolution=lambda:SimpleNamespace(numerator=24000,denominator=1))
    monkeypatch.setattr(sequence,'_native_section_text',Mock(side_effect=AssertionError('cached text must avoid clipboard')))
    anims=[SimpleNamespace(get_path_name=lambda:'/Anim/A'),SimpleNamespace(get_path_name=lambda:'/Anim/B')]
    for name,anim,start,count in [('Body',anims[0],0,696),('Eyes',anims[1],1.5,259)]:
        component=SimpleNamespace(get_name=lambda:name,get_path_name=lambda:'/Actor/'+name)
        sequence.add_animation_component_track(unreal,seq,object(),component,anim,
            source_start_seconds=start,native_text='immutable native text',frame_count=count)
    assert sections[0] is not sections[1]
    assert sections[0].range==(0,696) and sections[1].range==(0,259)
    first,second=[s.get_editor_property('params').values for s in sections]
    assert first['animation'] is anims[0] and second['animation'] is anims[1]
    assert first['first_loop_start_frame_offset']==0
    assert second['first_loop_start_frame_offset']==36000
    for params in (first,second):
        assert params['play_rate']==1 and params['force_custom_mode'] is True
        assert params['reverse'] is False
        assert params['start_frame_offset']==params['end_frame_offset']==0


def ground_rows():
    return [{'frame':i,'t':i/30,'actor_z_cm':z,'offset_z_cm':z-100.}
            for i,z in enumerate((100.,104.,101.))]


def test_ground_height_keys_are_absolute_z_only_with_original_transform_defaults():
    class Channel:
        def __init__(self,name):self.name=name;self.keys=[];self.default=None
        def get_editor_property(self,name):return self.name
        def set_default(self,value):self.default=value
        def add_key(self,frame,value,**kwargs):self.keys.append((frame,value,kwargs))
        def get_keys(self):return self.keys
    channels=[Channel(name) for name in sequence.CHANNEL_NAMES]
    section=SimpleNamespace(get_all_channels=lambda:channels,set_range=Mock())
    track=SimpleNamespace(set_display_name=Mock(),add_section=lambda:section)
    binding=SimpleNamespace(add_track=Mock(return_value=track))
    actor=SimpleNamespace(get_actor_location=lambda:SimpleNamespace(x=10.,y=20.,z=100.),
        get_actor_rotation=lambda:SimpleNamespace(roll=3.,pitch=5.,yaw=40.),
        get_actor_scale3d=lambda:SimpleNamespace(x=1.,y=2.,z=3.))
    unreal=SimpleNamespace(MovieScene3DTransformTrack=object,FrameNumber=lambda n:n,
        MovieSceneTimeUnit=SimpleNamespace(DISPLAY_RATE='display'),
        MovieSceneKeyInterpolation=SimpleNamespace(LINEAR='linear'))
    report=sequence.add_ground_height_track(unreal,binding,actor,ground_rows(),2)
    assert [c.default for c in channels]==[10.,20.,100.,3.,5.,40.,1.,2.,3.]
    assert [len(c.keys) for c in channels]==[0,0,3,0,0,0,0,0,0]
    assert [(f,z) for f,z,_ in channels[2].keys]==[(0,100.),(1,104.),(2,101.)]
    assert all(options['interpolation']=='linear' for _,_,options in channels[2].keys)
    section.set_range.assert_called_once_with(0,3)
    assert report['camera_policy']=='unchanged' and report['actor_z_key_count']==3


@pytest.mark.parametrize('corruption',['missing_endpoint','wrong_start','wrong_time','nan_time','nan_height','wrong_frame'])
def test_ground_height_curve_rejects_incomplete_or_changed_baseline(corruption):
    rows=ground_rows()
    if corruption=='missing_endpoint':rows.pop()
    elif corruption=='wrong_start':rows[0]['actor_z_cm']=99.
    elif corruption=='wrong_time':rows[1]['t']=.5
    elif corruption=='nan_time':rows[1]['t']=float('nan')
    elif corruption=='nan_height':rows[1]['actor_z_cm']=float('nan')
    else:rows[1]['frame']=2
    with pytest.raises(ValueError):sequence.ground_height_key_rows(rows,2,100.)
