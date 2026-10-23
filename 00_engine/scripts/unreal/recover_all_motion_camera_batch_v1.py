"""Explicit one-shot missing-PNG recovery without repeating the successful jobs.

The complete subset is encoded against its UNMODIFIED original render receipt,
original attempt/raw root, and exact original jobs. A pinned selection descriptor
documents which incomplete shot is excluded; it is not a synthetic render receipt.
Only recover-missing sends UE commands, and only the coordinator invokes it.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
from PIL import Image

S = Path(__file__).resolve().parent
sys.path.insert(0, str(S))
import run_all_motion_camera_review_v1 as runner
import encode_motion_scene_pilot_v1 as encoder

RUN = runner.RUN


def immutable_json(path, value):
    if path.exists():
        if encoder.read(path) != value:
            raise ValueError('Frozen recovery evidence differs: ' + str(path))
    else:
        encoder.atomic_json(path, value)


def snapshot(attempt, missing_sid, run=RUN):
    run = Path(run).resolve()
    encoder.identifier(attempt); encoder.identifier(missing_sid)
    plan_path = run / runner.PLAN_NAME
    shots, pins = encoder.shot_plan([plan_path])
    receipt_path = run / 'render_receipts' / (attempt + '.json')
    receipt = encoder.read(receipt_path)
    width, height, counts = encoder.validate_contract(receipt, shots)
    output = encoder.owned(run, run / 'renders' / attempt)
    if receipt['attempt_id'] != attempt or Path(receipt['output_root']).resolve() != output:
        raise ValueError('Unexpected source render attempt/root')
    ids = [j['shot_id'] for j in receipt['jobs']]
    if len(ids) > 12 or ids.count(missing_sid) != 1:
        raise ValueError('Require one explicitly identified shot from a bounded original batch')
    selected = [sid for sid in ids if sid != missing_sid]
    for sid in selected:
        folder = encoder.owned(output, output / sid)
        names = [p.name for p in sorted(folder.glob('*.png'))]
        if names != [f'frame_{i:04d}.png' for i in range(counts[sid])]:
            raise ValueError('A second shot is incomplete; stop bounded one-shot recovery: ' + sid)
    folder = encoder.owned(output, output / missing_sid)
    existing = sorted(folder.glob('*.png'))
    expected_names = {f'frame_{i:04d}.png' for i in range(counts[missing_sid])}
    present_names = {p.name for p in existing}
    if present_names - expected_names or not expected_names - present_names:
        raise ValueError('Explicit failed shot must have only missing expected PNGs')
    for key in ('videos', 'media_receipts'):
        extension = '.mp4' if key == 'videos' else '.json'
        if (run / key / (missing_sid + extension)).exists():
            raise ValueError('Failed shot already has media; inspect rather than overwrite')
    evidence_dir = run / 'recovery_evidence' / attempt
    original_copy = evidence_dir / 'original_render_receipt.json'
    runner.copy_pinned(receipt_path, original_copy)
    failure = {'schema': 'all_motion_missing_png_failure_v1', 'source_attempt': attempt,
               'shot_id': missing_sid, 'render_receipt_sha256': encoder.sha(receipt_path),
               'original_render_receipt_copy': str(original_copy), 'original_render_success': receipt['success'],
               'expected_frame_count': counts[missing_sid], 'observed_frame_count': len(existing),
               'missing_frame_names': sorted(expected_names - present_names),
               'observed_png_frames': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': encoder.sha(encoder.owned(folder, p))}
                                       for p in existing],
               'policy': 'preserve original incomplete PNGs and receipt; rerender only this frozen shot'}
    failure_path = evidence_dir / 'missing_png_failure_v1.json'
    immutable_json(failure_path, failure)
    descriptor = {'schema': 'all_motion_encoding_subset_v1', 'source_attempt': attempt,
                  'render_receipt_sha256': encoder.sha(receipt_path), 'plan_sha256': encoder.sha(plan_path),
                  'included_shot_ids': selected, 'excluded_shot_ids': [missing_sid],
                  'failure_evidence': {'path': str(failure_path), 'sha256': encoder.sha(failure_path)},
                  'policy': 'encode exact original jobs against unmodified original receipt; not a new render receipt'}
    descriptor_path = evidence_dir / 'complete_subset_descriptor_v1.json'
    immutable_json(descriptor_path, descriptor)
    return descriptor_path, descriptor, shots, pins, receipt, width, height, counts


def encode_good(attempt, missing_sid, run=RUN, *, retire_raw=False):
    run = Path(run).resolve()
    report_path = run / ('media_validation_' + attempt + '_complete_subset_v1.json')
    descriptor_path = run / 'recovery_evidence' / attempt / 'complete_subset_descriptor_v1.json'
    if report_path.exists():
        report = encoder.read(report_path)
        descriptor = encoder.read(descriptor_path)
        shots, _ = encoder.shot_plan([run / runner.PLAN_NAME])
        if (report.get('success') is not True or descriptor['excluded_shot_ids'] != [missing_sid]
                or descriptor['source_attempt'] != attempt
                or descriptor['plan_sha256'] != encoder.sha(run / runner.PLAN_NAME)
                or descriptor['render_receipt_sha256'] != encoder.sha(run / 'render_receipts' / (attempt + '.json'))
                or encoder.sha(descriptor['failure_evidence']['path']) != descriptor['failure_evidence']['sha256']
                or report.get('encoding_subset') != {'path': str(descriptor_path), 'sha256': encoder.sha(descriptor_path)}
                or {r['shot_id'] for r in report['videos']} != set(descriptor['included_shot_ids'])):
            raise ValueError('Existing subset report differs')
        for row in report['videos']:
            runner.checked_media(row, shots[row['shot_id']], run)
        if retire_raw:
            runner.retire_verified_raw(attempt, report, shots, run, subset_descriptor=descriptor_path)
        return report
    descriptor_path, descriptor, shots, pins, receipt, width, height, counts = snapshot(attempt, missing_sid, run)
    receipt_path = run / 'render_receipts' / (attempt + '.json')
    receipt_hash = descriptor['render_receipt_sha256']
    output = run / 'renders' / attempt
    for name in ('videos', 'contacts', 'media_receipts'):
        (run / name).mkdir(exist_ok=True)
    results = []
    for job in receipt['jobs']:
        sid = job['shot_id']
        if sid not in descriptor['included_shot_ids']:
            continue
        count = counts[sid]
        folder = encoder.owned(output, output / sid)
        files, pngs, png_sha = encoder.png_evidence(folder, count, width, height)
        video = run / 'videos' / (sid + '.mp4')
        media_receipt = run / 'media_receipts' / (sid + '.json')
        expected = {'attempt': attempt, 'shot_id': sid, 'render_receipt_sha256': receipt_hash,
                    'shot_plan_sha256': encoder.object_sha(shots[sid]), 'png_sequence_sha256': png_sha,
                    'render_job': job, 'video': video.relative_to(run).as_posix(),
                    'expected_frames': count, 'width': width, 'height': height}
        if video.exists():
            if not media_receipt.is_file():
                raise ValueError('Existing video lacks receipt; preserved: ' + sid)
            evidence = encoder.read(media_receipt)
            if (evidence.get('schema') != 'motion_scene_encoded_shot_v1'
                    or evidence.get('status') != 'encoded_verified'
                    or any(evidence.get(k) != v for k, v in expected.items())
                    or encoder.sha(video) != evidence['video_sha256']):
                raise ValueError('Existing source/media binding differs; preserved: ' + sid)
            decode = encoder.decode_video(video, width, height, count)
            if decode != evidence['decode']:
                raise ValueError('Existing decoded metadata differs: ' + sid)
        else:
            if media_receipt.exists():
                raise ValueError('Receipt exists without video; inspect recovery: ' + sid)
            subprocess.run([str(encoder.FFMPEG), '-v', 'error', '-xerror', '-n', '-framerate', '30',
                            '-i', str(folder / 'frame_%04d.png'), '-c:v', 'libx264', '-crf', '18',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)], check=True)
            decode = encoder.decode_video(video, width, height, count)
            evidence = {'schema': 'motion_scene_encoded_shot_v1', 'status': 'encoded_verified',
                        **expected, 'video_sha256': encoder.sha(video), 'decode': decode, 'png_frames': pngs}
            encoder.atomic_json(media_receipt, evidence)
        poster = run / 'videos' / (sid + '.jpg')
        contact = run / 'contacts' / (sid + '_timeline.jpg')
        indices = [round(i * (count - 1) / 19) for i in range(20)]
        # Match the original encoder's output settings while keeping the MP4
        # and its existing media receipt unchanged.
        with Image.open(files[0]) as image:
            image.convert('RGB').save(poster, quality=92)
        encoder.contact_sheet(files, indices, contact, sid, height > width)
        row = {'shot_id': sid, 'video': video.relative_to(run).as_posix(),
               'poster': poster.relative_to(run).as_posix(), 'poster_sha256': encoder.sha(poster),
               'timeline_contact': contact.relative_to(run).as_posix(), 'timeline_contact_sha256': encoder.sha(contact),
               'contact_frames': indices, **decode, 'width': width, 'height': height,
               'duration_seconds': count / 30, 'sha256': evidence['video_sha256'],
               'video_sha256': evidence['video_sha256'], 'verification_status': 'encoded_verified',
               'visual_review': 'pending', 'human_acceptance': 'pending',
               'verification_receipt': media_receipt.relative_to(run).as_posix(),
               'verification_receipt_sha256': encoder.sha(media_receipt)}
        runner.checked_media(row, shots[sid], run)
        results.append(row)
        print('Verified original-attempt subset media ' + sid, flush=True)
    if (encoder.sha(receipt_path) != receipt_hash or any(encoder.sha(p['path']) != p['sha256'] for p in pins)
            or encoder.read(descriptor_path) != descriptor):
        raise ValueError('Original receipt, plan, or explicit recovery descriptor changed')
    report = {'schema': 'motion_scene_media_validation_v1', 'success': True, 'attempt': attempt,
              'videos': results, 'render_receipt_sha256': receipt_hash, 'source_plans': pins,
              'encoding_subset': {'path': str(descriptor_path), 'sha256': encoder.sha(descriptor_path)},
              'excluded_shot_ids': [missing_sid], 'encoding_scope': 'complete original-job subset only',
              'visual_review': 'pending', 'human_acceptance': 'pending', 'raw_frames_deleted': False}
    immutable_json(report_path, report)
    if retire_raw:
        runner.retire_verified_raw(attempt, report, shots, run, fresh_process=True, subset_descriptor=descriptor_path)
    return report


def recovery_attempt(attempt, sid, plan_hash):
    return 'allmotion115_recovery_' + plan_hash[:10] + '_' + encoder.object_sha(attempt)[:10] + '_' + encoder.object_sha(sid)[:10] + '_v1'


def recover_missing(attempt, missing_sid, run=RUN, *, retire_raw=False, timeout=7200):
    run = Path(run).resolve()
    descriptor_path = run / 'recovery_evidence' / attempt / 'complete_subset_descriptor_v1.json'
    descriptor = encoder.read(descriptor_path)
    plan_path, rows, plan_hash = runner.frozen_plan(run)
    shots = {s['shot_id']: s for s in rows}
    if (descriptor['source_attempt'] != attempt or descriptor['excluded_shot_ids'] != [missing_sid]
            or descriptor['plan_sha256'] != plan_hash
            or encoder.sha(descriptor['failure_evidence']['path']) != descriptor['failure_evidence']['sha256']
            or descriptor['render_receipt_sha256'] != encoder.sha(run / 'render_receipts' / (attempt + '.json'))):
        raise ValueError('Recovery selection/source pins changed')
    done = runner.verified_rows(shots, run)
    if not set(descriptor['included_shot_ids']).issubset(done):
        raise ValueError('Complete/verify original good subset before missing-shot render')
    recovery = recovery_attempt(attempt, missing_sid, plan_hash)
    immutable_json(run / 'recovery_evidence' / attempt / 'replacement_attempt_v1.json',
        {'schema': 'all_motion_single_shot_replacement_v1', 'original_attempt': attempt,
         'replacement_attempt': recovery, 'shot_id': missing_sid, 'plan_sha256': plan_hash,
         'encoding_subset': {'path': str(descriptor_path), 'sha256': encoder.sha(descriptor_path)}})
    report = runner.complete_batch(recovery, [shots[missing_sid]], done, plan_path, plan_hash, run, timeout=timeout)
    if retire_raw:
        if report:
            runner.retire_verified_raw(recovery, report, shots, run, fresh_process=True)
        else:
            existing = run / ('media_validation_' + recovery + '.json')
            if existing.exists():
                runner.retire_verified_raw(recovery, encoder.read(existing), shots, run)
    return {'replacement_attempt': recovery, 'shot_id': missing_sid, 'newly_encoded': report is not None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['encode-good', 'recover-missing'])
    parser.add_argument('attempt')
    parser.add_argument('--missing-shot', required=True)
    parser.add_argument('--retire-verified-raw', action='store_true')
    parser.add_argument('--timeout-seconds', type=int, default=7200)
    args = parser.parse_args()
    with runner.run_lock(RUN):
        if args.mode == 'encode-good':
            report = encode_good(args.attempt, args.missing_shot, retire_raw=args.retire_verified_raw)
            result = {'encoded_original_subset': len(report['videos']), 'excluded': report['excluded_shot_ids']}
        else:
            result = recover_missing(args.attempt, args.missing_shot, retire_raw=args.retire_verified_raw,
                                     timeout=args.timeout_seconds)
        from build_all_motion_camera_gallery_v1 import build
        result['gallery'] = build(RUN)
    print(json.dumps(result, ensure_ascii=False))
