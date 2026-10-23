"""Build the 21-preset, seven-action stable-camera review (experimental).

Owner: SCENE_CAMERA_SEQUENCE.md. Read-only source media; verified copies are not
silently accepted as human-approved. No UE operations or old gallery changes.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/unreal_character_import/camera_complete_angles_20261010_v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(root, relative):
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    return path


def media_row(run, shot):
    sid = shot['shot_id']
    if not re.fullmatch(r'[A-Za-z0-9_]+', sid):
        raise ValueError('Unsafe shot ID')
    receipt_path = run / 'media_receipts' / (sid + '.json')
    row = {'shot_id': sid, 'camera_label': shot['camera_label'],
           'motion_label': shot['motion_label'], 'playable': False,
           'review_status': 'pending', 'video': None, 'poster': None,
           'trajectory_sha256': shot['trajectory_sha256']}
    if not receipt_path.exists():
        return row
    receipt = read(receipt_path)
    decode = receipt.get('decode', {})
    if (receipt.get('status') != 'encoded_verified' or receipt.get('shot_id') != sid
            or decode.get('decoded_frames') != 300 or decode.get('fps') != 30
            or decode.get('measured_duration_seconds') != 10):
        raise ValueError('Invalid ten-second media receipt: ' + sid)
    video = local_path(run, receipt['video'])
    if digest(video) != receipt['video_sha256']:
        raise ValueError('Video changed after verification: ' + sid)
    row.update(playable=True, video=video.relative_to(run.resolve()).as_posix(),
               video_sha256=receipt['video_sha256'],
               verification_receipt_sha256=digest(receipt_path))
    poster = run / 'videos' / (sid + '.jpg')
    if poster.exists():
        row['poster'] = poster.relative_to(run).as_posix()
    return row


def build(run=RUN):
    run = Path(run).resolve()
    plan_path = run / 'expansion_plan_v1.json'
    plan = read(plan_path)
    groups = {}
    shot_ids = set()
    for shot in plan['shots']:
        if shot['shot_id'] in shot_ids:
            raise ValueError('Duplicate shot ID')
        shot_ids.add(shot['shot_id'])
        preset = shot['stable_preset_id']
        action = shot.get('stable_action_id', shot['motion_label'])
        group = groups.setdefault(preset, {'id': preset, 'label': shot['camera_label'], 'clips': []})
        if any(c['action_id'] == action for c in group['clips']):
            raise ValueError('Duplicate action in preset: ' + preset)
        group['clips'].append(dict(media_row(run, shot), action_id=action))
    if len(groups) != 21 or len(shot_ids) != 147 or any(len(g['clips']) != 7 for g in groups.values()):
        raise ValueError('Expected exactly 21 presets × 7 actions')
    actions = {tuple(sorted(c['action_id'] for c in g['clips'])) for g in groups.values()}
    if len(actions) != 1:
        raise ValueError('All presets must cover the same seven actions')
    data = {'schema': 'complete_camera_review_delivery_v1', 'plan_sha256': digest(plan_path),
            'duration_seconds': 10, 'human_acceptance': 'pending', 'groups': list(groups.values()),
            'clips': [c for g in groups.values() for c in g['clips']]}
    data['playable'] = sum(c['playable'] for c in data['clips'])
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (S / 'complete_camera_gallery_v1.html').read_text(encoding='utf-8')
    output = template.replace('__DATA__', encoded)
    destination = run / 'gallery'
    destination.mkdir(exist_ok=True)
    (destination / 'index.html').write_text(output, encoding='utf-8')
    (destination / '打开完整视角审查.cmd').write_text(
        '@echo off\n"C:\\ProgramData\\anaconda3\\python.exe" "' + str(S / 'open_complete_camera_gallery_v1.py')
        + '" %*\nif errorlevel 1 pause\n', encoding='utf-8')
    (run / 'review_delivery_manifest_v1.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'index': str(destination / 'index.html'), 'presets': 21, 'clips': 147, 'playable': data['playable']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=RUN)
    print(json.dumps(build(parser.parse_args().run_root), ensure_ascii=False))
