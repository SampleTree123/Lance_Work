import importlib.util,math
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('planner',Path(__file__).parents[1]/'camera_motion_planner_v1.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def clip():
 base={'root':[0,0,0],'pelvis':[0,0,90],'head':[0,0,160],'neck_01':[0,0,145],
       'upperarm_l':[20,0,135],'upperarm_r':[-20,0,135],'hand_l':[35,0,85],'hand_r':[-35,0,85],
       'foot_l':[10,0,8],'foot_r':[-10,0,8],'calf_l':[10,0,45],'calf_r':[-10,0,45],
       'thigh_l':[10,0,80],'thigh_r':[-10,0,80],'spine_01':[0,0,105],'spine_02':[0,0,120],
       'ball_l':[10,10,5],'ball_r':[-10,10,5]}
 frames=[]
 for i in range(101):
  t=i/10;angle=math.radians(12*t)
  frames.append({'t':t,'bones':{key:[v[0]*math.cos(angle)-v[1]*math.sin(angle),v[0]*math.sin(angle)+v[1]*math.cos(angle),v[2]] for key,v in base.items()}})
 return {'clip_id':'turn','sex':'female','action_index':8,'animation_path':'/test','duration_seconds':10,'frames':frames}

def test_heading_unwrap_through_180():
 value=p.follow_heading(clip()['frames'],10,90)
 assert value['raw_yaw_degrees'][0]==pytest.approx(90)
 assert value['raw_yaw_degrees'][-1]==pytest.approx(210)
 assert max(abs(b-a) for a,b in zip(value['smoothed_yaw_degrees'],value['smoothed_yaw_degrees'][1:]))<2
 assert value['fallback_frame_count']==0

def test_gait_noise_is_attenuated():
 frames=clip()['frames']
 for i,frame in enumerate(frames):
  angle=math.radians(10*math.sin(2*math.pi*2*frame['t']))
  for name in ('thigh_l','thigh_r'):
   v=frame['bones'][name];frame['bones'][name]=[v[0]*math.cos(angle)-v[1]*math.sin(angle),v[0]*math.sin(angle)+v[1]*math.cos(angle),v[2]]
 result=p.follow_heading(frames,10,90)
 raw=[abs(a-(90+12*f['t'])) for a,f in zip(result['raw_yaw_degrees'][10:-10],frames[10:-10])]
 smooth=[abs(a-(90+12*f['t'])) for a,f in zip(result['smoothed_yaw_degrees'][10:-10],frames[10:-10])]
 assert sum(smooth)/len(smooth)<sum(raw)/len(raw)*.2

def test_ambiguous_calibration_fails_without_guess():
 with pytest.raises(ValueError,match='ambiguous'):p.follow_heading(clip()['frames'],10,0)

def test_degenerate_hip_uses_calibrated_shoulders():
 frames=clip()['frames'];frames[50]['bones']['thigh_l']=frames[50]['bones']['thigh_r']
 result=p.follow_heading(frames,10,90)
 assert result['fallback_frame_count']==1
 assert result['raw_yaw_degrees'][50]==pytest.approx(150)

@pytest.mark.parametrize('shot,offset',[('follow_front',0),('follow_side',90),('follow_rear',180)])
def test_follow_relative_heading_is_preserved(shot,offset):
 result=p.plan_shot(clip(),shot,10,fps=2,yaw_offset=90,follow_mode='pelvis_heading')
 assert result['status']=='geometry_pass'
 for camera,heading in zip(result['frames'],result['follow_heading']['smoothed_yaw_degrees']):
  d=p.sub(camera['position'],camera['look_at']);yaw=math.degrees(math.atan2(d[1],d[0]))
  assert ((yaw-heading-offset+180)%360-180)==pytest.approx(0,abs=1e-6)

def test_default_remains_fixed_world():
 result=p.plan_shot(clip(),'follow_front',10,fps=2,yaw_offset=90)
 offsets=[p.sub(f['position'],f['look_at']) for f in result['frames']]
 assert all(v==pytest.approx(offsets[0]) for v in offsets)
 assert 'follow_heading' not in result

def test_feet_consensus_does_not_assume_world_y():
 source=clip();frame=source['frames'][75]
 result=p.initial_foot_forward_evidence(frame)
 assert result['yaw_degrees']==pytest.approx(180)
 assert result['consensus_magnitude']==pytest.approx(1)

def test_divergent_initial_feet_fail_calibration():
 frame=clip()['frames'][0]
 frame['bones']['ball_r']=p.add(frame['bones']['foot_r'],[0,-10,0])
 with pytest.raises(ValueError,match='feet disagree'):p.initial_foot_forward_evidence(frame)

def test_explicit_slow_follow_has_bounded_smooth_turn():
 result=p.plan_shot(clip(),'follow_front',10,fps=2,yaw_offset=0,follow_mode='pelvis_heading',follow_sigma_seconds=1.5,follow_calibration='feet_consensus')
 assert result['status']=='geometry_pass'
 assert result['follow_heading']['sigma_seconds']==1.5
 assert result['follow_heading']['initial_facing_evidence']['yaw_degrees']==pytest.approx(90)
 assert result['path_metrics']['max_view_angular_speed_degrees_per_second']<13
