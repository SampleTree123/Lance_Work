"""Run only the approved 120 common-preset samples. Owner: SCENE_CAMERA_SEQUENCE."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time
import shutil

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_common_presets_20261014_v1'
sys.path.insert(0, str(S))
from encode_motion_scene_pilot_v1 import process, read, sha, object_sha


def remote(code, label):
    folder = RUN / 'commands'
    folder.mkdir(exist_ok=True)
    path = folder / (label + '.py')
    path.write_text('import sys,unreal as u\nsys.path.insert(0,' + repr(str(S)) + ')\n'
                    'import ue_common_camera_review_v1 as review; import importlib; importlib.reload(review)\n' + code + '\n', encoding='utf-8')
    with (folder / (label + '.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-X', 'utf8', str(S / 'ue_remote_exec.py'),
                                 '--project', 'datatry_02', '--script', str(path)], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('UE command failed: ' + str(path))


def verified_done(shots):
    done = set()
    for path in RUN.glob('media_validation_*.json'):
        report = read(path)
        if not report.get('success'):
            continue
        for row in report['videos']:
            sid = row['shot_id']
            if sid not in shots:
                continue
            receipt_path = RUN / row['verification_receipt']
            proof = read(receipt_path)
            assert sha(receipt_path) == row['verification_receipt_sha256']
            assert proof['shot_plan_sha256'] == object_sha(shots[sid])
            assert sha(RUN / row['video']) == row['video_sha256']
            done.add(sid)
    return done


def run(mode, batch_size):
    plan = RUN / 'camera_trial_plan_v2.json'
    rows = read(plan)['shots']
    assert len(rows) == 120 and all(s['camera_id'] != 'front_head' for s in rows)
    shots = {s['shot_id']: s for s in rows}
    done = verified_done(shots)
    if mode == 'smoke':
        rows = [s for s in rows if s['camera_id'] in ('front_full', 'front_upper')]
        assert len(rows) == 12
    else:
        gate = read(RUN / 'smoke_visual_review.json')
        assert gate['proceed_to_remaining'] is True and gate['plan_sha256'] == sha(plan)
    groups = []
    for orientation in ('portrait', 'landscape'):
        oriented = [s for s in rows if s['orientation'] == orientation and s['shot_id'] not in done]
        groups += [oriented[i:i + batch_size] for i in range(0, len(oriented), batch_size)]
    for i, group in enumerate(groups):
        if (RUN / 'STOP').exists():
            raise RuntimeError('User stop marker')
        if shutil.disk_usage('D:/').free < 25 * 1024**3:
            raise RuntimeError('Insufficient disk headroom')
        prefix = f'{mode}_{i:03d}_{group[0]["orientation"]}'
        attempt = prefix + '_v2'
        if (RUN / 'render_receipts' / (attempt + '.json')).exists():
            attempt = prefix + '_v2_resume_' + str(int(time.time()))
        ids = [s['shot_id'] for s in group]
        remote(f'review.prepare(u,{ids!r}); print("prepare completed")', attempt + '_prepare')
        remote(f'review.render(u,{attempt!r},{ids!r},{group[0]["width"]},{group[0]["height"]}); print("render submitted")', attempt + '_render')
        receipt = RUN / 'render_receipts' / (attempt + '.json')
        started = time.monotonic()
        while True:
            state = read(receipt)
            if state.get('status') in ('completed', 'failed', 'setup_failed'):
                if not state.get('success'):
                    raise RuntimeError('Render failed: ' + attempt)
                break
            if time.monotonic() - started > 7200:
                raise RuntimeError('Render timeout; inspect editor')
            time.sleep(3)
        report = process(attempt, [plan], run=RUN)
        done.update(r['shot_id'] for r in report['videos'])
        (RUN / 'batch_progress.json').write_text(json.dumps({'mode': mode, 'last_attempt': attempt,
            'verified': len(done), 'target': 120}, indent=2), encoding='utf-8')
        subprocess.run([sys.executable, '-X', 'utf8', str(S / 'build_common_camera_gallery_v1.py'),
                        '--run-root', str(RUN)], check=True)
        print(f'{attempt}: {len(done)}/120 verified', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['smoke', 'remaining'])
    parser.add_argument('--batch-size', type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 12:
        raise ValueError('Batch size must be 1..12')
    run(args.mode, args.batch_size)
