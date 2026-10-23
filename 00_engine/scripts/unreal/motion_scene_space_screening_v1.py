"""Offline sparse space screening, not scene acceptance. SCENE_CAMERA_SEQUENCE §11.

Uses the approved camera equations and full 30fps stable-center filtering, but
fits framing and checks extrema only every 0.5 seconds plus the exact endpoint.
This compact preflight cannot certify collision, occlusion or between-sample
extrema. It never writes the render camera plan or connects to Unreal.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import motion_portrait_camera_planner_v1 as planner

RUN = planner.RUN


def pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def bounds(points):
    points = np.asarray(points)
    return {'minimum_xyz_cm': points.min(axis=0).tolist(),
            'maximum_xyz_cm': points.max(axis=0).tolist(),
            'maximum_horizontal_radius_cm': float(np.linalg.norm(points[:, :2], axis=1).max())}


def run():
    sample_path = RUN / 'all_motion_samples_v1.json'
    decision_path = RUN / 'motion_window_decisions_v2.json'
    samples = json.loads(sample_path.read_text(encoding='utf-8'))
    decisions = json.loads(decision_path.read_text(encoding='utf-8'))
    clips = {c['clip_id']: c for c in samples['clips']}
    presets = planner.library.presets()
    paths, envelopes = [], {o: [] for o in ('landscape', 'portrait')}
    for decision in decisions['actions']:
        if decision['window_start_seconds'] is None:
            continue
        sex = 'female' if 'female' in decision['variants'] else 'male'
        if decision['motion_id'] in ('MOTION_CAND_029', 'MOTION_CAND_035'):
            sex = 'male'
        clip = clips[decision['variants'][sex]['clip_id']]
        full = planner.resample(clip, decision['window_start_seconds'],
                                decision['output_duration_seconds'], decision['body_play_rate'])
        original_root = np.asarray(full[0]['bones']['root'])
        # Ground stays z=0; only initial root XY is reanchored, not character yaw.
        origin = np.array([original_root[0], original_root[1], 0.])
        for row in full:
            row['bones'] = {k: (np.asarray(v)-origin).tolist() for k,v in row['bones'].items()}
        full_centers = planner.stable.centers_for(full)
        ids = sorted(set(range(0, len(full), 15)) | {len(full)-1})
        frames = [full[i] for i in ids]
        centers = {key: value[ids] for key,value in full_centers.items()}
        try:
            facing = planner.stable.old.initial_foot_forward_evidence(frames[0])
        except ValueError:
            lateral = np.asarray(frames[0]['bones']['thigh_r'])-np.asarray(frames[0]['bones']['thigh_l'])
            facing = {'method': 'initial_thigh_lateral_axis', 'yaw_degrees': math.degrees(math.atan2(-lateral[0], lateral[1]))}
        for orientation, aspect in [('landscape', 1280/720), ('portrait', 720/1280)]:
            for preset in presets:
                distances = [planner.fit(frames, preset, framing, facing['yaw_degrees'], centers, aspect)
                             for framing in (preset['start'], preset['end'])]
                rows = planner.path(frames, preset, distances, facing['yaw_degrees'], centers)
                points = [row['position'] for row in rows]
                envelopes[orientation].extend(points)
                paths.append({'motion_id': decision['motion_id'], 'label': decision['label'], 'sex': sex,
                              'camera_id': preset['id'], 'orientation': orientation,
                              'duration_seconds': frames[-1]['t'], 'source_start_seconds': decision['window_start_seconds'],
                              'source_body_play_rate': decision['body_play_rate'], 'original_root_xy_cm': origin[:2].tolist(),
                              'initial_facing': facing, 'camera_bounds': bounds(points),
                              'samples': [{'t': row['t'], 'camera_cm': [round(x,4) for x in row['position']],
                                           'look_at_cm': [round(x,4) for x in row['look_at']],
                                           'body_root_cm': [round(x,4) for x in frame['bones']['root']],
                                           'body_pelvis_cm': [round(x,4) for x in frame['bones']['pelvis']]}
                                          for row,frame in zip(rows,frames)]})
        print(decision['motion_id'], 'complete', flush=True)
    output = RUN / 'scene_camera_space_screening_v1.json'
    report = {'schema': 'scene_camera_space_screening_v1', 'status': 'sparse_screening_only',
              'inputs': [pin(sample_path), pin(decision_path)],
              'code': [pin(__file__), pin(planner.__file__), pin(planner.stable.__file__), pin(planner.library.__file__)],
              'coordinate_system': 'centimeters; source initial root XY translated to zero, original facing retained, ground Z unchanged',
              'sampling_seconds': .5, 'stable_center_sampling_fps': 30, 'framing_fit_sampling_seconds': .5,
              'camera_presets': len(presets), 'actions': len(paths)//(2*len(presets)), 'path_count': len(paths),
              'scope': 'Same 30 primary variants as overview. Native selected duration except walk first6-to10. Sparse camera fit and envelope, not final per-frame camera trajectories.',
              'limitations': ['May miss body and camera extrema between 0.5s samples.',
                             'Sparse framing fit can underestimate exact render camera distance.',
                             'No meshes, clothing, lens near-plane sweep, obstacle collision or visibility tested.',
                             'Use an extra 100cm layout margin as screening allowance; this is not a proved bound.',
                             'Other-sex variants require separate final checks.'],
              'orientation_camera_bounds': {o: bounds(points) for o,points in envelopes.items()},
              'recommended_layout_margin_cm': 100., 'paths': paths}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    print(json.dumps({'output': str(output), 'path_count': len(paths), 'bounds': report['orientation_camera_bounds']}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    run()
