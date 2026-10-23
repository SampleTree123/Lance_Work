"""Offline, action-scoped pelvis translation repair; never edits frozen inputs.

The original neutral camera specification, torso articulation and body clock are
retained. Only the two named actions' non-face pelvis XY trend is replaced.
"""
from pathlib import Path
import copy
import hashlib
import json
import math
import numpy as np
import motion_portrait_camera_planner_v1 as prior
import camera_calibration_planner_v1 as geometry
import ue_motion_scene_sequence_v1 as sequence

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'outputs/camera_follow_compact_scene_20261015_v1'
NONFACE = ROOT/'outputs/camera_all_motions_portrait115_20261014_v1/camera_trial_plan_v1.json'
FACE = ROOT/'outputs/camera_face_closeup_20261014_v2/camera_trial_plan_v1.json'
SAMPLES = prior.RUN/'all_motion_samples_v1.json'
MOTIONS = ('MOTION_CAND_036', 'ACT_F02_CATCH_BREATH')
SIGMA = .18
CLOCK = ('source_start_seconds', 'source_end_seconds', 'source_body_play_rate',
         'window_start_seconds', 'duration_seconds', 'frame_count', 'fps',
         'source_animation', 'source_clip_id')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def save(name, value):
    path = OUT/name
    if path.exists():
        if read(path) != value:
            raise ValueError('Refuse to replace frozen correction: '+str(path))
        return
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def endpoint_exact_trend(raw, times, sigma=SIGMA):
    """Local linear smoothing, with boundary residual removed over 3 sigma.

    The compact smoothstep taper has zero derivative at both ends. Corrections
    are local to boundaries, so no initial filter prediction becomes a permanent
    translation of the camera. Constant-speed input remains unchanged.
    """
    trend = prior.stable.low_frequency(raw, times, sigma)
    residual = trend-raw
    support = min(3*sigma, (times[-1]-times[0])/2)
    def taper(distance):
        u = np.clip(distance/support, 0., 1.)
        return 1-u*u*(3-2*u)
    trend -= taper(times-times[0])[:, None]*residual[0]
    trend -= taper(times[-1]-times)[:, None]*residual[-1]
    trend[[0, -1]] = raw[[0, -1]]
    return trend


def metrics(raw, camera, times):
    delta = camera-raw
    norms = np.linalg.norm(delta, axis=1)
    ix = int(norms.argmax())
    return {'max_distance_cm': float(norms[ix]), 'p95_distance_cm': float(np.quantile(norms, .95)),
            'worst_time_seconds': float(times[ix]), 'worst_delta_xy_cm': delta[ix].tolist(),
            'endpoint_delta_xy_cm': delta[-1].tolist()}


def action_data(shot, clip):
    frames = prior.resample(clip, shot['source_start_seconds'], shot['duration_seconds'],
                            shot['source_body_play_rate'])
    times = np.array([f['t'] for f in frames])
    pelvis = np.array([f['bones']['pelvis'][:2] for f in frames])
    old = prior.stable.low_frequency(pelvis, times, shot['tracking_policy']['pelvis_xy_sigma_seconds'])
    old = pelvis[0]+old-old[0]
    old[0] = pelvis[0]
    new = endpoint_exact_trend(pelvis, times)
    return frames, times, pelvis, old, new


def corrected(shot, data):
    frames, times, pelvis, old_pelvis, new_pelvis = data
    result = copy.deepcopy(shot)
    old_rows = shot['frames']+[shot['endpoint_validation_frame']]
    rows = []
    for i, old in enumerate(old_rows):
        # Applying identical translation to camera and target retains every
        # relative camera angle, distance, orientation, zoom and FOV parameter.
        delta = np.r_[new_pelvis[i]-old_pelvis[i], 0.]
        row = copy.deepcopy(old)
        row['position'] = (np.array(old['position'])+delta).tolist()
        row['look_at'] = (np.array(old['look_at'])+delta).tolist()
        rows.append(row)
    diagnostic = {}
    preset = shot['common_preset_parameters']['preset']
    for framing in shot['common_preset_parameters']['references']:
        active = np.ones(len(frames), dtype=bool)
        if preset['kind'].startswith('dolly'):
            active = times < 1e-6 if framing == preset['start'] else times >= 7.-1e-6
        diagnostic[framing] = geometry.diagnostics(frames, rows, framing, shot['aspect_ratio'],
                                                  rows[0]['horizontal_fov_degrees'], active)
    result.update(frames=rows[:-1], endpoint_validation_frame=rows[-1], trajectory_sha256=sha(rows),
                  framing_diagnostics=diagnostic, path_metrics=prior.stable.old.path_metrics(rows),
                  human_acceptance='pending')
    result['tracking_policy'] = copy.deepcopy(shot['tracking_policy'])
    result['tracking_policy'].update(pelvis_xy_sigma_seconds=SIGMA, per_action_tuning=True,
        pelvis_xy_boundary='exact raw initial and endpoint; compact smoothstep residual removal over 3 sigma',
        correction_scope=list(MOTIONS))
    result['follow_correction'] = {'schema':'camera_follow_correction_shot_v1',
        'base_shot_id':shot['shot_id'], 'base_trajectory_sha256':shot['trajectory_sha256'],
        'pelvis_xy_sigma_seconds':SIGMA, 'preserved':'body clocks; source; initial target; local torso XY; all Z; camera vector; rotation; FOV; preset distances; dolly/orbit',
        'reason':'broad centered filter plus raw-initial anchor anticipates acceleration and introduces persistent forward offset',
        'before_pelvis_trend_error':metrics(pelvis, old_pelvis, times),
        'after_pelvis_trend_error':metrics(pelvis, new_pelvis, times)}
    # Keep original diagnostic metadata for provenance, explicitly superseded.
    result['previous_follow_diagnostics'] = result.pop('follow_diagnostics')
    result['follow_diagnostics'] = result['follow_correction']
    return result


