"""Two imported-point behaviors through the private adapter; no Unreal import."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ue_primary_saved_site_review_v1 as adapter


def test_production_reload_tracks_trial_catalog_and_material_code_at_command_boundaries(tmp_path, monkeypatch):
    names = ('hair_eye_color_runtime_v1', 'ue_hair_coverage_runtime_v1', 'scene_site_hair_color_trials_v1',
             'hair_color_neutral_trial_runtime_v1', 'scene_site_appearance_v1',
             'ue_scene_site_appearance_v1', 'ue_production_site_runtime_v1')
    modules = {name: SimpleNamespace(__name__=name) for name in names}
    for name in names:
        (tmp_path / (name + '.py')).write_text('# ' + name, encoding='utf-8')
    modules['ue_production_site_runtime_v1'].install = lambda worker: worker
    monkeypatch.setattr(adapter, 'S', tmp_path)
    monkeypatch.setattr(adapter.importlib, 'import_module', lambda name: modules[name])
    reloaded = []
    monkeypatch.setattr(adapter.importlib, 'reload', lambda module: reloaded.append(module.__name__) or module)
    state = {'job': None}
    cache = {'actor': 'stale'}
    worker = SimpleNamespace(LIVE='live', u=SimpleNamespace(live=state, _dm_scene_site_appearance_cache_v1=cache))
    adapter.install_production_runtime(worker)
    assert reloaded == list(names) and cache == {}
    assert modules['scene_site_appearance_v1']._formal_cache is None
    reloaded.clear()
    adapter.install_production_runtime(worker)
    assert reloaded == []
    for name in ('scene_site_hair_color_trials_v1', 'hair_color_neutral_trial_runtime_v1', 'ue_hair_coverage_runtime_v1'):
        (tmp_path / (name + '.py')).write_text('# changed ' + name, encoding='utf-8')
        cache['actor'] = 'stale'
        adapter.install_production_runtime(worker)
        assert reloaded == [name] and cache == {}
        reloaded.clear()


class Properties:
    def __init__(self, **values): self.values=values
    def get_editor_property(self,key): return self.values[key]
    def set_editor_property(self,key,value): self.values[key]=value


def worker_fixture(tmp_path):
    config=tmp_path/'standard.json'
    config.write_text('{}',encoding='utf-8')
    def pin(path):
        return {'path':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    geo=SimpleNamespace(CAMERA_STANDARD=config,pin=pin,
        canonical_sha=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest())
    settings=Properties(override_auto_exposure_bias=False,auto_exposure_bias=-.7,auto_exposure_method='scene')
    component=Properties(post_process_settings=settings,post_process_blend_weight=.3,field_of_view=64.5,aspect_ratio=16/9)
    camera=SimpleNamespace(get_component_by_class=lambda cls:component)
    rows=[{'motion_id':'walk','camera_id':'orbit_360','orientation':'landscape'},
          {'motion_id':'walk','camera_id':'front_full','orientation':'portrait'}]
    site={'site_id':'primary_example','position':{'x':1,'y':2,'z':3},'yaw':30.,'exposure_compensation':2.,
        'exclusions':[{'camera_id':'orbit_360'}],'allowed_combinations':[],
        'imported_camera_standard':{'configuration':pin(config),
            'standard_id':'nonface_landscape_distance050_fov_compensated_v3','distance_factor':.5,
            'scope':'nonface_landscape','portrait_and_face_unchanged':True},
        'imported_excluded_combinations':[{'action_id':'walk','camera_id':'orbit_360','aspect':'landscape','decision':'excluded'}],
        'imported_preview_semantics':'pending_private_version_adapter_exposure_and_exclusion_integration'}
    state={'site':None,'report':None,'local':{'shots':rows},'camera':camera,'runtime_inputs':[],
           'input_stats':{},'input_result':None}
    saved={'imported':copy.deepcopy(site),'legacy':{'site_id':'gas_pilot','allowed_combinations':[
        {'action_id':'walk','camera_id':'front_full','aspect':'portrait','decision':'allowed'}]}}
    def load(request):
        state['site']=copy.deepcopy(saved[request['site_id']]);state['report']=None
    worker=SimpleNamespace(live=lambda:state,stamp=lambda:'real_loaded_point_and_scene_stamp',load_site=load,
        preview=lambda request:{'time_seconds':request.get('time_seconds',0)},geo=geo,
        require_site=lambda:state,u=SimpleNamespace(CameraComponent=object()))
    adapter.install_private_behaviors(worker)
    return worker,state,saved,component


def test_private_load_activates_only_exclusions_with_real_stamp_and_keeps_later_human_decisions(tmp_path):
    worker,state,saved,_=worker_fixture(tmp_path)
    worker.load_site({'site_id':'imported'})
    site=state['site']
    assert site['allowed_combinations']==saved['imported']['imported_excluded_combinations']
    assert site['decisions_stamp']==worker.stamp()
    assert site['human_acceptance']=='pending' and state['report'] is None
    assert site['exclusions']==saved['imported']['exclusions']
    assert site['imported_camera_standard']['distance_factor']==.5
    assert any(Path(p['path']).name==Path(adapter.__file__).name for p in state['runtime_inputs'])
    saved['imported']=copy.deepcopy(site)
    saved['imported']['allowed_combinations']=copy.deepcopy(saved['legacy']['allowed_combinations'])
    worker.load_site({'site_id':'imported'})
    assert state['site']['allowed_combinations']==saved['legacy']['allowed_combinations']
    worker.load_site({'site_id':'legacy'})
    assert state['site']==saved['legacy']  # Existing points still load unchanged.


@pytest.mark.parametrize('fault',['allowed','unknown_combination','wrong_standard'])
def test_imported_exclusion_binding_rejects_passes_unknown_combinations_and_other_standard(tmp_path,fault):
    worker,state,saved,_=worker_fixture(tmp_path)
    if fault=='allowed':saved['imported']['imported_excluded_combinations'][0]['decision']='allowed'
    elif fault=='unknown_combination':saved['imported']['imported_excluded_combinations'][0]['camera_id']='missing'
    else:saved['imported']['imported_camera_standard']['distance_factor']=.75
    with pytest.raises(ValueError):worker.load_site({'site_id':'imported'})
    assert 'decisions_stamp' not in state['site'] and state['site']['allowed_combinations']==[]


def test_private_preview_applies_camera_only_ev_and_zero_resets_scene_inheritance(tmp_path):
    worker,state,saved,component=worker_fixture(tmp_path)
    worker.load_site({'site_id':'imported'})
    before=copy.deepcopy(component.values)
    stamp=worker.stamp()
    assert worker.preview({'time_seconds':1.})=={'time_seconds':1.}
    settings=component.values['post_process_settings'].values
    assert settings['override_auto_exposure_bias'] is True and settings['auto_exposure_bias']==2.
    assert settings['auto_exposure_method']=='scene'
    assert component.values['field_of_view']==before['field_of_view']
    assert component.values['aspect_ratio']==before['aspect_ratio']
    state['site']['exposure_compensation']=0.
    assert worker.stamp()!=stamp
    worker.preview({'time_seconds':2.})
    assert settings['override_auto_exposure_bias'] is False
    worker.load_site({'site_id':'legacy'})
    worker.preview({})
    assert settings['override_auto_exposure_bias'] is False


def test_unloaded_marker_is_recovered_without_converting_null_uobject(tmp_path):
    state={'site':{'site_id':'draft','map':'/Game/Scenes/Old/Map','position':{'x':4,'y':5,'z':6}},
           'marker':object(),'preview':{'time_seconds':2}}
    writes=[]
    def invalid(_):raise TypeError('ObjectInstance is null!')
    worker=SimpleNamespace(live=lambda:state,current_map=lambda:'/Game/Scenes/Old/Map',
        u=SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=invalid)),RUN=tmp_path,
        write=lambda path,value:writes.append(copy.deepcopy(value)),pause_playback=lambda:None,cancel=lambda:None,
        restore=lambda:state.update(site=None,marker=None,character=None,camera=None,ranges=False))
    adapter.install_scene_switch_behaviors(worker)
    assert worker.synchronize()['site'] is None
    assert writes[0]['site']['position']=={'x':4,'y':5,'z':6}
    assert state['marker'] is None


@pytest.mark.parametrize('save_ok',[True,False])
def test_scene_switch_preserves_dirty_world_before_loading(tmp_path,monkeypatch,save_ok):
    import scene_site_catalog_v1 as directory
    monkeypatch.setattr(directory,'build_catalog',lambda:{'scenes':[{'map_path':'/Game/Scenes/New/Map'}]})
    events=[];state={'site':None};current=['/Game/Scenes/Old/Map']
    class Package:
        def get_name(self):return current[0]
        def __del__(self):events.append(('package_released',None))
    def load(target):
        assert any(kind=='package_released' for kind,_ in events)
        events.append(('load',target));current[0]=target;return True
    def save(world,path):events.append(('backup',path));return save_ok
    viewport=SimpleNamespace(load_level=load,get_level_viewport_fov=lambda key:80,
                             get_active_viewport_config_key=lambda:'main')
    editor=SimpleNamespace(get_level_viewport_camera_info=lambda:('position','rotation'))
    u=SimpleNamespace(MoviePipelineQueueSubsystem='queue',LevelEditorSubsystem='viewport',UnrealEditorSubsystem='editor',
        get_editor_subsystem=lambda key:{'queue':SimpleNamespace(is_rendering=lambda:False),'viewport':viewport,'editor':editor}[key],
        EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_map_packages=lambda:[Package()],save_map=save))
    worker=SimpleNamespace(live=lambda:state,current_map=lambda:current[0],u=u,RUN=tmp_path,
        write=lambda p,v:events.append(('receipt',copy.deepcopy(v))),world=lambda:'world',
        restore=lambda:events.append(('restore',None)))
    adapter.install_scene_switch_behaviors(worker)
    if save_ok:
        worker.open_scene({'map_path':'/Game/Scenes/New/Map'})
        kinds=[e[0] for e in events]
        assert kinds.index('backup')<kinds.index('restore')<kinds.index('load')
        assert next(v for k,v in events if k=='backup').startswith('/Game/DataMake/Validation/SceneSiteSwitchRecovery/')
    else:
        with pytest.raises(ValueError,match='备份失败'):worker.open_scene({'map_path':'/Game/Scenes/New/Map'})
        assert not any(k in ('load','restore') for k,_ in events)


def test_exclusions_from_previous_point_rejected_before_check_starts():
    calls=[]
    worker=SimpleNamespace(require_site=lambda:None,stamp=lambda:'new-point',
        start_check=lambda request,all_combinations:calls.append(request))
    adapter.install_scene_switch_behaviors(worker)
    request={'excluded_combinations':[{'action_id':'walk'}],'decisions_stamp':'old-point'}
    with pytest.raises(ValueError,match='旧排除清单'):worker.start_check(request,True)
    assert not calls
    worker.start_check({**request,'decisions_stamp':'new-point'},True)
    assert len(calls)==1


def test_stop_returns_current_preview_to_zero_and_restore_clears_old_playback():
    state={'site':{'map':'map'},'preview':{'action_id':'new','camera_id':'side','time_seconds':2.},
           'playback_selection':{'action_id':'old'},'playback':{'playing':True,'time_seconds':2.}}
    calls=[]
    worker=SimpleNamespace(live=lambda:state,current_map=lambda:'map',stop_playback=lambda:None,
        pause_playback=lambda:state['playback'].update(playing=False),
        preview=lambda selection:calls.append(selection),restore=lambda:None)
    adapter.install_scene_switch_behaviors(worker)
    worker.stop_playback()
    assert calls==[{'action_id':'new','camera_id':'side','time_seconds':0.}]
    worker.restore()
    assert 'playback_selection' not in state and state['playback']['time_seconds']==0.


def test_cached_private_worker_refreshes_scene_behaviors_and_installs_production(monkeypatch, tmp_path):
    events=[]
    state={'runtime_inputs':[],'site':None}
    adapter_pin={'path':str(Path(adapter.__file__)),'sha256':'old'}
    def old_live():
        if adapter_pin not in state['runtime_inputs']:state['runtime_inputs'].append(adapter_pin)
        return state
    def original_restore():events.append('restore')
    worker=SimpleNamespace(live=lambda:None,restore=lambda:None,_primary_adapter_revision=4,
        _production_site_installed=1,_production_site_originals={'live':old_live,'restore':original_restore},
        geo=SimpleNamespace(pin=lambda path:{'path':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}))
    fake_u=SimpleNamespace(**{adapter.CACHE:worker})
    monkeypatch.setitem(sys.modules,'unreal',fake_u)
    monkeypatch.setattr(adapter,'install_production_runtime',lambda value:events.append('production') or value)
    assert adapter.private_worker() is worker
    assert events==['production']
    assert worker._primary_adapter_revision==adapter.ADAPTER_REVISION
    worker.live()
    assert state['runtime_inputs'][0]['sha256']!='old'
    assert state['runtime_inputs'][0]==worker._primary_adapter_pin


def test_new_private_worker_installs_production_without_touching_frozen_source(monkeypatch):
    fake_u=SimpleNamespace()
    calls=[]
    monkeypatch.setitem(sys.modules,'unreal',fake_u)
    monkeypatch.setattr(adapter,'install_production_runtime',lambda worker:calls.append(worker) or worker)
    before=adapter.ORIGINAL.read_bytes()
    worker=adapter.private_worker()
    assert calls==[worker]
    assert getattr(fake_u,adapter.CACHE) is worker
    assert worker.LIVE==adapter.LIVE
    assert worker.PREFIX=='DM_SiteReview_Primary_'
    assert adapter.ORIGINAL.read_bytes()==before
    assert hashlib.sha256(before).hexdigest()==adapter.ORIGINAL_SHA256
