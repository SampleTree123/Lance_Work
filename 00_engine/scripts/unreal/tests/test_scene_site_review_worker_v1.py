"""Focused fake-UE checks; never connects to or modifies the shared editor."""
import copy
import importlib.util
import json
import sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest

S = Path(__file__).parents[1]
sys.path.insert(0, str(S))
import camera_standard_v2 as standard


def standard_config():
    return {'schema':standard.SCHEMA,
            'standard_id':'nonface_landscape_distance075_fov_compensated_v2',
            'landscape_distance_factor':.75,'scope':'nonface_landscape',
            'excluded_camera_ids':['front_head'],'compensate_horizontal_fov':True}


@pytest.fixture
def worker(monkeypatch):
    spec = importlib.util.spec_from_file_location('site_geometry_worker_test', S/'scene_site_review_geometry_v1.py')
    geometry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geometry)
    fake = SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=lambda x: bool(x)),
        unregister_slate_post_tick_callback=lambda handle: None, PrimitiveComponent=object,
        CollisionChannel=SimpleNamespace(ECC_VISIBILITY='visibility'),
        EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_map_packages=lambda: [], get_dirty_content_packages=lambda: []))
    monkeypatch.setitem(sys.modules, 'unreal', fake)
    monkeypatch.setitem(sys.modules, 'scene_site_review_geometry_v1', geometry)
    spec = importlib.util.spec_from_file_location('site_worker_test', S/'ue_scene_site_review_v1.py')
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    site = {'site_id':'test', 'map':'/Test', 'position':{'x':0., 'y':0., 'z':50.}, 'yaw':0.}
    d = {'site':site, 'marker':object(), 'local':{'input_fingerprint':'frozen','shots':[{},{}]},
         'job':None, 'report':None, 'preview':{}, 'ranges':False, 'original_fov':90.,
         'runtime_inputs':[], 'input_stats':{}, 'input_result':None,
         'frozen_shots':{}, 'motions':{}, 'loaded_plan_roots':set(),
         'runtime_version':7, 'camera_standard':standard_config()}
    monkeypatch.setattr(w, '_original_live', w.live, raising=False)
    monkeypatch.setattr(w, 'live', lambda: d)
    monkeypatch.setattr(w, 'synchronize', lambda: d)
    monkeypatch.setattr(w, 'current_map', lambda: '/Test')
    monkeypatch.setattr(w, 'write', lambda *args: None)
    return w, d


def job(d, kind='all'):
    return {'id':'offline', 'status':'running', 'scope':{'kind':kind, 'combinations':2 if kind=='all' else 1, 'selection':None},
            'shots':[{},{}] if kind=='all' else [{}], 'site':copy.deepcopy(d['site']), 'site_z':50.,
            'stamp':'same', 'input_signature':'inputs', 'scene_signature':'scene', 'last_validity_check':0.,
            'issues':[], 'seen':set(), 'completed':0, 'total':1, 'queue':deque(), 'handle':None}


def test_jumping_and_lifted_foot_keep_flat_ground_baseline(worker, monkeypatch):
    w, d = worker
    calls = []
    def flat(a,b):
        calls.append((a,b))
        return {'point':[a[0],a[1],50.], 'normal':[0.,0.,1.], 'actor':'Floor'}
    monkeypatch.setattr(w, 'ray', flat)
    monkeypatch.setattr(w, 'sphere', lambda *args: None)
    samples = [{'t':t, 'bones':{'foot_l':[1.,0.,z]},
                'ground_probes':[{'position':[1.,0.,z], 'baseline_ground_z_cm':50., 'baseline_height_cm':z-50.}]} for t,z in ((0.,53.),(.5,103.))]
    a = {'motion_id':'jump', 'samples':samples, 'body_segments':[]}
    j = job(d)
    w.check_action(j,a)
    assert j['issues'] == []
    assert [(a[2],b[2]) for a,b in calls] == [(130.,-100.),(130.,-100.)]


