import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_camera_library_expansion_v1 import camera, legacy_adapter, proposals
from camera_composable_planner_v1 import trajectory

def frames():
    # A translating body with well-defined face/feet landmarks.
    rows=[]
    for t in [0,5,10]:
        bones={k:[t*10,0,90] for k in ['root','pelvis','head','neck_01','upperarm_l','upperarm_r','hand_l','hand_r','foot_l','foot_r','calf_l','calf_r','thigh_l','thigh_r','spine_01','spine_02','ball_l','ball_r']}
        bones['head'][2]=165; bones['neck_01'][2]=145
        for k in ['foot_l','foot_r','ball_l','ball_r']: bones[k][2]=5
        rows.append({'t':t,'bones':bones})
    return rows

def test_no_silent_legacy_substitution():
    assert legacy_adapter(camera(35,25,movement='follow'))['status']=='requires_composable_planner'
    assert legacy_adapter(camera(framing='upper',movement='follow'))['status']=='requires_composable_planner'
    assert legacy_adapter(camera(90))['shot_type']=='static_side'

def test_dolly_moves_position_without_zoom():
    rows=trajectory(frames(),camera(movement='dolly_in',end='upper'),[650,360],90)
    assert rows[0]['position']!=rows[-1]['position']
    assert {r['horizontal_fov_degrees'] for r in rows}=={35}

def test_fixed_pan_and_orbit_have_distinct_position_semantics():
    f=frames()
    pan=trajectory(f,camera(35,movement='pan'),[650,650],90)
    orbit=trajectory(f,camera(35,movement='orbit',orbit=60),[650,650],90)
    assert all(r['position']==pan[0]['position'] for r in pan)
    assert orbit[0]['position']!=orbit[-1]['position']

def test_prioritized_candidates_cover_all_seven_actions_without_whitelisting():
    assert len(proposals())==16
    assert len({x[0] for x in proposals()})==7
