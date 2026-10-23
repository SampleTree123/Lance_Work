"""Bounded face pilot/all runner reusing verified render and encoding contracts."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_face_closeup_20261014_v1'
PILOTS = ('MOTION_CAND_002', 'MOTION_CAND_003', 'MOTION_CAND_030', 'MOTION_CAND_008', 'MOTION_CAND_029')
spec = importlib.util.spec_from_file_location('_face_runner_base', S / 'run_all_motion_camera_review_v1.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.RUN = RUN


def remote(code, label, run=RUN):
    folder = Path(run) / 'commands'
    folder.mkdir(exist_ok=True)
    script = folder / (base.identifier(label) + '.py')
    script.write_text('import sys,unreal as u,importlib,json\nsys.path.insert(0,' + repr(str(S)) + ')\n'
        'import ue_face_closeup_camera_review_v1 as review; importlib.reload(review)\n'
        'from pathlib import Path\nreview.RUN=Path(' + repr(str(Path(run).resolve())) + ')\n'
        'review.ASSETS="/Game/DataMake/Validation/FaceCloseupCamera20261014_' + Path(run).name.rsplit('_',1)[-1] + '"\n'
        + code + '\n', encoding='utf-8')
    with script.with_suffix('.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-X', 'utf8', str(S / 'ue_remote_exec.py'),
            '--project', 'datatry_02', '--script', str(script)], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('UE operation failed; inspect ' + str(script.with_suffix('.log')))


base.remote = remote


def frozen_plan():
    path = RUN / 'camera_trial_plan_v1.json'
    plan = base.read(path)
    rows = plan['shots']
    keys = {(s['motion_id'], s['orientation'], s['camera_id']) for s in rows}
    if (plan.get('schema') != 'camera_face_closeup_trial_v1' or len(rows) != 60 or len(keys) != 60
            or len({s['motion_id'] for s in rows}) != 30
            or any(s['camera_id'] != 'front_head' for s in rows)
            or {s['orientation'] for s in rows} != {'landscape', 'portrait'}):
        raise ValueError('Require 30 actions x2 face closeups')
    return path, rows, base.sha(path)


def schedule(rows, digest):
    for stage in ('pilot', 'remaining'):
        for orientation in ('portrait', 'landscape'):
            selected = [s for s in rows if s['orientation'] == orientation
                        and (s['motion_id'] in PILOTS) == (stage == 'pilot')]
            for index, offset in enumerate(range(0, len(selected), 5)):
                group = selected[offset:offset+5]
                attempt = f'faceclose_{stage}_{orientation}_{index:02d}_{digest[:10]}_v1'
                yield stage, attempt, group


def run(stage, retire=False):
    path, rows, digest = frozen_plan()
    shots = {s['shot_id']:s for s in rows}
    with base.run_lock(RUN):
        groups = list(schedule(rows, digest))
        descriptor = {'schema':'face_camera_batch_schedule_v1', 'plan_sha256':digest,
            'batches':[{'stage':st,'attempt':a,'shot_ids':[s['shot_id'] for s in g]} for st,a,g in groups]}
        schedule_path = RUN / 'batch_schedule_v1.json'
        if schedule_path.exists() and base.read(schedule_path) != descriptor:
            raise ValueError('Frozen schedule changed')
        base.atomic_json(schedule_path, descriptor)
        done = base.verified_rows(shots, RUN)
        for st, attempt, group in groups:
            if stage == 'pilot' and st != 'pilot':
                continue
            if (RUN / 'STOP').exists():
                raise RuntimeError('STOP requested')
            if all(s['shot_id'] in done for s in group):
                continue
            if shutil.disk_usage(RUN.anchor).free < 25*1024**3:
                raise RuntimeError('Insufficient disk headroom')
            report = base.complete_batch(attempt, group, done, path, digest, RUN)
            for row in report['videos']:
                base.checked_media(row, shots[row['shot_id']], RUN)
                done[row['shot_id']] = row
            if retire:
                base.retire_verified_raw(attempt, report, shots, RUN, fresh_process=True)
            base.atomic_json(RUN / 'batch_progress.json', {'verified':len(done),'target':60,'last_attempt':attempt,'plan_sha256':digest})
            from build_face_closeup_camera_gallery_v1 import build
            build(RUN)
            print(json.dumps({'verified':len(done),'target':60,'attempt':attempt}), flush=True)
        return {'verified':len(done),'target':60,'stage':stage,'plan_sha256':digest}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['pilot','all','status'])
    parser.add_argument('--retire-verified-raw',action='store_true')
    parser.add_argument('--revision',choices=['v1','v2'],default='v1')
    args = parser.parse_args()
    RUN = S.parents[1] / ('outputs/camera_face_closeup_20261014_' + args.revision)
    base.RUN = RUN
    if args.stage == 'status':
        _,rows,digest = frozen_plan()
        result = {'verified':len(base.verified_rows({s['shot_id']:s for s in rows},RUN)), 'target':60,'plan_sha256':digest}
    else:
        result = run(args.stage,args.retire_verified_raw)
    print(json.dumps(result),flush=True)
