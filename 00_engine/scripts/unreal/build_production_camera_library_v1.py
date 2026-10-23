"""Production clocks over accepted camera composition; no UE operations.

Body-follow targets use the exact motion time map. Orbit and dolly clocks are
independent of repeated/held body poses: orbit finishes at10, dolly at7.
"""
from pathlib import Path
import copy
import json
import math
import numpy as np
import production_motion_contract_v1 as motion
import scene_site_review_geometry_v1 as geo
from camera_motion_planner_v1 import camera_row

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'outputs/production_workflow_20261017_v1'

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.partial')
    temp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    temp.replace(path)

def rows(shot):return shot['frames']+[shot['endpoint_validation_frame']]


def movement_preset(shot):
    """Read accepted movement semantics after the landscape lens overlay.

    The horizontal standard archives source diagnostics, including the preset.
    Its movement/framing fields still describe the accepted camera; archived
    distances must not be reused because the current keys already include k=.5.
    """
    parameters=shot.get('common_preset_parameters')
    if parameters is None:
        parameters=(shot.get('camera_standard_v2',{}).get('superseded_source_diagnostics',{})
                    .get('common_preset_parameters'))
    preset=(parameters or {}).get('preset')
    if (not isinstance(preset,dict) or not {'kind','start','end'} <= preset.keys()
            or preset.get('id',shot['camera_id']) != shot['camera_id']
            or preset['kind'] not in {'static','follow','orbit','dolly_in','dolly_out'}
            or preset['start'] not in {'full','upper'} or preset['end'] not in {'full','upper'}):
        raise ValueError('Missing or inconsistent accepted camera movement preset: '+shot['camera_id'])
    if preset['kind']=='orbit' and not math.isfinite(float(preset.get('orbit',float('nan')))):
        raise ValueError('Accepted orbit requires a finite angle')
    return preset

class KeySampler:
    """One array conversion per source shot, never per output frame."""
    def __init__(self,keys):
        self.times=np.asarray([r['t'] for r in keys],float)
        if len(self.times)<2 or not np.isfinite(self.times).all() or np.any(np.diff(self.times)<=0):
            raise ValueError('Source camera keys require increasing finite times')
        self.values={field:np.asarray([r[field] for r in keys],float) for field in ('look_at','position','horizontal_fov_degrees')}
        if not all(np.isfinite(v).all() for v in self.values.values()):raise ValueError('Nonfinite source camera key')

    def sample(self,t,field):
        t=np.asarray(t,float)
        if not np.isfinite(t).all() or np.min(t)<self.times[0]-1e-6 or np.max(t)>self.times[-1]+1e-6:
            raise ValueError('Mapped camera time exceeds accepted source keys')
        values=self.values[field]
        if values.ndim==1:return np.interp(t,self.times,values)
        return np.stack([np.interp(t,self.times,values[:,i]) for i in range(values.shape[1])],axis=-1)


def interp(keys,t,field):
    return KeySampler(keys).sample(t,field)

def body_target(entry,shot,t,view,sampler=None):
    values=motion.map_output_time(entry,t,view=view,sex=shot['sex'])
    sampler=sampler or KeySampler(rows(shot))
    return sum(v['weight']*sampler.sample(
        (v['source_seconds']-shot['source_start_seconds'])/shot['source_body_play_rate'],'look_at') for v in values)


def follow_targets(entry,shot,view,cache):
    key=(entry['motion_id'],shot['sex'],shot['orientation'],shot['camera_id'],view)
    if key not in cache:
        sampler=KeySampler(rows(shot))
        total=motion.duration(entry,view,shot['sex']);times=np.arange(round(total*30)+1)/30
        mapped=[motion.map_output_time(entry,float(t),view,shot['sex']) for t in times]
        # Most frames have one source sample; the short repeat seam has two.
        # Both columns are interpolated in a vectorized batch.
        primary=np.asarray([(v[0]['source_seconds']-shot['source_start_seconds'])/shot['source_body_play_rate'] for v in mapped])
        result=sampler.sample(primary,'look_at')
        seam_indices=[i for i,v in enumerate(mapped) if len(v)==2]
        if seam_indices:
            second=np.asarray([(mapped[i][1]['source_seconds']-shot['source_start_seconds'])/shot['source_body_play_rate'] for i in seam_indices])
            weights=np.asarray([mapped[i][1]['weight'] for i in seam_indices])[:,None]
            result[seam_indices]=(1-weights)*result[seam_indices]+weights*sampler.sample(second,'look_at')
        cache[key]=result
    return cache[key]

