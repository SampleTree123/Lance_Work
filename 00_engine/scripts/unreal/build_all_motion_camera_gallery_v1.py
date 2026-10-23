"""Publish all-motion camera review. Owner: SCENE_CAMERA_SEQUENCE §15.

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
RUN = S.parents[1] / 'outputs/camera_all_motions_portrait115_20261014_v1'


def build(run=RUN):
    run = Path(run).resolve()
    source = run / 'camera_trial_plan_v1.json'
    plan = json.loads(source.read_text(encoding='utf-8-sig'))
    if plan.get('schema') != 'camera_all_motions_portrait115_trial_v1':
        raise ValueError('Expected all-motion portrait115 plan')
    shots = {s['shot_id']: s for s in plan['shots']}
    mids = {s['motion_id'] for s in shots.values()}
    cids = {s['camera_id'] for s in shots.values()}
    combinations = {(s['motion_id'], s['camera_id'], s['orientation']) for s in shots.values()}
    if (len(shots) != len(plan['shots']) or len(mids) != 30 or len(cids) != 20
            or len(combinations) != 1200 or 'front_head' in cids
            or any((mid, cid, orientation) not in combinations
                   for mid in mids for cid in cids for orientation in ('landscape', 'portrait'))):
        raise ValueError('Expected 30 actions × 20 cameras × 2 orientations without face closeup')
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
            'trial_schema': 'camera_all_motions_portrait115_review_v1',
            'motions': sorted(motions.values(), key=lambda m: (m['id'].startswith('ACT_'), m['id'])),
            'cameras': sorted(cameras.values(), key=lambda c: rank.get(c['id'], 99)),
            'clips': clips, 'scenes': [], 'updated_at': datetime.now(timezone.utc).isoformat(),
            'plan_sha256': digest(source), 'human_acceptance': 'pending',
            'geometry_risks_require_review': plan.get('geometry_risks_require_review', []),
            'standard_version': 'nonface_camera_standard_20261014_v1'}
    data = presentation(validate(data, run))
    observation_path = run / 'bounded_visual_review_v1.json'
    if observation_path.is_file():
        observation = json.loads(observation_path.read_text(encoding='utf-8-sig'))
        if (observation.get('schema') != 'camera_all_motions_bounded_visual_review_v1'
                or observation.get('plan', {}).get('sha256') != data['plan_sha256']):
            raise ValueError('Bounded observations differ from active plan')
        index = {row['id']: row for row in clips}
        attached = 0
        outside_scope = []
        for observed in observation.get('shots', []):
            sid = observed['shot_id']
            row = index.get(sid)
            if not row or not row['playable']:
                continue
            if any(observed.get(key) != row[key] for key in ('motion_id', 'camera_id', 'orientation')):
                raise ValueError('Bounded observation dimensions differ: ' + sid)
            pin = observed['verification_receipt']
            if (Path(pin['path']).resolve() != local_file(run, row['verification_receipt'])
                    or pin['sha256'] != row['verification_receipt_sha256']):
                raise ValueError('Bounded observation receipt differs: ' + sid)
            evidence = observed['image_evidence']
            image_path = Path(evidence['path']).resolve()
            image_path.relative_to(run)
            if digest(image_path) != evidence['sha256']:
                raise ValueError('Bounded observation image differs: ' + sid)
            camera_parts = []
            for part in re.split('[；。]', observed['actual_visual_observation']):
                if any(word in part for word in ('服装', '上衣', '裙部', '红衣', '缺口')):
                    outside_scope.append({'shot_id': sid, 'message_zh': part})
                elif part.strip():
                    camera_parts.append(part.strip())
            row['review_notes'] = {
                'source': '本轮代表样片的20张离散抽样',
                'message_zh': '；'.join(camera_parts) + '。',
                'has_local_crop_observation': bool(observed.get('local_crops')),
                'human_acceptance': 'pending',
                'scope': '仅此动作、镜头和画幅的20张采样；不代表连续逐帧审查，也不确定裁切持续时间或其他组合。',
            }
            attached += 1
        data['bounded_review_source'] = {
            'path': observation_path.name, 'sha256': digest(observation_path),
            'selected_shots': observation.get('selected_shot_count'),
            'observed_shots': observation.get('observed_shot_count'),
            'observed_images': observation.get('observed_image_count'),
            'attached_clips': attached, 'human_acceptance': 'pending',
        }
        # Keep garment observations in the summary metadata, outside camera UI.
        data['out_of_scope_observations_for_summary'] = outside_scope
    acceptance_path = run / 'user_acceptance_20261014_v1.json'
    if acceptance_path.is_file():
        acceptance = json.loads(acceptance_path.read_text(encoding='utf-8-sig'))
        if (acceptance.get('schema') != 'camera_nonface_standard_acceptance_v1'
                or acceptance.get('plan_sha256') != data['plan_sha256']
                or acceptance.get('human_acceptance') != 'accepted'
                or acceptance.get('accepted_clip_count') != len(clips)
                or data['playable_count'] != len(clips)):
            raise ValueError('Current standard acceptance does not match complete plan')
        data.update(human_acceptance='accepted', current_standard_acceptance=acceptance,
                    acceptance_source={'path': acceptance_path.name, 'sha256': digest(acceptance_path)})
        for row in clips:
            row.update(human_acceptance='accepted', visual_status='accepted_with_local_cropping_allowed')
            if row.get('review_notes'):
                row['review_notes']['human_acceptance'] = 'accepted_with_local_cropping_allowed'
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    gallery = run / 'gallery'
    gallery.mkdir(exist_ok=True)
    html = (S / 'all_motion_camera_gallery_v1.html').read_text(encoding='utf-8').replace('__DATA__', encoded)
    temporary = gallery / 'index.html.partial'
    temporary.write_text(html, encoding='utf-8')
    temporary.replace(gallery / 'index.html')
    manifest = run / 'review_delivery_manifest_v1.json'
    temporary = manifest.with_suffix('.json.partial')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(manifest)
    (gallery / '打开全部动作镜头审查.cmd').write_text(
        '@echo off\n"C:\\ProgramData\\anaconda3\\python.exe" "' + str(S / 'open_all_motion_camera_gallery_v1.py')
        + '" --run-root "' + str(run) + '" %*\nif errorlevel 1 pause\n', encoding='utf-8')
    return {'index': str(gallery / 'index.html'), 'clips': len(clips),
            'playable': data['playable_count'], 'human_acceptance': data['human_acceptance']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=RUN)
    print(json.dumps(build(parser.parse_args().run_root), ensure_ascii=False))
