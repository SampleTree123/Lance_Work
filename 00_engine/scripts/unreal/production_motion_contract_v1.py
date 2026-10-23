"""Offline time contract shared by production body, landmarks and camera clocks.

`full` preserves the selected review clock; `source_full` exposes the entire
unmodified source; `production10` is the approved ten-second construction.
Weighted source times must be applied to BOTH body and camera/landmark values.
No Unreal imports or editor side effects occur in this module.
"""
from __future__ import annotations
import argparse
import bisect
import copy
import hashlib
import json
import math
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
CONTRACT = ENGINE / 'assets/character_creator/production_motion_library_20261017_v1.json'
RUN = ENGINE / 'outputs/production_motion_library_20261017_v1'
SOURCE_ROOT = '/Game/DataMake/Animations/Body/Source'
PRODUCTION_ROOT = '/Game/DataMake/Animations/Body/Production'
REMOVED = ('MOTION_CAND_018', 'MOTION_CAND_034', 'ACT_M02_AUDIENCE_01', 'ACT_M01_BATTLE_DANCE')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify_pin(record):
    if pin(record['path'])['sha256'] != record['sha256']:
        raise ValueError('Changed pinned input: ' + str(record['path']))


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected finite numeric time')
    return float(value)


def duration(entry, view='production10', sex=None):
    if view == 'production10':
        return 10.
    if view == 'full':
        return entry['selected_clock']['duration_seconds']
    if view == 'source_full':
        return entry['variants'][sex or entry['preview_sex']]['source_duration_seconds']
    raise ValueError('Unknown motion view')


def map_output_time(entry, t, view='production10', sex=None):
    """Return [{source_seconds, weight}], including endpoints; no implicit wrap.

    Repeated clips use two exact five-second cycles. Only the 0.2-second seam
    blends the outgoing endpoint with the incoming start, with smoothstep weight.
    Mapping weighted *times* to one averaged time is incorrect across a seam.
    """
    t = finite(t)
    total = duration(entry, view, sex)
    if t < -1e-9 or t > total + 1e-9:
        raise ValueError('Time outside selected view')
    t = min(total, max(0., t))
    if view == 'source_full':
        return [{'source_seconds': t, 'weight': 1.}]
    if view == 'full':
        clock = entry['selected_clock']
        return [{'source_seconds': clock['source_start_seconds'] + t * clock['source_body_play_rate'], 'weight': 1.}]
    policy = entry['production10']
    start, end = policy['source_start_seconds'], policy['source_end_seconds']
    hold_start, hold_end = policy['hold_start_seconds'], policy['hold_end_seconds']
    active = 10 - hold_start - hold_end
    if policy['repeat_count'] == 1:
        phase = max(0., min(active, t - hold_start)) / active
        return [{'source_seconds': start + phase * (end - start), 'weight': 1.}]
    period = active / policy['repeat_count']
    seam = policy['seam_transition_seconds']
    for index in range(1, policy['repeat_count']):
        boundary = hold_start + index * period
        if seam and boundary-seam/2 <= t <= boundary+seam/2:
            x = (t - boundary + seam/2) / seam
            weight = x*x*(3-2*x)
            outgoing = start + min(period, max(0., t-(boundary-period))) / period * (end-start)
            incoming = start + min(period, max(0., t-boundary)) / period * (end-start)
            return [{'source_seconds': outgoing, 'weight': 1-weight}, {'source_seconds': incoming, 'weight': weight}]
    elapsed = min(active, max(0., t-hold_start))
    phase = period if math.isclose(elapsed, active, abs_tol=1e-9) else elapsed % period
    return [{'source_seconds': start + phase/period*(end-start), 'weight': 1.}]