@pytest.mark.parametrize('status,kind,completed,expected', [
    ('cancelled','all',0,False), ('failed','all',0,False), ('stale','all',1,False),
    ('complete','all',0,False), ('complete','current',1,False), ('complete','all',1,True)])
def test_only_complete_full_matrix_clears_recheck(worker, monkeypatch, status, kind, completed, expected):
    w, d = worker
    monkeypatch.setattr(w, 'stamp', lambda: 'same')
    monkeypatch.setattr(w, 'input_status', lambda **kwargs: {'valid':True})
    j = job(d,kind);j['completed']=completed;d['job']=j
    w.finish(j,status)
    state = w.state()
    assert state['full_matrix_fresh'] is expected
    assert state['needs_recheck'] is not expected
    if kind=='current' and completed==1:
        assert state['current_result_fresh'] is True
        assert d['report']['coverage']['full_matrix_checked'] is False
    if status=='complete' and completed==0:
        assert d['report']['status']=='partial'


def test_source_change_invalidates_current_result_and_caches(worker, monkeypatch, tmp_path):
    w, d = worker
    source = tmp_path/'source.json';source.write_text('frozen',encoding='utf-8')
    d['runtime_inputs']=[w.geo.pin(source)];d['frozen_shots']={'old':{}};d['motions']={'old':object()}
    monkeypatch.setattr(w, 'stamp', lambda: 'same')
    j=job(d);j['completed']=1;d['job']=j;w.finish(j)
    assert w.state()['full_matrix_fresh'] is True
    source.write_text('changed-content',encoding='utf-8')
    assert w.input_status()['valid'] is False
    assert w.input_status()['valid'] is False  # Remains invalid on subsequent unchanged polling.
    assert w.state()['needs_recheck'] is True
    assert d['frozen_shots']=={} and d['motions']=={}
    source.write_text('frozen',encoding='utf-8')
    assert w.input_status()['valid'] is True


@pytest.mark.parametrize('change', ['site','scene','source'])
def test_mid_check_changes_end_as_stale_before_further_traces(worker, monkeypatch, change):
    w,d=worker;j=job(d);d['job']=j
    monkeypatch.setattr(w.time,'monotonic',lambda:4.)
    monkeypatch.setattr(w,'input_status',lambda **kwargs:{'valid':change!='source','signature':'inputs'})
    monkeypatch.setattr(w,'scene_signature',lambda:'changed' if change=='scene' else 'scene')
    if change=='site':d['site']['position']['x']=5.
    monkeypatch.setattr(w,'check_action_sample',lambda *args:pytest.fail('Stale job must not trace'))
    w.tick(.01)
    assert j['status']=='stale'
    assert d['report']['coverage']['full_matrix_checked'] is False


def test_component_edits_change_signature_and_unsupported_properties_are_safe(worker, monkeypatch):
    w,d=worker
    class Rotator:
        pitch=1.
        yaw=2.
        roll=3.
    rotations=[]
    def fresh_rotation():
        # UE wrappers may have address-bearing repr even for identical angles.
        # Keep instances alive so successive wrapper addresses really differ.
        rotations.append(Rotator())
        return rotations[-1]
    class Component:
        mesh='mesh-a'
        def get_path_name(self):return 'component'
        def get_editor_property(self,name):
            if name=='static_mesh':return self.mesh
            if name=='relative_rotation':return fresh_rotation()
            raise AttributeError(name)
    c=Component()
    a=SimpleNamespace(get_actor_label=lambda:'Environment',get_path_name=lambda:'actor',
        get_actor_location=lambda:'location',get_actor_rotation=fresh_rotation,get_actor_scale3d=lambda:'scale',
        get_components_by_class=lambda cls:[c],get_editor_property=lambda name:False)
    monkeypatch.setattr(w,'actors',lambda:SimpleNamespace(get_all_level_actors=lambda:[a]))
    before=w.scene_signature()
    assert w.scene_signature()==before
    assert str(rotations[0])!=str(rotations[2])
    assert w._plain(fresh_rotation())==[1.,2.,3.]
    Rotator.yaw=4.
    assert w.scene_signature()!=before
    Rotator.yaw=2.
    assert w.scene_signature()==before
    c.mesh='mesh-b'
    assert w.scene_signature()!=before


