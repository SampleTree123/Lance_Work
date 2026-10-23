"""Focused behavior checks for accelerated travel and scene/renderer contracts."""
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_camera_follow_correction_v1 as repair


def test_accelerate_then_hold_does_not_retain_initial_prediction_offset():
    t = np.arange(301)/30
    y = np.where(t < 2, 25*t*t, np.where(t < 4, 100+100*(t-2)-25*(t-2)**2, 200))
    raw = np.c_[np.zeros(len(t)), y]
    old = repair.prior.stable.low_frequency(raw, t, 1.15)
    old = raw[0]+old-old[0]
    new = repair.endpoint_exact_trend(raw, t)
    # An initially accelerating walk must not shift the entire stopped segment
    # forward after filtering. This was the visible regression in both actions.
    assert np.linalg.norm(old[-1]-raw[-1]) > 10
    assert np.max(np.linalg.norm(new[t >= 5]-raw[t >= 5], axis=1)) < 1e-8
    assert np.max(np.linalg.norm(new-raw, axis=1)) < 2


def test_constant_velocity_and_endpoint_positions_remain_exact():
    t = np.arange(211)/30
    raw = np.c_[3+11*t, 7-17*t]
    new = repair.endpoint_exact_trend(raw, t)
    assert np.max(np.abs(new-raw)) < 1e-9
    assert np.array_equal(new[[0,-1]], raw[[0,-1]])


def test_frozen_scene_overlay_and_render_plan_are_same_cameras():
    overlay = repair.read(repair.OUT/'follow_correction_v1.json')
    render = repair.read(repair.OUT/'camera_trial_plan_v1.json')
    assert len(overlay['corrected_shots']) == len(render['shots']) == 80
    expected = {s['shot_id']:s for s in overlay['corrected_shots']}
    for shot in render['shots']:
        original = expected[shot['supersedes_shot_id']]
        assert shot['shot_id'] == original['shot_id']+'_followfix_v1'
        assert shot['frames'] == original['frames']
        assert shot['endpoint_validation_frame'] == original['endpoint_validation_frame']
        assert shot['trajectory_sha256'] == original['trajectory_sha256']
    for record in overlay['basepins']:
        assert repair.pin(record['path']) == record


def test_other_actions_and_accepted_face_plan_have_no_modified_shots():
    base = repair.read(repair.NONFACE)
    full = repair.read(repair.OUT/'corrected_full_nonface_plan_v1.json')
    unchanged = [(a,b) for a,b in zip(base['shots'],full['shots']) if a['motion_id'] not in repair.MOTIONS]
    assert len(unchanged) == 1120
    assert all(a == b for a,b in unchanged)
    manifest = repair.read(repair.OUT/'follow_correction_v1.json')
    assert manifest['face_plan_unchanged'] == repair.pin(repair.FACE)