def make_shot(entry,old,lookup,view,target_cache=None):
    target_cache={} if target_cache is None else target_cache
    # Frames dominate the old payload. Copy metadata only, then add the new keys.
    result=copy.deepcopy({k:v for k,v in old.items() if k not in ('frames','endpoint_validation_frame')})
    duration=motion.duration(entry,view,old['sex'])
    n=round(duration*30); new=[]
    keys=rows(old); first=keys[0]
    cid=old['camera_id']; face=cid=='front_head'
    preset=movement_preset(old) if view=='production10' and not face else {}
    initial=np.array(first['position'])-np.array(first['look_at'])
    startdist=np.linalg.norm(initial); direction=initial/startdist
    enddist=np.linalg.norm(np.array(keys[-1]['position'])-np.array(keys[-1]['look_at']))
    # Common static targets preserve the accepted full/upper tracking policy.
    def targets(framing):
        ref=lookup[(old['motion_id'],old['orientation'],'front_'+framing)]
        return follow_targets(entry,ref,view,target_cache)
    if view=='production10':
        if face:face_targets=follow_targets(entry,old,view,target_cache)
        else:
            kind=preset.get('kind','static')
            fstart=preset.get('start','upper' if 'upper' in cid else 'full')
            fend=preset.get('end',fstart)
            start_targets,end_targets=targets(fstart),targets(fend)
    for i in range(n+1):
        t=i/30
        if view=='full':
            # Identical accepted camera keys, only the body asset reference changes.
            row=copy.deepcopy(keys[i]);row['t']=t;new.append(row);continue
        if face:
            aim=face_targets[i]
            # Accepted per-action face offset and FOV remain unchanged.
            pos=aim+initial
        else:
            u=max(0.,min(1.,t/7.)) if kind.startswith('dolly') else 0.
            u=u*u*(3-2*u)
            aim=(1-u)*start_targets[i]+u*end_targets[i]
            vec=direction.copy()
            if kind=='orbit':
                angle=math.radians(float(preset.get('orbit',360))*t/10.)
                c,s=math.cos(angle),math.sin(angle)
                vec[:2]=[c*direction[0]-s*direction[1],s*direction[0]+c*direction[1]]
            pos=aim+vec*((1-u)*startdist+u*enddist)
        new.append(camera_row(t,pos.tolist(),aim.tolist(),first['horizontal_fov_degrees']))
    variant=entry['variants'][old['sex']]
    if view=='production10':
        asset=variant['production_destination']
        result.update(source_start_seconds=0.,source_body_play_rate=1.,source_end_seconds=10.,window_start_seconds=0.)
    else:
        # Full preview retains accepted windows; special walk remains slow10.
        asset=variant['source_destination']
    result.update(shot_id=f"production_{view}_{old['motion_id'].lower()}_{old['orientation']}_{cid}",
        motion_label=entry['label_zh'],source_animation=asset+'.'+asset.rsplit('/',1)[-1],
        source_clip_id=old['source_clip_id']+'_'+view,
        duration_seconds=duration,frame_count=n,frames=new[:-1],endpoint_validation_frame=new[-1],
        trajectory_sha256=geo.canonical_sha(new),production_view=view,
        original_accepted_shot_id=old['shot_id'],status='geometry_pass')
    # Historical projection diagnostics do not describe the new time domain.
    if view=='production10':
        for field in ('framing_diagnostics','follow_diagnostics','path_metrics'):
            result.pop(field,None)
        result['human_acceptance']='pending_new_10s_review'
        result['geometry_pass_scope']='Finite retimed camera keys and consistent source clock; framing, mesh clearance and visual naturalness pending.'
    result['production_camera_policy']={'body_follow':'accepted_targets_retimed_with_body',
        'orbit_seconds':10,'dolly_finish_seconds':7,'lens_and_distance':'accepted_unchanged',
        'visual_acceptance':'pending_4_trial_review',
        'repeated_seam_scope':'Accepted follow centers use the weighted source clock; local-quaternion body blending can change intermediate WORLD silhouette. Geometry prefers actual baked landmarks.'}
    return result