def test_visible_targets_cover_limbs_and_exclude_cropped_bones(worker):
    w,d=worker
    row={'position':[0.,0.,0.],'rotation_pitch_yaw_roll':[0.,0.,0.],'horizontal_fov_degrees':90.}
    shot={'width':20,'height':10,'camera_id':'front_full'}
    bones={'spine_02':[10.,0.,0.],'head':[10.,0.,4.], 'foot_l':[10.,0.,-4.],
           'hand_l':[10.,-8.,0.],'hand_r':[10.,8.,0.],'cropped':[10.,30.,0.],'behind':[-10.,0.,0.]}
    assert {t['bone'] for t in w.visible_targets(row,shot,bones)}=={'spine_02','head','foot_l','hand_l','hand_r'}


def test_old_human_decisions_cannot_be_resealed_after_scene_change(worker, monkeypatch):
    w,d=worker
    monkeypatch.setattr(w,'require_site',lambda:d)
    monkeypatch.setattr(w,'stamp',lambda:'new-scene')
    monkeypatch.setattr(w,'input_status',lambda **kwargs:{'valid':True})
    monkeypatch.setattr(w,'scene_signature',lambda:'scene')
    with pytest.raises(ValueError,match='人工决定'):
        w.save_site({'allowed_combinations':[], 'decisions_stamp':'old-scene'})
    w.save_site({'allowed_combinations':[], 'decisions_stamp':'new-scene'})
    assert d['site']['decisions_stamp']=='new-scene'


def test_queue_yields_between_samples_and_reuses_ignored_actors(worker, monkeypatch):
    w,d=worker
    sample={'t':0.,'frame_index':0,'bones':{},'ground_probes':[]}
    action={'motion_id':'jump','samples':[sample,{**sample,'t':.5,'frame_index':15}]}
    shot={'shot_id':'shot','motion_id':'jump','camera_id':'front_full','orientation':'portrait',
          'samples':[sample,{**sample,'t':.5,'frame_index':15}]}
    monkeypatch.setattr(w,'require_site',lambda:d)
    monkeypatch.setattr(w,'placed',lambda selection=None:{'shots':[shot],'actions':[action]})
    monkeypatch.setattr(w,'input_status',lambda **kwargs:{'valid':True,'signature':'inputs'})
    monkeypatch.setattr(w,'stamp',lambda:'same')
    monkeypatch.setattr(w,'scene_signature',lambda:'scene')
    scans=[]
    monkeypatch.setattr(w,'owned',lambda:scans.append(True) or ['preview-actor'])
    monkeypatch.setattr(w.u,'register_slate_post_tick_callback',lambda callback:'fake-handle',raising=False)
    w.start_check({'action_id':'jump','camera_id':'front_full','aspect':'portrait'})
    j=d['job']
    assert len(j['queue'])==4 and j['total']==4
    assert [w.trace_ignored() for _ in range(3)]==[['preview-actor']]*3
    assert len(scans)==1
    monkeypatch.setattr(w,'job_stale_reason',lambda *args,**kwargs:None)
    times=iter([0.,.001,.020])
    monkeypatch.setattr(w.time,'monotonic',lambda:next(times))
    checked=[]
    monkeypatch.setattr(w,'check_action_sample',lambda *args:checked.append(args))
    w.tick(.01)
    assert j['completed']==1 and len(j['queue'])==3 and len(checked)==1


