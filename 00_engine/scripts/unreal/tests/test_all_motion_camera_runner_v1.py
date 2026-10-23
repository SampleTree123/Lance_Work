"""Bounded offline recovery and new-run-only raw retirement tests."""
from pathlib import Path
import json
import sys
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_all_motion_camera_review_v1 as runner
import encode_motion_scene_pilot_v1 as encoder
import ue_all_motion_camera_review_v1 as ue_adapter


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def simple_batch(tmp_path):
    group = [{'shot_id': 'shot_1', 'orientation': 'portrait', 'width': 720, 'height': 1280}]
    plan = tmp_path / 'plan.json'
    write(plan, {'shots': group})
    intent = {'schema': 'all_motion_camera_batch_intent_v1', 'attempt_id': 'batch_1',
              'plan_sha256': runner.sha(plan), 'shot_ids': ['shot_1'], 'status': 'submitted'}
    write(tmp_path / 'batch_intents/batch_1.json', intent)
    return group, plan


@pytest.mark.parametrize('state', ['submitted', 'completed'])
def test_resume_receipt_never_resubmits(tmp_path, monkeypatch, state):
    group, plan = simple_batch(tmp_path)
    write(tmp_path / 'render_receipts/batch_1.json', {'status': state, 'jobs': [{'shot_id': 'shot_1'}]})
    calls = []
    monkeypatch.setattr(runner, 'remote', lambda *a: pytest.fail('Resume must not submit any UE command'))
    monkeypatch.setattr(runner, 'wait_receipt', lambda *a: calls.append('wait') or {})
    monkeypatch.setattr(runner, 'process', lambda *a, **k: calls.append('encode') or {'videos': [{'shot_id': 'shot_1'}]})
    runner.complete_batch('batch_1', group, {}, plan, runner.sha(plan), tmp_path)
    assert calls == ['wait', 'encode']


def test_unknown_submission_outcome_never_resubmits(tmp_path, monkeypatch):
    group, plan = simple_batch(tmp_path)
    monkeypatch.setattr(runner, 'remote', lambda *a: pytest.fail('Unknown dispatch must not be retried'))
    with pytest.raises(RuntimeError, match='never resubmit'):
        runner.complete_batch('batch_1', group, {}, plan, runner.sha(plan), tmp_path)


def test_dispatch_marker_precedes_render_command(tmp_path, monkeypatch):
    group, plan = simple_batch(tmp_path)
    (tmp_path / 'batch_intents/batch_1.json').unlink()
    calls = []

    def remote(code, label, run):
        calls.append(label)
        if label.endswith('_render'):
            assert runner.read(tmp_path / 'batch_intents/batch_1.json')['status'] == 'submission_requested'
            raise RuntimeError('bridge interrupted after possible submission')

    monkeypatch.setattr(runner, 'remote', remote)
    with pytest.raises(RuntimeError, match='bridge interrupted'):
        runner.complete_batch('batch_1', group, {}, plan, runner.sha(plan), tmp_path)
    with pytest.raises(RuntimeError, match='never resubmit'):
        runner.complete_batch('batch_1', group, {}, plan, runner.sha(plan), tmp_path)
    assert calls == ['batch_1_prepare', 'batch_1_render']


def encoded_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'RUN', tmp_path)
    attempt, sid, count = 'test_attempt', 'test_shot', 3
    folder = tmp_path / 'renders' / attempt / sid
    folder.mkdir(parents=True)
    for i in range(count):
        Image.new('RGB', (1280, 720), (i * 30, 70, 100)).save(folder / f'frame_{i:04d}.png')
    shot = {'shot_id': sid, 'width': 1280, 'height': 720, 'fps': 30,
            'frame_count': count, 'duration_seconds': count / 30}
    receipt = {'attempt_id': attempt, 'status': 'completed', 'success': True,
               'output_root': str(folder.parent), 'jobs': [{'shot_id': sid, 'map': 'm', 'sequence': 's'}],
               'render_contract': {'width': 1280, 'height': 720, 'fps': 30, 'frame_counts_by_shot': {sid: count}}}
    write(tmp_path / 'render_receipts' / (attempt + '.json'), receipt)
    write(tmp_path / 'camera_trial_plan_v1.json', {'shots': [shot]})
    report = encoder.process(attempt, run=tmp_path)
    return attempt, sid, folder, {sid: shot}, report


