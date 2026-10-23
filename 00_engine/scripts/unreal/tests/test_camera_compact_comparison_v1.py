"""Distance/FOV compensation is exact only on the frozen aim plane."""
import copy
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_camera_compact_comparison_v1 as compact


def row():
    return {'t': 0., 'position': [0., 500., 100.], 'look_at': [0., 0., 100.],
            'rotation_pitch_yaw_roll': [0., -90., 0.], 'horizontal_fov_degrees': 35.}


@pytest.mark.parametrize('k', [1., .9, .85, .8, .75, .7, .6, .5])
def test_frozen_aim_plane_survives_distance_change(k):
    original = row()
    before = copy.deepcopy(original)
    moved = compact.transform_row(original, k)
    for point in [[-80., 0., 30.], [0., 0., 100.], [80., 0., 170.]]:
        assert compact.project(point, moved, 16 / 9) == pytest.approx(
            compact.project(point, original, 16 / 9), abs=1e-12)
    assert original == before
    assert moved['look_at'] == original['look_at']
    assert moved['rotation_pitch_yaw_roll'] == original['rotation_pitch_yaw_roll']
    assert moved['t'] == original['t']
    assert moved['position'][1] == pytest.approx(500 * k)
    if k == 1:
        assert moved == original


def test_different_body_depth_has_expected_perspective_change():
    original = row()
    k = .75
    moved = compact.transform_row(original, k)
    # 50cm toward camera is z=-50 relative to frozen aim plane.
    point = [50., 50., 100.]
    before = compact.project(point, original, 16 / 9)[0] - .5
    after = compact.project(point, moved, 16 / 9)[0] - .5
    assert after / before == pytest.approx(k * (500 - 50) / (k * 500 - 50))
    assert not math.isclose(after, before)


@pytest.mark.parametrize('factor', [0, -1, 1.1])
def test_reject_unrequested_or_invalid_distance(factor):
    with pytest.raises(ValueError):
        compact.transform_row(row(), factor)


def test_source_pin_failure_creates_no_output(tmp_path):
    source = tmp_path / 'changed_source.json'
    source.write_text('{}', encoding='utf-8')
    output = tmp_path / 'never_created'
    with pytest.raises(ValueError, match='source plan changed'):
        compact.build_plan(output, source)
    assert not output.exists()


@pytest.fixture(scope='module')
def general_plans(tmp_path_factory):
    if not compact.SOURCE.is_file():
        pytest.skip('Pinned project comparison source is unavailable')
    root = tmp_path_factory.mktemp('general_compact')
    legacy, general = root / 'legacy', root / 'general'
    compact.build_plan(legacy)
    compact.build_plan(general, variants=compact.GENERAL_VARIANTS)
    return legacy, general


def test_general_six_uses_original_distance_without_composing_accepted_standard(general_plans):
    legacy_root, general_root = general_plans
    legacy = compact.read(legacy_root / compact.PLAN_NAME)
    plan = compact.read(general_root / compact.PLAN_NAME)
    source = {s['shot_id']: s for s in compact.read(compact.SOURCE)['shots']}
    assert len(plan['shots']) == 28
    assert plan['distance_comparison_percentages'] == [0, 10, 20, 30, 40, 50]
    assert plan['current_landscape_standard_distance_factor'] == .75
    legacy_by_id = {s['shot_id']: s for s in legacy['shots']}
    for group in plan['comparison_groups']:
        shots = [s for s in plan['shots'] if s['shot_id'] in group['shot_ids']]
        assert [s['compact_comparison']['distance_factor'] for s in shots] == [1., .9, .8, .7, .6, .5, .75]
        for shot in shots:
            k = shot['compact_comparison']['distance_factor']
            original = source[shot['source_shot_id']]
            assert {f: shot[f] for f in compact.CLOCK_FIELDS} == {f: original[f] for f in compact.CLOCK_FIELDS}
            for old, new in zip(original['frames'] + [original['endpoint_validation_frame']],
                                shot['frames'] + [shot['endpoint_validation_frame']]):
                expected = compact.add(old['look_at'], compact.mul(compact.sub(old['position'], old['look_at']), k))
                assert new['position'] == pytest.approx(expected)
                assert new['look_at'] == old['look_at']
            if k in (1., .75):
                assert shot == legacy_by_id[shot['shot_id']]


