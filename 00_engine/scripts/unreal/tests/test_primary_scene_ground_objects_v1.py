"""Offline routing checks; no Unreal editor execution."""
import importlib.util
from pathlib import Path
import sys
import types

S=Path(__file__).resolve().parents[1]


def make_modules(monkeypatch):
    unreal=types.ModuleType('unreal')
    unreal.CollisionChannel=types.SimpleNamespace(ECC_WORLD_STATIC='static',ECC_WORLD_DYNAMIC='dynamic',ECC_VISIBILITY='visibility')
    unreal.PrimitiveComponent=object;unreal.EditorActorSubsystem=object
    monkeypatch.setitem(sys.modules,'unreal',unreal)
    offline=types.ModuleType('scene_site_survey_v1');offline.RUN=Path('unused')
    offline.POLICY={'ground_min_normal_z':.94,'ground_probe_radius_cm':80,'ground_flat_tolerance_cm':3}
    offline.score_screen=lambda row:-sum(row['counts'].values())
    monkeypatch.setitem(sys.modules,offline.__name__,offline)
    geo=types.ModuleType('scene_site_review_geometry_v1');geo.transform_point=lambda value,p,yaw:value
    monkeypatch.setitem(sys.modules,geo.__name__,geo)
    def load(stem,name):
        spec=importlib.util.spec_from_file_location(name,S/(stem+'.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    original=load('ue_scene_site_review_v1','original_worker')
    monkeypatch.setitem(sys.modules,'ue_scene_site_review_v1',original)
    survey=load('ue_all_primary_scene_survey_v1','original_survey')
    monkeypatch.setitem(sys.modules,'ue_all_primary_scene_survey_v1',survey)
    adapter=load('ue_primary_scene_ground_objects_v1','adapter_test')
    private=load('ue_scene_site_review_v1','private_worker')
    ps=load('ue_all_primary_scene_survey_v1','private_survey');ps.worker=private
    return adapter,ps,private,original,unreal


def exhaust(generator):
    while True:
        try:next(generator)
        except StopIteration as done:return done.value


def test_exact_three_ground_domains_leave_camera_body_and_public_worker_unchanged(monkeypatch):
    adapter,ps,worker,original,_=make_modules(monkeypatch)
    original_ids=(original.ray,original.sphere,original.check_action_sample,original.check_shot_sample)
    shot_function=worker.check_shot_sample
    counts={'ground':0,'visibility':0,'sphere':0}
    domains=[]
    def ground(a,b,domain):
        counts['ground']+=1
        domains.append(domain)
        return {'point':[a[0],a[1],0],'normal':[0,0,1],'actor':'floor'}
    def visibility(*args):counts['visibility']+=1;return None
    def sphere(*args):counts['sphere']+=1;return None
    ps._ground_object_ray=ground;ps.ray=visibility;ps.sphere=sphere
    worker._ground_object_ray=ground;worker.ray=visibility;worker.sphere=sphere
    adapter._adapt_ground_function(ps,'_ground_candidate')
    adapter._adapt_ground_function(ps,'_screen',screen=True)
    adapter._adapt_ground_function(worker,'check_action_sample')
    point=adapter._load('ue_primary_scene_explicit_point_v1')
    adapter._adapt_point_entry(point)
    assert 'Object-type vertical ground trace' in repr(point.start.__code__.co_consts)
    result=exhaust(ps._ground_candidate({'position':[0,0,0]},{}))
    assert result['eligible'] and counts=={'ground':10,'visibility':0,'sphere':1}
    assert len(result['findings'])==0
    result=exhaust(ps._screen([0,0,0],0,{'proxies':{
        'ground':[{'position':[0,0,0]}],
        'body':[{'a':[0,0,20],'b':[0,0,100]}],
        'cameras':[{'position':[0,-300,100],'look_at':[0,0,100]}]}}))
    assert result['query_count']==4 and counts=={'ground':11,'visibility':1,'sphere':3}
    job={'site_z':0,'seen':set(),'issues':[],'unmeasured_visibility_samples':0}
    sample={'t':0,'ground_probes':[{'position':[0,0,0],'baseline_ground_z_cm':0}],
        'bones':{'a':[0,0,20],'b':[0,0,100]}}
    worker.check_action_sample(job,{'motion_id':'M','body_segments':[('a','b')]},sample)
    assert counts=={'ground':12,'visibility':1,'sphere':4} and not job['issues']
    worker.visible_targets=lambda *args:[{'bone':'head','position':[0,0,100]}]
    row={'t':0,'position':[0,-300,100],'frame_index':0}
    shot={'motion_id':'M','shot_id':'S','camera_id':'front_full','orientation':'portrait','samples':[row]}
    job['action_samples']={'M':{0:sample}}
    worker.check_shot_sample(job,shot,row,0)
    assert counts=={'ground':12,'visibility':2,'sphere':5}
    assert domains==['anchor']+['nine_probes']*9+['screen_ground','full_ground']
    assert worker.check_shot_sample is shot_function
    assert original_ids==(original.ray,original.sphere,original.check_action_sample,original.check_shot_sample)


def test_named_ground_actual_object_type_gates_dynamic_and_rejects_pawn(monkeypatch):
    adapter,_,_,_,unreal=make_modules(monkeypatch)
    component=types.SimpleNamespace(get_path_name=lambda:'/Map.Actor.Component',
        get_editor_property=lambda key:'/Mesh',get_collision_object_type=lambda:'static',
        get_class=lambda:types.SimpleNamespace(get_name=lambda:'SplineMeshComponent'),
        get_collision_enabled=lambda:'QUERY_AND_PHYSICS',
        get_collision_response_to_channel=lambda channel:'IGNORE')
    actor=types.SimpleNamespace(get_actor_label=lambda:'Road',get_path_name=lambda:'/Map.Actor',
        get_components_by_class=lambda cls:[component])
    unreal.get_editor_subsystem=lambda cls:types.SimpleNamespace(get_all_level_actors=lambda:[actor])
    assert adapter._targets('Road','/Mesh',None)[0]['is_world_dynamic'] is False
    component.get_collision_object_type=lambda:'dynamic'
    assert adapter._targets(None,None,'/Map.Actor.Component')[0]['is_world_dynamic'] is True
    component.get_collision_object_type=lambda:'pawn'
    try:adapter._targets('Road','/Mesh',None)
    except ValueError as error:assert 'no Pawn/Vehicle' in str(error)
    else:raise AssertionError('Pawn ground must not enable a broad object query')
