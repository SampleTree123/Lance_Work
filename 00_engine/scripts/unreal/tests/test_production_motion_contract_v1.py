"""Semantic clocks and camera synchronization for the approved26 motion rules."""
import copy
import importlib.util
import math
import json
from pathlib import Path
import sys
import pytest

SCRIPTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))
import production_motion_contract_v1 as m
import ue_production_motion_library_v1 as ue


@pytest.fixture(scope='module')
def motions():return {x['motion_id']:x for x in m.load_contract()['motions']}


def one(motions,mid,t):
    rows=m.map_output_time(motions[mid],t)
    assert len(rows)==1
    return rows[0]['source_seconds']


def test_exact_retained26_and_both_sexes(motions):
    assert len(motions)==26
    assert not set(motions)&set(m.REMOVED)
    assert all(set(x['variants'])=={'female','male'} for x in motions.values())


def test_selected_offset_trim_and_existing_walk_clock(motions):
    assert one(motions,'MOTION_CAND_035',0)==5.9
    assert one(motions,'MOTION_CAND_035',10)==pytest.approx(15.9)
    assert one(motions,'MOTION_CAND_008',5)==3
    assert one(motions,'MOTION_CAND_008',10)==6
    assert one(motions,'MOTION_CAND_036',10)==7
    assert one(motions,'ACT_M04_LIVING_ROOM_SWING',10)==10


@pytest.mark.parametrize('mid',['MOTION_CAND_022','MOTION_CAND_024','ACT_F06_ELEVATOR_GREETING','ACT_M05_ELEVATOR_GREETING'])
def test_nine_second_slowdown_then_hold(motions,mid):
    entry=motions[mid];end=entry['selected_clock']['source_end_seconds']
    assert one(motions,mid,4.5)==pytest.approx(end/2)
    assert one(motions,mid,9)==pytest.approx(end)
    assert one(motions,mid,9.9)==pytest.approx(end)
    assert one(motions,mid,10)==pytest.approx(end)


def test_jump_holds_both_ends(motions):
    mid='MOTION_CAND_033';end=motions[mid]['selected_clock']['source_end_seconds']
    assert one(motions,mid,.9)==0
    assert one(motions,mid,5)==pytest.approx(end/2)
    assert one(motions,mid,9.5)==pytest.approx(end)


@pytest.mark.parametrize('mid',['MOTION_CAND_017','MOTION_CAND_019','MOTION_CAND_020','ACT_F05_TIE_SHOES','ACT_F01_SEXY_DANCE'])
def test_short_body_slowed_entire_selected_window(motions,mid):
    entry=motions[mid];end=entry['selected_clock']['source_end_seconds']
    assert one(motions,mid,5)==pytest.approx(end/2)
    assert one(motions,mid,10)==pytest.approx(end)


@pytest.mark.parametrize('mid',['MOTION_CAND_023','ACT_F03_AUDIENCE_01'])
def test_two_cycles_and_continuous_weighted_seam(motions,mid):
    entry=motions[mid];end=entry['production10']['source_end_seconds']
    assert one(motions,mid,2.5)==pytest.approx(end/2)
    assert one(motions,mid,7.5)==pytest.approx(end/2)
    assert one(motions,mid,10)==pytest.approx(end)
    center=m.map_output_time(entry,5)
    assert [x['weight'] for x in center]==pytest.approx([.5,.5])
    # A discontinuous source-end ->source-start scalar must be continuous after
    # the weighted seam. Test around both seam boundaries and center.
    value=lambda t:sum(x['source_seconds']*x['weight'] for x in m.map_output_time(entry,t))
    for t in (4.9,5,5.1):assert abs(value(t-1e-7)-value(t+1e-7))<1e-4


def test_full_preview_and_entire_source_are_distinct(motions):
    entry=motions['MOTION_CAND_035']
    assert m.duration(entry,'full')==21.3
    assert m.duration(entry,'source_full','male')>34
    assert m.map_output_time(entry,0,'full')[0]['source_seconds']==5.9
    assert m.map_output_time(entry,0,'source_full','male')[0]['source_seconds']==0


def test_camera_same_clock_holds_repeat_and_offset(motions):
    keys=[{'t':i/10,'center':[i/10,2*i/10,0],'lens':50.} for i in range(351)]
    for mid in ('MOTION_CAND_035','MOTION_CAND_023','MOTION_CAND_033'):
        result=m.retime_camera_keys(motions[mid],keys)
        assert len(result)==301
        for row in result:
            expected=sum(x['weight']*x['source_seconds'] for x in m.map_output_time(motions[mid],row['t']))
            assert row['center'][0]==pytest.approx(expected)
            assert row['center'][1]==pytest.approx(expected*2)


def test_landmark_clock_matches_body(motions):
    mid='MOTION_CAND_023'
    clip={'motion_id':mid,'sex':'female','asset':'/Game/Test','frames':[{'t':i/10,'bones':{'root':[i/10,0,0]}} for i in range(61)]}
    result=m.retime_clip_samples(motions[mid],clip)
    assert len(result['frames'])==301
    assert result['seam_landmarks_require_baked_UE_resample']
    assert clip['frames'][0]['t']==0
    for row in result['frames']:
        assert row['bones']['root'][0]==pytest.approx(sum(x['weight']*x['source_seconds'] for x in m.map_output_time(motions[mid],row['t'])))


