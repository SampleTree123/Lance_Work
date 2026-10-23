"""Recoverable 1200-shot review runner, portrait first, at most 12 shots per queue.

Never re-submit an attempt with a render receipt or a durable dispatch marker.
Only --retire-verified-raw deletes PNGs, exclusively in this new run's completed
attempts after full-decode media evidence and fresh SHA checks. Old runs are read-only.
"""
from contextlib import contextmanager
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_all_motions_portrait115_20261014_v1'
OLD_RUN = S.parents[1] / 'outputs/camera_common_presets_20261014_v1'
PLAN_NAME = 'camera_trial_plan_v1.json'
sys.path.insert(0, str(S))
from encode_motion_scene_pilot_v1 import (process, read, sha, object_sha, owned,
    decode_video, validate_contract, identifier, atomic_json)


def frozen_plan(run=RUN):
    path = Path(run) / PLAN_NAME
    plan = read(path)
    rows = plan['shots']
    keys = [(s['motion_id'], s['camera_id'], s['orientation']) for s in rows]
    if (plan.get('schema') != 'camera_all_motions_portrait115_trial_v1'
            or len(rows) != 1200 or len(set(keys)) != 1200
            or len({s['shot_id'].casefold() for s in rows}) != 1200
            or len({s['motion_id'] for s in rows}) != 30
            or len({s['camera_id'] for s in rows}) != 20
            or any(s['camera_id'] == 'front_head' for s in rows)):
        raise ValueError('Require frozen 30 actions x 20 non-face cameras x 2 orientations')
    for shot in rows:
        identifier(shot['shot_id'])
        if shot['orientation'] not in ('portrait', 'landscape'):
            raise ValueError('Unknown orientation')
    return path, rows, sha(path)


def checked_media(row, shot, run=RUN, *, full_decode=False):
    """Validate complete report/receipt binding without requiring retained PNGs."""
    run = Path(run).resolve()
    sid = shot['shot_id']
    if row['shot_id'] != sid or row.get('verification_status') != 'encoded_verified':
        raise ValueError('Unverified media report: ' + sid)
    receipt_path = owned(run, run / row['verification_receipt'])
    evidence = read(receipt_path)
    if (sha(receipt_path) != row['verification_receipt_sha256']
            or evidence.get('schema') != 'motion_scene_encoded_shot_v1'
            or evidence.get('status') != 'encoded_verified'
            or evidence.get('shot_id') != sid
            or evidence.get('shot_plan_sha256') != object_sha(shot)):
        raise ValueError('Media receipt/shot pin differs: ' + sid)
    for field in ('video', 'video_sha256', 'width', 'height'):
        if row[field] != evidence[field]:
            raise ValueError('Media report differs from receipt: ' + field)
    count = shot['frame_count']
    decoded = evidence['decode']
    if (evidence['expected_frames'] != count
            or (evidence['width'], evidence['height']) != (shot['width'], shot['height'])
            or decoded.get('ffmpeg_full_decode_success') is not True
            or decoded.get('ffmpeg_full_decode_frames') != count
            or decoded.get('decoded_frames') != count
            or decoded.get('dimensions') != [shot['width'], shot['height']]
            or decoded.get('fps') != 30
            or abs(decoded['measured_duration_seconds'] - shot['duration_seconds']) > 1e-6):
        raise ValueError('Full decode contract differs: ' + sid)
    for path_key, hash_key in [('video', 'video_sha256'), ('poster', 'poster_sha256'),
                               ('timeline_contact', 'timeline_contact_sha256')]:
        path = owned(run, run / row[path_key])
        if not path.is_file() or sha(path) != row[hash_key]:
            raise ValueError('Media SHA differs: ' + str(path))
    if full_decode and decode_video(run / row['video'], shot['width'], shot['height'], count) != decoded:
        raise ValueError('Fresh decode differs: ' + sid)
    return evidence


def verified_rows(shots, run=RUN):
    found = {}
    for path in sorted(Path(run).glob('media_validation_*.json')):
        report = read(path)
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