def test_cancel_can_close_job_from_previous_runtime(worker):
    w,d=worker
    j=job(d);j.pop('scope');d['job']=j
    w.cancel()
    assert j['status']=='cancelled'
    assert d['report']['scope']['kind']=='legacy'
    assert d['report']['coverage']['full_matrix_checked'] is False


def test_runtime_reset_clears_loaded_roots_and_reloads_frozen_shot(worker, monkeypatch, tmp_path):
    w,d=worker
    d['runtime_version']=1
    d['local']['sources']=[]
    d['local']['shots']=[{'shot_id':'shot'}]
    d['loaded_plan_roots']={str(w.geo.NONFACE)}
    d['frozen_shots']={}
    monkeypatch.setattr(w.u,w.LIVE,d,raising=False)
    monkeypatch.setattr(w,'live',w._original_live)
    monkeypatch.setattr(w.geo,'pin',lambda path:{'path':str(path),'sha256':'fixed'})
    monkeypatch.setattr(w.geo,'FOLLOW_CORRECTION',tmp_path/'absent_correction.json')
    monkeypatch.setattr(importlib,'reload',lambda module:module)
    monkeypatch.setattr(standard,'load_config',lambda path:d['camera_standard'])
    monkeypatch.setattr(w,'input_status',lambda **kwargs:{'valid':True})
    loaded=[]
    def read_current(path):
        loaded.append(str(path))
        if Path(path).name=='site_review_local_geometry_v1.json':
            return {'sources':[], 'shots':[{'shot_id':'shot','reloaded_geometry':True}]}
        return {'shots':[{'shot_id':'shot','frozen':True}]}
    monkeypatch.setattr(w,'read',read_current)
    assert w.live()['loaded_plan_roots']==set()
    assert d['runtime_version']==7
    assert d['local']['shots']==[{'shot_id':'shot','reloaded_geometry':True}]
    assert d['shot_index']['shot']['reloaded_geometry'] is True
    assert w.frozen_shot('shot')=={'shot_id':'shot','frozen':True}
    assert w.frozen_shot('shot')['frozen'] is True
    assert len(loaded)==2
    assert Path(loaded[0]).name=='site_review_local_geometry_v1.json'
    assert str(w.geo.NONFACE) in d['loaded_plan_roots']


def test_follow_correction_wins_after_base_plan_loaded_for_another_shot(worker, monkeypatch, tmp_path):
    w,d=worker
    correction=tmp_path/'follow.json';correction.write_text('{}',encoding='utf-8')
    monkeypatch.setattr(w.geo,'FOLLOW_CORRECTION',correction)
    monkeypatch.setattr(w,'input_status',lambda **kwargs:{'valid':True})
    corrected={'shot_id':'affected','trajectory_sha256':'corrected','frames':[{'position':[1,2,3]}]}
    base={'shot_id':'affected','trajectory_sha256':'old','frames':[{'position':[99,2,3]}]}
    unaffected={'shot_id':'unaffected','trajectory_sha256':'unchanged'}
    loaded=[]
    def read_plan(path):
        loaded.append(Path(path))
        if Path(path)==correction:return {'corrected_shots':[corrected]}
        if Path(path).parent==w.geo.NONFACE:return {'shots':[base,unaffected]}
        return {'shots':[]}
    monkeypatch.setattr(w,'read',read_plan)
    # Loading the base for an unaffected request must never overwrite the
    # correction already cached for a later preview/playback request.
    assert w.frozen_shot('unaffected')==unaffected
    assert w.frozen_shot('affected')==corrected
    assert w.frozen_shot('affected')!=base
    assert loaded==[correction,w.geo.NONFACE/'camera_trial_plan_v1.json']


