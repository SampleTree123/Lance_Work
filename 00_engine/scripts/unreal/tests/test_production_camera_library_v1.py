"""Accepted composition, output-clock movement and cached camera retiming."""
import copy
import math
from pathlib import Path
import sys
import numpy as np
import pytest
SCRIPTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))
import build_production_camera_library_v1 as camera
import production_motion_contract_v1 as motion


@pytest.fixture(scope='module')
def entries():return {x['motion_id']:x for x in motion.load_contract()['motions']}


def shot(entry,cid='front_full',kind='follow',orbit=0,start='full',end='full',distance=600.,enddistance=None):
    clock=entry['selected_clock'];n=clock['frame_count'];enddistance=distance if enddistance is None else enddistance
    keys=[]
    for i in range(n+1):
        t=i/30;u=min(1.,t/7);u=u*u*(3-2*u) if kind.startswith('dolly') else 0.
        aim=np.array([2*t,0.,80. if start=='full' else 130.])
        pos=aim+np.array([0.,distance*(1-u)+enddistance*u,0.])
        keys.append(camera.camera_row(t,pos.tolist(),aim.tolist(),49.23 if cid=='front_head' else 35.))
    return dict(clock,shot_id='old_'+cid,motion_id=entry['motion_id'],sex=entry['preview_sex'],camera_id=cid,
        motion_label=entry['label_zh'],orientation='landscape',camera_label=cid,width=1280,height=720,
        common_preset_parameters={'preset':{'kind':kind,'start':start,'end':end,'orbit':orbit}},
        frames=keys[:-1],endpoint_validation_frame=keys[-1])


def library(entry):
    full=shot(entry);upper=shot(entry,'front_upper',start='upper',end='upper',distance=300.)
    return {(entry['motion_id'],'landscape','front_full'):full,(entry['motion_id'],'landscape','front_upper'):upper}


def distance(row):return np.linalg.norm(np.asarray(row['position'])-np.asarray(row['look_at']))


def test_orbit_finishes360_at10_and_never_resets_on_repeat(entries):
    entry=entries['MOTION_CAND_023'];old=shot(entry,'orbit_360','orbit',360)
    result=camera.make_shot(entry,old,library(entry),'production10')
    rows=camera.rows(result)
    angles=np.unwrap([math.atan2(r['position'][1]-r['look_at'][1],r['position'][0]-r['look_at'][0]) for r in rows])
    assert math.degrees(angles[-1]-angles[0])==pytest.approx(360)
    assert math.degrees(angles[150]-angles[149])==pytest.approx(1.2)
    assert all(distance(r)==pytest.approx(600.) for r in rows)
    assert all(r['horizontal_fov_degrees']==35. for r in rows)


def test_dolly_finishes_by7_even_when_body_is_repeating(entries):
    entry=entries['MOTION_CAND_023'];old=shot(entry,'dolly_in_front','dolly_in',start='full',end='upper',distance=600.,enddistance=300.)
    # Old clip is shorter than7; supply the accepted target endpoint explicitly.
    old['endpoint_validation_frame']['position']=(np.asarray(old['endpoint_validation_frame']['look_at'])+[0,300,0]).tolist()
    rows=camera.rows(camera.make_shot(entry,old,library(entry),'production10'))
    assert distance(rows[0])==pytest.approx(600.)
    assert distance(rows[210])==pytest.approx(300.)
    assert distance(rows[-1])==pytest.approx(300.)
    assert distance(rows[150])<distance(rows[149])


def test_hold_stops_follow_while_orbit_keeps_moving(entries):
    entry=entries['MOTION_CAND_033'];lookup=library(entry)
    follow=camera.rows(camera.make_shot(entry,lookup[(entry['motion_id'],'landscape','front_full')],lookup,'production10'))
    assert follow[0]['look_at']==follow[29]['look_at']
    assert follow[270]['look_at']==follow[-1]['look_at']
    orbit=camera.rows(camera.make_shot(entry,shot(entry,'orbit_360','orbit',360),lookup,'production10'))
    assert orbit[0]['look_at']==orbit[29]['look_at']
    assert orbit[0]['position']!=orbit[29]['position']


def test_face_uses_weighted_body_map_and_preserves_offset_lens(entries):
    entry=entries['MOTION_CAND_023'];old=shot(entry,'front_head',distance=230.)
    rows=camera.rows(camera.make_shot(entry,old,library(entry),'production10'))
    for row in rows:
        weighted=sum(v['source_seconds']*v['weight'] for v in motion.map_output_time(entry,row['t']))
        assert row['look_at'][0]==pytest.approx(weighted*2)
        assert distance(row)==pytest.approx(230.)
        assert row['horizontal_fov_degrees']==49.23
    assert np.linalg.norm(np.asarray(rows[150]['look_at'])-rows[149]['look_at'])<3


def test_full_keeps_accepted_keys_and_formal_clip_identity(entries,monkeypatch):
    entry=entries['MOTION_CAND_035'];old=shot(entry)
    result=camera.make_shot(entry,old,library(entry),'full')
    assert camera.rows(result)==camera.rows(old)
    assert result['source_start_seconds']==5.9
    source={'clip_id':old['source_clip_id'],'animation_path':old['source_animation'],'asset':old['source_animation'],'frames':[{'t':0.,'bones':{'root':[0,0,0]}}]}
    clip=camera.make_clip(entry,old,source,'full')
    assert clip['clip_id']==result['source_clip_id']
    assert clip['animation_path']==result['source_animation']==clip['asset']
    assert clip['frames']==source['frames']