def validate_contract(data, verify_sources=False):
    if data.get('schema') != 'production_motion_library_v1' or len(data.get('motions', [])) != 26:
        raise ValueError('Require exactly 26 production motions')
    ids = [entry['motion_id'] for entry in data['motions']]
    if len(set(ids)) != 26 or set(ids) & set(REMOVED) or set(data['removed_motion_ids']) != set(REMOVED):
        raise ValueError('Wrong retained or removed action identities')
    for entry in data['motions']:
        if set(entry['variants']) != {'female', 'male'}:
            raise ValueError('Require both shared skeleton variants')
        p = entry['production10']
        if p['repeat_count'] not in (1, 2) or p['hold_start_seconds'] < 0 or p['hold_end_seconds'] < 0 or p['hold_start_seconds']+p['hold_end_seconds'] >= 10:
            raise ValueError('Invalid ten-second timing policy')
        if not 0 <= p['seam_transition_seconds'] <= .2 or p['repeat_count'] == 1 and p['seam_transition_seconds']:
            raise ValueError('Unsupported transition')
        for sex, variant in entry['variants'].items():
            if variant['source_destination'] != SOURCE_ROOT+'/'+sex+'/A_'+entry['motion_id']+'_Source' or variant['production_destination'] != PRODUCTION_ROOT+'/'+sex+'/A_'+entry['motion_id']+'_10s':
                raise ValueError('Unexpected formal destination')
            for view in ('production10', 'full', 'source_full'):
                for i in range(301):
                    mapped = map_output_time(entry, duration(entry, view, sex)*i/300, view, sex)
                    if abs(sum(row['weight'] for row in mapped)-1) > 1e-9 or any(not 0 <= row['weight'] <= 1 or not -1e-9 <= row['source_seconds'] <= variant['source_duration_seconds']+1e-7 for row in mapped):
                        raise ValueError('Mapping exceeds source or invalid weights')
            if verify_sources:
                verify_pin(variant['source'])
    if verify_sources:
        for record in data['sources']:
            verify_pin(record)
    return data


def load_contract(path=CONTRACT, verify_sources=False):
    return validate_contract(read(path), verify_sources)


def _interpolate_frame(clip, time):
    frames = clip['frames']
    times = [f['t'] for f in frames]
    if time < times[0]-1e-7 or time > times[-1]+1e-7:
        raise ValueError('Landmark sampling does not cover source time')
    index = max(0, min(len(frames)-2, bisect.bisect_right(times, time)-1))
    a, b = frames[index:index+2]
    alpha = min(1., max(0., (time-a['t'])/(b['t']-a['t'])))
    return {name: [(1-alpha)*x+alpha*y for x,y in zip(xyz,b['bones'][name])] for name,xyz in a['bones'].items()}


def retime_clip_samples(entry, clip, view='production10', fps=30):
    """World landmarks for camera fitting; same weighted clock as body bake.

    These are screening landmarks. Blended local rotations can make the actual
    UE world pose differ during the seam; use the baked UE sample for final fit.
    """
    if clip['motion_id'] != entry['motion_id'] or clip['sex'] not in entry['variants']:
        raise ValueError('Mismatched source landmark clip')
    total = duration(entry, view, clip['sex'])
    count = round(total * fps)
    if fps <= 0 or not math.isclose(count/fps,total,abs_tol=1e-8):
        raise ValueError('View duration is not frame representable')
    result = copy.deepcopy({k:v for k,v in clip.items() if k != 'frames'})
    result.update(duration_seconds=total, window_start_seconds=0., window_duration_seconds=total,
                  view=view, source_asset=clip['asset'], frames=[], timing_contract_motion_id=entry['motion_id'])
    for i in range(count+1):
        t = i/fps
        samples = [(row['weight'],_interpolate_frame(clip,row['source_seconds'])) for row in map_output_time(entry,t,view,clip['sex'])]
        bones = {name: [sum(weight*pose[name][axis] for weight,pose in samples) for axis in range(3)] for name in samples[0][1]}
        result['frames'].append({'t':t,'bones':bones})
    result['seam_landmarks_require_baked_UE_resample'] = entry['production10']['repeat_count'] > 1 and view == 'production10'
    return result


