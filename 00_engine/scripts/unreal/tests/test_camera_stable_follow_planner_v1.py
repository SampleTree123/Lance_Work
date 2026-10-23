import math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import camera_stable_follow_planner_v1 as p


def frames():
    out=[]
    for i in range(301):
        t=i/30
        bones={k:[t*25,0,90] for k in p.old.REQUIRED}
        bones['head'][2]=155;bones['neck_01'][2]=140
        for k in ['foot_l','foot_r','ball_l','ball_r']:bones[k][2]=3
        out.append({'t':t,'bones':bones})
    return out


def test_stable_follow_suppresses_local_sway_but_preserves_locomotion():
    t=np.arange(301)/30
    sway=np.column_stack([8*np.sin(t*2*math.pi*2),6*np.cos(t*2*math.pi*2),np.zeros(301)])
    stationary=p.stable_translation(sway,t)
    assert np.ptp(stationary[:,0])<.1
    moving=sway+np.column_stack([t*40,np.zeros(301),np.zeros(301)])
    tracked=p.stable_translation(moving,t)
    assert tracked[-1,0]-tracked[0,0]>350
    assert np.max(np.abs(np.diff(tracked[30:-30,0],2)))<.05


def test_dolly_finishes_at_seven_seconds_while_follow_continues():
    f=frames();preset=next(x for x in p.presets() if x['id']=='dolly_in_front')
    rows=p.trajectory(f,preset,[650,350],90)
    offsets=[p.old.sub(r['position'],r['look_at']) for r in rows]
    assert np.allclose(offsets[210:],offsets[210])
    assert math.isclose(p.old.norm(offsets[210]),350)
    assert rows[210]['position']!=rows[-1]['position']
    assert p.progress(0)==0 and p.progress(7)==1 and p.progress(10)==1


def test_no_heading_pursuit_and_orbit_angle_exact():
    f=frames();c=p.centers_for(f)
    follow=p.trajectory(f,p.presets()[0],[600,600],90,c)
    assert np.allclose([r['rotation_pitch_yaw_roll'] for r in follow],follow[0]['rotation_pitch_yaw_roll'])
    orbit=p.trajectory(f,next(x for x in p.presets() if x['id']=='orbit_360'),[600,600],90,c)
    assert np.allclose(p.old.sub(orbit[0]['position'],orbit[0]['look_at']),p.old.sub(orbit[-1]['position'],orbit[-1]['look_at']))
    assert not np.allclose(p.old.sub(orbit[75]['position'],orbit[75]['look_at']),p.old.sub(orbit[0]['position'],orbit[0]['look_at']))


def test_candidate_matrix_is_exactly_45_with_three_symmetric_dolly_pairs():
    assert len(p.presets())==15
    assert len({(a[0],s['id']) for a in p.ACTIONS for s in p.presets()})==45
    for direction in ['front','side','back']:
        inside=next(s for s in p.presets() if s['id']=='dolly_in_'+direction)
        outside=next(s for s in p.presets() if s['id']=='dolly_out_'+direction)
        assert inside['start']==outside['end']=='full'
        assert inside['end']==outside['start']=='upper'
        assert inside['azimuth']==outside['azimuth']


def test_closeup_tracks_sustained_bending_without_copying_head_jitter():
    f=frames()
    for row in f:
        t=row['t']; offset=30*math.sin(math.pi*t/10)+4*math.sin(2*math.pi*3*t)
        row['bones']['head'][2]-=offset
        row['bones']['neck_01'][2]-=offset
    centers=p.centers_for(f)
    z=centers['head'][:,2]
    assert np.ptp(z)>15
    assert np.max(np.abs(np.diff(z,2)))<.03
    assert np.ptp(centers['full'][:,2])==0
