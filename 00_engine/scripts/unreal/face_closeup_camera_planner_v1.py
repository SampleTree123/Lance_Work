"""Bake head-translation closeups without connecting to Unreal.

The accepted non-face plan and its body clocks are read-only inputs. Each new
shot has one frozen distance and camera direction. Head rotation is deliberately
not an input: turning may reveal a profile or the back of the head.
"""
from pathlib import Path
import copy
import hashlib
import json
import math
import numpy as np
import camera_stable_follow_planner_v1 as stable
import motion_portrait_camera_planner_v1 as prior
import ue_motion_scene_sequence_v1 as sequence

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'outputs/camera_face_closeup_20261014_v1'
ACCEPTED = ROOT / 'outputs/camera_all_motions_portrait115_20261014_v1'
ACCEPTED_SHA = '30ef018c59b17ac2daa2e58a2596eb8eb964fc3c26b35fda41c188e0eed05792'
CLOCK_FIELDS = ('source_start_seconds', 'source_body_play_rate', 'source_end_seconds',
                'window_start_seconds', 'duration_seconds', 'frame_count', 'fps',
                'source_animation', 'source_clip_id')
PILOTS = ('MOTION_CAND_002', 'MOTION_CAND_003', 'MOTION_CAND_030',
          'MOTION_CAND_008', 'MOTION_CAND_029')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def save(name, document):
    """Identical replay is safe; revision of a frozen result requires a new run."""
    path = RUN / name
    if path.exists():
        if read(path) == document:
            return
        raise ValueError('Refuse to replace frozen face result: ' + str(path))
    with path.open('x', encoding='utf-8') as stream:
        json.dump(document, stream, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def action_tracking(frames, motion_id):
    """Select a bounded, explicit filter width from the accepted head translation."""
    times = np.array([f['t'] for f in frames])
    head = np.array([f['bones']['head'] for f in frames])
    # Smaller sigma for large/rapid articulation, broader for near-static poses.
    # These are seconds in the final output clock, including accepted slowdowns.
    speed = np.linalg.norm(np.diff(head, axis=0), axis=1)*30.
    p95 = float(np.quantile(speed, .95))
    sigma = .22 if p95 >= 50. else .28 if p95 >= 20. else .34
    overrides = {'MOTION_CAND_003': .22, 'MOTION_CAND_030': .22,
                 'MOTION_CAND_008': .28, 'MOTION_CAND_029': .22,
                 'MOTION_CAND_002': .34}
    sigma = overrides.get(motion_id, sigma)
    filtered = stable.low_frequency(head, times, sigma)
    residual = head-filtered
    return filtered, {
        'reference': 'head bone world XYZ translation only',
        'filter': 'symmetric local-linear Gaussian, support +/-3 sigma',
        'sigma_seconds': sigma, 'translation_gain': 1.,
        'uses_head_rotation': False, 'uses_pelvis_heading': False,
        'heading_pursuit': False, 'offline_centered_filter': True,
        'constant_velocity_preserved_including_endpoints': True,
        'raw_head_speed_p95_cm_s': p95,
        'residual_xyz_max_abs_cm': np.abs(residual).max(axis=0).tolist(),
        'residual_distance_p95_cm': float(np.quantile(np.linalg.norm(residual, axis=1), .95)),
        'raw_head_xyz_range_cm': np.ptp(head, axis=0).tolist(),
        'filtered_head_xyz_range_cm': np.ptp(filtered, axis=0).tolist(),
        'per_action_override': motion_id in overrides,
    }


def proxies(frames):
    """Conservative head envelope; shoulders are composition context, not a fit gate.

    Existing cached samples have translations, not bone rotations or silhouettes.
    World-axis padding therefore surrounds the cranium across profile/back views.
    Hair beyond this envelope still needs visual review.
    """
    head = np.array([f['bones']['head'] for f in frames])
    neck = np.array([f['bones']['neck_01'] for f in frames])
    offsets = np.array([[x, y, z] for x in (-13., 13.) for y in (-13., 13.)
                        for z in (-8., 22.)])
    head_box = head[:, None, :]+offsets[None, :, :]
    shoulders = np.stack([neck+[x, 0., -11.] for x in (-24., 24.)], axis=1)
    return head_box, shoulders


def projection(points, targets, distance, aspect, fov):
    # Fixed camera on the neutral character's +Y side, looking along -Y.
    positions = targets+np.array([0., distance, 0.])
    delta = points-positions[:, None, :]
    depth = -delta[:, :, 1]
    half = math.tan(math.radians(fov/2.))
    uv = np.stack([.5+delta[:, :, 0]/(2*depth*half),
                   .5-delta[:, :, 2]*aspect/(2*depth*half)], axis=-1)
    return uv, depth


def fit_distance(head_proxy, targets, spec):
    """One offline distance per shot; never modify it during the action."""
    fov, aspect = spec['horizontal_fov_degrees'], spec['width']/spec['height']
    low, high = spec['nominal_distance_cm'], 600.
    for _ in range(40):
        distance = (low+high)/2
        uv, depth = projection(head_proxy, targets, distance, aspect, fov)
        safe = depth.min() > 1. and uv.min() >= .09 and uv.max() <= .91
        if safe:
            high = distance
        else:
            low = distance
    return float(high)


def make_shot(source, frames, filtered, tracking, orientation, spec, config):
    targets = filtered+np.array(spec['target_offset_from_head_cm'])
    head_proxy, shoulders = proxies(frames)
    distance = fit_distance(head_proxy, targets, spec)
    rows = [stable.old.camera_row(float(f['t']), (target+[0., distance, 0.]).tolist(),
                                  target.tolist(), spec['horizontal_fov_degrees'])
            for f, target in zip(frames, targets)]
    aspect = spec['width']/spec['height']
    uv, depth = projection(head_proxy, targets, distance, aspect, spec['horizontal_fov_degrees'])
    shoulder_uv, _ = projection(shoulders, targets, distance, aspect, spec['horizontal_fov_degrees'])
    head_center, _ = projection(np.array([f['bones']['head'] for f in frames])[:, None, :],
                                 targets, distance, aspect, spec['horizontal_fov_degrees'])
    diagnostic = {
        'head_envelope_outside_frame_count': int(np.any((uv < 0)|(uv > 1), axis=(1, 2)).sum()),
        'head_envelope_margin_excursion_count': int(np.any((uv < .09-1e-8)|(uv > .91+1e-8), axis=(1, 2)).sum()),
        'head_envelope_uv_bounds': [uv.min(axis=(0, 1)).tolist(), uv.max(axis=(0, 1)).tolist()],
        'head_envelope_height_fraction_range': [float(np.ptp(uv[:, :, 1], axis=1).min()), float(np.ptp(uv[:, :, 1], axis=1).max())],
        'head_bone_uv_bounds': [head_center.min(axis=(0, 1)).tolist(), head_center.max(axis=(0, 1)).tolist()],
        'shoulder_context_visible_frame_count': int(np.all((shoulder_uv >= 0)&(shoulder_uv <= 1), axis=(1, 2)).sum()),
        'min_depth_cm': float(depth.min()),
        'scope': 'cached 10Hz skeletal translations interpolated to 30fps; conservative head padding; no silhouette or visibility guarantee',
    }
    result = {k: copy.deepcopy(source[k]) for k in CLOCK_FIELDS}
    result.update(
        shot_id=f"faceclose_{source['motion_id'].lower()}_{source['sex']}_{orientation[0]}_front_head_v1",
        status='geometry_pass', group='cameras', motion_id=source['motion_id'],
        motion_label=source['motion_label'], sex=source['sex'], camera_id='front_head',
        camera_label='面部近景（柔和跟随头部位置）', orientation=orientation,
        width=spec['width'], height=spec['height'], aspect_ratio=aspect,
        initial_facing={'method': 'frozen_neutral_character_axis', 'yaw_degrees': 90.},
        frames=rows[:-1], endpoint_validation_frame=rows[-1], trajectory_sha256=canonical_sha(rows),
        calibration_config_sha256=canonical_sha(config), endpoint_distances_cm=[distance, distance],
        tracking_policy=copy.deepcopy(tracking), framing_diagnostics={'head': diagnostic},
        path_metrics=stable.old.path_metrics(rows), cropping_allowed=True,
        human_acceptance='pending', exceptions_require_review=False,
        source_overview_shot_id=source['shot_id'], native_source_proof=copy.deepcopy(source['native_source_proof']),
        window_scope='complete_selected_window',
        distance_policy='one offline fitted constant distance per action/orientation; no in-shot zoom',
        follow_policy='soft head XYZ translation; fixed +Y camera direction; no yaw pursuit',
        geometry_pass_scope='finite uniform keys; head-envelope margin; positive depth; camera above floor',
        face_visibility_guaranteed=False,
        limitations=['profile/back of head and source head tilts remain visible when the motion turns',
                     'hands/hair may occlude face; shoulders may leave the image',
                     'skeletal proxy geometry is not human acceptance or silhouette certification'])
    return result


def checks(shot, source):
    rows = shot['frames']+[shot['endpoint_validation_frame']]
    vector = np.array([np.array(r['position'])-r['look_at'] for r in rows])
    diag = shot['framing_diagnostics']['head']
    return {
        'source_clock_fields_exact': all(shot[k] == source[k] for k in CLOCK_FIELDS),
        'representative_sex_exact': shot['sex'] == source['sex'],
        'consumer_key_schema': len(sequence.key_rows(shot)) == shot['frame_count']+1,
        'finite_keys': bool(np.isfinite(np.array([r['position']+r['look_at'] for r in rows])).all()),
        'fixed_relative_vector_no_yaw_pursuit_or_zoom': bool(np.max(np.abs(vector-vector[0])) < 1e-8),
        'fixed_fov': all(r['horizontal_fov_degrees'] == 35. for r in rows),
        'head_proxy_margin': diag['head_envelope_margin_excursion_count'] == 0,
        'positive_depth': diag['min_depth_cm'] > 1.,
        'above_floor': min(r['position'][2] for r in rows) >= 25.,
        'trajectory_sha': canonical_sha(rows) == shot['trajectory_sha256'],
    }


def build():
    accepted_plan = pin(ACCEPTED/'camera_trial_plan_v1.json')
    if accepted_plan['sha256'] != ACCEPTED_SHA:
        raise ValueError('Accepted non-face plan changed')
    manifest_path = ACCEPTED/'motion_sources_v1.json'
    manifest = read(manifest_path)
    sources = manifest['actions']
    if len(sources) != 30 or len({s['motion_id'] for s in sources}) != 30:
        raise ValueError('Require exactly 30 accepted unique representative actions')
    samples_path = prior.RUN/'all_motion_samples_v1.json'
    samples = read(samples_path)
    clips = {c['clip_id']: c for c in samples['clips']}
    config = {
        'schema': 'camera_face_closeup_config_v1',
        'scope': '30 accepted representative actions x2 independently composed orientations',
        'camera_id': 'front_head', 'fixed_world_camera_azimuth_degrees': 90.,
        'fixed_camera_elevation_degrees': 0., 'rotation_tracking': False,
        'automatic_in_shot_zoom': False, 'per_action_tracking_and_distance': True,
        'head_proxy_padding_cm': {'x': [-13., 13.], 'y': [-13., 13.], 'z': [-8., 22.]},
        'head_proxy_margin_fraction': .09,
        'orientations': {
            'landscape': {'width': 1280, 'height': 720, 'horizontal_fov_degrees': 35.,
                          'target_offset_from_head_cm': [0., 0., 4.], 'nominal_distance_cm': 155.,
                          'composition_intent': 'head and shoulder tops with modest breathing room'},
            'portrait': {'width': 720, 'height': 1280, 'horizontal_fov_degrees': 35.,
                         'target_offset_from_head_cm': [0., 0., -8.], 'nominal_distance_cm': 94.,
                         'composition_intent': 'head above center with shoulders and upper chest context'},
        },
        'accepted_nonface_plan': accepted_plan, 'nonface_plan_modified': False,
        'sampling_limit': '10Hz cached head translation, interpolated at final 30fps',
        'human_acceptance': 'pending',
    }
    RUN.mkdir(parents=True, exist_ok=True)
    shots, reports, actions = [], [], []
    for source in sources:
        clip = clips[source['source_clip_id']]
        frames = prior.resample(clip, source['source_start_seconds'], source['duration_seconds'], source['source_body_play_rate'])
        if len(frames) != source['frame_count']+1:
            raise ValueError('Source frame count changed')
        filtered, tracking = action_tracking(frames, source['motion_id'])
        per_orientation = {}
        for orientation, spec in config['orientations'].items():
            shot = make_shot(source, frames, filtered, tracking, orientation, spec, config)
            report = {'shot_id': shot['shot_id'], 'checks': checks(shot, source)}
            if not all(report['checks'].values()):
                raise ValueError('Targeted face check failed: ' + str(report))
            shots.append(shot)
            reports.append(report)
            per_orientation[orientation] = {'shot_id': shot['shot_id'], 'distance_cm': shot['endpoint_distances_cm'][0],
                                            'framing': shot['framing_diagnostics']['head']}
        actions.append({'motion_id': source['motion_id'], 'motion_label': source['motion_label'],
                        'sex': source['sex'], 'source_clock': {k: source[k] for k in CLOCK_FIELDS},
                        'tracking': tracking, 'orientations': per_orientation})
    pilots = [s['shot_id'] for m in PILOTS for s in shots if s['motion_id'] == m]
    if len(shots) != 60 or len(set(s['shot_id'] for s in shots)) != 60 or len(pilots) != 10:
        raise ValueError('Unexpected face matrix or pilot selection')
    # Verify the reused filter on straight translation; no broad test audit.
    t = np.arange(61)/30.
    linear = np.stack([17*t+3, -8*t+1, 2*t+150], axis=1)
    filter_error = float(np.max(np.abs(stable.low_frequency(linear, t, .28)-linear)))
    if filter_error > 1e-9:
        raise ValueError('Head smoothing does not preserve linear travel')
    if pin(ACCEPTED/'camera_trial_plan_v1.json') != accepted_plan:
        raise ValueError('Accepted non-face plan changed during offline build')
    save('camera_face_closeup_config_v1.json', config)
    plan = {'schema': 'camera_face_closeup_trial_v1', 'shots': shots,
            'matrix': {'actions': 30, 'presets': 1, 'orientations': 2, 'shots': 60},
            'source_pins': [accepted_plan, pin(manifest_path), pin(samples_path), pin(Path(__file__)),
                            pin(Path(stable.__file__)), pin(Path(prior.__file__)), pin(Path(sequence.__file__))],
            'source_samples_sha256': pin(samples_path)['sha256'],
            'decisions_path': manifest['window_decisions']['path'],
            'reference_config': pin(RUN/'camera_face_closeup_config_v1.json'),
            'pilot_shot_ids': pilots, 'smoke_shot_ids': pilots,
            'human_acceptance': 'pending', 'complete_window': True,
            'face_closeups_only': True, 'face_visibility_guaranteed': False,
            'cropping_allowed': True, 'nonface_plan_modified': False}
    save('camera_trial_plan_v1.json', plan)
    plan_pin = pin(RUN/'camera_trial_plan_v1.json')
    save('face_closeup_action_parameters_v1.json', {'schema': 'face_closeup_action_parameters_v1', 'plan': plan_pin,
                                                 'actions': actions, 'pilot_shot_ids': pilots})
    save('face_closeup_targeted_checks_v1.json', {'schema': 'face_closeup_targeted_checks_v1',
        'success': True, 'plan': plan_pin, 'reports': reports,
        'accepted_nonface_plan_sha_unchanged': True, 'matrix_exact': True,
        'linear_translation_filter_max_error_cm': filter_error,
        'scope': 'source clocks, 60-key schemas, finite translation, fixed camera vector, head proxy margins, depth/floor only',
        'not_full_audit': True, 'human_acceptance': 'pending'})
    save('face_closeup_freeze_v1.json', {'schema': 'face_closeup_freeze_v1', 'plan': plan_pin,
        'config': pin(RUN/'camera_face_closeup_config_v1.json'),
        'action_parameters': pin(RUN/'face_closeup_action_parameters_v1.json'),
        'targeted_checks': pin(RUN/'face_closeup_targeted_checks_v1.json'),
        'pilot_shot_ids': pilots, 'matrix': plan['matrix'],
        'ue_operations': False, 'rendered': False, 'human_acceptance': 'pending'})
    print(json.dumps({'success': True, 'plan': plan_pin, 'matrix': plan['matrix'],
                      'pilot_shot_ids': pilots}, ensure_ascii=False))


if __name__ == '__main__':
    build()