def retime_camera_keys(entry, source_keys, view='production10', fps=30, sex=None):
    """Retimes numeric camera key fields with the exact action clock.

    source_keys are {t, ...numeric/list fields}; times are source-animation time.
    Angles must be unwrapped before this interpolation. Camera fitting from the
    retimed/baked body landmarks is preferred for orbit/follow trajectories.
    """
    def lerp(a,b,w):
        if isinstance(a,(tuple,list)):
            return [lerp(x,y,w) for x,y in zip(a,b)]
        return (1-w)*finite(a)+w*finite(b)
    times = [row['t'] for row in source_keys]
    def sample(t):
        if not times or t < times[0]-1e-7 or t > times[-1]+1e-7:
            raise ValueError('Camera keys do not cover source clock')
        j = max(0,min(len(times)-2,bisect.bisect_right(times,t)-1))
        a,b = source_keys[j:j+2]
        w = min(1.,max(0.,(t-a['t'])/(b['t']-a['t'])))
        return {k:lerp(a[k],b[k],w) for k in a if k != 't'}
    total = duration(entry,view,sex)
    count = round(total*fps)
    if fps <= 0 or not math.isclose(count/fps,total,abs_tol=1e-8):
        raise ValueError('Camera duration is not frame representable')
    output=[]
    for i in range(count+1):
        t=i/fps
        mapped=map_output_time(entry,t,view,sex)
        values=[sample(row['source_seconds']) for row in mapped]
        value=values[0] if len(values)==1 else {k:lerp(values[0][k],values[1][k],mapped[1]['weight']) for k in values[0]}
        output.append(dict(value,t=t))
    return output


def build_tasks(data=None, run=RUN):
    data = data or load_contract()
    contract_pin = pin(CONTRACT)
    return [{'motion_id':entry['motion_id'],'sex':sex,'contract':contract_pin,
             'report_path':str(Path(run)/'assets'/(entry['motion_id']+'_'+sex+'.json'))}
            for entry in data['motions'] for sex in ('female','male')]


