"""Recoverable variable-duration pilot encoding. Owner: SCENE_CAMERA_SEQUENCE §11.

Reads completed isolated render receipts and frozen shot plans, never UE assets.
Existing verified media is rehashed and fully decoded; conflicts are preserved.
Raw frames are never deleted. FFmpeg full decode and OpenCV per-frame inspection
jointly validate output; the bundled FFmpeg location matches the earlier encoder.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import cv2
from PIL import Image, ImageDraw
from encode_camera_pilot_v1 import FFMPEG, sha, identifier, read, atomic_json

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1')


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def owned(root, path):
    result = Path(path).resolve()
    result.relative_to(root.resolve())
    return result


def shot_plan(plans):
    shots = {}
    pins = []
    for path in plans:
        path = Path(path).resolve()
        document = read(path)
        pins.append({'path': str(path), 'sha256': sha(path)})
        for shot in document['shots']:
            sid = identifier(shot['shot_id'])
            if sid in shots and object_sha(shots[sid]) != object_sha(shot):
                raise ValueError('Conflicting shot definitions: ' + sid)
            shots[sid] = shot
    return shots, pins


def validate_contract(receipt, shots):
    if receipt.get('success') is not True or receipt.get('status') != 'completed':
        raise ValueError('Render attempt has no terminal success; preserved without encoding')
    contract = receipt['render_contract']
    width, height = contract['width'], contract['height']
    if contract['fps'] != 30 or (width, height) not in ((1280, 720), (720, 1280)):
        raise ValueError('Require pilot 30 fps landscape/portrait resolution')
    counts = contract['frame_counts_by_shot']
    ids = [identifier(j['shot_id']) for j in receipt['jobs']]
    if not ids or len(set(x.casefold() for x in ids)) != len(ids) or set(ids) != set(counts):
        raise ValueError('Render jobs and per-shot frame contract disagree')
    for sid in ids:
        shot = shots[sid]
        count = counts[sid]
        if type(count) is not int or not 1 <= count <= 3600:
            raise ValueError('Invalid rendered frame count: ' + sid)
        if (shot['frame_count'] != count or shot['fps'] != 30
                or (shot['width'], shot['height']) != (width, height)
                or not math.isfinite(shot['duration_seconds'])
                or abs(shot['duration_seconds'] - count / 30) > 1e-6):
            raise ValueError('Frozen plan/render contract mismatch: ' + sid)
    return width, height, counts


def png_evidence(folder, count, width, height):
    files = sorted(folder.glob('*.png'))
    if [p.name for p in files] != [f'frame_{i:04d}.png' for i in range(count)]:
        raise ValueError('Missing/extra/noncontiguous PNG frames: ' + str(folder))
    records = []
    for file in files:
        owned(folder, file)
        with Image.open(file) as image:
            if image.size != (width, height):
                raise ValueError('PNG dimensions differ: ' + str(file))
        records.append({'name': file.name, 'bytes': file.stat().st_size, 'sha256': sha(file)})
    return files, records, object_sha(records)


def decode_video(video, width, height, count):
    # -xerror converts decoding errors into failure instead of accepting a partial file.
    decoded = subprocess.run([str(FFMPEG), '-v', 'error', '-xerror', '-nostats',
        '-i', str(video), '-map', '0:v:0', '-an', '-fps_mode', 'passthrough',
        '-progress', 'pipe:1', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    frame_rows = [int(line.split('=', 1)[1]) for line in decoded.stdout.splitlines() if line.startswith('frame=')]
    if not frame_rows or frame_rows[-1] != count or 'progress=end' not in decoded.stdout:
        raise ValueError('FFmpeg full decoded frame count differs: ' + str(video))
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    n = 0
    dimensions = set()
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            dimensions.add((frame.shape[1], frame.shape[0]))
            n += 1
    finally:
        capture.release()
    if not math.isfinite(fps) or abs(fps - 30) > 1e-8 or n != count or dimensions != {(width, height)}:
        raise ValueError('Per-frame decode contract differs: ' + str(video))
    return {'decoded_frames': n, 'fps': fps, 'measured_duration_seconds': n / fps,
            'dimensions': [width, height], 'ffmpeg_full_decode_frames': frame_rows[-1],
            'ffmpeg_full_decode_success': True}


def contact_sheet(files, indices, path, shot, portrait):
    cell = (216, 384) if portrait else (384, 216)
    width, height = cell
    image = Image.new('RGB', (5 * width, 4 * (height + 28)), (28, 28, 28))
    draw = ImageDraw.Draw(image)
    for i, frame in enumerate(indices):
        x, y = i % 5 * width, i // 5 * (height + 28)
        with Image.open(files[frame]) as source:
            image.paste(source.convert('RGB').resize(cell), (x, y + 28))
        draw.text((x + 5, y + 7), f'{frame/30:.2f}s / frame {frame}', fill='white')
    image.save(path, quality=94)


def process(attempt, plans=None, run=RUN):
    identifier(attempt)
    run = Path(run).resolve()
    plan_paths = [Path(p) for p in (plans or [run / 'camera_trial_plan_v1.json'])]
    shots, plan_pins = shot_plan(plan_paths)
    receipt_path = owned(run, run / 'render_receipts' / (attempt + '.json'))
    receipt = read(receipt_path)
    if receipt.get('attempt_id') != attempt:
        raise ValueError('Render receipt attempt identity differs')
    receipt_hash = sha(receipt_path)
    width, height, counts = validate_contract(receipt, shots)
    expected_output = owned(run, run / 'renders' / attempt)
    if Path(receipt['output_root']).resolve() != expected_output:
        raise ValueError('Render output root does not match the owned attempt')
    for name in ('videos', 'contacts', 'media_receipts'):
        owned(run, run / name).mkdir(exist_ok=True)
    results = []
    for job in receipt['jobs']:
        sid = identifier(job['shot_id'])
        count = counts[sid]
        folder = owned(run, expected_output / sid)
        files, pngs, png_sha = png_evidence(folder, count, width, height)
        video = owned(run, run / 'videos' / (sid + '.mp4'))
        media_receipt = owned(run, run / 'media_receipts' / (sid + '.json'))
        expected = {'attempt': attempt, 'shot_id': sid, 'render_receipt_sha256': receipt_hash,
                    'shot_plan_sha256': object_sha(shots[sid]), 'png_sequence_sha256': png_sha,
                    'render_job': job, 'video': video.relative_to(run).as_posix(),
                    'expected_frames': count, 'width': width, 'height': height}
        if video.exists():
            if not media_receipt.is_file():
                raise ValueError('Existing video lacks verified receipt; retained, not overwritten: ' + sid)
            evidence = read(media_receipt)
            if evidence.get('schema') != 'motion_scene_encoded_shot_v1' or evidence.get('status') != 'encoded_verified':
                raise ValueError('Existing receipt is not verified: ' + sid)
            if any(evidence.get(k) != v for k, v in expected.items()) or sha(video) != evidence['video_sha256']:
                raise ValueError('Existing media/source binding differs; retained: ' + sid)
            decode = decode_video(video, width, height, count)
            if decode != evidence['decode']:
                raise ValueError('Existing video decoded metadata differs: ' + sid)
        else:
            if media_receipt.exists():
                raise ValueError('Verified receipt exists without video; inspect before recovery: ' + sid)
            subprocess.run([str(FFMPEG), '-v', 'error', '-xerror', '-n', '-framerate', '30',
                '-i', str(folder / 'frame_%04d.png'), '-c:v', 'libx264', '-crf', '18',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)], check=True)
            decode = decode_video(video, width, height, count)
            evidence = {'schema': 'motion_scene_encoded_shot_v1', 'status': 'encoded_verified',
                        **expected, 'video_sha256': sha(video), 'decode': decode, 'png_frames': pngs}
            atomic_json(media_receipt, evidence)
        poster = owned(run, run / 'videos' / (sid + '.jpg'))
        contact = owned(run, run / 'contacts' / (sid + '_timeline.jpg'))
        indices = [round(i * (count - 1) / 19) for i in range(20)]
        with Image.open(files[0]) as image:
            image.convert('RGB').save(poster, quality=92)
        contact_sheet(files, indices, contact, sid, height > width)
        results.append({'shot_id': sid, 'video': video.relative_to(run).as_posix(),
            'poster': poster.relative_to(run).as_posix(), 'poster_sha256': sha(poster),
            'timeline_contact': contact.relative_to(run).as_posix(), 'timeline_contact_sha256': sha(contact),
            'contact_frames': indices, **decode, 'width': width, 'height': height,
            'duration_seconds': count / 30, 'sha256': evidence['video_sha256'],
            'video_sha256': evidence['video_sha256'], 'verification_status': 'encoded_verified',
            'visual_review': 'pending', 'human_acceptance': 'pending',
            'verification_receipt': media_receipt.relative_to(run).as_posix(),
            'verification_receipt_sha256': sha(media_receipt)})
        print('Verified motion/scene media ' + sid, flush=True)
    if sha(receipt_path) != receipt_hash or any(sha(pin['path']) != pin['sha256'] for pin in plan_pins):
        raise ValueError('Render receipt or frozen plan changed during encoding')
    report = {'schema': 'motion_scene_media_validation_v1', 'success': True, 'attempt': attempt,
              'videos': results, 'render_receipt_sha256': receipt_hash, 'source_plans': plan_pins,
              'visual_review': 'pending', 'human_acceptance': 'pending', 'raw_frames_deleted': False}
    destination = owned(run, run / ('media_validation_' + attempt + '.json'))
    if destination.exists():
        if read(destination) != report:
            raise ValueError('Existing final media report differs; retained without overwrite')
    else:
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt')
    parser.add_argument('--plan', type=Path, action='append', help='Repeat to include scene plans; default camera_trial_plan_v1.json')
    args = parser.parse_args()
    result = process(args.attempt, args.plan)
    print(json.dumps({'success': result['success'], 'videos': len(result['videos'])}))
