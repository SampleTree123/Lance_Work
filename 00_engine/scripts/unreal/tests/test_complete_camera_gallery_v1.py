"""Gallery must not label unverified or mismatched media as playable."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_complete_camera_gallery_v1 as gallery


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def shot():
    return {'shot_id': 'cam_test', 'camera_label': '正面全身',
            'motion_label': '弯腰伸展', 'trajectory_sha256': 'trajectory'}


def test_missing_receipt_stays_pending_even_if_video_exists(tmp_path):
    (tmp_path / 'videos').mkdir()
    (tmp_path / 'videos/cam_test.mp4').write_bytes(b'unverified')
    row = gallery.media_row(tmp_path, shot())
    assert row['playable'] is False
    assert row['video'] is None


@pytest.mark.parametrize('invalid', ['hash', 'duration', 'shot'])
def test_reject_bad_receipt(tmp_path, invalid):
    video = tmp_path / 'videos/cam_test.mp4'
    video.parent.mkdir()
    video.write_bytes(b'fixture')
    receipt = {'status': 'encoded_verified', 'shot_id': 'cam_test',
               'video': 'videos/cam_test.mp4', 'video_sha256': hashlib.sha256(b'fixture').hexdigest(),
               'decode': {'decoded_frames': 300, 'fps': 30, 'measured_duration_seconds': 10}}
    if invalid == 'hash':
        receipt['video_sha256'] = 'wrong'
    elif invalid == 'duration':
        receipt['decode']['measured_duration_seconds'] = 5
    else:
        receipt['shot_id'] = 'different_shot'
    write(tmp_path / 'media_receipts/cam_test.json', receipt)
    with pytest.raises(ValueError):
        gallery.media_row(tmp_path, shot())


def test_complete_matrix_and_pending_counts(tmp_path):
    shots = []
    for action in ('stand', 'bend', 'walk', 'turn', 'dance', 'thinking', 'curious'):
        for i in range(21):
            shots.append(dict(shot(), shot_id=f'cam_{action}_{i}', stable_preset_id=f'preset_{i}', stable_action_id=action))
    write(tmp_path / 'expansion_plan_v1.json', {'shots': shots})
    result = gallery.build(tmp_path)
    assert result['clips'] == 147 and result['playable'] == 0
    manifest = gallery.read(tmp_path / 'review_delivery_manifest_v1.json')
    assert len(manifest['groups']) == 21
    assert all(len(g['clips']) == 7 for g in manifest['groups'])
    assert manifest['human_acceptance'] == 'pending'
    shots[-1]['stable_action_id'] = 'bend'
    write(tmp_path / 'expansion_plan_v1.json', {'shots': shots})
    with pytest.raises(ValueError, match='Duplicate action'):
        gallery.build(tmp_path)


def test_new_launcher_isolated_and_reuses_range_handler():
    import open_complete_camera_gallery_v1 as launcher
    from open_stable_camera_gallery_v1 import RangeHandler
    assert launcher.PORT == 8879
    assert launcher.RangeHandler is RangeHandler
    assert launcher.RUN.name == 'camera_complete_angles_20261010_v1'
