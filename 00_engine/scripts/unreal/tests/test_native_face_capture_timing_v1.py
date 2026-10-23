"""Regression model follows UE 5.8's public single-node call semantics.

OverrideAnimationData evaluates the currently configured instance; setting an
asset resets time to zero; SetPosition alone never refreshes a pose or curves.
This tests ordering, not actual Unreal rendering or animation compression.
"""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def capture_module(monkeypatch):
    monkeypatch.setitem(sys.modules, 'unreal', SimpleNamespace())
    spec = importlib.util.spec_from_file_location('capture_timing_test', Path(__file__).parents[1] / 'ue_capture_native_face_review_v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def curves_at(asset, time):
    # Non-neutral 0 seconds and a narrow blink distinguish adjacent samples.
    return {'mouth': .2 + time / 10 if asset == 'new_face' else .03,
            'blink': max(0., 1. - abs(time - .2) * 30) if asset == 'new_face' else .1}


class SingleNode:
    def __init__(self):
        self.asset, self.position, self.loop, self.playing, self.rate = 'old_body', .7, True, True, .8

    def set_animation_asset(self, asset, loop, rate):
        self.asset, self.loop, self.rate, self.position = asset, loop, rate, 0.

    def set_playing(self, playing):
        self.playing = playing


class Body:
    def __init__(self):
        self.instance = SingleNode()
        self.evaluations = []
        self.saved = None
        self.curves = curves_at(self.instance.asset, self.instance.position)

    def override_animation_data(self, asset, loop, playing, position, rate):
        self.saved = (asset, loop, playing, position, rate)
        # Already in SingleNode mode: SetAnimationMode does not reinitialize.
        # TickAnimation(0) + RefreshBoneTransforms evaluate existing live state.
        self.curves = curves_at(self.instance.asset, self.instance.position)
        self.evaluations.append((self.instance.asset, self.instance.position))

    def get_anim_instance(self):
        return self.instance

    def set_position(self, position, fire_notifies):
        assert fire_notifies is False
        self.instance.position = position


def test_each_sample_including_zero_and_blink_is_evaluated_at_requested_time(capture_module):
    body = Body()
    for time in (0., 1/30, 5/30, 6/30, 7/30, 5.):
        capture_module.apply_animation_state(body, 'new_face', False, False, time, 1.)
        assert body.instance.position == time
        assert body.evaluations[-1] == ('new_face', time)
        assert body.curves == curves_at('new_face', time)
        assert body.instance.playing is False
        assert body.saved == ('new_face', False, False, time, 1.)


def test_source_semantics_reproduce_old_one_sample_delay():
    body = Body()
    for time in (0., 1/30, 6/30):
        prior = (body.instance.asset, body.instance.position)
        body.override_animation_data('new_face', False, False, time, 1.)
        body.instance.set_animation_asset('new_face', False, 1.)
        body.instance.set_playing(False)
        body.set_position(time, False)
        assert body.evaluations[-1] == prior
        assert body.curves == curves_at(*prior)
        assert body.curves != curves_at('new_face', time)


def test_restore_evaluates_original_asset_time_and_retains_playback_flags(capture_module):
    body = Body()
    old = ('old_body', True, True, .7, .8)
    capture_module.apply_animation_state(body, 'new_face', False, False, 5., 1.)
    capture_module.apply_animation_state(body, *old)
    assert body.evaluations[-1] == ('old_body', .7)
    assert body.curves == curves_at('old_body', .7)
    instance = body.instance
    assert (instance.asset, instance.loop, instance.playing, instance.position, instance.rate) == old
    assert body.saved == old


def test_repeating_same_zero_time_still_evaluates_without_advancing(capture_module):
    body = Body()
    for _ in range(2):
        capture_module.apply_animation_state(body, 'new_face', False, False, 0., 1.)
        assert body.evaluations[-1] == ('new_face', 0.)
        assert body.curves['mouth'] == .2
        assert body.instance.position == 0.