def test_shared_target_arrays_cached_across_camera_views(entries,monkeypatch):
    entry=entries['MOTION_CAND_023'];lookup=library(entry);cache={};count=0
    original=camera.KeySampler.__init__
    def track(self,keys):
        nonlocal count
        count+=1;original(self,keys)
    monkeypatch.setattr(camera.KeySampler,'__init__',track)
    for cid in ('front_full','side_full','orbit_360'):
        camera.make_shot(entry,shot(entry,cid,'orbit' if cid=='orbit_360' else 'follow',360 if cid=='orbit_360' else 0),lookup,'production10',cache)
    assert count==1
    assert len(cache)==1


def test_actual_baked_landmarks_used_and_bound_to_geometry(entries,monkeypatch):
    entry=entries['MOTION_CAND_023'];old=shot(entry)
    expected={'motion_id':entry['motion_id'],'sex':'female','frames':[{'t':0,'bones':{'root':[99,0,0]}},{'t':10,'bones':{'root':[100,0,0]}}],'duration_seconds':10.,'fps':10}
    monkeypatch.setattr(motion,'receipt_variant',lambda *a,**k:{'receipt':{'path':'receipt.json','sha256':'proof'}})
    monkeypatch.setattr(motion,'read',lambda *a:{'production_landmarks':expected})
    clip=camera.make_clip(entry,old,{},'production10')
    assert clip['frames']==expected['frames']
    assert clip['landmark_provenance']['kind']=='actual_baked_UE_world_pose'
    assert clip['seam_landmarks_require_baked_UE_resample'] is False
    result=camera.make_shot(entry,old,library(entry),'production10')
    assert clip['animation_path']==result['source_animation']
    assert camera.geo._body_frames(clip,result)[-1]['bones']['root']==[100,0,0]


def test_interpolation_outside_accepted_clock_rejected():
    keys=[{'t':0.,'look_at':[0,0,0],'position':[1,0,0],'horizontal_fov_degrees':35.},
          {'t':1.,'look_at':[1,0,0],'position':[2,0,0],'horizontal_fov_degrees':35.}]
    with pytest.raises(ValueError):camera.KeySampler(keys).sample(2.,'look_at')


@pytest.mark.parametrize('cid,kind,orbit,start,end',[
    ('orbit_360','orbit',360,'full','full'),
    ('orbit_120','orbit',120,'full','full'),
    *[(f'dolly_{direction}_{angle}',f'dolly_{direction}',0,
       'full' if direction=='in' else 'upper','upper' if direction=='in' else 'full')
      for direction in ('in','out') for angle in ('front','side','back')]])
def test_standard_archived_preset_preserves_moving_camera_semantics(entries,cid,kind,orbit,start,end):
    entry=entries['MOTION_CAND_001'];lookup=library(entry)
    old=shot(entry,cid,kind,orbit,start,end,600. if start=='full' else 300.,300. if end=='upper' else 600.)
    direct=camera.make_shot(entry,old,lookup,'production10')
    archived=copy.deepcopy(old)
    # This is the actual metadata shape emitted by camera_standard_v3.
    archived['camera_standard_v2']={'superseded_source_diagnostics':{
        'common_preset_parameters':archived.pop('common_preset_parameters'),
        'endpoint_distances_cm':[1200.,600.]}}
    archived_before=copy.deepcopy(archived)
    result=camera.make_shot(entry,archived,lookup,'production10')
    assert archived==archived_before
    assert camera.rows(result)==camera.rows(direct)
    keys=camera.rows(result)
    assert all(row['horizontal_fov_degrees']==35. for row in keys)
    if kind=='orbit':
        angles=np.unwrap([math.atan2(row['position'][1]-row['look_at'][1],row['position'][0]-row['look_at'][0]) for row in keys])
        assert math.degrees(angles[-1]-angles[0])==pytest.approx(orbit)
        assert all(distance(row)==pytest.approx(600.) for row in keys)
    else:
        assert distance(keys[210])==pytest.approx(distance(camera.rows(old)[-1]))
        assert distance(keys[210])==pytest.approx(distance(keys[-1]))
        assert distance(keys[0])!=pytest.approx(distance(keys[-1]))
        target=camera.follow_targets(entry,lookup[(entry['motion_id'],'landscape','front_'+end)],'production10',{})
        assert keys[210]['look_at']==pytest.approx(target[210])
        assert keys[-1]['look_at']==pytest.approx(target[-1])


def test_missing_moving_preset_fails_instead_of_becoming_front_full(entries):
    entry=entries['MOTION_CAND_001'];old=shot(entry,'orbit_360','orbit',360)
    old.pop('common_preset_parameters')
    with pytest.raises(ValueError,match='accepted camera movement preset'):
        camera.make_shot(entry,old,library(entry),'production10')
    # Full mode is an exact key copy and does not need movement metadata.
    assert camera.rows(camera.make_shot(entry,old,library(entry),'full'))==camera.rows(old)
