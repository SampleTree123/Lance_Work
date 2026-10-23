"""FName casing may differ between imported raw curves and SOURCE evaluation."""
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('composer_curve_case', Path(__file__).parents[1] / 'ue_compose_native_face_body_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_raw_camelcase_and_source_lowercase_are_present_but_missing_is_not():
    raw = ['CTRL_expressions_eyeBlinkL', 'CTRL_expressions_jawOpen']
    evaluated = [name.lower() for name in raw]
    assert m.curve_names_present(raw, evaluated)
    assert m.curve_names_present(evaluated, raw)
    assert not m.curve_names_present(raw, evaluated[:1])
    assert not m.curve_names_present(raw, ['unrelated', evaluated[0]])


def test_new_lowercase_source_uses_camelcase_allowlist_and_preserves_actual_names():
    result = m.classify_curve_names(
        ['ctrl_expressions_eyeblinkl', 'ctrl_expressions_jawopen', 'head_turn_l'],
        ['CTRL_expressions_eyeBlinkL', 'CTRL_expressions_jawOpen', 'Head_Turn_L'],
        ['CTRL_EXPRESSIONS_EYEBLINKL', 'BODY_Custom', 'HEAD_TURN_L'])
    assert result['face_curves'] == ['ctrl_expressions_eyeblinkl', 'ctrl_expressions_jawopen']
    assert result['replace_body_curves'] == ['CTRL_EXPRESSIONS_EYEBLINKL']
    assert result['unrelated_curves'] == ['BODY_Custom', 'HEAD_TURN_L']
    assert result['excluded_curves'] == ['head_turn_l']


def test_legacy_raw_names_remain_camelcase_in_report_and_api_lists():
    result = m.classify_curve_names(['CTRL_expressions_eyeBlinkL'], ['ctrl_expressions_eyeblinkl'], ['ctrl_expressions_eyeblinkl'])
    assert result['face_curves'] == ['CTRL_expressions_eyeBlinkL']
    assert result['replace_body_curves'] == ['ctrl_expressions_eyeblinkl']
    assert result['unrelated_curves'] == []


@pytest.mark.parametrize('name', ['head_turn_l', 'HEAD_TURN_L', 'neck_twist', 'NECK_TWIST', 'ctrl_expressions_neckThroatUp'])
def test_body_control_exclusion_is_case_insensitive(name):
    assert m.excluded_body_control_curve(name)


def test_truly_unknown_source_cannot_pass_allowlist():
    with pytest.raises(ValueError, match='unclassified.*CTRL_expressions_unknown'):
        m.classify_curve_names(['CTRL_expressions_eyeBlinkL', 'CTRL_expressions_unknown'], ['ctrl_expressions_eyeblinkl'], [])


@pytest.mark.parametrize('inventory', ['source', 'allowed', 'body'])
def test_conflicting_case_duplicates_inside_each_inventory_fail(inventory):
    names = {'source': ['Blink'], 'allowed': ['blink'], 'body': []}
    names[inventory] = ['Blink', 'blink']
    with pytest.raises(ValueError, match='collision'):
        m.classify_curve_names(names['source'], names['allowed'], names['body'])


def test_evaluator_case_collision_fails_instead_of_zero_fallback():
    with pytest.raises(ValueError, match='collision'):
        m.curve_names_present(['Blink'], ['Blink', 'blink'])


def test_extra_evaluator_curves_do_not_obscure_required_presence():
    assert m.curve_names_present(['Blink'], ['blink', 'jaw'])
    assert not m.curve_names_present(['Blink'], ['jaw'])


def test_empty_allowlist_or_only_excluded_source_still_fails():
    with pytest.raises(ValueError, match='approved'):
        m.classify_curve_names(['Blink'], [], [])
    with pytest.raises(ValueError, match='no face curves'):
        m.classify_curve_names(['head_turn_l'], ['Head_Turn_L'], [])
