import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import camera_complete_angles_planner_v1 as p


def test_full_and_upper_cover_exact_five_angles_and_head_is_front_only():
    presets=p.presets()
    assert len(presets)==21
    for framing in ['full','upper']:
        directional=[x for x in presets if x['kind']=='follow' and x['elevation']==0 and x['start']==framing]
        assert sorted(x['azimuth'] for x in directional)==[0,45,90,135,180]
    head=[x for x in presets if x['start']=='head']
    assert len(head)==1 and head[0]['azimuth']==0


def test_complete_matrix_has_147_unique_combinations_and_retimed_curious_source():
    assert len(p.ACTIONS)==7
    assert len({(a[0],x['id']) for a in p.ACTIONS for x in p.presets()})==147
    assert next(a for a in p.ACTIONS if a[0]=='curious')[2]==32
    assert len({a[2] for a in p.ACTIONS})==7


def test_existing_orbits_and_dollies_preserve_stable_follow_contract():
    new={x['id']:x for x in p.presets()}
    for old in p.stable.presets():
        if old['kind']!='follow':assert new[old['id']]==old
    assert {x['orbit'] for x in new.values() if x['kind']=='orbit'}=={120,360}
    assert sum(x['kind'].startswith('dolly') for x in new.values())==6
