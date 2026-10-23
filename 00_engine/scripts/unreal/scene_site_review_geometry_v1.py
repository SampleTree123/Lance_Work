"""Offline site-review inputs from the two accepted frozen camera plans.

No Unreal import or camera fitting. Positions use the original actor identity
origin, centimeters and Z-up. Sampling is a screening aid, not collision proof.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'outputs/scene_site_review_20261014_v1'
NONFACE = ROOT / 'outputs/camera_all_motions_portrait115_20261014_v1'
FACE = ROOT / 'outputs/camera_face_closeup_20261014_v2'
SAMPLES = ROOT / 'outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1/all_motion_samples_v1.json'
FOLLOW_CORRECTION = ROOT / 'outputs/camera_follow_general_compact_20261015_v2/follow_correction_v2.json'
CAMERA_STANDARD = ROOT / 'outputs/camera_standard050_accepted_20261015_v3/horizontal_camera_standard_v3.json'
CORRECTED_MOTIONS = ('MOTION_CAND_036', 'ACT_F02_CATCH_BREATH', 'MOTION_CAND_001',
                     'MOTION_CAND_008', 'MOTION_CAND_030', 'MOTION_CAND_035',
                     'ACT_F01_SEXY_DANCE', 'ACT_M04_LIVING_ROOM_SWING')
PLAN_PINS = (
    {'path': str(NONFACE / 'camera_trial_plan_v1.json'),
     'sha256': '30ef018c59b17ac2daa2e58a2596eb8eb964fc3c26b35fda41c188e0eed05792'},
    {'path': str(FACE / 'camera_trial_plan_v1.json'),
     'sha256': 'd4da981bb3aaf8abd730ba34cb805bb1684a988ebe275ce338c6b334814143aa'},
)
CLOCK_FIELDS = ('source_start_seconds', 'source_body_play_rate', 'source_end_seconds',
                'window_start_seconds', 'duration_seconds', 'frame_count', 'fps',
                'source_animation', 'source_clip_id')
GROUND_BONES = ('root', 'foot_l', 'foot_r', 'ball_l', 'ball_r')
BODY_SEGMENTS = (('head', 'neck_01'), ('neck_01', 'spine_02'), ('spine_02', 'pelvis'),
                 ('neck_01', 'upperarm_l'), ('upperarm_l', 'hand_l'),
                 ('neck_01', 'upperarm_r'), ('upperarm_r', 'hand_r'),
                 ('pelvis', 'thigh_l'), ('thigh_l', 'calf_l'), ('calf_l', 'foot_l'),
                 ('foot_l', 'ball_l'), ('pelvis', 'thigh_r'), ('thigh_r', 'calf_r'),
                 ('calf_r', 'foot_r'), ('foot_r', 'ball_r'))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify_pin(record):
    if pin(record['path'])['sha256'] != record['sha256']:
        raise ValueError('Site-review input changed: ' + str(record['path']))


def verify_sources(sources):
    """Call before accepting a cached result; a changed dependency invalidates it."""
    for record in sources:
        verify_pin(record)


def input_fingerprint(sources, selection, sampling):
    return canonical_sha({'sources': sources, 'selection': selection, 'sampling': sampling})


def load_library():
    plans = []
    for record in PLAN_PINS:
        verify_pin(record)
        plans.append(read(record['path']))
    sample_pin = pin(SAMPLES)
    if any(p['source_samples_sha256'] != sample_pin['sha256'] for p in plans):
        raise ValueError('Cached landmarks differ from frozen plan inputs')
    samples = read(SAMPLES)
    if not samples.get('success') or not samples.get('source_assets_unchanged'):
        raise ValueError('Cached source-pose sampling was not successful')
    shots = [s for p in plans for s in p['shots']]
    correction_sources = []
    if FOLLOW_CORRECTION.is_file():
        correction = read(FOLLOW_CORRECTION)
        if correction.get('schema') != 'camera_follow_correction_v2' or not correction.get('success'):
            raise ValueError('Follow correction is not validated')
        verify_sources(correction['basepins'])
        patched = {s['shot_id']: s for s in correction['corrected_shots']}
        expected = {s['shot_id'] for s in shots if s['motion_id'] in CORRECTED_MOTIONS and s['camera_id'] != 'front_head'}
        if len(correction['corrected_shots']) != 320 or len(patched) != 320 or set(patched) != expected:
            raise ValueError('Expected exactly the eight-action nonface correction')
        for shot in shots:
            if shot['shot_id'] in patched:
                new = patched[shot['shot_id']]
                if (shot['motion_id'] not in CORRECTED_MOTIONS
                        or shot['camera_id'] == 'front_head' or _clock(shot) != _clock(new)):
                    raise ValueError('Follow correction changed protected action clock or scope')
                if any(shot[k] != new[k] for k in ('motion_id','sex','camera_id','orientation','width','height')):
                    raise ValueError('Follow correction changed protected shot identity')
        shots = [patched.get(s['shot_id'], s) for s in shots]
        correction_sources = [pin(FOLLOW_CORRECTION), *correction['basepins']]
    import camera_standard_v3 as standard
    config = standard.load_config(CAMERA_STANDARD)
    shots = [standard.apply_standard(s, config) for s in shots]
    correction_sources += [pin(CAMERA_STANDARD), pin(standard.__file__), *config['source_pins']]
    if len(shots) != 1260 or len({s['shot_id'] for s in shots}) != 1260:
        raise ValueError('Expected exactly 1260 unique frozen shots')
    if len({s['motion_id'] for s in shots}) != 30:
        raise ValueError('Expected exactly 30 accepted representative actions')
    return {'shots': shots, 'clips': {c['clip_id']: c for c in samples['clips']},
            'source_sampling_fps': samples['fps'],
            'sources': [*copy.deepcopy(PLAN_PINS), sample_pin, pin(__file__), *correction_sources]}


def _clock(shot):
    return {key: shot[key] for key in CLOCK_FIELDS}


def build_catalog(library=None):
    library = load_library() if library is None else library
    actions, cameras, shots = {}, {}, []
    for shot in library['shots']:
        motion_id, camera_id = shot['motion_id'], shot['camera_id']
        action = {'motion_id': motion_id, 'motion_label': shot['motion_label'],
                  'sex': shot['sex'], 'clock': _clock(shot)}
        if motion_id in actions and actions[motion_id] != action:
            raise ValueError('Action clocks differ across frozen cameras: ' + motion_id)
        actions[motion_id] = action
        cameras[camera_id] = {'camera_id': camera_id, 'camera_label': shot['camera_label']}
        shots.append({key: shot[key] for key in ('shot_id', 'motion_id', 'camera_id', 'orientation',
                                                'sex', 'width', 'height', 'trajectory_sha256')})
    return {'schema': 'scene_site_review_catalog_v1', 'actions': list(actions.values()),
            'cameras': list(cameras.values()), 'shots': shots,
            'matrix': {'actions': len(actions), 'presets': len(cameras),
                       'orientations': 2, 'shots': len(shots)},
            'sources': library['sources']}


def bounds(points):
    values = list(points)
    if not values:
        raise ValueError('Cannot bound empty points')
    return {'minimum_xyz_cm': [float(min(p[k] for p in values)) for k in range(3)],
            'maximum_xyz_cm': [float(max(p[k] for p in values)) for k in range(3)]}


def _indices(frame_count, step):
    return sorted(set(range(0, frame_count + 1, step)) | {frame_count})


def _body_frames(clip, shot):
    """Same numpy interpolation and clock as the accepted camera planners."""
    # NumPy belongs only to offline preparation. UE's bundled Python can import
    # this module and use place_geometry / transform_point without NumPy.
    import numpy as np

    times = np.asarray([r['t'] for r in shot['frames']] + [shot['endpoint_validation_frame']['t']])
    source_times = shot['source_start_seconds'] + times * shot['source_body_play_rate']
    original_times = [r['t'] for r in clip['frames']]
    if source_times.min() < original_times[0] - 1e-5 or source_times.max() > original_times[-1] + 1e-5:
        raise ValueError('Frozen body clock extends beyond cached landmarks')
    result = [{'frame_index': i, 't': float(t), 'source_t': float(st), 'bones': {}}
              for i, (t, st) in enumerate(zip(times, source_times))]
    for bone in clip['frames'][0]['bones']:
        coords = np.asarray([r['bones'][bone] for r in clip['frames']])
        values = np.asarray([np.interp(source_times, original_times, coords[:, k]) for k in range(3)]).T
        for row, value in zip(result, values):
            row['bones'][bone] = value.tolist()
    return result


def _normalize_filter(values, allowed, label):
    result = sorted(set(allowed if values is None else values))
    if not result or not set(result) <= set(allowed):
        raise ValueError('Unknown or empty ' + label + ': ' + str(result))
    return result


def prepare_geometry(library=None, motion_ids=None, camera_ids=None, orientations=None,
                     sample_step_frames=15):
    library = load_library() if library is None else library
    if isinstance(sample_step_frames, bool) or not isinstance(sample_step_frames, int) or sample_step_frames < 1:
        raise ValueError('sample_step_frames must be a positive integer')
    selection = {
        'motion_ids': _normalize_filter(motion_ids, {s['motion_id'] for s in library['shots']}, 'motions'),
        'camera_ids': _normalize_filter(camera_ids, {s['camera_id'] for s in library['shots']}, 'cameras'),
        'orientations': _normalize_filter(orientations, ('landscape', 'portrait'), 'orientations')}
    selected = [s for s in library['shots'] if s['motion_id'] in selection['motion_ids']
                and s['camera_id'] in selection['camera_ids'] and s['orientation'] in selection['orientations']]
    if not selected:
        raise ValueError('Selection contains no frozen shot')
    sampling = {'sample_step_frames': sample_step_frames, 'endpoint_always_included': True,
                'camera_keys_fps': 30, 'cached_landmarks_fps': library['source_sampling_fps'],
                'body_interpolation': 'same linear XYZ interpolation as frozen camera planner',
                'activity_bounds_sampling': 'all frozen output keys including endpoint'}
    actions, shots = {}, []
    for shot in selected:
        clock = _clock(shot)
        indices = _indices(shot['frame_count'], sample_step_frames)
        motion_id = shot['motion_id']
        if motion_id not in actions:
            clip = library['clips'][shot['source_clip_id']]
            if clip['animation_path'] != shot['source_animation']:
                raise ValueError('Cached body clip does not match frozen source animation')
            body = _body_frames(clip, shot)
            samples = []
            for index in indices:
                row = copy.deepcopy(body[index])
                row['ground_probes'] = [
                    {'bone': bone, 'position': list(row['bones'][bone]),
                     'baseline_ground_z_cm': 0., 'baseline_height_cm': row['bones'][bone][2]}
                    for bone in GROUND_BONES if bone in row['bones']]
                samples.append(row)
            actions[motion_id] = {'motion_id': motion_id, 'motion_label': shot['motion_label'],
                'sex': shot['sex'], 'clock': clock, 'samples': samples,
                'root_route': [{'frame_index': row['frame_index'], 't': row['t'],
                                'position': list(row['bones']['root'])} for row in samples],
                'activity_bounds': bounds([point for row in body for point in row['bones'].values()]),
                'root_bounds': bounds([row['bones']['root'] for row in body]),
                'body_segments': [list(pair) for pair in BODY_SEGMENTS],
                'baseline_ground_z_cm': 0.,
                'ground_policy': 'Compare traced environment floor Z against placed baseline floor Z; '
                    'retain each original foot/root height. Jumping and lifted feet are expected motion, '
                    'not evidence of a ground anomaly.',
                'landmark_scope': '18 bone translations; foot/ball are bone proxies, not measured sole vertices'}
        elif actions[motion_id]['clock'] != clock:
            raise ValueError('Frozen action clocks differ between shots')
        rows = shot['frames'] + [shot['endpoint_validation_frame']]
        if len(rows) != shot['frame_count'] + 1:
            raise ValueError('Frozen key count differs from clock')
        samples = [dict(copy.deepcopy(rows[i]), frame_index=i,
                        endpoint=i == shot['frame_count']) for i in indices]
        shots.append({key: shot[key] for key in ('shot_id', 'motion_id', 'motion_label', 'sex',
                     'camera_id', 'camera_label', 'orientation', 'width', 'height', 'trajectory_sha256')}
                     | {'clock': clock, 'samples': samples,
                        'camera_bounds': bounds([r['position'] for r in rows])})
    fingerprint = input_fingerprint(library['sources'], selection, sampling)
    return {'schema': 'scene_site_review_geometry_v1', 'sources': library['sources'],
            'input_fingerprint': fingerprint, 'selection': selection, 'sampling': sampling,
            'coordinate_system': 'cm; Z up; frozen actor identity origin; no initial-root recentering',
            'placement': {'location_xyz_cm': [0., 0., 0.], 'yaw_degrees': 0.},
            'actions': list(actions.values()), 'shots': shots,
            'limitations': ['Sparse checks can miss events between samples.',
                'Cached 10fps landmarks cannot prove mesh, clothing, hair or sole clearance.',
                'Bounds include all interpolated 30fps points; they are proxies, not mesh bounds.',
                'Trace findings are suspected environment conflicts requiring visual review.']}


def transform_point(point, location_xyz_cm, yaw_degrees):
    angle = math.radians(yaw_degrees)
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = point
    return [c*x - s*y + location_xyz_cm[0], s*x + c*y + location_xyz_cm[1], z + location_xyz_cm[2]]


def _transform_bounds(box, location, yaw):
    corners = itertools.product(*zip(box['minimum_xyz_cm'], box['maximum_xyz_cm']))
    result = bounds([transform_point(p, location, yaw) for p in corners])
    result['scope'] = 'conservative transformed full-key local AABB'
    return result


def place_geometry(geometry, location_xyz_cm, yaw_degrees):
    """Transform once from local actor space, preserving every original lens key."""
    values = [*location_xyz_cm, yaw_degrees]
    if len(location_xyz_cm) != 3 or not all(math.isfinite(float(v)) for v in values):
        raise ValueError('Placement needs finite XYZ and yaw')
    if geometry['placement'] != {'location_xyz_cm': [0., 0., 0.], 'yaw_degrees': 0.}:
        raise ValueError('Place the original local geometry; do not compound placements')
    result = copy.deepcopy(geometry)
    point = lambda p: transform_point(p, location_xyz_cm, yaw_degrees)
    for action in result['actions']:
        for row in action['samples']:
            row['bones'] = {bone: point(p) for bone, p in row['bones'].items()}
            for probe in row['ground_probes']:
                probe['position'] = point(probe['position'])
                probe['baseline_ground_z_cm'] += location_xyz_cm[2]
        for row in action['root_route']:
            row['position'] = point(row['position'])
        for key in ('activity_bounds', 'root_bounds'):
            action[key] = _transform_bounds(action[key], location_xyz_cm, yaw_degrees)
        action['baseline_ground_z_cm'] += location_xyz_cm[2]
    for shot in result['shots']:
        for row in shot['samples']:
            row['position'], row['look_at'] = point(row['position']), point(row['look_at'])
            row['rotation_pitch_yaw_roll'][1] += yaw_degrees
        shot['camera_bounds'] = _transform_bounds(shot['camera_bounds'], location_xyz_cm, yaw_degrees)
    result['placement'] = {'location_xyz_cm': list(location_xyz_cm), 'yaw_degrees': yaw_degrees}
    result['placement_fingerprint'] = canonical_sha({'input_fingerprint': result['input_fingerprint'],
                                                   'placement': result['placement']})
    return result


def prepare_inputs(**filters):
    library = load_library()
    catalog = build_catalog(library)
    geometry = prepare_geometry(library, **filters)
    RUN.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, value in (('site_review_catalog_v1.json', catalog),
                        ('site_review_local_geometry_v1.json', geometry)):
        path = RUN / name
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False),
                        encoding='utf-8')
        outputs[name] = pin(path)
    return {'success': True, 'outputs': outputs, 'matrix': catalog['matrix'],
            'selected_shots': len(geometry['shots']), 'input_fingerprint': geometry['input_fingerprint']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion-id', action='append')
    parser.add_argument('--camera-id', action='append')
    parser.add_argument('--orientation', choices=('landscape', 'portrait'), action='append')
    parser.add_argument('--sample-step-frames', type=int, default=15)
    args = parser.parse_args()
    print(json.dumps(prepare_inputs(motion_ids=args.motion_id, camera_ids=args.camera_id,
                     orientations=args.orientation, sample_step_frames=args.sample_step_frames),
                     ensure_ascii=False))
