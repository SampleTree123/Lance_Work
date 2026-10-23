"""Bounded real-encoder tests for explicit original-job subset recovery."""
from pathlib import Path
import json
import sys
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recover_all_motion_camera_batch_v1 as recovery
import encode_motion_scene_pilot_v1 as encoder
import run_all_motion_camera_review_v1 as runner


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def interrupted_case(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'RUN', tmp_path)
    attempt = 'original_batch'
    shots = []
    for sid in ('good_before', 'missing_one', 'good_after'):
        folder = tmp_path / 'renders' / attempt / sid
        folder.mkdir(parents=True)
        for i in range(3):
            if sid == 'missing_one' and i == 1:
                continue
            Image.new('RGB', (1280, 720), (i * 30, 80, 110)).save(folder / f'frame_{i:04d}.png')
        shots.append({'shot_id': sid, 'width': 1280, 'height': 720, 'fps': 30, 'frame_count': 3,
                      'duration_seconds': .1, 'orientation': 'landscape'})
    receipt = {'attempt_id': attempt, 'success': True, 'status': 'completed',
               'output_root': str(tmp_path / 'renders' / attempt),
               'jobs': [{'shot_id': s['shot_id'], 'map': 'm', 'sequence': 's'} for s in shots],
               'render_contract': {'width': 1280, 'height': 720, 'fps': 30,
                                   'frame_counts_by_shot': {s['shot_id']: 3 for s in shots}}}
    write(tmp_path / 'render_receipts' / (attempt + '.json'), receipt)
    write(tmp_path / runner.PLAN_NAME, {'shots': shots})
    with pytest.raises(ValueError, match='Missing/extra/noncontiguous'):
        encoder.process(attempt, run=tmp_path)
    return attempt, {s['shot_id']: s for s in shots}


def test_good_subset_keeps_existing_video_and_original_receipt_then_retires_only_good_raw(tmp_path, monkeypatch):
    attempt, shots = interrupted_case(tmp_path, monkeypatch)
    original_receipt = tmp_path / 'render_receipts' / (attempt + '.json')
    pins = {p: encoder.sha(p) for p in (original_receipt,
            tmp_path / 'videos/good_before.mp4', tmp_path / 'media_receipts/good_before.json')}
    report = recovery.encode_good(attempt, 'missing_one', tmp_path, retire_raw=True)
    assert {r['shot_id'] for r in report['videos']} == {'good_before', 'good_after'}
    assert all(encoder.sha(p) == digest for p, digest in pins.items())
    assert len(list((tmp_path / 'renders/original_batch/missing_one').glob('*.png'))) == 2
    assert not list((tmp_path / 'renders/original_batch/good_before').glob('*.png'))
    assert not list((tmp_path / 'renders/original_batch/good_after').glob('*.png'))
    failure = encoder.read(tmp_path / 'recovery_evidence/original_batch/missing_png_failure_v1.json')
    assert failure['missing_frame_names'] == ['frame_0001.png'] and failure['original_render_success'] is True
    for row in report['videos']:
        media = encoder.read(tmp_path / row['verification_receipt'])
        assert media['attempt'] == attempt and media['render_receipt_sha256'] == pins[original_receipt]
    assert recovery.encode_good(attempt, 'missing_one', tmp_path, retire_raw=True) == report


def test_recovery_dispatch_selects_exactly_the_missing_frozen_shot(tmp_path, monkeypatch):
    attempt, shots = interrupted_case(tmp_path, monkeypatch)
    recovery.encode_good(attempt, 'missing_one', tmp_path)
    plan_path = tmp_path / runner.PLAN_NAME
    digest = encoder.sha(plan_path)
    monkeypatch.setattr(runner, 'frozen_plan', lambda run: (plan_path, list(shots.values()), digest))
    calls = []
    monkeypatch.setattr(runner, 'complete_batch', lambda *a, **k: calls.append(a) or None)
    result = recovery.recover_missing(attempt, 'missing_one', tmp_path)
    assert len(calls) == 1 and calls[0][1] == [shots['missing_one']]
    assert result['replacement_attempt'] == recovery.recovery_attempt(attempt, 'missing_one', digest)
    assert result['replacement_attempt'] != attempt


def test_second_missing_shot_blocks_recovery_before_new_media(tmp_path, monkeypatch):
    attempt, shots = interrupted_case(tmp_path, monkeypatch)
    (tmp_path / 'renders/original_batch/good_after/frame_0001.png').unlink()
    with pytest.raises(ValueError, match='second shot is incomplete'):
        recovery.encode_good(attempt, 'missing_one', tmp_path)
    assert not (tmp_path / 'videos/good_after.mp4').exists()


def test_unselected_missing_raw_cannot_be_retired_by_subset_descriptor(tmp_path, monkeypatch):
    attempt, shots = interrupted_case(tmp_path, monkeypatch)
    report = recovery.encode_good(attempt, 'missing_one', tmp_path)
    descriptor_path = tmp_path / 'recovery_evidence/original_batch/complete_subset_descriptor_v1.json'
    descriptor = encoder.read(descriptor_path)
    descriptor['included_shot_ids'].append('missing_one')
    write(descriptor_path, descriptor)
    with pytest.raises(ValueError, match='exact original receipt'):
        runner.retire_verified_raw(attempt, report, shots, tmp_path, fresh_process=True,
                                   subset_descriptor=descriptor_path)
    assert len(list((tmp_path / 'renders/original_batch/good_before').glob('*.png'))) == 3
    assert len(list((tmp_path / 'renders/original_batch/missing_one').glob('*.png'))) == 2
