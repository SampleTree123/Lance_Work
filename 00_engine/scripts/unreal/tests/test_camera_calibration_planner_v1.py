"""Common initial pose, explicit safety exceptions, and complete-window clocks."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import camera_calibration_planner_v1 as p
from test_motion_portrait_camera_planner_v1 import frames


def config(distance=700, exceptions=False):
    return {'horizontal_fov_degrees':35,
            'full_body_exception_policy':'explicit_safety_expansion' if exceptions else 'diagnose_only',
            'orientations':{o:{f:{'distance_cm':distance,'initial_target_height_cm':z}
                               for f,z in [('full',85),('upper',130),('head',155)]}
                            for o in ['landscape','portrait']}}


def inputs(duration=3,travel=0,sway=0):
    c={'clip_id':'example','animation_path':'/Game/Example','frames':frames(duration,30,travel,sway)}
    d={'window_start_seconds':0,'body_play_rate':1,'output_duration_seconds':duration,'motion_id':'EXAMPLE','label':'example'}
    return c,d


def preset(name='front_full'):
    return next(x for x in p.prior.library.presets() if x['id']==name)


def test_same_reference_keeps_initial_relative_position_and_fov():
    shots=[]
    for travel,sway in [(0,0),(30,8)]:
        c,d=inputs(travel=travel,sway=sway)
        shots.append(p.make_shot(c,d,'female',preset(),'landscape',config()))
    assert shots[0]['frames'][0]==shots[1]['frames'][0]
    assert shots[0]['endpoint_distances_cm']==shots[1]['endpoint_distances_cm']==[700,700]
    assert shots[1]['frames'][-1]['look_at'][0]>shots[0]['frames'][-1]['look_at'][0]+40


def test_actual_full_body_excursion_expands_explicit_exception_without_cropping():
    c,d=inputs()
    raw=p.make_shot(c,d,'female',preset(),'portrait',config(100))
    fixed=p.make_shot(c,d,'female',preset(),'portrait',config(100,True))
    assert raw['status']=='framing_exception'
    assert fixed['scale_exception']['resolved_full_body_excursion']
    assert fixed['endpoint_distances_cm'][0]>100
    assert fixed['framing_diagnostics']['full']['outside_frame_count']==0
    assert fixed['human_acceptance']=='pending'


def test_head_excursion_does_not_silently_turn_closeup_into_full_body():
    c,d=inputs(travel=10)
    shot=p.make_shot(c,d,'female',preset('front_head'),'portrait',config(50,True))
    assert shot['endpoint_distances_cm']==[50,50]
    assert shot['scale_exception'] is None
    assert shot['framing_diagnostics']['head']['outside_frame_count']>0


def test_default_keeps_whole_window_and_explicit_limit_is_labelled():
    c,d=inputs(12)
    full=p.make_shot(c,d,'female',preset(),'landscape',config())
    short=p.make_shot(c,d,'female',preset(),'landscape',config(),limit=10)
    assert full['duration_seconds']==12 and full['frame_count']==360
    assert full['window_scope']=='complete_selected_window'
    assert short['duration_seconds']==10 and short['window_scope']=='explicit_limited_window'


def test_source_window_overrun_rejected_instead_of_endpoint_freeze():
    c,d=inputs(3);d['output_duration_seconds']=5
    with pytest.raises(ValueError,match='exceeds sampled'):
        p.make_shot(c,d,'female',preset(),'portrait',config())


def test_source_clock_six_seconds_to_ten_preserved():
    c,d=inputs(6,travel=30);d.update(body_play_rate=.6,output_duration_seconds=10)
    shot=p.make_shot(c,d,'female',preset(),'landscape',config())
    assert shot['source_end_seconds']==6
    assert shot['duration_seconds']==10
    assert shot['source_body_play_rate']==.6


def test_inactive_full_region_during_upper_dolly_does_not_fail_depth(monkeypatch):
    uv=np.array([[[.2,.2],[.8,.8]],[[.1,.1],[.9,.9]]])
    depth=np.array([[100.,110.],[-3.,90.]])
    monkeypatch.setattr(p,'projections',lambda *a:(uv,depth))
    result=p.diagnostics([{'t':0.},{'t':1.}],[],'full',1.,35.,np.array([True,False]))
    assert result['min_depth_cm']==100
    assert result['inactive_min_depth_cm']==-3
    with pytest.raises(ValueError,match='behind camera'):
        p.diagnostics([{'t':0.},{'t':1.}],[],'full',1.,35.,np.array([True,True]))


def test_closeup_depth_safety_moves_only_minimum_and_records_exception():
    c,d=inputs();cfg=config(12);cfg['closeup_minimum_depth_cm']=15
    shot=p.make_shot(c,d,'female',preset('front_head'),'portrait',cfg)
    proof=shot['closeup_depth_exception']
    assert proof['baseline_min_depth_cm']<15
    assert proof['adjusted_min_depth_cm']>=15
    assert 12<shot['endpoint_distances_cm'][0]<40
    assert proof['baseline_endpoint_distances_cm']==[12,12]
    assert proof['adjusted_endpoint_distances_cm']==shot['endpoint_distances_cm']
    assert shot['scale_exception'] is None
