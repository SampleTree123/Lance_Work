"""Offline landscape distance/FOV comparison and receipt-backed standalone gallery.

Owner: SCENE_CAMERA_SEQUENCE. Does not connect to UE or modify approved inputs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

from camera_motion_planner_v1 import basis, dot, sub, add, mul, norm, path_metrics
from run_all_motion_camera_review_v1 import checked_media, copy_pinned, verified_rows
from encode_motion_scene_pilot_v1 import owned
from ue_motion_scene_sequence_v1 import key_rows

S = Path(__file__).resolve().parent
OUTPUTS = S.parents[1] / 'outputs'
SOURCE = OUTPUTS / 'camera_all_motions_portrait115_20261014_v1/camera_trial_plan_v1.json'
RUN = OUTPUTS / 'camera_follow_compact_scene_20261015_v1'
GENERAL_RUN = OUTPUTS / 'camera_follow_general_compact_20261015_v2'
SOURCE_SHA256 = '30ef018c59b17ac2daa2e58a2596eb8eb964fc3c26b35fda41c188e0eed05792'
PLAN_NAME = 'camera_compact_comparison_plan_v1.json'
SETUPS = (
    ('MOTION_CAND_003', 'front_full', '弯腰伸展 · 正面全身'),
    ('MOTION_CAND_003', 'front_upper', '弯腰伸展 · 正面上半身'),
    ('MOTION_CAND_008', 'orbit_120', '向前行走 · 120度环绕'),
    ('MOTION_CAND_034', 'dolly_in_side', '起跑 · 侧面推进'),
)
VARIANTS = ((1.0, '原距离'), (.85, '距离缩短15%'), (.75, '距离缩短25%'))
GENERAL_VARIANTS = ((1.0, '原距离'), (.9, '距离缩短10%'), (.8, '距离缩短20%'),
                    (.7, '距离缩短30%'), (.6, '距离缩短40%'), (.5, '距离缩短50%'),
                    (.75, '距离缩短25%'))
CLOCK_FIELDS = ('source_start_seconds', 'source_body_play_rate', 'source_end_seconds',
                'window_start_seconds', 'duration_seconds', 'frame_count', 'fps')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value, *, frozen=False):
    path = Path(path)
    if frozen and path.exists():
        if read(path) != value:
            raise ValueError('Existing frozen output differs: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.partial')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def transform_row(row, k):
    if not 0 < k <= 1:
        raise ValueError('Distance factor must be in (0,1]')
    result = copy.deepcopy(row)
    if k != 1:
        result['position'] = add(row['look_at'], mul(sub(row['position'], row['look_at']), k))
        result['horizontal_fov_degrees'] = math.degrees(2 * math.atan(
            math.tan(math.radians(row['horizontal_fov_degrees'] / 2)) / k))
    return result


def project(point, row, aspect):
    forward, right, up = basis(row['position'], row['look_at'])
    delta = sub(point, row['position'])
    depth = dot(delta, forward)
    if depth <= 0:
        raise ValueError('Geometric probe is behind camera')
    half = math.tan(math.radians(row['horizontal_fov_degrees'] / 2))
    return [.5 + dot(delta, right) / (2 * depth * half),
            .5 - dot(delta, up) * aspect / (2 * depth * half)]


def geometry(source, derived, k):
    old = source['frames'] + [source['endpoint_validation_frame']]
    new = derived['frames'] + [derived['endpoint_validation_frame']]
    plane_error = distance_error = fov_error = 0.
    deviations = []
    for a, b in zip(old, new):
        if (a['t'] != b['t'] or a['look_at'] != b['look_at']
                or a['rotation_pitch_yaw_roll'] != b['rotation_pitch_yaw_roll']):
            raise ValueError('Frozen clock, aim or rotation changed')
        da, db = norm(sub(a['position'], a['look_at'])), norm(sub(b['position'], b['look_at']))
        distance_error = max(distance_error, abs(db - k * da))
        ta = math.tan(math.radians(a['horizontal_fov_degrees'] / 2))
        tb = math.tan(math.radians(b['horizontal_fov_degrees'] / 2))
        fov_error = max(fov_error, abs(db * tb - da * ta))
        forward, right, up = basis(a['position'], a['look_at'])
        for x, y in ((-70, -70), (-70, 70), (0, 0), (70, -70), (70, 70)):
            point = add(a['look_at'], add(mul(right, x), mul(up, y)))
            plane_error = max(plane_error, *(abs(v - w) for v, w in zip(
                project(point, a, source['aspect_ratio']), project(point, b, source['aspect_ratio']))))
        for offset in (-50., 50.):
            # Depth offset is measured along the frozen view direction from aim plane.
            if min(da + offset, db + offset) <= 0:
                raise ValueError('Perspective probe is behind camera')
            deviations.append({'offset_cm': offset, 'relative_transverse_scale':
                               k * (da + offset) / (k * da + offset)})
    clocks = {f: source[f] for f in CLOCK_FIELDS}
    if clocks != {f: derived[f] for f in CLOCK_FIELDS} or len(new) != source['frame_count'] + 1:
        raise ValueError('Source animation clock changed')
    key_rows(derived)
    if max(plane_error, distance_error, fov_error) > 1e-8:
        raise ValueError('Distance/FOV compensation invariant failed')
    return {'shot_id': derived['shot_id'], 'source_shot_id': source['shot_id'],
            'distance_factor': k, 'clock': clocks, 'keys_including_endpoint': len(new),
            'max_aim_plane_uv_error': plane_error, 'max_distance_error_cm': distance_error,
            'max_distance_times_tan_half_fov_error_cm': fov_error,
            'initial_distance_cm': norm(sub(old[0]['position'], old[0]['look_at'])),
            'derived_initial_distance_cm': norm(sub(new[0]['position'], new[0]['look_at'])),
            'fov_degrees': [new[0]['horizontal_fov_degrees'], new[-1]['horizontal_fov_degrees']],
            'depth_offset_scale_ranges': {str(z): [min(v['relative_transverse_scale'] for v in deviations if v['offset_cm'] == z),
                    max(v['relative_transverse_scale'] for v in deviations if v['offset_cm'] == z)] for z in (-50., 50.)},
            'min_camera_z_cm': min(r['position'][2] for r in new),
            'scope': 'analytic aim-plane probes at all camera keys; no mesh silhouette, collision, occlusion or visual certification'}


def build_plan(run=RUN, source=SOURCE, *, variants=VARIANTS):
    run, source = Path(run).resolve(), Path(source).resolve()
    if run == source.parent:
        raise ValueError('Require isolated comparison destination')
    factors = [k for k, _ in variants]
    if (not factors or len(set(factors)) != len(factors)
            or any(not math.isfinite(k) or not 0 < k <= 1 for k in factors)):
        raise ValueError('Require unique finite distance factors in (0,1]')
    if sha(source) != SOURCE_SHA256:
        raise ValueError('Approved frozen source plan changed')
    original = read(source)
    shots, checks, groups = [], [], []
    for mid, cid, label in SETUPS:
        matches = [s for s in original['shots'] if (s['motion_id'], s['camera_id'], s['orientation']) == (mid, cid, 'landscape')]
        if len(matches) != 1 or cid == 'front_head':
            raise ValueError('Expected exact unique non-face landscape source')
        base = matches[0]
        group_id = mid.lower() + '_' + cid
        members = []
        for k, variant_label in variants:
            shot = copy.deepcopy(base)
            sid = f'compact_{group_id}_k{round(k * 100):03d}_v1'
            rows = [transform_row(r, k) for r in base['frames'] + [base['endpoint_validation_frame']]]
            # Source diagnostics are preserved explicitly; do not present them as derived checks.
            source_metadata = {key: shot.pop(key) for key in ('calibration_references', 'common_preset_parameters',
                'framing_diagnostics', 'follow_diagnostics', 'scale_exception', 'closeup_depth_exception',
                'calibration_config_sha256') if key in shot}
            shot.update(shot_id=sid, frames=rows[:-1], endpoint_validation_frame=rows[-1],
                source_shot_id=base['shot_id'], source_shot_plan_sha256=object_sha(base),
                source_trajectory_sha256=base['trajectory_sha256'], trajectory_sha256=object_sha(rows),
                source_camera_metadata=source_metadata, path_metrics=path_metrics(rows),
                endpoint_distances_cm=[norm(sub(r['position'], r['look_at'])) for r in (rows[0], rows[-1])],
                human_acceptance='pending', geometry_pass_scope='finite complete keys; exact aim-plane distance/FOV invariant; no visible-silhouette or scene checks',
                distance_policy='frozen aim center and rotation; position=aim+k*(original_position-aim); tan(new_hfov/2)=tan(original_hfov/2)/k',
                compact_comparison={'group_id': group_id, 'label_zh': label, 'distance_factor': k,
                    'variant_label_zh': variant_label, 'original_hfov_degrees': base['frames'][0]['horizontal_fov_degrees']},
                limitations=['人物瞄准平面上的大小保持；身体前后深度造成的透视比例会改变。',
                    '背景、遮挡、穿模与画面舒适度须看实际渲染；本报告不作视觉验收。'])
            check = geometry(base, shot, k)
            if check['min_camera_z_cm'] < 25:
                raise ValueError('Derived comparison camera below pilot floor')
            checks.append(check)
            shots.append(shot)
            members.append(sid)
        groups.append({'id': group_id, 'label_zh': label, 'shot_ids': members})
    plan = {'schema': 'camera_compact_comparison_trial_v1', 'shots': shots, 'comparison_groups': groups,
            'source_pins': [{'path': str(source), 'sha256': SOURCE_SHA256}],
            'source_samples_sha256': original['source_samples_sha256'], 'human_acceptance': 'pending',
            'face_closeups_excluded': True, 'complete_window': True, 'clock_policy': 'all selected full source windows unchanged',
            'approved_landscape_policy': 'read-only source; isolated comparison assets and unique IDs',
            'media_reuse': 'none; k100 is rendered separately under its own exact comparison plan'}
    if tuple(variants) == GENERAL_VARIANTS:
        plan.update(distance_comparison_percentages=[0, 10, 20, 30, 40, 50],
                    current_landscape_standard_distance_factor=.75,
                    reference_percentage=25,
                    distance_basis='immutable original landscape source, before the accepted k=.75 standard; factors are never composed',
                    media_reuse='exact unchanged k100 and k075 prior comparison shot objects only, with verified full-decode receipts')
    write(run / PLAN_NAME, plan, frozen=True)
    write(run / 'compact_comparison_geometry_v1.json', {'schema': 'camera_compact_comparison_geometry_v1',
        'plan_sha256': sha(run / PLAN_NAME), 'source_unchanged': sha(source) == SOURCE_SHA256,
        'formula': 'C_new=A+k*(C_old-A); tan(hfov_new/2)=tan(hfov_old/2)/k',
        'exact_preservation': 'screen coordinates for points on plane through each frozen aim A perpendicular to frozen view ray',
        'depth_limit': 'for offset z along view ray from aim plane and original distance D, transverse scale ratio is k*(D+z)/(k*D+z)',
        'shots': checks, 'human_acceptance': 'pending'}, frozen=True)
    return {'plan': str(run / PLAN_NAME), 'schema': plan['schema'], 'shots': len(shots),
            'total_render_frames': sum(s['frame_count'] for s in shots), 'source_unchanged': sha(source) == SOURCE_SHA256}


def media_rows(run, shots):
    found = {}
    for report_path in sorted(run.glob('media_validation_*.json')):
        report = read(report_path)
        if report.get('schema') != 'motion_scene_media_validation_v1' or report.get('success') is not True:
            continue
        for row in report['videos']:
            sid = row['shot_id']
            if sid not in shots:
                continue
            checked_media(row, shots[sid], run)
            if sid in found and found[sid] != row:
                raise ValueError('Conflicting verified media: ' + sid)
            found[sid] = row
    return found


def reuse_compact(run=GENERAL_RUN, source=RUN):
    """Reuse only identical approved comparison objects and complete media evidence."""
    run, source = Path(run).resolve(), Path(source).resolve()
    if run == source:
        raise ValueError('Require isolated reuse destination')
    target_plan, source_plan = run / PLAN_NAME, source / PLAN_NAME
    target_hash, source_hash = sha(target_plan), sha(source_plan)
    plan, prior = read(target_plan), read(source_plan)
    old = {s['shot_id']: s for s in prior['shots']}
    shots = {s['shot_id']: s for s in plan['shots']
             if s['compact_comparison']['distance_factor'] in (1., .75)}
    if len(shots) != 8 or any(old.get(sid) != shot for sid, shot in shots.items()):
        raise ValueError('Require eight exact unchanged k100/k075 source shot objects')
    report_path = run / 'media_validation_reused_compact_reference_v2.json'
    if report_path.exists():
        report = read(report_path)
        if (report.get('comparison_plan_sha256') != target_hash
                or report.get('success') is not True
                or {row['shot_id'] for row in report['videos']} != set(shots)):
            raise ValueError('Existing compact reuse report differs')
        for row in report['videos']:
            checked_media(row, shots[row['shot_id']], run)
        return {'plan': str(target_plan), 'reused': len(shots), 'plan_sha256': target_hash}
    rows = verified_rows(shots, source)
    if set(rows) != set(shots):
        raise ValueError('Not all eight exact comparison source clips are verified')
    pins = [{'path': str(source_plan), 'sha256': source_hash}]
    attempts = set()
    for sid, row in rows.items():
        evidence = checked_media(row, shots[sid], source, full_decode=True)
        attempts.add(evidence['attempt'])
        for key in ('video', 'poster', 'timeline_contact', 'verification_receipt'):
            pins.append(copy_pinned(owned(source, source / row[key]), owned(run, run / row[key])))
        checked_media(row, shots[sid], run)
    for attempt in sorted(attempts):
        relative = Path('render_receipts') / (attempt + '.json')
        pins.append(copy_pinned(owned(source, source / relative), owned(run, run / relative)))
    for path in sorted(source.glob('media_validation_*.json')):
        if any(row['shot_id'] in shots for row in read(path).get('videos', [])):
            pins.append(copy_pinned(path, run / 'reuse_source_reports' / ('compact_' + path.name)))
    if (sha(target_plan) != target_hash or sha(source_plan) != source_hash
            or any(sha(pin['path']) != pin['sha256'] for pin in pins)):
        raise ValueError('Compact reuse source or destination plan changed')
    write(report_path, {'schema': 'motion_scene_media_validation_v1', 'success': True,
        'attempt': 'reused_compact_reference_v2', 'videos': list(rows.values()),
        'comparison_plan_sha256': target_hash,
        'source_plans': [{'path': str(target_plan), 'sha256': target_hash}, pins[0]],
        'reuse_source_root': str(source), 'reuse_source_pins': pins,
        'reuse_policy': 'exact unchanged source shot objects, media and receipts; fresh full decode before copy',
        'visual_review': 'pending', 'human_acceptance': 'pending', 'raw_frames_deleted': False}, frozen=True)
    return {'plan': str(target_plan), 'reused': len(rows), 'plan_sha256': target_hash}


def build_follow_comparison(run=RUN, source=SOURCE):
    """Select exact before/after objects; copy only proven original media."""
    run, source = Path(run).resolve(), Path(source).resolve()
    if sha(source) != SOURCE_SHA256 or run == source.parent:
        raise ValueError('Require immutable source and isolated destination')
    corrected_path = run / 'camera_trial_plan_v1.json'
    corrected_hash = sha(corrected_path)
    original, corrected = read(source), read(corrected_path)
    combinations = [(mid, cid, orientation)
        for mid in ('MOTION_CAND_036', 'ACT_F02_CATCH_BREATH')
        for cid in ('side_upper', 'rear_three_quarter_upper')
        for orientation in ('landscape', 'portrait')]
    shots, originals, corrected_ids = [], {}, []
    for key in combinations:
        before = [s for s in original['shots'] if (s['motion_id'], s['camera_id'], s['orientation']) == key]
        after = [s for s in corrected['shots'] if (s['motion_id'], s['camera_id'], s['orientation']) == key]
        if len(before) != 1 or len(after) != 1:
            raise ValueError('Expected exact selected original/corrected pair: ' + str(key))
        before, after = before[0], after[0]
        if after['shot_id'] != before['shot_id'] + '_followfix_v1':
            raise ValueError('Unexpected corrected shot identity')
        if any(before[field] != after[field] for field in CLOCK_FIELDS):
            raise ValueError('Before/after source animation clocks differ')
        shots.extend([before, after])
        originals[before['shot_id']] = before
        corrected_ids.append(after['shot_id'])
    plan = {'schema': 'camera_follow_comparison_trial_v1', 'shots': shots,
            'source_samples_sha256': original['source_samples_sha256'],
            'source_pins': [{'path': str(source), 'sha256': SOURCE_SHA256},
                            {'path': str(corrected_path), 'sha256': corrected_hash}],
            'original_shot_ids': list(originals), 'corrected_shot_ids': corrected_ids,
            'clock_policy': 'complete original-speed source windows unchanged',
            'selected_camera_ids': ['side_upper', 'rear_three_quarter_upper'],
            'human_acceptance': 'pending', 'face_closeups_excluded': True,
            'shot_object_policy': 'exact source JSON objects; no added shot metadata'}
    target = run / 'follow_comparison_plan_v1.json'
    write(target, plan, frozen=True)
    rows = verified_rows(originals, source.parent)
    if set(rows) != set(originals):
        raise ValueError('Not all eight selected original clips have exact verified media')
    report_path = run / 'media_validation_reused_follow_baseline_v1.json'
    if report_path.exists():
        report = read(report_path)
        if (report.get('comparison_plan_sha256') != sha(target)
                or {v['shot_id'] for v in report['videos']} != set(originals)):
            raise ValueError('Existing baseline reuse differs')
        for row in report['videos']:
            checked_media(row, originals[row['shot_id']], run)
        return {'plan': str(target), 'shots': len(shots), 'reused': len(rows), 'corrected_ids': corrected_ids}
    pins = list(plan['source_pins'])
    attempts = set()
    for sid, row in rows.items():
        evidence = checked_media(row, originals[sid], source.parent, full_decode=True)
        attempts.add(evidence['attempt'])
        for key in ('video', 'poster', 'timeline_contact', 'verification_receipt'):
            pins.append(copy_pinned(owned(source.parent, source.parent / row[key]),
                                    owned(run, run / row[key])))
        checked_media(row, originals[sid], run)
    for attempt in sorted(attempts):
        relative = Path('render_receipts') / (attempt + '.json')
        pins.append(copy_pinned(owned(source.parent, source.parent / relative), owned(run, run / relative)))
    for path in sorted(source.parent.glob('media_validation_*.json')):
        source_report = read(path)
        if any(row['shot_id'] in originals for row in source_report.get('videos', [])):
            pins.append(copy_pinned(path, run / 'reuse_source_reports' / ('follow_baseline_' + path.name)))
    if (sha(source) != SOURCE_SHA256 or sha(corrected_path) != corrected_hash
            or any(sha(pin['path']) != pin['sha256'] for pin in pins)):
        raise ValueError('Comparison source changed during reuse')
    report = {'schema': 'motion_scene_media_validation_v1', 'success': True,
              'attempt': 'reused_follow_baseline_v1', 'videos': list(rows.values()),
              'comparison_plan_sha256': sha(target),
              'source_plans': [{'path': str(target), 'sha256': sha(target)}] + plan['source_pins'],
              'reuse_source_root': str(source.parent), 'reuse_source_pins': pins,
              'reuse_policy': 'unchanged exact source shots, media and receipts; fresh full decode before copy',
              'visual_review': 'pending', 'human_acceptance': 'pending', 'raw_frames_deleted': False}
    write(report_path, report, frozen=True)
    return {'plan': str(target), 'shots': len(shots), 'reused': len(rows), 'corrected_ids': corrected_ids}


def build_gallery(run=RUN, follow_plan=None):
    run = Path(run).resolve()
    compact = read(run / PLAN_NAME)
    general = compact.get('distance_comparison_percentages') == [0, 10, 20, 30, 40, 50]
    plans = [(run / PLAN_NAME, compact, 'compact')]
    if follow_plan:
        path = Path(follow_plan).resolve()
        plans.insert(0, (path, read(path), 'follow'))
    all_shots = {}
    for _, plan, _ in plans:
        for shot in plan['shots']:
            if shot['shot_id'] in all_shots:
                raise ValueError('Duplicate gallery shot ID')
            all_shots[shot['shot_id']] = shot
    media = media_rows(run, all_shots)
    labels_path = S.parent / 'dataset/prompt_catalog_first_batch_v1.json'
    legacy_labels = read(labels_path)['labels']['action']
    sections = []
    for path, plan, kind in plans:
        clips = []
        for shot in plan['shots']:
            comparison = shot.get('compact_comparison', {})
            motion_label = legacy_labels.get(shot['motion_id'].lower(), {}).get('zh-CN', shot['motion_label'])
            if general:
                motion_label = {'ACT_F01_SEXY_DANCE': '旧动作：Sexy Dance（ACT_F01_SEXY_DANCE）',
                                'ACT_M04_LIVING_ROOM_SWING': '旧动作：Living Room Swing（ACT_M04_LIVING_ROOM_SWING）'}.get(shot['motion_id'], motion_label)
            row = {key: shot[key] for key in ('shot_id', 'motion_id', 'motion_label', 'camera_id',
                'camera_label', 'orientation', 'duration_seconds', 'frame_count', 'width', 'height')}
            row.update(group_id=comparison.get('group_id', shot.get('comparison_group_id', shot['motion_id'] + '_' + shot['camera_id'] + '_' + shot['orientation'])),
                       label_zh=comparison.get('label_zh', motion_label + ' · ' + shot['camera_label'] + ' · ' + ('横屏' if shot['orientation'] == 'landscape' else '竖屏')),
                       variant_label_zh=comparison.get('variant_label_zh', shot.get('comparison_variant_label_zh',
                           '修复后' if shot['shot_id'].endswith('_followfix_v1') else '修复前')),
                       distance_factor=comparison.get('distance_factor'),
                       fov_degrees=shot['frames'][0]['horizontal_fov_degrees'],
                       playable=shot['shot_id'] in media, human_acceptance='pending')
            if general and kind == 'compact':
                percent = round((1 - comparison['distance_factor']) * 100)
                row.update(distance_reduction_percent=percent,
                           current_standard_reference=percent == 25,
                           variant_label_zh=f'移近{percent}%' + (' · 当前横屏标准（参考）' if percent == 25 else ' · 原始基线' if percent == 0 else ''))
                if shot['camera_id'] == 'front_upper':
                    row['group_warning_zh'] = '抽帧观察：原距离已有头顶贴边或局部裁切，移近50%后约4.53秒更明显；可按构图取舍保留。低头时脸部也可能被头发遮住，请结合完整视频选择距离。'
            if kind == 'follow' and shot.get('comparison_group_warning_zh'):
                row['group_warning_zh'] = shot['comparison_group_warning_zh']
            elif general and kind == 'follow' and shot['motion_id'] in ('ACT_F01_SEXY_DANCE', 'ACT_M04_LIVING_ROOM_SWING'):
                row['group_warning_zh'] = '修正后对摆动的响应更及时；画面是否自然、是否接受局部裁切，仍待人工确认。'
            elif not general and kind == 'follow' and shot['motion_id'] == 'ACT_F02_CATCH_BREATH' and shot['orientation'] == 'portrait':
                row['group_warning_zh'] = '修复后人物不再持续落在镜头后方；深弯腰时头部仍可能从右侧出画，需人工判断。'
            if row['playable']:
                row.update({key: media[shot['shot_id']][key] for key in ('video', 'poster', 'video_sha256',
                    'verification_receipt', 'verification_receipt_sha256', 'decoded_frames')})
            clips.append(row)
        sections.append({'kind': kind, 'plan': {'path': str(path), 'sha256': sha(path)}, 'clips': clips})
    data = {'schema': 'camera_follow_compact_review_v1', 'sections': sections,
            'playable_count': len(media), 'clip_count': len(all_shots), 'human_acceptance': 'pending'}
    if general:
        data.update(distance_basis='original baseline, before accepted 25% reduction',
                    compact_section_title_zh='横屏 · 移近0% / 10% / 20% / 30% / 40% / 50% · 25%现用标准参考',
                    current_landscape_standard_distance_factor=.75,
                    notice_zh='横屏移近25%已接受为当前标准。本页按最初原距离分别移近0%、10%、20%、30%、40%、50%，并保留25%现用标准作为参考；这些百分比都以最初原距离为基准。视角同时放宽，人物瞄准平面的画面大小保持。人物前后部位和背景的透视仍会改变。')
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    gallery = run / 'gallery'
    gallery.mkdir(exist_ok=True)
    target = gallery / 'index.html'
    tmp = gallery / 'index.html.partial'
    html = HTML.replace('__DATA__', encoded)
    if general:
        html = html.replace('<title>相机跟随与近距离比较</title>', '<title>跟随对照 · 25%现用标准与0–50%距离比较</title>')
        html = html.replace('<h1>相机跟随与近距离比较</h1>', '<h1>跟随对照 · 25%现用标准与0–50%距离比较</h1>')
        html = html.replace('已接受的横屏标准继续保留。本页近距离镜头是独立试验：相机移近15%或25%，同时放宽视角，让人物中心附近在画面中的大小保持接近。伸向前方的手、身体厚度和背景的远近关系仍会变化，请直接比较视频。', data['notice_zh'])
        html = html.replace("'横屏 · 原距离 / 移近15% / 移近25%'", 'DATA.compact_section_title_zh')
    tmp.write_text(html, encoding='utf-8')
    tmp.replace(target)
    (gallery / '打开相机比较.cmd').write_text('@echo off\n"' + sys.executable + '" "'
        + str(S / 'open_common_camera_gallery_v1.py') + '" --run-root "' + str(run)
        + '" --port ' + ('8897' if general else '8896') + ' %*\nif errorlevel 1 pause\n', encoding='utf-8')
    write(run / 'compact_review_delivery_manifest_v1.json', data)
    return {'index': str(target), 'clips': len(all_shots), 'playable': len(media), 'human_acceptance': 'pending'}


HTML = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>相机跟随与近距离比较</title>
<style>*{box-sizing:border-box}body{margin:0;background:#10151c;color:#e7edf5;font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1700px;margin:auto;padding:30px}h1{font-size:30px;margin:0 0 8px}h2{margin:34px 0 8px;font-size:23px}h3{font-size:18px;margin:0}p{max-width:1100px;color:#b9c9da}.notice{padding:16px 20px;background:#192633;border-left:4px solid #68bfce;border-radius:8px}.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:20px 0}button,select{font:inherit;border:1px solid #4e6984;background:#21354a;color:white;padding:7px 14px;border-radius:7px;cursor:pointer}button:hover{background:#2d4965}.group{background:#17212c;border:1px solid #2b3b4b;border-radius:12px;padding:18px;margin:18px 0}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin-top:14px}.card{min-width:0;background:#0b1118;border-radius:9px;overflow:hidden}.meta{padding:11px 13px}.meta strong{display:block}.meta small{color:#a9bdd1}video{width:100%;display:block;background:black;max-height:520px}.pending{aspect-ratio:16/9;display:grid;place-items:center;color:#9cacc0;background:#101820}.status{color:#92d1bd}.foot{font-size:14px;color:#9cacc0}details{font-size:13px;color:#a9bdd1;word-break:break-all}summary{cursor:pointer}input[type=range]{width:min(500px,100%)}.cards.pair{grid-template-columns:repeat(2,minmax(0,1fr))}@media(max-width:950px){.cards,.cards.pair{grid-template-columns:1fr}main{padding:18px}video{max-height:650px}}</style>
<main><h1>相机跟随与近距离比较</h1><p>先看运动时人物是否稳在合适位置，再比较把相机移近后的空间效果。同组使用相同的动作片段、时长和播放速度，只比较相机效果。</p>
<div class="notice">已接受的横屏标准继续保留。本页近距离镜头是独立试验：相机移近15%或25%，同时放宽视角，让人物中心附近在画面中的大小保持接近。伸向前方的手、身体厚度和背景的远近关系仍会变化，请直接比较视频。</div>
<div class="toolbar"><label>查看内容 <select id="section"><option value="all">全部</option><option value="follow">跟随修正</option><option value="compact">相机移近比较</option></select></label><span id="status" class="status"></span><button id="pause">暂停全部</button></div><div id="content"></div>
<p class="foot">“媒体已核验”仅表示视频帧数、时长、分辨率和来源凭据已核对。视觉接受仍待人工确认。人物前后部位和背景的比例仍可能变化；场景中的遮挡、穿模和画面是否舒服，需要另外看实际画面。</p></main>
<script>const DATA=__DATA__;const root=document.querySelector('#content');const el=(tag,text,cls)=>{let e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e};
function render(){document.querySelectorAll('video').forEach(v=>v.pause());root.replaceChildren();let filter=document.querySelector('#section').value;for(const section of DATA.sections){if(filter!=='all'&&section.kind!==filter)continue;root.append(el('h2',section.kind==='follow'?'跟随修正样片':'横屏 · 原距离 / 移近15% / 移近25%'));let groups=new Map();for(const clip of section.clips){if(!groups.has(clip.group_id))groups.set(clip.group_id,[]);groups.get(clip.group_id).push(clip)}for(const clips of groups.values()){let group=el('section',undefined,'group');group.append(el('h3',clips[0].label_zh));for(const warning of new Set(clips.map(c=>c.group_warning_zh).filter(Boolean)))group.append(el('p',warning,'notice'));let bar=el('div',undefined,'toolbar'),cards=el('div',undefined,'cards');if(clips.length===2)cards.classList.add('pair');let play=el('button','同组同步播放'),stop=el('button','暂停'),seek=document.createElement('input');seek.type='range';seek.min=0;seek.max=clips[0].duration_seconds;seek.step=1/30;seek.value=0;seek.setAttribute('aria-label','同组播放位置');let clock=el('span','0.00 秒');let videos=[];bar.append(play,stop,seek,clock);group.append(bar,cards);for(const clip of clips){let card=el('article',undefined,'card'),meta=el('div',undefined,'meta');meta.append(el('strong',clip.variant_label_zh));meta.append(el('small',`${clip.orientation==='landscape'?'横屏':'竖屏'} · ${clip.duration_seconds.toFixed(2)}秒 · ${clip.width}×${clip.height} · 视角 ${clip.fov_degrees.toFixed(2)}°`));if(clip.playable){let v=document.createElement('video');v.controls=true;v.muted=true;v.playsInline=true;v.preload='metadata';v.src='../'+clip.video;v.poster='../'+clip.poster;v.setAttribute('aria-label',clip.label_zh+' '+clip.variant_label_zh);videos.push(v);card.append(v)}else card.append(el('div','正在准备，媒体尚未核验','pending'));card.append(meta);let details=el('details'),summary=el('summary','查看样片编号');details.append(summary,el('div',clip.shot_id));meta.append(details);cards.append(card)}play.onclick=async()=>{const t=Number(seek.value);for(const v of videos){if(v.readyState<1)continue;v.currentTime=Math.min(t,v.duration-.001)}await Promise.all(videos.map(v=>v.play().catch(()=>{})))};stop.onclick=()=>videos.forEach(v=>v.pause());seek.oninput=()=>{const t=Number(seek.value);videos.forEach(v=>{if(v.readyState>=1)v.currentTime=Math.min(t,v.duration-.001)});clock.textContent=t.toFixed(2)+' 秒'};if(videos.length)videos[0].ontimeupdate=()=>{if(document.activeElement!==seek){seek.value=videos[0].currentTime;clock.textContent=videos[0].currentTime.toFixed(2)+' 秒'}};root.append(group)}}document.querySelector('#status').textContent=`媒体已核验 ${DATA.playable_count} / ${DATA.clip_count}；视觉确认待完成`}
document.querySelector('#section').onchange=render;document.querySelector('#pause').onclick=()=>document.querySelectorAll('video').forEach(v=>v.pause());render();</script></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'gallery', 'follow-comparison', 'reuse-compact'])
    parser.add_argument('--run-root', type=Path, default=RUN)
    parser.add_argument('--source-plan', type=Path, default=SOURCE)
    parser.add_argument('--follow-plan', type=Path)
    parser.add_argument('--general-six', action='store_true', help='Compare original-distance reductions 0/10/20/30/40/50 percent, plus accepted 25 percent reference')
    parser.add_argument('--reuse-root', type=Path, default=RUN)
    args = parser.parse_args()
    if args.mode == 'plan':
        result = build_plan(args.run_root, args.source_plan,
                            variants=GENERAL_VARIANTS if args.general_six else VARIANTS)
    elif args.mode == 'follow-comparison':
        result = build_follow_comparison(args.run_root, args.source_plan)
    elif args.mode == 'reuse-compact':
        result = reuse_compact(args.run_root, args.reuse_root)
    else:
        result = build_gallery(args.run_root, args.follow_plan)
    print(json.dumps(result, ensure_ascii=False))
