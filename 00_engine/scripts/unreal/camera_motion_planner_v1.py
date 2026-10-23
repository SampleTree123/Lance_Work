"""Offline, deterministic camera candidates for world-space skeletal samples.

No Unreal imports. Geometry checks use bone proxies, not rendered visibility.
All output clips share an explicit single duration. Old camera contracts untouched.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = 'camera_motion_samples_v1'
STATIC = {
    'static_front': (0, 0, 'full'), 'static_three_quarter': (45, 0, 'full'),
    'static_side': (90, 0, 'full'), 'static_rear': (135, 0, 'full'),
    'static_high': (35, 25, 'full'), 'static_low': (35, -8, 'full'),
    'static_upper': (0, 0, 'upper'), 'static_head': (15, 0, 'head'),
    'static_wide': (35, 0, 'wide'),
}
RANGES = {'full': (.55, .90), 'upper': (.60, .92), 'head': (.55, .90), 'wide': (.23, .48)}
REQUIRED = ('root', 'pelvis', 'head', 'neck_01', 'upperarm_l', 'upperarm_r',
            'hand_l', 'hand_r', 'foot_l', 'foot_r', 'calf_l', 'calf_r',
            'thigh_l', 'thigh_r', 'spine_01', 'spine_02', 'ball_l', 'ball_r')
MATRIX = [
    (2, ['static_front', 'static_upper', 'static_head', 'zoom_in', 'dolly_in']),
    (3, ['static_high', 'static_low', 'static_upper', 'dolly_out', 'pan']),
    (8, ['static_wide', 'static_side', 'follow_front', 'follow_side', 'follow_rear']),
    (29, ['static_three_quarter', 'static_rear', 'orbit_60', 'orbit_120', 'orbit_180']),
    (30, ['static_front', 'static_side', 'static_high', 'zoom_out', 'orbit_120']),
    (35, ['static_three_quarter', 'static_wide', 'follow_side', 'pan', 'dolly_out']),
]

def add(a, b): return [x + y for x, y in zip(a, b)]
def sub(a, b): return [x - y for x, y in zip(a, b)]
def mul(a, s): return [x * s for x in a]
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def norm(a): return math.sqrt(dot(a, a))
def unit(a):
    length = norm(a)
    if length < 1e-9: raise ValueError('Degenerate camera basis')
    return mul(a, 1 / length)
def mean(points): return [sum(p[j] for p in points) / len(points) for j in range(3)]
def lerp(a, b, u): return add(mul(a, 1-u), mul(b, u))
def ease(u): return u*u*(3-2*u)
def finite_vector(value):
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in value)

def validate_clip(clip, duration):
    if not 10 <= duration <= 15: raise ValueError('Unified duration must be 10–15 seconds')
    start = float(clip.get('window_start_seconds', 0))
    if float(clip['duration_seconds']) + 1e-7 < start + duration:
        raise ValueError('Source is shorter than unified duration; no automatic loops/stretch')
    frames = clip['frames']
    times = [float(f['t']) for f in frames]
    if len(times) < 2 or any(not math.isfinite(t) for t in times) or any(b <= a for a,b in zip(times,times[1:])):
        raise ValueError('Samples must have finite strictly increasing times')
    if times[0] > 1e-7 or times[-1] < duration - 1e-7:
        raise ValueError('Samples must cover local t=0 through duration endpoint')
    for f in frames:
        if any(not finite_vector(f['bones'].get(name)) for name in REQUIRED):
            raise ValueError('Missing/nonfinite required bone position')
    return times

def resample(clip, duration, fps=30):
    times = validate_clip(clip, duration)
    count = round(duration * fps)
    if abs(count / fps - duration) > 1e-8: raise ValueError('Duration must yield integral frames')
    output = []
    for i in range(count + 1):
        t = i / fps
        right = min(max(1, bisect.bisect_left(times, t)), len(times)-1)
        left = right - 1
        u = (t-times[left]) / (times[right]-times[left])
        output.append({'t':t, 'bones':{k:lerp(clip['frames'][left]['bones'][k], clip['frames'][right]['bones'][k], u) for k in REQUIRED}})
    return output

def semantic_points(bones, framing):
    # Conservative skeletal proxy only; visible hair/cloth silhouette must be inspected.
    head = bones['head']
    top = add(head,[0,0,20])
    crown = [add(top,[x,y,0]) for x in (-10,10) for y in (-10,10)]
    if framing == 'head':
        return crown + [add(bones['neck_01'], [x,y,-6]) for x in (-13,13) for y in (-13,13)]
    upper = crown + [add(bones[k], [x,y,0]) for k in ('pelvis','upperarm_l','upperarm_r','spine_02') for x in (-8,8) for y in (-8,8)]
    if framing == 'upper': return upper
    return upper + [add(bones[k], [x,y,z]) for k in ('foot_l','foot_r','ball_l','ball_r','hand_l','hand_r','calf_l','calf_r') for x,y,z in ((-10,-10,-8),(10,10,8),(-10,10,0),(10,-10,0))]

def basis(position, target):
    forward = unit(sub(target,position))
    right = unit(cross([0,0,1],forward))
    up = cross(forward,right)
    return forward,right,up

def project(point, camera, aspect):
    forward,right,up = basis(camera['position'],camera['look_at'])
    delta = sub(point,camera['position'])
    depth = dot(delta,forward)
    if depth <= .01: return None
    half_h = math.tan(math.radians(camera['horizontal_fov_degrees']/2))
    return [.5 + dot(delta,right)/(2*depth*half_h), .5-dot(delta,up)*aspect/(2*depth*half_h), depth]

def smooth(points, radius):
    # Symmetric pre-baked smoothing avoids online lag and follows pelvis, not limbs.
    return [mean(points[max(0,i-radius):min(len(points),i+radius+1)]) for i in range(len(points))]

def camera_row(t, position, target, fov):
    d=sub(target,position)
    return {'t':t,'position':position,'look_at':target,
            'rotation_pitch_yaw_roll':[math.degrees(math.atan2(d[2], math.hypot(d[0],d[1]))),math.degrees(math.atan2(d[1],d[0])),0.],
            'horizontal_fov_degrees':fov}

def initial_foot_forward_evidence(frame):
    """Independent first-pose foot-to-ball consensus, without a +Y assumption."""
    bones=frame['bones'];directions=[];feet=[]
    for side in ('l','r'):
        delta=sub(bones['ball_'+side],bones['foot_'+side]);delta[2]=0
        length=norm(delta)
        if length<3: raise ValueError('Initial foot-to-ball direction is degenerate')
        direction=unit(delta);directions.append(direction)
        feet.append({'side':side,'foot_to_ball_world':delta,'horizontal_length_cm':length,
                     'yaw_degrees':math.degrees(math.atan2(direction[1],direction[0]))})
    consensus=mean(directions);confidence=norm(consensus)
    disagreement=math.degrees(math.acos(max(-1,min(1,dot(*directions)))))
    if confidence<.75 or disagreement>75: raise ValueError('Initial feet disagree; cannot infer facing sign reliably')
    return {'method':'initial_dual_foot_to_ball_consensus','feet':feet,'consensus_magnitude':confidence,
            'left_right_disagreement_degrees':disagreement,
            'yaw_degrees':math.degrees(math.atan2(consensus[1],consensus[0])),
            'scope':'geometric sign cross-check; not claimed as visual acceptance'}

def follow_heading(frames, fps, calibrated_initial_yaw, sigma_seconds=.18):
    """Pelvis-facing estimate with explicit sign calibration and smooth unwrapped yaw.

    Cross-product sign is chosen once against the caller's visually verified
    initial facing, never guessed afresh during a turn. Shoulders are used only
    if the pelvis landmarks have a degenerate horizontal separation.
    """
    if not math.isfinite(calibrated_initial_yaw): raise ValueError('Need finite visually calibrated initial facing')
    if fps<=0 or sigma_seconds<=0: raise ValueError('Invalid heading smoothing parameters')
    raw=[];sources=[]
    for frame in frames:
        bones=frame['bones'];forward=None
        for left,right,source in [('thigh_l','thigh_r','pelvis_hip_landmarks'),('upperarm_l','upperarm_r','shoulder_fallback')]:
            lateral=sub(bones[right],bones[left]);lateral[2]=0
            if norm(lateral)>=2.:
                forward=unit(cross(lateral,[0,0,1]));sources.append(source);break
        if forward is None: raise ValueError('Both pelvis and shoulder heading landmarks are degenerate')
        raw.append(math.degrees(math.atan2(forward[1],forward[0])))
    reference=[math.cos(math.radians(calibrated_initial_yaw)),math.sin(math.radians(calibrated_initial_yaw)),0]
    initial=[math.cos(math.radians(raw[0])),math.sin(math.radians(raw[0])),0]
    agreement=dot(reference,initial)
    if abs(agreement)<.5: raise ValueError('Initial landmark heading ambiguous against visual calibration; do not guess sign')
    flip=180. if agreement<0 else 0.
    unwrapped=[]
    for angle in raw:
        angle+=flip
        if unwrapped: angle=unwrapped[-1]+((angle-unwrapped[-1]+180)%360-180)
        unwrapped.append(angle)
    radius=max(1,math.ceil(3*sigma_seconds*fps));smoothed=[]
    for i in range(len(raw)):
        pairs=[(unwrapped[j],math.exp(-.5*((j-i)/(sigma_seconds*fps))**2)) for j in range(max(0,i-radius),min(len(raw),i+radius+1))]
        smoothed.append(sum(angle*weight for angle,weight in pairs)/sum(weight for _,weight in pairs))
    return {'mode':'pelvis_heading','calibrated_initial_yaw_degrees':calibrated_initial_yaw,
            'calibration_absolute_dot':abs(agreement),'cross_product_sign_flipped':bool(flip),
            'smoothing':'prebaked_symmetric_gaussian_after_yaw_unwrap','sigma_seconds':sigma_seconds,
            'raw_yaw_degrees':unwrapped,'smoothed_yaw_degrees':smoothed,
            'landmark_sources':sources,'fallback_frame_count':sources.count('shoulder_fallback')}

def build_path(frames, shot, distance, duration, fps, yaw_offset, *, follow_mode='fixed_world', heading=None):
    if follow_mode not in ('fixed_world','pelvis_heading'): raise ValueError('Unknown follow mode')
    framing=STATIC.get(shot,(0,0,'full'))[2]
    centers=[mean(semantic_points(f['bones'],framing)) for f in frames]
    # X/Y follows stable pelvis; Z uses one segment-wide semantic center.
    stable=smooth([[f['bones']['pelvis'][0],f['bones']['pelvis'][1],0] for f in frames],round(.4*fps))
    offset=mean([sub(c,p) for c,p in zip(centers,stable)])
    centers=[add(p,offset) for p in stable]
    anchor=mean(centers)
    yaw,pitch,_=STATIC.get(shot,(35,0,framing))
    if shot.startswith('follow_'): yaw={'follow_front':0,'follow_side':90,'follow_rear':180}[shot]
    rows=[]
    for i,(f,c) in enumerate(zip(frames,centers)):
        u=ease(f['t']/duration)
        theta=math.radians(yaw+yaw_offset+(float(shot.split('_')[1])*u if shot.startswith('orbit_') else 0))
        if shot.startswith('follow_') and follow_mode=='pelvis_heading':
            if heading is None: heading=follow_heading(frames,fps,yaw_offset)
            theta=math.radians(yaw+heading['smoothed_yaw_degrees'][i])
        phi=math.radians(pitch)
        direction=[math.cos(theta)*math.cos(phi),math.sin(theta)*math.cos(phi),math.sin(phi)]
        radius=distance
        if shot=='dolly_in': radius*=1.18-.18*u
        if shot=='dolly_out': radius*=1+.18*u
        fov=35.
        if shot=='zoom_in': fov=41.-6*u
        if shot=='zoom_out': fov=35.+6*u
        moving=shot.startswith(('follow_','orbit_'))
        target=c if moving or shot=='pan' else anchor
        origin=c if moving else anchor
        position=add(origin,mul(direction,radius))
        # A full-body low-angle shot cannot put a physical camera underground.
        # Keep the requested low viewpoint at >=25 cm, retaining its fixed pose.
        if shot=='static_low': position[2]=max(25.,position[2])
        rows.append(camera_row(f['t'],position,target,fov))
    return rows

def assess(frames, rows, framing, aspect):
    low,high=RANGES[framing]
    heights=[]; scales=[]; bad=[]; feet_visible=[]
    # Bending should not relabel a correctly scaled fixed full-body camera as wide.
    # A segment-wide upright proxy measures camera scale, while actual pose points
    # independently enforce the screen boundary at every sampled instant.
    stature=max(max(p[2] for p in semantic_points(f['bones'],'full'))-min(p[2] for p in semantic_points(f['bones'],'full')) for f in frames)
    for f,c in zip(frames,rows):
        forward,right,up=basis(c['position'],c['look_at'])
        half_h=math.tan(math.radians(c['horizontal_fov_degrees']/2))
        def local_project(point):
            delta=sub(point,c['position']); depth=dot(delta,forward)
            if depth<=.01: return None
            return [.5+dot(delta,right)/(2*depth*half_h),.5-dot(delta,up)*aspect/(2*depth*half_h),depth]
        uv=[local_project(p) for p in semantic_points(f['bones'],framing)]
        if any(p is None for p in uv): bad.append(f['t']); heights.append(0); scales.append(0); continue
        height=max(p[1] for p in uv)-min(p[1] for p in uv)
        heights.append(height)
        if framing in ('full','wide'):
            center=mean(semantic_points(f['bones'],'full'))
            pair=[local_project(add(center,[0,0,z])) for z in (-stature/2,stature/2)]
            scales.append(abs(pair[1][1]-pair[0][1]) if all(pair) else 0)
        else: scales.append(height)
        if any(not (.035 <= p[0] <= .965 and .035 <= p[1] <= .965) for p in uv) or height>high+1e-6:
            bad.append(f['t'])
        if framing in ('upper','head'):
            feet=[local_project(f['bones'][k]) for k in ('foot_l','foot_r')]
            if any(p and 0<=p[0]<=1 and 0<=p[1]<=1 for p in feet): feet_visible.append(f['t'])
    under=[f['t'] for f,h in zip(frames,scales) if h<low]
    return {'max_height_fraction':max(heights),'min_height_fraction':min(heights),
            'min_camera_scale_fraction':min(scales),'max_camera_scale_fraction':max(scales),
            'camera_scale_method':'segment_stature_proxy' if framing in ('full','wide') else 'actual_semantic_region',
            'framing_violation_times':bad,'undersized_times':under,'excluded_feet_visible_times':feet_visible,
            'passed':not bad and not under and not feet_visible,
            'evidence_scope':'bone_proxy_projection_only; no mesh silhouette or scene occlusion test'}

def path_metrics(rows):
    speeds=[]; turns=[]
    for a,b in zip(rows,rows[1:]):
        dt=b['t']-a['t']
        speeds.append(norm(sub(b['position'],a['position']))/dt)
        av=unit(sub(a['look_at'],a['position'])); bv=unit(sub(b['look_at'],b['position']))
        turns.append(math.degrees(math.acos(max(-1,min(1,dot(av,bv)))))/dt)
    return {'max_camera_speed_cm_per_second':max(speeds,default=0),
            'max_view_angular_speed_degrees_per_second':max(turns,default=0),
            'min_camera_z_cm':min(r['position'][2] for r in rows),
            'speed_values_are_diagnostics_not_visual_acceptance':True}

def plan_shot(clip, shot, duration, fps=30, aspect=16/9, yaw_offset=0, *, follow_mode='fixed_world', follow_sigma_seconds=.18, follow_calibration='visual_initial'):
    supported=set(STATIC)|{'dolly_in','dolly_out','zoom_in','zoom_out','follow_front','follow_side','follow_rear','orbit_60','orbit_120','orbit_180','pan'}
    if shot not in supported: raise ValueError('Unknown camera type')
    if fps<=0 or not math.isfinite(aspect) or aspect<=0: raise ValueError('Invalid fps/aspect')
    frames=resample(clip,duration,fps)
    if follow_mode not in ('fixed_world','pelvis_heading'): raise ValueError('Unknown follow mode')
    heading=None
    if shot.startswith('follow_') and follow_mode=='pelvis_heading':
        if follow_calibration not in ('visual_initial','feet_consensus'): raise ValueError('Unknown heading calibration')
        foot_evidence=initial_foot_forward_evidence(frames[0]) if follow_calibration=='feet_consensus' else None
        calibration_yaw=foot_evidence['yaw_degrees'] if foot_evidence else yaw_offset
        heading=follow_heading(frames,fps,calibration_yaw,follow_sigma_seconds)
        if foot_evidence: heading['initial_facing_evidence']=foot_evidence
    framing=STATIC.get(shot,(0,0,'full'))[2]
    # Monotonic size search; never change the requested framing to obtain a pass.
    distance=25.; lo=25.; hi=6000.
    for _ in range(24):
        distance=(lo+hi)/2
        rows=build_path(frames,shot,distance,duration,fps,yaw_offset,follow_mode=follow_mode,heading=heading)
        quality=assess(frames,rows,framing,aspect)
        if quality['framing_violation_times']: lo=distance
        else: hi=distance
    distance=hi*1.01
    rows=build_path(frames,shot,distance,duration,fps,yaw_offset,follow_mode=follow_mode,heading=heading)
    quality=assess(frames,rows,framing,aspect)
    quality['camera_below_pilot_floor_times']=[r['t'] for r in rows if r['position'][2]<10.]
    quality['passed']=quality['passed'] and not quality['camera_below_pilot_floor_times']
    serialized=json.dumps(rows,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    result={'shot_type':shot,'family':'static' if shot in STATIC else shot.split('_')[0],
            'framing':framing,'duration_seconds':duration,'fps':fps,'frame_count':len(rows)-1,
            'aspect_ratio':aspect,'distance_cm':distance,'yaw_offset_degrees':yaw_offset,
            'status':'geometry_pass' if quality['passed'] else 'unsuitable',
            'quality':quality,'path_metrics':path_metrics(rows),'trajectory_sha256':hashlib.sha256(serialized).hexdigest(),
            'frames':rows[:-1],'endpoint_validation_frame':rows[-1],
            'motion_policy':'original speed; no body loop/stretch; five-second face may repeat'}
    if heading is not None:
        result['follow_heading']=heading
        result['follow_mode']='pelvis_heading'
        result['follow_relative_yaw_degrees']={'follow_front':0,'follow_side':90,'follow_rear':180}[shot]
    return result

def build_manifest(samples,duration,fps=30,aspect=16/9,yaw_offset=0):
    if samples.get('schema')!=SCHEMA: raise ValueError('Wrong input schema')
    shots=[]; rejected=[]
    clips=samples['clips']
    # action_index in sampling schema is a UI index; source_candidate_id is safer
    # when supplied. Caller can explicitly provide pilot_group=2/3/8/29/30/35.
    def group_of(c):
        if c.get('pilot_group') is not None: return int(c['pilot_group'])
        match=re.fullmatch(r'motion_cand_(\d+)_(?:female|male)',c['clip_id'])
        if match: return int(match.group(1))
        return int(c['action_index'])
    for group,types in MATRIX:
        matching=[c for c in clips if group_of(c)==group]
        if not matching: rejected.append({'pilot_group':group,'reason':'missing samples'}); continue
        bysex={c['sex']:c for c in matching}
        for ordinal,shot in enumerate(types):
            sex='female' if (ordinal+group)%2==0 else 'male'
            clip=bysex.get(sex,next(iter(bysex.values())))
            try:
                item=plan_shot(clip,shot,duration,fps,aspect,yaw_offset)
                if item['status']!='geometry_pass':
                    rejected.append({'clip_id':clip['clip_id'],'shot_type':shot,'reason':'geometry unsuitable',
                                     'quality':item['quality'],'trajectory_sha256':item['trajectory_sha256']})
                    original_clip=clip
                    for alternative_group in (29,2,35,30,8,3):
                        options=[c for c in clips if group_of(c)==alternative_group and c['sex']==sex and c['clip_id']!=original_clip['clip_id']
                                 and not any(s['clip_id']==c['clip_id'] and s['shot_type']==shot for s in shots)]
                        if not options: continue
                        alternative=options[0]
                        candidate=plan_shot(alternative,shot,duration,fps,aspect,yaw_offset)
                        if candidate['status']=='geometry_pass':
                            item=candidate; clip=alternative
                            item['replacement_of']={'clip_id':original_clip['clip_id'],'shot_type':shot,'reason':'same camera type on compatible motion; thresholds unchanged'}
                            break
                        rejected.append({'clip_id':alternative['clip_id'],'shot_type':shot,'reason':'replacement geometry unsuitable','quality':candidate['quality']})
                item.update({'shot_id':f"cam_{len(shots)+1:02d}_{shot}",'clip_id':clip['clip_id'],'sex':clip['sex'],
                             'action_index':clip['action_index'],'animation_path':clip['animation_path'],
                             'source_duration_seconds':clip['duration_seconds'],'window_start_seconds':clip.get('window_start_seconds',0)})
                shots.append(item)
            except ValueError as exc: rejected.append({'clip_id':clip['clip_id'],'shot_type':shot,'reason':str(exc)})
    return {'schema':'camera_motion_proposal_v1','unified_duration_seconds':duration,'fps':fps,
            'frame_count':round(duration*fps),'aspect_ratio':aspect,'shots':shots,'rejected':rejected,
            'geometry_pass_count':sum(s['status']=='geometry_pass' for s in shots),
            'human_visual_acceptance':'pending','paired_edit_policy':'reuse byte-identical pre-baked trajectory; never reframe independently',
            'limitations':['10 Hz source interpolation cannot certify in-between motion','bone proxies do not certify hair, cloth or occlusion','yaw offset requires visual calibration']}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--samples',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--duration',type=float,required=True); p.add_argument('--fps',type=int,default=30); p.add_argument('--aspect',type=float,default=16/9); p.add_argument('--yaw-offset',type=float,default=0)
    a=p.parse_args(); source=a.samples.read_bytes()
    result=build_manifest(json.loads(source.decode('utf-8-sig')),a.duration,a.fps,a.aspect,a.yaw_offset)
    result['source_samples_sha256']=hashlib.sha256(source).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'shots':len(result['shots']),'geometry_pass':result['geometry_pass_count'],'rejected':len(result['rejected'])}))

if __name__=='__main__': main()
