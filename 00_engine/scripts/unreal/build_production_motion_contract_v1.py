"""Build the 26-action policy from the selected review clocks and accepted pairs."""
from __future__ import annotations
import json
from pathlib import Path
import production_motion_contract_v1 as contract


def build():
    engine=contract.ENGINE
    catalog=engine/'outputs/scene_site_review_20261014_v1/site_review_catalog_v1.json'
    samples=engine/'outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1/all_motion_samples_v1.json'
    legacy=engine/'outputs/camera_motion_scene_alignment_20261012_v1/legacy_motion/legacy_cross_sex_candidates_v1.json'
    acceptance=legacy.with_name('user_cross_sex_acceptance_20261012_v1.json')
    sample_index={(row['motion_id'],row['sex']):row for row in contract.read(samples)['clips']}
    old_index={row['motion_id']:row for row in contract.read(legacy)['records']}
    names={'ACT_F03_AUDIENCE_01':'观众回应','ACT_F02_CATCH_BREATH':'喘气恢复',
           'ACT_F05_TIE_SHOES':'系鞋带','ACT_F06_ELEVATOR_GREETING':'打招呼A',
           'ACT_F01_SEXY_DANCE':'舒展舞蹈','ACT_M05_ELEVATOR_GREETING':'打招呼B',
           'ACT_M04_LIVING_ROOM_SWING':'摇摆舞','ACT_M06_CHEER_HANDS_STEP_DANCE':'踏步欢舞'}
    motions=[]
    for action in contract.read(catalog)['actions']:
        mid=action['motion_id']
        if mid in contract.REMOVED:continue
        clock=action['clock']
        start=clock['source_start_seconds'];end=clock['source_end_seconds']
        p={'duration_seconds':10.,'source_start_seconds':start,'source_end_seconds':end,
           'hold_start_seconds':0.,'hold_end_seconds':0.,'repeat_count':1,'seam_transition_seconds':0.}
        rule='selected_window_first10_original_rate'
        if clock['duration_seconds'] >= 10:
            p['source_end_seconds']=start+10*clock['source_body_play_rate']
        else:rule='selected_window_uniform_slowdown_to10'
        if mid=='MOTION_CAND_008':
            p.update(source_start_seconds=0.,source_end_seconds=6.);rule='preserve_first6_at_0.6'
        if mid in ('MOTION_CAND_022','MOTION_CAND_024','ACT_F06_ELEVATOR_GREETING','ACT_M05_ELEVATOR_GREETING'):
            p['hold_end_seconds']=1.;rule='slow_body_to9_hold_end1'
        if mid=='MOTION_CAND_033':
            p.update(hold_start_seconds=1.,hold_end_seconds=1.);rule='hold_start1_slow_body8_hold_end1'
        if mid in ('MOTION_CAND_023','ACT_F03_AUDIENCE_01'):
            p.update(repeat_count=2,seam_transition_seconds=.2);rule='first5_repeat_twice_smooth_seam' if mid=='MOTION_CAND_023' else 'slow_body5_repeat_twice_smooth_seam'
            if mid=='MOTION_CAND_023':p['source_end_seconds']=p['source_start_seconds']+5.
        if mid=='MOTION_CAND_036':
            p.update(source_start_seconds=0.,source_end_seconds=7.);rule='selected_first7_uniform_slowdown_to10'
        p['rule']=rule
        active=10-p['hold_start_seconds']-p['hold_end_seconds']
        p['body_play_rate']=(p['source_end_seconds']-p['source_start_seconds'])/(active/p['repeat_count'])
        variants={}
        for sex in ('female','male'):
            if mid in old_index:
                old=old_index[mid]['variants'][sex]
                source=old['body_asset']; proof=old['numeric_validation']; origin=old['origin_type']
                native=sample_index[(mid,action['sex'])]
                source_duration=native['duration_seconds'];frame_rate=native['source_frame_rate'];frames=native['source_frame_count']
                skeleton=old['target_shared_skeleton']['asset']
            else:
                native=sample_index[(mid,sex)]
                source=native['source_package'];source_duration=native['duration_seconds'];frame_rate=native['source_frame_rate'];frames=native['source_frame_count']
                skeleton=native['source_skeleton'];proof=[];origin='native_sex_export_bodyonly'
            variants[sex]={'source':source,'source_duration_seconds':source_duration,'source_frame_rate':frame_rate,
                'source_frame_count':frames,'shared_skeleton':skeleton,'origin_type':origin,'numeric_validation':proof,
                'source_destination':contract.SOURCE_ROOT+'/'+sex+'/A_'+mid+'_Source',
                'production_destination':contract.PRODUCTION_ROOT+'/'+sex+'/A_'+mid+'_10s',
                'source_created':False,'production_created':False}
        motions.append({'motion_id':mid,'label_zh':names.get(mid,action['motion_label']),
            'preview_sex':action['sex'],'selected_clock':clock,'production10':p,'variants':variants,
            'visual_acceptance':'pending_new_10s_review'})
    data={'schema':'production_motion_library_v1','created_date':'2026-10-17','status':'offline_contract_assets_pending',
        'removed_motion_ids':list(contract.REMOVED),'sources':[contract.pin(p) for p in (catalog,samples,legacy,acceptance)],
        'views':{'full':'Preserve existing selected review clock','source_full':'Entire reusable original source clip',
                 'production10':'Exactly 10 seconds with the user-approved trim/slow/hold/repeat policy'},
        'camera_policy':'Body and camera use map_output_time; retime or regenerate trajectories. Never reuse unchanged old duration keys.',
        'repeat_seam_policy':'0.2s smoothstep local-pose blend centered at5s, no root rebasing. Visual naturalness remains pending.',
        'face_policy':'BodyOnly output; accepted native face is composed afterwards on its independent unchanged clock.',
        'motions':motions}
    return contract.validate_contract(data)


if __name__=='__main__':
    data=build()
    contract.CONTRACT.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(str(contract.CONTRACT))
