"""Accepted nonface landscape distance standard; stdlib only, safe inside UE.

Load and verify configuration once per library load. Apply to the original-distance
shot after any follow overlay; this helper never modifies its input or a file.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / 'outputs/camera_follow_general_compact_20261015_v2/horizontal_camera_standard_v2.json'
SCHEMA = 'camera_horizontal_standard_v2'
MARKER = 'camera_standard_v2'
SUPERSEDED = ('path_metrics', 'endpoint_distances_cm', 'distance_cm', 'distance_policy',
              'calibration_references', 'common_preset_parameters', 'framing_diagnostics',
              'quality', 'scale_exception', 'closeup_depth_exception', 'calibration_config_sha256',
              'geometry_pass_scope', 'dolly_clock')


def canonical_sha(value):
    """Same compact sorted-key JSON convention as the frozen camera trajectories."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def _validate_config(config):
    if (config.get('schema') != SCHEMA
            or config.get('standard_id') != 'nonface_landscape_distance075_fov_compensated_v2'
            or config.get('landscape_distance_factor') != .75
            or config.get('scope') != 'nonface_landscape'
            or config.get('excluded_camera_ids') != ['front_head']
            or config.get('compensate_horizontal_fov') is not True):
        raise ValueError('Unsupported horizontal camera standard configuration')


def load_config(path=DEFAULT_CONFIG, *, verify_sources=True):
    """Read configuration and verify source pins once, outside per-shot loops."""
    config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    _validate_config(config)
    pins = config.get('source_pins', [])
    if len(pins) != 2 or {p.get('role') for p in pins} != {'original_nonface_plan', 'user_acceptance'}:
        raise ValueError('Require original nonface and explicit user-acceptance source pins')
    if verify_sources:
        for pin in pins:
            if hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest() != pin['sha256']:
                raise ValueError('Camera standard source changed: ' + pin['path'])
        acceptance_pin = next(p for p in pins if p['role'] == 'user_acceptance')
        accepted = json.loads(Path(acceptance_pin['path']).read_text(encoding='utf-8-sig'))['horizontal']
        if (accepted.get('accepted_distance_factor_from_original') != .75
                or accepted.get('compensate_fov') is not True):
            raise ValueError('User acceptance differs from configured standard')
    return config


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _norm(vector):
    return math.sqrt(sum(v * v for v in vector))


def _path_metrics(rows):
    speeds, turns = [], []
    for a, b in zip(rows, rows[1:]):
        dt = b['t'] - a['t']
        if dt <= 0:
            raise ValueError('Camera standard requires strictly increasing camera key times')
        speeds.append(_norm(_sub(b['position'], a['position'])) / dt)
        av, bv = _sub(a['look_at'], a['position']), _sub(b['look_at'], b['position'])
        cosine = sum(x * y for x, y in zip(av, bv)) / (_norm(av) * _norm(bv))
        turns.append(math.degrees(math.acos(max(-1., min(1., cosine)))) / dt)
    return {'max_camera_speed_cm_per_second': max(speeds, default=0.),
            'max_view_angular_speed_degrees_per_second': max(turns, default=0.),
            'min_camera_z_cm': min(r['position'][2] for r in rows),
            'speed_values_are_diagnostics_not_visual_acceptance': True}


def apply_standard(shot, config):
    """Return a copy with one accepted distance/FOV transform, preserving identity/clock.

    Portrait and front_head objects remain exactly equal. A repeated application of
    the same configuration returns the same derived object after verifying its
    complete trajectory; altered markers, trajectories or configurations fail.
    """
    _validate_config(config)
    result = copy.deepcopy(shot)
    if shot.get('orientation') != 'landscape' or shot.get('camera_id') in config['excluded_camera_ids']:
        if MARKER in shot:
            raise ValueError('Horizontal standard marker on an excluded shot')
        return result
    digest = canonical_sha(config)
    rows = result['frames'] + [result['endpoint_validation_frame']]
    if MARKER in shot:
        marker = shot[MARKER]
        if (marker.get('config_sha256') != digest or marker.get('distance_factor') != .75
                or marker.get('derived_trajectory_sha256') != canonical_sha(rows)
                or result.get('trajectory_sha256') != marker['derived_trajectory_sha256']):
            raise ValueError('Existing horizontal standard marker or trajectory differs')
        return result
    if 'compact_comparison' in shot:
        raise ValueError('Apply standard to original-distance source, not a compact comparison')
    if not result['frames'] or len(result['frames']) != result['frame_count']:
        raise ValueError('Camera standard requires every frame and endpoint')
    source_rows_sha = canonical_sha(rows)
    for row in rows:
        if any(len(row[key]) != 3 or not all(math.isfinite(v) for v in row[key])
               for key in ('position', 'look_at', 'rotation_pitch_yaw_roll')):
            raise ValueError('Invalid camera key geometry')
        fov = row['horizontal_fov_degrees']
        if not math.isfinite(fov) or not 0 < fov < 180 or _norm(_sub(row['position'], row['look_at'])) <= 0:
            raise ValueError('Invalid camera distance or horizontal FOV')
        row['position'] = [a + .75 * (c - a) for c, a in zip(row['position'], row['look_at'])]
        row['horizontal_fov_degrees'] = math.degrees(2 * math.atan(math.tan(math.radians(fov / 2)) / .75))
    superseded = {key: result.pop(key) for key in SUPERSEDED if key in result}
    trajectory_sha = canonical_sha(rows)
    result.update(frames=rows[:-1], endpoint_validation_frame=rows[-1],
                  trajectory_sha256=trajectory_sha, path_metrics=_path_metrics(rows),
                  endpoint_distances_cm=[_norm(_sub(r['position'], r['look_at'])) for r in (rows[0], rows[-1])],
                  distance_policy='accepted original-relative k=.75; aim and rotation fixed; compensated horizontal FOV; apply exactly once',
                  geometry_pass_scope='finite complete keys and aim-plane distance/FOV compensation; no derived mesh silhouette, collision, occlusion or visual certification')
    if 'distance_cm' in superseded:
        result['distance_cm'] = result['endpoint_distances_cm'][0]
    result[MARKER] = {'schema': 'camera_standard_application_v2', 'standard_id': config['standard_id'],
                      'config_sha256': digest, 'distance_factor': .75,
                      'source_trajectory_sha256': shot.get('trajectory_sha256'),
                      'source_rows_sha256': source_rows_sha,
                      'derived_trajectory_sha256': trajectory_sha,
                      'superseded_source_diagnostics': superseded,
                      'diagnostic_scope': 'source diagnostics are historical only; camera path metrics recalculated; visibility and framing require separate review'}
    return result
