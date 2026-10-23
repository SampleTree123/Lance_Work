import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('ue_compose_native_face_body_v1', Path(__file__).parents[1] / 'ue_compose_native_face_body_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def hierarchy():
    return {'root': 'None', 'pelvis': 'root', 'neck_01': 'pelvis', 'neck_02': 'neck_01', 'head': 'neck_02',
            'facialbone': 'head', 'jawroot': 'facialbone', 'upperjaw': 'facialbone',
            'l_eye': 'facialbone', 'r_eye': 'facialbone', 'teeth01': 'upperjaw', 'teeth02': 'jawroot',
            'tongue01': 'jawroot', 'tongue02': 'tongue01', 'tongue03': 'tongue02'}


def test_facial_scope_keeps_body_and_head_neck_out():
    assert set(m.select_face_bones(hierarchy())) == m.FACE_BONES
    assert not set(m.select_face_bones(hierarchy())) & m.FORBIDDEN_FACE_BONES


def test_unexpected_descendant_cannot_silently_override_body():
    parents = hierarchy()
    parents['hand_l'] = 'facialbone'
    with pytest.raises(ValueError, match='hierarchy'):
        m.select_face_bones(parents)


def test_disconnected_jaw_is_not_silently_accepted():
    parents = hierarchy()
    parents['jawroot'] = 'pelvis'
    with pytest.raises(ValueError):
        m.select_face_bones(parents)


def test_crop_and_rate_preserve_source_offset_and_do_not_accelerate_body():
    assert m.face_time(0, 2, 5, 1.5, 'loop') == 2
    assert m.face_time(1, 2, 5, 1.5, 'loop') == 3.5
    assert m.face_time(2, 2, 5, 1.5, 'loop') == 2
    assert m.face_time(3, 2, 5, 1.5, 'hold') == 5


@pytest.mark.parametrize('args', [(0, 5, 2, 1, 'loop'), (0, 0, 1, 0, 'loop'),
    (float('nan'), 0, 1, 1, 'loop'), (0, 0, 1, 1, 'once'), (-1, 0, 1, 1, 'loop')])
def test_invalid_time_contract_fails(args):
    with pytest.raises(ValueError):
        m.face_time(*args)


def test_explicit_head_neck_curve_ownership():
    for name in ('Head_Turn_Up', 'Head_L', 'CTRL_expressions_neckThroatUp', 'Neck_Twist'):
        assert m.excluded_body_control_curve(name)
    for name in ('CTRL_expressions_eyeBlinkL', 'C_BlinkL', 'CTRL_expressions_jawOpen', 'V_Open'):
        assert not m.excluded_body_control_curve(name)


def test_envelope_resets_each_window_and_both_composite_ends():
    def env(t): return m.face_envelope(t, 7, 3, 1, 'loop', .3)
    for t in (0,3,6,7): assert env(t) == pytest.approx(0)
    for t in (.3,2.7,3.3,6.7): assert env(t) == pytest.approx(1)
    assert env(.15) == pytest.approx(.5)
    assert env(6.85) == pytest.approx(.5)


def test_fade_uses_playback_seconds_and_hold_returns_neutral():
    assert m.face_envelope(.15,5,4,2,'loop',.3) == pytest.approx(.5)
    assert m.face_envelope(2,5,4,2,'loop',.3) == 0
    assert m.face_envelope(3,5,4,2,'hold',.3) == 0
    assert m.face_envelope(0,5,4,2,'loop',0) == 1
    with pytest.raises(ValueError): m.face_envelope(0,1,4,1,'loop',.6)


def test_quaternion_blend_shortest_path_and_normalization():
    neutral = [1,2,3,0,0,0,1,1,1,1]
    equivalent = [3,4,5,0,0,0,-1,2,2,2]
    halfway = m.blend_transform_values(neutral,equivalent,.5)
    assert halfway == pytest.approx([2,3,4,0,0,0,1,1.5,1.5,1.5])
    turned = [3,4,5,0,0,1,0,2,2,2]
    result = m.blend_transform_values(neutral,turned,.5)
    assert sum(v*v for v in result[3:7]) == pytest.approx(1)
    assert result[5] == pytest.approx(2**-.5)
    # A quarter of 180 degrees is 45 degrees: this distinguishes slerp from nlerp.
    import math
    quarter = m.blend_transform_values(neutral,turned,.25)
    assert quarter[5] == pytest.approx(math.sin(math.pi/8))
    assert quarter[6] == pytest.approx(math.cos(math.pi/8))
    assert m.blend_transform_values(neutral,turned,0) == pytest.approx(neutral)
    assert m.blend_transform_values(neutral,turned,1) == pytest.approx(turned)


def test_pose_metrics_use_cm_degrees_and_unitless_scale_separately():
    import math
    expected = [0,0,0,0,0,0,1,1,1,1]
    angle = math.radians(.01)
    actual = [.0003,.0004,0,0,0,math.sin(angle/2),math.cos(angle/2),1.00002,1,1]
    errors = m.transform_metric_errors(actual,expected)
    assert errors['translation_cm'] == pytest.approx(.0005)
    assert errors['rotation_degrees'] == pytest.approx(.01)
    assert errors['scale_abs'] == pytest.approx(.00002)
    assert all(value < m.FACE_TRANSFORM_TOLERANCES[key] for key,value in errors.items())
    actual[0] = .01
    assert m.transform_metric_errors(actual,expected)['translation_cm'] > m.FACE_TRANSFORM_TOLERANCES['translation_cm']


def test_pose_metrics_ignore_quaternion_sign_and_length_but_reject_real_rotation():
    import math
    expected = [0,0,0,0,0,0,1,1,1,1]
    actual = [0,0,0,0,0,0,-1.000001,1,1,1]
    assert m.transform_metric_errors(actual,expected)['rotation_degrees'] == 0
    actual[5:7] = [math.sin(math.radians(.21)/2),math.cos(math.radians(.21)/2)]
    assert m.transform_metric_errors(actual,expected)['rotation_degrees'] > m.FACE_TRANSFORM_TOLERANCES['rotation_degrees']
    actual[3:7] = [0,0,0,0]
    with pytest.raises(ValueError): m.transform_metric_errors(actual,expected)
