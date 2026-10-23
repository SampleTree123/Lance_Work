"""Accepted landscape standard preserves clocks and cannot silently compound."""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import camera_standard_v3 as standard


@pytest.fixture
def config():
    return {'schema': standard.SCHEMA,
            'standard_id': 'nonface_landscape_distance050_fov_compensated_v3',
            'landscape_distance_factor': .5, 'scope': 'nonface_landscape',
            'excluded_camera_ids': ['front_head'], 'compensate_horizontal_fov': True}


@pytest.fixture
def shot():
    def row(t):
        return {'t': float(t), 'position': [float(t), 500. + t * 20, 100.],
                'look_at': [float(t), 0., 100.], 'rotation_pitch_yaw_roll': [0., -90., 0.],
                'horizontal_fov_degrees': 35. + t}
    rows = [row(t) for t in (0, 1, 2)]
    return {'shot_id': 'original', 'motion_id': 'M01', 'camera_id': 'front_upper',
            'orientation': 'landscape', 'frame_count': 2, 'fps': 1,
            'source_animation': '/source', 'source_start_seconds': 4.,
            'source_end_seconds': 6., 'source_body_play_rate': 1.,
            'window_start_seconds': 4., 'duration_seconds': 2.,
            'frames': rows[:-1], 'endpoint_validation_frame': rows[-1],
            'trajectory_sha256': standard.canonical_sha(rows),
            'path_metrics': {'obsolete_metric': 7}, 'framing_diagnostics': {'passed': True},
            'quality': {'passed': True}, 'endpoint_distances_cm': [500., 540.],
            'calibration_references': {'distance_cm': 500.}, 'dolly_clock': {'distance': 540.}}


def test_all_keys_endpoint_aim_plane_and_source_clock_are_preserved(shot, config):
    before = copy.deepcopy(shot)
    transformed = standard.apply_standard(shot, config)
    assert shot == before
    for field in ('shot_id', 'motion_id', 'camera_id', 'orientation', 'frame_count', 'fps',
                  'source_animation', 'source_start_seconds', 'source_end_seconds',
                  'source_body_play_rate', 'window_start_seconds', 'duration_seconds'):
        assert transformed[field] == before[field]
    old_rows = shot['frames'] + [shot['endpoint_validation_frame']]
    new_rows = transformed['frames'] + [transformed['endpoint_validation_frame']]
    for old, new in zip(old_rows, new_rows):
        assert new['t'] == old['t']
        assert new['look_at'] == old['look_at']
        assert new['rotation_pitch_yaw_roll'] == old['rotation_pitch_yaw_roll']
        assert new['position'][1] == pytest.approx(old['position'][1] * .5)
        old_scale = old['position'][1] * math.tan(math.radians(old['horizontal_fov_degrees'] / 2))
        new_scale = new['position'][1] * math.tan(math.radians(new['horizontal_fov_degrees'] / 2))
        assert old_scale == pytest.approx(new_scale, abs=1e-10)
        # Two transverse coordinates on the target plane project identically.
        for transverse in (-80., 70.):
            assert transverse / new_scale == pytest.approx(transverse / old_scale, abs=1e-12)
    assert transformed['trajectory_sha256'] == standard.canonical_sha(new_rows)
    assert transformed['endpoint_distances_cm'] == [250., 270.]


@pytest.mark.parametrize('orientation,camera', [('portrait', 'front_upper'),
                                              ('portrait', 'front_head'), ('landscape', 'front_head')])
def test_portrait_and_face_objects_remain_exactly_unchanged(shot, config, orientation, camera):
    shot.update(orientation=orientation, camera_id=camera)
    result = standard.apply_standard(shot, config)
    assert result == shot
    assert result is not shot
    assert result['frames'] is not shot['frames']


def test_reapplying_standard_is_idempotent_not_distance_025(shot, config):
    first = standard.apply_standard(shot, config)
    second = standard.apply_standard(first, config)
    assert second == first
    assert second is not first
    assert second['frames'][0]['position'][1] == 250.
    assert second['frames'][0]['position'][1] != 500. * .5 * .5


def test_tampered_derived_rows_or_configuration_are_rejected(shot, config):
    first = standard.apply_standard(shot, config)
    damaged = copy.deepcopy(first)
    damaged['endpoint_validation_frame']['position'][1] += 1
    with pytest.raises(ValueError, match='marker or trajectory differs'):
        standard.apply_standard(damaged, config)
    with pytest.raises(ValueError, match='marker or trajectory differs'):
        standard.apply_standard(first, dict(config, source_pin_version=2))


def test_previous_geometry_claims_are_explicitly_historical(shot, config):
    result = standard.apply_standard(shot, config)
    history = result[standard.MARKER]['superseded_source_diagnostics']
    for key in ('path_metrics', 'framing_diagnostics', 'quality', 'calibration_references', 'dolly_clock'):
        assert history[key] == shot[key]
    assert 'framing_diagnostics' not in result
    assert 'quality' not in result
    assert 'obsolete_metric' not in result['path_metrics']
    assert result['path_metrics']['max_camera_speed_cm_per_second'] == pytest.approx(math.hypot(1., 10.))
    assert 'no derived mesh silhouette' in result['geometry_pass_scope']


def test_compact_candidate_cannot_silently_receive_a_second_transform(shot, config):
    shot['compact_comparison'] = {'distance_factor': .5}
    with pytest.raises(ValueError, match='original-distance source'):
        standard.apply_standard(shot, config)


@pytest.mark.parametrize('field,value', [('landscape_distance_factor', .9),
                                       ('compensate_horizontal_fov', False)])
def test_unaccepted_standard_is_rejected(shot, config, field, value):
    config[field] = value
    with pytest.raises(ValueError, match='Unsupported'):
        standard.apply_standard(shot, config)


def test_loaded_config_rejects_changed_acceptance_pin(tmp_path, config):
    pins = []
    for role, body in [('original_nonface_plan', {}),
                       ('user_acceptance', {'horizontal': {'accepted_distance_factor_from_original': .5, 'compensate_fov': True}})]:
        path = tmp_path / (role + '.json')
        path.write_text(json.dumps(body), encoding='utf-8')
        pins.append({'role': role, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    config['source_pins'] = pins
    target = tmp_path / 'config.json'
    target.write_text(json.dumps(config), encoding='utf-8')
    assert standard.load_config(target) == config
    Path(pins[1]['path']).write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='source changed'):
        standard.load_config(target)


def test_project_standard_applies_exactly_600_landscape_shots():
    if not standard.DEFAULT_CONFIG.is_file():
        pytest.skip('Project acceptance configuration unavailable')
    config = standard.load_config()
    source = next(pin for pin in config['source_pins'] if pin['role'] == 'original_nonface_plan')
    plan = json.loads(Path(source['path']).read_text(encoding='utf-8-sig'))
    changed = unchanged = 0
    for shot in plan['shots']:
        result = standard.apply_standard(shot, config)
        if shot['orientation'] == 'landscape':
            changed += 1
            assert standard.MARKER in result
            assert result['shot_id'] == shot['shot_id']
            assert standard.apply_standard(result, config) == result
        else:
            unchanged += 1
            assert result == shot
    assert changed == unchanged == 600
