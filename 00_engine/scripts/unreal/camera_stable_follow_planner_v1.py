"""Offline 15-preset stable-follow diagnostic pilot; never visual acceptance."""
from __future__ import annotations
import argparse, copy, hashlib, json, math
from pathlib import Path
import numpy as np
import camera_motion_planner_v1 as old

ACTIONS = [('bend', '弯腰伸展', 7), ('dance', '舒展舞步', 21), ('walk', '向前行走', 13)]

def presets():
    out=[]
    for pid,label,yaw,pitch,frame in [('front_full','正面全身',0,0,'full'),('side_full','侧面全身',90,0,'full'),('rear_three_quarter_full','背侧全身',135,0,'full'),('front_upper','上半身',0,0,'upper'),('front_head','面部近景',0,0,'head'),('high_full','俯视全身',35,25,'full'),('low_full','仰视全身',35,-8,'full')]:
        out.append(dict(id=pid,label=label,azimuth=yaw,elevation=pitch,start=frame,end=frame,kind='follow',orbit=0))
    for angle in [360,120]:
        out.append(dict(id=f'orbit_{angle}',label=f'{angle}°全身环绕',azimuth=0,elevation=0,start='full',end='full',kind='orbit',orbit=angle))
    for kind,label,a,b in [('dolly_in','推进','full','upper'),('dolly_out','拉远','upper','full')]:
        for direction,name,yaw in [('front','正面',0),('side','侧面',90),('back','背面',180)]:
            out.append(dict(id=f'{kind}_{direction}',label=name+label,azimuth=yaw,elevation=0,start=a,end=b,kind=kind,orbit=0))
    return out


def low_frequency(points, times, sigma=1.15):
    """Symmetric local-linear Gaussian fit preserves constant-speed endpoint motion."""
    p=np.asarray(points,float); t=np.asarray(times,float); delta=t[None,:]-t[:,None]
    w=np.exp(-.5*(delta/sigma)**2); w[np.abs(delta)>3*sigma]=0
    s0=w.sum(1);s1=(w*delta).sum(1);s2=(w*delta*delta).sum(1)
    effective=(w*s2[:,None]-w*delta*s1[:,None])/(s0*s2-s1*s1)[:,None]
    return effective@p


def stable_translation(points,times,deadzone=18.):
    trend=low_frequency(points,times,1.15)
    center=np.mean(trend,axis=0); delta=trend-center; radius=np.linalg.norm(delta[:,:2],axis=1)
    # Radial deadzone ignores local sway; a second symmetric fit removes boundary kinks.
    gain=np.maximum(0,1-deadzone/np.maximum(radius,1e-9))
    reduced=center+delta*gain[:,None]
    result=low_frequency(reduced,times,.45); result[:,2]=0
    return result


def progress(t):
    return old.ease(max(0.,min(1.,t/7.)))


def centers_for(frames):
    times=[f['t'] for f in frames]
    pelvis=np.array([[*f['bones']['pelvis'][:2],0.] for f in frames])
    stable=stable_translation(pelvis,times)
    result={}
    for framing in ['full','upper','head']:
        points=np.array([old.semantic_points(f['bones'],framing) for f in frames])
        box=(points.min(axis=1)+points.max(axis=1))/2
        relative=box-pelvis
        base=relative.mean(axis=0)
        if framing=='full':
            result[framing]=stable+base
        else:
            # Closeups adapt slowly to real bending/head translation, never raw bone jitter.
            local=low_frequency(relative,times,.7)
            result[framing]=stable+base+.80*(local-base)
    return result


def trajectory(frames,preset,distances,yaw,centers=None):
    centers=centers if centers is not None else centers_for(frames)
    result=[]
    for i,f in enumerate(frames):
        u=progress(f['t']) if preset['kind'].startswith('dolly') else 0.
        target=(1-u)*centers[preset['start']][i]+u*centers[preset['end']][i]
        theta=math.radians(yaw+preset['azimuth']+preset['orbit']*f['t']/10.)
        phi=math.radians(preset['elevation'])
        direction=np.array([math.cos(theta)*math.cos(phi),math.sin(theta)*math.cos(phi),math.sin(phi)])
        distance=(1-u)*distances[0]+u*distances[1]
        position=target+direction*distance
        position[2]=max(25.,position[2])
        result.append(old.camera_row(f['t'],position.tolist(),target.tolist(),35.))
    return result


def projections(frames,rows,framing):
    pts=np.array([old.semantic_points(f['bones'],framing) for f in frames])
    pos=np.array([r['position'] for r in rows]); tar=np.array([r['look_at'] for r in rows])
    forward=tar-pos; forward/=np.linalg.norm(forward,axis=1)[:,None]
    right=np.cross(np.array([0.,0.,1.]),forward);right/=np.linalg.norm(right,axis=1)[:,None]
    up=np.cross(forward,right);delta=pts-pos[:,None,:]
    depth=np.einsum('nkj,nj->nk',delta,forward)
    uv=np.stack([.5+np.einsum('nkj,nj->nk',delta,right)/(2*depth*math.tan(math.radians(17.5))),.5-np.einsum('nkj,nj->nk',delta,up)*(16/9)/(2*depth*math.tan(math.radians(17.5)))],axis=-1)
    return uv,depth


def fit_distance(frames,preset,framing,yaw,centers):
    fixed=dict(preset,start=framing,end=framing)
    lo,hi=60.,2200.
    # All full-body proxy points must fit. Closeups accept a small tail of excursions.
    quantile=1. if framing=='full' else .90
    for _ in range(15):
        d=(lo+hi)/2
        uv,depth=projections(frames,trajectory(frames,fixed,[d,d],yaw,centers),framing)
        overflow=np.maximum(np.abs(uv[:,:,0]-.5),np.abs(uv[:,:,1]-.5)).max(axis=1)
        if depth.min()<=1 or np.quantile(overflow,quantile)>.435: lo=d
        else: hi=d
    return hi*1.015


