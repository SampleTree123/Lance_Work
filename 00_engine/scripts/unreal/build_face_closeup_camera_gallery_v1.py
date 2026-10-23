"""Publish independent face-closeup camera review.

Reuse the receipt/media validator. Pending rows never receive media URLs.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import re
from build_camera_alignment_gallery_v1 import validate, digest, local_file, CAMERA_ORDER, presentation
from encode_motion_scene_pilot_v1 import object_sha

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_face_closeup_20261014_v2'


def build(run=RUN):
    run = Path(run).resolve()
    source = run / 'camera_trial_plan_v1.json'
    plan = json.loads(source.read_text(encoding='utf-8-sig'))
    if plan.get('schema') != 'camera_face_closeup_trial_v1':
        raise ValueError('Expected face-closeup plan')
    config_pin = plan['reference_config']
    config_path = Path(config_pin['path']).resolve()
    if digest(config_path) != config_pin['sha256']:
        raise ValueError('Face config differs from frozen plan')
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    shots = {s['shot_id']: s for s in plan['shots']}
    mids = {s['motion_id'] for s in shots.values()}
    cids = {s['camera_id'] for s in shots.values()}
    combinations = {(s['motion_id'], s['camera_id'], s['orientation']) for s in shots.values()}
    if (len(shots) != len(plan['shots']) or len(mids) != 30 or cids != {'front_head'}
            or len(combinations) != 60
            or any((mid, 'front_head', orientation) not in combinations
                   for mid in mids for orientation in ('landscape', 'portrait'))):
        raise ValueError('Expected 30 actions × face closeup × 2 orientations')
    media = {}
    for path in sorted(run.glob('media_validation_*.json')):
        report = json.loads(path.read_text(encoding='utf-8-sig'))
        if report.get('schema') != 'motion_scene_media_validation_v1' or report.get('success') is not True:
            continue
        for row in report['videos']:
            sid = row['shot_id']
            if sid not in shots:
                continue
            rp = local_file(run, row['verification_receipt'])
            if digest(rp) != row['verification_receipt_sha256']:
                raise ValueError('Changed receipt: ' + sid)
            receipt = json.loads(rp.read_text(encoding='utf-8-sig'))
            if receipt.get('shot_plan_sha256') != object_sha(shots[sid]):
                raise ValueError('Receipt plan differs: ' + sid)
            if sid in media and media[sid] != row:
                raise ValueError('Conflicting media: ' + sid)
            media[sid] = row
    motions, cameras, clips = {}, {}, []
    for sid, shot in shots.items():
        mid, cid = shot['motion_id'], shot['camera_id']
        motions[mid] = {'id': mid, 'label': shot['motion_label'], 'sex': shot['sex']}
        cameras[cid] = {'id': cid, 'label': shot['camera_label']}
        row = {key: shot[key] for key in
               ('motion_id', 'camera_id', 'sex', 'orientation', 'width', 'height', 'duration_seconds', 'fps')}
        row.update(id=sid, section='cameras', verification_status='pending',
                   face_camera_parameters={
                       **config['orientations'][shot['orientation']],
                       **shot.get('face_camera_parameters', {}),
                       'distance_cm': shot['endpoint_distances_cm'][0],
                       'horizontal_fov_degrees': shot['frames'][0]['horizontal_fov_degrees'],
                   },
                   common_preset_parameters={**shot.get('common_preset_parameters', {}),
                       'horizontal_fov_degrees': shot['frames'][0]['horizontal_fov_degrees']},
                   tracking_policy=shot.get('tracking_policy', {}),
                   follow_diagnostics=shot.get('follow_diagnostics', {}),
                   framing_diagnostics=shot.get('framing_diagnostics', {}),
                   path_metrics=shot.get('path_metrics', {}),
                   plan_status=shot.get('status', 'pending'))
        if sid in media:
            for key in ('video', 'video_sha256', 'poster', 'decoded_frames', 'verification_status',
                        'verification_receipt', 'verification_receipt_sha256'):
                if key in media[sid]:
                    row[key] = media[sid][key]
        clips.append(row)
    rank = {cid: i for i, cid in enumerate(CAMERA_ORDER)}
    data = {'schema': 'camera_motion_scene_alignment_review_v1',
            'trial_schema': 'camera_face_closeup_review_v1',
            'review_run_id': run.name, 'revision': plan.get('revision', 1),
            'motions': sorted(motions.values(), key=lambda m: (m['id'].startswith('ACT_'), m['id'])),
            'cameras': sorted(cameras.values(), key=lambda c: rank.get(c['id'], 99)),
            'clips': clips, 'scenes': [], 'updated_at': datetime.now(timezone.utc).isoformat(),
            'plan_sha256': digest(source), 'reference_config': config_pin, 'human_acceptance': 'pending',
            'geometry_risks_require_review': plan.get('geometry_risks_require_review', []),
            'per_action_tuning': True, 'pilot_shot_ids': plan.get('pilot_shot_ids', plan.get('smoke_shot_ids', []))}
    data = presentation(validate(data, run))
    observation_path = run / 'face_closeup_bounded_visual_review_v2.json'
    if observation_path.is_file():
        observation = json.loads(observation_path.read_text(encoding='utf-8-sig'))
        if (observation.get('schema') != 'face_closeup_bounded_visual_review_v2'
                or observation.get('plan', {}).get('sha256') != data['plan_sha256']):
            raise ValueError('Face observations differ from active plan')
        index = {row['id']: row for row in clips}
        for observed in observation.get('reviewed', []):
            orientation = observed.get('orientation')
            if observed.get(f'{orientation}_wider_than_pilot') is not True:
                continue
            row = index.get(observed['shot_id'])
            if (not row or row['orientation'] not in ('portrait', 'landscape')
                    or row['motion_id'] != observed['motion_id']
                    or observed['orientation'] != row['orientation']
                    or observed.get('evidence', {}).get('video', {}).get('sha256') != row.get('video_sha256')):
                raise ValueError('Wider composition observation differs from media')
            row['review_hint'] = {
                'message_zh': '动作幅度较大，近景范围较宽，请重点审查',
                'source': observation_path.name,
                'scope_zh': '依据本组合的20张离散抽样；构图仍待用户检查。',
                'human_acceptance': 'pending',
            }
        data['bounded_review_source'] = {'path': observation_path.name, 'sha256': digest(observation_path)}
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    gallery = run / 'gallery'
    gallery.mkdir(exist_ok=True)
    html = (S / 'face_closeup_camera_gallery_v1.html').read_text(encoding='utf-8').replace('__DATA__', encoded)
    temporary = gallery / 'index.html.partial'
    temporary.write_text(html, encoding='utf-8')
    temporary.replace(gallery / 'index.html')
    manifest = run / 'review_delivery_manifest_v1.json'
    temporary = manifest.with_suffix('.json.partial')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(manifest)
    (gallery / '打开面部近景审查.cmd').write_text(
        '@echo off\n"C:\\ProgramData\\anaconda3\\python.exe" "' + str(S / 'open_face_closeup_camera_gallery_v1.py')
        + '" --run-root "' + str(run) + '" %*\nif errorlevel 1 pause\n', encoding='utf-8')
    return {'index': str(gallery / 'index.html'), 'clips': len(clips),
            'playable': data['playable_count'], 'human_acceptance': data['human_acceptance']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=RUN)
    print(json.dumps(build(parser.parse_args().run_root), ensure_ascii=False))