def receipt_variant(entry, sex, run=RUN, check_assets=True):
    """Resolve only a successful hash-bound bake; pending assets stay unavailable."""
    path=Path(run)/'assets'/(entry['motion_id']+'_'+sex+'.json')
    if not path.exists():return None
    report=read(path);variant=entry['variants'][sex]
    expected_task={'motion_id':entry['motion_id'],'sex':sex,'contract':pin(CONTRACT),'report_path':str(path)}
    verify=report.get('verification',{})
    limits={'translation_cm':.00035,'rotation_degrees':.025,'scale_abs':.00001}
    errors=verify.get('maximum_physical_errors',{})
    if report.get('schema')!='production_motion_bake_v1' or report.get('success') is not True or report.get('task')!=expected_task:
        raise ValueError('Missing successful exact production task receipt')
    if report.get('sources_unchanged') is not True or report.get('new_dirty_packages_outside_target')!=[] or report.get('dirty_sources')!=[] or report.get('faces_included') is not False:
        raise ValueError('Production source preservation proof incomplete')
    if verify.get('duration_seconds')!=10 or verify.get('all_frames_verified') is not True or verify.get('bone_count')!=118 or verify.get('body_tracks')!=108 or verify.get('physical_limits')!=limits or set(errors)!=set(limits):
        raise ValueError('Production all-frame proof incomplete')
    scale_proof=verify.get('native_constant_scale_proof')
    scale_pass=math.isfinite(errors['scale_abs']) and 0<=errors['scale_abs']<=limits['scale_abs']
    if not scale_pass and isinstance(scale_proof,dict):
        channels=scale_proof.get('channels',[])
        scale_pass=(scale_proof.get('schema')=='ue_native_constant_scale_proof_v1' and scale_proof.get('success') is True
            and scale_proof.get('strict_scale_limit')==1e-5 and scale_proof.get('constant_channel_limit')==1e-4
            and scale_proof.get('first_default_match_limit')==1e-6 and bool(channels)
            and all(row.get('native_constant_channel_proven') is True and 1e-5<row['maximum_error']<=1e-4
                    and 0<=row['expected_max_deviation_from_first']<=1e-4
                    and 0<=row['actual_max_deviation_from_expected_first']<=1e-6 for row in channels)
            and math.isclose(max(row['maximum_error'] for row in channels),errors['scale_abs'],abs_tol=1e-12,rel_tol=0)
            and len(scale_proof.get('engine_precision_basis',[]))==2)
    rotation_proof=verify.get('native_euler_singularity_proof')
    rotation_pass=math.isfinite(errors['rotation_degrees']) and 0<=errors['rotation_degrees']<=limits['rotation_degrees']
    if not rotation_pass and isinstance(rotation_proof,dict):
        samples=rotation_proof.get('samples',[])
        rotation_pass=(rotation_proof.get('schema')=='ue_native_euler_singularity_proof_v1' and rotation_proof.get('success') is True
            and rotation_proof.get('strict_rotation_limit_degrees')==.025 and rotation_proof.get('singularity_rotation_limit_degrees')==.12
            and rotation_proof.get('prediction_component_limit')==1e-5 and bool(samples)
            and all(row.get('native_singularity_projection_proven') is True and .025<row['error']<=.12
                and abs(row['float32_singularity_test'])>row['float32_threshold']
                and 0<=row['predicted_actual_max_quaternion_component_error']<=1e-5 for row in samples)
            and math.isclose(max(row['error'] for row in samples),errors['rotation_degrees'],abs_tol=1e-12,rel_tol=0)
            and len(rotation_proof.get('engine_precision_basis',[]))==3)
    if not math.isfinite(errors['translation_cm']) or not 0<=errors['translation_cm']<=limits['translation_cm'] or not rotation_pass or not scale_pass or any(not math.isfinite(verify.get(k,float('inf'))) or not 0<=verify[k]<=1e-4 for k in ('maximum_curve_error','maximum_root_component_error')):
        raise ValueError('Production numerical proof failed')
    fps=verify.get('fps',0)
    if not isinstance(fps,(int,float)) or not math.isfinite(fps) or fps<=0 or verify.get('all_frame_count')!=round(10*fps)+1:
        raise ValueError('Production frame grid proof incomplete')
    for field,destination in (('asset_record','production_destination'),('source_asset_record','source_destination')):
        if report[field]['asset'].split('.')[0]!=variant[destination]:raise ValueError('Production destination differs')
    if report['sources'][0]['sha256']!=variant['source']['sha256'] or report['sources'][0]['asset'].split('.')[0]!=variant['source']['asset'].split('.')[0]:
        raise ValueError('Original production input differs')
    if check_assets:
        for record in report['sources']+[report['asset_record'],report['source_asset_record']]:verify_pin(record)
        if scale_proof:
            for record in scale_proof.get('engine_precision_basis',[]):verify_pin(record)
        if rotation_proof:
            for record in rotation_proof.get('engine_precision_basis',[]):verify_pin(record)
    return {'source':report['source_asset_record'],'production10':report['asset_record'],'receipt':pin(path),
            'source_duration_seconds':variant['source_duration_seconds'],'shared_skeleton':variant['shared_skeleton']}


def publish_runtime_manifest(run=RUN, require_complete=True, check_assets=True):
    """Derive usable asset paths from receipts without changing the pinned policy."""
    data=load_contract();motions=[];count=0
    for entry in data['motions']:
        variants={}
        for sex in ('female','male'):
            variant=receipt_variant(entry,sex,run,check_assets)
            if variant is not None:variants[sex]=variant;count+=1
        motions.append({'motion_id':entry['motion_id'],'label_zh':entry['label_zh'],'preview_sex':entry['preview_sex'],
                        'selected_clock':entry['selected_clock'],'production10':entry['production10'],'variants':variants})
    if require_complete and count!=52:raise ValueError('Need all52 successful production variants before final publication')
    result={'schema':'production_motion_runtime_library_v1','contract':pin(CONTRACT),'motions':motions,
            'ready_variant_count':count,'expected_variant_count':52,'complete':count==52,'human_naturalness_acceptance':'pending'}
    output=Path(run)/'runtime_motion_library_v1.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify-sources',action='store_true');parser.add_argument('--tasks',type=Path)
    args=parser.parse_args();data=load_contract(verify_sources=args.verify_sources)
    if args.tasks:
        args.tasks.parent.mkdir(parents=True,exist_ok=True)
        args.tasks.write_text(json.dumps({'schema':'production_motion_tasks_v1','tasks':build_tasks(data)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'motions':len(data['motions']),'variants':sum(len(x['variants']) for x in data['motions']),'source_hashes_checked':args.verify_sources}))
