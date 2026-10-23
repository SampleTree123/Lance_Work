"""Scope, preservation and measurement checks for the general follow extension."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import build_camera_follow_general_correction_v2 as general


def test_scope_screen_leaves_local_sway_and_well_followed_travel_untouched():
    t=np.arange(301)/30
    sway=np.c_[20*np.sin(t*2),np.zeros(len(t))]
    assert not general.needs_correction(sway,np.zeros_like(sway),t)
    linear=np.c_[20*t,np.zeros(len(t))]
    assert not general.needs_correction(linear,linear,t)
    assert general.needs_correction(linear,linear+np.array([25,0]),t)


def test_all_actions_audited_and_only_material_travel_extended():
    evidence=general.repair.read(general.OUT/'follow_correction_evidence_v2.json')
    assert evidence['inventory']=={'total_motion_count':30,'previously_accepted_count':2,
        'newly_audited_count':28,'newly_corrected_count':6,'calm_motion_paths_unchanged_count':22}
    selected=[a for a in evidence['actions'] if a['decision']=='correct_material_travel']
    assert {a['motion_id'] for a in selected}==set(general.MOTIONS)
    assert all(a['travel_span_xy_cm']>100 and a['before_pelvis_trend_error']['p95_distance_cm']>20 for a in selected)
    assert all(all(r['checks'].values()) for r in evidence['reports'])
    assert len(evidence['reports'])==240
    assert all(evidence['invariant_checks'].values())


def test_accepted_paths_and_calm_source_objects_are_exact():
    overlay=general.repair.read(general.OUT/'follow_correction_v2.json')
    cumulative={s['shot_id']:s for s in overlay['corrected_shots']}
    prior=general.repair.read(general.ACCEPTED)
    assert len(cumulative)==320
    assert all(cumulative[s['shot_id']]==s for s in prior['corrected_shots'])
    base=general.repair.read(general.repair.NONFACE)
    full=general.repair.read(general.OUT/'corrected_full_nonface_plan_v2.json')
    protected=[(a,b) for a,b in zip(base['shots'],full['shots'])
        if a['motion_id'] not in set(general.MOTIONS)|set(general.repair.MOTIONS)]
    assert len(protected)==880 and all(a==b for a,b in protected)
    for record in overlay['basepins']:
        assert general.repair.pin(record['path'])==record


def test_comparison_before_and_after_use_identical_body_and_composition():
    plan=general.repair.read(general.OUT/'follow_comparison_plan_v2.json')
    shots={s['shot_id']:s for s in plan['shots']}
    assert len(shots)==26 and len(plan['comparison_pairs'])==13
    for pair in plan['comparison_pairs']:
        before=shots[pair['before_shot_id']];after=shots[pair['after_shot_id']]
        assert all(before[k]==after[k] for k in general.repair.CLOCK)
        assert before['common_preset_parameters']==after['common_preset_parameters']
        assert before['endpoint_distances_cm']==after['endpoint_distances_cm']
        assert before['comparison_group_id']==after['comparison_group_id']
        assert before['comparison_variant_label_zh']=='修正前'
        assert after['comparison_variant_label_zh']=='修正后'
        assert after['trajectory_sha256']==pair['after_trajectory_sha256']


def test_kinematics_exposes_derivative_cost_separately_from_position_error():
    t=np.arange(301)/30
    linear=np.c_[5*t,np.zeros(len(t))]
    k=general.kinematics(linear,t)
    assert abs(k['speed_cm_per_second']['rms']-5)<1e-10
    assert k['acceleration_cm_per_second2']['max']<1e-9
    evidence=general.repair.read(general.OUT/'follow_correction_evidence_v2.json')
    swing=next(a for a in evidence['actions'] if a['motion_id']=='ACT_M04_LIVING_ROOM_SWING')
    derivatives=swing['pelvis_xy_kinematics']
    assert derivatives['after']['acceleration_cm_per_second2']['rms']>derivatives['before']['acceleration_cm_per_second2']['rms']
    assert swing['after_pelvis_trend_error']['p95_distance_cm']<swing['before_pelvis_trend_error']['p95_distance_cm']/4
