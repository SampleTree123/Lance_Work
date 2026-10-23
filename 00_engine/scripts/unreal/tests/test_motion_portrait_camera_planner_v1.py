"""Aspect ratio, source clock and stable-follow regression coverage."""
import json
import math
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import motion_portrait_camera_planner_v1 as p


def frames(duration=12, fps=30, travel=0, sway=0):
    result=[]
    for i in range(round(duration*fps)+1):
        t=i/fps; x=travel*t+sway*math.sin(4*math.pi*t)
        bones={k:[x,0.,90.] for k in p.stable.old.REQUIRED}
        for name,z in [('head',160),('neck_01',140),('foot_l',2),('foot_r',2),('ball_l',2),('ball_r',2)]:bones[name][2]=z
        bones['thigh_l'][1]=-12;bones['thigh_r'][1]=12
        bones['hand_l']=[x,-45,115];bones['hand_r']=[x,45,115]
        result.append({'t':t,'bones':bones})
    return result


def test_six_second_window_slowed_to_ten_uses_source_clock():
    clip={'frames':frames(12,10,travel=30)}
    result=p.resample(clip,0,10,.6)
    assert len(result)==301
    assert result[-1]['t']==10
    assert result[-1]['bones']['pelvis'][0]==pytest.approx(180)


def test_other_window_preserves_actual_duration_and_offset():
    clip={'frames':frames(30,10,travel=30)}
    result=p.resample(clip,5.9,21.3,1)
    assert len(result)==640
    assert result[0]['bones']['pelvis'][0]==pytest.approx(177)
    assert result[-1]['bones']['pelvis'][0]==pytest.approx(816)


def test_portrait_reframes_and_full_body_proxy_still_fits():
    f=frames(3,travel=20);centers=p.stable.centers_for(f)
    preset=next(x for x in p.library.presets() if x['id']=='front_full')
    distances={}
    for label,aspect in [('landscape',1280/720),('portrait',720/1280)]:
        distance=p.fit(f,preset,'full',0,centers,aspect);distances[label]=distance
        uv,depth=p.project(f,p.path(f,preset,[distance,distance],0,centers),'full',aspect)
        assert depth.min()>1
        assert np.abs(uv-.5).max()<.44
    assert distances['portrait']<distances['landscape']*.9


def test_new_path_preserves_sway_suppression_and_major_translation():
    preset=next(x for x in p.library.presets() if x['id']=='front_full')
    for travel in [0,40]:
        f=frames(10,travel=travel,sway=8);centers=p.stable.centers_for(f)
        rows=p.path(f,preset,[650,650],0,centers)
        x=np.array([r['look_at'][0] for r in rows])
        if not travel:assert np.ptp(x)<.1
        else:
            assert x[-1]-x[0]>350
            assert np.abs(np.diff(x[30:-30],2)).max()<.05


def test_build_caps_camera_trials_without_shortening_overviews(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'RUN',tmp_path)
    motion='MOTION_CAND_008'
    (tmp_path/'all_motion_samples_v1.json').write_text(json.dumps({'clips':[{'clip_id':'dance'}]}),encoding='utf-8')
    decisions=tmp_path/'decisions.json'
    decisions.write_text(json.dumps({'actions':[{'motion_id':motion,'window_start_seconds':0,'output_duration_seconds':24,'variants':{'female':{'clip_id':'dance'}}}]}),encoding='utf-8')
    calls=[]
    def record(clip,decision,sex,preset,orientation,group,limit=None):
        calls.append((group,limit));return {'frame_count':round(min(decision['output_duration_seconds'],limit or 1000)*30)}
    monkeypatch.setattr(p,'shot',record)
    p.build(decisions)
    assert calls[0]==('motions',None)
    assert len(calls)==43
    assert all(group=='portrait' and limit==10 for group,limit in calls[1:])
