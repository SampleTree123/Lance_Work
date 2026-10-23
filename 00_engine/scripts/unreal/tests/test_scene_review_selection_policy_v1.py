import copy
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import scene_review_selection_policy_v1 as policy


def sample():
    actions=[{'motion_id':'MOTION_CAND_001'},{'motion_id':'MOTION_CAND_007'}]
    shots=[{'shot_id':'a','motion_id':'MOTION_CAND_001','frames':[{'position':[1,2,3]}]},
           {'shot_id':'b','motion_id':'MOTION_CAND_007','frames':[{'position':[4,5,6]}]}]
    return {'geometry':{'actions':actions,'shots':shots,'input_fingerprint':'old'},
            'catalog':{'actions':actions,'cameras':[{'id':'front'}]},
            'shots':{s['shot_id']:s for s in shots},'frames':{'a':'a-frames','b':'b-frames'}}


def test_retired_motion_removed_from_all_runtime_views_without_source_mutation():
    data=sample();before=copy.deepcopy(data);new=policy.filter_mode(data)
    assert data==before
    assert [r['motion_id'] for r in new['geometry']['actions']]==['MOTION_CAND_001']
    assert new['geometry']['shots']==[before['shots']['a']]
    assert new['catalog']['actions']==[before['geometry']['actions'][0]]
    assert new['shots']=={'a':before['shots']['a']}
    assert new['frames']=={'a':'a-frames'}
    assert new['geometry']['input_fingerprint']!='old'


def test_install_is_idempotent_for_both_modes():
    seen=[]
    runtime=SimpleNamespace(load_mode=lambda mode:(seen.append(mode) or sample()))
    policy.install(runtime);first=runtime.load_mode;policy.install(runtime)
    assert runtime.load_mode is first
    for mode in ['full','production10']:
        assert runtime.load_mode(mode)['selection_policy']['active_actions']==1
    assert seen==['full','production10']


def test_worker_matrix_tracks_active_selection_and_is_idempotent():
    w=SimpleNamespace(catalog=lambda:{'motions':[1]*25,'cameras':[1]*21},
                      live=lambda:{'local':{'shots':[1]*1050}})
    current={'worker':w}
    policy.install_worker(current);first=w.catalog;policy.install_worker(current)
    assert w.catalog is first
    assert w.catalog()['matrix']=={'motions':25,'cameras':21,'aspects':2,'combinations':1050}
