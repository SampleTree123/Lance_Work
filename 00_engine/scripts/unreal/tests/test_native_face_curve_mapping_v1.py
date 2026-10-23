import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('native_face_curve_mapping_v1', Path(__file__).parents[1] / 'native_face_curve_mapping_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def build(names=None, targets=None):
    names = names or ['Eye_Blink_L', 'C_BlinkL_LookDownL', 'Mouth_Mouth_Press_UL']
    targets = targets or ['CTRL_expressions_eyeBlinkL', 'C_BlinkL_LookDownL', 'CTRL_expressions_mouthPressUL']
    return m.build_mapping(names, [{'path': '/Game/Body.Body', 'morph_names': targets},
                                  {'path': '/Game/Eye.Eye', 'morph_names': targets[:2]}], targets,
                           {'Eye_Blink_L': 'CTRL_expressions_eyeBlinkL'})


def test_preserves_correctives_negative_weights_and_component_bindings():
    mapping = build()
    out = m.map_samples(mapping, [{'frame': 0, 'ticks': 0,
        'weights': {'Eye_Blink_L': -0.02, 'C_BlinkL_LookDownL': 0.13, 'Mouth_Mouth_Press_UL': 0}}])
    assert out['samples'][0]['curves'] == {'CTRL_expressions_eyeBlinkL': -0.02, 'C_BlinkL_LookDownL': 0.13}
    assert out['bone_animation_included'] is False
    assert out['complete_facial_animation_verified'] is False
    assert 'CTRL_expressions_mouthPressUL' not in mapping['component_curves']['/Game/Body.Body']


def test_repeated_word_does_not_become_a_guessed_alias():
    mapping = build()
    assert mapping['unmapped'] == {'Mouth_Mouth_Press_UL': 'no_official_or_exact_exported_profile_name'}
    with pytest.raises(ValueError, match='Active expression'):
        m.map_samples(mapping, [{'frame': 0, 'weights': {'Eye_Blink_L': 0, 'C_BlinkL_LookDownL': 0, 'Mouth_Mouth_Press_UL': .001}}])


def test_missing_actual_ue_morph_cannot_be_assumed_from_profile():
    mapping = m.build_mapping(['Jaw_Open'], [{'path': '/Game/Body.Body', 'morph_names': ['Other']}], ['CTRL_expressions_jawOpen'], {'Jaw_Open': 'CTRL_expressions_jawOpen'})
    assert mapping['unmapped']['Jaw_Open'] == 'exported_name_missing_from_selected_ue_meshes'
    with pytest.raises(ValueError, match='Active expression'):
        m.map_samples(mapping, [{'frame': 0, 'weights': {'Jaw_Open': .1}}])


@pytest.mark.parametrize('targets', [['CTRL_expressions_eyeBlinkL', 'Eye_Blink_L'], ['X', 'X']])
def test_name_collisions_are_not_silently_resolved(targets):
    with pytest.raises(ValueError):
        build(targets=targets)


@pytest.mark.parametrize('weights', [{}, {'Eye_Blink_L': 0},
    {'Eye_Blink_L': float('nan'), 'C_BlinkL_LookDownL': 0, 'Mouth_Mouth_Press_UL': 0},
    {'Eye_Blink_L': True, 'C_BlinkL_LookDownL': 0, 'Mouth_Mouth_Press_UL': 0}])
def test_incomplete_or_invalid_sampling_fails(weights):
    with pytest.raises(ValueError):
        m.map_samples(build(), [{'frame': 0, 'weights': weights}])


def test_frame_order_and_timing_not_assumed():
    mapping = build(['Eye_Blink_L'], ['CTRL_expressions_eyeBlinkL'])
    samples = [{'frame': 5, 'weights': {'Eye_Blink_L': .2}}, {'frame': 6, 'weights': {'Eye_Blink_L': .3}}]
    assert m.map_samples(mapping, samples)['samples'][0] == {'frame': 5, 'curves': {'CTRL_expressions_eyeBlinkL': .2}}
    with pytest.raises(ValueError, match='Frames'):
        m.map_samples(mapping, samples[::-1])


def test_multiple_profile_avatars_are_ambiguous():
    one = {'ExpressionSet': '6', 'Expression': {'CTRL_expressions_eyeBlinkL': {'Bones': {}}}}
    assert m.exported_profile_names({'a': one}) == ['CTRL_expressions_eyeBlinkL']
    with pytest.raises(ValueError):
        m.exported_profile_names({'a': one, 'b': one})


def test_official_map_resolves_repeated_word_only_with_explicit_evidence(tmp_path):
    forward = tmp_path / 'map.ini'
    forward.write_text('[CC2MH]\nMouth_Mouth_Press_UL=CTRL_expressions_mouthPressUL\nMouth_Mouth_Press_UL=CTRL_expressions_mouthPressUL\n')
    official = m.load_official_name_map(forward)
    target = 'CTRL_expressions_mouthPressUL'
    mapping = m.build_mapping(['Mouth_Mouth_Press_UL'], [{'path': '/Game/Body.Body', 'morph_names': [target]}], [target], official['curve_map'])
    assert mapping['curve_map'] == {'Mouth_Mouth_Press_UL': target}
    assert len(official['sources'][0]['sha256']) == 64


def test_official_mapping_rejects_conflicting_duplicates(tmp_path):
    forward = tmp_path / 'map.ini'
    forward.write_text('[CC2MH]\nJaw_Open=First\nJaw_Open=Second\n')
    with pytest.raises(ValueError, match='Conflicting'):
        m.load_official_name_map(forward)


def test_official_mapping_rejects_reverse_disagreement(tmp_path):
    forward = tmp_path / 'map.ini'
    forward.write_text('[CC2MH]\nJaw_Open=CTRL_expressions_jawOpen\n')
    reverse = tmp_path / 'reverse.json'
    reverse.write_text('{"Mappings":{"CTRL_expressions_jawOpen":"Wrong"}}')
    with pytest.raises(ValueError, match='disagree'):
        m.load_official_name_map(forward, reverse)