def test_actual_1260_worker_shots_match_geometry_composition_without_ue(worker, monkeypatch):
    """Read real frozen inputs; fake Unreal never creates or changes an actor."""
    w,d=worker
    if not w.geo.CAMERA_STANDARD.is_file() or not w.geo.FOLLOW_CORRECTION.is_file():
        pytest.skip('Project v2 acceptance/correction configuration unavailable')
    config=standard.load_config(w.geo.CAMERA_STANDARD)
    d['camera_standard']=config
    monkeypatch.setattr(w,'input_status',lambda **kwargs:{'valid':True})
    loaded=w.geo.load_library()
    expected={s['shot_id']:s for s in loaded['shots']}
    correction=w.read(w.geo.FOLLOW_CORRECTION)
    originals={s['shot_id']:s for root in (w.geo.NONFACE,w.geo.FACE)
               for s in w.read(root/'camera_trial_plan_v1.json')['shots']}
    corrected={s['shot_id']:s for s in correction['corrected_shots']}
    assert len(corrected)==len(correction['corrected_shots'])==320
    assert len(expected)==1260
    assert sum(standard.MARKER in s for s in expected.values())==600
    face_count=0
    for sid,expected_shot in expected.items():
        actual=w.frozen_shot(sid)
        assert actual==expected_shot
        assert w.geo._clock(actual)==w.geo._clock(originals[sid])
        if actual['camera_id']=='front_head':
            face_count+=1
            assert actual==originals[sid]
        elif actual['orientation']=='portrait':
            assert actual==corrected.get(sid,originals[sid])
    assert face_count==60
    assert {str(w.geo.FOLLOW_CORRECTION),str(w.geo.NONFACE),str(w.geo.FACE)}.issubset(d['loaded_plan_roots'])


def test_near_supporting_floor_at_foot_or_ball_endpoint_is_not_occlusion(worker, monkeypatch):
    w,d=worker
    row={'t':0.,'frame_index':0,'position':[0.,0.,0.],
         'rotation_pitch_yaw_roll':[0.,0.,0.],'horizontal_fov_degrees':90.}
    shot={'shot_id':'shot','motion_id':'jump','camera_id':'front_full',
          'orientation':'landscape','width':20,'height':10,'samples':[row]}
    j=job(d);j['unmeasured_visibility_samples']=0;j['site_z']=0.
    j['action_samples']={'jump':{0:{'bones':{'foot_l':[10.,0.,2.],'ball_l':[11.,1.,1.]}}}}
    monkeypatch.setattr(w,'sphere',lambda *args:None)
    monkeypatch.setattr(w,'ray',lambda start,target:{'point':[target[0],target[1],0.],
        'normal':[0.,0.,1.],'actor':'Landscape'})
    w.check_shot_sample(j,shot,row,0)
    assert j['issues']==[]


def test_floor_height_difference_or_wall_and_nonfoot_hits_still_report_occlusion(worker, monkeypatch):
    w,d=worker
    row={'t':0.,'frame_index':0,'position':[0.,0.,0.],
         'rotation_pitch_yaw_roll':[0.,0.,0.],'horizontal_fov_degrees':90.}
    shot={'shot_id':'shot','motion_id':'jump','camera_id':'front_full',
          'orientation':'landscape','width':20,'height':10,'samples':[row]}
    monkeypatch.setattr(w,'sphere',lambda *args:None)
    for bone,point,normal in (('foot_l',[4.,0.,8.],[0.,0.,1.]),
                              ('ball_r',[10.,0.,1.],[1.,0.,0.]),
                              ('head',[10.,0.,1.],[0.,0.,1.])):
        j=job(d);j['unmeasured_visibility_samples']=0;j['site_z']=0.
        j['action_samples']={'jump':{0:{'bones':{bone:[10.,0.,2.]}}}}
        hit={'point':point,'normal':normal,'actor':'Environment'}
        monkeypatch.setattr(w,'ray',lambda start,target,hit=hit:hit)
        w.check_shot_sample(j,shot,row,0)
        assert [issue['kind'] for issue in j['issues']]==['occlusion']


