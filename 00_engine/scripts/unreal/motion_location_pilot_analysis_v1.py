"""Read-only full-library pose sampling and offline movement-window suggestions.

Owner: SCENE_CAMERA_SEQUENCE.md, motion/portrait/location pilot 2026-10-11.
No existing asset, accepted camera plan, or animation key is changed. The root
agent alone calls sample_in_ue(); importing this module never imports Unreal.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path('D:/UE/Lance_Work')
RUN = ROOT / '00_engine/outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1'
CATALOG = ROOT / '00_engine/outputs/unreal_character_import/motion_library_expansion_20261009_v1/final_motion_catalog_v1.json'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
BONES = ('root', 'pelvis', 'spine_01', 'spine_02', 'neck_01', 'head',
         'upperarm_l', 'upperarm_r', 'hand_l', 'hand_r', 'thigh_l', 'thigh_r',
         'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r')
POLICY = {'small_area_radius_cm': 125., 'straight_cross_span_cm': 60.,
          'straight_cross_to_along_ratio': .20, 'minimum_suggested_clip_seconds': 2.,
          'search_step_seconds': .1,
          'meaning': 'Screening suggestions for human review, not user-approved thresholds. Radius is relative to the sampled XY bounding-box centre. No root trajectory straightening. Along-line reversals are reported, not automatically excluded.'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def source_rows():
    catalog = read(CATALOG)
    rows = []
    for row in catalog['actions']:
        for sex, variant in row['variants'].items():
            rows.append({'motion_id': row['motion_id'], 'sex': sex, 'label': row['label'],
                         'action_index': row['index'], 'asset': variant['body_only']['asset'],
                         'source_package': variant['body_only'], 'duration_seconds': variant['duration_seconds'],
                         'scope': 'twenty_added_same_motion_pairs'})
    # The five old menu indices pair DIFFERENT male/female performances. Do not
    # invent semantic pairs or force a common crop across those ten originals.
    for aid, record in catalog['base_catalog_sources']['action_packages'].items():
        package = '/Game/' + Path(record['path']).relative_to(CONTENT).with_suffix('').as_posix()
        rows.append({'motion_id': aid, 'sex': 'female' if aid.startswith('ACT_F') else 'male',
                     'label': aid, 'action_index': None, 'asset': package,
                     'source_package': record, 'duration_seconds': None,
                     'scope': 'legacy_five_menu_pairs_ten_distinct_sources'})
    assert len(rows) == 50 and len({r['asset'] for r in rows}) == 50
    return rows


def sample_in_ue(output=None):
    """Root-only UE call; 10 Hz across the entire duration plus exact endpoint."""
    import unreal as u
    output = Path(output or RUN / 'all_motion_samples_v1.json')
    if output.exists():
        raise FileExistsError(output)
    assert Path(u.Paths.project_dir()).resolve() == CONTENT.parent.resolve()
    rows = source_rows()
    before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    catalog_pin = pin(CATALOG)
    for row in rows:
        if pin(row['source_package']['path'])['sha256'] != row['source_package']['sha256']:
            raise ValueError('Changed source: ' + row['motion_id'])
        if row['asset'].split('.')[0] in before:
            raise ValueError('Dirty motion source: ' + row['asset'])
    report = {'schema': 'motion_location_full_samples_v1', 'fps': 10, 'source': catalog_pin,
              'coordinates': 'AnimPoseSpaces.WORLD, model-space cm; actor identity transform',
              'geometry_scope': 'Bone landmarks only, not mesh silhouettes or semantic naturalness', 'clips': []}
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
        'extract_root_motion': False, 'incorporate_root_motion_into_pose': True, 'evaluate_curves': False})
    for row in rows:
        anim = u.load_asset(row['asset'])
        assert isinstance(anim, u.AnimSequence), row['asset']
        rate = anim.data_model_interface.get_frame_rate()
        raw_count = anim.data_model_interface.get_number_of_frames()
        count = int(getattr(raw_count, 'value', raw_count))
        duration = count * rate.denominator / rate.numerator
        assert abs(duration - float(anim.get_play_length())) < 1e-5
        if row['duration_seconds'] is not None:
            assert abs(duration - row['duration_seconds']) < 1e-5
        times = [i / 10 for i in range(math.floor(duration * 10) + 1)]
        if abs(times[-1] - duration) > 1e-8:
            times.append(duration)
        clip = dict(row, clip_id=row['motion_id'].lower() + '_' + row['sex'],
                    animation_path=anim.get_path_name(), duration_seconds=duration,
                    source_frame_rate={'numerator': int(rate.numerator), 'denominator': int(rate.denominator)},
                    source_frame_count=count, source_skeleton=anim.get_skeleton().get_path_name(),
                    window_start_seconds=0., window_duration_seconds=duration, frames=[])
        for t in times:
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(anim, t, options)
            assert u.AnimPoseExtensions.is_valid(pose)
            names = {str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)}
            assert set(BONES) <= names, sorted(set(BONES) - names)
            bones = {}
            for name in BONES:
                transform = u.AnimPoseExtensions.get_bone_pose(pose, u.Name(name), u.AnimPoseSpaces.WORLD)
                v = transform.translation
                bones[name] = [float(v.x), float(v.y), float(v.z)]
                assert all(math.isfinite(value) for value in bones[name])
                if name == 'root':
                    r = transform.rotation.rotator()
                    rotation = [float(r.pitch), float(r.yaw), float(r.roll)]
            clip['frames'].append({'t': t, 'bones': bones, 'root_rotation': rotation})
        report['clips'].append(clip)
        print('DM_MOTION_SAMPLE_PROGRESS=' + json.dumps({'done': len(report['clips']), 'total': len(rows), 'clip_id': clip['clip_id']}))
    assert before == {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert catalog_pin == pin(CATALOG)
    assert all(pin(row['source_package']['path'])['sha256'] == row['source_package']['sha256'] for row in rows)
    report.update(success=True, source_assets_unchanged=True, dirty_packages_unchanged=True)
    write_new(output, report)
    return {'success': True, 'clips': len(rows), 'report': str(output)}


def metrics(points, policy=POLICY):
    import numpy as np
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[0] < 2 or p.shape[1] != 2 or not np.isfinite(p).all():
        raise ValueError('Require finite two-dimensional motion samples')
    centre = (p.min(axis=0) + p.max(axis=0)) / 2
    radius = float(np.linalg.norm(p - centre, axis=1).max())
    q = p - p.mean(axis=0)
    _, vectors = np.linalg.eigh(q.T @ q)
    axis = vectors[:, -1]
    if axis @ (p[-1] - p[0]) < 0:
        axis = -axis
    along = q @ axis
    cross = q @ np.array([-axis[1], axis[0]])
    along_span, cross_span = float(np.ptp(along)), float(np.ptp(cross))
    local = radius <= policy['small_area_radius_cm']
    straight = cross_span <= policy['straight_cross_span_cm'] and cross_span <= max(1., along_span) * policy['straight_cross_to_along_ratio']
    backward = float(np.maximum.accumulate(along).max() - along[-1])
    # Maximum reverse excursion catches intermediate return trips too.
    backward = float(np.max(np.maximum.accumulate(along) - along))
    return {'accepted_geometry': bool(local or straight),
            'classification': 'small_area' if local else ('straight_travel' if straight else 'multi_direction'),
            'xy_extent_cm': np.ptp(p, axis=0).tolist(), 'small_area_radius_cm': radius,
            'principal_axis_xy': axis.tolist(), 'along_span_cm': along_span,
            'cross_span_cm': cross_span, 'net_displacement_cm': float(np.linalg.norm(p[-1] - p[0])),
            'maximum_reverse_excursion_cm': backward,
            'bounds_xy_cm': {'min': p.min(axis=0).tolist(), 'max': p.max(axis=0).tolist()}}


def window_metrics(clip, start, end):
    import numpy as np
    frames = clip['frames']
    times = np.asarray([f['t'] for f in frames])
    selected = sorted(set([float(start), float(end)] + [float(t) for t in times if start < t < end]))
    result = {}
    for bone in ('root', 'pelvis'):
        points = np.asarray([f['bones'][bone][:2] for f in frames])
        rows = np.column_stack([np.interp(selected, times, points[:, axis]) for axis in (0, 1)])
        result[bone] = metrics(rows)
    result['accepted_geometry'] = all(result[b]['accepted_geometry'] for b in ('root', 'pelvis'))
    return result


def analyze(samples_path, output=None):
    samples_path = Path(samples_path)
    samples = read(samples_path)
    assert samples.get('success') is True and samples.get('source_assets_unchanged') is True
    groups = {}
    for clip in samples['clips']:
        groups.setdefault(clip['motion_id'], []).append(clip)
    results = []
    for motion_id, clips in groups.items():
        duration = min(c['duration_seconds'] for c in clips)
        full = {c['sex']: window_metrics(c, 0, c['duration_seconds']) for c in clips}
        start, end, mode = 0., duration, 'keep_full'
        if motion_id == 'MOTION_CAND_008':
            end, mode = 6., 'user_requested_first_six_seconds_to_ten'
        elif not all(v['accepted_geometry'] for v in full.values()):
            # Longest duration first, then earliest start: maximise retained
            # continuous source footage; never concatenate or straighten keys.
            ticks = math.floor(duration * 10 + 1e-7)
            found = None
            for length in range(ticks, round(POLICY['minimum_suggested_clip_seconds'] * 10) - 1, -1):
                for first in range(ticks - length + 1):
                    a, b = first / 10, (first + length) / 10
                    if all(window_metrics(c, a, b)['accepted_geometry'] for c in clips):
                        found = (a, b)
                        break
                if found:
                    break
            if found:
                start, end, mode = *found, 'suggest_contiguous_crop'
            else:
                start, end, mode = None, None, 'suggest_exclusion_no_viable_window'
        selected = {c['sex']: window_metrics(c, start, end) for c in clips} if start is not None else None
        output_duration = (10. if motion_id == 'MOTION_CAND_008' else end - start) if selected else None
        variants = {c['sex']: {'clip_id': c['clip_id'], 'asset': c['animation_path'],
                    'source_package': c['source_package'], 'source_duration_seconds': c['duration_seconds'],
                    'source_skeleton': c.get('source_skeleton')} for c in clips}
        results.append({'motion_id': motion_id, 'label': clips[0]['label'], 'scope': clips[0]['scope'],
                        'mode': mode, 'window_start_seconds': start, 'window_end_seconds': end,
                        'output_duration_seconds': output_duration,
                        'body_play_rate': ((end - start) / output_duration) if selected else None,
                        'face_play_rate': 1., 'body_looped': False, 'trajectory_modified': False,
                        'human_acceptance': 'pending', 'full_source_metrics': full,
                        'selected_window_metrics': selected, 'variants': variants})
    result = {'schema': 'motion_location_window_suggestions_v1', 'samples': pin(samples_path),
              'source_catalog': samples['source'], 'policy': POLICY, 'actions': results,
              'counts': {mode: sum(r['mode'] == mode for r in results) for mode in sorted({r['mode'] for r in results})},
              'limitations': ['10Hz root/pelvis movement screening, not all-frame silhouette/foot-contact/naturalness proof.',
                  'Small-area and straightness thresholds are explicit conservative working suggestions for visual review.',
                  'Other than the requested walk slowdown, originals retain their selected source time and speed.',
                  'The ten legacy sex-specific clips are individual performances, not five same-motion male/female pairs.'],
              'success': True}
    write_new(output or RUN / 'motion_window_suggestions_v1.json', result)
    return result


def single_pass_revision(samples_path, previous_path, output=None):
    """Explicit second-stage review decision; never replaces the first receipt.

    Root requested a single-pass model walk after discovering its 3.1m return.
    The seven-second boundary preserves the approach and standing pose before
    the subsequent turnaround. Other small-area movement remains visible.
    """
    samples = read(samples_path)
    result = copy.deepcopy(read(previous_path))
    clips = {c['clip_id']: c for c in samples['clips']}
    row = next(r for r in result['actions'] if r['motion_id'] == 'MOTION_CAND_036')
    original = copy.deepcopy(row)
    row.update(mode='suggest_single_pass_crop', window_start_seconds=0., window_end_seconds=7.,
               output_duration_seconds=7., body_play_rate=1., human_acceptance='pending')
    row['selected_window_metrics'] = {s: window_metrics(clips[v['clip_id']], 0, 7) for s, v in row['variants'].items()}
    row['decision_note'] = 'Keep first straight approach and brief posing; stop before the later 3.1m retrace. Seven-second boundary is a source-pose-based review candidate, not a claimed visually seamless crop.'
    result['previous_decisions'] = pin(previous_path)
    result['decision_overrides'] = [{'motion_id': row['motion_id'],
        'reason': 'Prefer single-pass forward travel over 3.1m straight-line retrace after root review instruction.',
        'prior_full_clip_candidate': original}]
    result['counts'] = {mode: sum(r['mode'] == mode for r in result['actions']) for mode in sorted({r['mode'] for r in result['actions']})}
    result['remaining_reverse_over_60cm'] = []
    for action in result['actions']:
        for sex, value in (action['selected_window_metrics'] or {}).items():
            metric = value['root']
            if metric['maximum_reverse_excursion_cm'] > 60:
                result['remaining_reverse_over_60cm'].append({'motion_id': action['motion_id'], 'label': action['label'],
                    'sex': sex, 'classification': metric['classification'], 'along_span_cm': metric['along_span_cm'],
                    'small_area_radius_cm': metric['small_area_radius_cm'],
                    'maximum_reverse_excursion_cm': metric['maximum_reverse_excursion_cm'],
                    'disposition': 'retained small-area movement pending continuous visual review; PCA reversal alone does not mean a locomotion turn'})
    write_new(output or RUN / 'motion_window_decisions_v2.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=Path, default=RUN / 'all_motion_samples_v1.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--single-pass-revision', type=Path, help='Prior decision file to revise without replacing it')
    args = parser.parse_args()
    result = single_pass_revision(args.samples, args.single_pass_revision, args.output) if args.single_pass_revision else analyze(args.samples, args.output)
    print(json.dumps({'success': result['success'], 'counts': result['counts']}, ensure_ascii=False))