def make_shot(frames,preset,source,action,index):
    centers=centers_for(frames); yaw=float(source['yaw_offset_degrees'])
    distances=[fit_distance(frames,preset,f,yaw,centers) for f in [preset['start'],preset['end']]]
    rows=trajectory(frames,preset,distances,yaw,centers)
    diagnostics={}; safe=True
    for framing in set([preset['start'],preset['end']]):
        uv,depth=projections(frames,rows,framing)
        # Dolly endpoint intent is evaluated only where that framing is actually requested.
        active=np.array([not preset['kind'].startswith('dolly') or (f['t']<=.001 if framing==preset['start'] else f['t']>=7.) for f in frames])
        outside=np.any((uv<.035)|(uv>.965),axis=(1,2))
        safe &= bool(np.isfinite(uv).all() and depth.min()>1)
        diagnostics[framing]={'evaluated_times':[f['t'] for f,a in zip(frames,active) if a], 'outside_proxy_times':[f['t'] for f,o,a in zip(frames,outside,active) if o and a], 'min_depth_cm':float(depth.min()), 'height_range':[float(np.ptp(uv[:,:,1],axis=1)[active].min()),float(np.ptp(uv[:,:,1],axis=1)[active].max())]}
    safe &= all(old.finite_vector(r['position']) and old.finite_vector(r['look_at']) and r['position'][2]>=25 for r in rows)
    if not safe: raise ValueError('Unsafe camera geometry '+preset['id'])
    omit={'frames','endpoint_validation_frame','quality','path_metrics','trajectory_sha256','follow_heading','follow_mode','follow_relative_yaw_degrees','replaces_trajectory_sha256'}
    shot={k:copy.deepcopy(v) for k,v in source.items() if k not in omit}
    spec={'direction':{'azimuth_degrees':preset['azimuth'],'elevation_degrees':preset['elevation'],'reference':'initial_facing'},'framing':{'start':preset['start'],'end':preset['end']},'movement':{'kind':preset['kind'],'orbit_degrees':preset['orbit'],'finish_seconds':7 if preset['kind'].startswith('dolly') else 10},'horizontal_fov_degrees':35}
    shot.update(shot_id=f'cam_{index:02d}_stable_{action[0]}_{preset["id"]}',shot_type=preset['id'],stable_preset_id=preset['id'],stable_action_id=action[0],source_shot_id=source['shot_id'],camera_label=preset['label'],motion_label=action[1],camera_spec=spec,family=preset['kind'],framing=preset['start'],status='geometry_pass',geometry_pass_scope='finite camera; positive semantic depths; above floor; NOT strict framing acceptance',quality={'passed':True,'strict_framing_pass':all(not d['outside_proxy_times'] for d in diagnostics.values()),'framing_diagnostics':diagnostics,'closeup_policy':'user-authorized diagnostic excursions retained; human review pending','evidence_scope':'bone proxies only; no mesh silhouette or occlusion certification'},distance_cm=distances[0],endpoint_distances_cm=distances,frames=rows[:-1],endpoint_validation_frame=rows[-1],path_metrics=old.path_metrics(rows),human_visual_acceptance='pending',follow_mode='stable_translation_initial_facing',trajectory_sha256=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest())
    return shot


def build(prior,output):
    prior=Path(prior);output=Path(output);pins=[]
    def read(name):
        path=prior/name;data=path.read_bytes();pins.append({'path':str(path.resolve()),'sha256':hashlib.sha256(data).hexdigest()});return json.loads(data)
    sources={int(s['shot_id'].split('_')[1]):s for s in read('camera_motion_pilot_plan_v3.json')['shots']}
    clips={c['clip_id']:c for c in read('motion_samples_v1.json')['clips']}
    shots=[]
    for action in ACTIONS:
        source=sources[action[2]];frames=old.resample(clips[source['clip_id']],10,30)
        for preset in presets(): shots.append(make_shot(frames,preset,source,action,61+len(shots)))
    plan={'schema':'camera_motion_pilot_plan_v1','unified_duration_seconds':10,'fps':30,'frame_count':300,'aspect_ratio':16/9,'shots':shots,'rejected':[],'geometry_pass_count':45,'geometry_pass_scope':'renderable diagnostic trajectory only; strict framing separately recorded','human_visual_acceptance':'pending','source_pins':pins,'stable_follow_policy':{'horizontal_trend_sigma_seconds':1.15,'horizontal_deadzone_cm':18,'deadzone_resmoothing_sigma_seconds':.45,'closeup_local_sigma_seconds':.7,'closeup_adaptation_gain':.8,'full_body_vertical_target':'segment constant','facing':'source initial yaw, no heading pursuit','dolly_finish_seconds':7,'dolly_hold_seconds':3},'limitations':['45 diagnostic combinations, not production whitelist','closeup excursions explicitly allowed for inspection','body/face/identity source unchanged; no pixel-determinism claim']}
    output.mkdir(parents=True,exist_ok=True);target=output/'expansion_plan_v1.json'
    if target.exists(): raise FileExistsError('Refuse to overwrite frozen plan; inspect and version first')
    target.write_text(json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return plan

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();v=build(a.prior,a.output);print(json.dumps({'shots':len(v['shots']),'strict_framing_pass':sum(s['quality']['strict_framing_pass'] for s in v['shots'])}))
