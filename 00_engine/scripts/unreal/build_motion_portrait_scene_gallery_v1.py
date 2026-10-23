"""Build experimental variable-duration motion/portrait/scene review.

Owner: SCENE_CAMERA_SEQUENCE.md §11. Never changes source media or UE assets.
The input is assembled from actual encode/decode receipts by the pilot runner.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def local_file(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Expected a nonempty relative media path')
    target = (root / relative).resolve()
    target.relative_to(root.resolve())
    if not target.is_file():
        raise FileNotFoundError(target)
    return target


def build(run=RUN):
    run = Path(run).resolve()
    source = run / 'review_gallery_input_v1.json'
    data = json.loads(source.read_text(encoding='utf-8-sig'))
    if data.get('schema') != 'motion_portrait_scene_review_v1':
        raise ValueError('Unknown review schema')
    data.setdefault('motions', [])
    data.setdefault('scenes', [])
    data.setdefault('clips', [])
    for key in ('motions', 'scenes', 'clips'):
        ids = [row['id'] for row in data[key]]
        if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[\w.-]+', str(x)) for x in ids):
            raise ValueError('Unsafe or duplicate IDs: ' + key)
    motions = {row['id'] for row in data['motions']}
    scenes = {row['id'] for row in data['scenes']}
    for clip in data['clips']:
        if clip['section'] not in ('motions', 'portrait', 'scenes') or clip['motion_id'] not in motions:
            raise ValueError('Unknown section or motion: ' + clip['id'])
        if clip['section'] == 'scenes' and clip.get('scene_id') not in scenes:
            raise ValueError('Unknown scene: ' + clip['id'])
        clip['playable'] = False
        clip['human_acceptance'] = 'pending'
        if clip.get('verification_status') != 'encoded_verified':
            clip.pop('video', None)
            clip.pop('poster', None)
            continue
        duration, fps, count = (clip[k] for k in ('duration_seconds', 'fps', 'decoded_frames'))
        if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (duration, fps, count)):
            raise ValueError('Invalid media timing: ' + clip['id'])
        if int(count) != count or abs(count / fps - duration) > 1 / fps + 0.001:
            raise ValueError('Duration does not match complete decoded frames: ' + clip['id'])
        width, height = clip['width'], clip['height']
        if (width, height) not in ((1280, 720), (720, 1280)):
            raise ValueError('Unexpected pilot media dimensions: ' + clip['id'])
        expected = 'portrait' if height > width else 'landscape'
        if clip.get('orientation', expected) != expected:
            raise ValueError('Orientation/dimensions disagree: ' + clip['id'])
        clip['orientation'] = expected
        video = local_file(run, clip['video'])
        if video.suffix.lower() != '.mp4' or digest(video) != clip['video_sha256']:
            raise ValueError('Verified video hash mismatch: ' + clip['id'])
        clip['video'] = video.relative_to(run).as_posix()
        if clip.get('poster'):
            clip['poster'] = local_file(run, clip['poster']).relative_to(run).as_posix()
        clip['playable'] = True
    data.update(input_sha256=digest(source), human_acceptance='pending',
                playable_count=sum(c['playable'] for c in data['clips']))
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    gallery = run / 'gallery'
    gallery.mkdir(exist_ok=True)
    html = (S / 'motion_portrait_scene_gallery_v1.html').read_text(encoding='utf-8').replace('__DATA__', encoded)
    (gallery / 'index.html').write_text(html, encoding='utf-8')
    (gallery / '打开动作竖屏场景审查.cmd').write_text('@echo off\n"C:\\ProgramData\\anaconda3\\python.exe" "' + str(S / 'open_motion_portrait_scene_gallery_v1.py') + '" --run-root "' + str(run) + '" %*\nif errorlevel 1 pause\n', encoding='utf-8')
    (run / 'review_delivery_manifest_v1.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return {'index': str(gallery / 'index.html'), 'clips': len(data['clips']), 'playable': data['playable_count'], 'human_acceptance': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=RUN)
    print(json.dumps(build(parser.parse_args().run_root), ensure_ascii=False))
