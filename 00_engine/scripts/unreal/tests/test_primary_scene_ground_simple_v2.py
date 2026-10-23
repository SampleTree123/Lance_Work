"""Focused diagnostic gate and private simple-ground routing checks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import types
import pytest
from test_primary_scene_ground_objects_v1 import make_modules

S=Path(__file__).resolve().parents[1]
RUN=S.parents[1]/'outputs/all_primary_scene_sites_20261015_v1'


def wrapper(monkeypatch):
    base,ps,worker,original,u=make_modules(monkeypatch)
    def pin(p):
        p=Path(p).resolve();return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    base.geo.pin=pin;base.offline.read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
    spec=importlib.util.spec_from_file_location('simple_wrapper_test',S/'ue_primary_scene_ground_simple_v2.py')
    simple=importlib.util.module_from_spec(spec);spec.loader.exec_module(simple)
    return simple,base,ps,u,pin


def test_diagnostic_requires_same_xy_exact_target_and_unchanged_pin(monkeypatch):
    simple,_,_,_,pin=wrapper(monkeypatch)
    source=RUN/'kowloon_actual_ground_diagnostic_v1.json'
    data=json.loads(source.read_text(encoding='utf-8'));p=pin(source)
    assert simple._diagnostic(p,[560,-240,0],data['component'])[0]==p
    for position,component in (([561,-240,0],data['component']),([560,-240,0],'/different/ground')):
        with pytest.raises(ValueError):simple._diagnostic(p,position,component)
    with pytest.raises(ValueError):simple._diagnostic(dict(p,sha256='changed'),[560,-240,0],data['component'])


def test_simple_trace_is_private_and_base_complex_query_is_preserved(monkeypatch):
    simple,base,ps,u,pin=wrapper(monkeypatch)
    baseline=pin(simple.BASE)
    private=simple._private_adapter(pin(RUN/'kowloon_actual_ground_diagnostic_v1.json'))
    captured=[]
    u.SystemLibrary=types.SimpleNamespace(line_trace_single_for_objects=lambda *args:captured.append(args[4]))
    u.Vector=lambda *args:args;u.DrawDebugTrace=types.SimpleNamespace(NONE='none')
    job={'ground_object_state':{'trace_count':0,'miss_count':0,'trace_count_by_domain':{'anchor':0}},
        'ground_object_types':['static'],'ignored':[]}
    ps._job=lambda:job;ps.world=lambda:'world';ps.worker.hit_data=lambda raw:None
    private._object_ray(ps,[0,0,1],[0,0,-1],'anchor')
    base._object_ray(ps,[0,0,1],[0,0,-1],'anchor')
    assert captured==[False,True]
    assert pin(simple.BASE)==baseline
    assert private.__file__==simple.__file__
    constants=repr(private.start_point.__code__.co_consts)
    assert 'targeted_object_type_ground_simple_v2' in constants
    assert 'Simple collision proxy ground only' in constants