def source_clip_key(shot,view):
    return shot['source_clip_id']+'_'+view


def make_clip(entry,shot,source,view):
    """Clip identity must match the rewritten shot, including its formal asset."""
    key=source_clip_key(shot,view)
    if view=='production10':
        ready=motion.receipt_variant(entry,shot['sex'],check_assets=True)
        if ready:
            report=motion.read(ready['receipt']['path'])
            clip=copy.deepcopy(report['production_landmarks'])
            if clip['duration_seconds']!=10 or clip['frames'][0]['t']!=0 or clip['frames'][-1]['t']!=10:
                raise ValueError('Baked production landmarks lack inclusive ten-second coverage')
            clip['landmark_provenance']={'kind':'actual_baked_UE_world_pose','receipt':ready['receipt']}
            clip['seam_landmarks_require_baked_UE_resample']=False
        else:
            clip=motion.retime_clip_samples(entry,source,view=view,fps=30)
            clip['landmark_provenance']={'kind':'offline_source_time_map','production_bake_pending':True,
                'seam_shape_limit':'Weighted source WORLD landmarks may differ from local-quaternion blended UE WORLD pose at a repeat seam.'}
    else:
        # Keep original source-time landmarks because the selected full shot
        # still carries its nonzero source_start / source_body_play_rate.
        clip=copy.deepcopy(source)
        clip['landmark_provenance']={'kind':'original_source_full_landmarks'}
    variant=entry['variants'][shot['sex']]
    if clip['landmark_provenance']['kind']!='actual_baked_UE_world_pose' and 'source_package' in clip:
        # Source landmarks may have been measured on a historical source asset.
        # Do not relabel that package pin as the newly created formal copy.
        clip['landmark_source_package']=clip.pop('source_package')
    clip['source_skeleton']=variant['shared_skeleton']
    asset=variant['production_destination' if view=='production10' else 'source_destination']
    path=asset+'.'+asset.rsplit('/',1)[-1]
    clip.update(clip_id=key,asset=path,animation_path=path)
    return clip

def build():
    contract=motion.load_contract();library=geo.load_library()
    entries={m['motion_id']:m for m in contract['motions']}
    old=[s for s in library['shots'] if s['motion_id'] in entries]
    lookup={(s['motion_id'],s['orientation'],s['camera_id']):s for s in old}
    outputs={}
    for view in ('production10','full'):
        target_cache={}
        shots=[make_shot(entries[s['motion_id']],s,lookup,view,target_cache) for s in old]
        clips={}
        for s in old:
            key=source_clip_key(s,view)
            if key in clips:continue
            entry=entries[s['motion_id']]; source=library['clips'][s['source_clip_id']]
            clips[key]=make_clip(entry,s,source,view)
        receipt_pins=[clip['landmark_provenance']['receipt'] for clip in clips.values() if clip['landmark_provenance']['kind']=='actual_baked_UE_world_pose']
        pins=[geo.pin(motion.CONTRACT),geo.pin(__file__),geo.pin(motion.__file__),*library['sources'],*receipt_pins]
        actual_count=len(receipt_pins)
        active={'shots':shots,'clips':clips,'source_sampling_fps':min(c.get('fps',30 if view=='production10' else library['source_sampling_fps']) for c in clips.values()),
                'sources':pins}
        folder=RUN/'camera_library'/view
        plan={'schema':'production_camera_library_v1','view':view,'shots':shots,'sources':pins,
              'matrix':{'actions':26,'cameras':21,'aspects':2,'shots':len(shots)}}
        write(folder/'camera_plan.json',plan)
        write(folder/'catalog.json',geo.build_catalog(active))
        write(folder/'geometry.json',geo.prepare_geometry(active))
        outputs[view]={'shots':len(shots),'plan':str(folder/'camera_plan.json'),'actual_baked_landmark_clips':actual_count,
                       'offline_landmark_clips':len(clips)-actual_count if view=='production10' else 0}
    write(RUN/'camera_library/build_receipt.json',{'success':True,'views':outputs})
    return outputs

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False))
