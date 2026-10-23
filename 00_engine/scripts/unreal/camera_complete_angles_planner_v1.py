"""Seven-source complete-angle diagnostic camera matrix; preserves stable-follow v1."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import camera_stable_follow_planner_v1 as stable

ACTIONS=[('stand','调整站姿',1),('bend','弯腰伸展',7),('walk','向前行走',13),('turn','甩头转身',12),('dance','舒展舞步',21),('thinking','边走边思考',28),('curious','好奇探看',32)]

def presets():
    out=[]
    for framing,label in [('full','全身'),('upper','上半身')]:
        for direction,name,angle in [('front','正面',0),('front_three_quarter','前侧',45),('side','侧面',90),('rear_three_quarter','后侧面',135),('back','背面',180)]:
            out.append(dict(id=direction+'_'+framing,label=name+label,azimuth=angle,elevation=0,start=framing,end=framing,kind='follow',orbit=0))
    out.extend(p for p in stable.presets() if p['id'] in {'front_head','high_full','low_full','orbit_360','orbit_120','dolly_in_front','dolly_in_side','dolly_in_back','dolly_out_front','dolly_out_side','dolly_out_back'})
    return out


def build(prior,output):
    prior=Path(prior);output=Path(output);pins=[]
    def read(name):
        path=prior/name;data=path.read_bytes();pins.append({'path':str(path.resolve()),'sha256':hashlib.sha256(data).hexdigest()});return json.loads(data)
    sources={};clips={}
    for name in ['camera_motion_pilot_plan_v3.json','retime_pilot_plan_v1.json']:
        sources.update({int(s['shot_id'].split('_')[1]):s for s in read(name)['shots']})
    for name in ['motion_samples_v1.json','retime_motion_samples_v1.json']:
        clips.update({s['clip_id']:s for s in read(name)['clips']})
    shots=[]
    for action in ACTIONS:
        source=sources[action[2]];frames=stable.old.resample(clips[source['clip_id']],10,30)
        for preset in presets():
            shot=stable.make_shot(frames,preset,source,action,201+len(shots));shot['shot_id']=shot['shot_id'].replace('_stable_','_angles_');shots.append(shot)
    plan={'schema':'camera_motion_pilot_plan_v1','unified_duration_seconds':10,'fps':30,'frame_count':300,'aspect_ratio':16/9,'shots':shots,'rejected':[],'geometry_pass_count':len(shots),'geometry_pass_scope':'renderable diagnostic trajectory only; strict framing separately recorded','human_visual_acceptance':'pending','source_pins':pins,'stable_follow_policy':{'algorithm_owner':'camera_stable_follow_planner_v1.py','horizontal_trend_sigma_seconds':1.15,'horizontal_deadzone_cm':18,'deadzone_resmoothing_sigma_seconds':.45,'closeup_local_sigma_seconds':.7,'closeup_adaptation_gain':.8,'full_body_vertical_target':'segment constant','facing':'source initial yaw, no heading pursuit','dolly_finish_seconds':7,'dolly_hold_seconds':3},'limitations':['147 diagnostic combinations, not production whitelist','closeup excursions explicitly retained for user review','source body/face/identity and existing retiming remain unchanged','strict dolly framing diagnostics check start and 7–10 second target hold, not transitional boundaries']}
    output.mkdir(parents=True,exist_ok=True);target=output/'expansion_plan_v1.json'
    if target.exists():raise FileExistsError('Refuse overwrite of frozen plan')
    target.write_text(json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return plan


def audit(prior,output):
    output=Path(output);path=output/'expansion_plan_v1.json';plan=json.loads(path.read_text(encoding='utf-8'));sources={};clips={};pins=[]
    for pin in plan['source_pins']:
        data=Path(pin['path']).read_bytes();pins.append(dict(pin,match=hashlib.sha256(data).hexdigest()==pin['sha256']));parsed=json.loads(data)
        sources.update({s['shot_id']:s for s in parsed.get('shots',[])})
        clips.update({c['clip_id']:c for c in parsed.get('clips',[])})
    reports=[];cache={cid:stable.old.resample(clips[cid],10,30) for cid in {s['clip_id'] for s in plan['shots']}}
    for s in plan['shots']:
        frames=cache[s['clip_id']];preset=next(p for p in presets() if p['id']==s['stable_preset_id']);rows=s['frames']+[s['endpoint_validation_frame']];source=sources[s['source_shot_id']]
        again=stable.trajectory(frames,preset,s['endpoint_distances_cm'],source['yaw_offset_degrees']);offset=np.array([stable.old.sub(r['position'],r['look_at']) for r in rows]);angles=np.degrees(np.unwrap(np.arctan2(offset[:,1],offset[:,0])));distance=np.linalg.norm(offset,axis=1)
        depths={fr:float(stable.projections(frames,rows,fr)[1].min()) for fr in {preset['start'],preset['end']}};initial_error=(angles[0]-source['yaw_offset_degrees']-preset['azimuth']+180)%360-180
        digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        checks={'frame_count_301':len(rows)==301,'timestamps_30fps':np.allclose([r['t'] for r in rows],np.arange(301)/30,atol=1e-9),'trajectory_hash':digest==s['trajectory_sha256'],'independent_reconstruction':rows==again,'initial_yaw':abs(initial_error)<1e-8,'orbit_or_no_heading_chase':abs(angles[-1]-angles[0]-preset['orbit'])<1e-8,'finite':all(stable.old.finite_vector(r[k]) for r in rows for k in ['position','look_at','rotation_pitch_yaw_roll']),'above_floor':min(r['position'][2] for r in rows)>=25,'positive_depth':min(depths.values())>1,'source_window_preserved':s.get('window_start_seconds',0)==source.get('window_start_seconds',0)}
        rec={'shot_id':s['shot_id'],'checks':checks,'initial_yaw_error_degrees':float(initial_error),'actual_orbit_degrees':float(angles[-1]-angles[0]),'expected_orbit_degrees':preset['orbit'],'min_semantic_depth_cm':depths,'min_camera_z_cm':min(r['position'][2] for r in rows),'strict_framing_pass':s['quality']['strict_framing_pass'],'strict_proxy_excursion_counts':{k:len(v['outside_proxy_times']) for k,v in s['quality']['framing_diagnostics'].items()}}
        if preset['kind'].startswith('dolly'):
            checks['relative_vector_hold_after_7_seconds']=np.max(np.abs(offset[210:]-offset[210]))<1e-8;checks['target_distance_reached_at_7_seconds']=abs(distance[210]-s['endpoint_distances_cm'][1])<1e-8
            rec['dolly_hold']={'distance_at_7_seconds_cm':float(distance[210]),'distance_range_after_7_seconds_cm':float(np.ptp(distance[210:])),'camera_motion_after_7_seconds_cm':stable.old.norm(stable.old.sub(rows[-1]['position'],rows[210]['position']))}
        reports.append(rec)
    expected={(a[0],p['id']) for a in ACTIONS for p in presets()};actual={(s['stable_action_id'],s['stable_preset_id']) for s in plan['shots']}
    out={'schema':'complete_angles_geometry_audit_v1','plan_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'success':len(plan['shots'])==147 and actual==expected and all(p['match'] for p in pins) and all(all(r['checks'].values()) for r in reports),'matrix':{'expected':147,'actual_unique':len(actual),'missing':sorted(expected-actual),'unexpected':sorted(actual-expected)},'source_pins':pins,'sampled_frames_including_endpoints':len(reports)*301,'strict_proxy_pass_count':sum(r['strict_framing_pass'] for r in reports),'shots':reports,'limitations':plan['limitations']+['Bone proxies and reconstruction only; no mesh silhouette, occlusion, temporal comfort or user acceptance certification.']}
    (output/'complete_angles_geometry_audit_v1.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=lambda x:x.item())+'\n',encoding='utf-8');return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();build(a.prior,a.output);result=audit(a.prior,a.output);print(json.dumps({'success':result['success'],'shots':result['matrix']['actual_unique'],'strict_proxy_pass_count':result['strict_proxy_pass_count']}))