def test_grazing_ray_to_slightly_low_foot_ignores_far_xy_hit_on_baseline_floor(worker, monkeypatch):
    w,d=worker
    row={'t':0.,'frame_index':0,'position':[0.,0.,1.],
         'rotation_pitch_yaw_roll':[0.,0.,0.],'horizontal_fov_degrees':90.}
    shot={'shot_id':'shot','motion_id':'walk','camera_id':'front_full',
          'orientation':'landscape','width':20,'height':10,'samples':[row]}
    j=job(d);j['site_z']=0.;j['unmeasured_visibility_samples']=0
    j['action_samples']={'walk':{0:{'bones':{'ball_r':[100.,0.,-.36]}}}}
    monkeypatch.setattr(w,'sphere',lambda *args:None)
    # Along this shallow ray the floor intersection is ~26cm from the foot.
    hit={'point':[100./1.36,0.,0.],'normal':[0.,0.,1.],'actor':'Landscape'}
    monkeypatch.setattr(w,'ray',lambda start,target:hit)
    assert w.math.dist(hit['point'],[100.,0.,-.36])>5.
    w.check_shot_sample(j,shot,row,0)
    assert j['issues']==[]


def prepare_check_catalog(worker, monkeypatch):
    w, d = worker
    samples = [{'t': t, 'frame_index': index, 'bones': {}, 'ground_probes': []}
               for index, t in enumerate((0., .5))]
    actions = [{'motion_id': motion, 'samples': copy.deepcopy(samples)} for motion in ('walk', 'jump')]
    shots = [{'shot_id': motion + '_' + camera, 'motion_id': motion, 'camera_id': camera,
              'orientation': aspect, 'samples': copy.deepcopy(samples)}
             for motion in ('walk', 'jump') for camera, aspect in (('front', 'landscape'), ('side', 'portrait'))]
    graph = {'actions': actions, 'shots': shots}
    d['local']['shots'] = copy.deepcopy(shots)
    monkeypatch.setattr(w, 'placed', lambda selection=None: graph)
    monkeypatch.setattr(w, 'input_status', lambda **kwargs: {'valid': True, 'signature': 'inputs'})
    monkeypatch.setattr(w, 'stamp', lambda: 'same')
    monkeypatch.setattr(w, 'scene_signature', lambda: 'scene')
    monkeypatch.setattr(w, 'owned', lambda: [])
    monkeypatch.setattr(w.u, 'register_slate_post_tick_callback', lambda callback: 'check-handle', raising=False)
    return w, d, graph


@pytest.mark.parametrize('exclude_walk,expected_scope,expected_count,full', [
    (False, 'all', 4, True), (True, 'remaining', 2, False)])
def test_exclusion_filters_queue_and_action_work_without_claiming_full_coverage(
        worker, monkeypatch, exclude_walk, expected_scope, expected_count, full):
    w, d, graph = prepare_check_catalog(worker, monkeypatch)
    excluded = [{'action_id': 'walk', 'camera_id': camera, 'aspect': aspect}
                for camera, aspect in (('front', 'landscape'), ('side', 'portrait'))] if exclude_walk else []
    w.start_check({'excluded_combinations': excluded}, all_shots=True)
    job = d['job']
    assert job['scope']['kind'] == expected_scope
    assert job['scope']['combinations'] == expected_count
    assert len(job['shots']) == expected_count
    assert set(job['actions']) == ({'jump'} if exclude_walk else {'walk', 'jump'})
    assert job['total'] == (6 if exclude_walk else 12)
    assert len(job['queue']) == job['total']
    if exclude_walk:
        assert job['scope']['excluded_combinations'] == excluded
        assert all(item[1]['motion_id'] == 'jump' for item in job['queue'])
    job['completed'] = job['total']
    w.finish(job)
    result = w.state()
    assert result['current_result_fresh'] is True
    assert result['full_matrix_fresh'] is full
    assert d['report']['coverage']['full_matrix_checked'] is full