def test_reuse_rejects_changed_shot_metadata_before_copy(general_plans, tmp_path):
    legacy_root, general_root = general_plans
    changed = compact.read(general_root / compact.PLAN_NAME)
    changed['shots'][0]['source_shot_id'] = 'tampered_source'
    target = tmp_path / 'changed'
    compact.write(target / compact.PLAN_NAME, changed)
    with pytest.raises(ValueError, match='exact unchanged'):
        compact.reuse_compact(target, legacy_root)
    assert sorted(p.name for p in target.iterdir()) == [compact.PLAN_NAME]


def test_general_gallery_labels_reference_without_changing_receipt_bound_shots(general_plans, monkeypatch):
    _, general_root = general_plans
    path = general_root / compact.PLAN_NAME
    digest = compact.sha(path)
    monkeypatch.setattr(compact, 'media_rows', lambda *_: {})
    compact.build_gallery(general_root)
    manifest = compact.read(general_root / 'compact_review_delivery_manifest_v1.json')
    clips = manifest['sections'][0]['clips']
    assert len(clips) == 28
    assert [c['distance_reduction_percent'] for c in clips[:7]] == [0, 10, 20, 30, 40, 50, 25]
    assert [c['current_standard_reference'] for c in clips[:7]] == [False] * 6 + [True]
    assert '当前横屏标准' in clips[6]['variant_label_zh']
    assert '最初原距离为基准' in manifest['notice_zh']
    assert all('4.53秒' in c.get('group_warning_zh', '') for c in clips if c['camera_id']=='front_upper')
    assert compact.sha(path) == digest


@pytest.mark.parametrize('variants', [(), ((.75, 'a'), (.75, 'b')), ((float('nan'), 'bad'),)])
def test_invalid_general_variants_do_not_create_output(tmp_path, variants):
    target = tmp_path / 'not_created'
    with pytest.raises(ValueError, match='unique finite'):
        compact.build_plan(target, variants=variants)
    assert not target.exists()


@pytest.mark.parametrize('motion',['ACT_F01_SEXY_DANCE','ACT_M04_LIVING_ROOM_SWING'])
def test_new_general_follow_groups_and_review_note_survive_standard_plan(tmp_path,monkeypatch,motion):
    compact.write(tmp_path/compact.PLAN_NAME,{'shots':[],
        'distance_comparison_percentages':[0,10,20,30,40,50]})
    shots=[]
    for orientation in ('landscape','portrait'):
        for variant in ('before','after'):
            shots.append({'shot_id':motion+'_'+orientation+'_'+variant,'motion_id':motion,
                'motion_label':'test','camera_id':'side_upper','camera_label':'侧面上半身',
                'orientation':orientation,'duration_seconds':2.,'frame_count':60,
                'width':1280,'height':720,'frames':[row()],
                'comparison_group_id':motion+'_'+orientation,
                'comparison_variant_label_zh':'修正前' if variant=='before' else '修正后'})
    path=tmp_path/'follow_standard.json'
    compact.write(path,{'shots':shots})
    monkeypatch.setattr(compact,'media_rows',lambda *_:{})
    compact.build_gallery(tmp_path,path)
    clips=compact.read(tmp_path/'compact_review_delivery_manifest_v1.json')['sections'][0]['clips']
    assert len({c['group_id'] for c in clips})==2
    assert [c['variant_label_zh'] for c in clips]==['修正前','修正后']*2
    assert all('仍待人工确认' in c['group_warning_zh'] for c in clips)
    assert all(('Sexy Dance' if motion=='ACT_F01_SEXY_DANCE' else 'Living Room Swing') in c['label_zh'] for c in clips)
    assert '--port 8897' in (tmp_path/'gallery/打开相机比较.cmd').read_text(encoding='utf-8')
    assert '25%现用标准与0–50%' in (tmp_path/'gallery/index.html').read_text(encoding='utf-8')
