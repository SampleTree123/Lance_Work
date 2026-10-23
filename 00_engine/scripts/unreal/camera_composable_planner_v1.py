"""Offline composable trajectories; bone-proxy checks are not visual acceptance."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import camera_motion_planner_v1 as old
from build_camera_library_expansion_v1 import validate_spec

def region(frame, framing):
    return old.semantic_points(frame['bones'],framing)

def trajectory(frames, spec, distances, yaw):
    movement=spec['movement']['kind']; a=spec['framing']['start']; b=spec['framing']['end']
    stable=old.smooth([[f['bones']['pelvis'][0],f['bones']['pelvis'][1],0] for f in frames],12)
    offsets={v:old.mean([old.sub(old.mean(region(f,v)),p) for f,p in zip(frames,stable)]) for v in {a,b}}
    anchors={v:old.mean([old.add(p,offsets[v]) for p in stable]) for v in {a,b}}
    heading=old.follow_heading(frames,30,yaw)['smoothed_yaw_degrees'] if spec['direction']['reference']=='pelvis_heading' else [yaw]*len(frames)
    rows=[]
    for i,f in enumerate(frames):
        u=old.ease(f['t']/10)
        dynamic=movement in {'follow','orbit'}
        centers={v:old.add(stable[i],offsets[v]) for v in {a,b}}
        origin=old.lerp(centers[a],centers[b],u) if dynamic else old.lerp(anchors[a],anchors[b],u)
        target=old.lerp(centers[a],centers[b],u) if movement=='pan' else origin
        theta=math.radians(heading[i]+spec['direction']['azimuth_degrees']+spec['movement'].get('orbit_degrees',0)*u)
        phi=math.radians(spec['direction']['elevation_degrees'])
        distance=distances[0]*(1-u)+distances[1]*u
        direction=[math.cos(theta)*math.cos(phi),math.sin(theta)*math.cos(phi),math.sin(phi)]
        position=old.add(origin,old.mul(direction,distance))
        # Existing low-angle convention: safe camera height, same fixed position.
        if spec['direction']['elevation_degrees']<0: position[2]=max(25,position[2])
        rows.append(old.camera_row(f['t'],position,target,spec['horizontal_fov_degrees']))
    return rows

def evaluate(frames, rows, spec):
    a=spec['framing']['start']; b=spec['framing']['end']; bad=[]; heights=[]; feet=[]; hands=[]
    for f,c in zip(frames,rows):
        u=old.ease(f['t']/10)
        forward,right,up=old.basis(c['position'],c['look_at'])
        half=math.tan(math.radians(c['horizontal_fov_degrees']/2))
        def project(point):
            delta=old.sub(point,c['position']); depth=old.dot(delta,forward)
            if depth<=.01: return None
            return [.5+old.dot(delta,right)/(2*depth*half),.5-old.dot(delta,up)*(16/9)/(2*depth*half),depth]
        # Transition crop is explicitly interpolated from full to upper body.
        pts=region(f,a if u<.5 else b)
        if a!=b:
            pa=region(f,a); pb=region(f,b)
            low=(1-u)*min(p[2] for p in pa)+u*min(p[2] for p in pb)
            high=(1-u)*max(p[2] for p in pa)+u*max(p[2] for p in pb)
            pts=[p for p in region(f,'full') if low<=p[2]<=high]
            center=old.mean(region(f,'full'))
            pts += [[center[0],center[1],low],[center[0],center[1],high]]
        uv=[project(p) for p in pts]
        if any(p is None or not(.035<=p[0]<=.965 and .035<=p[1]<=.965) for p in uv): bad.append(f['t'])
        heights.append(max(p[1] for p in uv if p)-min(p[1] for p in uv if p))
        if a==b and a in {'upper','head'}:
            feetuv=[project(f['bones'][k]) for k in ['foot_l','foot_r']]
            if any(p and 0<=p[0]<=1 and 0<=p[1]<=1 for p in feetuv): feet.append(f['t'])
        for k in ['hand_l','hand_r']:
            p=project(f['bones'][k])
            if p is None or not(0<=p[0]<=1 and 0<=p[1]<=1): hands.append({'t':f['t'],'bone':k})
    return {'passed':not bad and not feet,'framing_violation_times':bad,'excluded_feet_visible_times':feet,
            'hand_outside_screen':hands,'min_height_fraction':min(heights),'max_height_fraction':max(heights),
            'endpoint_height_fractions':[heights[0],heights[-1]],
            'evidence_scope':'301-frame skeletal proxy only, excludes visible mesh silhouette and scene occlusion',
            'transition_crop_policy':'interpolated vertical semantic extent; full-body hands required, cropped shots may omit hands below crop'}

def fit(frames,spec,yaw):
    a,b=spec['framing']['start'],spec['framing']['end']; distances=[]
    for framing in [a,b]:
        fixed=copy.deepcopy(spec); fixed['framing']={'start':framing,'end':framing}
        lo,hi=50.,2500.
        for _ in range(18):
            mid=(lo+hi)/2; q=evaluate(frames,trajectory(frames,fixed,[mid,mid],yaw),fixed)
            if q['framing_violation_times']: lo=mid
            else: hi=mid
        distances.append(hi*1.03)
    movement=spec['movement']['kind']
    if movement=='dolly_out' and a==b: distances[1]=distances[0]*1.48
    if movement=='dolly_in' and a==b: distances[0]=distances[1]*1.48
    rows=trajectory(frames,spec,distances,yaw); quality=evaluate(frames,rows,spec)
    if a==b and movement not in {'dolly_in','dolly_out'}:
        conventional=old.assess(frames,rows,a,16/9)
        quality['standard_framing_check']=conventional
        quality['passed'] &= conventional['passed']
    if a!=b:
        endpoints=[old.assess([frames[0]],[rows[0]],a,16/9),old.assess([frames[-1]],[rows[-1]],b,16/9)]
        quality['endpoint_framing_checks']=endpoints
        quality['passed'] &= all(q['passed'] for q in endpoints)
    if movement in {'dolly_in','dolly_out'}:
        quality['dolly_distance_ratio']=max(distances)/min(distances)
        quality['passed'] &= quality['dolly_distance_ratio']>=1.3
    quality['camera_below_pilot_floor_times']=[r['t'] for r in rows if r['position'][2]<25]
    quality['passed'] &= not quality['camera_below_pilot_floor_times']
    return rows,quality,distances

def build(prior, output):
    prior=prior.resolve(); output=output.resolve()
    candidates=json.loads((output/'camera_coverage_candidates_v1.json').read_text(encoding='utf-8'))['rows']
    sources={}; clips={}; source_pins=[]
    for name in ['camera_motion_pilot_plan_v3.json','retime_pilot_plan_v1.json','extra_orbit_pilot_plan_v1.json']:
        p=prior/name
        if p.exists():
            data=p.read_bytes(); source_pins.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest()})
            for s in json.loads(data)['shots']: sources[int(s['shot_id'].split('_')[1])]=s
    for name in ['motion_samples_v1.json','retime_motion_samples_v1.json']:
        p=prior/name
        if p.exists():
            data=p.read_bytes(); source_pins.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest()})
            for c in json.loads(data)['clips']: clips[c['clip_id']]=c
    shots=[]; rejected=[]
    for i,candidate in enumerate(candidates,36):
        source=sources.get(candidate['comparison_sample_number']); spec=candidate['camera']; validate_spec(spec)
        if not source or source['clip_id'] not in clips:
            rejected.append({'candidate_id':candidate['candidate_id'],'reason':'matching source samples unavailable'}); continue
        sampled=old.resample(clips[source['clip_id']],10,30)
        rows,quality,distances=fit(sampled,spec,source['yaw_offset_degrees'])
        metadata={k:copy.deepcopy(v) for k,v in source.items() if k not in {'frames','endpoint_validation_frame','quality','path_metrics','trajectory_sha256','follow_heading','follow_mode','follow_relative_yaw_degrees'}}
        metadata.update({'shot_id':f'cam_{i:02d}_{candidate["candidate_id"]}', 'shot_type':candidate['candidate_id'],
                         'source_shot_id':source['shot_id'],'candidate_id':candidate['candidate_id'],
                         'camera_spec':spec,'camera_label':candidate['label'],'motion_label':candidate['motion_label'],
                         'family':spec['movement']['kind'],'framing':spec['framing']['start'],
                         'status':'geometry_pass' if quality['passed'] else 'geometry_rejected',
                         'quality':quality,'distance_cm':distances[0],'endpoint_distances_cm':distances,
                         'frames':rows[:-1],'endpoint_validation_frame':rows[-1],
                         'path_metrics':old.path_metrics(rows),'human_visual_acceptance':'pending',
                         'trajectory_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
        (shots if quality['passed'] else rejected).append(metadata)
    plan={'schema':'camera_motion_pilot_plan_v1','unified_duration_seconds':10,'fps':30,'frame_count':300,
          'aspect_ratio':16/9,'shots':shots,'rejected':rejected,'geometry_pass_count':len(shots),
          'human_visual_acceptance':'pending','source_pins':source_pins,
          'limitations':['bone proxies only; source identity/appearance must be cloned from source_shot_id','not a whitelist; unseen combinations remain candidates']}
    (output/'expansion_plan_v1.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':len(shots),'rejected':[{ 'id':s.get('shot_id',s.get('candidate_id')), 'quality':{k:v for k,v in s.get('quality',{}).items() if k not in {'standard_framing_check','endpoint_framing_checks','hand_outside_screen'}}} for s in rejected]},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.prior,a.output)