@pytest.mark.parametrize('all_shots', [False, True])
def test_all_excluded_selection_never_starts_empty_or_misleading_check(worker, monkeypatch, all_shots):
    w, d, graph = prepare_check_catalog(worker, monkeypatch)
    excluded = [{'action_id': shot['motion_id'], 'camera_id': shot['camera_id'], 'aspect': shot['orientation']}
                for shot in graph['shots']]
    with pytest.raises(ValueError, match='全部排除'):
        w.start_check({'action_id': 'walk', 'camera_id': 'front', 'aspect': 'landscape',
                       'excluded_combinations': excluded}, all_shots=all_shots)
    assert d['job'] is None
    assert d['report'] is None


@pytest.fixture
def playback(worker, monkeypatch):
    w, d = worker
    clock = {'time': 100.}
    shot = {'motion_id': 'walk', 'camera_id': 'front', 'orientation': 'landscape',
            'clock': {'duration_seconds': 5.}}
    selection = {'action_id': 'walk', 'camera_id': 'front', 'aspect': 'landscape'}
    rendered, registered, unregistered = [], [], []
    monkeypatch.setattr(w, 'select', lambda selection: (shot, {}))
    monkeypatch.setattr(w.time, 'monotonic', lambda: clock['time'])
    def preview(values):
        rendered.append(copy.deepcopy(values))
        d['preview'] = {'time_seconds': values['time_seconds']}
    def register(callback):
        registered.append(callback)
        return 'playback-handle-' + str(len(registered))
    monkeypatch.setattr(w, 'preview', preview)
    monkeypatch.setattr(w.u, 'register_slate_post_tick_callback', register, raising=False)
    monkeypatch.setattr(w.u, 'unregister_slate_post_tick_callback', unregistered.append)
    return w, d, clock, selection, rendered, registered, unregistered


def test_playback_resumes_from_requested_time_and_pause_unregisters_callback(playback):
    w, d, clock, selection, rendered, registered, unregistered = playback
    w.play({**selection, 'time_seconds': 2.5, 'loop': False})
    assert rendered[-1]['time_seconds'] == 2.5
    assert d['playback_started'] == 97.5
    assert registered == [w.playback_tick]
    clock['time'] = 101.
    w.playback_tick(.01)
    assert rendered[-1]['time_seconds'] == 3.5
    w.pause_playback()
    assert d['playback']['playing'] is False
    assert unregistered == ['playback-handle-1']
    assert 'playback_handle' not in d
    clock['time'] = 108.
    w.play({**selection, 'time_seconds': d['playback']['time_seconds'], 'loop': False})
    assert rendered[-1]['time_seconds'] == 3.5
    clock['time'] = 108.25
    w.playback_tick(.01)
    assert rendered[-1]['time_seconds'] == 3.75


def test_loop_wraps_at_duration_and_stop_returns_to_first_frame(playback):
    w, d, clock, selection, rendered, registered, unregistered = playback
    w.play({**selection, 'time_seconds': 4.5, 'loop': True})
    clock['time'] = 101.25
    w.playback_tick(.01)
    assert rendered[-1]['time_seconds'] == .75
    assert d['playback']['playing'] is True
    clock['time'] = 116.25
    w.playback_tick(.01)
    assert rendered[-1]['time_seconds'] == .75
    w.stop_playback()
    assert rendered[-1]['time_seconds'] == 0.
    assert d['playback']['time_seconds'] == 0.
    assert d['playback']['playing'] is False
    assert unregistered == ['playback-handle-1']


def test_non_loop_playback_stops_exactly_at_last_frame(playback):
    w, d, clock, selection, rendered, registered, unregistered = playback
    w.play({**selection, 'time_seconds': 4., 'loop': False})
    clock['time'] = 103.
    w.playback_tick(.01)
    assert rendered[-1]['time_seconds'] == 5.
    assert d['playback']['playing'] is False
    assert d['playback']['time_seconds'] == 5.
    assert unregistered == ['playback-handle-1']
    count = len(rendered)
    w.playback_tick(.01)
    assert len(rendered) == count


