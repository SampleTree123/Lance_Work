"""Small offline checks of the narrowly scoped dual-signature policy."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types

SOURCE=Path(__file__).resolve().parents[1]/'ue_primary_scene_survey_dual_v3.py'


def fixture(monkeypatch):
    unreal=types.ModuleType('unreal');unreal.PrimitiveComponent=object
    dirty=[]
    unreal.EditorLoadingAndSavingUtils=types.SimpleNamespace(
        get_dirty_map_packages=lambda:dirty,get_dirty_content_packages=lambda:[])
    monkeypatch.setitem(__import__('sys').modules,'unreal',unreal)
    for name in ('ue_all_primary_scene_survey_v1','scene_site_survey_v1',
                 'scene_site_review_geometry_v1','ue_scene_signature_diff_probe_v1'):
        module=types.ModuleType(name);module.RUN=Path('unused')
        monkeypatch.setitem(__import__('sys').modules,name,module)
    spec=importlib.util.spec_from_file_location('dual_offline',SOURCE)
    dual=importlib.util.module_from_spec(spec);spec.loader.exec_module(dual)
    class Component:
        def __init__(self,name,cls='StaticMeshComponent',collision='query',response='block'):
            self.cls=cls;self.record={'path':name,'get_collision_enabled':collision,
                'visibility_response':response,'static_mesh':'mesh','get_materials':['material']}
        def get_class(self):return types.SimpleNamespace(get_name=lambda:self.cls)
    class Actor:
        def __init__(self):self.parts=[Component('floor')];self.location=[0.,0.,0.]
        def get_actor_label(self):return 'Landscape'
        def get_path_name(self):return '/Map.Landscape_1'
        def get_components_by_class(self,cls):return self.parts
        def get_actor_location(self):return self.location
        def get_actor_rotation(self):return [0.,0.,0.]
        def get_actor_scale3d(self):return [1.,1.,1.]
        def get_editor_property(self,key):return False
    actor=Actor()
    worker=types.SimpleNamespace(PREFIX='DM_',actors=lambda:types.SimpleNamespace(get_all_level_actors=lambda:[actor]),
        _component_state=lambda c:copy.deepcopy(c.record),_safe=lambda f:copy.deepcopy(f()))
    def grass(name):return Component(name,'GrassInstancedStaticMeshComponent',
        dual.POLICY['required_collision'],dual.POLICY['required_visibility_response'])
    def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return dual,worker,actor,Component,grass,dirty,digest


def test_only_actual_noncolliding_visibility_ignored_grass_is_separated(monkeypatch):
    dual,worker,actor,Component,grass,dirty,digest=fixture(monkeypatch)
    raw0,proxy0,_=dual.capture_payloads(worker)
    actor.parts.append(grass('streamed_grass'))
    raw1,proxy1,excluded=dual.capture_payloads(worker)
    assert digest(raw0)!=digest(raw1) and digest(proxy0)==digest(proxy1)
    assert excluded[0]['actual_class']=='GrassInstancedStaticMeshComponent'
    # A misleading component name and a particle never receive the exemption.
    actor.parts.append(Component('GrassInstancedStaticMeshComponent_fake','NiagaraComponent',
        dual.POLICY['required_collision'],dual.POLICY['required_visibility_response']))
    assert digest(dual.capture_payloads(worker)[1])!=digest(proxy1)


def test_geometry_actor_material_dirty_and_grass_collision_changes_remain_visible(monkeypatch):
    dual,worker,actor,Component,grass,dirty,digest=fixture(monkeypatch)
    actor.parts.append(grass('grass'))
    original=digest(dual.capture_payloads(worker)[1])
    for change,undo in (
        (lambda:actor.location.__setitem__(0,1),lambda:actor.location.__setitem__(0,0)),
        (lambda:actor.parts[0].record.__setitem__('get_materials',['edited']),lambda:actor.parts[0].record.__setitem__('get_materials',['material'])),
        (lambda:actor.parts[1].record.__setitem__('get_collision_enabled','query'),lambda:actor.parts[1].record.__setitem__('get_collision_enabled',dual.POLICY['required_collision'])),
    ):
        change();assert digest(dual.capture_payloads(worker)[1])!=original;undo()
    # A dirty package is retained even when all component geometry is identical.
    dirty.append(types.SimpleNamespace(get_path_name=lambda:'/Map'))
    assert digest(dual.capture_payloads(worker)[1])!=original


def test_private_runtime_function_globals_do_not_modify_global_worker(monkeypatch):
    fixture(monkeypatch)
    path=SOURCE.with_name('ue_scene_site_review_v1.py')
    def load(name):
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    original=load('runtime_original_offline');private=load('runtime_private_offline')
    original_ray=original.ray;private.ray=lambda *args:'private'
    assert original.ray is original_ray
    assert private.check_action_sample.__globals__['ray'] is private.ray
    assert original.check_action_sample.__globals__['ray'] is original_ray
