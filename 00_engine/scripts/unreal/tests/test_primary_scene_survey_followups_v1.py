"""Separate follow-up helpers, with Unreal replaced by read-only stubs."""
from pathlib import Path
import importlib.util
import sys
import types
import pytest
S=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(S))
import scene_site_terrain_probe_v1 as terrain


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_terrain_grid_stays_inside_actual_landscape_and_ignores_distant_meshes():
    report={'actor_inventory':[{'label':'Landscape1','class':'Landscape','bounds_origin':[0.,0.,0.],
        'bounds_extent':[10000.,10000.,4000.]},{'label':'Player Start','class':'PlayerStart','location':[100.,100.,0.]},
        {'label':'dunes_decorative','class':'StaticMeshActor','bounds_origin':[1000000.,1000000.,0.],
         'bounds_extent':[10000.,10000.,1000.]}]}
    points=terrain.grid(report)
    assert 225<=len(points)<=306
    assert all(abs(v)<10000 for p in points for v in p['xy'])
    assert {p['landscape_actor'] for p in points}=={'Landscape1'}
    assert all(p['trace_top_z_cm']==4500 and p['trace_bottom_z_cm']==-4500 for p in points)


@pytest.mark.parametrize('slope,expected',[(.02,True),(.05,False)])
def test_runtime_terrain_probe_keeps_existing_three_cm_flatness(monkeypatch,slope,expected):
    fake=types.SimpleNamespace(Vector=lambda *v:v,SystemLibrary=types.SimpleNamespace(sphere_trace_single=lambda *a:None),
        TraceTypeQuery=types.SimpleNamespace(ECC_VISIBILITY=0),DrawDebugTrace=types.SimpleNamespace(NONE=0))
    monkeypatch.setitem(sys.modules,'unreal',fake)
    monkeypatch.setitem(sys.modules,'ue_scene_site_review_v1',types.SimpleNamespace(hit_data=lambda v:v,world=lambda:None))
    runtime=load('test_terrain_runtime',S/'ue_scene_terrain_probe_v1.py')
    monkeypatch.setattr(runtime,'ray',lambda a,b,job:{'point':[a[0],a[1],a[0]*slope],
        'normal':[0.,0.,1.],'actor':'Landscape1'})
    iterator=runtime._probe({'xy':[0.,0.],'trace_top_z_cm':4500.,'trace_bottom_z_cm':-4500.,'landscape_actor':'Landscape1'},{'ignored':[]})
    while True:
        try:next(iterator)
        except StopIteration as stop:result=stop.value;break
    assert result['eligible'] is expected
    assert result['height_error_cm']==pytest.approx(80*slope)


def test_retry_nonzero_requires_explicit_flag_and_reason(monkeypatch):
    monkeypatch.setitem(sys.modules,'ue_primary_scene_candidate_retry_v1',types.SimpleNamespace())
    monkeypatch.setitem(sys.modules,'ue_all_primary_scene_survey_v1',types.SimpleNamespace())
    runtime=load('test_retry_v2',S/'ue_primary_scene_candidate_retry_v2.py')
    report={'screen_candidates':[{'position':[1.,2.,3.],'yaw':180.,'score':-4.,'findings':[{'kind':'camera_collision'}]}]}
    with pytest.raises(ValueError):runtime.select_candidate(report,[1,2,3],180)
    with pytest.raises(ValueError):runtime.select_candidate(report,[1,2,3],180,allow_nonzero_screen=True)
    row=runtime.select_candidate(report,[1,2,3],180,allow_nonzero_screen=True,justification='Compare another measured point')
    assert row['score']==-4 and row['findings']==report['screen_candidates'][0]['findings']


def test_signature_differences_identifies_exact_component_and_numeric_delta(monkeypatch):
    monkeypatch.setitem(sys.modules,'unreal',types.SimpleNamespace())
    monkeypatch.setitem(sys.modules,'ue_scene_site_review_v1',types.SimpleNamespace())
    runtime=load('test_signature_diff',S/'ue_scene_signature_diff_probe_v1.py')
    first={'actors':[{'path':'actorA','location':[0,0,0],'components':[{'path':'particle','bounds':1.}]}],'dirty_packages':[]}
    after={'actors':[{'path':'actorA','location':[0,0,0],'components':[{'path':'particle','bounds':2.}]}],'dirty_packages':[]}
    diff=runtime.differences(first,after)
    assert len(diff)==1 and diff[0]['actor']=='actorA'
    assert diff[0]['field']=='component/particle/bounds' and diff[0]['absolute_delta']==1.