def test_bad_times_and_out_of_source_contract_rejected(motions):
    entry=motions['MOTION_CAND_008']
    for t in (-1,10.1,float('nan'),True):
        with pytest.raises(ValueError):m.map_output_time(entry,t)
    data=copy.deepcopy(m.load_contract());data['motions'][0]['production10']['source_end_seconds']=999
    with pytest.raises(ValueError):m.validate_contract(data)


def test_ue_import_is_offline_and_task_boundaries(tmp_path):
    task=m.build_tasks()[0]
    assert ue.validate_task(task)[0]['motion_id']==task['motion_id']
    invalid=dict(task,report_path=str(tmp_path/'escaped.json'))
    with pytest.raises(ValueError):ue.validate_task(invalid)
    invalid=dict(task,sex='unknown')
    with pytest.raises(ValueError):ue.validate_task(invalid)
    assert 'unreal' not in ue.__dict__


def test_receipt_pending_and_bad_proof_rejected(tmp_path,motions):
    entry=motions['MOTION_CAND_023'];sex='female';variant=entry['variants'][sex]
    assert m.receipt_variant(entry,sex,tmp_path,False) is None
    path=tmp_path/'assets'/(entry['motion_id']+'_'+sex+'.json');path.parent.mkdir()
    formal=lambda destination:{'asset':destination+'.'+destination.rsplit('/',1)[1],'path':'test.uasset','sha256':'0'*64}
    report={'schema':'production_motion_bake_v1','success':True,'task':{'motion_id':entry['motion_id'],'sex':sex,'contract':m.pin(m.CONTRACT),'report_path':str(path)},
        'sources_unchanged':True,'new_dirty_packages_outside_target':[],'dirty_sources':[],'faces_included':False,
        'source_asset_record':formal(variant['source_destination']),'asset_record':formal(variant['production_destination']),
        'sources':[variant['source']],
        'verification':{'duration_seconds':10.,'all_frames_verified':True,'bone_count':118,'body_tracks':108,
            'physical_limits':ue.LIMITS,'maximum_physical_errors':{k:0. for k in ue.LIMITS},'maximum_curve_error':0.,'maximum_root_component_error':0.,'fps':60.,'all_frame_count':601}}
    path.write_text(json.dumps(report),encoding='utf-8')
    assert m.receipt_variant(entry,sex,tmp_path,False)['production10']['asset']==report['asset_record']['asset']
    report['verification']['all_frame_count']=600;path.write_text(json.dumps(report),encoding='utf-8')
    with pytest.raises(ValueError):m.receipt_variant(entry,sex,tmp_path,False)
    report['verification']['all_frame_count']=601;report['sources_unchanged']=False;path.write_text(json.dumps(report),encoding='utf-8')
    with pytest.raises(ValueError):m.receipt_variant(entry,sex,tmp_path,False)


def test_only_native_constant_scale_simplification_can_exceed_strict_gate():
    expected={'pelvis':[[1.,1.,1.],[1.0000643,1.,1.],[1.00002,1.,1.]]}
    actual={'pelvis':[[1.,1.,1.]]*3}
    proof=ue.scale_constant_proof(expected,actual)
    assert proof['success']
    assert proof['channels'][0]['bone']=='pelvis'
    assert proof['channels'][0]['maximum_error']==pytest.approx(.0000643)
    expected['pelvis'][1][0]=1.00011
    assert not ue.scale_constant_proof(expected,actual)['success']
    expected['pelvis'][1][0]=1.0000643
    actual['pelvis'][1][0]=1.00002
    assert not ue.scale_constant_proof(expected,actual)['success']


def test_rotation_exception_requires_matching_native_singularity_projection():
    # Frozen real native-eye evidence from this same UE controller storage path.
    expected=[8.,-7.,3.,.7071114778518677,-.00011229505616938695,.7071018218994141,.000548982119653374,1.,1.,1.]
    actual=[8.,-7.,3.,.7071065680411545,-.0005490291978916465,.7071065680411546,.0005490291978916466,1.,1.,1.]
    row={'bone':'evidence','frame':1,'time_seconds':1/30,'error':.0500521648,'expected_local_transform':expected,'actual_local_transform':actual}
    proof=ue.rotation_singularity_proof([row])
    assert proof['success']
    assert proof['samples'][0]['predicted_actual_max_quaternion_component_error']<1e-6
    row['error']=.13
    assert not ue.rotation_singularity_proof([row])['success']
    row['error']=.05;row['actual_local_transform']=list(expected)
    assert not ue.rotation_singularity_proof([row])['success']
    row['expected_local_transform']=[0.,0.,0.,0.,0.,0.,1.,1.,1.,1.]
    assert not ue.rotation_singularity_proof([row])['success']