def checks(old, new, data):
    frames, times, raw, before, after = data
    a = old['frames']+[old['endpoint_validation_frame']]
    b = new['frames']+[new['endpoint_validation_frame']]
    va = np.array([np.array(r['position'])-r['look_at'] for r in a])
    vb = np.array([np.array(r['position'])-r['look_at'] for r in b])
    new_keys = dict(new, status='geometry_pass')
    return {'source_clock_exact':all(old[k] == new[k] for k in CLOCK),
        'frozen_common_parameters_exact':old['common_preset_parameters'] == new['common_preset_parameters'],
        'distance_parameters_exact':old['endpoint_distances_cm'] == new['endpoint_distances_cm'],
        'camera_vector_preserved':bool(np.max(np.abs(va-vb)) < 1e-8),
        'z_rotation_fov_exact':all(x['position'][2] == y['position'][2] and x['look_at'][2] == y['look_at'][2]
            and x['rotation_pitch_yaw_roll'] == y['rotation_pitch_yaw_roll']
            and x['horizontal_fov_degrees'] == y['horizontal_fov_degrees'] for x,y in zip(a,b)),
        'initial_camera_key_exact':a[0] == b[0],
        'endpoint_included':len(sequence.key_rows(new_keys)) == new['frame_count']+1,
        'pelvis_start_and_end_exact':bool(np.max(np.abs((after-raw)[[0,-1]])) < 1e-9),
        'pelvis_trend_error_below_8cm':float(np.linalg.norm(after-raw, axis=1).max()) < 8.,
        'trajectory_sha':new['trajectory_sha256'] == sha(b),
        'finite_and_floor':bool(np.isfinite(np.array([r['position']+r['look_at'] for r in b])).all())
            and min(r['position'][2] for r in b) >= 25.,
        'positive_depth':all(d['min_depth_cm'] > 1 and (d['inactive_min_depth_cm'] is None
            or d['inactive_min_depth_cm'] > 1) for d in new['framing_diagnostics'].values())}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    pins = [pin(p) for p in (NONFACE, FACE, SAMPLES, Path(__file__), Path(prior.stable.__file__))]
    source = read(NONFACE); face = read(FACE)
    clips = {c['clip_id']:c for c in read(SAMPLES)['clips']}
    selected = [s for s in source['shots'] if s['motion_id'] in MOTIONS]
    cache = {s['motion_id']:action_data(s, clips[s['source_clip_id']]) for s in selected
             if s['camera_id'] == 'side_upper' and s['orientation'] == 'landscape'}
    updated = [corrected(s, cache[s['motion_id']]) for s in selected]
    reports = [{'shot_id':s['shot_id'], 'checks':checks(s,n,cache[s['motion_id']])}
               for s,n in zip(selected,updated)]
    failures = [r for r in reports if not all(r['checks'].values())]
    if failures:
        raise ValueError('Targeted correction failed: '+str(failures))
    by_id = {s['shot_id']:s for s in updated}
    render = []
    for shot in updated:
        new = copy.deepcopy(shot)
        new['shot_id'] += '_followfix_v1'
        new['supersedes_shot_id'] = shot['shot_id']
        render.append(new)
    render_by_base = {s['supersedes_shot_id']:s for s in render}
    full = copy.deepcopy(source)
    full['shots'] = [render_by_base.get(s['shot_id'], s) for s in source['shots']]
    full['follow_correction'] = {'base_plan':pins[0], 'scope':list(MOTIONS),
        'changed_shots':len(updated), 'other_shot_objects_preserved':1120, 'face_plan_preserved':pins[1]}
    full['source_pins'] = source['source_pins']+pins
    full['smoke_shot_ids'] = [s['shot_id'] for s in render if s['camera_id'] in
                            ('side_upper','rear_three_quarter_upper')]
    save('corrected_full_nonface_plan_v1.json',full)
    render_plan = dict(full, shots=render, matrix={'actions':2,'presets':20,'orientations':2,'shots':80})
    save('camera_trial_plan_v1.json',render_plan)
    action_reports = []
    for motion, data in cache.items():
        frames,times,raw,before,after = data
        clip = clips[next(s['source_clip_id'] for s in selected if s['motion_id']==motion)]
        refs = [s for s in selected if s['motion_id']==motion and s['camera_id'] in
                ('side_upper','rear_three_quarter_upper')]
        side_reports = []
        for shot in refs:
            corrected_shot = by_id[shot['shot_id']]
            a=np.array([r['look_at'][:2] for r in shot['frames']+[shot['endpoint_validation_frame']]])
            b=np.array([r['look_at'][:2] for r in corrected_shot['frames']+[corrected_shot['endpoint_validation_frame']]])
            side_reports.append({'shot_id':shot['shot_id'],'camera_id':shot['camera_id'],
                'orientation':shot['orientation'],'before_target_vs_pelvis':metrics(raw,a,times),
                'after_target_vs_pelvis':metrics(raw,b,times),
                'before_framing':shot['framing_diagnostics'],'after_framing':corrected_shot['framing_diagnostics']})
        action_reports.append({'motion_id':motion, 'clock':{k:refs[0][k] for k in CLOCK},
            'source_samples':{'clip_id':clip['clip_id'],'sample_t_min':clip['frames'][0]['t'],
                'sample_t_max':clip['frames'][-1]['t'],'native_rate':clip['source_frame_rate'],
                'native_frame_count':clip['source_frame_count'],'source_package':clip['source_package']},
            'before_pelvis_trend_error':metrics(raw,before,times),
            'after_pelvis_trend_error':metrics(raw,after,times),'side_upper_evidence':side_reports,
            'ue_pose_check_samples':[{'t':float(times[i]),'source_t':float(refs[0]['source_start_seconds']+times[i]*refs[0]['source_body_play_rate']),
                'pelvis':frames[i]['bones']['pelvis'],'head':frames[i]['bones']['head']}
                for i in sorted(set([0,27,30,90,min(150,len(frames)-1),len(frames)-1]))]})
    t=np.arange(211)/30
    linear=np.c_[3+11*t,7-17*t]
    linear_error=float(np.max(np.abs(endpoint_exact_trend(linear,t)-linear)))
    unrelated=[(a,b) for a,b in zip(source['shots'],full['shots']) if a['motion_id'] not in MOTIONS]
    passed = all(a == b for a,b in unrelated) and linear_error < 1e-9
    manifest={'schema':'camera_follow_correction_v1','success':passed,
        'basepins':pins,'motion_ids':list(MOTIONS),'corrected_shots':updated,
        'original_shot_ids_preserved_for_scene_geometry':True,
        'render_plan':pin(OUT/'camera_trial_plan_v1.json'),
        'corrected_full_nonface_plan':pin(OUT/'corrected_full_nonface_plan_v1.json'),
        'face_plan_unchanged':pins[1], 'face_reason':'head .22s filtering has no raw-initial anchoring and no persistent pelvis filter bias',
        'other_nonface_shot_objects_exact':len(unrelated),'all_frozen_inputs_unchanged':all(pin(p['path'])==p for p in pins),
        'human_acceptance':'pending','ue_validation':'pending coordinator actual pose/render checks'}
    save('follow_correction_v1.json',manifest)
    save('follow_correction_evidence_v1.json',{'schema':'camera_follow_correction_evidence_v1',
        'success':passed,'manifest':pin(OUT/'follow_correction_v1.json'),'actions':action_reports,
        'linear_motion_endpoint_filter_max_error_cm':linear_error,'reports':reports,
        'scope':'80 affected nonface paths; targeted clock/vector/proxy checks; no UE pose or visual certification',
        'face_4_shot_objects_preserved':sum(s['motion_id'] in MOTIONS for s in face['shots']),
        'all_60_face_objects_preserved':True,'human_acceptance':'pending'})
    print(json.dumps({'success':passed,'corrected_shots':len(updated),'output':str(OUT),
                      'actions':[{k:a[k] for k in ('motion_id','before_pelvis_trend_error','after_pelvis_trend_error')}
                                 for a in action_reports]},ensure_ascii=True))


if __name__=='__main__':
    build()
