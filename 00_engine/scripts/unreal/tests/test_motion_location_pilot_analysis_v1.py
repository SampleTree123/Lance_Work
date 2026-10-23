"""Movement screening must distinguish broad corners from bodily sway."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('motion_location_analysis', Path(__file__).parents[1] / 'motion_location_pilot_analysis_v1.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_straight_travel_remains_straight_after_rotation_and_translation():
    points = np.column_stack((np.linspace(0, 800, 201), 8 * np.sin(np.linspace(0, 30, 201))))
    theta = .73
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    first = mod.metrics(points)
    second = mod.metrics(points @ rotation + [9100, -8000])
    assert first['classification'] == second['classification'] == 'straight_travel'
    assert first['cross_span_cm'] == pytest.approx(second['cross_span_cm'])
    assert first['along_span_cm'] == pytest.approx(second['along_span_cm'])


def test_large_right_angle_turn_is_not_straight_but_small_dance_can_move_both_ways():
    turn = np.concatenate((np.column_stack((np.linspace(0, 500, 51), np.zeros(51))),
                           np.column_stack((np.full(51, 500), np.linspace(0, 500, 51)))))
    assert not mod.metrics(turn)['accepted_geometry']
    theta = np.linspace(0, 2 * np.pi, 101)
    assert mod.metrics(np.column_stack((90 * np.cos(theta), 90 * np.sin(theta))))['classification'] == 'small_area'


def test_short_window_uses_requested_interpolated_endpoints():
    clip = {'frames': [{'t': t, 'bones': {b: [100 * t, 0, 100] for b in ('root', 'pelvis')}} for t in (0, 1, 2, 3)]}
    result = mod.window_metrics(clip, .25, 2.75)
    assert result['root']['along_span_cm'] == pytest.approx(250)
    assert result['pelvis']['bounds_xy_cm']['min'][0] == pytest.approx(25)


def test_line_reversal_is_reported_without_inventing_multidirectional_travel():
    result = mod.metrics([[0, 0], [600, 0], [300, 0]])
    assert result['classification'] == 'straight_travel'
    assert result['maximum_reverse_excursion_cm'] == pytest.approx(300)


def test_invalid_geometry_is_rejected_instead_of_silently_passing():
    with pytest.raises(ValueError):
        mod.metrics([[0, 0], [float('nan'), 4]])
