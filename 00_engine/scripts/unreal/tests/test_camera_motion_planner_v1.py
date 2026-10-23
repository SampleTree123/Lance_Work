import copy
import importlib.util
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('planner',Path(__file__).parents[1]/'camera_motion_planner_v1.py')
p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

def clip(duration=10, travel=0):
    positions={'root':[0,0,0],'pelvis':[0,0,90],'head':[0,0,160],'neck_01':[0,0,145],
               'upperarm_l':[0,-20,135],'upperarm_r':[0,20,135],'hand_l':[0,-35,85],
               'hand_r':[0,35,85],'foot_l':[0,-10,8],'foot_r':[0,10,8],
               'calf_l':[0,-10,45],'calf_r':[0,10,45],'thigh_l':[0,-10,80],
               'thigh_r':[0,10,80],'spine_01':[0,0,105],'spine_02':[0,0,120],
               'ball_l':[10,-10,5],'ball_r':[10,10,5]}
    return {'clip_id':'test','sex':'female','action_index':2,'animation_path':'/test',
            'duration_seconds':duration,'frames':[{'t':i/10,'bones':{k:[v[0]+travel*i/(duration*10),v[1],v[2]] for k,v in positions.items()}} for i in range(round(duration*10)+1)]}

def test_projection_axes_and_aspect():
    cam=p.camera_row(0,[0,0,0],[100,0,0],90)
    assert p.project([100,0,0],cam,2)==pytest.approx([.5,.5,100])
    assert p.project([100,100,0],cam,2)[0]==pytest.approx(1)
    assert p.project([100,0,50],cam,2)[1]==pytest.approx(0)
    assert p.project([-1,0,0],cam,2) is None

@pytest.mark.parametrize('duration',[10,12,15])
def test_unified_range_and_exact_end_exclusive_frames(duration):
    result=p.plan_shot(clip(duration),'static_front',duration,fps=2)
    assert result['frame_count']==2*duration
    assert result['frames'][0]['t']==0
    assert result['frames'][-1]['t']==duration-.5
    assert result['endpoint_validation_frame']['t']==duration
    assert result['status']=='geometry_pass'

def test_static_never_tracks_and_follow_moves():
    sample=clip(travel=120)
    fixed=p.plan_shot(sample,'static_front',10,fps=2)
    assert len({tuple(f['position']) for f in fixed['frames']})==1
    assert len({tuple(f['look_at']) for f in fixed['frames']})==1
    follow=p.plan_shot(sample,'follow_side',10,fps=2)
    assert follow['frames'][-1]['position'][0]>follow['frames'][0]['position'][0]+80

def test_zoom_is_stationary_dolly_focal_length_is_constant():
    sample=clip()
    zoom=p.plan_shot(sample,'zoom_in',10,fps=2)
    assert len({tuple(f['position']) for f in zoom['frames']})==1
    assert zoom['frames'][0]['horizontal_fov_degrees']>zoom['frames'][-1]['horizontal_fov_degrees']
    dolly=p.plan_shot(sample,'dolly_in',10,fps=2)
    assert len({f['horizontal_fov_degrees'] for f in dolly['frames']})==1
    assert dolly['frames'][0]['position']!=dolly['frames'][-1]['position']

def test_pan_position_fixed_rotation_changes():
    result=p.plan_shot(clip(travel=100),'pan',10,fps=2)
    assert len({tuple(f['position']) for f in result['frames']})==1
    assert result['frames'][0]['rotation_pitch_yaw_roll']!=result['frames'][-1]['rotation_pitch_yaw_roll']

@pytest.mark.parametrize('shot',['static_head','static_upper','static_wide'])
def test_semantic_framing(shot):
    result=p.plan_shot(clip(),shot,10,fps=2)
    assert result['status']=='geometry_pass'
    assert result['quality']['excluded_feet_visible_times']==[]

def test_extreme_travel_static_closeup_rejected_without_widening_label():
    result=p.plan_shot(clip(travel=1600),'static_head',10,fps=2)
    assert result['status']=='unsuitable'
    assert result['framing']=='head'

@pytest.mark.parametrize('mutator',[lambda c:c.update(duration_seconds=9),lambda c:c['frames'].pop(),lambda c:c['frames'][1].update(t=0),lambda c:c['frames'][0]['bones'].pop('head'),lambda c:c['frames'][0]['bones']['root'].__setitem__(0,float('nan'))])
def test_invalid_samples_fail(mutator):
    sample=clip(); mutator(sample)
    with pytest.raises(ValueError): p.plan_shot(sample,'static_front',10,fps=2)

def test_deterministic_paths_and_input_unchanged():
    sample=clip(); before=copy.deepcopy(sample)
    first=p.plan_shot(sample,'orbit_120',10,fps=2)
    second=p.plan_shot(sample,'orbit_120',10,fps=2)
    assert first['trajectory_sha256']==second['trajectory_sha256']
    assert sample==before

def test_short_body_not_stretched_or_looped():
    sample=clip(12)
    with pytest.raises(ValueError,match='shorter'): p.plan_shot(sample,'static_front',15,fps=2)

def test_exact_30fps_frame_count():
    frames=p.resample(clip(10),10,30)
    assert len(frames)==301
    assert len(frames[:-1])==300

def test_smooth_transition_end_velocities():
    assert p.ease(0)==0 and p.ease(1)==1
    assert p.ease(.001)<.00001
    assert 1-p.ease(.999)<.00001

def test_bending_does_not_turn_full_body_into_wide():
    sample=clip()
    for frame in sample['frames'][50:]:
        for name in ('head','neck_01','upperarm_l','upperarm_r','spine_01','spine_02'):
            frame['bones'][name][2]-=55
    result=p.plan_shot(sample,'static_front',10,fps=2)
    assert result['status']=='geometry_pass'
    assert result['quality']['min_height_fraction']<.55
    assert result['quality']['min_camera_scale_fraction']>.55

def test_camera_below_floor_rejected():
    sample=clip()
    for frame in sample['frames']:
        for position in frame['bones'].values(): position[2]-=200
    result=p.plan_shot(sample,'static_front',10,fps=2)
    assert result['status']=='unsuitable'
    assert result['quality']['camera_below_pilot_floor_times']

def test_low_angle_is_above_ground_and_still_fixed():
    result=p.plan_shot(clip(),'static_low',10,fps=2)
    assert result['status']=='geometry_pass'
    assert result['path_metrics']['min_camera_z_cm']>=25
    assert len({tuple(f['position']) for f in result['frames']})==1
    assert result['frames'][0]['rotation_pitch_yaw_roll'][0]>0
