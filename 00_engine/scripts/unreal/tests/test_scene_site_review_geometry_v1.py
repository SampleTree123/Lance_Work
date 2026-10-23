"""Bounded offline checks: rigid placement, frozen sampling, source invalidation."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
import camera_standard_v2 as standard

spec = importlib.util.spec_from_file_location('site_geometry', Path(__file__).parents[1] / 'scene_site_review_geometry_v1.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def library():
    frames = [{'t': i/30, 'position': [100+i, 200., 80.], 'look_at': [i, 0., 80.],
               'rotation_pitch_yaw_roll': [2., -90., 0.], 'horizontal_fov_degrees': 35.} for i in range(7)]
    shot = {'shot_id': 'test_l', 'motion_id': 'test', 'motion_label': 'jump', 'sex': 'female',
            'camera_id': 'front_full', 'camera_label': 'front', 'orientation': 'landscape',
            'width': 1280, 'height': 720, 'trajectory_sha256': 'frozen',
            'source_start_seconds': 1., 'source_body_play_rate': .5,
            'source_end_seconds': 1.1, 'window_start_seconds': 0.,
            'duration_seconds': .2, 'frame_count': 6, 'fps': 30,
            'source_animation': '/test', 'source_clip_id': 'test',
            'frames': frames[:-1], 'endpoint_validation_frame': frames[-1]}
    clip = {'animation_path': '/test', 'frames': [
        {'t': 1., 'bones': {'root': [0., 0., 0.], 'foot_l': [2., 0., 3.], 'ball_l': [3., 0., 2.]}},
        {'t': 1.1, 'bones': {'root': [10., 2., 30.], 'foot_l': [12., 2., 33.], 'ball_l': [13., 2., 32.]}}]}
    second = copy.deepcopy(shot)
    second.update(shot_id='test_p', orientation='portrait', width=720, height=1280)
    return {'shots': [shot, second], 'clips': {'test': clip}, 'source_sampling_fps': 10,
            'sources': [{'path': 'frozen-test', 'sha256': 'abc'}]}


def test_rigid_placement_preserves_camera_body_and_ground_baseline():
    local = g.prepare_geometry(library(), sample_step_frames=3)
    original = copy.deepcopy(local)
    placed = g.place_geometry(local, [100., 200., 50.], 90.)
    assert local == original
    assert placed['actions'][0]['samples'][-1]['bones']['root'] == pytest.approx([98., 210., 80.])
    probe = placed['actions'][0]['samples'][-1]['ground_probes'][1]
    assert probe['baseline_ground_z_cm'] == 50.
    assert probe['baseline_height_cm'] == 33.  # The lifted foot is expected, not a floor anomaly.
    assert probe['position'][2] - probe['baseline_ground_z_cm'] == probe['baseline_height_cm']
    camera = placed['shots'][0]['samples'][0]
    assert camera['position'] == pytest.approx([-100., 300., 130.])
    assert camera['look_at'] == pytest.approx([100., 200., 130.])
    assert camera['rotation_pitch_yaw_roll'] == [2., 0., 0.]
    assert camera['horizontal_fov_degrees'] == 35.
    assert placed['shots'][0]['trajectory_sha256'] == 'frozen'


def test_sampling_keeps_exact_frozen_keys_endpoint_and_accepted_source_clock():
    lib = library()
    result = g.prepare_geometry(lib, orientations=['portrait'], sample_step_frames=4)
    assert len(result['shots']) == 1
    camera = result['shots'][0]['samples']
    assert [r['frame_index'] for r in camera] == [0, 4, 6]
    source = lib['shots'][1]
    all_keys = source['frames'] + [source['endpoint_validation_frame']]
    for row in camera:
        assert {k: v for k, v in row.items() if k not in ('frame_index', 'endpoint')} == all_keys[row['frame_index']]
    body = result['actions'][0]['samples']
    assert [r['source_t'] for r in body] == pytest.approx([1., 1.+4/30*.5, 1.1])
    assert body[1]['bones']['root'] == pytest.approx([20/3, 4/3, 20.])
    assert camera[-1]['endpoint'] is True
    assert result['actions'][0]['activity_bounds']['maximum_xyz_cm'][2] == 33.


def test_changed_input_invalidates_fingerprint_and_cached_pin(tmp_path):
    dependency = tmp_path / 'input.json'
    dependency.write_text('original', encoding='utf-8')
    old = g.pin(dependency)
    g.verify_sources([old])
    first = g.input_fingerprint([old], {'camera': 'front'}, {'step': 15})
    dependency.write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='input changed'):
        g.verify_sources([old])
    assert g.input_fingerprint([g.pin(dependency)], {'camera': 'front'}, {'step': 15}) != first
    assert g.input_fingerprint([old], {'camera': 'front'}, {'step': 1}) != first


@pytest.fixture
def correction_library(tmp_path, monkeypatch):
    """Small keys, complete identity matrix; all real pin verification retained."""
    ids=list(g.CORRECTED_MOTIONS)+['other_'+str(i) for i in range(22)]
    nonface=[];face=[]
    for motion in ids:
        for camera in ['camera_'+str(i) for i in range(20)]+['front_head']:
            for orientation in ('landscape','portrait'):
                shot=copy.deepcopy(library()['shots'][0])
                shot.update(shot_id=motion+'_'+camera+'_'+orientation,motion_id=motion,
                            camera_id=camera,orientation=orientation)
                (face if camera=='front_head' else nonface).append(shot)
    sample_path=tmp_path/'samples.json'
    sample_path.write_text(json.dumps({'success':True,'source_assets_unchanged':True,
                                      'fps':10,'clips':[]}),encoding='utf-8')
    plan_paths=[tmp_path/'nonface.json',tmp_path/'face.json']
    for path,shots in zip(plan_paths,(nonface,face)):
        path.write_text(json.dumps({'source_samples_sha256':g.pin(sample_path)['sha256'],
                                   'shots':shots}),encoding='utf-8')
    monkeypatch.setattr(g,'PLAN_PINS',tuple(g.pin(p) for p in plan_paths))
    monkeypatch.setattr(g,'SAMPLES',sample_path)
    path=tmp_path/'correction.json';monkeypatch.setattr(g,'FOLLOW_CORRECTION',path)
    patched=[copy.deepcopy(s) for s in nonface if s['motion_id'] in g.CORRECTED_MOTIONS]
    for shot in patched:
        shot['frames'][0]['position'][0]=-500.
        shot['trajectory_sha256']='corrected'
    document={'schema':'camera_follow_correction_v2','success':True,
              'basepins':[g.pin(p) for p in plan_paths],'corrected_shots':patched}
    acceptance=tmp_path/'acceptance.json'
    acceptance.write_text(json.dumps({'horizontal':{'accepted_distance_factor_from_original':.75,
                                                  'compensate_fov':True}}),encoding='utf-8')
    config={'schema':standard.SCHEMA,
            'standard_id':'nonface_landscape_distance075_fov_compensated_v2',
            'landscape_distance_factor':.75,'scope':'nonface_landscape',
            'excluded_camera_ids':['front_head'],'compensate_horizontal_fov':True,
            'source_pins':[{**g.pin(plan_paths[0]),'role':'original_nonface_plan'},
                           {**g.pin(acceptance),'role':'user_acceptance'}]}
    config_path=tmp_path/'standard.json'
    config_path.write_text(json.dumps(config),encoding='utf-8')
    monkeypatch.setattr(g,'CAMERA_STANDARD',config_path)
    def save():path.write_text(json.dumps(document),encoding='utf-8')
    save()
    return document,save,nonface+face


def test_load_library_applies_exact_correction_and_pins_it(correction_library):
    document,save,base=correction_library
    loaded=g.load_library()
    actual={s['shot_id']:s for s in loaded['shots']}
    patched={s['shot_id']:s for s in document['corrected_shots']}
    config=standard.load_config(g.CAMERA_STANDARD)
    assert len(actual)==1260
    for shot in base:
        assert actual[shot['shot_id']]==standard.apply_standard(patched.get(shot['shot_id'],shot),config)
    assert sum(standard.MARKER in s for s in actual.values())==600
    assert all(actual[s['shot_id']]==s for s in base if s['camera_id']=='front_head')
    assert g.pin(g.FOLLOW_CORRECTION) in loaded['sources']
    assert all(p in loaded['sources'] for p in document['basepins'])
    assert g.pin(g.CAMERA_STANDARD) in loaded['sources']
    assert g.pin(standard.__file__) in loaded['sources']
    assert all(p in loaded['sources'] for p in config['source_pins'])


@pytest.mark.parametrize('field',g.CLOCK_FIELDS)
def test_follow_correction_rejects_changed_source_clock(correction_library,field):
    document,save,_=correction_library
    shot=document['corrected_shots'][0]
    shot[field]=shot[field]+'_different' if isinstance(shot[field],str) else shot[field]+1
    save()
    with pytest.raises(ValueError,match='protected action clock or scope'):
        g.load_library()


@pytest.mark.parametrize('bad_scope',['other_action','face','unknown','missing'])
def test_follow_correction_rejects_scope_expansion(correction_library,bad_scope):
    document,save,base=correction_library
    if bad_scope=='missing':document['corrected_shots'].pop()
    elif bad_scope=='unknown':document['corrected_shots'][0]['shot_id']='not_in_original'
    else:
        replacement=next(s for s in base if (s['motion_id']=='other_0' if bad_scope=='other_action'
                         else s['camera_id']=='front_head'))
        document['corrected_shots'][0]=copy.deepcopy(replacement)
    save()
    with pytest.raises(ValueError,match='correction|protected action clock or scope'):
        g.load_library()


def test_follow_correction_rejects_changed_pinned_base(correction_library):
    document,save,_=correction_library
    document['basepins'][0]['sha256']='0'*64
    save()
    with pytest.raises(ValueError,match='input changed'):
        g.load_library()


def test_duplicate_correction_rows_cannot_hide_oversized_raw_scope(correction_library):
    document,save,_=correction_library
    document['corrected_shots'].append(copy.deepcopy(document['corrected_shots'][0]))
    save()
    with pytest.raises(ValueError,match='correction'):
        g.load_library()


def test_acceptance_pin_is_transitively_revalidated_by_cached_geometry(correction_library):
    loaded=g.load_library()
    config=standard.load_config(g.CAMERA_STANDARD)
    acceptance=next(p for p in config['source_pins'] if p['role']=='user_acceptance')
    Path(acceptance['path']).write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='input changed'):
        g.verify_sources(loaded['sources'])


@pytest.mark.parametrize('field,value',[
    ('motion_id','ACT_F02_CATCH_BREATH'),('sex','male'),
    ('camera_id','front_head'),('orientation','portrait'),('width',99),('height',99)])
def test_follow_correction_cannot_change_replacement_identity(correction_library,field,value):
    document,save,_=correction_library
    document['corrected_shots'][0][field]=value
    save()
    with pytest.raises(ValueError,match='protected|identity|scope'):
        g.load_library()
