"""Explicit common-scale diagnostic cameras; SCENE_CAMERA_SEQUENCE.

No automatic action-dependent distance fitting or UE mutation. Callers supply a
reviewed reference configuration. Full-window diagnostics remain separate from
human acceptance; closeup excursions cannot silently promote a production shot.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import numpy as np
import motion_portrait_camera_planner_v1 as prior


def reference_for(config, orientation, preset, framing):
    reference = copy.deepcopy(config['orientations'][orientation][framing])
    reference.update(config.get('preset_overrides', {}).get(orientation, {}).get(preset['id'], {}).get(framing, {}))
    for key in ('distance_cm', 'initial_target_height_cm'):
        value = float(reference[key])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'Invalid explicit {key}: {value}')
        reference[key] = value
    return reference


def aligned_centers(frames, references, existing=None):
    """Same initial pelvis-relative XY and configured Z; preserve follow deltas."""
    centers = copy.deepcopy(existing) if existing is not None else prior.stable.centers_for(frames)
    pelvis = np.asarray(frames[0]['bones']['pelvis'], float)
    for framing, reference in references.items():
        centers[framing] = centers[framing].copy()
        centers[framing][:, :2] += pelvis[:2] - centers[framing][0, :2]
        centers[framing][:, 2] += reference['initial_target_height_cm'] - centers[framing][0, 2]
    return centers


def projections(frames, rows, framing, aspect, horizontal_fov):
    points = np.array([prior.stable.old.semantic_points(f['bones'], framing) for f in frames])
    pos = np.array([r['position'] for r in rows]); target = np.array([r['look_at'] for r in rows])
    forward = target-pos; forward /= np.linalg.norm(forward, axis=1)[:, None]
    right = np.cross(np.array([0., 0., 1.]), forward); right /= np.linalg.norm(right, axis=1)[:, None]
    up = np.cross(forward, right); delta = points-pos[:, None, :]
    depth = np.einsum('nkj,nj->nk', delta, forward)
    tangent = math.tan(math.radians(horizontal_fov/2))
    uv = np.stack([.5+np.einsum('nkj,nj->nk', delta, right)/(2*depth*tangent),
                   .5-np.einsum('nkj,nj->nk', delta, up)*aspect/(2*depth*tangent)], axis=-1)
    return uv, depth


def diagnostics(frames, rows, framing, aspect, fov, active):
    uv, depth = projections(frames, rows, framing, aspect, fov)
    if not np.isfinite(uv[active]).all() or depth[active].min() <= 1:
        raise ValueError('Nonfinite projection or semantic points behind camera')
    outside = np.any((uv < 0) | (uv > 1), axis=(1, 2))
    margin = np.any((uv < .035) | (uv > .965), axis=(1, 2))
    heights = np.ptp(uv[:, :, 1], axis=1); widths = np.ptp(uv[:, :, 0], axis=1)
    return {'active_frame_count': int(active.sum()),
            'outside_frame_count': int((outside & active).sum()),
            'outside_times_seconds': [float(f['t']) for f, yes in zip(frames, outside & active) if yes],
            'margin_excursion_frame_count': int((margin & active).sum()),
            'first_proxy_height_fraction': float(heights[0]),
            'active_proxy_height_range': [float(heights[active].min()), float(heights[active].max())],
            'active_proxy_width_range': [float(widths[active].min()), float(widths[active].max())],
            'min_depth_cm': float(depth[active].min()),
            'inactive_min_depth_cm': float(depth[~active].min()) if np.any(~active) else None,
            'scope': 'skeletal proxies with margins, not visible mesh silhouette'}


def make_shot(clip, decision, sex, preset, orientation, config, *, group='calibration', limit=None, prepared=None):
    """Build one explicit-scale candidate over the FULL selected window by default."""
    if orientation not in ('landscape', 'portrait'):
        raise ValueError('Unknown orientation')
    start = float(decision['window_start_seconds']); rate = float(decision['body_play_rate'])
    duration = float(decision['output_duration_seconds'])
    if limit is not None:
        if float(limit) <= 0: raise ValueError('Invalid explicit duration limit')
        duration = min(duration, float(limit))
    if start < 0 or rate <= 0 or duration < 1/30:
        raise ValueError('Invalid animation clock')
    if start + duration*rate > float(clip['frames'][-1]['t']) + 1/30 + 1e-6:
        raise ValueError('Selected source window exceeds sampled animation')
    fov = float(config['horizontal_fov_degrees'])
    if not math.isfinite(fov) or not 1 < fov < 175: raise ValueError('Invalid FOV')
    references = {f: reference_for(config, orientation, preset, f) for f in (preset['start'], preset['end'])}
    if prepared is None:
        frames = prior.resample(clip, start, duration, rate)
        raw_centers = None
    else:
        frames = prepared['frames']; raw_centers = prepared['centers']
        expected_duration = math.floor(duration*30+1e-6)/30
        if abs(frames[-1]['t']-expected_duration)>1e-6 or prepared['source_start_seconds']!=start or prepared['source_body_play_rate']!=rate:
            raise ValueError('Prepared motion clock mismatch')
    centers = aligned_centers(frames, references, raw_centers)
    try:
        facing = prior.stable.old.initial_foot_forward_evidence(frames[0])
    except ValueError:
        lateral = np.array(frames[0]['bones']['thigh_r'])-np.array(frames[0]['bones']['thigh_l'])
        if np.linalg.norm(lateral[:2]) < 1e-6: raise ValueError('Initial facing landmarks degenerate')
        facing = {'method': 'initial_thigh_lateral_axis', 'yaw_degrees': math.degrees(math.atan2(-lateral[0], lateral[1])), 'requires_visual_check': True}
    distances = [references[f]['distance_cm'] for f in (preset['start'], preset['end'])]
    rows = prior.path(frames, preset, distances, facing['yaw_degrees'], centers)
    for row in rows: row['horizontal_fov_degrees'] = fov
    width, height = (720, 1280) if orientation == 'portrait' else (1280, 720)
    times = np.array([f['t'] for f in frames]); finish = min(7., frames[-1]['t']*.7)
    closeup_depth_exception = None
    safety_depth = config.get('closeup_minimum_depth_cm')
    if safety_depth is not None:
        safety_depth = float(safety_depth)
        if not math.isfinite(safety_depth) or safety_depth <= 1: raise ValueError('Invalid closeup depth margin')
        for framing in references:
            if framing == 'full': continue
            _, depths = projections(frames, rows, framing, width/height, fov)
            # Upper semantic points remain relevant through a dolly transition too.
            minimum = float(depths.min())
            if minimum >= safety_depth: continue
            original_distances = list(distances)
            # First try the exact depth deficit. Dolly interpolation can reduce
            # the effective endpoint change; binary search the smallest safe lift.
            lo, hi = 0., max(1., safety_depth-minimum+.01)
            def depth_at(addition):
                ds = [d+addition if f==framing else d for d,f in zip(original_distances,(preset['start'],preset['end']))]
                rr = prior.path(frames,preset,ds,facing['yaw_degrees'],centers)
                return float(projections(frames,rr,framing,width/height,fov)[1].min()), ds, rr
            while depth_at(hi)[0] < safety_depth:
                hi *= 2
                if hi > 2500: raise ValueError('No bounded safe closeup trajectory')
            for _ in range(18):
                mid=(lo+hi)/2
                if depth_at(mid)[0] < safety_depth:lo=mid
                else:hi=mid
            final_min, distances, rows = depth_at(hi+.01)
            for row in rows: row['horizontal_fov_degrees']=fov
            closeup_depth_exception={'reason':'active closeup proxy approaches or crosses camera near plane',
                                     'framing':framing,'minimum_allowed_depth_cm':safety_depth,
                                     'baseline_min_depth_cm':minimum,'adjusted_min_depth_cm':final_min,
                                     'baseline_endpoint_distances_cm':original_distances,
                                     'adjusted_endpoint_distances_cm':list(distances),
                                     'scale_exception_requires_human_review':True,
                                     'policy':'minimum geometric depth correction only, never full-window screen-fit zoom-out'}
    diag = {}
    for framing in references:
        active = np.ones(len(frames), dtype=bool)
        if preset['kind'].startswith('dolly'):
            active = times <= 1e-6 if framing == preset['start'] else times >= finish-1e-6
        diag[framing] = diagnostics(frames, rows, framing, width/height, fov, active)
    full_outside = any(f == 'full' and d['outside_frame_count'] for f, d in diag.items())
    exception = None
    if full_outside and config.get('full_body_exception_policy') == 'explicit_safety_expansion':
        if fov != 35.: raise ValueError('Safety fitter currently requires 35 degree HFOV')
        baseline_diag = copy.deepcopy(diag)
        baseline_distances = list(distances)
        required = prior.fit(frames, preset, 'full', facing['yaw_degrees'], centers, width/height)
        for i, framing in enumerate((preset['start'],preset['end'])):
            if framing == 'full': distances[i] = max(distances[i], required)
        rows = prior.path(frames,preset,distances,facing['yaw_degrees'],centers)
        for row in rows: row['horizontal_fov_degrees'] = fov
        for framing in references:
            active = np.ones(len(frames),dtype=bool)
            if preset['kind'].startswith('dolly'):
                active = times <= 1e-6 if framing == preset['start'] else times >= finish-1e-6
            diag[framing] = diagnostics(frames,rows,framing,width/height,fov,active)
        full_outside = any(f=='full' and d['outside_frame_count'] for f,d in diag.items())
        exception = {'reason':'common full-body reference produces actual proxy outside image',
                     'baseline_endpoint_distances_cm':baseline_distances,'adjusted_endpoint_distances_cm':distances,
                     'baseline_framing_diagnostics':baseline_diag,'resolved_full_body_excursion':not full_outside,
                     'scale_exception_requires_human_review':True}
    short_id = f"{group}_{decision['motion_id'].lower()}_{sex}_{orientation[0]}_{preset['id']}"
    canonical = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    return {'shot_id': short_id, 'status': 'framing_exception' if full_outside else 'geometry_pass',
            'group': group, 'motion_id': decision['motion_id'], 'motion_label': decision['label'], 'sex': sex,
            'camera_id': preset['id'], 'camera_label': preset['label'], 'orientation': orientation,
            'width': width, 'height': height, 'aspect_ratio': width/height, 'fps': 30,
            'frame_count': len(rows)-1, 'duration_seconds': frames[-1]['t'],
            'source_start_seconds': start, 'source_body_play_rate': rate,
            'source_end_seconds': start+frames[-1]['t']*rate,
            'source_animation': clip['animation_path'], 'source_clip_id': clip['clip_id'],
            'window_start_seconds': start if rate == 1 else 0.,
            'initial_facing': facing, 'frames': rows[:-1], 'endpoint_validation_frame': rows[-1],
            'trajectory_sha256': hashlib.sha256(canonical).hexdigest(),
            'calibration_config_sha256': hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'endpoint_distances_cm': distances, 'calibration_references': references,
            'scale_exception': exception,
            'closeup_depth_exception': closeup_depth_exception,
            'framing_diagnostics': diag, 'human_acceptance': 'pending',
            'distance_policy': 'explicit common reference; no per-action automatic fit',
            'follow_policy': 'initial pelvis XY + existing low-frequency delta; no heading pursuit',
            'window_scope': 'complete_selected_window' if limit is None else 'explicit_limited_window',
            'exceptions_require_review': full_outside,
            'limitations': ['No pixel silhouette certification', 'Closeup excursions are diagnostic, not automatic rejection',
                            'Existing low-angle 25 cm floor clamp may change achieved elevation']}
