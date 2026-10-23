import copy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_wardrobe_coverage_review_v1 import evaluate_playback_samples


def sample(position, point, playing=True):
    bones = {"hand_l": [point, 0, 0]}
    return {"rows": [{"actor": "review_1", "playing": playing, "position": position,
                      "bones": bones, "followers": [{"name": "Shirts",
                          "leader_is_body": True, "bones": copy.deepcopy(bones)}]}]}


def samples():
    return ([sample(0, 0), sample(0.7, 4), sample(1.4, 5)],
            [sample(0, 0, False), sample(0, 0, False)])


def test_live_motion_pause_and_followers_pass():
    assert evaluate_playback_samples(*samples()) == []


def test_play_flag_without_tick_is_not_motion():
    moving, paused = samples()
    errors = evaluate_playback_samples([moving[0]] * 3, paused)
    assert any("time did not advance" in e for e in errors)
    assert any("bones did not move" in e for e in errors)


def test_time_without_bone_changes_is_not_motion():
    _, paused = samples()
    errors = evaluate_playback_samples([sample(t, 0) for t in (0, 0.5, 1)], paused)
    assert any("bones did not move" in e for e in errors)


@pytest.mark.parametrize("defect", ["leader", "pose", "pause", "actors"])
def test_detects_broken_following_and_pause(defect):
    moving, paused = samples()
    if defect == "leader":
        moving[1]["rows"][0]["followers"][0]["leader_is_body"] = False
    elif defect == "pose":
        moving[1]["rows"][0]["followers"][0]["bones"]["hand_l"][0] = 0
    elif defect == "pause":
        paused[1] = sample(1, 4)
    else:
        moving[1]["rows"] = []
    assert evaluate_playback_samples(moving, paused)


@pytest.mark.parametrize("original", [True, False])
def test_background_setting_survives_module_reload_and_restores(monkeypatch, original):
    settings = SimpleNamespace(value=original)
    settings.get_editor_property = lambda key: settings.value
    settings.set_editor_property = lambda key, value: setattr(settings, "value", value)
    fake_unreal = SimpleNamespace(load_object=lambda outer, path: settings)
    monkeypatch.setitem(sys.modules, "unreal", fake_unreal)
    path = Path(__file__).resolve().parents[1] / "ue_wardrobe_coverage_review_v1.py"
    def load():
        spec = importlib.util.spec_from_file_location("coverage_worker_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    load().preview_background_updates(True)
    assert settings.value is False
    load().preview_background_updates(True)
    assert settings.value is False
    load().preview_background_updates(False)
    assert settings.value is original
    load().preview_background_updates(False)
    assert settings.value is original


@pytest.mark.parametrize("playing", [True, False])
def test_serialized_reference_also_binds_live_instance(monkeypatch, playing):
    class Motion:
        pass
    motion = Motion()
    instance = SimpleNamespace(asset=None, playing=True)
    instance.get_animation_asset = lambda: instance.asset
    instance.set_playing = lambda value: setattr(instance, "playing", value)
    body = SimpleNamespace()
    body.get_editor_property = lambda key: SimpleNamespace(get_editor_property=lambda key: motion)
    body.set_enable_animation = lambda value: None
    body.set_component_tick_enabled = lambda value: None
    body.set_editor_property = lambda key, value: None
    body.set_animation_mode = lambda mode: None
    def play_animation(value, looping):
        assert looping is True
        instance.asset = value
    body.play_animation = play_animation
    body.set_play_rate = lambda value: None
    body.set_position = lambda position, notifies: None
    body.override_animation_data = lambda *args: None
    body.get_anim_instance = lambda: instance
    body.is_playing = lambda: instance.playing
    body.set_update_animation_in_editor = lambda value: None
    monkeypatch.setitem(sys.modules, "unreal", SimpleNamespace(
        AnimSequence=Motion, AnimationMode=SimpleNamespace(ANIMATION_SINGLE_NODE=1)))
    path = Path(__file__).resolve().parents[1] / "ue_wardrobe_coverage_review_v1.py"
    spec = importlib.util.spec_from_file_location("coverage_binding_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.set_body_playback(body, playing)
    assert instance.asset is motion
    assert instance.playing is playing