def copy_pinned(source, destination):
    source, destination = Path(source), Path(destination)
    digest = sha(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha(destination) != digest:
            raise ValueError('Existing copy differs; preserved: ' + str(destination))
    else:
        # Copies keep the old run fully independent from the new run.
        temporary = destination.with_suffix(destination.suffix + '.copying')
        shutil.copyfile(source, temporary)
        if sha(temporary) != digest:
            raise ValueError('Copied source changed')
        temporary.replace(destination)
    return {'path': str(source.resolve()), 'sha256': digest}


def reuse_landscape(run=RUN, source=OLD_RUN):
    run, source = Path(run).resolve(), Path(source).resolve()
    plan_path, rows, plan_hash = frozen_plan(run)
    old_plan = source / 'camera_trial_plan_v2.json'
    old_shots = {s['shot_id']: s for s in read(old_plan)['shots']}
    candidates = {s['shot_id']: s for s in rows if s['orientation'] == 'landscape'
                  and s['shot_id'] in old_shots and object_sha(s) == object_sha(old_shots[s['shot_id']])}
    if len(candidates) != 60:
        raise ValueError('Require exactly 60 identical legacy landscape shot objects')
    target = run / 'media_validation_reused_landscape_v1.json'
    if target.exists():
        report = read(target)
        if {r['shot_id'] for r in report['videos']} != set(candidates) or not report.get('success'):
            raise ValueError('Existing reuse report differs')
        for row in report['videos']:
            checked_media(row, candidates[row['shot_id']], run)
        return report
    source_rows = verified_rows(candidates, source)
    if set(source_rows) != set(candidates):
        raise ValueError('Not all 60 source landscape media are verified')
    pins = [{'path': str(old_plan), 'sha256': sha(old_plan)}]
    used_attempts = set()
    for sid, row in source_rows.items():
        evidence = checked_media(row, candidates[sid], source, full_decode=True)
        used_attempts.add(evidence['attempt'])
        for key in ('video', 'poster', 'timeline_contact', 'verification_receipt'):
            pins.append(copy_pinned(owned(source, source / row[key]), owned(run, run / row[key])))
        checked_media(row, candidates[sid], run)
    for attempt in sorted(used_attempts):
        identifier(attempt)
        pins.append(copy_pinned(source / 'render_receipts' / (attempt + '.json'),
                               run / 'render_receipts' / (attempt + '.json')))
    for source_report in sorted(source.glob('media_validation_*.json')):
        report = read(source_report)
        if any(r['shot_id'] in candidates for r in report.get('videos', [])):
            pins.append(copy_pinned(source_report, run / 'reuse_source_reports' / source_report.name))
    if sha(plan_path) != plan_hash or any(sha(p['path']) != p['sha256'] for p in pins):
        raise ValueError('Reuse source or destination plan changed')
    report = {'schema': 'motion_scene_media_validation_v1', 'success': True,
              'attempt': 'reused_landscape_v1', 'videos': list(source_rows.values()),
              'source_plans': [{'path': str(plan_path), 'sha256': plan_hash}, pins[0]],
              'reuse_source_root': str(source), 'reuse_source_pins': pins,
              'visual_review': 'pending', 'human_acceptance': 'pending',
              'raw_frames_deleted': False, 'reuse_policy': 'unchanged original media and receipts'}
    atomic_json(target, report)
    return report


def attempt_batches(rows, plan_hash, batch_size):
    # Obtain the bounded 30-action upper-body review early without changing any
    # shot object, moving landscape ahead of portrait, or adding review scope.
    priority = {('MOTION_CAND_030', 'portrait', 'back_upper'),
                ('MOTION_CAND_003', 'portrait', 'side_upper'),
                ('ACT_F02_CATCH_BREATH', 'portrait', 'dolly_out_back'),
                ('MOTION_CAND_008', 'portrait', 'orbit_360'),
                ('MOTION_CAND_029', 'landscape', 'high_full'),
                ('MOTION_CAND_035', 'landscape', 'low_full')}

    def rank(shot):
        if shot.get('orientation') == 'portrait' and shot.get('camera_id') == 'front_upper':
            return 0
        if (shot.get('motion_id'), shot.get('orientation'), shot.get('camera_id')) in priority:
            return 1
        return 2

    for orientation in ('portrait', 'landscape'):
        selected = sorted([s for s in rows if s['orientation'] == orientation], key=rank)
        for index, offset in enumerate(range(0, len(selected), batch_size)):
            group = selected[offset:offset + batch_size]
            signature = object_sha([s['shot_id'] for s in group])[:10]
            attempt = f'allmotion115_{orientation}_{index:03d}_{plan_hash[:10]}_{signature}_v1'
            yield attempt, group


def remote(code, label, run=RUN):
    folder = Path(run) / 'commands'
    folder.mkdir(exist_ok=True)
    script = folder / (identifier(label) + '.py')
    script.write_text('import sys,unreal as u,importlib,json\nsys.path.insert(0,' + repr(str(S)) + ')\n'
        'import ue_all_motion_camera_review_v1 as review; importlib.reload(review)\n'
        + code + '\n', encoding='utf-8')
    with (folder / (label + '.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-X', 'utf8', str(S / 'ue_remote_exec.py'),
                                '--project', 'datatry_02', '--script', str(script)],
                                stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('UE command failed; inspect ' + str(script.with_suffix('.log')))


def wait_receipt(path, ids, timeout=7200, run=RUN):
    started = time.monotonic()
    last_notice = -60
    while True:
        if (Path(run) / 'STOP').exists():
            raise RuntimeError('STOP marker; submitted UE attempt is preserved and not resubmitted')
        if path.exists():
            receipt = read(path)
            if {j['shot_id'] for j in receipt['jobs']} != set(ids):
                raise ValueError('Render receipt selected shots differ from durable intent')
            if receipt.get('status') in ('completed', 'failed', 'setup_failed'):
                if receipt.get('status') != 'completed' or receipt.get('success') is not True:
                    raise RuntimeError('Terminal render failure; preserved without retry: ' + str(path))
                return receipt
        elapsed = time.monotonic() - started
        if elapsed > timeout:
            raise RuntimeError('Render receipt timeout; inspect UE; this attempt will not be resubmitted')
        if elapsed - last_notice >= 60:
            print(f'Waiting for {path.stem} receipt ({int(elapsed)}s)', flush=True)
            last_notice = elapsed
        time.sleep(3)


def complete_batch(attempt, group, done, plan, plan_hash, run=RUN, *, timeout=7200):
    """Return None for already verified groups; dispatch at most once per intent."""
    run = Path(run).resolve()
    receipt_path = run / 'render_receipts' / (attempt + '.json')
    intent_path = run / 'batch_intents' / (attempt + '.json')
    group_ids = {s['shot_id'] for s in group}
    pending = [s for s in group if s['shot_id'] not in done]
    if not pending:
        return None
    if sha(plan) != plan_hash:
        raise ValueError('Frozen plan changed')
    if intent_path.exists():
        intent = read(intent_path)
        if (intent['plan_sha256'] != plan_hash or intent['attempt_id'] != attempt
                or not intent['shot_ids'] or len(intent['shot_ids']) != len(set(intent['shot_ids']))
                or not set(intent['shot_ids']).issubset(group_ids)
                or not {s['shot_id'] for s in pending}.issubset(set(intent['shot_ids']))):
            raise ValueError('Batch intent differs from frozen plan/group')
        ids = intent['shot_ids']
    elif receipt_path.exists():
        # Never derive a fresh submission from an existing receipt.
        raise RuntimeError('Receipt exists without durable intent; inspect rather than resubmit')
    else:
        ids = [s['shot_id'] for s in pending]
        intent = {'schema': 'all_motion_camera_batch_intent_v1', 'attempt_id': attempt,
                  'plan_sha256': plan_hash, 'shot_ids': ids, 'orientation': group[0]['orientation'],
                  'status': 'prepare_requested'}
        atomic_json(intent_path, intent)
    if not receipt_path.exists():
        if intent['status'] in ('submission_requested', 'submitted', 'encoded_verified'):
            raise RuntimeError('Submission marker exists but receipt absent; outcome unknown; never resubmit')
        remote(f'print(json.dumps(review.prepare(u,{ids!r},{plan_hash!r})))', attempt + '_prepare', run)
        # Persist before the external call. A bridge error may still have submitted UE.
        intent['status'] = 'submission_requested'
        atomic_json(intent_path, intent)
        remote(f'print(json.dumps(review.render(u,{attempt!r},{ids!r},{group[0]["width"]},'
               f'{group[0]["height"]},{plan_hash!r})))', attempt + '_render', run)
        intent['status'] = 'submitted'
        atomic_json(intent_path, intent)
    wait_receipt(receipt_path, ids, timeout, run)
    report = process(attempt, [plan], run=run)
    if {r['shot_id'] for r in report['videos']} != set(ids):
        raise ValueError('Encoded batch does not cover durable intent')
    intent['status'] = 'encoded_verified'
    atomic_json(intent_path, intent)
    return report


def retire_verified_raw(attempt, report, shots, run=RUN, *, fresh_process=False, subset_descriptor=None):
    """Two-phase PNG retirement; no recursion, no other extension, no old-run writes."""
    identifier(attempt)
    run = Path(run).resolve()
    if RUN.is_symlink():
        raise ValueError('The explicit new RUN cannot be a symlink')
    if run != RUN.resolve():
        raise ValueError('Raw retirement is restricted to the explicit new RUN')
    renders = owned(run, run / 'renders')
    expected = owned(renders, renders / attempt)
    if expected.parent != renders or expected == renders or (run / 'renders').is_symlink():
        raise ValueError('Raw attempt path is not an owned immediate child')
    receipt_path = run / 'render_receipts' / (attempt + '.json')
    receipt = read(receipt_path)
    if (receipt['attempt_id'] != attempt or Path(receipt['output_root']).resolve() != expected
            or report.get('success') is not True or report.get('attempt') != attempt
            or report.get('render_receipt_sha256') != sha(receipt_path)):
        raise ValueError('Raw retirement requires bound completed attempt/report')
    validate_contract(receipt, shots)
    jobs = {j['shot_id'] for j in receipt['jobs']}
    rows = {r['shot_id']: r for r in report['videos']}
    suffix = ''
    if subset_descriptor is not None:
        descriptor_path = owned(run, subset_descriptor)
        descriptor_path.relative_to(run / 'recovery_evidence')
        descriptor = read(descriptor_path)
        pin = {'path': str(descriptor_path), 'sha256': sha(descriptor_path)}
        selected = set(descriptor['included_shot_ids'])
        excluded = set(descriptor['excluded_shot_ids'])
        if (descriptor.get('schema') != 'all_motion_encoding_subset_v1'
                or descriptor['source_attempt'] != attempt
                or descriptor['render_receipt_sha256'] != sha(receipt_path)
                or descriptor['plan_sha256'] != sha(run / PLAN_NAME)
                or not selected or not excluded or selected & excluded
                or selected | excluded != jobs or report.get('encoding_subset') != pin):
            raise ValueError('Raw subset retirement requires exact original receipt and explicit selection')
        jobs = selected
        suffix = '_subset_' + object_sha(sorted(selected))[:10]
    if len(rows) != len(report['videos']) or set(rows) != jobs:
        raise ValueError('Raw retirement requires all batch media')
    retire_path = run / 'raw_retirements' / (attempt + suffix + '.json')
    marker = read(retire_path) if retire_path.exists() else None
    report_sha = object_sha(report)
    if marker and (marker['report_sha256'] != report_sha or marker['render_receipt_sha256'] != sha(receipt_path)):
        raise ValueError('Retirement evidence changed')
    if marker and marker['status'] == 'completed':
        return marker
    targets = []
    for sid, row in rows.items():
        evidence = checked_media(row, shots[sid], run, full_decode=not fresh_process)
        if evidence['attempt'] != attempt or evidence['render_receipt_sha256'] != sha(receipt_path):
            raise ValueError('Media belongs to another attempt')
        if evidence['render_job'] != next(j for j in receipt['jobs'] if j['shot_id'] == sid):
            raise ValueError('Media render job differs from terminal receipt')
        if object_sha(evidence['png_frames']) != evidence['png_sequence_sha256']:
            raise ValueError('PNG frame manifest digest differs')
        folder = owned(expected, expected / identifier(sid))
        if folder.parent != expected or (expected / sid).is_symlink():
            raise ValueError('Raw shot folder escaped attempt')
        names = {record['name'] for record in evidence['png_frames']}
        if (len(evidence['png_frames']) != shots[sid]['frame_count']
                or names != {f'frame_{i:04d}.png' for i in range(shots[sid]['frame_count'])}):
            raise ValueError('Raw receipt does not cover exact frame sequence')
        present = {p.name for p in folder.glob('*.png')}
        if present - names or (not marker and present != names):
            raise ValueError('Raw files differ before retirement')
        for record in evidence['png_frames']:
            name = record['name']
            if Path(name).name != name or Path(name).suffix != '.png':
                raise ValueError('Unsafe raw PNG evidence path')
            target = owned(folder, folder / name)
            if target.parent != folder or (folder / name).is_symlink():
                raise ValueError('Raw PNG resolved outside its shot folder')
            if target.exists():
                if target.stat().st_size != record['bytes'] or sha(target) != record['sha256']:
                    raise ValueError('Raw PNG differs; entire batch preserved')
                targets.append(target)
    marker = {'schema': 'all_motion_verified_raw_retirement_v1', 'attempt_id': attempt,
              'status': 'deleting', 'report_sha256': report_sha,
              'render_receipt_sha256': sha(receipt_path), 'output_root': str(expected),
              'policy': 'only verified PNG frames; preserve media and receipts',
              'frames_expected': sum(shots[s]['frame_count'] for s in jobs)}
    atomic_json(retire_path, marker)
    for target in targets:
        # Re-resolve immediately before unlink; no directory deletion or cross-shell action.
        resolved = owned(expected, target)
        if resolved != target or resolved.suffix != '.png' or target.is_symlink():
            raise ValueError('Raw target changed before unlink')
        target.unlink()
    marker['status'] = 'completed'
    atomic_json(retire_path, marker)
    return marker


@contextmanager
def run_lock(run):
    path = Path(run) / 'runner.lock'
    with path.open('a+b') as stream:
        stream.seek(0)
        if not stream.read(1):
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def run_batches(batch_size=12, *, retire_raw=False, max_batches=None, timeout=7200):
    plan, rows, plan_hash = frozen_plan()
    shots = {s['shot_id']: s for s in rows}
    with run_lock(RUN):
        schedule = list(attempt_batches(rows, plan_hash, batch_size))
        schedule_path = RUN / 'batch_schedule_v1.json'
        schedule_data = {'schema': 'all_motion_camera_batch_schedule_v1', 'plan_sha256': plan_hash,
                         'batch_size': batch_size, 'attempts': [{'attempt_id': a,
                          'shot_ids': [s['shot_id'] for s in g]} for a, g in schedule]}
        if schedule_path.exists() and read(schedule_path) != schedule_data:
            raise ValueError('Frozen batch schedule differs; keep original batch size')
        if not schedule_path.exists():
            atomic_json(schedule_path, schedule_data)
        done = verified_rows(shots)
        count = 0
        from build_all_motion_camera_gallery_v1 import build
        for attempt, group in schedule:
            if (RUN / 'STOP').exists():
                raise RuntimeError('STOP marker')
            existing_report = RUN / ('media_validation_' + attempt + '.json')
            if all(s['shot_id'] in done for s in group):
                if retire_raw and existing_report.exists():
                    retire_verified_raw(attempt, read(existing_report), shots)
                continue
            receipt_path = RUN / 'render_receipts' / (attempt + '.json')
            if not receipt_path.exists() and shutil.disk_usage(RUN.anchor).free < 25 * 1024**3:
                raise RuntimeError('Insufficient disk headroom; preserve pending attempt')
            report = complete_batch(attempt, group, done, plan, plan_hash, timeout=timeout)
            if report:
                for row in report['videos']:
                    checked_media(row, shots[row['shot_id']])
                    done[row['shot_id']] = row
                if retire_raw:
                    retire_verified_raw(attempt, report, shots, fresh_process=True)
                atomic_json(RUN / 'batch_progress.json', {'plan_sha256': plan_hash,
                    'last_attempt': attempt, 'verified': len(done), 'target': 1200})
                result = build(RUN)
                print(json.dumps({'attempt': attempt, 'verified': len(done), 'target': 1200,
                                  'gallery': result}, ensure_ascii=False), flush=True)
                count += 1
                if max_batches is not None and count >= max_batches:
                    break
        return {'verified': len(done), 'target': 1200, 'plan_sha256': plan_hash}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['run', 'reuse-landscape', 'status'])
    parser.add_argument('--batch-size', type=int, default=12)
    parser.add_argument('--retire-verified-raw', action='store_true')
    parser.add_argument('--max-batches', type=int)
    parser.add_argument('--timeout-seconds', type=int, default=7200)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 12 or (args.max_batches is not None and args.max_batches < 1):
        raise ValueError('Batch size must be 1..12 and max-batches positive')
    if args.mode == 'run':
        result = run_batches(args.batch_size, retire_raw=args.retire_verified_raw,
                             max_batches=args.max_batches, timeout=args.timeout_seconds)
    elif args.mode == 'reuse-landscape':
        with run_lock(RUN):
            report = reuse_landscape()
            from build_all_motion_camera_gallery_v1 import build
            gallery = build(RUN)
        result = {'reused': len(report['videos']), 'gallery': gallery}
    else:
        plan, rows, digest = frozen_plan()
        result = {'verified': len(verified_rows({s['shot_id']: s for s in rows})),
                  'target': 1200, 'plan_sha256': digest}
    print(json.dumps(result, ensure_ascii=False))
