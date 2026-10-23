"""Offline variable-duration, aspect-aware stable cameras. SCENE_CAMERA_SEQUENCE §11."""
from pathlib import Path
import json, math, hashlib
import numpy as np
import camera_stable_follow_planner_v1 as stable
import camera_complete_angles_planner_v1 as library

RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1')

def resample(clip,start,duration,rate=1.):
    count=int(math.floor(duration*30+1e-6))
    times=np.arange(count+1)/30
    old=clip['frames']; ts=[r['t'] for r in old]
    result=[{'t':float(t),'bones':{}} for t in times]
    for bone in old[0]['bones']:
        coords=np.array([r['bones'][bone] for r in old])
        vals=np.array([np.interp(start+times*rate,ts,coords[:,k]) for k in range(3)]).T
        for row,v in zip(result,vals):row['bones'][bone]=v.tolist()
    return result

def path(frames,preset,distances,yaw,centers):
    duration=frames[-1]['t']; rows=[]
    for i,f in enumerate(frames):
        phase=min(1.,f['t']/min(7.,duration*.7)) if preset['kind'].startswith('dolly') else 0.
        blend=stable.old.ease(phase)
        target=(1-blend)*centers[preset['start']][i]+blend*centers[preset['end']][i]
        angle=math.radians(yaw+preset['azimuth']+preset['orbit']*f['t']/duration)
        elev=math.radians(preset['elevation'])
        direction=np.array([math.cos(angle)*math.cos(elev),math.sin(angle)*math.cos(elev),math.sin(elev)])
        distance=(1-blend)*distances[0]+blend*distances[1]
        location=target+direction*distance;location[2]=max(25.,location[2])
        rows.append(stable.old.camera_row(f['t'],location.tolist(),target.tolist(),35.))
    return rows

def project(frames,rows,framing,aspect):
    points=np.array([stable.old.semantic_points(f['bones'],framing) for f in frames])
    pos=np.array([r['position'] for r in rows]); target=np.array([r['look_at'] for r in rows])
    forward=target-pos; forward/=np.linalg.norm(forward,axis=1)[:,None]
    right=np.cross(np.array([0.,0.,1.]),forward);right/=np.linalg.norm(right,axis=1)[:,None]
    up=np.cross(forward,right);delta=points-pos[:,None,:]
    depth=np.einsum('nkj,nj->nk',delta,forward)
    uv=np.stack([.5+np.einsum('nkj,nj->nk',delta,right)/(2*depth*math.tan(math.radians(17.5))),.5-np.einsum('nkj,nj->nk',delta,up)*aspect/(2*depth*math.tan(math.radians(17.5)))],axis=-1)
    return uv,depth

def fit(frames,preset,framing,yaw,centers,aspect):
    fixed=dict(preset,start=framing,end=framing);lo,hi=60.,2500.
    for _ in range(16):
        dist=(lo+hi)/2
        uv,depth=project(frames,path(frames,fixed,[dist,dist],yaw,centers),framing,aspect)
        over=np.maximum(np.abs(uv[:,:,0]-.5),np.abs(uv[:,:,1]-.5)).max(axis=1)
        if depth.min()<=1 or np.quantile(over,1. if framing=='full' else .9)>.43:lo=dist
        else:hi=dist
    return hi*1.015

def shot(clip,decision,sex,preset,orientation,group,limit=None):
    start=decision['window_start_seconds']; rate=decision['body_play_rate']
    duration=decision['output_duration_seconds']
    if limit:duration=min(duration,limit)
    frames=resample(clip,start,duration,rate)
    centers=stable.centers_for(frames)
    try:facing=stable.old.initial_foot_forward_evidence(frames[0])
    except ValueError:
        # A fixed initial upper-leg lateral axis gives a second anatomical estimate.
        lateral=np.array(frames[0]['bones']['thigh_r'])-np.array(frames[0]['bones']['thigh_l'])
        facing={'method':'initial_thigh_lateral_axis','yaw_degrees':math.degrees(math.atan2(-lateral[0],lateral[1])),'requires_visual_check':True}
    yaw=facing['yaw_degrees'];width,height=(720,1280) if orientation=='portrait' else (1280,720)
    aspect=width/height
    distances=[fit(frames,preset,f,yaw,centers,aspect) for f in (preset['start'],preset['end'])]
    rows=path(frames,preset,distances,yaw,centers)
    diagnostics={}
    for framing in {preset['start'],preset['end']}:
        uv,depth=project(frames,rows,framing,aspect)
        assert np.isfinite(uv).all() and depth.min()>1
        diagnostics[framing]={'min_depth_cm':float(depth.min()),'frames_with_proxy_excursion':int(np.any((uv<.035)|(uv>.965),axis=(1,2)).sum())}
    key=decision['motion_id'].lower()+'_'+sex
    sid=group+'_'+key+'_'+orientation[:1]+'_'+preset['id']
    return {'shot_id':sid,'status':'geometry_pass','group':group,'motion_id':decision['motion_id'],'motion_label':decision['label'],'sex':sex,'camera_id':preset['id'],'camera_label':preset['label'],'orientation':orientation,'width':width,'height':height,'aspect_ratio':aspect,'fps':30,'frame_count':len(rows)-1,'duration_seconds':(len(rows)-1)/30,'source_start_seconds':start,'source_body_play_rate':rate,'source_animation':clip['animation_path'],'source_clip_id':clip['clip_id'],'source_end_seconds':start+((len(rows)-1)/30)*rate,'initial_facing':facing,'window_start_seconds':start if rate==1 else 0.,'frames':rows[:-1],'endpoint_validation_frame':rows[-1],'trajectory_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'endpoint_distances_cm':distances,'framing_diagnostics':diagnostics,'human_acceptance':'pending','note':'Overview preserves selected speed/duration; camera trial uses up to ten seconds. Face clock is independent.'}

def build(decisions_path):
    samples=json.loads((RUN/'all_motion_samples_v1.json').read_text(encoding='utf-8'))
    decisions=json.loads(Path(decisions_path).read_text(encoding='utf-8'))
    clips={c['clip_id']:c for c in samples['clips']}; presets=library.presets(); front=next(p for p in presets if p['id']=='front_full')
    shots=[]
    for d in decisions['actions']:
        if d['window_start_seconds'] is None:continue
        sex='female' if 'female' in d['variants'] else 'male'
        if d['motion_id'] in ('MOTION_CAND_029','MOTION_CAND_035'):sex='male'
        clip=clips[d['variants'][sex]['clip_id']]
        shots.append(shot(clip,d,sex,front,'landscape','motions'))
        if d['motion_id'] in ('MOTION_CAND_003','MOTION_CAND_008','MOTION_CAND_030'):
            for orientation in ('landscape','portrait'):
                for preset in presets:shots.append(shot(clip,d,sex,preset,orientation,'portrait',limit=10.))
    target=RUN/'camera_trial_plan_v1.json'
    with target.open('x',encoding='utf-8') as f:json.dump({'schema':'motion_portrait_camera_trial_v1','decisions_path':str(decisions_path),'source_samples_sha256':hashlib.sha256((RUN/'all_motion_samples_v1.json').read_bytes()).hexdigest(),'shots':shots,'human_acceptance':'pending'},f,ensure_ascii=False,indent=2)
    return {'shots':len(shots),'frames':sum(s['frame_count'] for s in shots)}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('decisions',type=Path);a=p.parse_args();print(build(a.decisions))
