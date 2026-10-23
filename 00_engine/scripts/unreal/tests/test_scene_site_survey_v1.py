"""Bounded search and exclusion evidence; no Unreal dependency."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import scene_site_survey_v1 as s


def test_spatial_budget_keeps_mandatory_camera_families_and_extrema():
    points=[[0,0,0],[100,0,0],[0,100,0],[100,100,0]]
    chosen=s.farthest_indices(points,3,[0,1])
    assert chosen[:2]==[0,1]
    assert len(chosen)==3 and any(i in chosen for i in (2,3))
    assert s.farthest_indices([],10)==[]


def test_anchor_search_retains_explicit_starts_and_spreads_large_ground():
    actors=[{'label':'PlayerStart','class':'PlayerStart','location':[0,0,100]},
        {'label':'Floor','class':'StaticMeshActor','location':[0,0,0],
            'bounds_origin':[0,0,-10],'bounds_extent':[2000,2000,10]},
        {'label':'SkySphere','class':'StaticMeshActor','location':[0,0,0],
            'bounds_origin':[0,0,0],'bounds_extent':[99999,99999,10]}]
    points=s.anchor_seeds(actors,extra_seeds=[[200,0,0]],limit=5)
    assert len(points)<=5
    assert any(r['kind']=='player_start' for r in points)
    assert any(r['kind']=='coordinator_anchor' for r in points)
    assert not any(r['source_actor']=='SkySphere' for r in points)
    assert any(abs(r['position'][0])>500 or abs(r['position'][1])>500 for r in points)


def test_action_ground_failure_affects_all_its_cameras_and_aspects_only():
    local={'shots':[{'shot_id':f'{m}_{c}_{o}','motion_id':m,'camera_id':c,'orientation':o}
        for m in ('walk','idle') for c in ('front','side') for o in ('portrait','landscape')]}
    issues=[{'kind':'ground_height','action_id':'walk','camera_id':'front','aspect':'portrait'},
        {'kind':'occlusion','action_id':'idle','camera_id':'side','aspect':'landscape'}]
    results=s.combination_assessment(local,issues)
    assert sum(r['assessment']=='suspected_conflict' for r in results)==5
    assert all(not r['confirmed_excluded'] for r in results)


def test_clear_trace_count_is_never_a_confirmed_exclusion():
    rows=[{'shot_id':'a','assessment':'suspected_conflict','confirmed_excluded':False}]
    with pytest.raises(ValueError):s.confirmed_exclusions(rows,[{'shot_id':'a','decision':'exclude'}])
    confirmed=s.confirmed_exclusions(rows,[{'shot_id':'a','decision':'exclude',
        'reviewer':'coordinator','evidence':['render_frame.png']}])
    assert confirmed[0]['confirmed_excluded'] is True


def test_screen_score_prioritizes_compatible_body_and_ground_before_camera():
    ground_bad=s.score_screen({'counts':{'ground_missing':1}})
    camera_bad=s.score_screen({'counts':{'camera_collision':10}})
    assert ground_bad<camera_bad< s.score_screen({'counts':{}})


def test_runtime_full_matrix_generator_checks_all1260_without_ue(monkeypatch):
    import copy
    import importlib.util
    import types
    folder=Path(__file__).resolve().parents[1]
    monkeypatch.setitem(sys.modules,'unreal',types.SimpleNamespace())
    spec=importlib.util.spec_from_file_location('survey_test_worker',folder/'ue_scene_site_review_v1.py')
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    monkeypatch.setitem(sys.modules,'ue_scene_site_review_v1',worker)
    spec=importlib.util.spec_from_file_location('survey_test_runtime',folder/'ue_all_primary_scene_survey_v1.py')
    runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    ground=lambda a,b: {'point':[a[0],a[1],0.],'normal':[0.,0.,1.],'actor':'floor'} if a[:2]==b[:2] else None
    monkeypatch.setattr(runtime,'ray',ground)
    monkeypatch.setattr(runtime,'sphere',lambda *args:None)
    actions=[];shots=[]
    for m in range(30):
        mid='motion_'+str(m)
        sample={'frame_index':0,'t':0.,'bones':{'root':[0.,0.,0.],'spine_02':[0.,0.,100.]},
            'ground_probes':[{'position':[0.,0.,0.],'baseline_ground_z_cm':0.}]}
        box={'minimum_xyz_cm':[0.,0.,0.],'maximum_xyz_cm':[0.,0.,100.]}
        actions.append({'motion_id':mid,'samples':[sample],'root_route':[],'activity_bounds':copy.deepcopy(box),
            'root_bounds':copy.deepcopy(box),'body_segments':[],'baseline_ground_z_cm':0.})
        for c in range(21):
            for orientation in ('portrait','landscape'):
                shots.append({'shot_id':f'{mid}_{c}_{orientation}','motion_id':mid,'camera_id':'camera_'+str(c),
                    'orientation':orientation,'width':720 if orientation=='portrait' else 1280,
                    'height':1280 if orientation=='portrait' else 720,
                    'samples':[{'frame_index':0,'t':0.,'position':[0.,-100.,100.],'look_at':[0.,0.,100.],
                        'rotation_pitch_yaw_roll':[0.,90.,0.],'horizontal_fov_degrees':35.}],
                    'camera_bounds':copy.deepcopy(box)})
    local={'actions':actions,'shots':shots,'placement':{'location_xyz_cm':[0.,0.,0.],'yaw_degrees':0.},'input_fingerprint':'test'}
    job={'local':local,'full_attempts':[]}
    iterator=runtime._full({'position':[10.,20.,0.],'yaw':0.},job)
    while True:
        try:next(iterator)
        except StopIteration as stop:result=stop.value;break
    assert result['summary']['no_proxy_conflict_combinations']==1260
    assert result['summary']['sample_items_completed']==1290
    assert result['summary']['full_matrix_sampled'] is True
    assert result['confirmed_exclusions']==[]
