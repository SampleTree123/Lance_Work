"""Assemble the pilot review manifest from frozen plans and verified media.

Owner: SCENE_CAMERA_SEQUENCE section 11. Experimental, no Unreal operations.
"""
from pathlib import Path
import argparse
import json
from encode_motion_scene_pilot_v1 import RUN, read, sha, object_sha, owned, atomic_json
from build_motion_portrait_scene_gallery_v1 import build


def assemble(run=RUN, plans=None, decisions=None, scenes=None):
    run = Path(run).resolve()
    decisions_path = Path(decisions or run / 'motion_window_decisions_v2.json').resolve()
    decision_data = read(decisions_path)
    plan_paths = [Path(p).resolve() for p in (plans or [run / 'camera_trial_plan_v1.json'])]
    shots = {}
    scene_rows = {}
    for path in plan_paths:
        plan = read(path)
        for shot in plan['shots']:
            sid = shot['shot_id']
            if sid in shots and object_sha(shots[sid]) != object_sha(shot):
                raise ValueError('Conflicting review shot: ' + sid)
            shots[sid] = shot
        for scene in plan.get('scenes', []):
            scene_rows[scene['id']] = scene
    if scenes:
        for scene in read(scenes)['scenes']:
            scene_rows[scene['id']] = scene
    notes_path = run / 'review_clip_notes_v1.json'
    clip_notes = read(notes_path).get('clips', {}) if notes_path.exists() else {}
    media = {}
    report_pins = []
    for path in sorted(run.glob('media_validation_*.json')):
        report = read(path)
        if report.get('schema') != 'motion_scene_media_validation_v1' or report.get('success') is not True:
            continue
        relevant = [row for row in report['videos'] if row['shot_id'] in shots]
        if not relevant:
            continue
        report_pins.append({'path': path.relative_to(run).as_posix(), 'sha256': sha(path)})
        for row in relevant:
            sid = row['shot_id']
            receipt_path = owned(run, run / row['verification_receipt'])
            if sha(receipt_path) != row['verification_receipt_sha256']:
                raise ValueError('Media verification receipt changed: ' + sid)
            receipt = read(receipt_path)
            if (receipt.get('schema') != 'motion_scene_encoded_shot_v1'
                    or receipt.get('status') != 'encoded_verified'
                    or receipt['shot_id'] != sid
                    or receipt['shot_plan_sha256'] != object_sha(shots[sid])
                    or receipt['video_sha256'] != row['video_sha256']):
                raise ValueError('Media does not belong to the frozen shot: ' + sid)
            if sid in media and media[sid] != row:
                raise ValueError('Conflicting verified media records: ' + sid)
            media[sid] = row
    by_motion = {}
    for shot in shots.values():
        by_motion.setdefault(shot['motion_id'], []).append(shot)
    motions = []
    for action in decision_data['actions']:
        mid = action['motion_id']
        candidates = by_motion.get(mid, [])
        overview = next((s for s in candidates if s['group'] == 'motions'), candidates[0] if candidates else None)
        sex = overview['sex'] if overview else next(iter(action['variants']))
        mode = action['mode']
        decision = 'keep' if mode == 'keep_full' else 'exclude' if action['window_start_seconds'] is None else 'trim'
        if decision == 'keep':
            reason = '完整动作的移动范围符合初步几何筛选，先保留，等待你看自然度。'
        elif decision == 'exclude':
            reason = '暂未找到满足原地小范围或直线移动要求的连续片段；保留源资产。'
        elif action['body_play_rate'] != 1:
            reason = '按要求保留前6秒，以0.6倍速度播放为10秒；需要检查步伐是否自然。'
        else:
            reason = '截取连续片段，避开大幅拐弯或折返；保持原速，暂不统一时长。'
        motions.append({'id': mid, 'label': action['label'], 'decision': decision,
            'reason': reason, 'source_duration_seconds': action['variants'][sex]['source_duration_seconds'],
            'source_window_seconds': [action['window_start_seconds'], action['window_end_seconds']],
            'output_duration_seconds': action['output_duration_seconds'],
            'rendered_overview_duration_seconds': overview['duration_seconds'] if overview else None,
            'variant': '女性' if sex == 'female' else '男性', 'sex': sex,
            'human_acceptance': 'pending', 'scope': action['scope']})
    clips = []
    for sid, shot in shots.items():
        row = {'id': sid, 'section': shot['group'], 'motion_id': shot['motion_id'],
            'camera_id': shot['camera_id'], 'camera_label': shot['camera_label'],
            'orientation': shot['orientation'], 'width': shot['width'], 'height': shot['height'],
            'duration_seconds': shot['duration_seconds'], 'fps': shot['fps'],
            'verification_status': 'pending', 'human_acceptance': 'pending'}
        if shot.get('scene_id'):
            row['scene_id'] = shot['scene_id']
        if sid in media:
            evidence = media[sid]
            for key in ('video','video_sha256','poster','decoded_frames','verification_status','verification_receipt','verification_receipt_sha256'):
                row[key] = evidence[key]
        else:
            row['note'] = '生成中，完成编码与检查后开放播放。'
        if shot['group'] == 'portrait' and sid in media:
            row['note'] = '最多10秒构图试点；完整动作见动作审查。'
        if sid in clip_notes:
            row['note'] = (row.get('note', '') + ' ' + clip_notes[sid]['note']).strip()
        clips.append(row)
    data = {'schema': 'motion_portrait_scene_review_v1', 'human_acceptance': 'pending',
            'motions': motions, 'scenes': list(scene_rows.values()), 'clips': clips,
            'generation_status': 'in_progress', 'scene_pilot_target': 3,
            'source_decisions': {'path': str(decisions_path), 'sha256': sha(decisions_path)},
            'source_plans': [{'path': str(p), 'sha256': sha(p)} for p in plan_paths],
            'source_media_reports': report_pins}
    if notes_path.exists():
        data['source_clip_notes'] = {'path': str(notes_path), 'sha256': sha(notes_path)}
    atomic_json(run / 'review_gallery_input_v1.json', data)
    return build(run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, action='append')
    parser.add_argument('--decisions', type=Path)
    parser.add_argument('--scenes', type=Path, help='JSON containing scenes array for scene notes/limits')
    args = parser.parse_args()
    print(json.dumps(assemble(plans=args.plan, decisions=args.decisions, scenes=args.scenes), ensure_ascii=False))
