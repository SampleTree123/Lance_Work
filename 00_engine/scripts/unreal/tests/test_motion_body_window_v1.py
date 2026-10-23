"""Time mapping respects complete source motion and never pads or wraps."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('motion_body_window', Path(__file__).parents[1] / 'ue_motion_body_window_v1.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_six_second_walk_maps_to_ten_seconds_without_wrapping():
    result = mod.mapping(60, 1, 683, 683 / 60, 0, 6, 10)
    assert result['frames'] == 600
    assert result['body_play_rate'] == .6
    assert result['source_times'][300] == 3
    assert result['source_times'][-1] == 6
    assert all(a < b for a, b in zip(result['source_times'], result['source_times'][1:]))
    assert not result['body_looped']
    assert result['face_play_rate'] == 1


def test_native_noninteger_second_crop_keeps_original_speed():
    result = mod.mapping(60, 1, 835, 835 / 60, 1.5, 7 + 1 / 60, 5.5 + 1 / 60)
    assert result['source_times'][0] == 1.5
    assert result['source_times'][-1] == 7 + 1 / 60
    assert result['body_play_rate'] == pytest.approx(1)
    assert not result['body_retimed']


@pytest.mark.parametrize('start,end,duration', [(0, 7, 10), (-1, 4, 5), (2, 2, 5), (0, 4, 1.001), (0, float('nan'), 5)])
def test_invalid_or_out_of_source_windows_are_rejected(start, end, duration):
    with pytest.raises(ValueError):
        mod.mapping(60, 1, 360, 6, start, end, duration)


def test_inexact_duration_metadata_cannot_silently_change_source_endpoint():
    with pytest.raises(ValueError):
        mod.mapping(60, 1, 360, 6.2, 0, 6, 10)