@pytest.mark.parametrize('change', ['position', 'yaw', 'map'])
def test_site_change_cancels_playback_before_rendering_another_frame(playback, change):
    w, d, clock, selection, rendered, registered, unregistered = playback
    w.play({**selection, 'time_seconds': 1., 'loop': True})
    if change == 'position':
        d['site']['position']['x'] += 1.
    elif change == 'yaw':
        d['site']['yaw'] += 1.
    else:
        d['site']['map'] = '/Different'
    count = len(rendered)
    clock['time'] = 101.
    w.playback_tick(.01)
    assert len(rendered) == count
    assert d['playback']['playing'] is False
    assert d['playback']['error']
    assert unregistered == ['playback-handle-1']


def test_issue_reviews_round_trip_with_notes_and_cannot_be_resealed_when_stale(worker, monkeypatch):
    w, d = worker
    current = {'stamp': 'review-a', 'valid': True}
    monkeypatch.setattr(w, 'stamp', lambda: current['stamp'])
    monkeypatch.setattr(w, 'input_status', lambda **kwargs: {'valid': current['valid']})
    monkeypatch.setattr(w, 'scene_signature', lambda: 'scene')
    records = {}
    monkeypatch.setattr(w, 'write', lambda path, record: records.update({str(path): copy.deepcopy(record)}))
    monkeypatch.setattr(w, 'read', lambda path: copy.deepcopy(records[str(path)]))
    def create(site):
        d['site'] = copy.deepcopy(site)
        d['report'] = None
    monkeypatch.setattr(w, 'create', create)
    key = json.dumps({'kind': 'occlusion', 'action_id': 'walk', 'camera_id': 'front',
                      'aspect': 'landscape', 'time_seconds': 1., 'message': 'Branch'},
                     ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    reviews = {key: {'status': 'acceptable', 'note': '背景树枝，可接受'}}
    decisions = [{'action_id': 'walk', 'camera_id': 'front', 'aspect': 'portrait', 'decision': 'excluded'}]
    d['report'] = {'issues': [{'kind': 'occlusion'}]}
    path = w.save_site({'allowed_combinations': decisions, 'issue_reviews': reviews, 'decisions_stamp': 'review-a'})
    assert records[path]['site']['issue_reviews'] == reviews
    d['site'] = None
    w.load_site({'site_id': 'test'})
    assert d['site']['issue_reviews'] == reviews
    assert d['report']['issues'] == [{'kind': 'occlusion'}]
    assert w.state()['issue_reviews'] == reviews
    current['stamp'] = 'review-b'
    stale_site = copy.deepcopy(d['site'])
    with pytest.raises(ValueError, match='人工决定'):
        w.save_site({'issue_reviews': reviews, 'decisions_stamp': 'review-a'})
    assert d['site'] == stale_site
    assert w.state()['issue_reviews'] == {}
    assert w.state()['allowed_combinations'] == []
    current['valid'] = False
    with pytest.raises(ValueError, match='输入已经改变'):
        w.save_site({'issue_reviews': reviews, 'decisions_stamp': 'review-b'})
    current['valid'] = True
    w.save_site({})
    assert d['site']['issue_reviews'] == {}
    assert d['site']['allowed_combinations'] == []


@pytest.mark.parametrize('review', [{'status': 'unknown', 'note': ''},
                                  {'status': 'acceptable', 'note': 7}])
def test_invalid_issue_review_does_not_mutate_site(worker, monkeypatch, review):
    w, d = worker
    monkeypatch.setattr(w, 'stamp', lambda: 'same')
    monkeypatch.setattr(w, 'input_status', lambda **kwargs: {'valid': True})
    before = copy.deepcopy(d['site'])
    with pytest.raises(ValueError, match='格式无效'):
        w.save_site({'issue_reviews': {'recorded-issue': review}, 'decisions_stamp': 'same'})
    assert d['site'] == before