def test_verified_retirement_only_deletes_owned_pngs(tmp_path, monkeypatch):
    attempt, sid, folder, shots, report = encoded_batch(tmp_path, monkeypatch)
    preserved = folder / 'keep.txt'; preserved.write_text('keep', encoding='utf-8')
    old = tmp_path / 'old_run/renders/old/frame_0000.png'
    old.parent.mkdir(parents=True); old.write_bytes(b'old')
    row = report['videos'][0]
    pins = {key: runner.sha(tmp_path / row[key]) for key in ('video', 'poster', 'timeline_contact', 'verification_receipt')}
    result = runner.retire_verified_raw(attempt, report, shots, tmp_path, fresh_process=True)
    assert result['status'] == 'completed' and not list(folder.glob('*.png'))
    assert preserved.read_text() == 'keep' and old.read_bytes() == b'old'
    assert all(runner.sha(tmp_path / row[key]) == digest for key, digest in pins.items())
    assert runner.retire_verified_raw(attempt, report, shots, tmp_path) == result


def test_bad_raw_pin_preserves_entire_batch(tmp_path, monkeypatch):
    attempt, sid, folder, shots, report = encoded_batch(tmp_path, monkeypatch)
    (folder / 'frame_0002.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='entire batch preserved'):
        runner.retire_verified_raw(attempt, report, shots, tmp_path, fresh_process=True)
    assert len(list(folder.glob('*.png'))) == 3


@pytest.mark.parametrize('change', ['failed', 'outside', 'wrong_run', 'missing_media'])
def test_retirement_boundary_failure_preserves_pngs(tmp_path, monkeypatch, change):
    attempt, sid, folder, shots, report = encoded_batch(tmp_path, monkeypatch)
    receipt_path = tmp_path / 'render_receipts' / (attempt + '.json')
    if change in ('failed', 'outside'):
        receipt = runner.read(receipt_path)
        if change == 'failed':
            receipt.update(status='failed', success=False)
        else:
            receipt['output_root'] = str(tmp_path / 'old_run/renders' / attempt)
        write(receipt_path, receipt)
        report['render_receipt_sha256'] = runner.sha(receipt_path)
    elif change == 'wrong_run':
        monkeypatch.setattr(runner, 'RUN', tmp_path / 'actual_new_run')
    else:
        (tmp_path / report['videos'][0]['poster']).unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        runner.retire_verified_raw(attempt, report, shots, tmp_path, fresh_process=True)
    assert len(list(folder.glob('*.png'))) == 3


def test_stable_batch_ids_and_portrait_first():
    rows = [{'shot_id': f'{o}_{i}', 'orientation': o} for o in ('landscape', 'portrait') for i in range(25)]
    a = list(runner.attempt_batches(rows, 'a' * 64, 12))
    assert a == list(runner.attempt_batches(rows, 'a' * 64, 12))
    assert [g[0]['orientation'] for _, g in a] == ['portrait'] * 3 + ['landscape'] * 3
    assert max(len(g) for _, g in a) == 12


def test_review_camera_exception_is_local_frozen_and_finite(tmp_path, monkeypatch):
    monkeypatch.setattr(ue_adapter, 'RUN', tmp_path)
    frame = {'t': 0, 'position': [1, 2, 3], 'rotation_pitch_yaw_roll': [0, 90, 0],
             'horizontal_fov_degrees': 35, 'look_at': [0, 0, 1]}
    shot = {'shot_id': 'controlled_review', 'status': 'geometry_review_required', 'fps': 30,
            'frame_count': 1, 'duration_seconds': 1 / 30, 'frames': [frame],
            'endpoint_validation_frame': dict(frame, t=1 / 30)}
    plan_path = tmp_path / ue_adapter.PLAN_NAME
    write(plan_path, {'schema': 'camera_all_motions_portrait115_trial_v1', 'shots': [shot]})
    builder = ue_adapter.adapter().configured_module('ue_motion_scene_sequence_v1')
    assert len(builder.key_rows(shot)) == 2
    assert shot['status'] == 'geometry_review_required'
    assert runner.read(plan_path)['shots'][0]['status'] == 'geometry_review_required'
    mismatched = dict(shot, duration_seconds=2)
    with pytest.raises(ValueError, match='exact frozen'):
        builder.key_rows(mismatched)
    shot['frames'][0]['look_at'][0] = float('nan')
    write(plan_path, {'schema': 'camera_all_motions_portrait115_trial_v1', 'shots': [shot]})
    with pytest.raises(ValueError, match='exact frozen|Nonfinite'):
        builder.key_rows(shot)
